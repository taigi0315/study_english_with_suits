"""
Comprehensive integration tests for media pipeline verification.

This test suite is based on tools/verify_media_pipeline.py and verifies:
1) Demuxer-based AV repetition preserves audio
2) Concatenation via demuxer maintains audio
3) Stacking preserves audio
4) Audio has valid parameters (channels, sample_rate, duration > 0)
5) Final layout matches spec (long=hstack, short=vstack)
6) Final audio gain application preserves audio

These tests ensure the media pipeline functions correctly and can be run
automatically in CI/CD.
"""
import pytest
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
    apply_final_audio_gain,
)


def _make_test_av(path: Path, w: int, h: int, sr: int, ch: int, dur: float, freq: int = 440) -> Path:
    """Create a test AV file with specified parameters."""
    color = ffmpeg.input(f"color=c=black:s={w}x{h}:r=25", f="lavfi", t=dur)
    sine = ffmpeg.input(f"sine=frequency={freq}:sample_rate={sr}", f="lavfi", t=dur)
    (
        ffmpeg
        .output(color["v"], sine["a"], str(path), vcodec="libx264", acodec="aac", ac=ch, ar=sr)
        .overwrite_output()
        .run(quiet=True)
    )
    return path


def _assert_audio_present(path: Path, label: str):
    """Assert audio stream exists with valid parameters."""
    ap = get_audio_params(str(path))
    vp = get_video_params(str(path))
    dur = get_duration_seconds(str(path))
    
    # Check audio exists
    assert ap.codec is not None, f"[{label}] No audio stream found"
    
    # Check audio parameters
    assert ap.channels is not None, f"[{label}] Audio channels not detected"
    assert ap.sample_rate is not None, f"[{label}] Audio sample rate not detected"
    
    # Check duration is non-zero
    assert dur > 0, f"[{label}] Duration is zero or negative: {dur}"
    
    # Check video exists
    assert vp.codec is not None, f"[{label}] No video stream found"
    assert vp.width is not None, f"[{label}] Video width not detected"
    assert vp.height is not None, f"[{label}] Video height not detected"
    
    return {
        'audio': ap,
        'video': vp,
        'duration': dur
    }


def _assert_layout(path: Path, label: str, expected_layout: str):
    """Assert video layout matches expected (long=hstack or short=vstack)."""
    probe = run_ffprobe(str(path))
    v_streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "video"]
    
    assert len(v_streams) > 0, f"[{label}] No video stream found"
    
    v = v_streams[0]
    width = v.get("width")
    height = v.get("height")
    
    assert width is not None and height is not None, f"[{label}] Video dimensions not detected"
    
    # Basic sanity checks for layout
    if expected_layout == "hstack":
        # Long-form: side-by-side should be wide
        assert width > height * 1.5, (
            f"[{label}] Layout check failed: {width}x{height} "
            f"expected hstack/wide (width should be > height * 1.5)"
        )
    elif expected_layout == "vstack":
        # Short-form: top-bottom should be tall
        assert height > width * 1.3, (
            f"[{label}] Layout check failed: {width}x{height} "
            f"expected vstack/tall (height should be > width * 1.3)"
        )
    
    return width, height


