# [TICKET-027] Fix Scheduled Time Mismatch Between UI and Backend

## Priority
- [x] High (User experience, data consistency)

## Type
- [ ] Refactoring
- [ ] Performance Optimization
- [x] Test Coverage
- [x] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [ ] Code Duplication

## Impact Assessment
**Business Impact:**
- Users see different times in the upload modal vs. success popup
- Creates confusion and reduces trust in the scheduling system
- Users cannot reliably predict when their videos will be published

**Technical Impact:**
- Affects `langflix/youtube/schedule_manager.py` - `schedule_video()` method
- Affects `langflix/youtube/web_ui.py` - `schedule_upload()` endpoint
- Affects `langflix/templates/video_dashboard.html` - Frontend time display
- Requires timezone handling and datetime consistency

**Effort Estimate:**
- Medium (1-3 days) - Requires understanding timezone handling, datetime serialization, and frontend-backend communication

## Problem Description

### Current State
**Location:** 
- `langflix/youtube/web_ui.py:904-941` - schedule_upload endpoint
- `langflix/youtube/schedule_manager.py:224-300` - schedule_video method
- `langflix/templates/video_dashboard.html:984-1000` - Frontend success popup

**Current Flow:**
1. Frontend calls `/api/schedule/next-available` and displays "Next available time: 2025. 11.04. 오전 09:00"
2. User clicks "Schedule Upload" with `publish_time = nextAvailableTime`
3. Backend receives `publish_time` and calls `schedule_manager.schedule_video(video_path, video_type, publish_time)`
4. `schedule_video()` may modify the time if it's already occupied (even with preferred_time)
5. Backend returns `publish_time.isoformat()` (original request) instead of `scheduled_time` (actual DB time)
6. Frontend displays success popup with potentially different time

**Problem:**
- UI shows "Next available time: 2025. 11.04. 오전 09:00"
- Success popup shows "Scheduled for: 2025. 11. 04. 오전 03:00:00"
- Times don't match, causing user confusion
- The actual scheduled time (from DB) is not being returned to the frontend

### Root Cause Analysis
1. **Backend doesn't respect preferred_time**: `schedule_video()` may recalculate time even when `preferred_time` is provided
2. **Wrong time returned**: `schedule_upload()` returns `publish_time` instead of `scheduled_time` from `schedule_video()`
3. **Timezone mismatch**: Frontend and backend may be using different timezones for display
4. **No validation**: Frontend doesn't verify that the returned time matches the requested time

### Evidence
- User reported: "scheduled date in upload and final popup have different date"
- Screenshot shows modal displays "오전 09:00" but popup shows "오전 03:00:00"
- Logs show `schedule_video()` returning different time than requested
- Frontend uses `publish_time` from request, not `scheduled_publish_time` from response

## Proposed Solution

### Approach
1. **Fix `schedule_video()` to respect `preferred_time`**: When `preferred_time` is provided, use it even if the slot appears occupied (user explicitly chose it)
2. **Return actual scheduled time**: Modify `schedule_upload()` to return `scheduled_time` from `schedule_video()` instead of original `publish_time`
3. **Frontend consistency**: Ensure frontend displays the actual `scheduled_publish_time` from backend response
4. **Timezone handling**: Ensure consistent timezone handling between frontend and backend

### Implementation Details

#### 1. Fix `schedule_video()` to respect preferred_time
```python
# In langflix/youtube/schedule_manager.py
# If preferred_time is provided, use it even if occupied (user explicitly chose it)
# Only find alternative if no preferred_time was provided
if target_datetime in occupied_times and not preferred_time:
    # Find next available time
    target_datetime = self.get_next_available_slot(video_type, target_date)
    ...
elif target_datetime in occupied_times and preferred_time:
    # Preferred time is occupied, but user explicitly chose it - allow it anyway
    logger.warning(f"Preferred time {target_datetime} is already occupied, but using it as requested")
```

#### 2. Return actual scheduled time from backend
```python
# In langflix/youtube/web_ui.py
success, message, scheduled_time = self.schedule_manager.schedule_video(
    video_path, schedule_video_type, publish_time
)

# Use the actual scheduled_time from schedule_video() response
# This is the time that was actually stored in the database
actual_scheduled_time = scheduled_time if scheduled_time else publish_time

return jsonify({
    "success": True,
    "scheduled_publish_time": actual_scheduled_time.isoformat(),
    ...
})
```

#### 3. Fix frontend to use backend response
```python
// In langflix/templates/video_dashboard.html
// Use scheduled_publish_time from backend response (this is the actual scheduled time)
const scheduledTime = result.scheduled_publish_time || result.scheduled_time;
if (scheduledTime) {
    const scheduledDate = new Date(scheduledTime);
    const formattedScheduledTime = scheduledDate.toLocaleString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
    });
    alert(`Video scheduled successfully!\n\nScheduled for: ${formattedScheduledTime}`);
}
```

### Alternative Approaches Considered
- Option 1: Always recalculate time on backend - **Rejected** because it ignores user's explicit choice
- Option 2: Prevent time conflicts on frontend - **Rejected** because it's complex and doesn't solve race conditions
- Option 3: Show warning if time changed - **Rejected** because it's better to respect user's choice

### Benefits
- UI and backend display consistent scheduled times
- Users can trust the time shown in the modal
- Respects user's explicit time selection
- Better user experience with clear, consistent feedback
- Prevents confusion about when videos will be published

### Risks & Considerations
- **Race conditions**: Multiple users scheduling at the same time may still conflict
- **Timezone handling**: Need to ensure consistent timezone between frontend and backend
- **Database constraints**: Need to handle cases where preferred time is truly unavailable
- **Backward compatibility**: Ensure existing scheduled uploads still work

## Testing Strategy

