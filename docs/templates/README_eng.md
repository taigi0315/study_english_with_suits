# Templates Module

## Overview

The `langflix/templates/` module contains prompt templates and HTML templates used throughout the LangFlix system. These templates provide structured instructions for LLM (Large Language Model) interactions and UI components.

**Purpose:**
- Provide prompt templates for expression analysis via Gemini API
- Store HTML templates for web UI components
- Version management for prompt templates
- Template variable substitution

**When to use:**
- When modifying LLM prompts for expression extraction
- When updating web UI templates
- When creating new prompt versions for testing

## File Inventory

### `expression_analysis_prompt.txt`
Current version of the expression analysis prompt template.

**Purpose:**
- Main prompt template for extracting English expressions from TV show dialogues
- Used by `langflix.core.expression_analyzer` module
- Contains instructions for LLM to identify valuable learning expressions

**Key Sections:**
- Mission statement: Find 1-3 expressions learners would be excited to learn
- Language level specification
- North Star Principle: Quality over quantity
- Expression quality criteria (common, reusable, engaging scene)
- Strict filters for what NOT to extract
- Context slicing guidelines
- Output format (JSON structure)

### `expression_analysis_prompt_v2.txt`, `v3.txt`, `v4.txt`, `v5.txt`
Version history of prompt templates.

**Purpose:**
- Maintain historical versions for comparison
- Allow rollback if new versions cause issues
- Track prompt evolution and improvements

### `video_dashboard.html`
HTML template for video dashboard UI.

**Purpose:**
- Web interface template for video management
- Used by API or web UI components
- Provides structure for displaying video processing status

### `__init__.py`
Package initialization file.

## Key Components

### Expression Analysis Prompt Structure

The main prompt template follows this structure:

```
1. Introduction
   - Dialogue segment from TV show
   - Mission statement

2. Language Level
   - Target proficiency level specification
   - Level-specific instructions

3. North Star Principle
   - Quality criteria for expression selection
   - What makes an expression worth extracting

4. Expression Quality Criteria
   - Common & Reusable (most important)
   - Engaging Scene requirements
   - Clearly Useful expressions

5. Strict Filters
   - What NOT to extract
   - Examples of expressions to skip

6. Context Slicing Guidelines
   - How to select context start/end times
   - Goal: 10-25 second clips
   - Completeness test

7. Process Steps
   - Step-by-step extraction process
   - Ranking criteria

8. Output Format
   - JSON structure specification
   - Required fields for each expression
```

### Template Variables

The prompt template uses placeholders that are replaced at runtime:

- `{dialogues}` - The dialogue segment to analyze
- `{level_description}` - Description of target language level
- Additional variables may be added for customization

### JSON Output Format

The prompt specifies a structured JSON output format:

```json
[
  {
    "dialogues": [...],
    "expression": "...",
    "expression_translation": "...",
    "context_start_time": "...",
    "context_end_time": "...",
    "expression_start_time": "...",
    "expression_end_time": "...",
    "similar_expressions": [...],
    "catchy_keywords": [...],
    "educational_value": "..."
  }
]
```

## Implementation Details

### Prompt Loading

Templates are loaded by the expression analyzer:

```python
from pathlib import Path
from langflix import settings

template_file = settings.get_template_file()  # Default: 'expression_analysis_prompt.txt'
template_path = Path('langflix/templates') / template_file

with open(template_path, 'r', encoding='utf-8') as f:
    template = f.read()
```

### Variable Substitution

Template variables are replaced before sending to LLM:

```python
prompt = template.format(
    dialogues=formatted_dialogues,
    level_description=level_description
)
```

### Version Management

Multiple prompt versions are maintained for:
- **A/B Testing**: Compare different prompt strategies
- **Rollback**: Revert to previous version if issues occur
- **Evolution Tracking**: Document prompt improvements

**Naming Convention:**
- `expression_analysis_prompt.txt` - Current production version
- `expression_analysis_prompt_v{N}.txt` - Historical versions

## Dependencies

**Internal Dependencies:**
- `langflix.core.expression_analyzer` - Uses prompt templates
- `langflix.settings` - Template file configuration
- `langflix.templates` - Template file location

**External Dependencies:**
- None (plain text files)

## Common Tasks

### Modifying the Expression Analysis Prompt

1. **Backup current version:**
   ```bash
   cp langflix/templates/expression_analysis_prompt.txt \
      langflix/templates/expression_analysis_prompt_v6.txt
   ```

2. **Edit the template:**
   ```bash
   vim langflix/templates/expression_analysis_prompt.txt
   ```

3. **Test changes:**
   ```bash
   python -m langflix.main --subtitle "test.srt" --test-mode --save-llm-output
   ```

4. **Review LLM outputs:**
   - Check `output/*/metadata/llm_outputs/` for responses
   - Verify JSON structure and expression quality

### Creating a New Prompt Version

1. **Copy current version:**
   ```bash
   cp langflix/templates/expression_analysis_prompt.txt \
      langflix/templates/expression_analysis_prompt_v7.txt
   ```

2. **Modify the new version:**
   - Make experimental changes
   - Test with `--save-llm-output` flag

3. **Compare results:**
   - Analyze expression quality
   - Check extraction rates
   - Evaluate JSON structure compliance

### Using a Specific Prompt Version

Modify `config.yaml`:

```yaml
app:
  template_file: expression_analysis_prompt_v5.txt
```

Or use environment variable:

```bash
export LANGFLIX_APP_TEMPLATE_FILE=expression_analysis_prompt_v5.txt
```

## Gotchas and Notes

### Important Considerations

1. **Template Encoding:**
   - Always use UTF-8 encoding
   - Handle special characters properly
   - Test with multilingual content

2. **Variable Substitution:**
   - Ensure all variables are provided
   - Use `.format()` safely (escape braces if needed)
   - Validate template after substitution

3. **JSON Output Format:**
   - Prompt must clearly specify JSON structure
   - Include examples in prompt
   - Validate output structure in code

4. **Prompt Length:**
   - Longer prompts may improve quality but increase cost
   - Balance detail with token usage
   - Test prompt effectiveness regularly

5. **Version Control:**
   - Keep version history for rollback capability
   - Document changes between versions
   - Test new versions before production use

### Best Practices

- **Clear Instructions**: Be explicit about what to extract
- **Examples**: Include good and bad examples in prompt
- **Structured Output**: Specify exact JSON format required
- **Error Prevention**: Include filters to prevent common mistakes
- **Testing**: Always test prompt changes with `--save-llm-output`

### Prompt Evolution

The prompt has evolved through multiple versions:

- **v1**: Initial prompt with basic extraction criteria
- **v2**: Added North Star Principle
- **v3**: Enhanced quality filters
- **v4**: Improved context slicing guidelines
- **v5**: Refined output format specification
- **Current**: Optimized for expression quality and JSON compliance

### Template Maintenance

- Review prompt effectiveness periodically
- Update based on LLM response analysis
- Document changes in version history
- Keep production template stable
- Use versioned templates for experiments

## Related Documentation

- [Core Module](../core/README_eng.md) - Expression analyzer that uses templates
- [Config Module](../config/README_eng.md) - Template file configuration
- [CLI Reference](../CLI_REFERENCE.md) - Command-line options for testing prompts