@pytest.mark.integration
class TestMediaPipelineComprehensive:
    """Comprehensive media pipeline verification tests."""
    
    def test_input_av_clips(self, tmp_path):
        """Test that input AV clips are created correctly."""
        a = _make_test_av(tmp_path / "a.mkv", 640, 360, 44100, 1, 1.0, 440)
        b = _make_test_av(tmp_path / "b.mkv", 1280, 720, 48000, 2, 1.0, 660)
        
        info_a = _assert_audio_present(a, "input_a")
        info_b = _assert_audio_present(b, "input_b")
        
        # Verify input parameters
        assert info_a['audio'].channels == 1
        assert info_a['audio'].sample_rate == 44100
        assert info_b['audio'].channels == 2
        assert info_b['audio'].sample_rate == 48000
    
    def test_filter_based_concat(self, tmp_path):
        """Test filter-based concat preserves audio."""
        # Use same resolution and sample rate for compatibility
        a = _make_test_av(tmp_path / "a.mkv", 640, 360, 48000, 2, 1.0, 440)
        b = _make_test_av(tmp_path / "b.mkv", 640, 360, 48000, 2, 1.0, 660)
        
        concat_out = tmp_path / "concat_out.mkv"
        concat_filter_with_explicit_map(str(a), str(b), str(concat_out))
        
        info = _assert_audio_present(concat_out, "concat_filter")
        assert info['duration'] > 1.5, "Concat duration should be > 1.5s (two 1s clips)"
    
    def test_demuxer_based_repeat(self, tmp_path):
        """Test demuxer-based AV repetition preserves audio."""
        a = _make_test_av(tmp_path / "a.mkv", 640, 360, 44100, 1, 1.0, 440)
        
        repeat_out = tmp_path / "repeat_out.mkv"
        repeat_av_demuxer(str(a), 3, str(repeat_out))
        
        info = _assert_audio_present(repeat_out, "repeat_demuxer")
        # Should be approximately 3x the original duration (with small tolerance)
        assert 2.8 <= info['duration'] <= 3.2, (
            f"Repeated video duration should be ~3s, got {info['duration']:.2f}s"
        )
    
    def test_demuxer_based_concat(self, tmp_path):
        """Test demuxer-based concat maintains audio."""
        a = _make_test_av(tmp_path / "a.mkv", 640, 360, 44100, 1, 1.0, 440)
        b = _make_test_av(tmp_path / "b.mkv", 1280, 720, 48000, 2, 1.0, 660)
        
        concat_list = tmp_path / "concat_list.txt"
        with open(concat_list, 'w') as f:
            f.write(f"file '{a.absolute()}'\n")
            f.write(f"file '{b.absolute()}'\n")
        
        concat_demuxer_out = tmp_path / "concat_demuxer_out.mkv"
        concat_demuxer_if_uniform(str(concat_list), str(concat_demuxer_out))
        
        info = _assert_audio_present(concat_demuxer_out, "concat_demuxer")
        assert info['duration'] > 1.5, "Demuxer concat duration should be > 1.5s"
    
    def test_hstack_long_form_layout(self, tmp_path):
        """Test hstack (long-form side-by-side layout) preserves audio and layout."""
        a = _make_test_av(tmp_path / "a.mkv", 640, 360, 44100, 1, 1.0, 440)
        b = _make_test_av(tmp_path / "b.mkv", 1280, 720, 48000, 2, 1.0, 660)
        
        hstack_out = tmp_path / "hstack_out.mkv"
        hstack_keep_height(str(a), str(b), str(hstack_out))
        
        info = _assert_audio_present(hstack_out, "hstack")
        width, height = _assert_layout(hstack_out, "hstack", "hstack")
        
        # Verify layout dimensions make sense
        # hstack should combine widths, keep max height
        assert width > 640, "hstack width should be wider than individual clips"
        assert height >= 360, "hstack height should be at least max of individual heights"
    
    def test_vstack_short_form_layout(self, tmp_path):
        """Test vstack (short-form top-bottom layout) preserves audio and layout."""
        # Use same width for vstack (vstack_keep_width requires same width)
        a = _make_test_av(tmp_path / "a.mkv", 640, 360, 48000, 2, 1.0, 440)
        b = _make_test_av(tmp_path / "b.mkv", 640, 720, 48000, 2, 1.0, 660)
        
        vstack_out = tmp_path / "vstack_out.mkv"
        vstack_keep_width(str(a), str(b), str(vstack_out))
        
        info = _assert_audio_present(vstack_out, "vstack")
        width, height = _assert_layout(vstack_out, "vstack", "vstack")
        
        # Verify layout dimensions make sense
        # vstack should combine heights, keep same width
        assert height > 360, "vstack height should be taller than individual clips"
        assert width == 640, "vstack width should match input width (640)"
    
    def test_final_audio_gain(self, tmp_path):
        """Test final audio gain application preserves audio."""
        # Create a test video
        input_video = _make_test_av(tmp_path / "gain_input.mkv", 640, 360, 44100, 2, 1.0, 440)
        
        # Verify input has audio
        input_info = _assert_audio_present(input_video, "gain_input")
        
        gain_output = tmp_path / "gain_output.mkv"
        apply_final_audio_gain(str(input_video), str(gain_output), gain_factor=1.25)
        
        # Verify output has audio
        output_info = _assert_audio_present(gain_output, "final_gain")
        
        # Verify audio codec is aac (gain application encodes to aac)
        assert output_info['audio'].codec == 'aac', "Final gain should encode to aac"
        
        # Duration should be preserved
        assert abs(output_info['duration'] - input_info['duration']) < 0.1, (
            "Duration should be preserved after gain application"
        )
    
    def test_complete_pipeline_sequence(self, tmp_path):
        """Test complete pipeline sequence: concat -> repeat -> stack -> gain."""
        # Create test clips with compatible parameters
        a = _make_test_av(tmp_path / "a.mkv", 640, 360, 48000, 2, 1.0, 440)
        b = _make_test_av(tmp_path / "b.mkv", 640, 360, 48000, 2, 1.0, 660)
        
        # Step 1: Concat (using demuxer for better compatibility)
        concat_list = tmp_path / "pipeline_concat_list.txt"
        with open(concat_list, 'w') as f:
            f.write(f"file '{a.absolute()}'\n")
            f.write(f"file '{b.absolute()}'\n")
        
        concat_out = tmp_path / "pipeline_concat.mkv"
        concat_demuxer_if_uniform(str(concat_list), str(concat_out))
        _assert_audio_present(concat_out, "pipeline_concat")
        
        # Step 2: Repeat
        repeat_out = tmp_path / "pipeline_repeat.mkv"
        repeat_av_demuxer(str(concat_out), 2, str(repeat_out))
        repeat_info = _assert_audio_present(repeat_out, "pipeline_repeat")
        
        # Step 3: Stack (use same height for hstack)
        stack_out = tmp_path / "pipeline_stack.mkv"
        hstack_keep_height(str(repeat_out), str(b), str(stack_out))
        stack_info = _assert_audio_present(stack_out, "pipeline_stack")
        _assert_layout(stack_out, "pipeline_stack", "hstack")
        
        # Step 4: Final gain
        final_out = tmp_path / "pipeline_final.mkv"
        apply_final_audio_gain(str(stack_out), str(final_out), gain_factor=1.25)
        final_info = _assert_audio_present(final_out, "pipeline_final")
        
        # Verify audio is preserved through all steps
        assert final_info['audio'].codec == 'aac'
        assert final_info['audio'].channels is not None
        assert final_info['audio'].sample_rate is not None
        assert final_info['duration'] > 0

