"""
Unit tests for max_expressions_per_context validation (TICKET-025)
Tests that settings.get_max_expressions_per_context() validates and clamps values to 1-3 range
"""
import unittest
from unittest.mock import patch, MagicMock
from langflix import settings


class TestMaxExpressionsPerContextValidation(unittest.TestCase):
    """Test max_expressions_per_context validation and clamping"""
    
    @patch('langflix.settings.get_expression_llm')
    def test_default_value_is_3(self, mock_get_expression_llm):
        """Test that default value is 3 when not specified in config"""
        mock_get_expression_llm.return_value = {}
        
        result = settings.get_max_expressions_per_context()
        
        self.assertEqual(result, 3)
    
    @patch('langflix.settings.get_expression_llm')
    def test_valid_value_1(self, mock_get_expression_llm):
        """Test that valid value 1 is returned as-is"""
        mock_get_expression_llm.return_value = {'max_expressions_per_context': 1}
        
        result = settings.get_max_expressions_per_context()
        
        self.assertEqual(result, 1)
    
    @patch('langflix.settings.get_expression_llm')
    def test_valid_value_2(self, mock_get_expression_llm):
        """Test that valid value 2 is returned as-is"""
        mock_get_expression_llm.return_value = {'max_expressions_per_context': 2}
        
        result = settings.get_max_expressions_per_context()
        
        self.assertEqual(result, 2)
    
    @patch('langflix.settings.get_expression_llm')
    def test_valid_value_3(self, mock_get_expression_llm):
        """Test that valid value 3 is returned as-is"""
        mock_get_expression_llm.return_value = {'max_expressions_per_context': 3}
        
        result = settings.get_max_expressions_per_context()
        
        self.assertEqual(result, 3)
    
    @patch('langflix.settings.get_expression_llm')
    @patch('langflix.settings.logger')
    def test_value_below_range_clamped_to_1(self, mock_logger, mock_get_expression_llm):
        """Test that value below 1 is clamped to 1 with warning"""
        mock_get_expression_llm.return_value = {'max_expressions_per_context': 0}
        
        result = settings.get_max_expressions_per_context()
        
        self.assertEqual(result, 1)
        mock_logger.warning.assert_called_once()
        warning_call = str(mock_logger.warning.call_args)
        self.assertIn('less than 1', warning_call)
        self.assertIn('using 1', warning_call)
    
    @patch('langflix.settings.get_expression_llm')
    @patch('langflix.settings.logger')
    def test_value_above_range_clamped_to_3(self, mock_logger, mock_get_expression_llm):
        """Test that value above 3 is clamped to 3 with warning"""
        mock_get_expression_llm.return_value = {'max_expressions_per_context': 5}
        
        result = settings.get_max_expressions_per_context()
        
        self.assertEqual(result, 3)
        mock_logger.warning.assert_called_once()
        warning_call = str(mock_logger.warning.call_args)
        self.assertIn('greater than 3', warning_call)
        self.assertIn('using 3', warning_call)
    
    @patch('langflix.settings.get_expression_llm')
    @patch('langflix.settings.logger')
    def test_negative_value_clamped_to_1(self, mock_logger, mock_get_expression_llm):
        """Test that negative value is clamped to 1 with warning"""
        mock_get_expression_llm.return_value = {'max_expressions_per_context': -1}
        
        result = settings.get_max_expressions_per_context()
        
        self.assertEqual(result, 1)
        mock_logger.warning.assert_called_once()
    
    @patch('langflix.settings.get_expression_llm')
    @patch('langflix.settings.logger')
    def test_large_value_clamped_to_3(self, mock_logger, mock_get_expression_llm):
        """Test that very large value is clamped to 3 with warning"""
        mock_get_expression_llm.return_value = {'max_expressions_per_context': 100}
        
        result = settings.get_max_expressions_per_context()
        
        self.assertEqual(result, 3)
        mock_logger.warning.assert_called_once()


if __name__ == '__main__':
    unittest.main()

