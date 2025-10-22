#!/usr/bin/env python3
"""
Unit tests for expression ranking system
"""

import pytest
from typing import List

from langflix.core.expression_analyzer import (
    rank_expressions,
    calculate_expression_score,
    _remove_duplicates
)
from langflix.core.models import ExpressionAnalysis


def create_test_expression(
    expression: str,
    difficulty: int = 5,
    frequency: int = 1,
    educational_value_score: float = 5.0,
    **kwargs
) -> ExpressionAnalysis:
    """Helper function to create test expression"""
    return ExpressionAnalysis(
        dialogues=["Test dialogue"],
        translation=["테스트 대화"],
        expression_dialogue="Test dialogue",
        expression_dialogue_translation="테스트 대화",
        expression=expression,
        expression_translation="테스트",
        context_start_time="00:00:01,000",
        context_end_time="00:00:02,000",
        similar_expressions=["similar 1"],
        difficulty=difficulty,
        frequency=frequency,
        educational_value_score=educational_value_score,
        **kwargs
    )


class TestExpressionScoreCalculation:
    """Test expression score calculation"""
    
    def test_basic_score_calculation(self):
        """Test basic score calculation with default weights"""
        expr = create_test_expression(
            expression="test expression",
            difficulty=5,
            frequency=1,
            educational_value_score=5.0
        )
        
        score = calculate_expression_score(expr)
        
        # Score should be in 0-10 range
        assert 0 <= score <= 10
        assert isinstance(score, float)
    
    def test_high_difficulty_score(self):
        """Test that higher difficulty increases score"""
        low_difficulty_expr = create_test_expression(
            expression="easy",
            difficulty=2,
            frequency=1,
            educational_value_score=5.0
        )
        
        high_difficulty_expr = create_test_expression(
            expression="hard",
            difficulty=9,
            frequency=1,
            educational_value_score=5.0
        )
        
        low_score = calculate_expression_score(low_difficulty_expr)
        high_score = calculate_expression_score(high_difficulty_expr)
        
        assert high_score > low_score
    
    def test_high_frequency_score(self):
        """Test that higher frequency increases score"""
        low_freq_expr = create_test_expression(
            expression="rare",
            difficulty=5,
            frequency=1,
            educational_value_score=5.0
        )
        
        high_freq_expr = create_test_expression(
            expression="common",
            difficulty=5,
            frequency=10,
            educational_value_score=5.0
        )
        
        low_score = calculate_expression_score(low_freq_expr)
        high_score = calculate_expression_score(high_freq_expr)
        
        assert high_score > low_score
    
    def test_high_educational_value_score(self):
        """Test that higher educational value increases score"""
        low_value_expr = create_test_expression(
            expression="low value",
            difficulty=5,
            frequency=1,
            educational_value_score=2.0
        )
        
        high_value_expr = create_test_expression(
            expression="high value",
            difficulty=5,
            frequency=1,
            educational_value_score=9.0
        )
        
        low_score = calculate_expression_score(low_value_expr)
        high_score = calculate_expression_score(high_value_expr)
        
        assert high_score > low_score
    
    def test_custom_weights(self):
        """Test score calculation with custom weights"""
        expr = create_test_expression(
            expression="test",
            difficulty=5,
            frequency=5,
            educational_value_score=5.0
        )
        
        score1 = calculate_expression_score(
            expr,
            difficulty_weight=0.5,
            frequency_weight=0.3,
            educational_value_weight=0.2
        )
        
        score2 = calculate_expression_score(
            expr,
            difficulty_weight=0.2,
            frequency_weight=0.3,
            educational_value_weight=0.5
        )
        
        # Scores should be different with different weights
        assert score1 != score2


class TestDuplicateRemoval:
    """Test fuzzy duplicate detection and removal"""
    
    def test_no_duplicates(self):
        """Test that unique expressions are not removed"""
        expressions = [
            create_test_expression("get screwed"),
            create_test_expression("knock 'em dead"),
            create_test_expression("figure it out")
        ]
        
        result = _remove_duplicates(expressions)
        
        assert len(result) == len(expressions)
    
    def test_exact_duplicates(self):
        """Test removal of exact duplicates"""
        expressions = [
            create_test_expression("get screwed"),
            create_test_expression("get screwed"),  # Exact duplicate
            create_test_expression("knock 'em dead")
        ]
        
        result = _remove_duplicates(expressions)
        
        # Should remove one duplicate
        assert len(result) == 2
        assert result[0].expression == "get screwed"
        assert result[1].expression == "knock 'em dead"
    
    def test_fuzzy_duplicates(self):
        """Test removal of similar expressions (fuzzy matching)"""
        expressions = [
            create_test_expression("get screwed"),
            create_test_expression("Get Screwed"),  # Case variation
            create_test_expression("get  screwed"),  # Extra space
            create_test_expression("completely different expression")
        ]
        
        result = _remove_duplicates(expressions)
        
        # Should remove similar ones based on fuzzy threshold
        assert len(result) < len(expressions)
        assert len(result) >= 2  # At least 2 unique ones
    
    def test_similar_but_not_duplicate(self):
        """Test that similar but distinct expressions are kept"""
        expressions = [
            create_test_expression("get screwed over"),
            create_test_expression("get it done"),
            create_test_expression("get lost")
        ]
        
        result = _remove_duplicates(expressions)
        
        # All should be kept as they're distinct
        assert len(result) == 3


