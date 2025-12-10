# [TICKET-086] Fix Missing Result Extraction in Pipeline Runner

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [x] High (Performance issues, significant tech debt)
- [ ] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [ ] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [x] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [ ] Code Duplication

## Impact Assessment
**Business Impact:**
- Fixes the return value of pipeline jobs. The dashboard relies on receiving the path of generated videos. Currently, it returns empty.

**Technical Impact:**
- `langflix/services/pipeline_runner.py` returns hardcoded empty strings/lists for `final_videos`.
- Fix requires properly extracting paths from the `LangFlixPipeline` result or using `VideoPipelineService`.

**Effort Estimate:**
- [x] Small (< 1 day)
- Medium (1-3 days)
- Large (> 3 days)

## Problem Description

### Current State
**Location:** `langflix/services/pipeline_runner.py:98`

The result extraction logic is incomplete/stubbed:
```python
# langflix/services/pipeline_runner.py
# Final video path is created by pipeline internally...
# We can't easily extract it here without accessing pipeline.paths, so we return empty for now
# TODO: Consider using VideoPipelineService here for better result extraction
final_video_path = ''
short_videos = []
```

### Root Cause Analysis
- `LangFlixPipeline` might not have returned the paths cleanly in older versions, leading to this workaround.
- Feature was implemented partially to get the progress bar working, but the return value was neglected.

### Evidence
- Code explicitly sets `final_video_path = ''`.

## Proposed Solution

### Approach
Update `PipelineRunner` to verify where `LangFlixPipeline` saves files, and return those paths.
The `pipeline` object has a `paths` attribute or the `run()` method returns metadata.

### Implementation Details
```python
# Use the pipeline instance to resolve paths
if hasattr(pipeline, 'paths') and 'final_videos' in pipeline.paths:
   final_video_path = pipeline.paths['final_videos'][0] if pipeline.paths['final_videos'] else ''
```
Or refactor to use `VideoPipelineService` if that service abstracts this already.

### Benefits
- Correctness: The job result will actually contain the generated video path.
- Usability: Frontend can link to the new video immediately.

### Risks & Considerations
- Need to verify `LangFlixPipeline` API.

## Testing Strategy
- Run a pipeline job.
- Assert that the returned dictionary contains a valid `final_videos` path.
- Verify file existence.

## Files Affected
- `langflix/services/pipeline_runner.py`

## Dependencies
- None.

## References
- None.
