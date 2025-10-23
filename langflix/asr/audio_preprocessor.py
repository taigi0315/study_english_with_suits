#!/usr/bin/env python3
"""
Audio preprocessing for WhisperX ASR

This module handles audio extraction and preprocessing for WhisperX transcription.
"""

import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from langflix.core.video_processor import VideoProcessor
from langflix.asr.exceptions import AudioExtractionError, AudioPreprocessingError

logger = logging.getLogger(__name__)


class AudioPreprocessor:
    """
    Extract and preprocess audio for WhisperX ASR
    
    This class handles:
    - Audio extraction from video files
    - Audio format conversion for WhisperX
    - Sample rate normalization
    - Mono channel conversion
    """
    
    def __init__(self, video_processor: Optional[VideoProcessor] = None):
        """
        Initialize audio preprocessor
        
        Args:
            video_processor: Optional existing video processor for reuse
        """
        self.video_processor = video_processor
        self.supported_formats = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'}
        
    def extract_audio(
        self,
        media_path: str,
        output_path: str,
        sample_rate: int = 16000,
        channels: int = 1,
        format: str = 'wav'
    ) -> str:
        """
        Extract and preprocess audio for WhisperX
        
        Args:
            media_path: Path to input media file
            output_path: Path for output audio file
            sample_rate: Target sample rate (default: 16000 for WhisperX)
            channels: Number of audio channels (default: 1 for mono)
            format: Output audio format (default: wav)
            
        Returns:
            Path to preprocessed audio file
            
        Raises:
            AudioExtractionError: If audio extraction fails
        """
        media_path = Path(media_path)
        output_path = Path(output_path)
        
        # Validate input file
        if not media_path.exists():
            raise AudioExtractionError(
                str(media_path),
                "Media file does not exist"
            )
        
        if media_path.suffix.lower() not in self.supported_formats:
            raise AudioExtractionError(
                str(media_path),
                f"Unsupported format. Supported: {', '.join(self.supported_formats)}"
            )
        
        # Create output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build FFmpeg command for audio extraction
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', str(media_path),
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # 16-bit PCM
            '-ar', str(sample_rate),  # Sample rate
            '-ac', str(channels),  # Audio channels
            '-f', format,  # Output format
            '-y',  # Overwrite output
            str(output_path)
        ]
        
        logger.info(f"Extracting audio from {media_path} to {output_path}")
        logger.debug(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
        
        try:
            result = subprocess.run(
                ffmpeg_cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Verify output file was created
            if not output_path.exists():
                raise AudioExtractionError(
                    str(media_path),
                    "Output file was not created"
                )
            
            # Check file size
            if output_path.stat().st_size == 0:
                raise AudioExtractionError(
                    str(media_path),
                    "Output file is empty"
                )
            
            logger.info(f"Successfully extracted audio: {output_path}")
            return str(output_path)
            
        except subprocess.TimeoutExpired:
            raise AudioExtractionError(
                str(media_path),
                "Audio extraction timed out after 5 minutes"
            )
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else "Unknown FFmpeg error"
            logger.error(f"FFmpeg error: {error_msg}")
            raise AudioExtractionError(
                str(media_path),
                f"FFmpeg failed: {error_msg}"
            )
        except Exception as e:
            raise AudioExtractionError(
                str(media_path),
                f"Unexpected error: {str(e)}"
            )
    
    def get_audio_info(self, audio_path: str) -> Dict[str, Any]:
        """
        Get audio file information using FFprobe
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary with audio information
            
        Raises:
            AudioPreprocessingError: If info extraction fails
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise AudioPreprocessingError(
                str(audio_path),
                "Audio file does not exist"
            )
        
        ffprobe_cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            str(audio_path)
        ]
        
        try:
            result = subprocess.run(
                ffprobe_cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            import json
            info = json.loads(result.stdout)
            
            # Extract relevant audio information
            audio_stream = None
            for stream in info.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    audio_stream = stream
                    break
            
            if not audio_stream:
                raise AudioPreprocessingError(
                    str(audio_path),
                    "No audio stream found"
                )
            
            return {
                'duration': float(info.get('format', {}).get('duration', 0)),
                'sample_rate': int(audio_stream.get('sample_rate', 0)),
                'channels': int(audio_stream.get('channels', 0)),
                'codec': audio_stream.get('codec_name', 'unknown'),
                'bit_rate': int(audio_stream.get('bit_rate', 0)),
                'size': audio_path.stat().st_size
            }
            
        except subprocess.CalledProcessError as e:
            raise AudioPreprocessingError(
                str(audio_path),
                f"FFprobe failed: {e.stderr}"
            )
        except json.JSONDecodeError as e:
            raise AudioPreprocessingError(
                str(audio_path),
                f"Failed to parse FFprobe output: {str(e)}"
            )
        except Exception as e:
            raise AudioPreprocessingError(
                str(audio_path),
                f"Unexpected error: {str(e)}"
            )
    
    def validate_audio_for_whisperx(self, audio_path: str) -> bool:
        """
        Validate that audio file is suitable for WhisperX
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            True if audio is suitable for WhisperX
            
        Raises:
            AudioPreprocessingError: If validation fails
        """
        try:
            info = self.get_audio_info(audio_path)
            
            # Check sample rate (WhisperX works best with 16kHz)
            sample_rate = info.get('sample_rate', 0)
            if sample_rate < 8000 or sample_rate > 48000:
                logger.warning(f"Unusual sample rate: {sample_rate}Hz")
            
            # Check channels (mono is preferred)
            channels = info.get('channels', 0)
            if channels > 2:
                logger.warning(f"Multi-channel audio detected: {channels} channels")
            
            # Check duration (not too short or too long)
            duration = info.get('duration', 0)
            if duration < 1.0:
                raise AudioPreprocessingError(
                    audio_path,
                    "Audio too short (less than 1 second)"
                )
            if duration > 3600:  # 1 hour
                logger.warning(f"Very long audio: {duration:.1f} seconds")
            
            logger.info(f"Audio validation passed: {duration:.1f}s, {sample_rate}Hz, {channels}ch")
            return True
            
        except Exception as e:
            if isinstance(e, AudioPreprocessingError):
                raise
            raise AudioPreprocessingError(
                audio_path,
                f"Validation failed: {str(e)}"
            )
    
    def preprocess_for_whisperx(
        self,
        media_path: str,
        output_dir: str,
        sample_rate: int = 16000
    ) -> str:
        """
        Complete preprocessing pipeline for WhisperX
        
        Args:
            media_path: Path to input media file
            output_dir: Directory for output files
            sample_rate: Target sample rate
            
        Returns:
            Path to preprocessed audio file
        """
        media_path = Path(media_path)
        output_dir = Path(output_dir)
        
        # Generate output filename
        audio_filename = f"{media_path.stem}_whisperx.wav"
        output_path = output_dir / audio_filename
        
        # Extract audio
        audio_path = self.extract_audio(
            str(media_path),
            str(output_path),
            sample_rate=sample_rate,
            channels=1,  # Mono for WhisperX
            format='wav'
        )
        
        # Validate for WhisperX
        self.validate_audio_for_whisperx(audio_path)
        
        logger.info(f"Audio preprocessing complete: {audio_path}")
        return audio_path
