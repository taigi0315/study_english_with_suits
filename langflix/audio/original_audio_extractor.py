"""
Original audio extractor for LangFlix.

This module provides functionality to extract audio segments from original media files
when TTS is disabled, using subtitle timestamps to create educational audio timelines.
"""

import logging
import tempfile
from pathlib import Path
from typing import Tuple, Optional
import subprocess
import shutil

from langflix.core.models import ExpressionAnalysis
from langflix import settings

logger = logging.getLogger(__name__)


class OriginalAudioExtractor:
    """
    Extract audio segments from original media files using subtitle timestamps.
    
    This class handles audio extraction from the original video file when TTS is disabled,
    creating the same 3x repetition timeline pattern as TTS for educational consistency.
    """
    
    def __init__(self, original_video_path: str):
        """
        Initialize the original audio extractor.
        
        Args:
            original_video_path: Path to the original video file
        """
        self.original_video_path = Path(original_video_path)
        if not self.original_video_path.exists():
            raise FileNotFoundError(f"Original video file not found: {original_video_path}")
        
        logger.info(f"OriginalAudioExtractor initialized with video: {self.original_video_path}")
    
    def extract_expression_audio(
        self, 
        expression: ExpressionAnalysis, 
        output_path: Path, 
        audio_format: str = "wav"
    ) -> Tuple[Path, float]:
        """
        Extract audio segment for an expression from the original video.
        
        Args:
            expression: ExpressionAnalysis object containing timestamps
            output_path: Output path for the extracted audio
            audio_format: Audio format (wav or mp3)
            
        Returns:
            Tuple of (audio_file_path, duration_in_seconds)
            
        Raises:
            ValueError: If expression timestamps are invalid
            RuntimeError: If audio extraction fails
        """
        if not expression.expression_start_time or not expression.expression_end_time:
            raise ValueError(f"Expression '{expression.expression}' missing start/end timestamps")
        
        logger.info(f"Extracting audio for expression: '{expression.expression}'")
        logger.info(f"Timestamps: {expression.expression_start_time} - {expression.expression_end_time}")
        
        # Convert timestamps to seconds
        start_seconds = self._timestamp_to_seconds(expression.expression_start_time)
        end_seconds = self._timestamp_to_seconds(expression.expression_end_time)
        duration = end_seconds - start_seconds
        
        if duration <= 0:
            raise ValueError(f"Invalid duration: {duration}s (start: {start_seconds}s, end: {end_seconds}s)")
        
        logger.info(f"Audio segment duration: {duration:.2f}s")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Set audio codec and quality based on format - preserve original sample rate
        if audio_format.lower() == "wav":
            # Use original sample rate and proper channel downmix
            codec_args = [
                "-c:a", "pcm_s16le",  # 16-bit PCM
                "-ac", "2",           # Downmix to stereo (from 5.1 if needed)
                # Don't force sample rate - keep original (usually 48kHz for video)
            ]
            output_path = output_path.with_suffix('.wav')
        else:  # mp3
            codec_args = [
                "-c:a", "mp3", 
                "-b:a", "192k",
                "-ac", "2"            # Downmix to stereo
                # Don't force sample rate - keep original
            ]
            output_path = output_path.with_suffix('.mp3')
        
        # FFmpeg command to extract audio segment
        ffmpeg_cmd = [
            "ffmpeg",
            "-ss", str(start_seconds),  # Seek to start time
            "-i", str(self.original_video_path),  # Input video
            "-t", str(duration),  # Duration
            "-vn",  # No video output
            *codec_args,  # Audio codec and quality settings
            "-avoid_negative_ts", "make_zero",  # Fix timestamp issues
            "-y",  # Overwrite output file
            str(output_path)
        ]
        
        logger.debug(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
        
        try:
            # Run FFmpeg to extract audio
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            if not output_path.exists():
                raise RuntimeError(f"Audio extraction failed - output file not created: {output_path}")
            
            file_size = output_path.stat().st_size
            if file_size == 0:
                raise RuntimeError(f"Audio extraction failed - empty file created: {output_path}")
            
            logger.info(f"Successfully extracted audio: {output_path} ({file_size} bytes)")
            return output_path, duration
            
        except subprocess.CalledProcessError as e:
            error_msg = f"FFmpeg audio extraction failed: {e.stderr}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during audio extraction: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def create_audio_timeline(
        self,
        expression: ExpressionAnalysis,
        output_dir: Path,
        expression_index: int = 0,
        audio_format: str = "wav"
    ) -> Tuple[Path, float]:
        """
        Create an audio timeline with 3x repetition pattern matching TTS behavior.
        
        Timeline pattern: 1s silence - audio - 0.5s silence - audio - 0.5s silence - audio - 1s silence
        
        Args:
            expression: ExpressionAnalysis object
            output_dir: Directory for output files
            expression_index: Index for unique filename generation
            audio_format: Audio format (wav or mp3)
            
        Returns:
            Tuple of (timeline_audio_path, total_duration)
        """
        logger.info(f"Creating audio timeline for expression {expression_index}: '{expression.expression}'")
        
        # Create temporary directory for audio processing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Extract original audio segment
            base_audio_path = temp_path / f"expression_{expression_index}_base.{audio_format}"
            extracted_path, segment_duration = self.extract_expression_audio(
                expression, base_audio_path, audio_format
            )
            
            # Create silence audio files
            silence_1s_path = temp_path / f"silence_1s.{audio_format}"
            silence_05s_path = temp_path / f"silence_0.5s.{audio_format}"
            
            self._create_silence_audio(silence_1s_path, 1.0, audio_format)
            self._create_silence_audio(silence_05s_path, 0.5, audio_format)
            
            # Create concatenation list file for FFmpeg
            concat_list_path = temp_path / "concat_list.txt"
            with open(concat_list_path, 'w') as f:
                f.write(f"file '{silence_1s_path}'\n")      # 1s silence
                f.write(f"file '{extracted_path}'\n")        # Original audio
                f.write(f"file '{silence_05s_path}'\n")      # 0.5s silence  
                f.write(f"file '{extracted_path}'\n")        # Original audio (2nd)
                f.write(f"file '{silence_05s_path}'\n")      # 0.5s silence
                f.write(f"file '{extracted_path}'\n")        # Original audio (3rd)
                f.write(f"file '{silence_1s_path}'\n")       # 1s silence
            
            # Calculate total duration
            total_duration = 1.0 + segment_duration + 0.5 + segment_duration + 0.5 + segment_duration + 1.0
            
            # Output timeline file
            timeline_filename = f"expression_{expression_index}_timeline.{audio_format}"
            timeline_path = output_dir / timeline_filename
            
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # FFmpeg command to concatenate audio files
            concat_cmd = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list_path),
                "-c", "copy",  # Copy without re-encoding for speed
                "-y",  # Overwrite
                str(timeline_path)
            ]
            
            logger.debug(f"Concat command: {' '.join(concat_cmd)}")
            
            try:
                subprocess.run(concat_cmd, capture_output=True, text=True, check=True)
                
                if not timeline_path.exists():
                    raise RuntimeError(f"Timeline creation failed - output not created: {timeline_path}")
                
                logger.info(f"Audio timeline created: {timeline_path} (duration: {total_duration:.2f}s)")
                return timeline_path, total_duration
                
            except subprocess.CalledProcessError as e:
                error_msg = f"FFmpeg concatenation failed: {e.stderr}"
                logger.error(error_msg)
                raise RuntimeError(error_msg) from e
    
    def _create_silence_audio(self, output_path: Path, duration: float, audio_format: str) -> None:
        """
        Create a silence audio file with specified duration.
        
        Args:
            output_path: Output path for silence file
            duration: Duration in seconds
            audio_format: Audio format (wav or mp3)
        """
        # Use 48kHz to match typical video audio (not 44.1kHz for CD audio)
        sample_rate = 48000
        
        if audio_format.lower() == "wav":
            codec_args = ["-c:a", "pcm_s16le", "-ar", str(sample_rate)]
        else:  # mp3
            codec_args = ["-c:a", "mp3", "-b:a", "192k", "-ar", str(sample_rate)]
        
        silence_cmd = [
            "ffmpeg",
            "-f", "lavfi",
            "-i", f"anullsrc=channel_layout=stereo:sample_rate={sample_rate}",
            "-t", str(duration),
            *codec_args,
            "-y",
            str(output_path)
        ]
        
        try:
            subprocess.run(silence_cmd, capture_output=True, text=True, check=True)
            logger.debug(f"Created silence audio: {output_path} ({duration}s)")
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to create silence audio: {e.stderr}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def _timestamp_to_seconds(self, timestamp: str) -> float:
        """
        Convert SRT timestamp to seconds.
        
        Args:
            timestamp: Timestamp in format "HH:MM:SS,mmm" or "HH:MM:SS.mmm"
            
        Returns:
            Time in seconds as float
        """
        try:
            # Replace comma with dot for milliseconds if needed
            timestamp = timestamp.replace(',', '.')
            
            # Split by colon and dot
            parts = timestamp.split(':')
            if len(parts) != 3:
                raise ValueError(f"Invalid timestamp format: {timestamp}")
            
            hours = int(parts[0])
            minutes = int(parts[1])
            
            # Handle seconds and milliseconds
            seconds_part = parts[2]
            if '.' in seconds_part:
                seconds, milliseconds = seconds_part.split('.')
                seconds = int(seconds)
                # Pad milliseconds to 3 digits if needed
                milliseconds = milliseconds.ljust(3, '0')[:3]
                milliseconds = int(milliseconds)
            else:
                seconds = int(seconds_part)
                milliseconds = 0
            
            total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
            
            logger.debug(f"Converted timestamp {timestamp} to {total_seconds:.3f}s")
            return total_seconds
            
        except Exception as e:
            error_msg = f"Error parsing timestamp '{timestamp}': {e}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e


def create_original_audio_timeline(
    expression: ExpressionAnalysis,
    original_video_path: str,
    output_dir: Path,
    expression_index: int = 0,
    audio_format: str = "wav"
) -> Tuple[Path, float]:
    """
    Convenience function to create audio timeline from original video.
    
    Args:
        expression: ExpressionAnalysis object with timestamps
        original_video_path: Path to the original video file
        output_dir: Directory for output files
        expression_index: Index for unique filename generation
        audio_format: Audio format (wav or mp3)
        
    Returns:
        Tuple of (timeline_audio_path, total_duration)
    """
    extractor = OriginalAudioExtractor(original_video_path)
    return extractor.create_audio_timeline(expression, output_dir, expression_index, audio_format)
