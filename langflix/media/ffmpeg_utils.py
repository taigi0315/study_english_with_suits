"""
FFmpeg utilities for LangFlix

Goals
- Keep original video format (codec, resolution, pixel format) whenever possible
- Force audio to stereo 48k consistently to avoid concat/drop issues
- Provide explicit stream mapping helpers to prevent audio loss
- Offer safe probing, parameter extraction, concat/stack helpers

This module centralizes FFmpeg-related logic to make pipelines predictable
and maintainable across the codebase.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import ffmpeg

from langflix import settings

logger = logging.getLogger(__name__)


# --------------------------- FFprobe Cache ---------------------------

def _get_ffprobe_cache_key(path: str) -> Tuple[str, float, int]:
    """
    Generate cache key for ffprobe results based on file path, mtime, and size.
    
    This ensures cache invalidation when file is modified or replaced.
    
    Args:
        path: Path to media file
        
    Returns:
        Tuple of (resolved_path, mtime, size) for use as cache key
        
    Raises:
        OSError: If file does not exist or cannot be accessed
    """
    p = Path(path)
    stat = p.stat()
    return (str(p.resolve()), stat.st_mtime, stat.st_size)


@lru_cache(maxsize=512)
def _cached_ffprobe_result(cache_key: Tuple[str, float, int], timeout: int) -> Dict[str, Any]:
    """
    Cached ffprobe execution with LRU eviction.
    
    This is the actual cached function. Cache key includes file metadata
    (mtime, size) to ensure automatic invalidation on file changes.
    
    Args:
        cache_key: Tuple of (path, mtime, size) from _get_ffprobe_cache_key
        timeout: Timeout in seconds for ffprobe execution
        
    Returns:
        Parsed ffprobe JSON output as dictionary
        
    Raises:
        TimeoutError: If ffprobe times out
        FileNotFoundError: If ffprobe is not found
        subprocess.CalledProcessError: If ffprobe command fails
        json.JSONDecodeError: If output cannot be parsed as JSON
    """
    path = cache_key[0]  # Extract actual path from cache key
    logger.debug(f"🔍 FFprobe cache MISS for {Path(path).name} (mtime={cache_key[1]}, size={cache_key[2]})")
    
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_format",
            "-show_streams",
            "-of", "json",
            path,
        ]
        completed = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True,
            timeout=timeout
        )
        result = json.loads(completed.stdout or "{}")
        logger.debug(f"✅ FFprobe completed for {Path(path).name}")
        return result
    except subprocess.TimeoutExpired as e:
        logger.error(f"FFprobe timeout for {path} after {timeout}s")
        raise TimeoutError(f"FFprobe timeout for {path} after {timeout}s") from e
    except subprocess.CalledProcessError as e:
        stderr = e.stderr if isinstance(e.stderr, str) else (e.stderr.decode('utf-8', errors='replace') if e.stderr else "No stderr")
        logger.error(f"FFprobe failed for {path}: returncode={e.returncode}, stderr={stderr}")
        # Try ffmpeg-python probe as a fallback
        try:
            return ffmpeg.probe(path)  # type: ignore[no-any-return]
        except Exception as ee:
            logger.error(f"ffmpeg.probe fallback also failed for {path}: {ee}")
            raise
    except FileNotFoundError:
        logger.error("FFprobe not found. Please install ffmpeg.")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse FFprobe JSON output for {path}: {e}")
        raise


def clear_ffprobe_cache() -> None:
    """
    Clear all cached ffprobe results.
    
    Useful for testing or when you know files have been modified
    outside of the normal detection mechanism.
    """
    _cached_ffprobe_result.cache_clear()
    logger.info("🗑️ FFprobe cache cleared")


def get_ffprobe_cache_info() -> Dict[str, int]:
    """
    Get cache statistics for monitoring and debugging.
    
    Returns:
        Dictionary with 'hits', 'misses', 'size', and 'maxsize'
    """
    info = _cached_ffprobe_result.cache_info()
    return {
        'hits': info.hits,
        'misses': info.misses,
        'size': info.currsize,
        'maxsize': info.maxsize
    }



# --------------------------- Data models ---------------------------

@dataclass
class VideoParams:
    codec: Optional[str]
    width: Optional[int]
    height: Optional[int]
    pix_fmt: Optional[str]
    r_frame_rate: Optional[str]


@dataclass
class AudioParams:
    codec: Optional[str]
    channels: Optional[int]
    sample_rate: Optional[int]


# --------------------------- Probe helpers ---------------------------

def run_ffprobe(path: str, timeout: Optional[int] = None, use_cache: bool = True) -> Dict[str, Any]:
    """Run ffprobe and return parsed JSON, raising on failure.

    Results are cached by default using file path, mtime, and size as cache key.
    Cache automatically invalidates when file is modified.
    
    Args:
        path: Path to video file
        timeout: Timeout in seconds (if None, use configuration value)
        use_cache: Whether to use cache (default: True). Set to False for real-time uploads.
        
    Returns:
        Parsed ffprobe JSON output as dictionary
        
    Raises:
        TimeoutError: If ffprobe times out
        FileNotFoundError: If ffprobe is not found
        subprocess.CalledProcessError: If ffprobe command fails
        json.JSONDecodeError: If output cannot be parsed as JSON
        OSError: If file cannot be accessed for cache key generation
    """
    effective_timeout = timeout if timeout is not None else settings.get_ffprobe_timeout_seconds()
    
    if not use_cache:
        # Bypass cache for special cases (e.g., real-time uploads)
        logger.debug(f"⏭️ FFprobe cache bypassed for {Path(path).name}")
        return _run_ffprobe_uncached(path, effective_timeout)
    
    try:
        # Generate cache key based on file metadata
        cache_key = _get_ffprobe_cache_key(path)
        
        # Check if we have cached result
        cache_info_before = _cached_ffprobe_result.cache_info()
        result = _cached_ffprobe_result(cache_key, effective_timeout)
        cache_info_after = _cached_ffprobe_result.cache_info()
        
        # Log cache hit
        if cache_info_after.hits > cache_info_before.hits:
            logger.debug(f"✨ FFprobe cache HIT for {Path(path).name} (hit rate: {cache_info_after.hits}/{cache_info_after.hits + cache_info_after.misses})")
        
        return result
    except OSError as e:
        # File stat failed, fallback to uncached probe
        logger.warning(f"Failed to stat file for cache key: {e}, falling back to uncached probe")
        return _run_ffprobe_uncached(path, effective_timeout)


def _run_ffprobe_uncached(path: str, timeout: int) -> Dict[str, Any]:
    """
    Run ffprobe without caching (internal helper).
    
    This is used when cache is explicitly bypassed or when file stat fails.
    
    Args:
        path: Path to video file
        timeout: Timeout in seconds
        
    Returns:
        Parsed ffprobe JSON output as dictionary
        
    Raises:
        TimeoutError: If ffprobe times out
        FileNotFoundError: If ffprobe is not found
        subprocess.CalledProcessError: If ffprobe command fails
        json.JSONDecodeError: If output cannot be parsed as JSON
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_format",
            "-show_streams",
            "-of", "json",
            path,
        ]
        completed = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True,
            timeout=timeout
        )
        return json.loads(completed.stdout or "{}")
    except subprocess.TimeoutExpired as e:
        logger.error(f"FFprobe timeout for {path} after {timeout}s")
        raise TimeoutError(f"FFprobe timeout for {path} after {timeout}s") from e
    except subprocess.CalledProcessError as e:
        stderr = e.stderr if isinstance(e.stderr, str) else (e.stderr.decode('utf-8', errors='replace') if e.stderr else "No stderr")
        logger.error(f"FFprobe failed for {path}: returncode={e.returncode}, stderr={stderr}")
        # Try ffmpeg-python probe as a fallback
        try:
            return ffmpeg.probe(path)  # type: ignore[no-any-return]
        except Exception as ee:
            logger.error(f"ffmpeg.probe fallback also failed for {path}: {ee}")
            raise
    except FileNotFoundError:
        logger.error("FFprobe not found. Please install ffmpeg.")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse FFprobe JSON output for {path}: {e}")
        raise
    except Exception as e:
        logger.error(f"FFprobe error for {path}: {e}")
        raise


