# [TICKET-059] Populate expression & translation metadata when generating YouTube shorts descriptions

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [ ] High (Performance issues, significant tech debt)
- [x] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [x] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [x] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [ ] Code Duplication

## Impact Assessment
**Business Impact:**
- Automatically generated YouTube shorts metadata shows blank expressions and the hardcoded text `Learn the meaning and usage in the video`, which looks unprofessional and misleads viewers about the actual teaching point.
- Metadata quality directly affects click-through and watch-through rates for Shorts, so improving it protects viewers’ trust and discovery signals.
- Medium effort, no runtime risk beyond metadata generation.

**Technical Impact:**
- Touches `langflix/youtube/video_manager.py` and `langflix/youtube/metadata_generator.py`, and likely the parts of the pipeline that emit short-form videos (pipeline output metadata needs to be persisted).
- May also require new fixtures/tests under `tests/youtube/test_metadata_generator.py` and updates to `VideoMetadata` dataclass so _generate_description can read real translations.
- Estimated files impacted: 2–4.

**Effort Estimate:** Medium (< 3 days)

## Problem Description

### Current State
**Location:** `langflix/youtube/metadata_generator.py:409-426`  

Shorts descriptions are built like this:

```python
description = f"""🎬 {quick_lesson}
📚 {expression_label}: {video_metadata.expression}
📖 {meaning_label}: {translation}
💡 {watch_and_learn}
#Shorts #EnglishLearning #Suits #EnglishExpressions #LearnEnglish"""
```

However:
1. `video_metadata.expression` is unset for the new `short-form_{episode}_{batch}.mkv` videos because `VideoFileManager._parse_video_path` deliberately sets `expression = ""` (lines 262-282).  
2. `_get_translation()` simply returns the placeholder `Learn the meaning and usage in the video` (lines 489-497) because there is no translation data in `VideoMetadata`.

Result: generated descriptions look like this (from user report):

```
🎬 Quick English lesson from Suits!

📚 Expression: 

📖 Meaning: Learn the meaning and usage in the video

💡 Watch and learn from your favorite show!

#Shorts #EnglishLearning #Suits #EnglishExpressions #LearnEnglish
```

### Root Cause Analysis
- Short-form videos no longer carry expression metadata in their filenames, so `VideoMetadata.expression` is empty and the generator has nothing to show.  
- No expression translation data is persisted alongside the short-form file, so `_get_translation()` falls back to the hardcoded placeholder.  
- Metadata generator and video manager are never told which expressions each Short contains, so nothing upstream can populate the description fields.

### Evidence
- Screenshot/snippet from the user’s Shorts description above.
- `VideoFileManager._parse_video_path()` explicitly sets `expression = ""` for `short-form_*` filenames (lines 261-282).
- `_get_translation()` returns the literal string `Learn the meaning and usage in the video` (lines 489-497).

## Proposed Solution

### Approach
1. **Persist expression metadata for each short-form video.** When the short video batch is created (e.g., in `langflix/core/video_editor.py` / pipeline), also write a metadata file (`short-form_{episode}_{batch}_meta.json` or similar) that records:
   - expressions included (e.g., list of expression text and translations),
   - the primary expression (if any) that should appear in the title/description,
   - target language code.
   This metadata follows the same data as saved to `Expression` (expression text + `expression_translation`) via the pipeline.
2. **Extend `VideoMetadata`.** Add fields such as `expression_translation` and/or `included_expressions`. Update `VideoFileManager._extract_video_metadata()` to look for the metadata JSON next to each short-form file and populate those fields when present (fall back to existing behavior only if metadata is missing).
3. **Consume the enriched metadata in the generator.** Update `_generate_description()` to:
   - Prefer `video_metadata.expression` and `video_metadata.expression_translation` from the persisted metadata,
   - Avoid calling `_get_translation()` unless no metadata exists,
   - Use the actual translation string instead of the hardcoded placeholder.
4. **Update tests and documentation.** Add unit tests that verify `_generate_description()` uses the real translation when `VideoMetadata.expression_translation` is set; update any docs describing YouTube metadata.

### Benefits
- Short descriptions will show the actual expression and its translation, matching the content the Short is teaching.  
- Eliminates the embarrassing placeholder text and blank expression field reported by users.  
- Provides a clear path for future metadata (e.g., listing multiple expressions per batch) because the metadata file can enumerate them.

## Risks & Considerations
- Need to ensure metadata file creation doesn’t slow down the pipeline; use lightweight JSON writes.  
- VideoFileManager will now depend on reading extra files, so handle missing metadata gracefully.  
- For legacy videos without metadata, continue to fall back to the existing title/description generation logic.

## Testing Strategy
- Unit tests covering `_generate_description()` when `VideoMetadata.expression_translation` is provided vs missing.  
- Integration test where `VideoFileManager` reads the new metadata JSON and passes it through to the generator.  
- Manual verification: generate a short via CLI/API, check the YouTube metadata preview on the dashboard to confirm expression & translation are rendered.

## Files Affected
- `langflix/youtube/video_manager.py` - extend `VideoMetadata`, read metadata JSON when scanning.  
- `langflix/youtube/metadata_generator.py` - stop relying on `_get_translation()` when real data exists; format description accordingly.  
- `langflix/core/video_editor.py` (or wherever short videos are written) - emit the metadata file with expression + translation info.  
- `tests/youtube/test_metadata_generator.py` - add coverage for the new behavior.  
- `tests/youtube/test_video_manager.py` (if needed) - mock metadata reading path.

## Dependencies
- Depends on having the pipeline expose the expression list/translation for each short-form video.  
- Related to previous metadata work (TICKET-056) and the short-form batching changes; coordinate with those teams if necessary.

## Reference
- Template excerpt: `langflix/youtube/metadata_generator.py:409-426`  
- Placeholder translation source: `_get_translation()` at `langflix/youtube/metadata_generator.py:489-497`  
- Video path parsing: `langflix/youtube/video_manager.py:261-282`.

## Architect Review Questions
1. Should we store metadata per batch (JSON next to the video) or embed everything in the database with a mapping from video_path -> expressions?
2. Do we need to support listing multiple expressions for a single short title/description, or can we continue highlighting just the first expression?
3. Is there existing metadata (e.g., saved in Redis during generation) we can reuse instead of writing new JSON files?

## Success Criteria
- [ ] Short-form YouTube descriptions show actual expression + translation text instead of blanks/placeholders.  
- [ ] VideoMetadata carries translation data when metadata exists.  
- [ ] Tests verify description generator behaviour and metadata reader.  
- [ ] Documentation updated to describe how metadata is emitted and consumed.

