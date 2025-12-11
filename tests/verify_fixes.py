import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langflix.core.video_processor import VideoProcessor

class TestFixes(unittest.TestCase):
    def setUp(self):
        self.processor = VideoProcessor("assets/media")
        
    @patch('langflix.core.video_processor.VideoProcessor._extract_clip_encode')
    @patch('langflix.core.video_processor.VideoProcessor._extract_clip_copy')
    @patch('langflix.settings.get_clip_extraction_strategy')
    def test_extract_clip_defaults_to_encode(self, mock_settings, mock_copy, mock_encode):
        # Setup: Settings returns None (default behavior)
        mock_settings.return_value = None
        mock_encode.return_value = True
        
        # Action
        self.processor.extract_clip(Path("video.mkv"), "00:00:10.000", "00:00:20.000", Path("out.mkv"))
        
        # Assert
        mock_encode.assert_called_once()
        mock_copy.assert_not_called()
        print("\n✅ Sync Fix Verified: extract_clip defaults to encode when settings is None")

    @patch('langflix.core.video_processor.VideoProcessor._extract_clip_encode')
    @patch('langflix.core.video_processor.VideoProcessor._extract_clip_copy')
    def test_extract_clip_explicit_encode(self, mock_copy, mock_encode):
        # Setup
        mock_encode.return_value = True
        
        # Action: Explicit strategy='encode'
        self.processor.extract_clip(
            Path("video.mkv"), 
            "00:00:10.000", "00:00:20.000", 
            Path("out.mkv"),
            strategy='encode'
        )
        
        # Assert
        mock_encode.assert_called_once()
        mock_copy.assert_not_called()
        print("✅ Sync Fix Verified: extract_clip honors strategy='encode'")

if __name__ == '__main__':
    unittest.main()
