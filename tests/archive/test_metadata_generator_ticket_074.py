import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from langflix.youtube.metadata_generator import YouTubeMetadataGenerator
from langflix.youtube.video_manager import VideoMetadata

class TestYouTubeMetadataGeneratorTicket074(unittest.TestCase):
    def setUp(self):
        self.generator = YouTubeMetadataGenerator()
        self.metadata = VideoMetadata(
            path="/tmp/test_video.mp4",
            video_type="short",
            expression="Rise to the occasion",
            expression_translation="최선을 다하다",
            episode="Suits.S01E05",
            language="en",
            expressions_included=[],
            filename="test_video.mp4",
            size_mb=10.5,
            duration_seconds=60,
            resolution="1080p",
            format="mp4",
            created_at="2023-10-27T10:00:00"
        )

    def test_korean_metadata_format(self):
        """Test that Korean metadata follows the new format requirements"""
        result = self.generator.generate_metadata(self.metadata, target_language="Korean")
        
        # 1. Verify Title Format: {expression} | {translation} | from {episode}
        expected_title = "Rise to the occasion | 최선을 다하다 | from Suits.S01E05"
        self.assertEqual(result.title, expected_title, f"Title mismatch. Got: {result.title}")
        
        # 2. Verify Description Body
        description = result.description
        
        # Check Expression label (should be English "Expression")
        self.assertIn("Expression: Rise to the occasion", description)
        
        # Check Meaning label (should be localized "의미")
        self.assertIn("의미: 최선을 다하다", description)
        
        # Check Watch and Learn message (should be localized)
        self.assertIn("좋아하는 쇼에서 보고 배우세요!", description)
        
        # 3. Verify Tags (should be localized)
        # Note: Tags in the object are a list of strings
        self.assertTrue(any("영어학습" in tag for tag in result.tags), "Tags should contain localized keywords")
        self.assertTrue(any("수트" in tag for tag in result.tags), "Tags should contain localized keywords")

    def test_english_metadata_format(self):
        """Test that English metadata follows the new format requirements"""
        result = self.generator.generate_metadata(self.metadata, target_language="English")
        
        # 1. Verify Title Format
        expected_title = "Rise to the occasion | 최선을 다하다 | from Suits.S01E05"
        self.assertEqual(result.title, expected_title)
        
        # 2. Verify Description Body
        description = result.description
        self.assertIn("Expression: Rise to the occasion", description)
        self.assertIn("Meaning: 최선을 다하다", description) # English template uses "Meaning"
        self.assertIn("Watch and learn from your favorite show!", description)

if __name__ == '__main__':
    unittest.main()
