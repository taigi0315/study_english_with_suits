"""
Integration tests for short video context duration limits (TICKET-025)
Tests that LLM respects ≤ 40 second context duration limit for short videos
"""
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to the path so we can import langflix
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langflix.utils.prompts import get_prompt_for_chunk
from langflix import settings


class TestShortVideoContextDurationLimits(unittest.TestCase):
    """Test short video context duration limits in prompt"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.sample_chunk = [
            {
                'start_time': '00:05:30,000',
                'end_time': '00:05:35,000',
                'text': 'I need to figure this out.'
            },
            {
                'start_time': '00:05:35,000',
                'end_time': '00:05:40,000',
                'text': 'What do you think?'
            },
            {
                'start_time': '00:05:40,000',
                'end_time': '00:05:45,000',
                'text': 'Let me know your thoughts.'
            }
        ]
    
    def test_prompt_includes_short_video_context_duration_guidance(self):
        """Test that prompt includes short video context duration guidance"""
        prompt = get_prompt_for_chunk(self.sample_chunk, 'intermediate', 'ko')
        
        # Verify short video guidance is present
        self.assertIn('SHORT VIDEO CONTEXT DURATION', prompt)
        self.assertIn('≤ 40 seconds', prompt)
        self.assertIn('≤ 60 seconds total', prompt)
        self.assertIn('~20 seconds reserved for expression slides', prompt)
    
    def test_prompt_includes_context_duration_guidance_for_regular_videos(self):
        """Test that prompt includes context duration guidance for regular videos"""
        prompt = get_prompt_for_chunk(self.sample_chunk, 'intermediate', 'ko')
        
        # Verify regular video guidance is present
        self.assertIn('25-45 seconds for regular videos', prompt)
        self.assertIn('or ≤ 40 seconds for short videos', prompt)
    
    def test_prompt_includes_context_duration_in_final_checklist(self):
        """Test that final checklist includes context duration guidance"""
        prompt = get_prompt_for_chunk(self.sample_chunk, 'intermediate', 'ko')
        
        # Verify final checklist includes context duration
        self.assertIn('Context is 25-45 seconds for regular videos', prompt)
        self.assertIn('or ≤ 40 seconds for short videos', prompt)
    
    def test_prompt_prioritizes_40_second_contexts_for_short_videos(self):
        """Test that prompt prioritizes ≤ 40 second contexts for short videos"""
        prompt = get_prompt_for_chunk(self.sample_chunk, 'intermediate', 'ko')
        
        # Verify prioritization guidance
        self.assertIn('prioritize segments that are ≤ 40 seconds', prompt)
    
    @patch('langflix.utils.prompts.settings')
    @patch('langflix.utils.prompts.LanguageConfig')
    def test_prompt_uses_config_max_expressions_per_context(self, mock_lang_config, mock_settings):
        """Test that prompt uses max_expressions_per_context from config"""
        # Setup mocks
        mock_settings.DEFAULT_LANGUAGE_LEVEL = 'intermediate'
        mock_settings.LANGUAGE_LEVELS = {
            'intermediate': {'description': 'Intermediate level'}
        }
        mock_settings.get_min_expressions_per_chunk.return_value = 1
        mock_settings.get_max_expressions_per_chunk.return_value = 3
        mock_settings.get_max_expressions_per_context.return_value = 3
        mock_settings.get_show_name.return_value = 'Test Show'
        mock_settings.get_template_file.return_value = 'expression_analysis_prompt_v4.txt'
        
        mock_lang_config.get_config.return_value = {'prompt_language': 'Korean'}
        
        # Load actual template
        from langflix.utils.prompts import _load_prompt_template
        template = _load_prompt_template()
        
        # Verify template includes max_expressions_per_context placeholder
        self.assertIn('{max_expressions_per_context}', template)
        
        # Generate prompt
        prompt = get_prompt_for_chunk(self.sample_chunk, 'intermediate', 'ko')
        
        # Verify placeholder is replaced with actual value
        self.assertNotIn('{max_expressions_per_context}', prompt)
        self.assertIn('1-3', prompt)  # Should have actual value
    
    def test_prompt_expression_count_guidance_quality_over_quantity(self):
        """Test that prompt emphasizes quality over quantity for expressions"""
        prompt = get_prompt_for_chunk(self.sample_chunk, 'intermediate', 'ko')
        
        # Verify quality over quantity guidance
        self.assertIn('Quality over quantity', prompt)
        self.assertIn('Do NOT force yourself', prompt)
        self.assertIn('BEST expressions', prompt)
    
    def test_prompt_context_duration_guidance_in_step_3(self):
        """Test that Step 3 includes context duration guidance"""
        prompt = get_prompt_for_chunk(self.sample_chunk, 'intermediate', 'ko')
        
        # Verify Step 3 includes context duration guidance
        self.assertIn('25-45 seconds for regular videos', prompt)
        self.assertIn('or ≤ 40 seconds for short videos', prompt)
    
    @patch('langflix.utils.prompts.settings')
    @patch('langflix.utils.prompts.LanguageConfig')
    def test_prompt_respects_max_expressions_per_context_config(self, mock_lang_config, mock_settings):
        """Test that prompt respects max_expressions_per_context config value"""
        # Test with different config values
        for max_exprs in [1, 2, 3]:
            mock_settings.DEFAULT_LANGUAGE_LEVEL = 'intermediate'
            mock_settings.LANGUAGE_LEVELS = {
                'intermediate': {'description': 'Intermediate level'}
            }
            mock_settings.get_min_expressions_per_chunk.return_value = 1
            mock_settings.get_max_expressions_per_chunk.return_value = 3
            mock_settings.get_max_expressions_per_context.return_value = max_exprs
            mock_settings.get_show_name.return_value = 'Test Show'
            mock_settings.get_template_file.return_value = 'expression_analysis_prompt_v4.txt'
            
            mock_lang_config.get_config.return_value = {'prompt_language': 'Korean'}
            
            prompt = get_prompt_for_chunk(self.sample_chunk, 'intermediate', 'ko')
            
            # Verify the config value is used in prompt
            self.assertIn(f'1-{max_exprs}', prompt)
            self.assertNotIn('{max_expressions_per_context}', prompt)


if __name__ == '__main__':
    unittest.main()

