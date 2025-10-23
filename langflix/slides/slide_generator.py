"""
Educational slide content generation for LangFlix.

This module provides functionality to generate educational content for slides
using the Gemini API for expression-based learning.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import logging
from langflix.llm.gemini_client import GeminiClient
from langflix.core.models import ExpressionAnalysis
from langflix import settings

logger = logging.getLogger(__name__)


@dataclass
class SlideContent:
    """Educational slide content"""
    expression_text: str
    translation: str
    pronunciation: str
    difficulty_level: int
    category: str
    usage_examples: List[str]
    cultural_notes: Optional[str]
    grammar_notes: Optional[str]
    similar_expressions: List[str]
    context_sentences: List[str]


class SlideContentGenerator:
    """Generate educational content for slides"""
    
    def __init__(self, gemini_client: GeminiClient):
        """
        Initialize slide content generator
        
        Args:
            gemini_client: Gemini API client
        """
        self.gemini_client = gemini_client
        self.slide_config = settings.get_expression_config().get('slides', {})
    
    async def generate_slide_content(
        self,
        expression: ExpressionAnalysis
    ) -> SlideContent:
        """
        Generate educational content for slide
        
        Args:
            expression: Expression analysis data
            
        Returns:
            SlideContent: Generated slide content
        """
        try:
            # Create prompt for slide content generation
            prompt = self._create_slide_prompt(expression)
            
            # Generate content using Gemini
            response = await self.gemini_client.generate_content(
                prompt,
                temperature=0.7,
                max_tokens=1000
            )
            
            # Parse response into SlideContent
            slide_content = self._parse_slide_response(response, expression)
            
            logger.info(f"Generated slide content for: {expression.expression}")
            return slide_content
            
        except Exception as e:
            logger.error(f"Failed to generate slide content: {e}")
            # Return fallback content
            return self._create_fallback_content(expression)
    
    def _create_slide_prompt(self, expression: ExpressionAnalysis) -> str:
        """
        Create prompt for slide content generation
        
        Args:
            expression: Expression analysis
            
        Returns:
            str: Generated prompt
        """
        prompt = f"""
Create educational content for the English expression: "{expression.expression}"

Context:
- Translation: {expression.expression_translation}
- Difficulty: {getattr(expression, 'difficulty', 5)}/10
- Category: {getattr(expression, 'category', 'general')}
- Educational Value: {getattr(expression, 'educational_value', '')}

Please provide the following information in a structured format:

1. PRONUNCIATION: Provide phonetic pronunciation using IPA symbols
2. USAGE_EXAMPLES: Provide 3-4 practical usage examples with context
3. CULTURAL_NOTES: Explain any cultural context or background
4. GRAMMAR_NOTES: Explain grammar rules or patterns
5. SIMILAR_EXPRESSIONS: List 2-3 similar expressions or synonyms
6. CONTEXT_SENTENCES: Provide 2-3 example sentences showing natural usage

