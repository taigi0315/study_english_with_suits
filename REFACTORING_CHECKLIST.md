# LangFlix Refactoring - Implementation Checklist

**Use this checklist to track progress during refactoring.**
**Mark items with [x] as you complete them.**

---

## ⚙️ Pre-Implementation Setup

### Environment Preparation
- [ ] Create backup branch: `git branch backup/pre-refactoring`
- [ ] Create feature branch: `git checkout -b refactor/phase-1-video-editor`
- [ ] Ensure all tests pass: `pytest tests/ -v`
- [ ] Record baseline metrics:
  - [ ] Test execution time: __________ seconds
  - [ ] Video generation time: __________ seconds
  - [ ] Memory usage: __________ MB
- [ ] Set up monitoring dashboard
- [ ] Notify team of refactoring start

### Documentation Review
- [ ] Read REFACTORING_PLAN.md completely
- [ ] Read REFACTORING_SUMMARY.md
- [ ] Understand rollback plan
- [ ] Review existing test coverage
- [ ] Identify critical integration tests

---

## 🔴 PHASE 1: Video Editor Refactoring (Days 1-5)

### Day 1: Module Structure Creation ✅ COMPLETED

#### Create Directories
- [x] Create `langflix/core/video/` directory
- [x] Create `langflix/core/video/__init__.py`
- [x] Create `langflix/core/audio/` directory
- [x] Create `langflix/core/audio/__init__.py`
- [x] Create `langflix/core/slides/` directory
- [x] Create `langflix/core/slides/__init__.py`

#### Create Empty Module Files
- [x] Create `langflix/core/video/video_composer.py`
- [x] Create `langflix/core/video/short_form_creator.py`
- [x] Create `langflix/core/video/overlay_renderer.py`
- [x] Create `langflix/core/video/font_resolver.py`
- [ ] Create `langflix/core/video/transition_builder.py` (defer to Day 5)
- [x] Create `langflix/core/audio/audio_processor.py`
- [ ] Create `langflix/core/audio/audio_cache.py` (defer to Day 4)
- [ ] Create `langflix/core/slides/slide_builder.py` (defer to Day 4)
- [ ] Create `langflix/core/slides/slide_text_formatter.py` (defer to Day 4)
- [ ] Create `langflix/utils/time_utils.py` (defer to Day 5)

#### Write Module Docstrings
- [x] Add docstrings to all new `__init__.py` files
- [x] Add class-level docstrings to all new modules
- [x] Document module responsibilities in comments
- [x] Add type hints to all function signatures

#### Commit
- [x] Git commit: "refactor: Create module structure for video_editor split"

**Status:** Day 1 completed successfully on 2025-12-15
**Next:** Day 2 - Extract VideoComposer

---

### Day 2: Extract VideoComposer

#### Copy Code from video_editor.py
- [ ] Copy `create_long_form_video()` (lines 165-653) → `VideoComposer.create_long_form_video()`
- [ ] Copy `combine_videos()` (lines 3408-3450) → `VideoComposer.combine_videos()`
- [ ] Copy `_get_video_output_args()` (lines 1770-1827) → `VideoComposer._get_encoding_args()`
- [ ] Copy helper functions for video composition
- [ ] Add `__init__()` method with proper initialization

#### Refactor Extracted Code
- [ ] Update function signatures to use `self`
- [ ] Replace `self.output_dir` references
- [ ] Update logger name to `VideoComposer`
- [ ] Extract hardcoded values to constants
- [ ] Add comprehensive docstrings
- [ ] Add type hints to all parameters

#### Create Unit Tests
- [ ] Create `tests/unit/core/video/test_video_composer.py`
- [ ] Write test for `create_long_form_video()`
- [ ] Write test for `combine_videos()`
- [ ] Write test for `_get_encoding_args()`
- [ ] Run tests: `pytest tests/unit/core/video/test_video_composer.py -v`

