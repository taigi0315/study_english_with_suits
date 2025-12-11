# Gemini API Skills

> Patterns for working with Google Gemini API in LangFlix

---

## Configuration

### API Key Setup

```bash
# In .env file
GEMINI_API_KEY=your_api_key_here
```

### Access in Code

```python
from langflix import settings

api_key = settings.gemini_api_key
model = settings.llm.model  # e.g., "gemini-1.5-flash"
```

---

## Expression Analysis

### Location
`langflix/core/expression_analyzer.py`

### Basic Usage

```python
from langflix.core.expression_analyzer import ExpressionAnalyzer

analyzer = ExpressionAnalyzer()
expressions = analyzer.analyze_chunk(
    chunk_text="Your subtitle text here...",
    language_level="intermediate"
)
```

### Prompt Template

Located at: `langflix/templates/expression_analysis_prompt.txt`

Customize extraction by modifying this template.

---

## Text-to-Speech

### Location
`langflix/tts/gemini_tts.py`

### Basic Usage

```python
from langflix.tts import GeminiTTS

tts = GeminiTTS()
audio_path = tts.synthesize(
    text="Hello, how are you?",
    voice="en-US-Neural2-A",
    output_path=Path("output.mp3")
)
```

### Voice Selection by Language

```python
from langflix.core.language_config import LanguageConfig

config = LanguageConfig(language='ko')
voice = config.get_tts_voice()
```

---

## Error Handling

### Retry Logic

```python
import time
from google.api_core.exceptions import ResourceExhausted

max_retries = 3
for attempt in range(max_retries):
    try:
        result = call_gemini_api()
        break
    except ResourceExhausted:
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # Exponential backoff
        else:
            raise
```

### Rate Limiting

- Default delay between API calls: configurable
- Check `settings.llm.parallel_processing` for concurrent settings
- Free tier has lower limits than paid tier

---

## Common Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `429 Quota exceeded` | Rate limit hit | Add delays, check tier |
| `JSON parsing error` | Malformed LLM response | Check prompt, use `--save-llm-output` |
| `API key not found` | Missing environment variable | Check `.env` file |
| `Model not found` | Invalid model name | Use `gemini-1.5-flash` or `gemini-2.5-flash` |

---

## Structured Output

### Pydantic Validation

```python
from langflix.core.models import ExpressionAnalysis

# Response is validated against this model
class ExpressionAnalysis(BaseModel):
    expression: str
    context_start_time: str
    context_end_time: str
    expression_start_time: str
    expression_end_time: str
    translation: str
    definition: str
    usage_example: str
```

### JSON Repair

For malformed JSON responses:

```python
from json_repair import repair_json

fixed_json = repair_json(malformed_response)
```
