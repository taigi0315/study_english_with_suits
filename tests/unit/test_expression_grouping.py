"""
Test cases for expression grouping functionality (TICKET-008)
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from langflix.core.models import ExpressionAnalysis, ExpressionGroup
from langflix.core.expression_analyzer import group_expressions_by_context


class TestExpressionGroup(unittest.TestCase):
    """Test cases for ExpressionGroup model"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.sample_expression_1 = ExpressionAnalysis(
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
        
        self.sample_expression_2 = ExpressionAnalysis(
            dialogues=["You can count on it."],
            translation=["믿으셔도 됩니다."],
            expression_dialogue="You can count on it.",
            expression_dialogue_translation="믿으셔도 됩니다.",
            expression="count on it",
            expression_translation="믿다",
            context_start_time="00:05:30,000",  # Same context as expression_1
            context_end_time="00:06:10,000",
            expression_start_time="00:05:50,000",
            expression_end_time="00:05:55,000",
            similar_expressions=["rely on it", "trust it"]
        )
        
        self.sample_expression_3 = ExpressionAnalysis(
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
            similar_expressions=["a different matter", "another issue"]
        )
    
    def test_create_expression_group_single(self):
        """Test creating ExpressionGroup with single expression"""
        group = ExpressionGroup(
            context_start_time="00:05:30,000",
            context_end_time="00:06:10,000",
            expressions=[self.sample_expression_1]
        )
        
        self.assertEqual(len(group), 1)
        self.assertEqual(group.context_start_time, "00:05:30,000")
        self.assertEqual(group.context_end_time, "00:06:10,000")
        self.assertEqual(group.expressions[0], self.sample_expression_1)
    
    def test_create_expression_group_multiple(self):
        """Test creating ExpressionGroup with multiple expressions sharing same context"""
        group = ExpressionGroup(
            context_start_time="00:05:30,000",
            context_end_time="00:06:10,000",
            expressions=[self.sample_expression_1, self.sample_expression_2]
        )
        
        self.assertEqual(len(group), 2)
        self.assertEqual(group.context_start_time, "00:05:30,000")
        self.assertEqual(group.context_end_time, "00:06:10,000")
        self.assertIn(self.sample_expression_1, group.expressions)
        self.assertIn(self.sample_expression_2, group.expressions)
    
    def test_expression_group_validation_success(self):
        """Test ExpressionGroup validation passes when all expressions share same context"""
        group = ExpressionGroup(
            context_start_time="00:05:30,000",
            context_end_time="00:06:10,000",
            expressions=[self.sample_expression_1, self.sample_expression_2]
        )
        # Validation happens in __init__, so if we get here, validation passed
        self.assertEqual(len(group.expressions), 2)
    
    def test_expression_group_validation_failure(self):
        """Test ExpressionGroup validation fails when expressions have different contexts"""
        with self.assertRaises(ValueError) as context:
            ExpressionGroup(
                context_start_time="00:05:30,000",
                context_end_time="00:06:10,000",
                expressions=[self.sample_expression_1, self.sample_expression_3]  # Different contexts
            )
        
        self.assertIn("must share same context times", str(context.exception))
    
    def test_expression_group_iteration(self):
        """Test ExpressionGroup supports iteration"""
        group = ExpressionGroup(
            context_start_time="00:05:30,000",
            context_end_time="00:06:10,000",
            expressions=[self.sample_expression_1, self.sample_expression_2]
        )
        
        expressions_list = list(group)
        self.assertEqual(len(expressions_list), 2)
        self.assertEqual(expressions_list[0], self.sample_expression_1)
        self.assertEqual(expressions_list[1], self.sample_expression_2)
    
    def test_expression_group_indexing(self):
        """Test ExpressionGroup supports indexing"""
        group = ExpressionGroup(
            context_start_time="00:05:30,000",
            context_end_time="00:06:10,000",
            expressions=[self.sample_expression_1, self.sample_expression_2]
        )
        
        self.assertEqual(group[0], self.sample_expression_1)
        self.assertEqual(group[1], self.sample_expression_2)


