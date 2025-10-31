"""
Integration tests for temporary file cleanup.

Tests verify that temporary files are properly cleaned up in real workflows:
- Video processing workflows
- TTS workflows
- Multiple concurrent operations
"""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import asyncio

from langflix.utils.temp_file_manager import TempFileManager, get_temp_manager


class TestTempFileCleanupIntegration(unittest.TestCase):
    """Integration tests for temp file cleanup in workflows."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for testing
        self.test_base_dir = Path(tempfile.mkdtemp(prefix="test_temp_integration_"))
        self.manager = TempFileManager(prefix="test_", base_dir=self.test_base_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up all temp files created during test
        self.manager.cleanup_all()
        # Remove test base directory
        if self.test_base_dir.exists():
            import shutil
            shutil.rmtree(self.test_base_dir)
    
    def test_video_processing_workflow_cleanup(self):
        """Test that temp files are cleaned up after video processing workflow."""
        # Simulate video processing workflow
        temp_files_created = []
        
        # Step 1: Create temp video file (like in jobs.py)
        with self.manager.create_temp_file(suffix='.mkv', prefix='video_') as temp_video:
            temp_files_created.append(temp_video)
            temp_video.write_bytes(b"fake video content")
            self.assertTrue(temp_video.exists())
            
            # Step 2: Create temp subtitle file
            with self.manager.create_temp_file(suffix='.srt', prefix='subtitle_') as temp_subtitle:
                temp_files_created.append(temp_subtitle)
                temp_subtitle.write_text("1\n00:00:00,000 --> 00:00:01,000\nTest")
                self.assertTrue(temp_subtitle.exists())
                
                # Step 3: Simulate processing (files still exist during processing)
                self.assertTrue(temp_video.exists())
                self.assertTrue(temp_subtitle.exists())
        
        # Step 4: After context exits, files should be cleaned up
        self.assertFalse(temp_files_created[0].exists(), "Video file should be cleaned up")
        self.assertFalse(temp_files_created[1].exists(), "Subtitle file should be cleaned up")
    
    def test_tts_workflow_cleanup(self):
        """Test that temp files are cleaned up after TTS workflow."""
        # Simulate TTS workflow with delete=False (file persists after function returns)
        with self.manager.create_temp_file(suffix='.mp3', prefix='tts_', delete=False) as temp_audio:
            temp_audio.write_bytes(b"fake audio content")
            self.assertTrue(temp_audio.exists())
            
            # File persists after context (delete=False)
            self.assertTrue(temp_audio.exists())
            
            # Register for cleanup
            self.manager.register_file(temp_audio)
        
        # After cleanup_all, file should be removed
        self.assertTrue(temp_audio.exists(), "File should still exist before cleanup_all")
        self.manager.cleanup_all()
        self.assertFalse(temp_audio.exists(), "File should be cleaned up after cleanup_all")
    
    def test_multiple_concurrent_files_cleanup(self):
        """Test cleanup of multiple files created in sequence."""
        temp_files = []
        
        # Create multiple temp files
        for i in range(5):
            with self.manager.create_temp_file(suffix='.txt', prefix=f'file_{i}_') as temp_file:
                temp_files.append(temp_file)
                temp_file.write_text(f"content {i}")
                self.assertTrue(temp_file.exists())
        
        # All files should be cleaned up after contexts exit
        for temp_file in temp_files:
            self.assertFalse(temp_file.exists(), f"File {temp_file} should be cleaned up")
    
    def test_nested_contexts_cleanup(self):
        """Test cleanup with nested context managers."""
        outer_file = None
        inner_file = None
        
        with self.manager.create_temp_file(suffix='.mkv', prefix='outer_') as outer:
            outer_file = outer
            outer.write_bytes(b"outer content")
            self.assertTrue(outer.exists())
            
            with self.manager.create_temp_file(suffix='.srt', prefix='inner_') as inner:
                inner_file = inner
                inner.write_text("inner content")
                self.assertTrue(inner.exists())
                self.assertTrue(outer.exists())
            
            # Inner file should be cleaned up, outer still exists
            self.assertFalse(inner_file.exists())
            self.assertTrue(outer_file.exists())
        
        # Outer file should be cleaned up after outer context exits
        self.assertFalse(outer_file.exists())
    
    def test_exception_during_processing_cleanup(self):
        """Test that temp files are cleaned up even when exception occurs."""
        temp_file = None
        try:
            with self.manager.create_temp_file(suffix='.mkv', prefix='error_') as temp:
                temp_file = temp
                temp.write_bytes(b"content")
                self.assertTrue(temp.exists())
                # Simulate error during processing
                raise ValueError("Simulated error")
        except ValueError:
            pass
        
        # File should still be cleaned up despite exception
        self.assertIsNotNone(temp_file)
        self.assertFalse(temp_file.exists(), "File should be cleaned up even after exception")
    
    def test_register_external_file_cleanup(self):
        """Test registering externally created files for cleanup."""
        # Create a file outside of temp manager
        external_file = self.test_base_dir / "external_file.txt"
        external_file.write_text("external content")
        self.assertTrue(external_file.exists())
        
        # Register it with manager
        self.manager.register_file(external_file)
        self.assertIn(external_file, self.manager.temp_files)
        
        # Cleanup should remove it
        self.manager.cleanup_all()
        self.assertFalse(external_file.exists(), "External file should be cleaned up")
    
    def test_cleanup_all_with_mixed_files(self):
        """Test cleanup_all with mix of context-managed and registered files."""
        # Create files with context managers
        context_files = []
        for i in range(3):
            with self.manager.create_temp_file(suffix='.txt', prefix=f'context_{i}_', delete=False) as temp:
                temp.write_text(f"context {i}")
                context_files.append(temp)
        
        # Register external files
        external_files = []
        for i in range(2):
            external_file = self.test_base_dir / f"external_{i}.txt"
            external_file.write_text(f"external {i}")
            self.manager.register_file(external_file)
            external_files.append(external_file)
        
        # All files should exist
        all_files = context_files + external_files
        for f in all_files:
            self.assertTrue(f.exists())
        
        # cleanup_all should remove all
        self.manager.cleanup_all()
        
        for f in all_files:
            self.assertFalse(f.exists(), f"File {f} should be cleaned up")


class TestTempFileManagerGlobalInstance(unittest.TestCase):
    """Test global singleton instance behavior."""
    
    def test_global_manager_singleton(self):
        """Test that get_temp_manager returns same instance."""
        manager1 = get_temp_manager()
        manager2 = get_temp_manager()
        
        self.assertIs(manager1, manager2)
    
    def test_global_manager_cross_module(self):
        """Test that global manager works across different code paths."""
        manager = get_temp_manager()
        
        # Simulate file creation from different "modules"
        with manager.create_temp_file(suffix='.mkv', prefix='module1_') as file1:
            file1.write_bytes(b"module1")
            
            # Simulate another module using same manager
            with manager.create_temp_file(suffix='.srt', prefix='module2_') as file2:
                file2.write_text("module2")
                self.assertTrue(file1.exists())
                self.assertTrue(file2.exists())


if __name__ == '__main__':
    unittest.main()

