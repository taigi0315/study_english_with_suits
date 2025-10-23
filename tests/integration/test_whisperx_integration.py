#!/usr/bin/env python3
"""
Integration tests for WhisperX ASR pipeline

This module tests the complete WhisperX integration including:
- Audio preprocessing
- WhisperX transcription
- Timestamp alignment
- Expression extraction and alignment
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from langflix.asr.audio_preprocessor import AudioPreprocessor
from langflix.asr.whisperx_client import WhisperXClient
from langflix.asr.timestamp_aligner import TimestampAligner
from langflix.core.models import ExpressionAnalysis
from langflix.asr.exceptions import (
    AudioExtractionError,
    WhisperXError,
    TimestampAlignmentError
)


class TestWhisperXIntegration:
    """Test complete WhisperX integration pipeline"""
    
    def test_audio_preprocessing_pipeline(self):
        """Test audio preprocessing for WhisperX"""
        preprocessor = AudioPreprocessor()
        
        # Create a mock video file
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            f.write(b"Mock video content")
            temp_path = f.name
        
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Test audio extraction
                output_path = Path(temp_dir) / "audio.wav"
                
                with patch('subprocess.run') as mock_run:
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_result.stdout = "FFmpeg output"
                    mock_result.stderr = ""
                    mock_run.return_value = mock_result
                    
                    with patch('pathlib.Path.exists') as mock_exists:
                        mock_exists.return_value = True
                        
                        with patch('pathlib.Path.stat') as mock_stat:
                            mock_stat_result = MagicMock()
                            mock_stat_result.st_size = 1024
                            mock_stat.return_value = mock_stat_result
                            
                            with patch('pathlib.Path.mkdir'):
                                result = preprocessor.extract_audio(
                                    temp_path, 
                                    str(output_path)
                                )
                                
                                assert result == str(output_path)
                                mock_run.assert_called_once()
                
            finally:
                os.unlink(temp_path)
    
    def test_whisperx_transcription_pipeline(self):
        """Test WhisperX transcription with mocked model"""
        with patch('whisperx.load_model') as mock_load_model:
            with patch('whisperx.load_align_model') as mock_load_align:
                with patch('whisperx.align') as mock_align:
                    with patch('whisperx.load_audio') as mock_load_audio:
                        with patch('pathlib.Path.exists') as mock_exists:
                            # Mock model loading
                            mock_model = MagicMock()
                            mock_align_model = MagicMock()
                            mock_load_model.return_value = mock_model
                            mock_load_align.return_value = mock_align_model
                            
                            # Mock audio loading
                            mock_load_audio.return_value = [0.1, 0.2, 0.3]  # Mock audio array
                            
                            # Mock file existence
                            mock_exists.return_value = True
                            
                            # Mock transcription result
                            mock_transcription = {
                                'segments': [
                                    {
                                        'id': 0,
                                        'start': 0.0,
                                        'end': 2.0,
                                        'text': 'Hello world',
                                        'words': [
                                            {'word': 'Hello', 'start': 0.0, 'end': 0.5, 'score': 0.9},
                                            {'word': 'world', 'start': 0.5, 'end': 1.0, 'score': 0.8}
                                        ]
                                    }
                                ],
                                'language': 'en'
                            }
                            
                            # Mock model transcribe method
                            mock_model.transcribe.return_value = mock_transcription
                            
                            # Mock align method
                            mock_align.return_value = mock_transcription
                            
                            client = WhisperXClient()
                            
                            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                                f.write(b"Mock audio content")
                                temp_audio = f.name
                            
                            try:
                                result = client.transcribe_with_timestamps(temp_audio)
                                
                                assert result is not None
                                assert result.language == 'en'
                                assert len(result.segments) == 1
                                assert result.segments[0].text == 'Hello world'
                                assert len(result.word_timestamps) == 2
                                
                            finally:
                                os.unlink(temp_audio)
    
    def test_timestamp_alignment_pipeline(self):
        """Test timestamp alignment with expressions"""
        aligner = TimestampAligner()
        
        # Create test transcript
        from langflix.asr.whisperx_client import WhisperXWord, WhisperXSegment, WhisperXTranscript
        
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
        
        transcript = WhisperXTranscript(
            segments=segments,
            language="en",
            duration=2.7,
            word_timestamps=words
        )
        
        # Create test expressions
        expressions = [
            ExpressionAnalysis(
                dialogues=["Hello"],
                translation=["안녕하세요"],
                expression_dialogue="Hello",
                expression_dialogue_translation="안녕하세요",
                expression="Hello",
                expression_translation="안녕하세요",
                context_start_time="00:00:00,000",
                context_end_time="00:00:01,000",
                similar_expressions=["Hi", "Hey"]
            ),
            ExpressionAnalysis(
                dialogues=["test"],
                translation=["테스트"],
                expression_dialogue="test",
                expression_dialogue_translation="테스트",
                expression="test",
                expression_translation="테스트",
                context_start_time="00:00:02,000",
                context_end_time="00:00:03,000",
                similar_expressions=["exam", "trial"]
            )
        ]
        
        # Test alignment
        aligned_expressions = aligner.align_expressions(expressions, transcript)
        
        assert len(aligned_expressions) == 2
        assert aligned_expressions[0].expression == "Hello"
        assert aligned_expressions[0].start_time == 0.0
        assert aligned_expressions[0].end_time == 0.5
        assert aligned_expressions[1].expression == "test"
        assert aligned_expressions[1].start_time == 2.2
        assert aligned_expressions[1].end_time == 2.7
    
    def test_complete_pipeline_integration(self):
        """Test complete WhisperX pipeline integration"""
        with patch('whisperx.load_model') as mock_load_model:
            with patch('whisperx.load_align_model') as mock_load_align:
                with patch('whisperx.align') as mock_align:
                    with patch('whisperx.load_audio') as mock_load_audio:
                        with patch('subprocess.run') as mock_run:
                            with patch('pathlib.Path.exists') as mock_exists:
                                # Mock model loading
                                mock_model = MagicMock()
                                mock_align_model = MagicMock()
                                mock_load_model.return_value = mock_model
                                mock_load_align.return_value = mock_align_model
                                
                                # Mock audio loading
                                mock_load_audio.return_value = [0.1, 0.2, 0.3]  # Mock audio array
                                
                                # Mock file existence
                                mock_exists.return_value = True
                                
                                # Mock transcription result
                                mock_transcription = {
                                    'segments': [
                                        {
                                            'id': 0,
                                            'start': 0.0,
                                            'end': 2.0,
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
                                
                                # Mock model transcribe method
                                mock_model.transcribe.return_value = mock_transcription
                                
                                # Mock align method
                                mock_align.return_value = mock_transcription
                                
                                # Mock FFmpeg execution
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
                                
                                # Initialize components
                                preprocessor = AudioPreprocessor()
                                client = WhisperXClient()
                                aligner = TimestampAligner()
                                
                                # Create test video
                                with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
                                    f.write(b"Mock video content")
                                    temp_video = f.name
                                
                                with tempfile.TemporaryDirectory() as temp_dir:
                                    try:
                                        # Step 1: Audio preprocessing
                                        with patch('pathlib.Path.stat') as mock_stat:
                                            mock_stat_result = MagicMock()
                                            mock_stat_result.st_size = 1024
                                            mock_stat.return_value = mock_stat_result
                                            
                                            with patch('pathlib.Path.mkdir'):
                                                audio_path = preprocessor.preprocess_for_whisperx(
                                                    temp_video,
                                                    temp_dir
                                                )
                                                
                                                assert audio_path.endswith('_whisperx.wav')
                                        
                                        # Step 2: WhisperX transcription
                                        transcript = client.transcribe_with_timestamps(audio_path)
                                        
                                        assert transcript is not None
                                        assert transcript.language == 'en'
                                        assert len(transcript.segments) == 1
                                        
                                        # Step 3: Expression alignment
                                        expressions = [
                                            ExpressionAnalysis(
                                                dialogues=["Hello"],
                                                translation=["안녕하세요"],
                                                expression_dialogue="Hello",
                                                expression_dialogue_translation="안녕하세요",
                                                expression="Hello",
                                                expression_translation="안녕하세요",
                                                context_start_time="00:00:00,000",
                                                context_end_time="00:00:01,000",
                                                similar_expressions=["Hi", "Hey"]
                                            ),
                                            ExpressionAnalysis(
                                                dialogues=["test"],
                                                translation=["테스트"],
                                                expression_dialogue="test",
                                                expression_dialogue_translation="테스트",
                                                expression="test",
                                                expression_translation="테스트",
                                                context_start_time="00:00:02,000",
                                                context_end_time="00:00:03,000",
                                                similar_expressions=["exam", "trial"]
                                            )
                                        ]
                                        
                                        aligned_expressions = aligner.align_expressions(
                                            expressions, 
                                            transcript
                                        )
                                        
                                        assert len(aligned_expressions) == 2
                                        assert aligned_expressions[0].expression == "Hello"
                                        assert aligned_expressions[1].expression == "test"
                                        
                                    finally:
                                        os.unlink(temp_video)
    
    def test_error_handling_integration(self):
        """Test error handling across the pipeline"""
        preprocessor = AudioPreprocessor()
        
        # Test audio extraction error
        with pytest.raises(AudioExtractionError):
            preprocessor.extract_audio("/nonexistent/file.mp4", "/output/audio.wav")
        
        # Test unsupported format
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"Not a video file")
            temp_path = f.name
        
        try:
            with pytest.raises(AudioExtractionError):
                preprocessor.extract_audio(temp_path, "/output/audio.wav")
        finally:
            os.unlink(temp_path)
    
    def test_performance_metrics(self):
        """Test performance metrics collection"""
        aligner = TimestampAligner()
        
        # Create test data
        from langflix.asr.whisperx_client import WhisperXWord, WhisperXSegment, WhisperXTranscript
        
        words = [
            WhisperXWord(word="Hello", start=0.0, end=0.5, score=0.9),
            WhisperXWord(word="world", start=0.5, end=1.0, score=0.8),
        ]
        
        segments = [
            WhisperXSegment(
                id=0,
                start=0.0,
                end=1.0,
                text="Hello world",
                words=words
            )
        ]
        
        transcript = WhisperXTranscript(
            segments=segments,
            language="en",
            duration=1.0,
            word_timestamps=words
        )
        
        expressions = [
            ExpressionAnalysis(
                dialogues=["Hello"],
                translation=["안녕하세요"],
                expression_dialogue="Hello",
                expression_dialogue_translation="안녕하세요",
                expression="Hello",
                expression_translation="안녕하세요",
                context_start_time="00:00:00,000",
                context_end_time="00:00:01,000",
                similar_expressions=["Hi", "Hey"]
            )
        ]
        
        # Test alignment
        aligned_expressions = aligner.align_expressions(expressions, transcript)
        
        # Test statistics
        stats = aligner.get_alignment_statistics(aligned_expressions)
        
        assert stats['total_expressions'] == 1
        assert stats['average_confidence'] == 0.9
        assert stats['high_confidence_count'] == 1
        assert stats['low_confidence_count'] == 0
