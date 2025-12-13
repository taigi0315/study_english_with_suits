"""
Unit tests for langflix.core.dual_subtitle module.
Tests V2 dual-language subtitle models and service.
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from langflix.core.dual_subtitle import (
    SubtitleEntry,
    AlignedSubtitlePair,
    DualSubtitle,
    DualSubtitleService,
    get_dual_subtitle_service,
)


class TestSubtitleEntry:
    """Tests for SubtitleEntry model."""
    
    def test_create_entry(self):
        """Should create subtitle entry with all fields."""
        entry = SubtitleEntry(
            index=1,
            start_time="00:01:30,500",
            end_time="00:01:35,000",
            text="Hello, world!"
        )
        
        assert entry.index == 1
        assert entry.start_time == "00:01:30,500"
        assert entry.text == "Hello, world!"
    
    def test_time_to_seconds(self):
        """Should convert timestamp to seconds."""
        entry = SubtitleEntry(
            index=1,
            start_time="00:01:30,500",
            end_time="00:02:00,000",
            text="Test"
        )
        
        assert entry.start_seconds == 90.5  # 1*60 + 30.5
        assert entry.end_seconds == 120.0   # 2*60
    
    def test_time_with_period_separator(self):
        """Should handle period separator in timestamp."""
        entry = SubtitleEntry(
            index=1,
            start_time="00:00:10.500",
            end_time="00:00:15.000",
            text="Test"
        )
        
        assert entry.start_seconds == 10.5


class TestAlignedSubtitlePair:
    """Tests for AlignedSubtitlePair model."""
    
    def test_create_pair(self):
        """Should create aligned pair from source and target."""
        source = SubtitleEntry(
            index=1,
            start_time="00:00:01,000",
            end_time="00:00:03,000",
            text="Hello!"
        )
        target = SubtitleEntry(
            index=1,
            start_time="00:00:01,000",
            end_time="00:00:03,000",
            text="안녕하세요!"
        )
        
        pair = AlignedSubtitlePair(source=source, target=target)
        
        assert pair.source_text == "Hello!"
        assert pair.target_text == "안녕하세요!"


class TestDualSubtitle:
    """Tests for DualSubtitle model."""
    
    @pytest.fixture
    def sample_dual_subtitle(self):
        """Create sample dual subtitle for testing."""
        source_entries = [
            SubtitleEntry(index=1, start_time="00:00:01,000", end_time="00:00:03,000", text="Hello!"),
            SubtitleEntry(index=2, start_time="00:00:04,000", end_time="00:00:06,000", text="How are you?"),
            SubtitleEntry(index=3, start_time="00:00:10,000", end_time="00:00:12,000", text="Goodbye!"),
        ]
        target_entries = [
            SubtitleEntry(index=1, start_time="00:00:01,000", end_time="00:00:03,000", text="안녕!"),
            SubtitleEntry(index=2, start_time="00:00:04,000", end_time="00:00:06,000", text="어떻게 지내?"),
            SubtitleEntry(index=3, start_time="00:00:10,000", end_time="00:00:12,000", text="안녕히 가세요!"),
        ]
        
        return DualSubtitle(
            source_language="English",
            target_language="Korean",
            source_entries=source_entries,
            target_entries=target_entries,
        )
    
    def test_counts(self, sample_dual_subtitle):
        """Should return correct counts."""
        assert sample_dual_subtitle.source_count == 3
        assert sample_dual_subtitle.target_count == 3
    
    def test_is_aligned(self, sample_dual_subtitle):
        """Should detect aligned subtitles."""
        assert sample_dual_subtitle.is_aligned is True
        
        # Test misaligned
        sample_dual_subtitle.source_entries.append(
            SubtitleEntry(index=4, start_time="00:00:15,000", end_time="00:00:17,000", text="Extra")
        )
        assert sample_dual_subtitle.is_aligned is False
    
    def test_get_aligned_pair(self, sample_dual_subtitle):
        """Should get aligned pair by index."""
        pair = sample_dual_subtitle.get_aligned_pair(0)
        
        assert pair is not None
        assert pair.source_text == "Hello!"
        assert pair.target_text == "안녕!"
    
    def test_get_aligned_pair_out_of_range(self, sample_dual_subtitle):
        """Should return None for out of range index."""
        assert sample_dual_subtitle.get_aligned_pair(100) is None
        assert sample_dual_subtitle.get_aligned_pair(-1) is None
    
    def test_get_pairs_in_range(self, sample_dual_subtitle):
        """Should get pairs within time range."""
        # Get pairs between 0 and 8 seconds (should include first 2)
        pairs = sample_dual_subtitle.get_pairs_in_range(0, 8)
        
        assert len(pairs) == 2
        assert pairs[0].source_text == "Hello!"
        assert pairs[1].source_text == "How are you?"
    
    def test_to_dialogue_format(self, sample_dual_subtitle):
        """Should convert to dialogue format."""
        source_dialogues, target_dialogues = sample_dual_subtitle.to_dialogue_format()
        
        assert len(source_dialogues) == 3
        assert len(target_dialogues) == 3
        
        assert source_dialogues[0]["text"] == "Hello!"
        assert source_dialogues[0]["index"] == 0
        assert target_dialogues[0]["text"] == "안녕!"


class TestDualSubtitleService:
    """Tests for DualSubtitleService."""
    
    def test_discover_languages(self, tmp_path):
        """Should discover available languages."""
        # Setup
        media_file = tmp_path / "show.mp4"
        media_file.touch()
        subtitle_folder = tmp_path / "show"
        subtitle_folder.mkdir()
        
        (subtitle_folder / "3_Korean.srt").write_text("1\n00:00:01,000 --> 00:00:02,000\n안녕\n")
        (subtitle_folder / "6_English.srt").write_text("1\n00:00:01,000 --> 00:00:02,000\nHello\n")
        
        service = DualSubtitleService()
        languages = service.discover_languages(str(media_file))
        
        assert "Korean" in languages
        assert "English" in languages
    
    def test_load_dual_subtitles_validation_error(self, tmp_path):
        """Should raise error for same language."""
        media_file = tmp_path / "show.mp4"
        media_file.touch()
        
        service = DualSubtitleService()
        
        with pytest.raises(ValueError, match="different"):
            service.load_dual_subtitles(str(media_file), "English", "English")


class TestGetDualSubtitleService:
    """Tests for singleton service getter."""
    
    def test_returns_service(self):
        """Should return DualSubtitleService instance."""
        service = get_dual_subtitle_service()
        assert isinstance(service, DualSubtitleService)
    
    def test_returns_same_instance(self):
        """Should return same singleton instance."""
        service1 = get_dual_subtitle_service()
        service2 = get_dual_subtitle_service()
        assert service1 is service2
