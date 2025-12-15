"""
Subtitle overlay helpers for LangFlix

Responsibilities
- Locate subtitle files for an expression
- Create dual-language SRT (copy when already validated)
- Generate ASS style string from settings
- Apply subtitles via subtitles filter; drawtext fallback when needed
"""

from __future__ import annotations

import glob
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import ffmpeg
import textwrap
import tempfile
import os

from langflix import settings
from langflix.settings import get_expression_subtitle_styling

logger = logging.getLogger(__name__)


# Note: sanitize_expression_for_filename is now imported from langflix.utils.filename_utils
# This function is kept for backward compatibility
from langflix.utils.filename_utils import sanitize_for_expression_filename

def sanitize_expression_for_filename(text: str) -> str:
    """Backward compatibility wrapper - use sanitize_for_expression_filename directly."""
    return sanitize_for_expression_filename(text)


def find_subtitle_file(subtitle_dir: Path, expression_text: str) -> Optional[Path]:
    if not subtitle_dir.exists():
        return None
    safe_expr = "".join(c for c in expression_text if c.isalnum() or c in (" ", "-", "_")).rstrip()
    sanitized = sanitize_expression_for_filename(expression_text)
    patterns = [
        f"expression_*_{safe_expr[:30]}.srt",
        f"expression_{safe_expr[:30]}.srt",
        f"expression_*_{sanitized}.srt",
        f"expression_{sanitized}.srt",
    ]
    for p in patterns:
        matches = list(subtitle_dir.glob(p))
        if matches:
            matches.sort()
            return matches[0]
    # Partial match fallback
    for file_path in subtitle_dir.glob("expression_*.srt"):
        stem = file_path.stem
        if stem.startswith("expression_") and (safe_expr[:20] in stem or sanitized[:20] in stem):
            return file_path
    return None


def _time_to_seconds(time_str: str) -> float:
    """Convert SRT time string (HH:MM:SS,mmm) to seconds"""
    time_str = time_str.replace(',', '.')  # Handle both comma and dot separators
    parts = time_str.split(':')
    if len(parts) != 3:
        raise ValueError(f"Invalid time format: {time_str}")
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds


def _seconds_to_time(seconds: float) -> str:
    """Convert seconds to SRT time string (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace('.', ',')


def adjust_subtitle_timestamps(subtitle_file: Path, offset_seconds: float, output_file: Path) -> Path:
    """
    Adjust all subtitle timestamps by subtracting offset_seconds.
    
    This is used when applying subtitles to a sliced context video.
    The subtitles have absolute timestamps from the original video,
    but the context video starts at context_start_time, so we need
    to subtract that offset to align subtitles with the sliced video.
    
    Args:
        subtitle_file: Source SRT file with absolute timestamps
        offset_seconds: Time offset to subtract (context_start_time in seconds)
        output_file: Output SRT file with adjusted timestamps
        
    Returns:
        Path to output file
    """
    if offset_seconds <= 0:
        # No adjustment needed, just copy
        output_file.parent.mkdir(parents=True, exist_ok=True)
        content = subtitle_file.read_text(encoding="utf-8")
        output_file.write_text(content, encoding="utf-8")
        return output_file
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    content = subtitle_file.read_text(encoding="utf-8")
    lines = content.split('\n')
    
    adjusted_lines = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Check if this line contains a timestamp (format: HH:MM:SS,mmm --> HH:MM:SS,mmm)
        if '-->' in line:
            try:
                # Parse timestamp line
                start_time_str, end_time_str = line.split('-->')
                start_time_str = start_time_str.strip()
                end_time_str = end_time_str.strip()
                
                # Convert to seconds, subtract offset
                start_seconds = _time_to_seconds(start_time_str) - offset_seconds
                end_seconds = _time_to_seconds(end_time_str) - offset_seconds
                
                # Only include subtitles that are still within valid range (after offset)
                if end_seconds > 0:
                    # Adjust to start from 0 if start is negative
                    if start_seconds < 0:
                        start_seconds = 0
                    
                    # Convert back to time string
                    adjusted_start = _seconds_to_time(start_seconds)
                    adjusted_end = _seconds_to_time(end_seconds)
                    
                    adjusted_lines.append(f"{adjusted_start} --> {adjusted_end}")
                else:
                    # This subtitle is before the context start, skip it
                    # Skip the subtitle number and text lines too
                    if i > 0 and adjusted_lines and adjusted_lines[-1].strip().isdigit():
                        adjusted_lines.pop()  # Remove subtitle number
                    i += 1  # Skip timestamp line (already processed)
                    # Skip text lines until next subtitle number or empty line
                    while i < len(lines) and lines[i].strip() and not lines[i].strip().isdigit():
                        i += 1
                    continue
            except (ValueError, IndexError) as e:
                logger.warning(f"Error parsing timestamp line: {line}, error: {e}")
                adjusted_lines.append(line)  # Keep original if parsing fails
        else:
            adjusted_lines.append(line)
        
        i += 1
    
    output_file.write_text('\n'.join(adjusted_lines), encoding="utf-8")
    logger.info(f"Adjusted subtitle timestamps (offset: -{offset_seconds:.3f}s): {output_file}")
    return output_file



def wrap_subtitle_lines(input_path: Path, output_path: Path, max_chars: int = 15) -> Path:
    """
    Read an SRT file and wrap text lines to a maximum width.
    This ensures subtitles do not overflow the screen.
    
    This version parses SRT blocks, removes existing line breaks within text,
    and reflows the text to the specified width.
    
    Args:
        input_path: Source SRT file
        output_path: Destination SRT file
        max_chars: Maximum characters per line (default: 15 for narrow screens)
        
    Returns:
        Path to the wrapped SRT file
    """
    try:
        content = input_path.read_text(encoding='utf-8')
    except Exception as e:
        logger.warning(f"Failed to read SRT for wrapping ({input_path}): {e}")
        return input_path
        
    # Normalize line endings
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    
    # Split into blocks by double newline
    blocks = content.strip().split('\n\n')
    wrapped_blocks = []
    
    for block in blocks:
        if not block.strip():
            continue
            
        lines = block.split('\n')
        if len(lines) < 2:
            wrapped_blocks.append(block)
            continue
            
        # Parse block structure
        index_line = lines[0]
        
        # Find timestamp line
        timestamp_line_idx = -1
        for i, line in enumerate(lines):
            if '-->' in line:
                timestamp_line_idx = i
                break
        
        if timestamp_line_idx == -1:
            wrapped_blocks.append(block)
            continue
            
        timestamp_line = lines[timestamp_line_idx]
        text_lines = lines[timestamp_line_idx + 1:]
        
        # Combine text lines into one, removing existing breaks
        combined_text = " ".join([line.strip() for line in text_lines if line.strip()])
        
        # Check for HTML tags or ASS styling tags - if present, skip wrapping to avoid breaking
        if ('<' in combined_text and '>' in combined_text) or '{\\' in combined_text:
             wrapped_text = "\n".join(text_lines) # Keep original layout
        else:
             try:
                 # Reflow text
                 wrapped_text = textwrap.fill(combined_text, width=max_chars, break_long_words=False)
             except Exception:
                 wrapped_text = combined_text
        
        # Reconstruct block
        new_block = f"{index_line}\n{timestamp_line}\n{wrapped_text}"
        wrapped_blocks.append(new_block)
        
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text('\n\n'.join(wrapped_blocks) + '\n', encoding='utf-8')
    logger.info(f"Wrapped subtitles to {max_chars} chars (reflowed): {output_path}")
    return output_path


def create_dual_language_copy(source_subtitle_file: Path, target_subtitle_file: Path) -> Path:
    target_subtitle_file.parent.mkdir(parents=True, exist_ok=True)
    content = source_subtitle_file.read_text(encoding="utf-8")
    target_subtitle_file.write_text(content, encoding="utf-8")
    return target_subtitle_file


def _hex_to_ass_bgr(color_hex: str) -> str:
    color_hex = color_hex.lstrip("#")
    r = int(color_hex[0:2], 16)
    g = int(color_hex[2:4], 16)
    b = int(color_hex[4:6], 16)
    return f"&H{b:02x}{g:02x}{r:02x}"


def build_ass_force_style(is_expression: bool = False) -> str:
    try:
        cfg = settings.get_expression_subtitle_styling()
    except Exception:
        cfg = {
            "default": {"color": "#FFFFFF", "font_size": 28, "font_weight": "normal", "background_color": "#000000"},
            "expression_highlight": {"color": "#FFD700", "font_size": 32, "font_weight": "bold", "background_color": "#1A1A1A"},
        }
    style_cfg = cfg.get("expression_highlight" if is_expression else "default", {})
    color = _hex_to_ass_bgr(style_cfg.get("color", "#FFFFFF"))
    outline = _hex_to_ass_bgr(style_cfg.get("background_color", "#000000"))
    font_size = int(style_cfg.get("font_size", 24))
    bold = 1 if style_cfg.get("font_weight", "normal") == "bold" else 0
    outline_w = max(2, font_size // 12)
    
    # Increase vertical margin to avoid cropping at bottom (TICKET-090)
    # Lower value = closer to bottom edge
    margin_v = style_cfg.get("margin_v", 20)  # Reduced to 20 for lower position
    
    parts = [
        f"FontSize={font_size}",
        f"PrimaryColour={color}",
        f"OutlineColour={outline}",
        f"Outline={outline_w}",
        f"Bold={bold}",
        "BorderStyle=3",
        "Alignment=2",  # Bottom center alignment
        f"MarginV={margin_v}",
    ]
    return ",".join(parts)


def apply_subtitles_with_file(input_video: Path, subtitle_file: Path, output_path: Path, is_expression: bool = False) -> Path:
    # Wrap subtitles to ensure no overflow
    try:
        wrapped_path = subtitle_file.parent / f"wrapped_{subtitle_file.name}"
        # Use 25 chars for wrapping
        subtitle_file = wrap_subtitle_lines(Path(subtitle_file), wrapped_path, max_chars=25)
    except Exception as e:
        logger.warning(f"Failed to wrap subtitles for application: {e}")

    force_style = build_ass_force_style(is_expression=is_expression)
    
    # Get platform-specific fonts directory for FFmpeg
    from langflix.config.font_utils import get_fonts_dir
    fonts_dir = get_fonts_dir()
    
    (
        ffmpeg
        .input(str(input_video))
        .output(
            str(output_path),
            vf=f"subtitles={subtitle_file}:fontsdir={fonts_dir}:force_style='{force_style}'",
            # video encoder decided by caller; keep default here
            vcodec="libx264",
            preset="slow",  # Enforce slow preset
            crf=18,         # Enforce CRF 18
            acodec="aac",
            audio_bitrate="256k", # Enforce 256k audio
            ac=2,
            ar=48000,
        )
        .overwrite_output()
        .run(quiet=True)
    )
    return output_path


def apply_dual_subtitle_layers(
    video_path: str,
    original_subtitle_path: str,
    expression_subtitle_path: str,
    output_path: str,
    context_start_seconds: float,
    context_end_seconds: float,
    encoding_params: Optional[Dict[str, Any]] = None
) -> Path:
    """
    Extract context segment from source video, then apply original subtitles only.
    Cyan expression subtitle layer has been removed per user requirements.
    
    Args:
        video_path: Input video path (full source video, may be longer than context)
        original_subtitle_path: Path to original dual-language subtitle SRT
        expression_subtitle_path: Path to expression-only subtitle SRT (not used, kept for API compatibility)
        output_path: Output video path (context segment with subtitles)
        context_start_seconds: Context start time in source video (seconds)
        context_start_seconds: Context start time in source video (seconds)
        context_end_seconds: Context end time in source video (seconds)
        encoding_params: Optional dict with 'preset', 'crf' keys
        
    Returns:
        Path to output video with subtitles
    """
    # Wrap subtitles to ensure no overflow
    try:
        path_obj = Path(original_subtitle_path)
        wrapped_path = path_obj.parent / f"wrapped_{path_obj.name}"
        # Use 25 chars for wrapping
        original_subtitle_path = str(wrap_subtitle_lines(path_obj, wrapped_path, max_chars=25))
    except Exception as e:
        logger.warning(f"Failed to wrap subtitles for dual application: {e}")

    context_duration = context_end_seconds - context_start_seconds
    
    # Build force_style for original subtitle (bottom, white) - default behavior
    original_style = build_ass_force_style(is_expression=False)
    
    # CRITICAL: Use INPUT seeking for correct subtitle sync
    # When using relative subtitles (timestamps starting at 0), we must ensure
    # the video stream seen by the filter also starts at 0.
    # Input seeking (-ss before -i) resets timestamps to 0 at the seek point.
    video_input = ffmpeg.input(str(video_path), ss=context_start_seconds, t=context_duration)
    
    # Get platform-specific fonts directory for FFmpeg
    from langflix.config.font_utils import get_fonts_dir
    fonts_dir = get_fonts_dir()
    
    # Apply subtitle layer
    # Since input seeking was used, video T=0 corresponds to context_start_seconds
    # The relative SRT (T=0) will sync perfectly.
    video_with_subtitles = video_input['v'].filter(
        'subtitles',
        original_subtitle_path,
        fontsdir=fonts_dir,
        force_style=original_style
    )
    
    # Output
    default_args = {
        'vcodec': 'libx264',
        'preset': 'slow',   # Enforce slow preset
        'crf': 18,          # Enforce CRF 18
        'acodec': 'aac',
        'audio_bitrate': '256k', # Enforce 256k audio
        'ac': 2,
        'ar': 48000,
        # Note: ss and t are handled in input
    }
    
    output_args = default_args.copy()
    if encoding_params:
         output_args.update(encoding_params)
    
    (
        ffmpeg
        .output(
            video_with_subtitles,
            video_input['a'],
            str(output_path),
            **output_args
        )
        .overwrite_output()
        .run(quiet=True)
    )
    
    logger.info(f"Extracted context segment ({context_duration:.2f}s) and applied subtitle layer using input seeking")
    return Path(output_path)


def drawtext_fallback_single_line(input_video: Path, text: str, output_path: Path, language_code: Optional[str] = None) -> Path:
    def _clean(text_: str) -> str:
        text_ = text_.replace("'", "").replace('"', "").replace("\n", " ")
        text_ = "".join(c for c in text_ if c.isprintable())
        return text_[:200] if text_ else "Translation"

    clean = _clean(text)
    
    # Get language-specific font for drawtext
    font_opt = ""
    try:
        from langflix.config.font_utils import get_font_file_for_language
        import os
        font_path = get_font_file_for_language(language_code)
        if font_path and os.path.exists(font_path):
            font_opt = f"fontfile={font_path}:"
            logger.debug(f"Using font for fallback subtitle (language {language_code}): {font_path}")
        else:
            logger.warning(f"Font not found for language {language_code}, using default")
    except Exception as e:
        logger.warning(f"Error getting font for fallback subtitle: {e}")
        # Fallback to old method
        try:
            font_file = settings.get_font_file(language_code)
            font_opt = f"fontfile={font_file}:" if font_file else ""
        except Exception:
            font_opt = ""

    # Color from settings (default)
    try:
        default_size = settings.get_font_size()
    except Exception:
        default_size = 24

    (
        ffmpeg
        .input(str(input_video))
        .output(
            str(output_path),
            vf=(
                f"drawtext=text='{clean}':fontsize={default_size}:fontcolor=white:" \
                f"{font_opt}x=(w-text_w)/2:y=h-70"
            ),
            vcodec="libx264",
            preset="slow",  # Enforce slow preset
            crf=18,         # Enforce CRF 18
            acodec="aac",
            audio_bitrate="256k", # Enforce 256k audio
            ac=2,
            ar=48000,
        )
        .overwrite_output()
        .run(quiet=True)
    )
    return output_path