def get_streams(probe: Dict[str, Any], stream_type: str) -> list[Dict[str, Any]]:
    return [s for s in probe.get("streams", []) if s.get("codec_type") == stream_type]


def get_video_params(path: str) -> VideoParams:
    probe = run_ffprobe(path)
    v_streams = get_streams(probe, "video")
    if not v_streams:
        return VideoParams(None, None, None, None, None)
    v = v_streams[0]
    return VideoParams(
        codec=v.get("codec_name"),
        width=int(v.get("width")) if v.get("width") else None,
        height=int(v.get("height")) if v.get("height") else None,
        pix_fmt=v.get("pix_fmt"),
        r_frame_rate=v.get("r_frame_rate"),
    )


def get_audio_params(path: str) -> AudioParams:
    probe = run_ffprobe(path)
    a_streams = get_streams(probe, "audio")
    if not a_streams:
        return AudioParams(None, None, None)
    a = a_streams[0]
    sr = a.get("sample_rate")
    return AudioParams(
        codec=a.get("codec_name"),
        channels=int(a.get("channels")) if a.get("channels") else None,
        sample_rate=int(sr) if isinstance(sr, str) and sr.isdigit() else (int(sr) if isinstance(sr, int) else None),
        duration=float(a.get("duration")) if a.get("duration") else None,
    )


