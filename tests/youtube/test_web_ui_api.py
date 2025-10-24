"""
Comprehensive unit tests for YouTube Web UI API endpoints
Tests all API endpoints, authentication, scheduling, and error handling
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, time
import json

from langflix.youtube.web_ui import VideoManagementUI
from langflix.youtube.video_manager import VideoMetadata
from langflix.youtube.uploader import YouTubeUploadResult
from langflix.youtube.schedule_manager import DailyQuotaStatus
from langflix.db.models import YouTubeAccount, YouTubeQuotaUsage


class TestVideoManagementUI:
    """Test VideoManagementUI core functionality"""
    
    @pytest.fixture
    def mock_output_dir(self, tmp_path):
        """Create mock output directory"""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        return str(output_dir)
    
    @pytest.fixture
    def web_ui(self, mock_output_dir):
        """Create VideoManagementUI with mocked dependencies"""
        with patch('langflix.youtube.web_ui.get_db_session') as mock_db_session:
            with patch('langflix.youtube.web_ui.YouTubeScheduleManager') as mock_schedule_manager:
                with patch('langflix.youtube.web_ui.YouTubeUploadManager') as mock_upload_manager:
                    with patch('langflix.youtube.web_ui.VideoFileManager') as mock_video_manager:
                        with patch('langflix.youtube.web_ui.YouTubeMetadataGenerator') as mock_metadata_generator:
                            ui = VideoManagementUI(mock_output_dir)
                            
                            # Mock the managers
                            ui.schedule_manager = Mock()
                            ui.upload_manager = Mock()
                            ui.video_manager = Mock()
                            ui.metadata_generator = Mock()
                            
                            return ui
    
    def test_init(self, web_ui, mock_output_dir):
        """Test VideoManagementUI initialization"""
        assert web_ui.output_dir == mock_output_dir
        assert web_ui.port == 5000
        assert web_ui.app is not None
    
    def test_video_to_dict(self, web_ui):
        """Test converting VideoMetadata to dictionary"""
        video_metadata = VideoMetadata(
            path="/path/to/video.mp4",
            filename="video.mp4",
            size_mb=100.0,
            duration_seconds=120.0,
            resolution="1920x1080",
            format="h264",
            created_at=datetime.now(),
            episode="S01E01",
            expression="Test Expression",
            video_type="final",
            language="ko",
            ready_for_upload=True,
            uploaded_to_youtube=False,
            youtube_video_id=None
        )
        
        result = web_ui._video_to_dict(video_metadata)
        
        assert result["path"] == "/path/to/video.mp4"
        assert result["filename"] == "video.mp4"
        assert result["size_mb"] == 100.0
        assert result["duration_seconds"] == 120.0
        assert result["resolution"] == "1920x1080"
        assert result["format"] == "h264"
        assert result["episode"] == "S01E01"
        assert result["expression"] == "Test Expression"
        assert result["video_type"] == "final"
        assert result["language"] == "ko"
        assert result["ready_for_upload"] is True
        assert result["uploaded_to_youtube"] is False
        assert result["youtube_video_id"] is None
        assert "duration_formatted" in result
        assert "created_at" in result
    
    def test_format_duration_seconds(self, web_ui):
        """Test duration formatting for seconds"""
        result = web_ui._format_duration(30.0)
        assert result == "30s"
    
    def test_format_duration_minutes(self, web_ui):
        """Test duration formatting for minutes"""
        result = web_ui._format_duration(90.0)
        assert result == "1:30"
    
    def test_format_duration_hours(self, web_ui):
        """Test duration formatting for hours"""
        result = web_ui._format_duration(3661.0)
        assert result == "1:01:01"


class TestVideoAPIEndpoints:
    """Test video-related API endpoints"""
    
    @pytest.fixture
    def web_ui(self, tmp_path):
        """Create VideoManagementUI with mocked dependencies"""
        with patch('langflix.youtube.web_ui.get_db_session'):
            with patch('langflix.youtube.web_ui.YouTubeScheduleManager'):
                with patch('langflix.youtube.web_ui.YouTubeUploadManager'):
                    with patch('langflix.youtube.web_ui.VideoFileManager'):
                        with patch('langflix.youtube.web_ui.YouTubeMetadataGenerator'):
                            ui = VideoManagementUI(str(tmp_path))
                            
                            # Mock the managers
                            ui.schedule_manager = Mock()
                            ui.upload_manager = Mock()
                            ui.video_manager = Mock()
                            ui.metadata_generator = Mock()
                            
                            return ui
    
    def test_get_videos_success(self, web_ui):
        """Test successful video retrieval"""
        # Mock video data
        mock_videos = [
            VideoMetadata(
                path="/path/to/final.mp4", filename="final.mp4", size_mb=100.0,
                duration_seconds=120.0, resolution="1920x1080", format="h264",
                created_at=datetime.now(), episode="S01E01", expression="Test1",
                video_type="final", language="ko", ready_for_upload=True,
                uploaded_to_youtube=False, youtube_video_id=None
            ),
            VideoMetadata(
                path="/path/to/short.mp4", filename="short.mp4", size_mb=50.0,
                duration_seconds=30.0, resolution="1920x1080", format="h264",
                created_at=datetime.now(), episode="S01E01", expression="Test2",
                video_type="short", language="ko", ready_for_upload=True,
                uploaded_to_youtube=False, youtube_video_id=None
            )
        ]
        
        web_ui.video_manager.scan_all_videos.return_value = mock_videos
        web_ui.video_manager.get_uploadable_videos.return_value = mock_videos
        
        with web_ui.app.test_client() as client:
            response = client.get('/api/videos')
            
            assert response.status_code == 200
            data = response.get_json()
            assert len(data) == 2
            assert data[0]["video_type"] == "final"
            assert data[1]["video_type"] == "short"
    
    def test_get_videos_error(self, web_ui):
        """Test video retrieval with error"""
        web_ui.video_manager.scan_all_videos.side_effect = Exception("Scan error")
        
        with web_ui.app.test_client() as client:
            response = client.get('/api/videos')
            
            assert response.status_code == 500
            data = response.get_json()
            assert "error" in data
            assert "Scan error" in data["error"]
    
    def test_get_videos_by_type(self, web_ui):
        """Test filtering videos by type"""
        mock_videos = [
            VideoMetadata(
                path="/path/to/final.mp4", filename="final.mp4", size_mb=100.0,
                duration_seconds=120.0, resolution="1920x1080", format="h264",
                created_at=datetime.now(), episode="S01E01", expression="Test1",
                video_type="final", language="ko"
            ),
            VideoMetadata(
                path="/path/to/short.mp4", filename="short.mp4", size_mb=50.0,
                duration_seconds=30.0, resolution="1920x1080", format="h264",
                created_at=datetime.now(), episode="S01E01", expression="Test2",
                video_type="short", language="ko"
            )
        ]
        
        web_ui.video_manager.scan_all_videos.return_value = mock_videos
        web_ui.video_manager.get_videos_by_type.return_value = [mock_videos[0]]
        
        with web_ui.app.test_client() as client:
            response = client.get('/api/videos/final')
            
            assert response.status_code == 200
            data = response.get_json()
            assert len(data) == 1
            assert data[0]["video_type"] == "final"
    
    def test_get_videos_by_episode(self, web_ui):
        """Test filtering videos by episode"""
        mock_videos = [
            VideoMetadata(
                path="/path/to/video1.mp4", filename="video1.mp4", size_mb=100.0,
                duration_seconds=120.0, resolution="1920x1080", format="h264",
                created_at=datetime.now(), episode="S01E01", expression="Test1",
                video_type="final", language="ko"
            ),
            VideoMetadata(
                path="/path/to/video2.mp4", filename="video2.mp4", size_mb=50.0,
                duration_seconds=30.0, resolution="1920x1080", format="h264",
                created_at=datetime.now(), episode="S01E02", expression="Test2",
                video_type="short", language="ko"
            )
        ]
        
        web_ui.video_manager.scan_all_videos.return_value = mock_videos
        web_ui.video_manager.get_videos_by_episode.return_value = [mock_videos[0]]
        
        with web_ui.app.test_client() as client:
            response = client.get('/api/videos/episode/S01E01')
            
            assert response.status_code == 200
            data = response.get_json()
            assert len(data) == 1
            assert data[0]["episode"] == "S01E01"
    
    def test_get_upload_ready_videos(self, web_ui):
        """Test getting upload ready videos"""
        mock_videos = [
            VideoMetadata(
                path="/path/to/ready.mp4", filename="ready.mp4", size_mb=100.0,
                duration_seconds=120.0, resolution="1920x1080", format="h264",
                created_at=datetime.now(), episode="S01E01", expression="Test1",
                video_type="final", language="ko", ready_for_upload=True,
                uploaded_to_youtube=False
            )
        ]
        
        web_ui.video_manager.scan_all_videos.return_value = mock_videos
        web_ui.video_manager.get_upload_ready_videos.return_value = mock_videos
        
        with web_ui.app.test_client() as client:
            response = client.get('/api/upload-ready')
            
            assert response.status_code == 200
            data = response.get_json()
            assert len(data) == 1
            assert data[0]["ready_for_upload"] is True
    
    def test_get_statistics(self, web_ui):
        """Test getting video statistics"""
        mock_videos = [
            VideoMetadata(
                path="/path/to/video1.mp4", filename="video1.mp4", size_mb=100.0,
                duration_seconds=120.0, resolution="1920x1080", format="h264",
                created_at=datetime.now(), episode="S01E01", expression="Test1",
                video_type="final", language="ko"
            )
        ]
        
        mock_stats = {
            "total_videos": 1,
            "total_size_mb": 100.0,
            "total_duration_minutes": 2.0,
            "upload_ready_count": 1,
            "type_distribution": {"final": 1},
            "episodes": ["S01E01"]
        }
        
        web_ui.video_manager.scan_all_videos.return_value = mock_videos
        web_ui.video_manager.get_statistics.return_value = mock_stats
        
        with web_ui.app.test_client() as client:
            response = client.get('/api/statistics')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data["total_videos"] == 1
            assert data["total_size_mb"] == 100.0
            assert data["type_distribution"]["final"] == 1


class TestYouTubeAccountAPI:
    """Test YouTube account management API endpoints"""
    
    @pytest.fixture
    def web_ui(self, tmp_path):
        """Create VideoManagementUI with mocked dependencies"""
        with patch('langflix.youtube.web_ui.get_db_session'):
            with patch('langflix.youtube.web_ui.YouTubeScheduleManager'):
                with patch('langflix.youtube.web_ui.YouTubeUploadManager'):
                    with patch('langflix.youtube.web_ui.VideoFileManager'):
                        with patch('langflix.youtube.web_ui.YouTubeMetadataGenerator'):
                            ui = VideoManagementUI(str(tmp_path))
                            
                            # Mock the managers
                            ui.schedule_manager = Mock()
                            ui.upload_manager = Mock()
                            ui.video_manager = Mock()
                            ui.metadata_generator = Mock()
                            
                            return ui
    
    def test_get_youtube_account_authenticated(self, web_ui):
        """Test getting YouTube account when authenticated"""
        mock_channel_info = {
            "channel_id": "test_channel_id",
            "title": "Test Channel",
            "thumbnail_url": "https://example.com/thumb.jpg",
            "email": "test@example.com"
        }
        
        web_ui.upload_manager.uploader.get_channel_info.return_value = mock_channel_info
        
        with web_ui.app.test_client() as client:
            response = client.get('/api/youtube/account')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data["authenticated"] is True
            assert data["channel"] == mock_channel_info
    
    def test_get_youtube_account_not_authenticated(self, web_ui):
        """Test getting YouTube account when not authenticated"""
        web_ui.upload_manager.uploader.get_channel_info.return_value = None
        
        with web_ui.app.test_client() as client:
            response = client.get('/api/youtube/account')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data["authenticated"] is False
            assert "message" in data
    
    def test_get_youtube_account_error(self, web_ui):
        """Test getting YouTube account with error"""
        web_ui.upload_manager.uploader.get_channel_info.side_effect = Exception("API error")
        
        with web_ui.app.test_client() as client:
            response = client.get('/api/youtube/account')
            
            assert response.status_code == 500
            data = response.get_json()
            assert "error" in data
    
    def test_youtube_login_success(self, web_ui):
        """Test successful YouTube login"""
        mock_channel_info = {
            "channel_id": "test_channel_id",
            "title": "Test Channel",
            "thumbnail_url": "https://example.com/thumb.jpg"
        }
        
        web_ui.upload_manager.uploader.authenticate.return_value = True
        web_ui.upload_manager.uploader.get_channel_info.return_value = mock_channel_info
        
        with web_ui.app.test_client() as client:
            response = client.post('/api/youtube/login')
            
            assert response.status_code == 200
            data = response.get_json()
            assert "message" in data
            assert data["channel"] == mock_channel_info
    
    def test_youtube_login_failure(self, web_ui):
        """Test failed YouTube login"""
        web_ui.upload_manager.uploader.authenticate.return_value = False
        
        with web_ui.app.test_client() as client:
            response = client.post('/api/youtube/login')
            
            assert response.status_code == 401
            data = response.get_json()
            assert "error" in data
    
    def test_youtube_login_error(self, web_ui):
        """Test YouTube login with error"""
        web_ui.upload_manager.uploader.authenticate.side_effect = Exception("Auth error")
        
        with web_ui.app.test_client() as client:
            response = client.post('/api/youtube/login')
            
            assert response.status_code == 500
            data = response.get_json()
            assert "error" in data
    
    def test_youtube_logout_success(self, web_ui):
        """Test successful YouTube logout"""
        with patch('os.path.exists', return_value=True):
            with patch('os.remove') as mock_remove:
                with web_ui.app.test_client() as client:
                    response = client.post('/api/youtube/logout')
                    
                    assert response.status_code == 200
                    data = response.get_json()
                    assert "message" in data
                    mock_remove.assert_called_once()
    
    def test_youtube_logout_error(self, web_ui):
        """Test YouTube logout with error"""
        with patch('os.path.exists', return_value=True):
            with patch('os.remove', side_effect=Exception("Remove error")):
                with web_ui.app.test_client() as client:
                    response = client.post('/api/youtube/logout')
                    
                    assert response.status_code == 500
                    data = response.get_json()
                    assert "error" in data


class TestScheduleAPI:
    """Test schedule management API endpoints"""
    
    @pytest.fixture
    def web_ui(self, tmp_path):
        """Create VideoManagementUI with mocked dependencies"""
        with patch('langflix.youtube.web_ui.get_db_session'):
            with patch('langflix.youtube.web_ui.YouTubeScheduleManager'):
                with patch('langflix.youtube.web_ui.YouTubeUploadManager'):
                    with patch('langflix.youtube.web_ui.VideoFileManager'):
                        with patch('langflix.youtube.web_ui.YouTubeMetadataGenerator'):
                            ui = VideoManagementUI(str(tmp_path))
                            
                            # Mock the managers
                            ui.schedule_manager = Mock()
                            ui.upload_manager = Mock()
                            ui.video_manager = Mock()
                            ui.metadata_generator = Mock()
                            
                            return ui
    
    def test_get_next_available_time_success(self, web_ui):
        """Test getting next available time successfully"""
        next_time = datetime(2025, 10, 25, 10, 0)
        web_ui.schedule_manager.get_next_available_slot.return_value = next_time
        
        with web_ui.app.test_client() as client:
            response = client.get('/api/schedule/next-available?video_type=final')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data["next_available_time"] == next_time.isoformat()
            assert data["video_type"] == "final"
    
    def test_get_next_available_time_invalid_type(self, web_ui):
        """Test getting next available time with invalid video type"""
        with web_ui.app.test_client() as client:
            response = client.get('/api/schedule/next-available?video_type=invalid')
            
            assert response.status_code == 400
            data = response.get_json()
            assert "error" in data
            assert "Invalid video_type" in data["error"]
    
    def test_get_next_available_time_error(self, web_ui):
        """Test getting next available time with error"""
        web_ui.schedule_manager.get_next_available_slot.side_effect = Exception("Schedule error")
        
        with web_ui.app.test_client() as client:
            response = client.get('/api/schedule/next-available?video_type=final')
            
            assert response.status_code == 500
            data = response.get_json()
            assert "error" in data
    
    def test_get_schedule_calendar_success(self, web_ui):
        """Test getting schedule calendar successfully"""
        mock_calendar = {
            "2025-10-25": [
                {
                    "id": "test_id",
                    "video_path": "/path/to/video.mp4",
                    "video_type": "final",
                    "scheduled_time": "2025-10-25T10:00:00",
                    "status": "scheduled"
                }
            ]
        }
        web_ui.schedule_manager.get_schedule_calendar.return_value = mock_calendar
        
        with web_ui.app.test_client() as client:
            response = client.get('/api/schedule/calendar')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data == mock_calendar
    
    def test_get_schedule_calendar_with_params(self, web_ui):
        """Test getting schedule calendar with parameters"""
        mock_calendar = {}
        web_ui.schedule_manager.get_schedule_calendar.return_value = mock_calendar
        
        with web_ui.app.test_client() as client:
            response = client.get('/api/schedule/calendar?start_date=2025-10-25&days=14')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data == mock_calendar
    
    def test_schedule_upload_success_auto_time(self, web_ui):
        """Test successful video scheduling with auto time"""
        video_path = "/path/to/video.mp4"
        video_type = "final"
        scheduled_time = datetime(2025, 10, 25, 10, 0)
        
        web_ui.schedule_manager.schedule_video.return_value = (True, "Scheduled successfully", scheduled_time)
        
        with web_ui.app.test_client() as client:
            response = client.post('/api/upload/schedule', json={
                "video_path": video_path,
                "video_type": video_type
            })
            
            assert response.status_code == 200
            data = response.get_json()
            assert "message" in data
            assert data["scheduled_time"] == scheduled_time.isoformat()
            assert data["video_path"] == video_path
            assert data["video_type"] == video_type
    
    def test_schedule_upload_success_custom_time(self, web_ui):
        """Test successful video scheduling with custom time"""
        video_path = "/path/to/video.mp4"
        video_type = "final"
        custom_time = datetime(2025, 10, 25, 14, 0)
        scheduled_time = custom_time
        
        web_ui.schedule_manager.schedule_video.return_value = (True, "Scheduled successfully", scheduled_time)
        
        with web_ui.app.test_client() as client:
            response = client.post('/api/upload/schedule', json={
                "video_path": video_path,
                "video_type": video_type,
                "publish_time": custom_time.isoformat()
            })
            
            assert response.status_code == 200
            data = response.get_json()
            assert data["scheduled_time"] == scheduled_time.isoformat()
    
    def test_schedule_upload_missing_params(self, web_ui):
        """Test video scheduling with missing parameters"""
        with web_ui.app.test_client() as client:
            response = client.post('/api/upload/schedule', json={
                "video_path": "/path/to/video.mp4"
                # Missing video_type
            })
            
            assert response.status_code == 400
            data = response.get_json()
            assert "error" in data
            assert "video_type" in data["error"]
    
    def test_schedule_upload_invalid_type(self, web_ui):
        """Test video scheduling with invalid video type"""
        with web_ui.app.test_client() as client:
            response = client.post('/api/upload/schedule', json={
                "video_path": "/path/to/video.mp4",
                "video_type": "invalid"
            })
            
            assert response.status_code == 400
            data = response.get_json()
            assert "error" in data
            assert "video_type must be" in data["error"]
    
    def test_schedule_upload_quota_exceeded(self, web_ui):
        """Test video scheduling when quota is exceeded"""
        web_ui.schedule_manager.schedule_video.return_value = (False, "No remaining quota", None)
        
        with web_ui.app.test_client() as client:
            response = client.post('/api/upload/schedule', json={
                "video_path": "/path/to/video.mp4",
                "video_type": "final"
            })
            
            assert response.status_code == 400
            data = response.get_json()
            assert "error" in data
            assert "No remaining quota" in data["error"]
    
    def test_schedule_upload_error(self, web_ui):
        """Test video scheduling with error"""
        web_ui.schedule_manager.schedule_video.side_effect = Exception("Schedule error")
        
        with web_ui.app.test_client() as client:
            response = client.post('/api/upload/schedule', json={
                "video_path": "/path/to/video.mp4",
                "video_type": "final"
            })
            
            assert response.status_code == 500
            data = response.get_json()
            assert "error" in data


class TestQuotaAPI:
    """Test quota management API endpoints"""
    
    @pytest.fixture
    def web_ui(self, tmp_path):
        """Create VideoManagementUI with mocked dependencies"""
        with patch('langflix.youtube.web_ui.get_db_session'):
            with patch('langflix.youtube.web_ui.YouTubeScheduleManager'):
                with patch('langflix.youtube.web_ui.YouTubeUploadManager'):
                    with patch('langflix.youtube.web_ui.VideoFileManager'):
                        with patch('langflix.youtube.web_ui.YouTubeMetadataGenerator'):
                            ui = VideoManagementUI(str(tmp_path))
                            
                            # Mock the managers
                            ui.schedule_manager = Mock()
                            ui.upload_manager = Mock()
                            ui.video_manager = Mock()
                            ui.metadata_generator = Mock()
                            
                            return ui
    
    def test_get_quota_status_success(self, web_ui):
        """Test getting quota status successfully"""
        mock_quota_status = DailyQuotaStatus(
            date=date.today(),
            final_used=1,
            final_remaining=1,
            short_used=2,
            short_remaining=3,
            quota_used=3200,
            quota_remaining=6800,
            quota_percentage=32.0
        )
        
        web_ui.schedule_manager.check_daily_quota.return_value = mock_quota_status
        web_ui.schedule_manager.get_quota_warnings.return_value = []
        web_ui.schedule_manager.config.daily_limits = {'final': 2, 'short': 5}
        
        with web_ui.app.test_client() as client:
            response = client.get('/api/quota/status')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data["date"] == date.today().isoformat()
            assert data["final_videos"]["used"] == 1
            assert data["final_videos"]["remaining"] == 1
            assert data["final_videos"]["limit"] == 2
            assert data["short_videos"]["used"] == 2
            assert data["short_videos"]["remaining"] == 3
            assert data["short_videos"]["limit"] == 5
            assert data["api_quota"]["used"] == 3200
            assert data["api_quota"]["remaining"] == 6800
            assert data["api_quota"]["percentage"] == 32.0
            assert data["warnings"] == []
    
    def test_get_quota_status_with_warnings(self, web_ui):
        """Test getting quota status with warnings"""
        mock_quota_status = DailyQuotaStatus(
            date=date.today(),
            final_used=1,
            final_remaining=1,
            short_used=4,
            short_remaining=1,
            quota_used=8500,
            quota_remaining=1500,
            quota_percentage=85.0
        )
        
        warnings = ["Only 1 final video slot remaining", "API quota usage is 85.0%"]
        
        web_ui.schedule_manager.check_daily_quota.return_value = mock_quota_status
        web_ui.schedule_manager.get_quota_warnings.return_value = warnings
        web_ui.schedule_manager.config.daily_limits = {'final': 2, 'short': 5}
        
        with web_ui.app.test_client() as client:
            response = client.get('/api/quota/status')
            
            assert response.status_code == 200
            data = response.get_json()
            assert len(data["warnings"]) == 2
            assert "Only 1 final video slot" in data["warnings"][0]
            assert "85.0%" in data["warnings"][1]
    
    def test_get_quota_status_error(self, web_ui):
        """Test getting quota status with error"""
        web_ui.schedule_manager.check_daily_quota.side_effect = Exception("Quota error")
        
        with web_ui.app.test_client() as client:
            response = client.get('/api/quota/status')
            
            assert response.status_code == 500
            data = response.get_json()
            assert "error" in data


class TestUploadAPI:
    """Test upload-related API endpoints"""
    
    @pytest.fixture
    def web_ui(self, tmp_path):
        """Create VideoManagementUI with mocked dependencies"""
        with patch('langflix.youtube.web_ui.get_db_session'):
            with patch('langflix.youtube.web_ui.YouTubeScheduleManager'):
                with patch('langflix.youtube.web_ui.YouTubeUploadManager'):
                    with patch('langflix.youtube.web_ui.VideoFileManager'):
                        with patch('langflix.youtube.web_ui.YouTubeMetadataGenerator'):
                            ui = VideoManagementUI(str(tmp_path))
                            
                            # Mock the managers
                            ui.schedule_manager = Mock()
                            ui.upload_manager = Mock()
                            ui.video_manager = Mock()
                            ui.metadata_generator = Mock()
                            
                            return ui
    
    def test_preview_upload_metadata_success(self, web_ui):
        """Test previewing upload metadata successfully"""
        video_path = "/path/to/video.mp4"
        mock_video_metadata = VideoMetadata(
            path=video_path, filename="video.mp4", size_mb=100.0,
            duration_seconds=120.0, resolution="1920x1080", format="h264",
            created_at=datetime.now(), episode="S01E01", expression="Test",
            video_type="final", language="ko"
        )

        mock_preview = {
            "title": "Test Title",
            "description_preview": "Test description...",
            "tags": ["tag1", "tag2"],
            "category_id": "22",
            "template_used": "final"
        }

        web_ui.video_manager.scan_all_videos.return_value = [mock_video_metadata]
        web_ui.metadata_generator.preview_metadata.return_value = mock_preview

        with web_ui.app.test_client() as client:
            # Use proper URL encoding
            encoded_path = video_path.replace("/", "%2F")
            response = client.get(f'/api/upload/preview/{encoded_path}', follow_redirects=True)

            assert response.status_code == 200
            data = response.get_json()
            assert data == mock_preview
    
    def test_preview_upload_metadata_video_not_found(self, web_ui):
        """Test previewing upload metadata when video not found"""
        video_path = "/path/to/video.mp4"

        web_ui.video_manager.scan_all_videos.return_value = []

        with web_ui.app.test_client() as client:
            # Use proper URL encoding
            encoded_path = video_path.replace("/", "%2F")
            response = client.get(f'/api/upload/preview/{encoded_path}', follow_redirects=True)

            assert response.status_code == 404
            data = response.get_json()
            assert "error" in data
            assert "Video metadata not found" in data["error"]
    
    def test_add_to_upload_queue_success(self, web_ui):
        """Test adding video to upload queue successfully"""
        video_path = "/path/to/video.mp4"
        mock_video_metadata = VideoMetadata(
            path=video_path, filename="video.mp4", size_mb=100.0,
            duration_seconds=120.0, resolution="1920x1080", format="h264",
            created_at=datetime.now(), episode="S01E01", expression="Test",
            video_type="final", language="ko"
        )
        
        mock_youtube_metadata = Mock()
        mock_youtube_metadata.title = "Test Title"
        mock_youtube_metadata.description = "Test description"
        mock_youtube_metadata.tags = ["tag1", "tag2"]
        mock_youtube_metadata.privacy_status = "private"
        
        web_ui.video_manager.scan_all_videos.return_value = [mock_video_metadata]
        web_ui.metadata_generator.generate_metadata.return_value = mock_youtube_metadata
        
        with web_ui.app.test_client() as client:
            response = client.post('/api/upload/queue', json={
                "video_path": video_path,
                "privacy_status": "private"
            })
            
            assert response.status_code == 200
            data = response.get_json()
            assert "message" in data
            assert data["video_path"] == video_path
            assert "metadata" in data
    
    def test_add_to_upload_queue_missing_path(self, web_ui):
        """Test adding to upload queue with missing video path"""
        with web_ui.app.test_client() as client:
            response = client.post('/api/upload/queue', json={
                "privacy_status": "private"
            })
            
            assert response.status_code == 400
            data = response.get_json()
            assert "error" in data
            assert "Video path is required" in data["error"]
    
    def test_add_to_upload_queue_video_not_found(self, web_ui):
        """Test adding to upload queue when video not found"""
        video_path = "/path/to/video.mp4"
        
        web_ui.video_manager.scan_all_videos.return_value = []
        
        with web_ui.app.test_client() as client:
            response = client.post('/api/upload/queue', json={
                "video_path": video_path
            })
            
            assert response.status_code == 404
            data = response.get_json()
            assert "error" in data
            assert "Video metadata not found" in data["error"]
    
    def test_get_upload_queue_status(self, web_ui):
        """Test getting upload queue status"""
        mock_status = {
            "total": 5,
            "queued": 2,
            "completed": 2,
            "failed": 1
        }
        
        web_ui.upload_manager.get_queue_status.return_value = mock_status
        
        with web_ui.app.test_client() as client:
            response = client.get('/api/upload/queue')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data == mock_status
    
    def test_process_upload_queue_success(self, web_ui):
        """Test processing upload queue successfully"""
        mock_results = [
            YouTubeUploadResult(
                success=True,
                video_id="test_video_id",
                video_url="https://youtube.com/watch?v=test_video_id",
                upload_time=datetime.now()
            )
        ]
        
        web_ui.upload_manager.uploader.authenticated = True
        web_ui.upload_manager.process_queue.return_value = mock_results
        
        with web_ui.app.test_client() as client:
            response = client.post('/api/upload/process')
            
            assert response.status_code == 200
            data = response.get_json()
            assert "message" in data
            assert "results" in data
            assert len(data["results"]) == 1
            assert data["results"][0]["success"] is True
    
    def test_process_upload_queue_not_authenticated(self, web_ui):
        """Test processing upload queue when not authenticated"""
        web_ui.upload_manager.uploader.authenticated = False
        web_ui.upload_manager.uploader.authenticate.return_value = False
        
        with web_ui.app.test_client() as client:
            response = client.post('/api/upload/process')
            
            assert response.status_code == 401
            data = response.get_json()
            assert "error" in data
            assert "YouTube authentication failed" in data["error"]
    
    def test_authenticate_youtube_success(self, web_ui):
        """Test YouTube authentication successfully"""
        web_ui.upload_manager.uploader.authenticate.return_value = True
        
        with web_ui.app.test_client() as client:
            response = client.post('/api/upload/authenticate')
            
            assert response.status_code == 200
            data = response.get_json()
            assert "message" in data
            assert "Successfully authenticated" in data["message"]
    
    def test_authenticate_youtube_failure(self, web_ui):
        """Test YouTube authentication failure"""
        web_ui.upload_manager.uploader.authenticate.return_value = False
        
        with web_ui.app.test_client() as client:
            response = client.post('/api/upload/authenticate')
            
            assert response.status_code == 401
            data = response.get_json()
            assert "error" in data
            assert "Authentication failed" in data["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
