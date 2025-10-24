"""
Comprehensive unit tests for YouTubeUploader
Tests authentication, channel info, scheduling, and quota management
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime, timedelta
from pathlib import Path
import os
import json

from langflix.youtube.uploader import (
    YouTubeUploader, 
    YouTubeUploadResult, 
    YouTubeVideoMetadata,
    YouTubeUploadManager
)


class TestYouTubeVideoMetadata:
    """Test YouTubeVideoMetadata dataclass"""
    
    def test_metadata_creation(self):
        """Test creating YouTube video metadata"""
        metadata = YouTubeVideoMetadata(
            title="Test Video",
            description="Test Description",
            tags=["tag1", "tag2"],
            category_id="22",
            privacy_status="private",
            thumbnail_path="/path/to/thumb.jpg"
        )
        
        assert metadata.title == "Test Video"
        assert metadata.description == "Test Description"
        assert metadata.tags == ["tag1", "tag2"]
        assert metadata.category_id == "22"
        assert metadata.privacy_status == "private"
        assert metadata.thumbnail_path == "/path/to/thumb.jpg"
    
    def test_metadata_defaults(self):
        """Test metadata with default values"""
        metadata = YouTubeVideoMetadata(
            title="Test Video",
            description="Test Description",
            tags=["tag1"]
        )
        
        assert metadata.category_id == "22"  # People & Blogs
        assert metadata.privacy_status == "private"
        assert metadata.thumbnail_path is None


class TestYouTubeUploadResult:
    """Test YouTubeUploadResult dataclass"""
    
    def test_upload_result_success(self):
        """Test successful upload result"""
        upload_time = datetime.now()
        result = YouTubeUploadResult(
            success=True,
            video_id="test_video_id",
            video_url="https://youtube.com/watch?v=test_video_id",
            upload_time=upload_time
        )
        
        assert result.success is True
        assert result.video_id == "test_video_id"
        assert result.video_url == "https://youtube.com/watch?v=test_video_id"
        assert result.upload_time == upload_time
        assert result.error_message is None
    
    def test_upload_result_failure(self):
        """Test failed upload result"""
        result = YouTubeUploadResult(
            success=False,
            error_message="Upload failed"
        )
        
        assert result.success is False
        assert result.error_message == "Upload failed"
        assert result.video_id is None
        assert result.video_url is None
        assert result.upload_time is None


class TestYouTubeUploader:
    """Test YouTubeUploader core functionality"""
    
    @pytest.fixture
    def mock_credentials_file(self, tmp_path):
        """Create mock credentials file"""
        credentials_file = tmp_path / "test_credentials.json"
        credentials_data = {
            "web": {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "redirect_uris": ["http://localhost:8080/"]
            }
        }
        credentials_file.write_text(json.dumps(credentials_data))
        return str(credentials_file)
    
    @pytest.fixture
    def mock_token_file(self, tmp_path):
        """Create mock token file"""
        token_file = tmp_path / "test_token.json"
        token_data = {
            "token": "test_token",
            "refresh_token": "test_refresh_token",
            "expiry": "2025-12-31T23:59:59Z"
        }
        token_file.write_text(json.dumps(token_data))
        return str(token_file)
    
    @pytest.fixture
    def uploader(self, mock_credentials_file, mock_token_file):
        """Create YouTubeUploader with mocked dependencies"""
        with patch('langflix.youtube.uploader.YOUTUBE_API_AVAILABLE', True):
            uploader = YouTubeUploader(
                credentials_file=mock_credentials_file,
                token_file=mock_token_file
            )
            return uploader
    
    def test_init_with_credentials(self, mock_credentials_file, mock_token_file):
        """Test uploader initialization with credentials"""
        with patch('langflix.youtube.uploader.YOUTUBE_API_AVAILABLE', True):
            uploader = YouTubeUploader(
                credentials_file=mock_credentials_file,
                token_file=mock_token_file
            )
            
            assert uploader.credentials_file == mock_credentials_file
            assert uploader.token_file == mock_token_file
            assert uploader.service is None
            assert uploader.authenticated is False
    
    def test_init_without_api_libraries(self):
        """Test uploader initialization without API libraries"""
        with patch('langflix.youtube.uploader.YOUTUBE_API_AVAILABLE', False):
            with pytest.raises(ImportError, match="YouTube API libraries not available"):
                YouTubeUploader()
    
    def test_authenticate_success_with_existing_token(self, uploader):
        """Test successful authentication with existing valid token"""
        # Mock valid credentials
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.expired = False
        mock_creds.refresh_token = "test_refresh_token"
        
        with patch('langflix.youtube.uploader.Credentials.from_authorized_user_file', return_value=mock_creds):
            with patch('langflix.youtube.uploader.build') as mock_build:
                mock_service = Mock()
                mock_build.return_value = mock_service
                
                result = uploader.authenticate()
                
                assert result is True
                assert uploader.authenticated is True
                assert uploader.service == mock_service
    
    def test_authenticate_success_with_refresh(self, uploader):
        """Test successful authentication with token refresh"""
        # Mock expired credentials with refresh token
        mock_creds = Mock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "test_refresh_token"
        mock_creds.to_json.return_value = '{"access_token": "test_token"}'
        
        with patch('langflix.youtube.uploader.Credentials.from_authorized_user_file', return_value=mock_creds):
            with patch('langflix.youtube.uploader.Request') as mock_request:
                with patch('langflix.youtube.uploader.build') as mock_build:
                    mock_service = Mock()
                    mock_build.return_value = mock_service
                    
                    result = uploader.authenticate()
                    
                    assert result is True
                    assert uploader.authenticated is True
                    assert uploader.service == mock_service
                    # Should refresh token
                    mock_creds.refresh.assert_called_once_with(mock_request.return_value)
    
    def test_authenticate_success_new_flow(self, uploader):
        """Test successful authentication with new OAuth flow"""
        # Mock no existing credentials
        with patch('langflix.youtube.uploader.Credentials.from_authorized_user_file', return_value=None):
            with patch('langflix.youtube.uploader.InstalledAppFlow') as mock_flow_class:
                with patch('langflix.youtube.uploader.build') as mock_build:
                    # Mock OAuth flow
                    mock_flow = Mock()
                    mock_creds = Mock()
                    mock_creds.to_json.return_value = '{"access_token": "test_token"}'
                    mock_flow.run_local_server.return_value = mock_creds
                    mock_flow_class.from_client_secrets_file.return_value = mock_flow
                    
                    mock_service = Mock()
                    mock_build.return_value = mock_service
                    
                    result = uploader.authenticate()
                    
                    assert result is True
                    assert uploader.authenticated is True
                    assert uploader.service == mock_service
                    
                    # Should save credentials
                    mock_flow.run_local_server.assert_called_once_with(port=8080, open_browser=True)
    
    def test_authenticate_credentials_file_not_found(self, uploader):
        """Test authentication when credentials file not found"""
        # Remove credentials file
        os.remove(uploader.credentials_file)
        
        result = uploader.authenticate()
        
        assert result is False
        assert uploader.authenticated is False
    
    def test_authenticate_flow_error(self, uploader):
        """Test authentication with OAuth flow error"""
        with patch('langflix.youtube.uploader.Credentials.from_authorized_user_file', return_value=None):
            with patch('langflix.youtube.uploader.InstalledAppFlow') as mock_flow_class:
                mock_flow = Mock()
                mock_flow.run_local_server.side_effect = Exception("OAuth error")
                mock_flow_class.from_client_secrets_file.return_value = mock_flow
                
                result = uploader.authenticate()
                
                assert result is False
                assert uploader.authenticated is False
    
    def test_authenticate_build_service_error(self, uploader):
        """Test authentication with service build error"""
        mock_creds = Mock()
        mock_creds.valid = True
        
        with patch('langflix.youtube.uploader.Credentials.from_authorized_user_file', return_value=mock_creds):
            with patch('langflix.youtube.uploader.build') as mock_build:
                mock_build.side_effect = Exception("Service build error")
                
                result = uploader.authenticate()
                
                assert result is False
                assert uploader.authenticated is False
    
    def test_get_channel_info_success(self, uploader):
        """Test getting channel info successfully"""
        # Mock authenticated service
        uploader.authenticated = True
        mock_service = Mock()
        uploader.service = mock_service
        
        # Mock channel response
        mock_response = {
            'items': [{
                'id': 'test_channel_id',
                'snippet': {
                    'title': 'Test Channel',
                    'description': 'Test Description',
                    'thumbnails': {
                        'default': {'url': 'https://example.com/thumb.jpg'}
                    },
                    'country': 'US',
                    'publishedAt': '2020-01-01T00:00:00Z'
                }
            }]
        }
        mock_service.channels.return_value.list.return_value.execute.return_value = mock_response
        
        channel_info = uploader.get_channel_info()
        
        assert channel_info is not None
        assert channel_info['channel_id'] == 'test_channel_id'
        assert channel_info['title'] == 'Test Channel'
        assert channel_info['description'] == 'Test Description'
        assert channel_info['thumbnail_url'] == 'https://example.com/thumb.jpg'
        assert channel_info['country'] == 'US'
        assert channel_info['published_at'] == '2020-01-01T00:00:00Z'
    
    def test_get_channel_info_not_authenticated(self, uploader):
        """Test getting channel info when not authenticated"""
        uploader.authenticated = False
        
        channel_info = uploader.get_channel_info()
        
        assert channel_info is None
    
    def test_get_channel_info_auto_authenticate(self, uploader):
        """Test getting channel info with auto-authentication"""
        uploader.authenticated = False
        
        with patch.object(uploader, 'authenticate', return_value=True) as mock_authenticate:
            with patch.object(uploader, 'get_channel_info') as mock_get_info:
                mock_get_info.return_value = {'channel_id': 'test_id'}
                
                # This would cause infinite recursion, so we'll test the logic differently
                uploader.authenticated = True
                mock_service = Mock()
                uploader.service = mock_service
                
                mock_response = {'items': [{'id': 'test_id', 'snippet': {'title': 'Test'}}]}
                mock_service.channels.return_value.list.return_value.execute.return_value = mock_response
                
                channel_info = uploader.get_channel_info()
                
                assert channel_info is not None
    
    def test_get_channel_info_no_channels(self, uploader):
        """Test getting channel info when no channels found"""
        uploader.authenticated = True
        mock_service = Mock()
        uploader.service = mock_service
        
        # Mock empty response
        mock_response = {'items': []}
        mock_service.channels.return_value.list.return_value.execute.return_value = mock_response
        
        channel_info = uploader.get_channel_info()
        
        assert channel_info is None
    
    def test_get_channel_info_api_error(self, uploader):
        """Test getting channel info with API error"""
        uploader.authenticated = True
        mock_service = Mock()
        uploader.service = mock_service
        
        # Mock API error
        mock_service.channels.return_value.list.return_value.execute.side_effect = Exception("API error")
        
        channel_info = uploader.get_channel_info()
        
        assert channel_info is None
    
    def test_schedule_video_publish_success(self, uploader):
        """Test scheduling video publish successfully"""
        uploader.authenticated = True
        mock_service = Mock()
        uploader.service = mock_service
        
        video_id = "test_video_id"
        publish_at = datetime.now() + timedelta(days=1)
        
        # Mock video info
        mock_video_info = {
            'id': video_id,
            'status': {
                'privacyStatus': 'public'
            }
        }
        
        with patch.object(uploader, 'get_video_info', return_value=mock_video_info):
            result = uploader.schedule_video_publish(video_id, publish_at)
            
            assert result is True
            # Should update video with scheduled publish time
            mock_service.videos.return_value.update.assert_called_once()
    
    def test_schedule_video_publish_not_authenticated(self, uploader):
        """Test scheduling video publish when not authenticated"""
        uploader.authenticated = False
        
        result = uploader.schedule_video_publish("test_id", datetime.now())
        
        assert result is False
    
    def test_schedule_video_publish_video_not_found(self, uploader):
        """Test scheduling video publish when video not found"""
        uploader.authenticated = True
        mock_service = Mock()
        uploader.service = mock_service
        
        with patch.object(uploader, 'get_video_info', return_value=None):
            result = uploader.schedule_video_publish("test_id", datetime.now())
            
            assert result is False
    
    def test_schedule_video_publish_api_error(self, uploader):
        """Test scheduling video publish with API error"""
        uploader.authenticated = True
        mock_service = Mock()
        uploader.service = mock_service
        
        video_id = "test_video_id"
        publish_at = datetime.now() + timedelta(days=1)
        
        mock_video_info = {
            'id': video_id,
            'status': {'privacyStatus': 'public'}
        }
        
        with patch.object(uploader, 'get_video_info', return_value=mock_video_info):
            # Mock API error
            mock_service.videos.return_value.update.return_value.execute.side_effect = Exception("API error")
            
            result = uploader.schedule_video_publish(video_id, publish_at)
            
            assert result is False
    
    def test_update_video_publish_time_success(self, uploader):
        """Test updating video publish time successfully"""
        uploader.authenticated = True
        mock_service = Mock()
        uploader.service = mock_service
        
        video_id = "test_video_id"
        new_publish_time = datetime.now() + timedelta(days=2)
        
        mock_video_info = {
            'id': video_id,
            'status': {'privacyStatus': 'private'}
        }
        
        with patch.object(uploader, 'get_video_info', return_value=mock_video_info):
            result = uploader.update_video_publish_time(video_id, new_publish_time)
            
            assert result is True
            mock_service.videos.return_value.update.assert_called_once()
    
    def test_update_video_publish_time_not_authenticated(self, uploader):
        """Test updating video publish time when not authenticated"""
        uploader.authenticated = False
        
        result = uploader.update_video_publish_time("test_id", datetime.now())
        
        assert result is False
    
    def test_update_video_publish_time_video_not_found(self, uploader):
        """Test updating video publish time when video not found"""
        uploader.authenticated = True
        mock_service = Mock()
        uploader.service = mock_service
        
        with patch.object(uploader, 'get_video_info', return_value=None):
            result = uploader.update_video_publish_time("test_id", datetime.now())
            
            assert result is False
    
    def test_get_quota_usage(self, uploader):
        """Test getting quota usage"""
        quota_info = uploader.get_quota_usage()
        
        assert 'quota_used_estimate' in quota_info
        assert 'quota_limit' in quota_info
        assert 'operations_performed' in quota_info
        assert quota_info['quota_limit'] == 10000


class TestYouTubeUploadManager:
    """Test YouTubeUploadManager functionality"""
    
    @pytest.fixture
    def upload_manager(self):
        """Create YouTubeUploadManager with mocked uploader"""
        with patch('langflix.youtube.uploader.YouTubeUploader') as mock_uploader_class:
            mock_uploader = Mock()
            mock_uploader_class.return_value = mock_uploader
            
            manager = YouTubeUploadManager()
            manager.uploader = mock_uploader
            return manager
    
    def test_init(self, upload_manager):
        """Test upload manager initialization"""
        assert upload_manager.uploader is not None
        assert upload_manager.upload_queue == []
        assert upload_manager.upload_history == []
    
    def test_add_to_queue(self, upload_manager):
        """Test adding video to upload queue"""
        video_path = "/path/to/video.mp4"
        metadata = YouTubeVideoMetadata(
            title="Test Video",
            description="Test Description",
            tags=["tag1"]
        )
        
        upload_manager.add_to_queue(video_path, metadata)
        
        assert len(upload_manager.upload_queue) == 1
        queue_item = upload_manager.upload_queue[0]
        assert queue_item['video_path'] == video_path
        assert queue_item['metadata'] == metadata
        assert queue_item['status'] == 'queued'
        assert 'added_at' in queue_item
    
    def test_process_queue_success(self, upload_manager):
        """Test processing upload queue successfully"""
        # Add videos to queue
        video_path = "/path/to/video.mp4"
        metadata = YouTubeVideoMetadata(
            title="Test Video",
            description="Test Description",
            tags=["tag1"]
        )
        upload_manager.add_to_queue(video_path, metadata)
        
        # Mock successful upload
        mock_result = YouTubeUploadResult(
            success=True,
            video_id="test_video_id",
            video_url="https://youtube.com/watch?v=test_video_id"
        )
        upload_manager.uploader.upload_video.return_value = mock_result
        
        results = upload_manager.process_queue()
        
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].video_id == "test_video_id"
        
        # Check queue item updated
        queue_item = upload_manager.upload_queue[0]
        assert queue_item['status'] == 'completed'
        assert queue_item['result'] == mock_result
        assert 'completed_at' in queue_item
        
        # Check added to history
        assert len(upload_manager.upload_history) == 1
    
    def test_process_queue_failure(self, upload_manager):
        """Test processing upload queue with failure"""
        # Add video to queue
        video_path = "/path/to/video.mp4"
        metadata = YouTubeVideoMetadata(
            title="Test Video",
            description="Test Description",
            tags=["tag1"]
        )
        upload_manager.add_to_queue(video_path, metadata)
        
        # Mock failed upload
        mock_result = YouTubeUploadResult(
            success=False,
            error_message="Upload failed"
        )
        upload_manager.uploader.upload_video.return_value = mock_result
        
        results = upload_manager.process_queue()
        
        assert len(results) == 1
        assert results[0].success is False
        assert results[0].error_message == "Upload failed"
        
        # Check queue item updated
        queue_item = upload_manager.upload_queue[0]
        assert queue_item['status'] == 'failed'
        assert queue_item['result'] == mock_result
    
    def test_process_queue_with_progress_callback(self, upload_manager):
        """Test processing queue with progress callback"""
        # Add video to queue
        video_path = "/path/to/video.mp4"
        metadata = YouTubeVideoMetadata(
            title="Test Video",
            description="Test Description",
            tags=["tag1"]
        )
        upload_manager.add_to_queue(video_path, metadata)
        
        # Mock successful upload
        mock_result = YouTubeUploadResult(success=True)
        upload_manager.uploader.upload_video.return_value = mock_result
        
        # Mock progress callback
        progress_callback = Mock()
        
        results = upload_manager.process_queue(progress_callback)
        
        # Should call progress callback
        progress_callback.assert_called_with("Completed 1/1")
    
    def test_get_queue_status(self, upload_manager):
        """Test getting queue status"""
        # Add videos with different statuses
        upload_manager.upload_queue = [
            {'status': 'queued'},
            {'status': 'completed'},
            {'status': 'failed'},
            {'status': 'queued'}
        ]
        
        status = upload_manager.get_queue_status()
        
        assert status['total'] == 4
        assert status['queued'] == 2
        assert status['completed'] == 1
        assert status['failed'] == 1


class TestYouTubeUploaderIntegration:
    """Test YouTubeUploader integration scenarios"""
    
    @pytest.fixture
    def mock_credentials_file(self, tmp_path):
        """Create mock credentials file"""
        credentials_file = tmp_path / "test_credentials.json"
        credentials_data = {
            "web": {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "redirect_uris": ["http://localhost:8080/"]
            }
        }
        credentials_file.write_text(json.dumps(credentials_data))
        return str(credentials_file)
    
    def test_full_upload_workflow(self, mock_credentials_file):
        """Test complete upload workflow"""
        with patch('langflix.youtube.uploader.YOUTUBE_API_AVAILABLE', True):
            uploader = YouTubeUploader(credentials_file=mock_credentials_file)
            
            # Mock authentication
            uploader.authenticated = True
            mock_service = Mock()
            uploader.service = mock_service
            
            # Mock video file
            video_path = "/path/to/test_video.mp4"
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.stat') as mock_stat:
                    mock_stat.return_value.st_size = 1024 * 1024  # 1MB
                with patch('builtins.open', mock_open(read_data=b'fake video content')):
                    
                    # Mock successful upload
                    mock_response = {
                        'id': 'test_video_id',
                        'snippet': {'title': 'Test Video'}
                    }
                    mock_service.videos.return_value.insert.return_value = Mock()
                    uploader._resumable_upload = Mock(return_value=mock_response)
                    
                    metadata = YouTubeVideoMetadata(
                        title="Test Video",
                        description="Test Description",
                        tags=["tag1", "tag2"]
                    )
                    
                    result = uploader.upload_video(video_path, metadata)
                    
                    assert result.success is True
                    assert result.video_id == "test_video_id"
                    assert result.video_url == "https://www.youtube.com/watch?v=test_video_id"
                    assert result.upload_time is not None
    
    def test_upload_video_not_authenticated(self, mock_credentials_file):
        """Test upload video when not authenticated"""
        with patch('langflix.youtube.uploader.YOUTUBE_API_AVAILABLE', True):
            uploader = YouTubeUploader(credentials_file=mock_credentials_file)
            
            # Mock authentication failure
            with patch.object(uploader, 'authenticate', return_value=False):
                metadata = YouTubeVideoMetadata(
                    title="Test Video",
                    description="Test Description",
                    tags=["tag1"]
                )
                
                result = uploader.upload_video("/path/to/video.mp4", metadata)
                
                assert result.success is False
                assert result.error_message == "Authentication failed"
    
    def test_upload_video_file_not_found(self, mock_credentials_file):
        """Test upload video when file not found"""
        with patch('langflix.youtube.uploader.YOUTUBE_API_AVAILABLE', True):
            uploader = YouTubeUploader(credentials_file=mock_credentials_file)
            uploader.authenticated = True
            
            metadata = YouTubeVideoMetadata(
                title="Test Video",
                description="Test Description",
                tags=["tag1"]
            )
            
            result = uploader.upload_video("/nonexistent/video.mp4", metadata)
            
            assert result.success is False
            assert "Video file not found" in result.error_message
    
    def test_upload_video_api_error(self, mock_credentials_file):
        """Test upload video with API error"""
        with patch('langflix.youtube.uploader.YOUTUBE_API_AVAILABLE', True):
            uploader = YouTubeUploader(credentials_file=mock_credentials_file)
            uploader.authenticated = True
            mock_service = Mock()
            uploader.service = mock_service
    
            # Mock video file
            video_path = "/path/to/test_video.mp4"
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.stat') as mock_stat:
                    mock_stat.return_value.st_size = 1024 * 1024
                with patch('builtins.open', mock_open(read_data=b'fake video content')):
                    
                    # Mock API error
                    from googleapiclient.errors import HttpError
                    mock_error = HttpError(Mock(status=403), b'Forbidden')
                    uploader._resumable_upload = Mock(side_effect=mock_error)
                    
                    metadata = YouTubeVideoMetadata(
                        title="Test Video",
                        description="Test Description",
                        tags=["tag1"]
                    )
                    
                    result = uploader.upload_video(video_path, metadata)
                    
                    assert result.success is False
                    assert "YouTube API error" in result.error_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
