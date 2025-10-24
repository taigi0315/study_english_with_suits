"""
Subtitle rendering for LangFlix expression videos.

This module provides functionality to render subtitles for expression videos
with configurable styling and highlighting.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import subprocess
import tempfile
import logging
from langflix.core.models import ExpressionAnalysis
# Note: AlignedExpression import removed - using external transcription
from langflix import settings
from .exceptions import SubtitleRenderingError

logger = logging.getLogger(__name__)


class SubtitleRenderer:
    """Render subtitles for expression videos"""
    
    def __init__(self, output_dir: Path):
        """
        Initialize subtitle renderer
        
        Args:
            output_dir: Output directory for subtitle files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get subtitle styling from configuration
        self.subtitle_config = settings.get_expression_subtitle_styling()
        self.default_style = self.subtitle_config.get('default', {})
        self.expression_style = self.subtitle_config.get('expression_highlight', {})
    
    def render_expression_subtitles(
        self,
        expression: ExpressionAnalysis,
        aligned_expression: AlignedExpression,
        video_path: str,
        output_path: str
    ) -> str:
        """
        Render subtitles for expression video
        
        Args:
            expression: Expression analysis data
            aligned_expression: Aligned expression with timestamps
            video_path: Path to video file
            output_path: Path for output video with subtitles
            
        Returns:
            str: Path to video with rendered subtitles
        """
        try:
            # Create temporary SRT file
            srt_content = self._create_srt_content(expression, aligned_expression)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False) as srt_file:
                srt_file.write(srt_content)
                srt_path = srt_file.name
            
            # Render subtitles with FFmpeg
            rendered_path = self._render_with_ffmpeg(
                video_path,
                srt_path,
                output_path,
                expression.expression
            )
            
            # Clean up temporary file
            Path(srt_path).unlink()
            
            return rendered_path
            
        except Exception as e:
            logger.error(f"Failed to render subtitles: {e}")
            raise SubtitleRenderingError(
                f"Subtitle rendering failed: {str(e)}",
                expression=expression.expression,
                file_path=video_path
            )
    
    def _create_srt_content(
        self,
        expression: ExpressionAnalysis,
        aligned_expression: AlignedExpression
    ) -> str:
        """
        Create SRT content for expression
        
        Args:
            expression: Expression analysis
            aligned_expression: Aligned expression with timestamps
            
        Returns:
            str: SRT content
        """
        srt_content = []
        
        # Add expression highlight
        start_time = self._format_timestamp(aligned_expression.start_time)
        end_time = self._format_timestamp(aligned_expression.end_time)
        
        # Create highlighted expression subtitle
        expression_text = f"<font color='{self.expression_style.get('color', '#FFD700')}'>{expression.expression}</font>"
        translation_text = f"<font color='{self.default_style.get('color', '#FFFFFF')}'>{expression.expression_translation}</font>"
        
        srt_content.append("1")
        srt_content.append(f"{start_time} --> {end_time}")
        srt_content.append(expression_text)
        srt_content.append(translation_text)
        srt_content.append("")
        
        # Add context dialogues if available
        if hasattr(expression, 'dialogues') and expression.dialogues:
            for i, dialogue in enumerate(expression.dialogues, 2):
                if i <= 5:  # Limit to 5 context lines
                    context_start = aligned_expression.start_time + (i - 1) * 0.5
                    context_end = context_start + 2.0
                    
                    srt_content.append(str(i))
                    srt_content.append(f"{self._format_timestamp(context_start)} --> {self._format_timestamp(context_end)}")
                    srt_content.append(f"<font color='{self.default_style.get('color', '#FFFFFF')}'>{dialogue}</font>")
                    if hasattr(expression, 'translation') and i - 2 < len(expression.translation):
                        srt_content.append(f"<font color='{self.default_style.get('color', '#CCCCCC')}'>{expression.translation[i-2]}</font>")
                    srt_content.append("")
        
        return "\n".join(srt_content)
    
    def _format_timestamp(self, seconds: float) -> str:
        """
        Format timestamp for SRT
        
        Args:
            seconds: Time in seconds
            
        Returns:
            str: Formatted timestamp (HH:MM:SS,mmm)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    def _render_with_ffmpeg(
        self,
        video_path: str,
        srt_path: str,
        output_path: str,
        expression_text: str
    ) -> str:
        """
        Render subtitles with FFmpeg
        
        Args:
            video_path: Input video path
            srt_path: SRT file path
            output_path: Output video path
            expression_text: Expression text for styling
            
        Returns:
            str: Path to rendered video
        """
        # Get styling configuration
        font_size = self.default_style.get('font_size', 24)
        font_color = self.default_style.get('color', '#FFFFFF')
        background_color = self.default_style.get('background_color', '#000000')
        highlight_color = self.expression_style.get('color', '#FFD700')
        
        # FFmpeg command with subtitle styling
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vf', f"subtitles={srt_path}:force_style='FontSize={font_size},PrimaryColour={font_color},BackColour={background_color},OutlineColour={highlight_color}'",
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-movflags', '+faststart',
            '-y',
            output_path
        ]
        
        logger.info(f"Rendering subtitles for expression: {expression_text}")
        logger.debug(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
        
        try:
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=300  # 5 minute timeout
            )
        except subprocess.CalledProcessError as e:
            raise SubtitleRenderingError(
                f"FFmpeg subtitle rendering failed: {e.stderr}",
                expression=expression_text,
                file_path=video_path
            )
        except subprocess.TimeoutExpired:
            raise SubtitleRenderingError(
                "FFmpeg subtitle rendering timeout",
                expression=expression_text,
                file_path=video_path
            )
        
        # Verify output file
        if not Path(output_path).exists() or Path(output_path).stat().st_size == 0:
            raise SubtitleRenderingError(
                "Output file not created or empty",
                expression=expression_text,
                file_path=video_path
            )
        
        logger.info(f"Successfully rendered subtitles: {output_path}")
        return output_path
    
    def render_burn_in_subtitles(
        self,
        video_path: str,
        srt_path: str,
        output_path: str,
        style_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render burn-in subtitles (hardcoded)
        
        Args:
            video_path: Input video path
            srt_path: SRT file path
            output_path: Output video path
            style_config: Optional style configuration
            
        Returns:
            str: Path to video with burn-in subtitles
        """
        if style_config is None:
            style_config = self.default_style
        
        # FFmpeg command for burn-in subtitles
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vf', f"subtitles={srt_path}:force_style='FontSize={style_config.get('font_size', 24)},PrimaryColour={style_config.get('color', '#FFFFFF')}'",
            '-c:v', 'libx264',
            '-c:a', 'copy',  # Copy audio without re-encoding
            '-y',
            output_path
        ]
        
        logger.info(f"Rendering burn-in subtitles")
        
        try:
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=300
            )
        except subprocess.CalledProcessError as e:
            raise SubtitleRenderingError(
                f"FFmpeg burn-in rendering failed: {e.stderr}",
                file_path=video_path
            )
        
        return output_path
    
    def create_srt_file(
        self,
        expression: ExpressionAnalysis,
        aligned_expression: AlignedExpression,
        output_path: str
    ) -> str:
        """
        Create SRT file for expression
        
        Args:
            expression: Expression analysis
            aligned_expression: Aligned expression with timestamps
            output_path: Output SRT file path
            
        Returns:
            str: Path to created SRT file
        """
        try:
            srt_content = self._create_srt_content(expression, aligned_expression)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            logger.info(f"Created SRT file: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to create SRT file: {e}")
            raise SubtitleRenderingError(
                f"SRT file creation failed: {str(e)}",
                expression=expression.expression,
                file_path=output_path
            )
    
    def get_subtitle_info(self, expression: ExpressionAnalysis) -> Dict[str, Any]:
        """
        Get subtitle rendering information
        
        Args:
            expression: Expression analysis
            
        Returns:
            Dict with subtitle information
        """
        return {
            'expression': expression.expression,
            'translation': expression.expression_translation,
            'default_style': self.default_style,
            'expression_style': self.expression_style,
            'output_dir': str(self.output_dir)
        }
