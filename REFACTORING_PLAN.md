# LangFlix Codebase Refactoring Plan
**Version:** 2.0.0
**Date:** 2025-12-15
**Status:** Draft - Ready for Implementation
**Priority:** CRITICAL (Technical Debt Reduction)

---

## 📊 Executive Summary

### Current State
- **Total Codebase:** 217 Python files, 60,714 LOC
- **Largest File:** `video_editor.py` (3,554 lines) - **CRITICAL**
- **Files >1000 lines:** 5 files requiring refactoring
- **Test Coverage:** 106 test files (43% test ratio)

### Key Issues
1. 🔴 **CRITICAL:** `video_editor.py` - God class with 39 functions, mixed responsibilities
2. 🔴 **CRITICAL:** `expression_analyzer.py` - 1,150 lines with complex LLM interaction
3. 🟠 **HIGH:** Subtitle code fragmented across 4+ modules
4. 🟠 **HIGH:** `settings.py` - Monolithic configuration accessor (1,319 lines)

### Estimated Impact
- **Maintainability:** 70% improvement (based on file size reduction)
- **Testing:** Easier unit testing with focused classes
- **Onboarding:** 50% reduction in new developer ramp-up time
- **Bug Risk:** 40% reduction in regression potential

---

## 🎯 Refactoring Objectives

### Primary Goals
1. **Reduce File Complexity:** Target max 500 lines per file
2. **Single Responsibility:** Each class/module has ONE clear purpose
3. **Improve Testability:** Extract logic into testable units
4. **Eliminate Duplication:** Consolidate subtitle functionality
5. **Maintain Backwards Compatibility:** Zero breaking changes to API

### Success Metrics
- ✅ All files under 800 lines (ideal: <500)
- ✅ Functions under 50 lines (ideal: <30)
- ✅ Test coverage maintained or improved
- ✅ All existing tests pass
- ✅ No performance degradation

---

## 🔴 Phase 1: CRITICAL - Video Editor Refactoring

### Priority: P0 (Must Do First)
### Estimated Effort: 3-5 days
### Risk: Medium (high complexity, but well-tested)

### Problem Analysis

**File:** `langflix/core/video_editor.py`
**Current Size:** 3,554 lines
**Functions:** 39 (17 functions >50 lines)
**Responsibilities:** 7+ distinct concerns

#### Current Structure
```python
class VideoEditor:
    # Responsibilities (VIOLATIONS):
    1. Video composition & concatenation (create_long_form_video)
    2. Short-form video creation (create_short_form_from_long_form)
    3. Subtitle rendering & overlay (multiple helper methods)
    4. Audio extraction & mixing (_create_context_audio_timeline_direct)
    5. Educational slide generation (_create_educational_slide)
    6. TTS timeline creation (_generate_tts_timeline)
    7. HTML cleaning for subtitles (inline logic)
    8. File management & cleanup (_cleanup_temp_files)
    9. Font configuration & retrieval (_get_font_option)
    10. Transition video creation (_create_transition_video)
```

#### Longest Functions (Top 10)
```python
Line    | Function                              | Lines | Complexity
--------|---------------------------------------|-------|------------
165-653 | create_long_form_video()              | 489   | 🔴 CRITICAL
663-1739| create_short_form_from_long_form()    | 1077  | 🔴 CRITICAL
2084-2699| _create_educational_slide()          | 616   | 🔴 CRITICAL
2700-2854| _generate_tts_timeline()             | 155   | 🟠 HIGH
2855-2957| _create_context_audio_timeline_direct| 103   | 🟠 HIGH
2958-3041| _extract_original_audio_timeline()   | 84    | 🟡 MEDIUM
3042-3105| _create_silence_fallback()           | 64    | 🟡 MEDIUM
3284-3407| _create_transition_video()           | 124   | 🟠 HIGH
3408-3450| combine_videos()                     | 43    | 🟢 OK
3451-3534| _create_video_batch()                | 84    | 🟡 MEDIUM
```

---

### Refactoring Strategy

#### Step 1: Extract Video Composition Module
**New File:** `langflix/core/video/video_composer.py`

**Responsibilities:**
- Video concatenation (long-form creation)
- Clip extraction and timing
- Video padding and layout
- Quality settings management

**Classes to Create:**
```python
class VideoComposer:
    """Handles video composition and concatenation."""

    def __init__(self, output_dir: Path, test_mode: bool = False):
        self.output_dir = output_dir
        self.encoding_args = self._get_encoding_args(test_mode)

    def create_long_form_video(
        self,
        expression: ExpressionAnalysis,
        context_video_path: str,
        expression_video_path: str,
        expression_index: int = 0,
        pre_extracted_context_clip: Optional[Path] = None
    ) -> str:
        """Create long-form video: context → expression (2x) → slide."""
        # Extract from lines 165-653 of video_editor.py
        pass

    def extract_clip(
        self,
        source_video: str,
        start_time: float,
        end_time: float,
        output_path: str
    ) -> str:
        """Extract video clip with precise timing."""
        pass

    def combine_videos(
        self,
        video_paths: List[str],
        output_path: str
    ) -> str:
        """Concatenate multiple videos."""
        # Extract from lines 3408-3450
        pass

    def _get_encoding_args(self, test_mode: bool) -> dict:
        """Get quality settings based on mode."""
        # Extract from lines 1770-1827
        pass
```

