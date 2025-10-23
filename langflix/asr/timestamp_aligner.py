#!/usr/bin/env python3
"""
Timestamp alignment for expressions

This module provides precise timestamp alignment for expressions using
WhisperX word-level timestamps and fuzzy matching.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher

from langflix.core.models import ExpressionAnalysis
from langflix.asr.whisperx_client import WhisperXTranscript, WhisperXWord
from langflix.asr.exceptions import TimestampAlignmentError

logger = logging.getLogger(__name__)


@dataclass
class AlignedExpression:
    """Expression with precise timestamps"""
    expression: str
    start_time: float
    end_time: float
    confidence: float
    context_start: float
    context_end: float
    matched_words: List[WhisperXWord]
    alignment_score: float


class TimestampAligner:
    """
    Align expressions with precise timestamps using WhisperX
    
    This class provides:
    - Expression-to-audio alignment
    - Fuzzy matching for expression variations
    - Confidence scoring
    - Context extraction
    """
    
    def __init__(
        self,
        fuzzy_threshold: float = 0.85,
        context_buffer: float = 0.5
    ):
        """
        Initialize timestamp aligner
        
        Args:
            fuzzy_threshold: Minimum similarity for fuzzy matching (0-1)
            context_buffer: Buffer time around expression (seconds)
        """
        self.fuzzy_threshold = fuzzy_threshold
        self.context_buffer = context_buffer
    
    def align_expressions(
        self,
        expressions: List[ExpressionAnalysis],
        transcript: WhisperXTranscript
    ) -> List[AlignedExpression]:
        """
        Align multiple expressions with timestamps
        
        Args:
            expressions: List of expressions to align
            transcript: WhisperX transcript with word timestamps
            
        Returns:
            List of aligned expressions with timestamps
        """
        aligned_expressions = []
        
        for expression in expressions:
            try:
                aligned = self.align_single_expression(expression, transcript)
                if aligned:
                    aligned_expressions.append(aligned)
                    logger.info(f"Aligned expression '{expression.expression}': "
                              f"{aligned.start_time:.2f}s - {aligned.end_time:.2f}s")
                else:
                    logger.warning(f"Could not align expression: '{expression.expression}'")
                    
            except Exception as e:
                logger.error(f"Failed to align expression '{expression.expression}': {e}")
                continue
        
        logger.info(f"Successfully aligned {len(aligned_expressions)}/{len(expressions)} expressions")
        return aligned_expressions
    
    def align_single_expression(
        self,
        expression: ExpressionAnalysis,
        transcript: WhisperXTranscript
    ) -> Optional[AlignedExpression]:
        """
        Align a single expression with timestamps
        
        Args:
            expression: Expression to align
            transcript: WhisperX transcript
            
        Returns:
            Aligned expression with timestamps, or None if not found
        """
        expression_text = expression.expression.strip()
        
        # Try exact match first
        exact_match = self._find_exact_match(expression_text, transcript)
        if exact_match:
            return self._create_aligned_expression(expression, exact_match, 1.0)
        
        # Try fuzzy match
        fuzzy_match = self._find_fuzzy_match(expression_text, transcript)
        if fuzzy_match:
            return self._create_aligned_expression(expression, fuzzy_match, fuzzy_match['score'])
        
        # Try partial match
        partial_match = self._find_partial_match(expression_text, transcript)
        if partial_match:
            return self._create_aligned_expression(expression, partial_match, partial_match['score'])
        
        return None
    
    def _find_exact_match(
        self,
        expression: str,
        transcript: WhisperXTranscript
    ) -> Optional[Dict[str, Any]]:
        """Find exact match for expression"""
        expression_lower = expression.lower()
        
        for i, word in enumerate(transcript.word_timestamps):
            if word.word.lower() == expression_lower:
                return {
                    'start_time': word.start,
                    'end_time': word.end,
                    'matched_words': [word],
                    'score': word.score
                }
        
        return None
    
    def _find_fuzzy_match(
        self,
        expression: str,
        transcript: WhisperXTranscript
    ) -> Optional[Dict[str, Any]]:
        """Find fuzzy match for expression"""
        expression_lower = expression.lower()
        words = expression_lower.split()
        
        best_match = None
        best_score = 0.0
        
        # Try different starting positions
        for i in range(len(transcript.word_timestamps) - len(words) + 1):
            # Extract candidate sequence
            candidate_words = transcript.word_timestamps[i:i + len(words)]
            candidate_text = " ".join(w.word.lower() for w in candidate_words)
            
            # Calculate similarity
            similarity = SequenceMatcher(None, expression_lower, candidate_text).ratio()
            
            if similarity >= self.fuzzy_threshold and similarity > best_score:
                best_score = similarity
                best_match = {
                    'start_time': candidate_words[0].start,
                    'end_time': candidate_words[-1].end,
                    'matched_words': candidate_words,
                    'score': similarity
                }
        
        return best_match
    
    def _find_partial_match(
        self,
        expression: str,
        transcript: WhisperXTranscript
    ) -> Optional[Dict[str, Any]]:
        """Find partial match for expression (some words match)"""
        expression_words = expression.lower().split()
        
        best_match = None
        best_score = 0.0
        
        # Try different window sizes
        for window_size in range(len(expression_words), 0, -1):
            for i in range(len(transcript.word_timestamps) - window_size + 1):
                candidate_words = transcript.word_timestamps[i:i + window_size]
                candidate_text = " ".join(w.word.lower() for w in candidate_words)
                
                # Calculate partial similarity
                similarity = self._calculate_partial_similarity(expression_words, candidate_text)
                
                if similarity >= self.fuzzy_threshold * 0.8 and similarity > best_score:
                    best_score = similarity
                    best_match = {
                        'start_time': candidate_words[0].start,
                        'end_time': candidate_words[-1].end,
                        'matched_words': candidate_words,
                        'score': similarity
                    }
        
        return best_match
    
    def _calculate_partial_similarity(
        self,
        expression_words: List[str],
        candidate_text: str
    ) -> float:
        """Calculate similarity for partial matches"""
        candidate_words = candidate_text.split()
        
        # Count matching words
        matches = 0
        for expr_word in expression_words:
            for cand_word in candidate_words:
                if expr_word in cand_word or cand_word in expr_word:
                    matches += 1
                    break
        
        return matches / len(expression_words)
    
    def _create_aligned_expression(
        self,
        expression: ExpressionAnalysis,
        match: Dict[str, Any],
        alignment_score: float
    ) -> AlignedExpression:
        """Create aligned expression from match data"""
        
        # Add context buffer
        context_start = max(0.0, match['start_time'] - self.context_buffer)
        context_end = match['end_time'] + self.context_buffer
        
        return AlignedExpression(
            expression=expression.expression,
            start_time=match['start_time'],
            end_time=match['end_time'],
            confidence=match['score'],
            context_start=context_start,
            context_end=context_end,
            matched_words=match['matched_words'],
            alignment_score=alignment_score
        )
    
    def find_expression_in_segment(
        self,
        expression: str,
        segment_text: str,
        segment_start: float,
        segment_end: float
    ) -> Optional[Dict[str, Any]]:
        """
        Find expression within a specific segment
        
        Args:
            expression: Expression to find
            segment_text: Text of the segment
            segment_start: Start time of segment
            segment_end: End time of segment
            
        Returns:
            Match data if found, None otherwise
        """
        expression_lower = expression.lower()
        segment_lower = segment_text.lower()
        
        # Check if expression is in segment
        if expression_lower in segment_lower:
            # Simple proportional positioning
            start_pos = segment_lower.find(expression_lower)
            end_pos = start_pos + len(expression_lower)
            
            # Calculate proportional times
            segment_duration = segment_end - segment_start
            text_length = len(segment_text)
            
            if text_length > 0:
                start_ratio = start_pos / text_length
                end_ratio = end_pos / text_length
                
                return {
                    'start_time': segment_start + (start_ratio * segment_duration),
                    'end_time': segment_start + (end_ratio * segment_duration),
                    'confidence': 0.8,  # Medium confidence for proportional positioning
                    'method': 'proportional'
                }
        
        return None
    
    def get_alignment_statistics(
        self,
        aligned_expressions: List[AlignedExpression]
    ) -> Dict[str, Any]:
        """Get statistics about alignment quality"""
        if not aligned_expressions:
            return {
                'total_expressions': 0,
                'average_confidence': 0.0,
                'average_alignment_score': 0.0,
                'high_confidence_count': 0,
                'low_confidence_count': 0
            }
        
        confidences = [expr.confidence for expr in aligned_expressions]
        alignment_scores = [expr.alignment_score for expr in aligned_expressions]
        
        return {
            'total_expressions': len(aligned_expressions),
            'average_confidence': sum(confidences) / len(confidences),
            'average_alignment_score': sum(alignment_scores) / len(alignment_scores),
            'high_confidence_count': sum(1 for c in confidences if c >= 0.8),
            'low_confidence_count': sum(1 for c in confidences if c < 0.5),
            'min_confidence': min(confidences),
            'max_confidence': max(confidences)
        }
