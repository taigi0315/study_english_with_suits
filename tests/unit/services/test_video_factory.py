import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from langflix.services.video_factory import VideoFactory
from langflix.core.models import ExpressionAnalysis

class TestVideoFactory:
    
    @pytest.fixture
    def factory(self):
        return VideoFactory()
        
    @pytest.fixture
    def mock_video_editor(self):
        with patch('langflix.services.video_factory.VideoEditor') as mock:
            yield mock
            
    @pytest.fixture
    def mock_dependencies(self):
        return {
            'video_processor': MagicMock(),
            'subtitle_processor': MagicMock(),
        }

    def test_create_educational_videos_extracts_slices(self, factory, mock_dependencies, mock_video_editor):
        # Setup
        expr = ExpressionAnalysis(
            expression="Test", 
            expression_translation="T", 
            expression_dialogue="D", 
            expression_dialogue_translation="DT", 
            context_start_time="00:00:00.000", 
            context_end_time="00:00:10.000", 
            meaning="M", grammar_point="G", 
            similar_expressions=["S1"], 
            example_sentence="E", 
            example_sentence_translation="ET",
            dialogues=["D"],
            translation=["DT"]
        )
        
        mock_dependencies['video_processor'].find_video_file.return_value = Path("orig.mkv")
        mock_dependencies['video_processor'].extract_clip.return_value = True
        
        # Run
        with patch('langflix.services.video_factory.get_temp_manager') as mock_tm:
             mock_tm.return_value.create_temp_file.return_value.__enter__.return_value = Path("slice.mkv")
             
             factory.create_educational_videos(
                expressions=[expr],
                translated_expressions={'ko': [expr]},
                target_languages=['ko'],
                paths={'languages': {'ko': {'final_videos': Path('/tmp/fv')}}},
                video_processor=mock_dependencies['video_processor'],
                subtitle_processor=mock_dependencies['subtitle_processor'],
                output_dir=Path('/tmp'),
                episode_name='Ep1',
                subtitle_file=Path('sub.srt')
             )
             
        # Verify slice extraction
        mock_dependencies['video_processor'].extract_clip.assert_called_once()
        
        # Verify editor creation and video generation
        mock_video_editor.assert_called()
        mock_video_editor.return_value.create_long_form_video.assert_called_once()
        