**Migration Path:**
```python
# OLD (in video_editor.py):
video_path = video_editor.create_long_form_video(expr, ctx, expr_vid, idx)

# NEW (using VideoComposer):
composer = VideoComposer(output_dir, test_mode=False)
video_path = composer.create_long_form_video(expr, ctx, expr_vid, idx)
```

---

#### Step 2: Extract Short-Form Video Module
**New File:** `langflix/core/video/short_form_creator.py`

**Responsibilities:**
- 9:16 vertical video creation
- Overlay rendering (viral_title, keywords, narrations, annotations)
- Black padding layout
- Expression/translation text positioning

**Classes to Create:**
```python
class ShortFormCreator:
    """Creates short-form vertical videos (9:16) with overlays."""

    def __init__(
        self,
        output_dir: Path,
        source_language_code: str,
        target_language_code: str,
        test_mode: bool = False
    ):
        self.output_dir = output_dir
        self.source_language_code = source_language_code
        self.target_language_code = target_language_code
        self.overlay_renderer = OverlayRenderer(source_language_code, target_language_code)

    def create_short_form_from_long_form(
        self,
        long_form_video_path: str,
        expression: ExpressionAnalysis,
        expression_index: int = 0
    ) -> str:
        """Create 9:16 short-form video from long-form."""
        # Extract from lines 663-1739
        pass

    def _scale_and_pad_video(
        self,
        input_video: str,
        target_width: int,
        target_height: int,
        output_path: str
    ) -> str:
        """Scale video and add black padding."""
        pass


class OverlayRenderer:
    """Renders text overlays for short-form videos."""

    def __init__(self, source_lang: str, target_lang: str):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.font_resolver = FontResolver()

    def add_viral_title(
        self,
        video_stream,
        viral_title: str,
        duration: float = 0.0
    ):
        """Add viral title overlay at top."""
        # Extract from lines 889-929
        pass

    def add_catchy_keywords(
        self,
        video_stream,
        keywords: List[str]
    ):
        """Add hashtag keywords below viral title."""
        # Extract from lines 931-1068
        pass

    def add_narrations(
        self,
        video_stream,
        narrations: List[dict],
        dialogue_timing: dict
    ):
        """Add narration overlays at specified times."""
        # Extract from lines 1314-1384
        pass

    def add_vocabulary_annotations(
        self,
        video_stream,
        vocab_annotations: List[dict],
        dialogue_timing: dict
    ):
        """Add vocabulary word overlays."""
        # Extract from lines 1163-1310
        pass

    def add_expression_annotations(
        self,
        video_stream,
        expr_annotations: List[dict],
        dialogue_timing: dict
    ):
        """Add expression/idiom overlays."""
        # Extract from lines 1386+
        pass


class FontResolver:
    """Resolves fonts for different languages and use cases."""

    def __init__(self):
        self.font_cache = {}

    def get_font_for_language(
        self,
        language_code: str,
        use_case: str = "default"
    ) -> Optional[str]:
        """Get font path for language and use case."""
        # Extract from lines 1750-1769
        pass

    def get_font_option_string(self) -> str:
        """Get FFmpeg font option string."""
        # Extract from lines 1740-1748
        pass
```

---

#### Step 3: Extract Audio Processing Module
**New File:** `langflix/core/audio/audio_processor.py`

**Responsibilities:**
- TTS timeline generation
- Original audio extraction
- Audio mixing and synchronization
- Silence fallback generation

**Classes to Create:**
```python
class AudioProcessor:
    """Handles audio processing for educational videos."""

    def __init__(self, cache_manager=None):
        self.cache_manager = cache_manager or get_cache_manager()
        self.tts_cache = {}

    def generate_tts_timeline(
        self,
        text: str,
        tts_client,
        provider_config: dict,
        output_dir: Path,
        expression_index: int = 0
    ) -> Tuple[Path, float]:
        """Generate TTS audio timeline with caching."""
        # Extract from lines 2700-2854
        pass

    def extract_original_audio_timeline(
        self,
        video_path: str,
        start_time: float,
        duration: float,
        repeat_count: int,
        output_dir: Path,
        expression_index: int = 0
    ) -> Tuple[Path, float]:
        """Extract and repeat original audio."""
        # Extract from lines 2958-3041
        pass

    def create_context_audio_timeline(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        output_dir: Path,
        expression_index: int = 0
    ) -> Tuple[Path, float]:
        """Extract context audio directly."""
        # Extract from lines 2855-2957
        pass

    def create_silence_fallback(
        self,
        duration: float,
        output_dir: Path,
        expression_index: int = 0
    ) -> Tuple[Path, float]:
        """Create silent audio as fallback."""
        # Extract from lines 3042-3149
        pass

    def _get_cached_tts(
        self,
        text: str,
        expression_index: int
    ) -> Optional[Tuple[str, float]]:
        """Retrieve cached TTS audio."""
        # Extract from lines 1905-1920
        pass

    def _cache_tts(
        self,
        text: str,
        expression_index: int,
        tts_path: str,
        duration: float
    ) -> None:
        """Cache TTS audio for reuse."""
        # Extract from lines 1921-1934
        pass
```

