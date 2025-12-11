"""
Expression video slicing for LangFlix.

This module provides functionality to slice media files for expressions
using FFmpeg with precise timestamps from external transcription.

TICKET-036: Added concurrency control with asyncio.Semaphore to prevent
resource exhaustion during batch slicing operations.
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
    """
    Slice media files for expressions using FFmpeg.
    
    TICKET-036: Implements concurrency control to prevent FFmpeg process storms
    on resource-limited servers. Uses asyncio.Semaphore to limit concurrent operations.
    """
    
    def __init__(
        self,
        storage_backend: StorageBackend,
        output_dir: Path,
        quality: str = 'high',
        max_concurrency: Optional[int] = None
    ):
        """
        Initialize expression media slicer
        
        Args:
            storage_backend: Storage backend for saving sliced videos
            output_dir: Local output directory
            quality: Video quality preset (low, medium, high, lossless)
            max_concurrency: Maximum concurrent slicing operations 
                           (None = use configuration default)
        """
        self.storage = storage_backend
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.quality = quality
        self.quality_settings = self._get_quality_settings(quality)
        
        # Get buffer settings from configuration
        self.buffer_start = settings.get_expression_config().get('media', {}).get('slicing', {}).get('buffer_start', 0.2)
        self.buffer_end = settings.get_expression_config().get('media', {}).get('slicing', {}).get('buffer_end', 0.2)
        
        # TICKET-036: Concurrency control with semaphore
        if max_concurrency is None:
            max_concurrency = settings.get_max_concurrent_slicing()
        self._max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)
        logger.info(f"ExpressionMediaSlicer initialized with max_concurrency={max_concurrency}")
    
    def _get_quality_settings(self, quality: str) -> Dict[str, Any]:
        """Get FFmpeg quality settings"""
        settings = {
            'low': {
                'crf': 28,
                'preset': 'veryfast',
                'audio_bitrate': '128k'
            },
            'medium': {
                'crf': 20,          # Upgraded from 23
                'preset': 'slow',   # Upgraded from medium -> slow
                'audio_bitrate': '256k' # Upgraded from 192k
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
        expression_data: dict,  # Changed from AlignedExpression to dict
        media_id: str
    ) -> str:
        """
        Slice media file for expression
        
        Args:
            media_path: Path to source media file
            expression_data: Expression data with timestamps
            media_id: Unique media identifier
            
        Returns:
            str: Path to sliced video (local or cloud)
        """
        try:
            # Calculate times with buffer
            start_time = max(
                0,
                expression_data.get('start_time', 0) - self.buffer_start
            )
            end_time = expression_data.get('end_time', 0) + self.buffer_end
            duration = end_time - start_time
            
            # Generate output filename
            expression_text = expression_data.get('expression', 'unknown')[:30].replace(' ', '_').replace('/', '_')
            output_filename = f"expr_{media_id}_{expression_text}_{int(start_time*1000)}.mp4"
            local_output = self.output_dir / output_filename
            
            # FFmpeg command
            # IMPORTANT: Put -ss AFTER -i for accurate seeking and subtitle sync
            # When -ss is before -i (input seeking), it's faster but less accurate
            # When -ss is after -i (output seeking), it's slower but more accurate
            # For subtitle sync, we need accurate seeking, so use output seeking
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', media_path,
                '-ss', str(start_time),  # Seek to start (output seeking for accuracy)
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
                    expression=expression_data.get('expression', 'unknown'),
                    file_path=media_path
                )
            
            # Verify output file
            if not local_output.exists() or local_output.stat().st_size == 0:
                raise VideoSlicingError(
                    "Output file not created or empty",
                    expression=expression_data.get('expression', 'unknown'),
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
            
            # TICKET-036: Cleanup failed/partial files
            if 'local_output' in locals() and local_output.exists():
                try:
                    local_output.unlink()
                    logger.debug(f"Cleaned up failed slice: {local_output}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup {local_output}: {cleanup_error}")
            
            # TICKET-036: Fixed NameError - use expression_data dict instead of aligned_expression object
            raise VideoSlicingError(
                f"Slicing failed: {str(e)}",
                expression=expression_data.get('expression', 'unknown'),
                file_path=media_path
            )
    
    async def slice_multiple_expressions(
        self,
        media_path: str,
        expressions: List[dict],  # Changed from List[AlignedExpression]
        media_id: str
    ) -> List[str]:
        """
        Slice multiple expressions from media file with concurrency control.
        
        TICKET-036: Fixed NameError bug and added semaphore-based concurrency control
        to prevent resource exhaustion from unlimited parallel FFmpeg processes.
        
        Args:
            media_path: Path to source media file
            expressions: List of expression dictionaries with timestamps
            media_id: Unique media identifier
            
        Returns:
            List[str]: Paths to sliced videos (successful only)
        """
        logger.info(f"Slicing {len(expressions)} expressions with max_concurrency={self._max_concurrency}")
        
        # TICKET-036: Wrap each slice operation with semaphore guard
        async def _guarded_slice(expr: dict) -> str:
            """Slice with concurrency control"""
            async with self._semaphore:
                logger.debug(f"Acquired semaphore for expression: {expr.get('expression', 'unknown')[:30]}")
                try:
                    result = await self.slice_expression(media_path, expr, media_id)
                    return result
                finally:
                    logger.debug(f"Released semaphore for expression: {expr.get('expression', 'unknown')[:30]}")
        
        # TICKET-036: Fixed NameError - changed aligned_expressions to expressions
        tasks = [_guarded_slice(expression) for expression in expressions]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions and cleanup
        successful_paths = []
        failed_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to slice expression {i}: {result}")
                failed_count += 1
                # TICKET-036: Cleanup logic - already handled in slice_expression
            else:
                successful_paths.append(result)
        
        logger.info(f"Slicing complete: {len(successful_paths)} successful, {failed_count} failed")
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
    
    def get_slicing_info(self, expression_data: dict) -> Dict[str, Any]:
        """
        Get information about slicing operation
        
        Args:
            aligned_expression: Aligned expression
            
        Returns:
            Dict with slicing information
        """
        start_time = max(0, expression_data.get('start_time', 0) - self.buffer_start)
        end_time = expression_data.get('end_time', 0) + self.buffer_end
        duration = end_time - start_time
        
        return {
            'expression': expression_data.get('expression', 'unknown'),
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
        expression_data: dict
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
        if expression_data.get('end_time', 0) > media_metadata.duration:
            logger.warning(
                f"Expression end time ({expression_data.get('end_time', 0)}) "
                f"exceeds media duration ({media_metadata.duration})"
            )
            return False
        
        # Check if start time is valid
        if expression_data.get('start_time', 0) < 0:
            logger.warning(f"Invalid start time: {expression_data.get('start_time', 0)}")
            return False
        
        # Check if duration is reasonable
        expression_duration = expression_data.get('end_time', 0) - expression_data.get('start_time', 0)
        if expression_duration < 0.1:  # Less than 100ms
            logger.warning(f"Expression duration too short: {expression_duration}")
            return False
        
        return True
