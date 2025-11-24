"""
Adaptive subtitle rendering system for LangFlix Expression-Based Learning Feature.

This module provides:
- Automatic subtitle positioning
- Dynamic font sizing
- Color contrast optimization
- Multi-language subtitle support
- Context-aware styling
"""

import logging
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import subprocess
import json

from langflix.media.subtitle_renderer import SubtitleRenderer
from langflix.core.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)

@dataclass
class VideoDimensions:
    """Video dimensions and properties"""
    width: int
    height: int
    aspect_ratio: float
    safe_area_top: int
    safe_area_bottom: int
    safe_area_left: int
    safe_area_right: int

@dataclass
class SubtitleContext:
    """Context information for subtitle styling"""
    expression_text: str
    scene_type: str  # dialogue, action, narration, etc.
    character_count: int
    reading_speed: float  # characters per second
    language: str
    difficulty_level: int

@dataclass
class AdaptiveStyle:
    """Adaptive subtitle style configuration"""
    font_size: int
    font_family: str
    primary_color: str
    outline_color: str
    background_color: str
    position_x: int
    position_y: int
    max_width: int
    line_height: int
    outline_width: int
    shadow_offset: Tuple[int, int]
    animation_duration: float

class AdaptiveSubtitleRenderer(SubtitleRenderer):
    """Advanced subtitle renderer with adaptive styling"""
    
    def __init__(self, output_dir: Path):
        """
        Initialize adaptive subtitle renderer
        
        Args:
            output_dir: Output directory for rendered subtitles
        """
        super().__init__(output_dir)
        self.cache_manager = get_cache_manager()
        
        # Style templates for different contexts
        self.style_templates = self._initialize_style_templates()
        
        logger.info("AdaptiveSubtitleRenderer initialized")
    
    def _initialize_style_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize style templates for different contexts"""
        return {
            'dialogue': {
                'font_size': 24,
                'font_family': 'Arial',
                'primary_color': '#FFFFFF',
                'outline_color': '#000000',
                'background_color': 'transparent',
                'position': 'bottom',
                'max_width_ratio': 0.8,
                'line_height_ratio': 1.2,
                'outline_width': 2,
                'shadow_offset': (2, 2)
            },
            'action': {
                'font_size': 28,
                'font_family': 'Arial Bold',
                'primary_color': '#FFFF00',
                'outline_color': '#000000',
                'background_color': 'transparent',
                'position': 'center',
                'max_width_ratio': 0.9,
                'line_height_ratio': 1.3,
                'outline_width': 3,
                'shadow_offset': (3, 3)
            },
            'narration': {
                'font_size': 22,
                'font_family': 'Arial',
                'primary_color': '#CCCCCC',
                'outline_color': '#000000',
                'background_color': 'transparent',
                'position': 'bottom',
                'max_width_ratio': 0.7,
                'line_height_ratio': 1.1,
                'outline_width': 1,
                'shadow_offset': (1, 1)
            },
            'expression_highlight': {
                'font_size': 32,
                'font_family': 'Arial Bold',
                'primary_color': '#FFD700',
                'outline_color': '#000000',
                'background_color': 'rgba(0,0,0,0.7)',
                'position': 'center',
                'max_width_ratio': 0.8,
                'line_height_ratio': 1.4,
                'outline_width': 3,
                'shadow_offset': (4, 4)
            }
        }
    
    def analyze_video_dimensions(self, video_path: str) -> VideoDimensions:
        """Analyze video dimensions and safe areas"""
        try:
            # Use ffprobe to get video information
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_streams', '-show_format', video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            # Find video stream
            video_stream = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            if not video_stream:
                raise ValueError("No video stream found")
            
            width = int(video_stream.get('width', 1920))
            height = int(video_stream.get('height', 1080))
            aspect_ratio = width / height
            
            # Calculate safe areas (10% margin)
            safe_area_top = int(height * 0.1)
            safe_area_bottom = int(height * 0.1)
            safe_area_left = int(width * 0.1)
            safe_area_right = int(width * 0.1)
            
            return VideoDimensions(
                width=width,
                height=height,
                aspect_ratio=aspect_ratio,
                safe_area_top=safe_area_top,
                safe_area_bottom=safe_area_bottom,
                safe_area_left=safe_area_left,
                safe_area_right=safe_area_right
            )
            
        except Exception as e:
            logger.warning(f"Failed to analyze video dimensions: {e}")
            # Return default dimensions
            return VideoDimensions(
                width=1920, height=1080, aspect_ratio=16/9,
                safe_area_top=108, safe_area_bottom=108,
                safe_area_left=192, safe_area_right=192
            )
    
    def analyze_subtitle_context(self, subtitle_content: str, expression_text: str = "") -> SubtitleContext:
        """Analyze subtitle context for adaptive styling"""
        # Count characters
        character_count = len(subtitle_content)
        
        # Estimate reading speed (characters per second)
        # Typical reading speed: 3-5 characters per second for subtitles
        reading_speed = min(max(character_count / 3.0, 1.0), 5.0)
        
        # Determine scene type based on content
        scene_type = self._classify_scene_type(subtitle_content, expression_text)
        
        # Determine language
        language = self._detect_language(subtitle_content)
        
        # Estimate difficulty level
        difficulty_level = self._estimate_difficulty(subtitle_content)
        
        return SubtitleContext(
            expression_text=expression_text,
            scene_type=scene_type,
            character_count=character_count,
            reading_speed=reading_speed,
            language=language,
            difficulty_level=difficulty_level
        )
    
    def _classify_scene_type(self, content: str, expression_text: str) -> str:
        """Classify the type of scene based on content"""
        content_lower = content.lower()
        
        # Check for action indicators
        action_indicators = ['!', 'bang', 'crash', 'explosion', 'fight', 'run', 'jump']
        if any(indicator in content_lower for indicator in action_indicators):
            return 'action'
        
        # Check for dialogue indicators
        dialogue_indicators = ['"', "'", 'said', 'told', 'asked', 'replied']
        if any(indicator in content_lower for indicator in dialogue_indicators):
            return 'dialogue'
        
        # Check for narration indicators
        narration_indicators = ['meanwhile', 'later', 'suddenly', 'finally', 'eventually']
        if any(indicator in content_lower for indicator in narration_indicators):
            return 'narration'
        
        # Check if it's an expression highlight
        if expression_text and expression_text.lower() in content_lower:
            return 'expression_highlight'
        
        # Default to dialogue
        return 'dialogue'
    
    def _detect_language(self, content: str) -> str:
        """Detect language of subtitle content"""
        # Simple language detection based on character patterns
        # This is a basic implementation - could be enhanced with proper language detection
        
        # Check for Korean characters
        if any('\uac00' <= char <= '\ud7af' for char in content):
            return 'ko'
        
        # Check for Chinese characters
        if any('\u4e00' <= char <= '\u9fff' for char in content):
            return 'zh'
        
        # Check for Japanese characters
        if any('\u3040' <= char <= '\u309f' or '\u30a0' <= char <= '\u30ff' for char in content):
            return 'ja'
        
        # Default to English
        return 'en'
    
    def _estimate_difficulty(self, content: str) -> int:
        """Estimate difficulty level of content (1-10)"""
        # Simple difficulty estimation based on word length and complexity
        words = content.split()
        if not words:
            return 5
        
        # Calculate average word length
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        # Calculate complexity based on punctuation and special characters
        special_chars = sum(1 for char in content if not char.isalnum() and char != ' ')
        complexity_ratio = special_chars / len(content) if content else 0
        
        # Estimate difficulty (1-10)
        difficulty = min(max(int(avg_word_length * 0.5 + complexity_ratio * 20), 1), 10)
        
        return difficulty
    
    def generate_adaptive_style(
        self,
        video_dimensions: VideoDimensions,
        context: SubtitleContext,
        base_style: Optional[Dict[str, Any]] = None
    ) -> AdaptiveStyle:
        """Generate adaptive style based on video and context"""
        # Get base template for scene type
        template = self.style_templates.get(context.scene_type, self.style_templates['dialogue'])
        
        # Override with base style if provided
        if base_style:
            template.update(base_style)
        
        # Calculate adaptive font size
        font_size = self._calculate_adaptive_font_size(
            template['font_size'], video_dimensions, context
        )
        
        # Calculate adaptive positioning
        position_x, position_y = self._calculate_adaptive_position(
            video_dimensions, context, template['position']
        )
        
        # Calculate adaptive dimensions
        max_width = int(video_dimensions.width * template['max_width_ratio'])
        line_height = int(font_size * template['line_height_ratio'])
        
        # Calculate adaptive colors
        primary_color, outline_color, background_color = self._calculate_adaptive_colors(
            template, context, video_dimensions
        )
        
        return AdaptiveStyle(
            font_size=font_size,
            font_family=template['font_family'],
            primary_color=primary_color,
            outline_color=outline_color,
            background_color=background_color,
            position_x=position_x,
            position_y=position_y,
            max_width=max_width,
            line_height=line_height,
            outline_width=template['outline_width'],
            shadow_offset=template['shadow_offset'],
            animation_duration=0.3
        )
    
    def _calculate_adaptive_font_size(
        self,
        base_font_size: int,
        video_dimensions: VideoDimensions,
        context: SubtitleContext
    ) -> int:
        """Calculate adaptive font size based on context"""
        # Base font size
        font_size = base_font_size
        
        # Adjust for video resolution
        resolution_factor = min(video_dimensions.width / 1920, video_dimensions.height / 1080)
        font_size = int(font_size * resolution_factor)
        
        # Adjust for reading speed (slower reading = larger font)
        if context.reading_speed < 2.0:  # Very slow reading
            font_size = int(font_size * 1.2)
        elif context.reading_speed > 4.0:  # Very fast reading
            font_size = int(font_size * 0.9)
        
        # Adjust for difficulty level
        if context.difficulty_level > 7:  # High difficulty
            font_size = int(font_size * 1.1)
        elif context.difficulty_level < 4:  # Low difficulty
            font_size = int(font_size * 0.95)
        
        # Adjust for character count (more characters = smaller font)
        if context.character_count > 50:
            font_size = int(font_size * 0.9)
        elif context.character_count < 20:
            font_size = int(font_size * 1.1)
        
        # Ensure reasonable bounds
        return max(min(font_size, 48), 12)
    
    def _calculate_adaptive_position(
        self,
        video_dimensions: VideoDimensions,
        context: SubtitleContext,
        position_preference: str
    ) -> Tuple[int, int]:
        """Calculate adaptive subtitle position"""
        if position_preference == 'bottom':
            x = video_dimensions.width // 2
            y = video_dimensions.height - video_dimensions.safe_area_bottom - 50
        elif position_preference == 'top':
            x = video_dimensions.width // 2
            y = video_dimensions.safe_area_top + 50
        elif position_preference == 'center':
            x = video_dimensions.width // 2
            y = video_dimensions.height // 2
        else:
            x = video_dimensions.width // 2
            y = video_dimensions.height - video_dimensions.safe_area_bottom - 50
        
        # Adjust for expression highlighting
        if context.scene_type == 'expression_highlight':
            y = video_dimensions.height // 2  # Center for expressions
        
        return x, y
    
    def _calculate_adaptive_colors(
        self,
        template: Dict[str, Any],
        context: SubtitleContext,
        video_dimensions: VideoDimensions
    ) -> Tuple[str, str, str]:
        """Calculate adaptive colors for better contrast"""
        primary_color = template['primary_color']
        outline_color = template['outline_color']
        background_color = template['background_color']
        
        # Adjust colors based on difficulty level
        if context.difficulty_level > 7:  # High difficulty - use high contrast
            if primary_color == '#FFFFFF':
                primary_color = '#FFFF00'  # Bright yellow for high contrast
        elif context.difficulty_level < 4:  # Low difficulty - use softer colors
            if primary_color == '#FFFFFF':
                primary_color = '#CCCCCC'  # Softer white
        
        # Adjust for scene type
        if context.scene_type == 'action':
            primary_color = '#FFFF00'  # Bright yellow for action
            outline_color = '#000000'  # Black outline
        elif context.scene_type == 'expression_highlight':
            primary_color = '#FFD700'  # Gold for expressions
            background_color = 'rgba(0,0,0,0.7)'  # Semi-transparent background
        
        return primary_color, outline_color, background_color
    
    async def render_adaptive_subtitles(
        self,
        video_path: str,
        subtitle_content: str,
        output_filename: str,
        expression_text: str = "",
        base_style: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render subtitles with adaptive styling
        
        Args:
            video_path: Path to input video
            subtitle_content: Subtitle content
            output_filename: Output filename
            expression_text: Expression text for highlighting
            base_style: Base style overrides
            
        Returns:
            Path to rendered video
        """
        # Analyze video and context
        video_dimensions = self.analyze_video_dimensions(video_path)
        context = self.analyze_subtitle_context(subtitle_content, expression_text)
        
        # Generate adaptive style
        adaptive_style = self.generate_adaptive_style(
            video_dimensions, context, base_style
        )
        
        # Convert adaptive style to ASS format
        ass_style = self._convert_adaptive_style_to_ass(adaptive_style)
        
        # Render with adaptive style
        return await self.render_subtitles(
            video_path, subtitle_content, output_filename, ass_style
        )
    
    def _convert_adaptive_style_to_ass(self, style: AdaptiveStyle) -> str:
        """Convert adaptive style to ASS format"""
        # Convert colors to ASS format
        primary_color = self._convert_color_to_ass(style.primary_color)
        outline_color = self._convert_color_to_ass(style.outline_color)
        background_color = self._convert_color_to_ass(style.background_color)
        
        # Build ASS style string
        ass_style = (
            f"Fontname={style.font_family},"
            f"Fontsize={style.font_size},"
            f"PrimaryColour={primary_color},"
            f"SecondaryColour={primary_color},"
            f"OutlineColour={outline_color},"
            f"BackColour={background_color},"
            f"Bold=0,"
            f"Italic=0,"
            f"Underline=0,"
            f"StrikeOut=0,"
            f"ScaleX=100,"
            f"ScaleY=100,"
            f"Spacing=0,"
            f"Angle=0,"
            f"BorderStyle=1,"
            f"Outline={style.outline_width},"
            f"Shadow={style.shadow_offset[0]},"
            f"Alignment=2,"
            f"MarginL={style.position_x - style.max_width // 2},"
            f"MarginR={style.position_x - style.max_width // 2},"
            f"MarginV={style.position_y}"
        )
        
        return ass_style
    
    def _convert_color_to_ass(self, hex_color: str) -> str:
        """Convert hex color to ASS format"""
        if hex_color.startswith('#'):
            hex_color = hex_color[1:]
        
        if len(hex_color) == 6:
            r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
            return f"&H{b}{g}{r}&"
        
        return "&HFFFFFF&"  # Default to white
    
    async def render_subtitles(
        self,
        video_path: str,
        subtitle_content: str,
        output_filename: str,
        style_string: str
    ) -> str:
        """Render subtitles with custom style string"""
        local_output_path = self.output_dir / output_filename
        temp_srt_path = self.output_dir / f"temp_{Path(output_filename).stem}.srt"
        
        try:
            # Write subtitle content to temporary SRT file
            with open(temp_srt_path, 'w', encoding='utf-8') as f:
                f.write(subtitle_content)
            
            # Get language-specific font
            from langflix.core.language_config import LanguageConfig
            font_path = LanguageConfig.get_font_path()  # Default font
            font_name = "Arial"  # Fallback font name
            
            # Try to determine font name from font path
            if font_path and font_path.endswith('.ttc'):
                if 'AppleSDGothicNeo' in font_path:
                    font_name = "Apple SD Gothic Neo"
                elif 'Hiragino' in font_path:
                    font_name = "Hiragino Sans"
                elif 'HelveticaNeue' in font_path:
                    font_name = "Helvetica Neue"
                else:
                    font_name = "Arial"
            
            # Get platform-specific fonts directory and font name
            from langflix.config.font_utils import get_fonts_dir, get_font_name_for_ffmpeg
            fonts_dir = get_fonts_dir()
            font_name = get_font_name_for_ffmpeg(font_path, None)
            
            # Build FFmpeg command with custom style and font configuration
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vf', f"subtitles='{temp_srt_path}':fontsdir={fonts_dir}:force_style='FontName={font_name},{style_string}'",
                '-c:a', 'copy',
                '-y',
                str(local_output_path)
            ]
            
            logger.info(f"Rendering adaptive subtitles: {output_filename}")
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
            
            return str(local_output_path)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg subtitle rendering failed: {e.stderr}")
            raise Exception(f"Subtitle rendering failed: {e.stderr}")
        finally:
            if temp_srt_path.exists():
                temp_srt_path.unlink()

# Global adaptive renderer instance
_adaptive_renderer: Optional[AdaptiveSubtitleRenderer] = None

def get_adaptive_renderer(output_dir: Path) -> AdaptiveSubtitleRenderer:
    """Get global adaptive subtitle renderer instance"""
    global _adaptive_renderer
    if _adaptive_renderer is None:
        _adaptive_renderer = AdaptiveSubtitleRenderer(output_dir)
    return _adaptive_renderer