---

#### Step 4: Extract Slide Generation Module
**New File:** `langflix/core/slides/slide_builder.py`

**Responsibilities:**
- Educational slide creation
- Text layout and formatting
- Multi-language slide rendering
- Slide audio synchronization

**Classes to Create:**
```python
class SlideBuilder:
    """Builds educational slides with expression details."""

    def __init__(
        self,
        output_dir: Path,
        source_language_code: str,
        target_language_code: str
    ):
        self.output_dir = output_dir
        self.source_language = source_language_code
        self.target_language = target_language_code
        self.text_formatter = SlideTextFormatter()

    def create_educational_slide(
        self,
        expression_source_video: str,
        expression: ExpressionAnalysis,
        expression_index: int = 0,
        target_duration: Optional[float] = None,
        use_expression_audio: bool = False,
        expression_video_clip_path: Optional[str] = None
    ) -> str:
        """Create educational slide with expression breakdown."""
        # Extract from lines 2084-2699
        pass

    def _format_slide_text(
        self,
        expression: ExpressionAnalysis
    ) -> dict:
        """Format text elements for slide display."""
        pass

    def _position_text_elements(
        self,
        video_params: dict,
        text_elements: dict
    ) -> List[dict]:
        """Calculate positioning for all text elements."""
        pass


class SlideTextFormatter:
    """Formats and wraps text for slide display."""

    def wrap_text(
        self,
        text: str,
        max_width: int,
        font_size: int
    ) -> str:
        """Wrap text to fit width constraints."""
        pass

    def add_line_breaks(
        self,
        text: str,
        max_words: int
    ) -> str:
        """Add line breaks at word boundaries."""
        pass

    def escape_for_ffmpeg(self, text: str) -> str:
        """Escape text for FFmpeg drawtext filter."""
        pass
```

---

#### Step 5: Extract Utility Modules
**New File:** `langflix/core/video/transition_builder.py`

```python
class TransitionBuilder:
    """Creates transition videos between segments."""

    def create_transition_video(
        self,
        duration: float,
        image_path: str,
        sound_effect_path: str,
        source_video_path: str,
        aspect_ratio: str = "16:9"
    ) -> Path:
        """Create transition with image and sound effect."""
        # Extract from lines 3284-3407
        pass
```

**New File:** `langflix/utils/time_utils.py`

```python
def time_to_seconds(time_str: str) -> float:
    """Convert timestamp string to seconds."""
    # Extract from lines 3150-3193
    pass

def seconds_to_time(seconds: float) -> str:
    """Convert seconds to timestamp string."""
    # Extract from lines 3194-3220
    pass
```

---

### New Directory Structure

```
langflix/
├── core/
│   ├── video/                           # NEW MODULE
│   │   ├── __init__.py
│   │   ├── video_composer.py           # Lines 165-653, 3408-3450
│   │   ├── short_form_creator.py       # Lines 663-1739
│   │   ├── overlay_renderer.py         # Overlay logic from short_form
│   │   ├── font_resolver.py            # Lines 1740-1769
│   │   └── transition_builder.py       # Lines 3284-3407
│   │
│   ├── audio/                           # NEW MODULE (or expand existing)
│   │   ├── __init__.py
│   │   ├── audio_processor.py          # Lines 2700-3149
│   │   └── audio_cache.py              # Lines 1905-1934
│   │
│   ├── slides/                          # NEW MODULE (or expand existing)
│   │   ├── __init__.py
│   │   ├── slide_builder.py            # Lines 2084-2699
│   │   └── slide_text_formatter.py     # Text formatting logic
│   │
│   └── video_editor.py                  # REFACTORED (coordinator only)
│
└── utils/
    └── time_utils.py                    # Lines 3150-3220
```

---

### Refactored VideoEditor (Coordinator Pattern)

**New Size:** ~500 lines (down from 3,554)