def detect_black_bars(video_path: str, duration: float = 2.0) -> Optional[str]:
    """
    Detect black bars in video using cropdetect filter.
    Returns crop parameters string (w:h:x:y) or None if detection fails or is invalid.
    
    Args:
        video_path: Path to video file
        duration: Duration to analyze (seconds)
        
    Returns:
        String crop parameters "w:h:x:y" for ffmpeg crop filter, or None
    """
    try:
        # Run ffmpeg with cropdetect filter for a few frames
        # We process a small segment from the middle to avoid intro/outro black frames
        probe = run_ffprobe(video_path)
        format_info = probe.get('format', {})
        total_duration = float(format_info.get('duration', 0))
        
        start_time = total_duration / 2 if total_duration > 0 else 0
        
        cmd = [
            'ffmpeg',
            '-ss', str(start_time),
            '-i', str(video_path),
            '-t', str(duration),
            '-vf', 'cropdetect=24:16:0',
            '-f', 'null',
            '-'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        output = result.stderr
        
        # Parse last cropdetect output
        # Output format: ... crop=1920:800:0:140 ...
        import re
        from collections import Counter
        matches = re.findall(r'crop=(\d+:\d+:\d+:\d+)', output)
        
        if matches:
            # Use the most frequent crop value to avoid noise
            most_common = Counter(matches).most_common(1)
            if most_common:
                return most_common[0][0]
                
        return None
        
    except Exception as e:
        logger.warning(f"Failed to detect black bars for {video_path}: {e}")
        return None


def log_media_params(path: str, label: str = "media") -> None:
    try:
        vp = get_video_params(path)
        ap = get_audio_params(path)
        logger.info(
            f"[{label}] video: codec={vp.codec} {vp.width}x{vp.height} pix_fmt={vp.pix_fmt}, "
            f"audio: codec={ap.codec} ch={ap.channels} sr={ap.sample_rate}"
        )
    except Exception as e:
        logger.warning(f"Could not log media params for {path}: {e}")


# --------------------------- Encoding decisions ---------------------------

def should_copy_video(input_path: str) -> bool:
    """Decide whether we can `-c:v copy` safely.

    We copy video when we are not applying any video filters AND we are concatenating
    with segments of identical parameters. This function itself only checks feasibility
    on a single file; callers must ensure pipeline operations allow copy.
    """
    vp = get_video_params(input_path)
    return vp.codec is not None and vp.width is not None and vp.height is not None


def make_video_encode_args_from_source(source_path: str, include_preset_crf: bool = True) -> Dict[str, Any]:
    """Create encoder arguments that match the source video as closely as possible.

    If source codec is usable with filters, we reuse it; otherwise fallback to libx264
    while preserving width/height. We do NOT force yuv420p unless necessary.
    
    Args:
        source_path: Path to source video file
        include_preset_crf: If True, include preset and crf from settings (default: True)
    """
    vp = get_video_params(source_path)
    args: Dict[str, Any] = {}

    # Preferred: keep original codec when possible. Some codecs may not be encodable
    # in our environment; in such case, fall back to libx264 gracefully.
    preferred_codec = vp.codec or "libx264"
    if preferred_codec in {"h264", "libx264", "hevc", "libx265", "vp9", "prores"}:
        # Map decoder name to encoder name when needed
        encoder = {
            "h264": "libx264",
            "hevc": "libx265",
            "vp9": "libvpx-vp9",
        }.get(preferred_codec, preferred_codec)
    else:
        encoder = "libx264"

    args["vcodec"] = encoder
    
    # Add preset and CRF from settings for optimal encoding quality
    # Updated defaults: preset "medium" and CRF 18 for better quality (TICKET-072)
    if include_preset_crf:
        try:
            from langflix import settings
            video_config = settings.get_video_config()
            # High quality defaults: CRF 16/slow
            args["preset"] = video_config.get("preset", "slow")
            args["crf"] = video_config.get("crf", 16)
        except Exception:
            # Fallback if settings not available - use quality-focused defaults
            args["preset"] = "slow"
            args["crf"] = 18
        
        # Log encoding parameters for debugging and quality monitoring (TICKET-055)
        logger.info(
            f"Encoding video with preset={args.get('preset', 'N/A')}, "
            f"crf={args.get('crf', 'N/A')}, codec={args.get('vcodec', 'N/A')}"
        )

    # Preserve resolution by not adding explicit scale; when filters require scale,
    # the caller should provide it based on source params.
    # We avoid forcing pix_fmt; only set if needed by downstream demuxers.
    return args


def make_audio_encode_args(normalize: bool = False, quality: str = "high") -> Dict[str, Any]:
    """Get audio encoding arguments.
    
    Args:
        normalize: If True, normalize to stereo 48k. If False, use copy.
        quality: Audio quality level - "high" (256kbps), "medium" (192kbps), or "low" (128kbps)
    
    Returns:
        Dict with audio codec args
    """
    if normalize:
        # Use high-quality AAC encoding to preserve original audio quality
        # High bitrate (256kbps) ensures minimal quality loss during re-encoding
        bitrate_map = {
            "high": "256k",
            "medium": "192k",
            "low": "128k"
        }
        bitrate = bitrate_map.get(quality, "256k")
        return {
            "acodec": "aac",
            "ac": 2,  # Stereo
            "ar": 48000,  # 48kHz sample rate (video standard)
            "b:a": bitrate  # High bitrate for quality preservation
        }
    return {"acodec": "copy"}


def make_audio_encode_args_copy() -> Dict[str, Any]:
    """Prefer copying audio without re-encoding (no format changes)."""
    return make_audio_encode_args(normalize=False)


# --------------------------- Probe misc ---------------------------

def get_duration_seconds(path: str) -> float:
    try:
        probe = run_ffprobe(path)
        dur = probe.get("format", {}).get("duration")
        if dur is None:
            return 0.0
        return float(dur)
    except Exception:
        return 0.0


# --------------------------- Standardization helpers ---------------------------

def standardize_for_concat(input_path: str, target_video: Optional[VideoParams] = None) -> Tuple[Dict[str, Any], str]:
    """Return (output_args, filter_v) for a segment so that multiple segments can be concatenated.

    - Normalizes audio to stereo/48k
    - Keeps video resolution; does not force pixel format unless explicitly needed
    - If target_video is provided, ensures width/height match via scale
    """
    vp = get_video_params(input_path)
    vfilter = None

    if target_video and target_video.width and target_video.height:
        if (vp.width != target_video.width) or (vp.height != target_video.height):
            vfilter = f"scale={target_video.width}:{target_video.height}"

    out_args = {}
    out_args.update(make_video_encode_args_from_source(input_path))
    out_args.update(make_audio_encode_args(True))
    return out_args, (vfilter or "")


# --------------------------- Output helpers ---------------------------

def output_with_explicit_streams(v_in, a_in, out_path: Path | str, **encode_args: Any) -> None:
    """Write an output mapping video and audio streams explicitly to avoid drops."""
    (
        ffmpeg
        .output(v_in, a_in, str(out_path), **encode_args)
        .overwrite_output()
        .run(quiet=True)
    )


# --------------------------- Concat helpers ---------------------------

def concat_filter_multiple(segment_paths: List[str], out_path: Path | str) -> None:
    """Concatenate multiple segments at once using filter concat (much faster than sequential).
    
    This is optimized for speed - concatenates all segments in a single pass instead of
    sequentially, which avoids multiple re-encodings.
    
    Args:
        segment_paths: List of paths to video segments to concatenate
        out_path: Output path for concatenated video
    """
    if len(segment_paths) == 0:
        raise ValueError("No segments provided for concatenation")
    if len(segment_paths) == 1:
        import shutil
        shutil.copy2(segment_paths[0], out_path)
        ensure_dir(Path(out_path))
        return
    
    logger.info(f"Concatenating {len(segment_paths)} segments in single pass (filter concat)")
    
    # Get frame rate from first segment for normalization
    first_vp = get_video_params(segment_paths[0])
    target_fps = 25.0
    if first_vp.r_frame_rate:
        try:
            if '/' in first_vp.r_frame_rate:
                num, den = map(float, first_vp.r_frame_rate.split('/'))
                target_fps = num / den if den > 0 else 25.0
            else:
                target_fps = float(first_vp.r_frame_rate)
        except (ValueError, ZeroDivisionError):
            target_fps = 25.0
    
    # Create inputs and normalize all segments
    inputs = []
    video_streams = []
    audio_streams = []
    
    for i, segment_path in enumerate(segment_paths):
        segment_in = ffmpeg.input(segment_path)
        # Normalize frame rate and reset timestamps
        v = ffmpeg.filter(segment_in["v"], 'fps', fps=target_fps)
        v = ffmpeg.filter(v, 'setpts', 'PTS-STARTPTS')
        a = ffmpeg.filter(segment_in["a"], 'asetpts', 'PTS-STARTPTS')
        video_streams.append(v)
        audio_streams.append(a)
    
    # Concatenate all segments at once (much faster than sequential)
    # n=len(segment_paths) means we have n segments to concatenate
    all_streams = []
    for v, a in zip(video_streams, audio_streams):
        all_streams.extend([v, a])
    
    concat_node = ffmpeg.concat(*all_streams, v=1, a=1, n=len(segment_paths)).node
    
    try:
        output_with_explicit_streams(
            concat_node[0],
            concat_node[1],
            out_path,
            **make_video_encode_args_from_source(segment_paths[0]),
            **make_audio_encode_args(normalize=True),
        )
        logger.info(f"✅ Successfully concatenated {len(segment_paths)} segments")
    except ffmpeg.Error as e:
        stderr = e.stderr.decode('utf-8') if e.stderr else str(e)
        logger.error(
            f"❌ concat_filter_multiple FAILED: Cannot concatenate {len(segment_paths)} segments\n"
            f"   Output: {out_path}\n"
            f"   Error: {stderr[:1000]}\n"
        )
        raise RuntimeError(f"concat_filter_multiple failed: {stderr[:500]}") from e


def concat_filter_with_explicit_map(
    left_path: str,
    right_path: str,
    out_path: Path | str,
) -> None:
    """Concat two segments with filter concat ensuring v=1,a=1 and explicit mapping.

    This is safer when input parameters differ.
    Normalizes frame rate to ensure A-V sync and prevent freezing.
    Falls back to demuxer concat if filter concat fails.
    """
    left_in = ffmpeg.input(left_path)
    right_in = ffmpeg.input(right_path)
    left_dur = get_duration_seconds(left_path)
    right_dur = get_duration_seconds(right_path)

    # Get frame rates to ensure consistency and prevent A-V sync issues
    left_vp = get_video_params(left_path)
    
    # Normalize frame rate to a common value to prevent freezing and A-V sync issues
    target_fps = 25.0  # Default frame rate for smooth playback
    if left_vp.r_frame_rate:
        try:
            # Parse frame rate (e.g., "25/1" or "30/1")
            if '/' in left_vp.r_frame_rate:
                num, den = map(float, left_vp.r_frame_rate.split('/'))
                target_fps = num / den if den > 0 else 25.0
            else:
                target_fps = float(left_vp.r_frame_rate)
        except (ValueError, ZeroDivisionError):
            target_fps = 25.0
    
    # Scale to target resolution (1280x720) to prevent resolution mismatch
    # force_original_aspect_ratio='decrease' ensures we fit within the box
    # pad ensures we fill the box exactly
    left_v = ffmpeg.filter(left_in["v"], 'scale', 1280, 720, force_original_aspect_ratio='decrease')
    left_v = ffmpeg.filter(left_v, 'pad', 1280, 720, '(ow-iw)/2', '(oh-ih)/2')
    left_v = ffmpeg.filter(left_v, 'setsar', r='1')
    
    right_v = ffmpeg.filter(right_in["v"], 'scale', 1280, 720, force_original_aspect_ratio='decrease')
    right_v = ffmpeg.filter(right_v, 'pad', 1280, 720, '(ow-iw)/2', '(oh-ih)/2')
    right_v = ffmpeg.filter(right_v, 'setsar', r='1')

    # Apply fps filter to both videos to ensure consistent frame rate and prevent A-V sync issues
    # Reset timestamps after fps filter to prevent 0.5s delay and A-V sync issues
    # setpts=PTS-STARTPTS ensures timestamps start from 0 for proper concat
    left_v = ffmpeg.filter(left_v, 'fps', fps=target_fps)
    left_v = ffmpeg.filter(left_v, 'setpts', 'PTS-STARTPTS')
    right_v = ffmpeg.filter(right_v, 'fps', fps=target_fps)
    right_v = ffmpeg.filter(right_v, 'setpts', 'PTS-STARTPTS')
    
    # Reset audio timestamps as well to ensure A-V sync
    # asetpts=PTS-STARTPTS ensures audio timestamps start from 0
    left_a = ffmpeg.filter(left_in["a"], 'asetpts', 'PTS-STARTPTS')
    right_a = ffmpeg.filter(right_in["a"], 'asetpts', 'PTS-STARTPTS')

    # Use .node to obtain stream tuple indices safely
    concat_node = ffmpeg.concat(left_v, left_a, right_v, right_a, v=1, a=1, n=2).node
    
    try:
        # Must re-encode audio when using filters (setpts, asetpts) - cannot use streamcopy
        # Filtering and streamcopy cannot be used together
        output_with_explicit_streams(
            concat_node[0],
            concat_node[1],
            out_path,
            **make_video_encode_args_from_source(left_path),
            **make_audio_encode_args(normalize=True),  # Re-encode audio (filtered streams cannot use copy)
        )
    except ffmpeg.Error as e:
        # Read stderr for detailed error information
        stderr = e.stderr.decode('utf-8') if e.stderr else str(e)
        logger.error(
            f"❌ concat_filter_with_explicit_map FAILED: Cannot concatenate videos\n"
            f"   Left: {left_path}\n"
            f"   Right: {right_path}\n"
            f"   Output: {out_path}\n"
            f"   Error: {stderr}\n"
            f"   This usually means:\n"
            f"   1. Video codecs/resolutions are incompatible\n"
            f"   2. One or both videos have no audio stream\n"
            f"   3. Frame rate mismatch causing filter issues\n"
            f"   4. File corruption or incomplete files\n"
            f"   Fix: Check files with 'ffprobe {left_path}' and 'ffprobe {right_path}'"
        )
        raise RuntimeError(f"concat_filter_with_explicit_map failed: {stderr}") from e


def concat_demuxer_if_uniform(list_file: Path | str, out_path: Path | str, normalize_audio: bool = True) -> None:
    """Use concat demuxer when all inputs are uniform; caller must ensure uniformity.
    
    Note: This is a simplified version that reads from a concat list file.
    For in-memory concat, use repeat_av_demuxer pattern.
    
    Args:
        list_file: Path to concat list file
        out_path: Output path for concatenated video
        normalize_audio: If True, normalize audio to stereo 48k with high quality encoding.
                         This prevents audio breaking issues when concatenating videos with
                         different audio parameters. Default: True for quality preservation.
    """
    # First, probe one of the input files to get encoding params
    # This ensures we use appropriate encoding settings, not just copy mode
    first_file = None
    try:
        with open(list_file) as f:
            first_line = f.readline().strip()
            if first_line.startswith("file "):
                first_file = first_line[6:-1]  # Remove 'file ' prefix and quotes
    except Exception as e:
        logger.warning(f"Could not read concat file to determine encoding: {e}")
    
    if first_file and Path(first_file).exists():
        # Use encoding args from source (includes preset/crf from config)
        # Normalize audio to prevent breaking issues when concatenating videos
        # with different audio parameters (sample rate, channels, codec)
        if normalize_audio:
            audio_args = make_audio_encode_args(normalize=True, quality="high")
            logger.info(f"Normalizing audio during concatenation (stereo 48kHz, 256kbps) to prevent audio breaking")
        else:
            audio_args = make_audio_encode_args_copy()
        encode_args = {**make_video_encode_args_from_source(str(first_file)), **audio_args}
    else:
        # Fallback: use copy for video, normalize audio if requested
        if normalize_audio:
            encode_args = {"vcodec": "copy", **make_audio_encode_args(normalize=True, quality="high")}
            logger.info(f"Normalizing audio during concatenation (stereo 48kHz, 256kbps) to prevent audio breaking")
        else:
            encode_args = {"vcodec": "copy", "acodec": "copy"}
    
    (
        ffmpeg
        .input(str(list_file), format="concat", safe=0)
        .output(str(out_path), **encode_args)
        .overwrite_output()
        .run(quiet=True)
    )
    ensure_dir(Path(out_path))


# --------------------------- Stack helpers ---------------------------

def vstack_keep_width(top_path: str, bottom_path: str, out_path: Path | str) -> None:
    """Stack two videos vertically keeping source widths; make height sum.

    We scale secondaries to the first's width; heights scale proportionally.
    """
    top_vp = get_video_params(top_path)
    top_in = ffmpeg.input(top_path)
    bot_in = ffmpeg.input(bottom_path)

    # Scale bottom to match top width, preserve aspect ratio
    bot_scaled = ffmpeg.filter(bot_in["v"], "scale", top_vp.width or -1, -2)
    top_v = top_in["v"]
    stacked_v = ffmpeg.filter([top_v, bot_scaled], "vstack", inputs=2)

    # Prefer audio from top input as-is
    top_a = top_in["a"]
    output_with_explicit_streams(
        stacked_v,
        top_a,
        out_path,
        **make_video_encode_args_from_source(top_path),
        **make_audio_encode_args_copy(),
    )


def center_video_with_letterbox(
    input_path: str,
    target_width: int,
    target_height: int,
    out_path: Path | str
) -> None:
    """
    Center video in target frame with letterboxing (black bars top/bottom).
    
    Maintains original video aspect ratio by adding black bars.
    For short-form: target is 1080x1920 (9:16), video is centered vertically.
    
    Args:
        input_path: Input video path
        target_width: Target frame width (e.g., 1080)
        target_height: Target frame height (e.g., 1920)
        out_path: Output video path
    """
    input_vp = get_video_params(input_path)
    input_ap = get_audio_params(input_path)
    video_in = ffmpeg.input(input_path)
    
    video_width = input_vp.width or target_width
    video_height = input_vp.height or target_height
    
    # Calculate aspect ratio
    aspect_ratio = video_width / video_height if video_height > 0 else 16 / 9
    
    # Calculate scaled dimensions to fit within target while maintaining aspect ratio
    # Scale to fit width first, then check if height fits
    scaled_width = target_width
    scaled_height = int(target_width / aspect_ratio)
    
    # If scaled height exceeds target, scale to fit height instead
    if scaled_height > target_height:
        scaled_height = target_height
        scaled_width = int(target_height * aspect_ratio)
    
    # Center calculation
    x_offset = (target_width - scaled_width) // 2
    y_offset = (target_height - scaled_height) // 2
    
    logger.info(
        f"Centering video: {video_width}x{video_height} -> {scaled_width}x{scaled_height} "
        f"in {target_width}x{target_height} frame (offset: {x_offset}, {y_offset})"
    )
    
    # FFmpeg filter chain: scale -> pad
    video_stream = ffmpeg.filter(video_in['v'], 'scale', scaled_width, scaled_height)
    video_stream = ffmpeg.filter(
        video_stream,
        'pad',
        target_width,
        target_height,
        x_offset,
        y_offset,
        color='black'
    )
    
    # Reset timestamps for proper concatenation
    video_stream = ffmpeg.filter(video_stream, 'setpts', 'PTS-STARTPTS')
    
    # Use audio from input if available
    audio_stream = None
    if input_ap.codec:
        try:
            audio_stream = ffmpeg.filter(video_in['a'], 'asetpts', 'PTS-STARTPTS')
        except (KeyError, AttributeError):
            logger.debug(f"No audio stream in {input_path}")
            audio_stream = None
    
    # Output with explicit stream mapping
    if audio_stream:
        output_with_explicit_streams(
            video_stream,
            audio_stream,
            out_path,
            **make_video_encode_args_from_source(input_path),
            **make_audio_encode_args(normalize=True),  # Re-encode audio (filtered streams cannot use copy)
        )
    else:
        # No audio - output video only
        (
            ffmpeg
            .output(video_stream, str(out_path),
                   **make_video_encode_args_from_source(input_path))
            .overwrite_output()
            .run(quiet=True)
        )
        ensure_dir(Path(out_path))


def hstack_keep_height(left_path: str, right_path: str, out_path: Path | str) -> None:
    """Stack two videos horizontally keeping source heights; widths scale proportionally.
    
    Resets timestamps to prevent delay at video start.
    Right video may not have audio (e.g., silent slides), so only use left audio.
    """
    left_vp = get_video_params(left_path)
    left_in = ffmpeg.input(left_path)
    right_in = ffmpeg.input(right_path)

    # Reset timestamps to prevent delay
    left_v = ffmpeg.filter(left_in["v"], "setpts", "PTS-STARTPTS")
    
    # Check if left has audio stream before processing
    # Use try/except to handle cases where audio stream doesn't exist
    has_audio = False
    left_a = None
    
    try:
        left_ap = get_audio_params(left_path)
        if left_ap.codec:
            # Try to access audio stream
            try:
                left_a = ffmpeg.filter(left_in["a"], "asetpts", "PTS-STARTPTS")
                has_audio = True
            except (KeyError, AttributeError, Exception) as e:
                logger.warning(f"Left video has audio codec but stream access failed: {e}, proceeding without audio")
                has_audio = False
                left_a = None
    except Exception as e:
        logger.debug(f"Left video has no audio stream: {e}")
        has_audio = False
        left_a = None
    
    # Scale right to match left height, preserve aspect ratio
    right_scaled = ffmpeg.filter(right_in["v"], "scale", -2, left_vp.height or -1)
    # Reset right video timestamps as well
    right_scaled = ffmpeg.filter(right_scaled, "setpts", "PTS-STARTPTS")
    
    stacked_v = ffmpeg.filter([left_v, right_scaled], "hstack", inputs=2)

    # Use left audio if available (right video may be silent slide)
    # Must re-encode audio when using filters (asetpts) - cannot use streamcopy
    if has_audio and left_a is not None:
        output_with_explicit_streams(
            stacked_v,
            left_a,
            out_path,
            **make_video_encode_args_from_source(left_path),
            **make_audio_encode_args(normalize=True),  # Re-encode audio (filtered streams cannot use copy)
        )
    else:
        # No audio - output video only
        (
            ffmpeg
            .output(stacked_v, str(out_path),
                   **make_video_encode_args_from_source(left_path))
            .overwrite_output()
            .run(quiet=True)
        )
        ensure_dir(Path(out_path))


# --------------------------- Misc helpers ---------------------------

def ensure_dir(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


# --------------------------- Repeat AV helpers ---------------------------

def build_repeated_av(input_path: str, repeat_count: int, out_path: Path | str) -> None:
    """Repeat an AV segment N times preserving audio via filter concat with explicit mapping.

    DEPRECATED: Use repeat_av_demuxer for better reliability.
    Kept for backward compatibility.

    - Normalizes audio to stereo/48k and applies +25% volume
    - Normalizes video pixel format to yuv420p for compatibility
    """
    repeat_count = max(1, int(repeat_count))
    inputs = [ffmpeg.input(input_path) for _ in range(repeat_count)]

    concat_args = []
    for s in inputs:
        v_in = s["v"]
        a_in = s["a"]
        concat_args.append(v_in)
        concat_args.append(a_in)

    node = ffmpeg.concat(*concat_args, v=1, a=1, n=repeat_count).node
    output_with_explicit_streams(
        node[0],
        node[1],
        out_path,
        **make_video_encode_args_from_source(input_path),
        **make_audio_encode_args_copy(),
    )


def repeat_av_demuxer(input_path: str, repeat_count: int, out_path: Path | str) -> None:
    """Repeat an AV segment N times using concat demuxer for maximum reliability.
    
    This method uses FFmpeg's concat demuxer which is simpler and more reliable
    than filter-based concatenation. It preserves audio without any transformations
    until explicitly needed.
    
    Args:
        input_path: Path to input AV file
        repeat_count: Number of times to repeat the segment
        out_path: Path to output file
    
    Returns:
        None (writes to out_path)
    """
    repeat_count = max(1, int(repeat_count))
    
    # If only one repeat, just copy the file
    if repeat_count == 1:
        import shutil
        shutil.copy2(input_path, out_path)
        ensure_dir(Path(out_path))
        return
    
    # Create temporary concat list file
    import tempfile
    concat_list = []
    for _ in range(repeat_count):
        concat_list.append(f"file '{Path(input_path).absolute()}'")
    
    # Write concat file
    concat_content = '\n'.join(concat_list)
    
    # Use concat demuxer - try file-based method first (more reliable than pipe)
    # Write concat file to disk for better error messages
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(concat_content)
        concat_file = f.name
    
    try:
        (
            ffmpeg
            .input(concat_file, format='concat', safe=0)
            .output(
                str(out_path),
                **make_video_encode_args_from_source(input_path),
                **make_audio_encode_args_copy()
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        # Read stderr for detailed error information
        stderr = e.stderr.decode('utf-8') if e.stderr else str(e)
        logger.error(
            f"❌ repeat_av_demuxer FAILED: Cannot repeat video segment\n"
            f"   Input: {input_path}\n"
            f"   Repeat count: {repeat_count}\n"
            f"   Output: {out_path}\n"
            f"   Error: {stderr}\n"
            f"   This usually means:\n"
            f"   1. Input file has no audio stream (concat demuxer requires audio)\n"
            f"   2. Input file is corrupted or incomplete\n"
            f"   3. File permissions issue\n"
            f"   Fix: Check input file with 'ffprobe {input_path}'"
        )
        # Clean up temp file before raising
        if os.path.exists(concat_file):
            os.unlink(concat_file)
        raise RuntimeError(f"repeat_av_demuxer failed: {stderr}") from e
    finally:
        if os.path.exists(concat_file):
            os.unlink(concat_file)
    ensure_dir(Path(out_path))


# --------------------------- Final audio gain helpers ---------------------------

def apply_final_audio_gain(input_path: str, out_path: Path | str, gain_factor: float = 1.25) -> None:
    """Apply audio gain as a separate final pass (simple map, no filter_complex).
    
    This function applies volume boost to audio stream while preserving video stream
    as-is. Used as the final step in the pipeline to boost audio without modifying
    the video stream or using complex filter graphs.
    
    Args:
        input_path: Path to input video file
        out_path: Path to output video file
        gain_factor: Audio gain multiplier (default 1.25 = +25%)
    
    Returns:
        None (writes to out_path)
    """
    input_stream = ffmpeg.input(str(input_path))
    
    # Get video and audio streams
    video_stream = input_stream['v']
    audio_stream = input_stream['a']
    
    # Apply volume filter to audio only
    boosted_audio = audio_stream.filter('volume', str(gain_factor))
    
    # Output with explicit stream mapping
    # Video: copy if possible, Audio: boosted (requires encoding due to filter)
    if should_copy_video(str(input_path)):
        encode_args = {
            'vcodec': 'copy',
            'acodec': 'aac',
            'ac': 2,
            'ar': 48000,
            'b:a': '256k'
        }
    else:
        encode_args = {
            **make_video_encode_args_from_source(str(input_path)),
            'acodec': 'aac',
            'ac': 2,
            'ar': 48000,
            'b:a': '256k'
        }
    
    (
        ffmpeg
        .output(video_stream, boosted_audio, str(out_path), **encode_args)
        .overwrite_output()
        .run(quiet=True)
    )
    ensure_dir(Path(out_path))

