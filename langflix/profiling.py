"""
Pipeline profiling instrumentation for LangFlix.

TICKET-037: Provides structured profiling and performance measurement
for the video processing pipeline.

This module implements:
- PipelineProfiler: Collects and stores profiling data
- profile_stage: Context manager for timing pipeline stages
- JSON report generation for performance analysis
"""

import json
import logging
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class PipelineProfiler:
    """
    Collects and stores profiling data for pipeline stages.
    
    TICKET-037: Implements structured profiling with JSON report generation
    for performance analysis and optimization tracking.
    """
    
    def __init__(self, output_path: Optional[Path] = None):
        """
        Initialize pipeline profiler.
        
        Args:
            output_path: Optional path to save JSON report. If None, uses default
                        profiles/<timestamp>.json
        """
        self.stages: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        
        # Set output path
        if output_path:
            self.output_path = Path(output_path)
        else:
            # Default: output/profiling/<timestamp>.json
            profiles_dir = Path("output/profiling")
            profiles_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_path = profiles_dir / f"profile_{timestamp}.json"
        
        # Ensure output directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"PipelineProfiler initialized, output: {self.output_path}")
    
    def start(self, metadata: Optional[Dict[str, Any]] = None):
        """
        Start profiling session.
        
        Args:
            metadata: Optional metadata to include in report (e.g., input files, config)
        """
        self.start_time = perf_counter()
        self.metadata = metadata or {}
        self.metadata['start_timestamp'] = datetime.now().isoformat()
        logger.info("Pipeline profiling started")
    
    def record(
        self,
        stage_name: str,
        duration_sec: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record a pipeline stage with timing information.
        
        Args:
            stage_name: Name of the pipeline stage
            duration_sec: Duration in seconds
            metadata: Optional additional metadata (e.g., counts, cache hits)
        """
        stage_data = {
            "stage": stage_name,
            "duration_sec": round(duration_sec, 4),
            "metadata": metadata or {}
        }
        self.stages.append(stage_data)
        
        debug_extra = {"stage": stage_name, "duration_sec": duration_sec}
        if metadata:
            debug_extra.update(metadata)
        logger.debug(
            f"PROFILE_STAGE: {stage_name} took {duration_sec:.4f}s",
            extra=debug_extra
        )
    
    def stop(self):
        """Stop profiling session and calculate total duration."""
        if self.start_time is None:
            logger.warning("Profiler stop() called without start()")
            return
        
        self.end_time = perf_counter()
        total_duration = self.end_time - self.start_time
        self.metadata['end_timestamp'] = datetime.now().isoformat()
        self.metadata['total_duration_sec'] = round(total_duration, 4)
        
        logger.info(f"Pipeline profiling stopped, total duration: {total_duration:.4f}s")
    
    def save_report(self) -> Path:
        """
        Save profiling report to JSON file.
        
        Returns:
            Path to saved report file
            
        Raises:
            IOError: If file cannot be written
        """
        if self.start_time is None:
            logger.warning("Cannot save report: profiling not started")
            return self.output_path
        
        # Build report structure
        report = {
            "metadata": self.metadata,
            "stages": self.stages,
            "summary": self._generate_summary()
        }
        
        try:
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Profiling report saved to: {self.output_path}")
            return self.output_path
            
        except IOError as e:
            logger.error(f"Failed to save profiling report: {e}")
            raise
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics from recorded stages."""
        if not self.stages:
            return {}
        
        durations = [stage['duration_sec'] for stage in self.stages]
        total_stage_time = sum(durations)
        
        # Find slowest stage
        slowest = max(self.stages, key=lambda s: s['duration_sec'])
        
        return {
            "total_stages": len(self.stages),
            "total_stage_duration_sec": round(total_stage_time, 4),
            "slowest_stage": {
                "name": slowest['stage'],
                "duration_sec": slowest['duration_sec']
            },
            "average_stage_duration_sec": round(total_stage_time / len(self.stages), 4) if self.stages else 0
        }
    
    def get_report(self) -> Dict[str, Any]:
        """
        Get profiling report as dictionary (without saving).
        
        Returns:
            Dictionary with profiling data
        """
        return {
            "metadata": self.metadata,
            "stages": self.stages,
            "summary": self._generate_summary()
        }


@contextmanager
def profile_stage(
    name: str,
    profiler: Optional[PipelineProfiler] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Context manager for profiling a pipeline stage.
    
    TICKET-037: Provides easy-to-use timing instrumentation for pipeline stages.
    
    Usage:
        with profile_stage("parse_subtitles", profiler):
            # Stage code here
            result = parse_subtitles()
    
    Args:
        name: Name of the pipeline stage
        profiler: Optional PipelineProfiler instance to record timing
        metadata: Optional metadata to include in stage record
        
    Yields:
        None (context manager)
    """
    start = perf_counter()
    
    # Log stage start
    logger.debug(f"PROFILE_STAGE_START: {name}")
    
    try:
        yield
    finally:
        duration = perf_counter() - start
        
        # Record in profiler if provided
        if profiler:
            try:
                profiler.record(name, duration, metadata)
            except Exception as e:
                logger.warning(f"Failed to record profiling data for {name}: {e}")
        
        # Always log PROFILE_STAGE event for structured logging
        # Include duration in message for better visibility
        duration_str = f"{duration:.4f}s"
        log_extra = {"stage": name, "duration_sec": round(duration, 4)}
        if metadata:
            log_extra.update(metadata)
            metadata_str = ", ".join([f"{k}={v}" for k, v in metadata.items()])
            logger.info(f"PROFILE_STAGE: {name} took {duration_str} ({metadata_str})", extra=log_extra)
        else:
            logger.info(f"PROFILE_STAGE: {name} took {duration_str}", extra=log_extra)