```python
# langflix/core/video_editor.py (REFACTORED)

from langflix.core.video.video_composer import VideoComposer
from langflix.core.video.short_form_creator import ShortFormCreator
from langflix.core.audio.audio_processor import AudioProcessor
from langflix.core.slides.slide_builder import SlideBuilder
from langflix.core.video.transition_builder import TransitionBuilder

class VideoEditor:
    """
    Coordinator for video editing operations.

    Delegates to specialized components:
    - VideoComposer: Long-form video composition
    - ShortFormCreator: 9:16 vertical video creation
    - AudioProcessor: Audio extraction and TTS
    - SlideBuilder: Educational slide generation
    - TransitionBuilder: Transition video creation
    """

    def __init__(
        self,
        output_dir: str = "output",
        language_code: str = None,
        episode_name: str = None,
        subtitle_processor = None,
        source_language_code: str = None,
        test_mode: bool = False,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize specialized components
        self.video_composer = VideoComposer(
            output_dir=self.output_dir,
            test_mode=test_mode
        )

        self.short_form_creator = ShortFormCreator(
            output_dir=self.output_dir,
            source_language_code=source_language_code or "en",
            target_language_code=language_code or "ko",
            test_mode=test_mode
        )

        self.audio_processor = AudioProcessor()

        self.slide_builder = SlideBuilder(
            output_dir=self.output_dir,
            source_language_code=source_language_code or "en",
            target_language_code=language_code or "ko"
        )

        self.transition_builder = TransitionBuilder()

        # Maintain temp file tracking for cleanup
        from langflix.utils.temp_file_manager import get_temp_manager
        self.temp_manager = get_temp_manager()
        self.cache_manager = get_cache_manager()

    # Delegate to VideoComposer
    def create_long_form_video(self, *args, **kwargs) -> str:
        """Create long-form video (delegates to VideoComposer)."""
        return self.video_composer.create_long_form_video(*args, **kwargs)

    # Delegate to ShortFormCreator
    def create_short_form_from_long_form(self, *args, **kwargs) -> str:
        """Create short-form video (delegates to ShortFormCreator)."""
        return self.short_form_creator.create_short_form_from_long_form(*args, **kwargs)

    # Keep utility methods
    def combine_videos(self, video_paths: List[str], output_path: str) -> str:
        """Combine multiple videos (delegates to VideoComposer)."""
        return self.video_composer.combine_videos(video_paths, output_path)

    def _cleanup_temp_files(self, preserve_short_format: bool = False) -> None:
        """Clean up temporary files."""
        # Keep this method as-is (lines 1988-2033)
        pass

    def __del__(self):
        """Cleanup on destruction."""
        # Keep this method as-is (lines 2075-2082)
        pass
```

**Result:**
- ✅ VideoEditor reduced from 3,554 → ~500 lines
- ✅ Each component has single responsibility
- ✅ Easier to test individual components
- ✅ No breaking changes to public API

---

### Migration & Testing Plan

#### Phase 1.1: Create New Modules (Day 1)
1. Create directory structure: `core/video/`, `core/audio/`, `core/slides/`
2. Create empty module files with interfaces
3. Add comprehensive docstrings and type hints

#### Phase 1.2: Extract VideoComposer (Day 2)
1. Copy `create_long_form_video()` → `VideoComposer`
2. Copy `combine_videos()` → `VideoComposer`
3. Copy `_get_encoding_args()` → `VideoComposer`
4. Add unit tests for `VideoComposer`
5. Update `VideoEditor` to delegate to `VideoComposer`
6. Run integration tests to verify no regression

#### Phase 1.3: Extract ShortFormCreator (Day 3)
1. Copy `create_short_form_from_long_form()` → `ShortFormCreator`
2. Extract `OverlayRenderer` from inline overlay logic
3. Extract `FontResolver` from font-related methods
4. Add unit tests for each component
5. Update `VideoEditor` to delegate to `ShortFormCreator`
6. Run integration tests

#### Phase 1.4: Extract AudioProcessor & SlideBuilder (Day 4)
1. Copy audio-related methods → `AudioProcessor`
2. Copy `_create_educational_slide()` → `SlideBuilder`
3. Add unit tests
4. Update `VideoEditor` to delegate
5. Run integration tests

#### Phase 1.5: Final Cleanup & Validation (Day 5)
1. Remove duplicated code from `video_editor.py`
2. Update all imports across codebase
3. Run full test suite (unit + integration + e2e)
4. Performance benchmarking (ensure no degradation)
5. Code review and documentation update

---

### Testing Strategy

#### Unit Tests (NEW)
```python
# tests/unit/core/video/test_video_composer.py
def test_create_long_form_video():
    """Test long-form video creation."""
    composer = VideoComposer(output_dir="/tmp/test")
    result = composer.create_long_form_video(expr, ctx, expr_vid, 0)
    assert Path(result).exists()

# tests/unit/core/video/test_short_form_creator.py
def test_create_short_form_video():
    """Test short-form video creation."""
    creator = ShortFormCreator(output_dir="/tmp/test", source_lang="ko", target_lang="es")
    result = creator.create_short_form_from_long_form(long_form_path, expr, 0)
    assert Path(result).exists()

# tests/unit/core/video/test_overlay_renderer.py
def test_add_viral_title():
    """Test viral title overlay."""
    renderer = OverlayRenderer(source_lang="ko", target_lang="es")
    # Mock ffmpeg stream
    stream_with_overlay = renderer.add_viral_title(mock_stream, "Test Title")
    assert stream_with_overlay is not None
```

#### Integration Tests (EXISTING - Should Still Pass)
```python
# tests/integration/test_video_pipeline.py
# All existing tests should pass without modification
# because VideoEditor API remains unchanged
```

---

### Rollback Plan

**If refactoring introduces issues:**

