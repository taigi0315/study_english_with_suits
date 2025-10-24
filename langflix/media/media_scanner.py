"""
Media Scanner Module
Scans media directories to discover video files and their associated subtitle files
"""
import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
import ffmpeg

logger = logging.getLogger(__name__)


class MediaScanner:
    """Scans media directories for video files and associated subtitles"""
    
    SUPPORTED_VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.mov', '.m4v', '.webm']
    SUPPORTED_SUBTITLE_EXTENSIONS = ['.srt', '.vtt', '.ass']
    
    def __init__(self, media_directory: str, scan_recursive: bool = True):
        """
        Initialize media scanner
        
        Args:
            media_directory: Root directory to scan for media files
            scan_recursive: Whether to scan subdirectories recursively
        """
        self.media_directory = Path(media_directory)
        self.scan_recursive = scan_recursive
        
        if not self.media_directory.exists():
            raise ValueError(f"Media directory does not exist: {media_directory}")
    
    def scan_media_directory(self) -> List[Dict[str, Any]]:
        """
        Scan media directory and return list of available media files
        
        Returns:
            List of media file metadata dictionaries
        """
        media_files = []
        
        try:
            if self.scan_recursive:
                video_files = self._scan_recursive()
            else:
                video_files = self._scan_flat()
            
            for video_path in video_files:
                try:
                    media_info = self._build_media_info(video_path)
                    if media_info:
                        media_files.append(media_info)
                except Exception as e:
                    logger.warning(f"Failed to process {video_path}: {e}")
                    continue
            
            logger.info(f"Found {len(media_files)} media files in {self.media_directory}")
            return media_files
            
        except Exception as e:
            logger.error(f"Error scanning media directory: {e}")
            return []
    
    def _scan_recursive(self) -> List[Path]:
        """Recursively scan for video files"""
        video_files = []
        for ext in self.SUPPORTED_VIDEO_EXTENSIONS:
            video_files.extend(self.media_directory.rglob(f"*{ext}"))
        return sorted(video_files)
    
    def _scan_flat(self) -> List[Path]:
        """Scan only top-level directory for video files"""
        video_files = []
        for ext in self.SUPPORTED_VIDEO_EXTENSIONS:
            video_files.extend(self.media_directory.glob(f"*{ext}"))
        return sorted(video_files)
    
    def _build_media_info(self, video_path: Path) -> Optional[Dict[str, Any]]:
        """
        Build media information dictionary for a video file
        
        Args:
            video_path: Path to video file
            
        Returns:
            Media info dictionary or None if failed
        """
        try:
            # Parse show name and episode from path
            show_name, episode = self._parse_show_episode(video_path)
            
            # Find subtitle file
            subtitle_path = self._find_subtitle_file(video_path)
            
            # Get video metadata using ffprobe
            metadata = self._get_video_metadata(video_path)
            
            return {
                "id": str(video_path.relative_to(self.media_directory)),
                "show_name": show_name,
                "episode": episode,
                "video_path": str(video_path),
                "subtitle_path": str(subtitle_path) if subtitle_path else None,
                "has_subtitle": subtitle_path is not None,
                "duration": metadata.get("duration", 0.0),
                "resolution": metadata.get("resolution", "Unknown"),
                "size_mb": metadata.get("size_mb", 0.0),
                "format": metadata.get("format", "Unknown")
            }
        except Exception as e:
            logger.error(f"Failed to build media info for {video_path}: {e}")
            return None
    
    def _parse_show_episode(self, video_path: Path) -> tuple[str, str]:
        """
        Parse show name and episode from video path
        
        Args:
            video_path: Path to video file
            
        Returns:
            Tuple of (show_name, episode)
        """
        # Try to extract from directory structure
        # Expected structure: .../ShowName/Season/Episode.mkv
        # or: .../ShowName/SxxExx.mkv
        
        parts = video_path.relative_to(self.media_directory).parts
        
        # Try to find show name (usually first directory)
        show_name = parts[0] if len(parts) > 1 else video_path.stem
        
        # Try to extract episode number from filename
        filename = video_path.stem
        
        # Pattern: S01E03, S1E3, etc.
        episode_match = re.search(r'[Ss](\d+)[Ee](\d+)', filename)
        if episode_match:
            season = int(episode_match.group(1))
            episode_num = int(episode_match.group(2))
            episode = f"S{season:02d}E{episode_num:02d}"
        else:
            # Try simpler pattern: E03, E3, etc.
            episode_match = re.search(r'[Ee](\d+)', filename)
            if episode_match:
                episode_num = int(episode_match.group(1))
                episode = f"E{episode_num:02d}"
            else:
                # Fallback to filename
                episode = filename
        
        return show_name, episode
    
    def _find_subtitle_file(self, video_path: Path) -> Optional[Path]:
        """
        Find subtitle file for a video file
        
        Searches for subtitle files with the same basename as the video file
        
        Args:
            video_path: Path to video file
            
        Returns:
            Path to subtitle file or None if not found
        """
        video_basename = video_path.stem
        video_dir = video_path.parent
        
        # Try exact match first
        for ext in self.SUPPORTED_SUBTITLE_EXTENSIONS:
            subtitle_path = video_dir / f"{video_basename}{ext}"
            if subtitle_path.exists():
                return subtitle_path
        
        # Try common subtitle locations
        subtitle_dirs = [
            video_dir,
            video_dir / "subtitles",
            video_dir / "subs",
            video_dir / "Subtitles",
            video_dir / "Subs"
        ]
        
        for sub_dir in subtitle_dirs:
            if not sub_dir.exists():
                continue
            for ext in self.SUPPORTED_SUBTITLE_EXTENSIONS:
                # Try exact match
                subtitle_path = sub_dir / f"{video_basename}{ext}"
                if subtitle_path.exists():
                    return subtitle_path
                # Try with language codes (e.g., .en.srt, .ko.srt)
                for lang_code in ['en', 'ko', 'ja', 'zh', 'es', 'fr']:
                    subtitle_path = sub_dir / f"{video_basename}.{lang_code}{ext}"
                    if subtitle_path.exists():
                        return subtitle_path
        
        return None
    
    def _get_video_metadata(self, video_path: Path) -> Dict[str, Any]:
        """
        Extract video metadata using ffprobe
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary with video metadata
        """
        try:
            probe = ffmpeg.probe(str(video_path))
            video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
            
            if not video_stream:
                return {}
            
            # Get duration
            duration = float(probe['format'].get('duration', 0))
            
            # Get resolution
            width = video_stream.get('width', 0)
            height = video_stream.get('height', 0)
            resolution = f"{width}x{height}"
            
            # Get file size
            size_bytes = int(probe['format'].get('size', 0))
            size_mb = round(size_bytes / (1024 * 1024), 2)
            
            # Get format
            format_name = probe['format'].get('format_name', 'Unknown')
            
            return {
                "duration": duration,
                "resolution": resolution,
                "width": width,
                "height": height,
                "size_mb": size_mb,
                "format": format_name,
                "codec": video_stream.get('codec_name', 'Unknown')
            }
        except Exception as e:
            logger.error(f"Failed to probe video metadata for {video_path}: {e}")
            return {}

