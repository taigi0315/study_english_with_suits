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
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import ffmpeg

logger = logging.getLogger(__name__)


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

def run_ffprobe(path: str) -> Dict[str, Any]:
    """Run ffprobe and return parsed JSON, raising on failure.

    We use subprocess here because ffmpeg-python's probe may hide stderr.
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
        completed = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(completed.stdout or "{}")
    except Exception as e:
        logger.error(f"ffprobe failed for {path}: {e}")
        # Try ffmpeg-python probe as a fallback
        try:
            return ffmpeg.probe(path)  # type: ignore[no-any-return]
        except Exception as ee:
            logger.error(f"ffmpeg.probe fallback also failed for {path}: {ee}")
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
    )


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


def make_video_encode_args_from_source(source_path: str) -> Dict[str, Any]:
    """Create encoder arguments that match the source video as closely as possible.

    If source codec is usable with filters, we reuse it; otherwise fallback to libx264
    while preserving width/height. We do NOT force yuv420p unless necessary.
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

    # Preserve resolution by not adding explicit scale; when filters require scale,
    # the caller should provide it based on source params.
    # We avoid forcing pix_fmt; only set if needed by downstream demuxers.
    return args


def make_audio_encode_args(normalize: bool = False) -> Dict[str, Any]:
    """Get audio encoding arguments.
    
    Args:
        normalize: If True, normalize to stereo 48k. If False, use copy.
    
    Returns:
        Dict with audio codec args
    """
    if normalize:
        return {"acodec": "aac", "ac": 2, "ar": 48000}
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

def concat_filter_with_explicit_map(
    left_path: str,
    right_path: str,
    out_path: Path | str,
) -> None:
    """Concat two segments with filter concat ensuring v=1,a=1 and explicit mapping.

    This is safer when input parameters differ.
    Falls back to demuxer concat if filter concat fails.
    """
    left_in = ffmpeg.input(left_path)
    right_in = ffmpeg.input(right_path)
    left_dur = get_duration_seconds(left_path)
    right_dur = get_duration_seconds(right_path)

    left_v = left_in["v"]
    right_v = right_in["v"]
    # Use original audio streams as-is (no reformatting, no volume change)
    left_a = left_in["a"]
    right_a = right_in["a"]

    # Use .node to obtain stream tuple indices safely
    concat_node = ffmpeg.concat(left_v, left_a, right_v, right_a, v=1, a=1, n=2).node
    
    try:
        output_with_explicit_streams(
            concat_node[0],
            concat_node[1],
            out_path,
            **make_video_encode_args_from_source(left_path),
            **make_audio_encode_args_copy(),
        )
    except ffmpeg.Error as e:
        logger.warning(f"Filter concat failed, falling back to demuxer concat: {e}")
        # Fallback to demuxer concat
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(f"file '{Path(left_path).absolute()}'\n")
            f.write(f"file '{Path(right_path).absolute()}'\n")
            concat_file = f.name
        
        try:
            concat_demuxer_if_uniform(concat_file, out_path)
        finally:
            import os
            if os.path.exists(concat_file):
                os.unlink(concat_file)
        ensure_dir(Path(out_path))


def concat_demuxer_if_uniform(list_file: Path | str, out_path: Path | str) -> None:
    """Use concat demuxer when all inputs are uniform; caller must ensure uniformity.
    
    Note: This is a simplified version that reads from a concat list file.
    For in-memory concat, use repeat_av_demuxer pattern.
    """
    # First, probe one of the input files to get encoding params
    import tempfile
    first_file = None
    try:
        with open(list_file) as f:
            first_line = f.readline().strip()
            if first_line.startswith("file "):
                first_file = first_line[6:-1]  # Remove 'file ' prefix and quotes
    except Exception as e:
        logger.warning(f"Could not read concat file to determine encoding: {e}")
    
    if first_file and Path(first_file).exists():
        encode_args = {**make_video_encode_args_from_source(str(first_file)), **make_audio_encode_args_copy()}
    else:
        # Fallback: use copy for both
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


def hstack_keep_height(left_path: str, right_path: str, out_path: Path | str) -> None:
    """Stack two videos horizontally keeping source heights; widths scale proportionally."""
    left_vp = get_video_params(left_path)
    left_in = ffmpeg.input(left_path)
    right_in = ffmpeg.input(right_path)

    # Scale right to match left height, preserve aspect ratio
    right_scaled = ffmpeg.filter(right_in["v"], "scale", -2, left_vp.height or -1)
    left_v = left_in["v"]
    stacked_v = ffmpeg.filter([left_v, right_scaled], "hstack", inputs=2)

    # Prefer audio from left input as-is
    left_a = left_in["a"]
    output_with_explicit_streams(
        stacked_v,
        left_a,
        out_path,
        **make_video_encode_args_from_source(left_path),
        **make_audio_encode_args_copy(),
    )


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
    
    # Use concat demuxer
    try:
        (
            ffmpeg
            .input('pipe:', format='concat', safe=0)
            .output(
                str(out_path),
                **make_video_encode_args_from_source(input_path),
                **make_audio_encode_args_copy()
            )
            .overwrite_output()
            .run(input=concat_content.encode('utf-8'), quiet=True)
        )
    except ffmpeg.Error as e:
        logger.error(f"concat demuxer failed, falling back to file-based method: {e}")
        # Fallback: write concat file to disk
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
                .run(quiet=True)
            )
        finally:
            import os
            if os.path.exists(concat_file):
                os.unlink(concat_file)
        ensure_dir(Path(out_path))


