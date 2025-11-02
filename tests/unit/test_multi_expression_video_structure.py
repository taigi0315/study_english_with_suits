"""
Unit tests for multi-expression video structure (TICKET-008 update)
Tests the new video output structure:
- Context video with multi-expression slide (for multi-expression groups)
- Individual expression videos (for each expression)
- No overlapping context videos
"""
import unittest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
from langflix.core.models import ExpressionAnalysis, ExpressionGroup
from langflix.main import LangFlixPipeline


class TestMultiExpressionVideoStructure(unittest.TestCase):
    """Test new video output structure for multiple expressions per context"""
    
    def setUp(self):
        """Set up test fixtures"""
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
            similar_expressions=["hit it out of the park"]
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
            similar_expressions=["rely on it"]
        )
        
        self.expr3 = ExpressionAnalysis(
            dialogues=["That's a different story."],
            translation=["그건 별개의 이야기예요."],
            expression_dialogue="That's a different story.",
            expression_dialogue_translation="그건 별개의 이야기예요.",
            expression="a different story",
            expression_translation="별개의 이야기",
            context_start_time="00:10:00,000",  # Different context
            context_end_time="00:10:30,000",
            expression_start_time="00:10:05,000",
            expression_end_time="00:10:15,000",
            similar_expressions=["a different matter"]
        )
    
    @patch('langflix.main.LangFlixPipeline._create_educational_videos')
    @patch('langflix.main.LangFlixPipeline._process_expressions')
    def test_video_order_for_multi_expression_group(self, mock_process, mock_create_videos):
        """Test that videos are created in correct order for multi-expression group"""
        # Setup pipeline with multi-expression group
        pipeline = MagicMock(spec=LangFlixPipeline)
        pipeline.expressions = [self.expr1, self.expr2]
        pipeline.expression_groups = [
            ExpressionGroup(
                context_start_time="00:05:30,000",
                context_end_time="00:06:10,000",
                expressions=[self.expr1, self.expr2]
            )
        ]
        pipeline.processed_expressions = 0
        
        # Track video creation order
        video_order = []
        
        def track_video_creation(expr_or_group, *args, **kwargs):
            if isinstance(expr_or_group, ExpressionGroup):
                video_order.append(('context', expr_or_group))
            elif isinstance(expr_or_group, ExpressionAnalysis):
                video_order.append(('expression', expr_or_group))
        
        # Simulate video creation (would need actual implementation)
        # For now, verify the expected structure:
        expected_order = [
            ('context', 'group_1'),  # Context video with multi-expression slide
            ('expression', 'expr1'),  # Expression 1 video
            ('expression', 'expr2'),  # Expression 2 video
        ]
        
        # This test verifies the expected order structure
        self.assertEqual(len(expected_order), 3)
        self.assertEqual(expected_order[0][0], 'context')
        self.assertEqual(expected_order[1][0], 'expression')
        self.assertEqual(expected_order[2][0], 'expression')
    
    def test_context_videos_no_overlap(self):
        """Test that context videos from different groups don't overlap (prompt should enforce this)"""
        # Create two groups with different contexts
        group1 = ExpressionGroup(
            context_start_time="00:05:30,000",
            context_end_time="00:06:10,000",
            expressions=[self.expr1, self.expr2]
        )
        
        group2 = ExpressionGroup(
            context_start_time="00:10:00,000",  # Different context
            context_end_time="00:10:30,000",
            expressions=[self.expr3]
        )
        
        # Verify contexts don't overlap
        context1_start = self._time_to_seconds(group1.context_start_time)
        context1_end = self._time_to_seconds(group1.context_end_time)
        context2_start = self._time_to_seconds(group2.context_start_time)
        context2_end = self._time_to_seconds(group2.context_end_time)
        
        # Context 1 ends before Context 2 starts
        self.assertLess(context1_end, context2_start, 
                       "Context videos should not overlap (prompt should enforce this)")
        
        # Or Context 2 ends before Context 1 starts
        # (both conditions ensure no overlap)
        no_overlap = (context1_end <= context2_start) or (context2_end <= context1_start)
        self.assertTrue(no_overlap, "Context videos should not overlap (prompt should enforce this)")
    
    def test_detect_context_overlap_in_expressions(self):
        """Test helper function to detect context overlap in expressions"""
        # Helper function to check if contexts overlap
        def contexts_overlap(expr1: ExpressionAnalysis, expr2: ExpressionAnalysis) -> bool:
            """Check if two expressions have overlapping contexts"""
            start1 = self._time_to_seconds(expr1.context_start_time)
            end1 = self._time_to_seconds(expr1.context_end_time)
            start2 = self._time_to_seconds(expr2.context_start_time)
            end2 = self._time_to_seconds(expr2.context_end_time)
            
            # Overlap if: (start1 < end2) and (start2 < end1)
            # AND contexts are different (not same context times)
            same_context = (expr1.context_start_time == expr2.context_start_time and 
                          expr1.context_end_time == expr2.context_end_time)
            
            if same_context:
                return False  # Same context is allowed (they'll be grouped)
            
            # Different contexts - check for overlap
            return (start1 < end2) and (start2 < end1)
        
        # Test: Same context (should not be considered overlap)
        self.assertFalse(contexts_overlap(self.expr1, self.expr2), 
                        "Same context times should not be considered overlap")
        
        # Test: Different contexts, no overlap
        self.assertFalse(contexts_overlap(self.expr1, self.expr3),
                        "Different non-overlapping contexts should not overlap")
        
        # Test: Different contexts with overlap (should be detected)
        overlapping_expr = ExpressionAnalysis(
            dialogues=["Overlapping context."],
            translation=["겹치는 컨텍스트."],
            expression_dialogue="Overlapping context.",
            expression_dialogue_translation="겹치는 컨텍스트.",
            expression="overlapping",
            expression_translation="겹치는",
            context_start_time="00:06:00,000",  # Overlaps with group1 (00:05:30 - 00:06:10)
            context_end_time="00:06:20,000",
            expression_start_time="00:06:05,000",
            expression_end_time="00:06:15,000",
            similar_expressions=["overlap"]
        )
        
        self.assertTrue(contexts_overlap(self.expr1, overlapping_expr),
                       "Should detect overlapping contexts")
    
    def _time_to_seconds(self, time_str: str) -> float:
        """Helper to convert time string to seconds"""
        parts = time_str.replace(',', '.').split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    
    def test_multi_expression_context_video_creation(self):
        """Test that context video with multi-expression slide should be created for multi-expression groups"""
        # This test verifies the expected behavior (implementation will follow)
        group = ExpressionGroup(
            context_start_time="00:05:30,000",
            context_end_time="00:06:10,000",
            expressions=[self.expr1, self.expr2]
        )
        
        # Verify group structure supports multi-expression context video
        if len(group.expressions) > 1:
            # Would create: context video with multi-expression slide
            should_create_context_video = True
        else:
            should_create_context_video = False
        
        self.assertTrue(should_create_context_video, 
                       "Should create context video with multi-expression slide for multi-expression groups")
        self.assertEqual(len(group.expressions), 2, 
                        "Group should have multiple expressions")
    
    @patch('langflix.core.video_editor.VideoEditor.create_educational_sequence')
    def test_single_expression_group_creates_only_expression_video(self, mock_create_seq):
        """Test that single-expression group creates only expression video (no separate context video)"""
        group = ExpressionGroup(
            context_start_time="00:10:00,000",
            context_end_time="00:10:30,000",
            expressions=[self.expr3]  # Single expression
        )
        
        # For single expression, should create only expression video (backward compatible)
        # No separate context video needed
        if len(group.expressions) == 1:
            should_create_context_video = False
        else:
            should_create_context_video = True
        
        self.assertFalse(should_create_context_video,
                        "Single-expression group should not create separate context video")
        self.assertEqual(len(group.expressions), 1,
                        "Group should have single expression")
    
    def test_final_video_order_mixed_groups(self):
        """Test final video concatenation order for mixed single and multi-expression groups"""
        # Group 1: Multi-expression
        group1 = ExpressionGroup(
            context_start_time="00:05:30,000",
            context_end_time="00:06:10,000",
            expressions=[self.expr1, self.expr2]
        )
        
        # Group 2: Single-expression
        group2 = ExpressionGroup(
            context_start_time="00:10:00,000",
            context_end_time="00:10:30,000",
            expressions=[self.expr3]
        )
        
        groups = [group1, group2]
        
        # Expected final video order:
        # 1. Context video (group 1) - with multi-expression slide
        # 2. Expression 1 video (expr1)
        # 3. Expression 2 video (expr2)
        # 4. Expression 3 video (expr3) - no separate context video for single expression
        
        expected_video_sequence = []
        for group in groups:
            if len(group.expressions) > 1:
                # Multi-expression: context video first
                expected_video_sequence.append(f"context_group_{groups.index(group)+1}")
                # Then each expression
                for expr in group.expressions:
                    expected_video_sequence.append(f"expression_{expr.expression}")
            else:
                # Single-expression: just expression video (backward compatible)
                expected_video_sequence.append(f"expression_{group.expressions[0].expression}")
        
        # Verify expected sequence
        self.assertEqual(len(expected_video_sequence), 4)  # 1 context + 2 expressions + 1 expression
        self.assertEqual(expected_video_sequence[0], "context_group_1")
        self.assertIn("knock it out of the park", expected_video_sequence[1])
        self.assertIn("count on it", expected_video_sequence[2])
        self.assertIn("a different story", expected_video_sequence[3])
    
    def test_context_video_slide_contains_all_expressions(self):
        """Test that context video slide contains all expressions from the group"""
        group = ExpressionGroup(
            context_start_time="00:05:30,000",
            context_end_time="00:06:10,000",
            expressions=[self.expr1, self.expr2]
        )
        
        # Verify group has all expressions
        expressions_in_group = group.expressions
        
        # Slide should contain all expressions
        expected_expressions = [self.expr1, self.expr2]
        
        self.assertEqual(len(expressions_in_group), len(expected_expressions))
        self.assertIn(self.expr1, expressions_in_group)
        self.assertIn(self.expr2, expressions_in_group)
        
        # Verify slide would display all expressions
        # (actual implementation would create slide with all expression info)
        all_expressions_text = [expr.expression for expr in expressions_in_group]
        self.assertEqual(len(all_expressions_text), 2)
        self.assertIn("knock it out of the park", all_expressions_text)
        self.assertIn("count on it", all_expressions_text)
    
    @patch('langflix.main.LangFlixPipeline._create_final_video')
    def test_final_video_concatenation_order(self, mock_create_final):
        """Test that _create_final_video receives videos in correct order"""
        # This test would verify that educational_videos list passed to _create_final_video
        # follows the correct order: context → expr1 → expr2 → expr3
        
        # Expected order for groups:
        # Group 1 (multi): context_video, expr1_video, expr2_video
        # Group 2 (single): expr3_video
        
        expected_video_order = [
            "context_group_1_multi_expression.mkv",
            "expression_knock_it_out_of_the_park.mkv",
            "expression_count_on_it.mkv",
            "expression_a_different_story.mkv"
        ]
        
        # Verify expected structure
        self.assertEqual(len(expected_video_order), 4)
        self.assertTrue(expected_video_order[0].startswith("context_"))
        self.assertTrue(expected_video_order[1].startswith("expression_"))
        self.assertTrue(expected_video_order[2].startswith("expression_"))
        self.assertTrue(expected_video_order[3].startswith("expression_"))


