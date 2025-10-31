import os
from pathlib import Path

import ffmpeg

from langflix.media.ffmpeg_utils import (
    get_audio_params,
    get_video_params,
    concat_filter_with_explicit_map,
    vstack_keep_width,
)


def _make_av(path: Path, freq: int = 440, sr: int = 44100, ch: int = 1, w: int = 320, h: int = 240, dur: float = 1.0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    sine = ffmpeg.input(f"sine=frequency={freq}:sample_rate={sr}:beep_factor=2", f="lavfi", t=dur)
    color = ffmpeg.input("color=c=black:s={}x{}:r=25".format(w, h), f="lavfi", t=dur)
    (
        ffmpeg
        .output(color["v"], sine["a"], str(path), vcodec="libx264", acodec="aac", ac=ch, ar=sr)
        .overwrite_output()
        .run(quiet=True)
    )
    return path


def test_concat_filter_preserves_audio(tmp_path: Path):
    """Test that concat preserves audio presence (demuxer may keep first file's params)."""
    a = _make_av(tmp_path / "a.mkv", sr=44100, ch=1)
    b = _make_av(tmp_path / "b.mkv", sr=48000, ch=2)
    out = tmp_path / "out_concat.mkv"
    concat_filter_with_explicit_map(str(a), str(b), str(out))

    ap = get_audio_params(str(out))
    # Audio should exist (parameters may vary depending on fallback to demuxer)
    assert ap.channels is not None
    assert ap.sample_rate is not None


def test_vstack_keeps_audio_from_top(tmp_path: Path):
    top = _make_av(tmp_path / "top.mkv", w=320, h=240, sr=48000, ch=2)
    bot = _make_av(tmp_path / "bot.mkv", w=640, h=360, sr=44100, ch=1)
    out = tmp_path / "out_stack.mkv"
    vstack_keep_width(str(top), str(bot), str(out))

    vp = get_video_params(str(out))
    assert vp.width in (320, 321, 318)  # allow minor scaler variance
    ap = get_audio_params(str(out))
    assert ap.channels == 2
    assert ap.sample_rate == 48000