### Unit Tests
- Test `schedule_video()` with `preferred_time` that is already occupied
- Test `schedule_video()` returns the same time as `preferred_time` when provided
- Test `schedule_upload()` returns `scheduled_time` from `schedule_video()`
- Test timezone consistency between frontend and backend

### Integration Tests
- Test full flow: Frontend requests time → Backend schedules → Frontend displays correct time
- Test with multiple concurrent schedule requests
- Test with timezone differences

### Manual Testing
- Verify modal time matches success popup time
- Test with different timezones
- Test with occupied time slots

## Files Affected
- `langflix/youtube/schedule_manager.py` - Fix `schedule_video()` to respect `preferred_time`
- `langflix/youtube/web_ui.py` - Return actual `scheduled_time` instead of `publish_time`
- `langflix/templates/video_dashboard.html` - Use backend response time for display
- `tests/youtube/test_schedule_manager.py` - Add tests for `preferred_time` handling
- `tests/youtube/test_web_ui_api.py` - Add tests for time consistency

## Dependencies
- None - this is a bug fix

## References
- Related to TICKET-019 implementation (time mismatch discovered during testing)
- Current implementation: `langflix/youtube/schedule_manager.py:224-300`
- Current endpoint: `langflix/youtube/web_ui.py:705-956`

## Architect Review Questions
**For the architect to consider:**
1. Should we allow scheduling at occupied times, or enforce strict conflict prevention?
2. How should we handle timezone differences between user's browser and server?
3. Should we add validation to prevent scheduling conflicts before upload?
4. Is there a need for a queue system for conflicting schedule requests?

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-11-04
**Decision:** ✅ APPROVED

**Strategic Rationale:**
이 티켓은 사용자 경험과 데이터 일관성에 직접적인 영향을 미치는 중요한 버그 수정입니다:
- UI와 백엔드 간 시간 불일치는 사용자 신뢰를 해치는 심각한 문제입니다
- 명시적으로 선택한 시간을 존중하는 것은 올바른 사용자 경험 원칙입니다
- 데이터 일관성을 보장하는 것은 시스템 신뢰성의 핵심입니다

**Implementation Phase:** Phase 0 - Immediate (This Week)
**Sequence Order:** #1 in bug fix queue

**Architectural Guidance:**
1. **Timezone Handling**: 현재 `datetime.combine()`을 사용하는데, 이는 naive datetime을 생성합니다. YouTube API는 timezone-aware datetime을 요구하므로, `web_ui.py`에서 timezone을 추가하는 것은 올바른 접근입니다. 다만 `schedule_manager.py`의 `get_next_available_slot()`도 timezone-aware datetime을 반환하도록 고려해야 합니다.

2. **Conflict Resolution**: 사용자가 명시적으로 선택한 시간을 우선하는 것은 좋지만, 실제로 DB에 저장될 때 race condition이 발생할 수 있습니다. 이를 완전히 방지하기 위해서는 optimistic locking이나 unique constraint가 필요할 수 있지만, 현재는 경고 로그로 충분합니다.

3. **Response Consistency**: 백엔드가 실제 DB에 저장된 시간을 반환하는 것은 올바른 접근입니다. 이렇게 하면 프론트엔드와 백엔드가 항상 동일한 정보를 표시합니다.

**Dependencies:**
- **Must complete first:** None (standalone bug fix)
- **Should complete first:** None
- **Blocks:** None
- **Related work:** TICKET-019 (discovered during implementation)

**Risk Mitigation:**
- **Race Conditions**: 여러 사용자가 동시에 같은 시간을 스케줄링할 수 있지만, YouTube API의 `publishAt`은 중복을 허용하므로 큰 문제는 아닙니다. 다만 DB에 중복 기록이 생길 수 있으므로, 향후 unique constraint 추가를 고려할 수 있습니다.
- **Timezone Issues**: 브라우저와 서버 간 timezone 차이로 인한 혼란을 방지하기 위해, 모든 시간을 UTC로 통일하고 프론트엔드에서 로컬 시간으로 변환하는 것이 좋습니다. 현재 구현은 이를 부분적으로 처리하고 있습니다.

**Enhanced Success Criteria:**
Beyond original ticket criteria:
- [x] All times are timezone-aware (UTC)
- [x] Frontend displays time from backend response
- [x] Backend returns actual scheduled time from database
- [x] User's explicit time choice is respected
- [x] Logging added for debugging time mismatches

**Alternative Approaches Considered:**
- **Original proposal**: Use preferred_time even if occupied - **Selected** - This respects user's explicit choice
- **Alternative 1**: Always recalculate time - **Rejected** - Ignores user's explicit choice, poor UX
- **Alternative 2**: Show warning if time changed - **Rejected** - Better to respect user's choice upfront
- **Alternative 3**: Add conflict validation before upload - **Future consideration** - Good idea but adds complexity

**Implementation Notes:**
- Start by: Fixing `schedule_video()` to respect `preferred_time`
- Then: Update `schedule_upload()` to return actual `scheduled_time`
- Finally: Update frontend to use backend response time
- Watch out for: Timezone conversions between frontend and backend
- Coordinate with: Frontend team (if separate) for time display consistency
- Reference: TICKET-018 (scheduled upload implementation)

**Estimated Timeline:** 1-2 days
**Recommended Owner:** Backend engineer with frontend knowledge

## Success Criteria
How do we know this is successfully implemented?
- [ ] Modal time matches success popup time
- [ ] `schedule_video()` respects `preferred_time` when provided
- [ ] Backend returns actual `scheduled_time` from database
- [ ] Frontend displays time from backend response
- [ ] Unit tests pass for `preferred_time` handling
- [ ] Integration tests verify time consistency
- [ ] Manual testing confirms UI and backend times match
- [ ] Code review approved

