# Changelog

## Recent Updates

### Pipeline Architecture Simplification (December 2024)

**Unified Expression Analysis and Translation**
- Combined expression analysis and dialogue translation into single LLM call
- Removed separate Translator and Aggregator agents
- **Impact**: 66% reduction in LLM API calls (3 → 1 per chunk)

**Key Changes**:
- ScriptAgent now handles both analysis and translation
- Pipeline requires both source and target subtitle files
- Bilingual `dialogues` field in response schema
- See: [PIPELINE_UNIFIED_ARCHITECTURE.md](./PIPELINE_UNIFIED_ARCHITECTURE.md)

### Subtitle Processing Features

**Dual-Language Subtitle Support**
- Netflix-style subtitle folder structure
- Automatic subtitle file discovery
- Support for indexed subtitle files (e.g., `3_English.srt`, `6_Korean.srt`)

**Non-Split Processing Mode**
- Process entire subtitle files without chunking
- Leverages large context models (Gemini 1.5 Pro, 2.5 Flash)
- Set `max_input_length: 0` in configuration

### LLM Integration

**Gemini 1.5 Pro for Translation**
- Massive context window (2M tokens) for full episode awareness
- Better consistency in character names and recurring themes
- Single API call for entire subtitle file

**Configuration**:
```yaml
llm:
  translation:
    model_name: "gemini-1.5-pro"
    batch_size: -1  # Process all at once
  max_input_length: 0  # No chunking
```

## Migration Notes

### From Legacy Multi-Agent Pipeline

If upgrading from the older multi-agent architecture:

1. **Update pipeline calls**: Now requires `target_subtitle_chunks` parameter
   ```python
   pipeline.run(
       subtitle_chunks=source_chunks,
       target_subtitle_chunks=target_chunks  # NEW: Required
   )
   ```

2. **Remove configuration**: `translator_model` and `aggregator_model` no longer used

3. **Update data access**: `dialogues` field is now `Dict[str, List[Dict]]` instead of `List[str]`

4. **File requirements**: Both source and target subtitle files must be present

### Deprecated Components

The following components are no longer used and can be safely deleted:
- `langflix/pipeline/agents/translator.py`
- `langflix/pipeline/agents/aggregator.py`
- `langflix/pipeline/prompts/aggregator.txt`

## Documentation

- [PIPELINE_UNIFIED_ARCHITECTURE.md](./PIPELINE_UNIFIED_ARCHITECTURE.md) - Current architecture
- [PIPELINE_DATA_FLOW.md](./PIPELINE_DATA_FLOW.md) - Data flow diagrams
- [CONFIGURATION.md](./CONFIGURATION.md) - Configuration reference
- [archive/](./archive/) - Historical documentation
