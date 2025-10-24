"""
Integration tests for YouTube automation system
Tests end-to-end workflows without actual YouTube API calls
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, time, timedelta
from pathlib import Path
import json

from langflix.youtube.schedule_manager import YouTubeScheduleManager, ScheduleConfig
from langflix.youtube.uploader import YouTubeUploader, YouTubeUploadResult
from langflix.youtube.video_manager import VideoFileManager, VideoMetadata
from langflix.youtube.metadata_generator import YouTubeMetadataGenerator
from langflix.youtube.web_ui import VideoManagementUI


class TestYouTubeAutomationIntegration:
    """Test complete YouTube automation workflows"""
    
    @pytest.fixture
    def mock_output_dir(self, tmp_path):
        """Create comprehensive mock output directory"""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Create episode structure
        episodes = ["S01E01_Test", "S01E02_Another"]
        languages = ["ko", "en"]
        video_types = ["final", "short", "educational"]
        
        for episode in episodes:
            episode_dir = output_dir / episode
            episode_dir.mkdir()
            
            for lang in languages:
                lang_dir = episode_dir / lang
                lang_dir.mkdir()
                
                for video_type in video_types:
                    type_dir = lang_dir / video_type
                    type_dir.mkdir()
                    
                    # Create test video files
                    video_file = type_dir / f"{video_type}_Test_Expression.mp4"
                    video_file.write_bytes(b"fake video content")
        
        return str(output_dir)
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        session = Mock()
        session.query.return_value = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        return session
    
    def test_complete_workflow_video_discovery_to_scheduling(self, mock_output_dir, mock_db_session):
        """Test complete workflow from video discovery to scheduling"""
        # Step 1: Video Discovery
        with patch('langflix.youtube.video_manager.subprocess.run') as mock_run:
            # Mock ffprobe output
            ffprobe_output = {
                "format": {"duration": "120.0"},
                "streams": [{"codec_type": "video", "width": 1920, "height": 1080, "codec_name": "h264"}]
            }
            mock_run.return_value = Mock(
                stdout=json.dumps(ffprobe_output),
                stderr="",
                returncode=0
            )
            
            with patch('pathlib.Path.stat') as mock_stat:
                mock_stat.return_value.st_size = 1024 * 1024
                mock_stat.return_value.st_ctime = datetime.now().timestamp()
                
                video_manager = VideoFileManager(mock_output_dir)
                all_videos = video_manager.scan_all_videos()
                
                # Should find all video files
                expected_count = 2 * 2 * 3  # episodes * languages * video_types
                assert len(all_videos) == expected_count
                
                # Filter to uploadable videos
                uploadable_videos = video_manager.get_uploadable_videos(all_videos)
                assert len(uploadable_videos) > 0
                assert all(v.video_type in ['final', 'short'] for v in uploadable_videos)
        
        # Step 2: Metadata Generation
        metadata_generator = YouTubeMetadataGenerator()
        test_video = uploadable_videos[0]
        
        metadata = metadata_generator.generate_metadata(test_video)
        
        assert metadata.title is not None
        assert metadata.description is not None
        assert metadata.tags is not None
        assert metadata.category_id == "22"
        assert metadata.privacy_status == "private"
        
        # Step 3: Scheduling
        with patch('langflix.youtube.schedule_manager.get_db_session', return_value=mock_db_session):
            schedule_manager = YouTubeScheduleManager()
            
            # Mock quota status
            with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
                mock_quota.return_value = Mock(
                    date=date.today(),
                    final_used=0,
                    final_remaining=2,
                    short_used=0,
                    short_remaining=5,
                    quota_used=0,
                    quota_remaining=10000,
                    quota_percentage=0.0
                )
                
                # Mock empty existing schedules
                schedule_manager.db_session.query.return_value.filter.return_value.all.return_value = []
                
                success, message, scheduled_time = schedule_manager.schedule_video(
                    str(test_video.path),
                    test_video.video_type
                )
                
                assert success is True
                assert scheduled_time is not None
                assert "scheduled" in message.lower()
    
    def test_quota_management_workflow(self, mock_db_session):
        """Test quota management and limit enforcement"""
        with patch('langflix.youtube.schedule_manager.get_db_session', return_value=mock_db_session):
            schedule_manager = YouTubeScheduleManager()
            
            # Test initial quota status
            with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
                mock_quota.return_value = Mock(
                    date=date.today(),
                    final_used=0,
                    final_remaining=2,
                    short_used=0,
                    short_remaining=5,
                    quota_used=0,
                    quota_remaining=10000,
                    quota_percentage=0.0
                )
                
                quota_status = schedule_manager.check_daily_quota(date.today())
                assert quota_status.final_remaining == 2
                assert quota_status.short_remaining == 5
                
                # Test quota warnings
                warnings = schedule_manager.get_quota_warnings()
                assert len(warnings) == 0  # No warnings initially
                
                # Test quota exceeded scenario
                mock_quota.return_value = Mock(
                    date=date.today(),
                    final_used=2,
                    final_remaining=0,  # No remaining slots
                    short_used=0,
                    short_remaining=5,
                    quota_used=0,
                    quota_remaining=10000,
                    quota_percentage=0.0
                )
                
                success, message, scheduled_time = schedule_manager.schedule_video(
                    "/path/to/video.mp4",
                    "final"
                )
                
                assert success is False
                assert "No remaining quota" in message
                assert scheduled_time is None
    
    def test_schedule_conflict_resolution(self, mock_db_session):
        """Test schedule conflict resolution"""
        with patch('langflix.youtube.schedule_manager.get_db_session', return_value=mock_db_session):
            schedule_manager = YouTubeScheduleManager()
            
            # Mock existing schedule at requested time
            existing_schedule = Mock()
            existing_schedule.scheduled_publish_time = datetime.combine(date.today(), time(10, 0))
            
            with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
                mock_quota.return_value = Mock(
                    date=date.today(),
                    final_used=0,
                    final_remaining=2,
                    short_used=0,
                    short_remaining=5,
                    quota_used=0,
                    quota_remaining=10000,
                    quota_percentage=0.0
                )
                
                # Mock existing schedules
                schedule_manager.db_session.query.return_value.filter.return_value.all.return_value = [existing_schedule]
                
                # Mock get_next_available_slot to return different time
                next_available = datetime.combine(date.today(), time(14, 0))
                with patch.object(schedule_manager, 'get_next_available_slot', return_value=next_available):
                    success, message, scheduled_time = schedule_manager.schedule_video(
                        "/path/to/video.mp4",
                        "final",
                        datetime.combine(date.today(), time(10, 0))  # Requested time conflicts
                    )
                    
                    assert success is False
                    assert "time slot is occupied" in message
                    assert "Next available" in message
    
    def test_metadata_generation_workflow(self, mock_output_dir):
        """Test metadata generation for different video types"""
        metadata_generator = YouTubeMetadataGenerator()
        
        # Test educational video metadata
        educational_video = VideoMetadata(
            path="/path/to/educational.mp4", filename="educational.mp4", size_mb=100.0,
            duration_seconds=300.0, resolution="1920x1080", format="h264",
            created_at=datetime.now(), episode="S01E01_Test", expression="Not the point",
            video_type="educational", language="ko"
        )
        
        educational_metadata = metadata_generator.generate_metadata(educational_video)
        
        assert "Not the point" in educational_metadata.title
        assert "S01E01" in educational_metadata.title or "Season 1 Episode 1" in educational_metadata.title
        assert "English Expressions" in educational_metadata.title
        assert "English Learning" in educational_metadata.tags
        assert "Suits" in educational_metadata.tags
        
        # Test short video metadata
        short_video = VideoMetadata(
            path="/path/to/short.mp4", filename="short.mp4", size_mb=50.0,
            duration_seconds=30.0, resolution="1920x1080", format="h264",
            created_at=datetime.now(), episode="S01E01_Test", expression="Not the point",
            video_type="short", language="ko"
        )
        
        short_metadata = metadata_generator.generate_metadata(short_video)
        
        assert "#Shorts" in short_metadata.title
        assert "Not the point" in short_metadata.title
        assert "Quick English lesson" in short_metadata.description
        assert "Shorts" in short_metadata.tags
        
        # Test final video metadata
        final_video = VideoMetadata(
            path="/path/to/final.mp4", filename="final.mp4", size_mb=200.0,
            duration_seconds=600.0, resolution="1920x1080", format="h264",
            created_at=datetime.now(), episode="S01E01_Test", expression="Not the point",
            video_type="final", language="ko"
        )
        
        final_metadata = metadata_generator.generate_metadata(final_video)
        
        assert "Complete English lesson" in final_metadata.title
        assert "comprehensive lesson" in final_metadata.description
        assert "Complete Lesson" in final_metadata.tags
    
    def test_batch_metadata_generation(self, mock_output_dir):
        """Test batch metadata generation"""
        metadata_generator = YouTubeMetadataGenerator()
        
        videos = [
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
        
        results = metadata_generator.generate_batch_metadata(videos)
        
        assert len(results) == 2
        assert "/path/to/video1.mp4" in results
        assert "/path/to/video2.mp4" in results
        
        # Check that results contain proper metadata
        for video_path, metadata in results.items():
            assert metadata.title is not None
            assert metadata.description is not None
            assert metadata.tags is not None
            assert metadata.category_id == "22"
    
    def test_web_ui_integration(self, mock_output_dir, mock_db_session):
        """Test web UI integration with all components"""
        with patch('langflix.youtube.web_ui.get_db_session', return_value=mock_db_session):
            with patch('langflix.youtube.web_ui.YouTubeScheduleManager'):
                with patch('langflix.youtube.web_ui.YouTubeUploadManager'):
                    with patch('langflix.youtube.web_ui.VideoFileManager'):
                        with patch('langflix.youtube.web_ui.YouTubeMetadataGenerator'):
                            ui = VideoManagementUI(mock_output_dir)
                            
                            # Mock the managers
                            ui.schedule_manager = Mock()
                            ui.upload_manager = Mock()
                            ui.video_manager = Mock()
                            ui.metadata_generator = Mock()
                            
                            # Test video listing
                            mock_videos = [
                                VideoMetadata(
                                    path="/path/to/final.mp4", filename="final.mp4", size_mb=100.0,
                                    duration_seconds=120.0, resolution="1920x1080", format="h264",
                                    created_at=datetime.now(), episode="S01E01", expression="Test",
                                    video_type="final", language="ko", ready_for_upload=True,
                                    uploaded_to_youtube=False, youtube_video_id=None
                                )
                            ]
                            
                            ui.video_manager.scan_all_videos.return_value = mock_videos
                            ui.video_manager.get_uploadable_videos.return_value = mock_videos
                            
                            with ui.app.test_client() as client:
                                response = client.get('/api/videos')
                                assert response.status_code == 200
                                data = response.get_json()
                                assert len(data) == 1
                                assert data[0]["video_type"] == "final"
                            
                            # Test YouTube account info
                            mock_channel_info = {
                                "channel_id": "test_channel_id",
                                "title": "Test Channel",
                                "thumbnail_url": "https://example.com/thumb.jpg"
                            }
                            
                            ui.upload_manager.uploader.get_channel_info.return_value = mock_channel_info
                            
                            with ui.app.test_client() as client:
                                response = client.get('/api/youtube/account')
                                assert response.status_code == 200
                                data = response.get_json()
                                assert data["authenticated"] is True
                                assert data["channel"] == mock_channel_info
                            
                            # Test scheduling
                            next_time = datetime(2025, 10, 25, 10, 0)
                            ui.schedule_manager.get_next_available_slot.return_value = next_time
                            ui.schedule_manager.schedule_video.return_value = (True, "Scheduled", next_time)
                            
                            with ui.app.test_client() as client:
                                response = client.get('/api/schedule/next-available?video_type=final')
                                assert response.status_code == 200
                                data = response.get_json()
                                assert data["next_available_time"] == next_time.isoformat()
                                
                                response = client.post('/api/upload/schedule', json={
                                    "video_path": "/path/to/video.mp4",
                                    "video_type": "final"
                                })
                                assert response.status_code == 200
                                data = response.get_json()
                                assert "scheduled_time" in data
    
    def test_error_handling_workflow(self, mock_db_session):
        """Test error handling across the system"""
        with patch('langflix.youtube.schedule_manager.get_db_session', return_value=mock_db_session):
            schedule_manager = YouTubeScheduleManager()
            
            # Test database error
            schedule_manager.db_session.commit.side_effect = Exception("Database error")
            
            with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
                mock_quota.return_value = Mock(
                    date=date.today(),
                    final_used=0,
                    final_remaining=2,
                    short_used=0,
                    short_remaining=5,
                    quota_used=0,
                    quota_remaining=10000,
                    quota_percentage=0.0
                )
                
                # Mock empty existing schedules
                schedule_manager.db_session.query.return_value.filter.return_value.all.return_value = []
                
                success, message, scheduled_time = schedule_manager.schedule_video(
                    "/path/to/video.mp4",
                    "final"
                )
                
                assert success is False
                assert "Failed to schedule video" in message
                assert scheduled_time is None
                
                # Should rollback on error
                schedule_manager.db_session.rollback.assert_called_once()
    
    def test_performance_under_load(self, mock_db_session):
        """Test system performance under load"""
        with patch('langflix.youtube.schedule_manager.get_db_session', return_value=mock_db_session):
            schedule_manager = YouTubeScheduleManager()
            
            # Test scheduling multiple videos
            with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
                mock_quota.return_value = Mock(
                    date=date.today(),
                    final_used=0,
                    final_remaining=2,
                    short_used=0,
                    short_remaining=5,
                    quota_used=0,
                    quota_remaining=10000,
                    quota_percentage=0.0
                )
                
                # Mock empty existing schedules
                schedule_manager.db_session.query.return_value.filter.return_value.all.return_value = []
                
                # Schedule multiple videos
                results = []
                for i in range(5):
                    success, message, scheduled_time = schedule_manager.schedule_video(
                        f"/path/to/video{i}.mp4",
                        "short"
                    )
                    results.append((success, message, scheduled_time))
                
                # Should handle multiple requests efficiently
                assert len(results) == 5
                # First few should succeed, then quota should be exceeded
                successful_schedules = [r for r in results if r[0]]
                assert len(successful_schedules) <= 5  # Should respect daily limits
    
    def test_data_consistency(self, mock_db_session):
        """Test data consistency across operations"""
        with patch('langflix.youtube.schedule_manager.get_db_session', return_value=mock_db_session):
            schedule_manager = YouTubeScheduleManager()
            
            # Test quota tracking consistency
            with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
                mock_quota.return_value = Mock(
                    date=date.today(),
                    final_used=0,
                    final_remaining=2,
                    short_used=0,
                    short_remaining=5,
                    quota_used=0,
                    quota_remaining=10000,
                    quota_percentage=0.0
                )
                
                # Mock empty existing schedules
                schedule_manager.db_session.query.return_value.filter.return_value.all.return_value = []
                
                # Schedule a video
                success, message, scheduled_time = schedule_manager.schedule_video(
                    "/path/to/video.mp4",
                    "final"
                )
                
                assert success is True
                
                # Update quota usage
                schedule_manager.update_quota_usage("final", 1600)
                
                # Check that quota was updated
                schedule_manager.db_session.add.assert_called()
                schedule_manager.db_session.commit.assert_called()
                
                # Test quota warnings after usage
                mock_quota.return_value = Mock(
                    date=date.today(),
                    final_used=1,
                    final_remaining=1,
                    short_used=0,
                    short_remaining=5,
                    quota_used=1600,
                    quota_remaining=8400,
                    quota_percentage=16.0
                )
                
                warnings = schedule_manager.get_quota_warnings()
                # Should have warning about remaining slots
                assert any("Only 1 final video slot" in warning for warning in warnings)


class TestYouTubeAutomationEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_malformed_video_paths(self, tmp_path):
        """Test handling of malformed video paths"""
        video_manager = VideoFileManager(str(tmp_path))
        
        # Test various malformed paths
        malformed_paths = [
            Path("/random/path/video.mp4"),
            Path("/output/Unknown_Format/ko/final/video.mp4"),
            Path("/output/S01E01/unknown/final/video.mp4"),
            Path("/output/S01E01/ko/unknown/video.mp4")
        ]
        
        for path in malformed_paths:
            video_type, episode, expression, language = video_manager._parse_video_path(path)
            
            # Should handle gracefully
            assert video_type is not None
            assert episode is not None
            assert expression is not None
            assert language is not None
    
    def test_extreme_metadata_values(self, tmp_path):
        """Test metadata generation with extreme values"""
        metadata_generator = YouTubeMetadataGenerator()
        
        # Test with very long expression
        long_expression = "This is a very long expression that might cause issues with title and description generation and should be handled gracefully by the system"
        video_metadata = VideoMetadata(
            path="/path/to/video.mp4", filename="video.mp4", size_mb=100.0,
            duration_seconds=120.0, resolution="1920x1080", format="h264",
            created_at=datetime.now(), episode="S01E01", expression=long_expression,
            video_type="final", language="ko"
        )
        
        metadata = metadata_generator.generate_metadata(video_metadata)
        
        assert metadata.title is not None
        assert metadata.description is not None
        assert metadata.tags is not None
        
        # Title should be reasonable length
        assert len(metadata.title) < 1000  # YouTube title limit
        
        # Test with special characters
        special_expression = "Test & Expression (with symbols!) @#$%"
        video_metadata.expression = special_expression
        
        metadata = metadata_generator.generate_metadata(video_metadata)
        
        assert metadata.title is not None
        assert metadata.description is not None
        assert metadata.tags is not None
    
    def test_schedule_edge_cases(self, tmp_path):
        """Test scheduling edge cases"""
        with patch('langflix.youtube.schedule_manager.get_db_session') as mock_db_session:
            schedule_manager = YouTubeScheduleManager()
            
            # Test with no preferred times configured
            schedule_manager.config.preferred_times = []
            
            with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
                mock_quota.return_value = Mock(
                    date=date.today(),
                    final_used=0,
                    final_remaining=2,
                    short_used=0,
                    short_remaining=5,
                    quota_used=0,
                    quota_remaining=10000,
                    quota_percentage=0.0
                )
                
                # Mock empty existing schedules
                schedule_manager.db_session.query.return_value.filter.return_value.all.return_value = []
                
                next_slot = schedule_manager.get_next_available_slot("final")
                
                # Should still return a valid time
                assert next_slot is not None
                assert next_slot.date() == date.today()
                assert 9 <= next_slot.hour <= 21  # Should fall back to hourly slots
    
    def test_quota_edge_cases(self, tmp_path):
        """Test quota management edge cases"""
        with patch('langflix.youtube.schedule_manager.get_db_session') as mock_db_session:
            schedule_manager = YouTubeScheduleManager()
            
            # Test with very high quota usage
            with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
                mock_quota.return_value = Mock(
                    date=date.today(),
                    final_used=0,
                    final_remaining=2,
                    short_used=0,
                    short_remaining=5,
                    quota_used=9500,  # 95% usage
                    quota_remaining=500,
                    quota_percentage=95.0
                )
                
                warnings = schedule_manager.get_quota_warnings()
                
                # Should have warning about high usage
                assert len(warnings) > 0
                assert any("95.0%" in warning for warning in warnings)
    
    def test_concurrent_operations(self, tmp_path):
        """Test concurrent operations handling"""
        with patch('langflix.youtube.schedule_manager.get_db_session') as mock_db_session:
            schedule_manager = YouTubeScheduleManager()
            
            # Test multiple concurrent schedule requests
            with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
                mock_quota.return_value = Mock(
                    date=date.today(),
                    final_used=0,
                    final_remaining=2,
                    short_used=0,
                    short_remaining=5,
                    quota_used=0,
                    quota_remaining=10000,
                    quota_percentage=0.0
                )
                
                # Mock empty existing schedules
                schedule_manager.db_session.query.return_value.filter.return_value.all.return_value = []
                
                # Simulate concurrent requests
                results = []
                for i in range(3):
                    success, message, scheduled_time = schedule_manager.schedule_video(
                        f"/path/to/video{i}.mp4",
                        "final"
                    )
                    results.append((success, message, scheduled_time))
                
                # Should handle concurrent requests
                assert len(results) == 3
                # All should succeed since we have quota for 2 final videos
                successful = [r for r in results if r[0]]
                assert len(successful) <= 2  # Should respect daily limits


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
