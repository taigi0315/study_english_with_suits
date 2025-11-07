"""
Integration tests for short format video preservation (TICKET-029)
"""
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

from langflix.core.video_editor import VideoEditor
from langflix.core.models import ExpressionAnalysis


class TestShortFormatPreservationIntegration(unittest.TestCase):
    """Integration tests for short format video preservation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.output_dir = self.temp_dir / "output" / "translations" / "ko" / "long_form_videos"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.video_editor = VideoEditor(
            output_dir=str(self.output_dir),
            language_code="ko",
            episode_name="Test_Episode"
        )
        
        # Create mock expression
        self.expression = Mock(spec=ExpressionAnalysis)
        self.expression.expression = "test expression"
        self.expression.context_start_time = "00:00:10.000"
        self.expression.expression_start_time = "00:00:12.000"
        self.expression.expression_end_time = "00:00:15.000"
        self.expression.expression_dialogue = "test expression dialogue"
        self.expression.expression_dialogue_translation = "test translation"
    
    def tearDown(self):
        """Clean up test fixtures"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_vstack_file_tracking_mechanism(self):
        """Test that vstack file tracking mechanism works correctly"""
        # This test verifies the tracking mechanism without needing full FFmpeg setup
        # Create a vstack file manually and track it
        vstack_file = self.output_dir / "temp_vstack_short_test_expression.mkv"
        vstack_file.write_bytes(b"fake vstack video")
        
        # Manually add to tracking (simulating what create_short_format_video does)
        self.video_editor.short_format_temp_files.append(vstack_file)
        self.video_editor._register_temp_file(vstack_file)
        
        # Verify it's tracked
        self.assertIn(vstack_file, self.video_editor.short_format_temp_files,
                     "Vstack file should be tracked in short_format_temp_files")
        
        # Verify it's registered in temp_manager
        self.assertIn(Path(vstack_file), self.video_editor.temp_manager.temp_files,
                     "Vstack file should be registered in temp_manager")
    
    def test_preservation_creates_expressions_directory(self):
        """Test that preservation creates expressions directory"""
        # Create a temp file to preserve
        vstack_file = self.output_dir / "temp_vstack_short_test_expression.mkv"
        vstack_file.write_bytes(b"fake video content")
        
        # Track the file
        self.video_editor.short_format_temp_files = [vstack_file]
        self.video_editor._register_temp_file(vstack_file)
        
        # Preserve files
        self.video_editor._cleanup_temp_files(preserve_short_format=True)
        
        # Check expressions directory exists
        expressions_dir = self.video_editor.short_videos_dir / "expressions"
        self.assertTrue(expressions_dir.exists(), "Expressions directory should be created")
        self.assertTrue(expressions_dir.is_dir(), "Expressions should be a directory")
    
    def test_preserved_file_has_correct_name(self):
        """Test that preserved file has correct naming (expression_{name}.mkv)"""
        # Create a temp file to preserve
        vstack_file = self.output_dir / "temp_vstack_short_test_expression.mkv"
        vstack_file.write_bytes(b"fake video content")
        
        # Track the file
        self.video_editor.short_format_temp_files = [vstack_file]
        self.video_editor._register_temp_file(vstack_file)
        
        # Preserve files
        self.video_editor._cleanup_temp_files(preserve_short_format=True)
        
        # Check preserved file has correct name
        expressions_dir = self.video_editor.short_videos_dir / "expressions"
        preserved_file = expressions_dir / "expression_test_expression.mkv"
        self.assertTrue(preserved_file.exists(), 
                       f"Preserved file should exist at {preserved_file}")
        self.assertEqual(preserved_file.name, "expression_test_expression.mkv",
                        "Preserved file should have correct naming")
    
    def test_long_form_cleanup_still_deletes_files(self):
        """Test that long form cleanup still deletes temp files"""
        # Create a temp file
        temp_file = self.output_dir / "temp_long_form_file.mkv"
        temp_file.write_bytes(b"fake content")
        
        # Register it
        self.video_editor._register_temp_file(temp_file)
        
        # Clean up without preservation (long form behavior)
        self.video_editor._cleanup_temp_files(preserve_short_format=False)
        
        # File should be deleted
        self.assertFalse(temp_file.exists(), "Temp file should be deleted for long form")
    
    def test_preserved_file_not_in_temp_manager(self):
        """Test that preserved files are removed from temp_manager"""
        # Create a temp file to preserve
        vstack_file = self.output_dir / "temp_vstack_short_test.mkv"
        vstack_file.write_bytes(b"fake content")
        
        # Track and register
        self.video_editor.short_format_temp_files = [vstack_file]
        self.video_editor._register_temp_file(vstack_file)
        
        # Verify it's in temp_manager
        self.assertIn(Path(vstack_file), self.video_editor.temp_manager.temp_files)
        
        # Preserve files
        self.video_editor._cleanup_temp_files(preserve_short_format=True)
        
        # File should be removed from temp_manager
        self.assertNotIn(Path(vstack_file), self.video_editor.temp_manager.temp_files,
                        "Preserved file should be removed from temp_manager")
    
    def test_multiple_expressions_preserved_separately(self):
        """Test that multiple expression videos are preserved separately"""
        # Create multiple vstack files
        vstack1 = self.output_dir / "temp_vstack_short_expression1.mkv"
        vstack2 = self.output_dir / "temp_vstack_short_expression2.mkv"
        
        for f in [vstack1, vstack2]:
            f.write_bytes(b"fake content")
        
        # Track both
        self.video_editor.short_format_temp_files = [vstack1, vstack2]
        for f in [vstack1, vstack2]:
            self.video_editor._register_temp_file(f)
        
        # Preserve files
        self.video_editor._cleanup_temp_files(preserve_short_format=True)
        
        # Check both are preserved
        expressions_dir = self.video_editor.short_videos_dir / "expressions"
        preserved1 = expressions_dir / "expression_expression1.mkv"
        preserved2 = expressions_dir / "expression_expression2.mkv"
        
        self.assertTrue(preserved1.exists(), "First expression should be preserved")
        self.assertTrue(preserved2.exists(), "Second expression should be preserved")


if __name__ == '__main__':
    unittest.main()

