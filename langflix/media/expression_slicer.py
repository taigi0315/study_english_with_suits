"""
Expression video slicing for LangFlix.

This module provides functionality to slice media files for expressions
using FFmpeg with precise timestamps from external transcription.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import subprocess
import asyncio
import logging
# Note: AlignedExpression import removed - using external transcription
from langflix.media.media_validator import MediaMetadata
from langflix.storage.base import StorageBackend
from langflix import settings
from .exceptions import VideoSlicingError

logger = logging.getLogger(__name__)


class ExpressionMediaSlicer:
    """Slice media files for expressions using FFmpeg"""
    
    def __init__(
        self,
        storage_backend: StorageBackend,
        output_dir: Path,
        quality: str = 'high'
    ):
        """
        Initialize expression media slicer
        
        Args:
            storage_backend: Storage backend for saving sliced videos
            output_dir: Local output directory
            quality: Video quality preset (low, medium, high, lossless)
        """
        self.storage = storage_backend
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.quality = quality
        self.quality_settings = self._get_quality_settings(quality)
        
        # Get buffer settings from configuration
        self.buffer_start = settings.get_expression_config().get('media', {}).get('slicing', {}).get('buffer_start', 0.2)
        self.buffer_end = settings.get_expression_config().get('media', {}).get('slicing', {}).get('buffer_end', 0.2)
    
    def _get_quality_settings(self, quality: str) -> Dict[str, Any]:
        """Get FFmpeg quality settings"""
        settings = {
            'low': {
                'crf': 28,
                'preset': 'veryfast',
                'audio_bitrate': '128k'
            },
            'medium': {
                'crf': 23,
                'preset': 'medium',
                'audio_bitrate': '192k'
            },
            'high': {
                'crf': 18,
                'preset': 'slow',
                'audio_bitrate': '256k'
            },
            'lossless': {
                'crf': 0,
                'preset': 'veryslow',
                'audio_bitrate': '320k'
            }
        }
        return settings.get(quality, settings['high'])
    
    async def slice_expression(
        self,
        media_path: str,
        aligned_expression: AlignedExpression,
        media_id: str
    ) -> str:
        """
        Slice media file for expression
        
        Args:
            media_path: Path to source media file
            aligned_expression: Aligned expression with timestamps
            media_id: Unique media identifier
            
        Returns:
            str: Path to sliced video (local or cloud)
        """
        try:
            # Calculate times with buffer
            start_time = max(
                0,
                aligned_expression.start_time - self.buffer_start
            )
            end_time = aligned_expression.end_time + self.buffer_end
            duration = end_time - start_time
            
            # Generate output filename
            expression_text = aligned_expression.expression[:30].replace(' ', '_').replace('/', '_')
            output_filename = f"expr_{media_id}_{expression_text}_{int(start_time*1000)}.mp4"
            local_output = self.output_dir / output_filename
            
            # FFmpeg command
            ffmpeg_cmd = [
                'ffmpeg',
                '-ss', str(start_time),  # Seek to start
                '-i', media_path,
                '-t', str(duration),  # Duration
                '-c:v', 'libx264',
                '-preset', self.quality_settings['preset'],
                '-crf', str(self.quality_settings['crf']),
                '-c:a', 'aac',
                '-b:a', self.quality_settings['audio_bitrate'],
                '-movflags', '+faststart',  # Web optimization
                '-avoid_negative_ts', 'make_zero',  # Fix timestamp issues
                '-y',  # Overwrite
                str(local_output)
            ]
            
            logger.info(f"Slicing expression video: {output_filename}")
            logger.debug(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
            
            # Run FFmpeg
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise VideoSlicingError(
                    f"FFmpeg failed: {stderr.decode()}",
                    expression=aligned_expression.expression,
                    file_path=media_path
                )
            
            # Verify output file
            if not local_output.exists() or local_output.stat().st_size == 0:
                raise VideoSlicingError(
                    "Output file not created or empty",
                    expression=aligned_expression.expression,
                    file_path=media_path
                )
            
            logger.info(f"Successfully sliced video: {output_filename}")
            
            # Upload to storage backend
            cloud_path = await self._upload_to_storage(local_output, output_filename)
            
            # Clean up local file if using cloud storage
            if cloud_path != str(local_output):
                local_output.unlink()
                logger.debug(f"Cleaned up local file: {local_output}")
            
            return cloud_path
            
        except Exception as e:
            logger.error(f"Failed to slice expression: {e}")
            raise VideoSlicingError(
                f"Slicing failed: {str(e)}",
                expression=aligned_expression.expression,
                file_path=media_path
            )
    
    async def slice_multiple_expressions(
        self,
        media_path: str,
        aligned_expressions: List[AlignedExpression],
        media_id: str
    ) -> List[str]:
        """
        Slice multiple expressions from media file
        
        Args:
            media_path: Path to source media file
            aligned_expressions: List of aligned expressions
            media_id: Unique media identifier
            
        Returns:
            List[str]: Paths to sliced videos
        """
        tasks = []
        for expression in aligned_expressions:
            task = self.slice_expression(media_path, expression, media_id)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        successful_paths = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to slice expression {i}: {result}")
            else:
                successful_paths.append(result)
        
        return successful_paths
    
    async def _upload_to_storage(self, local_path: Path, filename: str) -> str:
        """
        Upload sliced video to storage backend
        
        Args:
            local_path: Local file path
            filename: Filename for storage
            
        Returns:
            str: Cloud storage path or local path
        """
        try:
            # Upload to storage backend
            cloud_path = await self.storage.upload_file(
                str(local_path),
                f"expressions/{filename}"
            )
            logger.info(f"Uploaded to storage: {cloud_path}")
            return cloud_path
        except Exception as e:
            logger.warning(f"Failed to upload to storage: {e}")
            # Return local path as fallback
            return str(local_path)
    
    def get_slicing_info(self, aligned_expression: AlignedExpression) -> Dict[str, Any]:
        """
        Get information about slicing operation
        
        Args:
            aligned_expression: Aligned expression
            
        Returns:
            Dict with slicing information
        """
        start_time = max(0, aligned_expression.start_time - self.buffer_start)
        end_time = aligned_expression.end_time + self.buffer_end
        duration = end_time - start_time
        
        return {
            'expression': aligned_expression.expression,
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration,
            'buffer_start': self.buffer_start,
            'buffer_end': self.buffer_end,
            'quality': self.quality,
            'quality_settings': self.quality_settings
        }
    
    def validate_slicing_parameters(
        self,
        media_metadata: MediaMetadata,
        aligned_expression: AlignedExpression
    ) -> bool:
        """
        Validate slicing parameters
        
        Args:
            media_metadata: Media metadata
            aligned_expression: Aligned expression
            
        Returns:
            bool: True if parameters are valid
        """
        # Check if expression is within media duration
        if aligned_expression.end_time > media_metadata.duration:
            logger.warning(
                f"Expression end time ({aligned_expression.end_time}) "
                f"exceeds media duration ({media_metadata.duration})"
            )
            return False
        
        # Check if start time is valid
        if aligned_expression.start_time < 0:
            logger.warning(f"Invalid start time: {aligned_expression.start_time}")
            return False
        
        # Check if duration is reasonable
        expression_duration = aligned_expression.end_time - aligned_expression.start_time
        if expression_duration < 0.1:  # Less than 100ms
            logger.warning(f"Expression duration too short: {expression_duration}")
            return False
        
        return True
