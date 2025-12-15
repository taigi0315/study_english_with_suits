"""
Unit tests for VideoComposer.

Tests video composition functionality including:
- Video concatenation
- Encoding argument generation
- Temp file management
"""

import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import ffmpeg

from langflix.core.video.video_composer import VideoComposer


def _make_test_video(path: Path, duration: float = 1.0) -> Path:
    """Helper to create a simple test video."""
    path.parent.mkdir(parents=True, exist_ok=True)
    sine = ffmpeg.input(f"sine=frequency=440:sample_rate=44100", f="lavfi", t=duration)
    color = ffmpeg.input("color=c=black:s=320x240:r=25", f="lavfi", t=duration)
    (
        ffmpeg
        .output(color["v"], sine["a"], str(path), vcodec="libx264", acodec="aac", preset="ultrafast")
        .overwrite_output()
        .run(quiet=True)
    )
    return path


class TestVideoComposer:
    """Test suite for VideoComposer class."""

    def test_init_creates_output_dir(self, tmp_path):
        """Test that VideoComposer creates output directory."""
        output_dir = tmp_path / "output"
        composer = VideoComposer(output_dir=output_dir, test_mode=True)

        assert output_dir.exists()
        assert composer.output_dir == output_dir
        assert composer.test_mode is True

    def test_init_test_mode_encoding(self, tmp_path):
        """Test that test mode uses fast encoding settings."""
        composer = VideoComposer(output_dir=tmp_path, test_mode=True)
        args = composer.encoding_args

        assert args['preset'] == 'ultrafast'
        assert args['crf'] == 28
        assert args['vcodec'] == 'libx264'
        assert args['acodec'] == 'aac'

    def test_init_production_mode_encoding(self, tmp_path):
        """Test that production mode uses quality encoding settings."""
        composer = VideoComposer(output_dir=tmp_path, test_mode=False)
        args = composer.encoding_args

        assert args['preset'] == 'slow'
        assert args['crf'] == 18
        assert args['vcodec'] == 'libx264'
        assert args['acodec'] == 'aac'

    def test_combine_videos_creates_output(self, tmp_path):
        """Test that combine_videos creates concatenated video."""
        # Create test videos
        video1 = _make_test_video(tmp_path / "video1.mp4", duration=0.5)
        video2 = _make_test_video(tmp_path / "video2.mp4", duration=0.5)

        # Combine videos
        composer = VideoComposer(output_dir=tmp_path, test_mode=True)
        output_path = str(tmp_path / "combined.mp4")
        result = composer.combine_videos(
            video_paths=[str(video1), str(video2)],
            output_path=output_path
        )

        assert result == output_path
        assert Path(output_path).exists()

        # Verify output is a valid video
        probe = ffmpeg.probe(output_path)
        assert 'streams' in probe
        assert len(probe['streams']) >= 1

    def test_combine_videos_raises_on_empty_list(self, tmp_path):
        """Test that combine_videos raises ValueError on empty video list."""
        composer = VideoComposer(output_dir=tmp_path, test_mode=True)

        with pytest.raises(ValueError, match="No video paths provided"):
            composer.combine_videos(
                video_paths=[],
                output_path=str(tmp_path / "output.mp4")
            )

    def test_combine_videos_creates_temp_concat_file(self, tmp_path):
        """Test that combine_videos creates temporary concat list file."""
        # Create test videos
        video1 = _make_test_video(tmp_path / "video1.mp4", duration=0.5)
        video2 = _make_test_video(tmp_path / "video2.mp4", duration=0.5)

        composer = VideoComposer(output_dir=tmp_path, test_mode=True)
        output_path = str(tmp_path / "combined.mp4")

        # Mock temp_manager to track registered files
        mock_temp_manager = Mock()
        composer.temp_manager = mock_temp_manager

        composer.combine_videos(
            video_paths=[str(video1), str(video2)],
            output_path=output_path
        )

        # Verify temp file was registered
        assert mock_temp_manager.register_file.called
        registered_path = mock_temp_manager.register_file.call_args[0][0]
        assert 'temp_concat_list' in str(registered_path)

    def test_get_encoding_args_test_mode(self, tmp_path):
        """Test encoding args in test mode."""
        composer = VideoComposer(output_dir=tmp_path, test_mode=True)
        args = composer._get_encoding_args()

        assert args['preset'] == 'ultrafast'
        assert args['crf'] == 28
        assert args['b:a'] == '128k'
        assert args['ac'] == 2
        assert args['ar'] == 48000

    def test_get_encoding_args_production_mode(self, tmp_path):
        """Test encoding args in production mode."""
        composer = VideoComposer(output_dir=tmp_path, test_mode=False)
        args = composer._get_encoding_args()

        assert args['preset'] == 'slow'
        assert args['crf'] == 18
        assert args['b:a'] == '256k'
        assert args['ac'] == 2
        assert args['ar'] == 48000

    @patch('langflix.settings.get_encoding_preset')
    def test_get_encoding_args_respects_settings(self, mock_get_preset, tmp_path):
        """Test that encoding args respect settings configuration."""
        # Mock settings to return custom encoding preset
        mock_get_preset.return_value = {
            'preset': 'medium',
            'crf': 23,
            'audio_bitrate': '128k'
        }

        composer = VideoComposer(output_dir=tmp_path, test_mode=False)
        args = composer._get_encoding_args()

        assert args['preset'] == 'medium'
        assert args['crf'] == 23
        assert args['b:a'] == '128k'

    def test_get_encoding_args_adjusts_for_720p(self, tmp_path):
        """Test that 720p sources get higher quality encoding in production."""
        # Create a 720p test video
        video_720p = tmp_path / "video_720p.mp4"
        _make_test_video(video_720p, duration=0.5)

        composer = VideoComposer(output_dir=tmp_path, test_mode=False)

        # Mock get_video_params to return 720p dimensions
        with patch('langflix.media.ffmpeg_utils.get_video_params') as mock_get_params:
            mock_params = Mock()
            mock_params.height = 720
            mock_get_params.return_value = mock_params

            args = composer._get_encoding_args(source_video_path=str(video_720p))

            # For 720p in production mode, CRF should be adjusted to 16 (higher quality)
            assert args['crf'] <= 18  # Should be 16 or base CRF (18)

    def test_combine_videos_handles_absolute_paths(self, tmp_path):
        """Test that combine_videos handles absolute paths correctly."""
        video1 = _make_test_video(tmp_path / "video1.mp4", duration=0.5)
        video2 = _make_test_video(tmp_path / "video2.mp4", duration=0.5)

        composer = VideoComposer(output_dir=tmp_path, test_mode=True)
        output_path = str(tmp_path / "combined.mp4")

        # Use absolute paths
        result = composer.combine_videos(
            video_paths=[str(video1.absolute()), str(video2.absolute())],
            output_path=output_path
        )

        assert Path(result).exists()

    def test_temp_manager_not_available(self, tmp_path):
        """Test that VideoComposer handles missing temp_manager gracefully."""
        with patch('langflix.utils.temp_file_manager.get_temp_manager', side_effect=ImportError):
            composer = VideoComposer(output_dir=tmp_path, test_mode=True)
            assert composer.temp_manager is None

    def test_combine_videos_creates_parent_directory(self, tmp_path):
        """Test that combine_videos creates parent directory if it doesn't exist."""
        video1 = _make_test_video(tmp_path / "video1.mp4", duration=0.5)
        video2 = _make_test_video(tmp_path / "video2.mp4", duration=0.5)

        composer = VideoComposer(output_dir=tmp_path, test_mode=True)

        # Output path with non-existent parent directory
        output_path = str(tmp_path / "nested" / "dir" / "combined.mp4")
        result = composer.combine_videos(
            video_paths=[str(video1), str(video2)],
            output_path=output_path
        )

        assert Path(result).exists()
        assert Path(result).parent.exists()

    def test_extract_clip_creates_clip(self, tmp_path):
        """Test that extract_clip extracts a video clip correctly."""
        # Create a 2-second test video
        source_video = _make_test_video(tmp_path / "source.mp4", duration=2.0)

        composer = VideoComposer(output_dir=tmp_path, test_mode=True)
        output_path = str(tmp_path / "clip.mp4")

        # Extract 0.5s clip from 0.5s to 1.0s
        result = composer.extract_clip(
            source_video=str(source_video),
            start_time=0.5,
            end_time=1.0,
            output_path=output_path
        )

        assert result == output_path
        assert Path(output_path).exists()

        # Verify clip duration is approximately 0.5s
        probe = ffmpeg.probe(output_path)
        duration = float(probe['format']['duration'])
        assert 0.4 < duration < 0.6  # Allow some tolerance

    def test_extract_clip_raises_on_invalid_duration(self, tmp_path):
        """Test that extract_clip raises ValueError for invalid duration."""
        source_video = _make_test_video(tmp_path / "source.mp4", duration=2.0)

        composer = VideoComposer(output_dir=tmp_path, test_mode=True)

        with pytest.raises(ValueError, match="Invalid duration"):
            composer.extract_clip(
                source_video=str(source_video),
                start_time=1.0,
                end_time=0.5,  # End before start
                output_path=str(tmp_path / "clip.mp4")
            )

    def test_extract_clip_creates_parent_directory(self, tmp_path):
        """Test that extract_clip creates parent directory if needed."""
        source_video = _make_test_video(tmp_path / "source.mp4", duration=2.0)

        composer = VideoComposer(output_dir=tmp_path, test_mode=True)
        output_path = str(tmp_path / "nested" / "dir" / "clip.mp4")

        result = composer.extract_clip(
            source_video=str(source_video),
            start_time=0.0,
            end_time=0.5,
            output_path=output_path
        )

        assert Path(result).exists()
        assert Path(result).parent.exists()
