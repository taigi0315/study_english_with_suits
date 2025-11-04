"""
Comprehensive unit tests for YouTubeScheduleManager
Tests scheduling logic, daily limits, conflict resolution, and quota management
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any

from langflix.youtube.schedule_manager import (
    YouTubeScheduleManager, 
    ScheduleConfig, 
    DailyQuotaStatus
)
from langflix.db.models import YouTubeSchedule, YouTubeQuotaUsage


class TestScheduleConfig:
    """Test ScheduleConfig dataclass"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = ScheduleConfig()
        
        assert config.daily_limits == {'final': 2, 'short': 5}
        assert config.preferred_times == ['10:00', '14:00', '18:00']
        assert config.quota_limit == 10000
        assert config.warning_threshold == 0.8
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = ScheduleConfig(
            daily_limits={'final': 3, 'short': 7},
            preferred_times=['09:00', '15:00'],
            quota_limit=15000,
            warning_threshold=0.9
        )
        
        assert config.daily_limits == {'final': 3, 'short': 7}
        assert config.preferred_times == ['09:00', '15:00']
        assert config.quota_limit == 15000
        assert config.warning_threshold == 0.9


class TestDailyQuotaStatus:
    """Test DailyQuotaStatus dataclass"""
    
    def test_quota_status_creation(self):
        """Test DailyQuotaStatus creation and properties"""
        today = date.today()
        status = DailyQuotaStatus(
            date=today,
            final_used=1,
            final_remaining=1,
            short_used=2,
            short_remaining=3,
            quota_used=3200,
            quota_remaining=6800,
            quota_percentage=32.0
        )
        
        assert status.date == today
        assert status.final_used == 1
        assert status.final_remaining == 1
        assert status.short_used == 2
        assert status.short_remaining == 3
        assert status.quota_used == 3200
        assert status.quota_remaining == 6800
        assert status.quota_percentage == 32.0


