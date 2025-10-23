"""
Expression validation and accuracy improvement system for LangFlix Expression-Based Learning Feature.

This module provides:
- Multi-pass expression validation
- Context consistency checking
- Translation accuracy verification
- Confidence scoring
- Quality assurance
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re

from langflix.core.models import ExpressionAnalysis
from langflix.core.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of expression validation"""
    is_valid: bool
    confidence_score: float
    issues: List[str]
    suggestions: List[str]
    quality_metrics: Dict[str, float]

@dataclass
class ValidationConfig:
    """Configuration for expression validation"""
    min_confidence: float = 0.7
    max_issues: int = 3
    require_translation: bool = True
    require_examples: bool = True
    require_pronunciation: bool = False
    context_consistency_weight: float = 0.3
    translation_accuracy_weight: float = 0.4
    educational_value_weight: float = 0.3

class ExpressionValidator:
    """Advanced expression validation system"""
    
    def __init__(self, config: Optional[ValidationConfig] = None):
        """
        Initialize expression validator
        
        Args:
            config: Validation configuration
        """
        self.config = config or ValidationConfig()
        self.cache_manager = get_cache_manager()
        
        # Validation patterns
        self.expression_patterns = self._initialize_validation_patterns()
        
        logger.info("ExpressionValidator initialized")
    
    def _initialize_validation_patterns(self) -> Dict[str, re.Pattern]:
        """Initialize regex patterns for validation"""
        return {
            'english_expression': re.compile(r'^[a-zA-Z\s\-\'\.]+$'),
            'korean_translation': re.compile(r'^[가-힣\s\-\'\.]+$'),
            'pronunciation': re.compile(r'^[a-zA-Z\s\-\'\.\/\[\]]+$'),
            'example_sentence': re.compile(r'^[a-zA-Z\s\-\'\.\!\?]+$')
        }
    
    def validate_expression(self, expression: ExpressionAnalysis) -> ValidationResult:
        """
        Validate a single expression with comprehensive checks
        
        Args:
            expression: Expression to validate
            
        Returns:
            ValidationResult with validation details
        """
        logger.debug(f"Validating expression: {expression.expression}")
        
        issues = []
        suggestions = []
        quality_metrics = {}
        
        # Basic validation checks
        basic_valid, basic_issues = self._validate_basic_fields(expression)
        issues.extend(basic_issues)
        
        # Content validation
        content_valid, content_issues, content_suggestions = self._validate_content(expression)
        issues.extend(content_issues)
        suggestions.extend(content_suggestions)
        
        # Context consistency
        context_score = self._validate_context_consistency(expression)
        quality_metrics['context_consistency'] = context_score
        
        # Translation accuracy
        translation_score = self._validate_translation_accuracy(expression)
        quality_metrics['translation_accuracy'] = translation_score
        
        # Educational value
        educational_score = self._validate_educational_value(expression)
        quality_metrics['educational_value'] = educational_score
        
        # Calculate overall confidence
        confidence_score = self._calculate_confidence_score(quality_metrics)
        
        # Determine if valid
        is_valid = (
            basic_valid and 
            content_valid and 
            confidence_score >= self.config.min_confidence and
            len(issues) <= self.config.max_issues
        )
        
        return ValidationResult(
            is_valid=is_valid,
            confidence_score=confidence_score,
            issues=issues,
            suggestions=suggestions,
            quality_metrics=quality_metrics
        )
    
    def _validate_basic_fields(self, expression: ExpressionAnalysis) -> Tuple[bool, List[str]]:
        """Validate basic required fields"""
        issues = []
        
        # Check required fields
        if not expression.expression or not expression.expression.strip():
            issues.append("Expression text is empty")
        
        if self.config.require_translation and not expression.expression_translation:
            issues.append("Translation is required but missing")
        
        if self.config.require_examples and not expression.usage_examples:
            issues.append("Usage examples are required but missing")
        
        if self.config.require_pronunciation and not expression.pronunciation:
            issues.append("Pronunciation is required but missing")
        
        # Check field lengths
        if expression.expression and len(expression.expression) > 100:
            issues.append("Expression text is too long")
        
        if expression.expression_translation and len(expression.expression_translation) > 200:
            issues.append("Translation is too long")
        
        return len(issues) == 0, issues
    
    def _validate_content(self, expression: ExpressionAnalysis) -> Tuple[bool, List[str], List[str]]:
        """Validate content quality and format"""
        issues = []
        suggestions = []
        
        # Validate expression format
        if expression.expression:
            if not self.expression_patterns['english_expression'].match(expression.expression):
                issues.append("Expression contains invalid characters")
            elif len(expression.expression.split()) < 2:
                suggestions.append("Expression might be too short for educational value")
        
        # Validate translation format
        if expression.expression_translation:
            if not self.expression_patterns['korean_translation'].match(expression.expression_translation):
                issues.append("Translation contains invalid characters")
        
        # Validate pronunciation format
        if expression.pronunciation:
            if not self.expression_patterns['pronunciation'].match(expression.pronunciation):
                issues.append("Pronunciation contains invalid characters")
        
        # Validate usage examples
        if expression.usage_examples:
            for i, example in enumerate(expression.usage_examples):
                if not self.expression_patterns['example_sentence'].match(example):
                    issues.append(f"Usage example {i+1} contains invalid characters")
                elif len(example.split()) < 3:
                    suggestions.append(f"Usage example {i+1} might be too short")
        
        # Validate difficulty level
        if expression.difficulty and (expression.difficulty < 1 or expression.difficulty > 10):
            issues.append("Difficulty level must be between 1 and 10")
        
        # Validate educational value score
        if expression.educational_value_score and (expression.educational_value_score < 0 or expression.educational_value_score > 10):
            issues.append("Educational value score must be between 0 and 10")
        
        return len(issues) == 0, issues, suggestions
    
    def _validate_context_consistency(self, expression: ExpressionAnalysis) -> float:
        """Validate context consistency"""
        score = 0.5  # Base score
        
        # Check if expression matches context
        if expression.expression and expression.expression_dialogue:
            if expression.expression.lower() in expression.expression_dialogue.lower():
                score += 0.3
            else:
                score -= 0.2
        
        # Check if translation matches context
        if expression.expression_translation and expression.expression_dialogue_translation:
            if expression.expression_translation in expression.expression_dialogue_translation:
                score += 0.2
            else:
                score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def _validate_translation_accuracy(self, expression: ExpressionAnalysis) -> float:
        """Validate translation accuracy"""
        score = 0.5  # Base score
        
        # Check if translation exists
        if not expression.expression_translation:
            return 0.0
        
        # Check translation length (should be reasonable)
        if len(expression.expression_translation) < 2:
            score -= 0.3
        elif len(expression.expression_translation) > 50:
            score -= 0.1
        
        # Check if translation contains Korean characters
        if any('\uac00' <= char <= '\ud7af' for char in expression.expression_translation):
            score += 0.2
        
        # Check if translation matches expression length
        expr_words = len(expression.expression.split())
        trans_words = len(expression.expression_translation.split())
        if abs(expr_words - trans_words) <= 2:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _validate_educational_value(self, expression: ExpressionAnalysis) -> float:
        """Validate educational value"""
        score = 0.5  # Base score
        
        # Check educational value score
        if expression.educational_value_score:
            score = expression.educational_value_score / 10.0
        
        # Check if educational value explanation exists
        if expression.educational_value and len(expression.educational_value) > 10:
            score += 0.1
        
        # Check if usage notes exist
        if expression.usage_notes and len(expression.usage_notes) > 10:
            score += 0.1
        
        # Check if cultural notes exist
        if expression.cultural_notes and len(expression.cultural_notes) > 10:
            score += 0.1
        
        # Check if grammar notes exist
        if expression.grammar_notes and len(expression.grammar_notes) > 10:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _calculate_confidence_score(self, quality_metrics: Dict[str, float]) -> float:
        """Calculate overall confidence score"""
        weights = {
            'context_consistency': self.config.context_consistency_weight,
            'translation_accuracy': self.config.translation_accuracy_weight,
            'educational_value': self.config.educational_value_weight
        }
        
        weighted_score = sum(
            quality_metrics.get(metric, 0.5) * weight
            for metric, weight in weights.items()
        )
        
        return weighted_score
    
    def validate_expression_batch(
        self,
        expressions: List[ExpressionAnalysis]
    ) -> List[ValidationResult]:
        """
        Validate a batch of expressions
        
        Args:
            expressions: List of expressions to validate
            
        Returns:
            List of validation results
        """
        logger.info(f"Validating batch of {len(expressions)} expressions")
        
        results = []
        for expression in expressions:
            result = self.validate_expression(expression)
            results.append(result)
        
        # Log validation summary
        valid_count = sum(1 for result in results if result.is_valid)
        avg_confidence = sum(result.confidence_score for result in results) / len(results)
        
        logger.info(f"Validation complete: {valid_count}/{len(expressions)} valid, "
                   f"avg confidence: {avg_confidence:.2f}")
        
        return results
    
    def get_validation_statistics(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Get validation statistics"""
        if not results:
            return {}
        
        total = len(results)
        valid_count = sum(1 for result in results if result.is_valid)
        avg_confidence = sum(result.confidence_score for result in results) / total
        
        # Count issues by type
        issue_counts = {}
        for result in results:
            for issue in result.issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        # Calculate quality metrics
        avg_context_consistency = sum(
            result.quality_metrics.get('context_consistency', 0) for result in results
        ) / total
        
        avg_translation_accuracy = sum(
            result.quality_metrics.get('translation_accuracy', 0) for result in results
        ) / total
        
        avg_educational_value = sum(
            result.quality_metrics.get('educational_value', 0) for result in results
        ) / total
        
        return {
            'total_expressions': total,
            'valid_expressions': valid_count,
            'invalid_expressions': total - valid_count,
            'validation_rate': valid_count / total,
            'average_confidence': avg_confidence,
            'common_issues': sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            'quality_metrics': {
                'context_consistency': avg_context_consistency,
                'translation_accuracy': avg_translation_accuracy,
                'educational_value': avg_educational_value
            }
        }
    
    def suggest_improvements(self, expression: ExpressionAnalysis) -> List[str]:
        """Suggest improvements for an expression"""
        suggestions = []
        
        # Check expression length
        if expression.expression and len(expression.expression.split()) < 2:
            suggestions.append("Consider using a longer, more descriptive expression")
        
        # Check translation quality
        if not expression.expression_translation:
            suggestions.append("Add a Korean translation")
        elif len(expression.expression_translation) < 2:
            suggestions.append("Provide a more detailed translation")
        
        # Check usage examples
        if not expression.usage_examples:
            suggestions.append("Add usage examples to improve educational value")
        elif len(expression.usage_examples) < 2:
            suggestions.append("Add more usage examples")
        
        # Check pronunciation
        if not expression.pronunciation:
            suggestions.append("Add pronunciation guide")
        
        # Check educational content
        if not expression.educational_value:
            suggestions.append("Add explanation of educational value")
        
        if not expression.cultural_notes:
            suggestions.append("Add cultural context notes")
        
        if not expression.grammar_notes:
            suggestions.append("Add grammar explanation")
        
        return suggestions

# Global validator instance
_expression_validator: Optional[ExpressionValidator] = None

def get_expression_validator() -> ExpressionValidator:
    """Get global expression validator instance"""
    global _expression_validator
    if _expression_validator is None:
        _expression_validator = ExpressionValidator()
    return _expression_validator

def validate_expression(expression: ExpressionAnalysis) -> ValidationResult:
    """
    Convenience function for expression validation
    
    Args:
        expression: Expression to validate
        
    Returns:
        ValidationResult with validation details
    """
    validator = get_expression_validator()
    return validator.validate_expression(expression)

def validate_expression_batch(expressions: List[ExpressionAnalysis]) -> List[ValidationResult]:
    """
    Convenience function for batch expression validation
    
    Args:
        expressions: List of expressions to validate
        
    Returns:
        List of validation results
    """
    validator = get_expression_validator()
    return validator.validate_expression_batch(expressions)
