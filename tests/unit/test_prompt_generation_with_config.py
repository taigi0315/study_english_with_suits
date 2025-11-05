"""
Unit tests for prompt generation with config values (TICKET-025)
Tests that max_expressions_per_context is correctly passed to prompt template
"""
import unittest
from unittest.mock import patch, MagicMock
from langflix.utils.prompts import get_prompt_for_chunk


class TestPromptGenerationWithConfig(unittest.TestCase):
    """Test prompt generation includes max_expressions_per_context from config"""
    
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
            }
        ]
    
    @patch('langflix.utils.prompts.settings')
    @patch('langflix.utils.prompts.LanguageConfig')
    def test_prompt_includes_max_expressions_per_context_default(self, mock_lang_config, mock_settings):
        """Test that prompt includes default max_expressions_per_context (3)"""
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
        
        # Mock template file
        template_content = """Test prompt
Find 1-{max_expressions_per_context} expressions.
Context: {dialogues}
Level: {level_description}
"""
        
        with patch('langflix.utils.prompts._load_prompt_template', return_value=template_content):
            prompt = get_prompt_for_chunk(self.sample_chunk, 'intermediate', 'ko')
            
            # Verify max_expressions_per_context is included
            self.assertIn('1-3 expressions', prompt)
            self.assertNotIn('{max_expressions_per_context}', prompt)  # Should be replaced
    
    @patch('langflix.utils.prompts.settings')
    @patch('langflix.utils.prompts.LanguageConfig')
    def test_prompt_includes_max_expressions_per_context_custom(self, mock_lang_config, mock_settings):
        """Test that prompt includes custom max_expressions_per_context (2)"""
        # Setup mocks
        mock_settings.DEFAULT_LANGUAGE_LEVEL = 'intermediate'
        mock_settings.LANGUAGE_LEVELS = {
            'intermediate': {'description': 'Intermediate level'}
        }
        mock_settings.get_min_expressions_per_chunk.return_value = 1
        mock_settings.get_max_expressions_per_chunk.return_value = 2
        mock_settings.get_max_expressions_per_context.return_value = 2
        mock_settings.get_show_name.return_value = 'Test Show'
        mock_settings.get_template_file.return_value = 'expression_analysis_prompt_v4.txt'
        
        mock_lang_config.get_config.return_value = {'prompt_language': 'Korean'}
        
        # Mock template file
        template_content = """Test prompt
Find 1-{max_expressions_per_context} expressions.
Context: {dialogues}
"""
        
        with patch('langflix.utils.prompts._load_prompt_template', return_value=template_content):
            prompt = get_prompt_for_chunk(self.sample_chunk, 'intermediate', 'ko')
            
            # Verify max_expressions_per_context is included
            self.assertIn('1-2 expressions', prompt)
            self.assertNotIn('{max_expressions_per_context}', prompt)
    
    @patch('langflix.utils.prompts.settings')
    @patch('langflix.utils.prompts.LanguageConfig')
    def test_prompt_includes_short_video_guidance(self, mock_lang_config, mock_settings):
        """Test that prompt includes short video context duration guidance"""
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
        
        # Mock template file with short video guidance
        template_content = """Test prompt
**SHORT VIDEO CONTEXT DURATION (if applicable):**

For short videos (≤ 60 seconds total):
- Context must be ≤ 40 seconds
- Remaining ~20 seconds reserved for expression slides
"""
        
        with patch('langflix.utils.prompts._load_prompt_template', return_value=template_content):
            prompt = get_prompt_for_chunk(self.sample_chunk, 'intermediate', 'ko')
            
            # Verify short video guidance is present
            self.assertIn('SHORT VIDEO CONTEXT DURATION', prompt)
            self.assertIn('≤ 40 seconds', prompt)
            self.assertIn('≤ 60 seconds total', prompt)
    
    @patch('langflix.utils.prompts.settings')
    @patch('langflix.utils.prompts.LanguageConfig')
    def test_prompt_includes_expression_count_guidance(self, mock_lang_config, mock_settings):
        """Test that prompt includes expression count guidance with config value"""
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
        
        # Mock template file with expression count guidance
        template_content = """Test prompt
**EXPRESSION COUNT:**
- Find 1 to {max_expressions_per_context} expressions per context
- Do NOT force yourself to find {max_expressions_per_context} expressions
- Quality over quantity
"""
        
        with patch('langflix.utils.prompts._load_prompt_template', return_value=template_content):
            prompt = get_prompt_for_chunk(self.sample_chunk, 'intermediate', 'ko')
            
            # Verify expression count guidance is present with value
            self.assertIn('EXPRESSION COUNT', prompt)
            self.assertIn('1 to 3 expressions', prompt)
            self.assertIn('Do NOT force yourself to find 3 expressions', prompt)
            self.assertNotIn('{max_expressions_per_context}', prompt)
    
    @patch('langflix.utils.prompts.settings')
    @patch('langflix.utils.prompts.LanguageConfig')
    def test_prompt_validates_max_expressions_per_context_range(self, mock_lang_config, mock_settings):
        """Test that prompt generation validates max_expressions_per_context range (1-3)"""
        # Setup mocks
        mock_settings.DEFAULT_LANGUAGE_LEVEL = 'intermediate'
        mock_settings.LANGUAGE_LEVELS = {
            'intermediate': {'description': 'Intermediate level'}
        }
        mock_settings.get_min_expressions_per_chunk.return_value = 1
        mock_settings.get_max_expressions_per_chunk.return_value = 3
        mock_settings.get_show_name.return_value = 'Test Show'
        mock_settings.get_template_file.return_value = 'expression_analysis_prompt_v4.txt'
        
        mock_lang_config.get_config.return_value = {'prompt_language': 'Korean'}
        
        # Test with value below range (validation happens in get_prompt_for_chunk)
        # get_max_expressions_per_context() already validates, but get_prompt_for_chunk also validates
        # So we test that the validation in get_prompt_for_chunk works
        mock_settings.get_max_expressions_per_context.return_value = 0
        template_content = "Find 1-{max_expressions_per_context} expressions."
        
        with patch('langflix.utils.prompts._load_prompt_template', return_value=template_content):
            prompt = get_prompt_for_chunk(self.sample_chunk, 'intermediate', 'ko')
            # get_prompt_for_chunk validates and clamps to 3 (default) if value is outside range
            self.assertIn('1-3 expressions', prompt)
        
        # Test with value above range (should clamp to 3)
        mock_settings.get_max_expressions_per_context.return_value = 5
        template_content = "Find 1-{max_expressions_per_context} expressions."
        
        with patch('langflix.utils.prompts._load_prompt_template', return_value=template_content):
            prompt = get_prompt_for_chunk(self.sample_chunk, 'intermediate', 'ko')
            # get_prompt_for_chunk validates and clamps to 3 if value is outside range
            self.assertIn('1-3 expressions', prompt)
        
        # Test with valid value (should use as-is)
        mock_settings.get_max_expressions_per_context.return_value = 2
        template_content = "Find 1-{max_expressions_per_context} expressions."
        
        with patch('langflix.utils.prompts._load_prompt_template', return_value=template_content):
            prompt = get_prompt_for_chunk(self.sample_chunk, 'intermediate', 'ko')
            # Should use 2 without warning
            self.assertIn('1-2 expressions', prompt)
    
    @patch('langflix.utils.prompts.settings')
    @patch('langflix.utils.prompts.LanguageConfig')
    def test_prompt_includes_context_duration_guidance(self, mock_lang_config, mock_settings):
        """Test that prompt includes context duration guidance for short videos"""
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
        
        # Mock template file with context duration guidance
        template_content = """Test prompt
- ✓ Context is 25-45 seconds for regular videos (or ≤ 40 seconds for short videos)
"""
        
        with patch('langflix.utils.prompts._load_prompt_template', return_value=template_content):
            prompt = get_prompt_for_chunk(self.sample_chunk, 'intermediate', 'ko')
            
            # Verify context duration guidance is present
            self.assertIn('25-45 seconds for regular videos', prompt)
            self.assertIn('≤ 40 seconds for short videos', prompt)
    
    @patch('langflix.utils.prompts.settings')
    @patch('langflix.utils.prompts.LanguageConfig')
    def test_prompt_includes_final_checklist_with_max_expressions(self, mock_lang_config, mock_settings):
        """Test that final checklist includes max_expressions_per_context"""
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
        
        # Mock template file with final checklist
        template_content = """Test prompt
- ✓ 1-{max_expressions_per_context} expressions total (minimum 1, maximum {max_expressions_per_context})
"""
        
        with patch('langflix.utils.prompts._load_prompt_template', return_value=template_content):
            prompt = get_prompt_for_chunk(self.sample_chunk, 'intermediate', 'ko')
            
            # Verify final checklist includes max_expressions_per_context
            self.assertIn('1-3 expressions total (minimum 1, maximum 3)', prompt)
            self.assertNotIn('{max_expressions_per_context}', prompt)


if __name__ == '__main__':
    unittest.main()

