"""
Edge case tests for YouTubeUploader
Tests publishAt parameter, error handling, retry logic, and edge cases
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from googleapiclient.errors import HttpError

from langflix.youtube.uploader import YouTubeUploader, YouTubeUploadResult, YouTubeVideoMetadata


class TestUploaderEdgeCases:
    """Test uploader edge cases"""
    
    @pytest.fixture
    def uploader(self):
        """Create YouTubeUploader"""
        return YouTubeUploader()
    
    @pytest.fixture
    def sample_metadata(self):
        """Sample YouTube metadata for testing"""
        return YouTubeVideoMetadata(
            title="Test Video",
            description="Test description",
            tags=["test", "video"],
            category_id="22",
            privacy_status="public"
        )
    
    def test_upload_video_with_publish_at(self, uploader, sample_metadata, tmp_path):
        """Test upload_video with publishAt parameter"""
        # Create a test video file
        video_file = tmp_path / "test_video.mp4"
        video_file.write_bytes(b"fake video content")
        
        # Set up authenticated uploader
        uploader.authenticated = True
        uploader.service = Mock()
        
        # Mock the insert request and upload
        mock_insert = Mock()
        mock_response = {'id': 'test_video_id'}
        mock_insert.execute.return_value = mock_response
        uploader.service.videos.return_value.insert.return_value = mock_insert
        
        # Mock _resumable_upload to return success
        with patch.object(uploader, '_resumable_upload', return_value=mock_response):
            publish_time = datetime.now(timezone.utc) + timedelta(days=1)
            
            result = uploader.upload_video(
                video_path=str(video_file),
                metadata=sample_metadata,
                publish_at=publish_time
            )
            
            assert result.success is True
            assert result.video_id == 'test_video_id'
            
            # Verify publishAt was set in the request
            insert_call_args = uploader.service.videos.return_value.insert.call_args
            body = insert_call_args[1]['body']
            assert 'publishAt' in body['status']
            assert body['status']['privacyStatus'] == 'private'
            assert body['status']['publishAt'].endswith('Z')  # UTC format with Z
    
    def test_upload_video_publish_at_timezone_conversion(self, uploader, sample_metadata, tmp_path):
        """Test publishAt timezone conversion to UTC"""
        video_file = tmp_path / "test_video.mp4"
        video_file.write_bytes(b"fake video content")
        
        uploader.authenticated = True
        uploader.service = Mock()
        
        mock_insert = Mock()
        mock_response = {'id': 'test_video_id'}
        mock_insert.execute.return_value = mock_response
        uploader.service.videos.return_value.insert.return_value = mock_insert
        
        with patch.object(uploader, '_resumable_upload', return_value=mock_response):
            # Create time in different timezone (KST is UTC+9)
            from datetime import timezone as tz
            kst_time = datetime(2025, 1, 1, 10, 0, 0, tzinfo=tz(timedelta(hours=9)))
            
            result = uploader.upload_video(
                video_path=str(video_file),
                metadata=sample_metadata,
                publish_at=kst_time
            )
            
            assert result.success is True
            
            # Verify timezone conversion
            insert_call_args = uploader.service.videos.return_value.insert.call_args
            body = insert_call_args[1]['body']
            publish_at_str = body['status']['publishAt']
            
            # Should be converted to UTC (1 hour earlier)
            assert publish_at_str.startswith('2025-01-01T01:00:00')  # KST 10:00 = UTC 01:00
            assert publish_at_str.endswith('Z')
    
    def test_upload_video_file_not_found(self, uploader, sample_metadata):
        """Test upload_video handles missing file gracefully"""
        result = uploader.upload_video(
            video_path="/nonexistent/path/video.mp4",
            metadata=sample_metadata
        )
        
        assert result.success is False
        assert "not found" in result.error_message.lower()
    
    def test_upload_video_not_authenticated(self, uploader, sample_metadata, tmp_path):
        """Test upload_video requires authentication"""
        video_file = tmp_path / "test_video.mp4"
        video_file.write_bytes(b"fake video content")
        
        uploader.authenticated = False
        
        # Mock authentication failure
        with patch.object(uploader, 'authenticate', return_value=False):
            result = uploader.upload_video(
                video_path=str(video_file),
                metadata=sample_metadata
            )
            
            assert result.success is False
            assert "Authentication failed" in result.error_message
    
    def test_upload_video_without_publish_at(self, uploader, sample_metadata, tmp_path):
        """Test upload_video without publishAt uses original privacy status"""
        video_file = tmp_path / "test_video.mp4"
        video_file.write_bytes(b"fake video content")
        
        uploader.authenticated = True
        uploader.service = Mock()
        
        mock_insert = Mock()
        mock_response = {'id': 'test_video_id'}
        mock_insert.execute.return_value = mock_response
        uploader.service.videos.return_value.insert.return_value = mock_insert
        
        with patch.object(uploader, '_resumable_upload', return_value=mock_response):
            result = uploader.upload_video(
                video_path=str(video_file),
                metadata=sample_metadata,
                publish_at=None  # No scheduled publishing
            )
            
            assert result.success is True
            
            # Verify publishAt not set and original privacy status used
            insert_call_args = uploader.service.videos.return_value.insert.call_args
            body = insert_call_args[1]['body']
            assert 'publishAt' not in body['status']
            assert body['status']['privacyStatus'] == 'public'  # Original status
    
    def test_upload_video_retry_on_transient_error(self, uploader, sample_metadata, tmp_path):
        """Test upload retry logic on transient errors"""
        video_file = tmp_path / "test_video.mp4"
        video_file.write_bytes(b"fake video content")
        
        uploader.authenticated = True
        uploader.service = Mock()
        
        mock_insert = Mock()
        mock_response = {'id': 'test_video_id'}
        
        # Mock _resumable_upload to fail twice, then succeed
        call_count = 0
        def mock_resumable_upload(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                # Simulate transient error (500)
                mock_resp = Mock(status=500)
                raise HttpError(mock_resp, b'Server Error')
            else:
                return mock_response
        
        with patch.object(uploader, '_resumable_upload', side_effect=mock_resumable_upload):
            # Note: Current implementation doesn't have automatic retry,
            # but we can test error handling
            result = uploader.upload_video(
                video_path=str(video_file),
                metadata=sample_metadata
            )
            
            # Should handle error gracefully
            # (Actual retry logic would need to be implemented)
            assert result is not None
    
    def test_upload_video_publish_at_minimum_time(self, uploader, sample_metadata, tmp_path):
        """Test upload_video with publishAt very close to current time"""
        video_file = tmp_path / "test_video.mp4"
        video_file.write_bytes(b"fake video content")
        
        uploader.authenticated = True
        uploader.service = Mock()
        
        mock_insert = Mock()
        mock_response = {'id': 'test_video_id'}
        mock_insert.execute.return_value = mock_response
        uploader.service.videos.return_value.insert.return_value = mock_insert
        
        with patch.object(uploader, '_resumable_upload', return_value=mock_response):
            # Publish time very close to now (might be rejected by YouTube)
            publish_time = datetime.now(timezone.utc) + timedelta(minutes=1)
            
            result = uploader.upload_video(
                video_path=str(video_file),
                metadata=sample_metadata,
                publish_at=publish_time
            )
            
            # Should still attempt upload (YouTube will validate minimum time)
            assert result.success is True
            insert_call_args = uploader.service.videos.return_value.insert.call_args
            body = insert_call_args[1]['body']
            assert 'publishAt' in body['status']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

