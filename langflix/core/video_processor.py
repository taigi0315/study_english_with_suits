"""
Video processing module for LangFlix
Handles video file loading, validation, and clip extraction
"""
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import ffmpeg

logger = logging.getLogger(__name__)


class VideoProcessor:
    """
    Handles video file operations including loading, validation, and clip extraction
    """
    
    def __init__(self, media_dir: str = "assets/media", video_file: str = None):
        """
        Initialize video processor
        
        Args:
            media_dir: Directory containing video files
            video_file: Optional direct path to video file (if provided, will be used directly)
        """
        self.media_dir = Path(media_dir)
        self.video_file = Path(video_file) if video_file else None
        self.supported_formats = {'.mp4', '.mkv', '.avi', '.mov', '.wmv'}
        
    def find_video_file(self, subtitle_file_path: str) -> Optional[Path]:
        """
        Find corresponding video file for a subtitle file
        
        Args:
            subtitle_file_path: Path to subtitle file
            
        Returns:
            Path to corresponding video file, or None if not found
        """
        # If video_file was provided directly, use it (priority)
        if self.video_file and self.video_file.exists():
            logger.info(f"Using directly specified video file: {self.video_file}")
            return self.video_file
        
        subtitle_path = Path(subtitle_file_path)
        subtitle_name = subtitle_path.stem  # Remove extension
        
        # Remove language suffix (e.g., ".en" from "Pilot.720p.WEB-DL.en")
        if subtitle_name.endswith('.en'):
            base_name = subtitle_name[:-3]  # Remove ".en"
        else:
            base_name = subtitle_name
            
        logger.info(f"Looking for video file with base name: {base_name}")
        
        # Search for video files with matching base name
        # First try direct match in media directory
        for video_file in self.media_dir.glob(f"{base_name}.*"):
            if video_file.suffix.lower() in self.supported_formats:
                logger.info(f"Found video file: {video_file}")
                return video_file
        
        # Try searching in subdirectories (e.g., assets/media/Suits/)
        for video_file in self.media_dir.rglob(f"{base_name}.*"):
            if video_file.suffix.lower() in self.supported_formats:
                logger.info(f"Found video file in subdirectory: {video_file}")
                return video_file
        
        # If no exact match, try more flexible matching
        # Extract episode info (e.g., "1x01" from "Suits - 1x01 - Pilot.720p.WEB-DL")
        import re
        episode_match = re.search(r'(\d+x\d+)', base_name)
        if episode_match:
            episode = episode_match.group(1)
            logger.info(f"Looking for video with episode: {episode}")
            
            # Search for any video file containing the episode number
            for video_file in self.media_dir.glob(f"*{episode}*"):
                if video_file.suffix.lower() in self.supported_formats:
                    logger.info(f"Found video file by episode: {video_file}")
                    return video_file
        
        # If still no match, try any video file in the directory
        logger.info("Trying any video file in directory")
        for video_file in self.media_dir.glob("*"):
            if video_file.suffix.lower() in self.supported_formats:
                logger.info(f"Using any available video file: {video_file}")
                return video_file
                
        logger.warning(f"No video file found for subtitle: {subtitle_file_path}")
        return None
    
    def validate_video_file(self, video_path: Path) -> Dict[str, Any]:
        """
        Validate video file and extract metadata
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary with video metadata and validation status
        """
        try:
            # Check if file exists
            if not video_path.exists():
                return {
                    'valid': False,
                    'error': f"Video file not found: {video_path}",
                    'metadata': None
                }
            
            # Get video metadata using ffmpeg
            probe = ffmpeg.probe(str(video_path))
            video_stream = next(
                (stream for stream in probe['streams'] if stream['codec_type'] == 'video'), 
                None
            )
            
            if not video_stream:
                return {
                    'valid': False,
                    'error': "No video stream found in file",
                    'metadata': None
                }
            
            # Extract metadata
            metadata = {
                'duration': float(probe['format']['duration']),
                'width': int(video_stream['width']),
                'height': int(video_stream['height']),
                'fps': eval(video_stream['r_frame_rate']),
                'codec': video_stream['codec_name'],
                'bitrate': int(probe['format'].get('bit_rate', 0))
            }
            
            logger.info(f"Video metadata: {metadata}")
            
            return {
                'valid': True,
                'error': None,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error validating video file {video_path}: {e}")
            return {
                'valid': False,
                'error': f"Error validating video: {e}",
                'metadata': None
            }
    
    def extract_clip(self, video_path: Path, start_time: str, end_time: str, 
                   output_path: Path) -> bool:
        """
        Extract video clip between start and end times
        
        Args:
            video_path: Path to source video file
            start_time: Start time in format "HH:MM:SS.mmm"
            end_time: End time in format "HH:MM:SS.mmm"
            output_path: Path for output clip
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Extracting clip from {video_path} ({start_time} - {end_time})")
            
            # Convert time format from "HH:MM:SS,mmm" to "HH:MM:SS.mmm"
            start_ffmpeg = start_time.replace(',', '.')
            end_ffmpeg = end_time.replace(',', '.')
            
            # Calculate duration
            start_seconds = self._time_to_seconds(start_ffmpeg)
            end_seconds = self._time_to_seconds(end_ffmpeg)
            duration = end_seconds - start_seconds
            
            logger.info(f"Clip duration: {duration:.3f} seconds")
            
            # Extract clip using ffmpeg with precise timing
            # Use -ss and -t for exact start and duration
            # Re-encode for frame accuracy
            (
                ffmpeg
                .input(str(video_path), ss=start_seconds, t=duration)
                .output(str(output_path), 
                       vcodec='libx264',  # Re-encode for frame accuracy
                       acodec='aac',
                       preset='fast',
                       crf=23,
                       avoid_negative_ts='make_zero')
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info(f"Successfully extracted clip to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error extracting clip: {e}")
            return False
    
    def _time_to_seconds(self, time_str: str) -> float:
        """
        Convert time string "HH:MM:SS.mmm" to seconds
        
        Args:
            time_str: Time string in format "HH:MM:SS.mmm"
            
        Returns:
            Time in seconds as float
        """
        try:
            # Split by colon and dot
            parts = time_str.replace(',', '.').split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            
            return hours * 3600 + minutes * 60 + seconds
            
        except Exception as e:
            logger.error(f"Error parsing time string '{time_str}': {e}")
            return 0.0


def get_video_file_for_subtitle(subtitle_path: str, media_dir: str = "assets/media") -> Optional[Path]:
    """
    Convenience function to find video file for a subtitle file
    
    Args:
        subtitle_path: Path to subtitle file
        media_dir: Directory containing video files
        
    Returns:
        Path to corresponding video file, or None if not found
    """
    processor = VideoProcessor(media_dir)
    return processor.find_video_file(subtitle_path)


if __name__ == "__main__":
    # Test the video processor
    import sys
    
    if len(sys.argv) > 1:
        subtitle_path = sys.argv[1]
        video_file = get_video_file_for_subtitle(subtitle_path)
        
        if video_file:
            print(f"Found video file: {video_file}")
            
            # Validate the video file
            processor = VideoProcessor()
            result = processor.validate_video_file(video_file)
            
            if result['valid']:
                print(f"Video is valid. Metadata: {result['metadata']}")
            else:
                print(f"Video validation failed: {result['error']}")
        else:
            print("No video file found")
    else:
        print("Usage: python video_processor.py <subtitle_file_path>")
