"""
Unit tests for Video Format Selection feature in VideoPipelineService
"""
import unittest
from unittest.mock import MagicMock, patch, ANY
import tempfile
import os
from pathlib import Path

from langflix.services.video_pipeline_service import VideoPipelineService

class TestVideoFormatSelection(unittest.TestCase):
    """Test cases for video format selection logic"""

    def setUp(self):
        """Set up test fixtures"""
        self.service = VideoPipelineService(
            language_code="ko",
            output_dir="test_output"
        )
        # Create dummy video and subtitle files
        self.temp_video = tempfile.NamedTemporaryFile(suffix='.mkv', delete=False)
        self.temp_subtitle = tempfile.NamedTemporaryFile(suffix='.srt', delete=False)
        self.video_path = self.temp_video.name
        self.subtitle_path = self.temp_subtitle.name
        self.temp_video.close()
        self.temp_subtitle.close()

    def tearDown(self):
        """Cleanup temporary files"""
        if os.path.exists(self.video_path):
            os.unlink(self.video_path)
        if os.path.exists(self.subtitle_path):
            os.unlink(self.subtitle_path)

    @patch('langflix.services.video_pipeline_service.LangFlixPipeline')
    def test_create_both_formats_default(self, mock_pipeline_class):
        """Test default behavior (create both formats)"""
        mock_pipeline = MagicMock()
        mock_pipeline_class.return_value = mock_pipeline
        mock_pipeline.run.return_value = {}
        mock_pipeline.paths = {
            'language': {
                'final_videos': Path('test/final'),
                'short_videos': Path('test/short')
            }, 
            'episode': {
                'episode_dir': Path('test/episode')
            }
        }

        self.service.process_video(
            video_path=self.video_path,
            subtitle_path=self.subtitle_path,
            show_name="Test",
            episode_name="Ep1",
            create_long_form=True,
            create_short_form=True
        )

        mock_pipeline.run.assert_called_once()
        call_kwargs = mock_pipeline.run.call_args[1]
        
        # Verify default translation
        self.assertFalse(call_kwargs['no_long_form'], "no_long_form should be False when create_long_form is True")
        self.assertFalse(call_kwargs['no_shorts'], "no_shorts should be False when create_short_form is True")

    @patch('langflix.services.video_pipeline_service.LangFlixPipeline')
    def test_skip_long_form(self, mock_pipeline_class):
        """Test skipping long form video"""
        mock_pipeline = MagicMock()
        mock_pipeline_class.return_value = mock_pipeline
        mock_pipeline.run.return_value = {}
        mock_pipeline.paths = {
            'language': {
                'final_videos': Path('test/final'),
                'short_videos': Path('test/short')
            }, 
            'episode': {
                'episode_dir': Path('test/episode')
            }
        }

        self.service.process_video(
            video_path=self.video_path,
            subtitle_path=self.subtitle_path,
            show_name="Test",
            episode_name="Ep1",
            create_long_form=False,
            create_short_form=True
        )

        call_kwargs = mock_pipeline.run.call_args[1]
        self.assertTrue(call_kwargs['no_long_form'], "no_long_form should be True when create_long_form is False")
        self.assertFalse(call_kwargs['no_shorts'])

    @patch('langflix.services.video_pipeline_service.LangFlixPipeline')
    def test_skip_short_form(self, mock_pipeline_class):
        """Test skipping short form video"""
        mock_pipeline = MagicMock()
        mock_pipeline_class.return_value = mock_pipeline
        mock_pipeline.run.return_value = {}
        mock_pipeline.paths = {
            'language': {
                'final_videos': Path('test/final'),
                'short_videos': Path('test/short')
            }, 
            'episode': {
                'episode_dir': Path('test/episode')
            }
        }

        self.service.process_video(
            video_path=self.video_path,
            subtitle_path=self.subtitle_path,
            show_name="Test",
            episode_name="Ep1",
            create_long_form=True,
            create_short_form=False
        )

        call_kwargs = mock_pipeline.run.call_args[1]
        self.assertFalse(call_kwargs['no_long_form'])
        self.assertTrue(call_kwargs['no_shorts'], "no_shorts should be True when create_short_form is False")

    @patch('langflix.services.video_pipeline_service.LangFlixPipeline')
    def test_skip_both(self, mock_pipeline_class):
        """Test skipping both formats"""
        mock_pipeline = MagicMock()
        mock_pipeline_class.return_value = mock_pipeline
        mock_pipeline.run.return_value = {}
        mock_pipeline.paths = {
            'language': {
                'final_videos': Path('test/final'),
                'short_videos': Path('test/short')
            }, 
            'episode': {
                'episode_dir': Path('test/episode')
            }
        }

        self.service.process_video(
            video_path=self.video_path,
            subtitle_path=self.subtitle_path,
            show_name="Test",
            episode_name="Ep1",
            create_long_form=False,
            create_short_form=False
        )

        call_kwargs = mock_pipeline.run.call_args[1]
        self.assertTrue(call_kwargs['no_long_form'])
        self.assertTrue(call_kwargs['no_shorts'])

if __name__ == '__main__':
    unittest.main()
