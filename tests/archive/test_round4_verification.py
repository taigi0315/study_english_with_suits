"""
Unit tests for Round 4 changes:
1. Prompt v7 adoption
2. Spanish font fix on macOS (Apple SD Gothic Neo)
3. Pipeline optimization (skip translation service)
"""

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import os
import platform

# Imports
from langflix import settings
from langflix.config.font_utils import get_font_file_for_language
from langflix.main import LangFlixPipeline

class TestRound4Settings(unittest.TestCase):
    """Verify settings updates"""
    
    def test_default_template_is_v7(self):
        """Ensure default template is set to v7"""
        # We need to ensure we are testing the default, so might need to clear env vars or config cache if any
        # Assuming settings.get_template_file() reads from config fresh or we trust it logic
        template_file = settings.get_template_file()
        self.assertEqual(template_file, 'expression_analysis_prompt.txt')

class TestRound4FontUtils(unittest.TestCase):
    """Verify Font Utils updates for Spanish on macOS"""

    @patch('platform.system')
    @patch('os.path.exists')
    def test_spanish_font_on_darwin(self, mock_exists, mock_system):
        """Test that Spanish language on macOS prefers AppleSDGothicNeo"""
        mock_system.return_value = 'Darwin'
        
        # When checking for AppleSDGothicNeo, return True
        def side_effect(path):
            if "AppleSDGothicNeo" in str(path):
                return True
            return False
        mock_exists.side_effect = side_effect
        
        font_path = get_font_file_for_language('es')
        self.assertIn("AppleSDGothicNeo", font_path)

    @patch('platform.system')
    def test_spanish_font_on_linux(self, mock_system):
        """Test that Spanish language on non-macOS does NOT force AppleSDGothicNeo"""
        mock_system.return_value = 'Linux'
        
        # Should fall back to standard logic (e.g. settings or default fallback)
        # We assume standard logic returns something else (like Arial or configured font)
        # We just verify it's NOT AppleSDGothicNeo unless explicitly configured in settings which isn't default
        font_path = get_font_file_for_language('es')
        # It's possible it returns None or a different path depending on environment
        # But crucially, our special "Darwin" branch shouldn't trigger.
        if font_path:
            self.assertNotIn("AppleSDGothicNeo", font_path)

class TestRound4PipelineOptimization(unittest.TestCase):
    """Verify Pipeline Optimization (Skip Translation)"""

    @patch('langflix.main.TranslationService')
    @patch('langflix.main.ExpressionService')
    @patch('langflix.main.VideoFactory')
    @patch('langflix.main.VideoProcessor')
    @patch('langflix.main.SubtitleService')
    def test_skip_translation_when_single_target_matches(
        self,
        MockSubtitleService, 
        MockVideoProcessor, 
        MockVideoFactory, 
        MockExpressionService, 
        MockTranslationService
    ):
        """
        If target_languages=['es'] and we analyzed in 'es', 
        TranslationService.translate should NOT be called.
        """
        pipeline = LangFlixPipeline(
            subtitle_file="sub.srt",
            video_dir=".",
            output_dir="out",
            language_code="es",
            series_name="Show",
            episode_name="Ep",
            target_languages=['es'], # Match language_code
            video_file="video.mp4"
        )
        
        # Set mocks on the instance
        pipeline.expression_service = MockExpressionService.return_value
        pipeline.translation_service = MockTranslationService.return_value
        pipeline.video_factory = MockVideoFactory.return_value
        pipeline.subtitle_service = MockSubtitleService.return_value
        pipeline.media_scanner = MagicMock() 

        # Mock ExpressionService.analyze result
        mock_expressions = [MagicMock(expression="Hola", expression_translation="Hello")] 
        pipeline.expression_service.analyze.return_value = mock_expressions
        
        # Mock other steps
        pipeline.subtitle_service.parse.return_value = []
        pipeline.subtitle_service.chunk.return_value = []
        pipeline.video_factory.create_educational_videos.return_value = (None, None)
        pipeline._init_db_media = MagicMock(return_value=None)
        pipeline._update_progress = MagicMock()
        pipeline._save_expressions_to_db = MagicMock()

        # RUN
        pipeline.run(max_expressions=1, dry_run=True, test_mode=True)
        
        # ASSERT
        pipeline.translation_service.translate.assert_not_called()
        self.assertIn('es', pipeline.translated_expressions)
        self.assertEqual(pipeline.translated_expressions['es'], mock_expressions)

    @patch('langflix.main.TranslationService')
    @patch('langflix.main.ExpressionService')
    @patch('langflix.main.VideoFactory')
    @patch('langflix.main.VideoProcessor')
    @patch('langflix.main.SubtitleService')
    def test_do_not_skip_translation_when_multiple_targets(
        self,
        MockSubtitleService, 
        MockVideoProcessor, 
        MockVideoFactory, 
        MockExpressionService, 
        MockTranslationService
    ):
        """
        If target_languages=['es', 'fr'], we MUST call translate for 'fr'.
        """
        pipeline = LangFlixPipeline(
            subtitle_file="sub.srt",
            video_dir=".",
            output_dir="out",
            language_code="es",
            series_name="Show",
            episode_name="Ep",
            target_languages=['es', 'fr'], # Multiple!
            video_file="video.mp4"
        )
        
        pipeline.expression_service = MockExpressionService.return_value
        pipeline.translation_service = MockTranslationService.return_value
        pipeline.video_factory = MockVideoFactory.return_value
        pipeline.subtitle_service = MockSubtitleService.return_value
        pipeline.media_scanner = MagicMock()

        mock_expressions = [MagicMock(expression="Hola")] 
        pipeline.expression_service.analyze.return_value = mock_expressions
        
        pipeline.subtitle_service.parse.return_value = []
        pipeline.subtitle_service.chunk.return_value = []
        pipeline.video_factory.create_educational_videos.return_value = (None, None)
        pipeline._init_db_media = MagicMock(return_value=None)
        pipeline._update_progress = MagicMock()

        # RUN
        pipeline.run(max_expressions=1, dry_run=True, test_mode=True)
        
        # ASSERT
        pipeline.translation_service.translate.assert_called_once()


if __name__ == '__main__':
    unittest.main()
