#!/usr/bin/env python3
"""
Unit tests for timestamp alignment
"""

import pytest
from unittest.mock import MagicMock

from langflix.asr.timestamp_aligner import TimestampAligner, AlignedExpression
from langflix.asr.whisperx_client import WhisperXTranscript, WhisperXSegment, WhisperXWord
from langflix.core.models import ExpressionAnalysis


class TestTimestampAligner:
    """Test timestamp alignment functionality"""
    
    def test_init(self):
        """Test TimestampAligner initialization"""
        aligner = TimestampAligner()
        assert aligner.fuzzy_threshold == 0.85
        assert aligner.context_buffer == 0.5
    
    def test_init_custom_params(self):
        """Test initialization with custom parameters"""
        aligner = TimestampAligner(fuzzy_threshold=0.9, context_buffer=1.0)
        assert aligner.fuzzy_threshold == 0.9
        assert aligner.context_buffer == 1.0
    
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
    
    def create_test_expression(self, expression: str) -> ExpressionAnalysis:
        """Create test expression for testing"""
        return ExpressionAnalysis(
            dialogues=["Test dialogue"],
            translation=["테스트 대화"],
            expression_dialogue="Test dialogue",
            expression_dialogue_translation="테스트 대화",
            expression=expression,
            expression_translation="테스트",
            context_start_time="00:00:01,000",
            context_end_time="00:00:02,000",
            similar_expressions=["similar 1"]
        )
    
    def test_align_single_expression_exact_match(self):
        """Test alignment with exact match"""
        aligner = TimestampAligner()
        transcript = self.create_test_transcript()
        expression = self.create_test_expression("Hello")
        
        result = aligner.align_single_expression(expression, transcript)
        
        assert result is not None
        assert result.expression == "Hello"
        assert result.start_time == 0.0
        assert result.end_time == 0.5
        assert result.confidence == 0.9
        assert result.context_start == 0.0  # No buffer applied for first word
        assert result.context_end == 1.0  # 0.5 + 0.5 buffer
    
    def test_align_single_expression_fuzzy_match(self):
        """Test alignment with fuzzy match"""
        aligner = TimestampAligner(fuzzy_threshold=0.8)
        transcript = self.create_test_transcript()
        expression = self.create_test_expression("helo")  # Typo in "hello"
        
        result = aligner.align_single_expression(expression, transcript)
        
        # Should find fuzzy match
        assert result is not None
        assert result.expression == "helo"
        assert result.start_time == 0.0
        assert result.end_time == 0.5
    
    def test_align_single_expression_no_match(self):
        """Test alignment with no match"""
        aligner = TimestampAligner()
        transcript = self.create_test_transcript()
        expression = self.create_test_expression("completely nonexistent phrase that will never match")
        
        result = aligner.align_single_expression(expression, transcript)
        
        assert result is None
    
    def test_align_expressions_multiple(self):
        """Test alignment of multiple expressions"""
        aligner = TimestampAligner()
        transcript = self.create_test_transcript()
        
        expressions = [
            self.create_test_expression("Hello"),
            self.create_test_expression("test"),
            self.create_test_expression("completely nonexistent phrase that will never match")
        ]
        
        results = aligner.align_expressions(expressions, transcript)
        
        # Should align 2 out of 3 expressions
        assert len(results) == 2
        assert results[0].expression == "Hello"
        assert results[1].expression == "test"
    
    def test_find_expression_in_segment_success(self):
        """Test finding expression in segment"""
        aligner = TimestampAligner()
        
        result = aligner.find_expression_in_segment(
            "test",
            "Hello world this is a test",
            0.0,
            2.7
        )
        
        assert result is not None
        assert result['start_time'] > 0.0
        assert result['end_time'] > result['start_time']
        assert result['confidence'] == 0.8
        assert result['method'] == 'proportional'
    
    def test_find_expression_in_segment_not_found(self):
        """Test finding expression not in segment"""
        aligner = TimestampAligner()
        
        result = aligner.find_expression_in_segment(
            "nonexistent",
            "Hello world this is a test",
            0.0,
            2.7
        )
        
        assert result is None
    
    def test_calculate_partial_similarity(self):
        """Test partial similarity calculation"""
        aligner = TimestampAligner()
        
        expression_words = ["hello", "world"]
        candidate_text = "hello there world"
        
        similarity = aligner._calculate_partial_similarity(expression_words, candidate_text)
        
        # Should find both words
        assert similarity == 1.0
    
    def test_calculate_partial_similarity_partial_match(self):
        """Test partial similarity with partial match"""
        aligner = TimestampAligner()
        
        expression_words = ["hello", "world", "test"]
        candidate_text = "hello there"
        
        similarity = aligner._calculate_partial_similarity(expression_words, candidate_text)
        
        # Should find 1 out of 3 words
        assert similarity == 1.0 / 3.0
    
    def test_get_alignment_statistics(self):
        """Test alignment statistics calculation"""
        aligner = TimestampAligner()
        
        # Create mock aligned expressions
        aligned_expressions = [
            AlignedExpression(
                expression="Hello",
                start_time=0.0,
                end_time=0.5,
                confidence=0.9,
                context_start=0.0,
                context_end=1.0,
                matched_words=[],
                alignment_score=1.0
            ),
            AlignedExpression(
                expression="test",
                start_time=2.0,
                end_time=2.5,
                confidence=0.7,
                context_start=1.5,
                context_end=3.0,
                matched_words=[],
                alignment_score=0.8
            )
        ]
        
        stats = aligner.get_alignment_statistics(aligned_expressions)
        
        assert stats['total_expressions'] == 2
        assert stats['average_confidence'] == 0.8
        assert stats['average_alignment_score'] == 0.9
        assert stats['high_confidence_count'] == 1
        assert stats['low_confidence_count'] == 0
        assert stats['min_confidence'] == 0.7
        assert stats['max_confidence'] == 0.9
    
    def test_get_alignment_statistics_empty(self):
        """Test alignment statistics with empty list"""
        aligner = TimestampAligner()
        
        stats = aligner.get_alignment_statistics([])
        
        assert stats['total_expressions'] == 0
        assert stats['average_confidence'] == 0.0
        assert stats['average_alignment_score'] == 0.0
        assert stats['high_confidence_count'] == 0
        assert stats['low_confidence_count'] == 0
    
    def test_find_exact_match(self):
        """Test exact match finding"""
        aligner = TimestampAligner()
        transcript = self.create_test_transcript()
        
        result = aligner._find_exact_match("Hello", transcript)
        
        assert result is not None
        assert result['start_time'] == 0.0
        assert result['end_time'] == 0.5
        assert result['score'] == 0.9
    
    def test_find_exact_match_not_found(self):
        """Test exact match not found"""
        aligner = TimestampAligner()
        transcript = self.create_test_transcript()
        
        result = aligner._find_exact_match("nonexistent", transcript)
        
        assert result is None
    
    def test_find_fuzzy_match(self):
        """Test fuzzy match finding"""
        aligner = TimestampAligner(fuzzy_threshold=0.8)
        transcript = self.create_test_transcript()
        
        result = aligner._find_fuzzy_match("helo", transcript)  # Typo
        
        # Should find fuzzy match
        assert result is not None
        assert result['score'] >= 0.8
    
    def test_find_fuzzy_match_below_threshold(self):
        """Test fuzzy match below threshold"""
        aligner = TimestampAligner(fuzzy_threshold=0.95)
        transcript = self.create_test_transcript()
        
        result = aligner._find_fuzzy_match("completely different", transcript)
        
        assert result is None
    
    def test_create_aligned_expression(self):
        """Test aligned expression creation"""
        aligner = TimestampAligner()
        expression = self.create_test_expression("test")
        
        match_data = {
            'start_time': 2.0,
            'end_time': 2.5,
            'matched_words': [],
            'score': 0.9
        }
        
        result = aligner._create_aligned_expression(expression, match_data, 0.8)
        
        assert result.expression == "test"
        assert result.start_time == 2.0
        assert result.end_time == 2.5
        assert result.confidence == 0.9
        assert result.context_start == 1.5  # 2.0 - 0.5 buffer
        assert result.context_end == 3.0   # 2.5 + 0.5 buffer
        assert result.alignment_score == 0.8
