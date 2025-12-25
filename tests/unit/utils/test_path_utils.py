"""
Unit tests for langflix.utils.path_utils module.
Tests dual-language subtitle file structure utilities.
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from langflix.utils.path_utils import (
    parse_subtitle_filename,
    get_subtitle_folder,
    discover_subtitle_languages,
    get_available_language_names,
    get_subtitle_file,
    find_media_subtitle_pairs,
    validate_dual_subtitle_availability,
)


class TestParseSubtitleFilename:
    """Tests for parse_subtitle_filename function."""
    
    def test_valid_filename(self):
        """Should parse valid subtitle filenames correctly."""
        assert parse_subtitle_filename("3_Korean.srt") == (3, "Korean")
        assert parse_subtitle_filename("6_English.srt") == (6, "English")
        assert parse_subtitle_filename("13_Spanish.srt") == (13, "Spanish")
        assert parse_subtitle_filename("100_Japanese.srt") == (100, "Japanese")
    
    def test_invalid_filename_no_match(self):
        """Should return None for invalid patterns."""
        assert parse_subtitle_filename("Korean.srt") is None
        assert parse_subtitle_filename("3-Korean.srt") is None
        assert parse_subtitle_filename("3_Korean.txt") is None
        assert parse_subtitle_filename("English.srt") is None
    
    def test_edge_cases(self):
        """Should handle edge cases."""
        assert parse_subtitle_filename("") is None
        assert parse_subtitle_filename("0_Test.srt") == (0, "Test")


class TestGetSubtitleFolder:
    """Tests for get_subtitle_folder function."""
    
    def test_existing_folder(self, tmp_path):
        """Should return folder path when it exists (Netflix Subs/ structure)."""
        # Create media file and subtitle folder in Netflix structure
        media_file = tmp_path / "show.mp4"
        media_file.touch()
        subs_dir = tmp_path / "Subs"
        subs_dir.mkdir()
        subtitle_folder = subs_dir / "show"
        subtitle_folder.mkdir()
        # Add at least one .srt file so the folder is recognized
        (subtitle_folder / "test.srt").touch()

        result = get_subtitle_folder(str(media_file))
        assert result == subtitle_folder
    
    def test_missing_folder(self, tmp_path):
        """Should return None when subtitle folder doesn't exist."""
        media_file = tmp_path / "show.mp4"
        media_file.touch()
        
        result = get_subtitle_folder(str(media_file))
        assert result is None
    
    def test_missing_media_file(self, tmp_path):
        """Should return None when media file doesn't exist."""
        result = get_subtitle_folder(str(tmp_path / "nonexistent.mp4"))
        assert result is None


class TestDiscoverSubtitleLanguages:
    """Tests for discover_subtitle_languages function."""
    
    def test_discover_languages(self, tmp_path):
        """Should discover all available languages."""
        # Setup
        media_file = tmp_path / "show.mp4"
        media_file.touch()
        subtitle_folder = tmp_path / "show"
        subtitle_folder.mkdir()
        
        # Create subtitle files
        (subtitle_folder / "3_Korean.srt").touch()
        (subtitle_folder / "4_Korean.srt").touch()
        (subtitle_folder / "6_English.srt").touch()
        (subtitle_folder / "13_Spanish.srt").touch()
        
        result = discover_subtitle_languages(str(media_file))
        
        assert "Korean" in result
        assert "English" in result
        assert "Spanish" in result
        assert len(result["Korean"]) == 2  # Two Korean variants
        assert len(result["English"]) == 1
    
    def test_empty_folder(self, tmp_path):
        """Should return empty dict for folder with no subtitles."""
        media_file = tmp_path / "show.mp4"
        media_file.touch()
        subtitle_folder = tmp_path / "show"
        subtitle_folder.mkdir()
        
        result = discover_subtitle_languages(str(media_file))
        assert result == {}
    
    def test_no_subtitle_folder(self, tmp_path):
        """Should return empty dict when no subtitle folder exists."""
        media_file = tmp_path / "show.mp4"
        media_file.touch()
        
        result = discover_subtitle_languages(str(media_file))
        assert result == {}


