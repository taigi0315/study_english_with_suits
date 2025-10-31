"""
Unit tests for VideoPipelineService
"""
import unittest
from unittest.mock import Mock, patch, MagicMock, call, ANY
from pathlib import Path
import tempfile
import os

from langflix.services.video_pipeline_service import VideoPipelineService


class TestVideoPipelineService(unittest.TestCase):
    """Test cases for VideoPipelineService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.service = VideoPipelineService(
            language_code="ko",
            output_dir="test_output"
        )
    
    def test_init(self):
        """Test service initialization"""
        self.assertEqual(self.service.language_code, "ko")
        self.assertEqual(self.service.output_dir, "test_output")
    
    @patch('langflix.services.video_pipeline_service.LangFlixPipeline')
    def test_process_video_basic(self, mock_pipeline_class):
        """Test basic video processing"""
        # Setup mocks
        mock_pipeline = MagicMock()
        mock_pipeline_class.return_value = mock_pipeline
        
        # Mock pipeline results
        mock_pipeline.expressions = []
        mock_pipeline.paths = {
            'language': {
                'final_videos': Path('test_output/test/final_videos'),
                'short_videos': Path('test_output/test/short_videos')
            },
            'episode': {
                'episode_dir': Path('test_output/test')
            }
        }
        mock_pipeline.run.return_value = {
            'total_expressions': 0,
            'processed_expressions': 0
        }
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.mkv', delete=False) as video_file:
            video_path = video_file.name
        with tempfile.NamedTemporaryFile(suffix='.srt', delete=False) as subtitle_file:
            subtitle_path = subtitle_file.name
        
        try:
            # Test processing
            result = self.service.process_video(
                video_path=video_path,
                subtitle_path=subtitle_path,
                show_name="TestShow",
                episode_name="TestEpisode",
                max_expressions=5,
                language_level="intermediate",
                test_mode=True,
                no_shorts=True
            )
            
            # Verify pipeline was created correctly
            mock_pipeline_class.assert_called_once()
            call_kwargs = mock_pipeline_class.call_args[1]
            self.assertEqual(call_kwargs['language_code'], 'ko')
            self.assertEqual(call_kwargs['output_dir'], 'test_output')
            # Verify critical parameters are passed to pipeline
            self.assertEqual(call_kwargs.get('series_name'), 'TestShow')
            self.assertEqual(call_kwargs.get('episode_name'), 'TestEpisode')
            self.assertEqual(call_kwargs.get('video_file'), video_path)
            # Verify subtitle_file and video_dir are set
            self.assertIn('subtitle_file', call_kwargs)
            self.assertIn('video_dir', call_kwargs)
            
            # Verify pipeline.run was called
            mock_pipeline.run.assert_called_once_with(
                max_expressions=5,
                dry_run=False,
                language_level="intermediate",
                save_llm_output=False,
                test_mode=True,
                no_shorts=True
            )
            
            # Verify result structure
            self.assertIn('expressions', result)
            self.assertIn('educational_videos', result)
            self.assertIn('short_videos', result)
            self.assertIn('final_video', result)
            self.assertIn('output_directory', result)
            self.assertIn('summary', result)
            
        finally:
            # Cleanup
            if os.path.exists(video_path):
                os.unlink(video_path)
            if os.path.exists(subtitle_path):
                os.unlink(subtitle_path)
    
    @patch('langflix.services.video_pipeline_service.LangFlixPipeline')
    def test_process_video_with_progress_callback(self, mock_pipeline_class):
        """Test video processing with progress callback"""
        # Setup mocks
        mock_pipeline = MagicMock()
        mock_pipeline_class.return_value = mock_pipeline
        mock_pipeline.expressions = []
        mock_pipeline.paths = {
            'language': {
                'final_videos': Path('test_output/test/final_videos'),
                'short_videos': Path('test_output/test/short_videos')
            },
            'episode': {
                'episode_dir': Path('test_output/test')
            }
        }
        mock_pipeline.run.return_value = {
            'total_expressions': 0,
            'processed_expressions': 0
        }
        
        # Track callback calls
        callback_calls = []
        def progress_callback(progress, message):
            callback_calls.append((progress, message))
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.mkv', delete=False) as video_file:
            video_path = video_file.name
        with tempfile.NamedTemporaryFile(suffix='.srt', delete=False) as subtitle_file:
            subtitle_path = subtitle_file.name
        
        try:
            # Test processing with callback
            result = self.service.process_video(
                video_path=video_path,
                subtitle_path=subtitle_path,
                show_name="TestShow",
                episode_name="TestEpisode",
                max_expressions=5,
                progress_callback=progress_callback
            )
            
            # Verify callback was passed to pipeline
            call_kwargs = mock_pipeline_class.call_args[1]
            self.assertEqual(call_kwargs['progress_callback'], progress_callback)
            
            # Verify initial callback was called
            self.assertTrue(len(callback_calls) > 0)
            self.assertEqual(callback_calls[0][0], 10)
            
        finally:
            # Cleanup
            if os.path.exists(video_path):
                os.unlink(video_path)
            if os.path.exists(subtitle_path):
                os.unlink(subtitle_path)
    
    @patch('langflix.services.video_pipeline_service.LangFlixPipeline')
    def test_process_video_error_handling(self, mock_pipeline_class):
        """Test error handling in video processing"""
        # Setup mocks to raise exception
        mock_pipeline_class.side_effect = Exception("Pipeline initialization failed")
        
        with tempfile.NamedTemporaryFile(suffix='.mkv', delete=False) as video_file:
            video_path = video_file.name
        with tempfile.NamedTemporaryFile(suffix='.srt', delete=False) as subtitle_file:
            subtitle_path = subtitle_file.name
        
        try:
            # Track callback calls
            callback_calls = []
            def progress_callback(progress, message):
                callback_calls.append((progress, message))
            
            # Test that exception is raised
            with self.assertRaises(Exception) as context:
                self.service.process_video(
                    video_path=video_path,
                    subtitle_path=subtitle_path,
                    show_name="TestShow",
                    episode_name="TestEpisode",
                    progress_callback=progress_callback
                )
            
            self.assertIn("Pipeline initialization failed", str(context.exception))
            
            # Verify error callback was called
            self.assertTrue(len(callback_calls) > 0)
            self.assertTrue("Error" in callback_calls[-1][1])
            
        finally:
            # Cleanup
            if os.path.exists(video_path):
                os.unlink(video_path)
            if os.path.exists(subtitle_path):
                os.unlink(subtitle_path)
    
    def test_extract_expressions(self):
        """Test expression extraction from pipeline results"""
        # Create mock expression objects
        mock_expression_1 = MagicMock()
        mock_expression_1.expression = "test expression"
        mock_expression_1.expression_translation = "테스트 표현"
        mock_expression_1.expression_dialogue = "This is a test"
        mock_expression_1.expression_dialogue_translation = "이것은 테스트입니다"
        mock_expression_1.similar_expressions = ["similar 1", "similar 2"]
        mock_expression_1.context_start_time = "00:01:00,000"
        mock_expression_1.context_end_time = "00:01:10,000"
        mock_expression_1.expression_start_time = "00:01:05,000"
        mock_expression_1.expression_end_time = "00:01:07,000"
        mock_expression_1.difficulty = 5
        mock_expression_1.category = "test"
        
        mock_expression_2 = MagicMock()
        mock_expression_2.expression = "another expression"
        mock_expression_2.expression_translation = "또 다른 표현"
        mock_expression_2.expression_dialogue = "Another test"
        mock_expression_2.expression_dialogue_translation = "또 다른 테스트"
        mock_expression_2.similar_expressions = []
        mock_expression_2.context_start_time = "00:02:00,000"
        mock_expression_2.context_end_time = "00:02:10,000"
        mock_expression_2.expression_start_time = None
        mock_expression_2.expression_end_time = None
        
        # Test extraction
        expressions = [mock_expression_1, mock_expression_2]
        result = self.service._extract_expressions(expressions)
        
        # Verify results
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['expression'], "test expression")
        self.assertEqual(result[0]['translation'], "테스트 표현")
        self.assertEqual(result[0]['difficulty'], 5)
        self.assertEqual(result[0]['category'], "test")
        self.assertEqual(result[1]['expression'], "another expression")
        self.assertIsNone(result[1].get('difficulty'))
        self.assertIsNone(result[1].get('category'))
    
    def test_find_educational_videos(self):
        """Test finding educational videos from paths"""
        # Create temporary directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            final_videos_dir = Path(temp_dir) / "final_videos"
            final_videos_dir.mkdir(parents=True)
            
            # Create mock video files
            video1 = final_videos_dir / "educational_01_test.mkv"
            video2 = final_videos_dir / "educational_02_test.mkv"
            video1.touch()
            video2.touch()
            
            paths = {
                'language': {
                    'final_videos': final_videos_dir
                }
            }
            
            result = self.service._find_educational_videos(paths)
            
            # Verify videos found
            self.assertEqual(len(result), 2)
            self.assertIn(str(video1), result)
            self.assertIn(str(video2), result)
    
    def test_find_short_videos(self):
        """Test finding short videos from paths"""
        # Create temporary directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            short_videos_dir = Path(temp_dir) / "short_videos"
            short_videos_dir.mkdir(parents=True)
            
            # Create mock video files
            video1 = short_videos_dir / "short_01.mkv"
            video2 = short_videos_dir / "short_02.mkv"
            video1.touch()
            video2.touch()
            
            paths = {
                'language': {
                    'short_videos': short_videos_dir
                }
            }
            
            result = self.service._find_short_videos(paths)
            
            # Verify videos found
            self.assertEqual(len(result), 2)
            self.assertIn(str(video1), result)
            self.assertIn(str(video2), result)
    
    def test_find_final_video(self):
        """Test finding final concatenated video"""
        # Create temporary directory structure
        with tempfile.TemporaryDirectory() as temp_dir:
            final_videos_dir = Path(temp_dir) / "final_videos"
            final_videos_dir.mkdir(parents=True)
            
            # Create final video file
            final_video = final_videos_dir / "long-form_TestEpisode_video.mkv"
            final_video.touch()
            
            paths = {
                'language': {
                    'final_videos': final_videos_dir
                }
            }
            
            result = self.service._find_final_video(paths, "TestEpisode", "video.mkv")
            
            # Verify final video found
            self.assertEqual(result, str(final_video))
    
    def test_find_final_video_not_found(self):
        """Test when final video is not found"""
        # Create temporary directory structure without final video
        with tempfile.TemporaryDirectory() as temp_dir:
            final_videos_dir = Path(temp_dir) / "final_videos"
            final_videos_dir.mkdir(parents=True)
            
            paths = {
                'language': {
                    'final_videos': final_videos_dir
                }
            }
            
            result = self.service._find_final_video(paths, "TestEpisode", "video.mkv")
            
            # Verify None is returned
            self.assertIsNone(result)
    
    @patch('langflix.services.video_pipeline_service.LangFlixPipeline')
    def test_pipeline_parameters_validation(self, mock_pipeline_class):
        """Test that all required parameters are correctly passed to LangFlixPipeline"""
        # Setup mocks
        mock_pipeline = MagicMock()
        mock_pipeline_class.return_value = mock_pipeline
        mock_pipeline.expressions = []
        mock_pipeline.paths = {
            'language': {
                'final_videos': Path('test_output/test/final_videos'),
                'short_videos': Path('test_output/test/short_videos')
            },
            'episode': {
                'episode_dir': Path('test_output/test')
            }
        }
        mock_pipeline.run.return_value = {
            'total_expressions': 0,
            'processed_expressions': 0
        }
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.mkv', delete=False) as video_file:
            video_path = video_file.name
        with tempfile.NamedTemporaryFile(suffix='.srt', delete=False) as subtitle_file:
            subtitle_path = subtitle_file.name
        
        try:
            # Test processing with all parameters
            result = self.service.process_video(
                video_path=video_path,
                subtitle_path=subtitle_path,
                show_name="TestSeries",
                episode_name="S01E01",
                max_expressions=10,
                language_level="advanced",
                test_mode=False,
                no_shorts=False,
                progress_callback=lambda p, m: None
            )
            
            # Verify pipeline was instantiated
            mock_pipeline_class.assert_called_once()
            call_kwargs = mock_pipeline_class.call_args[1]
            
            # Verify all required parameters are present and correct
            required_params = {
                'subtitle_file': subtitle_path,
                'video_dir': str(Path(video_path).parent),
                'output_dir': 'test_output',
                'language_code': 'ko',
                'series_name': 'TestSeries',
                'episode_name': 'S01E01',
                'video_file': video_path,
                'progress_callback': ANY
            }
            
            for param_name, expected_value in required_params.items():
                if expected_value is ANY:
                    self.assertIn(param_name, call_kwargs, 
                                f"Missing parameter: {param_name}")
                else:
                    self.assertEqual(call_kwargs.get(param_name), expected_value,
                                   f"Parameter {param_name} mismatch: "
                                   f"expected {expected_value}, got {call_kwargs.get(param_name)}")
            
        finally:
            # Cleanup
            if os.path.exists(video_path):
                os.unlink(video_path)
            if os.path.exists(subtitle_path):
                os.unlink(subtitle_path)


if __name__ == '__main__':
    unittest.main()