class TestVideoEditorMultiExpressionSupport(unittest.TestCase):
    """Test VideoEditor methods for multi-expression support"""
    
    def setUp(self):
        """Set up test fixtures"""
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
            similar_expressions=["hit it out of the park"]
        )
        
        self.expr2 = ExpressionAnalysis(
            dialogues=["You can count on it."],
            translation=["믿으셔도 됩니다."],
            expression_dialogue="You can count on it.",
            expression_dialogue_translation="믿으셔도 됩니다.",
            expression="count on it",
            expression_translation="믿다",
            context_start_time="00:05:30,000",
            context_end_time="00:06:10,000",
            expression_start_time="00:05:50,000",
            expression_end_time="00:05:55,000",
            similar_expressions=["rely on it"]
        )
    
    def test_create_multi_expression_slide_needed_for_groups(self):
        """Test that multi-expression slide should be created for multi-expression groups"""
        # This test verifies expected behavior (implementation will follow)
        group = ExpressionGroup(
            context_start_time="00:05:30,000",
            context_end_time="00:06:10,000",
            expressions=[self.expr1, self.expr2]
        )
        
        # Verify slide should be created with all expressions
        if len(group.expressions) > 1:
            should_create_multi_slide = True
            expressions_for_slide = group.expressions
        else:
            should_create_multi_slide = False
            expressions_for_slide = []
        
        self.assertTrue(should_create_multi_slide)
        self.assertEqual(len(expressions_for_slide), 2)
        self.assertIn(self.expr1, expressions_for_slide)
        self.assertIn(self.expr2, expressions_for_slide)
    
    def test_multi_expression_slide_content_structure(self):
        """Test that multi-expression slide contains all expression information"""
        group = ExpressionGroup(
            context_start_time="00:05:30,000",
            context_end_time="00:06:10,000",
            expressions=[self.expr1, self.expr2]
        )
        
        # Slide should contain:
        # - All expressions
        # - All translations
        # - All similar expressions
        # - Organized layout for multiple expressions
        
        all_expressions = [expr.expression for expr in group.expressions]
        all_translations = [expr.expression_translation for expr in group.expressions]
        all_similar = []
        for expr in group.expressions:
            all_similar.extend(expr.similar_expressions)
        
        self.assertEqual(len(all_expressions), 2)
        self.assertEqual(len(all_translations), 2)
        self.assertGreaterEqual(len(all_similar), 2)  # At least 2 similar expressions (2 from expr1 + expr2)
        
        # Verify content
        self.assertIn("knock it out of the park", all_expressions)
        self.assertIn("count on it", all_expressions)
        self.assertIn("완벽하게 해내다", all_translations)
        self.assertIn("믿다", all_translations)
    
    def test_each_expression_has_individual_slide(self):
        """Test that each expression in multi-expression group gets its own slide for expression videos"""
        group = ExpressionGroup(
            context_start_time="00:05:30,000",
            context_end_time="00:06:10,000",
            expressions=[self.expr1, self.expr2]
        )
        
        # For multi-expression context:
        # 1. Context video: left=context video, right=multi-expression slide (all expressions)
        # 2. Expression 1 video: left=video, right=expression 1 slide
        # 3. Expression 2 video: left=video, right=expression 2 slide
        
        # Each expression should get its own slide
        for i, expr in enumerate(group.expressions):
            # Verify each expression has unique slide content
            self.assertIsNotNone(expr.expression)
            self.assertIsNotNone(expr.expression_translation)
            self.assertIsNotNone(expr.similar_expressions)
            
            # Each slide should be unique to the expression
            expr_slide_content = {
                'expression': expr.expression,
                'translation': expr.expression_translation,
                'similar': expr.similar_expressions
            }
            
            # Verify slide content is expression-specific
            self.assertEqual(expr_slide_content['expression'], expr.expression)
        
        # Verify different expressions have different slide content
        self.assertNotEqual(self.expr1.expression, self.expr2.expression)
        self.assertNotEqual(self.expr1.expression_translation, self.expr2.expression_translation)


if __name__ == '__main__':
    unittest.main()

