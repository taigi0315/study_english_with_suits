"""
Unit tests for ParallelProcessor
"""

import pytest
import time
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor

from langflix.core.parallel_processor import (
    ParallelProcessor, ProcessingTask, ProcessingResult,
    ExpressionBatchProcessor, VideoBatchProcessor, ResourceManager,
    get_resource_manager, get_expression_processor, get_video_processor,
    process_expressions_parallel
)

class TestProcessingTask:
    """Test ProcessingTask functionality"""
    
    def test_processing_task_creation(self):
        """Test processing task creation"""
        def dummy_function(x, y, z=None):
            return x + y + (z or 0)
        
        task = ProcessingTask(
            task_id="test_task",
            function=dummy_function,
            args=(1, 2),
            kwargs={"z": 3},
            priority=5,
            timeout=10.0
        )
        
        assert task.task_id == "test_task"
        assert task.function == dummy_function
        assert task.args == (1, 2)
        assert task.kwargs == {"z": 3}
        assert task.priority == 5
        assert task.timeout == 10.0

class TestProcessingResult:
    """Test ProcessingResult functionality"""
    
    def test_processing_result_creation(self):
        """Test processing result creation"""
        result = ProcessingResult(
            task_id="test_task",
            success=True,
            result="test_result",
            duration=1.5
        )
        
        assert result.task_id == "test_task"
        assert result.success is True
        assert result.result == "test_result"
        assert result.error is None
        assert result.duration == 1.5
    
    def test_processing_result_with_error(self):
        """Test processing result with error"""
        error = ValueError("Test error")
        result = ProcessingResult(
            task_id="test_task",
            success=False,
            error=error,
            duration=0.5
        )
        
        assert result.task_id == "test_task"
        assert result.success is False
        assert result.result is None
        assert result.error == error
        assert result.duration == 0.5

