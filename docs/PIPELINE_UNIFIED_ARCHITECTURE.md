# Pipeline Architecture: Unified Expression Analysis and Translation

## Overview
The pipeline uses a unified approach where the Expression Analysis agent (ScriptAgent) handles both expression analysis AND dialogue translations in a single LLM call, with no separate translation step needed.

## Implementation Details

### 1. Expression Analysis Prompt (`langflix/prompts/expression_analysis_prompt.yaml`)
- Added new `dialogues` field to output schema
- Format:
  ```json
  "dialogues": {
    "en": [
      {"index": 3, "timestamp": "00:00:49,460 --> 00:00:50,527", "text": "Gerald Tate's here."},
      {"index": 4, "timestamp": "00:00:50,595 --> 00:00:51,929", "text": "He wants to know..."}
    ],
    "ko": [
      {"index": 3, "timestamp": "00:00:49,460 --> 00:00:50,527", "text": "제럴드 테이트가 왔어요."},
      {"index": 4, "timestamp": "00:00:50,595 --> 00:00:51,929", "text": "자기 거래가..."}
    ]
  }
  ```
- Added language code placeholders: `{source_language_code}`, `{target_language_code}`

### 2. Pipeline Models (`langflix/pipeline/models.py`)
- Added `DialogueEntry` model for bilingual subtitle extraction
  ```python
  class DialogueEntry(BaseModel):
      index: int
      timestamp: str
      text: str
  ```
- Updated `TranslationResult.dialogues` field from `List[str]` to `Dict[str, List[Dict[str, Any]]]`
- Marked `LocalizationData` as DEPRECATED (translations now in dialogues field)
- Removed `translator_model` from `PipelineConfig` (deprecated)

### 3. ScriptAgent (`langflix/pipeline/agents/script_agent.py`)
- Added `target_script_chunk` parameter to `analyze_chunk()` and `analyze_chunks_batch()`
- Now accepts both source and target language subtitle chunks
- Updated prompt formatting to include both source and target dialogues
- Added language code retrieval from settings

### 4. Settings (`langflix/settings.py`)
- Added `get_source_language_code()` - returns ISO 639-1 code (e.g., 'en')
- Added `get_target_language_code()` - returns ISO 639-1 code (e.g., 'ko')
- Language mapping for: English, Korean, Japanese, Spanish, French, German, Chinese, Italian, Portuguese, Russian

### 5. Pipeline Orchestrator (`langflix/pipeline/orchestrator.py`)
- **Removed TranslatorAgent import and initialization**
- Updated `run()` to accept `target_subtitle_chunks` parameter
- Updated workflow documentation:
  - Phase 1: Extract expressions + Generate summaries + **Translate dialogues** (Script Agent)
  - Phase 2: Aggregate summaries (Aggregator)
  - Phase 3: Translator **DEPRECATED** (now handled in Phase 1)
- `translate_episode()` now just converts expressions to TranslationResult format
- Removed separate translation LLM calls

### 6. Main Pipeline (`langflix/main.py`)
- Now loads **BOTH** source and target subtitle files
- Creates both `chunks` and `target_chunks` with parallel structure
- Format: `[index] [timestamp --> timestamp] text`
- Includes `subtitles` field in chunks for timestamp lookup
- Passes both chunks to `pipeline.run()`
- Removed `translator_model` from `PipelineConfig` initialization

### 7. Translation Service (`langflix/services/translation_service.py`)
- Still used for translating to additional languages beyond the initial target
- Compatible with the unified dialogues structure

## Architecture

The pipeline uses a single-agent architecture for maximum efficiency:

```
Source Subtitle + Target Subtitle
    ↓
ScriptAgent (expression analysis + dialogue extraction for both languages)
    ↓
TranslationResult (with bilingual dialogues field)
```

This unified approach replaces the previous multi-agent pipeline which required separate expression analysis, aggregation, and translation steps.

## Benefits

1. **Massive LLM call reduction**: One LLM call per chunk instead of three (analysis + aggregation + translation)
2. **Better context**: LLM sees both languages simultaneously, ensuring better alignment
3. **Much simpler pipeline**: One agent instead of three
4. **Consistent timing**: Index and timestamp are identical across both languages
5. **More reliable**: Less chance of misalignment between analysis and translation steps
6. **Faster execution**: No aggregation step needed
7. **Lower cost**: 66% reduction in LLM API calls (3 → 1 per chunk)

## API

### Pipeline Execution

The pipeline requires both source and target subtitle chunks:

```python
pipeline.run(
    subtitle_chunks=source_chunks,
    target_subtitle_chunks=target_chunks,
    language_level="intermediate",
    max_expressions_per_chunk=3
)
```

### Key Changes from Legacy Architecture

1. **`pipeline.run()` signature**: Requires `target_subtitle_chunks` parameter
2. **`PipelineConfig`**: No `translator_model` or `aggregator_model` fields
3. **`TranslationResult.dialogues`**: Type is `Dict[str, List[Dict]]` with language codes as keys
4. **Input requirements**: Both source and target subtitle files must be present

## Testing Recommendations

1. Test with a single chunk to verify LLM response format
2. Verify `dialogues` field contains correct structure with both language codes
3. Confirm timestamps match between source and target dialogues
4. Test with multiple chunks to ensure proper batching
5. Verify video generation still works with new dialogues structure

## Key Files

- `langflix/prompts/expression_analysis_prompt.yaml` - LLM prompt template
- `langflix/pipeline/models.py` - Data models
- `langflix/pipeline/agents/script_agent.py` - Core agent implementation
- `langflix/pipeline/orchestrator.py` - Pipeline coordination
- `langflix/main.py` - Entry point
- `langflix/settings.py` - Configuration

## Unused Legacy Files

The following files are no longer part of the pipeline and can be safely deleted:
- `langflix/pipeline/agents/translator.py` - Separate translation agent (replaced by unified approach)
- `langflix/pipeline/agents/aggregator.py` - Summary aggregation agent (output was unused)

## Next Steps

1. Run end-to-end test with sample video
2. Verify LLM response includes complete dialogues field
3. Update any downstream code that accesses `TranslationResult.dialogues`
4. Consider removing `LocalizationData` model if not used elsewhere
5. Update API documentation if pipeline is exposed via API
