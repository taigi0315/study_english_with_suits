"""
Unit tests for VideoEditor cleanup and preservation logic (TICKET-029)
"""
import unittest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import tempfile
import shutil

from langflix.core.video_editor import VideoEditor
from langflix.core.models import ExpressionAnalysis


class TestVideoEditorCleanup(unittest.TestCase):
    """Test cleanup and preservation logic for short format videos"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.output_dir = self.temp_dir / "output"
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
    
    def test_short_format_temp_files_initialized(self):
        """Test that short_format_temp_files list is initialized"""
        self.assertTrue(hasattr(self.video_editor, 'short_format_temp_files'))
        self.assertEqual(self.video_editor.short_format_temp_files, [])
    
    def test_cleanup_preserves_short_format_files_when_flag_true(self):
        """Test that cleanup preserves short format files when preserve_short_format=True"""
        # Create a temp file to preserve
        preserved_file = self.output_dir / "temp_vstack_short_test.mkv"
        preserved_file.parent.mkdir(parents=True, exist_ok=True)
        preserved_file.write_bytes(b"fake video content")
        
        # Track the file
        self.video_editor.short_format_temp_files = [preserved_file]
        self.video_editor._register_temp_file(preserved_file)
        
        # Clean up with preservation
        self.video_editor._cleanup_temp_files(preserve_short_format=True)
        
        # File should be preserved (moved to expressions directory)
        expressions_dir = self.video_editor.short_videos_dir / "expressions"
        preserved_path = expressions_dir / "expression_test.mkv"
        self.assertTrue(preserved_path.exists(), f"Preserved file should exist at {preserved_path}")
        self.assertFalse(preserved_file.exists(), "Original temp file should be moved")
    
    def test_cleanup_deletes_files_when_flag_false(self):
        """Test that cleanup deletes all files when preserve_short_format=False"""
        # Create a temp file
        temp_file = self.output_dir / "temp_vstack_short_test.mkv"
        temp_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file.write_bytes(b"fake video content")
        
        # Track the file
        self.video_editor.short_format_temp_files = [temp_file]
        self.video_editor._register_temp_file(temp_file)
        
        # Clean up without preservation
        self.video_editor._cleanup_temp_files(preserve_short_format=False)
        
        # File should be deleted
        self.assertFalse(temp_file.exists(), "Temp file should be deleted")
        expressions_dir = self.video_editor.short_videos_dir / "expressions"
        self.assertFalse(expressions_dir.exists(), "Expressions directory should not exist")
    
    def test_preserve_short_format_files_renames_correctly(self):
        """Test that _preserve_short_format_files renames files correctly"""
        # Create temp files with different patterns
        vstack_file = self.output_dir / "temp_vstack_short_test_expression.mkv"
        expr_clip_file = self.output_dir / "temp_expr_clip_long_test_expression.mkv"
        expr_repeated_file = self.output_dir / "temp_expr_repeated_test_expression.mkv"
        
        for f in [vstack_file, expr_clip_file, expr_repeated_file]:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(b"fake content")
        
        files_to_preserve = {vstack_file, expr_clip_file, expr_repeated_file}
        self.video_editor._preserve_short_format_files(files_to_preserve)
        
        expressions_dir = self.video_editor.short_videos_dir / "expressions"
        
        # Check renamed files
        self.assertTrue((expressions_dir / "expression_test_expression.mkv").exists())
        self.assertTrue((expressions_dir / "expr_clip_test_expression.mkv").exists())
        self.assertTrue((expressions_dir / "expr_repeated_test_expression.mkv").exists())
    
    def test_preserve_short_format_files_creates_directory(self):
        """Test that _preserve_short_format_files creates expressions directory"""
        temp_file = self.output_dir / "temp_vstack_short_test.mkv"
        temp_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file.write_bytes(b"fake content")
        
        self.video_editor._preserve_short_format_files({temp_file})
        
        expressions_dir = self.video_editor.short_videos_dir / "expressions"
        self.assertTrue(expressions_dir.exists(), "Expressions directory should be created")
        self.assertTrue(expressions_dir.is_dir(), "Expressions should be a directory")
    
    def test_preserve_short_format_files_handles_missing_files(self):
        """Test that _preserve_short_format_files handles missing files gracefully"""
        missing_file = self.output_dir / "temp_vstack_short_nonexistent.mkv"
        
        # Should not raise an exception
        self.video_editor._preserve_short_format_files({missing_file})
        
        expressions_dir = self.video_editor.short_videos_dir / "expressions"
        # Directory may be created (mkdir with exist_ok=True), but no files should be preserved
        # The important thing is that no exception is raised
        if expressions_dir.exists():
            # If directory exists, it should be empty
            files_in_dir = list(expressions_dir.glob("*.mkv"))
            self.assertEqual(len(files_in_dir), 0, "No files should be preserved if file doesn't exist")
    
    def test_cleanup_removes_files_from_temp_manager(self):
        """Test that preserved files are removed from temp_manager before cleanup"""
        temp_file = self.output_dir / "temp_vstack_short_test.mkv"
        temp_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file.write_bytes(b"fake content")
        
        # Register the file
        self.video_editor.short_format_temp_files = [temp_file]
        self.video_editor._register_temp_file(temp_file)
        
        # Verify it's in temp_manager
        self.assertIn(Path(temp_file), self.video_editor.temp_manager.temp_files)
        
        # Clean up with preservation
        self.video_editor._cleanup_temp_files(preserve_short_format=True)
        
        # File should be removed from temp_manager
        self.assertNotIn(Path(temp_file), self.video_editor.temp_manager.temp_files)
    
    def test_cleanup_defaults_to_false(self):
        """Test that cleanup defaults to preserve_short_format=False"""
        temp_file = self.output_dir / "temp_vstack_short_test.mkv"
        temp_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file.write_bytes(b"fake content")
        
        self.video_editor.short_format_temp_files = [temp_file]
        self.video_editor._register_temp_file(temp_file)
        
        # Clean up without specifying preserve_short_format
        self.video_editor._cleanup_temp_files()
        
        # File should be deleted (default behavior)
        self.assertFalse(temp_file.exists(), "Temp file should be deleted by default")
    
    def test_vstack_file_tracked_in_create_short_format_video(self):
        """Test that vstack files are tracked when creating short format videos"""
        # This test will need to be updated after implementation
        # For now, we'll verify the tracking mechanism exists
        self.assertTrue(hasattr(self.video_editor, 'short_format_temp_files'))
        self.assertIsInstance(self.video_editor.short_format_temp_files, list)


if __name__ == '__main__':
    unittest.main()