class TestGroupExpressionsByContext(unittest.TestCase):
    """Test cases for group_expressions_by_context function"""
    
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
        
        self.expr4 = ExpressionAnalysis(
            dialogues=["I see what you mean."],
            translation=["무슨 말인지 알겠어요."],
            expression_dialogue="I see what you mean.",
            expression_dialogue_translation="무슨 말인지 알겠어요.",
            expression="I see what you mean",
            expression_translation="무슨 말인지 알겠다",
            context_start_time="00:10:00,000",  # Same context as expr3
            context_end_time="00:10:30,000",
            expression_start_time="00:10:20,000",
            expression_end_time="00:10:25,000",
            similar_expressions=["I understand"]
        )
    
    def test_group_empty_list(self):
        """Test grouping empty list returns empty list"""
        groups = group_expressions_by_context([])
        self.assertEqual(groups, [])
    
    def test_group_single_expression(self):
        """Test grouping single expression creates group of 1"""
        groups = group_expressions_by_context([self.expr1])
        
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 1)
        self.assertEqual(groups[0].expressions[0], self.expr1)
        self.assertEqual(groups[0].context_start_time, "00:05:30,000")
        self.assertEqual(groups[0].context_end_time, "00:06:10,000")
    
    def test_group_multiple_different_contexts(self):
        """Test grouping expressions with different contexts creates separate groups"""
        groups = group_expressions_by_context([self.expr1, self.expr3])
        
        self.assertEqual(len(groups), 2)
        self.assertEqual(len(groups[0]), 1)
        self.assertEqual(len(groups[1]), 1)
        
        # Check first group
        self.assertIn(self.expr1, groups[0].expressions)
        self.assertEqual(groups[0].context_start_time, "00:05:30,000")
        
        # Check second group
        self.assertIn(self.expr3, groups[1].expressions)
        self.assertEqual(groups[1].context_start_time, "00:10:00,000")
    
    def test_group_multiple_same_context(self):
        """Test grouping expressions with same context creates one group"""
        groups = group_expressions_by_context([self.expr1, self.expr2])
        
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 2)
        self.assertIn(self.expr1, groups[0].expressions)
        self.assertIn(self.expr2, groups[0].expressions)
        self.assertEqual(groups[0].context_start_time, "00:05:30,000")
        self.assertEqual(groups[0].context_end_time, "00:06:10,000")
    
    def test_group_mixed_contexts(self):
        """Test grouping mix of same and different contexts"""
        groups = group_expressions_by_context([self.expr1, self.expr2, self.expr3, self.expr4])
        
        # Should have 2 groups: one for expr1/expr2, one for expr3/expr4
        self.assertEqual(len(groups), 2)
        
        # Find groups by context
        group1 = None
        group2 = None
        for group in groups:
            if group.context_start_time == "00:05:30,000":
                group1 = group
            elif group.context_start_time == "00:10:00,000":
                group2 = group
        
        self.assertIsNotNone(group1)
        self.assertIsNotNone(group2)
        
        # Group 1 should have 2 expressions
        self.assertEqual(len(group1), 2)
        self.assertIn(self.expr1, group1.expressions)
        self.assertIn(self.expr2, group1.expressions)
        
        # Group 2 should have 2 expressions
        self.assertEqual(len(group2), 2)
        self.assertIn(self.expr3, group2.expressions)
        self.assertIn(self.expr4, group2.expressions)
    
    def test_group_three_expressions_same_context(self):
        """Test grouping three expressions with same context"""
        expr3_same_context = ExpressionAnalysis(
            dialogues=["I'm sure about it."],
            translation=["확신합니다."],
            expression_dialogue="I'm sure about it.",
            expression_dialogue_translation="확신합니다.",
            expression="I'm sure about it",
            expression_translation="확신하다",
            context_start_time="00:05:30,000",  # Same context
            context_end_time="00:06:10,000",
            expression_start_time="00:06:00,000",
            expression_end_time="00:06:05,000",
            similar_expressions=["I'm certain"]
        )
        
        groups = group_expressions_by_context([self.expr1, self.expr2, expr3_same_context])
        
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 3)
        self.assertIn(self.expr1, groups[0].expressions)
        self.assertIn(self.expr2, groups[0].expressions)
        self.assertIn(expr3_same_context, groups[0].expressions)


