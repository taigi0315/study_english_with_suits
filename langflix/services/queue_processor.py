"""
Queue Processor
Sequentially processes jobs from Redis queue.
"""

import asyncio
import logging
import os
from typing import Optional
from datetime import datetime, timezone, timedelta

from langflix.core.redis_client import get_redis_job_manager
from langflix.utils.temp_file_manager import get_temp_manager
from langflix.core.error_handler import handle_error, ErrorContext
from langflix.settings import get_short_video_max_duration

logger = logging.getLogger(__name__)


class QueueProcessor:
    """
    Processes jobs from Redis queue sequentially.
    Only one instance should run at a time (enforced via Redis lock).
    """
    
    POLL_INTERVAL = 1.0  # Seconds to wait when queue is empty
    PROCESSING_POLL_INTERVAL = 2.0  # Seconds to wait when job is processing
    LOCK_RENEWAL_INTERVAL = 1800.0  # Renew lock every 30 minutes
    JOB_TIMEOUT_HOURS = 1  # Jobs processing >1 hour are considered stuck
    
    def __init__(self):
        """Initialize queue processor."""
        self.redis_manager = get_redis_job_manager()
        self._running = False
        self._current_task: Optional[asyncio.Task] = None
        self._lock_renewal_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """
        Start the queue processor loop.
        Runs until explicitly stopped or cancelled.
        """
        # Try to acquire processor lock
        if not self.redis_manager.acquire_processor_lock():
            logger.warning("⚠️ Processor lock already held, another instance may be running")
            logger.info("Queue processor not started (lock unavailable)")
            return
        
        self._running = True
        logger.info("🚀 Queue processor started")
        
        # Start lock renewal task
        self._lock_renewal_task = asyncio.create_task(self._renew_lock_loop())
        
        # Recover stuck jobs on startup
        await self._recover_stuck_jobs()
        
        try:
            while self._running:
                # Check if any job is currently processing
                current_job = self.redis_manager.get_currently_processing_job()
                
                if current_job:
                    # Job is processing, wait and check again
                    logger.debug(f"Job {current_job} is processing, waiting...")
                    await asyncio.sleep(self.PROCESSING_POLL_INTERVAL)
                    continue
                
                # No job processing, try to get next from queue
                
                # Check for rate limiting (e.g. 1 job per 24h)
                interval_hours = float(os.getenv('JOB_INTERVAL_HOURS', '0'))
                if interval_hours > 0:
                    last_completion = self.redis_manager.get_last_job_completion_time()
                    if last_completion:
                        # Ensure timezone awareness
                        if last_completion.tzinfo is None:
                            last_completion = last_completion.replace(tzinfo=timezone.utc)
                        
                        elapsed = datetime.now(timezone.utc) - last_completion
                        required_wait = timedelta(hours=interval_hours)
                        
                        if elapsed < required_wait:
                            remaining = (required_wait - elapsed).total_seconds()
                            hours_remaining = remaining / 3600
                            
                            # Only log occasionally to avoid spamming
                            logger.info(f"⏳ Daily Quota Limit: Waiting {hours_remaining:.2f} hours for next slot (Interval: {interval_hours}h)")
                            
                            # Report status
                            self.redis_manager.set_processor_status('waiting', {
                                'reason': 'quota_limit',
                                'message': f"Daily Limit: Waiting {hours_remaining:.2f}h",
                                'next_run': (datetime.now(timezone.utc) + timedelta(seconds=remaining)).isoformat(),
                                'interval_hours': interval_hours
                            })
                            
                            # Sleep for 5 minutes or remaining time, whichever is smaller
                            # This allows checking for shutdown signals
                            await asyncio.sleep(min(300, remaining))
                            continue

                next_job_id = self.redis_manager.get_next_job_from_queue()
                
                if next_job_id:
                    # Try to claim the job (atomic lock)
                    if self.redis_manager.mark_job_processing(next_job_id):
                        # Successfully claimed, process it
                        logger.info(f"📦 Processing job {next_job_id} from queue (queue length: {self.redis_manager.get_queue_length()})")
                        
                        # Report status
                        self.redis_manager.set_processor_status('processing', {
                            'job_id': next_job_id,
                            'message': f"Processing job {next_job_id}"
                        })
                        
                        try:
                            await self._process_job(next_job_id)
                            logger.info(f"✅ Job {next_job_id} completed successfully")
                        except Exception as e:
                            logger.error(f"❌ Error processing job {next_job_id}: {e}", exc_info=True)
                            # Mark job as failed
                            try:
                                self.redis_manager.update_job(next_job_id, {
                                    "status": "FAILED",
                                    "error": f"Processing error: {str(e)}",
                                    "failed_at": datetime.now(timezone.utc).isoformat()
                                })
                                self.redis_manager.remove_from_processing()
                            except Exception as cleanup_error:
                                logger.error(f"Failed to cleanup after job {next_job_id} error: {cleanup_error}")
                    else:
                        # Failed to claim (another processor got it first)
                        logger.debug(f"⚠️ Failed to claim job {next_job_id}, may be claimed by another processor")
                else:
                    # No jobs in queue, wait
                    self.redis_manager.set_processor_status('idle', {
                        'message': "No jobs in queue"
                    })
                    await asyncio.sleep(self.POLL_INTERVAL)
                    
        except asyncio.CancelledError:
            logger.info("Queue processor cancelled")
            raise
        except Exception as e:
            logger.error(f"❌ Queue processor error: {e}", exc_info=True)
            raise
        finally:
            await self._cleanup()
    
    async def stop(self):
        """Stop the queue processor gracefully."""
        logger.info("Stopping queue processor...")
        self._running = False
        
        # Cancel lock renewal
        if self._lock_renewal_task:
            self._lock_renewal_task.cancel()
            try:
                await self._lock_renewal_task
            except asyncio.CancelledError:
                pass
        
        # Release processor lock
        self.redis_manager.release_processor_lock()
        
        # If currently processing a job, mark it as QUEUED so it can be retried
        current_job = self.redis_manager.get_currently_processing_job()
        if current_job:
            logger.info(f"Requeuing job {current_job} due to shutdown")
            self.redis_manager.update_job(current_job, {
                "status": "QUEUED"
            })
            # Re-add to queue
            self.redis_manager.add_job_to_queue(current_job)
            self.redis_manager.remove_from_processing()
        
        logger.info("✅ Queue processor stopped")
    
    async def _recover_stuck_jobs(self):
        """
        Recover stuck jobs on startup.
        Jobs in PROCESSING state for >1 hour are marked as FAILED.
        """
        logger.info("Checking for stuck jobs...")
        
        try:
            all_jobs = self.redis_manager.get_all_jobs()
            stuck_count = 0
            
            for job_id, job_data in all_jobs.items():
                if job_data.get('status') == 'PROCESSING':
                    # Check if job is stuck (processing >1 hour)
                    updated_at = job_data.get('updated_at')
                    if updated_at:
                        try:
                            updated_time = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                            time_diff = datetime.now(timezone.utc) - updated_time
                            
                            if time_diff > timedelta(hours=self.JOB_TIMEOUT_HOURS):
                                logger.warning(f"Found stuck job {job_id} (processing for {time_diff})")
                                self.redis_manager.update_job(job_id, {
                                    "status": "FAILED",
                                    "error": f"Job timeout: processing for >{self.JOB_TIMEOUT_HOURS} hour(s)",
                                    "failed_at": datetime.now(timezone.utc).isoformat()
                                })
                                stuck_count += 1
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Invalid updated_at for job {job_id}: {e}")
            
            # Clear processing marker if no job is actually processing
            current_processing = self.redis_manager.get_currently_processing_job()
            if current_processing:
                processing_job = self.redis_manager.get_job(current_processing)
                if not processing_job or processing_job.get('status') != 'PROCESSING':
                    logger.info("Clearing stale processing marker")
                    self.redis_manager.remove_from_processing()
            
            if stuck_count > 0:
                logger.info(f"Recovered {stuck_count} stuck jobs")
            else:
                logger.info("No stuck jobs found")
                
        except Exception as e:
            logger.error(f"Error recovering stuck jobs: {e}", exc_info=True)
    
    async def _process_job(self, job_id: str):
        """
        Process a single job from the queue.
        
        Args:
            job_id: Job identifier to process
        """
        try:
            # Get job data
            job_data = self.redis_manager.get_job(job_id)
            if not job_data:
                logger.error(f"Job {job_id} not found")
                self.redis_manager.remove_from_processing()
                return
            
            # Job should already be marked as PROCESSING by mark_job_processing
            # But update progress to show we're starting
            self.redis_manager.update_job(job_id, {
                "status": "PROCESSING",
                "progress": 10,
                "current_step": "Initializing video processing..."
            })
            
            # Extract job parameters
            video_path = job_data.get('video_path')
            subtitle_path = job_data.get('subtitle_path', '')
            language_code = job_data.get('language_code')
            show_name = job_data.get('show_name', 'Suits')
            episode_name = job_data.get('episode_name')
            
            # Parse numeric and boolean fields
            max_expressions = int(job_data.get('max_expressions', 50))
            language_level = job_data.get('language_level', 'intermediate')
            test_mode = job_data.get('test_mode', 'False') == 'True'
            no_shorts = job_data.get('no_shorts', 'False') == 'True'
            short_form_max_duration = float(job_data.get('short_form_max_duration', get_short_video_max_duration()))
            create_long_form = job_data.get('create_long_form', 'True') == 'True'
            create_short_form = job_data.get('create_short_form', 'True') == 'True'
            output_dir = job_data.get('output_dir', 'output')
            
            if not video_path or not os.path.exists(video_path):
                raise ValueError(f"Video file not found: {video_path}")
            
            if not subtitle_path or not os.path.exists(subtitle_path):
                raise ValueError(f"Subtitle file not found: {subtitle_path}")
            
            logger.info(f"📥 Loading video and subtitle files for job {job_id}")
            
            # Get temp file manager
            temp_manager = get_temp_manager()
            
            # Read file contents (blocking I/O - but files are small, so acceptable)
            # For large files, consider async file I/O
            def read_files():
                """Read video and subtitle files"""
                with open(video_path, 'rb') as vf:
                    video_content = vf.read()
                
                subtitle_content = b''
                if subtitle_path:
                    with open(subtitle_path, 'rb') as sf:
                        subtitle_content = sf.read()
                
                return video_content, subtitle_content
            
            # Read files (small delay acceptable for small files)
            loop = asyncio.get_event_loop()
            video_content, subtitle_content = await loop.run_in_executor(None, read_files)
            
            logger.info(f"📁 Files loaded: video={len(video_content)} bytes, subtitle={len(subtitle_content)} bytes")
            
            # Save to temp files for processing
            with temp_manager.create_temp_file(suffix='.mkv', prefix=f'{job_id}_video_') as temp_video_path:
                with temp_manager.create_temp_file(suffix='.srt', prefix=f'{job_id}_subtitle_') as temp_subtitle_path:
                    # Write file contents (blocking, but small files)
                    def write_temp_files():
                        temp_video_path.write_bytes(video_content)
                        temp_subtitle_path.write_bytes(subtitle_content)
                    
                    await loop.run_in_executor(None, write_temp_files)
                    
                    logger.info(f"🎬 Starting video processing for job {job_id}")
                    logger.info(f"   Video: {video_path}")
                    logger.info(f"   Subtitle: {subtitle_path}")
                    
                    # Progress callback wrapper for Redis updates
                    def update_progress(progress: int, message: str):
                        """Update job progress in Redis"""
                        try:
                            self.redis_manager.update_job(job_id, {
                                "progress": progress,
                                "current_step": message,
                                "updated_at": datetime.now(timezone.utc).isoformat()
                            })
                        except Exception as e:
                            logger.warning(f"Failed to update progress for job {job_id}: {e}")
                    
                    # Use unified pipeline service
                    # IMPORTANT: process_video is a synchronous blocking function
                    # We must run it in a thread executor to avoid blocking the event loop
                    from langflix.services.video_pipeline_service import VideoPipelineService
                    
                    service = VideoPipelineService(
                        language_code=language_code,
                        output_dir=output_dir
                    )
                    
                    # Process video using unified service in thread executor
                    # This prevents blocking the async event loop
                    logger.info(f"🚀 Running video pipeline in background thread for job {job_id}")
                    result = await loop.run_in_executor(
                        None,  # Use default ThreadPoolExecutor
                        lambda: service.process_video(
                            video_path=str(temp_video_path),
                            subtitle_path=str(temp_subtitle_path),
                            show_name=show_name,
                            episode_name=episode_name,
                            max_expressions=max_expressions,
                            language_level=language_level,
                            test_mode=test_mode,
                            no_shorts=no_shorts,
                            short_form_max_duration=short_form_max_duration,
                            create_long_form=create_long_form,
                            create_short_form=create_short_form,
                            progress_callback=update_progress
                        )
                    )
                    
                    logger.info(f"✅ Video processing completed for job {job_id}")
                    
                    # Update job with results
                    self.redis_manager.update_job(job_id, {
                        "status": "COMPLETED",
                        "progress": 100,
                        "current_step": "Completed successfully!",
                        "expressions": result.get("expressions", []),
                        "educational_videos": result.get("educational_videos", []),
                        "short_videos": result.get("short_videos", []),
                        "final_video": result.get("final_video"),
                        "completed_at": datetime.now(timezone.utc).isoformat()
                    })
                    
                    # Invalidate video cache since new videos were created
                    logger.info("Invalidating video cache after job completion...")
                    self.redis_manager.invalidate_video_cache()
                    
                    # Set last completion time for rate limiting
                    self.redis_manager.set_last_job_completion_time()
                    
                    logger.info(f"✅ Completed processing for job {job_id}")
                    # Temp files automatically cleaned up when context exits
            
            # Remove from processing marker
            self.redis_manager.remove_from_processing()
            
            # Update batch status if this job is part of a batch
            batch_id = job_data.get('batch_id')
            if batch_id:
                from langflix.services.batch_queue_service import BatchQueueService
                batch_service = BatchQueueService()
                batch_service.get_batch_status(batch_id)  # This will recalculate and update status
            
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}", exc_info=True)
            
            # Report error to error handler
            error_context = ErrorContext(
                operation="queue_process_job",
                component="services.queue_processor",
                additional_data={
                    "job_id": job_id,
                    "video_path": job_data.get('video_path') if 'job_data' in locals() else None
                }
            )
            handle_error(e, error_context, retry=False, fallback=False)
            
            # Update job with error
            self.redis_manager.update_job(job_id, {
                "status": "FAILED",
                "error": str(e),
                "failed_at": datetime.now(timezone.utc).isoformat()
            })
            
            # Remove from processing marker
            self.redis_manager.remove_from_processing()
            
            # Update batch status if this job is part of a batch
            if 'job_data' in locals() and job_data.get('batch_id'):
                from langflix.services.batch_queue_service import BatchQueueService
                batch_service = BatchQueueService()
                batch_service.get_batch_status(job_data['batch_id'])
    
    async def _renew_lock_loop(self):
        """Periodically renew processor lock to prevent expiration."""
        try:
            while self._running:
                await asyncio.sleep(self.LOCK_RENEWAL_INTERVAL)
                if self._running:
                    success = self.redis_manager.renew_processor_lock()
                    if success:
                        logger.debug("Processor lock renewed")
                    else:
                        logger.warning("Failed to renew processor lock")
        except asyncio.CancelledError:
            logger.debug("Lock renewal task cancelled")
            raise
    
    async def _cleanup(self):
        """Cleanup resources on shutdown."""
        self._running = False
        if self._lock_renewal_task:
            self._lock_renewal_task.cancel()
        self.redis_manager.release_processor_lock()
        logger.info("Queue processor cleanup complete")

