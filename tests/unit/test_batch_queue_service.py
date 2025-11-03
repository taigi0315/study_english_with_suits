"""
Unit tests for BatchQueueService
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from langflix.services.batch_queue_service import BatchQueueService


class TestBatchQueueService:
    """Test BatchQueueService functionality"""
    
    @pytest.fixture
    def mock_redis_manager(self):
        """Create a mock Redis job manager"""
        mock_manager = Mock()
        mock_manager.create_job = Mock(return_value=True)
        mock_manager.add_job_to_queue = Mock(return_value=True)
        mock_manager.create_batch = Mock(return_value=True)
        return mock_manager
    
    @pytest.fixture
    def batch_service(self, mock_redis_manager):
        """Create BatchQueueService with mocked Redis manager"""
        with patch('langflix.services.batch_queue_service.get_redis_job_manager', return_value=mock_redis_manager):
            service = BatchQueueService()
            return service
    
    @pytest.fixture
    def sample_config(self):
        """Sample batch configuration"""
        return {
            'language_code': 'ko',
            'language_level': 'intermediate',
            'test_mode': False,
            'max_expressions': 50,
            'no_shorts': False,
            'output_dir': 'output'
        }
    
    @pytest.fixture
    def sample_videos(self):
        """Sample video list"""
        return [
            {
                'video_path': '/path/to/video1.mp4',
                'subtitle_path': '/path/to/subtitle1.srt',
                'episode_name': 'Episode 1',
                'show_name': 'Suits'
            },
            {
                'video_path': '/path/to/video2.mp4',
                'subtitle_path': '/path/to/subtitle2.srt',
                'episode_name': 'Episode 2',
                'show_name': 'Suits'
            }
        ]
    
    def test_create_batch_with_episode_names(self, batch_service, sample_config, sample_videos):
        """Test batch creation when episode_name is provided"""
        result = batch_service.create_batch(sample_videos, sample_config)
        
        assert 'batch_id' in result
        assert result['total_jobs'] == 2
        assert len(result['jobs']) == 2
        assert result['status'] == 'PENDING'
        
        # Verify Redis manager was called correctly
        assert batch_service.redis_manager.create_job.call_count == 2
        assert batch_service.redis_manager.add_job_to_queue.call_count == 2
        assert batch_service.redis_manager.create_batch.call_count == 1
    
    def test_create_batch_without_episode_names(self, batch_service, sample_config):
        """Test batch creation when episode_name is not provided (should extract from path)"""
        videos = [
            {
                'video_path': '/path/to/Suits.S01E01.720p.mkv',
                'subtitle_path': '/path/to/subtitle1.srt',
                'show_name': 'Suits'
                # episode_name not provided
            },
            {
                'video_path': '/path/to/video2.mp4',
                'subtitle_path': '/path/to/subtitle2.srt'
                # episode_name not provided
            }
        ]
        
        result = batch_service.create_batch(videos, sample_config)
        
        assert 'batch_id' in result
        assert result['total_jobs'] == 2
        
        # Verify episode_name was extracted from path
        calls = batch_service.redis_manager.create_job.call_args_list
        assert len(calls) == 2
        
        # Check first job - should extract "Suits.S01E01.720p" from path
        first_job_data = calls[0][0][1]  # Second argument is job_data dict
        assert first_job_data['episode_name'] == 'Suits.S01E01.720p'
        
        # Check second job - should extract "video2" from path
        second_job_data = calls[1][0][1]
        assert second_job_data['episode_name'] == 'video2'
    
    def test_create_batch_with_mixed_episode_names(self, batch_service, sample_config):
        """Test batch creation with some videos having episode_name and some not"""
        videos = [
            {
                'video_path': '/path/to/video1.mp4',
                'subtitle_path': '/path/to/subtitle1.srt',
                'episode_name': 'Custom Episode 1',  # Provided
                'show_name': 'Suits'
            },
            {
                'video_path': '/path/to/Suits.S01E02.mkv',
                'subtitle_path': '/path/to/subtitle2.srt'
                # episode_name not provided - should extract
            }
        ]
        
        result = batch_service.create_batch(videos, sample_config)
        
        assert result['total_jobs'] == 2
        
        # Verify first job uses provided episode_name
        calls = batch_service.redis_manager.create_job.call_args_list
        first_job_data = calls[0][0][1]
        assert first_job_data['episode_name'] == 'Custom Episode 1'
        
        # Verify second job extracts episode_name from path
        second_job_data = calls[1][0][1]
        assert second_job_data['episode_name'] == 'Suits.S01E02'
    
    def test_create_batch_exceeds_max_size(self, batch_service, sample_config):
        """Test batch creation fails when exceeding maximum batch size"""
        videos = [
            {
                'video_path': f'/path/to/video{i}.mp4',
                'subtitle_path': f'/path/to/subtitle{i}.srt',
                'episode_name': f'Episode {i}'
            }
            for i in range(51)  # Exceeds MAX_BATCH_SIZE of 50
        ]
        
        with pytest.raises(ValueError, match="exceeds maximum"):
            batch_service.create_batch(videos, sample_config)
    
    def test_create_batch_empty_videos(self, batch_service, sample_config):
        """Test batch creation fails with empty video list"""
        with pytest.raises(ValueError, match="Cannot create batch with no videos"):
            batch_service.create_batch([], sample_config)
    
    def test_create_batch_missing_language_code(self, batch_service, sample_videos):
        """Test batch creation fails when language_code is missing"""
        config = {
            'language_level': 'intermediate'
            # language_code missing
        }
        
        with pytest.raises(ValueError, match="language_code is required"):
            batch_service.create_batch(sample_videos, config)
    
    def test_create_batch_video_without_path(self, batch_service, sample_config):
        """Test batch creation skips videos without video_path"""
        videos = [
            {
                'episode_name': 'Episode 1',
                'subtitle_path': '/path/to/subtitle1.srt'
                # video_path missing
            },
            {
                'video_path': '/path/to/video2.mp4',
                'subtitle_path': '/path/to/subtitle2.srt',
                'episode_name': 'Episode 2'
            }
        ]
        
        result = batch_service.create_batch(videos, sample_config)
        
        # Should only create 1 job (second video)
        assert result['total_jobs'] == 1
        assert batch_service.redis_manager.create_job.call_count == 1
    
    def test_create_batch_with_empty_subtitle_path(self, batch_service, sample_config):
        """Test batch creation handles empty subtitle_path"""
        videos = [
            {
                'video_path': '/path/to/video1.mp4',
                'subtitle_path': '',  # Empty
                'episode_name': 'Episode 1'
            }
        ]
        
        result = batch_service.create_batch(videos, sample_config)
        
        assert result['total_jobs'] == 1
        calls = batch_service.redis_manager.create_job.call_args_list
        job_data = calls[0][0][1]
        
        # subtitle_file should be empty string, not crash
        assert job_data['subtitle_file'] == ''
        assert job_data['subtitle_path'] == ''
    
    def test_create_batch_job_data_structure(self, batch_service, sample_config, sample_videos):
        """Test that job data has correct structure"""
        result = batch_service.create_batch(sample_videos, sample_config)
        
        calls = batch_service.redis_manager.create_job.call_args_list
        job_data = calls[0][0][1]  # First job's data
        
        # Verify all required fields are present
        assert 'job_id' in job_data
        assert job_data['status'] == 'QUEUED'
        assert 'batch_id' in job_data
        assert job_data['batch_id'] == result['batch_id']
        assert 'video_file' in job_data
        assert 'subtitle_file' in job_data
        assert 'video_path' in job_data
        assert 'subtitle_path' in job_data
        assert 'language_code' in job_data
        assert 'show_name' in job_data
        assert 'episode_name' in job_data
        assert 'max_expressions' in job_data
        assert 'language_level' in job_data
        assert 'test_mode' in job_data
        assert 'no_shorts' in job_data
        assert 'output_dir' in job_data
        assert 'progress' in job_data
        assert 'error' in job_data
    
    def test_calculate_batch_status_all_completed(self, batch_service):
        """Test batch status calculation - all jobs completed"""
        jobs = [
            {'status': 'COMPLETED'},
            {'status': 'COMPLETED'},
            {'status': 'COMPLETED'}
        ]
        
        status = BatchQueueService.calculate_batch_status(jobs)
        assert status == 'COMPLETED'
    
    def test_calculate_batch_status_all_failed(self, batch_service):
        """Test batch status calculation - all jobs failed"""
        jobs = [
            {'status': 'FAILED'},
            {'status': 'FAILED'}
        ]
        
        status = BatchQueueService.calculate_batch_status(jobs)
        assert status == 'FAILED'
    
    def test_calculate_batch_status_processing(self, batch_service):
        """Test batch status calculation - jobs still processing"""
        jobs = [
            {'status': 'COMPLETED'},
            {'status': 'PROCESSING'},
            {'status': 'QUEUED'}
        ]
        
        status = BatchQueueService.calculate_batch_status(jobs)
        assert status == 'PROCESSING'
    
    def test_calculate_batch_status_partially_failed(self, batch_service):
        """Test batch status calculation - partially failed"""
        jobs = [
            {'status': 'COMPLETED'},
            {'status': 'FAILED'},
            {'status': 'COMPLETED'}
        ]
        
        status = BatchQueueService.calculate_batch_status(jobs)
        assert status == 'PARTIALLY_FAILED'
    
    def test_calculate_batch_status_pending(self, batch_service):
        """Test batch status calculation - all queued"""
        jobs = [
            {'status': 'QUEUED'},
            {'status': 'QUEUED'}
        ]
        
        status = BatchQueueService.calculate_batch_status(jobs)
        assert status == 'PENDING'
    
    def test_get_batch_status_not_found(self, batch_service):
        """Test get_batch_status returns None for non-existent batch"""
        batch_service.redis_manager.get_batch_status = Mock(return_value=None)
        
        result = batch_service.get_batch_status('non-existent-batch-id')
        assert result is None
    
    def test_get_batch_status_updates_on_status_change(self, batch_service):
        """Test get_batch_status recalculates and updates batch status"""
        # Mock batch with job details
        batch_data = {
            'batch_id': 'test-batch',
            'status': 'PENDING',  # Old status
            'total_jobs': 2,
            'completed_jobs': 0,
            'failed_jobs': 0,
            'jobs': ['job1', 'job2'],
            'job_details': [
                {'status': 'COMPLETED'},
                {'status': 'COMPLETED'}
            ]
        }
        
        batch_service.redis_manager.get_batch_status = Mock(return_value=batch_data)
        batch_service.redis_manager.update_batch_status = Mock(return_value=True)
        
        result = batch_service.get_batch_status('test-batch')
        
        # Should recalculate status to COMPLETED
        assert result['status'] == 'COMPLETED'
        assert result['completed_jobs'] == 2
        
        # Should update batch status in Redis
        batch_service.redis_manager.update_batch_status.assert_called_once()
        update_call = batch_service.redis_manager.update_batch_status.call_args
        assert update_call[0][0] == 'test-batch'
        assert update_call[0][1]['status'] == 'COMPLETED'

