#!/usr/bin/env python3
"""
Unit tests for audio preprocessing
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from langflix.asr.audio_preprocessor import AudioPreprocessor
from langflix.asr.exceptions import AudioExtractionError, AudioPreprocessingError


class TestAudioPreprocessor:
    """Test audio preprocessing functionality"""
    
    def test_init(self):
        """Test AudioPreprocessor initialization"""
        preprocessor = AudioPreprocessor()
        assert preprocessor.video_processor is None
        assert '.mp4' in preprocessor.supported_formats
        assert '.mkv' in preprocessor.supported_formats
    
    def test_init_with_video_processor(self):
        """Test initialization with video processor"""
        mock_video_processor = MagicMock()
        preprocessor = AudioPreprocessor(video_processor=mock_video_processor)
        assert preprocessor.video_processor == mock_video_processor
    
    def test_extract_audio_nonexistent_file(self):
        """Test audio extraction with non-existent file"""
        preprocessor = AudioPreprocessor()
        
        with pytest.raises(AudioExtractionError) as exc_info:
            preprocessor.extract_audio("/nonexistent/file.mp4", "/output/audio.wav")
        
        assert "does not exist" in str(exc_info.value)
    
    def test_extract_audio_unsupported_format(self):
        """Test audio extraction with unsupported format"""
        preprocessor = AudioPreprocessor()
        
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"Not a video file")
            temp_path = f.name
        
        try:
            with pytest.raises(AudioExtractionError) as exc_info:
                preprocessor.extract_audio(temp_path, "/output/audio.wav")
            
            assert "Unsupported format" in str(exc_info.value)
        finally:
            os.unlink(temp_path)
    
    @patch('subprocess.run')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.stat')
    @patch('pathlib.Path.mkdir')
    def test_extract_audio_success(self, mock_mkdir, mock_stat, mock_exists, mock_run):
        """Test successful audio extraction"""
        # Mock successful FFmpeg execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "FFmpeg output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        mock_exists.return_value = True
        
        # Mock file size check
        mock_stat_result = MagicMock()
        mock_stat_result.st_size = 1024  # Non-zero file size
        mock_stat.return_value = mock_stat_result
        
        # Mock directory creation
        mock_mkdir.return_value = None
        
        preprocessor = AudioPreprocessor()
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            f.write(b"Mock video content")
            temp_path = f.name
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "output.wav"
            
            try:
                result = preprocessor.extract_audio(temp_path, str(output_path))
                
                assert result == str(output_path)
                mock_run.assert_called_once()
                
                # Check FFmpeg command
                call_args = mock_run.call_args[0][0]
                assert 'ffmpeg' in call_args
                assert '-i' in call_args
                assert str(temp_path) in call_args
                assert str(output_path) in call_args
                
            finally:
                os.unlink(temp_path)
    
    @patch('subprocess.run')
    def test_extract_audio_ffmpeg_error(self, mock_run):
        """Test audio extraction with FFmpeg error"""
        # Mock FFmpeg error
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "FFmpeg error message"
        mock_run.return_value = mock_result
        
        preprocessor = AudioPreprocessor()
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            f.write(b"Mock video content")
            temp_path = f.name
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "audio.wav"
            
            try:
                with pytest.raises(AudioExtractionError) as exc_info:
                    preprocessor.extract_audio(temp_path, str(output_path))
                
                assert "Output file was not created" in str(exc_info.value)
            finally:
                os.unlink(temp_path)
    
    @patch('subprocess.run')
    def test_extract_audio_timeout(self, mock_run):
        """Test audio extraction timeout"""
        # Mock timeout
        mock_run.side_effect = TimeoutError("Process timed out")
        
        preprocessor = AudioPreprocessor()
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            f.write(b"Mock video content")
            temp_path = f.name
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "audio.wav"
            
            try:
                with pytest.raises(AudioExtractionError) as exc_info:
                    preprocessor.extract_audio(temp_path, str(output_path))
                
                assert "timed out" in str(exc_info.value)
            finally:
                os.unlink(temp_path)
    
    @patch('subprocess.run')
    def test_get_audio_info_success(self, mock_run):
        """Test successful audio info extraction"""
        # Mock FFprobe output
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '''
        {
            "format": {
                "duration": "120.5"
            },
            "streams": [
                {
                    "codec_type": "audio",
                    "sample_rate": "16000",
                    "channels": 1,
                    "codec_name": "pcm_s16le",
                    "bit_rate": "256000"
                }
            ]
        }
        '''
        mock_run.return_value = mock_result
        
        preprocessor = AudioPreprocessor()
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            f.write(b"Mock audio content")
            temp_path = f.name
        
        try:
            info = preprocessor.get_audio_info(temp_path)
            
            assert info['duration'] == 120.5
            assert info['sample_rate'] == 16000
            assert info['channels'] == 1
            assert info['codec'] == 'pcm_s16le'
            assert info['bit_rate'] == 256000
            
        finally:
            os.unlink(temp_path)
    
    @patch('subprocess.run')
    def test_get_audio_info_no_audio_stream(self, mock_run):
        """Test audio info with no audio stream"""
        # Mock FFprobe output with no audio stream
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '''
        {
            "format": {
                "duration": "120.5"
            },
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264"
                }
            ]
        }
        '''
        mock_run.return_value = mock_result
        
        preprocessor = AudioPreprocessor()
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            f.write(b"Mock video content")
            temp_path = f.name
        
        try:
            with pytest.raises(AudioPreprocessingError) as exc_info:
                preprocessor.get_audio_info(temp_path)
            
            assert "No audio stream found" in str(exc_info.value)
        finally:
            os.unlink(temp_path)
    
    @patch('subprocess.run')
    def test_validate_audio_for_whisperx_success(self, mock_run):
        """Test successful audio validation"""
        # Mock FFprobe output for valid audio
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '''
        {
            "format": {
                "duration": "30.0"
            },
            "streams": [
                {
                    "codec_type": "audio",
                    "sample_rate": "16000",
                    "channels": 1,
                    "codec_name": "pcm_s16le"
                }
            ]
        }
        '''
        mock_run.return_value = mock_result
        
        preprocessor = AudioPreprocessor()
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            f.write(b"Mock audio content")
            temp_path = f.name
        
        try:
            result = preprocessor.validate_audio_for_whisperx(temp_path)
            assert result is True
            
        finally:
            os.unlink(temp_path)
    
    @patch('subprocess.run')
    def test_validate_audio_too_short(self, mock_run):
        """Test validation with too short audio"""
        # Mock FFprobe output for very short audio
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '''
        {
            "format": {
                "duration": "0.5"
            },
            "streams": [
                {
                    "codec_type": "audio",
                    "sample_rate": "16000",
                    "channels": 1
                }
            ]
        }
        '''
        mock_run.return_value = mock_result
        
        preprocessor = AudioPreprocessor()
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            f.write(b"Mock audio content")
            temp_path = f.name
        
        try:
            with pytest.raises(AudioPreprocessingError) as exc_info:
                preprocessor.validate_audio_for_whisperx(temp_path)
            
            assert "too short" in str(exc_info.value)
        finally:
            os.unlink(temp_path)
    
    @patch('subprocess.run')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.stat')
    @patch('pathlib.Path.mkdir')
    def test_preprocess_for_whisperx_success(self, mock_mkdir, mock_stat, mock_exists, mock_run):
        """Test complete preprocessing pipeline"""
        # Mock successful FFmpeg execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '''
        {
            "format": {
                "duration": "30.0"
            },
            "streams": [
                {
                    "codec_type": "audio",
                    "sample_rate": "16000",
                    "channels": 1,
                    "codec_name": "pcm_s16le"
                }
            ]
        }
        '''
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        mock_exists.return_value = True
        
        # Mock file size check
        mock_stat_result = MagicMock()
        mock_stat_result.st_size = 1024  # Non-zero file size
        mock_stat.return_value = mock_stat_result
        
        # Mock directory creation
        mock_mkdir.return_value = None
        
        preprocessor = AudioPreprocessor()
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            f.write(b"Mock video content")
            temp_path = f.name
        
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                result = preprocessor.preprocess_for_whisperx(
                    temp_path,
                    temp_dir,
                    sample_rate=16000
                )
                
                assert result.endswith('_whisperx.wav')
                assert Path(result).exists()
                
            finally:
                os.unlink(temp_path)
