# [TICKET-057] Multi-Language Video Generation Support

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [x] High (Performance issues, significant tech debt)
- [ ] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [ ] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [x] Code Duplication
- [x] Feature Enhancement

## Impact Assessment
**Business Impact:**
- Enables users to create videos in multiple languages simultaneously
- Significantly reduces processing time for multi-language content (reuse LLM analysis and video slices)
- Better user experience: one job creates videos for all target languages

**Technical Impact:**
- Major pipeline modification: `langflix/main.py::LangFlixPipeline`
- New translation service: `langflix/core/translator.py`
- Modifications to: `langflix/core/subtitle_processor.py`, `langflix/core/video_editor.py`, `langflix/services/output_manager.py`
- API updates: `langflix/api/routes/jobs.py`, `langflix/services/video_pipeline_service.py`
- Estimated files: 8-10 files modified, 2 new files

**Effort Estimate:**
- Large (> 3 days)

## Problem Description

### Current State
**Location:** `langflix/main.py`, `langflix/core/video_editor.py`, `langflix/core/subtitle_processor.py`

Currently, the system generates videos for a single target language:
- LLM analysis generates expressions with translations in one language (e.g., Korean)
- Video slices are extracted and subtitles applied for that language only
- To create videos in multiple languages, users must run the pipeline multiple times

**Why it's problematic:**
- Expensive operations (LLM analysis, video extraction) are repeated for each language
- Time-consuming: N languages = Nx processing time
- Inefficient use of resources

### Root Cause Analysis
- Pipeline is designed for single language processing
- No mechanism to reuse LLM analysis results across languages
- Video slices are extracted per language instead of once and reused
- Translation happens during LLM analysis, not as a separate step

### Evidence
- Current flow: Parse → Chunk → LLM Analysis (with translation) → Process → Create Videos
- LLM analysis includes translation in the prompt (`langflix/templates/expression_analysis_prompt*.txt`)
- Video extraction happens in `create_long_form_video()` for each expression
- No reuse mechanism for video slices or LLM results

## Proposed Solution

### Approach
1. **Separate LLM Analysis from Translation**
   - Run LLM analysis once (language-agnostic expression extraction)
   - Create translation service to translate text elements to multiple languages
   - Reuse `ExpressionAnalysis` objects (timings, context) across languages

2. **Reuse Video Slices**
   - Extract video slices once per expression
   - Store in temporary location
   - Apply different language subtitles to same slices

3. **Parallel Language Processing**
   - Process all target languages in parallel where possible
   - Generate subtitle files for each language
   - Create videos for each language using same slices

4. **Translation Quality**
   - Create context-aware translation prompt (의역, not 직역)
   - Include full dialogue context, scene context, catchy keywords
   - Natural translations that capture meaning and emotion

### Implementation Details

**New Translation Service** (`langflix/core/translator.py`):
```python
def translate_expression_to_languages(
    expression: ExpressionAnalysis, 
    target_languages: List[str]
) -> Dict[str, ExpressionAnalysis]:
    """
    Translate expression text elements to multiple languages.
    Reuses: expression, timings, scene_type, difficulty, category
    Translates: dialogues, translation, expression_translation, 
                expression_dialogue_translation, catchy_keywords, similar_expressions
    """
```

**Translation Prompt** (`langflix/templates/translation_prompt.txt`):
- Input: Full context (dialogues, expression, scene context, catchy keywords)
- Output: Natural translations (의역) for all target languages
- Emphasizes contextual understanding over literal translation

**Pipeline Modifications** (`langflix/main.py`):
- Add `target_languages: List[str]` parameter
- Modify `_analyze_expressions()`: Run once, store base results
- New method: `_translate_expressions_to_languages()`: Translate to all target languages
- Modify `_process_expressions()`: Extract slices once, generate subtitles for all languages
- Modify `_create_educational_videos()`: Create videos for each language using same slices