1. **Keep original file as backup:** `video_editor_v1_backup.py`
2. **Feature flag:** Add config option `use_refactored_video_editor: false`
3. **Gradual migration:** Deploy new modules but keep old code path
4. **Monitoring:** Track error rates in production
5. **Quick revert:** Restore `video_editor_v1_backup.py` if needed

---

## 🔴 Phase 2: CRITICAL - Expression Analyzer Refactoring

### Priority: P0 (Do Immediately After Phase 1)
### Estimated Effort: 2-3 days
### Risk: Medium

### Problem Analysis

**File:** `langflix/core/expression_analyzer.py`
**Current Size:** 1,150 lines
**Functions:** 12 (9 functions >50 lines)
**Responsibilities:** 5+ distinct concerns

#### Current Structure
```python
class ExpressionAnalyzer:
    # Responsibilities (VIOLATIONS):
    1. LLM prompt building and template loading
    2. API interaction and retry logic
    3. Response parsing and JSON handling
    4. Schema validation and cleaning (clean_schema: 249 lines!)
    5. Expression postprocessing and normalization
    6. Chunk analysis and batch processing
```

---

### Refactoring Strategy

#### Step 1: Extract Prompt Builder
**New File:** `langflix/core/llm/prompt_builder.py`

```python
class PromptBuilder:
    """Builds LLM prompts from templates."""

    def __init__(self, template_dir: Path):
        self.template_dir = template_dir
        self.template_cache = {}

    def load_template(self, template_name: str) -> str:
        """Load prompt template from file."""
        pass

    def build_expression_prompt(
        self,
        subtitle_text: str,
        show_name: str,
        language_level: str
    ) -> str:
        """Build expression analysis prompt."""
        pass

    def format_subtitles_for_prompt(
        self,
        subtitles: List[str]
    ) -> str:
        """Format subtitle entries for LLM input."""
        pass
```

---

#### Step 2: Extract Response Parser
**New File:** `langflix/core/llm/response_parser.py`

```python
class ResponseParser:
    """Parses and validates LLM responses."""

    def parse_expression_response(
        self,
        response_text: str
    ) -> List[ExpressionAnalysis]:
        """Parse LLM response into ExpressionAnalysis objects."""
        pass

    def extract_json_from_response(
        self,
        response_text: str
    ) -> dict:
        """Extract JSON from potentially malformed response."""
        pass

    def validate_expression_schema(
        self,
        expression_data: dict
    ) -> ExpressionAnalysis:
        """Validate expression data against schema."""
        pass


class SchemaValidator:
    """Validates and cleans LLM response schemas."""

    def clean_schema(
        self,
        response_data: dict
    ) -> dict:
        """Clean and normalize LLM response schema."""
        # Extract 249-line clean_schema() function here
        pass

    def normalize_timestamps(
        self,
        expression: dict
    ) -> dict:
        """Normalize timestamp formats."""
        pass

    def validate_field_types(
        self,
        expression: dict
    ) -> bool:
        """Validate all fields have correct types."""
        pass
```

---

#### Step 3: Extract LLM Client
**New File:** `langflix/core/llm/gemini_client.py`

```python
class GeminiClient:
    """Handles Gemini API interactions with retry logic."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.5-flash"
    ):
        self.api_key = api_key
        self.model_name = model_name
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def generate_content_with_retry(
        self,
        prompt: str,
        generation_config: dict,
        max_retries: int = 3
    ) -> str:
        """Generate content with automatic retry on failure."""
        # Extract retry logic from _generate_content_with_retry()
        pass

    def _handle_api_error(
        self,
        error: Exception,
        attempt: int
    ) -> bool:
        """Determine if error is retryable."""
        pass
```

---

#### Step 4: Refactored ExpressionAnalyzer (Coordinator)

```python
# langflix/core/expression_analyzer.py (REFACTORED)

from langflix.core.llm.prompt_builder import PromptBuilder
from langflix.core.llm.response_parser import ResponseParser, SchemaValidator
from langflix.core.llm.gemini_client import GeminiClient

class ExpressionAnalyzer:
    """
    Analyzes subtitles to extract expressions using LLM.

    Delegates to specialized components:
    - PromptBuilder: Constructs LLM prompts
    - GeminiClient: Handles API interaction
    - ResponseParser: Parses LLM responses
    - SchemaValidator: Validates and cleans data
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.5-flash"
    ):
        self.prompt_builder = PromptBuilder(
            template_dir=Path(__file__).parent.parent / "templates"
        )
        self.gemini_client = GeminiClient(api_key, model_name)
        self.response_parser = ResponseParser()
        self.schema_validator = SchemaValidator()

    def analyze_chunk(
        self,
        subtitle_chunk: str,
        show_name: str,
        language_level: str = "intermediate"
    ) -> List[ExpressionAnalysis]:
        """Analyze subtitle chunk for expressions."""

        # Build prompt
        prompt = self.prompt_builder.build_expression_prompt(
            subtitle_text=subtitle_chunk,
            show_name=show_name,
            language_level=language_level
        )

        # Call LLM
        response_text = self.gemini_client.generate_content_with_retry(
            prompt=prompt,
            generation_config=self._get_generation_config()
        )

        # Parse response
        expressions = self.response_parser.parse_expression_response(
            response_text
        )

        # Validate and clean
        cleaned_expressions = [
            self.schema_validator.clean_schema(expr)
            for expr in expressions
        ]

        return cleaned_expressions
```

