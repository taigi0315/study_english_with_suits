"""
Video File Manager for YouTube Content Management
Scans and manages generated video files for YouTube upload
"""
import os
import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import subprocess

logger = logging.getLogger(__name__)

@dataclass
class VideoMetadata:
    """Video file metadata"""
    path: str
    filename: str
    size_mb: float
    duration_seconds: float
    resolution: str
    format: str
    created_at: datetime
    episode: str
    expression: str
    video_type: str  # 'educational', 'short', 'final', 'slide', 'context'
    language: str
    ready_for_upload: bool = False
    uploaded_to_youtube: bool = False
    youtube_video_id: Optional[str] = None

class VideoFileManager:
    """Manages generated video files for YouTube upload"""
    
    def __init__(self, output_dir: str = "output", use_cache: bool = True):
        self.output_dir = Path(output_dir)
        self.video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.webm'}
        self.use_cache = use_cache
        
    def scan_all_videos(self, force_refresh: bool = False) -> List[VideoMetadata]:
        """
        Scan all generated video files and extract metadata.
        
        Args:
            force_refresh: If True, bypass cache and force filesystem scan
            
        Returns:
            List of VideoMetadata objects
        """
        # Try to get from cache first (unless force_refresh is True)
        if self.use_cache and not force_refresh:
            try:
                from langflix.core.redis_client import get_redis_job_manager
                redis_manager = get_redis_job_manager()
                cached_videos = redis_manager.get_video_cache()
                
                if cached_videos:
                    logger.info(f"✅ Loaded {len(cached_videos)} videos from cache")
                    # Convert cached dictionaries back to VideoMetadata objects
                    return [self._dict_to_metadata(v) for v in cached_videos]
            except Exception as e:
                logger.warning(f"Cache retrieval failed, falling back to filesystem scan: {e}")
        
        # Cache miss or force refresh - scan filesystem
        logger.info(f"Scanning for video files in: {self.output_dir}")
        
        videos = []
        for video_file in self._find_video_files():
            try:
                metadata = self._extract_video_metadata(video_file)
                if metadata:
                    videos.append(metadata)
            except Exception as e:
                logger.error(f"Error processing {video_file}: {e}")
                continue
                
        logger.info(f"Found {len(videos)} video files")
        
        # Cache the results
        if self.use_cache and videos:
            try:
                from langflix.core.redis_client import get_redis_job_manager
                redis_manager = get_redis_job_manager()
                video_dicts = [self._metadata_to_dict(v) for v in videos]
                redis_manager.set_video_cache(video_dicts, ttl=300)  # 5 minutes TTL
            except Exception as e:
                logger.warning(f"Failed to cache video results: {e}")
        
        return videos
    
    def _find_video_files(self) -> List[Path]:
        """Find all video files in the output directory"""
        video_files = []
        
        for root, dirs, files in os.walk(self.output_dir):
            for file in files:
                if Path(file).suffix.lower() in self.video_extensions:
                    video_files.append(Path(root) / file)
                    
        return video_files
    
    def _extract_video_metadata(self, video_path: Path) -> Optional[VideoMetadata]:
        """Extract metadata from a video file using ffprobe"""
        try:
            # Get file info
            stat = video_path.stat()
            size_mb = stat.st_size / (1024 * 1024)
            created_at = datetime.fromtimestamp(stat.st_ctime)
            
            # Get video info using ffprobe
            ffprobe_cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', str(video_path)
            ]
            
            result = subprocess.run(ffprobe_cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            # Extract video stream info
            video_stream = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
            if not video_stream:
                logger.warning(f"No video stream found in {video_path}")
                return None
                
            # Get duration
            duration = float(data['format'].get('duration', 0))
            
            # Get resolution
            width = video_stream.get('width', 0)
            height = video_stream.get('height', 0)
            resolution = f"{width}x{height}" if width and height else "unknown"
            
            # Determine video type and extract episode/expression info
            video_type, episode, expression, language = self._parse_video_path(video_path)
            
            # Check database for upload status
            uploaded_to_youtube = False
            youtube_video_id = None
            try:
                from langflix.db.session import db_manager
                from langflix.db.models import YouTubeSchedule
                
                with db_manager.session() as db:
                    schedule = db.query(YouTubeSchedule).filter_by(
                        video_path=str(video_path)
                    ).first()
                    
                    if schedule and schedule.youtube_video_id:
                        uploaded_to_youtube = True
                        youtube_video_id = schedule.youtube_video_id
                        logger.debug(f"Found upload status for {video_path}: uploaded={uploaded_to_youtube}, video_id={youtube_video_id}")
            except Exception as e:
                # Database might not be available - log but don't fail
                logger.debug(f"Could not check upload status from database: {e}")
            
            return VideoMetadata(
                path=str(video_path),
                filename=video_path.name,
                size_mb=round(size_mb, 2),
                duration_seconds=round(duration, 2),
                resolution=resolution,
                format=video_stream.get('codec_name', 'unknown'),
                created_at=created_at,
                episode=episode,
                expression=expression,
                video_type=video_type,
                language=language,
                ready_for_upload=self._is_ready_for_upload(video_type, duration),
                uploaded_to_youtube=uploaded_to_youtube,
                youtube_video_id=youtube_video_id
            )
            
        except subprocess.CalledProcessError as e:
            logger.error(f"ffprobe failed for {video_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error extracting metadata from {video_path}: {e}")
            return None
    
    def _parse_video_path(self, video_path: Path) -> tuple[str, str, str, str]:
        """Parse video path to extract type, episode, expression, and language"""
        path_parts = video_path.parts
        
        # Default values
        video_type = "unknown"
        episode = "unknown"
        expression = "unknown"
        language = "unknown"
        
        try:
            # Find episode info (S01E01, S02E03, etc.) from any path segment
            for part in path_parts:
                match = re.search(r'(S\d+E\d+)', part, flags=re.IGNORECASE)
                if match:
                    episode = match.group(1).upper()
                    break
            
            # Find language info - prioritize translations directory structure
            # Look for /translations/{language}/ pattern first
            for i, part in enumerate(path_parts):
                if part == "translations" and i + 1 < len(path_parts):
                    lang_part = path_parts[i + 1].lower()
                    if lang_part in ["ko", "korean"]:
                        language = "ko"
                        break
                    elif lang_part in ["ja", "japanese"]:
                        language = "ja"
                        break
                    elif lang_part in ["zh", "chinese"]:
                        language = "zh"
                        break
                    elif lang_part in ["es", "spanish"]:
                        language = "es"
                        break
                    elif lang_part in ["fr", "french"]:
                        language = "fr"
                        break
                    elif lang_part in ["en", "english"]:
                        language = "en"
                        break
            
            # Fallback: check all path parts for language indicators if not found in translations
            if language == "unknown":
                for part in path_parts:
                    part_lower = part.lower()
                    if "ko" in part_lower or "korean" in part_lower:
                        language = "ko"
                        break
                    elif "ja" in part_lower or "japanese" in part_lower:
                        language = "ja"
                        break
                    elif "zh" in part_lower or "chinese" in part_lower:
                        language = "zh"
                        break
                    elif "es" in part_lower or "spanish" in part_lower:
                        language = "es"
                        break
                    elif "fr" in part_lower or "french" in part_lower:
                        language = "fr"
                        break
                    elif "en" in part_lower or "english" in part_lower:
                        language = "en"
                        break
            
            # Determine video type from filename and directory
            filename = video_path.stem.lower()
            parent_dir = video_path.parent.name.lower()
            
            # New naming convention detection
            if filename.startswith("long-form_"):
                video_type = "long-form"  # Updated to use long-form as video type
                # Extract episode info from long-form filename
                parts = filename.split("_")
                if len(parts) >= 3:
                    expression = f"{parts[1]} - Long Form"  # e.g., "S01E01 - Long Form"
                else:
                    expression = "Long Form Video"
            elif filename.startswith("short-form_"):
                video_type = "short"  # Use "short" to match template
                # Extract episode from short-form filename
                # Format: short-form_Suits.S01E01.720p.HDTV.x264_008
                parts = filename.split("_")
                if len(parts) >= 2:
                    # Extract episode from parts[1] (e.g., "Suits.S01E01.720p.HDTV.x264")
                    episode_part = parts[1]
                    if "S01E" in episode_part:
                        # Extract S01E## pattern
                        episode_match = re.search(r'[Ss](\d+)[Ee](\d+)', episode_part)
                        if episode_match:
                            episode = f"S{episode_match.group(1)}E{episode_match.group(2)}"
                        else:
                            episode = episode_part
                    else:
                        episode = episode_part
                    # For batch videos, expression is not in filename - use empty string
                    # This will trigger fallback in metadata generator to extract from filename or use default
                    expression = ""  # Empty to trigger fallback extraction
                else:
                    expression = ""  # Empty to trigger fallback
            # Legacy naming convention (for backward compatibility)
            elif "educational" in filename:
                video_type = "educational"
                expression = filename.replace("educational_", "").replace("_", " ").title()
            elif "short" in filename and not filename.startswith("short-form_"):
                video_type = "short"
                expression = filename.replace("short_", "").replace("_", " ").title()
            elif "final" in filename and not filename.startswith("long-form_"):
                video_type = "final"
                expression = filename.replace("final_", "").replace("_", " ").title()
            elif "slide" in filename:
                video_type = "slide"
                expression = filename.replace("slide_", "").replace("_", " ").title()
            elif "context" in filename:
                video_type = "context"
                expression = filename.replace("context_", "").replace("_", " ").title()
            else:
                # Default handling
                expression = filename.replace("_", " ").title()
            
        except Exception as e:
            logger.warning(f"Error parsing path {video_path}: {e}")
        
        return video_type, episode, expression, language
    
    def _is_ready_for_upload(self, video_type: str, duration: float) -> bool:
        """Determine if video is ready for YouTube upload"""
        # Short-form videos should be under 1 minute (YouTube Shorts requirement)
        if video_type in ["short", "short-form"]:
            return 10 <= duration <= 60  # 10 seconds to 1 minute
        
        # Educational videos should be reasonable length
        if video_type == "educational":
            return 10 <= duration <= 300  # 10 seconds to 5 minutes
        
        # Long-form videos can be any length (YouTube allows up to 12 hours)
        # Minimum 10 seconds, no maximum limit
        if video_type in ["final", "long-form"]:
            return duration >= 10  # 10 seconds minimum, no maximum
        
        return False
    
    def get_videos_by_type(self, videos: List[VideoMetadata], video_type: str) -> List[VideoMetadata]:
        """Filter videos by type"""
        return [v for v in videos if v.video_type == video_type]
    
    def get_videos_by_episode(self, videos: List[VideoMetadata], episode: str) -> List[VideoMetadata]:
        """Filter videos by episode"""
        return [v for v in videos if v.episode == episode]
    
    def get_upload_ready_videos(self, videos: List[VideoMetadata]) -> List[VideoMetadata]:
        """Get videos that are ready for upload"""
        return [v for v in videos if v.ready_for_upload and not v.uploaded_to_youtube]
    
    def get_uploadable_videos(self, videos: List[VideoMetadata]) -> List[VideoMetadata]:
        """
        Filter videos that are uploadable:
        - long-form and short-form videos (new naming convention)
        - context_slide_combined videos (vertical format, ready for upload)
        - Legacy final/short videos (excluding intermediate files)
        """
        uploadable_videos = []
        for v in videos:
            # Only include videos with new naming convention or legacy final videos
            filename = Path(v.path).stem.lower()
            parent_dir = Path(v.path).parent.name.lower()
            
            # Include long-form and short-form videos (new naming convention)
            if (filename.startswith("long-form_") or filename.startswith("short-form_")):
                # Include regardless of uploaded status - we want to show all uploadable videos
                if v.ready_for_upload:
                    uploadable_videos.append(v)
            # Include context_slide_combined videos (vertical format, ready for YouTube Shorts)
            elif "context_slide_combined" in parent_dir and v.video_type in ["context", "short"]:
                # Context+slide combined videos are vertical format and ready for upload
                # Note: These files may have video_type="short" (from filename parsing) but are in context_slide_combined dir
                if v.ready_for_upload:
                    uploadable_videos.append(v)
            # Include legacy final/short videos but exclude intermediate files
            elif (v.video_type in ['final', 'short', 'long-form', 'short-form'] and 
                  not any(x in filename for x in ['educational', 'temp_']) and
                  'context_slide_combined' not in parent_dir):  # Individual context files excluded, only combined
                # Include regardless of uploaded status - we want to show all uploadable videos
                if v.ready_for_upload:
                    uploadable_videos.append(v)
        
        logger.debug(f"Found {len(uploadable_videos)} uploadable videos (including {sum(1 for v in uploadable_videos if v.uploaded_to_youtube)} already uploaded)")
        logger.debug(f"Uploadable video types: {set(v.video_type for v in uploadable_videos)}")
        return uploadable_videos
    
    def generate_thumbnail(self, video_path: str, output_path: str, timestamp: float = 5.0) -> bool:
        """Generate thumbnail from video using ffmpeg"""
        try:
            ffmpeg_cmd = [
                'ffmpeg', '-i', video_path,
                '-ss', str(timestamp),
                '-vframes', '1',
                '-q:v', '2',
                '-y',  # Overwrite output
                output_path
            ]
            
            subprocess.run(ffmpeg_cmd, capture_output=True, check=True)
            logger.info(f"Generated thumbnail: {output_path}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to generate thumbnail for {video_path}: {e}")
            return False
    
    def organize_videos_by_episode(self, videos: List[VideoMetadata]) -> Dict[str, List[VideoMetadata]]:
        """Organize videos by episode"""
        organized = {}
        for video in videos:
            if video.episode not in organized:
                organized[video.episode] = []
            organized[video.episode].append(video)
        return organized
    
    def get_statistics(self, videos: List[VideoMetadata]) -> Dict[str, Any]:
        """Get statistics about the video collection"""
        if not videos:
            return {}
        
        total_size = sum(v.size_mb for v in videos)
        total_duration = sum(v.duration_seconds for v in videos)
        
        type_counts = {}
        for video in videos:
            type_counts[video.video_type] = type_counts.get(video.video_type, 0) + 1
        
        upload_ready = len(self.get_upload_ready_videos(videos))
        
        return {
            "total_videos": len(videos),
            "total_size_mb": round(total_size, 2),
            "total_duration_minutes": round(total_duration / 60, 2),
            "upload_ready_count": upload_ready,
            "type_distribution": type_counts,
            "episodes": list(set(v.episode for v in videos))
        }
    
    def _metadata_to_dict(self, metadata: VideoMetadata) -> Dict[str, Any]:
        """Convert VideoMetadata to dictionary for caching."""
        data = asdict(metadata)
        # Convert datetime to ISO format string
        if isinstance(data.get('created_at'), datetime):
            data['created_at'] = data['created_at'].isoformat()
        return data
    
    def _dict_to_metadata(self, data: Dict[str, Any]) -> VideoMetadata:
        """Convert dictionary to VideoMetadata object."""
        # Convert ISO format string back to datetime
        if isinstance(data.get('created_at'), str):
            try:
                data['created_at'] = datetime.fromisoformat(data['created_at'])
            except:
                data['created_at'] = datetime.now(timezone.utc)
        
        return VideoMetadata(**data)
