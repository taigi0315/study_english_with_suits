from pathlib import Path

import ffmpeg

from langflix.media.ffmpeg_utils import (
    get_audio_params,
    concat_filter_with_explicit_map,
    hstack_keep_height,
    apply_final_audio_gain,
)


def _make_tone(w: int, h: int, sr: int, ch: int, dur: float, path: Path) -> Path:
    color = ffmpeg.input(f"color=c=blue:s={w}x{h}:r=25", f="lavfi", t=dur)
    a = ffmpeg.input(f"sine=frequency=660:sample_rate={sr}", f="lavfi", t=dur)
    (
        ffmpeg
        .output(color["v"], a["a"], str(path), vcodec="libx264", acodec="aac", ac=ch, ar=sr)
        .overwrite_output()
        .run(quiet=True)
    )
    return path


def test_concat_and_stack_pipeline(tmp_path: Path):
    """Test that concat and stack operations preserve audio presence."""
    a = _make_tone(854, 480, 44100, 1, 1.0, tmp_path / "a.mkv")
    b = _make_tone(1280, 720, 48000, 2, 1.0, tmp_path / "b.mkv")

    # concat with explicit mapping - audio should be present
    concat_out = tmp_path / "concat_out.mkv"
    concat_filter_with_explicit_map(str(a), str(b), str(concat_out))
    ap = get_audio_params(str(concat_out))
    # Audio should exist (demuxer keeps original first file's params or first file's audio)
    assert ap.channels is not None and ap.sample_rate is not None

    # stack with audio preserved from left
    stack_out = tmp_path / "stack_out.mkv"
    hstack_keep_height(str(concat_out), str(b), str(stack_out))
    sap = get_audio_params(str(stack_out))
    # Audio should exist
    assert sap.channels is not None and sap.sample_rate is not None

    # Test final audio gain application
    gain_output = tmp_path / "gain_output.mkv"
    apply_final_audio_gain(str(stack_out), str(gain_output), gain_factor=1.25)
    gain_ap = get_audio_params(str(gain_output))
    # Audio should still exist after gain application
    # Note: gain application encodes to aac with normalization, so params may change
    assert gain_ap.channels is not None and gain_ap.sample_rate is not None
    assert gain_ap.codec == 'aac'  # Should be encoded to aac


