# LangFlix Pipeline Architecture

**Last Updated**: December 21, 2025

## Overview

LangFlix uses a contextual localization pipeline that creates context-aware multilingual educational content from video subtitles.

## Core Pipeline Workflow

```
1. Load Source Subtitle (single file - any language)
   ↓
2. Create Show Bible (Wikipedia-sourced context)
   ↓
3. Extract Expressions + Generate Chunk Summaries (Script Agent)
   ↓
4. Aggregate Summaries → Master Episode Summary (Aggregator)
   ↓
5. Context-Aware Translation (Translator Agent)
   ↓
6. Generate Educational Videos
```

## Key Components

### 1. Show Bible
- **Purpose**: Static context about show premise, characters, relationships
- **Source**: Wikipedia API
- **Caching**: Cached per show (reused across episodes)
- **Location**: `langflix/v3/artifacts/show_bibles/`

### 2. Script Agent
- **Purpose**: Extract educational expressions + Generate micro-summaries
- **Input**: Subtitle chunks + Show Bible
- **Output**:
  - Expressions (idioms, phrases, cultural references)
  - Chunk summaries with emotional context
- **Model**: `gemini-2.5-flash` (configurable)

### 3. Aggregator
- **Purpose**: Combine chunk summaries into cohesive episode narrative
- **Input**: List of chronological chunk summaries
- **Output**: Master Episode Summary (200-400 words)
- **Model**: `gemini-2.5-flash` (cheaper model)

### 4. Translator
- **Purpose**: Context-aware multilingual translation
- **Input**:
  - Expressions
  - Show Bible
  - Master Episode Summary
- **Output**: Localized translations respecting:
  - Character hierarchy (honorifics)
  - Emotional tone
  - Cultural context
- **Model**: `gemini-1.5-pro` (smart model)

## Configuration

Pipeline settings are in `langflix/config/default.yaml`:

```yaml
pipeline:
  show_bible:
    cache_dir: "langflix/v3/artifacts/show_bibles"
    use_wikipedia: true
    force_refresh: false

  master_summary:
    cache_dir: "langflix/v3/artifacts/summaries"

  aggregator:
    model_name: "gemini-2.5-flash"
    temperature: 0.3

  translator:
    model_name: "gemini-1.5-pro"
    temperature: 0.2
```

## Language Support

### Honorifics & Formality
- **Korean**: 반말 (informal) vs 존댓말 (formal)
- **Japanese**: 常体 (plain) vs 敬語 (keigo)
- **Spanish**: tú (informal) vs usted (formal)

The Translator uses Show Bible to determine character relationships and apply appropriate formality levels.

## Data Flow

### Input
- **Source Subtitle**: Single .srt file in any language
- **Show Name**: Required for Wikipedia lookup
- **Target Languages**: List of language codes (e.g., `['ko', 'ja', 'es']`)

### Output
- **Expressions**: List of educational content items with:
  - Original expression + dialogue
  - Context summary
  - Scene type
  - Similar expressions
  - Catchy keywords
  - **Translations**: For each target language:
    - Translated expression + dialogue
    - Translated keywords
    - Translation notes (honorifics applied)

## Cost Optimization

1. **Show Bible**: Generated once per show, cached forever
2. **Master Summary**: Generated once per episode, cached
3. **Aggregator**: Uses cheaper Flash model
4. **Translator**: Uses Pro model but only translates expressions (not full script)

## Directory Structure

```
langflix/
├── v3/
│   ├── agents/
│   │   ├── script_agent_v3.py      # Expression extraction + summarization
│   │   ├── aggregator.py            # Summary aggregation
│   │   └── translator.py            # Context-aware translation
│   ├── tools/
│   │   └── wikipedia_tool.py        # Wikipedia API wrapper
│   ├── prompts/
│   │   ├── script_agent_v3.txt      # Script agent prompt
│   │   ├── aggregator.txt           # Aggregator prompt
│   │   └── translator_v3.txt        # Translator prompt
│   ├── artifacts/
│   │   ├── show_bibles/             # Cached Show Bibles
│   │   └── summaries/               # Cached Master Summaries
│   ├── models.py                    # Data models
│   ├── pipeline.py                  # Pipeline orchestrator
│   └── bible_manager.py             # Show Bible cache manager
```

## Key Advantages

1. **Single Subtitle Requirement**: Only needs source language subtitle
2. **Context-Aware Translation**: Uses character relationships & emotional tone
3. **Cost Efficient**: Caching + cheaper models where appropriate
4. **Multilingual**: Single pipeline run produces all target languages
5. **Educational Focus**: Prioritizes learning expressions, not literal translation

## Example Usage

```python
from langflix.main import LangFlixPipeline

pipeline = LangFlixPipeline(
    subtitle_file="/path/to/english.srt",
    video_file="/path/to/video.mkv",
    source_language="English",
    target_languages=["ko", "ja", "es"],
    series_name="Suits",
    episode_name="S01E01"
)

results = pipeline.run(
    test_mode=False,
    language_level="intermediate",
    max_expressions=50
)
```

## Settings API

```python
from langflix import settings

# Pipeline configuration
settings.get_show_bible_cache_dir()
settings.get_use_wikipedia()
settings.get_aggregator_model()
settings.get_translator_model()
```

## Future Enhancements

- [ ] Multi-show Bible support (e.g., crossover episodes)
- [ ] User-provided Show Bible (override Wikipedia)
- [ ] Chunk-level translation caching
- [ ] Additional language-specific rules (German, French, etc.)
