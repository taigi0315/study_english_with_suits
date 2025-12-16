"""
Unit tests for PathResolver.

Tests path resolution functionality including:
- Directory resolution
- Temporary file paths
- Expression filename generation
- Short-form and long-form video paths
- Subtitle paths
- Cleanup utilities
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from langflix.core.utils.path_resolver import PathResolver


class TestPathResolver:
    """Test suite for PathResolver class."""

    def test_init_creates_output_dir(self, tmp_path):
        """Test that PathResolver creates output directory."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        assert output_dir.exists()
        assert resolver.output_dir == output_dir
        assert resolver.language_dir == tmp_path / "korean"

    def test_init_with_string_path(self, tmp_path):
        """Test initialization with string path."""
        output_dir = str(tmp_path / "korean" / "long_form_videos")
        resolver = PathResolver(output_dir=output_dir)

        assert resolver.output_dir == Path(output_dir)
        assert resolver.output_dir.exists()

    def test_init_without_creating_dirs(self, tmp_path):
        """Test initialization without creating directories."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir, create_dirs=False)

        assert not output_dir.exists()
        assert resolver.output_dir == output_dir

    def test_get_language_dir(self, tmp_path):
        """Test language directory resolution."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        language_dir = resolver.get_language_dir()

        assert language_dir == tmp_path / "korean"
        assert language_dir.exists()

    def test_get_shorts_dir(self, tmp_path):
        """Test shorts directory resolution."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        shorts_dir = resolver.get_shorts_dir()

        assert shorts_dir == tmp_path / "korean" / "shorts"
        assert shorts_dir.exists()

    def test_get_expressions_dir(self, tmp_path):
        """Test expressions directory resolution."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        expressions_dir = resolver.get_expressions_dir()

        assert expressions_dir == tmp_path / "korean" / "expressions"
        assert expressions_dir.exists()

    def test_get_subtitles_dir(self, tmp_path):
        """Test subtitles directory resolution."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        subtitles_dir = resolver.get_subtitles_dir()

        assert subtitles_dir == tmp_path / "korean" / "subtitles"
        assert subtitles_dir.exists()

    def test_get_tts_audio_dir(self, tmp_path):
        """Test TTS audio directory resolution."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        tts_audio_dir = resolver.get_tts_audio_dir()

        assert tts_audio_dir == tmp_path / "korean" / "tts_audio"
        assert tts_audio_dir.exists()

    def test_get_videos_dir(self, tmp_path):
        """Test videos directory resolution."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        videos_dir = resolver.get_videos_dir()

        assert videos_dir == tmp_path / "korean" / "videos"
        assert videos_dir.exists()

    def test_get_output_dir(self, tmp_path):
        """Test output directory resolution."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        result = resolver.get_output_dir()

        assert result == output_dir
        assert result.exists()

    def test_get_temp_path(self, tmp_path):
        """Test temporary file path generation."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        temp_path = resolver.get_temp_path("context_clip", "hello", "mkv")

        assert temp_path == output_dir / "temp_context_clip_hello.mkv"
        assert temp_path.parent.exists()

    def test_get_temp_path_with_different_extension(self, tmp_path):
        """Test temporary file path with custom extension."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        temp_path = resolver.get_temp_path("audio", "clip1", "wav")

        assert temp_path == output_dir / "temp_audio_clip1.wav"

    def test_get_temp_concat_list(self, tmp_path):
        """Test temporary concat list path generation."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        concat_list = resolver.get_temp_concat_list("combined")

        assert concat_list == output_dir / "temp_concat_list_combined.txt"

    @patch('langflix.utils.filename_utils.sanitize_for_expression_filename')
    def test_get_expression_filename(self, mock_sanitize, tmp_path):
        """Test expression filename generation."""
        mock_sanitize.return_value = "annyeonghaseyo"
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        filename = resolver.get_expression_filename("안녕하세요", index=0)

        assert filename == "0_annyeonghaseyo.mkv"
        mock_sanitize.assert_called_once_with("안녕하세요")

    @patch('langflix.utils.filename_utils.sanitize_for_expression_filename')
    def test_get_expression_filename_with_prefix_suffix(self, mock_sanitize, tmp_path):
        """Test expression filename with prefix and suffix."""
        mock_sanitize.return_value = "hello"
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        filename = resolver.get_expression_filename(
            "hello",
            index=5,
            prefix="short",
            suffix="with_logo"
        )

        assert filename == "short_5_hello_with_logo.mkv"

    @patch('langflix.utils.filename_utils.sanitize_for_expression_filename')
    def test_get_expression_filename_without_index(self, mock_sanitize, tmp_path):
        """Test expression filename without index."""
        mock_sanitize.return_value = "goodbye"
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        filename = resolver.get_expression_filename("goodbye")

        assert filename == "goodbye.mkv"

    @patch('langflix.utils.filename_utils.sanitize_for_expression_filename')
    def test_get_short_form_path(self, mock_sanitize, tmp_path):
        """Test short-form video path generation."""
        mock_sanitize.return_value = "hello"
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        short_form_path = resolver.get_short_form_path("hello", index=0)

        assert short_form_path == tmp_path / "korean" / "shorts" / "0_hello.mkv"

    @patch('langflix.utils.filename_utils.sanitize_for_expression_filename')
    def test_get_short_form_path_with_logo(self, mock_sanitize, tmp_path):
        """Test short-form video path with logo suffix."""
        mock_sanitize.return_value = "hello"
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        short_form_path = resolver.get_short_form_path("hello", index=0, with_logo=True)

        assert short_form_path == tmp_path / "korean" / "shorts" / "0_hello_with_logo.mkv"

    @patch('langflix.utils.filename_utils.sanitize_for_expression_filename')
    def test_get_long_form_path(self, mock_sanitize, tmp_path):
        """Test long-form video path generation."""
        mock_sanitize.return_value = "hello"
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        long_form_path = resolver.get_long_form_path("hello", index=0)

        assert long_form_path == output_dir / "0_hello.mkv"

    @patch('langflix.utils.filename_utils.sanitize_for_expression_filename')
    def test_get_long_form_path_with_logo(self, mock_sanitize, tmp_path):
        """Test long-form video path with logo suffix."""
        mock_sanitize.return_value = "hello"
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        long_form_path = resolver.get_long_form_path("hello", index=0, with_logo=True)

        assert long_form_path == output_dir / "0_hello_with_logo.mkv"

    def test_get_subtitle_path(self, tmp_path):
        """Test subtitle path generation."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        subtitle_path = resolver.get_subtitle_path("S01E01", "ko", "original")

        assert subtitle_path == tmp_path / "korean" / "subtitles" / "S01E01.ko.original.srt"

    def test_get_subtitle_path_without_language(self, tmp_path):
        """Test subtitle path without language code."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        subtitle_path = resolver.get_subtitle_path("S01E01")

        assert subtitle_path == tmp_path / "korean" / "subtitles" / "S01E01.srt"

    def test_get_temp_files(self, tmp_path):
        """Test finding temporary files."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        # Create some temp files
        (output_dir / "temp_clip1.mkv").touch()
        (output_dir / "temp_clip2.mkv").touch()
        (output_dir / "regular_file.mkv").touch()

        temp_files = resolver.get_temp_files("temp_*.mkv")

        assert len(temp_files) == 2
        assert output_dir / "temp_clip1.mkv" in temp_files
        assert output_dir / "temp_clip2.mkv" in temp_files
        assert output_dir / "regular_file.mkv" not in temp_files

    def test_get_temp_files_empty_directory(self, tmp_path):
        """Test finding temp files in empty directory."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        temp_files = resolver.get_temp_files()

        assert temp_files == []

    def test_get_temp_files_nonexistent_directory(self, tmp_path):
        """Test finding temp files when directory doesn't exist."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir, create_dirs=False)

        temp_files = resolver.get_temp_files()

        assert temp_files == []

    def test_cleanup_temp_files(self, tmp_path):
        """Test cleaning up temporary files."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        # Create temp files
        (output_dir / "temp_clip1.mkv").touch()
        (output_dir / "temp_clip2.mkv").touch()
        (output_dir / "temp_audio.wav").touch()
        (output_dir / "regular_file.mkv").touch()

        cleaned_count = resolver.cleanup_temp_files()

        assert cleaned_count == 3
        assert not (output_dir / "temp_clip1.mkv").exists()
        assert not (output_dir / "temp_clip2.mkv").exists()
        assert not (output_dir / "temp_audio.wav").exists()
        assert (output_dir / "regular_file.mkv").exists()

    def test_cleanup_temp_files_dry_run(self, tmp_path):
        """Test cleanup dry run (no deletion)."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        # Create temp files
        (output_dir / "temp_clip1.mkv").touch()
        (output_dir / "temp_clip2.mkv").touch()

        cleaned_count = resolver.cleanup_temp_files(dry_run=True)

        assert cleaned_count == 2
        assert (output_dir / "temp_clip1.mkv").exists()
        assert (output_dir / "temp_clip2.mkv").exists()

    def test_cleanup_temp_files_custom_patterns(self, tmp_path):
        """Test cleanup with custom patterns."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        # Create different temp files
        (output_dir / "temp_clip.mkv").touch()
        (output_dir / "temp_audio.wav").touch()
        (output_dir / "debug_info.txt").touch()

        cleaned_count = resolver.cleanup_temp_files(patterns=["temp_*.mkv"])

        assert cleaned_count == 1
        assert not (output_dir / "temp_clip.mkv").exists()
        assert (output_dir / "temp_audio.wav").exists()
        assert (output_dir / "debug_info.txt").exists()

    def test_validate_structure(self, tmp_path):
        """Test directory structure validation."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        # Trigger directory creation
        _ = resolver.get_shorts_dir()
        _ = resolver.get_expressions_dir()
        _ = resolver.get_subtitles_dir()
        _ = resolver.get_videos_dir()

        validation = resolver.validate_structure()

        assert validation["output_dir"] is True
        assert validation["language_dir"] is True
        assert validation["shorts_dir"] is True
        assert validation["expressions_dir"] is True
        assert validation["subtitles_dir"] is True
        assert validation["videos_dir"] is True

    def test_validate_structure_missing_dirs(self, tmp_path):
        """Test validation when directories are missing."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir, create_dirs=False)

        validation = resolver.validate_structure()

        assert validation["output_dir"] is False
        assert validation["shorts_dir"] is False

    def test_repr(self, tmp_path):
        """Test string representation."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        repr_str = repr(resolver)

        assert "PathResolver" in repr_str
        assert str(output_dir) in repr_str
        assert str(tmp_path / "korean") in repr_str


