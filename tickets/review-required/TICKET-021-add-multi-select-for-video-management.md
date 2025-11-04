# [TICKET-021] Add Multi-Select Checkbox for Video Management (Upload/Delete)

## Priority
- [x] High (User experience, productivity improvement)

## Type
- [ ] Refactoring
- [ ] Performance Optimization
- [x] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [ ] Code Duplication

## Impact Assessment
**Business Impact:**
- Users can currently only upload/delete one video at a time
- Batch operations significantly improve productivity
- Reduces repetitive actions for users managing multiple videos
- Enables efficient bulk management of video library

**Technical Impact:**
- Affects `langflix/templates/video_dashboard.html` - Add checkboxes to video list
- Affects `langflix/youtube/web_ui.py` - Add batch upload/delete endpoints
- Requires sequential scheduling logic for scheduled uploads
- May require backend queue management for batch operations

**Effort Estimate:**
- Medium (2-3 days) - Requires frontend UI changes, backend batch endpoints, and sequential scheduling logic

## Problem Description

### Current State
**Location:**
- `langflix/templates/video_dashboard.html:691-720` - Video list display
- `langflix/templates/video_dashboard.html:800-1029` - Upload functionality (single file)
- `langflix/youtube/web_ui.py:705-956` - Upload endpoint (single file)

**Current Flow:**
1. User sees list of videos in dashboard
2. Each video has individual "Upload" button
3. User can only upload one video at a time
4. No batch delete functionality exists
5. No way to select multiple videos for batch operations

**Problem:**
- Users must click "Upload" for each video individually
- No way to delete multiple videos at once
- No batch scheduling capability
- Inefficient for managing large video libraries
- No checkboxes for multi-selection

### Root Cause Analysis
1. **UI Design**: Video list uses individual buttons, no checkbox selection mechanism
2. **Backend API**: Endpoints only accept single video_path
3. **Scheduling Logic**: Current scheduling calculates one time slot, doesn't handle sequential scheduling
4. **Missing Features**: No batch delete endpoint exists

### Evidence
- User request: "Currently user can chose 1 file to upload, I wish there is check box on list of items"
- Content Creation modal already has checkbox pattern (`.media-checkbox`) that can be reused
- TICKET-014 already implemented batch processing for content creation, similar pattern needed for uploads

## Proposed Solution

### Approach
1. **Add Checkboxes to Video List**: Add checkbox to each video row in the dashboard
2. **Batch Action Buttons**: Add "Delete Selected" and "Upload Selected" buttons
3. **Backend Batch Endpoints**: Create endpoints for batch delete and batch upload
4. **Sequential Scheduling**: For scheduled uploads, calculate next available slot for each video sequentially
5. **Progress Tracking**: Show progress for batch operations

### Implementation Details

#### 1. Frontend: Add Checkboxes to Video List
```html
<!-- In langflix/templates/video_dashboard.html -->
<div class="video-row">
    <input type="checkbox" class="video-checkbox" data-video-path="${video.path}" style="margin-right: 10px;">
    <!-- Existing video info -->
    <button onclick="uploadToYouTube('${video.path}')">Upload</button>
</div>
```

#### 2. Frontend: Add Batch Action Buttons
```html
<!-- Add action bar above video list -->
<div class="batch-actions" style="display: none; padding: 10px; background: #f8f9fa; margin-bottom: 10px;">
    <span id="selectedCount">0 selected</span>
    <button id="deleteSelectedBtn" style="margin-left: 10px;">Delete Selected</button>
    <button id="uploadImmediateBtn" style="margin-left: 10px;">Upload Selected (Immediate)</button>
    <button id="uploadScheduleBtn" style="margin-left: 10px;">Upload Selected (Schedule)</button>
</div>
```

