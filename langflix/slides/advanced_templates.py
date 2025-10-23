"""
Advanced slide templates for LangFlix Expression-Based Learning Feature.

This module provides:
- Interactive slide templates
- Animation support
- Custom branding
- Template inheritance
- Dynamic content adaptation
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import math

from langflix.slides.slide_templates import BaseSlideTemplate
from langflix.slides.slide_generator import SlideContent

logger = logging.getLogger(__name__)

@dataclass
class AnimationConfig:
    """Animation configuration for slides"""
    fade_in_duration: float = 0.5
    fade_out_duration: float = 0.5
    slide_duration: float = 3.0
    transition_type: str = "fade"  # fade, slide, zoom
    loop_animation: bool = False

@dataclass
class BrandingConfig:
    """Branding configuration for slides"""
    logo_path: Optional[str] = None
    brand_colors: List[str] = None
    font_family: str = "Arial"
    brand_style: str = "modern"  # modern, classic, playful, professional
    
    def __post_init__(self):
        if self.brand_colors is None:
            self.brand_colors = ["#1a1a1a", "#ffffff", "#ffd700"]

class InteractiveExpressionTemplate(BaseSlideTemplate):
    """Interactive expression template with animations"""
    
    def __init__(self, slide_size: Tuple[int, int], config: Dict[str, Any]):
        super().__init__(slide_size, config)
        self.animation_config = AnimationConfig()
        self.branding_config = BrandingConfig()
    
    def render(self, content: SlideContent) -> Image.Image:
        """Render interactive expression slide"""
        img = Image.new('RGB', (self.width, self.height), self.background_color)
        draw = ImageDraw.Draw(img)
        
        # Create gradient background
        self._draw_gradient_background(draw)
        
        # Add animated elements
        self._draw_animated_expression(draw, content)
        self._draw_animated_translation(draw, content)
        self._draw_animated_examples(draw, content)
        
        # Add branding elements
        self._draw_branding_elements(draw)
        
        return img
    
    def _draw_gradient_background(self, draw: ImageDraw.ImageDraw):
        """Draw gradient background"""
        # Create gradient effect
        for y in range(self.height):
            ratio = y / self.height
            r = int(26 + (255 - 26) * ratio)  # Dark to light
            g = int(26 + (255 - 26) * ratio)
            b = int(26 + (255 - 26) * ratio)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))
    
    def _draw_animated_expression(self, draw: ImageDraw.ImageDraw, content: SlideContent):
        """Draw animated expression text"""
        title_font = self._get_font(self.title_font_size)
        
        # Expression with glow effect
        expression_text = content.expression_text
        x, y = self.width // 2, self.height // 3
        
        # Draw glow effect
        for offset in range(5, 0, -1):
            glow_color = (255, 255, 0, 50 - offset * 10)
            self._draw_text_with_glow(
                draw, expression_text, (x, y), title_font, glow_color, offset
            )
        
        # Draw main text
        self._draw_text_multiline(
            draw, expression_text, (x, y), title_font, self.text_color,
            align='center', max_width=self.width - 200
        )
    
    def _draw_animated_translation(self, draw: ImageDraw.ImageDraw, content: SlideContent):
        """Draw animated translation text"""
        text_font = self._get_font(self.font_size)
        
        translation_text = content.translation
        x, y = self.width // 2, self.height // 2
        
        # Draw with shadow effect
        shadow_offset = 3
        self._draw_text_multiline(
            draw, translation_text, (x + shadow_offset, y + shadow_offset),
            text_font, (0, 0, 0, 128), align='center', max_width=self.width - 200
        )
        
        self._draw_text_multiline(
            draw, translation_text, (x, y), text_font, self.text_color,
            align='center', max_width=self.width - 200
        )
    
    def _draw_animated_examples(self, draw: ImageDraw.ImageDraw, content: SlideContent):
        """Draw animated usage examples"""
        if not content.usage_examples:
            return
        
        text_font = self._get_font(self.font_size - 4)
        y_start = int(self.height * 0.6)
        
        for i, example in enumerate(content.usage_examples[:3]):  # Limit to 3 examples
            y = y_start + i * 40
            
            # Draw example with bullet point
            bullet_text = f"• {example}"
            self._draw_text_multiline(
                draw, bullet_text, (100, y), text_font, self.text_color,
                align='left', max_width=self.width - 200
            )
    
    def _draw_branding_elements(self, draw: ImageDraw.ImageDraw):
        """Draw branding elements"""
        # Draw corner accent
        accent_color = self.branding_config.brand_colors[2]  # Gold
        draw.rectangle([0, 0, 20, self.height], fill=accent_color)
        draw.rectangle([self.width - 20, 0, self.width, self.height], fill=accent_color)
    
    def _draw_text_with_glow(self, draw: ImageDraw.ImageDraw, text: str, pos: Tuple[int, int], 
                           font: ImageFont.FreeTypeFont, color: Tuple[int, int, int, int], offset: int):
        """Draw text with glow effect"""
        x, y = pos
        for dx in range(-offset, offset + 1):
            for dy in range(-offset, offset + 1):
                if dx * dx + dy * dy <= offset * offset:
                    draw.text((x + dx, y + dy), text, font=font, fill=color)

class CulturalNotesTemplate(BaseSlideTemplate):
    """Advanced cultural notes template with rich formatting"""
    
    def render(self, content: SlideContent) -> Image.Image:
        """Render cultural notes slide with rich formatting"""
        img = Image.new('RGB', (self.width, self.height), self.background_color)
        draw = ImageDraw.Draw(img)
        
        # Draw cultural background pattern
        self._draw_cultural_pattern(draw)
        
        # Draw title with cultural styling
        self._draw_cultural_title(draw)
        
        # Draw cultural content
        if content.cultural_notes:
            self._draw_cultural_content(draw, content.cultural_notes)
        
        return img
    
    def _draw_cultural_pattern(self, draw: ImageDraw.ImageDraw):
        """Draw cultural background pattern"""
        # Draw subtle cultural pattern
        pattern_color = (50, 50, 50)
        for i in range(0, self.width, 50):
            for j in range(0, self.height, 50):
                if (i + j) % 100 == 0:
                    draw.ellipse([i, j, i + 10, j + 10], fill=pattern_color)
    
    def _draw_cultural_title(self, draw: ImageDraw.ImageDraw):
        """Draw cultural title with special styling"""
        title_font = self._get_font(self.title_font_size)
        title_text = "Cultural Context"
        
        x, y = self.width // 2, 100
        
        # Draw title with cultural border
        self._draw_text_multiline(
            draw, title_text, (x, y), title_font, self.text_color,
            align='center'
        )
        
        # Draw decorative border
        border_color = (255, 215, 0)  # Gold
        draw.rectangle([x - 200, y - 20, x + 200, y + 60], outline=border_color, width=3)
    
    def _draw_cultural_content(self, draw: ImageDraw.ImageDraw, cultural_notes: str):
        """Draw cultural content with rich formatting"""
        text_font = self._get_font(self.font_size)
        
        # Split content into paragraphs
        paragraphs = cultural_notes.split('\n\n')
        
        y_start = 200
        for paragraph in paragraphs:
            self._draw_text_multiline(
                draw, paragraph, (100, y_start), text_font, self.text_color,
                align='left', max_width=self.width - 200
            )
            y_start += 150

class GrammarNotesTemplate(BaseSlideTemplate):
    """Advanced grammar notes template with structured layout"""
    
    def render(self, content: SlideContent) -> Image.Image:
        """Render grammar notes slide with structured layout"""
        img = Image.new('RGB', (self.width, self.height), self.background_color)
        draw = ImageDraw.Draw(img)
        
        # Draw grammar structure background
        self._draw_grammar_background(draw)
        
        # Draw grammar title
        self._draw_grammar_title(draw)
        
        # Draw grammar content
        if content.grammar_notes:
            self._draw_grammar_content(draw, content.grammar_notes)
        
        return img
    
    def _draw_grammar_background(self, draw: ImageDraw.ImageDraw):
        """Draw grammar structure background"""
        # Draw grammar tree-like structure
        tree_color = (100, 100, 100)
        
        # Main trunk
        draw.line([self.width // 2, 0, self.width // 2, self.height], fill=tree_color, width=3)
        
        # Branches
        for i in range(0, self.height, 100):
            draw.line([self.width // 2 - 50, i, self.width // 2 + 50, i], fill=tree_color, width=2)
    
    def _draw_grammar_title(self, draw: ImageDraw.ImageDraw):
        """Draw grammar title"""
        title_font = self._get_font(self.title_font_size)
        title_text = "Grammar Notes"
        
        x, y = self.width // 2, 80
        
        self._draw_text_multiline(
            draw, title_text, (x, y), title_font, self.text_color,
            align='center'
        )
    
    def _draw_grammar_content(self, draw: ImageDraw.ImageDraw, grammar_notes: str):
        """Draw grammar content with structured formatting"""
        text_font = self._get_font(self.font_size)
        
        # Format grammar notes with bullet points
        lines = grammar_notes.split('\n')
        y_start = 150
        
        for line in lines:
            if line.strip():
                # Add bullet point
                bullet_text = f"• {line.strip()}"
                self._draw_text_multiline(
                    draw, bullet_text, (120, y_start), text_font, self.text_color,
                    align='left', max_width=self.width - 240
                )
                y_start += 40

class PronunciationTemplate(BaseSlideTemplate):
    """Advanced pronunciation template with phonetic guides"""
    
    def render(self, content: SlideContent) -> Image.Image:
        """Render pronunciation slide with phonetic guides"""
        img = Image.new('RGB', (self.width, self.height), self.background_color)
        draw = ImageDraw.Draw(img)
        
        # Draw pronunciation background
        self._draw_pronunciation_background(draw)
        
        # Draw pronunciation title
        self._draw_pronunciation_title(draw)
        
        # Draw pronunciation content
        if content.pronunciation:
            self._draw_pronunciation_content(draw, content.pronunciation)
        
        return img
    
    def _draw_pronunciation_background(self, draw: ImageDraw.ImageDraw):
        """Draw pronunciation background with sound waves"""
        # Draw sound wave pattern
        wave_color = (80, 80, 80)
        for i in range(0, self.width, 20):
            amplitude = int(20 * math.sin(i * 0.1))
            draw.line([i, self.height // 2 - amplitude, i, self.height // 2 + amplitude], 
                     fill=wave_color, width=2)
    
    def _draw_pronunciation_title(self, draw: ImageDraw.ImageDraw):
        """Draw pronunciation title"""
        title_font = self._get_font(self.title_font_size)
        title_text = "Pronunciation Guide"
        
        x, y = self.width // 2, 100
        
        self._draw_text_multiline(
            draw, title_text, (x, y), title_font, self.text_color,
            align='center'
        )
    
    def _draw_pronunciation_content(self, draw: ImageDraw.ImageDraw, pronunciation: str):
        """Draw pronunciation content with phonetic formatting"""
        text_font = self._get_font(self.font_size)
        
        # Draw pronunciation with special formatting
        x, y = self.width // 2, self.height // 2
        
        # Draw phonetic symbols
        phonetic_text = f"/{pronunciation}/"
        self._draw_text_multiline(
            draw, phonetic_text, (x, y), text_font, (255, 255, 0),  # Yellow for phonetic
            align='center'
        )

class SimilarExpressionsTemplate(BaseSlideTemplate):
    """Advanced similar expressions template with network visualization"""
    
    def render(self, content: SlideContent) -> Image.Image:
        """Render similar expressions slide with network visualization"""
        img = Image.new('RGB', (self.width, self.height), self.background_color)
        draw = ImageDraw.Draw(img)
        
        # Draw network background
        self._draw_network_background(draw)
        
        # Draw similar expressions title
        self._draw_similar_title(draw)
        
        # Draw similar expressions content
        if content.similar_expressions:
            self._draw_similar_content(draw, content.similar_expressions)
        
        return img
    
    def _draw_network_background(self, draw: ImageDraw.ImageDraw):
        """Draw network background with connection lines"""
        # Draw network nodes and connections
        node_color = (120, 120, 120)
        
        # Central node
        center_x, center_y = self.width // 2, self.height // 2
        draw.ellipse([center_x - 20, center_y - 20, center_x + 20, center_y + 20], 
                    fill=node_color)
        
        # Surrounding nodes
        for angle in range(0, 360, 60):
            x = center_x + int(100 * math.cos(math.radians(angle)))
            y = center_y + int(100 * math.sin(math.radians(angle)))
            draw.ellipse([x - 15, y - 15, x + 15, y + 15], fill=node_color)
            
            # Draw connection line
            draw.line([center_x, center_y, x, y], fill=node_color, width=2)
    
    def _draw_similar_title(self, draw: ImageDraw.ImageDraw):
        """Draw similar expressions title"""
        title_font = self._get_font(self.title_font_size)
        title_text = "Similar Expressions"
        
        x, y = self.width // 2, 100
        
        self._draw_text_multiline(
            draw, title_text, (x, y), title_font, self.text_color,
            align='center'
        )
    
    def _draw_similar_content(self, draw: ImageDraw.ImageDraw, similar_expressions: List[str]):
        """Draw similar expressions content"""
        text_font = self._get_font(self.font_size)
        
        y_start = 200
        for i, expression in enumerate(similar_expressions[:5]):  # Limit to 5
            y = y_start + i * 50
            
            # Draw expression with connection line
            self._draw_text_multiline(
                draw, f"• {expression}", (150, y), text_font, self.text_color,
                align='left', max_width=self.width - 300
            )

class TemplateFactory:
    """Factory for creating advanced slide templates"""
    
    @staticmethod
    def create_template(template_type: str, slide_size: Tuple[int, int], 
                      config: Dict[str, Any]) -> BaseSlideTemplate:
        """Create advanced template based on type"""
        if template_type == 'interactive_expression':
            return InteractiveExpressionTemplate(slide_size, config)
        elif template_type == 'cultural_advanced':
            return CulturalNotesTemplate(slide_size, config)
        elif template_type == 'grammar_advanced':
            return GrammarNotesTemplate(slide_size, config)
        elif template_type == 'pronunciation_advanced':
            return PronunciationTemplate(slide_size, config)
        elif template_type == 'similar_advanced':
            return SimilarExpressionsTemplate(slide_size, config)
        else:
            # Fallback to base template
            from langflix.slides.slide_templates import ExpressionSlideTemplate
            return ExpressionSlideTemplate(slide_size, config)
    
    @staticmethod
    def get_available_templates() -> List[str]:
        """Get list of available advanced templates"""
        return [
            'interactive_expression',
            'cultural_advanced',
            'grammar_advanced',
            'pronunciation_advanced',
            'similar_advanced'
        ]

# Global template factory
_template_factory = TemplateFactory()

def get_advanced_template(template_type: str, slide_size: Tuple[int, int], 
                         config: Dict[str, Any]) -> BaseSlideTemplate:
    """Get advanced template instance"""
    return _template_factory.create_template(template_type, slide_size, config)

def get_available_advanced_templates() -> List[str]:
    """Get available advanced templates"""
    return _template_factory.get_available_templates()