Format the response as:
PRONUNCIATION: [phonetic pronunciation]
USAGE_EXAMPLES:
- [example 1]
- [example 2]
- [example 3]
CULTURAL_NOTES: [cultural context]
GRAMMAR_NOTES: [grammar explanation]
SIMILAR_EXPRESSIONS: [similar expressions]
CONTEXT_SENTENCES:
- [sentence 1]
- [sentence 2]
"""
        return prompt
    
    def _parse_slide_response(self, response: str, expression: ExpressionAnalysis) -> SlideContent:
        """
        Parse Gemini response into SlideContent
        
        Args:
            response: Gemini API response
            expression: Original expression analysis
            
        Returns:
            SlideContent: Parsed slide content
        """
        # Initialize with defaults
        pronunciation = ""
        usage_examples = []
        cultural_notes = ""
        grammar_notes = ""
        similar_expressions = []
        context_sentences = []
        
        # Parse response line by line
        lines = response.strip().split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for section headers
            if line.startswith('PRONUNCIATION:'):
                pronunciation = line.replace('PRONUNCIATION:', '').strip()
                current_section = 'pronunciation'
            elif line.startswith('USAGE_EXAMPLES:'):
                current_section = 'usage_examples'
            elif line.startswith('CULTURAL_NOTES:'):
                cultural_notes = line.replace('CULTURAL_NOTES:', '').strip()
                current_section = 'cultural_notes'
            elif line.startswith('GRAMMAR_NOTES:'):
                grammar_notes = line.replace('GRAMMAR_NOTES:', '').strip()
                current_section = 'grammar_notes'
            elif line.startswith('SIMILAR_EXPRESSIONS:'):
                similar_expressions = line.replace('SIMILAR_EXPRESSIONS:', '').strip().split(', ')
                current_section = 'similar_expressions'
            elif line.startswith('CONTEXT_SENTENCES:'):
                current_section = 'context_sentences'
            elif line.startswith('- '):
                # Handle bullet points
                content = line[2:].strip()
                if current_section == 'usage_examples':
                    usage_examples.append(content)
                elif current_section == 'context_sentences':
                    context_sentences.append(content)
        
        return SlideContent(
            expression_text=expression.expression,
            translation=expression.expression_translation,
            pronunciation=pronunciation,
            difficulty_level=getattr(expression, 'difficulty', 5),
            category=getattr(expression, 'category', 'general'),
            usage_examples=usage_examples,
            cultural_notes=cultural_notes,
            grammar_notes=grammar_notes,
            similar_expressions=similar_expressions,
            context_sentences=context_sentences
        )
    
    def _create_fallback_content(self, expression: ExpressionAnalysis) -> SlideContent:
        """
        Create fallback content when generation fails
        
        Args:
            expression: Expression analysis
            
        Returns:
            SlideContent: Fallback content
        """
        return SlideContent(
            expression_text=expression.expression,
            translation=expression.expression_translation,
            pronunciation="[Pronunciation not available]",
            difficulty_level=getattr(expression, 'difficulty', 5),
            category=getattr(expression, 'category', 'general'),
            usage_examples=[
                f"Example: {expression.expression}",
                f"Usage: {expression.expression}"
            ],
            cultural_notes="Cultural context not available",
            grammar_notes="Grammar notes not available",
            similar_expressions=getattr(expression, 'similar_expressions', []),
            context_sentences=[
                f"Context: {expression.expression}",
                f"Example: {expression.expression}"
            ]
        )
    
    async def generate_multiple_slides(
        self,
        expressions: List[ExpressionAnalysis]
    ) -> List[SlideContent]:
        """
        Generate slide content for multiple expressions
        
        Args:
            expressions: List of expression analyses
            
        Returns:
            List[SlideContent]: Generated slide contents
        """
        slide_contents = []
        
        for expression in expressions:
            try:
                content = await self.generate_slide_content(expression)
                slide_contents.append(content)
            except Exception as e:
                logger.error(f"Failed to generate content for {expression.expression}: {e}")
                # Add fallback content
                fallback = self._create_fallback_content(expression)
                slide_contents.append(fallback)
        
        return slide_contents
    
    def get_content_summary(self, slide_content: SlideContent) -> Dict[str, Any]:
        """
        Get summary of slide content
        
        Args:
            slide_content: Slide content
            
        Returns:
            Dict with content summary
        """
        return {
            'expression': slide_content.expression_text,
            'translation': slide_content.translation,
            'difficulty': slide_content.difficulty_level,
            'category': slide_content.category,
            'examples_count': len(slide_content.usage_examples),
            'has_cultural_notes': bool(slide_content.cultural_notes),
            'has_grammar_notes': bool(slide_content.grammar_notes),
            'similar_count': len(slide_content.similar_expressions),
            'context_count': len(slide_content.context_sentences)
        }
