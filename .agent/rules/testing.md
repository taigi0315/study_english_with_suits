# Testing Rules

> Standards for testing in LangFlix

---

## Test Organization

| Test Type | Location | Purpose |
|-----------|----------|---------|
| Unit | `tests/unit/` | Individual component tests |
| Integration | `tests/integration/` | Cross-module tests |
| API | `tests/api/` | REST endpoint tests |
| Step-by-step | `tests/step_by_step/` | Pipeline stage isolation |

---

## Running Tests

```bash
# All tests
make test

# With coverage
python run_tests.py all --coverage

# Specific suite
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/api/ -v

# Single file
pytest tests/unit/test_video_editor.py -v

# Step-by-step debugging
python tests/step_by_step/run_all_steps.py
```

---

## Test Requirements

### Must Have
- [ ] Unit tests for new functions/methods
- [ ] Integration tests for new workflows
- [ ] Update existing tests when modifying code
- [ ] Edge case coverage
- [ ] Error scenario tests

### Test Naming

```python
def test_<function_name>_<scenario>():
    """Test <function_name> when <scenario>."""
    pass

# Examples
def test_create_structured_video_with_valid_input():
def test_create_structured_video_with_missing_subtitle():
def test_expression_analyzer_handles_empty_chunk():
```

---

## Integration Testing

### Video Generation Test

```bash
# Quick test mode (2 expressions only)
python -m langflix.main \
  --subtitle "assets/media/test/test.srt" \
  --test-mode \
  --max-expressions 2
```

### Step-by-Step Pipeline Tests

```bash
# Isolate which stage fails
python tests/step_by_step/test_step1_load_and_analyze.py  # LLM
python tests/step_by_step/test_step2_slice_video.py       # Video extraction
python tests/step_by_step/test_step3_add_subtitles.py     # Subtitles
python tests/step_by_step/test_step4_generate_audio.py    # TTS
python tests/step_by_step/test_step5_create_slide.py      # Slides
python tests/step_by_step/test_step6_combine.py           # Combine
python tests/step_by_step/test_step7_final.py             # Final output
```

---

## Mocking Guidelines

- Mock external APIs (Gemini, YouTube) in unit tests
- Use `pytest-mock` or `unittest.mock`
- Don't mock internal modules in integration tests
