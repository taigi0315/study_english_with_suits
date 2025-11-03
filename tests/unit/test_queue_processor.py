"""
Unit tests for QueueProcessor
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timezone, timedelta

from langflix.services.queue_processor import QueueProcessor


class TestQueueProcessor:
    """Test QueueProcessor functionality"""
    
    @pytest.fixture
    def mock_redis_manager(self):
        """Create a mock Redis job manager"""
        mock_manager = Mock()
        mock_manager.acquire_processor_lock = Mock(return_value=True)
        mock_manager.release_processor_lock = Mock(return_value=True)
        mock_manager.renew_processor_lock = Mock(return_value=True)
        mock_manager.get_currently_processing_job = Mock(return_value=None)
        mock_manager.get_next_job_from_queue = Mock(return_value=None)
        mock_manager.mark_job_processing = Mock(return_value=True)
        mock_manager.remove_from_processing = Mock(return_value=True)
        mock_manager.get_queue_length = Mock(return_value=0)
        mock_manager.get_job = Mock(return_value=None)
        mock_manager.get_all_jobs = Mock(return_value={})
        mock_manager.update_job = Mock(return_value=True)
        mock_manager.invalidate_video_cache = Mock(return_value=True)
        return mock_manager
    
    @pytest.fixture
    def queue_processor(self, mock_redis_manager):
        """Create QueueProcessor with mocked Redis manager"""
        with patch('langflix.services.queue_processor.get_redis_job_manager', return_value=mock_redis_manager):
            processor = QueueProcessor()
            processor.redis_manager = mock_redis_manager
            return processor
    
    @pytest.mark.asyncio
    async def test_start_acquires_lock(self, queue_processor, mock_redis_manager):
        """Test that start() acquires processor lock"""
        mock_redis_manager.acquire_processor_lock.return_value = True
        
        # Start processor (will run until cancelled)
        start_task = asyncio.create_task(queue_processor.start())
        
        # Wait a bit for it to start
        await asyncio.sleep(0.1)
        
        # Stop it
        await queue_processor.stop()
        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass
        
        # Verify lock was acquired
        assert mock_redis_manager.acquire_processor_lock.called
    
    @pytest.mark.asyncio
    async def test_start_rejects_if_lock_unavailable(self, queue_processor, mock_redis_manager):
        """Test that start() exits if lock is already held"""
        mock_redis_manager.acquire_processor_lock.return_value = False
        
        await queue_processor.start()
        
        # Should not have started processing loop
        assert not queue_processor._running
    
    @pytest.mark.asyncio
    async def test_process_job_with_sync_blocking_call(self, queue_processor, mock_redis_manager):
        """Test that process_video runs in executor to prevent event loop blocking"""
        job_id = "test-job-1"
        job_data = {
            'job_id': job_id,
            'status': 'QUEUED',
            'video_path': '/path/to/video.mp4',
            'subtitle_path': '/path/to/subtitle.srt',
            'language_code': 'ko',
            'show_name': 'Suits',
            'episode_name': 'Episode 1',
            'max_expressions': 50,
            'language_level': 'intermediate',
            'test_mode': False,
            'no_shorts': False,
            'output_dir': 'output',
            'batch_id': None
        }
        
        mock_redis_manager.get_job.return_value = job_data
        
        # Mock VideoPipelineService
        mock_service = Mock()
        mock_service.process_video = Mock(return_value={
            'expressions': [],
            'educational_videos': [],
            'short_videos': [],
            'final_video': '/path/to/final.mkv'
        })
        
        # Mock temp file manager
        from unittest.mock import MagicMock
        mock_temp_manager = MagicMock()
        mock_temp_file = MagicMock()
        mock_temp_file.__enter__ = Mock(return_value=mock_temp_file)
        mock_temp_file.__exit__ = Mock(return_value=False)
        mock_temp_file.write_bytes = Mock()
        mock_temp_manager.create_temp_file = Mock(return_value=mock_temp_file)
        
        with patch('langflix.services.queue_processor.get_temp_manager', return_value=mock_temp_manager), \
             patch('langflix.services.video_pipeline_service.VideoPipelineService', return_value=mock_service), \
             patch('builtins.open', create=True), \
             patch('os.path.exists', return_value=True), \
             patch('asyncio.get_event_loop') as mock_get_loop:
            
            mock_loop = Mock()
            mock_executor_result = {
                'expressions': [],
                'educational_videos': [],
                'short_videos': [],
                'final_video': '/path/to/final.mkv'
            }
            
            async def mock_run_in_executor(executor, func):
                # Simulate executor running the function
                return func() if callable(func) else mock_executor_result
            
            mock_loop.run_in_executor = AsyncMock(side_effect=mock_run_in_executor)
            mock_get_loop.return_value = mock_loop
            
            # Process the job
            await queue_processor._process_job(job_id)
            
            # Verify process_video was called (via executor)
            # The executor call should have happened
            assert mock_loop.run_in_executor.called
    
    @pytest.mark.asyncio
    async def test_process_job_handles_missing_files(self, queue_processor, mock_redis_manager):
        """Test that process_job fails gracefully when files are missing"""
        job_id = "test-job-2"
        job_data = {
            'job_id': job_id,
            'status': 'QUEUED',
            'video_path': '/nonexistent/video.mp4',
            'subtitle_path': '/nonexistent/subtitle.srt',
            'language_code': 'ko',
            'batch_id': None
        }
        
        mock_redis_manager.get_job.return_value = job_data
        
        with patch('os.path.exists', return_value=False):
            await queue_processor._process_job(job_id)
            
            # Job should be marked as failed
            assert mock_redis_manager.update_job.called
            update_call = mock_redis_manager.update_job.call_args
            assert update_call[0][0] == job_id
            assert update_call[0][1]['status'] == 'FAILED'
    
    @pytest.mark.asyncio
    async def test_recover_stuck_jobs(self, queue_processor, mock_redis_manager):
        """Test stuck job recovery on startup"""
        # Create a stuck job (PROCESSING for >1 hour)
        stuck_job_id = "stuck-job-1"
        stuck_time = datetime.now(timezone.utc) - timedelta(hours=2)
        stuck_job_data = {
            'job_id': stuck_job_id,
            'status': 'PROCESSING',
            'updated_at': stuck_time.isoformat()
        }
        
        all_jobs = {stuck_job_id: stuck_job_data}
        mock_redis_manager.get_all_jobs.return_value = all_jobs
        mock_redis_manager.get_currently_processing_job.return_value = None
        
        await queue_processor._recover_stuck_jobs()
        
        # Verify stuck job was marked as FAILED
        assert mock_redis_manager.update_job.called
        update_call = mock_redis_manager.update_job.call_args
        assert update_call[0][0] == stuck_job_id
        assert update_call[0][1]['status'] == 'FAILED'
    
    @pytest.mark.asyncio
    async def test_stop_requeues_current_job(self, queue_processor, mock_redis_manager):
        """Test that stop() requeues currently processing job"""
        current_job_id = "current-job-1"
        mock_redis_manager.get_currently_processing_job.return_value = current_job_id
        mock_redis_manager.get_job.return_value = {'status': 'PROCESSING'}
        
        await queue_processor.stop()
        
        # Verify job was requeued
        assert mock_redis_manager.update_job.called
        assert mock_redis_manager.add_job_to_queue.called
        assert mock_redis_manager.remove_from_processing.called
    
    @pytest.mark.asyncio
    async def test_process_job_updates_batch_status(self, queue_processor, mock_redis_manager):
        """Test that completing a job updates batch status"""
        job_id = "batch-job-1"
        batch_id = "batch-1"
        job_data = {
            'job_id': job_id,
            'status': 'QUEUED',
            'video_path': '/path/to/video.mp4',
            'subtitle_path': '/path/to/subtitle.srt',
            'language_code': 'ko',
            'show_name': 'Suits',
            'episode_name': 'Episode 1',
            'max_expressions': 50,
            'language_level': 'intermediate',
            'test_mode': False,
            'no_shorts': False,
            'output_dir': 'output',
            'batch_id': batch_id
        }
        
        mock_redis_manager.get_job.return_value = job_data
        
        # Mock batch service
        mock_batch_service = Mock()
        mock_batch_service.get_batch_status = Mock(return_value={'status': 'PROCESSING'})
        
        with patch('langflix.services.queue_processor.get_temp_manager'), \
             patch('langflix.services.video_pipeline_service.VideoPipelineService'), \
             patch('builtins.open', create=True), \
             patch('os.path.exists', return_value=True), \
             patch('langflix.services.batch_queue_service.BatchQueueService', return_value=mock_batch_service), \
             patch('asyncio.get_event_loop') as mock_get_loop:
            
            mock_loop = Mock()
            async def mock_run_in_executor(executor, func):
                return {'expressions': [], 'educational_videos': [], 'short_videos': [], 'final_video': ''}
            mock_loop.run_in_executor = AsyncMock(side_effect=mock_run_in_executor)
            mock_get_loop.return_value = mock_loop
            
            await queue_processor._process_job(job_id)
            
            # Verify batch status was updated
            assert mock_batch_service.get_batch_status.called
            assert mock_batch_service.get_batch_status.call_args[0][0] == batch_id

