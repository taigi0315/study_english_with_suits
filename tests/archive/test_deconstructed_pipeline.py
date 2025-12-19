import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from langflix.main import LangFlixPipeline
from langflix.services.subtitle_service import SubtitleService
from langflix.services.expression_service import ExpressionService
from langflix.services.translation_service import TranslationService
from langflix.services.video_factory import VideoFactory
from langflix.services.upload_service import UploadService

class TestLangFlixPipeline:
    
    @pytest.fixture
    def mock_services(self):
        with patch('langflix.main.SubtitleService', autospec=True) as sub_mock, \
             patch('langflix.main.ExpressionService', autospec=True) as expr_mock, \
             patch('langflix.main.TranslationService', autospec=True) as trans_mock, \
             patch('langflix.main.VideoFactory', autospec=True) as vf_mock, \
             patch('langflix.main.UploadService', autospec=True) as up_mock, \
             patch('langflix.main.VideoProcessor', autospec=True) as vp_mock, \
             patch('langflix.main.SubtitleProcessor', autospec=True) as sp_mock, \
             patch('langflix.main.create_output_structure') as cos_mock, \
             patch('langflix.main.OutputManager') as om_mock:
            
            # Setup return values for create_output_structure
            cos_mock.return_value = {
                'series_name': 'TestShow',
                'episode_name': 'TestEp',
                'episode': {'metadata': {'llm_outputs': Path('/tmp/llm_out')}},
                'languages': {}
            }
            
            # Setup OutputManager mock
            om = om_mock.return_value
            om.create_language_structure.return_value = {'language_dir': Path('/tmp/lang')}

            yield {
                'subtitle': sub_mock.return_value,
                'expression': expr_mock.return_value,
                'translation': trans_mock.return_value,
                'video_factory': vf_mock.return_value,
                'upload': up_mock.return_value,
                'video_processor': vp_mock.return_value,
                'subtitle_processor': sp_mock.return_value,
                'cos': cos_mock
            }

    def test_pipeline_initialization(self, mock_services):
        pipeline = LangFlixPipeline(
            subtitle_file="test.srt",
            video_dir="videos",
            output_dir="output",
            language_code="ko"
        )
        
        assert pipeline.subtitle_service == mock_services['subtitle']
        assert pipeline.expression_service == mock_services['expression']
        assert pipeline.translation_service == mock_services['translation']
        assert pipeline.video_factory == mock_services['video_factory']
        assert pipeline.upload_service == mock_services['upload']
        
        mock_services['cos'].assert_called_once()


    def test_pipeline_run_flow(self, mock_services):
        pipeline = LangFlixPipeline(
            subtitle_file="test.srt",
            video_dir="videos",
            output_dir="output",
            language_code="ko"
        )
        
        # Mock behaviors
        mock_services['subtitle'].parse.return_value = [{'text': 'foo'}]
        mock_services['subtitle'].chunk.return_value = ([{'text': 'foo'}])
        
        mock_expr = MagicMock()
        mock_services['expression'].analyze.return_value = [mock_expr]
        
        mock_services['translation'].translate.return_value = {'ko': [mock_expr]}
        
        # Run
        result = pipeline.run(max_expressions=5, schedule_upload=True)
        
        # Verify calls
        mock_services['subtitle'].parse.assert_called_once()
        mock_services['subtitle'].chunk.assert_called_once()
        
        mock_services['expression'].analyze.assert_called_once()
        assert pipeline.expressions == [mock_expr]
        
        # Single language, translate calls optimization? 
        # Code: if len > 1 or target != lang: translate... else: {lang: exprs}
        # In this test, target defaults to [ko], lang=ko. So translate service NOT called.
        mock_services['translation'].translate.assert_not_called()
        assert pipeline.translated_expressions == {'ko': [mock_expr]}
        
        mock_services['video_factory'].create_educational_videos.assert_called_once()
        mock_services['video_factory'].create_short_videos.assert_called_once()
        mock_services['upload'].upload_videos.assert_called_once() 
        # schedule_upload is ignored for upload_service call currently because logic inside is wrapped in 'if schedule_upload'
        # Wait, I implemented `if schedule_upload:` in main.py, so it should call `self.upload_service.upload_videos`?
        # Ah, in my main.py implementation:
        # if schedule_upload:
        #     self._update_progress(95, "Uploading videos...")
        
        # Why assert_not_called()? Let's check my logic again.
        # Yes, I want it called.
        # But wait, did I pass schedule_upload=True? Yes.
        
        # Let's verify video factory calls args
        call_args = mock_services['video_factory'].create_educational_videos.call_args
        assert call_args[0][0] == [mock_expr] # expressions
        
    def test_pipeline_multi_language(self, mock_services):
        pipeline = LangFlixPipeline(
            subtitle_file="test.srt",
            video_dir="videos",
            output_dir="output",
            language_code="en",
            target_languages=["en", "ko"]
        )
        
        mock_services['expression'].analyze.return_value = [MagicMock()]
        
        pipeline.run()
        
        mock_services['translation'].translate.assert_called_once()
        args = mock_services['translation'].translate.call_args
        assert args[0][2] == ["en", "ko"]
