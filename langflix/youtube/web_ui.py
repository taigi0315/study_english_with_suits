"""
Simple Web UI for Video File Management
Provides a web interface to view and manage generated videos
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_file, render_template_string
from langflix.youtube.video_manager import VideoFileManager, VideoMetadata
from langflix.youtube.uploader import YouTubeUploader, YouTubeUploadResult, YouTubeUploadManager
from langflix.youtube.metadata_generator import YouTubeMetadataGenerator
from langflix.youtube.schedule_manager import YouTubeScheduleManager, ScheduleConfig
from langflix.db.models import YouTubeAccount, YouTubeQuotaUsage
from langflix.db.session import db_manager
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
        
        # Initialize OAuth state storage (use Redis if available)
        oauth_state_storage = None
        try:
            from langflix.core.redis_client import get_redis_job_manager
            redis_manager = get_redis_job_manager()
            oauth_state_storage = redis_manager.redis_client
            logger.info("Using Redis for OAuth state storage")
        except Exception as e:
            logger.warning(f"Redis not available for OAuth state storage, using in-memory: {e}")
            oauth_state_storage = None
        
        self.upload_manager = YouTubeUploadManager()
        # Pass OAuth state storage to uploader
        if hasattr(self.upload_manager, 'uploader'):
            self.upload_manager.uploader.oauth_state_storage = oauth_state_storage
        
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
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
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
        
        @self.app.route('/assets/<path:filename>')
        def serve_static_assets(filename):
            """Serve static assets like icons"""
            try:
                # Get the project root directory
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                assets_path = os.path.join(project_root, 'assets', filename)
                
                if os.path.exists(assets_path):
                    return send_file(assets_path)
                else:
                    return jsonify({"error": "Asset not found"}), 404
                    
            except Exception as e:
                logger.error(f"Error serving asset {filename}: {e}")
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
            """Authenticate with YouTube (supports both Desktop and Web flow)"""
            data = request.get_json() or {}
            email = data.get('email')  # Optional email for web flow
            use_web_flow = data.get('use_web_flow', False)  # Default to Desktop flow
            
            if use_web_flow or email:
                # Generate auth URL for web flow
                try:
                    # Get redirect URI (use Flask's request host)
                    redirect_uri = f"http://localhost:{self.port}/api/youtube/auth/callback"
                    
                    auth_data = self.upload_manager.uploader.get_authorization_url(
                        redirect_uri=redirect_uri,
                        email=email
                    )
                    return jsonify({
                        "auth_url": auth_data['url'],
                        "state": auth_data['state'],
                        "flow": "web"
                    })
                except FileNotFoundError as e:
                    logger.error(f"YouTube credentials file not found: {e}")
                    return jsonify({
                        "error": "YouTube credentials file not found",
                        "details": str(e),
                        "hint": (
                            "Please download OAuth2 credentials from Google Cloud Console and save as 'youtube_credentials.json'.\n"
                            "See docs/YOUTUBE_SETUP_GUIDE_eng.md for detailed setup instructions.\n"
                            "Note: This is different from Gemini API key in .env file."
                        ),
                        "setup_guide": "docs/YOUTUBE_SETUP_GUIDE_eng.md"
                    }), 400
                except Exception as e:
                    logger.error(f"Error generating OAuth URL: {e}", exc_info=True)
                    return jsonify({
                        "error": "Failed to generate OAuth URL",
                        "details": str(e)
                    }), 500
            else:
                # Use existing Desktop flow
                try:
                    success = self.upload_manager.uploader.authenticate()
                    if success:
                        # Get channel info and save to database
                        channel_info = self.upload_manager.uploader.get_channel_info()
                        if channel_info:
                            self._save_youtube_account(channel_info)
                        
                        return jsonify({
                            "message": "Successfully authenticated with YouTube",
                            "channel": channel_info,
                            "flow": "desktop"
                        })
                    else:
                        return jsonify({"error": "Authentication failed"}), 401
                except FileNotFoundError as e:
                    logger.error(f"YouTube credentials file not found: {e}")
                    return jsonify({
                        "error": "YouTube credentials file not found",
                        "details": str(e),
                        "hint": (
                            "Please download OAuth2 credentials from Google Cloud Console and save as 'youtube_credentials.json'.\n"
                            "See docs/YOUTUBE_SETUP_GUIDE_eng.md for detailed setup instructions.\n"
                            "Note: This is different from Gemini API key in .env file."
                        ),
                        "setup_guide": "docs/YOUTUBE_SETUP_GUIDE_eng.md"
                    }), 400
                except OSError as e:
                    logger.error(f"YouTube OAuth port conflict: {e}")
                    return jsonify({
                        "error": "Port 8080 is already in use",
                        "details": str(e),
                        "hint": "Please close other applications using port 8080"
                    }), 500
                except Exception as e:
                    logger.error(f"Error authenticating with YouTube: {e}", exc_info=True)
                    return jsonify({
                        "error": "Authentication failed",
                        "details": str(e)
                    }), 500
        
        @self.app.route('/api/youtube/auth/callback')
        def youtube_auth_callback():
            """Handle OAuth callback from Google"""
            authorization_code = request.args.get('code')
            state = request.args.get('state')
            error = request.args.get('error')
            error_description = request.args.get('error_description', 'Unknown error')
            
            if error:
                logger.error(f"OAuth error: {error} - {error_description}")
                return render_template_string(
                    '<html><head><title>Authentication Failed</title></head>'
                    '<body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">'
                    '<h1 style="color: #d32f2f;">❌ Authentication Failed</h1>'
                    '<p style="color: #666;">{{ error_description }}</p>'
                    '<p style="font-size: 0.9em; color: #999; margin-top: 30px;">This window will close automatically...</p>'
                    '<script>'
                    'window.opener.postMessage({type: "youtube-auth-error", error: "{{ error }}", details: "{{ error_description }}"}, "*");'
                    'setTimeout(() => window.close(), 3000);'
                    '</script>'
                    '</body></html>',
                    error=error,
                    error_description=error_description
                ), 400
            
            if not authorization_code or not state:
                return render_template_string(
                    '<html><head><title>Authentication Error</title></head>'
                    '<body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">'
                    '<h1 style="color: #d32f2f;">❌ Authentication Error</h1>'
                    '<p style="color: #666;">Missing authorization code or state</p>'
                    '<script>setTimeout(() => window.close(), 3000);</script>'
                    '</body></html>'
                ), 400
            
            try:
                redirect_uri = f"http://localhost:{self.port}/api/youtube/auth/callback"
                
                success = self.upload_manager.uploader.authenticate_from_callback(
                    authorization_code=authorization_code,
                    state=state,
                    redirect_uri=redirect_uri
                )
                
                if success:
                    # Get channel info and save to database
                    channel_info = self.upload_manager.uploader.get_channel_info()
                    if channel_info:
                        self._save_youtube_account(channel_info)
                    
                    # Serialize channel_info to JSON for safe embedding
                    channel_info_json = json.dumps(channel_info) if channel_info else 'null'
                    
                    return render_template_string(
                        '<html><head><title>Authentication Successful</title></head>'
                        '<body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">'
                        '<h1 style="color: #4caf50;">✅ Authentication Successful!</h1>'
                        '<p style="color: #666;">You can close this window now.</p>'
                        '<script>'
                        'window.opener.postMessage({type: "youtube-auth-success", channel: {{ channel_info_json | safe }}}, "*");'
                        'setTimeout(() => window.close(), 2000);'
                        '</script>'
                        '</body></html>',
                        channel_info_json=channel_info_json
                    )
                else:
                    return render_template_string(
                        '<html><head><title>Authentication Failed</title></head>'
                        '<body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">'
                        '<h1 style="color: #d32f2f;">❌ Authentication Failed</h1>'
                        '<p style="color: #666;">Could not complete authentication</p>'
                        '<script>setTimeout(() => window.close(), 3000);</script>'
                        '</body></html>'
                    ), 500
                    
            except ValueError as e:
                # Invalid state (CSRF protection)
                logger.error(f"Invalid OAuth state: {e}")
                return render_template_string(
                    '<html><head><title>Security Error</title></head>'
                    '<body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">'
                    '<h1 style="color: #d32f2f;">❌ Security Error</h1>'
                    '<p style="color: #666;">Invalid OAuth state. Please try again.</p>'
                    '<script>setTimeout(() => window.close(), 3000);</script>'
                    '</body></html>'
                ), 400
            except Exception as e:
                logger.error(f"OAuth callback error: {e}", exc_info=True)
                return render_template_string(
                    '<html><head><title>Authentication Error</title></head>'
                    '<body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">'
                    '<h1 style="color: #d32f2f;">❌ Authentication Error</h1>'
                    '<p style="color: #666;">{{ error }}</p>'
                    '<script>'
                    'window.opener.postMessage({type: "youtube-auth-error", error: "Authentication failed", details: "{{ error }}"}, "*");'
                    'setTimeout(() => window.close(), 3000);'
                    '</script>'
                    '</body></html>',
                    error=str(e)
                ), 500
        
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
                    return jsonify({
                        "error": "Schedule manager not available",
                        "hint": "Please ensure database is configured and PostgreSQL is running"
                    }), 503
                
                next_slot = self.schedule_manager.get_next_available_slot(video_type)
                return jsonify({
                    "next_available_time": next_slot.isoformat(),
                    "video_type": video_type
                })
            except ValueError as e:
                # Database connection errors
                error_msg = str(e)
                if "database" in error_msg.lower() or "postgresql" in error_msg.lower():
                    logger.error(f"Database connection error: {e}")
                    return jsonify({
                        "error": "Database connection failed",
                        "details": error_msg,
                        "hint": "Please ensure PostgreSQL is running: docker-compose up -d postgres (or start your PostgreSQL service)"
                    }), 503
                return jsonify({"error": error_msg}), 400
            except Exception as e:
                logger.error(f"Error getting next available time: {e}", exc_info=True)
                return jsonify({
                    "error": "Failed to get next available time",
                    "details": str(e)
                }), 500
        
        @self.app.route('/api/schedule/calendar')
        def get_schedule_calendar():
            """Get scheduled uploads calendar view"""
            try:
                if not self.schedule_manager:
                    return jsonify({
                        "error": "Schedule manager not available",
                        "hint": "Please ensure database is configured and PostgreSQL is running"
                    }), 503
                
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
            except ValueError as e:
                # Database connection errors
                error_msg = str(e)
                if "database" in error_msg.lower() or "postgresql" in error_msg.lower():
                    logger.error(f"Database connection error: {e}")
                    return jsonify({
                        "error": "Database connection failed",
                        "details": error_msg,
                        "hint": "Please ensure PostgreSQL is running: docker-compose up -d postgres (or start your PostgreSQL service)"
                    }), 503
                return jsonify({"error": error_msg}), 400
            except Exception as e:
                logger.error(f"Error getting schedule calendar: {e}", exc_info=True)
                return jsonify({
                    "error": "Failed to get schedule calendar",
                    "details": str(e)
                }), 500
        
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
                    return jsonify({
                        "error": "Schedule manager not available",
                        "hint": "Please ensure database is configured and PostgreSQL is running"
                    }), 503
                
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
                    # Check if it's a database connection error
                    error_msg = message
                    if "database" in error_msg.lower() or "postgresql" in error_msg.lower():
                        return jsonify({
                            "error": "Database connection failed",
                            "details": error_msg,
                            "hint": "Please ensure PostgreSQL is running: docker-compose up -d postgres (or start your PostgreSQL service)"
                        }), 503
                    return jsonify({"error": message}), 400
                    
            except ValueError as e:
                # Database connection errors from schedule_manager
                error_msg = str(e)
                if "database" in error_msg.lower() or "postgresql" in error_msg.lower():
                    logger.error(f"Database connection error scheduling upload: {e}")
                    return jsonify({
                        "error": "Database connection failed",
                        "details": error_msg,
                        "hint": "Please ensure PostgreSQL is running: docker-compose up -d postgres (or start your PostgreSQL service)"
                    }), 503
                return jsonify({"error": error_msg}), 400
            except Exception as e:
                logger.error(f"Error scheduling upload: {e}", exc_info=True)
                return jsonify({
                    "error": "Failed to schedule upload",
                    "details": str(e)
                }), 500
        
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
            except ValueError as e:
                # Database connection errors
                error_msg = str(e)
                if "database" in error_msg.lower() or "postgresql" in error_msg.lower():
                    logger.error(f"Database connection error: {e}")
                    return jsonify({
                        "error": "Database connection failed",
                        "details": error_msg,
                        "hint": "Please ensure PostgreSQL is running: docker-compose up -d postgres (or start your PostgreSQL service)"
                    }), 503
                return jsonify({"error": error_msg}), 400
            except Exception as e:
                logger.error(f"Error getting quota status: {e}", exc_info=True)
                return jsonify({
                    "error": "Failed to get quota status",
                    "details": str(e)
                }), 500
        
        @self.app.route('/api/video/status/<path:video_path>')
        def get_video_status(video_path):
            """Get upload status for a specific video"""
            try:
                if not self.schedule_manager:
                    return jsonify({"error": "Schedule manager not available"}), 503
                
                from langflix.db.models import YouTubeSchedule
                
                # Ensure the path starts with / (Flask strips it sometimes)
                if not video_path.startswith('/'):
                    video_path = '/' + video_path
                
                with db_manager.session() as db:
                    schedule = db.query(YouTubeSchedule).filter_by(
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
                        
            except ValueError as e:
                # Database connection errors
                error_msg = str(e)
                if "database" in error_msg.lower() or "postgresql" in error_msg.lower():
                    logger.error(f"Database connection error: {e}")
                    return jsonify({
                        "error": "Database connection failed",
                        "details": error_msg,
                        "hint": "Please ensure PostgreSQL is running: docker-compose up -d postgres (or start your PostgreSQL service)"
                    }), 503
                return jsonify({"error": error_msg}), 400
            except Exception as e:
                logger.error(f"Error getting video status: {e}", exc_info=True)
                return jsonify({
                    "error": "Failed to get video status",
                    "details": str(e)
                }), 500
        
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
                
            from langflix.db.models import YouTubeSchedule
            
            with db_manager.session() as db:
                # Find the schedule entry for this video
                schedule = db.query(YouTubeSchedule).filter_by(
                    video_path=video_path
                ).first()
                
                if schedule:
                    schedule.youtube_video_id = youtube_video_id
                    schedule.upload_status = status
                    # Commit happens automatically via context manager
                    logger.info(f"Updated video status: {video_path} -> {status}")
                else:
                    logger.warning(f"No schedule found for video: {video_path}")
                    
        except Exception as e:
            logger.error(f"Error updating video status: {e}", exc_info=True)
            # Don't raise - status update failure shouldn't block upload process
    
    def _save_youtube_account(self, channel_info: Dict[str, Any]):
        """Save YouTube account info to database"""
        try:
            from langflix.db.session import db_manager
            
            with db_manager.session() as db:
                # Check if account already exists
                existing_account = db.query(YouTubeAccount).filter(
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
                    db.add(new_account)
                
                # Commit happens automatically via context manager
                logger.info(f"Saved YouTube account: {channel_info['title']}")
                
        except Exception as e:
            logger.error(f"Failed to save YouTube account: {e}", exc_info=True)
            # Don't raise - account save failure shouldn't block authentication
    
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
            """Trigger content creation pipeline via FastAPI backend"""
            try:
                data = request.json
                
                # Validate required fields
                required_fields = ['media_id', 'video_path', 'language_code', 'language_level']
                for field in required_fields:
                    if field not in data:
                        return jsonify({"error": f"Missing required field: {field}"}), 400
                
                # Get test_mode parameter (optional, defaults to False)
                test_mode = data.get('test_mode', False)
                
                # Call FastAPI backend with file uploads
                import requests
                fastapi_url = "http://localhost:8000/api/v1/jobs"
                
                # Prepare files for upload
                files = {}
                form_data = {
                    "language_code": data['language_code'],
                    "show_name": "Suits",  # Extract from path or use default
                    "episode_name": os.path.splitext(os.path.basename(data['video_path']))[0],
                    "max_expressions": 50,
                    "language_level": data['language_level'],
                    "test_mode": test_mode,
                    "no_shorts": False
                }
                
                # Add video file if it exists
                video_file_handle = None
                subtitle_file_handle = None
                
                try:
                    if os.path.exists(data['video_path']):
                        video_file_handle = open(data['video_path'], 'rb')
                        files['video_file'] = (os.path.basename(data['video_path']), video_file_handle, 'video/mp4')
                    
                    # Add subtitle file if it exists
                    if data.get('subtitle_path') and os.path.exists(data['subtitle_path']):
                        subtitle_file_handle = open(data['subtitle_path'], 'rb')
                        files['subtitle_file'] = (os.path.basename(data['subtitle_path']), subtitle_file_handle, 'text/plain')
                    
                    # Make request to FastAPI with multipart/form-data
                    response = requests.post(fastapi_url, files=files, data=form_data)
                    
                finally:
                    # Close file handles
                    if video_file_handle:
                        video_file_handle.close()
                    if subtitle_file_handle:
                        subtitle_file_handle.close()
                
                if response.status_code == 200:
                    result = response.json()
                    return jsonify({
                        "job_id": result.get('job_id'),
                        "status": "queued",
                        "backend": "fastapi"
                    })
                else:
                    return jsonify({"error": f"FastAPI error: {response.text}"}), response.status_code
                    
            except Exception as e:
                logger.error(f"Error creating content: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/content/jobs/<job_id>')
        def get_job_status(job_id):
            """Get job status from Redis (Phase 7 architecture)"""
            try:
                # Import Redis job manager
                from langflix.core.redis_client import get_redis_job_manager
                redis_manager = get_redis_job_manager()
                
                # Get job from Redis
                job = redis_manager.get_job(job_id)
                
                if job:
                    return jsonify({
                        "job_id": job.get("job_id", job_id),
                        "status": job.get("status", "UNKNOWN"),
                        "progress": int(job.get("progress", 0)),
                        "current_step": job.get("current_step", ""),
                        "error_message": job.get("error", None)
                    })
                else:
                    # Try to get from FastAPI backend as fallback
                    import requests
                    fastapi_url = f"http://localhost:8000/api/v1/jobs/{job_id}"
                    response = requests.get(fastapi_url)
                    
                    if response.status_code == 200:
                        return jsonify(response.json())
                    else:
                        return jsonify({"error": "Job not found"}), 404
                    
            except Exception as e:
                logger.error(f"Error getting job status: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/content/batch', methods=['POST'])
        def create_batch():
            """Create batch of video processing jobs via FastAPI backend"""
            try:
                data = request.json
                
                # Validate required fields
                if 'videos' not in data or not isinstance(data['videos'], list):
                    return jsonify({"error": "videos array is required"}), 400
                
                if not data['videos']:
                    return jsonify({"error": "At least one video is required"}), 400
                
                # Call FastAPI backend batch endpoint
                import requests
                fastapi_url = "http://localhost:8000/api/v1/batch"
                
                response = requests.post(fastapi_url, json=data)
                
                if response.status_code == 200:
                    return jsonify(response.json())
                else:
                    error_detail = response.json().get('detail', response.text) if response.content else response.text
                    return jsonify({"error": f"FastAPI error: {error_detail}"}), response.status_code
                    
            except Exception as e:
                logger.error(f"Error creating batch: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/content/batch/<batch_id>')
        def get_batch_status(batch_id):
            """Get batch status from FastAPI backend"""
            try:
                import requests
                fastapi_url = f"http://localhost:8000/api/v1/batch/{batch_id}"
                response = requests.get(fastapi_url)
                
                if response.status_code == 200:
                    return jsonify(response.json())
                else:
                    error_detail = response.json().get('detail', response.text) if response.content else response.text
                    return jsonify({"error": error_detail}), response.status_code
                    
            except Exception as e:
                logger.error(f"Error getting batch status: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/content/jobs')
        def get_all_jobs():
            """Get all jobs from Redis (Phase 7 architecture)"""
            try:
                # Import Redis job manager
                from langflix.core.redis_client import get_redis_job_manager
                redis_manager = get_redis_job_manager()
                
                # Get all jobs from Redis
                all_jobs = redis_manager.get_all_jobs()
                
                # Convert to list format
                jobs_list = []
                for job_id, job_data in all_jobs.items():
                    jobs_list.append({
                        "job_id": job_data.get("job_id", job_id),
                        "media_id": job_data.get("media_id", ""),
                        "status": job_data.get("status", "UNKNOWN"),
                        "progress": int(job_data.get("progress", 0)),
                        "current_step": job_data.get("current_step", ""),
                        "created_at": job_data.get("created_at", ""),
                        "error_message": job_data.get("error", None)
                    })
                
                return jsonify(jobs_list)
            except Exception as e:
                logger.error(f"Error getting jobs: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/content/jobs/<job_id>/cancel', methods=['POST'])
        def cancel_job(job_id):
            """Cancel a job via Redis (Phase 7 architecture)"""
            try:
                # Import Redis job manager
                from langflix.core.redis_client import get_redis_job_manager
                redis_manager = get_redis_job_manager()
                
                # Get current job status
                job = redis_manager.get_job(job_id)
                if not job:
                    return jsonify({"error": "Job not found"}), 404
                
                # Check if job can be cancelled
                current_status = job.get("status", "UNKNOWN")
                if current_status in ["COMPLETED", "FAILED", "CANCELLED"]:
                    return jsonify({"error": "Job cannot be cancelled"}), 400
                
                # Update job status to cancelled
                redis_manager.update_job(job_id, {
                    "status": "CANCELLED",
                    "current_step": "Job cancelled by user"
                })
                
                return jsonify({"status": "cancelled"})
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