class TestGetAvailableLanguageNames:
    """Tests for get_available_language_names function."""
    
    def test_returns_sorted_list(self, tmp_path):
        """Should return sorted list of language names."""
        media_file = tmp_path / "show.mp4"
        media_file.touch()
        subtitle_folder = tmp_path / "show"
        subtitle_folder.mkdir()
        
        (subtitle_folder / "3_Korean.srt").touch()
        (subtitle_folder / "6_English.srt").touch()
        (subtitle_folder / "13_Spanish.srt").touch()
        
        result = get_available_language_names(str(media_file))
        
        assert result == ["English", "Korean", "Spanish"]


class TestGetSubtitleFile:
    """Tests for get_subtitle_file function."""
    
    def test_get_first_variant(self, tmp_path):
        """Should return first variant by default."""
        media_file = tmp_path / "show.mp4"
        media_file.touch()
        subtitle_folder = tmp_path / "show"
        subtitle_folder.mkdir()
        
        (subtitle_folder / "3_Korean.srt").touch()
        (subtitle_folder / "4_Korean.srt").touch()
        
        result = get_subtitle_file(str(media_file), "Korean")
        assert "3_Korean.srt" in result
    
    def test_get_specific_variant(self, tmp_path):
        """Should return specified variant."""
        media_file = tmp_path / "show.mp4"
        media_file.touch()
        subtitle_folder = tmp_path / "show"
        subtitle_folder.mkdir()
        
        (subtitle_folder / "3_Korean.srt").touch()
        (subtitle_folder / "4_Korean.srt").touch()
        
        result = get_subtitle_file(str(media_file), "Korean", variant_index=1)
        assert "4_Korean.srt" in result
    
    def test_language_not_found(self, tmp_path):
        """Should return None for unavailable language."""
        media_file = tmp_path / "show.mp4"
        media_file.touch()
        subtitle_folder = tmp_path / "show"
        subtitle_folder.mkdir()
        
        (subtitle_folder / "3_Korean.srt").touch()
        
        result = get_subtitle_file(str(media_file), "Klingon")
        assert result is None


class TestFindMediaSubtitlePairs:
    """Tests for find_media_subtitle_pairs function."""
    
    def test_find_pairs(self, tmp_path):
        """Should find all media-subtitle pairs."""
        # Create first pair
        (tmp_path / "show1.mp4").touch()
        show1_folder = tmp_path / "show1"
        show1_folder.mkdir()
        (show1_folder / "3_Korean.srt").touch()
        
        # Create second pair
        (tmp_path / "show2.mkv").touch()
        show2_folder = tmp_path / "show2"
        show2_folder.mkdir()
        (show2_folder / "6_English.srt").touch()
        
        # Create media without subtitles (should be excluded)
        (tmp_path / "show3.mp4").touch()
        
        result = find_media_subtitle_pairs(str(tmp_path))
        
        assert len(result) == 2
        media_names = {p[0].name for p in result}
        assert "show1.mp4" in media_names
        assert "show2.mkv" in media_names


class TestValidateDualSubtitleAvailability:
    """Tests for validate_dual_subtitle_availability function."""
    
    def test_valid_pair(self, tmp_path):
        """Should return valid for available language pair."""
        media_file = tmp_path / "show.mp4"
        media_file.touch()
        subtitle_folder = tmp_path / "show"
        subtitle_folder.mkdir()
        
        (subtitle_folder / "3_Korean.srt").touch()
        (subtitle_folder / "6_English.srt").touch()
        
        is_valid, error = validate_dual_subtitle_availability(
            str(media_file), "English", "Korean"
        )
        
        assert is_valid is True
        assert error is None
    
    def test_same_language_error(self, tmp_path):
        """Should error when source equals target."""
        media_file = tmp_path / "show.mp4"
        media_file.touch()
        
        is_valid, error = validate_dual_subtitle_availability(
            str(media_file), "English", "English"
        )
        
        assert is_valid is False
        assert "different" in error.lower()
    
    def test_missing_language(self, tmp_path):
        """Should error when a language is missing."""
        media_file = tmp_path / "show.mp4"
        media_file.touch()
        subtitle_folder = tmp_path / "show"
        subtitle_folder.mkdir()
        
        (subtitle_folder / "3_Korean.srt").touch()
        
        is_valid, error = validate_dual_subtitle_availability(
            str(media_file), "English", "Korean"
        )
        
        assert is_valid is False
        assert "English" in error
