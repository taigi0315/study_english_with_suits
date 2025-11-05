# [TICKET-018] Fix Scheduled YouTube Upload to Use publishAt Instead of Background Worker

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
- **Critical Feature Broken**: Scheduled uploads are stored in database but never executed
- **User Trust**: Users schedule videos expecting them to upload, but they never do
- **Misunderstanding**: Current implementation assumes server-side scheduling, but should use YouTube API's `publishAt` for scheduled publishing
- **Correct Behavior**: Upload immediately with `publishAt` set to scheduled time, not wait for scheduled time to upload

**Technical Impact:**
- **Affected Modules**: 
  - `langflix/youtube/schedule_manager.py` - Only stores schedules, doesn't process them
  - Missing: Background worker/task to process scheduled uploads
- **Files to Change**: ~3-5 files
  - Create new scheduled upload processor
  - Add periodic task (Celery Beat or FastAPI background task)
  - Update schedule_manager with process methods
- **Breaking Changes**: None (new feature)

**Effort Estimate:**
- Medium (1-3 days)
  - Need to implement background worker
  - Periodic task to check schedules
  - Upload execution logic
  - Error handling and retry logic

## Problem Description

### Current State

**Location:** 
- `langflix/youtube/schedule_manager.py:207-282` - `schedule_video()` method only stores schedule in DB
- `langflix/youtube/web_ui.py:797-816` - Schedule endpoint only creates DB record, doesn't upload
- `langflix/youtube/uploader.py:362-453` - `upload_video()` doesn't support `publishAt` parameter

**Critical Misunderstanding:**
The system was designed with a **server-side scheduling** model (wait for scheduled time, then upload), but YouTube scheduling should work differently:
- ✅ **Correct**: Upload immediately with YouTube API's `publishAt` parameter (scheduled publishing)
- ❌ **Wrong**: Store schedule in DB, wait for scheduled time, then upload

Currently, the system:
1. **Only stores schedule in database** but never uploads
2. **Assumes background worker** will process schedules later (not needed!)
3. **Missing `publishAt` support** in `upload_video()` method

**Evidence from Database:**
```
스케줄된 업로드 개수: 2
  - /path/to/video1.mkv: 2025-11-02 10:00:00+00:00 (status: scheduled)
  - /path/to/video2.mkv: 2025-11-03 16:00:00+00:00 (status: scheduled)
```
These are stored but never uploaded!

### Root Cause Analysis

1. **Architectural Misunderstanding**: System assumes server-side scheduling (background worker waits and uploads)
2. **Missing YouTube API Feature**: `upload_video()` doesn't accept `publishAt` parameter
3. **Incomplete Flow**: Schedule endpoint stores in DB but doesn't trigger upload
4. **Design Gap**: No integration between schedule creation and immediate upload

**Why this problem exists:**
- Schedule storage was implemented (TICKET-015) assuming background worker would process
- YouTube API's `publishAt` feature was not utilized
- Upload logic doesn't support scheduled publishing

### Evidence

**Database Evidence:**
```
스케줄된 업로드 개수: 2
  - /path/to/video1.mkv: 2025-11-02 10:00:00+00:00 (status: scheduled)
  - /path/to/video2.mkv: 2025-11-03 16:00:00+00:00 (status: scheduled)
```

**Code Evidence:**
- `schedule_manager.py` has no `process_scheduled_uploads()` method
- `tasks.py` has no Celery task for scheduled uploads
- No periodic task checking schedules
- Celery Beat container not running (or no tasks defined)

**User Impact:**
- Users schedule videos and see "success" message
- Videos never actually upload to YouTube
- Schedule accumulates in database with no execution

## Proposed Solution

### Approach

**Use YouTube API's `publishAt` feature for scheduled publishing:**
1. **Upload immediately** when user schedules a video
2. **Set `publishAt`** parameter in YouTube API request to scheduled time
3. **YouTube handles scheduling** - video uploads now but publishes at scheduled time
4. **Store schedule in DB** for tracking and quota management

**Strategy:**
1. **Modify `upload_video()`** to accept optional `publish_at` parameter
2. **Add `publishAt` to API request** body when `publish_at` is provided
3. **Update `schedule_upload` endpoint** to:
   - Generate metadata
   - Upload video immediately with `publishAt` set
   - Store schedule in DB with video_id and status='completed' (uploaded, scheduled)
4. **No background worker needed** - YouTube handles the scheduling

### Implementation Details

**1. Modify `YouTubeUploader.upload_video()` to support `publishAt`:**

