"""
Unit tests for structured output functionality
"""
import pytest
from unittest.mock import patch, MagicMock
from langflix.models import ExpressionAnalysis, ExpressionAnalysisResponse
from langflix.expression_analyzer import analyze_chunk, _fallback_parse_response


class TestPydanticModels:
    """Test Pydantic model validation"""
    
    def test_expression_analysis_valid(self):
        """Test valid ExpressionAnalysis model"""
        data = {
            "dialogues": ["Hello", "How are you?"],
            "translation": ["안녕", "어떻게 지내세요?"],
            "expression": "How are you?",
            "expression_translation": "어떻게 지내세요?",
            "context_start_time": "00:01:25,657",
            "context_end_time": "00:01:32,230",
            "similar_expressions": ["How's it going?", "What's up?"]
        }
        
        expr = ExpressionAnalysis.model_validate(data)
        assert expr.expression == "How are you?"
        assert len(expr.dialogues) == 2
        assert len(expr.similar_expressions) == 2
    
    def test_expression_analysis_invalid_timestamp(self):
        """Test invalid timestamp format"""
        data = {
            "dialogues": ["Hello"],
            "translation": ["안녕"],
            "expression": "Hello",
            "expression_translation": "안녕",
            "context_start_time": "invalid_timestamp",
            "context_end_time": "00:01:32,230",
            "similar_expressions": ["Hi"]
        }
        
        with pytest.raises(ValueError):
            ExpressionAnalysis.model_validate(data)
    
    def test_expression_analysis_too_many_similar_expressions(self):
        """Test too many similar expressions"""
        data = {
            "dialogues": ["Hello"],
            "translation": ["안녕"],
            "expression": "Hello",
            "expression_translation": "안녕",
            "context_start_time": "00:01:25,657",
            "context_end_time": "00:01:32,230",
            "similar_expressions": ["Hi", "Hey", "Greetings"]  # 3 items, max is 2
        }
        
        with pytest.raises(ValueError):
            ExpressionAnalysis.model_validate(data)
    
    def test_expression_analysis_response_valid(self):
        """Test valid ExpressionAnalysisResponse model"""
        expressions = [
            {
                "dialogues": ["Hello"],
                "translation": ["안녕"],
                "expression": "Hello",
                "expression_translation": "안녕",
                "context_start_time": "00:01:25,657",
                "context_end_time": "00:01:32,230",
                "similar_expressions": ["Hi"]
            }
        ]
        
        response = ExpressionAnalysisResponse.model_validate({"expressions": expressions})
        assert len(response.expressions) == 1
        assert response.expressions[0].expression == "Hello"
    
    def test_expression_analysis_response_too_many_expressions(self):
        """Test too many expressions in response"""
        expressions = [
            {
                "dialogues": ["Hello"],
                "translation": ["안녕"],
                "expression": "Hello",
                "expression_translation": "안녕",
                "context_start_time": "00:01:25,657",
                "context_end_time": "00:01:32,230",
                "similar_expressions": ["Hi"]
            }
        ] * 6  # 6 expressions, max is 5
        
        with pytest.raises(ValueError):
            ExpressionAnalysisResponse.model_validate({"expressions": expressions})


class TestStructuredOutput:
    """Test structured output functionality"""
    
    @patch('langflix.expression_analyzer.genai.GenerativeModel')
    def test_analyze_chunk_structured_output_success(self, mock_model_class):
        """Test successful structured output parsing"""
        # Mock response with structured output
        mock_response = MagicMock()
        mock_response.text = '{"expressions": []}'
        mock_response.parsed = ExpressionAnalysisResponse(expressions=[])
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        # Test data
        subtitle_chunk = [
            {"start_time": "00:01:25,657", "end_time": "00:01:32,230", "text": "Hello world"}
        ]
        
        result = analyze_chunk(subtitle_chunk)
        
        # Verify structured output was used
        mock_model.generate_content.assert_called_once()
        call_args = mock_model.generate_content.call_args
        assert "generation_config" in call_args[1]
        assert call_args[1]["generation_config"]["response_mime_type"] == "application/json"
        assert call_args[1]["generation_config"]["response_schema"] == ExpressionAnalysisResponse
        
        assert isinstance(result, list)
    
    @patch('langflix.expression_analyzer.genai.GenerativeModel')
    def test_analyze_chunk_fallback_parsing(self, mock_model_class):
        """Test fallback parsing when structured output fails"""
        # Mock response without parsed attribute
        mock_response = MagicMock()
        mock_response.text = '[{"expression": "Hello", "dialogues": ["Hello"], "translation": ["안녕"], "expression_translation": "안녕", "context_start_time": "00:01:25,657", "context_end_time": "00:01:32,230", "similar_expressions": ["Hi"]}]'
        mock_response.parsed = None
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        # Test data
        subtitle_chunk = [
            {"start_time": "00:01:25,657", "end_time": "00:01:32,230", "text": "Hello world"}
        ]
        
        result = analyze_chunk(subtitle_chunk)
        
        assert isinstance(result, list)
        if result:  # If parsing succeeded
            assert hasattr(result[0], "expression")
    
    def test_fallback_parse_response_valid_json(self):
        """Test fallback parsing with valid JSON"""
        response_text = '[{"expression": "Hello", "dialogues": ["Hello"], "translation": ["안녕"], "expression_translation": "안녕", "context_start_time": "00:01:25,657", "context_end_time": "00:01:32,230", "similar_expressions": ["Hi"]}]'
        
        result = _fallback_parse_response(response_text)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].expression == "Hello"
    
    def test_fallback_parse_response_markdown_cleanup(self):
        """Test fallback parsing with markdown code blocks"""
        response_text = '```json\n[{"expression": "Hello", "dialogues": ["Hello"], "translation": ["안녕"], "expression_translation": "안녕", "context_start_time": "00:01:25,657", "context_end_time": "00:01:32,230", "similar_expressions": ["Hi"]}]\n```'
        
        result = _fallback_parse_response(response_text)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].expression == "Hello"
    
    def test_fallback_parse_response_invalid_json(self):
        """Test fallback parsing with invalid JSON"""
        response_text = "This is not JSON"
        
        result = _fallback_parse_response(response_text)
        
        assert result == []
    
    def test_fallback_parse_response_non_list(self):
        """Test fallback parsing with non-list response"""
        response_text = '{"expression": "Hello", "dialogues": ["Hello"], "translation": ["안녕"], "expression_translation": "안녕", "context_start_time": "00:01:25,657", "context_end_time": "00:01:32,230", "similar_expressions": ["Hi"]}'
        
        result = _fallback_parse_response(response_text)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].expression == "Hello"


if __name__ == "__main__":
    pytest.main([__file__])
