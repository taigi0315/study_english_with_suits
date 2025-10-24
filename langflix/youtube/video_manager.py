"""
Video File Manager for YouTube Content Management
Scans and manages generated video files for YouTube upload
"""
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
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
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.webm'}
        
    def scan_all_videos(self) -> List[VideoMetadata]:
        """Scan all generated video files and extract metadata"""
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
                ready_for_upload=self._is_ready_for_upload(video_type, duration)
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
            # Find episode info (S01E01, S01E02, etc.)
            for part in path_parts:
                if "S01E" in part:
                    episode = part
                    break
            
            # Find language info
            if "ko" in path_parts:
                language = "ko"
            elif "en" in path_parts:
                language = "en"
            
            # Determine video type from filename and directory
            filename = video_path.stem.lower()
            parent_dir = video_path.parent.name.lower()
            
            if "educational" in filename:
                video_type = "educational"
            elif "short" in filename:
                video_type = "short"
            elif "final" in filename:
                video_type = "final"
            elif "slide" in filename:
                video_type = "slide"
            elif "context" in filename:
                video_type = "context"
            
            # Extract expression from filename
            if video_type in ["educational", "short", "slide", "context", "final"]:
                # Remove prefixes and get expression
                expression = filename
                for prefix in ["educational_", "short_", "slide_", "context_", "final_"]:
                    if expression.startswith(prefix):
                        expression = expression[len(prefix):]
                        break
                expression = expression.replace("_", " ").title()
            
        except Exception as e:
            logger.warning(f"Error parsing path {video_path}: {e}")
        
        return video_type, episode, expression, language
    
    def _is_ready_for_upload(self, video_type: str, duration: float) -> bool:
        """Determine if video is ready for YouTube upload"""
        # Short videos should be under 60 seconds for YouTube Shorts
        if video_type == "short":
            return duration <= 60
        
        # Educational videos should be reasonable length
        if video_type == "educational":
            return 10 <= duration <= 300  # 10 seconds to 5 minutes
        
        # Final videos can be longer
        if video_type == "final":
            return duration <= 600  # Up to 10 minutes
        
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
        Filter videos that are uploadable (final or short only)
        """
        return [v for v in videos 
                if v.video_type in ['final', 'short'] 
                and v.ready_for_upload 
                and not v.uploaded_to_youtube]
    
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
