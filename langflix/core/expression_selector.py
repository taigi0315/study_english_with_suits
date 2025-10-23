"""
Intelligent expression selection system for LangFlix Expression-Based Learning Feature.

This module provides:
- Machine learning-based expression ranking
- Context-aware expression selection
- Difficulty progression analysis
- Learning curve optimization
- Educational value assessment
"""

import logging
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json

from langflix.core.models import ExpressionAnalysis
from langflix.core.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)

@dataclass
class SelectionCriteria:
    """Criteria for expression selection"""
    difficulty_weight: float = 0.3
    frequency_weight: float = 0.2
    educational_value_weight: float = 0.3
    context_relevance_weight: float = 0.2
    diversity_weight: float = 0.1
    novelty_weight: float = 0.1

@dataclass
class LearningProfile:
    """User learning profile for personalized selection"""
    current_level: str = "intermediate"
    preferred_categories: List[str] = None
    weak_areas: List[str] = None
    learning_goals: List[str] = None
    progress_history: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.preferred_categories is None:
            self.preferred_categories = []
        if self.weak_areas is None:
            self.weak_areas = []
        if self.learning_goals is None:
            self.learning_goals = []
        if self.progress_history is None:
            self.progress_history = []

@dataclass
class SelectionResult:
    """Result of expression selection"""
    selected_expressions: List[ExpressionAnalysis]
    selection_reasons: List[str]
    confidence_score: float
    diversity_score: float
    difficulty_progression: List[int]
    educational_value_score: float