#### Update VideoEditor to Delegate
- [ ] Add `from langflix.core.video.video_composer import VideoComposer`
- [ ] Initialize `self.video_composer` in `__init__()`
- [ ] Replace `create_long_form_video()` with delegation:
  ```python
  def create_long_form_video(self, *args, **kwargs):
      return self.video_composer.create_long_form_video(*args, **kwargs)
  ```
- [ ] Replace `combine_videos()` with delegation

#### Run Integration Tests
- [ ] Run all video-related integration tests
- [ ] Check for any broken imports
- [ ] Verify no performance degradation
- [ ] Fix any failing tests

#### Commit
- [ ] Git commit: "refactor: Extract VideoComposer from VideoEditor"

---

### Day 3: Extract ShortFormCreator

#### Copy Code from video_editor.py
- [ ] Copy `create_short_form_from_long_form()` (lines 663-1739) → `ShortFormCreator`
- [ ] Extract overlay rendering logic → `OverlayRenderer` class
  - [ ] `add_viral_title()` (lines 889-929)
  - [ ] `add_catchy_keywords()` (lines 931-1068)
  - [ ] `add_narrations()` (lines 1314-1384)
  - [ ] `add_vocabulary_annotations()` (lines 1163-1310)
  - [ ] `add_expression_annotations()` (lines 1386+)
- [ ] Extract font logic → `FontResolver` class
  - [ ] `_get_font_option()` (lines 1740-1748)
  - [ ] `_get_font_path_for_use_case()` (lines 1750-1769)

#### Create OverlayRenderer Class
- [ ] Create `OverlayRenderer.__init__(source_lang, target_lang)`
- [ ] Move `escape_drawtext_string()` as static method
- [ ] Refactor overlay methods to use instance variables
- [ ] Add docstrings and type hints

#### Create FontResolver Class
- [ ] Create `FontResolver.__init__()`
- [ ] Implement font caching
- [ ] Add font discovery logic
- [ ] Add docstrings and type hints

#### Create Unit Tests
- [ ] Create `tests/unit/core/video/test_short_form_creator.py`
- [ ] Create `tests/unit/core/video/test_overlay_renderer.py`
- [ ] Create `tests/unit/core/video/test_font_resolver.py`
- [ ] Write tests for each overlay method
- [ ] Write tests for font resolution
- [ ] Run tests: `pytest tests/unit/core/video/ -v`

#### Update VideoEditor to Delegate
- [ ] Add imports for ShortFormCreator
- [ ] Initialize `self.short_form_creator` in `__init__()`
- [ ] Replace `create_short_form_from_long_form()` with delegation

#### Run Integration Tests
- [ ] Run short-form video integration tests
- [ ] Verify overlays render correctly
- [ ] Check font resolution
- [ ] Fix any failing tests

#### Commit
- [ ] Git commit: "refactor: Extract ShortFormCreator, OverlayRenderer, and FontResolver"

---

### Day 4: Extract AudioProcessor & SlideBuilder

#### Extract AudioProcessor
- [ ] Copy TTS methods to `AudioProcessor`:
  - [ ] `_generate_tts_timeline()` (lines 2700-2854)
  - [ ] `_get_cached_tts()` (lines 1905-1920)
  - [ ] `_cache_tts()` (lines 1921-1934)
  - [ ] `_create_timeline_from_tts()` (lines 1935-1987)
- [ ] Copy audio extraction methods:
  - [ ] `_create_context_audio_timeline_direct()` (lines 2855-2957)
  - [ ] `_extract_original_audio_timeline()` (lines 2958-3041)
  - [ ] `_create_silence_fallback()` (lines 3042-3105)
  - [ ] `_create_silence_fallback_single()` (lines 3106-3149)

#### Extract SlideBuilder
- [ ] Copy `_create_educational_slide()` (lines 2084-2699) → `SlideBuilder`
- [ ] Extract text formatting logic → `SlideTextFormatter`
- [ ] Create `_format_slide_text()` method
- [ ] Create `_position_text_elements()` method

