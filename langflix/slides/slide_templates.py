"""
Slide templates for LangFlix educational slides.

This module provides template management for different types of educational slides,
including expression slides, usage examples, cultural notes, and grammar explanations.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from enum import Enum
import logging
from langflix import settings

logger = logging.getLogger(__name__)


class SlideType(Enum):
    """Slide template types"""
    EXPRESSION = "expression"
    USAGE = "usage"
    CULTURAL = "cultural"
    GRAMMAR = "grammar"
    PRONUNCIATION = "pronunciation"
    SIMILAR = "similar"


@dataclass
class SlideTemplate:
    """Slide template configuration"""
    template_type: SlideType
    background_color: str
    text_color: str
    font_family: str
    font_size: int
    title_font_size: int
    layout: Dict[str, Any]
    margins: Dict[str, int]
    spacing: Dict[str, int]


class SlideTemplates:
    """Manage slide templates"""
    
    def __init__(self):
        """Initialize with default templates"""
        self.templates = self._create_default_templates()
        self.config = settings.get_expression_config().get('slides', {})
    
    def _create_default_templates(self) -> Dict[SlideType, SlideTemplate]:
        """Create default slide templates"""
        templates = {}
        
        # Expression slide template
        templates[SlideType.EXPRESSION] = SlideTemplate(
            template_type=SlideType.EXPRESSION,
            background_color="#1a1a1a",
            text_color="#ffffff",
            font_family="DejaVu Sans",
            font_size=48,
            title_font_size=72,
            layout={
                'title_position': (960, 200),
                'subtitle_position': (960, 300),
                'content_position': (960, 500),
                'alignment': 'center'
            },
            margins={'top': 100, 'bottom': 100, 'left': 100, 'right': 100},
            spacing={'line': 20, 'paragraph': 40}
        )
        
        # Usage examples template
        templates[SlideType.USAGE] = SlideTemplate(
            template_type=SlideType.USAGE,
            background_color="#2d2d2d",
            text_color="#ffffff",
            font_family="DejaVu Sans",
            font_size=36,
            title_font_size=56,
            layout={
                'title_position': (960, 150),
                'content_position': (960, 400),
                'alignment': 'left'
            },
            margins={'top': 80, 'bottom': 80, 'left': 150, 'right': 150},
            spacing={'line': 15, 'paragraph': 30}
        )
        
        # Cultural notes template
        templates[SlideType.CULTURAL] = SlideTemplate(
            template_type=SlideType.CULTURAL,
            background_color="#1e3a5f",
            text_color="#ffffff",
            font_family="DejaVu Sans",
            font_size=32,
            title_font_size=48,
            layout={
                'title_position': (960, 200),
                'content_position': (960, 400),
                'alignment': 'center'
            },
            margins={'top': 100, 'bottom': 100, 'left': 120, 'right': 120},
            spacing={'line': 18, 'paragraph': 36}
        )
        
        # Grammar notes template
        templates[SlideType.GRAMMAR] = SlideTemplate(
            template_type=SlideType.GRAMMAR,
            background_color="#3d1a1a",
            text_color="#ffffff",
            font_family="DejaVu Sans",
            font_size=34,
            title_font_size=52,
            layout={
                'title_position': (960, 180),
                'content_position': (960, 420),
                'alignment': 'left'
            },
            margins={'top': 90, 'bottom': 90, 'left': 130, 'right': 130},
            spacing={'line': 16, 'paragraph': 32}
        )
        
        # Pronunciation template
        templates[SlideType.PRONUNCIATION] = SlideTemplate(
            template_type=SlideType.PRONUNCIATION,
            background_color="#1a3d1a",
            text_color="#ffffff",
            font_family="DejaVu Sans",
            font_size=42,
            title_font_size=64,
            layout={
                'title_position': (960, 250),
                'content_position': (960, 450),
                'alignment': 'center'
            },
            margins={'top': 120, 'bottom': 120, 'left': 100, 'right': 100},
            spacing={'line': 22, 'paragraph': 44}
        )
        
        # Similar expressions template
        templates[SlideType.SIMILAR] = SlideTemplate(
            template_type=SlideType.SIMILAR,
            background_color="#3d3d1a",
            text_color="#ffffff",
            font_family="DejaVu Sans",
            font_size=38,
            title_font_size=58,
            layout={
                'title_position': (960, 180),
                'content_position': (960, 400),
                'alignment': 'center'
            },
            margins={'top': 100, 'bottom': 100, 'left': 110, 'right': 110},
            spacing={'line': 20, 'paragraph': 40}
        )
        
        return templates
    
    def get_template(self, slide_type: SlideType) -> SlideTemplate:
        """
        Get template for slide type
        
        Args:
            slide_type: Type of slide
            
        Returns:
            SlideTemplate: Template configuration
        """
        if slide_type not in self.templates:
            logger.warning(f"Template not found for {slide_type}, using default")
            return self.templates[SlideType.EXPRESSION]
        
        return self.templates[slide_type]
    
    def get_custom_template(self, slide_type: SlideType) -> SlideTemplate:
        """
        Get custom template from configuration
        
        Args:
            slide_type: Type of slide
            
        Returns:
            SlideTemplate: Custom template or default
        """
        template_config = self.config.get('templates', {}).get(slide_type.value, {})
        
        if not template_config:
            return self.get_template(slide_type)
        
        # Create custom template from configuration
        default_template = self.get_template(slide_type)
        
        return SlideTemplate(
            template_type=slide_type,
            background_color=template_config.get('background_color', default_template.background_color),
            text_color=template_config.get('text_color', default_template.text_color),
            font_family=template_config.get('font_family', default_template.font_family),
            font_size=template_config.get('font_size', default_template.font_size),
            title_font_size=template_config.get('title_font_size', default_template.title_font_size),
            layout=template_config.get('layout', default_template.layout),
            margins=template_config.get('margins', default_template.margins),
            spacing=template_config.get('spacing', default_template.spacing)
        )
    
    def get_all_templates(self) -> Dict[SlideType, SlideTemplate]:
        """
        Get all available templates
        
        Returns:
            Dict[SlideType, SlideTemplate]: All templates
        """
        return self.templates.copy()
    
    def create_custom_template(
        self,
        slide_type: SlideType,
        background_color: str,
        text_color: str,
        font_family: str = "DejaVu Sans",
        font_size: int = 36,
        title_font_size: int = 56,
        layout: Optional[Dict[str, Any]] = None,
        margins: Optional[Dict[str, int]] = None,
        spacing: Optional[Dict[str, int]] = None
    ) -> SlideTemplate:
        """
        Create custom template
        
        Args:
            slide_type: Type of slide
            background_color: Background color
            text_color: Text color
            font_family: Font family
            font_size: Font size
            title_font_size: Title font size
            layout: Layout configuration
            margins: Margin configuration
            spacing: Spacing configuration
            
        Returns:
            SlideTemplate: Custom template
        """
        default_template = self.get_template(slide_type)
        
        return SlideTemplate(
            template_type=slide_type,
            background_color=background_color,
            text_color=text_color,
            font_family=font_family,
            font_size=font_size,
            title_font_size=title_font_size,
            layout=layout or default_template.layout,
            margins=margins or default_template.margins,
            spacing=spacing or default_template.spacing
        )
    
    def get_template_info(self, slide_type: SlideType) -> Dict[str, Any]:
        """
        Get template information
        
        Args:
            slide_type: Type of slide
            
        Returns:
            Dict with template information
        """
        template = self.get_template(slide_type)
        
        return {
            'type': slide_type.value,
            'background_color': template.background_color,
            'text_color': template.text_color,
            'font_family': template.font_family,
            'font_size': template.font_size,
            'title_font_size': template.title_font_size,
            'layout': template.layout,
            'margins': template.margins,
            'spacing': template.spacing
        }
    
    def validate_template(self, template: SlideTemplate) -> bool:
        """
        Validate template configuration
        
        Args:
            template: Template to validate
            
        Returns:
            bool: True if valid
        """
        try:
            # Check required fields
            if not template.background_color or not template.text_color:
                return False
            
            if template.font_size <= 0 or template.title_font_size <= 0:
                return False
            
            # Check layout
            if not template.layout or 'title_position' not in template.layout:
                return False
            
            # Check margins
            if not template.margins or any(m < 0 for m in template.margins.values()):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Template validation failed: {e}")
            return False
