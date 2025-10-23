"""
Media file validation and metadata extraction for LangFlix.

This module provides functionality to validate media files and extract
metadata using FFprobe for the expression-based learning feature.
"""

from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Any
import subprocess
import json
import logging
from pathlib import Path
from .exceptions import MediaValidationError

logger = logging.getLogger(__name__)


@dataclass
class MediaMetadata:
    """Media file metadata"""
    path: str
    duration: float
    video_codec: Optional[str]
    audio_codec: Optional[str]
    resolution: Tuple[int, int]
    fps: float
    bitrate: int
    has_video: bool
    has_audio: bool
    file_size: int
    format_name: str


class MediaValidator:
    """Validate and extract media metadata using FFprobe"""
    
    def __init__(self):
        """Initialize media validator"""
        self.supported_formats = {'.mp4', '.mkv', '.avi', '.mov', '.webm', '.wmv', '.flv'}
    
    def validate_media(self, media_path: str) -> MediaMetadata:
        """
        Validate and extract media metadata using FFprobe
        
        Args:
            media_path: Path to media file
            
        Returns:
            MediaMetadata: Extracted metadata
            
        Raises:
            MediaValidationError: If validation fails
        """
        if not Path(media_path).exists():
            raise MediaValidationError(
                f"Media file not found: {media_path}",
                file_path=media_path
            )
        
        # Check file extension
        file_ext = Path(media_path).suffix.lower()
        if file_ext not in self.supported_formats:
            raise MediaValidationError(
                f"Unsupported media format: {file_ext}. "
                f"Supported formats: {', '.join(self.supported_formats)}",
                file_path=media_path
            )
        
        # Get file size
        file_size = Path(media_path).stat().st_size
        
        # FFprobe command
        ffprobe_cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format', '-show_streams',
            media_path
        ]
        
        try:
            result = subprocess.run(
                ffprobe_cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=30  # 30 second timeout
            )
            data = json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            raise MediaValidationError(
                f"FFprobe failed: {e.stderr}",
                file_path=media_path
            )
        except json.JSONDecodeError as e:
            raise MediaValidationError(
                f"Invalid FFprobe output: {e}",
                file_path=media_path
            )
        except subprocess.TimeoutExpired:
            raise MediaValidationError(
                "FFprobe timeout - file may be corrupted",
                file_path=media_path
            )
        
        return self._parse_metadata(data, media_path, file_size)
    
    def _parse_metadata(self, data: dict, path: str, file_size: int) -> MediaMetadata:
        """Parse FFprobe JSON output into MediaMetadata"""
        format_info = data.get('format', {})
        streams = data.get('streams', [])
        
        # Find video and audio streams
        video_stream = next((s for s in streams if s.get('codec_type') == 'video'), None)
        audio_stream = next((s for s in streams if s.get('codec_type') == 'audio'), None)
        
        # Extract video information
        video_codec = video_stream.get('codec_name') if video_stream else None
        audio_codec = audio_stream.get('codec_name') if audio_stream else None
        
        # Extract resolution
        width = int(video_stream.get('width', 0)) if video_stream else 0
        height = int(video_stream.get('height', 0)) if video_stream else 0
        resolution = (width, height)
        
        # Extract FPS
        fps = 0.0
        if video_stream and 'r_frame_rate' in video_stream:
            try:
                fps_str = video_stream['r_frame_rate']
                if '/' in fps_str:
                    num, den = fps_str.split('/')
                    fps = float(num) / float(den)
                else:
                    fps = float(fps_str)
            except (ValueError, ZeroDivisionError):
                fps = 0.0
        
        # Extract bitrate
        bitrate = int(format_info.get('bit_rate', 0))
        
        # Extract duration
        duration = float(format_info.get('duration', 0))
        
        # Extract format name
        format_name = format_info.get('format_name', 'unknown')
        
        return MediaMetadata(
            path=path,
            duration=duration,
            video_codec=video_codec,
            audio_codec=audio_codec,
            resolution=resolution,
            fps=fps,
            bitrate=bitrate,
            has_video=video_stream is not None,
            has_audio=audio_stream is not None,
            file_size=file_size,
            format_name=format_name
        )
    
    def validate_for_slicing(self, metadata: MediaMetadata) -> bool:
        """
        Validate if media is suitable for slicing
        
        Args:
            metadata: Media metadata
            
        Returns:
            bool: True if suitable for slicing
        """
        # Check if media has video
        if not metadata.has_video:
            logger.warning(f"No video stream found in {metadata.path}")
            return False
        
        # Check if duration is reasonable
        if metadata.duration < 1.0:
            logger.warning(f"Media duration too short: {metadata.duration}s")
            return False
        
        # Check if resolution is valid
        if metadata.resolution[0] < 320 or metadata.resolution[1] < 240:
            logger.warning(f"Resolution too low: {metadata.resolution}")
            return False
        
        return True
    
    def get_slicing_recommendations(self, metadata: MediaMetadata) -> Dict[str, Any]:
        """
        Get recommendations for slicing based on metadata
        
        Args:
            metadata: Media metadata
            
        Returns:
            Dict with slicing recommendations
        """
        recommendations = {
            'quality': 'high',
            'crf': 18,
            'preset': 'medium',
            'audio_bitrate': '192k'
        }
        
        # Adjust quality based on source
        if metadata.bitrate < 1000000:  # Less than 1 Mbps
            recommendations['quality'] = 'medium'
            recommendations['crf'] = 23
        elif metadata.bitrate > 5000000:  # More than 5 Mbps
            recommendations['quality'] = 'lossless'
            recommendations['crf'] = 0
            recommendations['preset'] = 'slow'
        
        # Adjust audio bitrate based on source
        if metadata.audio_codec == 'aac':
            recommendations['audio_bitrate'] = '128k'
        elif metadata.audio_codec == 'mp3':
            recommendations['audio_bitrate'] = '160k'
        
        return recommendations
