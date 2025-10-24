"""
Simple Web UI for Video File Management
Provides a web interface to view and manage generated videos
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_file
from langflix.youtube.video_manager import VideoFileManager, VideoMetadata
from langflix.youtube.uploader import YouTubeUploader, YouTubeUploadResult, YouTubeUploadManager
from langflix.youtube.metadata_generator import YouTubeMetadataGenerator
from langflix.youtube.schedule_manager import YouTubeScheduleManager, ScheduleConfig
from langflix.db.models import YouTubeAccount, YouTubeQuotaUsage
from langflix.db.session import get_db_session
import logging

logger = logging.getLogger(__name__)

class VideoManagementUI:
    """Web UI for video file management"""
    
    def __init__(self, output_dir: str = "output", media_dir: str = "assets/media", port: int = 5000):
        self.output_dir = output_dir
        self.media_dir = media_dir
        self.port = port
        # Use absolute path for video manager
        import os
        abs_output_dir = os.path.abspath(output_dir)
        self.video_manager = VideoFileManager(abs_output_dir)
        self.upload_manager = YouTubeUploadManager()
        self.metadata_generator = YouTubeMetadataGenerator()
        try:
            self.schedule_manager = YouTubeScheduleManager()
        except Exception as e:
            logger.warning(f"Failed to initialize schedule manager: {e}")
            self.schedule_manager = None
        
        # Initialize media scanner
        from langflix.media.media_scanner import MediaScanner
        try:
            self.media_scanner = MediaScanner(media_dir, scan_recursive=True)
            logger.info(f"Media scanner initialized for: {media_dir}")
        except Exception as e:
            logger.warning(f"Failed to initialize media scanner: {e}")
            self.media_scanner = None
        
        # Initialize job queue
        from langflix.services.job_queue import get_job_queue
        from langflix.services.pipeline_runner import create_pipeline_processor
        self.job_queue = get_job_queue()
        
        # Set pipeline processor with progress callback
        def progress_callback(job_id: str, progress: int, message: str):
            self.job_queue.update_progress(job_id, progress, message)
        
        processor = create_pipeline_processor(progress_callback)
        self.job_queue.set_job_processor(processor)
        
        # Flask 앱 초기화 시 템플릿 디렉토리 경로 설정
        import os
        template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'templates')
        self.app = Flask(__name__, template_folder=template_dir)
        self._setup_routes()
        
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            """Main dashboard"""
            return render_template('video_dashboard.html')
        
        @self.app.route('/api/videos')
        def get_videos():
            """Get all videos as JSON (filtered to final and short only)"""
            try:
                all_videos = self.video_manager.scan_all_videos()
                # Filter to only final and short videos for upload
                uploadable_videos = self.video_manager.get_uploadable_videos(all_videos)
                return jsonify([self._video_to_dict(v) for v in uploadable_videos])
            except Exception as e:
                logger.error(f"Error getting videos: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/videos/<video_type>')
        def get_videos_by_type(video_type):
            """Get videos by type"""
            try:
                all_videos = self.video_manager.scan_all_videos()
                videos = self.video_manager.get_videos_by_type(all_videos, video_type)
                return jsonify([self._video_to_dict(v) for v in videos])
            except Exception as e:
                logger.error(f"Error getting videos by type: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/videos/episode/<episode>')
        def get_videos_by_episode(episode):
            """Get videos by episode"""
            try:
                all_videos = self.video_manager.scan_all_videos()
                videos = self.video_manager.get_videos_by_episode(all_videos, episode)
                return jsonify([self._video_to_dict(v) for v in videos])
            except Exception as e:
                logger.error(f"Error getting videos by episode: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/upload-ready')
        def get_upload_ready_videos():
            """Get videos ready for upload"""
            try:
                all_videos = self.video_manager.scan_all_videos()
                videos = self.video_manager.get_upload_ready_videos(all_videos)
                return jsonify([self._video_to_dict(v) for v in videos])
            except Exception as e:
                logger.error(f"Error getting upload ready videos: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/statistics')
        def get_statistics():
            """Get video statistics"""
            try:
                all_videos = self.video_manager.scan_all_videos()
                stats = self.video_manager.get_statistics(all_videos)
                return jsonify(stats)
            except Exception as e:
                logger.error(f"Error getting statistics: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/thumbnail/<path:video_path>')
        def generate_thumbnail(video_path):
            """Generate and serve thumbnail"""
            try:
                # Decode URL-encoded path
                video_path = video_path.replace('%2F', '/')
                
                # Ensure the path starts with / (Flask strips it sometimes)
                if not video_path.startswith('/'):
                    video_path = '/' + video_path
                
                video_file = Path(video_path)
                
                if not video_file.exists():
                    return jsonify({"error": "Video file not found"}), 404
                
                # Generate thumbnail
                thumbnail_path = video_file.parent / f"{video_file.stem}_thumb.jpg"
                success = self.video_manager.generate_thumbnail(
                    str(video_file), str(thumbnail_path)
                )
                
                if success and thumbnail_path.exists():
                    return send_file(str(thumbnail_path), mimetype='image/jpeg')
                else:
                    return jsonify({"error": "Failed to generate thumbnail"}), 500
                    
            except Exception as e:
                logger.error(f"Error generating thumbnail: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/organize')
        def organize_videos():
            """Organize videos by episode"""
            try:
                all_videos = self.video_manager.scan_all_videos()
                organized = self.video_manager.organize_videos_by_episode(all_videos)
                
                # Convert to serializable format
                result = {}
                for episode, videos in organized.items():
                    result[episode] = [self._video_to_dict(v) for v in videos]
                
                return jsonify(result)
            except Exception as e:
                logger.error(f"Error organizing videos: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/upload/preview/<path:video_path>')
        def preview_upload_metadata(video_path):
            """Preview YouTube metadata for a video"""
            try:
                # Decode URL-encoded path
                video_path = video_path.replace('%2F', '/')
                
                # Ensure the path starts with / (Flask strips it sometimes)
                if not video_path.startswith('/'):
                    video_path = '/' + video_path
                
                # Use the path as-is since it's already absolute from the API
                video_file = Path(video_path)
                
                if not video_file.exists():
                    return jsonify({"error": "Video file not found"}), 404
                
                # Find video metadata
                all_videos = self.video_manager.scan_all_videos()
                video_metadata = next((v for v in all_videos if v.path == video_path), None)
                
                if not video_metadata:
                    return jsonify({"error": "Video metadata not found"}), 404
                
                # Generate preview metadata
                preview = self.metadata_generator.preview_metadata(video_metadata)
                return jsonify(preview)
                
            except Exception as e:
                logger.error(f"Error previewing upload metadata: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/upload/queue', methods=['POST'])
        def add_to_upload_queue():
            """Add video to upload queue"""
            try:
                data = request.get_json()
                video_path = data.get('video_path')
                custom_title = data.get('custom_title')
                custom_description = data.get('custom_description')
                privacy_status = data.get('privacy_status', 'private')
                
                if not video_path:
                    return jsonify({"error": "Video path is required"}), 400
                
                # Find video metadata
                all_videos = self.video_manager.scan_all_videos()
                video_metadata = next((v for v in all_videos if v.path == video_path), None)
                
                if not video_metadata:
                    return jsonify({"error": "Video metadata not found"}), 404
                
                # Generate YouTube metadata
                youtube_metadata = self.metadata_generator.generate_metadata(
                    video_metadata,
                    custom_title=custom_title,
                    custom_description=custom_description,
                    privacy_status=privacy_status
                )
                
                # Add to upload queue
                self.upload_manager.add_to_queue(video_path, youtube_metadata)
                
                return jsonify({
                    "message": "Video added to upload queue",
                    "video_path": video_path,
                    "metadata": {
                        "title": youtube_metadata.title,
                        "description": youtube_metadata.description[:100] + "...",
                        "tags": youtube_metadata.tags,
                        "privacy_status": youtube_metadata.privacy_status
                    }
                })
                
            except Exception as e:
                logger.error(f"Error adding to upload queue: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/upload/queue')
        def get_upload_queue():
            """Get upload queue status"""
            try:
                queue_status = self.upload_manager.get_queue_status()
                return jsonify(queue_status)
            except Exception as e:
                logger.error(f"Error getting upload queue: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/upload/process', methods=['POST'])
        def process_upload_queue():
            """Process upload queue"""
            try:
                # Check if authenticated
                if not self.upload_manager.uploader.authenticated:
                    if not self.upload_manager.uploader.authenticate():
                        return jsonify({"error": "YouTube authentication failed"}), 401
                
                # Process queue
                results = self.upload_manager.process_queue()
                
                # Convert results to serializable format
                serializable_results = []
                for result in results:
                    serializable_results.append({
                        "success": result.success,
                        "video_id": result.video_id,
                        "video_url": result.video_url,
                        "error_message": result.error_message,
                        "upload_time": result.upload_time.isoformat() if result.upload_time else None
                    })
                
                return jsonify({
                    "message": f"Processed {len(results)} videos",
                    "results": serializable_results
                })
                
            except Exception as e:
                logger.error(f"Error processing upload queue: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/upload/authenticate', methods=['POST'])
        def authenticate_youtube():
            """Authenticate with YouTube API"""
            try:
                success = self.upload_manager.uploader.authenticate()
                if success:
                    return jsonify({"message": "Successfully authenticated with YouTube"})
                else:
                    return jsonify({"error": "Authentication failed"}), 401
            except Exception as e:
                logger.error(f"Error authenticating with YouTube: {e}")
                return jsonify({"error": str(e)}), 500
        
        # YouTube Account Management
        @self.app.route('/api/youtube/account')
        def get_youtube_account():
            """Get current authenticated YouTube account info"""
            try:
                channel_info = self.upload_manager.uploader.get_channel_info()
                if channel_info:
                    return jsonify({
                        "authenticated": True,
                        "channel": channel_info
                    })
                else:
                    return jsonify({
                        "authenticated": False,
                        "message": "Not authenticated with YouTube"
                    })
            except Exception as e:
                logger.error(f"Error getting YouTube account: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/youtube/login', methods=['POST'])
        def youtube_login():
            """Authenticate with YouTube (triggers OAuth flow)"""
            try:
                success = self.upload_manager.uploader.authenticate()
                if success:
                    # Get channel info and save to database
                    channel_info = self.upload_manager.uploader.get_channel_info()
                    if channel_info:
                        self._save_youtube_account(channel_info)
                    
                    return jsonify({
                        "message": "Successfully authenticated with YouTube",
                        "channel": channel_info
                    })
                else:
                    return jsonify({"error": "Authentication failed"}), 401
            except Exception as e:
                logger.error(f"Error authenticating with YouTube: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/youtube/logout', methods=['POST'])
        def youtube_logout():
            """Logout from YouTube (delete tokens)"""
            try:
                # Delete token file
                token_file = self.upload_manager.uploader.token_file
                if os.path.exists(token_file):
                    os.remove(token_file)
                
                # Reset authentication status
                self.upload_manager.uploader.authenticated = False
                self.upload_manager.uploader.service = None
                
                return jsonify({"message": "Successfully logged out from YouTube"})
            except Exception as e:
                logger.error(f"Error logging out from YouTube: {e}")
                return jsonify({"error": str(e)}), 500
        
        # Schedule Management
        @self.app.route('/api/schedule/next-available')
        def get_next_available_time():
            """Get next available upload slot for video type"""
            try:
                video_type = request.args.get('video_type', 'final')
                if video_type not in ['final', 'short']:
                    return jsonify({"error": "Invalid video_type. Must be 'final' or 'short'"}), 400
                
                if not self.schedule_manager:
                    return jsonify({"error": "Schedule manager not available"}), 503
                
                next_slot = self.schedule_manager.get_next_available_slot(video_type)
                return jsonify({
                    "next_available_time": next_slot.isoformat(),
                    "video_type": video_type
                })
            except Exception as e:
                logger.error(f"Error getting next available time: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/schedule/calendar')
        def get_schedule_calendar():
            """Get scheduled uploads calendar view"""
            try:
                if not self.schedule_manager:
                    return jsonify({"error": "Schedule manager not available"}), 503
                
                start_date_str = request.args.get('start_date')
                days = int(request.args.get('days', 7))
                
                if start_date_str:
                    from datetime import datetime
                    start_date = datetime.fromisoformat(start_date_str).date()
                else:
                    from datetime import date
                    start_date = date.today()
                
                calendar = self.schedule_manager.get_schedule_calendar(start_date, days)
                return jsonify(calendar)
            except Exception as e:
                logger.error(f"Error getting schedule calendar: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/upload/schedule', methods=['POST'])
        def schedule_upload():
            """
            Schedule video for upload at specific time
            Body: {
                video_path, 
                video_type,
                publish_time (optional - auto if not provided),
                immediate (optional - upload immediately for testing)
            }
            """
            try:
                data = request.get_json()
                video_path = data.get('video_path')
                video_type = data.get('video_type')
                publish_time_str = data.get('publish_time')
                immediate = data.get('immediate', False)
                
                if not video_path or not video_type:
                    return jsonify({"error": "video_path and video_type are required"}), 400
                
                if video_type not in ['final', 'short']:
                    return jsonify({"error": "video_type must be 'final' or 'short'"}), 400
                
                # Handle immediate upload for testing
                if immediate:
                    try:
                        from langflix.youtube.uploader import YouTubeUploader
                        uploader = YouTubeUploader()
                        
                        # Create metadata object
                        from langflix.youtube.metadata_generator import YouTubeVideoMetadata
                        metadata = YouTubeVideoMetadata(
                            title=data.get('title', 'Test Upload'),
                            description=data.get('description', 'Test upload for development'),
                            tags=data.get('tags', []),
                            category_id=data.get('category_id', '22'),
                            privacy_status='private'  # Upload as private for testing
                        )
                        
                        # Upload immediately
                        result = uploader.upload_video(
                            video_path=video_path,
                            metadata=metadata
                        )
                        
                        if result.success:
                            # Update video metadata in database
                            self._update_video_upload_status(
                                video_path, 
                                result.video_id, 
                                f"https://www.youtube.com/watch?v={result.video_id}",
                                'uploaded'
                            )
                            
                            return jsonify({
                                "success": True,
                                "message": "Video uploaded immediately for testing",
                                "video_id": result.video_id,
                                "video_url": f"https://www.youtube.com/watch?v={result.video_id}"
                            })
                        else:
                            return jsonify({
                                "success": False,
                                "error": result.error_message or 'Upload failed'
                            }), 500
                            
                    except Exception as e:
                        logger.error(f"Immediate upload failed: {e}")
                        return jsonify({"error": f"Immediate upload failed: {str(e)}"}), 500
                
                if not self.schedule_manager:
                    return jsonify({"error": "Schedule manager not available"}), 503
                
                # Parse publish time if provided
                publish_time = None
                if publish_time_str:
                    from datetime import datetime
                    publish_time = datetime.fromisoformat(publish_time_str.replace('Z', '+00:00'))
                
                # Schedule the video
                success, message, scheduled_time = self.schedule_manager.schedule_video(
                    video_path, video_type, publish_time
                )
                
                if success:
                    # Update video status to scheduled
                    self._update_video_upload_status(
                        video_path, 
                        None,  # No video ID yet
                        None,   # No URL yet
                        'scheduled'
                    )
                    
                    return jsonify({
                        "message": message,
                        "scheduled_time": scheduled_time.isoformat() if scheduled_time else None,
                        "video_path": video_path,
                        "video_type": video_type
                    })
                else:
                    return jsonify({"error": message}), 400
                    
            except Exception as e:
                logger.error(f"Error scheduling upload: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/quota/status')
        def get_quota_status():
            """Get YouTube API quota usage status"""
            try:
                if not self.schedule_manager:
                    return jsonify({"error": "Schedule manager not available"}), 503
                
                from datetime import date
                today = date.today()
                quota_status = self.schedule_manager.check_daily_quota(today)
                warnings = self.schedule_manager.get_quota_warnings()
                
                return jsonify({
                    "date": today.isoformat(),
                    "final_videos": {
                        "used": quota_status.final_used,
                        "remaining": quota_status.final_remaining,
                        "limit": self.schedule_manager.config.daily_limits['final']
                    },
                    "short_videos": {
                        "used": quota_status.short_used,
                        "remaining": quota_status.short_remaining,
                        "limit": self.schedule_manager.config.daily_limits['short']
                    },
                    "api_quota": {
                        "used": quota_status.quota_used,
                        "remaining": quota_status.quota_remaining,
                        "percentage": quota_status.quota_percentage,
                        "limit": quota_status.quota_used + quota_status.quota_remaining
                    },
                    "warnings": warnings
                })
            except Exception as e:
                logger.error(f"Error getting quota status: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/video/status/<path:video_path>')
        def get_video_status(video_path):
            """Get upload status for a specific video"""
            try:
                if not self.schedule_manager:
                    return jsonify({"error": "Schedule manager not available"}), 503
                
                from langflix.db.session import get_db_session
                from langflix.db.models import YouTubeSchedule
                
                # Ensure the path starts with / (Flask strips it sometimes)
                if not video_path.startswith('/'):
                    video_path = '/' + video_path
                
                with get_db_session() as session:
                    schedule = session.query(YouTubeSchedule).filter_by(
                        video_path=video_path
                    ).first()
                    
                    if schedule:
                        return jsonify({
                            "video_path": schedule.video_path,
                            "video_type": schedule.video_type,
                            "upload_status": schedule.upload_status,
                            "youtube_video_id": schedule.youtube_video_id,
                            "scheduled_time": schedule.scheduled_publish_time.isoformat() if schedule.scheduled_publish_time else None
                        })
                    else:
                        return jsonify({"error": "Video not found in schedule"}), 404
                        
            except Exception as e:
                logger.error(f"Error getting video status: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/video/<path:video_path>')
        def serve_video(video_path):
            """Serve video file for preview"""
            try:
                # Decode URL-encoded path
                video_path = video_path.replace('%2F', '/')
                
                # Ensure the path starts with / (Flask strips it sometimes)
                if not video_path.startswith('/'):
                    video_path = '/' + video_path
                
                # Use the path as-is since it's already absolute from the API
                video_file = Path(video_path)
                
                logger.info(f"Serving video: {video_file}")
                logger.info(f"Video file exists: {video_file.exists()}")
                logger.info(f"Video file absolute path: {video_file.absolute()}")
                
                if not video_file.exists():
                    logger.error(f"Video file not found: {video_file}")
                    import os
                    logger.error(f"Current working directory: {os.getcwd()}")
                    logger.error(f"Output directory: {self.video_manager.output_dir}")
                    return jsonify({"error": "Video file not found"}), 404
                
                # Check if it's a video file
                if video_file.suffix.lower() not in ['.mp4', '.mkv', '.avi', '.mov', '.webm']:
                    logger.error(f"Invalid video file extension: {video_file.suffix}")
                    return jsonify({"error": "Invalid video file"}), 400
                
                # Determine MIME type based on file extension
                mime_type = 'video/mp4'
                if video_file.suffix.lower() == '.mkv':
                    mime_type = 'video/x-matroska'
                elif video_file.suffix.lower() == '.avi':
                    mime_type = 'video/x-msvideo'
                elif video_file.suffix.lower() == '.mov':
                    mime_type = 'video/quicktime'
                elif video_file.suffix.lower() == '.webm':
                    mime_type = 'video/webm'
                
                # Serve the video file with proper headers for inline playback
                response = send_file(
                    str(video_file), 
                    mimetype=mime_type,
                    as_attachment=False,  # Don't force download
                    conditional=True,     # Support range requests for video seeking
                    etag=True            # Enable ETag for caching
                )
                
                # Add additional headers to force inline display
                response.headers['Content-Disposition'] = 'inline'
                response.headers['X-Content-Type-Options'] = 'nosniff'
                response.headers['Accept-Ranges'] = 'bytes'
                
                return response
                    
            except Exception as e:
                logger.error(f"Error serving video: {e}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
                return jsonify({"error": str(e)}), 500
        
        # Setup content creation routes
        self._setup_content_creation_routes()
    
    def _video_to_dict(self, video: VideoMetadata) -> Dict[str, Any]:
        """Convert VideoMetadata to dictionary"""
        # Determine upload status
        upload_status = 'not_uploaded'
        if video.uploaded_to_youtube or video.youtube_video_id:
            upload_status = 'uploaded'
        
        return {
            "path": video.path,
            "filename": video.filename,
            "size_mb": video.size_mb,
            "duration_seconds": video.duration_seconds,
            "duration_formatted": self._format_duration(video.duration_seconds),
            "resolution": video.resolution,
            "format": video.format,
            "created_at": video.created_at.isoformat(),
            "episode": video.episode,
            "expression": video.expression,
            "video_type": video.video_type,
            "language": video.language,
            "ready_for_upload": video.ready_for_upload,
            "uploaded_to_youtube": video.uploaded_to_youtube,
            "youtube_video_id": video.youtube_video_id,
            "upload_status": upload_status
        }
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in MM:SS or HH:MM:SS format"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}:{secs:02d}"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            return f"{hours}:{minutes:02d}:{secs:02d}"
    
    def _update_video_upload_status(self, video_path, youtube_video_id, youtube_url, status):
        """Update video upload status in database"""
        try:
            if not self.schedule_manager:
                return
                
            from langflix.db.session import get_db_session
            from langflix.db.models import YouTubeSchedule
            
            with get_db_session() as session:
                # Find the schedule entry for this video
                schedule = session.query(YouTubeSchedule).filter_by(
                    video_path=video_path
                ).first()
                
                if schedule:
                    schedule.youtube_video_id = youtube_video_id
                    schedule.upload_status = status
                    session.commit()
                    logger.info(f"Updated video status: {video_path} -> {status}")
                else:
                    logger.warning(f"No schedule found for video: {video_path}")
                    
        except Exception as e:
            logger.error(f"Error updating video status: {e}")
    
    def _save_youtube_account(self, channel_info: Dict[str, Any]):
        """Save YouTube account info to database"""
        try:
            db_session = get_db_session()
            
            # Check if account already exists
            existing_account = db_session.query(YouTubeAccount).filter(
                YouTubeAccount.channel_id == channel_info['channel_id']
            ).first()
            
            if existing_account:
                # Update existing account
                existing_account.channel_title = channel_info['title']
                existing_account.channel_thumbnail = channel_info['thumbnail_url']
                existing_account.last_authenticated = datetime.now()
                existing_account.is_active = True
            else:
                # Create new account
                new_account = YouTubeAccount(
                    channel_id=channel_info['channel_id'],
                    channel_title=channel_info['title'],
                    channel_thumbnail=channel_info['thumbnail_url'],
                    email=channel_info.get('email', ''),
                    last_authenticated=datetime.now(),
                    is_active=True
                )
                db_session.add(new_account)
            
            db_session.commit()
            logger.info(f"Saved YouTube account: {channel_info['title']}")
            
        except Exception as e:
            logger.error(f"Failed to save YouTube account: {e}")
            if 'db_session' in locals():
                db_session.rollback()
    
    def _setup_content_creation_routes(self):
        """Setup content creation API routes"""
        
        @self.app.route('/api/media/scan')
        def scan_media():
            """Scan media directory and return available files"""
            try:
                if not self.media_scanner:
                    return jsonify({"error": "Media scanner not initialized"}), 503
                
                media_files = self.media_scanner.scan_media_directory()
                return jsonify(media_files)
            except Exception as e:
                logger.error(f"Error scanning media: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/content/create', methods=['POST'])
        def create_content():
            """Trigger content creation pipeline"""
            try:
                data = request.json
                
                # Validate required fields
                required_fields = ['media_id', 'video_path', 'language_code', 'language_level']
                for field in required_fields:
                    if field not in data:
                        return jsonify({"error": f"Missing required field: {field}"}), 400
                
                # Enqueue job
                job_id = self.job_queue.enqueue(
                    media_id=data['media_id'],
                    video_path=data['video_path'],
                    subtitle_path=data.get('subtitle_path'),
                    language_code=data['language_code'],
                    language_level=data['language_level']
                )
                
                return jsonify({
                    "job_id": job_id,
                    "status": "queued"
                })
            except Exception as e:
                logger.error(f"Error creating content: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/content/jobs/<job_id>')
        def get_job_status(job_id):
            """Get job status"""
            try:
                job = self.job_queue.get_job(job_id)
                if not job:
                    return jsonify({"error": "Job not found"}), 404
                
                return jsonify({
                    "job_id": job.job_id,
                    "status": job.status.value,
                    "progress": job.progress,
                    "current_step": job.current_step,
                    "error_message": job.error_message,
                    "created_at": job.created_at.isoformat(),
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "result": job.result
                })
            except Exception as e:
                logger.error(f"Error getting job status: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/content/jobs')
        def get_all_jobs():
            """Get all jobs"""
            try:
                jobs = self.job_queue.get_all_jobs()
                return jsonify([{
                    "job_id": job.job_id,
                    "media_id": job.media_id,
                    "status": job.status.value,
                    "progress": job.progress,
                    "current_step": job.current_step,
                    "created_at": job.created_at.isoformat()
                } for job in jobs])
            except Exception as e:
                logger.error(f"Error getting jobs: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/content/jobs/<job_id>/cancel', methods=['POST'])
        def cancel_job(job_id):
            """Cancel a job"""
            try:
                success = self.job_queue.cancel_job(job_id)
                if success:
                    return jsonify({"status": "cancelled"})
                else:
                    return jsonify({"error": "Job cannot be cancelled"}), 400
            except Exception as e:
                logger.error(f"Error cancelling job: {e}")
                return jsonify({"error": str(e)}), 500
    
    def run(self, debug: bool = False):
        """Run the web UI"""
        logger.info(f"Starting Video Management UI on port {self.port}")
        self.app.run(host='0.0.0.0', port=self.port, debug=debug)

def create_app(output_dir: str = "output") -> Flask:
    """Create Flask app for video management"""
    ui = VideoManagementUI(output_dir)
    return ui.app

if __name__ == "__main__":
    # Create templates directory if it doesn't exist
    templates_dir = Path("templates")
    templates_dir.mkdir(exist_ok=True)
    
    # Run the UI
    ui = VideoManagementUI()
    ui.run(debug=True)