#### Create Unit Tests
- [ ] Create `tests/unit/core/audio/test_audio_processor.py`
- [ ] Create `tests/unit/core/slides/test_slide_builder.py`
- [ ] Write tests for TTS methods
- [ ] Write tests for audio extraction
- [ ] Write tests for slide creation
- [ ] Run tests: `pytest tests/unit/core/ -v`

#### Update VideoEditor to Delegate
- [ ] Add imports for AudioProcessor and SlideBuilder
- [ ] Initialize components in `__init__()`
- [ ] Replace audio methods with delegation
- [ ] Replace slide methods with delegation

#### Run Integration Tests
- [ ] Run audio processing tests
- [ ] Run slide generation tests
- [ ] Verify end-to-end video creation still works
- [ ] Fix any failing tests

#### Commit
- [ ] Git commit: "refactor: Extract AudioProcessor and SlideBuilder"

---

### Day 5: Cleanup & Validation

#### Remove Duplicate Code
- [ ] Delete extracted functions from `video_editor.py`
- [ ] Keep only delegation methods
- [ ] Remove unused imports
- [ ] Remove commented-out code

#### Extract Utility Functions
- [ ] Move `_time_to_seconds()` → `langflix/utils/time_utils.py`
- [ ] Move `_seconds_to_time()` → `langflix/utils/time_utils.py`
- [ ] Create `TransitionBuilder` for transition videos
- [ ] Update all imports

#### Final VideoEditor Refactoring
- [ ] Verify VideoEditor is now ~500 lines
- [ ] Ensure all methods are delegation or coordination
- [ ] Add comprehensive class docstring
- [ ] Document coordinator pattern

#### Update All Imports Across Codebase
- [ ] Search for `from langflix.core.video_editor import` (uses)
- [ ] Update imports if internal functions were used
- [ ] Check `langflix/services/` for import usage
- [ ] Check `langflix/api/` for import usage
- [ ] Check test files for import usage

#### Run Full Test Suite
- [ ] Run unit tests: `pytest tests/unit/ -v`
- [ ] Run integration tests: `pytest tests/integration/ -v`
- [ ] Run functional tests: `pytest tests/functional/ -v`
- [ ] Run full suite: `pytest tests/ -v --cov=langflix`
- [ ] Verify coverage didn't drop

#### Performance Benchmarking
- [ ] Run video generation benchmark
- [ ] Compare with baseline (target: ≤105%)
- [ ] Run memory profiling
- [ ] Compare with baseline (target: ≤110%)
- [ ] Document results

#### Code Review
- [ ] Self-review all changes
- [ ] Run linter: `flake8 langflix/`
- [ ] Run type checker: `mypy langflix/`
- [ ] Fix any issues
- [ ] Request peer review

#### Documentation Update
- [ ] Update ARCHITECTURE.md
- [ ] Update README.md if needed
- [ ] Add migration notes
- [ ] Document new module structure

#### Commit & Merge
- [ ] Git commit: "refactor: Complete Phase 1 - VideoEditor refactoring"
- [ ] Push to remote
- [ ] Create pull request
- [ ] Get approvals
- [ ] Merge to main
- [ ] Tag release: `git tag refactor-phase1-complete`

---

## 🔴 PHASE 2: Expression Analyzer Refactoring (Days 6-8)

### Day 6: Create LLM Module Structure

#### Create Directories
- [ ] Create `langflix/core/llm/` directory
- [ ] Create `langflix/core/llm/__init__.py`

#### Create Module Files
- [ ] Create `langflix/core/llm/prompt_builder.py`
- [ ] Create `langflix/core/llm/response_parser.py`
- [ ] Create `langflix/core/llm/schema_validator.py`
- [ ] Create `langflix/core/llm/gemini_client.py`

