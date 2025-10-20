# ADR-001: Externalize LLM Prompt Templates

**Date:** 2025-10-19  
**Status:** Accepted  
**Deciders:** Development Team  

## Context

The LangFlix application generates educational content by analyzing TV show subtitles using Large Language Models (LLMs). The core functionality relies heavily on well-crafted prompts that instruct the LLM to extract meaningful English expressions for language learning.

Originally, the prompt was hardcoded as a large f-string within the `langflix/prompts.py` file. This approach presented several challenges:

1. **Maintainability**: The prompt was embedded within Python code, making it difficult to read, edit, and version control changes independently
2. **Collaboration**: Non-developers (linguists, educators) found it challenging to contribute to prompt improvements
3. **Testing**: It was difficult to test different prompt variations without modifying source code
4. **Readability**: The large multi-line string cluttered the Python code and made the logic harder to follow

## Decision

We will externalize the LLM prompt template to a separate text file that can be loaded and formatted at runtime.

### Implementation

1. **Create prompt template directory**: `langflix/templates/`
2. **Extract prompt to external file**: `langflix/templates/expression_analysis_prompt.txt`
3. **Modify `prompts.py`**: Replace hardcoded f-string with template loading and formatting logic

```python
def _load_prompt_template() -> str:
    """Load the prompt template from file"""
    template_path = Path(__file__).parent / "templates" / "expression_analysis_prompt.txt"
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt template not found at {template_path}")
    except Exception as e:
        raise RuntimeError(f"Failed to load prompt template: {e}")

def get_prompt_for_chunk(subtitle_chunk: List[dict], language_level: str = None, language_code: str = "ko") -> str:
    # ... existing logic ...
    
    # Load prompt template from file
    template = _load_prompt_template()
    
    # Format the template with variables
    prompt = template.format(
        dialogues=dialogues,
        level_description=level_description,
        min_expressions=min_expressions,
        max_expressions=max_expressions,
        target_language=target_language
    )
    return prompt
```

### Template Format

The external template uses Python string formatting with named placeholders:

```
Here is a segment of dialogue from the TV show "Suits":

---
{dialogues}
---

**YOUR ROLE:**
You are an expert English language educator...

**LANGUAGE LEVEL TARGET:**
{level_description}

**YOUR TASK:**
Follow this two-step process to select the BEST expressions:

**STEP 1: FULL ANALYSIS**
First, go through the entire dialogue segment and identify ALL potentially valuable expressions...

**STEP 2: SELECT BEST ONES**
From all the valuable expressions you identified, select the TOP {min_expressions} to {max_expressions} BEST expressions...
```

## Consequences

### Positive

1. **Improved Maintainability**: Prompt changes can be made by editing a plain text file without touching Python code
2. **Better Collaboration**: Non-technical team members can easily contribute to prompt engineering
3. **Version Control**: Changes to prompts can be tracked independently and reviewed more easily
4. **Testing**: Different prompt variations can be tested by simply swapping template files
5. **Code Clarity**: The Python code is now focused on logic rather than content

### Negative

1. **Runtime Dependency**: The application now depends on external template files being present
2. **Error Handling**: Additional error handling needed for file I/O operations
3. **Performance**: Minimal overhead for file reading (happens once per chunk analysis)

### Risks

1. **File Missing**: If template file is missing, the application will fail at runtime
   - **Mitigation**: Proper error handling with clear error messages and fallback to hardcoded prompt if needed
2. **Template Corruption**: Malformed template could cause formatting errors
   - **Mitigation**: Template validation and clear error reporting

## Alternatives Considered

1. **Configuration-based prompts**: Store prompts in YAML configuration files
   - **Rejected**: YAML escaping and formatting would be more complex for multi-line prompts

2. **Multiple template files**: Support for different prompt variants
   - **Deferred**: Could be added later if needed, current single template approach is sufficient

3. **Template engine**: Use Jinja2 or similar templating engine
   - **Rejected**: Adds unnecessary complexity for simple string formatting needs

## Implementation Details

- Template file location: `langflix/templates/expression_analysis_prompt.txt`
- Template format: Python `.format()` with named placeholders
- Error handling: Comprehensive error handling with informative messages
- Backwards compatibility: No breaking changes to the public API

This decision aligns with the principle of separation of concerns and makes the codebase more maintainable and accessible to a broader range of contributors.