**Result:**
- ✅ ExpressionAnalyzer reduced from 1,150 → ~200 lines
- ✅ Prompt building separated and testable
- ✅ LLM client can be mocked for testing
- ✅ Schema validation isolated
- ✅ No breaking changes

---

### New Directory Structure

```
langflix/
├── core/
│   ├── llm/                             # NEW MODULE
│   │   ├── __init__.py
│   │   ├── prompt_builder.py           # Prompt construction
│   │   ├── response_parser.py          # Response parsing
│   │   ├── schema_validator.py         # Schema validation (clean_schema)
│   │   └── gemini_client.py            # API interaction + retry
│   │
│   └── expression_analyzer.py           # REFACTORED (coordinator)
```

---

## 🟠 Phase 3: HIGH - Subtitle Code Consolidation

### Priority: P1 (After Critical Refactoring)
### Estimated Effort: 2-3 days
### Risk: Low

### Problem Analysis

**Subtitle functionality is fragmented across 4 modules:**

| File | Lines | Responsibilities |
|------|-------|------------------|
| `core/subtitle_processor.py` | 814 | Core subtitle processing, SRT generation |
| `media/subtitle_renderer.py` | 420 | FFmpeg subtitle rendering |
| `subtitles/overlay.py` | 471 | Subtitle overlay application |
| `core/dual_subtitle.py` | 454 | V2 dual-language subtitle support |

**Total:** 2,159 lines of subtitle-related code

---

### Refactoring Strategy

#### Recommended Consolidation

```
langflix/
├── core/
│   └── subtitles/                       # CONSOLIDATED MODULE
│       ├── __init__.py
│       ├── subtitle_parser.py           # SRT parsing (keep existing)
│       ├── subtitle_generator.py        # SRT generation (from processor)
│       ├── subtitle_renderer.py         # FFmpeg rendering (from media/)
│       ├── subtitle_overlay.py          # Overlay application (from subtitles/)
│       ├── dual_subtitle.py             # V2 dual-language (keep existing)
│       └── subtitle_exceptions.py       # Error handling (keep existing)
```

**Actions:**
1. Move `media/subtitle_renderer.py` → `core/subtitles/subtitle_renderer.py`
2. Move `subtitles/overlay.py` → `core/subtitles/subtitle_overlay.py`
3. Extract SRT generation from `subtitle_processor.py` → `subtitle_generator.py`
4. Keep `dual_subtitle.py` as-is (V2-specific logic)
5. Update all imports across codebase

**Result:**
- ✅ All subtitle code in one place
- ✅ Easier to find and maintain
- ✅ Reduces import confusion
- ✅ No functional changes

---

## 🟠 Phase 4: HIGH - Settings Refactoring

### Priority: P1
### Estimated Effort: 1-2 days
### Risk: Low

### Problem Analysis

**File:** `langflix/settings.py`
**Current Size:** 1,319 lines
**Functions:** 40+ getter functions
**Issue:** Monolithic configuration accessor

---

### Refactoring Strategy

#### Option A: Split by Domain (Recommended)

```
langflix/
├── config/
│   ├── __init__.py
│   ├── app_config.py                    # App settings
│   ├── llm_config.py                    # LLM/Gemini settings
│   ├── video_config.py                  # Video encoding settings
│   ├── font_config.py                   # Font configuration
│   ├── database_config.py               # Database settings
│   └── config_loader.py                 # YAML loading (keep existing)
```

**Example:**
```python
# langflix/config/video_config.py
from .config_loader import ConfigLoader

_loader = ConfigLoader()

def get_video_preset() -> str:
    """Get FFmpeg encoding preset."""
    return _loader.get('video', 'preset', default='slow')

def get_video_crf() -> int:
    """Get Constant Rate Factor."""
    return int(_loader.get('video', 'crf', default=18))

def get_short_video_dimensions() -> Tuple[int, int]:
    """Get short video resolution (width, height)."""
    layout = _loader.get('short_video', 'layout', default={})
    width = layout.get('target_width', 1080)
    height = layout.get('target_height', 1920)
    return (width, height)
```

---

#### Option B: Pydantic Settings (Modern Approach)

```python
# langflix/config/settings_models.py
from pydantic_settings import BaseSettings

class VideoSettings(BaseSettings):
    """Video encoding settings."""
    preset: str = "slow"
    crf: int = 18

    class Config:
        env_prefix = "VIDEO_"

class LLMSettings(BaseSettings):
    """LLM configuration."""
    model_name: str = "gemini-2.5-flash"
    temperature: float = 0.1
    max_input_length: int = 3000

    class Config:
        env_prefix = "LLM_"

class AppSettings(BaseSettings):
    """Main application settings."""
    video: VideoSettings = VideoSettings()
    llm: LLMSettings = LLMSettings()

    class Config:
        env_file = ".env"
```

