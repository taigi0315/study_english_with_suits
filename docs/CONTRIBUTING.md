# Contributing to LangFlix

**Version:** 1.0  
**Last Updated:** October 19, 2025

Thank you for your interest in contributing to LangFlix! This guide will help you get started with the development process, coding standards, and contribution workflow.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Environment Setup](#development-environment-setup)
3. [Code Style and Standards](#code-style-and-standards)
4. [Testing Guidelines](#testing-guidelines)
5. [Pull Request Process](#pull-request-process)
6. [Issue Reporting](#issue-reporting)
7. [Architecture Overview](#architecture-overview)
8. [Common Development Tasks](#common-development-tasks)

---

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- Python 3.9+ installed
- Git installed
- Basic understanding of video processing concepts
- Familiarity with machine learning APIs (especially Google Gemini)

### Quick Start

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/study_english_with_suits.git
   cd study_english_with_suits
   ```

3. **Set up your development environment** (see [Development Environment Setup](#development-environment-setup))

4. **Create a new branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

---

## Development Environment Setup

### 1. Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

### 2. Install Dependencies

```bash
# Install project dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov flake8 black isort mypy
```

### 3. Environment Configuration

```bash
# Copy environment template
cp env.example .env

# Edit with your API keys and settings
nano .env
```

**Required environment variables for development:**
```env
GEMINI_API_KEY=your_gemini_api_key_here
LANGFLIX_LOG_LEVEL=DEBUG
```

### 4. Verify Setup

```bash
# Run basic tests
python -m pytest tests/unit/

# Check code style
flake8 langflix/

# Verify imports work
python -c "import langflix; print('Setup successful!')"
```

---

## Code Style and Standards

### Python Code Style

We follow **PEP 8** with some project-specific modifications:

#### Formatting
- **Line length**: 88 characters (Black standard)
- **Indentation**: 4 spaces (no tabs)
- **String quotes**: Double quotes for docstrings, single for code when possible

#### Naming Conventions
- **Classes**: `PascalCase` (e.g., `LangFlixPipeline`)
- **Functions/Variables**: `snake_case` (e.g., `process_episode`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`)
- **Private methods**: Leading underscore (e.g., `_process_chunk`)

### Code Organization

#### Module Structure
```python
"""
Module docstring describing the module's purpose.
"""

# Standard library imports
import os
from pathlib import Path
from typing import List, Optional

# Third-party imports
import ffmpeg
from pydantic import BaseModel

# Local imports
from . import settings
from .models import ExpressionAnalysis
```

#### Function Documentation
```python
def process_episode(file_path: str, options: Optional[Dict] = None) -> ProcessResult:
    """
    Process a single episode for expression extraction.
    
    Args:
        file_path: Path to the episode file (.srt)
        options: Optional processing configuration
        
    Returns:
        ProcessResult containing extracted expressions and metadata
        
    Raises:
        FileNotFoundError: If the episode file doesn't exist
        ValueError: If the file format is invalid
    """
    # Implementation here
    pass
```

### Automated Code Formatting

We use automated tools to ensure consistency:

```bash
# Format code with Black
black langflix/ tests/

# Sort imports with isort
isort langflix/ tests/

# Check for style issues
flake8 langflix/ tests/

# Type checking with mypy
mypy langflix/
```

**Pre-commit hook setup:**
```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install
```

**`.pre-commit-config.yaml`:**
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.9

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
```

---

## Testing Guidelines

### Test Structure

Tests are organized in the `tests/` directory:

```
tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests for multiple components
├── functional/     # End-to-end functional tests
└── step_by_step/   # Step-by-step pipeline tests
```

### Writing Tests

#### Unit Tests
Test individual functions and classes in isolation:

```python
# tests/unit/test_expression_analyzer.py
import pytest
from langflix.expression_analyzer import analyze_chunk
from langflix.models import ExpressionAnalysis

def test_analyze_chunk_returns_expressions():
    """Test that analyze_chunk returns expected structure."""
    chunk = [
        {"start_time": "00:01:25,657", "end_time": "00:01:28,200", "text": "Test dialogue"}
    ]
    
    result = analyze_chunk(chunk, language_code="ko")
    
    assert isinstance(result, list)
    assert all(isinstance(expr, ExpressionAnalysis) for expr in result)

def test_analyze_chunk_handles_empty_chunk():
    """Test behavior with empty input."""
    result = analyze_chunk([])
    assert result == []
```

#### Integration Tests
Test interaction between multiple components:

```python
# tests/integration/test_pipeline.py
import pytest
from langflix.main import LangFlixPipeline

def test_full_pipeline_execution():
    """Test complete pipeline with sample data."""
    pipeline = LangFlixPipeline(
        subtitle_file="tests/fixtures/sample.srt",
        video_dir="tests/fixtures/video",
        output_dir="tests/temp_output"
    )
    
    results = pipeline.run(max_expressions=2, dry_run=True)
    
    assert results["total_expressions"] > 0
    assert results["processed_expressions"] <= 2
```

#### Functional Tests
Test end-to-end functionality:

```python
# tests/functional/test_end_to_end.py
def test_complete_workflow_with_real_files():
    """Test complete workflow with real subtitle and video files."""
    # This test would use actual test media files
    pass
```

### Test Data

- Place test fixtures in `tests/fixtures/`
- Use small, representative sample files
- Never commit large media files - use test data generators

### Running Tests

```bash
# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/unit/
python -m pytest tests/integration/

# Run with coverage
python -m pytest --cov=langflix --cov-report=html

# Run in verbose mode
python -m pytest -v
```

### Test Requirements

- **Coverage**: Maintain at least 80% code coverage
- **Speed**: Unit tests should run quickly (< 1 second each)
- **Independence**: Tests should not depend on each other
- **Deterministic**: Tests should produce consistent results

---

## Pull Request Process

### Before Submitting

1. **Ensure tests pass**:
   ```bash
   python -m pytest
   ```

2. **Check code style**:
   ```bash
   black --check langflix/ tests/
   flake8 langflix/ tests/
   ```

3. **Update documentation** if your changes affect user-facing functionality

4. **Test your changes** with sample data

### Pull Request Template

When creating a PR, use this template:

```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated (if needed)
- [ ] Tests pass locally
```

### Review Process

1. **Automatic checks** must pass (CI/CD pipeline)
2. **Code review** by maintainers
3. **Testing** by maintainers (if needed)
4. **Approval** and merge

---

## Issue Reporting

### Bug Reports

When reporting bugs, include:

1. **Environment details**:
   ```markdown
   - OS: [e.g., Ubuntu 20.04, macOS 13.0]
   - Python version: [e.g., 3.9.7]
   - LangFlix version: [e.g., 1.0.0]
   ```

2. **Steps to reproduce**:
   ```markdown
   1. Run command: `python -m langflix.main --subtitle example.srt`
   2. See error: [error message]
   ```

3. **Expected vs actual behavior**

4. **Logs** (if available):
   ```bash
   # Include relevant log output
   tail -n 50 langflix.log
   ```

### Feature Requests

For feature requests, include:

1. **Use case description**
2. **Expected behavior**
3. **Possible implementation** (if you have ideas)

---

## Architecture Overview

### Core Components

```
langflix/
├── main.py              # Main pipeline orchestrator
├── models.py            # Pydantic data models
├── settings.py          # Configuration management
├── expression_analyzer.py # LLM interaction and analysis
├── video_processor.py   # Video file operations
├── video_editor.py      # Video editing and effects
├── subtitle_parser.py   # Subtitle file parsing
├── subtitle_processor.py # Subtitle processing utilities
├── prompts.py           # LLM prompt generation
├── output_manager.py    # Output directory management
└── templates/           # External prompt templates
```

### Data Flow

1. **Input**: SRT subtitle files and corresponding video files
2. **Parsing**: Subtitles are parsed and chunked
3. **Analysis**: LLM analyzes chunks for expressions
4. **Processing**: Video clips are extracted and processed
5. **Output**: Educational videos with subtitles and slides

### Key Design Patterns

- **Pipeline Pattern**: Main workflow follows a pipeline architecture
- **Strategy Pattern**: Different language levels use different analysis strategies
- **Factory Pattern**: Output managers create appropriate directory structures

---

## Common Development Tasks

### Adding a New Language

1. **Update language configuration**:
   ```python
   # langflix/language_config.py
   LANGUAGE_CONFIGS = {
       # ... existing languages
       "zh": {
           "name": "Chinese (Simplified)",
           "level_descriptions": {
               "beginner": "Beginner Chinese learning",
               # ...
           }
       }
   }
   ```

2. **Add CLI choice**:
   ```python
   # langflix/main.py
   parser.add_argument(
       "--language-code",
       choices=['ko', 'ja', 'zh', 'es', 'fr', 'zh'],  # Add new language
       default="ko"
   )
   ```

3. **Test with sample data**

### Adding New Video Codecs

1. **Update video processor**:
   ```python
   # langflix/video_processor.py
   class VideoProcessor:
       def __init__(self, media_dir: str = "assets/media"):
           self.supported_formats = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.webm'}  # Add new format
   ```

2. **Update FFmpeg operations** if needed

### Modifying LLM Prompts

1. **Update prompt template**:
   ```bash
   # Edit the template file
   nano langflix/templates/expression_analysis_prompt.txt
   ```

2. **Test prompt changes**:
   ```python
   # langflix/prompts.py
   def get_prompt_for_chunk(subtitle_chunk, ...):
       # Prompt formatting logic
       pass
   ```

### Adding New Output Formats

1. **Extend output manager**:
   ```python
   # langflix/output_manager.py
   def create_output_structure(subtitle_file, language_code, output_dir):
       # Add new directory or file structure
       pass
   ```

2. **Update video editor** if needed for new format support

---

## Performance Considerations

### Profiling

Use profiling tools to identify bottlenecks:

```python
import cProfile
import pstats

# Profile a function
profiler = cProfile.Profile()
profiler.enable()

# Run your code
your_function()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats()
```

### Memory Management

- Clean up large video objects promptly
- Use generators for large datasets
- Monitor memory usage during video processing

### API Optimization

- Implement proper retry logic
- Cache expensive operations when appropriate
- Batch operations where possible

---

## Contributing Checklist

Before submitting your contribution:

- [ ] Code follows style guidelines (`black`, `flake8`, `isort`)
- [ ] Tests are added or updated
- [ ] Tests pass locally (`pytest`)
- [ ] Documentation is updated if needed
- [ ] No large files are committed
- [ ] Environment variables are not committed
- [ ] Changes are focused and atomic
- [ ] Commit messages are clear and descriptive

---

## Getting Help

- **Documentation**: Check existing docs in `docs/` directory
- **Issues**: Search existing issues before creating new ones
- **Discussions**: Use GitHub Discussions for questions
- **Code review**: Ask for help in PR comments

---

**Thank you for contributing to LangFlix! Your efforts help make language learning more accessible and effective.**

**For Korean version of this contributing guide, see [CONTRIBUTING_KOR.md](CONTRIBUTING_KOR.md)**

**Related Documentation:**
- [API Reference](API_REFERENCE.md) - Understanding the codebase
- [Deployment Guide](DEPLOYMENT.md) - Setting up environments
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
