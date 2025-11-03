"""
Parallel processing utilities for LangFlix Expression-Based Learning Feature.

This module provides:
- Concurrent expression analysis
- Parallel video processing
- Batch operations optimization
- Resource management
- Progress tracking
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
from typing import List, Dict, Any, Optional, Callable, Tuple, Union
from dataclasses import dataclass
from pathlib import Path
import multiprocessing as mp

logger = logging.getLogger(__name__)

@dataclass
class ProcessingTask:
    """Represents a processing task"""
    task_id: str
    function: Callable
    args: Tuple
    kwargs: Dict[str, Any]
    priority: int = 0
    timeout: Optional[float] = None

@dataclass
class ProcessingResult:
    """Represents the result of a processing task"""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    duration: float = 0.0

class ParallelProcessor:
    """Advanced parallel processing manager"""
    
    def __init__(
        self,
        max_workers: Optional[int] = None,
        use_processes: bool = False,
        timeout: Optional[float] = None
    ):
        """
        Initialize parallel processor
        
        Args:
            max_workers: Maximum number of workers (default: CPU count)
            use_processes: Use processes instead of threads
            timeout: Default timeout for tasks
        """
        self.max_workers = max_workers or mp.cpu_count()
        self.use_processes = use_processes
        self.timeout = timeout
        self.executor_class = ProcessPoolExecutor if use_processes else ThreadPoolExecutor
        
        logger.info(f"ParallelProcessor initialized: {self.max_workers} workers, "
                   f"processes={use_processes}")
    
    def process_batch(
        self,
        tasks: List[ProcessingTask],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[ProcessingResult]:
        """
        Process a batch of tasks in parallel
        
        Args:
            tasks: List of processing tasks
            progress_callback: Optional progress callback (completed, total)
            
        Returns:
            List of processing results
        """
        if not tasks:
            return []
        
        # Sort tasks by priority (higher priority first)
        sorted_tasks = sorted(tasks, key=lambda t: t.priority, reverse=True)
        
        results = []
        completed = 0
        
        logger.info(f"Processing {len(tasks)} tasks with {self.max_workers} workers")
        
        with self.executor_class(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {}
            for task in sorted_tasks:
                future = executor.submit(
                    self._execute_task,
                    task.function,
                    task.args,
                    task.kwargs,
                    task.timeout or self.timeout
                )
                future_to_task[future] = task
            
            # Collect results as they complete
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                start_time = time.time()
                
                try:
                    result = future.result()
                    duration = time.time() - start_time
                    
                    results.append(ProcessingResult(
                        task_id=task.task_id,
                        success=True,
                        result=result,
                        duration=duration
                    ))
                    
                    logger.debug(f"Task {task.task_id} completed successfully in {duration:.2f}s")
                    
                except Exception as e:
                    duration = time.time() - start_time
                    
                    results.append(ProcessingResult(
                        task_id=task.task_id,
                        success=False,
                        error=e,
                        duration=duration
                    ))
                    
                    logger.error(f"Task {task.task_id} failed: {e}")
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(tasks))
        
        logger.info(f"Batch processing complete: {len(results)} results")
        return results
    
    def _execute_task(
        self,
        function: Callable,
        args: Tuple,
        kwargs: Dict[str, Any],
        timeout: Optional[float]
    ) -> Any:
        """
        Execute a single task with timeout.
        
        Uses synchronous timeout mechanism suitable for ThreadPoolExecutor context.
        ThreadPoolExecutor worker threads do not have an event loop, so we cannot
        use asyncio primitives. Instead, we use Future.result(timeout) which is
        designed for synchronous threading contexts.
        
        Args:
            function: The function to execute
            args: Function arguments
            kwargs: Function keyword arguments
            timeout: Optional timeout in seconds
            
        Returns:
            Result from function execution
            
        Raises:
            TimeoutError: If task exceeds timeout (raises concurrent.futures.TimeoutError)
        """
        if timeout:
            # Use nested ThreadPoolExecutor for timeout support
            # This is necessary because Future.result(timeout) requires submitting
            # the task to an executor that supports timeout
            with ThreadPoolExecutor(max_workers=1) as timeout_executor:
                future = timeout_executor.submit(
                    self._run_task,
                    function,
                    args,
                    kwargs
                )
                try:
                    return future.result(timeout=timeout)
                except FuturesTimeoutError as e:
                    # concurrent.futures.TimeoutError is raised for timeout
                    logger.error(f"Task timed out after {timeout}s")
                    raise TimeoutError(f"Task execution exceeded {timeout}s timeout") from e
                except Exception as e:
                    # For other exceptions, re-raise as-is
                    raise
        else:
            return self._run_task(function, args, kwargs)
    
    def _run_task(
        self,
        function: Callable,
        args: Tuple,
        kwargs: Dict[str, Any]
    ) -> Any:
        """Run a task function"""
        return function(*args, **kwargs)

class ExpressionBatchProcessor:
    """Specialized processor for expression analysis batches"""
    
    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize expression batch processor
        
        Args:
            max_workers: Maximum number of workers
        """
        self.processor = ParallelProcessor(
            max_workers=max_workers,
            use_processes=False,  # Use threads for I/O bound tasks
            timeout=300  # 5 minutes timeout
        )
    
    def analyze_expression_chunks(
        self,
        chunks: List[List[Dict[str, Any]]],
        language_level: str = None,
        language_code: str = "ko",
        save_output: bool = False,
        output_dir: str = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[List[Any]]:
        """
        Analyze multiple expression chunks in parallel
        
        Args:
            chunks: List of subtitle chunks
            language_level: Target language level
            language_code: Target language code
            save_output: Whether to save LLM output to file
            output_dir: Directory to save LLM output (if save_output is True)
            progress_callback: Progress callback
            
        Returns:
            List of expression analysis results
        """
        from langflix.core.expression_analyzer import analyze_chunk
        
        # Create tasks for each chunk
        tasks = []
        for i, chunk in enumerate(chunks):
            task = ProcessingTask(
                task_id=f"chunk_{i}",
                function=analyze_chunk,
                args=(chunk, language_level, language_code),
                kwargs={"save_output": save_output, "output_dir": output_dir},
                priority=len(chunk)  # Prioritize larger chunks
            )
            tasks.append(task)
        
        # Process in parallel
        results = self.processor.process_batch(tasks, progress_callback)
        
        # Extract successful results
        successful_results = []
        for result in results:
            if result.success:
                successful_results.append(result.result)
            else:
                logger.error(f"Chunk analysis failed: {result.error}")
                successful_results.append([])  # Empty list for failed chunks
        
        return successful_results

class VideoBatchProcessor:
    """Specialized processor for video processing batches"""
    
    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize video batch processor
        
        Args:
            max_workers: Maximum number of workers
        """
        self.processor = ParallelProcessor(
            max_workers=max_workers,
            use_processes=True,  # Use processes for CPU-intensive tasks
            timeout=600  # 10 minutes timeout
        )
    
    def process_video_clips(
        self,
        video_tasks: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[ProcessingResult]:
        """
        Process multiple video clips in parallel
        
        Args:
            video_tasks: List of video processing tasks
            progress_callback: Progress callback
            
        Returns:
            List of processing results
        """
        # Create tasks for video processing
        tasks = []
        for i, task_data in enumerate(video_tasks):
            # This would be implemented based on specific video processing needs
            task = ProcessingTask(
                task_id=f"video_{i}",
                function=self._process_single_video,
                args=(task_data,),
                kwargs={},
                priority=1
            )
            tasks.append(task)
        
        return self.processor.process_batch(tasks, progress_callback)
    
    def _process_single_video(self, task_data: Dict[str, Any]) -> Any:
        """Process a single video task"""
        # Implementation would depend on specific video processing requirements
        # This is a placeholder for the actual video processing logic
        return {"status": "processed", "data": task_data}

class ResourceManager:
    """Manages system resources for parallel processing"""
    
    def __init__(self):
        """Initialize resource manager"""
        self.cpu_count = mp.cpu_count()
        self.memory_info = self._get_memory_info()
        
        logger.info(f"ResourceManager initialized: {self.cpu_count} CPUs, "
                   f"{self.memory_info['total_gb']:.1f}GB RAM")
    
    def _get_memory_info(self) -> Dict[str, Any]:
        """Get system memory information"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return {
                'total_gb': memory.total / (1024**3),
                'available_gb': memory.available / (1024**3),
                'percent_used': memory.percent
            }
        except ImportError:
            return {
                'total_gb': 8.0,  # Default assumption
                'available_gb': 4.0,
                'percent_used': 50.0
            }
    
    def get_optimal_workers(self, task_type: str = "mixed") -> int:
        """
        Get optimal number of workers for task type
        
        Args:
            task_type: Type of task (cpu_intensive, io_intensive, mixed)
            
        Returns:
            Optimal number of workers
        """
        if task_type == "cpu_intensive":
            # For CPU-intensive tasks, use fewer workers to avoid context switching
            return max(1, self.cpu_count // 2)
        elif task_type == "io_intensive":
            # For I/O-intensive tasks, can use more workers
            return min(self.cpu_count * 2, 16)
        else:  # mixed
            return self.cpu_count
    
    def get_memory_limit_per_worker(self) -> float:
        """Get memory limit per worker in GB"""
        available_memory = self.memory_info['available_gb']
        return available_memory / self.cpu_count

# Global instances
_resource_manager = ResourceManager()
_expression_processor = ExpressionBatchProcessor()
_video_processor = VideoBatchProcessor()

def get_resource_manager() -> ResourceManager:
    """Get global resource manager"""
    return _resource_manager

def get_expression_processor() -> ExpressionBatchProcessor:
    """Get global expression processor"""
    return _expression_processor

def get_video_processor() -> VideoBatchProcessor:
    """Get global video processor"""
    return _video_processor

def process_expressions_parallel(
    chunks: List[List[Dict[str, Any]]],
    language_level: str = None,
    language_code: str = "ko",
    save_output: bool = False,
    output_dir: str = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[List[Any]]:
    """
    Convenience function for parallel expression processing
    
    Args:
        chunks: List of subtitle chunks
        language_level: Target language level
        language_code: Target language code
        save_output: Whether to save LLM output to file
        output_dir: Directory to save LLM output (if save_output is True)
        progress_callback: Progress callback
        
    Returns:
        List of expression analysis results
    """
    return _expression_processor.analyze_expression_chunks(
        chunks, language_level, language_code, save_output, output_dir, progress_callback
    )
