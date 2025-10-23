#!/usr/bin/env python3
"""
Unit tests for WhisperX client
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from langflix.asr.whisperx_client import (
    WhisperXClient,
    WhisperXWord,
    WhisperXSegment,
    WhisperXTranscript
)
from langflix.asr.exceptions import (
    WhisperXError,
    ModelLoadError,
    TranscriptionTimeoutError
)


class TestWhisperXClient:
    """Test WhisperX client functionality"""
    
    def test_whisperx_not_available(self):
        """Test behavior when WhisperX is not available"""
        with patch('langflix.asr.whisperx_client.WHISPERX_AVAILABLE', False):
            with pytest.raises(ModelLoadError) as exc_info:
                WhisperXClient()
            
            assert "WhisperX not installed" in str(exc_info.value)
    
    @patch('langflix.asr.whisperx_client.whisperx')
    def test_init_success(self, mock_whisperx):
        """Test successful initialization"""
        mock_whisperx.load_model.return_value = MagicMock()
        
        client = WhisperXClient(
            model_size='base',
            device='cpu',
            compute_type='float32'
        )
        
        assert client.model_size == 'base'
        assert client.device == 'cpu'
        assert client.compute_type == 'float32'
        assert client.language is None
        assert client.batch_size == 16
    
    @patch('langflix.asr.whisperx_client.whisperx')
    def test_init_with_language(self, mock_whisperx):
        """Test initialization with language"""
        mock_whisperx.load_model.return_value = MagicMock()
        
        client = WhisperXClient(language='en')
        assert client.language == 'en'
    
    @patch('langflix.asr.whisperx_client.whisperx')
    def test_init_model_load_error(self, mock_whisperx):
        """Test initialization with model load error"""
        mock_whisperx.load_model.side_effect = Exception("Model load failed")
        
        with pytest.raises(ModelLoadError) as exc_info:
            WhisperXClient()
        
        assert "Failed to load model" in str(exc_info.value)
    
    def create_test_transcript(self) -> WhisperXTranscript:
        """Create test transcript for testing"""
        words = [
            WhisperXWord(word="Hello", start=0.0, end=0.5, score=0.9),
            WhisperXWord(word="world", start=0.5, end=1.0, score=0.8),
            WhisperXWord(word="this", start=1.0, end=1.5, score=0.7),
            WhisperXWord(word="is", start=1.5, end=2.0, score=0.6),
            WhisperXWord(word="a", start=2.0, end=2.2, score=0.5),
            WhisperXWord(word="test", start=2.2, end=2.7, score=0.9),
        ]
        
        segments = [
            WhisperXSegment(
                id=0,
                start=0.0,
                end=2.7,
                text="Hello world this is a test",
                words=words
            )
        ]
        
        return WhisperXTranscript(
            segments=segments,
            language="en",
            duration=2.7,
            word_timestamps=words
        )
    
    @patch('langflix.asr.whisperx_client.whisperx')
    def test_transcribe_with_timestamps_nonexistent_file(self, mock_whisperx):
        """Test transcription with non-existent file"""
        mock_whisperx.load_model.return_value = MagicMock()
        
        client = WhisperXClient()
        
        with pytest.raises(WhisperXError) as exc_info:
            client.transcribe_with_timestamps("/nonexistent/file.wav")
        
        assert "Audio file does not exist" in str(exc_info.value)
    
    @patch('langflix.asr.whisperx_client.whisperx')
    def test_transcribe_with_timestamps_success(self, mock_whisperx):
        """Test successful transcription"""
        # Mock WhisperX components
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            'segments': [
                {
                    'start': 0.0,
                    'end': 2.7,
                    'text': 'Hello world this is a test',
                    'words': [
                        {'word': 'Hello', 'start': 0.0, 'end': 0.5, 'score': 0.9},
                        {'word': 'world', 'start': 0.5, 'end': 1.0, 'score': 0.8},
                        {'word': 'this', 'start': 1.0, 'end': 1.5, 'score': 0.7},
                        {'word': 'is', 'start': 1.5, 'end': 2.0, 'score': 0.6},
                        {'word': 'a', 'start': 2.0, 'end': 2.2, 'score': 0.5},
                        {'word': 'test', 'start': 2.2, 'end': 2.7, 'score': 0.9}
                    ]
                }
            ],
            'language': 'en'
        }
        
        mock_whisperx.load_model.return_value = mock_model
        mock_whisperx.load_audio.return_value = [0.1, 0.2, 0.3]  # Mock audio data
        mock_whisperx.align.return_value = {
            'segments': [
                {
                    'start': 0.0,
                    'end': 2.7,
                    'text': 'Hello world this is a test',
                    'words': [
                        {'word': 'Hello', 'start': 0.0, 'end': 0.5, 'score': 0.9},
                        {'word': 'world', 'start': 0.5, 'end': 1.0, 'score': 0.8},
                        {'word': 'this', 'start': 1.0, 'end': 1.5, 'score': 0.7},
                        {'word': 'is', 'start': 1.5, 'end': 2.0, 'score': 0.6},
                        {'word': 'a', 'start': 2.0, 'end': 2.2, 'score': 0.5},
                        {'word': 'test', 'start': 2.2, 'end': 2.7, 'score': 0.9}
                    ]
                }
            ]
        }
        
        client = WhisperXClient()
        
        with patch('pathlib.Path.exists', return_value=True):
            result = client.transcribe_with_timestamps("/test/audio.wav")
        
        assert isinstance(result, WhisperXTranscript)
        assert result.language == "en"
        assert result.duration == 2.7
        assert len(result.segments) == 1
        assert len(result.word_timestamps) == 6
        assert result.word_timestamps[0].word == "Hello"
        assert result.word_timestamps[0].start == 0.0
        assert result.word_timestamps[0].end == 0.5
    
    @patch('langflix.asr.whisperx_client.whisperx')
    def test_transcribe_with_timestamps_alignment_failure(self, mock_whisperx):
        """Test transcription with alignment failure"""
        # Mock WhisperX components
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            'segments': [
                {
                    'start': 0.0,
                    'end': 2.7,
                    'text': 'Hello world this is a test'
                }
            ],
            'language': 'en'
        }
        
        mock_whisperx.load_model.return_value = mock_model
        mock_whisperx.load_audio.return_value = [0.1, 0.2, 0.3]
        mock_whisperx.align.side_effect = Exception("Alignment failed")
        
        client = WhisperXClient()
        
        with patch('pathlib.Path.exists', return_value=True):
            result = client.transcribe_with_timestamps("/test/audio.wav")
        
        # Should still work with segment-level timestamps
        assert isinstance(result, WhisperXTranscript)
        assert result.language == "en"
        assert len(result.segments) == 1
    
    @patch('langflix.asr.whisperx_client.whisperx')
    def test_transcribe_with_timestamps_error(self, mock_whisperx):
        """Test transcription with error"""
        mock_whisperx.load_model.return_value = MagicMock()
        mock_whisperx.load_audio.side_effect = Exception("Audio load failed")
        
        client = WhisperXClient()
        
        with patch('pathlib.Path.exists', return_value=True):
            with pytest.raises(WhisperXError) as exc_info:
                client.transcribe_with_timestamps("/test/audio.wav")
            
            assert "Transcription failed" in str(exc_info.value)
    
    @patch('langflix.asr.whisperx_client.whisperx')
    def test_find_expression_timestamps(self, mock_whisperx):
        """Test finding expression timestamps"""
        mock_whisperx.load_model.return_value = MagicMock()
        
        client = WhisperXClient()
        transcript = self.create_test_transcript()
        
        matches = client.find_expression_timestamps(transcript, "Hello", context_words=2)
        
        assert len(matches) == 1
        assert matches[0]['expression'] == "Hello"
        assert matches[0]['start_time'] == 0.0
        assert matches[0]['end_time'] == 0.5
        assert matches[0]['confidence'] == 0.9
        assert "Hello" in matches[0]['context']
    
    @patch('langflix.asr.whisperx_client.whisperx')
    def test_find_expression_timestamps_not_found(self, mock_whisperx):
        """Test finding non-existent expression"""
        mock_whisperx.load_model.return_value = MagicMock()
        
        client = WhisperXClient()
        transcript = self.create_test_transcript()
        
        matches = client.find_expression_timestamps(transcript, "nonexistent")
        
        assert len(matches) == 0
    
    @patch('langflix.asr.whisperx_client.whisperx')
    def test_get_device_info(self, mock_whisperx):
        """Test device information"""
        mock_whisperx.load_model.return_value = MagicMock()
        
        client = WhisperXClient(device='cpu', compute_type='float32')
        
        with patch('torch.cuda.is_available', return_value=False):
            info = client.get_device_info()
        
        assert info['device'] == 'cpu'
        assert info['compute_type'] == 'float32'
        assert info['model_size'] == 'base'
        assert info['cuda_available'] is False
    
    @patch('langflix.asr.whisperx_client.whisperx')
    def test_get_device_info_cuda(self, mock_whisperx):
        """Test device information with CUDA"""
        mock_whisperx.load_model.return_value = MagicMock()
        
        client = WhisperXClient(device='cuda')
        
        with patch('torch.cuda.is_available', return_value=True), \
             patch('torch.cuda.device_count', return_value=2), \
             patch('torch.cuda.current_device', return_value=0), \
             patch('torch.cuda.get_device_name', return_value='RTX 3080'):
            
            info = client.get_device_info()
        
        assert info['device'] == 'cuda'
        assert info['cuda_available'] is True
        assert info['cuda_device_count'] == 2
        assert info['cuda_current_device'] == 0
        assert info['cuda_device_name'] == 'RTX 3080'
    
    def test_whisperx_word_creation(self):
        """Test WhisperXWord creation"""
        word = WhisperXWord(
            word="Hello",
            start=0.0,
            end=0.5,
            score=0.9
        )
        
        assert word.word == "Hello"
        assert word.start == 0.0
        assert word.end == 0.5
        assert word.score == 0.9
    
    def test_whisperx_segment_creation(self):
        """Test WhisperXSegment creation"""
        words = [
            WhisperXWord(word="Hello", start=0.0, end=0.5, score=0.9),
            WhisperXWord(word="world", start=0.5, end=1.0, score=0.8)
        ]
        
        segment = WhisperXSegment(
            id=0,
            start=0.0,
            end=1.0,
            text="Hello world",
            words=words
        )
        
        assert segment.id == 0
        assert segment.start == 0.0
        assert segment.end == 1.0
        assert segment.text == "Hello world"
        assert len(segment.words) == 2
        assert segment.words[0].word == "Hello"
    
    def test_whisperx_transcript_creation(self):
        """Test WhisperXTranscript creation"""
        words = [WhisperXWord(word="Hello", start=0.0, end=0.5, score=0.9)]
        segments = [WhisperXSegment(id=0, start=0.0, end=0.5, text="Hello", words=words)]
        
        transcript = WhisperXTranscript(
            segments=segments,
            language="en",
            duration=0.5,
            word_timestamps=words
        )
        
        assert transcript.language == "en"
        assert transcript.duration == 0.5
        assert len(transcript.segments) == 1
        assert len(transcript.word_timestamps) == 1
