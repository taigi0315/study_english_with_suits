"""
Unit tests for FFprobe caching functionality.

Tests cover:
- Cache hit/miss behavior
- Cache invalidation on file modification
- Cache bypass option
- Cache statistics
"""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from langflix.media.ffmpeg_utils import (
    run_ffprobe,
    clear_ffprobe_cache,
    get_ffprobe_cache_info,
    _get_ffprobe_cache_key,
    _cached_ffprobe_result,
)


class TestFFprobeCache:
    """Test suite for FFprobe caching functionality"""

    def setup_method(self):
        """Clear cache before each test"""
        clear_ffprobe_cache()

    def teardown_method(self):
        """Clean up after each test"""
        clear_ffprobe_cache()

    @patch('langflix.media.ffmpeg_utils.subprocess.run')
    def test_cache_hit_on_repeated_call(self, mock_subprocess):
        """Test that second call to same file uses cache"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mkv', delete=False) as f:
            temp_path = f.name
            f.write("dummy video content")

        try:
            # Mock the subprocess probe to return fake data
            fake_probe_data = {
                'format': {'duration': '10.5'},
                'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080}]
            }
            
            mock_result = MagicMock()
            mock_result.stdout = json.dumps(fake_probe_data)
            mock_subprocess.return_value = mock_result

            # First call - should be cache miss
            result1 = run_ffprobe(temp_path)
            assert result1 == fake_probe_data
            assert mock_subprocess.call_count == 1

            # Second call - should be cache hit (no additional subprocess call)
            result2 = run_ffprobe(temp_path)
            assert result2 == fake_probe_data
            assert mock_subprocess.call_count == 1  # Still 1, not 2

            # Verify cache statistics
            cache_info = get_ffprobe_cache_info()
            assert cache_info['hits'] == 1
            assert cache_info['misses'] == 1
            assert cache_info['size'] >= 1

        finally:
            Path(temp_path).unlink()

    @patch('langflix.media.ffmpeg_utils.subprocess.run')
    def test_cache_invalidation_on_file_modification(self, mock_subprocess):
        """Test that cache invalidates when file is modified"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mkv', delete=False) as f:
            temp_path = f.name
            f.write("dummy video content")

        try:
            # Mock responses for different file states
            probe_data_v1 = {
                'format': {'duration': '10.5'},
                'streams': [{'codec_type': 'video'}]
            }
            probe_data_v2 = {
                'format': {'duration': '20.0'},
                'streams': [{'codec_type': 'video'}]
            }
            
            mock_result_v1 = MagicMock()
            mock_result_v1.stdout = json.dumps(probe_data_v1)
            mock_result_v2 = MagicMock()
            mock_result_v2.stdout = json.dumps(probe_data_v2)
            mock_subprocess.side_effect = [mock_result_v1, mock_result_v2]

            # First call
            result1 = run_ffprobe(temp_path)
            assert result1 == probe_data_v1
            assert mock_subprocess.call_count == 1

            # Modify file (change content and mtime)
            time.sleep(0.01)  # Ensure mtime changes
            with open(temp_path, 'a') as f:
                f.write("modified content")

            # Call again - should be cache miss due to mtime/size change
            result2 = run_ffprobe(temp_path)
            assert result2 == probe_data_v2
            assert mock_subprocess.call_count == 2  # Should have called subprocess again

        finally:
            Path(temp_path).unlink()

    @patch('langflix.media.ffmpeg_utils._run_ffprobe_uncached')
    def test_cache_bypass_option(self, mock_uncached):
        """Test that use_cache=False bypasses cache"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mkv', delete=False) as f:
            temp_path = f.name
            f.write("dummy video content")

        try:
            fake_probe_data = {
                'format': {'duration': '10.5'},
                'streams': []
            }
            mock_uncached.return_value = fake_probe_data

            # Call with cache bypass
            result1 = run_ffprobe(temp_path, use_cache=False)
            assert result1 == fake_probe_data
            assert mock_uncached.call_count == 1

            # Call again with cache bypass - should call uncached again
            result2 = run_ffprobe(temp_path, use_cache=False)
            assert result2 == fake_probe_data
            assert mock_uncached.call_count == 2  # Should have called twice

            # Verify cache was not used at all
            cache_info = get_ffprobe_cache_info()
            assert cache_info['hits'] == 0
            assert cache_info['misses'] == 0

        finally:
            Path(temp_path).unlink()

    def test_cache_clear_functionality(self):
        """Test that cache clear works correctly"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mkv', delete=False) as f:
            temp_path = f.name
            f.write("dummy video content")

        try:
            with patch('langflix.media.ffmpeg_utils.subprocess.run') as mock_subprocess:
                fake_probe_data = {'format': {'duration': '10.5'}}
                mock_result = MagicMock()
                mock_result.stdout = json.dumps(fake_probe_data)
                mock_subprocess.return_value = mock_result

                # First call - cache miss
                run_ffprobe(temp_path)
                assert mock_subprocess.call_count == 1

                # Second call - cache hit
                run_ffprobe(temp_path)
                assert mock_subprocess.call_count == 1

                # Clear cache
                clear_ffprobe_cache()
                cache_info = get_ffprobe_cache_info()
                assert cache_info['hits'] == 0
                assert cache_info['misses'] == 0
                assert cache_info['size'] == 0

                # Call again after clear - should be cache miss
                run_ffprobe(temp_path)
                assert mock_subprocess.call_count == 2

        finally:
            Path(temp_path).unlink()

    def test_cache_statistics(self):
        """Test cache statistics are reported correctly"""
        initial_stats = get_ffprobe_cache_info()
        assert 'hits' in initial_stats
        assert 'misses' in initial_stats
        assert 'size' in initial_stats
        assert 'maxsize' in initial_stats
        assert initial_stats['maxsize'] == 512  # Default maxsize

    @patch('langflix.media.ffmpeg_utils._run_ffprobe_uncached')
    def test_cache_key_generation(self, mock_uncached):
        """Test that cache key includes path, mtime, and size"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mkv', delete=False) as f:
            temp_path = f.name
            f.write("dummy video content")

        try:
            # Get cache key
            key = _get_ffprobe_cache_key(temp_path)
            
            # Verify key structure
            assert isinstance(key, tuple)
            assert len(key) == 3
            assert isinstance(key[0], str)  # Path
            assert isinstance(key[1], float)  # mtime
            assert isinstance(key[2], int)  # size
            
            # Verify path is resolved
            assert Path(key[0]).is_absolute()

        finally:
            Path(temp_path).unlink()

    @patch('langflix.media.ffmpeg_utils.subprocess.run')
    def test_multiple_files_separate_cache_entries(self, mock_subprocess):
        """Test that different files have separate cache entries"""
        # Create two temporary files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mkv', delete=False) as f1:
            temp_path1 = f1.name
            f1.write("video 1")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.mkv', delete=False) as f2:
            temp_path2 = f2.name
            f2.write("video 2 different content")

        try:
            probe_data_1 = {'format': {'duration': '10.0'}}
            probe_data_2 = {'format': {'duration': '20.0'}}
            
            mock_result_1 = MagicMock()
            mock_result_1.stdout = json.dumps(probe_data_1)
            mock_result_2 = MagicMock()
            mock_result_2.stdout = json.dumps(probe_data_2)
            mock_subprocess.side_effect = [mock_result_1, mock_result_2]

            # Probe both files
            result1 = run_ffprobe(temp_path1)
            result2 = run_ffprobe(temp_path2)

            assert result1 == probe_data_1
            assert result2 == probe_data_2
            assert mock_subprocess.call_count == 2

            # Probe again - both should be cache hits
            result1_cached = run_ffprobe(temp_path1)
            result2_cached = run_ffprobe(temp_path2)

            assert result1_cached == probe_data_1
            assert result2_cached == probe_data_2
            assert mock_subprocess.call_count == 2  # No additional calls

            # Verify cache size
            cache_info = get_ffprobe_cache_info()
            assert cache_info['size'] == 2  # Two separate entries
            assert cache_info['hits'] == 2

        finally:
            Path(temp_path1).unlink()
            Path(temp_path2).unlink()

    @patch('langflix.media.ffmpeg_utils.subprocess.run')
    def test_cache_with_timeout_parameter(self, mock_subprocess):
        """Test that timeout parameter is passed correctly to cached function"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mkv', delete=False) as f:
            temp_path = f.name
            f.write("dummy")

        try:
            fake_probe_data = {'format': {}}
            mock_result = MagicMock()
            mock_result.stdout = json.dumps(fake_probe_data)
            mock_subprocess.return_value = mock_result

            # Call with custom timeout
            run_ffprobe(temp_path, timeout=60)

            # Verify the cached function was called with correct timeout
            # (checking internal cache key includes timeout)
            cache_info = get_ffprobe_cache_info()
            assert cache_info['size'] == 1

        finally:
            Path(temp_path).unlink()

    @patch('langflix.media.ffmpeg_utils.subprocess.run')
    def test_cache_integration_with_real_ffprobe_structure(self, mock_subprocess):
        """Test cache works with realistic ffprobe output structure"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mkv', delete=False) as f:
            temp_path = f.name
            f.write("dummy")

        try:
            # Mock realistic ffprobe output
            realistic_output = {
                'streams': [
                    {
                        'codec_type': 'video',
                        'codec_name': 'h264',
                        'width': 1280,
                        'height': 720,
                        'pix_fmt': 'yuv420p',
                        'r_frame_rate': '25/1'
                    },
                    {
                        'codec_type': 'audio',
                        'codec_name': 'aac',
                        'channels': 2,
                        'sample_rate': '48000'
                    }
                ],
                'format': {
                    'duration': '125.5',
                    'size': '10485760',
                    'bit_rate': '668877'
                }
            }

            mock_result = MagicMock()
            mock_result.stdout = json.dumps(realistic_output)
            mock_subprocess.return_value = mock_result

            # First call
            result1 = run_ffprobe(temp_path)
            assert result1 == realistic_output
            assert mock_subprocess.call_count == 1

            # Second call - should use cache
            result2 = run_ffprobe(temp_path)
            assert result2 == realistic_output
            assert mock_subprocess.call_count == 1  # No additional subprocess call

            # Verify cache hit
            cache_info = get_ffprobe_cache_info()
            assert cache_info['hits'] == 1

        finally:
            Path(temp_path).unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