class TestParallelProcessor:
    """Test ParallelProcessor functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.processor = ParallelProcessor(
            max_workers=2,
            use_processes=False,
            timeout=5.0
        )
    
    def test_parallel_processor_initialization(self):
        """Test parallel processor initialization"""
        assert self.processor.max_workers == 2
        assert self.processor.use_processes is False
        assert self.processor.timeout == 5.0
        assert self.processor.executor_class == ThreadPoolExecutor
    
    def test_simple_function_execution(self):
        """Test simple function execution"""
        def add_numbers(x, y):
            return x + y
        
        task = ProcessingTask(
            task_id="add_task",
            function=add_numbers,
            args=(3, 4),
            kwargs={}
        )
        
        results = self.processor.process_batch([task])
        
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].result == 7
        assert results[0].task_id == "add_task"
    
    def test_multiple_tasks_execution(self):
        """Test multiple tasks execution"""
        def multiply(x, y):
            return x * y
        
        tasks = [
            ProcessingTask(
                task_id=f"multiply_{i}",
                function=multiply,
                args=(i, 2),
                kwargs={}
            )
            for i in range(5)
        ]
        
        results = self.processor.process_batch(tasks)
        
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result.success is True
            assert result.result == i * 2
            assert result.task_id == f"multiply_{i}"
    
    def test_task_with_error(self):
        """Test task that raises an error"""
        def error_function():
            raise ValueError("Test error")
        
        task = ProcessingTask(
            task_id="error_task",
            function=error_function,
            args=(),
            kwargs={}
        )
        
        results = self.processor.process_batch([task])
        
        assert len(results) == 1
        assert results[0].success is False
        assert isinstance(results[0].error, ValueError)
        assert str(results[0].error) == "Test error"
    
    def test_task_priority_ordering(self):
        """Test task priority ordering"""
        def priority_function(priority):
            return priority
        
        tasks = [
            ProcessingTask(
                task_id=f"task_{i}",
                function=priority_function,
                args=(i,),
                kwargs={},
                priority=i
            )
            for i in [3, 1, 4, 2, 0]  # Random order
        ]
        
        results = self.processor.process_batch(tasks)
        
        # Results should be in priority order (highest first)
        assert len(results) == 5
        priorities = [result.result for result in results]
        assert priorities == [4, 3, 2, 1, 0]  # Sorted by priority
    
    def test_progress_callback(self):
        """Test progress callback functionality"""
        def slow_function(x):
            time.sleep(0.1)
            return x * 2
        
        tasks = [
            ProcessingTask(
                task_id=f"slow_task_{i}",
                function=slow_function,
                args=(i,),
                kwargs={}
            )
            for i in range(3)
        ]
        
        progress_calls = []
        
        def progress_callback(completed, total):
            progress_calls.append((completed, total))
        
        results = self.processor.process_batch(tasks, progress_callback)
        
        assert len(results) == 3
        assert len(progress_calls) == 3
        assert progress_calls[0] == (1, 3)
        assert progress_calls[1] == (2, 3)
        assert progress_calls[2] == (3, 3)
    
    def test_empty_task_list(self):
        """Test processing empty task list"""
        results = self.processor.process_batch([])
        assert len(results) == 0

class TestExpressionBatchProcessor:
    """Test ExpressionBatchProcessor functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.processor = ExpressionBatchProcessor(max_workers=2)
    
    @patch('langflix.core.expression_analyzer.analyze_chunk')
    def test_analyze_expression_chunks(self, mock_analyze_chunk):
        """Test expression chunk analysis"""
        # Mock the analyze_chunk function
        mock_analyze_chunk.return_value = [
            {"expression": "test_expression", "translation": "테스트 표현"}
        ]
        
        # Create test chunks
        chunks = [
            [{"text": "Hello world", "start": 0, "end": 1}],
            [{"text": "Good morning", "start": 1, "end": 2}],
            [{"text": "How are you", "start": 2, "end": 3}]
        ]
        
        # Process chunks
        results = self.processor.analyze_expression_chunks(
            chunks,
            language_level="intermediate",
            language_code="ko"
        )
        
        # Verify results
        assert len(results) == 3
        assert all(len(result) == 1 for result in results)
        assert mock_analyze_chunk.call_count == 3
    
    @patch('langflix.core.expression_analyzer.analyze_chunk')
    def test_analyze_expression_chunks_with_progress(self, mock_analyze_chunk):
        """Test expression chunk analysis with progress callback"""
        mock_analyze_chunk.return_value = []
        
        chunks = [
            [{"text": "Chunk 1"}],
            [{"text": "Chunk 2"}],
            [{"text": "Chunk 3"}]
        ]
        
        progress_calls = []
        
        def progress_callback(completed, total):
            progress_calls.append((completed, total))
        
        results = self.processor.analyze_expression_chunks(
            chunks,
            progress_callback=progress_callback
        )
        
        assert len(results) == 3
        assert len(progress_calls) == 3
        assert progress_calls[0] == (1, 3)
        assert progress_calls[1] == (2, 3)
        assert progress_calls[2] == (3, 3)
    
    @patch('langflix.core.expression_analyzer.analyze_chunk')
    def test_analyze_expression_chunks_with_save_output(self, mock_analyze_chunk):
        """Test expression chunk analysis with save_output parameter"""
        mock_analyze_chunk.return_value = [
            {"expression": "test_expression", "translation": "테스트 표현"}
        ]
        
        chunks = [
            [{"text": "Hello world", "start": 0, "end": 1}],
            [{"text": "Good morning", "start": 1, "end": 2}]
        ]
        
        results = self.processor.analyze_expression_chunks(
            chunks,
            language_level="intermediate",
            language_code="ko",
            save_output=True,
            output_dir="/tmp/test_output"
        )
        
        assert len(results) == 2
        assert mock_analyze_chunk.call_count == 2
        
        # Verify save_output and output_dir were passed correctly
        for call in mock_analyze_chunk.call_args_list:
            assert call.kwargs.get('save_output') is True
            assert call.kwargs.get('output_dir') == "/tmp/test_output"
    
    @patch('langflix.core.expression_analyzer.analyze_chunk')
    def test_analyze_expression_chunks_without_save_output(self, mock_analyze_chunk):
        """Test expression chunk analysis without save_output (default)"""
        mock_analyze_chunk.return_value = []
        
        chunks = [[{"text": "Test"}]]
        
        results = self.processor.analyze_expression_chunks(chunks)
        
        assert len(results) == 1
        mock_analyze_chunk.assert_called_once()
        
        # Verify save_output defaults to False
        call_kwargs = mock_analyze_chunk.call_args.kwargs
        assert call_kwargs.get('save_output') is False
        assert call_kwargs.get('output_dir') is None

