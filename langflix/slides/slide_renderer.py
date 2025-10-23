"""
Educational slide rendering for LangFlix.

This module provides functionality to render educational slides using PIL
with configurable templates and styling.
"""

from pathlib import Path
from typing import Tuple, List, Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont
import logging
from .slide_templates import SlideTemplate, SlideType
from .slide_generator import SlideContent

logger = logging.getLogger(__name__)


class SlideRenderer:
    """Render educational slides"""
    
    def __init__(self, output_dir: Path):
        """
        Initialize slide renderer
        
        Args:
            output_dir: Output directory for rendered slides
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Default font paths (will be updated based on system)
        self.font_paths = self._get_font_paths()
    
    def _get_font_paths(self) -> Dict[str, str]:
        """Get available font paths"""
        font_paths = {}
        
        # Common font paths
        common_paths = [
            "/System/Library/Fonts/",  # macOS
            "/usr/share/fonts/",       # Linux
            "C:/Windows/Fonts/",       # Windows
            "/Library/Fonts/",          # macOS user fonts
        ]
        
        # Try to find DejaVu Sans
        for path in common_paths:
            dejavu_path = Path(path) / "DejaVuSans.ttf"
            if dejavu_path.exists():
                font_paths['DejaVu Sans'] = str(dejavu_path)
                break
        
        # Fallback to system default
        if 'DejaVu Sans' not in font_paths:
            font_paths['DejaVu Sans'] = None  # Will use default font
        
        return font_paths
    
    def render_slide(
        self,
        template: SlideTemplate,
        content: SlideContent,
        output_path: str,
        size: Tuple[int, int] = (1920, 1080)
    ) -> str:
        """
        Render slide with content
        
        Args:
            template: Slide template configuration
            content: Slide content
            output_path: Output image path
            size: Slide dimensions (width, height)
            
        Returns:
            str: Path to rendered slide
        """
        try:
            # Create image
            image = Image.new('RGB', size, template.background_color)
            draw = ImageDraw.Draw(image)
            
            # Load fonts
            title_font = self._get_font(template.font_family, template.title_font_size)
            content_font = self._get_font(template.font_family, template.font_size)
            
            # Render based on template type
            if template.template_type == SlideType.EXPRESSION:
                self._render_expression_slide(draw, template, content, title_font, content_font, size)
            elif template.template_type == SlideType.USAGE:
                self._render_usage_slide(draw, template, content, title_font, content_font, size)
            elif template.template_type == SlideType.CULTURAL:
                self._render_cultural_slide(draw, template, content, title_font, content_font, size)
            elif template.template_type == SlideType.GRAMMAR:
                self._render_grammar_slide(draw, template, content, title_font, content_font, size)
            elif template.template_type == SlideType.PRONUNCIATION:
                self._render_pronunciation_slide(draw, template, content, title_font, content_font, size)
            elif template.template_type == SlideType.SIMILAR:
                self._render_similar_slide(draw, template, content, title_font, content_font, size)
            else:
                self._render_default_slide(draw, template, content, title_font, content_font, size)
            
            # Save image
            image.save(output_path, 'PNG', quality=95)
            logger.info(f"Rendered slide: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to render slide: {e}")
            raise
    
    def _get_font(self, font_family: str, font_size: int) -> ImageFont.ImageFont:
        """Get font with fallback"""
        try:
            if font_family in self.font_paths and self.font_paths[font_family]:
                return ImageFont.truetype(self.font_paths[font_family], font_size)
            else:
                return ImageFont.load_default()
        except Exception:
            return ImageFont.load_default()
    
    def _render_expression_slide(
        self,
        draw: ImageDraw.Draw,
        template: SlideTemplate,
        content: SlideContent,
        title_font: ImageFont.ImageFont,
        content_font: ImageFont.ImageFont,
        size: Tuple[int, int]
    ):
        """Render expression slide"""
        width, height = size
        
        # Title (expression)
        title_pos = template.layout['title_position']
        draw.text(title_pos, content.expression_text, font=title_font, fill=template.text_color, anchor='mm')
        
        # Subtitle (translation)
        subtitle_pos = template.layout['subtitle_position']
        draw.text(subtitle_pos, content.translation, font=content_font, fill=template.text_color, anchor='mm')
        
        # Content (pronunciation)
        content_pos = template.layout['content_position']
        if content.pronunciation:
            draw.text(content_pos, f"Pronunciation: {content.pronunciation}", font=content_font, fill=template.text_color, anchor='mm')
    
    def _render_usage_slide(
        self,
        draw: ImageDraw.Draw,
        template: SlideTemplate,
        content: SlideContent,
        title_font: ImageFont.ImageFont,
        content_font: ImageFont.ImageFont,
        size: Tuple[int, int]
    ):
        """Render usage examples slide"""
        width, height = size
        
        # Title
        title_pos = template.layout['title_position']
        draw.text(title_pos, "Usage Examples", font=title_font, fill=template.text_color, anchor='mm')
        
        # Usage examples
        content_pos = template.layout['content_position']
        y_offset = content_pos[1]
        
        for i, example in enumerate(content.usage_examples[:4]):  # Limit to 4 examples
            text = f"• {example}"
            draw.text((content_pos[0], y_offset), text, font=content_font, fill=template.text_color, anchor='lm')
            y_offset += template.spacing['line'] + 20
    
    def _render_cultural_slide(
        self,
        draw: ImageDraw.Draw,
        template: SlideTemplate,
        content: SlideContent,
        title_font: ImageFont.ImageFont,
        content_font: ImageFont.ImageFont,
        size: Tuple[int, int]
    ):
        """Render cultural notes slide"""
        width, height = size
        
        # Title
        title_pos = template.layout['title_position']
        draw.text(title_pos, "Cultural Notes", font=title_font, fill=template.text_color, anchor='mm')
        
        # Cultural notes
        content_pos = template.layout['content_position']
        if content.cultural_notes:
            # Wrap text
            wrapped_text = self._wrap_text(content.cultural_notes, content_font, width - template.margins['left'] - template.margins['right'])
            draw.text(content_pos, wrapped_text, font=content_font, fill=template.text_color, anchor='mm')
    
    def _render_grammar_slide(
        self,
        draw: ImageDraw.Draw,
        template: SlideTemplate,
        content: SlideContent,
        title_font: ImageFont.ImageFont,
        content_font: ImageFont.ImageFont,
        size: Tuple[int, int]
    ):
        """Render grammar notes slide"""
        width, height = size
        
        # Title
        title_pos = template.layout['title_position']
        draw.text(title_pos, "Grammar Notes", font=title_font, fill=template.text_color, anchor='mm')
        
        # Grammar notes
        content_pos = template.layout['content_position']
        if content.grammar_notes:
            # Wrap text
            wrapped_text = self._wrap_text(content.grammar_notes, content_font, width - template.margins['left'] - template.margins['right'])
            draw.text(content_pos, wrapped_text, font=content_font, fill=template.text_color, anchor='mm')
    
    def _render_pronunciation_slide(
        self,
        draw: ImageDraw.Draw,
        template: SlideTemplate,
        content: SlideContent,
        title_font: ImageFont.ImageFont,
        content_font: ImageFont.ImageFont,
        size: Tuple[int, int]
    ):
        """Render pronunciation slide"""
        width, height = size
        
        # Title
        title_pos = template.layout['title_position']
        draw.text(title_pos, "Pronunciation", font=title_font, fill=template.text_color, anchor='mm')
        
        # Pronunciation
        content_pos = template.layout['content_position']
        if content.pronunciation:
            draw.text(content_pos, content.pronunciation, font=content_font, fill=template.text_color, anchor='mm')
    
    def _render_similar_slide(
        self,
        draw: ImageDraw.Draw,
        template: SlideTemplate,
        content: SlideContent,
        title_font: ImageFont.ImageFont,
        content_font: ImageFont.ImageFont,
        size: Tuple[int, int]
    ):
        """Render similar expressions slide"""
        width, height = size
        
        # Title
        title_pos = template.layout['title_position']
        draw.text(title_pos, "Similar Expressions", font=title_font, fill=template.text_color, anchor='mm')
        
        # Similar expressions
        content_pos = template.layout['content_position']
        y_offset = content_pos[1]
        
        for expression in content.similar_expressions[:5]:  # Limit to 5 expressions
            text = f"• {expression}"
            draw.text((content_pos[0], y_offset), text, font=content_font, fill=template.text_color, anchor='lm')
            y_offset += template.spacing['line'] + 20
    
    def _render_default_slide(
        self,
        draw: ImageDraw.Draw,
        template: SlideTemplate,
        content: SlideContent,
        title_font: ImageFont.ImageFont,
        content_font: ImageFont.ImageFont,
        size: Tuple[int, int]
    ):
        """Render default slide"""
        width, height = size
        
        # Title
        title_pos = template.layout['title_position']
        draw.text(title_pos, content.expression_text, font=title_font, fill=template.text_color, anchor='mm')
        
        # Content
        content_pos = template.layout['content_position']
        draw.text(content_pos, content.translation, font=content_font, fill=template.text_color, anchor='mm')
    
    def _wrap_text(self, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
        """Wrap text to fit within max_width"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = font.getbbox(test_line)
            if bbox[2] - bbox[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return '\n'.join(lines)
    
    def render_multiple_slides(
        self,
        templates: List[SlideTemplate],
        contents: List[SlideContent],
        output_dir: str,
        size: Tuple[int, int] = (1920, 1080)
    ) -> List[str]:
        """
        Render multiple slides
        
        Args:
            templates: List of slide templates
            contents: List of slide contents
            output_dir: Output directory
            size: Slide dimensions
            
        Returns:
            List[str]: Paths to rendered slides
        """
        rendered_paths = []
        
        for i, (template, content) in enumerate(zip(templates, contents)):
            output_path = Path(output_dir) / f"slide_{i+1:02d}_{template.template_type.value}.png"
            
            try:
                rendered_path = self.render_slide(template, content, str(output_path), size)
                rendered_paths.append(rendered_path)
            except Exception as e:
                logger.error(f"Failed to render slide {i+1}: {e}")
        
        return rendered_paths
    
    def get_render_info(self, template: SlideTemplate, content: SlideContent) -> Dict[str, Any]:
        """
        Get rendering information
        
        Args:
            template: Slide template
            content: Slide content
            
        Returns:
            Dict with rendering information
        """
        return {
            'template_type': template.template_type.value,
            'background_color': template.background_color,
            'text_color': template.text_color,
            'font_family': template.font_family,
            'font_size': template.font_size,
            'expression': content.expression_text,
            'translation': content.translation,
            'has_pronunciation': bool(content.pronunciation),
            'has_cultural_notes': bool(content.cultural_notes),
            'has_grammar_notes': bool(content.grammar_notes),
            'examples_count': len(content.usage_examples),
            'similar_count': len(content.similar_expressions)
        }