```python
# langflix/youtube/uploader.py
def upload_video(
    self, 
    video_path: str, 
    metadata: YouTubeVideoMetadata,
    progress_callback: Optional[callable] = None,
    publish_at: Optional[datetime] = None  # NEW: Scheduled publish time
) -> YouTubeUploadResult:
    """Upload video to YouTube
    
    Args:
        video_path: Path to video file
        metadata: YouTube metadata
        progress_callback: Optional progress callback
        publish_at: Optional datetime for scheduled publishing (YouTube API publishAt)
    
    Returns:
        YouTubeUploadResult with upload status
    """
    # ... existing authentication and file checks ...
    
    # Prepare video metadata
    body = {
        'snippet': {
            'title': metadata.title,
            'description': metadata.description,
            'tags': metadata.tags,
            'categoryId': metadata.category_id
        },
        'status': {
            'privacyStatus': metadata.privacy_status
        }
    }
    
    # Add publishAt if scheduled publishing is requested
    if publish_at:
        # Convert to ISO format with Z timezone (YouTube API requirement)
        body['status']['publishAt'] = publish_at.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
        # Set privacy to private when using publishAt (required by YouTube)
        body['status']['privacyStatus'] = 'private'
        logger.info(f"Scheduling video for publish at {publish_at}")
    
    # ... rest of upload logic ...
```

**2. Update `schedule_upload` endpoint to upload immediately:**

```python
# langflix/youtube/web_ui.py
@self.app.route('/api/upload/schedule', methods=['POST'])
def schedule_upload():
    """Schedule video for upload with scheduled publishing"""
    data = request.get_json()
    video_path = data.get('video_path')
    video_type = data.get('video_type')
    publish_time_str = data.get('publish_time')
    
    # Parse publish time
    publish_time = None
    if publish_time_str:
        publish_time = datetime.fromisoformat(publish_time_str.replace('Z', '+00:00'))
    else:
        # Get next available slot
        publish_time = self.schedule_manager.get_next_available_slot(video_type)
    
    # Validate quota (existing logic)
    # ...
    
    # Generate metadata
    from langflix.youtube.video_manager import VideoFileManager
    from langflix.youtube.metadata_generator import YouTubeMetadataGenerator
    
    video_manager = VideoFileManager()
    all_videos = video_manager.scan_all_videos()
    video_metadata = next((v for v in all_videos if v.path == video_path), None)
    
    if not video_metadata:
        return jsonify({"error": "Video not found"}), 404
    
    metadata_generator = YouTubeMetadataGenerator()
    youtube_metadata = metadata_generator.generate_metadata(video_metadata)
    
    # Upload immediately with publishAt
    from langflix.youtube.uploader import YouTubeUploader
    uploader = YouTubeUploader()
    
    result = uploader.upload_video(
        video_path=video_path,
        metadata=youtube_metadata,
        publish_at=publish_time  # NEW: Pass publishAt parameter
    )
    
    if result.success:
        # Store schedule in DB for tracking
        success, message, scheduled_time = self.schedule_manager.schedule_video(
            video_path, video_type, publish_time
        )
        
        # Update schedule with video_id
        if success:
            self.schedule_manager.update_schedule_with_video_id(
                video_path, result.video_id, 'completed'  # Uploaded, scheduled
            )
            self.schedule_manager.update_quota_usage(video_type)
        
        return jsonify({
            "success": True,
            "message": f"Video uploaded and scheduled for {publish_time}",
            "video_id": result.video_id,
            "video_url": result.video_url,
            "scheduled_publish_time": publish_time.isoformat()
        })
    else:
        return jsonify({
            "success": False,
            "error": result.error_message
        }), 500
```

### Required Changes

**1. `YouTubeUploader.upload_video()` - Add `publish_at` parameter:**
- Add optional `publish_at: Optional[datetime] = None` parameter
- Set `body['status']['publishAt']` when `publish_at` is provided
- Set `privacyStatus` to 'private' when using `publishAt` (YouTube requirement)
- Convert datetime to UTC ISO format with 'Z' suffix

**2. `schedule_upload` endpoint - Upload immediately:**
- Generate video metadata using `VideoFileManager` and `YouTubeMetadataGenerator`
- Call `uploader.upload_video()` with `publish_at` parameter
- Store schedule in DB after successful upload
- Update schedule with `youtube_video_id` and status='completed'

