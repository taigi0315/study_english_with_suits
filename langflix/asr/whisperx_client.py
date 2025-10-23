#!/usr/bin/env python3
"""
WhisperX client for precise timestamp detection

This module provides WhisperX integration for automatic speech recognition
with word-level timestamp alignment.
"""

import logging
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from pathlib import Path
import torch

from langflix.asr.exceptions import (
    WhisperXError,
    ModelLoadError,
    TranscriptionTimeoutError
)
from langflix.core.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)

# Try to import WhisperX, handle gracefully if not available
try:
    import whisperx
    WHISPERX_AVAILABLE = True
except ImportError:
    WHISPERX_AVAILABLE = False
    whisperx = None


@dataclass
class WhisperXWord:
    """Word-level timestamp from WhisperX"""
    word: str
    start: float
    end: float
    score: float  # Confidence score


@dataclass
class WhisperXSegment:
    """Segment with word-level timestamps"""
    id: int
    start: float
    end: float
    text: str
    words: List[WhisperXWord]


@dataclass
class WhisperXTranscript:
    """Complete WhisperX transcription result"""
    segments: List[WhisperXSegment]
    language: str
    duration: float
    word_timestamps: List[WhisperXWord]


class WhisperXClient:
    """
    WhisperX client for precise timestamp detection
    
    This class provides:
    - Audio transcription with WhisperX
    - Word-level timestamp alignment
    - Language detection
    - Confidence scoring
    """
    
    def __init__(
        self,
        model_size: str = 'base',
        device: str = 'cpu',
        compute_type: str = 'float32',
        language: Optional[str] = None,
        batch_size: int = 16
    ):
        """
        Initialize WhisperX client
        
        Args:
            model_size: Model size (tiny, base, small, medium, large-v2)
            device: Device to use (cpu, cuda, mps)
            compute_type: Compute type (int8, float16, float32)
            language: Force language (None for auto-detect)
            batch_size: Batch size for processing
        """
        self.cache_manager = get_cache_manager()
        if not WHISPERX_AVAILABLE:
            raise ModelLoadError(
                "whisperx",
                "WhisperX not installed. Install with: pip install whisperx"
            )
        
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.batch_size = batch_size
        
        # Model components
        self.model = None
        self.alignment_model = None
        self.metadata = None
        
        # Initialize model
        self._load_model()
    
    def _load_model(self) -> None:
        """Load WhisperX model and alignment components"""
        try:
            logger.info(f"Loading WhisperX model: {self.model_size} on {self.device}")
            
            # Load main transcription model
            self.model = whisperx.load_model(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            
            logger.info("WhisperX model loaded successfully")
            
        except Exception as e:
            raise ModelLoadError(
                self.model_size,
                f"Failed to load model: {str(e)}"
            )
    
    def _load_alignment_model(self, language_code: str) -> None:
        """Load alignment model for word-level timestamps"""
        try:
            if self.alignment_model is None or self.metadata is None:
                logger.info(f"Loading alignment model for language: {language_code}")
                
                self.alignment_model, self.metadata = whisperx.load_align_model(
                    language_code=language_code,
                    device=self.device
                )
                
                logger.info("Alignment model loaded successfully")
                
        except Exception as e:
            logger.warning(f"Failed to load alignment model: {e}")
            # Continue without alignment - will use segment-level timestamps
    
    def transcribe_with_timestamps(
        self,
        audio_path: str,
        language: Optional[str] = None,
        timeout_seconds: int = 300
    ) -> WhisperXTranscript:
        """
        Transcribe audio with word-level timestamps (with caching)
        
        Args:
            audio_path: Path to audio file
            language: Force language (None for auto-detect)
            timeout_seconds: Timeout for transcription
            
        Returns:
            WhisperXTranscript with word-level timestamps
            
        Raises:
            WhisperXError: If transcription fails
            TranscriptionTimeoutError: If transcription times out
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise WhisperXError(
                str(audio_path),
                "Audio file does not exist"
            )
        
        # Check cache first
        cache_key = self.cache_manager.get_whisperx_key(
            str(audio_path), 
            self.model_size, 
            language or "auto"
        )
        cached_result = self.cache_manager.get(cache_key)
        
        if cached_result and isinstance(cached_result, dict):
            logger.info(f"Using cached WhisperX result for: {audio_path}")
            return self._parse_result(cached_result, cached_result.get('language', 'en'))
        
        try:
            logger.info(f"Starting WhisperX transcription: {audio_path}")
            
            # Load audio
            audio = whisperx.load_audio(str(audio_path))
            logger.debug(f"Audio loaded: {len(audio)} samples")
            
            # Step 1: Transcribe with WhisperX
            logger.info("Transcribing audio...")
            result = self.model.transcribe(
                audio,
                language=language or self.language,
                batch_size=self.batch_size
            )
            
            detected_language = result.get('language', 'unknown')
            logger.info(f"Detected language: {detected_language}")
            
            # Step 2: Align timestamps (word-level)
            logger.info("Aligning word-level timestamps...")
            try:
                self._load_alignment_model(detected_language)
                
                aligned_result = whisperx.align(
                    result['segments'],
                    self.alignment_model,
                    self.metadata,
                    audio,
                    self.device,
                    return_char_alignments=False
                )
                
                logger.info("Word-level alignment completed")
                
            except Exception as e:
                logger.warning(f"Alignment failed, using segment-level timestamps: {e}")
                aligned_result = result
            
            # Parse results
            transcript = self._parse_result(aligned_result, detected_language)
            
            # Cache the result
            cache_data = {
                'segments': [asdict(seg) for seg in transcript.segments],
                'word_timestamps': [asdict(word) for word in transcript.word_timestamps],
                'language': transcript.language,
                'duration': transcript.duration
            }
            self.cache_manager.set(cache_key, cache_data, ttl=86400, persist_to_disk=True)  # 24 hours
            
            logger.info(f"Transcription complete: {len(transcript.segments)} segments, "
                       f"{len(transcript.word_timestamps)} words")
            
            return transcript
            
        except Exception as e:
            if "timeout" in str(e).lower():
                raise TranscriptionTimeoutError(str(audio_path), timeout_seconds)
            raise WhisperXError(
                str(audio_path),
                f"Transcription failed: {str(e)}"
            )
    
    def _parse_result(
        self,
        result: Dict[str, Any],
        language: str
    ) -> WhisperXTranscript:
        """Parse WhisperX result into our data structure"""
        segments = []
        all_words = []
        
        # Calculate total duration
        duration = 0.0
        if result.get('segments'):
            duration = max(seg.get('end', 0) for seg in result['segments'])
        
        for i, seg in enumerate(result.get('segments', [])):
            words = []
            
            # Extract word-level timestamps if available
            if 'words' in seg:
                for word_data in seg['words']:
                    word = WhisperXWord(
                        word=word_data.get('word', '').strip(),
                        start=word_data.get('start', 0.0),
                        end=word_data.get('end', 0.0),
                        score=word_data.get('score', 1.0)
                    )
                    words.append(word)
                    all_words.append(word)
            
            # Create segment
            segment = WhisperXSegment(
                id=i,
                start=seg.get('start', 0.0),
                end=seg.get('end', 0.0),
                text=seg.get('text', '').strip(),
                words=words
            )
            segments.append(segment)
        
        return WhisperXTranscript(
            segments=segments,
            language=language,
            duration=duration,
            word_timestamps=all_words
        )
    
    def find_expression_timestamps(
        self,
        transcript: WhisperXTranscript,
        expression: str,
        context_words: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find timestamps for a specific expression in the transcript
        
        Args:
            transcript: WhisperX transcript
            expression: Expression to find
            context_words: Number of words to include as context
            
        Returns:
            List of matches with timestamps and context
        """
        expression_lower = expression.lower().strip()
        matches = []
        
        # Search through all words
        for i, word in enumerate(transcript.word_timestamps):
            # Check if this word starts the expression
            if word.word.lower().startswith(expression_lower.split()[0]):
                # Try to match the full expression
                match_text = ""
                match_words = []
                start_idx = i
                
                # Collect words to match against expression
                for j in range(i, min(i + len(expression_lower.split()) + 2, len(transcript.word_timestamps))):
                    if j < len(transcript.word_timestamps):
                        match_words.append(transcript.word_timestamps[j])
                        match_text += transcript.word_timestamps[j].word + " "
                
                match_text = match_text.strip().lower()
                
                # Check if we have a match
                if expression_lower in match_text:
                    # Find the end of the expression
                    end_idx = start_idx + len(expression_lower.split()) - 1
                    if end_idx < len(transcript.word_timestamps):
                        start_time = word.start
                        end_time = transcript.word_timestamps[end_idx].end
                        
                        # Get context words
                        context_start = max(0, start_idx - context_words)
                        context_end = min(len(transcript.word_timestamps), end_idx + context_words + 1)
                        
                        context_words_list = transcript.word_timestamps[context_start:context_end]
                        context_text = " ".join(w.word for w in context_words_list)
                        
                        matches.append({
                            'expression': expression,
                            'start_time': start_time,
                            'end_time': end_time,
                            'confidence': min(w.score for w in match_words[:len(expression_lower.split())]),
                            'context': context_text,
                            'context_start': context_words_list[0].start if context_words_list else start_time,
                            'context_end': context_words_list[-1].end if context_words_list else end_time
                        })
        
        logger.info(f"Found {len(matches)} matches for expression '{expression}'")
        return matches
    
    def get_device_info(self) -> Dict[str, Any]:
        """Get information about available devices"""
        info = {
            'device': self.device,
            'compute_type': self.compute_type,
            'model_size': self.model_size
        }
        
        if torch.cuda.is_available():
            info['cuda_available'] = True
            info['cuda_device_count'] = torch.cuda.device_count()
            if torch.cuda.is_available():
                info['cuda_current_device'] = torch.cuda.current_device()
                info['cuda_device_name'] = torch.cuda.get_device_name()
        else:
            info['cuda_available'] = False
        
        return info
