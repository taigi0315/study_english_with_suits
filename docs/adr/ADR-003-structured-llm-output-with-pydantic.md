# ADR-003: Structured LLM Output with Pydantic Models

**Date:** 2025-10-19  
**Status:** Accepted  
**Deciders:** Development Team  

## Context

LangFlix uses Large Language Models (LLMs) to analyze TV show subtitles and extract educational expressions. The LLM responses need to be parsed and validated to ensure data consistency and reliability throughout the processing pipeline.

Originally, the application relied on unstructured text responses from the LLM that required manual parsing and validation. This approach led to several challenges:

1. **Data Consistency**: LLM responses varied in format, making parsing unreliable
2. **Error Handling**: Difficult to validate LLM output and handle malformed responses
3. **Type Safety**: No compile-time guarantees about data structure
4. **Maintainability**: Parsing logic was scattered and hard to maintain
5. **Debugging**: Hard to trace issues with LLM response processing

The application needed a robust way to ensure that LLM responses conform to expected schema and can be reliably processed by downstream components.

## Decision

We will implement structured output validation using Pydantic models to ensure consistent, validated data from LLM responses.

### Implementation

1. **Define Pydantic Models**: Create structured models for expected LLM output
2. **Response Validation**: Parse and validate LLM responses against these models
3. **Error Handling**: Graceful handling of malformed or incomplete responses
4. **Type Safety**: Leverage Python type hints throughout the pipeline

### Model Definition

```python
# langflix/models.py
from typing import List, Optional
from pydantic import BaseModel, Field

class ExpressionAnalysis(BaseModel):
    """
    Model for a single expression analysis result
    """
    dialogues: List[str] = Field(
        description="Complete dialogue lines in the scene",
        min_length=1
    )
    translation: List[str] = Field(
        description="Translations of all dialogue lines in the same order",
        min_length=1
    )
    expression: str = Field(
        description="The main expression/phrase to learn",
        min_length=1
    )
    expression_translation: str = Field(
        description="Translation of the main expression",
        min_length=1
    )
    context_start_time: str = Field(
        description="Timestamp where conversational context should BEGIN",
        pattern=r"^\d{2}:\d{2}:\d{2}[.,]\d{3,6}$"
    )
    context_end_time: str = Field(
        description="Timestamp where conversational context should END", 
        pattern=r"^\d{2}:\d{2}:\d{2}[.,]\d{3,6}$"
    )
    expression_start_time: Optional[str] = Field(
        default=None,
        description="Exact timestamp where the expression phrase begins",
        pattern=r"^\d{2}:\d{2}:\d{2}[.,]\d{3,6}$"
    )
    expression_end_time: Optional[str] = Field(
        default=None,
        description="Exact timestamp where the expression phrase ends",
        pattern=r"^\d{2}:\d{2}:\d{2}[.,]\d{3,6}$"
    )
    similar_expressions: List[str] = Field(
        description="List of 1-3 similar expressions or alternative ways to say the same thing",
        min_length=1,
    )

class ExpressionAnalysisResponse(BaseModel):
    """
    Model for the complete response from LLM
    """
    expressions: List[ExpressionAnalysis] = Field(
        description="List of analyzed expressions",
    )
```

### LLM Integration

```python
# langflix/expression_analyzer.py
from .models import ExpressionAnalysis, ExpressionAnalysisResponse

def _extract_response_text(response) -> str:
    """Extract text from LLM response with proper error handling."""
    try:
        if hasattr(response, 'text'):
            return response.text
        elif hasattr(response, 'candidates') and response.candidates:
            return response.candidates[0].content.parts[0].text
        else:
            logger.error("Unexpected response format")
            return ""
    except Exception as e:
        logger.error(f"Error extracting response text: {e}")
        return ""

def _validate_and_filter_expressions(expressions: List[ExpressionAnalysis]) -> List[ExpressionAnalysis]:
    """Validate expressions and filter out those with validation issues."""
    validated_expressions = []
    
    for i, expr in enumerate(expressions):
        try:
            # Check dialogues and translation count mismatch
            dialogues_count = len(expr.dialogues) if expr.dialogues else 0
            translation_count = len(expr.translation) if expr.translation else 0
            
            if dialogues_count != translation_count:
                logger.error(f"Dropping expression {i+1}: '{expr.expression}' - "
                           f"Dialogue/translation count mismatch: {dialogues_count} dialogues vs {translation_count} translations")
                continue
            
            # Additional validation can be added here
            validated_expressions.append(expr)
            
        except Exception as e:
            logger.error(f"Error validating expression {i+1}: {e}")
            continue
    
    return validated_expressions

def analyze_chunk(subtitle_chunk: List[dict], language_level: str = None, language_code: str = "ko") -> List[ExpressionAnalysis]:
    """Analyze subtitle chunk with structured output validation."""
    try:
        # Generate and send prompt to LLM
        prompt = get_prompt_for_chunk(subtitle_chunk, language_level, language_code)
        response = _generate_content_with_retry(model, prompt, max_retries=max_retries)
        
        # Extract and parse response
        response_text = _extract_response_text(response)
        if not response_text:
            logger.error("Empty response from LLM")
            return []
        
        # Parse JSON and validate against Pydantic models
        try:
            response_data = json.loads(response_text)
            analysis_response = ExpressionAnalysisResponse(**response_data)
            
            # Additional validation and filtering
            validated_expressions = _validate_and_filter_expressions(analysis_response.expressions)
            
            return validated_expressions
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return []
        except ValidationError as e:
            logger.error(f"LLM response validation failed: {e}")
            return []
            
    except Exception as e:
        logger.error(f"Error analyzing chunk: {e}")
        return []
```

## Consequences

### Positive

1. **Data Consistency**: Guaranteed structure for all LLM responses
2. **Type Safety**: Compile-time validation and proper type hints throughout
3. **Error Handling**: Clear validation errors and graceful degradation
4. **Maintainability**: Centralized model definitions make schema changes easier
5. **Documentation**: Models serve as API documentation
6. **Development Experience**: Better IDE support and static analysis

### Negative

1. **Additional Dependencies**: Pydantic adds to project dependencies
2. **Performance Overhead**: Validation adds minimal processing overhead
3. **Complexity**: More sophisticated error handling required

### Risks

1. **LLM Response Format Changes**: LLM might return unexpected format
   - **Mitigation**: Comprehensive error handling and fallback mechanisms

2. **Validation Too Strict**: Pydantic validation might be too restrictive
   - **Mitigation**: Careful field definitions with appropriate optional fields

3. **Performance Impact**: Validation overhead for large responses
   - **Mitigation**: Minimal overhead observed in practice, can be optimized if needed

## Alternatives Considered

1. **Manual Parsing**: Continue with manual text parsing
   - **Rejected**: Too error-prone and difficult to maintain

2. **JSON Schema**: Use JSON Schema for validation
   - **Rejected**: Pydantic provides better Python integration and type safety

3. **Dataclasses**: Use Python dataclasses for structure
   - **Rejected**: Pydantic provides validation and better error messages

4. **Custom Validation**: Build custom validation logic
   - **Rejected**: Pydantic is more mature and feature-rich

## Implementation Details

- **Models**: Defined in `langflix/models.py` with comprehensive field validation
- **Integration**: Used throughout `expression_analyzer.py` for response processing
- **Error Handling**: Graceful degradation with detailed logging
- **Backwards Compatibility**: No breaking changes to existing API
- **Documentation**: Models include comprehensive docstrings and examples

This decision significantly improves the reliability and maintainability of LLM response processing while providing better development experience through type safety and validation.
