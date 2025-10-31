"""
Unit tests for TempFileManager utility.

Tests cover:
- Temporary file creation and automatic cleanup
- Temporary directory creation and cleanup
- Exception handling during cleanup
- Context manager behavior
- Manual file registration
- cleanup_all functionality
"""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from langflix.utils.temp_file_manager import TempFileManager, get_temp_manager


class TestTempFileManager(unittest.TestCase):
    """Test cases for TempFileManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for testing
        self.test_base_dir = Path(tempfile.mkdtemp(prefix="test_temp_manager_"))
        self.manager = TempFileManager(prefix="test_", base_dir=self.test_base_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up all temp files created during test
        self.manager.cleanup_all()
        # Remove test base directory
        if self.test_base_dir.exists():
            import shutil
            shutil.rmtree(self.test_base_dir)
    
    def test_init_default_prefix(self):
        """Test TempFileManager initialization with default prefix."""
        manager = TempFileManager()
        self.assertEqual(manager.prefix, "langflix_")
        self.assertIsNotNone(manager.base_dir)
    
    def test_init_custom_prefix(self):
        """Test TempFileManager initialization with custom prefix."""
        manager = TempFileManager(prefix="custom_", base_dir=self.test_base_dir)
        self.assertEqual(manager.prefix, "custom_")
        self.assertEqual(manager.base_dir, self.test_base_dir)
    
    def test_create_temp_file_basic(self):
        """Test basic temporary file creation and cleanup."""
        with self.manager.create_temp_file(suffix='.txt') as temp_path:
            # Verify file exists
            self.assertTrue(temp_path.exists())
            self.assertTrue(temp_path.is_file())
            
            # Verify file has correct suffix
            self.assertEqual(temp_path.suffix, '.txt')
            
            # Verify file has correct prefix
            self.assertTrue(temp_path.name.startswith('test_'))
            
            # Write to file
            temp_path.write_text("test content")
            self.assertEqual(temp_path.read_text(), "test content")
        
        # After context exits, file should be deleted
        self.assertFalse(temp_path.exists())
        self.assertEqual(len(self.manager.temp_files), 0)
    
    def test_create_temp_file_with_custom_prefix(self):
        """Test temporary file creation with custom prefix."""
        with self.manager.create_temp_file(suffix='.mkv', prefix='video_') as temp_path:
            self.assertTrue(temp_path.exists())
            self.assertTrue(temp_path.name.startswith('video_'))
            self.assertEqual(temp_path.suffix, '.mkv')
    
    def test_create_temp_file_no_delete(self):
        """Test temporary file creation with delete=False."""
        with self.manager.create_temp_file(suffix='.txt', delete=False) as temp_path:
            temp_path.write_text("persistent content")
            self.assertTrue(temp_path.exists())
        
        # After context exits, file should still exist (delete=False)
        self.assertTrue(temp_path.exists())
        self.assertEqual(temp_path.read_text(), "persistent content")
        
        # Manually clean up for test
        if temp_path.exists():
            temp_path.unlink()
    
    def test_create_temp_file_exception_cleanup(self):
        """Test that temp file is cleaned up even when exception occurs."""
        temp_path = None
        try:
            with self.manager.create_temp_file(suffix='.txt') as temp_path:
                temp_path.write_text("test")
                # Raise exception
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # File should be cleaned up despite exception
        self.assertIsNotNone(temp_path)
        self.assertFalse(temp_path.exists())
    
    def test_create_temp_dir_basic(self):
        """Test basic temporary directory creation and cleanup."""
        with self.manager.create_temp_dir() as temp_dir:
            # Verify directory exists
            self.assertTrue(temp_dir.exists())
            self.assertTrue(temp_dir.is_dir())
            
            # Verify directory has correct prefix
            self.assertTrue(temp_dir.name.startswith('test_'))
            
            # Create a file in the directory
            test_file = temp_dir / "test.txt"
            test_file.write_text("content")
            self.assertTrue(test_file.exists())
        
        # After context exits, directory should be deleted
        self.assertFalse(temp_dir.exists())
        self.assertEqual(len(self.manager.temp_dirs), 0)
    
    def test_create_temp_dir_with_custom_prefix(self):
        """Test temporary directory creation with custom prefix."""
        with self.manager.create_temp_dir(prefix='custom_') as temp_dir:
            self.assertTrue(temp_dir.exists())
            self.assertTrue(temp_dir.name.startswith('custom_'))
    
    def test_create_temp_dir_exception_cleanup(self):
        """Test that temp directory is cleaned up even when exception occurs."""
        temp_dir = None
        try:
            with self.manager.create_temp_dir() as temp_dir:
                (temp_dir / "test.txt").write_text("content")
                # Raise exception
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Directory should be cleaned up despite exception
        self.assertIsNotNone(temp_dir)
        self.assertFalse(temp_dir.exists())
    
    def test_register_file(self):
        """Test manual file registration for cleanup."""
        # Create a file manually
        test_file = self.test_base_dir / "manual_test.txt"
        test_file.write_text("content")
        
        # Register it
        self.manager.register_file(test_file)
        self.assertIn(test_file, self.manager.temp_files)
        
        # Clean up all
        self.manager.cleanup_all()
        
        # File should be deleted
        self.assertFalse(test_file.exists())
        self.assertEqual(len(self.manager.temp_files), 0)
    
    def test_cleanup_all_files_and_dirs(self):
        """Test cleanup_all removes all registered files and directories."""
        # Create and register multiple files (with delete=False to keep them after context)
        file1 = None
        file2 = None
        
        with self.manager.create_temp_file(suffix='.txt', delete=False) as file1:
            pass
        
        with self.manager.create_temp_file(suffix='.mkv', delete=False) as file2:
            pass
        
        # Create a directory (with delete=False would require modifying the manager)
        # Instead, manually create and register a directory
        import tempfile
        dir1 = Path(tempfile.mkdtemp(prefix='test_', dir=str(self.test_base_dir)))
        (dir1 / "test.txt").write_text("content")
        self.manager.temp_dirs.append(dir1)
        
        # All should exist
        self.assertTrue(file1.exists())
        self.assertTrue(file2.exists())
        self.assertTrue(dir1.exists())
        
        # Clean up all
        self.manager.cleanup_all()
        
        # All should be deleted
        self.assertFalse(file1.exists())
        self.assertFalse(file2.exists())
        self.assertFalse(dir1.exists())
        self.assertEqual(len(self.manager.temp_files), 0)
        self.assertEqual(len(self.manager.temp_dirs), 0)
    
    def test_cleanup_all_handles_missing_files(self):
        """Test cleanup_all handles files that no longer exist gracefully."""
        # Create and register a file
        with self.manager.create_temp_file(suffix='.txt', delete=False) as temp_path:
            pass
        
        # Manually delete the file
        temp_path.unlink()
        
        # cleanup_all should not raise an exception
        try:
            self.manager.cleanup_all()
        except Exception as e:
            self.fail(f"cleanup_all raised {e} unexpectedly")
    
    def test_get_temp_manager_singleton(self):
        """Test get_temp_manager returns singleton instance."""
        manager1 = get_temp_manager()
        manager2 = get_temp_manager()
        
        self.assertIs(manager1, manager2)
    
    def test_multiple_contexts_nested(self):
        """Test using multiple context managers nested."""
        with self.manager.create_temp_dir() as dir1:
            with self.manager.create_temp_file(suffix='.txt') as file1:
                with self.manager.create_temp_file(suffix='.mkv') as file2:
                    file1.write_text("content1")
                    file2.write_bytes(b"content2")
                    
                    self.assertTrue(file1.exists())
                    self.assertTrue(file2.exists())
                    self.assertTrue(dir1.exists())
            
            # Inner files should be cleaned up
            self.assertFalse(file1.exists())
            self.assertFalse(file2.exists())
            self.assertTrue(dir1.exists())
        
        # Directory should be cleaned up after outer context exits
        self.assertFalse(dir1.exists())
    
    def test_file_in_registered_list(self):
        """Test that created files are added to temp_files list."""
        with self.manager.create_temp_file(suffix='.txt') as temp_path:
            self.assertIn(temp_path, self.manager.temp_files)
        
        # After cleanup, should be removed from list
        self.assertNotIn(temp_path, self.manager.temp_files)
    
    def test_dir_in_registered_list(self):
        """Test that created directories are added to temp_dirs list."""
        with self.manager.create_temp_dir() as temp_dir:
            self.assertIn(temp_dir, self.manager.temp_dirs)
        
        # After cleanup, should be removed from list
        self.assertNotIn(temp_dir, self.manager.temp_dirs)


if __name__ == '__main__':
    unittest.main()