#### Write Interfaces
- [ ] Add class skeletons with docstrings
- [ ] Define method signatures
- [ ] Add type hints
- [ ] Document responsibilities

#### Commit
- [ ] Git commit: "refactor: Create LLM module structure"

---

### Day 7: Extract LLM Components

#### Extract PromptBuilder
- [ ] Copy prompt loading logic
- [ ] Copy template formatting logic
- [ ] Implement `load_template()`
- [ ] Implement `build_expression_prompt()`
- [ ] Add unit tests
- [ ] Run tests

#### Extract ResponseParser
- [ ] Copy JSON parsing logic
- [ ] Copy response extraction logic
- [ ] Implement `parse_expression_response()`
- [ ] Implement `extract_json_from_response()`
- [ ] Add unit tests
- [ ] Run tests

#### Extract SchemaValidator
- [ ] Copy `clean_schema()` function (249 lines!)
- [ ] Refactor into smaller methods
- [ ] Implement `normalize_timestamps()`
- [ ] Implement `validate_field_types()`
- [ ] Add unit tests
- [ ] Run tests

#### Extract GeminiClient
- [ ] Copy API interaction logic
- [ ] Copy retry logic
- [ ] Implement `generate_content_with_retry()`
- [ ] Implement `_handle_api_error()`
- [ ] Add unit tests (with mocking)
- [ ] Run tests

#### Commit
- [ ] Git commit: "refactor: Extract LLM components"

---

### Day 8: Integration & Validation

#### Update ExpressionAnalyzer
- [ ] Add imports for new modules
- [ ] Initialize components in `__init__()`
- [ ] Replace methods with delegation
- [ ] Verify ~200 lines total

#### Run Tests
- [ ] Run unit tests: `pytest tests/unit/core/llm/ -v`
- [ ] Run expression analyzer tests
- [ ] Run integration tests
- [ ] Fix any failures

#### Performance Check
- [ ] Benchmark LLM response time
- [ ] Verify no regression
- [ ] Check memory usage

#### Code Review & Merge
- [ ] Self-review
- [ ] Request peer review
- [ ] Fix issues
- [ ] Git commit: "refactor: Complete Phase 2 - ExpressionAnalyzer refactoring"
- [ ] Merge to main

---

## 🟠 PHASE 3: Subtitle Consolidation (Days 9-10)

### Day 9: Move Files

#### Create Consolidated Structure
- [ ] Create `langflix/core/subtitles/` directory
- [ ] Create `langflix/core/subtitles/__init__.py`

#### Move Files
- [ ] Move `media/subtitle_renderer.py` → `core/subtitles/subtitle_renderer.py`
- [ ] Move `subtitles/overlay.py` → `core/subtitles/subtitle_overlay.py`
- [ ] Keep `subtitle_processor.py` in place (or move to subtitles/)
- [ ] Keep `dual_subtitle.py` in place (V2-specific)

#### Update Imports
- [ ] Find all `from langflix.media.subtitle_renderer`
- [ ] Update to `from langflix.core.subtitles.subtitle_renderer`
- [ ] Find all `from langflix.subtitles.overlay`
- [ ] Update to `from langflix.core.subtitles.subtitle_overlay`

#### Commit
- [ ] Git commit: "refactor: Consolidate subtitle modules"

---

### Day 10: Validation

#### Run Tests
- [ ] Run subtitle-related unit tests
- [ ] Run subtitle integration tests
- [ ] Fix any import errors
- [ ] Verify functionality unchanged

#### Documentation
- [ ] Update ARCHITECTURE.md
- [ ] Document new subtitle module structure
- [ ] Add migration notes

#### Code Review & Merge
- [ ] Self-review
- [ ] Request peer review
- [ ] Git commit: "refactor: Complete Phase 3 - Subtitle consolidation"
- [ ] Merge to main

---

