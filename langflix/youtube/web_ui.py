"""
Simple Web UI for Video File Management
Provides a web interface to view and manage generated videos
"""
import os
import json
from pathlib import Path
from urllib.parse import unquote
from typing import List, Dict, Any
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_file, render_template_string
from langflix.youtube.video_manager import VideoFileManager, VideoMetadata
from langflix.youtube.uploader import YouTubeUploader, YouTubeUploadResult, YouTubeUploadManager
from langflix.youtube.metadata_generator import YouTubeMetadataGenerator
from langflix.youtube.schedule_manager import YouTubeScheduleManager, ScheduleConfig
from langflix.youtube.last_schedule import YouTubeLastScheduleService
from langflix.db.models import YouTubeAccount, YouTubeQuotaUsage
from langflix.db.session import db_manager
from langflix import settings
import logging

logger = logging.getLogger(__name__)

DEFAULT_API_BASE_LOCAL = "http://localhost:8000"
DEFAULT_API_BASE_DOCKER = "http://langflix-api:8000"


def _is_truthy(value: str) -> bool:
    """Convert common truthy string to boolean."""
    return value.lower() in {"1", "true", "yes", "on"} if value else False


def _is_running_inside_docker() -> bool:
    """
    Best-effort detection for Docker/Container environments.
    
    Primarily relies on explicit override via LANGFLIX_RUNNING_IN_DOCKER.
    Falls back to checking /.dockerenv or Docker markers in /proc/1/cgroup.
    """
    override = os.getenv("LANGFLIX_RUNNING_IN_DOCKER")
    if override is not None:
        return _is_truthy(override)
    
    if Path("/.dockerenv").exists():
        return True
    
    cgroup_path = Path("/proc/1/cgroup")
    try:
        if cgroup_path.exists():
            content = cgroup_path.read_text(errors="ignore")
            if "docker" in content or "container" in content:
                return True
    except OSError:
        # Ignore permission errors or missing /proc (e.g., macOS)
        pass
    
    return False


def resolve_api_base_url() -> str:
    """
    Determine API base URL with sane defaults for local and Docker environments.
    
    Priority:
    1. LANGFLIX_API_BASE_URL environment variable (user override)
    2. Detected Docker/container runtime (defaults to langflix-api hostname)
    3. Local development fallback (localhost)
    """
    raw_api_base = os.getenv("LANGFLIX_API_BASE_URL")
    if raw_api_base:
        sanitized = raw_api_base.rstrip("/")
        logger.info("Using API base URL from LANGFLIX_API_BASE_URL: %s", sanitized)
        return sanitized
    
    if _is_running_inside_docker():
        logger.info("Docker environment detected. Using default API base URL: %s", DEFAULT_API_BASE_DOCKER)
        return DEFAULT_API_BASE_DOCKER
    
    logger.info("Defaulting API base URL to local development endpoint: %s", DEFAULT_API_BASE_LOCAL)
    return DEFAULT_API_BASE_LOCAL

