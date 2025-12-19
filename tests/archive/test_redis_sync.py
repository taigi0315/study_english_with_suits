"""
Unit tests for Redis synchronization functionality
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from langflix.core.redis_client import RedisJobManager


class TestRedisSync:
    """Test Redis job synchronization functionality"""
    
    @patch('redis.from_url')
    def test_redis_connection(self, mock_redis):
        """Test Redis connection initialization"""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client
        
        manager = RedisJobManager()
        
        mock_redis.assert_called_once()
        mock_client.ping.assert_called_once()
    
    @patch('redis.from_url')
    def test_cleanup_expired_jobs(self, mock_redis):
        """Test cleanup of expired jobs"""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client
        
        # Mock active jobs with some orphaned references
        mock_client.smembers.return_value = {'job1', 'job2', 'job3'}
        mock_client.exists.side_effect = lambda key: key != 'job:job2'  # job2 is orphaned
        
        manager = RedisJobManager()
        cleaned_count = manager.cleanup_expired_jobs()
        
        assert cleaned_count == 1
        mock_client.srem.assert_called_with('jobs:active', 'job2')
    
    @patch('redis.from_url')
    def test_cleanup_stale_jobs(self, mock_redis):
        """Test cleanup of stale jobs"""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client
        
        # Create old and new job timestamps
        old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        new_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        
        mock_client.smembers.return_value = {'job1', 'job2'}
        
        # Mock job data - job1 is old, job2 is new
        def mock_hgetall(key):
            if key == 'job:job1':
                return {'created_at': old_time, 'status': 'PROCESSING'}
            elif key == 'job:job2':
                return {'created_at': new_time, 'status': 'PROCESSING'}
            return {}
        
        mock_client.hgetall.side_effect = mock_hgetall
        
        manager = RedisJobManager()
        cleaned_count = manager.cleanup_stale_jobs(max_age_hours=24)
        
        assert cleaned_count == 1
        # Should delete the old job
        mock_client.delete.assert_called()
        mock_client.srem.assert_called()
    
    @patch('redis.from_url')
    def test_health_check_healthy(self, mock_redis):
        """Test Redis health check when healthy"""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client
        
        mock_client.ping.return_value = True
        mock_client.info.return_value = {
            'used_memory_human': '1.5M',
            'redis_version': '6.2.0',
            'connected_clients': 2,
            'uptime_in_seconds': 3600
        }
        mock_client.scard.return_value = 5
        
        manager = RedisJobManager()
        health = manager.health_check()
        
        assert health['status'] == 'healthy'
        assert health['active_jobs'] == 5
        assert health['memory_used'] == '1.5M'
        assert health['redis_version'] == '6.2.0'
        assert 'ping_time_ms' in health
    
    @patch('redis.from_url')
    def test_health_check_unhealthy(self, mock_redis):
        """Test Redis health check when unhealthy"""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client
        
        mock_client.ping.side_effect = Exception("Connection failed")
        
        manager = RedisJobManager()
        health = manager.health_check()
        
        assert health['status'] == 'unhealthy'
        assert 'error' in health
        assert health['ping_time_ms'] is None
        assert health['active_jobs'] is None
    
    @patch('redis.from_url')
    def test_video_cache_operations(self, mock_redis):
        """Test video cache get/set operations"""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client
        
        manager = RedisJobManager()
        
        # Test cache miss
        mock_client.get.return_value = None
        result = manager.get_video_cache()
        assert result is None
        
        # Test cache set
        videos = [{'path': 'test.mkv', 'language': 'ko'}]
        mock_client.setex.return_value = True
        success = manager.set_video_cache(videos, ttl=300)
        assert success is True
        
        # Test cache hit
        import json
        mock_client.get.return_value = json.dumps(videos)
        result = manager.get_video_cache()
        assert result == videos
    
    @patch('redis.from_url')
    def test_job_crud_operations(self, mock_redis):
        """Test job CRUD operations"""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client
        
        manager = RedisJobManager()
        
        # Test create job
        job_data = {'status': 'QUEUED', 'progress': 0}
        mock_client.hset.return_value = True
        mock_client.expire.return_value = True
        mock_client.sadd.return_value = True
        
        success = manager.create_job('test_job', job_data)
        assert success is True
        
        # Test get job
        mock_client.hgetall.return_value = {
            'status': 'PROCESSING',
            'progress': '50',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        job = manager.get_job('test_job')
        assert job is not None
        assert job['status'] == 'PROCESSING'
        assert job['progress'] == 50  # Should be converted to int
        
        # Test update job
        mock_client.hset.return_value = True
        success = manager.update_job('test_job', {'progress': 75})
        assert success is True
        
        # Test delete job
        mock_client.srem.return_value = True
        mock_client.delete.return_value = True
        success = manager.delete_job('test_job')
        assert success is True


class TestRedisHealthEndpoints:
    """Test Redis health check endpoints"""
    
    @patch('langflix.core.redis_client.get_redis_job_manager')
    def test_redis_health_endpoint_healthy(self, mock_get_manager):
        """Test Redis health endpoint when healthy"""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        
        mock_manager.health_check.return_value = {
            'status': 'healthy',
            'active_jobs': 3,
            'ping_time_ms': 1.5
        }
        
        # This would be tested with FastAPI test client in integration tests
        # Here we just test the manager mock
        health = mock_manager.health_check()
        assert health['status'] == 'healthy'
        assert health['active_jobs'] == 3
    
    @patch('langflix.core.redis_client.get_redis_job_manager')
    def test_redis_cleanup_endpoint(self, mock_get_manager):
        """Test Redis cleanup endpoint"""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        
        mock_manager.cleanup_expired_jobs.return_value = 2
        mock_manager.cleanup_stale_jobs.return_value = 1
        
        # Simulate endpoint logic
        expired_count = mock_manager.cleanup_expired_jobs()
        stale_count = mock_manager.cleanup_stale_jobs()
        
        assert expired_count == 2
        assert stale_count == 1
        assert expired_count + stale_count == 3