class TestYouTubeScheduleManager:
    """Test YouTubeScheduleManager core functionality"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        session = Mock()
        session.query.return_value = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        return session
    
    @pytest.fixture
    def schedule_manager(self, mock_db_session):
        """Create YouTubeScheduleManager with mocked dependencies"""
        with patch('langflix.youtube.schedule_manager.get_db_session', return_value=mock_db_session):
            manager = YouTubeScheduleManager()
            manager.db_session = mock_db_session
            return manager
    
    def test_init_default_config(self, schedule_manager):
        """Test initialization with default config"""
        assert schedule_manager.config.daily_limits == {'final': 2, 'short': 5}
        assert schedule_manager.config.preferred_times == ['10:00', '14:00', '18:00']
        assert schedule_manager.config.quota_limit == 10000
    
    def test_init_custom_config(self, mock_db_session):
        """Test initialization with custom config"""
        custom_config = ScheduleConfig(
            daily_limits={'final': 3, 'short': 7},
            preferred_times=['09:00', '15:00']
        )
        
        with patch('langflix.youtube.schedule_manager.get_db_session', return_value=mock_db_session):
            manager = YouTubeScheduleManager(custom_config)
            assert manager.config.daily_limits == {'final': 3, 'short': 7}
            assert manager.config.preferred_times == ['09:00', '15:00']
    
    def test_get_next_available_slot_final_video(self, schedule_manager):
        """Test getting next available slot for final video"""
        # Mock empty schedule
        schedule_manager.db_session.query.return_value.filter.return_value.all.return_value = []
        
        # Mock quota status with available slots
        with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
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
            
            next_slot = schedule_manager.get_next_available_slot('final')
            
            # Should return today at 10:00 AM (first preferred time)
            expected_time = datetime.combine(date.today(), time(10, 0))
            assert next_slot == expected_time
    
    def test_get_next_available_slot_short_video(self, schedule_manager):
        """Test getting next available slot for short video"""
        # Mock empty schedule
        schedule_manager.db_session.query.return_value.filter.return_value.all.return_value = []
        
        # Mock quota status with available slots
        with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
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
            
            next_slot = schedule_manager.get_next_available_slot('short')
            
            # Should return today at 10:00 AM (first preferred time)
            expected_time = datetime.combine(date.today(), time(10, 0))
            assert next_slot == expected_time
    
    def test_get_next_available_slot_invalid_type(self, schedule_manager):
        """Test getting next available slot with invalid video type"""
        with pytest.raises(ValueError, match="Invalid video_type: invalid"):
            schedule_manager.get_next_available_slot('invalid')
    
    def test_get_next_available_slot_no_quota_today(self, schedule_manager):
        """Test getting next available slot when today's quota is full"""
        # Mock quota status with no remaining slots
        with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
            # Today is full
            mock_quota.side_effect = [
                DailyQuotaStatus(
                    date=date.today(),
                    final_used=2,
                    final_remaining=0,
                    short_used=0,
                    short_remaining=5,
                    quota_used=0,
                    quota_remaining=10000,
                    quota_percentage=0.0
                ),
                # Tomorrow has slots
                DailyQuotaStatus(
                    date=date.today() + timedelta(days=1),
                    final_used=0,
                    final_remaining=2,
                    short_used=0,
                    short_remaining=5,
                    quota_used=0,
                    quota_remaining=10000,
                    quota_percentage=0.0
                )
            ]
        
        # Mock _get_schedules_for_date to return empty list
        with patch.object(schedule_manager, '_get_schedules_for_date', return_value=[]):
            
            next_slot = schedule_manager.get_next_available_slot('final')
            
            # Should return tomorrow at 10:00 AM
            expected_time = datetime.combine(date.today() + timedelta(days=1), time(10, 0))
            assert next_slot == expected_time
    
    def test_get_next_available_slot_no_slots_found(self, schedule_manager):
        """Test getting next available slot when no slots found in 7 days"""
        # Mock quota status with no remaining slots for 7 days
        with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
            mock_quota.return_value = DailyQuotaStatus(
                date=date.today(),
                final_used=2,
                final_remaining=0,
                short_used=0,
                short_remaining=5,
                quota_used=0,
                quota_remaining=10000,
                quota_percentage=0.0
            )
            
            next_slot = schedule_manager.get_next_available_slot('final')
            
            # Should return fallback time (7 days from now at 10:00 AM)
            expected_time = datetime.combine(date.today() + timedelta(days=7), time(10, 0))
            assert next_slot == expected_time
    
    def test_check_daily_quota_existing_record(self, schedule_manager):
        """Test checking daily quota with existing record"""
        today = date.today()
        existing_quota = YouTubeQuotaUsage(
            date=today,
            quota_used=3200,
            quota_limit=10000,
            upload_count=2,
            final_videos_uploaded=1,
            short_videos_uploaded=1
        )
        
        # Mock existing quota record
        schedule_manager.db_session.query.return_value.filter.return_value.first.return_value = existing_quota
        
        quota_status = schedule_manager.check_daily_quota(today)
        
        assert quota_status.date == today
        assert quota_status.final_used == 1
        assert quota_status.final_remaining == 1  # 2 - 1 = 1
        assert quota_status.short_used == 1
        assert quota_status.short_remaining == 4  # 5 - 1 = 4
        assert quota_status.quota_used == 3200
        assert quota_status.quota_remaining == 6800
        assert quota_status.quota_percentage == 32.0
    
    def test_check_daily_quota_new_record(self, schedule_manager):
        """Test checking daily quota with new record creation"""
        today = date.today()
        
        # Mock no existing quota record
        schedule_manager.db_session.query.return_value.filter.return_value.first.return_value = None
        
        quota_status = schedule_manager.check_daily_quota(today)
        
        # Should create new record
        schedule_manager.db_session.add.assert_called_once()
        schedule_manager.db_session.commit.assert_called_once()
        
        assert quota_status.date == today
        assert quota_status.final_used == 0
        assert quota_status.final_remaining == 2
        assert quota_status.short_used == 0
        assert quota_status.short_remaining == 5
        assert quota_status.quota_used == 0
        assert quota_status.quota_remaining == 10000
        assert quota_status.quota_percentage == 0.0
    
    def test_schedule_video_success_auto_time(self, schedule_manager):
        """Test successful video scheduling with auto-assigned time"""
        video_path = "/path/to/video.mp4"
        video_type = "final"
        
        # Mock next available slot
        next_slot = datetime.combine(date.today(), time(10, 0))
        with patch.object(schedule_manager, 'get_next_available_slot', return_value=next_slot):
            with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
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
                
                # Mock empty existing schedules
                schedule_manager.db_session.query.return_value.filter.return_value.all.return_value = []
                
                success, message, scheduled_time = schedule_manager.schedule_video(
                    video_path, video_type
                )
                
                assert success is True
                assert "scheduled for" in message.lower()
                assert scheduled_time == next_slot
                
                # Should create schedule record
                schedule_manager.db_session.add.assert_called_once()
                schedule_manager.db_session.commit.assert_called_once()
    
    def test_schedule_video_success_custom_time(self, schedule_manager):
        """Test successful video scheduling with custom time"""
        video_path = "/path/to/video.mp4"
        video_type = "final"
        custom_time = datetime.combine(date.today(), time(14, 0))
        
        with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
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
            
            # Mock empty existing schedules
            schedule_manager.db_session.query.return_value.filter.return_value.all.return_value = []
            
            success, message, scheduled_time = schedule_manager.schedule_video(
                video_path, video_type, custom_time
            )
            
            assert success is True
            assert scheduled_time == custom_time
    
    def test_schedule_video_quota_exceeded(self, schedule_manager):
        """Test video scheduling when quota is exceeded"""
        video_path = "/path/to/video.mp4"
        video_type = "final"
        
        with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
            mock_quota.return_value = DailyQuotaStatus(
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
                video_path, video_type
            )
            
            assert success is False
            assert "No remaining quota" in message
            assert scheduled_time is None
    
    def test_schedule_video_insufficient_api_quota(self, schedule_manager):
        """Test video scheduling when API quota is insufficient"""
        video_path = "/path/to/video.mp4"
        video_type = "final"
        
        with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
            mock_quota.return_value = DailyQuotaStatus(
                date=date.today(),
                final_used=0,
                final_remaining=2,
                short_used=0,
                short_remaining=5,
                quota_used=9000,
                quota_remaining=1000,  # Less than 1600 required
                quota_percentage=90.0
            )
            
            success, message, scheduled_time = schedule_manager.schedule_video(
                video_path, video_type
            )
            
            assert success is False
            assert "Insufficient API quota" in message
            assert scheduled_time is None
    
    def test_schedule_video_time_slot_occupied(self, schedule_manager):
        """Test video scheduling when requested time slot is occupied"""
        video_path = "/path/to/video.mp4"
        video_type = "final"
        requested_time = datetime.combine(date.today(), time(10, 0))
        
        # Mock existing schedule at requested time
        existing_schedule = YouTubeSchedule(
            video_path="/other/video.mp4",
            video_type="final",
            scheduled_publish_time=requested_time,
            upload_status="scheduled"
        )
        
        with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
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
            
            # Mock existing schedules
            schedule_manager.db_session.query.return_value.filter.return_value.all.return_value = [existing_schedule]
            
            # Mock get_next_available_slot to return different time
            next_available = datetime.combine(date.today(), time(14, 0))
            with patch.object(schedule_manager, 'get_next_available_slot', return_value=next_available):
                success, message, scheduled_time = schedule_manager.schedule_video(
                    video_path, video_type, requested_time
                )
                
                assert success is False
                assert "time slot is occupied" in message
                assert "Next available" in message
    
    def test_schedule_video_invalid_type(self, schedule_manager):
        """Test video scheduling with invalid video type"""
        video_path = "/path/to/video.mp4"
        video_type = "invalid"
        
        success, message, scheduled_time = schedule_manager.schedule_video(
            video_path, video_type
        )
        
        assert success is False
        assert "Invalid video_type" in message
        assert scheduled_time is None
    
    def test_schedule_video_database_error(self, schedule_manager):
        """Test video scheduling with database error"""
        video_path = "/path/to/video.mp4"
        video_type = "final"
        
        # Mock database error
        schedule_manager.db_session.commit.side_effect = Exception("Database error")
        
        with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
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
            
            # Mock empty existing schedules
            schedule_manager.db_session.query.return_value.filter.return_value.all.return_value = []
            
            success, message, scheduled_time = schedule_manager.schedule_video(
                video_path, video_type
            )
            
            assert success is False
            assert "Failed to schedule video" in message
            assert scheduled_time is None
            
            # Should rollback on error
            schedule_manager.db_session.rollback.assert_called_once()
    
    def test_get_schedule_calendar(self, schedule_manager):
        """Test getting schedule calendar"""
        start_date = date.today()
        days = 7
        
        # Mock schedules
        schedule1 = YouTubeSchedule(
            video_path="/path/to/video1.mp4",
            video_type="final",
            scheduled_publish_time=datetime.combine(start_date, time(10, 0)),
            upload_status="scheduled"
        )
        schedule2 = YouTubeSchedule(
            video_path="/path/to/video2.mp4",
            video_type="short",
            scheduled_publish_time=datetime.combine(start_date + timedelta(days=1), time(14, 0)),
            upload_status="scheduled"
        )
        
        schedule_manager.db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [schedule1, schedule2]
        
        calendar = schedule_manager.get_schedule_calendar(start_date, days)
        
        # Should group by date
        assert start_date.isoformat() in calendar
        assert (start_date + timedelta(days=1)).isoformat() in calendar
        
        # Check schedule data
        today_schedules = calendar[start_date.isoformat()]
        assert len(today_schedules) == 1
        assert today_schedules[0]['video_type'] == 'final'
        assert today_schedules[0]['status'] == 'scheduled'
    
    def test_update_quota_usage_new_record(self, schedule_manager):
        """Test updating quota usage with new record"""
        video_type = "final"
        quota_used = 1600
        
        # Mock no existing quota record
        schedule_manager.db_session.query.return_value.filter.return_value.first.return_value = None
        
        schedule_manager.update_quota_usage(video_type, quota_used)
        
        # Should create new record
        schedule_manager.db_session.add.assert_called_once()
        schedule_manager.db_session.commit.assert_called_once()
        
        # Check the created record
        added_record = schedule_manager.db_session.add.call_args[0][0]
        assert added_record.date == date.today()
        assert added_record.quota_used == quota_used
        assert added_record.upload_count == 1
        assert added_record.final_videos_uploaded == 1
        assert added_record.short_videos_uploaded == 0
    
    def test_update_quota_usage_existing_record(self, schedule_manager):
        """Test updating quota usage with existing record"""
        video_type = "short"
        quota_used = 1600
        
        # Mock existing quota record
        existing_quota = YouTubeQuotaUsage(
            date=date.today(),
            quota_used=3200,
            quota_limit=10000,
            upload_count=2,
            final_videos_uploaded=1,
            short_videos_uploaded=1
        )
        schedule_manager.db_session.query.return_value.filter.return_value.first.return_value = existing_quota
        
        schedule_manager.update_quota_usage(video_type, quota_used)
        
        # Should update existing record
        assert existing_quota.quota_used == 4800  # 3200 + 1600
        assert existing_quota.upload_count == 3  # 2 + 1
        assert existing_quota.final_videos_uploaded == 1  # unchanged
        assert existing_quota.short_videos_uploaded == 2  # 1 + 1
        
        schedule_manager.db_session.commit.assert_called_once()
    
    def test_get_quota_warnings_no_warnings(self, schedule_manager):
        """Test getting quota warnings when no warnings"""
        with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
            mock_quota.return_value = DailyQuotaStatus(
                date=date.today(),
                final_used=0,
                final_remaining=2,
                short_used=0,
                short_remaining=5,
                quota_used=1000,
                quota_remaining=9000,
                quota_percentage=10.0
            )
            
            warnings = schedule_manager.get_quota_warnings()
            
            assert len(warnings) == 0
    
    def test_get_quota_warnings_high_usage(self, schedule_manager):
        """Test getting quota warnings for high API usage"""
        with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
            mock_quota.return_value = DailyQuotaStatus(
                date=date.today(),
                final_used=0,
                final_remaining=2,
                short_used=0,
                short_remaining=5,
                quota_used=8500,  # 85% usage
                quota_remaining=1500,
                quota_percentage=85.0
            )
            
            warnings = schedule_manager.get_quota_warnings()
            
            assert len(warnings) == 1
            assert "85.0%" in warnings[0]
    
    def test_get_quota_warnings_daily_limits(self, schedule_manager):
        """Test getting quota warnings for daily limits"""
        with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
            mock_quota.return_value = DailyQuotaStatus(
                date=date.today(),
                final_used=1,
                final_remaining=1,  # Only 1 remaining
                short_used=4,
                short_remaining=1,  # Only 1 remaining
                quota_used=1000,
                quota_remaining=9000,
                quota_percentage=10.0
            )
            
            warnings = schedule_manager.get_quota_warnings()
            
            assert len(warnings) == 2
            assert any("Only 1 final video slot" in warning for warning in warnings)
            assert any("Only 1 short video slot" in warning for warning in warnings)
    
    def test_cancel_schedule_success(self, schedule_manager):
        """Test successful schedule cancellation"""
        schedule_id = "test-schedule-id"
        
        # Mock existing schedule
        existing_schedule = YouTubeSchedule(
            video_path="/path/to/video.mp4",
            video_type="final",
            scheduled_publish_time=datetime.now(),
            upload_status="scheduled"
        )
        schedule_manager.db_session.query.return_value.filter.return_value.first.return_value = existing_schedule
        
        result = schedule_manager.cancel_schedule(schedule_id)
        
        assert result is True
        assert existing_schedule.upload_status == "failed"
        assert existing_schedule.error_message == "Cancelled by user"
        schedule_manager.db_session.commit.assert_called_once()
    
    def test_cancel_schedule_not_found(self, schedule_manager):
        """Test canceling non-existent schedule"""
        schedule_id = "non-existent-id"
        
        # Mock no existing schedule
        schedule_manager.db_session.query.return_value.filter.return_value.first.return_value = None
        
        result = schedule_manager.cancel_schedule(schedule_id)
        
        assert result is False
    
    def test_cancel_schedule_already_processing(self, schedule_manager):
        """Test canceling schedule that's already processing"""
        schedule_id = "test-schedule-id"
        
        # Mock schedule that's already uploading
        existing_schedule = YouTubeSchedule(
            video_path="/path/to/video.mp4",
            video_type="final",
            scheduled_publish_time=datetime.now(),
            upload_status="uploading"  # Already processing
        )
        schedule_manager.db_session.query.return_value.filter.return_value.first.return_value = existing_schedule
        
        result = schedule_manager.cancel_schedule(schedule_id)
        
        assert result is False  # Cannot cancel already processing uploads
    
    def test_cancel_schedule_database_error(self, schedule_manager):
        """Test canceling schedule with database error"""
        schedule_id = "test-schedule-id"
        
        # Mock existing schedule
        existing_schedule = YouTubeSchedule(
            video_path="/path/to/video.mp4",
            video_type="final",
            scheduled_publish_time=datetime.now(),
            upload_status="scheduled"
        )
        schedule_manager.db_session.query.return_value.filter.return_value.first.return_value = existing_schedule
        
        # Mock database error
        schedule_manager.db_session.commit.side_effect = Exception("Database error")
        
        result = schedule_manager.cancel_schedule(schedule_id)
        
        assert result is False
        schedule_manager.db_session.rollback.assert_called_once()


class TestScheduleManagerEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        session = Mock()
        session.query.return_value = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        return session
    
    @pytest.fixture
    def schedule_manager(self, mock_db_session):
        """Create YouTubeScheduleManager with mocked dependencies"""
        with patch('langflix.youtube.schedule_manager.get_db_session', return_value=mock_db_session):
            manager = YouTubeScheduleManager()
            manager.db_session = mock_db_session
            return manager
    
    def test_get_available_times_for_date_no_preferred_times(self, schedule_manager):
        """Test getting available times when no preferred times configured"""
        schedule_manager.config.preferred_times = []
        target_date = date.today()
        
        # Mock empty existing schedules
        schedule_manager.db_session.query.return_value.filter.return_value.all.return_value = []
        
        available_times = schedule_manager._get_available_times_for_date(target_date, "final")
        
        # Should fall back to hourly slots (9 AM to 9 PM)
        assert len(available_times) == 1  # Should find at least one slot
        assert available_times[0].date() == target_date
        assert 9 <= available_times[0].hour <= 21
    
    def test_get_available_times_for_date_all_occupied(self, schedule_manager):
        """Test getting available times when all preferred times are occupied"""
        target_date = date.today()
        
        # Mock all preferred times occupied
        occupied_schedules = []
        for time_str in schedule_manager.config.preferred_times:
            hour, minute = map(int, time_str.split(':'))
            occupied_time = datetime.combine(target_date, time(hour, minute))
            occupied_schedules.append(YouTubeSchedule(
                video_path="/path/to/video.mp4",
                video_type="final",
                scheduled_publish_time=occupied_time,
                upload_status="scheduled"
            ))
        
        schedule_manager.db_session.query.return_value.filter.return_value.all.return_value = occupied_schedules
        
        available_times = schedule_manager._get_available_times_for_date(target_date, "final")
        
        # Should fall back to hourly slots
        assert len(available_times) == 1  # Should find at least one slot
        assert available_times[0].date() == target_date
        assert 9 <= available_times[0].hour <= 21
    
    def test_schedule_video_preferred_date_future(self, schedule_manager):
        """Test scheduling video for future date"""
        video_path = "/path/to/video.mp4"
        video_type = "final"
        future_date = date.today() + timedelta(days=3)
        future_time = datetime.combine(future_date, time(10, 0))
        
        with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
            mock_quota.return_value = DailyQuotaStatus(
                date=future_date,
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
                video_path, video_type, future_time
            )
            
            assert success is True
            assert scheduled_time == future_time
    
    def test_get_schedules_for_date_timezone_handling(self, schedule_manager):
        """Test getting schedules with timezone handling"""
        target_date = date.today()
        
        # Mock schedules with different times
        schedules = [
            YouTubeSchedule(
                video_path="/path/to/video1.mp4",
                video_type="final",
                scheduled_publish_time=datetime.combine(target_date, time(9, 0)),
                upload_status="scheduled"
            ),
            YouTubeSchedule(
                video_path="/path/to/video2.mp4",
                video_type="final",
                scheduled_publish_time=datetime.combine(target_date, time(23, 0)),
                upload_status="scheduled"
            )
        ]
        
        schedule_manager.db_session.query.return_value.filter.return_value.all.return_value = schedules
        
        result_schedules = schedule_manager._get_schedules_for_date(target_date)
        
        assert len(result_schedules) == 2
        assert all(s.scheduled_publish_time.date() == target_date for s in result_schedules)
    
    def test_quota_warnings_multiple_conditions(self, schedule_manager):
        """Test quota warnings with multiple warning conditions"""
        with patch.object(schedule_manager, 'check_daily_quota') as mock_quota:
            mock_quota.return_value = DailyQuotaStatus(
                date=date.today(),
                final_used=1,
                final_remaining=1,  # Warning condition
                short_used=4,
                short_remaining=1,  # Warning condition
                quota_used=8500,  # Warning condition (85%)
                quota_remaining=1500,
                quota_percentage=85.0
            )
            
            warnings = schedule_manager.get_quota_warnings()
            
            assert len(warnings) == 3
            assert any("85.0%" in warning for warning in warnings)
            assert any("Only 1 final video slot" in warning for warning in warnings)
            assert any("Only 1 short video slot" in warning for warning in warnings)