**Video Editor Modifications** (`langflix/core/video_editor.py`):
- Accept pre-extracted video slices
- Accept `language_code` parameter for subtitle selection
- Reuse same video slice, apply different language subtitles

**Output Structure** (`langflix/services/output_manager.py`):
- Create output structure for all target languages
- `output/Series/Episode/{lang}/expressions/`, `shorts/`, `long/` for each language

### Alternative Approaches Considered
- **Option 1**: Run full pipeline N times (current approach) - Rejected: Too slow, wasteful
- **Option 2**: Translate during LLM analysis - Rejected: Would require N LLM calls
- **Option 3**: Post-process translation only - Rejected: Doesn't reuse video slices
- **Selected**: Separate translation step with full reuse - Best balance of efficiency and quality

### Benefits
- **Performance**: ~1/N processing time for N languages (excluding translation time)
- **Cost**: 1x LLM analysis calls instead of Nx
- **Quality**: Context-aware translations (의역) with full scene context
- **Maintainability**: Clear separation of concerns (analysis vs translation)
- **Scalability**: Easy to add new languages without modifying core pipeline

### Risks & Considerations
- **Translation Quality**: Need to test with native speakers for each language
- **Video Slice Storage**: Temporary files need proper cleanup
- **Memory Usage**: Processing multiple languages may increase memory usage
- **Error Handling**: If one language fails, should continue with others
- **Backward Compatibility**: Default to single language to maintain existing behavior

## Testing Strategy
- Unit tests for translation service with multiple languages
- Integration tests: Verify video slices are reused (check file system)
- Integration tests: Verify translations are natural (의역) not literal
- End-to-end tests: Generate videos for 2-3 languages simultaneously
- Performance tests: Compare time for 3 languages vs 3 sequential runs
- Validation: Check all languages generate correct videos with proper subtitles

## Files Affected
- `langflix/core/translator.py` - **NEW**: Translation service
- `langflix/templates/translation_prompt.txt` - **NEW**: Translation prompt template
- `langflix/main.py` - Pipeline modifications for multi-language support
- `langflix/core/subtitle_processor.py` - Language-specific subtitle generation
- `langflix/core/video_editor.py` - Video slice reuse, language-specific processing
- `langflix/services/output_manager.py` - Multi-language output structure
- `langflix/services/video_pipeline_service.py` - API integration
- `langflix/api/routes/jobs.py` - API parameter updates
- `tests/integration/test_multi_language.py` - **NEW**: Integration tests
- `docs/core/multi_language_generation_eng.md` - **NEW**: Documentation
- `docs/core/multi_language_generation_kor.md` - **NEW**: Documentation

## Dependencies
- Depends on: None
- Blocks: None
- Related to: TICKET-038 (Structured video creation), TICKET-039 (Short-form video architecture)

## References
- Related documentation: `docs/core/structured_video_creation_eng.md`
- Translation prompt design: Based on user requirement for 의역 (contextual translation)
- Video slice reuse: Similar to current architecture where context clips are extracted once

## Architect Review Questions
**For the architect to consider:**
1. Should translation be synchronous or async? (Current plan: synchronous batch)
2. Should we cache translations to avoid re-translating same content?
3. Memory management: Process languages sequentially if memory constrained?
4. Should translation service support incremental translation (add languages later)?
5. API design: Accept language list or comma-separated string?

## Success Criteria
How do we know this is successfully implemented?
- [ ] Videos generated for all target languages in single pipeline run
- [ ] LLM analysis runs only once (verified in logs)
- [ ] Video slices are extracted once and reused (verified in file system)
- [ ] Translation quality is natural (의역) not literal (validated by native speakers)
- [ ] Processing time is significantly less than N sequential runs
- [ ] All existing single-language functionality continues to work
- [ ] API accepts `target_languages` parameter and processes correctly
- [ ] Output structure created correctly for all languages
- [ ] Comprehensive tests pass
- [ ] Documentation updated

