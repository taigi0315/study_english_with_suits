"""
Batch Queue Service
Manages batch video processing with queue-based sequential execution.
"""

import logging
import os
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from langflix.core.redis_client import get_redis_job_manager

logger = logging.getLogger(__name__)


class BatchQueueService:
    """Manages batch video processing queue."""
    
    MAX_BATCH_SIZE = 50  # Maximum videos per batch
    
    def __init__(self):
        """Initialize batch queue service."""
        self.redis_manager = get_redis_job_manager()
    
    def create_batch(
        self,
        videos: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a batch with multiple videos.
        
        Args:
            videos: List of video dictionaries, each containing:
                - video_path: Path to video file
                - subtitle_path: Path to subtitle file (optional)
                - episode_name: Episode name
                - show_name: Show name (optional, defaults to "Suits")
            config: Batch configuration containing:
                - language_code: Target language code
                - language_level: Language level (beginner/intermediate/advanced/mixed)
                - test_mode: Test mode flag (optional)
                - max_expressions: Maximum expressions per video (optional, default 50)
                - no_shorts: Skip short videos flag (optional, default False)
                - output_dir: Output directory (optional, default "output")
        
        Returns:
            Dictionary with batch_id and job information
            
        Raises:
            ValueError: If batch size exceeds maximum or invalid input
        """
        # Validate batch size
        if len(videos) > self.MAX_BATCH_SIZE:
            raise ValueError(f"Batch size {len(videos)} exceeds maximum {self.MAX_BATCH_SIZE}")
        
        if len(videos) == 0:
            raise ValueError("Cannot create batch with no videos")
        
        # Generate batch ID
        batch_id = str(uuid.uuid4())
        
        # Extract configuration
        language_code = config.get('language_code')
        language_level = config.get('language_level', 'intermediate')
        test_mode = config.get('test_mode', False)
        max_expressions = config.get('max_expressions', 50)
        no_shorts = config.get('no_shorts', False)
        output_dir = config.get('output_dir', 'output')
        
        if not language_code:
            raise ValueError("language_code is required in config")
        
        # Create jobs for each video
        job_list = []
        for video in videos:
            job_id = str(uuid.uuid4())
            
            # Extract episode/show name
            episode_name = video.get('episode_name')
            if not episode_name:
                # Extract from video path
                episode_name = os.path.splitext(os.path.basename(video.get('video_path', '')))[0]
            
            show_name = video.get('show_name', 'Suits')
            video_path = video.get('video_path')
            subtitle_path = video.get('subtitle_path', '')
            
            if not video_path:
                logger.warning(f"Skipping video with no video_path in batch {batch_id}")
                continue
            
            # Create job data (similar to existing job structure)
            job_data = {
                "job_id": job_id,
                "status": "QUEUED",  # Start as QUEUED, not PROCESSING
                "batch_id": batch_id,
                "video_file": os.path.basename(video_path),
                "subtitle_file": os.path.basename(subtitle_path) if subtitle_path else "",
                "video_path": video_path,
                "subtitle_path": subtitle_path,
                "language_code": language_code,
                "show_name": show_name,
                "episode_name": episode_name,
                "max_expressions": str(max_expressions),
                "language_level": language_level,
                "test_mode": str(test_mode),
                "no_shorts": str(no_shorts),
                "output_dir": output_dir,
                "progress": "0",
                "error": ""
            }
            
            # Store job in Redis
            self.redis_manager.create_job(job_id, job_data)
            
            # Add to queue
            self.redis_manager.add_job_to_queue(job_id)
            
            job_list.append({
                "job_id": job_id,
                "video_path": video_path,
                "subtitle_path": subtitle_path,
                "episode_name": episode_name,
                "show_name": show_name
            })
            
            logger.info(f"Created job {job_id} for {episode_name} in batch {batch_id}")
        
        # Create batch record
        batch_config = {
            "language_code": language_code,
            "language_level": language_level,
            "test_mode": test_mode,
            "max_expressions": max_expressions,
            "no_shorts": no_shorts,
            "output_dir": output_dir
        }
        
        # Prepare videos list for batch storage (simplified)
        batch_videos = [{"job_id": j["job_id"]} for j in job_list]
        
        self.redis_manager.create_batch(batch_id, batch_videos, batch_config)
        
        logger.info(f"✅ Created batch {batch_id} with {len(job_list)} jobs")
        
        return {
            "batch_id": batch_id,
            "total_jobs": len(job_list),
            "jobs": job_list,
            "status": "PENDING"
        }
    
    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Get batch status with all job details.
        
        Args:
            batch_id: Batch identifier
            
        Returns:
            Dictionary with batch status and job details, or None if not found
        """
        batch_data = self.redis_manager.get_batch_status(batch_id)
        
        if not batch_data:
            return None
        
        # Calculate batch status from job statuses
        jobs = batch_data.get('job_details', [])
        if not jobs:
            return batch_data
        
        batch_status = self.calculate_batch_status(jobs)
        
        # Update batch status if changed
        if batch_data.get('status') != batch_status:
            completed_count = sum(1 for j in jobs if j.get('status') == 'COMPLETED')
            failed_count = sum(1 for j in jobs if j.get('status') == 'FAILED')
            
            self.redis_manager.update_batch_status(batch_id, {
                "status": batch_status,
                "completed_jobs": str(completed_count),
                "failed_jobs": str(failed_count)
            })
            batch_data['status'] = batch_status
            batch_data['completed_jobs'] = completed_count
            batch_data['failed_jobs'] = failed_count
        
        return batch_data
    
    @staticmethod
    def calculate_batch_status(jobs: List[Dict[str, Any]]) -> str:
        """
        Calculate batch status from individual job statuses.
        
        Status priority:
        - COMPLETED: All jobs completed successfully
        - FAILED: All jobs failed
        - PARTIALLY_FAILED: Some succeeded, some failed
        - PROCESSING: At least one job is QUEUED or PROCESSING
        - PENDING: All jobs are QUEUED (not yet started)
        
        Args:
            jobs: List of job dictionaries with 'status' field
            
        Returns:
            Batch status string
        """
        if not jobs:
            return "PENDING"
        
        statuses = [job.get('status', 'UNKNOWN') for job in jobs]
        
        # Check if all completed
        if all(s == 'COMPLETED' for s in statuses):
            return 'COMPLETED'
        
        # Check if all failed
        if all(s == 'FAILED' for s in statuses):
            return 'FAILED'
        
        # Check if partially failed (mix of completed and failed, no processing/queued)
        if any(s == 'FAILED' for s in statuses) and any(s == 'COMPLETED' for s in statuses) and not any(s in ('PROCESSING', 'QUEUED') for s in statuses):
            return 'PARTIALLY_FAILED'
        
        # Check if all are QUEUED (pending - not yet started)
        if all(s == 'QUEUED' for s in statuses):
            return 'PENDING'
        
        # Check if any are still processing or queued (and not all QUEUED)
        if any(s in ('PROCESSING', 'QUEUED') for s in statuses):
            return 'PROCESSING'
        
        # Unknown state
        return 'UNKNOWN'