class TestPathResolverIntegration:
    """Integration tests for PathResolver."""

    def test_complete_directory_structure(self, tmp_path):
        """Test creating complete directory structure."""
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        # Create all directories
        shorts_dir = resolver.get_shorts_dir()
        expressions_dir = resolver.get_expressions_dir()
        subtitles_dir = resolver.get_subtitles_dir()
        tts_audio_dir = resolver.get_tts_audio_dir()
        videos_dir = resolver.get_videos_dir()

        # Verify structure
        assert output_dir.exists()
        assert shorts_dir.exists()
        assert expressions_dir.exists()
        assert subtitles_dir.exists()
        assert tts_audio_dir.exists()
        assert videos_dir.exists()

        # All under same language directory
        assert shorts_dir.parent == output_dir.parent
        assert expressions_dir.parent == output_dir.parent
        assert subtitles_dir.parent == output_dir.parent

    @patch('langflix.utils.filename_utils.sanitize_for_expression_filename')
    def test_expression_workflow(self, mock_sanitize, tmp_path):
        """Test typical expression processing workflow."""
        mock_sanitize.return_value = "hello"
        output_dir = tmp_path / "korean" / "long_form_videos"
        resolver = PathResolver(output_dir=output_dir)

        # Create long-form video path
        long_form_path = resolver.get_long_form_path("hello", index=0)

        # Create short-form video path
        short_form_path = resolver.get_short_form_path("hello", index=0)

        # Create temp paths for processing
        context_clip = resolver.get_temp_path("context_clip", "hello")
        expr_clip = resolver.get_temp_path("expr_clip", "hello")

        # Verify all paths use correct directories
        assert long_form_path.parent == output_dir
        assert short_form_path.parent == tmp_path / "korean" / "shorts"
        assert context_clip.parent == output_dir
        assert expr_clip.parent == output_dir

        # All filenames contain expression identifier
        assert "hello" in long_form_path.name
        assert "hello" in short_form_path.name
        assert "hello" in context_clip.name
        assert "hello" in expr_clip.name
