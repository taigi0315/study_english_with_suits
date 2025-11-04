"""
Edge case tests for YouTubeScheduleManager
Tests timezone handling, invalid inputs, error scenarios, and edge cases
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, time, timedelta, timezone
from sqlalchemy.exc import OperationalError

from langflix.youtube.schedule_manager import (
    YouTubeScheduleManager, 
    ScheduleConfig, 
    DailyQuotaStatus
)
from langflix.db.models import YouTubeSchedule, YouTubeQuotaUsage
from langflix.db.session import db_manager


class TestSchedulerEdgeCases:
    """Test scheduler edge cases and error scenarios"""
    
    @pytest.fixture
    def schedule_manager(self):
        """Create YouTubeScheduleManager"""
        return YouTubeScheduleManager()
    
    def test_timezone_handling_utc(self, schedule_manager):
        """Test scheduler handles UTC timezones correctly"""
        from unittest.mock import patch
        
        # Create schedule with UTC timezone
        utc_time = datetime.now(timezone.utc)
        target_date = utc_time.date()
        
        mock_quota_status = DailyQuotaStatus(
            date=target_date,
            final_used=0,
            final_remaining=2,
            short_used=0,
            short_remaining=5,
            quota_used=0,
            quota_remaining=10000,
            quota_percentage=0.0
        )
        
        with patch.object(schedule_manager, 'check_daily_quota', return_value=mock_quota_status):
            with patch.object(schedule_manager, '_get_schedules_for_date', return_value=[]):
                with patch.object(db_manager, 'session') as mock_session:
                    mock_db = Mock()
                    mock_session.return_value.__enter__.return_value = mock_db
                    mock_session.return_value.__exit__.return_value = None
                    
                    success, msg, scheduled = schedule_manager.schedule_video(
                        video_path="/test/video.mp4",
                        video_type="short",
                        preferred_time=utc_time
                    )
                    assert success is True
                    assert scheduled.tzinfo is not None
    
    def test_invalid_time_format_in_preferred_times(self, schedule_manager):
        """Test scheduler handles invalid time formats gracefully"""
        config = ScheduleConfig(preferred_times=['invalid', '10:00', '25:00', '09:30'])
        manager = YouTubeScheduleManager(config=config)
        
        # Should skip invalid times and use valid ones
        with patch.object(manager, 'check_daily_quota') as mock_quota:
            mock_quota.return_value = DailyQuotaStatus(
                date=date.today(),
                final_used=0,
                final_remaining=2,
                short_used=0,
                short_remaining=5,
                quota_used=0,
                quota_remaining=10000,
                quota_percentage=0.0
            )
            with patch.object(manager, '_get_schedules_for_date', return_value=[]):
                slot = manager.get_next_available_slot('short')
                assert slot is not None
                # Should use one of the valid times (10:00 or 09:30)
                assert slot.hour in [9, 10]
    
    def test_database_connection_failure_during_quota_check(self, schedule_manager):
        """Test graceful handling of database failures during quota check"""
        target_date = date.today()
        
        # Mock database connection error
        with patch.object(db_manager, 'session') as mock_session:
            mock_session.side_effect = OperationalError("Connection failed", None, None)
            
            quota = schedule_manager.check_daily_quota(target_date)
            # Should return default quota, not crash
            assert quota.final_remaining == 2
            assert quota.short_remaining == 5
            assert quota.quota_percentage == 0.0
    
    def test_schedule_update_with_video_id(self, schedule_manager):
        """Test updating schedule with YouTube video ID"""
        from unittest.mock import patch
        
        video_path = "/test/video.mp4"
        target_date = date.today()
        
        with patch.object(db_manager, 'session') as mock_session:
            mock_db = Mock()
            mock_schedule = Mock()
            mock_db.query.return_value.filter_by.return_value.first.return_value = mock_schedule
            mock_session.return_value.__enter__.return_value = mock_db
            mock_session.return_value.__exit__.return_value = None
            
            # Update with video ID
            result = schedule_manager.update_schedule_with_video_id(
                video_path=video_path,
                youtube_video_id="test_video_id",
                status="completed"
            )
            assert result is True
            assert mock_schedule.youtube_video_id == "test_video_id"
            assert mock_schedule.upload_status == "completed"
    
    def test_cancel_schedule_edge_cases(self, schedule_manager):
        """Test schedule cancellation edge cases"""
        from unittest.mock import patch
        
        # Test canceling non-existent schedule
        with patch.object(db_manager, 'session') as mock_session:
            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = None
            mock_session.return_value.__enter__.return_value = mock_db
            mock_session.return_value.__exit__.return_value = None
            
            result = schedule_manager.cancel_schedule("non-existent-id")
            assert result is False
        
        # Test canceling already completed schedule
        with patch.object(db_manager, 'session') as mock_session:
            mock_db = Mock()
            mock_schedule = Mock()
            mock_schedule.upload_status = 'completed'
            mock_db.query.return_value.filter.return_value.first.return_value = mock_schedule
            mock_session.return_value.__enter__.return_value = mock_db
            mock_session.return_value.__exit__.return_value = None
            
            result = schedule_manager.cancel_schedule("completed-id")
            assert result is False  # Cannot cancel completed schedule
    
    def test_check_daily_quota_with_lock(self, schedule_manager):
        """Test check_daily_quota with lock parameter (if available)"""
        target_date = date.today()
        
        # Check if lock parameter is available (from TICKET-021)
        import inspect
        sig = inspect.signature(schedule_manager.check_daily_quota)
        has_lock_param = 'lock' in sig.parameters
        
        if has_lock_param:
            with patch.object(db_manager, 'session') as mock_session:
                mock_db = Mock()
                mock_query = Mock()
                mock_filter = Mock()
                mock_with_for_update = Mock()
                
                mock_db.query.return_value = mock_query
                mock_query.filter.return_value = mock_filter
                mock_filter.with_for_update.return_value = mock_with_for_update
                mock_with_for_update.first.return_value = None  # No existing record
                
                mock_session.return_value.__enter__.return_value = mock_db
                mock_session.return_value.__exit__.return_value = None
                
                # Call with lock=True
                quota = schedule_manager.check_daily_quota(target_date, lock=True)
                
                # Verify SELECT FOR UPDATE was called
                mock_filter.with_for_update.assert_called_once_with(timeout=5.0)
                assert quota is not None
                assert isinstance(quota, DailyQuotaStatus)
        else:
            # If lock parameter not available, test without it
            with patch.object(db_manager, 'session') as mock_session:
                mock_db = Mock()
                mock_query = Mock()
                mock_filter = Mock()
                
                mock_db.query.return_value = mock_query
                mock_query.filter.return_value = mock_filter
                mock_filter.first.return_value = None  # No existing record
                
                mock_session.return_value.__enter__.return_value = mock_db
                mock_session.return_value.__exit__.return_value = None
                
                quota = schedule_manager.check_daily_quota(target_date)
                assert quota is not None
                assert isinstance(quota, DailyQuotaStatus)
    
    def test_get_next_available_slot_preferred_date(self, schedule_manager):
        """Test get_next_available_slot with preferred date"""
        preferred_date = date.today() + timedelta(days=3)
        
        mock_quota_status = DailyQuotaStatus(
            date=preferred_date,
            final_used=0,
            final_remaining=2,
            short_used=0,
            short_remaining=5,
            quota_used=0,
            quota_remaining=10000,
            quota_percentage=0.0
        )
        
        with patch.object(schedule_manager, 'check_daily_quota', return_value=mock_quota_status):
            with patch.object(schedule_manager, '_get_available_times_for_date') as mock_available:
                mock_available.return_value = [datetime.combine(preferred_date, time(10, 0))]
                
                slot = schedule_manager.get_next_available_slot('final', preferred_date=preferred_date)
                
                assert slot is not None
                assert slot.date() == preferred_date
                schedule_manager.check_daily_quota.assert_called_with(preferred_date)
    
    def test_schedule_video_with_invalid_video_type(self, schedule_manager):
        """Test schedule_video rejects invalid video types"""
        success, message, scheduled = schedule_manager.schedule_video(
            video_path="/test/video.mp4",
            video_type="invalid_type"
        )
        
        assert success is False
        assert "Invalid video_type" in message
        assert scheduled is None
    
    def test_get_quota_warnings_threshold_edge_cases(self, schedule_manager):
        """Test quota warnings with threshold edge cases"""
        # Test exactly at threshold (80%)
        with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
            mock_quota.return_value = DailyQuotaStatus(
                date=date.today(),
                final_used=0,
                final_remaining=2,
                short_used=0,
                short_remaining=5,
                quota_used=8000,
                quota_remaining=2000,
                quota_percentage=80.0  # Exactly at threshold
            )
            
            warnings = schedule_manager.get_quota_warnings()
            # Should trigger warning at exactly 80%
            assert len(warnings) >= 1
            assert any("80.0%" in warning for warning in warnings)
        
        # Test just below threshold (79.9%)
        with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
            mock_quota.return_value = DailyQuotaStatus(
                date=date.today(),
                final_used=0,
                final_remaining=2,
                short_used=0,
                short_remaining=5,
                quota_used=7990,
                quota_remaining=2010,
                quota_percentage=79.9  # Just below threshold
            )
            
            warnings = schedule_manager.get_quota_warnings()
            # Should not trigger warning below threshold
            assert not any("79.9%" in warning for warning in warnings)
    
    def test_schedule_video_quota_exhausted_for_video_type(self, schedule_manager):
        """Test schedule_video handles quota exhaustion for specific video type"""
        from unittest.mock import patch
        
        video_path = "/test/video.mp4"
        video_type = "short"
        target_date = date.today()
        target_datetime = datetime.combine(target_date, time(10, 0))
        
        # Mock quota exhausted for short videos
        mock_quota_status = DailyQuotaStatus(
            date=target_date,
            final_used=0,
            final_remaining=2,
            short_used=5,  # All 5 slots used
            short_remaining=0,  # No remaining
            quota_used=8000,
            quota_remaining=2000,
            quota_percentage=80.0
        )
        
        # Check if _check_quota_with_lock exists (TICKET-021)
        has_private_method = hasattr(schedule_manager, '_check_quota_with_lock')
        
        if has_private_method:
            # Use private method if available (TICKET-021)
            with patch.object(schedule_manager, '_check_quota_with_lock', return_value=mock_quota_status):
                with patch.object(schedule_manager, '_get_schedules_for_date_locked', return_value=[]):
                    with patch.object(db_manager, 'session') as mock_session:
                        mock_db = Mock()
                        mock_session.return_value.__enter__.return_value = mock_db
                        mock_session.return_value.__exit__.return_value = None
                        
                        success, message, scheduled = schedule_manager.schedule_video(
                            video_path, video_type, preferred_time=target_datetime
                        )
                        
                        assert success is False
                        assert "No remaining quota" in message
                        assert "short" in message.lower()
                        assert scheduled is None
        else:
            # Use public method (main branch)
            with patch.object(schedule_manager, 'check_daily_quota', return_value=mock_quota_status):
                with patch.object(schedule_manager, '_get_schedules_for_date', return_value=[]):
                    with patch.object(db_manager, 'session') as mock_session:
                        mock_db = Mock()
                        mock_session.return_value.__enter__.return_value = mock_db
                        mock_session.return_value.__exit__.return_value = None
                        
                        success, message, scheduled = schedule_manager.schedule_video(
                            video_path, video_type, preferred_time=target_datetime
                        )
                        
                        assert success is False
                        assert "No remaining quota" in message
                        assert "short" in message.lower()
                        assert scheduled is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

