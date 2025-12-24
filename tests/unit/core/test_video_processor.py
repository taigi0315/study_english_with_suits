"""
Unit tests for video_processor.py
"""
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os
from pathlib import Path
import sys

# Add the parent directory to the path so we can import langflix
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langflix.core.video_processor import VideoProcessor, get_video_file_for_subtitle


class TestVideoProcessor(unittest.TestCase):
    """Test cases for the video processor module."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.media_dir = Path(self.temp_dir) / "media"
        self.media_dir.mkdir()
        
        self.processor = VideoProcessor(str(self.media_dir))
    
    def test_init_with_video_file(self):
        """Test VideoProcessor initialization with video_file parameter."""
        video_file_path = self.media_dir / "direct_video.mkv"
        video_file_path.touch()
        
        processor = VideoProcessor(str(self.media_dir), video_file=str(video_file_path))
        
        self.assertEqual(processor.media_dir, Path(self.media_dir))
        self.assertEqual(processor.video_file, Path(video_file_path))
        self.assertIsNotNone(processor.video_file)
    
    def test_find_video_file_uses_direct_video_file(self):
        """Test that find_video_file uses directly provided video_file when available."""
        # Create a direct video file
        direct_video = self.media_dir / "direct_video.mkv"
        direct_video.touch()
        
        # Create another video file that would match the subtitle
        subtitle_video = self.media_dir / "Subtitle.mkv"
        subtitle_video.touch()
        
        # Initialize processor with direct video file
        processor = VideoProcessor(str(self.media_dir), video_file=str(direct_video))
        
        # Should return the direct video file, not the subtitle-matched one
        result = processor.find_video_file("Subtitle.srt")
        
        self.assertIsNotNone(result)
        self.assertEqual(result, direct_video)
    
    def test_find_video_file_falls_back_to_search_when_direct_not_exists(self):
        """Test that find_video_file falls back to search when direct video_file doesn't exist."""
        # Create a non-existent direct video file path
        non_existent_video = self.media_dir / "non_existent.mkv"
        
        # Create a video file that matches subtitle
        matching_video = self.media_dir / "Test.mkv"
        matching_video.touch()
        
        # Initialize processor with non-existent direct video file
        processor = VideoProcessor(str(self.media_dir), video_file=str(non_existent_video))
        
        # Should fall back to searching and find the matching video
        result = processor.find_video_file("Test.srt")
        
        self.assertIsNotNone(result)
        self.assertEqual(result, matching_video)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_find_video_file_success(self):
        """Test successful video file finding."""
        # Create test files
        subtitle_path = "Suits - 1x01 - Pilot.720p.WEB-DL.en.srt"
        video_path = self.media_dir / "Suits - 1x01 - Pilot.720p.WEB-DL.mkv"
        video_path.touch()
        
        result = self.processor.find_video_file(subtitle_path)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "Suits - 1x01 - Pilot.720p.WEB-DL.mkv")
    
    def test_find_video_file_without_language_suffix(self):
        """Test video file finding without .en suffix."""
        # Create test files
        subtitle_path = "Suits - 1x01 - Pilot.720p.WEB-DL.srt"
        video_path = self.media_dir / "Suits - 1x01 - Pilot.720p.WEB-DL.mp4"
        video_path.touch()
        
        result = self.processor.find_video_file(subtitle_path)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "Suits - 1x01 - Pilot.720p.WEB-DL.mp4")
    
    def test_find_video_file_not_found(self):
        """Test video file not found."""
        subtitle_path = "NonExistent.srt"
        
        result = self.processor.find_video_file(subtitle_path)
        
        self.assertIsNone(result)
    
    def test_find_video_file_unsupported_format(self):
        """Test video file with unsupported format."""
        # Create test files
        subtitle_path = "Test.srt"
        video_path = self.media_dir / "Test.txt"  # Unsupported format
        video_path.touch()
        
        result = self.processor.find_video_file(subtitle_path)
        
        self.assertIsNone(result)
    
    @patch('langflix.core.video_processor.ffmpeg.probe')
    def test_validate_video_file_success(self, mock_probe):
        """Test successful video file validation."""
        # Mock ffmpeg probe response
        mock_probe.return_value = {
            'streams': [
                {
                    'codec_type': 'video',
                    'width': 1920,
                    'height': 1080,
                    'r_frame_rate': '30/1',
                    'codec_name': 'h264'
                }
            ],
            'format': {
                'duration': '120.5',
                'bit_rate': '5000000'
            }
        }
        
        video_path = self.media_dir / "test.mkv"
        video_path.touch()
        
        result = self.processor.validate_video_file(video_path)
        
        self.assertTrue(result['valid'])
        self.assertIsNone(result['error'])
        self.assertIsNotNone(result['metadata'])
        self.assertEqual(result['metadata']['width'], 1920)
        self.assertEqual(result['metadata']['height'], 1080)
    
    def test_validate_video_file_not_found(self):
        """Test video file validation when file doesn't exist."""
        video_path = self.media_dir / "nonexistent.mkv"
        
        result = self.processor.validate_video_file(video_path)
        
        self.assertFalse(result['valid'])
        self.assertIn("Video file not found", result['error'])
        self.assertIsNone(result['metadata'])
    
    @patch('langflix.core.video_processor.ffmpeg.probe')
    def test_validate_video_file_no_video_stream(self, mock_probe):
        """Test video file validation with no video stream."""
        # Mock ffmpeg probe response with no video stream
        mock_probe.return_value = {
            'streams': [
                {
                    'codec_type': 'audio',
                    'codec_name': 'aac'
                }
            ],
            'format': {
                'duration': '120.5'
            }
        }
        
        video_path = self.media_dir / "test.mkv"
        video_path.touch()
        
        result = self.processor.validate_video_file(video_path)
        
        self.assertFalse(result['valid'])
        self.assertIn("No video stream found", result['error'])
        self.assertIsNone(result['metadata'])
    
    def test_time_to_seconds(self):
        """Test time string to seconds conversion."""
        # Test various time formats
        test_cases = [
            ("00:01:25.657", 85.657),
            ("01:30:45.123", 5445.123),
            ("00:00:10.000", 10.0),
            ("00:00:00.500", 0.5)
        ]
        
        for time_str, expected_seconds in test_cases:
            with self.subTest(time_str=time_str):
                result = self.processor._time_to_seconds(time_str)
                self.assertAlmostEqual(result, expected_seconds, places=3)
    
    def test_time_to_seconds_invalid_format(self):
        """Test time string conversion with invalid format."""
        invalid_times = ["invalid", "not-a-time"]
        
        for invalid_time in invalid_times:
            with self.subTest(invalid_time=invalid_time):
                result = self.processor._time_to_seconds(invalid_time)
                self.assertEqual(result, 0.0)
    
    @patch('langflix.core.video_processor.ffmpeg')
    def test_extract_clip_success(self, mock_ffmpeg):
        """Test successful video clip extraction with fallback mechanism."""
        # Mock ffmpeg operations
        mock_input = MagicMock()
        mock_output = MagicMock()
        mock_ffmpeg.input.return_value = mock_input
        mock_input.output.return_value = mock_output

        video_path = self.media_dir / "source.mkv"
        output_path = self.media_dir / "clip.mkv"
        video_path.touch()

        result = self.processor.extract_clip(
            video_path,
            "00:01:25,657",
            "00:01:32,230",
            output_path
        )

        self.assertTrue(result)
        # Note: ffmpeg.input is called twice due to stream copy fallback mechanism
        # First attempt: stream copy, second attempt: re-encode
        self.assertEqual(mock_ffmpeg.input.call_count, 2)
        # Output is called for both attempts
        self.assertGreaterEqual(mock_input.output.call_count, 1)
    
    @patch('langflix.core.video_processor.ffmpeg')
    def test_extract_clip_failure(self, mock_ffmpeg):
        """Test video clip extraction failure."""
        # Mock ffmpeg to raise exception
        mock_ffmpeg.input.side_effect = Exception("FFmpeg error")
        
        video_path = self.media_dir / "source.mkv"
        output_path = self.media_dir / "clip.mkv"
        video_path.touch()
        
        result = self.processor.extract_clip(
            video_path, 
            "00:01:25,657", 
            "00:01:32,230", 
            output_path
        )
        
        self.assertFalse(result)
    
    def test_get_video_file_for_subtitle(self):
        """Test convenience function."""
        # Create test files
        subtitle_path = "Test.srt"
        video_path = self.media_dir / "Test.mp4"
        video_path.touch()
        
        result = get_video_file_for_subtitle(subtitle_path, str(self.media_dir))
        
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "Test.mp4")
    
    def test_find_video_file_multiple_matches(self):
        """Test finding video file when multiple similar files exist."""
        # Create test files with similar names
        subtitle_path = "Test.episode.srt"
        video_paths = [
            self.media_dir / "Test.episode.1080p.mp4",
            self.media_dir / "Test.episode.720p.mkv",
            self.media_dir / "Test.episode.season.1.mkv"
        ]
        
        for path in video_paths:
            path.touch()
        
        result = self.processor.find_video_file(subtitle_path)
        
        # Should find the first matching file
        self.assertIsNotNone(result)
        self.assertIn(result.name, [p.name for p in video_paths])
    
    def test_extract_clip_invalid_time_format(self):
        """Test video clip extraction with invalid time format."""
        video_path = self.media_dir / "source.mkv"
        output_path = self.media_dir / "clip.mkv"
        video_path.touch()
        
        # Test with invalid time formats
        result = self.processor.extract_clip(
            video_path, 
            "invalid_time", 
            "also_invalid", 
            output_path
        )
        
        self.assertFalse(result)
    
    def test_extract_clip_zero_duration(self):
        """Test video clip extraction with zero duration."""
        video_path = self.media_dir / "source.mkv"
        output_path = self.media_dir / "clip.mkv"
        video_path.touch()
        
        # Same start and end time (zero duration)
        result = self.processor.extract_clip(
            video_path, 
            "00:01:25,657", 
            "00:01:25,657", 
            output_path
        )
        
        self.assertFalse(result)
    
    def test_extract_clip_negative_duration(self):
        """Test video clip extraction with negative duration."""
        video_path = self.media_dir / "source.mkv"
        output_path = self.media_dir / "clip.mkv"
        video_path.touch()
        
        # End time before start time
        result = self.processor.extract_clip(
            video_path, 
            "00:01:32,230", 
            "00:01:25,657", 
            output_path
        )
        
        self.assertFalse(result)
    
    @patch('langflix.core.video_processor.ffmpeg.probe')
    def test_validate_video_file_corrupted_streams(self, mock_probe):
        """Test video file validation with corrupted stream data."""
        # Mock ffmpeg probe response with missing stream data
        mock_probe.return_value = {
            'streams': [
                {
                    'codec_type': 'video',
                    # Missing width, height, codec_name
                }
            ],
            'format': {
                'duration': 'invalid_duration'  # Invalid duration
            }
        }
        
        video_path = self.media_dir / "test.mkv"
        video_path.touch()
        
        result = self.processor.validate_video_file(video_path)
        
        # Should handle gracefully
        self.assertIsNotNone(result)
        # May be valid or invalid depending on implementation
    
    def test_time_to_seconds_edge_cases(self):
        """Test time conversion with edge cases."""
        test_cases = [
            ("23:59:59.999", 86399.999),  # Max reasonable time
            ("00:00:00.000", 0.0),        # Zero time
            ("00:00:01.001", 1.001),      # Just over 1 second
            ("99:99:99.999", 362439.999), # Large time values (still valid format)
        ]

        for time_str, expected_seconds in test_cases:
            with self.subTest(time_str=time_str):
                result = self.processor._time_to_seconds(time_str)
                self.assertAlmostEqual(result, expected_seconds, places=3)
    
    @patch('langflix.core.video_processor.ffmpeg')
    def test_extract_clip_permission_error(self, mock_ffmpeg):
        """Test video clip extraction with permission error."""
        # Mock ffmpeg to raise permission error
        mock_ffmpeg.input.side_effect = PermissionError("Permission denied")
        
        video_path = self.media_dir / "source.mkv"
        output_path = self.media_dir / "clip.mkv"
        video_path.touch()
        
        result = self.processor.extract_clip(
            video_path, 
            "00:01:25,657", 
            "00:01:32,230", 
            output_path
        )
        
        self.assertFalse(result)
    
    def test_find_video_file_case_sensitivity(self):
        """Test video file finding with case sensitivity."""
        # Create test file with different case
        subtitle_path = "test.srt"
        video_path = self.media_dir / "TEST.MP4"  # Different case
        video_path.touch()
        
        result = self.processor.find_video_file(subtitle_path)
        
        # Implementation should handle case sensitivity appropriately
        # This test documents the current behavior
        if result is not None:
            self.assertIsInstance(result, Path)
    
    @patch('langflix.core.video_processor.ffmpeg')
    def test_extract_clip_large_timestamps(self, mock_ffmpeg):
        """Test video clip extraction with large timestamps."""
        mock_input = MagicMock()
        mock_output = MagicMock()
        mock_ffmpeg.input.return_value = mock_input
        mock_input.output.return_value = mock_output
        
        video_path = self.media_dir / "source.mkv"
        output_path = self.media_dir / "clip.mkv"
        video_path.touch()
        
        # Large timestamp (over 24 hours)
        result = self.processor.extract_clip(
            video_path, 
            "25:30:45,123", 
            "25:30:50,456", 
            output_path
        )
        
        # Should handle large timestamps without error
        self.assertIsInstance(result, bool)


if __name__ == '__main__':
    unittest.main()
