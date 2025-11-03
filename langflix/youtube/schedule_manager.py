"""
YouTube Schedule Manager
Manages YouTube upload scheduling with daily limits and smart time allocation
"""
import logging
from datetime import datetime, date, timedelta, time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from langflix.db.models import YouTubeSchedule, YouTubeQuotaUsage
from langflix.db.session import db_manager

logger = logging.getLogger(__name__)

@dataclass
class ScheduleConfig:
    """Configuration for scheduling preferences"""
    daily_limits: Dict[str, int] = None  # {'final': 2, 'short': 5}
    preferred_times: List[str] = None    # ['10:00', '14:00', '18:00']
    quota_limit: int = 10000
    warning_threshold: float = 0.8       # 80% of quota
    
    def __post_init__(self):
        if self.daily_limits is None:
            self.daily_limits = {'final': 2, 'short': 5}
        if self.preferred_times is None:
            self.preferred_times = ['10:00', '14:00', '18:00']

@dataclass
class DailyQuotaStatus:
    """Daily quota status for a specific date"""
    date: date
    final_used: int
    final_remaining: int
    short_used: int
    short_remaining: int
    quota_used: int
    quota_remaining: int
    quota_percentage: float

class YouTubeScheduleManager:
    """Manages YouTube upload scheduling with daily limits"""
    
    def __init__(self, config: Optional[ScheduleConfig] = None):
        self.config = config or ScheduleConfig()
        # Removed: self.db_session = get_db_session()
        # Database sessions now use db_manager.session() context manager on-demand
    
    def get_next_available_slot(
        self, 
        video_type: str,
        preferred_date: Optional[date] = None
    ) -> datetime:
        """
        Calculate next available upload slot based on:
        - Current schedule
        - Daily limits (2 final, 5 shorts)
        - Preferred posting times (e.g., 10 AM, 2 PM, 6 PM)
        """
        if video_type not in ['final', 'short']:
            raise ValueError(f"Invalid video_type: {video_type}. Must be 'final' or 'short'")
        
        # Start from today or preferred date
        start_date = preferred_date or date.today()
        
        # Check up to 7 days ahead
        for days_ahead in range(7):
            check_date = start_date + timedelta(days=days_ahead)
            quota_status = self.check_daily_quota(check_date)
            
            # Check if we have quota for this video type
            if video_type == 'final' and quota_status.final_remaining > 0:
                available_times = self._get_available_times_for_date(check_date, video_type)
                if available_times:
                    return available_times[0]
            elif video_type == 'short' and quota_status.short_remaining > 0:
                available_times = self._get_available_times_for_date(check_date, video_type)
                if available_times:
                    return available_times[0]
        
        # If no slots found in 7 days, return a fallback time
        logger.warning(f"No available slots found for {video_type} in next 7 days")
        return datetime.combine(start_date + timedelta(days=7), time(10, 0))
    
    def _get_available_times_for_date(self, target_date: date, video_type: str) -> List[datetime]:
        """Get available time slots for a specific date"""
        available_times = []
        
        # Parse preferred times
        preferred_times = []
        for time_str in self.config.preferred_times:
            try:
                hour, minute = map(int, time_str.split(':'))
                preferred_times.append(time(hour, minute))
            except ValueError:
                logger.warning(f"Invalid time format: {time_str}")
                continue
        
        # Get existing schedules for this date
        try:
            existing_schedules = self._get_schedules_for_date(target_date)
        except (OperationalError, SQLAlchemyError) as e:
            # Database connection error - return empty list to allow fallback time
            logger.warning(f"Database connection error getting schedules: {e}")
            existing_schedules = []
        
        # Extract times from schedules while still in session context (to avoid DetachedInstanceError)
        # Read all needed attributes before session closes
        occupied_times = set()
        for schedule in existing_schedules:
            # Access scheduled_publish_time while schedule is still attached to session
            if schedule.scheduled_publish_time:
                occupied_times.add(schedule.scheduled_publish_time.time())
        
        # Find available preferred times
        for preferred_time in preferred_times:
            if preferred_time not in occupied_times:
                available_times.append(datetime.combine(target_date, preferred_time))
        
        # If no preferred times available, find any available time
        if not available_times:
            # Try every hour from 9 AM to 9 PM
            for hour in range(9, 22):
                candidate_time = time(hour, 0)
                if candidate_time not in occupied_times:
                    available_times.append(datetime.combine(target_date, candidate_time))
                    break
        
        return available_times
    
    def _get_schedules_for_date(self, target_date: date) -> List[YouTubeSchedule]:
        """Get all schedules for a specific date"""
        try:
            start_datetime = datetime.combine(target_date, time.min)
            end_datetime = datetime.combine(target_date, time.max)
            
            with db_manager.session() as db:
                # Include all schedules with scheduled_publish_time, regardless of status
                # 'completed' schedules also occupy time slots
                return db.query(YouTubeSchedule).filter(
                    YouTubeSchedule.scheduled_publish_time >= start_datetime,
                    YouTubeSchedule.scheduled_publish_time <= end_datetime,
                    YouTubeSchedule.upload_status.in_(['scheduled', 'uploading', 'completed'])
                ).all()
        except OperationalError as e:
            # Database connection error - return empty list
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            logger.warning(f"Database connection error getting schedules (returning empty): {error_msg}")
            return []
        except Exception as e:
            logger.error(f"Database error getting schedules for date {target_date}: {e}")
            raise ValueError(f"Unable to connect to database. Please ensure PostgreSQL is running. Error: {str(e)}")
    
    def check_daily_quota(self, target_date: date) -> DailyQuotaStatus:
        """
        Check daily quota status for a specific date.
        
        Returns DailyQuotaStatus with quota information.
        If database is unavailable, returns default quota (assumes no usage).
        """
        try:
            with db_manager.session() as db:
                # Get or create quota record for this date
                quota_record = db.query(YouTubeQuotaUsage).filter(
                    YouTubeQuotaUsage.date == target_date
                ).first()
                
                if not quota_record:
                    # Create new quota record
                    quota_record = YouTubeQuotaUsage(
                        date=target_date,
                        quota_used=0,
                        quota_limit=self.config.quota_limit,
                        upload_count=0,
                        final_videos_uploaded=0,
                        short_videos_uploaded=0
                    )
                    db.add(quota_record)
                    # Commit happens automatically via context manager
                
                # Calculate remaining quotas
                final_remaining = max(0, self.config.daily_limits['final'] - quota_record.final_videos_uploaded)
                short_remaining = max(0, self.config.daily_limits['short'] - quota_record.short_videos_uploaded)
                quota_remaining = max(0, quota_record.quota_limit - quota_record.quota_used)
                quota_percentage = (quota_record.quota_used / quota_record.quota_limit) * 100 if quota_record.quota_limit > 0 else 0
                
                return DailyQuotaStatus(
                    date=target_date,
                    final_used=quota_record.final_videos_uploaded,
                    final_remaining=final_remaining,
                    short_used=quota_record.short_videos_uploaded,
                    short_remaining=short_remaining,
                    quota_used=quota_record.quota_used,
                    quota_remaining=quota_remaining,
                    quota_percentage=quota_percentage
                )
        except OperationalError as e:
            # Database connection error - return default status (assume no usage)
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            logger.warning(f"Database connection error checking quota (assuming no usage): {error_msg}")
            return DailyQuotaStatus(
                date=target_date,
                final_used=0,
                final_remaining=self.config.daily_limits.get('final', 2),
                short_used=0,
                short_remaining=self.config.daily_limits.get('short', 5),
                quota_used=0,
                quota_remaining=self.config.quota_limit,
                quota_percentage=0.0
            )
        except Exception as e:
            logger.error(f"Database error checking daily quota for {target_date}: {e}")
            raise ValueError(f"Unable to connect to database. Please ensure PostgreSQL is running. Error: {str(e)}")
    
    def schedule_video(
        self,
        video_path: str,
        video_type: str,
        preferred_time: Optional[datetime] = None
    ) -> Tuple[bool, str, Optional[datetime]]:
        """
        Schedule video upload.
        If preferred_time is None, auto-assign next available slot.
        Validates against daily limits.
        
        Returns: (success, message, scheduled_time)
        """
        if video_type not in ['final', 'short']:
            return False, f"Invalid video_type: {video_type}", None
        
        # Determine target date and time
        if preferred_time:
            target_date = preferred_time.date()
            target_datetime = preferred_time
        else:
            target_datetime = self.get_next_available_slot(video_type)
            target_date = target_datetime.date()
        
        # Check quota for target date
        quota_status = self.check_daily_quota(target_date)
        
        # Validate quota limits
        if video_type == 'final' and quota_status.final_remaining <= 0:
            return False, f"No remaining quota for final videos on {target_date}. Used: {quota_status.final_used}/{self.config.daily_limits['final']}", None
        
        if video_type == 'short' and quota_status.short_remaining <= 0:
            return False, f"No remaining quota for short videos on {target_date}. Used: {quota_status.short_used}/{self.config.daily_limits['short']}", None
        
        # Check quota usage
        if quota_status.quota_remaining < 1600:  # Upload costs 1600 quota units
            return False, f"Insufficient API quota. Remaining: {quota_status.quota_remaining}/1600 required", None
        
        # Check if time slot is available
        existing_schedules = self._get_schedules_for_date(target_date)
        # Extract scheduled_publish_time while schedules are still attached to session
        occupied_times = set()
        for schedule in existing_schedules:
            # Access scheduled_publish_time while schedule is still attached to session
            if schedule.scheduled_publish_time:
                occupied_times.add(schedule.scheduled_publish_time)
        
        if target_datetime in occupied_times:
            # Find next available time
            target_datetime = self.get_next_available_slot(video_type, target_date)
            if target_datetime.date() != target_date:
                return False, f"Requested time slot is occupied. Next available: {target_datetime}", None
        
        # Create schedule record
        try:
            with db_manager.session() as db:
                schedule = YouTubeSchedule(
                    video_path=video_path,
                    video_type=video_type,
                    scheduled_publish_time=target_datetime,
                    upload_status='scheduled'
                )
                db.add(schedule)
                # Commit happens automatically via context manager
                
                logger.info(f"Scheduled {video_type} video for {target_datetime}: {video_path}")
                return True, f"Video scheduled for {target_datetime}", target_datetime
                
        except OperationalError as e:
            # Database connection errors (PostgreSQL not running, wrong credentials, etc.)
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            logger.error(f"Database connection error scheduling video: {error_msg}")
            return False, f"Database connection failed. Please ensure PostgreSQL is running.", None
        except (ValueError, SQLAlchemyError) as e:
            # Other database errors
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            logger.error(f"Database error scheduling video: {error_msg}")
            return False, f"Database error: {error_msg}", None
        except Exception as e:
            logger.error(f"Failed to schedule video: {e}", exc_info=True)
            return False, f"Failed to schedule video: {str(e)}", None
    
    def get_schedule_calendar(self, start_date: date, days: int = 7) -> Dict[str, List[Dict]]:
        """Get scheduled uploads calendar view for a date range"""
        try:
            end_date = start_date + timedelta(days=days)
            
            with db_manager.session() as db:
                schedules = db.query(YouTubeSchedule).filter(
                    YouTubeSchedule.scheduled_publish_time >= datetime.combine(start_date, time.min),
                    YouTubeSchedule.scheduled_publish_time <= datetime.combine(end_date, time.max)
                ).order_by(YouTubeSchedule.scheduled_publish_time).all()
                
                # Group by date
                calendar = {}
                for schedule in schedules:
                    date_key = schedule.scheduled_publish_time.date().isoformat()
                    if date_key not in calendar:
                        calendar[date_key] = []
                    
                    calendar[date_key].append({
                        'id': str(schedule.id),
                        'video_path': schedule.video_path,
                        'video_type': schedule.video_type,
                        'scheduled_time': schedule.scheduled_publish_time.isoformat(),
                        'status': schedule.upload_status,
                        'youtube_video_id': schedule.youtube_video_id
                    })
                
                return calendar
        except Exception as e:
            logger.error(f"Database error getting schedule calendar: {e}")
            raise ValueError(f"Unable to connect to database. Please ensure PostgreSQL is running. Error: {str(e)}")
    
    def update_quota_usage(self, video_type: str, quota_used: int = 1600):
        """Update quota usage after successful upload"""
        try:
            today = date.today()
            
            with db_manager.session() as db:
                quota_record = db.query(YouTubeQuotaUsage).filter(
                    YouTubeQuotaUsage.date == today
                ).first()
                
                if not quota_record:
                    quota_record = YouTubeQuotaUsage(
                        date=today,
                        quota_used=0,
                        quota_limit=self.config.quota_limit,
                        upload_count=0,
                        final_videos_uploaded=0,
                        short_videos_uploaded=0
                    )
                    db.add(quota_record)
                
                # Update quota usage
                quota_record.quota_used += quota_used
                quota_record.upload_count += 1
                
                if video_type == 'final':
                    quota_record.final_videos_uploaded += 1
                elif video_type == 'short':
                    quota_record.short_videos_uploaded += 1
                
                # Commit happens automatically via context manager
                logger.info(f"Updated quota usage: {quota_used} units for {video_type} video")
        except Exception as e:
            logger.error(f"Database error updating quota usage: {e}")
            raise ValueError(f"Unable to connect to database. Please ensure PostgreSQL is running. Error: {str(e)}")
    
    def get_quota_warnings(self) -> List[str]:
        """Get quota usage warnings"""
        warnings = []
        today = date.today()
        quota_status = self.check_daily_quota(today)
        
        # Check quota percentage
        if quota_status.quota_percentage >= (self.config.warning_threshold * 100):
            warnings.append(f"API quota usage is {quota_status.quota_percentage:.1f}% ({quota_status.quota_used}/{quota_status.quota_remaining + quota_status.quota_used})")
        
        # Check daily limits
        if quota_status.final_remaining <= 1:
            warnings.append(f"Only {quota_status.final_remaining} final video slot(s) remaining today")
        
        if quota_status.short_remaining <= 1:
            warnings.append(f"Only {quota_status.short_remaining} short video slot(s) remaining today")
        
        return warnings
    
    def update_schedule_with_video_id(self, video_path: str, youtube_video_id: str, status: str = 'completed'):
        """Update schedule record with YouTube video ID after successful upload"""
        try:
            with db_manager.session() as db:
                schedule = db.query(YouTubeSchedule).filter_by(video_path=video_path).first()
                if schedule:
                    schedule.youtube_video_id = youtube_video_id
                    schedule.upload_status = status
                    # Commit happens automatically via context manager
                    logger.info(f"Updated schedule for {video_path} with video_id: {youtube_video_id}, status: {status}")
                    return True
                else:
                    logger.warning(f"No schedule found for video_path: {video_path}")
                    return False
        except Exception as e:
            logger.error(f"Failed to update schedule with video_id: {e}", exc_info=True)
            return False
    
    def cancel_schedule(self, schedule_id: str) -> bool:
        """Cancel a scheduled upload"""
        try:
            with db_manager.session() as db:
                schedule = db.query(YouTubeSchedule).filter(
                    YouTubeSchedule.id == schedule_id
                ).first()
                
                if not schedule:
                    return False
                
                if schedule.upload_status in ['uploading', 'completed']:
                    return False  # Cannot cancel already processing/completed uploads
                
                schedule.upload_status = 'failed'
                schedule.error_message = 'Cancelled by user'
                # Commit happens automatically via context manager
                
                logger.info(f"Cancelled schedule: {schedule_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to cancel schedule {schedule_id}: {e}", exc_info=True)
            return False
