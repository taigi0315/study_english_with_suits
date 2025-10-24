"""
Job Queue System
Simple in-memory job queue for managing async content creation tasks
"""
import uuid
import time
import threading
import queue
import logging
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job status enumeration"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    """Represents a content creation job"""
    job_id: str
    media_id: str
    video_path: str
    subtitle_path: Optional[str]
    language_code: str
    language_level: str
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0  # 0-100
    current_step: str = ""
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None


class JobQueue:
    """
    Simple in-memory job queue with background worker thread
    """
    
    def __init__(self, max_workers: int = 1):
        """
        Initialize job queue
        
        Args:
            max_workers: Number of worker threads (default: 1 for sequential processing)
        """
        self.jobs: Dict[str, Job] = {}
        self.job_queue: queue.Queue = queue.Queue()
        self.max_workers = max_workers
        self.workers: list[threading.Thread] = []
        self.running = False
        self.lock = threading.Lock()
        
    def start(self):
        """Start worker threads"""
        if self.running:
            return
        
        self.running = True
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker, name=f"JobWorker-{i}", daemon=True)
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"Started {self.max_workers} job worker(s)")
    
    def stop(self):
        """Stop worker threads"""
        self.running = False
        # Add sentinel values to unblock workers
        for _ in range(self.max_workers):
            self.job_queue.put(None)
        
        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=5)
        
        self.workers.clear()
        logger.info("Stopped all job workers")
    
    def enqueue(
        self, 
        media_id: str,
        video_path: str,
        subtitle_path: Optional[str],
        language_code: str,
        language_level: str
    ) -> str:
        """
        Enqueue a new content creation job
        
        Args:
            media_id: Unique media identifier
            video_path: Path to video file
            subtitle_path: Path to subtitle file (optional)
            language_code: Target language code (ko, ja, zh, etc.)
            language_level: Target language level (beginner, intermediate, advanced, mixed)
            
        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())
        
        job = Job(
            job_id=job_id,
            media_id=media_id,
            video_path=video_path,
            subtitle_path=subtitle_path,
            language_code=language_code,
            language_level=language_level
        )
        
        with self.lock:
            self.jobs[job_id] = job
        
        self.job_queue.put(job_id)
        logger.info(f"Enqueued job {job_id} for media {media_id}")
        
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get job by ID
        
        Args:
            job_id: Job ID
            
        Returns:
            Job object or None if not found
        """
        with self.lock:
            return self.jobs.get(job_id)
    
    def get_all_jobs(self) -> list[Job]:
        """
        Get all jobs
        
        Returns:
            List of all jobs
        """
        with self.lock:
            return list(self.jobs.values())
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job (only if queued or processing)
        
        Args:
            job_id: Job ID
            
        Returns:
            True if cancelled, False otherwise
        """
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return False
            
            if job.status in [JobStatus.QUEUED, JobStatus.PROCESSING]:
                job.status = JobStatus.CANCELLED
                job.completed_at = datetime.now()
                logger.info(f"Cancelled job {job_id}")
                return True
        
        return False
    
    def update_progress(self, job_id: str, progress: int, current_step: str):
        """
        Update job progress
        
        Args:
            job_id: Job ID
            progress: Progress percentage (0-100)
            current_step: Current step description
        """
        with self.lock:
            job = self.jobs.get(job_id)
            if job:
                job.progress = min(100, max(0, progress))
                job.current_step = current_step
                logger.debug(f"Job {job_id}: {progress}% - {current_step}")
    
    def _worker(self):
        """Background worker thread that processes jobs"""
        logger.info(f"Worker {threading.current_thread().name} started")
        
        while self.running:
            try:
                # Get job from queue (blocking with timeout)
                job_id = self.job_queue.get(timeout=1)
                
                if job_id is None:  # Sentinel value
                    break
                
                # Get job details
                with self.lock:
                    job = self.jobs.get(job_id)
                    if not job:
                        continue
                    
                    # Check if already cancelled
                    if job.status == JobStatus.CANCELLED:
                        continue
                    
                    # Mark as processing
                    job.status = JobStatus.PROCESSING
                    job.started_at = datetime.now()
                
                logger.info(f"Processing job {job_id}")
                
                try:
                    # Process the job
                    self._process_job(job)
                    
                    # Mark as completed
                    with self.lock:
                        if job.status != JobStatus.CANCELLED:
                            job.status = JobStatus.COMPLETED
                            job.progress = 100
                            job.current_step = "Completed"
                            job.completed_at = datetime.now()
                    
                    logger.info(f"Job {job_id} completed successfully")
                    
                except Exception as e:
                    logger.error(f"Job {job_id} failed: {e}", exc_info=True)
                    
                    # Mark as failed
                    with self.lock:
                        job.status = JobStatus.FAILED
                        job.error_message = str(e)
                        job.completed_at = datetime.now()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
        
        logger.info(f"Worker {threading.current_thread().name} stopped")
    
    def _process_job(self, job: Job):
        """
        Process a single job
        
        This is a placeholder that will be replaced by the actual pipeline runner
        
        Args:
            job: Job to process
        """
        # This will be implemented by PipelineRunner
        # For now, just simulate progress
        steps = [
            (10, "Parsing subtitles..."),
            (30, "Analyzing expressions..."),
            (60, "Generating videos..."),
            (80, "Creating shorts..."),
            (100, "Finalizing...")
        ]
        
        for progress, step in steps:
            if job.status == JobStatus.CANCELLED:
                break
            
            self.update_progress(job.job_id, progress, step)
            time.sleep(1)  # Simulate work
        
        # Store dummy result
        job.result = {
            "final_videos": [],
            "short_videos": [],
            "expressions_processed": 0
        }
    
    def set_job_processor(self, processor: Callable[[Job], Dict[str, Any]]):
        """
        Set custom job processor function
        
        Args:
            processor: Function that takes a Job and returns result dict
        """
        self._process_job = lambda job: setattr(job, 'result', processor(job))


# Global job queue instance
_job_queue: Optional[JobQueue] = None


def get_job_queue() -> JobQueue:
    """Get global job queue instance (singleton)"""
    global _job_queue
    if _job_queue is None:
        _job_queue = JobQueue(max_workers=1)
        _job_queue.start()
    return _job_queue

