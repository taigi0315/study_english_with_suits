"""
Educational slide generation package for LangFlix.

This package handles the generation of educational slides for expressions,
including content generation, templates, and rendering.
"""

from .slide_generator import SlideContentGenerator, SlideContent
from .slide_templates import SlideTemplates, SlideTemplate, SlideType
from .slide_renderer import SlideRenderer

__all__ = [
    'SlideContentGenerator',
    'SlideContent',
    'SlideTemplates',
    'SlideTemplate',
    'SlideType',
    'SlideRenderer'
]
