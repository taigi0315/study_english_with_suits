# TICKET-V2-011: V2 Pipeline Integration

## Priority: 🔴 Critical
## Type: Feature

## Overview

Integrate V2 dual-language workflow into main pipeline (`langflix/main.py`).

Currently V2 components exist but are not connected to the main flow.

## Current State

V2 components implemented:
- [x] `path_utils.py` - Subtitle discovery
- [x] `dual_subtitle.py` - DualSubtitle model
- [x] `content_selection_models.py` - V2 models
- [x] `content_selection_analyzer.py` - V2 analyzer
- [x] `content_selection_prompt_v1.txt` - V2 prompt
- [x] `media.py` API routes - Language discovery

**NOT connected to main pipeline yet.**

## Required Integration Points

### 1. main.py: LangFlixPipeline.run()

```python
def run(self, ...):
    # V2: Check if dual-language mode enabled
    if settings.is_dual_language_enabled():
        return self._run_v2_pipeline(...)
    else:
        return self._run_v1_pipeline(...)
```

### 2. V2 Pipeline Steps

```python
def _run_v2_pipeline(self, media_path, source_lang, target_lang, ...):
    # 1. Load dual subtitles
    service = get_dual_subtitle_service()
    dual_sub = service.load_dual_subtitles(media_path, source_lang, target_lang)
    
    # 2. Analyze for content selection
    analyzer = V2ContentAnalyzer(show_name=self.show_name)
    selections = analyzer.analyze(dual_sub, language_level=level, ...)
    
    # 3. For each selection, slice media and generate video
    for selection in selections:
        # Get times from subtitle indices
        start_time = dual_sub.source_entries[selection.context_start_index].start_time
        end_time = dual_sub.source_entries[selection.context_end_index].end_time
        
        # Slice media
        clip_path = self.media_slicer.slice(media_path, start_time, end_time)
        
        # Generate video (existing pipeline)
        self.video_editor.create_short_form_video(clip_path, selection, ...)
```

### 3. VideoEditor Updates

Currently `VideoEditor` receives `expression` object with these fields:
- `expression`, `expression_translation`
- `dialogues`, `translation`
- `context_start_time`, `context_end_time`
- `vocabulary_annotations`, etc.

V2 provides compatible format via `convert_v2_to_v1_format()`.

### 4. Language Code Handling

VideoEditor needs BOTH language codes:
```python
class VideoEditor:
    def __init__(self, ..., source_language_code=None, target_language_code=None):
        self.source_language_code = source_language_code or "en"
        self.target_language_code = target_language_code or self.language_code
```

## API Integration

### New API Endpoints Needed

1. `POST /api/v2/jobs/analyze` - Accept media_path + source_lang + target_lang
2. `GET /api/v2/jobs/{id}/status` - Track V2 job progress

### Existing Endpoints to Update

- `GET /api/v1/files` - Show available languages per media file

## Testing Strategy

1. Unit tests for V2 pipeline steps
2. Integration test with real Netflix subtitles
3. End-to-end test: media → v2 analysis → video output

## Dependencies

- V2-007: Dual-font vocabulary (for proper rendering)
- V2-008: Token optimization (for efficient API calls)
- V2-009: Subtitle time lookup (for accurate slicing)