class TestVideoBatchProcessor:
    """Test VideoBatchProcessor functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.processor = VideoBatchProcessor(max_workers=2)
    
    def test_process_video_clips(self):
        """Test video clip processing"""
        video_tasks = [
            {"video_path": "/path/to/video1.mp4", "output_path": "/path/to/output1.mp4"},
            {"video_path": "/path/to/video2.mp4", "output_path": "/path/to/output2.mp4"},
            {"video_path": "/path/to/video3.mp4", "output_path": "/path/to/output3.mp4"}
        ]
        
        results = self.processor.process_video_clips(video_tasks)
        
        assert len(results) == 3
        assert all(result.success for result in results)
        assert all(result.task_id.startswith("video_") for result in results)

class TestResourceManager:
    """Test ResourceManager functionality"""
    
    def test_resource_manager_initialization(self):
        """Test resource manager initialization"""
        manager = ResourceManager()
        
        assert manager.cpu_count > 0
        assert 'total_gb' in manager.memory_info
        assert 'available_gb' in manager.memory_info
        assert 'percent_used' in manager.memory_info
    
    def test_get_optimal_workers(self):
        """Test getting optimal number of workers"""
        manager = ResourceManager()
        
        # Test different task types
        cpu_workers = manager.get_optimal_workers("cpu_intensive")
        io_workers = manager.get_optimal_workers("io_intensive")
        mixed_workers = manager.get_optimal_workers("mixed")
        
        assert cpu_workers > 0
        assert io_workers > 0
        assert mixed_workers > 0
        
        # IO intensive should allow more workers than CPU intensive
        assert io_workers >= cpu_workers
    
    def test_get_memory_limit_per_worker(self):
        """Test getting memory limit per worker"""
        manager = ResourceManager()
        
        memory_limit = manager.get_memory_limit_per_worker()
        assert memory_limit > 0
        assert isinstance(memory_limit, float)

class TestGlobalFunctions:
    """Test global functions"""
    
    def test_get_resource_manager(self):
        """Test getting global resource manager"""
        manager = get_resource_manager()
        assert isinstance(manager, ResourceManager)
    
    def test_get_expression_processor(self):
        """Test getting global expression processor"""
        processor = get_expression_processor()
        assert isinstance(processor, ExpressionBatchProcessor)
    
    def test_get_video_processor(self):
        """Test getting global video processor"""
        processor = get_video_processor()
        assert isinstance(processor, VideoBatchProcessor)
    
    @patch('langflix.core.parallel_processor.get_expression_processor')
    def test_process_expressions_parallel(self, mock_get_processor):
        """Test process_expressions_parallel convenience function"""
        mock_processor = Mock()
        mock_processor.analyze_expression_chunks.return_value = [["result1"], ["result2"]]
        mock_get_processor.return_value = mock_processor
        
        chunks = [["chunk1"], ["chunk2"]]
        results = process_expressions_parallel(chunks, "intermediate", "ko")
        
        assert results == [["result1"], ["result2"]]
        mock_processor.analyze_expression_chunks.assert_called_once_with(
            chunks, "intermediate", "ko", False, None, None
        )
    
    @patch('langflix.core.parallel_processor.get_expression_processor')
    def test_process_expressions_parallel_with_save_output(self, mock_get_processor):
        """Test process_expressions_parallel with save_output parameter"""
        mock_processor = Mock()
        mock_processor.analyze_expression_chunks.return_value = [["result1"]]
        mock_get_processor.return_value = mock_processor
        
        chunks = [["chunk1"]]
        results = process_expressions_parallel(
            chunks, 
            language_level="intermediate", 
            language_code="ko",
            save_output=True,
            output_dir="/tmp/output"
        )
        
        assert results == [["result1"]]
        mock_processor.analyze_expression_chunks.assert_called_once_with(
            chunks, "intermediate", "ko", True, "/tmp/output", None
        )

class TestIntegration:
    """Integration tests"""
    
    def test_end_to_end_processing(self):
        """Test end-to-end processing workflow"""
        processor = ParallelProcessor(max_workers=2)
        
        def process_item(item):
            return f"processed_{item}"
        
        tasks = [
            ProcessingTask(
                task_id=f"item_{i}",
                function=process_item,
                args=(i,),
                kwargs={}
            )
            for i in range(10)
        ]
        
        results = processor.process_batch(tasks)
        
        assert len(results) == 10
        assert all(result.success for result in results)
        assert all(result.result == f"processed_{i}" for i, result in enumerate(results))
    
    def test_error_handling_in_batch(self):
        """Test error handling in batch processing"""
        processor = ParallelProcessor(max_workers=2)
        
        def good_function(x):
            return x * 2
        
        def bad_function(x):
            if x == 3:
                raise ValueError("Bad value")
            return x * 2
        
        tasks = [
            ProcessingTask(
                task_id=f"task_{i}",
                function=good_function if i != 3 else bad_function,
                args=(i,),
                kwargs={}
            )
            for i in range(5)
        ]
        
        results = processor.process_batch(tasks)
        
        assert len(results) == 5
        
        # Check successful results
        for i, result in enumerate(results):
            if i != 3:
                assert result.success is True
                assert result.result == i * 2
            else:
                assert result.success is False
                assert isinstance(result.error, ValueError)
