"""
Test cases for expression_analyzer.py - Updated for structured output
"""
import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add the parent directory to the path so we can import langflix
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langflix.expression_analyzer import analyze_chunk
from langflix.models import ExpressionAnalysis, ExpressionAnalysisResponse


class TestExpressionAnalyzer(unittest.TestCase):
    """Test cases for the expression analyzer module."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_subtitle_chunk = [
            {
                "start_time": "00:01:15,250",
                "end_time": "00:01:17,500", 
                "text": "You gotta be kidding me."
            },
            {
                "start_time": "00:01:18,000",
                "end_time": "00:01:20,000",
                "text": "I'm serious about this."
            }
        ]
    
    @patch('langflix.expression_analyzer.genai.GenerativeModel')
    def test_analyze_chunk_success(self, mock_model_class):
        """Test successful analysis of a subtitle chunk with structured output."""
        # Mock the model and its response
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        
        # Mock structured response
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "expressions": [{
                "dialogues": ["You gotta be kidding me."],
                "translation": ["농담하는 거겠지."],
                "expression": "You gotta be kidding me.",
                "expression_translation": "농담하는 거겠지.",
                "context_start_time": "00:01:14,000",
                "context_end_time": "00:01:18,000",
                "similar_expressions": ["You can't be serious.", "Are you for real?"]
            }]
        })
        mock_response.parsed = None  # Simulate fallback parsing
        mock_model.generate_content.return_value = mock_response
        
        # Test the function
        result = analyze_chunk(self.sample_subtitle_chunk)
        
        # Assertions
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], ExpressionAnalysis)
        self.assertEqual(result[0].expression, "You gotta be kidding me.")
        mock_model.generate_content.assert_called_once()
    
    def test_analyze_chunk_empty_input(self):
        """Test handling of empty input."""
        with self.assertRaises(ValueError):
            analyze_chunk([])
    
    @patch.dict(os.environ, {}, clear=True)
    def test_analyze_chunk_no_api_key(self):
        """Test handling of missing API key."""
        with self.assertRaises(RuntimeError):
            analyze_chunk(self.sample_subtitle_chunk)
    
    @patch('langflix.expression_analyzer.genai.GenerativeModel')
    def test_analyze_chunk_invalid_json(self, mock_model_class):
        """Test handling of invalid JSON response."""
        # Mock the model and its response
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        
        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.text = "This is not valid JSON"
        mock_response.parsed = None
        mock_model.generate_content.return_value = mock_response
        
        # Test the function
        result = analyze_chunk(self.sample_subtitle_chunk)
        
        # Should return empty list on JSON error
        self.assertEqual(result, [])
    
    @patch('langflix.expression_analyzer.genai.GenerativeModel')
    def test_analyze_chunk_empty_response(self, mock_model_class):
        """Test handling of empty response."""
        # Mock the model and its response
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        
        # Mock empty response
        mock_response = MagicMock()
        mock_response.text = ""
        mock_response.parsed = None
        mock_model.generate_content.return_value = mock_response
        
        # Test the function
        result = analyze_chunk(self.sample_subtitle_chunk)
        
        # Should return empty list
        self.assertEqual(result, [])
    
    @patch('langflix.expression_analyzer.genai.GenerativeModel')
    def test_analyze_chunk_with_structured_output(self, mock_model_class):
        """Test handling of structured output with parsed response."""
        # Mock the model and its response
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        
        # Create mock structured response
        mock_expression = ExpressionAnalysis(
            dialogues=["You gotta be kidding me."],
            translation=["농담하는 거겠지."],
            expression="You gotta be kidding me.",
            expression_translation="농담하는 거겠지.",
            context_start_time="00:01:14,000",
            context_end_time="00:01:18,000",
            similar_expressions=["You can't be serious."]
        )
        mock_response_obj = ExpressionAnalysisResponse(expressions=[mock_expression])
        
        mock_response = MagicMock()
        mock_response.text = "structured response"
        mock_response.parsed = mock_response_obj
        mock_model.generate_content.return_value = mock_response
        
        # Test the function
        result = analyze_chunk(self.sample_subtitle_chunk)
        
        # Should return structured objects
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], ExpressionAnalysis)
        self.assertEqual(result[0].expression, "You gotta be kidding me.")


if __name__ == '__main__':
    unittest.main()
