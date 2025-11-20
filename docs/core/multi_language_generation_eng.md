# Multi-Language Video Generation Architecture

**Last Updated:** 2025-01-30  
**Status:** ✅ Implemented

## Overview

This document describes the architecture and implementation plan for generating videos in multiple languages simultaneously. The key innovation is reusing expensive operations (LLM analysis, video slicing) across all target languages, translating only text elements.

## Problem Statement

Currently, to create videos in multiple languages (e.g., Korean, Japanese, Chinese), users must run the pipeline multiple times:
- Each run performs expensive LLM analysis
- Each run extracts video slices
- Total time = N × single language time

**Goal**: Generate videos for N languages in approximately the same time as a single language (excluding translation time).

## Architecture Principles

### 1. Reuse Language-Agnostic Operations

**What to Reuse:**
- **LLM Expression Analysis**: Expression extraction, timings, context boundaries, scene analysis
- **Video Slices**: Context clips, expression clips (same time slices from source video)
- **Pipeline Structure**: Expression processing logic, video assembly logic

**What to Translate:**
- Dialogue translations (`ExpressionAnalysis.translation[]`)
- Expression translations (`expression_translation`, `expression_dialogue_translation`)
- Catchy keywords (`catchy_keywords[]`)
- Similar expressions (`similar_expressions[]`)
- Educational slide content (text overlays)
- Subtitle files (SRT files for video overlay)

### 2. Separation of Concerns

- **Analysis Phase**: Extract expressions (language-agnostic)
- **Translation Phase**: Translate text elements to target languages
- **Generation Phase**: Create videos for each language using translated content

## Implementation Architecture

### Phase 1: Translation Service

**New File**: `langflix/core/translator.py`

**Purpose**: Translate `ExpressionAnalysis` objects to multiple target languages while preserving language-agnostic data.

**Key Method**:
```python
def translate_expression_to_languages(
    expression: ExpressionAnalysis,
    target_languages: List[str]
) -> Dict[str, ExpressionAnalysis]:
    """
    Translate expression text elements to multiple languages.
    
    Reuses (copies from original):
    - expression (English text)
    - context_start_time, context_end_time
    - expression_start_time, expression_end_time
    - scene_type, difficulty, category
    - educational_value, usage_notes
    
    Translates (new values per language):
    - dialogues → translated dialogues
    - translation → translated dialogue translations
    - expression_translation → translated expression
    - expression_dialogue_translation → translated expression dialogue
    - catchy_keywords → translated keywords
    - similar_expressions → translated similar expressions
    """
```

**Translation Prompt Design** (`langflix/templates/translation_prompt.txt`):

The prompt emphasizes **contextual translation (의역)** over literal translation (직역):

```
Translate the following English learning content to {target_language}.
Provide natural, contextual translations (의역) that capture the meaning 
and emotion, not literal word-by-word translations (직역).

Context:
- Expression: {expression}
- Full Dialogue: {expression_dialogue}
- Scene Context: {dialogues}
- Scene Type: {scene_type}
- Catchy Keywords: {catchy_keywords}
- Similar Expressions: {similar_expressions}

Translate:
1. All dialogue lines (maintain same count, preserve timing)
2. Expression translation (natural, contextual)
3. Expression dialogue translation (natural, contextual)
4. Catchy keywords (3-6 words each, natural in target language)
5. Similar expressions (natural alternatives in target language)

Important:
- Maintain the emotional tone and context of the scene
- Use natural expressions that native speakers would use
- Preserve the educational value and memorability
```

### Phase 2: Pipeline Modifications

**File**: `langflix/main.py::LangFlixPipeline`

#### Changes to `__init__`:
```python
def __init__(
    self,
    subtitle_file: str,
    video_dir: str,
    output_dir: str = "output",
    language_code: str = "ko",
    target_languages: Optional[List[str]] = None,  # NEW
    ...
):
    self.language_code = language_code
    self.target_languages = target_languages or [language_code]  # Default: single language
```

#### Changes to `run()`:
```python
def run(
    self,
    max_expressions: int = None,
    target_languages: Optional[List[str]] = None,  # NEW
    ...
):
    # Override if provided
    if target_languages:
        self.target_languages = target_languages
```

#### Modified `_analyze_expressions()`:
- **Current**: Runs LLM analysis with translation in target language
- **New**: Run LLM analysis once (use first language for prompt, or English)
- Store base `ExpressionAnalysis` objects (with original language translations)
- **Reuse**: These objects for all target languages

#### New Method: `_translate_expressions_to_languages()`
```python
def _translate_expressions_to_languages(
    self,
    expressions: List[ExpressionAnalysis],
    target_languages: List[str]
) -> Dict[str, List[ExpressionAnalysis]]:
    """
    Translate expressions to all target languages.
    
    Returns:
        Dict mapping language_code to list of translated ExpressionAnalysis objects
    """
    from langflix.core.translator import translate_expression_to_languages
    
    translated_expressions = {}
    
    for lang in target_languages:
        if lang == self.language_code:
            # Use original (already translated during analysis)
            translated_expressions[lang] = expressions
        else:
            # Translate to target language
            lang_expressions = []
            for expr in expressions:
                translated = translate_expression_to_languages(expr, [lang])
                lang_expressions.append(translated[lang])
            translated_expressions[lang] = lang_expressions
    
    return translated_expressions
```