class TestExpressionRanking:
    """Test complete expression ranking pipeline"""
    
    def test_ranking_basic(self):
        """Test basic ranking functionality"""
        expressions = [
            create_test_expression(
                "low score",
                difficulty=2,
                frequency=1,
                educational_value_score=2.0
            ),
            create_test_expression(
                "high score",
                difficulty=9,
                frequency=10,
                educational_value_score=9.0
            ),
            create_test_expression(
                "medium score",
                difficulty=5,
                frequency=5,
                educational_value_score=5.0
            )
        ]
        
        ranked = rank_expressions(expressions, max_count=10)
        
        # Should be ranked by score (highest first)
        assert len(ranked) == 3
        assert ranked[0].expression == "high score"
        assert ranked[2].expression == "low score"
        
        # Ranking scores should be assigned
        assert ranked[0].ranking_score > ranked[1].ranking_score
        assert ranked[1].ranking_score > ranked[2].ranking_score
    
    def test_ranking_with_max_count(self):
        """Test ranking with max_count limit"""
        expressions = [
            create_test_expression(f"expr_{i}", difficulty=i, educational_value_score=float(i))
            for i in range(1, 11)
        ]
        
        max_count = 5
        ranked = rank_expressions(expressions, max_count=max_count)
        
        # Should return only top N
        assert len(ranked) == max_count
        
        # Should be the highest scoring ones
        assert all(hasattr(expr, 'ranking_score') for expr in ranked)
    
    def test_ranking_with_duplicates(self):
        """Test ranking removes duplicates"""
        expressions = [
            create_test_expression("get screwed over", difficulty=8, educational_value_score=8.0),
            create_test_expression("duplicate text", difficulty=7, educational_value_score=7.0),
            create_test_expression("duplicate text", difficulty=7, educational_value_score=7.0),
            create_test_expression("knock them dead", difficulty=6, educational_value_score=6.0)
        ]
        
        ranked = rank_expressions(expressions, max_count=10, remove_duplicates=True)
        
        # Should have removed duplicate (3 unique expressions)
        assert len(ranked) == 3
        
        # Check all expressions are unique
        expression_texts = [expr.expression for expr in ranked]
        assert len(expression_texts) == len(set(expression_texts))
    
    def test_ranking_without_duplicate_removal(self):
        """Test ranking keeps duplicates when disabled"""
        expressions = [
            create_test_expression("duplicate", difficulty=7, educational_value_score=7.0),
            create_test_expression("duplicate", difficulty=7, educational_value_score=7.0)
        ]
        
        ranked = rank_expressions(expressions, max_count=10, remove_duplicates=False)
        
        # Should keep duplicates
        assert len(ranked) == 2
    
    def test_ranking_empty_list(self):
        """Test ranking with empty input"""
        ranked = rank_expressions([], max_count=5)
        
        assert ranked == []
    
    def test_ranking_single_expression(self):
        """Test ranking with single expression"""
        expressions = [
            create_test_expression("only one", difficulty=5, educational_value_score=5.0)
        ]
        
        ranked = rank_expressions(expressions, max_count=5)
        
        assert len(ranked) == 1
        assert ranked[0].expression == "only one"
        assert ranked[0].ranking_score > 0


class TestRankingScoreProperties:
    """Test properties of ranking scores"""
    
    def test_score_is_numeric(self):
        """Test that ranking score is a number"""
        expr = create_test_expression("test")
        score = calculate_expression_score(expr)
        
        assert isinstance(score, (int, float))
    
    def test_score_is_positive(self):
        """Test that ranking score is positive"""
        expr = create_test_expression(
            "test",
            difficulty=1,
            frequency=1,
            educational_value_score=0.0
        )
        score = calculate_expression_score(expr)
        
        assert score >= 0
    
    def test_score_consistency(self):
        """Test that same input produces same score"""
        expr = create_test_expression(
            "test",
            difficulty=5,
            frequency=3,
            educational_value_score=7.0
        )
        
        score1 = calculate_expression_score(expr)
        score2 = calculate_expression_score(expr)
        
        assert score1 == score2