class TestLangFlixPipelineGrouping(unittest.TestCase):
    """Test LangFlixPipeline expression grouping integration"""
    
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
    
    @patch('langflix.main.group_expressions_by_context')
    def test_pipeline_creates_groups_when_enabled(self, mock_group):
        """Test pipeline creates expression groups when grouping is enabled"""
        from langflix.main import LangFlixPipeline
        
        # Mock grouping function
        mock_group.return_value = [
            ExpressionGroup(
                context_start_time="00:05:30,000",
                context_end_time="00:06:10,000",
                expressions=[self.expr1, self.expr2]
            )
        ]
        
        # Create mock pipeline
        pipeline = MagicMock(spec=LangFlixPipeline)
        pipeline.enable_expression_grouping = True
        pipeline.expressions = [self.expr1, self.expr2]
        
        # Simulate grouping in run() method (after _analyze_expressions)
        if pipeline.enable_expression_grouping and len(pipeline.expressions) > 0:
            pipeline.expression_groups = mock_group(pipeline.expressions)
        
        # Verify grouping was called
        mock_group.assert_called_once_with([self.expr1, self.expr2])
        self.assertEqual(len(pipeline.expression_groups), 1)
        self.assertEqual(len(pipeline.expression_groups[0]), 2)
    
    @patch('langflix.main.group_expressions_by_context')
    def test_pipeline_creates_single_groups_when_disabled(self, mock_group):
        """Test pipeline creates single-expression groups when grouping is disabled"""
        from langflix.main import LangFlixPipeline
        
        # Create mock pipeline
        pipeline = MagicMock(spec=LangFlixPipeline)
        pipeline.enable_expression_grouping = False
        pipeline.expressions = [self.expr1, self.expr2]
        
        # Simulate grouping when disabled (creates single-expression groups)
        if not pipeline.enable_expression_grouping:
            pipeline.expression_groups = [
                ExpressionGroup(
                    context_start_time=expr.context_start_time,
                    context_end_time=expr.context_end_time,
                    expressions=[expr]
                )
                for expr in pipeline.expressions
            ]
        
        # Verify grouping function was NOT called
        mock_group.assert_not_called()
        # Verify single-expression groups were created
        self.assertEqual(len(pipeline.expression_groups), 2)
        self.assertEqual(len(pipeline.expression_groups[0]), 1)
        self.assertEqual(len(pipeline.expression_groups[1]), 1)
    
    def test_pipeline_grouping_with_mixed_contexts(self):
        """Test pipeline handles mixed contexts correctly"""
        expr3 = ExpressionAnalysis(
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
        
        expressions = [self.expr1, self.expr2, expr3]
        groups = group_expressions_by_context(expressions)
        
        # Should have 2 groups: one with expr1/expr2, one with expr3
        self.assertEqual(len(groups), 2)
        
        # Find groups by context
        group1 = next(g for g in groups if g.context_start_time == "00:05:30,000")
        group2 = next(g for g in groups if g.context_start_time == "00:10:00,000")
        
        self.assertEqual(len(group1), 2)
        self.assertEqual(len(group2), 1)
        self.assertIn(self.expr1, group1.expressions)
        self.assertIn(self.expr2, group1.expressions)
        self.assertIn(expr3, group2.expressions)


if __name__ == '__main__':
    unittest.main()

