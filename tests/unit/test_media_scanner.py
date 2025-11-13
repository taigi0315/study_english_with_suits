"""
Unit tests for media_scanner.py

Tests cover:
- File accessibility checks
- Video metadata extraction with various error scenarios
- FFprobe error handling
- Timeout scenarios
- Permission errors
- File not found errors
"""
import unittest
from unittest.mock import patch, MagicMock, Mock
import tempfile
import os
import subprocess
import json
from pathlib import Path
import sys

# Add the parent directory to the path so we can import langflix
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langflix.media.media_scanner import MediaScanner


class TestMediaScanner(unittest.TestCase):
    """Test cases for MediaScanner class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.media_dir = Path(self.temp_dir) / "media"
        self.media_dir.mkdir()
        
        self.scanner = MediaScanner(str(self.media_dir))
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_check_file_accessible_file_exists(self):
        """Test _check_file_accessible with existing file."""
        video_file = self.media_dir / "test.mkv"
        video_file.write_bytes(b"fake video content")
        
        is_accessible, error_msg = self.scanner._check_file_accessible(video_file)
        self.assertTrue(is_accessible)
        self.assertIsNone(error_msg)
    
    def test_check_file_accessible_file_not_exists(self):
        """Test _check_file_accessible with non-existent file."""
        video_file = self.media_dir / "nonexistent.mkv"
        
        is_accessible, error_msg = self.scanner._check_file_accessible(video_file)
        self.assertFalse(is_accessible)
        self.assertIn("does not exist", error_msg)
    
    def test_check_file_accessible_path_is_directory(self):
        """Test _check_file_accessible with directory path."""
        subdir = self.media_dir / "subdir"
        subdir.mkdir()
        
        is_accessible, error_msg = self.scanner._check_file_accessible(subdir)
        self.assertFalse(is_accessible)
        self.assertIn("not a file", error_msg)
    
    def test_check_file_accessible_empty_file(self):
        """Test _check_file_accessible with empty file."""
        video_file = self.media_dir / "empty.mkv"
        video_file.touch()  # Create empty file
        
        is_accessible, error_msg = self.scanner._check_file_accessible(video_file)
        self.assertFalse(is_accessible)
        self.assertIn("empty", error_msg)
    
    @patch('langflix.media.ffmpeg_utils.run_ffprobe')
    def test_get_video_metadata_success(self, mock_run_ffprobe):
        """Test successful video metadata extraction."""
        video_file = self.media_dir / "test.mkv"
        video_file.write_bytes(b"fake video content")
        
        # Mock ffprobe response
        mock_probe = {
            'streams': [
                {
                    'codec_type': 'video',
                    'width': 1920,
                    'height': 1080,
                    'codec_name': 'h264'
                }
            ],
            'format': {
                'duration': '3600.0',
                'size': '1073741824',  # 1GB
                'format_name': 'matroska,webm'
            }
        }
        mock_run_ffprobe.return_value = mock_probe
        
        metadata = self.scanner._get_video_metadata(video_file)
        
        self.assertEqual(metadata['duration'], 3600.0)
        self.assertEqual(metadata['resolution'], '1920x1080')
        self.assertEqual(metadata['width'], 1920)
        self.assertEqual(metadata['height'], 1080)
        self.assertEqual(metadata['size_mb'], 1024.0)
        self.assertEqual(metadata['format'], 'matroska,webm')
        self.assertEqual(metadata['codec'], 'h264')
    
    def test_get_video_metadata_file_not_exists(self):
        """Test _get_video_metadata with non-existent file."""
        video_file = self.media_dir / "nonexistent.mkv"
        
        metadata = self.scanner._get_video_metadata(video_file)
        self.assertEqual(metadata, {})
    
    @patch('langflix.media.ffmpeg_utils.run_ffprobe')
    def test_get_video_metadata_no_video_stream(self, mock_run_ffprobe):
        """Test _get_video_metadata when no video stream found."""
        video_file = self.media_dir / "test.mkv"
        video_file.write_bytes(b"fake video content")
        
        # Mock ffprobe response with no video stream
        mock_probe = {
            'streams': [
                {
                    'codec_type': 'audio',
                    'codec_name': 'aac'
                }
            ],
            'format': {
                'duration': '3600.0',
                'size': '1073741824'
            }
        }
        mock_run_ffprobe.return_value = mock_probe
        
        metadata = self.scanner._get_video_metadata(video_file)
        self.assertEqual(metadata, {})
    
    @patch('langflix.media.ffmpeg_utils.run_ffprobe')
    def test_get_video_metadata_ffprobe_called_process_error(self, mock_run_ffprobe):
        """Test _get_video_metadata when ffprobe raises CalledProcessError."""
        video_file = self.media_dir / "test.mkv"
        video_file.write_bytes(b"fake video content")
        
        # Mock CalledProcessError with stderr
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd=['ffprobe'],
            stderr=b"Error: Invalid data found when processing input"
        )
        mock_run_ffprobe.side_effect = error
        
        metadata = self.scanner._get_video_metadata(video_file)
        self.assertEqual(metadata, {})
    
    @patch('langflix.media.ffmpeg_utils.run_ffprobe')
    def test_get_video_metadata_ffprobe_file_not_found(self, mock_run_ffprobe):
        """Test _get_video_metadata when ffprobe is not found."""
        video_file = self.media_dir / "test.mkv"
        video_file.write_bytes(b"fake video content")
        
        mock_run_ffprobe.side_effect = FileNotFoundError("ffprobe not found")
        
        metadata = self.scanner._get_video_metadata(video_file)
        self.assertEqual(metadata, {})
    
    @patch('langflix.media.ffmpeg_utils.run_ffprobe')
    def test_get_video_metadata_json_decode_error(self, mock_run_ffprobe):
        """Test _get_video_metadata when JSON parsing fails."""
        video_file = self.media_dir / "test.mkv"
        video_file.write_bytes(b"fake video content")
        
        mock_run_ffprobe.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        metadata = self.scanner._get_video_metadata(video_file)
        self.assertEqual(metadata, {})
    
    @patch('langflix.media.ffmpeg_utils.run_ffprobe')
    def test_get_video_metadata_permission_error(self, mock_run_ffprobe):
        """Test _get_video_metadata when permission denied."""
        video_file = self.media_dir / "test.mkv"
        video_file.write_bytes(b"fake video content")
        
        mock_run_ffprobe.side_effect = PermissionError("Permission denied")
        
        metadata = self.scanner._get_video_metadata(video_file)
        self.assertEqual(metadata, {})
    
    @patch('langflix.media.ffmpeg_utils.run_ffprobe')
    def test_get_video_metadata_timeout_error(self, mock_run_ffprobe):
        """Test _get_video_metadata when timeout occurs."""
        video_file = self.media_dir / "test.mkv"
        video_file.write_bytes(b"fake video content")
        
        mock_run_ffprobe.side_effect = TimeoutError("FFprobe timeout")
        
        metadata = self.scanner._get_video_metadata(video_file)
        self.assertEqual(metadata, {})
    
    @patch('langflix.media.ffmpeg_utils.run_ffprobe')
    def test_get_video_metadata_generic_exception(self, mock_run_ffprobe):
        """Test _get_video_metadata with generic exception."""
        video_file = self.media_dir / "test.mkv"
        video_file.write_bytes(b"fake video content")
        
        mock_run_ffprobe.side_effect = ValueError("Unexpected error")
        
        metadata = self.scanner._get_video_metadata(video_file)
        self.assertEqual(metadata, {})
    
    @patch('langflix.media.ffmpeg_utils.run_ffprobe')
    def test_get_video_metadata_stderr_logging(self, mock_run_ffprobe):
        """Test that stderr is properly logged when ffprobe fails."""
        video_file = self.media_dir / "test.mkv"
        video_file.write_bytes(b"fake video content")
        
        # Mock CalledProcessError with stderr as string
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd=['ffprobe'],
            stderr="Error: Invalid data found when processing input"
        )
        mock_run_ffprobe.side_effect = error
        
        with patch('langflix.media.media_scanner.logger') as mock_logger:
            metadata = self.scanner._get_video_metadata(video_file)
            self.assertEqual(metadata, {})
            
            # Verify error was logged with stderr
            error_calls = [call for call in mock_logger.error.call_args_list 
                          if 'FFprobe command failed' in str(call)]
            self.assertGreater(len(error_calls), 0)
            
            # Check that stderr is in the log message
            log_message = str(error_calls[0])
            self.assertIn('stderr', log_message)


class TestFFprobeUtils(unittest.TestCase):
    """Test cases for run_ffprobe function improvements."""
    
    @patch('langflix.media.ffmpeg_utils.subprocess.run')
    def test_run_ffprobe_with_timeout(self, mock_subprocess_run):
        """Test run_ffprobe with timeout parameter."""
        from langflix.media.ffmpeg_utils import run_ffprobe
        
        # Mock successful subprocess run
        mock_result = MagicMock()
        mock_result.stdout = json.dumps({
            'streams': [],
            'format': {}
        })
        mock_subprocess_run.return_value = mock_result
        
        result = run_ffprobe("/path/to/video.mkv", timeout=30)
        self.assertIsInstance(result, dict)
        
        # Verify timeout was passed to subprocess.run
        mock_subprocess_run.assert_called_once()
        call_kwargs = mock_subprocess_run.call_args[1]
        self.assertEqual(call_kwargs.get('timeout'), 30)
    
    @patch('langflix.media.ffmpeg_utils.subprocess.run')
    def test_run_ffprobe_timeout_expired(self, mock_subprocess_run):
        """Test run_ffprobe when timeout expires."""
        from langflix.media.ffmpeg_utils import run_ffprobe
        
        # Mock timeout exception
        mock_subprocess_run.side_effect = subprocess.TimeoutExpired(
            cmd=['ffprobe'],
            timeout=30
        )
        
        with self.assertRaises(TimeoutError):
            run_ffprobe("/path/to/video.mkv", timeout=30)
    
    @patch('langflix.media.ffmpeg_utils.subprocess.run')
    def test_run_ffprobe_called_process_error_with_stderr(self, mock_subprocess_run):
        """Test run_ffprobe when CalledProcessError occurs with stderr."""
        from langflix.media.ffmpeg_utils import run_ffprobe
        
        # Mock CalledProcessError with stderr
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd=['ffprobe'],
            stderr=b"Error: Invalid data"
        )
        mock_subprocess_run.side_effect = error
        
        # Mock ffmpeg.probe fallback
        with patch('langflix.media.ffmpeg_utils.ffmpeg.probe') as mock_ffmpeg_probe:
            mock_ffmpeg_probe.return_value = {'streams': [], 'format': {}}
            
            result = run_ffprobe("/path/to/video.mkv")
            self.assertIsInstance(result, dict)
    
    @patch('langflix.media.ffmpeg_utils.subprocess.run')
    def test_run_ffprobe_file_not_found(self, mock_subprocess_run):
        """Test run_ffprobe when ffprobe command is not found."""
        from langflix.media.ffmpeg_utils import run_ffprobe
        
        mock_subprocess_run.side_effect = FileNotFoundError("ffprobe not found")
        
        with self.assertRaises(FileNotFoundError):
            run_ffprobe("/path/to/video.mkv")
    
    @patch('langflix.media.ffmpeg_utils.subprocess.run')
    def test_run_ffprobe_json_decode_error(self, mock_subprocess_run):
        """Test run_ffprobe when JSON parsing fails."""
        from langflix.media.ffmpeg_utils import run_ffprobe
        
        # Mock subprocess returning invalid JSON
        mock_result = MagicMock()
        mock_result.stdout = "invalid json"
        mock_subprocess_run.return_value = mock_result
        
        with self.assertRaises(json.JSONDecodeError):
            run_ffprobe("/path/to/video.mkv")


if __name__ == '__main__':
    unittest.main()