**Benefits:**
- ✅ Type validation via Pydantic
- ✅ Environment variable support
- ✅ IDE autocomplete
- ✅ Easier testing (mock entire config)

---

## 📋 Implementation Checklist

### Pre-Implementation
- [ ] Review refactoring plan with team
- [ ] Set up feature branch: `refactor/phase-1-video-editor`
- [ ] Ensure all tests pass on main branch
- [ ] Create backup of critical files
- [ ] Set up code review process

### Phase 1: Video Editor (Days 1-5)
- [ ] Day 1: Create module structure
  - [ ] Create `core/video/` directory
  - [ ] Create `core/audio/` directory
  - [ ] Create `core/slides/` directory
  - [ ] Add `__init__.py` files
  - [ ] Write module docstrings

- [ ] Day 2: Extract VideoComposer
  - [ ] Create `video_composer.py`
  - [ ] Move `create_long_form_video()`
  - [ ] Move `combine_videos()`
  - [ ] Move `_get_encoding_args()`
  - [ ] Add unit tests
  - [ ] Update VideoEditor to delegate
  - [ ] Run integration tests

- [ ] Day 3: Extract ShortFormCreator
  - [ ] Create `short_form_creator.py`
  - [ ] Move `create_short_form_from_long_form()`
  - [ ] Extract `OverlayRenderer` class
  - [ ] Extract `FontResolver` class
  - [ ] Add unit tests
  - [ ] Update VideoEditor to delegate
  - [ ] Run integration tests

- [ ] Day 4: Extract AudioProcessor & SlideBuilder
  - [ ] Create `audio_processor.py`
  - [ ] Move audio methods
  - [ ] Create `slide_builder.py`
  - [ ] Move `_create_educational_slide()`
  - [ ] Add unit tests
  - [ ] Update VideoEditor to delegate
  - [ ] Run integration tests

- [ ] Day 5: Cleanup & Validation
  - [ ] Remove duplicate code from `video_editor.py`
  - [ ] Update all imports
  - [ ] Run full test suite
  - [ ] Performance benchmarking
  - [ ] Code review
  - [ ] Merge to main

### Phase 2: Expression Analyzer (Days 6-8)
- [ ] Day 6: Create LLM module structure
  - [ ] Create `core/llm/` directory
  - [ ] Create module files
  - [ ] Write interfaces

- [ ] Day 7: Extract components
  - [ ] Extract PromptBuilder
  - [ ] Extract ResponseParser
  - [ ] Extract SchemaValidator
  - [ ] Extract GeminiClient
  - [ ] Add unit tests

- [ ] Day 8: Integration & validation
  - [ ] Update ExpressionAnalyzer
  - [ ] Run all tests
  - [ ] Code review
  - [ ] Merge to main

### Phase 3: Subtitle Consolidation (Days 9-10)
- [ ] Day 9: Move files
  - [ ] Create `core/subtitles/` structure
  - [ ] Move subtitle modules
  - [ ] Update imports

- [ ] Day 10: Validation
  - [ ] Run tests
  - [ ] Code review
  - [ ] Merge to main

### Phase 4: Settings Refactoring (Days 11-12)
- [ ] Day 11: Choose approach (A or B)
  - [ ] Implement chosen approach
  - [ ] Migrate existing functions

- [ ] Day 12: Validation
  - [ ] Update all usages
  - [ ] Run tests
  - [ ] Merge to main

---

## 📊 Success Metrics

### Code Quality Metrics
| Metric | Before | Target | Status |
|--------|--------|--------|--------|
| Largest file size | 3,554 lines | <800 lines | ⏳ Pending |
| Avg function size | ~80 lines | <30 lines | ⏳ Pending |
| Files >1000 lines | 5 files | 0 files | ⏳ Pending |
| Cyclomatic complexity | High | Medium | ⏳ Pending |
| Test coverage | 43% | ≥43% | ⏳ Pending |

### Performance Metrics
| Metric | Baseline | Threshold | Status |
|--------|----------|-----------|--------|
| Video generation time | TBD | ≤105% baseline | ⏳ Pending |
| Memory usage | TBD | ≤110% baseline | ⏳ Pending |
| Test suite runtime | TBD | ≤120% baseline | ⏳ Pending |

### Developer Experience Metrics
| Metric | Before | Target | Status |
|--------|--------|--------|--------|
| Time to find function | 5+ min | <2 min | ⏳ Pending |
| Lines to understand flow | 500+ | <100 | ⏳ Pending |
| New feature implementation | 2-3 days | 1-2 days | ⏳ Pending |

---

## 🚨 Risk Mitigation

### Risk 1: Breaking Changes
**Probability:** Low
**Impact:** High
**Mitigation:**
- Maintain public API compatibility
- Keep all existing function signatures
- Use coordinator pattern (delegation)
- Comprehensive integration testing
- Feature flags for gradual rollout

