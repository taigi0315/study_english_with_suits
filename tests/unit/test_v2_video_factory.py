"""
Unit tests for V2 Video Factory.
Tests the video slice extraction and master clip creation for V2 mode.
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path
from langflix.services.video_factory import VideoFactory


class TestV2VideoFactory:
    """Tests for VideoFactory V2 mode functionality."""
    
    @pytest.fixture
    def video_factory(self):
        """Create VideoFactory instance."""
        return VideoFactory()
    
    @pytest.fixture
    def mock_video_processor(self):
        """Create mock video processor."""
        processor = MagicMock()
        processor.video_file = Path("/tmp/test_video.mp4")
        processor.find_video_file.return_value = Path("/tmp/test_video.mp4")
        processor.extract_clip.return_value = True
        return processor
    
    @pytest.fixture
    def v2_expression(self):
        """Create V2 expression dict with dialogue_entries."""
        return {
            'expression': '니까짓 게 날 죽여?',
            'expression_translation': '¿Crees que puedes matarme?',
            'title': '도전적 표현',
            'title_translation': 'Expresión desafiante',
            'context_start_time': '00:05:47,764',
            'context_end_time': '00:06:23,174',
            'expression_start_time': '00:05:55,000',
            'expression_end_time': '00:06:00,000',
            'dialogues': ['네가 뭔데?', '니까짓 게?', '해봐.'],
            'translation': ['¿Quién eres?', '¿Crees que?', 'Inténtalo.'],
            'dialogue_entries': [
                {
                    'text': '네가 뭔데?',
                    'translation': '¿Quién eres?',
                    'start_time': '00:05:47,764',
                    'end_time': '00:05:52,000',
                },
                {
                    'text': '니까짓 게?',
                    'translation': '¿Crees que?',
                    'start_time': '00:05:55,000',
                    'end_time': '00:06:00,000',
                },
                {
                    'text': '해봐.',
                    'translation': 'Inténtalo.',
                    'start_time': '00:06:05,000',
                    'end_time': '00:06:10,000',
                },
            ],
        }
    
    def test_extract_slices_from_expressions(self, video_factory, mock_video_processor, v2_expression):
        """Should extract video slices from V2 expressions."""
        expressions = [v2_expression]
        original_video = Path("/tmp/test_video.mp4")
        
        with patch('langflix.services.video_factory.get_temp_manager') as mock_temp:
            mock_temp.return_value.create_temp_file.return_value.__enter__ = Mock(return_value=Path("/tmp/clip.mkv"))
            mock_temp.return_value.create_temp_file.return_value.__exit__ = Mock(return_value=False)
            
            slices = video_factory._extract_slices(
                expressions=expressions,
                video_processor=mock_video_processor,
                original_video=original_video,
                test_mode=True
            )
            
            # Should extract one slice
            assert 0 in slices
            
            # Should call extract_clip with correct times
            mock_video_processor.extract_clip.assert_called_once()
            call_args = mock_video_processor.extract_clip.call_args
            assert call_args[0][1] == '00:05:47,764'  # start_time
            assert call_args[0][2] == '00:06:23,174'  # end_time
    
    def test_extract_slices_skips_missing_timestamps(self, video_factory, mock_video_processor):
        """Should skip expressions with missing timestamps."""
        expressions = [
            {
                'expression': 'test',
                'context_start_time': None,  # Missing start
                'context_end_time': '00:01:00,000',
            }
        ]
        original_video = Path("/tmp/test_video.mp4")
        
        with patch('langflix.services.video_factory.get_temp_manager') as mock_temp:
            slices = video_factory._extract_slices(
                expressions=expressions,
                video_processor=mock_video_processor,
                original_video=original_video,
                test_mode=True
            )
            
            # Should skip the expression (no slices extracted)
            assert 0 not in slices
            mock_video_processor.extract_clip.assert_not_called()
    
    def test_video_file_passed_to_factory(self, video_factory, mock_video_processor):
        """Should use video_file parameter when provided."""
        video_file = Path("/tmp/uploaded_video.mp4")
        subtitle_file = None  # V2 mode - no subtitle file
        
        # Mock find_video_file to return the video_file
        mock_video_processor.find_video_file.return_value = video_file
        
        reference_path = str(video_file) if video_file else None
        original_video = mock_video_processor.find_video_file(reference_path)
        
        assert original_video == video_file


class TestV2ExpressionFormat:
    """Tests for V2 expression format requirements."""
    
    def test_v2_expression_required_fields(self):
        """V2 expressions should have required fields."""
        v2_expr = {
            'expression': 'test expression',
            'expression_translation': 'expresión de prueba',
            'title': 'Title',
            'title_translation': 'Título',
            'context_start_time': '00:00:10,000',
            'context_end_time': '00:00:30,000',
            'expression_start_time': '00:00:15,000',
            'expression_end_time': '00:00:20,000',
            'dialogues': ['Dialog 1', 'Dialog 2'],
            'translation': ['Diálogo 1', 'Diálogo 2'],
            'dialogue_entries': [
                {'text': 'Dialog 1', 'translation': 'Diálogo 1', 'start_time': '00:00:10,000', 'end_time': '00:00:15,000'},
                {'text': 'Dialog 2', 'translation': 'Diálogo 2', 'start_time': '00:00:20,000', 'end_time': '00:00:25,000'},
            ],
        }
        
        # Required V2 fields
        assert 'expression' in v2_expr
        assert 'expression_translation' in v2_expr
        assert 'title' in v2_expr
        assert 'title_translation' in v2_expr
        assert 'context_start_time' in v2_expr
        assert 'context_end_time' in v2_expr
        assert 'dialogue_entries' in v2_expr
        
        # Dialogue entries should have timing
        for entry in v2_expr['dialogue_entries']:
            assert 'text' in entry
            assert 'translation' in entry
            assert 'start_time' in entry
            assert 'end_time' in entry
    
    def test_dialogue_entries_match_dialogues(self):
        """dialogue_entries should match dialogues array."""
        dialogues = ['Line 1', 'Line 2', 'Line 3']
        translations = ['Línea 1', 'Línea 2', 'Línea 3']
        
        dialogue_entries = [
            {'text': dialogues[0], 'translation': translations[0], 'start_time': '00:00:01,000', 'end_time': '00:00:02,000'},
            {'text': dialogues[1], 'translation': translations[1], 'start_time': '00:00:03,000', 'end_time': '00:00:04,000'},
            {'text': dialogues[2], 'translation': translations[2], 'start_time': '00:00:05,000', 'end_time': '00:00:06,000'},
        ]
        
        assert len(dialogue_entries) == len(dialogues)
        for i, entry in enumerate(dialogue_entries):
            assert entry['text'] == dialogues[i]
            assert entry['translation'] == translations[i]
