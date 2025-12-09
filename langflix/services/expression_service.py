import logging
import time
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

from langflix.core.models import ExpressionAnalysis
from langflix.core.expression_analyzer import analyze_chunk
from langflix.core.parallel_processor import ExpressionBatchProcessor
from langflix.core.subtitle_processor import SubtitleProcessor
from langflix import settings

logger = logging.getLogger(__name__)

class ExpressionService:
    """Service for analyzing expressions via LLM."""

    def __init__(self, language_code: str):
        self.language_code = language_code

    def analyze(
        self,
        chunks: List[List[Dict[str, Any]]],
        subtitle_processor: SubtitleProcessor,
        max_expressions: int = None,
        language_level: str = None,
        save_llm_output: bool = False,
        test_mode: bool = False,
        output_dir: Optional[Union[str, Path]] = None,
        progress_callback: Optional[callable] = None
    ) -> List[ExpressionAnalysis]:
        """
        Analyze expressions from subtitle chunks.
        
        Args:
            chunks: List of subtitle chunks.
            subtitle_processor: Processor for finding exact timings.
            max_expressions: Maximum number of expressions to return.
            language_level: Difficulty level.
            save_llm_output: Whether to save LLM outputs.
            test_mode: If true, process fewer chunks/expressions.
            output_dir: Directory to save LLM outputs.
            progress_callback: Callback for progress updates.
            
        Returns:
            List of analyzed ExpressionAnalysis objects with timings.
        """
        import time
        
        # In test mode, process only the first chunk if chunks exist
        if test_mode and chunks:
            chunks_to_process = [chunks[0]]
            logger.info("🧪 TEST MODE: Processing only first chunk")
        else:
            chunks_to_process = chunks

        parallel_enabled = settings.get_parallel_llm_processing_enabled()
        should_use_parallel = parallel_enabled and len(chunks_to_process) > 1 and not test_mode
        
        expressions = []
        if should_use_parallel:
            expressions = self._analyze_parallel(
                chunks_to_process, 
                language_level, 
                save_llm_output, 
                output_dir, 
                progress_callback
            )
        else:
            expressions = self._analyze_sequential(
                chunks_to_process, 
                max_expressions, 
                language_level, 
                save_llm_output, 
                test_mode, 
                output_dir,
                progress_callback
            )
            
        # Limit to max_expressions
        if max_expressions:
            expressions = expressions[:max_expressions]
            
        logger.info(f"Total expressions found: {len(expressions)}")
        
        # Enrich with timings
        self._enrich_timings(expressions, subtitle_processor)
        
        return expressions

    def _analyze_parallel(
        self,
        chunks: List[List[Dict[str, Any]]],
        language_level: str,
        save_llm_output: bool,
        output_dir: Optional[str],
        progress_callback: Optional[callable]
    ) -> List[ExpressionAnalysis]:
        logger.info(f"Using PARALLEL processing for {len(chunks)} chunks")
        max_workers = settings.get_parallel_llm_max_workers()
        
        # Local progress tracker
        completed_chunks = [0]
        total_chunks = len(chunks)
        
        def local_callback(completed, total):
            completed_chunks[0] = completed
            if progress_callback:
                progress_callback(completed, total)

        processor = ExpressionBatchProcessor(max_workers=max_workers)
        
        start_time = time.time()
        all_results = processor.analyze_expression_chunks(
            chunks,
            language_level=language_level,
            language_code=self.language_code,
            save_output=save_llm_output,
            output_dir=output_dir,
            progress_callback=local_callback
        )
        duration = time.time() - start_time
        logger.info(f"Parallel analysis complete in {duration:.2f}s")
        
        all_expressions = []
        for chunk_results in all_results:
            if chunk_results:
                all_expressions.extend(chunk_results)
                
        return all_expressions

    def _analyze_sequential(
        self,
        chunks: List[List[Dict[str, Any]]],
        max_expressions: int,
        language_level: str,
        save_llm_output: bool,
        test_mode: bool,
        output_dir: Optional[str],
        progress_callback: Optional[callable]
    ) -> List[ExpressionAnalysis]:
        logger.info(f"Using SEQUENTIAL processing for {len(chunks)} chunks")
        all_expressions = []
        
        for i, chunk in enumerate(chunks):
            if max_expressions is not None and len(all_expressions) >= max_expressions:
                break
                
            if progress_callback:
                progress_callback(i, len(chunks))
            
            # Rate limiting delay
            if i > 0:
                time.sleep(5)
                
            try:
                expressions = analyze_chunk(
                    chunk, 
                    language_level, 
                    self.language_code, 
                    save_llm_output, 
                    output_dir
                )
                if expressions:
                    all_expressions.extend(expressions)
            except Exception as e:
                logger.error(f"Error analyzing chunk {i+1}: {e}")
                
            if test_mode:
                break
                
        return all_expressions

    def _enrich_timings(self, expressions: List[ExpressionAnalysis], subtitle_processor: SubtitleProcessor):
        logger.info("Finding exact expression timings from subtitles...")
        for expression in expressions:
            try:
                start, end = subtitle_processor.find_expression_timing(expression)
                expression.expression_start_time = start
                expression.expression_end_time = end
            except Exception as e:
                logger.warning(f"Could not find timing for expression '{expression.expression}': {e}")