#### 3. Backend: Batch Delete Endpoint
```python
# In langflix/youtube/web_ui.py
@self.app.route('/api/videos/batch/delete', methods=['POST'])
def batch_delete_videos():
    """Delete multiple video files"""
    try:
        data = request.get_json()
        video_paths = data.get('video_paths', [])
        
        if not video_paths:
            return jsonify({"error": "No video paths provided"}), 400
        
        deleted = []
        failed = []
        
        for video_path in video_paths:
            try:
                # Delete file
                if os.path.exists(video_path):
                    os.remove(video_path)
                    deleted.append(video_path)
                else:
                    failed.append({"path": video_path, "error": "File not found"})
            except Exception as e:
                failed.append({"path": video_path, "error": str(e)})
        
        return jsonify({
            "success": len(failed) == 0,
            "deleted": deleted,
            "failed": failed,
            "deleted_count": len(deleted),
            "failed_count": len(failed)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

#### 4. Backend: Batch Upload Endpoint (Immediate)
```python
@self.app.route('/api/upload/batch/immediate', methods=['POST'])
def batch_upload_immediate():
    """Upload multiple videos immediately"""
    try:
        data = request.get_json()
        videos = data.get('videos', [])  # List of {video_path, video_type}
        
        if not videos:
            return jsonify({"error": "No videos provided"}), 400
        
        results = []
        for video in videos:
            # Reuse existing immediate upload logic
            result = self._upload_immediate(video['video_path'], video['video_type'])
            results.append(result)
        
        return jsonify({
            "success": all(r.get('success') for r in results),
            "results": results
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

#### 5. Backend: Batch Upload Endpoint (Scheduled)
```python
@self.app.route('/api/upload/batch/schedule', methods=['POST'])
def batch_upload_schedule():
    """Schedule multiple videos for upload (sequential scheduling)"""
    try:
        data = request.get_json()
        videos = data.get('videos', [])  # List of {video_path, video_type}
        
        if not videos:
            return jsonify({"error": "No videos provided"}), 400
        
        if not self.schedule_manager:
            return jsonify({"error": "Schedule manager not available"}), 503
        
        results = []
        # Schedule videos sequentially, calculating next available slot for each
        for video in videos:
            video_path = video['video_path']
            video_type = video['video_type']
            
            # Map video_type for schedule_manager
            schedule_video_type = 'short' if video_type == 'context' else ('final' if video_type == 'long-form' else video_type)
            
            # Get next available slot (will automatically find next available time)
            publish_time = self.schedule_manager.get_next_available_slot(schedule_video_type)
            
            # Upload with publishAt
            result = self._upload_with_schedule(video_path, video_type, publish_time)
            
            # After successful upload, schedule next video at next available slot
            # This ensures sequential scheduling
            results.append({
                "video_path": video_path,
                "scheduled_time": publish_time.isoformat(),
                "success": result.get('success', False),
                "video_id": result.get('video_id'),
                "error": result.get('error')
            })
        
        return jsonify({
            "success": all(r.get('success') for r in results),
            "results": results
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

#### 6. Sequential Scheduling Logic
The key requirement is that scheduled uploads should be scheduled one by one, with each video getting the next available slot:

```python
# For each video in batch:
# 1. Get next available slot (this automatically finds next free time)
publish_time = schedule_manager.get_next_available_slot(video_type)
# 2. Upload with publishAt
upload_video(video_path, publish_at=publish_time)
# 3. Schedule is saved to DB, occupying the time slot
# 4. Next video will get the next available slot automatically
```

### Alternative Approaches Considered
- **Option 1**: Parallel scheduling (calculate all slots upfront) - **Rejected** because user wants sequential scheduling
- **Option 2**: Queue-based batch processing - **Rejected** because immediate feedback is better for UI
- **Option 3**: Single endpoint for both immediate and scheduled - **Rejected** because they have different logic flows

### Benefits
- Users can manage multiple videos efficiently
- Batch operations save time and clicks
- Sequential scheduling ensures proper time slot allocation
- Consistent with existing batch content creation pattern
- Better user experience for bulk operations

### Risks & Considerations
- **File System Errors**: Some files might fail to delete, need error handling
- **Upload Failures**: Some uploads might fail, need partial success handling
- **Scheduling Conflicts**: Sequential scheduling should prevent conflicts, but race conditions possible
- **Large Batches**: Need to handle timeouts for large batches
- **Progress Feedback**: Need to show progress for long-running batch operations
- **Backward Compatibility**: Single-file upload should still work

## Testing Strategy

### Unit Tests
- Test batch delete with valid/invalid file paths
- Test batch upload immediate with multiple videos
- Test batch upload schedule with sequential time calculation
- Test error handling for partial failures

### Integration Tests
- Test full flow: Select videos → Batch delete → Verify files removed
- Test full flow: Select videos → Batch upload immediate → Verify uploads
- Test full flow: Select videos → Batch upload schedule → Verify sequential scheduling
- Test with empty selection
- Test with mixed video types

### Manual Testing
- Select multiple videos and delete
- Select multiple videos and upload immediately
- Select multiple videos and schedule uploads
- Verify scheduled times are sequential
- Test with large batches (10+ videos)

## Files Affected
- `langflix/templates/video_dashboard.html` - Add checkboxes, batch action buttons, JavaScript handlers
- `langflix/youtube/web_ui.py` - Add batch delete, batch upload immediate, batch upload schedule endpoints
- `tests/youtube/test_web_ui_api.py` - Add tests for batch endpoints
- `tests/integration/test_batch_operations.py` - Add integration tests (if exists)

## Dependencies
- None - this is a new feature

## References
- TICKET-014: Batch content creation (similar pattern for batch operations)
- Current implementation: `langflix/templates/video_dashboard.html:691-720`
- Current upload endpoint: `langflix/youtube/web_ui.py:705-956`

## Architect Review Questions
**For the architect to consider:**
1. Should batch operations be queued and processed asynchronously, or processed synchronously?
2. How should we handle very large batches (50+ videos)? Should we add a limit?
3. Should we show progress for batch operations in real-time?
4. Should batch delete also remove YouTube uploads if videos are already uploaded?
5. Should we add a "Select All" checkbox for convenience?

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-11-04
**Decision:** ✅ APPROVED

**Strategic Rationale:**
이 티켓은 사용자 생산성과 시스템 효율성을 크게 향상시키는 중요한 기능 개선입니다:
- 배치 작업 기능은 대규모 비디오 라이브러리 관리에 필수적입니다
- TICKET-014의 배치 콘텐츠 생성과 일관된 패턴을 따릅니다
- 순차적 스케줄링은 YouTube 할당량 관리와 일관된 게시 전략에 중요합니다
- 사용자 경험을 크게 개선하여 반복 작업을 줄입니다

**Implementation Phase:** Phase 1 - Sprint 1 (Next 2 weeks)
**Sequence Order:** #1 in feature queue

**Architectural Guidance:**
1. **Batch Processing Pattern**: TICKET-014의 배치 콘텐츠 생성 패턴을 재사용하세요. 이는 이미 검증된 패턴이며 일관성을 제공합니다.

2. **Sequential Scheduling**: 순차적 스케줄링은 각 비디오마다 `get_next_available_slot()`을 호출하여 자동으로 다음 사용 가능한 시간을 찾도록 구현해야 합니다. 이는 사용자 요구사항을 정확히 충족합니다.

3. **Synchronous vs Asynchronous**: 초기 구현은 동기식으로 하되, 향후 대용량 배치 처리를 위해 비동기 큐 시스템으로 확장할 수 있도록 설계하세요. 즉시 피드백이 사용자 경험에 중요합니다.

4. **Error Handling**: 부분 실패 상황을 명확히 처리해야 합니다. 일부 파일이 삭제/업로드에 실패하더라도 나머지는 성공적으로 처리되어야 합니다.

5. **Progress Feedback**: UI에서 배치 작업 진행 상황을 표시해야 합니다. 특히 대용량 배치의 경우 사용자가 진행 상황을 볼 수 있어야 합니다.

6. **Backward Compatibility**: 기존 단일 파일 업로드 기능은 그대로 유지되어야 합니다. 체크박스는 추가 기능이지 기존 기능을 대체하지 않습니다.

**Dependencies:**
- **Must complete first:** None (standalone feature)
- **Should complete first:** TICKET-014 (for reference pattern), TICKET-018 (for scheduling logic)
- **Blocks:** None
- **Related work:** TICKET-014 (batch content creation pattern)

**Risk Mitigation:**
- **Large Batches**: 배치 크기 제한(예: 최대 50개)을 추가하여 타임아웃을 방지하세요.
- **File System Errors**: 삭제 실패 시 명확한 에러 메시지를 제공하고, 부분 실패를 허용하세요.
- **Upload Failures**: 일부 업로드 실패 시에도 성공한 항목은 완료 상태로 표시하고, 실패한 항목은 재시도 가능하도록 하세요.
- **Scheduling Race Conditions**: 순차적 스케줄링은 대부분의 경쟁 조건을 방지하지만, 동시 사용자 시나리오를 고려하세요.

**Enhanced Success Criteria:**
Beyond original ticket criteria:
- [x] Follows TICKET-014 batch processing pattern for consistency
- [x] Sequential scheduling ensures each video gets next available slot
- [x] Partial failure handling works correctly
- [x] Progress feedback shown for batch operations
- [x] Backward compatibility maintained (single-file upload still works)
- [x] Batch size limit enforced (e.g., max 50 videos)
- [x] Error messages are clear and actionable

**Alternative Approaches Considered:**
- **Original proposal**: Synchronous batch processing with sequential scheduling - **Selected** - Matches user requirements, provides immediate feedback
- **Alternative 1**: Asynchronous queue-based processing - **Future consideration** - Good for very large batches, but adds complexity
- **Alternative 2**: Parallel scheduling (calculate all slots upfront) - **Rejected** - Doesn't match user requirement for sequential scheduling
- **Alternative 3**: Single unified batch endpoint - **Rejected** - Immediate and scheduled have different logic flows

**Implementation Notes:**
- Start by: Adding checkboxes to video list UI
- Then: Implement batch action buttons and handlers
- Next: Create backend batch endpoints (delete, immediate, schedule)
- Finally: Add progress tracking and error handling
- Watch out for: Timeout issues with large batches, sequential scheduling logic correctness
- Coordinate with: Frontend patterns from TICKET-014
- Reference: TICKET-014 (batch content creation), TICKET-018 (scheduling logic)

**Estimated Timeline:** 2-3 days
**Recommended Owner:** Full-stack engineer (frontend + backend knowledge)

## Success Criteria
How do we know this is successfully implemented?
- [ ] Checkboxes appear on each video row
- [ ] Batch action buttons appear when videos are selected
- [ ] Users can delete multiple videos at once
- [ ] Users can upload multiple videos immediately
- [ ] Users can schedule multiple videos with sequential time slots
- [ ] Each scheduled video gets the next available time slot (not all at once)
- [ ] Error handling works for partial failures
- [ ] Progress feedback is shown for batch operations
- [ ] Single-file upload still works (backward compatibility)
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing confirms all features work
- [ ] Code review approved

