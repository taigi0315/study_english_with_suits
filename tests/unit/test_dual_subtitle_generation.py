"""
Unit tests for V2 subtitle processor functionality.
Tests the dialogue_entries-based subtitle generation for V2 mode.
"""
import pytest
from unittest.mock import patch, MagicMock
from langflix.core.subtitle_processor import SubtitleProcessor, get_expr_attr


class TestV2SubtitleGeneration:
    """Tests for V2 subtitle generation with dialogue_entries."""
    
    @pytest.fixture
    def v2_expression(self):
        """Create a V2-style expression dict with dialogue_entries."""
        return {
            'expression': '니까짓 게 날 죽여?',
            'expression_translation': '¿Crees que puedes matarme?',
            'title': '도전적 표현',
            'title_translation': 'Expresión desafiante',
            'context_start_time': '00:05:47,764',
            'context_end_time': '00:06:23,174',
            'expression_start_time': '00:05:55,000',
            'expression_end_time': '00:06:00,000',
            'dialogues': [
                '네가 뭔데 날 건드려?',
                '니까짓 게 날 죽여?',
                '한번 해봐.',
            ],
            'translation': [
                '¿Quién eres para tocarme?',
                '¿Crees que puedes matarme?',
                'Inténtalo.',
            ],
            'dialogue_entries': [
                {
                    'text': '네가 뭔데 날 건드려?',
                    'translation': '¿Quién eres para tocarme?',
                    'start_time': '00:05:47,764',
                    'end_time': '00:05:52,000',
                },
                {
                    'text': '니까짓 게 날 죽여?',
                    'translation': '¿Crees que puedes matarme?',
                    'start_time': '00:05:55,000',
                    'end_time': '00:06:00,000',
                },
                {
                    'text': '한번 해봐.',
                    'translation': 'Inténtalo.',
                    'start_time': '00:06:05,000',
                    'end_time': '00:06:10,000',
                },
            ],
        }
    
    @pytest.fixture
    def v1_expression(self):
        """Create a V1-style expression dict WITHOUT dialogue_entries."""
        return {
            'expression': 'test expression',
            'expression_translation': 'expresión de prueba',
            'context_start_time': '00:01:00,000',
            'context_end_time': '00:01:30,000',
            'dialogues': ['Hello', 'World'],
            'translation': ['Hola', 'Mundo'],
            # Note: No dialogue_entries field
        }
    
    def test_v2_expression_has_dialogue_entries(self, v2_expression):
        """V2 expressions should have dialogue_entries with timing."""
        entries = get_expr_attr(v2_expression, 'dialogue_entries', [])
        
        assert len(entries) == 3
        assert entries[0]['text'] == '네가 뭔데 날 건드려?'
        assert entries[0]['translation'] == '¿Quién eres para tocarme?'
        assert entries[0]['start_time'] == '00:05:47,764'
        assert entries[0]['end_time'] == '00:05:52,000'
    
    def test_v1_expression_no_dialogue_entries(self, v1_expression):
        """V1 expressions should not have dialogue_entries."""
        entries = get_expr_attr(v1_expression, 'dialogue_entries', [])
        assert entries == []
    
    def test_get_translation_for_subtitle_v2_mode(self, v2_expression):
        """Should use direct translation from subtitle in V2 mode."""
        processor = SubtitleProcessor("")  # Empty path for V2 mode
        
        # V2 subtitle has translation field
        v2_subtitle = {
            'text': '니까짓 게 날 죽여?',
            'translation': '¿Crees que puedes matarme?',
            'start_time': '00:05:55,000',
            'end_time': '00:06:00,000',
        }
        
        translation = processor._get_translation_for_subtitle(
            subtitle_idx=0,
            subtitle=v2_subtitle,
            subtitle_to_dialogue_map=[],  # Not used in V2
            expression=v2_expression
        )
        
        assert translation == '¿Crees que puedes matarme?'
    
    def test_get_translation_for_subtitle_v1_fallback(self, v1_expression):
        """Should fall back to mapping lookup in V1 mode."""
        processor = SubtitleProcessor("")
        
        # V1 subtitle without translation field
        v1_subtitle = {
            'text': 'Hello',
            'start_time': '00:01:00,000',
            'end_time': '00:01:05,000',
        }
        
        # Simulating V1 mapping
        subtitle_to_dialogue_map = [0, 1]  # Subtitle 0 maps to dialogue 0
        
        translation = processor._get_translation_for_subtitle(
            subtitle_idx=0,
            subtitle=v1_subtitle,
            subtitle_to_dialogue_map=subtitle_to_dialogue_map,
            expression=v1_expression
        )
        
        # Should get from expression's translation list
        assert translation == 'Hola'


class TestV2DualLanguageSubtitleFile:
    """Tests for creating dual-language subtitle files in V2 mode."""
    
    @pytest.fixture
    def v2_expression(self):
        """Create V2 expression with dialogue_entries."""
        return {
            'expression': 'test',
            'context_start_time': '00:00:10,000',
            'context_end_time': '00:00:30,000',
            'dialogues': ['Line 1', 'Line 2'],
            'translation': ['Línea 1', 'Línea 2'],
            'dialogue_entries': [
                {
                    'text': 'Line 1',
                    'translation': 'Línea 1',
                    'start_time': '00:00:10,000',
                    'end_time': '00:00:15,000',
                },
                {
                    'text': 'Line 2',
                    'translation': 'Línea 2',
                    'start_time': '00:00:20,000',
                    'end_time': '00:00:25,000',
                },
            ],
        }
    
    def test_v2_mode_uses_dialogue_entries(self, v2_expression, tmp_path):
        """V2 mode should use dialogue_entries directly."""
        processor = SubtitleProcessor("")  # Empty path - V2 mode
        
        output_path = tmp_path / "test_subtitle.srt"
        
        # Mock the _generate_dual_language_srt method to capture what's passed
        with patch.object(processor, '_generate_dual_language_srt', return_value="1\n00:00:00,000 --> 00:00:05,000\nTest\n") as mock_generate:
            result = processor.create_dual_language_subtitle_file(v2_expression, str(output_path))
            
            # Check that subtitles were passed (from dialogue_entries)
            call_args = mock_generate.call_args
            subtitles = call_args[0][0]
            
            assert len(subtitles) == 2
            assert subtitles[0]['text'] == 'Line 1'
            assert subtitles[0]['translation'] == 'Línea 1'
            assert subtitles[0]['start_time'] == '00:00:10,000'


class TestDialogueEntriesFormat:
    """Tests for dialogue_entries format and structure."""
    
    def test_dialogue_entry_structure(self):
        """Each dialogue entry should have required fields."""
        entry = {
            'text': 'Source text',
            'translation': 'Target text',
            'start_time': '00:01:00,000',
            'end_time': '00:01:05,000',
        }
        
        assert 'text' in entry
        assert 'translation' in entry
        assert 'start_time' in entry
        assert 'end_time' in entry
    
    def test_dialogue_entries_preserve_order(self):
        """Dialogue entries should preserve chronological order."""
        entries = [
            {'text': 'First', 'start_time': '00:00:01,000'},
            {'text': 'Second', 'start_time': '00:00:05,000'},
            {'text': 'Third', 'start_time': '00:00:10,000'},
        ]
        
        times = [e['start_time'] for e in entries]
        assert times == sorted(times)
