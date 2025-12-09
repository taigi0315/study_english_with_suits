# [TICKET-082] Deconstruct LangFlixPipeline God Class

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [x] High (Performance issues, significant tech debt)
- [ ] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [x] Refactoring
- [ ] Performance Optimization
- [x] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [x] Technical Debt
- [ ] Code Duplication

## Impact Assessment
**Business Impact:**
- **Feature Velocity**: Adding new steps (e.g., "Add Intro Video" or "Support French") is hard because 2000 lines of code rely on shared state in `self`.
- **Reliability**: Side effects in `self` variables make bugs hard to trace.

**Technical Impact:**
- **Module**: `langflix.main`
- **Files**: `langflix/main.py`
- **Effort**: Large (> 3 days)

## Problem Description

### Current State
**Location:** `langflix/main.py`

The `LangFlixPipeline` class (1800+ lines) violates the Single Responsibility Principle. It orchestrates *and implements* every step of the video creation process.

Current responsibilities:
1.  Subtitle parsing
2.  LLM interaction (analysis)
3.  Translation
4.  DB persistence
5.  Video cutting (ffmpeg)
6.  Audio mixing
7.  Profiling

It maintains massive state in `self` (`self.expressions`, `self.videos`, `self.paths`, etc.), making it impossible to reuse components in isolation (e.g., "Just cut this video").

### Root Cause Analysis
- **MVP Growth**: Started as a script, wrapped in a class, and features were appended as methods.

## Proposed Solution

### Approach
Adopt a **Pipeline Pattern** or **Service Orchestrator**. Use specialized, stateless services for each step. `LangFlixPipeline` should only *coordinate* these services.

### Implementation Details

**New Services:**
1.  `SubtitleService`: Parsing and validation.
2.  `ExpressionEngine`: LLM interaction (already exists partially in `core/expression_analyzer.py` but coupled).
3.  `TranslationService`: Handling multi-language translation.
4.  `VideoFactory`: FFmpeg operations (cutting, stitching).
5.  `PipelineOrchestrator`: The new thin "Main".

**Code Example (Orchestrator):**

```python
class PipelineOrchestrator:
    def __init__(self, subtitle_service: SubtitleService, video_factory: VideoFactory, ...):
        self.subtitle_service = subtitle_service
        self.video_factory = video_factory

    def run(self, input_video: Path, input_subtitle: Path, config: JobConfig):
        # Step 1: Parse
        subtitles = self.subtitle_service.parse(input_subtitle)
        
        # Step 2: Analyze
        expressions = self.expression_engine.analyze(subtitles, config)
        
        # Step 3: Create Videos
        final_video = self.video_factory.create_educational_video(input_video, expressions, config)
        
        return final_video
```

### Benefits
- **Testability**: Each service can be unit tested with mocks easily.
- **Reusability**: `VideoFactory` can be used by an API endpoint to "just cut a clip" without running full analysis.
- **Clarity**: `main.py` becomes a high-level description of *what* happens, not *how*.

## Risks & Considerations
- **Big Bang Refactor**: High risk of breaking existing flows.
    - **Mitigation**: Extract one service at a time (Strangler Fig Pattern). Start with `SubtitleService` (easiest), then `VideoFactory`.

## Testing Strategy
- Unit tests for each new service.
- Integration test for the Orchestrator ensuring it calls services in order.
- Functional regression test (running the full pipeline on a sample video) to ensure result is identical.

## Files Affected
- `langflix/main.py` (Delete/Shrink)
- `langflix/services/subtitle_service.py` (New)
- `langflix/services/translation_service.py` (New)
- `langflix/services/video_factory.py` (New)

## Success Criteria
- [ ] `LangFlixPipeline` reduced to < 300 lines (coordination only).
- [ ] No `self.state_variable` used for passing data between steps (pass as return values/arguments).
