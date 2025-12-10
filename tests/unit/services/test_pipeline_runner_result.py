
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from langflix.services.pipeline_runner import PipelineRunner
from langflix.services.job_queue import Job

class TestPipelineRunner(unittest.TestCase):
    
    @patch('langflix.main.LangFlixPipeline')
    @patch('langflix.services.pipeline_runner.os.path.exists')
    @patch('langflix.settings.get_storage_local_path')
    def test_run_pipeline_extracts_results_correctly(self, mock_get_storage, mock_exists, MockPipeline):
        """Test that run_pipeline correctly extracts video paths from pipeline.paths"""
        
        # Setup mocks
        mock_exists.return_value = True
        mock_get_storage.return_value = Path("/mock/output")
        
        # Mock Pipeline Instance
        pipeline_instance = MockPipeline.return_value
        pipeline_instance.run.return_value = {'expressions_count': 42}
        
        # Mock pipeline.paths structure
        pipeline_instance.paths = {
            'languages': {
                'ko': {
                    'final_videos': '/mock/output/ko/final',
                    'shorts': '/mock/output/ko/shorts'
                }
            }
        }
        
        # Mock Path.glob to simulate existing files
        # Since Path usage inside run_pipeline is from pathlib (imported at top level), we should patch 'langflix.services.pipeline_runner.Path'
        # BUT we are patching os.path.exists separately.
        
        with patch('langflix.services.pipeline_runner.Path') as MockPath:
            # We need MockPath(str).exists() -> True
            # And MockPath(str).glob pattern.
            
            # Setup mock path instances
            mock_final_path = MagicMock()
            mock_final_path.exists.return_value = True
            mock_final_path.glob.return_value = [Path('/mock/output/ko/final/vid1.mkv')]
            
            mock_shorts_path = MagicMock()
            mock_shorts_path.exists.return_value = True
            mock_shorts_path.glob.return_value = [Path('/mock/output/ko/shorts/short1.mkv')]
            
            def path_side_effect(arg):
                if arg == '/mock/output/ko/final':
                    return mock_final_path
                if arg == '/mock/output/ko/shorts':
                    return mock_shorts_path
                # Fallback for job.video_path extraction
                m = MagicMock()
                m.parent.name = "Show"
                m.stem = "Episode"
                return m
            
            MockPath.side_effect = path_side_effect
            
            runner = PipelineRunner()
            job = Job(
                job_id="test-job", 
                video_path="/data/Show/Episode.mkv",
                subtitle_path="/data/Show/Episode.srt",
                language_code="ko",
                media_id="mock-media-id",
                language_level="intermediate"
            )
            
            result = runner.run_pipeline(job)
            
            self.assertIn('/mock/output/ko/final/vid1.mkv', result['final_videos'])
            self.assertIn('/mock/output/ko/shorts/short1.mkv', result['short_videos'])



    @patch('langflix.services.pipeline_runner.Path')
    @patch('langflix.main.LangFlixPipeline')
    @patch('langflix.services.pipeline_runner.os.path.exists')
    @patch('langflix.settings.get_storage_local_path')
    def test_run_pipeline_result_extraction_logic(self, mock_get_storage, mock_os_exists, MockPipeline, MockPath):
        """Verify the logic for extracting paths from pipeline object"""
        
        # Setup basic validity checks
        mock_os_exists.return_value = True
        mock_get_storage.return_value = "output"
        
        # Setup Pipeline Mock
        pipeline = MockPipeline.return_value
        pipeline.run.return_value = {'expressions_count': 10}
        pipeline.paths = {
            'languages': {
                'en': {
                    'final_videos': '/out/final',
                    'shorts': '/out/shorts'
                }
            }
        }
        
        # Setup Path Mock behavior
        # We need Path('/out/final').exists() -> True
        # Path('/out/final').glob('*.mkv') -> [Path('vid1.mkv'), Path('vid2.mkv')]
        
        mock_final_dir = MagicMock()
        mock_final_dir.exists.return_value = True
        mock_final_dir.glob.return_value = [Path('/out/final/video1.mkv')]
        
        mock_shorts_dir = MagicMock()
        mock_shorts_dir.exists.return_value = True
        mock_shorts_dir.glob.return_value = [Path('/out/shorts/short1.mkv')]
        
        # Dispatch based on path string
        def path_side_effect(path_str):
            if path_str == '/out/final':
                return mock_final_dir
            if path_str == '/out/shorts':
                return mock_shorts_dir
            return MagicMock()
            
        MockPath.side_effect = path_side_effect
        
        # Create Runner and Job
        runner = PipelineRunner()
        job = Job(
            job_id="test-job",
            video_path="/data/Show/Episode.mkv",
            subtitle_path="/data/Show/Episode.srt",
            language_code="en",
            media_id="mock-media-id",
            language_level="intermediate"
        )
        
        # Run
        result = runner.run_pipeline(job)
        
        # Verify
        self.assertIn("/out/final/video1.mkv", result['final_videos'])
        self.assertIn("/out/shorts/short1.mkv", result['short_videos'])
        self.assertEqual(result['expressions_processed'], 10)
        
if __name__ == '__main__':
    unittest.main()
