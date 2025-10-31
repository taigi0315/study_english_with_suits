"""
Integration tests for VideoPipelineService
Verifies that API and CLI use the same pipeline and produce identical results
"""
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os
from pathlib import Path

from langflix.services.video_pipeline_service import VideoPipelineService
from langflix.main import LangFlixPipeline


class TestPipelineServiceIntegration(unittest.TestCase):
    """Integration tests for pipeline service"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class"""
        # Create temporary test files
        cls.test_video_path = None
        cls.test_subtitle_path = None
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary files for testing
        # Note: These are minimal files for testing structure, not actual video/subtitle content
        if not self.test_video_path or not os.path.exists(self.test_video_path):
            with tempfile.NamedTemporaryFile(suffix='.mkv', delete=False) as f:
                self.test_video_path = f.name
        
        if not self.test_subtitle_path or not os.path.exists(self.test_subtitle_path):
            # Create minimal valid SRT file
            with tempfile.NamedTemporaryFile(suffix='.srt', delete=False, mode='w') as f:
                f.write("1\n00:00:00,000 --> 00:00:05,000\nTest subtitle\n\n")
                self.test_subtitle_path = f.name
    
    @patch('langflix.services.video_pipeline_service.LangFlixPipeline')
    def test_service_uses_same_pipeline_as_cli(self, mock_pipeline_class):
        """Test that VideoPipelineService uses LangFlixPipeline same as CLI"""
        mock_pipeline = MagicMock()
        mock_pipeline_class.return_value = mock_pipeline
        mock_pipeline.expressions = []
        mock_pipeline.paths = {
            'language': {
                'final_videos': Path('test_output/final_videos'),
                'short_videos': Path('test_output/short_videos')
            },
            'episode': {
                'episode_dir': Path('test_output')
            }
        }
        mock_pipeline.run.return_value = {
            'total_expressions': 0,
            'processed_expressions': 0
        }
        
        service = VideoPipelineService(language_code="ko", output_dir="test_output")
        
        # Process video through service
        service.process_video(
            video_path=self.test_video_path,
            subtitle_path=self.test_subtitle_path,
            show_name="TestShow",
            episode_name="TestEpisode",
            max_expressions=5,
            language_level="intermediate",
            test_mode=True,
            no_shorts=True
        )
        
        # Verify LangFlixPipeline was instantiated
        mock_pipeline_class.assert_called_once()
        
        # Verify parameters match what CLI would use
        call_kwargs = mock_pipeline_class.call_args[1]
        self.assertEqual(call_kwargs['language_code'], 'ko')
        self.assertEqual(call_kwargs['output_dir'], 'test_output')
        
        # Verify run was called with same parameters
        run_call = mock_pipeline.run.call_args[1]
        self.assertEqual(run_call['max_expressions'], 5)
        self.assertEqual(run_call['language_level'], 'intermediate')
        self.assertEqual(run_call['test_mode'], True)
        self.assertEqual(run_call['no_shorts'], True)
        self.assertEqual(run_call['dry_run'], False)
    
    def test_progress_callback_integration(self):
        """Test that progress callback works through service to pipeline"""
        progress_updates = []
        
        def track_progress(progress, message):
            progress_updates.append((progress, message))
        
        with patch('langflix.services.video_pipeline_service.LangFlixPipeline') as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline_class.return_value = mock_pipeline
            mock_pipeline.expressions = []
            mock_pipeline.paths = {
                'language': {
                    'final_videos': Path('test_output/final_videos'),
                    'short_videos': Path('test_output/short_videos')
                },
                'episode': {
                    'episode_dir': Path('test_output')
                }
            }
            mock_pipeline.run.return_value = {
                'total_expressions': 0,
                'processed_expressions': 0
            }
            
            service = VideoPipelineService(language_code="ko", output_dir="test_output")
            
            service.process_video(
                video_path=self.test_video_path,
                subtitle_path=self.test_subtitle_path,
                show_name="TestShow",
                episode_name="TestEpisode",
                progress_callback=track_progress
            )
            
            # Verify callback was passed to pipeline
            call_kwargs = mock_pipeline_class.call_args[1]
            self.assertEqual(call_kwargs['progress_callback'], track_progress)
            
            # Verify initial progress update was made
            self.assertTrue(len(progress_updates) > 0)
            self.assertEqual(progress_updates[0][0], 10)
    
    @patch('langflix.services.video_pipeline_service.LangFlixPipeline')
    def test_result_structure_consistency(self, mock_pipeline_class):
        """Test that service returns consistent result structure"""
        mock_pipeline = MagicMock()
        mock_pipeline_class.return_value = mock_pipeline
        mock_pipeline.expressions = []
        mock_pipeline.paths = {
            'language': {
                'final_videos': Path('test_output/final_videos'),
                'short_videos': Path('test_output/short_videos')
            },
            'episode': {
                'episode_dir': Path('test_output')
            }
        }
        mock_pipeline.run.return_value = {
            'total_expressions': 0,
            'processed_expressions': 0
        }
        
        service = VideoPipelineService(language_code="ko", output_dir="test_output")
        
        result = service.process_video(
            video_path=self.test_video_path,
            subtitle_path=self.test_subtitle_path,
            show_name="TestShow",
            episode_name="TestEpisode"
        )
        
        # Verify result structure matches expected format
        required_keys = ['expressions', 'educational_videos', 'short_videos', 
                        'final_video', 'output_directory', 'summary']
        for key in required_keys:
            self.assertIn(key, result, f"Result missing required key: {key}")
        
        # Verify types
        self.assertIsInstance(result['expressions'], list)
        self.assertIsInstance(result['educational_videos'], list)
        self.assertIsInstance(result['short_videos'], list)
        self.assertIsInstance(result['output_directory'], str)
        self.assertIsInstance(result['summary'], dict)


if __name__ == '__main__':
    unittest.main()