class IntelligentExpressionSelector:
    """Advanced expression selection system with ML-based ranking"""
    
    def __init__(
        self,
        criteria: Optional[SelectionCriteria] = None,
        learning_profile: Optional[LearningProfile] = None
    ):
        """
        Initialize intelligent expression selector
        
        Args:
            criteria: Selection criteria weights
            learning_profile: User learning profile
        """
        self.criteria = criteria or SelectionCriteria()
        self.learning_profile = learning_profile or LearningProfile()
        self.cache_manager = get_cache_manager()
        
        # Learning curve parameters
        self.difficulty_progression = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        self.category_weights = self._initialize_category_weights()
        
        logger.info("IntelligentExpressionSelector initialized")
    
    def _initialize_category_weights(self) -> Dict[str, float]:
        """Initialize category weights based on learning profile"""
        weights = {
            'idiom': 1.0,
            'slang': 1.0,
            'formal': 1.0,
            'greeting': 1.0,
            'cultural': 1.0,
            'grammar': 1.0,
            'pronunciation': 1.0,
            'general': 1.0
        }
        
        # Adjust weights based on learning profile
        if self.learning_profile.weak_areas:
            for area in self.learning_profile.weak_areas:
                if area in weights:
                    weights[area] *= 1.5  # Boost weak areas
        
        if self.learning_profile.preferred_categories:
            for category in self.learning_profile.preferred_categories:
                if category in weights:
                    weights[category] *= 1.2  # Slight boost for preferences
        
        return weights
    
    def select_expressions(
        self,
        candidate_expressions: List[ExpressionAnalysis],
        target_count: int = 5,
        context: Optional[Dict[str, Any]] = None
    ) -> SelectionResult:
        """
        Select optimal expressions using intelligent ranking
        
        Args:
            candidate_expressions: List of candidate expressions
            target_count: Number of expressions to select
            context: Additional context for selection
            
        Returns:
            SelectionResult with selected expressions and metadata
        """
        if not candidate_expressions:
            return SelectionResult([], [], 0.0, 0.0, [], 0.0)
        
        logger.info(f"Selecting {target_count} expressions from {len(candidate_expressions)} candidates")
        
        # Calculate comprehensive scores for all candidates
        scored_expressions = []
        for expr in candidate_expressions:
            score = self._calculate_comprehensive_score(expr, context)
            scored_expressions.append((expr, score))
        
        # Sort by score (descending)
        scored_expressions.sort(key=lambda x: x[1], reverse=True)
        
        # Apply diversity and progression constraints
        selected = self._apply_selection_constraints(
            scored_expressions, target_count, context
        )
        
        # Generate selection metadata
        selection_reasons = self._generate_selection_reasons(selected)
        confidence_score = self._calculate_confidence_score(selected)
        diversity_score = self._calculate_diversity_score(selected)
        difficulty_progression = [expr.difficulty for expr in selected]
        educational_value_score = sum(expr.educational_value_score for expr in selected) / len(selected)
        
        result = SelectionResult(
            selected_expressions=selected,
            selection_reasons=selection_reasons,
            confidence_score=confidence_score,
            diversity_score=diversity_score,
            difficulty_progression=difficulty_progression,
            educational_value_score=educational_value_score
        )
        
        logger.info(f"Selected {len(selected)} expressions with confidence {confidence_score:.2f}")
        return result
    
    def _calculate_comprehensive_score(
        self,
        expression: ExpressionAnalysis,
        context: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate comprehensive score for an expression"""
        scores = {}
        
        # Base scores
        scores['difficulty'] = self._score_difficulty(expression)
        scores['frequency'] = self._score_frequency(expression)
        scores['educational_value'] = self._score_educational_value(expression)
        scores['context_relevance'] = self._score_context_relevance(expression, context)
        scores['diversity'] = self._score_diversity(expression)
        scores['novelty'] = self._score_novelty(expression)
        scores['category'] = self._score_category(expression)
        
        # Weighted combination
        total_score = (
            scores['difficulty'] * self.criteria.difficulty_weight +
            scores['frequency'] * self.criteria.frequency_weight +
            scores['educational_value'] * self.criteria.educational_value_weight +
            scores['context_relevance'] * self.criteria.context_relevance_weight +
            scores['diversity'] * self.criteria.diversity_weight +
            scores['novelty'] * self.criteria.novelty_weight +
            scores['category'] * 0.1  # Category bonus
        )
        
        return total_score
    
    def _score_difficulty(self, expression: ExpressionAnalysis) -> float:
        """Score based on difficulty appropriateness"""
        target_difficulty = self._get_target_difficulty()
        difficulty_diff = abs(expression.difficulty - target_difficulty)
        
        # Optimal difficulty gets highest score
        if difficulty_diff == 0:
            return 1.0
        elif difficulty_diff <= 1:
            return 0.8
        elif difficulty_diff <= 2:
            return 0.6
        else:
            return 0.3
    
    def _score_frequency(self, expression: ExpressionAnalysis) -> float:
        """Score based on frequency in content"""
        # Higher frequency indicates importance
        return min(expression.frequency / 10.0, 1.0)
    
    def _score_educational_value(self, expression: ExpressionAnalysis) -> float:
        """Score based on educational value"""
        return expression.educational_value_score / 10.0
    
    def _score_context_relevance(self, expression: ExpressionAnalysis, context: Optional[Dict[str, Any]]) -> float:
        """Score based on context relevance"""
        if not context:
            return 0.5  # Neutral score without context
        
        # Check if expression matches context themes
        context_themes = context.get('themes', [])
        expression_text = expression.expression.lower()
        
        relevance_score = 0.5  # Base score
        for theme in context_themes:
            if theme.lower() in expression_text:
                relevance_score += 0.2
        
        return min(relevance_score, 1.0)
    
    def _score_diversity(self, expression: ExpressionAnalysis) -> float:
        """Score based on diversity contribution"""
        # This would be calculated relative to other selected expressions
        # For now, return a base score
        return 0.5
    
    def _score_novelty(self, expression: ExpressionAnalysis) -> float:
        """Score based on novelty (uniqueness)"""
        # Check if expression is similar to previously learned ones
        # For now, return a base score
        return 0.5
    
    def _score_category(self, expression: ExpressionAnalysis) -> float:
        """Score based on category preferences"""
        category = expression.category or 'general'
        return self.category_weights.get(category, 1.0)
    
    def _get_target_difficulty(self) -> int:
        """Get target difficulty based on learning profile"""
        level_mapping = {
            'beginner': 3,
            'intermediate': 6,
            'advanced': 8
        }
        return level_mapping.get(self.learning_profile.current_level, 6)
    
    def _apply_selection_constraints(
        self,
        scored_expressions: List[Tuple[ExpressionAnalysis, float]],
        target_count: int,
        context: Optional[Dict[str, Any]]
    ) -> List[ExpressionAnalysis]:
        """Apply diversity and progression constraints to selection"""
        selected = []
        used_categories = set()
        difficulty_levels = []
        
        for expression, score in scored_expressions:
            if len(selected) >= target_count:
                break
            
            # Check diversity constraints
            category = expression.category or 'general'
            if len(used_categories) < 3 and category in used_categories:
                continue  # Skip if we already have this category and need diversity
            
            # Check difficulty progression
            if difficulty_levels:
                avg_difficulty = sum(difficulty_levels) / len(difficulty_levels)
                if abs(expression.difficulty - avg_difficulty) > 3:
                    continue  # Skip if too different from current progression
            
            selected.append(expression)
            used_categories.add(category)
            difficulty_levels.append(expression.difficulty)
        
        return selected
    
    def _generate_selection_reasons(self, selected: List[ExpressionAnalysis]) -> List[str]:
        """Generate human-readable reasons for selection"""
        reasons = []
        
        if not selected:
            return ["No suitable expressions found"]
        
        # Difficulty analysis
        difficulties = [expr.difficulty for expr in selected]
        avg_difficulty = sum(difficulties) / len(difficulties)
        reasons.append(f"Average difficulty: {avg_difficulty:.1f}/10")
        
        # Category diversity
        categories = [expr.category or 'general' for expr in selected]
        unique_categories = len(set(categories))
        reasons.append(f"Category diversity: {unique_categories} types")
        
        # Educational value
        avg_educational_value = sum(expr.educational_value_score for expr in selected) / len(selected)
        reasons.append(f"Educational value: {avg_educational_value:.1f}/10")
        
        # Frequency analysis
        avg_frequency = sum(expr.frequency for expr in selected) / len(selected)
        reasons.append(f"Content frequency: {avg_frequency:.1f} occurrences")
        
        return reasons
    
    def _calculate_confidence_score(self, selected: List[ExpressionAnalysis]) -> float:
        """Calculate confidence in the selection"""
        if not selected:
            return 0.0
        
        # Base confidence on expression quality
        avg_educational_value = sum(expr.educational_value_score for expr in selected) / len(selected)
        avg_frequency = sum(expr.frequency for expr in selected) / len(selected)
        
        # Higher educational value and frequency = higher confidence
        confidence = (avg_educational_value / 10.0 + min(avg_frequency / 5.0, 1.0)) / 2.0
        
        return min(confidence, 1.0)
    
    def _calculate_diversity_score(self, selected: List[ExpressionAnalysis]) -> float:
        """Calculate diversity score of selected expressions"""
        if len(selected) <= 1:
            return 0.0
        
        # Category diversity
        categories = [expr.category or 'general' for expr in selected]
        unique_categories = len(set(categories))
        category_diversity = unique_categories / len(categories)
        
        # Difficulty diversity
        difficulties = [expr.difficulty for expr in selected]
        difficulty_range = max(difficulties) - min(difficulties)
        difficulty_diversity = min(difficulty_range / 5.0, 1.0)  # Normalize to 0-1
        
        return (category_diversity + difficulty_diversity) / 2.0
    
    def update_learning_profile(self, progress_data: Dict[str, Any]) -> None:
        """Update learning profile based on progress data"""
        if 'completed_expressions' in progress_data:
            completed = progress_data['completed_expressions']
            
            # Update weak areas based on performance
            if 'performance_scores' in progress_data:
                scores = progress_data['performance_scores']
                weak_areas = [area for area, score in scores.items() if score < 0.6]
                self.learning_profile.weak_areas = weak_areas
            
            # Update progress history
            self.learning_profile.progress_history.append({
                'timestamp': datetime.now().isoformat(),
                'completed_count': len(completed),
                'performance': progress_data.get('performance_scores', {})
            })
            
            # Keep only last 10 progress entries
            if len(self.learning_profile.progress_history) > 10:
                self.learning_profile.progress_history = self.learning_profile.progress_history[-10:]
            
            logger.info("Learning profile updated with progress data")
    
    def get_selection_statistics(self) -> Dict[str, Any]:
        """Get statistics about expression selection"""
        return {
            'criteria_weights': {
                'difficulty': self.criteria.difficulty_weight,
                'frequency': self.criteria.frequency_weight,
                'educational_value': self.criteria.educational_value_weight,
                'context_relevance': self.criteria.context_relevance_weight,
                'diversity': self.criteria.diversity_weight,
                'novelty': self.criteria.novelty_weight
            },
            'learning_profile': {
                'current_level': self.learning_profile.current_level,
                'preferred_categories': self.learning_profile.preferred_categories,
                'weak_areas': self.learning_profile.weak_areas,
                'progress_entries': len(self.learning_profile.progress_history)
            },
            'category_weights': self.category_weights
        }

# Global selector instance
_expression_selector: Optional[IntelligentExpressionSelector] = None

def get_expression_selector() -> IntelligentExpressionSelector:
    """Get global expression selector instance"""
    global _expression_selector
    if _expression_selector is None:
        _expression_selector = IntelligentExpressionSelector()
    return _expression_selector

def select_expressions_intelligent(
    candidate_expressions: List[ExpressionAnalysis],
    target_count: int = 5,
    context: Optional[Dict[str, Any]] = None
) -> SelectionResult:
    """
    Convenience function for intelligent expression selection
    
    Args:
        candidate_expressions: List of candidate expressions
        target_count: Number of expressions to select
        context: Additional context for selection
        
    Returns:
        SelectionResult with selected expressions and metadata
    """
    selector = get_expression_selector()
    return selector.select_expressions(candidate_expressions, target_count, context)