#### Modified `_process_expressions()`:
- **Current**: Creates subtitle files for single language
- **New**: 
  - Extract video slices once per expression (language-agnostic)
  - Store slices in temporary location
  - Generate subtitle files for each target language
  - **Reuse**: Same video slices, different subtitle files

#### Modified `_create_educational_videos()`:
- **Current**: Creates videos for single language
- **New**:
  - Iterate over target languages
  - For each language:
    - Use translated `ExpressionAnalysis` objects
    - Reuse pre-extracted video slices
    - Apply language-specific subtitle files
    - Create videos in language-specific output directory

### Phase 3: Subtitle Generation

**File**: `langflix/core/subtitle_processor.py`

**New Method**:
```python
def create_subtitle_file_for_language(
    self,
    expression: ExpressionAnalysis,
    language_code: str,
    output_path: Path
) -> Path:
    """
    Generate SRT file with translated dialogues for specific language.
    
    Reuses: Timing information from base expression
    Translates: Dialogue text and translations from ExpressionAnalysis
    """
```

**Current Location**: Subtitle file creation in `_process_expressions()` (line ~649-700)
- Extract this logic into `SubtitleProcessor` method
- Accept language-specific `ExpressionAnalysis` object

### Phase 4: Video Editor Modifications

**File**: `langflix/core/video_editor.py::create_long_form_video()`

#### Changes:
1. **Reuse Video Slices**:
   - Accept optional `pre_extracted_context_clip: Optional[Path]` parameter
   - If provided, reuse instead of extracting
   - If not provided, extract as before (backward compatible)

2. **Language-Specific Subtitles**:
   - Accept `language_code: str` parameter
   - Load appropriate subtitle file for language
   - Apply to same video slice

3. **Language-Specific Slide Content**:
   - Use translated `ExpressionAnalysis` for slide generation
   - Method: `_create_educational_slide()` already uses expression data

### Phase 5: Output Structure

**File**: `langflix/services/output_manager.py`

**Current Structure**: `output/Series/Episode/{language_code}/expressions/`, `shorts/`, `long/`

**Multi-Language Structure**: Create directories for each target language
```
output/
└── Series/
    └── Episode/
        ├── ko/
        │   ├── expressions/
        │   ├── shorts/
        │   └── long/
        ├── ja/
        │   ├── expressions/
        │   ├── shorts/
        │   └── long/
        └── zh/
            ├── expressions/
            ├── shorts/
            └── long/
```

**Modify**: `create_language_structure()` to handle multiple languages
- Call for each target language
- Create structure for all languages before processing

### Phase 6: API Integration

**Files**: `langflix/api/routes/jobs.py`, `langflix/services/video_pipeline_service.py`

#### Changes:
1. **Add `target_languages` parameter** to API endpoints
   - Default: `[language_code]` for backward compatibility
   - Accept: List of language codes `['ko', 'ja', 'zh']` or comma-separated string

2. **Modify**: `VideoPipelineService.process_video()`
   - Accept `target_languages: List[str]` parameter
   - Pass to `LangFlixPipeline`

3. **Progress Updates**:
   - Update progress for each language being processed
   - Example: "Creating videos for ko (1/3)", "Creating videos for ja (2/3)"

## Data Flow

### Current Flow (Single Language):
```
Parse Subtitles → Chunk → LLM Analysis (with translation) → 
Process Expressions → Create Videos
```

### New Flow (Multi-Language):
```
Parse Subtitles → Chunk → LLM Analysis (once, language-agnostic) →
Translate to Languages → Extract Video Slices (once) →
For each language:
  - Generate Subtitle Files
  - Create Videos (reuse slices, apply language subtitles)
```

## Performance Benefits

### Time Savings:
- **LLM Analysis**: 1x instead of Nx (N = number of languages)
- **Video Extraction**: 1x instead of Nx per expression
- **Total Time**: ~1/N for N languages (excluding translation time)

### Cost Savings:
- **LLM API Calls**: 1x instead of Nx
- **Processing Resources**: Shared across languages

### Example:
- **Before**: 3 languages × 10 minutes = 30 minutes
- **After**: 1 analysis (10 min) + 3 translations (2 min) + 3 video generations (6 min) = ~18 minutes
- **Savings**: ~40% time reduction

## Implementation Steps

### Step 1: Create Translation Service ✅
- ✅ Create `langflix/core/translator.py`
- ✅ Create translation prompt template `langflix/templates/translation_prompt.txt`
- ✅ Implement `translate_expression_to_languages()` method
- ✅ Test with single expression, multiple languages