**3. `YouTubeScheduleManager` - Add helper method:**
```python
def update_schedule_with_video_id(self, video_path: str, youtube_video_id: str, status: str = 'completed'):
    """Update schedule record with YouTube video ID after successful upload"""
    with db_manager.session() as db:
        schedule = db.query(YouTubeSchedule).filter_by(video_path=video_path).first()
        if schedule:
            schedule.youtube_video_id = youtube_video_id
            schedule.upload_status = status
            # Commit happens automatically via context manager
```

### Alternative Approaches Considered

**Option A: Background Worker (Original Ticket Approach)**
- **Pros**: Server controls upload timing
- **Cons**: Complex, unnecessary, YouTube already handles scheduling, requires background worker maintenance
- **Decision**: Rejected - YouTube API already provides this feature

**Option B: Two-step process (Upload now, schedule later)**
- **Pros**: Could use existing `schedule_video_publish()` method
- **Cons**: Extra API call, more complex, two operations instead of one
- **Decision**: Rejected - `publishAt` in upload request is cleaner

**Option C: Use YouTube API's `publishAt` (Selected)**
- **Pros**: 
  - Single operation (upload + schedule in one API call)
  - YouTube handles scheduling (no background worker needed)
  - More reliable (YouTube manages publish time)
  - Simpler codebase
- **Cons**: None significant
- **Decision**: ✅ Selected - This is the correct YouTube scheduling pattern

### Benefits

- **Fixes Broken Feature**: Scheduled uploads actually work
- **Simpler Architecture**: No background worker needed (YouTube handles it)
- **Better Reliability**: YouTube manages publish timing, not our server
- **Immediate Feedback**: User sees upload success immediately
- **Lower Resource Usage**: No periodic tasks running
- **Follows Best Practices**: Uses YouTube API's native scheduling feature

### Risks & Considerations

- **Timezone Handling**: Must convert `publish_at` to UTC with 'Z' suffix (YouTube requirement)
- **Privacy Status**: YouTube requires `privacyStatus='private'` when using `publishAt`
- **Upload Failures**: Handle upload errors gracefully, don't store schedule if upload fails
- **Quota Management**: Update quota after successful upload (happens immediately, not at publish time)
- **Metadata Generation**: Must generate metadata before upload (uses existing VideoFileManager)
- **Authentication**: YouTubeUploader must be authenticated before upload
- **Minimum Publish Time**: YouTube may require publish time to be at least a few minutes in future (validate)

## Testing Strategy

### Unit Tests
1. Test `get_ready_schedules()` - returns correct schedules
2. Test `update_schedule_status()` - updates DB correctly
3. Test `complete_schedule()` - marks as completed with video ID
4. Test `fail_schedule()` - marks as failed with error message
5. Test metadata generation/retrieval

### Integration Tests
1. Test full flow: schedule → wait → process → upload → complete
2. Test error handling: failed upload marks schedule as failed
3. Test quota updates after successful upload
4. Test concurrent processing prevention

### Manual Testing
1. Schedule an upload for 2 minutes in future
2. Wait and verify upload executes
3. Check YouTube channel for uploaded video
4. Verify database status updated

## Files Affected

1. **`langflix/youtube/uploader.py`**
   - Modify `upload_video()` to accept optional `publish_at` parameter
   - Add `publishAt` to request body when provided
   - Handle timezone conversion (UTC with 'Z' suffix)
   - Set `privacyStatus='private'` when using `publishAt`

2. **`langflix/youtube/web_ui.py`**
   - Modify `schedule_upload()` endpoint to upload immediately
   - Generate metadata before upload
   - Call `upload_video()` with `publish_at` parameter
   - Update schedule in DB with `youtube_video_id` after successful upload

3. **`langflix/youtube/schedule_manager.py`**
   - Add `update_schedule_with_video_id()` method to store video_id after upload

4. **`tests/unit/test_uploader.py`** (create/update if exists)
   - Test `upload_video()` with `publish_at` parameter
   - Test timezone conversion
   - Test privacy status handling

5. **`tests/integration/test_scheduled_upload.py`** (create)
   - Test full scheduled upload flow
   - Test upload with publishAt
   - Test schedule storage after upload

## Dependencies

- **Depends on**: 
  - YouTubeUploader working correctly (recent fixes should help)
  - PostgreSQL running (for schedule storage and tracking)
  - VideoFileManager and YouTubeMetadataGenerator working

- **Blocks**: None (standalone feature)

- **Related to**: 
  - TICKET-015 (schedule storage implementation - still needed for tracking)
  - YouTube upload functionality
  - No Celery dependency needed!

## References

