"""
Test cases for expression_analyzer.py
"""
import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add the parent directory to the path so we can import langflix
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langflix.expression_analyzer import analyze_chunk


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
        """Test successful analysis of a subtitle chunk."""
        # Mock the model and its response
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        
        # Mock response with valid JSON
        mock_response = MagicMock()
        mock_response.text = json.dumps([
            {
                "expression": "You gotta be kidding me.",
                "definition": "An expression of disbelief or astonishment.",
                "translation": {"korean": "농담하는 거겠지."},
                "context_start_time": "00:01:14,000",
                "context_end_time": "00:01:18,000",
                "similar_expressions": ["You can't be serious.", "Are you for real?"]
            }
        ])
        mock_model.generate_content.return_value = mock_response
        
        # Test the function
        result = analyze_chunk(self.sample_subtitle_chunk)
        
        # Assertions
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["expression"], "You gotta be kidding me.")
        mock_model.generate_content.assert_called_once()
    
    @patch('langflix.expression_analyzer.genai.GenerativeModel')
    def test_analyze_chunk_invalid_json(self, mock_model_class):
        """Test handling of invalid JSON response."""
        # Mock the model and its response
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        
        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.text = "This is not valid JSON"
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
        mock_model.generate_content.return_value = mock_response
        
        # Test the function
        result = analyze_chunk(self.sample_subtitle_chunk)
        
        # Should return empty list
        self.assertEqual(result, [])
    
    @patch('langflix.expression_analyzer.genai.GenerativeModel')
    def test_analyze_chunk_with_markdown_blocks(self, mock_model_class):
        """Test handling of response wrapped in markdown code blocks."""
        # Mock the model and its response
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        
        # Mock response with markdown code blocks
        mock_response = MagicMock()
        mock_response.text = "```json\n" + json.dumps([{"expression": "test"}]) + "\n```"
        mock_model.generate_content.return_value = mock_response
        
        # Test the function
        result = analyze_chunk(self.sample_subtitle_chunk)
        
        # Should successfully parse JSON
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)


if __name__ == '__main__':
    unittest.main()