## 🟠 PHASE 4: Settings Refactoring (Days 11-12)

### Day 11: Choose Approach & Implement

#### Decision Point
- [ ] Review Option A: Split by domain
- [ ] Review Option B: Pydantic Settings
- [ ] Make decision: Option _____ (A or B)
- [ ] Document choice rationale

#### Option A: Split by Domain
If chosen:
- [ ] Create `langflix/config/app_config.py`
- [ ] Create `langflix/config/llm_config.py`
- [ ] Create `langflix/config/video_config.py`
- [ ] Create `langflix/config/font_config.py`
- [ ] Create `langflix/config/database_config.py`
- [ ] Move functions from `settings.py` to respective files
- [ ] Update imports

#### Option B: Pydantic Settings
If chosen:
- [ ] Create `langflix/config/settings_models.py`
- [ ] Define `VideoSettings` class
- [ ] Define `LLMSettings` class
- [ ] Define `AppSettings` class
- [ ] Migrate existing functions
- [ ] Add validation rules

#### Commit
- [ ] Git commit: "refactor: Implement new settings structure"

---

### Day 12: Validation

#### Update All Settings Usage
- [ ] Search for `from langflix import settings` (uses)
- [ ] Update to new import structure
- [ ] Test each usage

#### Run Tests
- [ ] Run all tests: `pytest tests/ -v`
- [ ] Fix any configuration-related failures
- [ ] Verify environment overrides still work

#### Documentation
- [ ] Update configuration documentation
- [ ] Add migration guide
- [ ] Document new settings structure

#### Code Review & Merge
- [ ] Self-review
- [ ] Request peer review
- [ ] Git commit: "refactor: Complete Phase 4 - Settings refactoring"
- [ ] Merge to main
- [ ] Tag release: `git tag refactor-complete-v2.0`

---

## 📊 Post-Refactoring Validation

### Metrics Comparison
- [ ] Record final file sizes:
  - [ ] video_editor.py: ______ lines (target: <800)
  - [ ] expression_analyzer.py: ______ lines (target: <500)
  - [ ] settings.py: ______ lines (target: <500)
- [ ] Record test execution time: ______ seconds (target: ≤120% baseline)
- [ ] Record video generation time: ______ seconds (target: ≤105% baseline)
- [ ] Record memory usage: ______ MB (target: ≤110% baseline)

### Success Criteria Validation
- [ ] No files over 800 lines
- [ ] No functions over 50 lines
- [ ] All tests pass
- [ ] No performance degradation
- [ ] Test coverage maintained or improved

### Production Deployment
- [ ] Deploy to staging environment
- [ ] Run smoke tests
- [ ] Monitor error rates
- [ ] Monitor performance metrics
- [ ] Get approval for production deploy
- [ ] Deploy to production
- [ ] Monitor for 48 hours

---

## 📝 Final Documentation

### Update Documents
- [ ] Update ARCHITECTURE.md with new structure
- [ ] Update CONTRIBUTING.md with new conventions
- [ ] Update README.md if needed
- [ ] Create migration guide for developers
- [ ] Document lessons learned

### Celebrate!
- [ ] Share results with team
- [ ] Document metrics improvement
- [ ] Plan next iteration of improvements
- [ ] 🎉 Mark refactoring as COMPLETE

---

## 🚨 Emergency Rollback Procedure

**If critical issues arise:**

1. **Immediate Actions:**
   - [ ] Stop deployment
   - [ ] Assess severity
   - [ ] Notify team

2. **Rollback:**
   - [ ] `git checkout main`
   - [ ] `git revert <commit-hash>`
   - [ ] Deploy rollback
   - [ ] Verify system stable

3. **Post-Mortem:**
   - [ ] Document what went wrong
   - [ ] Identify root cause
   - [ ] Update rollback plan
   - [ ] Plan fix

---

**End of Checklist**

*Mark items as you complete them. Good luck with the refactoring!*