class VideoManagementUI:
    """Web UI for video file management"""
    
    def __init__(self, output_dir: str = "output", media_dir: str = "assets/media", port: int = 5000):
        self.api_base_url = resolve_api_base_url()
        self.output_dir = output_dir
        self.media_dir = media_dir
        self.port = port
        # Use absolute path for video manager
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
        
        # Determine if running in Docker or locally
        is_docker = os.path.exists("/app") or os.getenv("DOCKER_ENV") == "true"
        
        # Use appropriate default path based on environment
        if is_docker:
            default_creds = "/app/auth/youtube_credentials.json"
            default_token = "/app/auth/youtube_token.json"
        else:
            # Local development: use relative paths from project root
            project_root = os.getcwd()
            default_creds = os.path.join(project_root, "auth", "youtube_credentials.json")
            default_token = os.path.join(project_root, "auth", "youtube_token.json")
        
        youtube_creds_file = os.getenv("YOUTUBE_CREDENTIALS_FILE", default_creds)
        youtube_token_file = os.getenv("YOUTUBE_TOKEN_FILE", default_token)
        
        # Fallback logic: Try multiple locations (new structure -> old locations)
        if not os.path.exists(youtube_creds_file):
            project_root = os.getcwd()
            fallback_paths = [
                os.path.join(project_root, "auth", "youtube_credentials.json"),  # New location
                os.path.join(project_root, "assets", "youtube_credentials.json"),  # Old location
                os.path.join(project_root, "youtube_credentials.json"),  # Root (legacy)
            ]
            # Also check Docker path if not already checked
            if not is_docker:
                fallback_paths.append("/app/auth/youtube_credentials.json")
            
            for path in fallback_paths:
                if os.path.exists(path):
                    youtube_creds_file = path
                    logger.info(f"Found YouTube credentials at fallback location: {path}")
                    break
        
        if not os.path.exists(youtube_token_file):
            project_root = os.getcwd()
            fallback_paths = [
                os.path.join(project_root, "auth", "youtube_token.json"),  # New location
                os.path.join(project_root, "assets", "youtube_token.json"),  # Old location
                os.path.join(project_root, "youtube_token.json"),  # Root (legacy)
            ]
            # Also check Docker path if not already checked
            if not is_docker:
                fallback_paths.append("/app/auth/youtube_token.json")
            
            for path in fallback_paths:
                if os.path.exists(path):
                    youtube_token_file = path
                    logger.info(f"Found YouTube token at fallback location: {path}")
                    break
        
        self.upload_manager = YouTubeUploadManager(credentials_file=youtube_creds_file)
        # Pass OAuth state storage to uploader
        if hasattr(self.upload_manager, 'uploader'):
            self.upload_manager.uploader.oauth_state_storage = oauth_state_storage
            # Also set token file path
            self.upload_manager.uploader.token_file = youtube_token_file
        
        self.metadata_generator = YouTubeMetadataGenerator()
        try:
            self.schedule_manager = YouTubeScheduleManager()
        except Exception as e:
            logger.warning(f"Failed to initialize schedule manager: {e}")
            self.schedule_manager = None
        
        # Initialize YouTube-based lightweight scheduler
        try:
            self.yt_scheduler = YouTubeLastScheduleService()
            logger.info("YouTube-based scheduler initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize YouTube scheduler: {e}")
            self.yt_scheduler = None
        
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
        
        # Flask 앱 초기화 시 템플릿 및 정적 파일 디렉토리 설정
        current_dir = os.path.dirname(os.path.abspath(__file__)) # langflix/youtube
        parent_dir = os.path.dirname(current_dir) # langflix
        template_dir = os.path.join(parent_dir, 'templates')
        static_dir = os.path.join(parent_dir, 'static')
        
        self.app = Flask(__name__, 
                        template_folder=template_dir,
                        static_folder=static_dir,
                        static_url_path='/static')
        
        # Disable Flask/Werkzeug HTTP request logging (too verbose and not useful)
        # Only log errors and warnings
        import logging as std_logging
        werkzeug_logger = std_logging.getLogger('werkzeug')
        werkzeug_logger.setLevel(std_logging.WARNING)
        
        # Register error handlers to ensure JSON responses for API errors
        self._setup_error_handlers()
        
        self._setup_routes()
    
    def _setup_error_handlers(self):
        """Setup error handlers to return JSON for API routes"""
        
        @self.app.errorhandler(404)
        def not_found(error):
            """Return JSON for 404 errors on API routes"""
            if request.path.startswith('/api/'):
                return jsonify({
                    "error": "Endpoint not found",
                    "path": request.path
                }), 404
            return error
        
        @self.app.errorhandler(500)
        def internal_error(error):
            """Return JSON for 500 errors on API routes"""
            if request.path.startswith('/api/'):
                logger.error(f"Internal server error on {request.path}: {error}", exc_info=True)
                return jsonify({
                    "error": "Internal server error",
                    "path": request.path,
                    "details": str(error) if logger.level <= logging.DEBUG else None
                }), 500
            return error
        
        @self.app.errorhandler(Exception)
        def handle_exception(e):
            """Handle all unhandled exceptions"""
            if request.path.startswith('/api/'):
                logger.error(f"Unhandled exception on {request.path}: {e}", exc_info=True)
                return jsonify({
                    "error": "An error occurred",
                    "details": str(e),
                    "type": type(e).__name__
                }), 500
            # Re-raise for non-API routes to use Flask's default handling
            raise e
    
    def _build_api_url(self, path: str) -> str:
        """Build API URL using configured base URL"""
        return f"{self.api_base_url}{path}"
    
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
                video_path = unquote(video_path)
                
                # Ensure the path starts with / (Flask strips it sometimes)
                if not video_path.startswith('/'):
                    video_path = '/' + video_path
                
                video_file = Path(video_path)
                
                if not video_file.exists():
                    return jsonify({"error": "Video file not found"}), 404
                
                # Generate thumbnail to temporary file (not saved to disk)
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                    thumbnail_path = tmp_file.name
                
                try:
                    success = self.video_manager.generate_thumbnail(
                        str(video_file), thumbnail_path
                    )
                    
                    if success and Path(thumbnail_path).exists():
                        # Send file and then delete it
                        response = send_file(thumbnail_path, mimetype='image/jpeg')
                        # Delete temporary file after sending
                        try:
                            Path(thumbnail_path).unlink()
                        except Exception:
                            pass  # Ignore cleanup errors
                        return response
                    else:
                        return jsonify({"error": "Failed to generate thumbnail"}), 500
                except Exception as e:
                    # Clean up temp file on error
                    try:
                        Path(thumbnail_path).unlink()
                    except Exception:
                        pass
                    raise
                    
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
        
        @self.app.route('/api/explore')
        def explore_directory():
            """Explore directory structure - returns files and subdirectories"""
            try:
                # Get path parameter (default to output directory)
                path = request.args.get('path', '')
                
                # Start from output directory if path is empty or relative
                if not path or not os.path.isabs(path):
                    base_path = Path(self.output_dir).resolve()
                    if path:
                        # Join relative path to base
                        target_path = base_path / path
                    else:
                        target_path = base_path
                else:
                    # Absolute path provided
                    target_path = Path(path)
                
                # Security: Ensure path is within output directory
                base_path = Path(self.output_dir).resolve()
                try:
                    target_path = target_path.resolve()
                    # Check if target_path is within base_path
                    if not str(target_path).startswith(str(base_path)):
                        return jsonify({"error": "Access denied: Path outside output directory"}), 403
                except (OSError, ValueError) as e:
                    return jsonify({"error": f"Invalid path: {e}"}), 400
                
                if not target_path.exists():
                    return jsonify({"error": "Path does not exist"}), 404
                
                if not target_path.is_dir():
                    return jsonify({"error": "Path is not a directory"}), 400
                
                # Get directory contents
                items = []
                for item in sorted(target_path.iterdir()):
                    try:
                        # Filter out .DS_Store files (macOS system files)
                        if item.name == '.DS_Store':
                            continue
                        
                        # Filter out thumbnail files (they're generated on-demand)
                        if item.name.endswith('_thumb.jpg'):
                            continue
                        
                        # Filter out .json metadata files (TICKET-070)
                        if item.is_file() and item.suffix.lower() == '.json':
                            continue
                        
                        stat = item.stat()
                        item_info = {
                            "name": item.name,
                            "path": str(item.relative_to(base_path)),
                            "absolute_path": str(item),
                            "is_directory": item.is_dir(),
                            "is_file": item.is_file(),
                            "size": stat.st_size if item.is_file() else 0,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        }
                        
                        # Add file extension for files
                        if item.is_file():
                            item_info["extension"] = item.suffix.lower()
                            # Check if it's a video file
                            video_extensions = {'.mkv', '.mp4', '.avi', '.mov', '.webm'}
                            item_info["is_video"] = item.suffix.lower() in video_extensions
                        else:
                            item_info["extension"] = None
                            item_info["is_video"] = False
                        
                        items.append(item_info)
                    except (OSError, PermissionError) as e:
                        logger.warning(f"Could not access {item}: {e}")
                        continue
                
                # Calculate parent path
                parent_path = None
                if target_path != base_path:
                    try:
                        parent = target_path.parent
                        if parent.resolve() != base_path.resolve() and str(parent.resolve()).startswith(str(base_path)):
                            parent_path = str(parent.relative_to(base_path))
                        else:
                            parent_path = ""
                    except Exception:
                        parent_path = None
                
                return jsonify({
                    "path": str(target_path.relative_to(base_path)),
                    "absolute_path": str(target_path),
                    "parent_path": parent_path,
                    "items": items,
                    "item_count": len(items)
                })
                
            except Exception as e:
                logger.error(f"Error exploring directory: {e}", exc_info=True)
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/explore/file-info')
        def get_file_info():
            """Get detailed information about a file"""
            try:
                path = request.args.get('path', '')
                if not path:
                    return jsonify({"error": "Path parameter required"}), 400
                
                base_path = Path(self.output_dir).resolve()
                if not os.path.isabs(path):
                    target_path = base_path / path
                else:
                    target_path = Path(path)
                
                # Security check
                try:
                    target_path = target_path.resolve()
                    if not str(target_path).startswith(str(base_path)):
                        return jsonify({"error": "Access denied"}), 403
                except (OSError, ValueError):
                    return jsonify({"error": "Invalid path"}), 400
                
                if not target_path.exists():
                    return jsonify({"error": "File not found"}), 404
                
                stat = target_path.stat()
                info = {
                    "name": target_path.name,
                    "path": str(target_path.relative_to(base_path)),
                    "absolute_path": str(target_path),
                    "size": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "is_directory": target_path.is_dir(),
                    "is_file": target_path.is_file(),
                }
                
                # Add video-specific info if it's a video file
                if target_path.is_file() and target_path.suffix.lower() in {'.mkv', '.mp4', '.avi', '.mov', '.webm'}:
                    try:
                        from langflix.media.ffmpeg_utils import get_duration_seconds, get_video_params
                        duration = get_duration_seconds(str(target_path))
                        video_params = get_video_params(str(target_path))
                        info["duration_seconds"] = duration
                        info["duration_formatted"] = f"{int(duration // 60)}m {int(duration % 60)}s"
                        info["video_codec"] = video_params.codec
                        info["resolution"] = f"{video_params.width}x{video_params.height}" if video_params.width and video_params.height else None
                    except Exception as e:
                        logger.debug(f"Could not get video info: {e}")
                        info["duration_seconds"] = None
                
                return jsonify(info)
                
            except Exception as e:
                logger.error(f"Error getting file info: {e}")
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
            except (FileNotFoundError, ValueError) as e:
                # Expected errors when not authenticated or credentials missing
                logger.info(f"YouTube account check failed (expected if not logged in): {e}")
                return jsonify({
                    "authenticated": False,
                    "message": str(e)
                })
            except Exception as e:
                logger.error(f"Error getting YouTube account: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/youtube/channels')
        def get_youtube_channels():
            """Get all installed YouTube accounts (tokens)"""
            try:
                # Scan tokens directory for available accounts
                accounts = self.upload_manager.scan_accounts()
                
                # Also list accessible channels for current token (for legacy reasons or if needed)
                # But primarily we want "accounts" we can switch to.
                # scan_accounts returns list of dicts with channel info
                
                if accounts:
                    return jsonify({
                        "authenticated": True,
                        "channels": accounts,
                        "count": len(accounts)
                    })
                else:
                    return jsonify({
                        "authenticated": False,
                        "channels": [],
                        "message": "No YouTube accounts found"
                    })
            except Exception as e:
                logger.error(f"Error getting YouTube accounts: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/youtube/account/switch', methods=['POST'])
        def switch_youtube_account():
            """Switch active YouTube account"""
            data = request.get_json() or {}
            channel_id = data.get('channel_id')
            
            if not channel_id:
                return jsonify({"error": "channel_id is required"}), 400
                
            try:
                success = self.upload_manager.switch_account(channel_id)
                if success:
                    # Get new channel info
                    info = self.upload_manager.uploader.get_channel_info()
                    return jsonify({
                        "success": True, 
                        "message": f"Switched to channel {channel_id}",
                        "channel": info
                    })
                else:
                    return jsonify({"error": "Failed to switch account or account not found"}), 404
            except Exception as e:
                logger.error(f"Error switching account: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/youtube/login', methods=['POST'])
        def youtube_login():
            """Authenticate with YouTube (supports both Desktop and Web flow)"""
            data = request.get_json(silent=True) or {}
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
                except ImportError as e:
                    logger.error(f"Missing OAuth library: {e}")
                    return jsonify({
                        "error": "OAuth library not available",
                        "details": str(e),
                        "hint": "Please install: pip install google-auth-oauthlib"
                    }), 500
                except ValueError as e:
                    logger.error(f"Invalid OAuth configuration: {e}")
                    error_msg = str(e)
                    # Check if it's an empty file error
                    if "empty" in error_msg.lower() or "invalid json" in error_msg.lower():
                        return jsonify({
                            "error": "Invalid YouTube credentials file",
                            "details": error_msg,
                            "hint": (
                                "The youtube_credentials.json file is empty or contains invalid JSON.\n"
                                "Please download OAuth2 credentials from Google Cloud Console and save as 'youtube_credentials.json'.\n"
                                "See docs/youtube/YOUTUBE_SETUP_GUIDE_eng.md for detailed setup instructions."
                            ),
                            "setup_guide": "docs/youtube/YOUTUBE_SETUP_GUIDE_eng.md"
                        }), 400
                    return jsonify({
                        "error": "Invalid OAuth configuration",
                        "details": error_msg,
                        "hint": "Please check your youtube_credentials.json file format"
                    }), 400
                except Exception as e:
                    logger.error(f"Error generating OAuth URL: {e}", exc_info=True)
                    import traceback
                    error_trace = traceback.format_exc()
                    logger.error(f"Full traceback: {error_trace}")
                    return jsonify({
                        "error": "Failed to generate OAuth URL",
                        "details": str(e),
                        "type": type(e).__name__
                    }), 500
            else:
                # Use existing Desktop flow
                try:
                    success = self.upload_manager.uploader.authenticate()
                    if success:
                        # Get channel info and save to database
                        channel_info = self.upload_manager.uploader.get_channel_info()
                        if channel_info:
                            try:
                                self._save_youtube_account(channel_info)
                            except Exception as e:
                                logger.warning(f"Failed to save account to DB (ignoring): {e}")
                            
                            # AUTO-SAVE account to tokens dir
                            self.upload_manager.save_current_account()
                        
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
                except ValueError as e:
                    error_msg = str(e)
                    # Check if it's an empty file or invalid JSON error
                    if "empty" in error_msg.lower() or "invalid json" in error_msg.lower():
                        logger.error(f"Invalid YouTube credentials file: {e}")
                        return jsonify({
                            "error": "Invalid YouTube credentials file",
                            "details": error_msg,
                            "hint": (
                                "The youtube_credentials.json file is empty or contains invalid JSON.\n"
                                "Please download OAuth2 credentials from Google Cloud Console and save as 'youtube_credentials.json'.\n"
                                "See docs/youtube/YOUTUBE_SETUP_GUIDE_eng.md for detailed setup instructions."
                            ),
                            "setup_guide": "docs/youtube/YOUTUBE_SETUP_GUIDE_eng.md"
                        }), 400
                    logger.error(f"Invalid OAuth configuration: {e}")
                    return jsonify({
                        "error": "Invalid OAuth configuration",
                        "details": error_msg,
                        "hint": "Please check your youtube_credentials.json file format"
                    }), 400
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
                        try:
                            self._save_youtube_account(channel_info)
                        except Exception as e:
                            logger.warning(f"Failed to save account to DB in callback (ignoring): {e}")
                            
                        # AUTO-SAVE account to tokens dir
                        self.upload_manager.save_current_account()
                    
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
                
                # Initialize lightweight YouTube-based scheduler (no DB dependency)
                try:
                    from langflix.youtube.last_schedule import YouTubeLastScheduleService, LastScheduleConfig
                    yt_scheduler = YouTubeLastScheduleService(LastScheduleConfig())
                except Exception as e:
                    logger.warning(f"Failed to initialize YouTubeLastScheduleService: {e}")
                    yt_scheduler = None
                
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
                        logger.info(f"Starting immediate upload: {video_path}")
                        result = uploader.upload_video(
                            video_path=video_path,
                            metadata=metadata
                        )
                        
                        logger.info(f"Upload result: success={result.success}, error={result.error_message}")
                        
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
                            error_msg = result.error_message or 'Upload failed'
                            logger.error(f"Upload failed: {error_msg}")
                            return jsonify({
                                "success": False,
                                "error": error_msg
                            }), 500
                            
                    except Exception as e:
                        error_msg = f"Immediate upload exception: {type(e).__name__}: {str(e)}"
                        logger.error(error_msg, exc_info=True)
                        return jsonify({
                            "error": error_msg,
                            "details": str(e)
                        }), 500
                
                if not self.schedule_manager:
                    return jsonify({
                        "error": "Schedule manager not available",
                        "hint": "Please ensure database is configured and PostgreSQL is running"
                    }), 503
                
                # Parse publish time if provided
                from datetime import datetime, timezone
                publish_time = None
                if publish_time_str:
                    publish_time = datetime.fromisoformat(publish_time_str.replace('Z', '+00:00'))
                    # Ensure timezone-aware
                    if publish_time.tzinfo is None:
                        publish_time = publish_time.replace(tzinfo=timezone.utc)
                else:
                    # Get next available slot if not provided
                    # For context videos (context_slide_combined), treat as 'short' type
                    # For long-form videos, treat as 'final' type
                    if video_type == 'context':
                        schedule_video_type = 'short'
                    elif video_type == 'long-form':
                        schedule_video_type = 'final'
                    else:
                        schedule_video_type = video_type
                    
                    publish_time = self.schedule_manager.get_next_available_slot(schedule_video_type)
                    logger.info(f"Auto-calculated next available slot for {video_type} (mapped to {schedule_video_type}): {publish_time}")
                
                # Validate quota before attempting upload
                from datetime import date
                quota_status = self.schedule_manager.check_daily_quota(publish_time.date())
                
                # Validate quota limits
                if video_type == 'final' and quota_status.final_remaining <= 0:
                    return jsonify({
                        "error": f"No remaining quota for final videos on {publish_time.date()}. Used: {quota_status.final_used}/{self.schedule_manager.config.daily_limits['final']}"
                    }), 400
                
                if video_type == 'short' and quota_status.short_remaining <= 0:
                    return jsonify({
                        "error": f"No remaining quota for short videos on {publish_time.date()}. Used: {quota_status.short_used}/{self.schedule_manager.config.daily_limits['short']}"
                    }), 400
                
                # Check quota usage
                if quota_status.quota_remaining < 1600:  # Upload costs 1600 quota units
                    return jsonify({
                        "error": f"Insufficient API quota. Remaining: {quota_status.quota_remaining}/1600 required"
                    }), 400
                
                # Generate metadata before upload
                from langflix.youtube.video_manager import VideoFileManager
                from langflix.youtube.metadata_generator import YouTubeMetadataGenerator
                
                video_manager = VideoFileManager()
                all_videos = video_manager.scan_all_videos()
                
                # Try to find video by path (handle both absolute and relative paths)
                video_metadata = None
                for v in all_videos:
                    # Try exact match first
                    if v.path == video_path:
                        video_metadata = v
                        break
                    # Try with absolute path
                    abs_video_path = os.path.abspath(video_path)
                    abs_v_path = os.path.abspath(v.path)
                    if abs_v_path == abs_video_path:
                        video_metadata = v
                        break
                
                if not video_metadata:
                    logger.error(f"Video metadata not found for path: {video_path}")
                    logger.debug(f"Available video paths ({len(all_videos)} total):")
                    for v in all_videos[:5]:  # Log first 5 for debugging
                        logger.debug(f"  - {v.path}")
                    return jsonify({
                        "error": "Video not found",
                        "details": f"Could not find metadata for video path: {video_path}",
                        "hint": "Make sure the video file exists and has been processed"
                    }), 404
                
                # Log video metadata for debugging
                logger.info(f"Generating YouTube metadata for video: {video_path}")
                logger.info(f"  Video metadata: type={video_metadata.video_type}, expression='{video_metadata.expression}', episode='{video_metadata.episode}', language={video_metadata.language}")
                
                # Generate metadata (will use fallbacks if expression/episode are missing)
                metadata_generator = YouTubeMetadataGenerator()
                youtube_metadata = metadata_generator.generate_metadata(video_metadata)
                
                # Validate generated metadata (this is the critical check)
                if not youtube_metadata.title or youtube_metadata.title.strip() == "":
                    expression = getattr(video_metadata, 'expression', '')
                    show_name = getattr(video_metadata, 'show_name', '')
                    
                    if expression:
                        fallback_title = f"{expression} | {show_name}" if show_name else expression
                    else:
                        fallback_title = video_metadata.episode or os.path.splitext(os.path.basename(video_path))[0]

                    logger.warning(f"Generated metadata has empty title. Using smart fallback: {fallback_title}")
                    youtube_metadata.title = fallback_title
                
                logger.info(f"✅ Generated metadata successfully: title='{youtube_metadata.title[:60]}...', description length={len(youtube_metadata.description)}, tags={len(youtube_metadata.tags)}")
                
                # Upload immediately with publishAt parameter
                from langflix.youtube.uploader import YouTubeUploader
                uploader = YouTubeUploader()
                
                logger.info(f"Starting scheduled upload for {video_path} with publishAt: {publish_time}")
                result = uploader.upload_video(
                    video_path=video_path,
                    metadata=youtube_metadata,
                    publish_at=publish_time  # Pass publishAt to schedule publishing on YouTube
                )
                
                if result.success:
                    # Store schedule in DB for tracking (after successful upload)
                    # Map video_type for schedule_manager (context->short, long-form->final)
                    schedule_video_type = 'short' if video_type == 'context' else ('final' if video_type == 'long-form' else video_type)
                    success, message, scheduled_time = self.schedule_manager.schedule_video(
                        video_path, schedule_video_type, publish_time
                    )
                    
                    # Use the actual scheduled_time from schedule_video() response
                    # This is the time that was actually stored in the database
                    actual_scheduled_time = scheduled_time if scheduled_time else publish_time
                    
                    if not success:
                        logger.warning(f"Failed to store schedule in DB: {message}, but upload was successful")
                    
                    # Update schedule with video_id
                    if success:
                        self.schedule_manager.update_schedule_with_video_id(
                            video_path, result.video_id, 'completed'  # Uploaded, scheduled for publishing
                        )
                        # Use mapped schedule_video_type for quota update
                        self.schedule_manager.update_quota_usage(schedule_video_type)
                    
                    # Also update video status
                    self._update_video_upload_status(
                        video_path,
                        result.video_id,
                        result.video_url,
                        'completed'  # Use 'completed' status (matches DB constraint)
                    )
                    
                    # Clear video cache to force refresh on next scan
                    try:
                        from langflix.core.redis_client import get_redis_job_manager
                        redis_manager = get_redis_job_manager()
                        redis_manager.invalidate_video_cache()
                        logger.info("✅ Cleared video cache after upload")
                    except Exception as e:
                        logger.warning(f"Failed to clear video cache: {e}")
                    
                    # Log the actual scheduled time for debugging
                    logger.info(f"✅ Upload successful - Scheduled time: {actual_scheduled_time} (requested: {publish_time})")
                    
                    return jsonify({
                        "success": True,
                        "message": f"Video uploaded and scheduled for publishing at {actual_scheduled_time}",
                        "video_id": result.video_id,
                        "video_url": result.video_url,
                        "scheduled_publish_time": actual_scheduled_time.isoformat() if hasattr(actual_scheduled_time, 'isoformat') else str(actual_scheduled_time),
                        "video_path": video_path,
                        "video_type": video_type
                    })
                else:
                    # Upload failed - don't store schedule
                    error_msg = result.error_message or 'Upload failed'
                    logger.error(f"Scheduled upload failed: {error_msg}")
                    return jsonify({
                        "success": False,
                        "error": error_msg
                    }), 500
                    
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
        
        @self.app.route('/api/videos/batch/delete', methods=['POST'])
        def batch_delete_videos():
            """Delete multiple video files"""
            try:
                data = request.get_json()
                video_paths = data.get('video_paths', [])
                
                if not video_paths:
                    return jsonify({"error": "No video paths provided"}), 400
                
                deleted = []
                failed = []
                
                for video_path in video_paths:
                    try:
                        # Delete file
                        if os.path.exists(video_path):
                            os.remove(video_path)
                            deleted.append(video_path)
                            logger.info(f"Deleted video file: {video_path}")
                        else:
                            failed.append({"path": video_path, "error": "File not found"})
                    except Exception as e:
                        logger.error(f"Failed to delete {video_path}: {e}")
                        failed.append({"path": video_path, "error": str(e)})
                
                return jsonify({
                    "success": len(failed) == 0,
                    "deleted": deleted,
                    "failed": failed,
                    "deleted_count": len(deleted),
                    "failed_count": len(failed)
                })
            except Exception as e:
                logger.error(f"Error in batch delete: {e}", exc_info=True)
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/upload/batch/immediate', methods=['POST'])
        def batch_upload_immediate():
            """Upload multiple videos immediately"""
            try:
                data = request.get_json()
                videos = data.get('videos', [])
                
                if not videos:
                    return jsonify({"error": "No videos provided"}), 400
                
                if len(videos) > 50:
                    return jsonify({"error": "Maximum 50 videos allowed per batch"}), 400
                
                results = []
                for video in videos:
                    video_path = video.get('video_path')
                    video_type = video.get('video_type')
                    
                    if not video_path or not video_type:
                        results.append({
                            "video_path": video_path,
                            "success": False,
                            "error": "video_path and video_type are required"
                        })
                        continue
                    
                    try:
                        # Reuse existing immediate upload logic
                        from langflix.youtube.uploader import YouTubeUploader
                        uploader = YouTubeUploader()
                        
                        # Generate metadata
                        from langflix.youtube.video_manager import VideoFileManager
                        from langflix.youtube.metadata_generator import YouTubeMetadataGenerator
                        from pathlib import Path
                        
                        video_manager = VideoFileManager()
                        metadata_generator = YouTubeMetadataGenerator()
                        
                        # Convert string path to Path object
                        video_path_obj = Path(video_path)
                        if not video_path_obj.exists():
                            results.append({
                                "video_path": video_path,
                                "success": False,
                                "error": f"Video file not found: {video_path}"
                            })
                            continue
                        
                        video_metadata = video_manager._extract_video_metadata(video_path_obj)
                        if not video_metadata:
                            logger.error(f"Failed to extract metadata from {video_path}")
                            results.append({
                                "video_path": video_path,
                                "success": False,
                                "error": "Failed to extract video metadata"
                            })
                            continue
                        
                        youtube_metadata = metadata_generator.generate_metadata(video_metadata)
                        
                        # Fallback if title is empty
                        if not youtube_metadata.title or not youtube_metadata.title.strip():
                            expression = getattr(video_metadata, 'expression', '')
                            show_name = getattr(video_metadata, 'show_name', '')
                            
                            if expression:
                                fallback_title = f"{expression} | {show_name}" if show_name else expression
                            else:
                                fallback_title = video_path_obj.stem
                                
                            logger.warning(f"Generated metadata has empty title. Using smart fallback: {fallback_title}")
                            youtube_metadata.title = fallback_title
                        
                        # Upload immediately
                        logger.info(f"Starting immediate batch upload: {video_path}")
                        result = uploader.upload_video(
                            video_path=video_path,
                            metadata=youtube_metadata
                        )
                        
                        if result.success:
                            # Update video status
                            self._update_video_upload_status(
                                video_path,
                                result.video_id,
                                result.video_url,
                                'completed'
                            )
                            
                            # Clear video cache
                            try:
                                from langflix.core.redis_client import get_redis_job_manager
                                redis_manager = get_redis_job_manager()
                                redis_manager.invalidate_video_cache()
                            except Exception as e:
                                logger.warning(f"Failed to clear video cache: {e}")
                            
                            results.append({
                                "video_path": video_path,
                                "success": True,
                                "video_id": result.video_id,
                                "video_url": result.video_url
                            })
                        else:
                            results.append({
                                "video_path": video_path,
                                "success": False,
                                "error": result.error_message or "Upload failed"
                            })
                    except Exception as e:
                        logger.error(f"Error uploading {video_path}: {e}", exc_info=True)
                        results.append({
                            "video_path": video_path,
                            "success": False,
                            "error": str(e)
                        })
                
                return jsonify({
                    "success": all(r.get('success') for r in results),
                    "results": results,
                    "success_count": sum(1 for r in results if r.get('success')),
                    "failed_count": sum(1 for r in results if not r.get('success'))
                })
            except Exception as e:
                logger.error(f"Error in batch upload immediate: {e}", exc_info=True)
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/upload/batch/schedule', methods=['POST'])
        def batch_upload_schedule():
            """Schedule multiple videos for upload (sequential scheduling)"""
            try:
                data = request.get_json()
                videos = data.get('videos', [])
                
                if not videos:
                    return jsonify({"error": "No videos provided"}), 400
                
                if len(videos) > 50:
                    return jsonify({"error": "Maximum 50 videos allowed per batch"}), 400
                
                # Initialize lightweight YouTube-based scheduler (no DB dependency).
                yt_scheduler = None
                try:
                    from langflix.youtube.last_schedule import YouTubeLastScheduleService, LastScheduleConfig
                    yt_scheduler = YouTubeLastScheduleService(LastScheduleConfig())
                except Exception as e:
                    logger.warning(f"Failed to initialize YouTubeLastScheduleService: {e}")
                    yt_scheduler = None
 
                results = []
                # Schedule videos sequentially, calculating next available slot for each
                for video in videos:
                    video_path = video.get('video_path')
                    video_type = video.get('video_type')
                    
                    if not video_path or not video_type:
                        results.append({
                            "video_path": video_path,
                            "success": False,
                            "error": "video_path and video_type are required"
                        })
                        continue
                    
                    try:
                        # Map video_type for schedule_manager
                        schedule_video_type = 'short' if video_type == 'context' else ('final' if video_type == 'long-form' else video_type)
                        
                        # Determine next publish time.
                        # Prefer YouTube-based lightweight scheduler; fall back to DB schedule manager.
                        publish_time = None
                        if self.yt_scheduler:
                            try:
                                publish_time = self.yt_scheduler.get_next_available_slot()
                            except Exception as e:
                                logger.warning(f"YouTube scheduler failed, falling back to DB: {e}")
                                publish_time = None
                        
                        if not publish_time:
                            if not self.schedule_manager:
                                raise RuntimeError("No scheduler available (YouTube or DB)")
                            # Fallback to DB-driven slot finding
                            publish_time = self.schedule_manager.get_next_available_slot(schedule_video_type)
                        logger.info(f"Next available slot for {video_path} ({schedule_video_type}): {publish_time}")
                        
                        # Generate metadata
                        from langflix.youtube.video_manager import VideoFileManager
                        from langflix.youtube.metadata_generator import YouTubeMetadataGenerator
                        from pathlib import Path
                        
                        video_manager = VideoFileManager()
                        metadata_generator = YouTubeMetadataGenerator()
                        
                        # Convert string path to Path object
                        video_path_obj = Path(video_path)
                        if not video_path_obj.exists():
                            logger.error(f"Video file not found: {video_path}")
                            results.append({
                                "video_path": video_path,
                                "success": False,
                                "error": f"Video file not found: {video_path}"
                            })
                            continue
                        
                        try:
                            video_metadata = video_manager._extract_video_metadata(video_path_obj)
                            if not video_metadata:
                                logger.error(f"Failed to extract metadata from {video_path}")
                                results.append({
                                    "video_path": video_path,
                                    "success": False,
                                    "error": "Failed to extract video metadata"
                                })
                                continue
                        except Exception as e:
                            logger.error(f"Error extracting metadata from {video_path}: {e}", exc_info=True)
                            results.append({
                                "video_path": video_path,
                                "success": False,
                                "error": f"Error extracting metadata: {str(e)}"
                            })
                            continue
                        
                        try:
                            youtube_metadata = metadata_generator.generate_metadata(video_metadata)
                            
                            # Fallback if title is empty
                            if not youtube_metadata.title or not youtube_metadata.title.strip():
                                expression = getattr(video_metadata, 'expression', '')
                                show_name = getattr(video_metadata, 'show_name', '')
                                
                                if expression:
                                    fallback_title = f"{expression} | {show_name}" if show_name else expression
                                else:
                                    fallback_title = video_path_obj.stem
                                    
                                logger.warning(f"Generated metadata has empty title. Using smart fallback: {fallback_title}")
                                youtube_metadata.title = fallback_title
                                
                        except Exception as e:
                            logger.error(f"Error generating metadata for {video_path}: {e}", exc_info=True)
                            results.append({
                                "video_path": video_path,
                                "success": False,
                                "error": f"Error generating metadata: {str(e)}"
                            })
                            continue
                        
                        # Upload with publishAt
                        from langflix.youtube.uploader import YouTubeUploader
                        uploader = YouTubeUploader()
                        
                        logger.info(f"Starting scheduled batch upload: {video_path} for {publish_time}")
                        result = uploader.upload_video(
                            video_path=video_path,
                            metadata=youtube_metadata,
                            publish_at=publish_time
                        )
                        
                        if result.success:
                            # Update lightweight scheduler state for sequential batches
                            if self.yt_scheduler:
                                self.yt_scheduler.record_local(publish_time)
                            
                            # Store schedule in DB for tracking when available
                            actual_scheduled_time = publish_time
                            if self.schedule_manager and settings.get_database_enabled():
                                try:
                                    success, message, scheduled_time = self.schedule_manager.schedule_video(
                                        video_path, schedule_video_type, publish_time
                                    )
                                    if success and scheduled_time:
                                        actual_scheduled_time = scheduled_time
                                        self.schedule_manager.update_schedule_with_video_id(
                                            video_path, result.video_id, 'completed'
                                        )
                                        self.schedule_manager.update_quota_usage(schedule_video_type)
                                    else:
                                        logger.warning(f"DB schedule failed: {message}")
                                except Exception as e:
                                    logger.warning(f"DB schedule record failed (continuing): {e}")
                            else:
                                # Stateless mode: assume success for scheduling
                                logger.info(f"Stateless mode: Scheduled {video_path} for {publish_time}")
                                # In stateless mode, we don't have a DB to update, but we still need to track the actual_scheduled_time
                                # The original code had `publish_timer.update_schedule_with_video_id` which is incorrect.
                                # We just set actual_scheduled_time and proceed.
                                actual_scheduled_time = publish_time
                            
                            # Update video status
                            self._update_video_upload_status(
                                video_path,
                                result.video_id,
                                result.video_url,
                                'completed'
                            )
                            
                            # Clear video cache
                            try:
                                from langflix.core.redis_client import get_redis_job_manager
                                redis_manager = get_redis_job_manager()
                                redis_manager.invalidate_video_cache()
                            except Exception as e:
                                logger.warning(f"Failed to clear video cache: {e}")
                            
                            results.append({
                                "video_path": video_path,
                                "scheduled_time": actual_scheduled_time.isoformat() if hasattr(actual_scheduled_time, 'isoformat') else str(actual_scheduled_time),
                                "success": True,
                                "video_id": result.video_id,
                                "video_url": result.video_url
                            })
                        else:
                            results.append({
                                "video_path": video_path,
                                "success": False,
                                "error": result.error_message or "Upload failed"
                            })
                    except Exception as e:
                        logger.error(f"Error scheduling {video_path}: {e}", exc_info=True)
                        results.append({
                            "video_path": video_path,
                            "success": False,
                            "error": str(e)
                        })
                
                return jsonify({
                    "success": all(r.get('success') for r in results),
                    "results": results,
                    "success_count": sum(1 for r in results if r.get('success')),
                    "failed_count": sum(1 for r in results if not r.get('success'))
                })
            except ValueError as e:
                # Database connection errors
                error_msg = str(e)
                if "database" in error_msg.lower() or "postgresql" in error_msg.lower():
                    logger.error(f"Database connection error in batch schedule: {e}")
                    return jsonify({
                        "error": "Database connection failed",
                        "details": error_msg,
                        "hint": "Please ensure PostgreSQL is running"
                    }), 503
                return jsonify({"error": error_msg}), 400
            except Exception as e:
                logger.error(f"Error in batch upload schedule: {e}", exc_info=True)
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/quota/status')
        def get_quota_status():
            """Get YouTube API quota usage status"""
            try:
                if not self.schedule_manager:
                    return jsonify({"error": "Schedule manager not available"}), 503
                
                # Check if DB is enabled for quota tracking
                if not settings.get_database_enabled():
                    # Return default/empty quota status if DB is disabled
                    from datetime import date
                    today = date.today()
                    return jsonify({
                        "date": today.isoformat(),
                        "final_videos": {"used": 0, "remaining": 2, "limit": 2},
                        "short_videos": {"used": 0, "remaining": 5, "limit": 5},
                        "api_quota": {"used": 0, "remaining": 10000, "percentage": 0, "limit": 10000},
                        "warnings": ["Database disabled - quota tracking unavailable"]
                    })
                
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
                
                if not settings.get_database_enabled():
                    return jsonify({"error": "Database disabled"}), 404

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
                
            if not settings.get_database_enabled():
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
            # Check if it's a database connection error
            error_msg = str(e)
            if "connection" in error_msg.lower() and ("refused" in error_msg.lower() or "5432" in error_msg):
                logger.warning(f"Database connection error updating video status (PostgreSQL not running): {error_msg.split('(')[0] if '(' in error_msg else error_msg}")
            else:
                logger.error(f"Error updating video status: {e}", exc_info=True)
            # Don't raise - status update failure shouldn't block upload process
    
    def _save_youtube_account(self, channel_info: Dict[str, Any]):
        """Save YouTube account info to database"""
        try:
            if not settings.get_database_enabled():
                return

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
            # Check if it's a database connection error
            error_msg = str(e)
            if "connection" in error_msg.lower() and ("refused" in error_msg.lower() or "5432" in error_msg):
                logger.warning(f"Database connection error saving YouTube account (PostgreSQL not running): {error_msg.split('(')[0] if '(' in error_msg else error_msg}")
            else:
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
                
                # Filter out non-video files (e.g., .json metadata files)
                # Only return files with video extensions
                video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.m4v', '.webm']
                filtered_files = [
                    f for f in media_files 
                    if any(f.get('video_path', '').lower().endswith(ext) for ext in video_extensions)
                ]
                
                logger.debug(f"Filtered {len(media_files)} files to {len(filtered_files)} video files")
                return jsonify(filtered_files)
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
                test_llm = data.get('test_llm', False)  # Dev: Use cached LLM response
                
                # Call FastAPI backend with file uploads
                import requests
                # Use configured API base URL (from environment variable)
                fastapi_url = self._build_api_url("/api/jobs")
                
                # Prepare files for upload
                files = {}
                # Get duration parameter from request - short_form_max_duration is used for both expression clip target and max short-form duration
                short_form_max_duration = data.get('short_form_max_duration', 180.0)

                form_data = {
                    "language_code": data['language_code'],
                    "source_language": data.get('source_language', data['language_code']),  # Explicit source language
                    "show_name": data.get('show_name', ''),  # User-provided show name from UI
                    "episode_name": os.path.splitext(os.path.basename(data['video_path']))[0],
                    "max_expressions": 50,
                    "language_level": data['language_level'],
                    "test_mode": str(test_mode).lower(),
                    "test_llm": str(test_llm).lower(),  # Forward to FastAPI backend
                    "no_shorts": False,
                    "targetDuration": short_form_max_duration,  # 🎯 Use short_form_max_duration for expression clip target duration
                    "short_form_max_duration": short_form_max_duration,
                    "create_long_form": data.get('create_long_form', True),
                    "create_short_form": data.get('create_short_form', True)
                }
                
                logger.info(f"Sending job request to FastAPI with test_mode={form_data['test_mode']}")
                
                # Add target_languages if provided (for multi-language support)
                if 'target_languages' in data and data['target_languages']:
                    # Explicitly join to string to ensure consistent handling by requests/FastAPI
                    if isinstance(data['target_languages'], list):
                        form_data['target_languages'] = ",".join(data['target_languages'])
                    else:
                        form_data['target_languages'] = data['target_languages']
                
                # Add auto_upload_config if provided
                if 'auto_upload_config' in data and data['auto_upload_config']:
                    import json
                    form_data['auto_upload_config'] = json.dumps(data['auto_upload_config'])
                
                # Add video file if it exists
                video_file_handle = None
                subtitle_file_handle = None

                try:
                    if os.path.exists(data['video_path']):
                        video_file_handle = open(data['video_path'], 'rb')
                        files['video_file'] = (os.path.basename(data['video_path']), video_file_handle, 'video/mp4')

                    # Add subtitle file if it exists
                    subtitle_path = data.get('subtitle_path')

                    # FALLBACK: If subtitle_path not provided, try to auto-discover it
                    if not subtitle_path or not os.path.exists(subtitle_path):
                        from pathlib import Path
                        from langflix import settings

                        logger.info("Subtitle path not provided, attempting auto-discovery...")

                        # Get source language from form data (user's selection in UI)
                        # Fall back to config if not provided
                        source_lang_code = data.get('source_language') or form_data.get('source_language', 'en')

                        # Convert language code to name (e.g., 'en' -> 'English', 'ko' -> 'Korean')
                        from langflix.utils.language_utils import language_code_to_name
                        source_lang = language_code_to_name(source_lang_code)

                        logger.info(f"Auto-discovery using source language: {source_lang} (from code: {source_lang_code})")

                        # Strategy 1: Try video file directory (for files in assets/media/)
                        video_path = Path(data['video_path'])
                        video_basename = video_path.stem
                        video_dir = video_path.parent

                        search_locations = [
                            (video_dir / "Subs" / video_basename, "NEW structure (video dir)"),
                            (video_dir / video_basename, "LEGACY structure (video dir)"),
                        ]

                        # Strategy 2: Try assets/media/{show_name}/Subs/{episode_name}/
                        # This works when video is uploaded to temp location
                        if 'show_name' in data and form_data.get('episode_name'):
                            media_root = Path("assets/media")
                            show_path = media_root / data['show_name']
                            episode_name = form_data['episode_name']

                            search_locations.extend([
                                (show_path / "Subs" / episode_name, "NEW structure (show path)"),
                                (show_path / episode_name, "LEGACY structure (show path)"),
                            ])

                        # Search in all locations
                        for subs_folder, location_desc in search_locations:
                            if not subs_folder.exists():
                                logger.debug(f"Subtitle folder not found: {subs_folder} ({location_desc})")
                                continue

                            logger.info(f"Searching for subtitles in: {subs_folder} ({location_desc})")

                            # Try exact match: {Language}.srt
                            for ext in ['.srt', '.vtt', '.ass', '.smi']:
                                candidate = subs_folder / f"{source_lang}{ext}"
                                if candidate.exists():
                                    subtitle_path = str(candidate)
                                    logger.info(f"✅ Auto-discovered subtitle: {subtitle_path} (exact match)")
                                    break

                            # Try pattern match: *{Language}*.srt
                            if not subtitle_path:
                                for ext in ['.srt', '.vtt', '.ass', '.smi']:
                                    matches = list(subs_folder.glob(f"*{source_lang}*{ext}"))
                                    if matches:
                                        subtitle_path = str(matches[0])
                                        logger.info(f"✅ Auto-discovered subtitle: {subtitle_path} (pattern match)")
                                        break

                            # Priority 3: Fallback - removed to prevent picking wrong language
                            # We should rely on exact language matches or user upload
                            pass

                            if subtitle_path:
                                break

                        if not subtitle_path:
                            logger.warning(f"Could not auto-discover subtitle for: {video_basename} (source lang: {source_lang})")

                    # Open subtitle file if found
                    if subtitle_path and os.path.exists(subtitle_path):
                        subtitle_file_handle = open(subtitle_path, 'rb')
                        files['subtitle_file'] = (os.path.basename(subtitle_path), subtitle_file_handle, 'text/plain')
                        logger.info(f"Uploading subtitle file: {subtitle_path}")
                    
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
                        "progress": float(job.get("progress", 0)),
                        "current_step": job.get("current_step", ""),
                        "error_message": job.get("error", None)
                    })
                else:
                    # Try to get from FastAPI backend as fallback
                    import requests
                    fastapi_url = self._build_api_url(f"/api/jobs/{job_id}")
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
                fastapi_url = self._build_api_url("/api/batch")
                
                # Ensure auto_upload_config is passed if present
                if 'auto_upload_config' in data:
                    # It's already in data, which is passed as json
                    pass
                
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
                fastapi_url = self._build_api_url(f"/api/batch/{batch_id}")
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
                        "progress": float(job_data.get("progress", 0)),
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
    
    def _build_api_url(self, path: str) -> str:
        """Construct API URL using configured base."""
        if not path.startswith('/'):
            path = f'/{path}'
        return f"{self.api_base_url}{path}"
    
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
    # templates_dir = Path("templates")
    # templates_dir.mkdir(exist_ok=True)
    
    # Run the UI
    output_dir = os.getenv("LANGFLIX_OUTPUT_DIR", "output")
    media_dir = os.getenv("LANGFLIX_MEDIA_DIR", "assets/media")
    ui_port = int(os.getenv("LANGFLIX_UI_PORT", "5000"))
    debug_enabled = os.getenv("LANGFLIX_UI_DEBUG", "false").lower() in ("1", "true", "yes")
    
    ui = VideoManagementUI(output_dir=output_dir, media_dir=media_dir, port=ui_port)
    ui.run(debug=debug_enabled)