- [Celery Periodic Tasks](https://docs.celeryproject.org/en/stable/userguide/periodic-tasks.html)
- Related: TICKET-015 (YouTube schedule storage)
- Related: QueueProcessor pattern (for background task reference)

## Success Criteria

How do we know this is successfully implemented?
- [ ] When user schedules upload, video uploads immediately to YouTube
- [ ] Video is set to private with `publishAt` set to scheduled time
- [ ] YouTube video ID is stored in schedule record after upload
- [ ] Schedule status shows 'completed' (uploaded, scheduled for publishing)
- [ ] Quota usage is updated after successful upload (not at publish time)
- [ ] Video appears in YouTube Studio as "Scheduled"
- [ ] Video publishes automatically at scheduled time (YouTube handles it)
- [ ] Failed uploads don't create schedule records
- [ ] Timezone conversion works correctly (UTC with 'Z' suffix)
- [ ] Unit tests cover `publish_at` parameter handling
- [ ] Integration test verifies end-to-end scheduled upload flow
- [ ] Manual testing confirms video uploads immediately and publishes at scheduled time

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-11-03
**Decision:** ✅ APPROVED

**Strategic Rationale:**
Why this aligns with our architectural vision:
- **Critical Feature Completion**: Scheduled uploads are a core feature that users rely on. The current implementation is incomplete and broken.
- **User Trust**: Broken scheduling undermines user confidence in the platform. Fixing this is essential for product credibility.
- **Simpler Architecture**: Using YouTube's native `publishAt` eliminates need for background workers, reducing complexity and operational overhead.
- **Best Practices**: Follows YouTube API's recommended pattern for scheduled publishing.
- **Immediate Value**: Users get immediate feedback (upload success) while YouTube handles the scheduling.

**Implementation Phase:** Phase 0 - Immediate (Critical Bug Fix)
**Sequence Order:** #1 - Highest priority

**Architectural Guidance:**

**⚠️ IMPORTANT CORRECTION:**
The original ticket assumed server-side scheduling (background worker waits and uploads). However, YouTube scheduling should work differently:
- **Upload immediately** with YouTube API's `publishAt` parameter
- **YouTube handles scheduling** - no background worker needed
- **Simpler, more reliable** approach

**1. Metadata Generation Pattern:**
- **Issue**: `get_video_metadata()` in ticket needs to use `VideoFileManager` to get `VideoMetadata`, then pass to `YouTubeMetadataGenerator`
- **Current Pattern**: `VideoFileManager.scan_all_videos()` → find video by path → `metadata_generator.generate_metadata(video_metadata)`
- **Implementation**:
```python
def get_video_metadata(self, video_path: str) -> YouTubeVideoMetadata:
    """Get or generate YouTube metadata for video"""
    from langflix.youtube.video_manager import VideoFileManager
    from langflix.youtube.metadata_generator import YouTubeMetadataGenerator
    
    # Scan videos and find the one matching video_path
    video_manager = VideoFileManager()
    all_videos = video_manager.scan_all_videos()
    video_metadata = next((v for v in all_videos if v.path == video_path), None)
    
    if not video_metadata:
        raise ValueError(f"Video metadata not found for path: {video_path}")
    
    # Generate YouTube metadata
    generator = YouTubeMetadataGenerator()
    return generator.generate_metadata(video_metadata)
```

**2. YouTube API `publishAt` Requirements:**
- **Format**: Must be ISO 8601 format with 'Z' timezone suffix: `2025-11-03T10:00:00Z`
- **Timezone**: Must be UTC (convert local time to UTC)
- **Privacy Status**: Must be 'private' when using `publishAt` (YouTube requirement)
- **Minimum Time**: YouTube may require publish time to be at least a few minutes in the future (validate)
```python
# Convert to UTC with 'Z' suffix
if publish_at:
    utc_time = publish_at.astimezone(timezone.utc)
    publish_at_iso = utc_time.isoformat().replace('+00:00', 'Z')
    body['status']['publishAt'] = publish_at_iso
    body['status']['privacyStatus'] = 'private'  # Required when using publishAt
```

**3. Upload Flow:**
- **Generate metadata first** (before upload attempt)
- **Upload with `publish_at`** parameter
- **Store schedule in DB** only after successful upload
- **Update quota** immediately after upload (not at publish time)

**4. Error Handling:**
- **Upload failures**: Don't create schedule record, return error to user
- **Authentication errors**: Re-authenticate before upload
- **File access errors**: Validate file exists before upload
- **Metadata generation errors**: Fail fast with clear error message

**5. Integration Points:**
- **YouTubeUploader**: Must support `publish_at` parameter in `upload_video()`
- **VideoFileManager**: Used to get video metadata for metadata generation
- **YouTubeMetadataGenerator**: Generates YouTube metadata from video metadata
- **Database**: Store schedule for tracking (video_id, status, scheduled_publish_time)
- **No Celery needed**: YouTube handles scheduling

**6. Schedule Storage Purpose:**
- **Tracking**: Track which videos are scheduled (even though YouTube also tracks)
- **Quota Management**: Track daily limits and quota usage
- **UI Display**: Show scheduled videos in calendar view
- **Status**: Store as 'completed' (uploaded, scheduled for publishing)

**Dependencies:**
- **Must complete first:** None (standalone fix)
- **Blocks:** None
- **Related work:** 
  - TICKET-015 (schedule storage - still needed for tracking and quota)
  - YouTubeUploader must be working (recent fixes in TICKET-017)

**Risk Mitigation:**

**Risk 1: Timezone Conversion Error**
- **Impact**: Video publishes at wrong time
- **Mitigation**: Always convert to UTC, use 'Z' suffix, test timezone conversions
- **Rollback**: Fix timezone conversion, reschedule if needed

**Risk 2: Metadata Generation Failure**
- **Impact**: Upload fails because video metadata not found
- **Mitigation**: Validate video exists before upload, clear error messages
- **Rollback**: User can retry after fixing video path

**Risk 3: Authentication Expiration**
- **Impact**: Upload fails due to expired token
- **Mitigation**: Check authentication before upload, auto-refresh token
- **Rollback**: User can re-authenticate and retry

**Risk 4: YouTube API publishAt Validation**
- **Impact**: YouTube rejects publishAt (too soon, invalid format)
- **Mitigation**: Validate minimum time (e.g., 15 minutes in future), format correctly
- **Rollback**: Return clear error, allow user to adjust time

**Risk 5: Upload Success but Schedule Storage Fails**
- **Impact**: Video uploaded but not tracked in our DB
- **Mitigation**: Store schedule in same transaction, handle gracefully
- **Rollback**: Video still uploaded to YouTube (not lost), can manually add to DB

**Enhanced Success Criteria:**
Beyond original ticket criteria:
- [ ] Timezone conversion works correctly (UTC with 'Z' suffix)
- [ ] Privacy status automatically set to 'private' when using publishAt
- [ ] Metadata generation handles missing videos gracefully
- [ ] Authentication automatically refreshed when needed
- [ ] Failed uploads don't create schedule records (clean error handling)
- [ ] Video appears in YouTube Studio as "Scheduled" immediately after upload
- [ ] Comprehensive logging for debugging scheduled upload issues
- [ ] Documentation updated explaining YouTube scheduling vs server scheduling

**Alternative Approaches Considered:**
- **Background Worker (Original)**: Server waits and uploads at scheduled time
  - **Why not chosen**: Unnecessary complexity, YouTube already handles scheduling, requires worker maintenance
- **Two-Step Process**: Upload now, call `schedule_video_publish()` separately
  - **Why not chosen**: Extra API call, less efficient, two operations instead of one
- **YouTube API publishAt (Selected)**: Upload immediately with publishAt in request
  - **Why chosen**: Native YouTube feature, simpler, more reliable, single operation

**Selected approach:** YouTube API's `publishAt` parameter - leverages YouTube's native scheduling, simpler architecture, production-ready

**Implementation Notes:**
- **Start by**: Modifying `YouTubeUploader.upload_video()` to accept `publish_at` parameter
- **Then**: Update `schedule_upload` endpoint to upload immediately with `publish_at`
- **Finally**: Add `update_schedule_with_video_id()` method to store video_id after upload
- **Watch out for**: 
  - Timezone conversion (must be UTC with 'Z' suffix)
  - Privacy status must be 'private' when using publishAt
  - YouTube may require minimum time in future (validate)
  - Handle upload failures gracefully (don't store schedule)
- **Coordinate with**: Ensure YouTubeUploader is stable (recent fixes should help)
- **Reference**: 
  - YouTube API documentation for `publishAt`
  - Existing `schedule_video_publish()` method (similar concept, but use publishAt directly)
  - `docs/services/README_eng.md` for service patterns

**Estimated Timeline:** 1-2 days
- Day 1: Modify `upload_video()` + update `schedule_upload` endpoint + unit tests
- Day 2: Integration tests, manual testing, documentation update

**Recommended Owner:** Senior Backend Engineer
- Requires understanding of Celery, database transactions, YouTube API
- Needs experience with async/concurrency patterns

