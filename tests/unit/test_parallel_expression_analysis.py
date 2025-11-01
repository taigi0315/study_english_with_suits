"""
Unit tests for parallel expression analysis functionality
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
from pathlib import Path

from langflix.main import LangFlixPipeline
from langflix import settings


class TestParallelExpressionAnalysisSettings(unittest.TestCase):
    """Test parallel expression analysis settings"""
    
    @patch('langflix.settings.get_expression_llm')
    def test_get_parallel_llm_processing_enabled_true(self, mock_get_llm):
        """Test parallel processing enabled returns True"""
        mock_get_llm.return_value = {
            'parallel_processing': {
                'enabled': True
            }
        }
        result = settings.get_parallel_llm_processing_enabled()
        self.assertTrue(result)
    
    @patch('langflix.settings.get_expression_llm')
    def test_get_parallel_llm_processing_enabled_false(self, mock_get_llm):
        """Test parallel processing enabled returns False"""
        mock_get_llm.return_value = {
            'parallel_processing': {
                'enabled': False
            }
        }
        result = settings.get_parallel_llm_processing_enabled()
        self.assertFalse(result)
    
    @patch('langflix.settings.get_expression_llm')
    def test_get_parallel_llm_processing_enabled_default(self, mock_get_llm):
        """Test parallel processing enabled defaults to True"""
        mock_get_llm.return_value = {}
        result = settings.get_parallel_llm_processing_enabled()
        self.assertTrue(result)  # Default is True
    
    @patch('langflix.settings.get_expression_llm')
    @patch('multiprocessing.cpu_count')
    def test_get_parallel_llm_max_workers_auto(self, mock_cpu_count, mock_get_llm):
        """Test max workers auto-detection (capped at 5)"""
        mock_cpu_count.return_value = 8
        mock_get_llm.return_value = {
            'parallel_processing': {
                'max_workers': None
            }
        }
        result = settings.get_parallel_llm_max_workers()
        self.assertEqual(result, 5)  # min(8, 5) = 5
    
    @patch('langflix.settings.get_expression_llm')
    @patch('multiprocessing.cpu_count')
    def test_get_parallel_llm_max_workers_auto_small_cpu(self, mock_cpu_count, mock_get_llm):
        """Test max workers auto-detection with small CPU count"""
        mock_cpu_count.return_value = 2
        mock_get_llm.return_value = {
            'parallel_processing': {
                'max_workers': None
            }
        }
        result = settings.get_parallel_llm_max_workers()
        self.assertEqual(result, 2)  # min(2, 5) = 2
    
    @patch('langflix.settings.get_expression_llm')
    def test_get_parallel_llm_max_workers_custom(self, mock_get_llm):
        """Test max workers with custom value"""
        mock_get_llm.return_value = {
            'parallel_processing': {
                'max_workers': 3
            }
        }
        result = settings.get_parallel_llm_max_workers()
        self.assertEqual(result, 3)
    
    @patch('langflix.settings.get_expression_llm')
    def test_get_parallel_llm_timeout(self, mock_get_llm):
        """Test timeout per chunk"""
        mock_get_llm.return_value = {
            'parallel_processing': {
                'timeout_per_chunk': 600
            }
        }
        result = settings.get_parallel_llm_timeout()
        self.assertEqual(result, 600)
    
    @patch('langflix.settings.get_expression_llm')
    def test_get_parallel_llm_timeout_default(self, mock_get_llm):
        """Test timeout per chunk defaults to 300"""
        mock_get_llm.return_value = {}
        result = settings.get_parallel_llm_timeout()
        self.assertEqual(result, 300)


class TestLangFlixPipelineParallelAnalysis(unittest.TestCase):
    """Test LangFlixPipeline parallel expression analysis"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.subtitle_file = Path("test_data/test.srt")
        self.video_dir = Path("test_data")
        self.output_dir = Path("test_output")
    
    @patch('langflix.main.LangFlixPipeline._analyze_expressions_sequential')
    @patch('langflix.settings.get_parallel_llm_processing_enabled')
    def test_analyze_expressions_uses_sequential_for_test_mode(self, mock_enabled, mock_sequential):
        """Test that test_mode always uses sequential processing"""
        mock_enabled.return_value = True
        mock_sequential.return_value = []
        
        # Create mock pipeline
        pipeline = MagicMock(spec=LangFlixPipeline)
        pipeline.chunks = [
            [{"text": "Chunk 1"}],
            [{"text": "Chunk 2"}]
        ]
        pipeline._analyze_expressions_sequential = mock_sequential
        pipeline._analyze_expressions_parallel = MagicMock()
        pipeline.paths = {'episode': {}}
        
        # Call _analyze_expressions directly with test_mode=True
        from langflix.main import LangFlixPipeline
        LangFlixPipeline._analyze_expressions = LangFlixPipeline._analyze_expressions.__func__
        
        result = LangFlixPipeline._analyze_expressions(
            pipeline,
            max_expressions=None,
            language_level="intermediate",
            save_llm_output=False,
            test_mode=True
        )
        
        # Should use sequential, not parallel
        mock_sequential.assert_called_once()
        pipeline._analyze_expressions_parallel.assert_not_called()
    
    @patch('langflix.main.LangFlixPipeline._analyze_expressions_parallel')
    @patch('langflix.settings.get_parallel_llm_processing_enabled')
    def test_analyze_expressions_uses_parallel_when_enabled(self, mock_enabled, mock_parallel):
        """Test that parallel mode is used when enabled and multiple chunks exist"""
        mock_enabled.return_value = True
        mock_parallel.return_value = []
        
        # Create mock pipeline
        pipeline = MagicMock(spec=LangFlixPipeline)
        pipeline.chunks = [
            [{"text": "Chunk 1"}],
            [{"text": "Chunk 2"}],
            [{"text": "Chunk 3"}]
        ]
        pipeline._analyze_expressions_parallel = mock_parallel
        pipeline._analyze_expressions_sequential = MagicMock()
        pipeline.paths = {'episode': {}}
        
        # Call _analyze_expressions directly with test_mode=False
        from langflix.main import LangFlixPipeline
        LangFlixPipeline._analyze_expressions = LangFlixPipeline._analyze_expressions.__func__
        
        result = LangFlixPipeline._analyze_expressions(
            pipeline,
            max_expressions=None,
            language_level="intermediate",
            save_llm_output=False,
            test_mode=False
        )
        
        # Should use parallel, not sequential
        mock_parallel.assert_called_once()
        pipeline._analyze_expressions_sequential.assert_not_called()
    
    @patch('langflix.main.LangFlixPipeline._analyze_expressions_sequential')
    @patch('langflix.settings.get_parallel_llm_processing_enabled')
    def test_analyze_expressions_uses_sequential_for_single_chunk(self, mock_enabled, mock_sequential):
        """Test that single chunk uses sequential processing"""
        mock_enabled.return_value = True
        mock_sequential.return_value = []
        
        # Create mock pipeline
        pipeline = MagicMock(spec=LangFlixPipeline)
        pipeline.chunks = [
            [{"text": "Chunk 1"}]
        ]
        pipeline._analyze_expressions_sequential = mock_sequential
        pipeline._analyze_expressions_parallel = MagicMock()
        pipeline.paths = {'episode': {}}
        
        # Call _analyze_expressions directly
        from langflix.main import LangFlixPipeline
        LangFlixPipeline._analyze_expressions = LangFlixPipeline._analyze_expressions.__func__
        
        result = LangFlixPipeline._analyze_expressions(
            pipeline,
            max_expressions=None,
            language_level="intermediate",
            save_llm_output=False,
            test_mode=False
        )
        
        # Should use sequential for single chunk
        mock_sequential.assert_called_once()
        pipeline._analyze_expressions_parallel.assert_not_called()
    
    @patch('langflix.core.parallel_processor.ExpressionBatchProcessor')
    @patch('langflix.settings.get_parallel_llm_max_workers')
    @patch('langflix.settings.get_parallel_llm_timeout')
    def test_analyze_expressions_parallel_creates_processor(self, mock_timeout, mock_workers, mock_processor_class):
        """Test that parallel analysis creates ExpressionBatchProcessor with correct config"""
        mock_workers.return_value = 5
        mock_timeout.return_value = 300
        mock_processor = MagicMock()
        mock_processor.analyze_expression_chunks.return_value = [[], []]
        mock_processor_class.return_value = mock_processor
        
        # Create mock pipeline
        pipeline = MagicMock(spec=LangFlixPipeline)
        pipeline.chunks = [
            [{"text": "Chunk 1"}],
            [{"text": "Chunk 2"}]
        ]
        pipeline.language_code = "ko"
        pipeline.subtitle_processor = MagicMock()
        pipeline.subtitle_processor.find_expression_timing.return_value = ("00:00:00", "00:00:01")
        pipeline.paths = {
            'episode': {
                'episode_dir': Path("test_output/test")
            }
        }
        
        from langflix.main import LangFlixPipeline
        LangFlixPipeline._analyze_expressions_parallel = LangFlixPipeline._analyze_expressions_parallel.__func__
        
        result = LangFlixPipeline._analyze_expressions_parallel(
            pipeline,
            chunks=pipeline.chunks,
            max_expressions=None,
            language_level="intermediate",
            save_llm_output=False
        )
        
        # Verify ExpressionBatchProcessor was created with correct max_workers
        mock_processor_class.assert_called_once_with(max_workers=5)
        
        # Verify analyze_expression_chunks was called
        mock_processor.analyze_expression_chunks.assert_called_once()
        call_kwargs = mock_processor.analyze_expression_chunks.call_args[1]
        self.assertEqual(call_kwargs['language_level'], "intermediate")
        self.assertEqual(call_kwargs['language_code'], "ko")
        self.assertEqual(call_kwargs['save_output'], False)


if __name__ == '__main__':
    unittest.main()

