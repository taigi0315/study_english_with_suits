"""
Audio timeline builders for LangFlix

Provides utilities to generate repeated audio timelines following the pattern:
1.0s silence - segment - 0.5s silence - segment - ... - 1.0s silence

All outputs are normalized to stereo 48k for stable mux/concat.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, List, Tuple

import ffmpeg

logger = logging.getLogger(__name__)


def _gen_silence(path: Path, duration: float, sample_rate: int = 48000, channels: int = 2) -> Path:
    (
        ffmpeg
        .input(f"anullsrc=r={sample_rate}:cl=stereo", f="lavfi", t=duration)
        .output(str(path), acodec="pcm_s16le", ar=sample_rate, ac=channels)
        .overwrite_output()
        .run(quiet=True)
    )
    return path


def _to_wav(input_path: Path, out_path: Path, sample_rate: int = 48000, channels: int = 2) -> Path:
    (
        ffmpeg
        .input(str(input_path))
        .audio
        .output(str(out_path), acodec="pcm_s16le", ar=sample_rate, ac=channels)
        .overwrite_output()
        .run(quiet=True)
    )
    return out_path


def concat_audio_files(list_file: Path, out_path: Path, sample_rate: int = 48000, channels: int = 2) -> Path:
    (
        ffmpeg
        .input(str(list_file), format="concat", safe=0)
        .output(str(out_path), acodec="pcm_s16le", ar=sample_rate, ac=channels)
        .overwrite_output()
        .run(quiet=True)
    )
    return out_path


def build_repeated_timeline(
    base_audio_path: Path,
    out_path: Path,
    repeat_count: int,
    start_silence: float = 1.0,
    gap_silence: float = 0.5,
    end_silence: float = 1.0,
) -> Tuple[Path, float]:
    """Create timeline: 1s - (segment + 0.5s) * repeat_count - last segment - 1s.

    Returns (timeline_path, total_duration_seconds).
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Prepare building blocks
    tmp_dir = out_path.parent
    seg_wav = tmp_dir / f"_seg_{out_path.stem}.wav"
    seg_wav = _to_wav(base_audio_path, seg_wav)
    s1 = _gen_silence(tmp_dir / f"_silence_start_{out_path.stem}.wav", start_silence)
    s05 = _gen_silence(tmp_dir / f"_silence_gap_{out_path.stem}.wav", gap_silence)
    s_end = _gen_silence(tmp_dir / f"_silence_end_{out_path.stem}.wav", end_silence)

    # Build concat list
    concat_list = tmp_dir / f"_concat_{out_path.stem}.txt"
    with concat_list.open("w") as f:
        f.write(f"file '{s1.resolve()}'\n")
        for i in range(repeat_count):
            f.write(f"file '{seg_wav.resolve()}'\n")
            if i < repeat_count - 1:
                f.write(f"file '{s05.resolve()}'\n")
        f.write(f"file '{s_end.resolve()}'\n")

    # Concat
    concat_audio_files(concat_list, out_path)

    # Probe duration
    try:
        probe = ffmpeg.probe(str(seg_wav))
        seg_dur = float(probe["format"]["duration"]) if "format" in probe else 0.0
    except Exception:
        seg_dur = 0.0

    total = start_silence + (seg_dur * repeat_count) + (gap_silence * (repeat_count - 1)) + end_silence
    logger.info(f"Audio timeline created: {out_path} ({total:.2f}s)")
    return out_path, total


def extract_segment_to_wav(
    source_video_path: Path,
    start_seconds: float,
    duration_seconds: float,
    out_path: Path,
) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    (
        ffmpeg
        .input(str(source_video_path), ss=start_seconds, t=duration_seconds)
        .audio
        .output(str(out_path), acodec="pcm_s16le", ar=48000, ac=2)
        .overwrite_output()
        .run(quiet=True)
    )
    return out_path