class TestSchedulerConcurrency:
    """Test scheduler concurrency and race condition handling"""
    
    @pytest.fixture
    def schedule_manager(self):
        """Create YouTubeScheduleManager"""
        return YouTubeScheduleManager()
    
    def test_check_quota_with_lock(self, schedule_manager):
        """Test _check_quota_with_lock uses SELECT FOR UPDATE"""
        from unittest.mock import Mock, MagicMock
        from langflix.db.session import db_manager
        
        target_date = date.today()
        mock_db = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_with_for_update = Mock()
        mock_quota_record = Mock()
        
        # Setup mock chain
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.with_for_update.return_value = mock_with_for_update
        mock_with_for_update.first.return_value = None  # No existing record
        
        # Mock quota record creation
        mock_quota_record.final_videos_uploaded = 0
        mock_quota_record.short_videos_uploaded = 0
        mock_quota_record.quota_used = 0
        mock_quota_record.quota_limit = 10000
        
        with patch('langflix.youtube.schedule_manager.YouTubeQuotaUsage', return_value=mock_quota_record):
            with patch.object(db_manager, 'session') as mock_session:
                mock_session.return_value.__enter__.return_value = mock_db
                mock_session.return_value.__exit__.return_value = None
                
                # Call _check_quota_with_lock
                result = schedule_manager._check_quota_with_lock(mock_db, target_date)
                
                # Verify SELECT FOR UPDATE was called
                mock_filter.with_for_update.assert_called_once_with(timeout=5.0)
                assert result is not None
                assert isinstance(result, DailyQuotaStatus)
    
    def test_reserve_quota_for_date(self, schedule_manager):
        """Test _reserve_quota_for_date reserves quota correctly"""
        from unittest.mock import Mock, MagicMock
        
        target_date = date.today()
        video_type = 'short'
        mock_db = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_with_for_update = Mock()
        mock_quota_record = Mock(spec=['final_videos_uploaded', 'short_videos_uploaded', 'quota_used', 'upload_count'])
        
        # Setup mock chain
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.with_for_update.return_value = mock_with_for_update
        mock_with_for_update.first.return_value = None  # No existing record
        
        # Mock quota record creation
        mock_new_record = Mock()
        mock_new_record.final_videos_uploaded = 0
        mock_new_record.short_videos_uploaded = 0
        mock_new_record.quota_used = 0
        mock_new_record.upload_count = 0
        
        with patch('langflix.youtube.schedule_manager.YouTubeQuotaUsage', return_value=mock_new_record):
            schedule_manager._reserve_quota_for_date(mock_db, target_date, video_type)
            
            # Verify quota was reserved (incremented)
            assert mock_new_record.quota_used == 1600
            assert mock_new_record.upload_count == 1
            assert mock_new_record.short_videos_uploaded == 1
            assert mock_new_record.final_videos_uploaded == 0
    
    def test_get_schedules_for_date_locked(self, schedule_manager):
        """Test _get_schedules_for_date_locked uses SELECT FOR UPDATE"""
        from unittest.mock import Mock
        from datetime import datetime, time
        
        target_date = date.today()
        mock_db = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_with_for_update = Mock()
        
        # Setup mock chain
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.with_for_update.return_value = mock_with_for_update
        
        # Mock schedule with scheduled_publish_time
        mock_schedule = Mock()
        mock_schedule.scheduled_publish_time = datetime.combine(target_date, time(10, 0))
        mock_with_for_update.all.return_value = [mock_schedule]
        
        result = schedule_manager._get_schedules_for_date_locked(mock_db, target_date)
        
        # Verify SELECT FOR UPDATE was called
        mock_filter.with_for_update.assert_called_once_with(timeout=5.0)
        assert len(result) == 1
        assert result[0] == mock_schedule.scheduled_publish_time
    
    def test_schedule_video_atomic_operation(self, schedule_manager):
        """Test schedule_video performs atomic quota check and reservation"""
        from unittest.mock import Mock, patch, MagicMock
        from langflix.db.session import db_manager
        
        video_path = "/test/video.mp4"
        video_type = "short"
        target_date = date.today()
        target_datetime = datetime.combine(target_date, time(10, 0))
        
        mock_db = Mock()
        
        # Mock quota check with lock
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
        
        with patch.object(schedule_manager, '_check_quota_with_lock', return_value=mock_quota_status):
            with patch.object(schedule_manager, '_get_schedules_for_date_locked', return_value=[]):
                with patch.object(schedule_manager, '_reserve_quota_for_date'):
                    with patch.object(db_manager, 'session') as mock_session:
                        mock_session.return_value.__enter__.return_value = mock_db
                        mock_session.return_value.__exit__.return_value = None
                        
                        # Mock get_next_available_slot
                        with patch.object(schedule_manager, 'get_next_available_slot', return_value=target_datetime):
                            success, message, scheduled_time = schedule_manager.schedule_video(
                                video_path, video_type
                            )
                            
                            # Verify atomic operation was performed
                            schedule_manager._check_quota_with_lock.assert_called_once_with(mock_db, target_date)
                            schedule_manager._reserve_quota_for_date.assert_called_once_with(mock_db, target_date, video_type)
                            assert success is True
                            assert scheduled_time == target_datetime
    
    def test_concurrent_schedule_requests_quota_reservation(self, schedule_manager):
        """Test that concurrent schedule requests properly reserve quota"""
        from unittest.mock import Mock, patch
        from langflix.db.session import db_manager
        from concurrent.futures import ThreadPoolExecutor
        import threading
        
        video_path_template = "/test/video_{}.mp4"
        video_type = "short"
        target_date = date.today()
        target_datetime = datetime.combine(target_date, time(10, 0))
        
        # Shared state to track quota reservations
        quota_reservations = []
        lock = threading.Lock()
        
        def schedule_video_thread(video_num):
            """Thread function to schedule a video"""
            video_path = video_path_template.format(video_num)
            mock_db = Mock()
            
            # Mock quota check - return decreasing remaining quota
            with lock:
                current_remaining = 5 - len(quota_reservations)
                if current_remaining <= 0:
                    return False, "No quota", None
            
            mock_quota_status = DailyQuotaStatus(
                date=target_date,
                final_used=0,
                final_remaining=2,
                short_used=len(quota_reservations),
                short_remaining=current_remaining,
                quota_used=len(quota_reservations) * 1600,
                quota_remaining=10000 - (len(quota_reservations) * 1600),
                quota_percentage=0.0
            )
            
            with patch.object(schedule_manager, '_check_quota_with_lock', return_value=mock_quota_status):
                with patch.object(schedule_manager, '_get_schedules_for_date_locked', return_value=[]):
                    with patch.object(schedule_manager, '_reserve_quota_for_date') as mock_reserve:
                        with patch.object(db_manager, 'session') as mock_session:
                            mock_session.return_value.__enter__.return_value = mock_db
                            mock_session.return_value.__exit__.return_value = None
                            
                            with patch.object(schedule_manager, 'get_next_available_slot', return_value=target_datetime):
                                success, message, scheduled_time = schedule_manager.schedule_video(
                                    video_path, video_type
                                )
                                
                                if success:
                                    with lock:
                                        quota_reservations.append(video_num)
                                
                                return success, message, scheduled_time
        
        # Run 10 concurrent schedule requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(schedule_video_thread, i) for i in range(10)]
            results = [f.result() for f in futures]
        
        # Verify that quota was respected (max 5 shorts per day)
        successful = [r for r in results if r[0] is True]
        assert len(successful) <= 5, f"Expected max 5 successful schedules, got {len(successful)}"
    
    def test_schedule_video_quota_reservation_for_future_date(self, schedule_manager):
        """Test that quota is reserved for scheduled date, not today"""
        from unittest.mock import Mock, patch
        from langflix.db.session import db_manager
        
        video_path = "/test/video.mp4"
        video_type = "short"
        future_date = date.today() + timedelta(days=3)
        future_datetime = datetime.combine(future_date, time(10, 0))
        
        mock_db = Mock()
        mock_quota_status = DailyQuotaStatus(
            date=future_date,
            final_used=0,
            final_remaining=2,
            short_used=0,
            short_remaining=5,
            quota_used=0,
            quota_remaining=10000,
            quota_percentage=0.0
        )
        
        with patch.object(schedule_manager, '_check_quota_with_lock', return_value=mock_quota_status):
            with patch.object(schedule_manager, '_get_schedules_for_date_locked', return_value=[]):
                with patch.object(schedule_manager, '_reserve_quota_for_date') as mock_reserve:
                    with patch.object(db_manager, 'session') as mock_session:
                        mock_session.return_value.__enter__.return_value = mock_db
                        mock_session.return_value.__exit__.return_value = None
                        
                        success, message, scheduled_time = schedule_manager.schedule_video(
                            video_path, video_type, preferred_time=future_datetime
                        )
                        
                        # Verify quota was reserved for future date, not today
                        schedule_manager._check_quota_with_lock.assert_called_once_with(mock_db, future_date)
                        schedule_manager._reserve_quota_for_date.assert_called_once_with(mock_db, future_date, video_type)
                        assert success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