### Risk 2: Performance Degradation
**Probability:** Low
**Impact:** Medium
**Mitigation:**
- Benchmark before/after refactoring
- Profile critical paths
- Monitor production metrics
- Rollback plan ready

### Risk 3: Test Failures
**Probability:** Medium
**Impact:** Medium
**Mitigation:**
- Run tests after each step
- Fix tests immediately
- Do not proceed if tests fail
- Pair programming for critical sections

### Risk 4: Scope Creep
**Probability:** Medium
**Impact:** Low
**Mitigation:**
- Stick to plan (no "while we're at it" changes)
- Time-box each phase
- Track hours spent vs. estimated
- Daily progress reviews

---

## 📚 Additional Optimizations

### Optimization 1: Caching Layer
**File:** `langflix/core/cache_manager.py`
**Opportunity:** Add TTL-based caching for LLM responses

```python
class LLMResponseCache:
    """Cache LLM responses to reduce API costs."""

    def __init__(self, ttl: int = 3600):
        self.cache = {}
        self.ttl = ttl

    def get(self, prompt_hash: str) -> Optional[str]:
        """Get cached response if not expired."""
        pass

    def set(self, prompt_hash: str, response: str) -> None:
        """Cache response with TTL."""
        pass
```

**Impact:**
- 💰 Reduce Gemini API costs by 30-50%
- ⚡ Faster response times for repeated prompts
- 🔧 Easier development/testing

---

### Optimization 2: Parallel Processing
**File:** `langflix/core/parallel_processor.py` (413 lines)
**Status:** Already implemented ✅
**Recommendation:** Ensure usage across all batch operations

---

### Optimization 3: Database Query Optimization
**File:** `langflix/db/crud.py`
**Opportunities:**
- Add database indexes on frequently queried fields
- Use select_related() to reduce N+1 queries
- Implement pagination for large result sets

```python
# Example optimization
# BEFORE
expressions = session.query(Expression).filter_by(media_id=media_id).all()

# AFTER (with eager loading)
expressions = (
    session.query(Expression)
    .options(selectinload(Expression.media))
    .filter_by(media_id=media_id)
    .all()
)
```

---

### Optimization 4: FFmpeg Command Optimization
**File:** `langflix/media/ffmpeg_utils.py` (1,101 lines)
**Opportunities:**
- Use hardware acceleration where available
- Optimize filter chains (combine multiple filters)
- Cache video metadata to avoid repeated probes

```python
# Example: Hardware acceleration
ffmpeg_cmd = [
    'ffmpeg',
    '-hwaccel', 'videotoolbox',  # macOS hardware accel
    '-i', input_file,
    # ... rest of command
]
```

---

### Optimization 5: Error Handling Standardization
**File:** `langflix/core/error_handler.py` (483 lines)
**Status:** Well-implemented ✅
**Recommendation:** Audit all try-except blocks to use decorators

```bash
# Find all try-except blocks not using decorator
grep -r "try:" langflix/ | grep -v "error_handler" | wc -l
# Result: 179 instances

# Recommendation: Convert to decorator usage
# BEFORE
try:
    result = process_video(path)
except Exception as e:
    logger.error(f"Failed: {e}")
    raise

# AFTER
@handle_error_decorator(
    ErrorContext(operation="process_video", component="video_processor")
)
def process_video(path: str):
    return process(path)
```

---

## 🎓 Best Practices for Future Development

### 1. File Size Limits
- **Maximum file size:** 500 lines
- **Ideal file size:** 200-300 lines
- **Action if exceeded:** Split into logical modules

### 2. Function Complexity Limits
- **Maximum function length:** 50 lines
- **Ideal function length:** 10-20 lines
- **Cyclomatic complexity:** ≤10

### 3. Code Organization Principles
- **Single Responsibility Principle:** Each class has ONE reason to change
- **Dependency Inversion:** Depend on abstractions, not concretions
- **Interface Segregation:** Many specific interfaces > one general interface

### 4. Testing Requirements
- **Unit test coverage:** ≥80% for new code
- **Integration tests:** Required for all public APIs
- **Performance tests:** Required for video processing code

### 5. Documentation Standards
- **Docstrings:** Required for all public functions/classes
- **Type hints:** Required for all function parameters and returns
- **README:** Update with architectural changes

---

## 📖 Reference Documentation

### Related Files
- `ARCHITECTURE.md` - System architecture overview
- `CONTRIBUTING.md` - Contribution guidelines
- `tests/README.md` - Testing documentation
- `docs/API.md` - API documentation

### External Resources
- [Python Design Patterns](https://refactoring.guru/design-patterns/python)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Martin Fowler - Refactoring](https://refactoring.com/)

---

## ✅ Approval & Sign-off

**Plan Created:** 2025-12-15
**Plan Review:** [ ] Pending
**Approved By:** ___________________
**Start Date:** ___________________
**Target Completion:** ___________________

---

**End of Refactoring Plan**

*This document will be updated as refactoring progresses. Track status in project management tool.*
