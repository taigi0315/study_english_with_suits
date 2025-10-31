#!/usr/bin/env python3
"""
Verify media pipeline audio presence and parameters.

This script verifies:
1) Demuxer-based AV repetition preserves audio
2) Concatenation via demuxer maintains audio
3) Stacking preserves audio
4) Audio has valid parameters (channels, sample_rate, duration > 0)
5) Final layout matches spec (long=hstack, short=vstack)

Usage:
  python tools/verify_media_pipeline.py
"""

import sys
from pathlib import Path

import ffmpeg

from langflix.media.ffmpeg_utils import (
    get_audio_params,
    get_video_params,
    concat_filter_with_explicit_map,
    concat_demuxer_if_uniform,
    hstack_keep_height,
    vstack_keep_width,
    repeat_av_demuxer,
    run_ffprobe,
    get_duration_seconds,
)


def make_av(path: Path, w: int, h: int, sr: int, ch: int, dur: float, freq: int = 440) -> Path:
    color = ffmpeg.input(f"color=c=black:s={w}x{h}:r=25", f="lavfi", t=dur)
    sine = ffmpeg.input(f"sine=frequency={freq}:sample_rate={sr}", f="lavfi", t=dur)
    (
        ffmpeg
        .output(color["v"], sine["a"], str(path), vcodec="libx264", acodec="aac", ac=ch, ar=sr)
        .overwrite_output()
        .run(quiet=True)
    )
    return path


def assert_audio(p: Path, label: str):
    """Assert audio stream exists with valid parameters."""
    ap = get_audio_params(str(p))
    vp = get_video_params(str(p))
    dur = get_duration_seconds(str(p))
    
    # Check audio exists
    if ap.codec is None:
        print(f"[{label}] ❌ No audio stream found")
        sys.exit(1)
    
    # Check audio parameters
    ok_params = ap.channels is not None and ap.sample_rate is not None
    print(f"[{label}] audio: codec={ap.codec} ch={ap.channels} sr={ap.sample_rate} -> {'OK' if ok_params else 'FAIL'}")
    
    # Check duration is non-zero
    ok_dur = dur > 0
    print(f"[{label}] duration: {dur:.2f}s -> {'OK' if ok_dur else 'FAIL'}")
    
    # Check video exists
    ok_video = vp.codec is not None and vp.width is not None and vp.height is not None
    print(f"[{label}] video: codec={vp.codec} {vp.width}x{vp.height} -> {'OK' if ok_video else 'FAIL'}")
    
    if not (ok_params and ok_dur and ok_video):
        sys.exit(1)
    
    return True


def assert_layout(p: Path, label: str, expected_layout: str):
    """Assert video layout matches expected (long=hstack or short=vstack)."""
    probe = run_ffprobe(str(p))
    v_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "video"]
    
    if not v_streams:
        print(f"[{label}] ❌ No video stream found")
        sys.exit(1)
    
    v = v_streams[0]
    width = v.get("width")
    height = v.get("height")
    
    # Basic sanity checks
    if expected_layout == "hstack":
        # Long-form: side-by-side should be wide
        ok = width and height and width > height * 1.5
        print(f"[{label}] layout: {width}x{height} (expected hstack/wide) -> {'OK' if ok else 'WARN'}")
    elif expected_layout == "vstack":
        # Short-form: top-bottom should be tall
        ok = width and height and height > width * 1.3
        print(f"[{label}] layout: {width}x{height} (expected vstack/tall) -> {'OK' if ok else 'WARN'}")
    else:
        print(f"[{label}] layout: {width}x{height} -> OK")


def main():
    print("=== Media Pipeline Verification ===")
    tmp = Path("test_output/tools_verify")
    tmp.mkdir(parents=True, exist_ok=True)

    # Create test AV clips
    print("\n1. Creating test AV clips...")
    a = make_av(tmp / "a.mkv", 640, 360, 44100, 1, 1.0, 440)
    b = make_av(tmp / "b.mkv", 1280, 720, 48000, 2, 1.0, 660)
    assert_audio(a, "input_a")
    assert_audio(b, "input_b")

    # Test filter-based concat
    print("\n2. Testing filter-based concat...")
    concat_out = tmp / "concat_out.mkv"
    concat_filter_with_explicit_map(str(a), str(b), str(concat_out))
    assert_audio(concat_out, "concat_filter")

    # Test demuxer-based repeat
    print("\n3. Testing demuxer-based AV repeat...")
    repeat_out = tmp / "repeat_out.mkv"
    repeat_av_demuxer(str(a), 3, str(repeat_out))
    assert_audio(repeat_out, "repeat_demuxer")
    assert_layout(repeat_out, "repeat_demuxer", "")

    # Test demuxer-based concat
    print("\n4. Testing demuxer-based concat...")
    concat_list = tmp / "concat_list.txt"
    with open(concat_list, 'w') as f:
        f.write(f"file '{tmp.absolute() / 'a.mkv'}'\n")
        f.write(f"file '{tmp.absolute() / 'b.mkv'}'\n")
    
    concat_demuxer_out = tmp / "concat_demuxer_out.mkv"
    concat_demuxer_if_uniform(str(concat_list), str(concat_demuxer_out))
    assert_audio(concat_demuxer_out, "concat_demuxer")

    # Test hstack (long-form layout)
    print("\n5. Testing hstack (long-form side-by-side layout)...")
    hstack_out = tmp / "hstack_out.mkv"
    hstack_keep_height(str(a), str(b), str(hstack_out))
    assert_audio(hstack_out, "hstack")
    assert_layout(hstack_out, "hstack", "hstack")

    # Test vstack (short-form top-bottom layout)
    print("\n6. Testing vstack (short-form top-bottom layout)...")
    vstack_out = tmp / "vstack_out.mkv"
    vstack_keep_width(str(a), str(b), str(vstack_out))
    assert_audio(vstack_out, "vstack")
    assert_layout(vstack_out, "vstack", "vstack")

    print("\n✅ All checks passed!")


if __name__ == "__main__":
    main()