### Step 2: Modify Pipeline for Multi-Language ✅
- ✅ Add `target_languages` parameter to `LangFlixPipeline`
- ✅ Modify `_analyze_expressions()` to run once
- ✅ Implement `_translate_expressions_to_languages()`
- ✅ Test translation with existing expressions

### Step 3: Reuse Video Slices ✅
- ✅ Modify `_process_expressions()` to extract slices once
- ✅ Store slices in temporary location
- ✅ Modify `create_long_form_video()` to accept pre-extracted slices
- ✅ Test video slice reuse

### Step 4: Language-Specific Subtitle Generation ✅
- ✅ Extract subtitle generation logic to `SubtitleProcessor`
- ✅ Implement `create_subtitle_file_for_language()`
- ✅ Test subtitle generation for multiple languages

### Step 5: Language-Specific Video Generation ✅
- ✅ Modify `_create_educational_videos()` to iterate over languages
- ✅ Reuse video slices, apply language-specific subtitles
- ✅ Test video generation for multiple languages

### Step 6: Output Structure Updates ✅
- ✅ Modify `OutputManager` to create structure for all languages
- ✅ Update path management for multi-language output
- ✅ Test output structure creation

### Step 7: API Integration ✅
- ✅ Update API endpoints to accept `target_languages`
- ✅ Update `VideoPipelineService` to pass languages to pipeline
- ✅ Test API with multiple languages

### Step 8: Short Video Generation for All Languages ✅
- ✅ Modify `_create_short_videos()` to iterate over all target languages
- ✅ Use language-specific `VideoEditor` instances with correct paths
- ✅ Use translated expressions for text rendering (catchy keywords, expression text)
- ✅ Ensure language-specific fonts are used for each language
- ✅ Clean up intermediate files for all languages

### Step 8: Testing & Validation
- ✅ Test with 2-3 languages simultaneously
- ✅ Verify video slices are reused (check file system)
- ✅ Verify translations are natural (의역)
- ✅ Verify all languages generate correct videos
- ✅ Performance testing (should be faster than sequential)
- ✅ Short video generation for all target languages
- ✅ Language-specific font rendering in short videos
- ✅ Cleanup of intermediate files for all languages

## Key Design Decisions

### 1. Translation Timing
**Decision**: After LLM analysis, before video processing
- **Rationale**: Allows parallel video generation for all languages
- **Benefit**: Reuses expensive LLM calls

### 2. Video Slice Reuse
**Decision**: Extract once, apply subtitles multiple times
- **Rationale**: Saves significant processing time
- **Benefit**: Same video quality for all languages

### 3. Backward Compatibility
**Decision**: Default to single language (`[language_code]`)
- **Rationale**: Existing code continues to work
- **Benefit**: Gradual migration path

### 4. Translation Quality
**Decision**: Use context-aware translation (의역)
- **Rationale**: Better learning experience than literal translation
- **Benefit**: Natural, memorable translations

## Risk Mitigation

1. **Translation Quality**
   - Test with native speakers for each language
   - Provide fallback to literal translation if needed
   - Allow manual translation review/editing

2. **Video Slice Storage**
   - Use temporary directory with proper cleanup
   - Monitor disk space usage
   - Clean up slices after all languages processed

3. **Memory Usage**
   - Process languages sequentially if memory constrained
   - Option to process languages in batches

4. **Error Handling**
   - If one language fails, continue with others
   - Log errors per language
   - Return partial results if some languages succeed

5. **Performance**
   - Monitor translation API rate limits
   - Cache translations if same content requested
   - Optimize batch translation calls

## Testing Strategy

### Unit Tests
- Translation service with multiple languages
- Subtitle generation for different languages
- Video slice reuse logic

### Integration Tests
- Verify video slices are reused (check file system)
- Verify translations are natural (의역) not literal
- Verify all languages generate correct videos

### End-to-End Tests
- Generate videos for 2-3 languages simultaneously
- Compare output quality across languages
- Verify output structure is correct

### Performance Tests
- Compare time for 3 languages vs 3 sequential runs
- Measure LLM call count (should be 1x)
- Measure video extraction count (should be 1x per expression)

## Future Enhancements

1. **Translation Caching**: Cache translations to avoid re-translating same content
2. **Incremental Translation**: Add languages to existing videos without re-processing
3. **Translation Quality Metrics**: Automatic quality scoring
4. **Parallel Translation**: Translate multiple languages in parallel
5. **Custom Translation Models**: Support different translation models per language

## References

- Related Documentation:
  - `docs/core/structured_video_creation_eng.md` - Current video creation architecture
  - `docs/core/subtitle_sync_guide_eng.md` - Subtitle processing details
  - `langflix/templates/expression_analysis_prompt*.txt` - Current LLM prompts

- Code References:
  - `langflix/main.py::LangFlixPipeline` - Main pipeline class
  - `langflix/core/expression_analyzer.py` - LLM analysis
  - `langflix/core/video_editor.py` - Video creation
  - `langflix/core/subtitle_processor.py` - Subtitle processing

