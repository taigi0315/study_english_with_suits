#!/usr/bin/env python3
"""
Unit tests for ASR exceptions
"""

import pytest

from langflix.asr.exceptions import (
    AudioExtractionError,
    WhisperXError,
    TimestampAlignmentError,
    ModelLoadError,
    AudioPreprocessingError,
    TranscriptionTimeoutError
)


class TestASRExceptions:
    """Test ASR exception classes"""
    
    def test_audio_extraction_error(self):
        """Test AudioExtractionError"""
        error = AudioExtractionError("/path/to/file.mp4", "FFmpeg failed")
        
        assert error.media_path == "/path/to/file.mp4"
        assert error.reason == "FFmpeg failed"
        assert "Failed to extract audio from '/path/to/file.mp4'" in str(error)
        assert "FFmpeg failed" in str(error)
    
    def test_audio_extraction_error_no_reason(self):
        """Test AudioExtractionError without reason"""
        error = AudioExtractionError("/path/to/file.mp4")
        
        assert error.media_path == "/path/to/file.mp4"
        assert error.reason == ""
        assert "Failed to extract audio from '/path/to/file.mp4'" in str(error)
    
    def test_whisperx_error(self):
        """Test WhisperXError"""
        error = WhisperXError("/path/to/audio.wav", "Model not loaded")
        
        assert error.audio_path == "/path/to/audio.wav"
        assert error.reason == "Model not loaded"
        assert "WhisperX transcription failed for '/path/to/audio.wav'" in str(error)
        assert "Model not loaded" in str(error)
    
    def test_whisperx_error_no_reason(self):
        """Test WhisperXError without reason"""
        error = WhisperXError("/path/to/audio.wav")
        
        assert error.audio_path == "/path/to/audio.wav"
        assert error.reason == ""
        assert "WhisperX transcription failed for '/path/to/audio.wav'" in str(error)
    
    def test_timestamp_alignment_error(self):
        """Test TimestampAlignmentError"""
        error = TimestampAlignmentError("get screwed", "No matching words found")
        
        assert error.expression == "get screwed"
        assert error.reason == "No matching words found"
        assert "Failed to align timestamps for expression 'get screwed'" in str(error)
        assert "No matching words found" in str(error)
    
    def test_timestamp_alignment_error_no_reason(self):
        """Test TimestampAlignmentError without reason"""
        error = TimestampAlignmentError("get screwed")
        
        assert error.expression == "get screwed"
        assert error.reason == ""
        assert "Failed to align timestamps for expression 'get screwed'" in str(error)
    
    def test_model_load_error(self):
        """Test ModelLoadError"""
        error = ModelLoadError("whisperx-base", "CUDA not available")
        
        assert error.model_name == "whisperx-base"
        assert error.reason == "CUDA not available"
        assert "Failed to load WhisperX model 'whisperx-base'" in str(error)
        assert "CUDA not available" in str(error)
    
    def test_model_load_error_no_reason(self):
        """Test ModelLoadError without reason"""
        error = ModelLoadError("whisperx-base")
        
        assert error.model_name == "whisperx-base"
        assert error.reason == ""
        assert "Failed to load WhisperX model 'whisperx-base'" in str(error)
    
    def test_audio_preprocessing_error(self):
        """Test AudioPreprocessingError"""
        error = AudioPreprocessingError("/path/to/audio.wav", "Invalid format")
        
        assert error.audio_path == "/path/to/audio.wav"
        assert error.reason == "Invalid format"
        assert "Audio preprocessing failed for '/path/to/audio.wav'" in str(error)
        assert "Invalid format" in str(error)
    
    def test_audio_preprocessing_error_no_reason(self):
        """Test AudioPreprocessingError without reason"""
        error = AudioPreprocessingError("/path/to/audio.wav")
        
        assert error.audio_path == "/path/to/audio.wav"
        assert error.reason == ""
        assert "Audio preprocessing failed for '/path/to/audio.wav'" in str(error)
    
    def test_transcription_timeout_error(self):
        """Test TranscriptionTimeoutError"""
        error = TranscriptionTimeoutError("/path/to/audio.wav", 300)
        
        assert error.audio_path == "/path/to/audio.wav"
        assert error.timeout_seconds == 300
        assert "Transcription timeout after 300s for '/path/to/audio.wav'" in str(error)
    
    def test_exception_inheritance(self):
        """Test that exceptions inherit from correct base classes"""
        assert issubclass(AudioExtractionError, Exception)
        assert issubclass(WhisperXError, Exception)
        assert issubclass(TimestampAlignmentError, Exception)
        assert issubclass(ModelLoadError, Exception)
        assert issubclass(AudioPreprocessingError, Exception)
        assert issubclass(TranscriptionTimeoutError, Exception)
    
    def test_exception_attributes(self):
        """Test that exceptions have correct attributes"""
        # Test AudioExtractionError attributes
        error = AudioExtractionError("path", "reason")
        assert hasattr(error, 'media_path')
        assert hasattr(error, 'reason')
        
        # Test WhisperXError attributes
        error = WhisperXError("path", "reason")
        assert hasattr(error, 'audio_path')
        assert hasattr(error, 'reason')
        
        # Test TimestampAlignmentError attributes
        error = TimestampAlignmentError("expr", "reason")
        assert hasattr(error, 'expression')
        assert hasattr(error, 'reason')
        assert hasattr(error, 'line_number')
        
        # Test ModelLoadError attributes
        error = ModelLoadError("model", "reason")
        assert hasattr(error, 'model_name')
        assert hasattr(error, 'reason')
        
        # Test AudioPreprocessingError attributes
        error = AudioPreprocessingError("path", "reason")
        assert hasattr(error, 'audio_path')
        assert hasattr(error, 'reason')
        
        # Test TranscriptionTimeoutError attributes
        error = TranscriptionTimeoutError("path", 300)
        assert hasattr(error, 'audio_path')
        assert hasattr(error, 'timeout_seconds')
    
    def test_timestamp_alignment_error_with_line_number(self):
        """Test TimestampAlignmentError with line number"""
        error = TimestampAlignmentError("get screwed", "Invalid format", line_number=5)
        
        assert error.expression == "get screwed"
        assert error.reason == "Invalid format"
        assert error.line_number == 5
        assert "line 5" in str(error)
    
    def test_timestamp_alignment_error_without_line_number(self):
        """Test TimestampAlignmentError without line number"""
        error = TimestampAlignmentError("get screwed", "Invalid format")
        
        assert error.expression == "get screwed"
        assert error.reason == "Invalid format"
        assert error.line_number is None
        assert "line" not in str(error)
