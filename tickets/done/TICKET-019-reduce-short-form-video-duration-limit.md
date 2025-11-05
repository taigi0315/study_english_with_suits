# [TICKET-019] Reduce Short-Form Video Duration Limit to Under 1 Minute

## Priority
- [x] Medium (Code quality, maintainability improvements)

## Type
- [x] Refactoring
- [ ] Performance Optimization
- [x] Test Coverage
- [x] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [ ] Code Duplication

## Impact Assessment
**Business Impact:**
- Better alignment with YouTube Shorts format requirements (< 1 minute)
- More accurate filtering of videos ready for upload
- Prevents uploading videos that YouTube might flag or restrict

**Technical Impact:**
- Single file needs modification: `langflix/youtube/video_manager.py`
- Simple constant change from 180 seconds (3 minutes) to 60 seconds (1 minute)
- No breaking changes - only affects validation logic

**Effort Estimate:**
- Small (< 1 day) - Simple constant change

## Problem Description

### Current State
**Location:** `langflix/youtube/video_manager.py:300-304`

The current implementation allows short-form videos up to 3 minutes (180 seconds):

```python
def _is_ready_for_upload(self, video_type: str, duration: float) -> bool:
    """Determine if video is ready for YouTube upload"""
    # Short-form videos should be under 3 minutes
    if video_type in ["short", "short-form"]:
        return 10 <= duration <= 180  # 10 seconds to 3 minutes
```

**Problem:**
- YouTube Shorts format typically requires videos to be under 60 seconds
- Current limit of 180 seconds (3 minutes) is too permissive
- Videos between 60-180 seconds may not qualify as YouTube Shorts
- User reported that YouTube was complaining about videos over 60 seconds

### Root Cause Analysis
- Initial implementation used a more lenient 3-minute limit
- YouTube Shorts format requirements evolved to prefer < 1 minute content
- No validation for YouTube Shorts-specific requirements

### Evidence
- User feedback: "youtube was complaining about more than 60 seconds"
- YouTube Shorts best practices recommend < 60 seconds
- Current limit doesn't align with YouTube Shorts format
- **Test inconsistency found**: `tests/youtube/test_video_manager.py` tests assume 60-second limit but code allows 180 seconds, indicating test expectations are correct but code is outdated

## Proposed Solution

### Approach
Change the duration limit for short-form videos from 180 seconds (3 minutes) to 60 seconds (1 minute).

### Implementation Details
```python
def _is_ready_for_upload(self, video_type: str, duration: float) -> bool:
    """Determine if video is ready for YouTube upload"""
    # Short-form videos should be under 1 minute (YouTube Shorts requirement)
    if video_type in ["short", "short-form"]:
        return 10 <= duration <= 60  # 10 seconds to 1 minute
```

### Alternative Approaches Considered
- Option 1: Keep 180 seconds but add warning - Not chosen because it doesn't solve the YouTube Shorts format issue
- Option 2: Make it configurable - Not chosen because it adds unnecessary complexity for a simple requirement

### Benefits
- Better alignment with YouTube Shorts format requirements
- Prevents uploading videos that YouTube might reject or flag
- Clearer validation logic matching actual platform requirements
- Reduces user confusion about which videos qualify for Shorts

### Risks & Considerations
- Videos currently between 60-180 seconds will no longer be marked as "ready for upload"
- Users may need to manually verify or re-encode existing videos
- No breaking changes to API - only affects internal validation

## Testing Strategy
- Unit test for `_is_ready_for_upload` with duration values:
  - 5 seconds (should return False - too short)
  - 30 seconds (should return True - within range)
  - 59 seconds (should return True - at upper limit)
  - 60 seconds (should return True - exactly at limit)
  - 61 seconds (should return False - over limit)
  - 180 seconds (should return False - over new limit)
- Integration test to verify short-form videos > 60 seconds are filtered out
- Manual testing with actual video files

## Files Affected
- `langflix/youtube/video_manager.py` - Update `_is_ready_for_upload` method (line 304)
- `tests/unit/test_video_manager.py` - Add/update tests for new duration limit (if exists)

## Dependencies
- None

## References
- YouTube Shorts format requirements
- Current implementation: `langflix/youtube/video_manager.py:300-314`

## Architect Review Questions
**For the architect to consider:**
1. Should we add a configuration option for this limit?
2. Should we support multiple duration limits for different video types?
3. Is there a need for a warning system for videos close to the limit?

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Code Improve Agent (Senior Engineer)
**Review Date:** 2025-01-03
**Decision:** ✅ APPROVED

**Strategic Rationale:**
This change aligns perfectly with YouTube Shorts format requirements and resolves the mismatch between test expectations (60s) and actual implementation (180s). The fix ensures code matches user requirements and platform best practices.

**Implementation Phase:** Immediate
**Sequence Order:** Ready for implementation

**Key Findings:**
- ✅ Tests already expect 60-second limit (tests were correct, code was outdated)
- ✅ Simple constant change with no breaking API changes
- ✅ Aligns with YouTube Shorts best practices
- ✅ Resolves user-reported issue with YouTube rejecting videos > 60 seconds

**Implementation Notes:**
- Code change: `langflix/youtube/video_manager.py:304` - change `180` to `60`
- All existing tests pass (they already expected this behavior)
- No additional test updates needed
- Documentation update recommended but not required

**Estimated Timeline:** < 1 hour
**Recommended Owner:** Any engineer (trivial change)

## Success Criteria
How do we know this is successfully implemented?
- [ ] `_is_ready_for_upload` returns False for short-form videos > 60 seconds
- [ ] `_is_ready_for_upload` returns True for short-form videos 10-60 seconds
- [ ] Unit tests pass with new duration limit
- [ ] Documentation updated if applicable
- [ ] Code review approved
