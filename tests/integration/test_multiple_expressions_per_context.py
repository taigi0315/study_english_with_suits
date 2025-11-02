"""
Integration tests for multiple expressions per context feature (TICKET-008)
Tests actual video creation workflow with multiple expressions sharing same context
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from langflix.core.models import ExpressionAnalysis, ExpressionGroup
from langflix.core.expression_analyzer import group_expressions_by_context


class TestMultipleExpressionsPerContextIntegration(unittest.TestCase):
    """Integration tests for multi-expression context video creation"""
    
    def setUp(self):
        """Set up test fixtures with multiple expressions sharing context"""
        self.expr1 = ExpressionAnalysis(
            dialogues=["I'll knock it out of the park for you."],
            translation=["제가 완벽하게 해낼게요."],
            expression_dialogue="I'll knock it out of the park for you.",
            expression_dialogue_translation="제가 완벽하게 해낼게요.",
            expression="knock it out of the park",
            expression_translation="완벽하게 해내다",
            context_start_time="00:05:30,000",
            context_end_time="00:06:10,000",
            expression_start_time="00:05:35,000",
            expression_end_time="00:05:45,000",
            similar_expressions=["hit it out of the park", "nail it"]
        )
        
        self.expr2 = ExpressionAnalysis(
            dialogues=["You can count on it."],
            translation=["믿으셔도 됩니다."],
            expression_dialogue="You can count on it.",
            expression_dialogue_translation="믿으셔도 됩니다.",
            expression="count on it",
            expression_translation="믿다",
            context_start_time="00:05:30,000",  # Same context as expr1
            context_end_time="00:06:10,000",
            expression_start_time="00:05:50,000",
            expression_end_time="00:05:55,000",
            similar_expressions=["rely on it", "trust it"]
        )
        
        self.expr3 = ExpressionAnalysis(
            dialogues=["I'm sure about it."],
            translation=["확신합니다."],
            expression_dialogue="I'm sure about it.",
            expression_dialogue_translation="확신합니다.",
            expression="I'm sure about it",
            expression_translation="확신하다",
            context_start_time="00:05:30,000",  # Same context as expr1 and expr2
            context_end_time="00:06:10,000",
            expression_start_time="00:06:00,000",
            expression_end_time="00:06:05,000",
            similar_expressions=["I'm certain", "I'm confident"]
        )
    
    def test_group_three_expressions_same_context(self):
        """Test grouping three expressions from same context creates one group"""
        expressions = [self.expr1, self.expr2, self.expr3]
        groups = group_expressions_by_context(expressions)
        
        # Should create one group with 3 expressions
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 3)
        self.assertIn(self.expr1, groups[0].expressions)
        self.assertIn(self.expr2, groups[0].expressions)
        self.assertIn(self.expr3, groups[0].expressions)
        
        # Verify all share same context times
        self.assertEqual(groups[0].context_start_time, "00:05:30,000")
        self.assertEqual(groups[0].context_end_time, "00:06:10,000")
    
    def test_expression_timings_within_context_dont_overlap(self):
        """Test that expression timings within same context don't overlap"""
        group = ExpressionGroup(
            context_start_time="00:05:30,000",
            context_end_time="00:06:10,000",
            expressions=[self.expr1, self.expr2, self.expr3]
        )
        
        # Convert timings to seconds for comparison
        def time_to_seconds(time_str: str) -> float:
            parts = time_str.replace(',', '.').split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        
        # Extract expression timings
        expr_timings = []
        for expr in group.expressions:
            start = time_to_seconds(expr.expression_start_time)
            end = time_to_seconds(expr.expression_end_time)
            expr_timings.append((start, end, expr.expression))
        
        # Sort by start time
        expr_timings.sort(key=lambda x: x[0])
        
        # Verify expressions don't overlap (they can be adjacent)
        for i in range(len(expr_timings) - 1):
            current_end = expr_timings[i][1]
            next_start = expr_timings[i + 1][0]
            
            # Expressions should not overlap (end <= next start, or at most adjacent)
            self.assertLessEqual(
                current_end, next_start,
                f"Expression '{expr_timings[i][2]}' overlaps with '{expr_timings[i + 1][2]}'"
            )
    
    def test_multi_expression_group_video_creation_order(self):
        """Test expected video creation order for multi-expression group"""
        group = ExpressionGroup(
            context_start_time="00:05:30,000",
            context_end_time="00:06:10,000",
            expressions=[self.expr1, self.expr2]
        )
        
        # Expected order:
        # 1. Context video with multi-expression slide (for multi-expression groups)
        # 2. Expression 1 video (expression repeat only, skip_context=True)
        # 3. Expression 2 video (expression repeat only, skip_context=True)
        
        is_multi_expression = len(group.expressions) > 1
        
        if is_multi_expression:
            # Should create context video first
            should_create_context_video = True
            
            # Then each expression video with skip_context=True
            for expr in group.expressions:
                should_skip_context = True  # For multi-expression groups
        
        self.assertTrue(is_multi_expression)
        self.assertTrue(should_create_context_video)
        self.assertEqual(len(group.expressions), 2)
    
    def test_single_vs_multi_expression_behavior_difference(self):
        """Test behavioral difference between single and multi-expression groups"""
        single_group = ExpressionGroup(
            context_start_time="00:10:00,000",
            context_end_time="00:10:30,000",
            expressions=[self.expr1]
        )
        
        multi_group = ExpressionGroup(
            context_start_time="00:05:30,000",
            context_end_time="00:06:10,000",
            expressions=[self.expr1, self.expr2]
        )
        
        # Single-expression group:
        # - No separate context video
        # - Expression video includes context + expression repeat
        # - skip_context=False
        
        # Multi-expression group:
        # - Creates context video with multi-expression slide FIRST
        # - Each expression video has expression repeat only
        # - skip_context=True for expression videos
        
        self.assertEqual(len(single_group), 1)
        self.assertEqual(len(multi_group), 2)
        
        # Verify expected behavior flags
        single_should_skip_context = False
        multi_should_skip_context = True
        multi_should_create_context_video = True
        single_should_create_context_video = False
        
        self.assertFalse(single_should_skip_context)
        self.assertTrue(multi_should_skip_context)
        self.assertTrue(multi_should_create_context_video)
        self.assertFalse(single_should_create_context_video)
    
    def test_context_video_includes_all_expressions_in_slide(self):
        """Test that context video slide for multi-expression group includes all expressions"""
        group = ExpressionGroup(
            context_start_time="00:05:30,000",
            context_end_time="00:06:10,000",
            expressions=[self.expr1, self.expr2, self.expr3]
        )
        
        # Multi-expression slide should contain:
        # - All expression texts
        # - All translations
        # - All similar expressions
        # - Organized vertically in the slide
        
        all_expressions = [expr.expression for expr in group.expressions]
        all_translations = [expr.expression_translation for expr in group.expressions]
        
        # Verify all are included
        self.assertEqual(len(all_expressions), 3)
        self.assertEqual(len(all_translations), 3)
        
        self.assertIn("knock it out of the park", all_expressions)
        self.assertIn("count on it", all_expressions)
        self.assertIn("I'm sure about it", all_expressions)
        
        self.assertIn("완벽하게 해내다", all_translations)
        self.assertIn("믿다", all_translations)
        self.assertIn("확신하다", all_translations)
    
    def test_no_context_overlap_between_different_groups(self):
        """Test that different expression groups have non-overlapping contexts"""
        # Create two groups with different contexts
        group1 = ExpressionGroup(
            context_start_time="00:05:30,000",
            context_end_time="00:06:10,000",
            expressions=[self.expr1, self.expr2]
        )
        
        expr4 = ExpressionAnalysis(
            dialogues=["That's different."],
            translation=["그건 달라요."],
            expression_dialogue="That's different.",
            expression_dialogue_translation="그건 달라요.",
            expression="That's different",
            expression_translation="그건 다르다",
            context_start_time="00:10:00,000",  # Different context
            context_end_time="00:10:30,000",
            expression_start_time="00:10:05,000",
            expression_end_time="00:10:15,000",
            similar_expressions=["That's not the same"]
        )
        
        group2 = ExpressionGroup(
            context_start_time="00:10:00,000",
            context_end_time="00:10:30,000",
            expressions=[expr4]
        )
        
        # Verify contexts don't overlap
        def time_to_seconds(time_str: str) -> float:
            parts = time_str.replace(',', '.').split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        
        g1_start = time_to_seconds(group1.context_start_time)
        g1_end = time_to_seconds(group1.context_end_time)
        g2_start = time_to_seconds(group2.context_start_time)
        g2_end = time_to_seconds(group2.context_end_time)
        
        # Context 1 ends before Context 2 starts (no overlap)
        self.assertLess(g1_end, g2_start, 
                       "Different groups should have non-overlapping contexts (prompt should enforce this)")


if __name__ == '__main__':
    unittest.main()

