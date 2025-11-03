# [TICKET-014] Implement Batch Video Processing Queue System

## Priority
- [x] High (Performance issues, significant tech debt)
- [ ] Critical (System stability, security, data loss risk)
- [ ] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [ ] Refactoring
- [x] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [x] Code Duplication

## Impact Assessment
**Business Impact:**
- **User Experience**: Users can select multiple videos at once instead of processing them one-by-one, significantly improving workflow efficiency
- **Time Savings**: Eliminates repetitive clicking and waiting for each individual video
- **Risk of NOT fixing**: Users waste time with repetitive single-video processing, leading to poor UX and potential user frustration

**Technical Impact:**
- **Modules Affected:**
  - UI: `langflix/templates/video_dashboard.html` - Media selection UI, progress display
  - Flask Routes: `langflix/youtube/web_ui.py` - Batch creation endpoint
  - FastAPI Routes: `langflix/api/routes/jobs.py` - Batch job management
  - Redis Manager: `langflix/core/redis_client.py` - Batch queue storage
  - Background Processing: New queue processor service needed
- **Files Needing Changes**: ~8-10 files (estimate)
- **Breaking Changes**: None (backward compatible - single video processing still works)

**Effort Estimate:**
- **Large (> 3 days)**
  - UI changes: ~1 day
  - Backend queue system: ~1.5 days
  - Progress tracking & display: ~1 day
  - Testing & refinement: ~0.5 days
  - **Total: ~4 days**

## Problem Description

### Current State
**Location:** 
- `langflix/templates/video_dashboard.html:1188-1195` (Media selection)
- `langflix/templates/video_dashboard.html:1262-1316` (Content creation)
- `langflix/youtube/web_ui.py:793-860` (Flask content creation route)
- `langflix/api/routes/jobs.py:145-231` (FastAPI job creation)

Currently, the system only allows processing **one video at a time**:

1. **UI Limitation**: Users can only select a single video using radio buttons
   ```html
   <!-- Current: Single selection via radio -->
   <input type="radio" name="mediaFile" value="${media.id}" ... />
   ```

2. **Immediate Execution**: When a video is selected and "Create Content" is clicked, the job is immediately submitted to FastAPI and starts processing via `BackgroundTasks`
   ```python
   # Current: Immediate execution
   background_tasks.add_task(process_video_task, ...)
   ```

3. **No Queue Management**: There's no mechanism to:
   - Queue multiple videos for batch processing
   - Track batch status
   - Display progress for multiple concurrent/queued jobs
   - Automatically process next job in queue

4. **Single Progress Display**: The UI only shows progress for one job at a time via `showJobProgressModal(job_id)` function

### Root Cause Analysis
The system was designed for single-job processing because:
- Initial implementation focused on getting basic video processing working
- BackgroundTasks from FastAPI executes tasks immediately (no queue)
- Redis stores individual jobs but doesn't have a queue structure
- UI was built for simple single-video workflow

**Pattern that led to this:**
- Synchronous workflow: User action → Immediate job creation → Background task execution
- No separation between job creation and job execution
- Redis used for job state storage, not as a queue system

### Evidence
- **User Workflow**: Users must click "Create Content" → wait → click again for next video (repetitive)
- **No batch capability**: Cannot select multiple videos in UI
- **No queue system**: Redis stores jobs but doesn't manage execution order
- **Limited progress tracking**: Only one job's progress visible at a time

## Proposed Solution

### High-Level Architecture

The solution involves three main components:

1. **Batch Queue System**: Redis-based queue that stores pending jobs and manages execution order
2. **Queue Processor**: Background worker that processes jobs sequentially from the queue
3. **Multi-Job Progress UI**: UI component that displays progress for all jobs in a batch

### Approach

#### Phase 1: Backend Queue Infrastructure

**1.1. Extend Redis Job Manager** (`langflix/core/redis_client.py`)
Add batch queue management methods:
- `create_batch(batch_id, video_list)` - Create batch with multiple videos
- `add_job_to_batch(batch_id, job_id)` - Add job to batch
- `get_batch_status(batch_id)` - Get batch with all jobs
- `get_next_job_from_queue()` - Get next pending job (FIFO)
- `mark_job_processing(job_id)` - Mark job as processing
- `mark_job_complete(job_id)` - Mark job complete and trigger next

**1.2. Create Batch Queue Service** (`langflix/services/batch_queue_service.py`)
New service that manages batch processing:
```python
class BatchQueueService:
    """Manages batch video processing queue"""
    
    def create_batch(self, videos: List[Dict], config: Dict) -> str:
        """Create a batch with multiple videos, returns batch_id"""
        
    def get_batch_status(self, batch_id: str) -> Dict:
        """Get batch status with all jobs"""
        
    def start_queue_processor(self):
        """Start background worker that processes queue sequentially"""
```

**1.3. Modify FastAPI Job Creation** (`langflix/api/routes/jobs.py`)
- Add new endpoint: `POST /api/v1/batch` - Create batch jobs (don't execute immediately)
- Modify existing: `POST /api/v1/jobs` - Keep for single jobs (backward compatible)
- Jobs created via batch endpoint are queued, not executed immediately

#### Phase 2: Queue Processor Worker

**2.1. Sequential Job Processor** (`langflix/services/queue_processor.py`)
Background worker that:
- Polls Redis queue for pending jobs
- Processes one job at a time (sequential execution)
- Automatically starts next job when current completes
- Updates batch status when each job completes

```python
class QueueProcessor:
    """Processes jobs from queue sequentially"""
    
    async def start(self):
        """Start processing loop"""
        while True:
            job_id = redis_manager.get_next_job_from_queue()
            if job_id:
                await self.process_job(job_id)
            else:
                await asyncio.sleep(1)  # Poll interval
    
    async def process_job(self, job_id: str):
        """Process single job (similar to current process_video_task)"""
        # Mark as PROCESSING
        # Execute video processing
        # Mark as COMPLETED/FAILED
        # Trigger next job if in batch
```

**2.2. Integration Point**
- Start queue processor when FastAPI app starts (in `langflix/api/main.py`)
- Use asyncio background task or separate thread

#### Phase 3: UI Changes

**3.1. Multi-Selection UI** (`langflix/templates/video_dashboard.html`)

**Change 1: Radio → Checkbox Selection**
```javascript
// Current (line 1188):
<input type="radio" name="mediaFile" value="${media.id}" ... />

// New:
<input type="checkbox" class="media-checkbox" data-media-id="${media.id}" 
       data-video="${media.video_path}" data-subtitle="${media.subtitle_path || ''}" ... />
```

**Change 2: Batch Creation Function**
```javascript
async function startBatchContentCreation() {
    // Get all selected checkboxes
    const selectedMedia = document.querySelectorAll('.media-checkbox:checked');
    
    if (selectedMedia.length === 0) {
        alert('Please select at least one media file');
        return;
    }
    
    // Collect all selected videos
    const videos = Array.from(selectedMedia).map(checkbox => ({
        media_id: checkbox.dataset.mediaId,
        video_path: checkbox.dataset.video,
        subtitle_path: checkbox.dataset.subtitle
    }));
    
    // Get configuration
    const config = {
        language_code: document.getElementById('languageSelect').value,
        language_level: document.getElementById('levelSelect').value,
        test_mode: document.getElementById('testModeCheckbox').checked
    };
    
    // Call batch creation API
    const response = await fetch('/api/content/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ videos, ...config })
    });
    
    // Show batch progress modal
    const result = await response.json();
    showBatchProgressModal(result.batch_id);
}
```

**3.2. Batch Progress Display** (`langflix/templates/video_dashboard.html`)

Create new function to display multiple jobs:
```javascript
async function showBatchProgressModal(batchId) {
    // Create bottom progress panel
    const progressPanel = document.createElement('div');
    progressPanel.id = 'batchProgressPanel';
    progressPanel.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 20px;
        right: 20px;
        max-height: 400px;
        overflow-y: auto;
        background: white;
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        z-index: 1000;
        padding: 20px;
    `;
    
    // Poll for batch status and update UI
    const updateInterval = setInterval(async () => {
        const response = await fetch(`/api/content/batch/${batchId}`);
        const batch = await response.json();
        
        updateBatchProgressUI(batch);
        
        // Stop polling if all jobs completed
        if (batch.status === 'COMPLETED' || batch.status === 'FAILED') {
            clearInterval(updateInterval);
        }
    }, 2000);  // Poll every 2 seconds
}
```

**3.3. Individual Job Progress Cards**
Each job in batch gets its own progress card:
```html
<div class="job-progress-card">
    <div class="job-header">
        <span class="job-title">${job.episode_name}</span>
        <span class="job-status">${job.status}</span>
    </div>
    <div class="progress-bar">
        <div class="progress-fill" style="width: ${job.progress}%"></div>
    </div>
    <div class="job-step">${job.current_step}</div>
</div>
```

#### Phase 4: Flask Proxy Routes

**4.1. Batch Creation Route** (`langflix/youtube/web_ui.py`)
```python
@self.app.route('/api/content/batch', methods=['POST'])
def create_batch():
    """Create batch of video processing jobs"""
    data = request.json
    
    videos = data.get('videos', [])
    if not videos:
        return jsonify({"error": "No videos provided"}), 400
    
    # Call FastAPI batch endpoint
    fastapi_url = "http://localhost:8000/api/v1/batch"
    response = requests.post(fastapi_url, json=data)
    
    return jsonify(response.json()), response.status_code
```

**4.2. Batch Status Route**
```python
@self.app.route('/api/content/batch/<batch_id>')
def get_batch_status(batch_id):
    """Get batch status with all jobs"""
    fastapi_url = f"http://localhost:8000/api/v1/batch/{batch_id}"
    response = requests.get(fastapi_url)
    return jsonify(response.json()), response.status_code
```

### Implementation Details

#### Redis Queue Structure

**Batch Storage:**
```
batch:{batch_id} -> {
    "batch_id": "uuid",
    "status": "PENDING|PROCESSING|COMPLETED|FAILED",
    "total_jobs": "5",
    "completed_jobs": "2",
    "failed_jobs": "0",
    "created_at": "2024-01-01T00:00:00Z",
    "jobs": ["job_id_1", "job_id_2", ...]
}
```

**Queue List (FIFO):**
```
jobs:queue -> [job_id_1, job_id_2, job_id_3, ...]  # Redis LIST
jobs:processing -> job_id_current  # Currently processing job
```

**Job States:**
- `QUEUED` - Job is in queue, waiting to be processed
- `PROCESSING` - Job is currently being processed
- `COMPLETED` - Job completed successfully
- `FAILED` - Job failed

#### Queue Processing Flow

```python
# Pseudo-code for queue processor
async def queue_processor_loop():
    while True:
        # Check if any job is processing
        current_job = redis_manager.get_currently_processing_job()
        
        if current_job is None:
            # No job processing, get next from queue
            next_job_id = redis_manager.pop_job_from_queue()
            
            if next_job_id:
                # Mark as processing
                redis_manager.mark_job_processing(next_job_id)
                
                # Get job data
                job_data = redis_manager.get_job(next_job_id)
                
                # Process job (similar to current process_video_task)
                await process_video_task_async(
                    job_id=next_job_id,
                    video_path=job_data['video_path'],
                    subtitle_path=job_data['subtitle_path'],
                    ...
                )
                
                # Job completion handled in process_video_task_async
                # which calls redis_manager.mark_job_complete()
                # and triggers next job if in batch
            else:
                # No jobs in queue, wait
                await asyncio.sleep(1)
        else:
            # Job is processing, wait
            await asyncio.sleep(2)
```

#### Batch Status Calculation

```python
def calculate_batch_status(batch):
    """Calculate batch status from individual jobs"""
    jobs = batch['jobs']
    statuses = [job['status'] for job in jobs]
    
    if all(s == 'COMPLETED' for s in statuses):
        return 'COMPLETED'
    elif any(s == 'FAILED' for s in statuses) and not any(s == 'PROCESSING' for s in statuses):
        return 'FAILED'
    elif any(s == 'PROCESSING' or s == 'QUEUED' for s in statuses):
        return 'PROCESSING'
    else:
        return 'PENDING'
```

### Alternative Approaches Considered

**Option 1: Parallel Processing (Rejected)**
- **Approach**: Process multiple jobs simultaneously using asyncio.gather()
- **Why not chosen**: 
  - Resource intensive (memory, CPU, disk I/O)
  - Could cause system overload with large batches
  - Sequential processing is safer and more predictable

**Option 2: Celery/External Task Queue (Rejected)**
- **Approach**: Use Celery or RQ for job queue management
- **Why not chosen**:
  - Adds external dependency (Redis is already used)
  - More complex setup and configuration
  - Current Redis-based solution is simpler and sufficient

**Option 3: Keep Single-Job Flow, Add UI Multiple Selection (Rejected)**
- **Approach**: Allow multiple selection but still create jobs individually
- **Why not chosen**:
  - Doesn't solve the core problem (no queue management)
  - Jobs would still execute immediately, causing resource conflicts
  - No unified batch status tracking

### Benefits

**Improved Performance:**
- **User Time Savings**: Process multiple videos with single action instead of N separate actions
- **Efficient Resource Usage**: Sequential processing prevents system overload
- **Better Progress Visibility**: See all jobs' status at once

**Better Maintainability:**
- **Centralized Queue Management**: Single place to manage job execution
- **Reusable Components**: Queue processor can be used for other batch operations
- **Clear Separation**: Job creation vs. job execution are now separate concerns

**Reduced Complexity:**
- **Unified Batch Tracking**: One batch_id tracks all related jobs
- **Simplified UI**: Users see all progress in one place
- **Consistent State**: Redis queue ensures jobs are processed in order

**Enhanced Scalability:**
- **Future Parallel Processing**: Can extend to support parallel processing later
- **Priority Queues**: Can add priority system to queue
- **Resume Capability**: Failed jobs can be retried without recreating batch

**Enhanced Testability:**
- **Queue System is Testable**: Can test queue operations independently
- **Mock Batch Processing**: Easy to test UI with mock batch responses
- **Isolated Components**: Each component can be tested separately

### Risks & Considerations

**Breaking Changes:**
- **None**: Single-job processing (`POST /api/v1/jobs`) remains unchanged and functional
- Backward compatible: Existing UI code for single jobs still works

**Migration Path:**
- No migration needed - this is a new feature
- Existing jobs continue to work as before

**Dependencies:**
- **Redis Required**: System already uses Redis, so no new dependencies
- **Async Support**: FastAPI already supports async, so queue processor can use asyncio

**Backward Compatibility:**
- Single video processing remains unchanged
- Existing API endpoints continue to work
- UI supports both single and batch modes

**Potential Issues:**
- **Queue Processor Failure**: If queue processor crashes, jobs remain in QUEUED state
  - **Mitigation**: Add health check and auto-restart mechanism
  - **Mitigation**: Add manual "resume processing" endpoint
  
- **Memory with Large Batches**: Many queued jobs could use memory
  - **Mitigation**: Jobs are stored in Redis (not memory), only current job loads files
  - **Mitigation**: Set reasonable batch size limits (e.g., max 50 videos)
  
- **Job Timeout**: Long-running jobs could block queue
  - **Mitigation**: Add timeout mechanism for stuck jobs
  - **Mitigation**: Allow manual job cancellation

**Resource Considerations:**
- **Disk Space**: Multiple videos processing sequentially uses disk space
  - **Mitigation**: Temp files are cleaned up after each job (already implemented)
  
- **Redis Memory**: Batch data stored in Redis
  - **Mitigation**: Batch data expires after 24 hours (same as jobs)
  - **Mitigation**: Batch status is lightweight (just IDs and metadata)

## Testing Strategy

### Unit Tests

**Test Queue Operations** (`tests/unit/test_batch_queue.py`):
```python
def test_create_batch():
    """Test batch creation with multiple videos"""
    
def test_add_job_to_queue():
    """Test adding job to queue"""
    
def test_get_next_job_from_queue():
    """Test FIFO queue retrieval"""
    
def test_mark_job_processing():
    """Test marking job as processing"""
    
def test_batch_status_calculation():
    """Test batch status calculation from jobs"""
```

**Test Queue Processor** (`tests/unit/test_queue_processor.py`):
```python
def test_process_job_sequentially():
    """Test jobs are processed one at a time"""
    
def test_next_job_starts_after_completion():
    """Test next job starts when current completes"""
    
def test_failed_job_doesnt_block_queue():
    """Test queue continues after job failure"""
```

### Integration Tests

**Test Batch API Endpoints** (`tests/integration/test_batch_api.py`):
```python
async def test_create_batch_endpoint():
    """Test POST /api/v1/batch creates batch with jobs"""
    
async def test_get_batch_status():
    """Test GET /api/v1/batch/{batch_id} returns status"""
    
async def test_batch_jobs_execute_sequentially():
    """Test jobs in batch execute in order"""
```

**Test End-to-End Batch Flow** (`tests/integration/test_batch_workflow.py`):
```python
async def test_full_batch_workflow():
    """Test: Create batch → Jobs queue → Process sequentially → Complete"""
    # 1. Create batch with 3 videos
    # 2. Verify all jobs are QUEUED
    # 3. Start queue processor
    # 4. Verify jobs process one at a time
    # 5. Verify batch status updates
    # 6. Verify all jobs complete
```

### Performance Tests

**Test Queue Throughput**:
- Create batch with 10 videos
- Measure time from batch creation to all jobs complete
- Verify no resource leaks (memory, file handles)

**Test Large Batch Handling**:
- Create batch with 50 videos
- Verify queue handles large batches
- Verify Redis memory usage is reasonable

### Regression Testing

- **Single Job Processing**: Verify existing single-job flow still works
- **Job Status Endpoints**: Verify existing endpoints still work
- **Progress Modal**: Verify single-job progress modal still works

## Files Affected

### New Files
- `langflix/services/batch_queue_service.py` - Batch queue management service
- `langflix/services/queue_processor.py` - Sequential job processor worker
- `langflix/api/routes/batch.py` - FastAPI batch endpoints
- `tests/unit/test_batch_queue.py` - Unit tests for queue operations
- `tests/unit/test_queue_processor.py` - Unit tests for processor
- `tests/integration/test_batch_api.py` - Integration tests for batch API
- `tests/integration/test_batch_workflow.py` - End-to-end batch workflow tests

### Modified Files
- `langflix/core/redis_client.py` - Add batch queue methods:
  - `create_batch(batch_id, video_list, config)`
  - `get_batch_status(batch_id)`
  - `get_next_job_from_queue()`
  - `add_job_to_queue(job_id)`
  - `mark_job_processing(job_id)`
  - `get_currently_processing_job()`
  - `pop_job_from_queue()`
  
- `langflix/api/routes/jobs.py` - Add batch endpoint:
  - `POST /api/v1/batch` - Create batch (new)
  - `GET /api/v1/batch/{batch_id}` - Get batch status (new)
  - Keep existing `POST /api/v1/jobs` unchanged
  
- `langflix/api/main.py` - Start queue processor on app startup:
  - Initialize `QueueProcessor` and start background task
  
- `langflix/youtube/web_ui.py` - Add Flask proxy routes:
  - `POST /api/content/batch` - Proxy to FastAPI batch endpoint
  - `GET /api/content/batch/<batch_id>` - Get batch status
  
- `langflix/templates/video_dashboard.html` - UI changes:
  - Change radio buttons to checkboxes (line ~1188)
  - Modify `startContentCreation()` to support batch (line ~1262)
  - Add `startBatchContentCreation()` function (new)
  - Add `showBatchProgressModal(batch_id)` function (new)
  - Add batch progress UI component (new)
  - Update modal HTML to support batch mode (line ~1199)

### Documentation Updates
- `docs/api/README_eng.md` - Document batch API endpoints
- `docs/api/README_kor.md` - Document batch API endpoints (Korean)
- `docs/services/README_eng.md` - Document batch queue service
- `docs/services/README_kor.md` - Document batch queue service (Korean)

## Dependencies
- **Depends on**: None (can be implemented independently)
- **Blocks**: None
- **Related to**: 
  - TICKET-002: Uses VideoPipelineService for processing
  - TICKET-003: Uses TempFileManager for file handling

## References
- **Related Documentation**: 
  - `docs/api/README_eng.md` - Current API structure
  - `docs/services/README_eng.md` - Service architecture
- **Design Patterns**: 
  - Producer-Consumer pattern (UI creates jobs, queue processor consumes)
  - Queue pattern (FIFO job processing)
- **Redis Structures**: 
  - Redis Lists for FIFO queue
  - Redis Hashes for batch/job storage
- **External Resources**: 
  - Redis Lists: https://redis.io/docs/data-types/lists/
  - FastAPI Background Tasks: https://fastapi.tiangolo.com/tutorial/background-tasks/

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-01-30
**Decision:** ✅ APPROVED

**Strategic Rationale:**
Why this aligns with our architectural vision:
- **User Experience Improvement**: Eliminates repetitive single-video processing workflow, significantly improving productivity
- **Scalability Foundation**: Queue-based architecture provides foundation for future enhancements (parallel processing, priorities, scheduling)
- **Resource Management**: Sequential processing prevents system overload while maintaining predictable resource usage
- **Code Quality**: Centralizes job execution logic, reduces duplication between immediate and batch processing

**Implementation Phase:** Phase 2 - Sprint 2 (after TICKET-007, TICKET-008 completion)
**Sequence Order:** #8 in implementation queue
**Priority:** High (significant UX improvement)

**Architectural Guidance:**

### 1. Feature Scope Clarification

**Core Feature (Must Implement):**
- ✅ Multi-select UI (checkboxes instead of radio buttons)
- ✅ Batch creation endpoint (`POST /api/v1/batch`)
- ✅ Redis-based FIFO queue system
- ✅ Sequential queue processor (one job at a time)
- ✅ Batch progress tracking UI
- ✅ Backward compatibility (single job processing unchanged)

**Out of Scope (Future Enhancements):**
- ❌ Parallel processing (keep sequential for v1)
- ❌ Priority queues
- ❌ Batch persistence across restarts
- ❌ WebSocket real-time updates (polling is acceptable)
- ❌ Job retry mechanism

**Clarification Needed:**
- Batch vs Single Job: Users can still use existing single-job flow. Batch is optional enhancement.
- Queue Processing: Only ONE queue processor should run (avoid multiple FastAPI instances starting duplicate processors)

### 2. Redis Data Structure Design

**Batch Storage (Hash):**
```
Key: batch:{batch_id}
Hash fields:
  - batch_id: "uuid"
  - status: "PENDING|PROCESSING|COMPLETED|FAILED|PARTIALLY_FAILED"
  - total_jobs: "5"
  - completed_jobs: "2"
  - failed_jobs: "1"
  - created_at: "2024-01-01T00:00:00Z"
  - updated_at: "2024-01-01T00:05:00Z"
  - config: JSON string with batch config (language_code, etc.)
```

**Job Queue (Redis List - FIFO):**
```
Key: jobs:queue
Type: LIST
Values: [job_id_1, job_id_2, job_id_3, ...]
Operations:
  - LPUSH (add to queue)
  - RPOP (get next job)
  - LLEN (queue length)
```

**Currently Processing (String):**
```
Key: jobs:processing
Type: STRING
Value: job_id or empty
Purpose: Track which job is currently running (prevents duplicate processing)
```

**Individual Job Status (Hash - existing):**
```
Key: job:{job_id}
Hash fields: (existing RedisJobManager structure)
  - Add: batch_id (if part of batch, else null)
  - Add: queue_position (position in queue, for UI display)
```

**Implementation Notes:**
- Use `LPUSH` to add jobs to queue (FIFO order)
- Use `RPOP` to get next job (atomic operation)
- Use `SETNX jobs:processing {job_id}` to claim job (prevents duplicate processing)
- Use `DEL jobs:processing` when job completes/fails

### 3. Queue Processor Architecture

**Decision: FastAPI Lifespan Background Task** ✅

**Implementation:**
```python
# In langflix/api/main.py lifespan()
from langflix.services.queue_processor import QueueProcessor

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting queue processor...")
    queue_processor = QueueProcessor()
    processor_task = asyncio.create_task(queue_processor.start())
    
    yield
    
    # Shutdown
    logger.info("Stopping queue processor...")
    processor_task.cancel()
    try:
        await processor_task
    except asyncio.CancelledError:
        pass
```

**Key Requirements:**
- **Single Instance**: Only start processor if not already running (check Redis lock)
- **Graceful Shutdown**: Cancel processing on shutdown, mark current job as QUEUED if incomplete
- **Error Recovery**: If processor crashes, jobs remain in QUEUED state (will resume on restart)
- **Resource Management**: Use existing TempFileManager for file cleanup

**Alternative Rejected:**
- Separate daemon/service: Adds deployment complexity, FastAPI lifespan is sufficient
- Systemd supervisor: Over-engineering for current needs

### 4. Error Handling Strategy

**Decision: Continue on Failure** ✅

**Implementation:**
- If job fails: Mark as FAILED, continue processing next job
- Update batch status: Calculate `PARTIALLY_FAILED` if some jobs failed
- UI Display: Show failed jobs clearly with error message

**Error States:**
- Batch status `COMPLETED`: All jobs succeeded
- Batch status `FAILED`: All jobs failed
- Batch status `PARTIALLY_FAILED`: Some succeeded, some failed
- Batch status `PROCESSING`: At least one job still QUEUED or PROCESSING

### 5. Batch Size Limits

**Decision: Enforce Maximum** ✅

**Implementation:**
- Maximum batch size: **50 videos** (configurable via settings)
- Validation: Reject batch creation if > 50 videos
- UI Warning: Show warning if > 20 videos (processing time estimate)

**Rationale:**
- Prevents accidental large batches that consume excessive resources
- Reasonable limit for typical user workflows
- Can be increased later if needed

### 6. Server Restart Handling

**Decision: Resume Queue** ✅

**Implementation:**
- On startup: Check Redis for jobs in QUEUED state
- Resume: Queue processor automatically picks up QUEUED jobs
- Stuck Jobs: Jobs in PROCESSING state for > 1 hour are marked FAILED (timeout)

**Timeout Mechanism:**
```python
# In queue processor startup
for job_id in redis_manager.get_all_queued_jobs():
    job = redis_manager.get_job(job_id)
    if job['status'] == 'PROCESSING':
        # Check if stuck (processing > 1 hour)
        if is_job_stuck(job):
            redis_manager.update_job(job_id, {
                "status": "FAILED",
                "error": "Job timeout (server restart)"
            })
            redis_manager.remove_from_processing()
```

### 7. Progress Polling Interval

**Decision: 2-second Polling** ✅

**Rationale:**
- Acceptable for user experience
- Reduces server load compared to WebSocket
- Simple to implement
- WebSocket can be added later if needed

**Future Enhancement:**
- WebSocket support for real-time updates (not in v1 scope)

**Dependencies:**
- **Must complete first:** TICKET-007 (parallel LLM processing), TICKET-008 (multi-expression)
  - Reason: Batch processing will benefit from parallel processing performance
  - Reason: Multi-expression feature should be stable before adding batch complexity
- **Should complete first:** TICKET-012 (health checks) - Optional but recommended for monitoring
- **Blocks:** None (this is independent feature)
- **Related work:** 
  - TICKET-010: Uses RedisJobManager (already implemented)
  - TICKET-011: Uses VideoPipelineService (already implemented)

**Risk Mitigation:**

1. **Queue Processor Failure:**
   - Risk: Processor crashes, jobs stuck in QUEUED state
   - Mitigation: Health check detects processor status, auto-restart on FastAPI restart
   - Mitigation: Manual "resume processing" endpoint for recovery
   - Rollback: Disable queue processor, fall back to immediate processing

2. **Large Batch Memory Usage:**
   - Risk: Many jobs in queue consume Redis memory
   - Mitigation: Jobs stored in Redis (not memory), only current job loads files
   - Mitigation: Batch size limit (50 videos)
   - Mitigation: Batch data expires after 24 hours

3. **Job Timeout/Stuck:**
   - Risk: Long-running job blocks entire queue
   - Mitigation: Timeout detection (1 hour), mark as FAILED, continue with next job
   - Mitigation: Allow manual job cancellation via API

4. **Duplicate Processing:**
   - Risk: Multiple FastAPI instances start duplicate processors
   - Mitigation: Redis lock (`SETNX jobs:processor_lock`) prevents duplicates
   - Mitigation: Only start processor if lock acquired

**Enhanced Success Criteria:**
Beyond original ticket criteria:
- [ ] Queue processor uses Redis lock to prevent duplicates
- [ ] Stuck jobs (>1 hour) are automatically marked FAILED
- [ ] Batch size validation rejects >50 videos
- [ ] Server restart resumes QUEUED jobs automatically
- [ ] Queue processor gracefully handles shutdown
- [ ] Documentation updated in `docs/services/` and `docs/api/`

**Alternative Approaches Considered:**

1. **Original Proposal (Sequential Queue):** ✅ Selected
   - Pros: Safe, predictable, prevents resource overload
   - Cons: Slower than parallel
   - **Decision:** Keep sequential for v1, add parallel processing later

2. **Parallel Processing (Rejected for v1):**
   - Pros: Faster processing
   - Cons: Resource intensive, complex error handling
   - **Decision:** Defer to future enhancement

3. **Celery/RQ External Queue (Rejected):**
   - Pros: Mature, battle-tested
   - Cons: Additional dependency, more complex setup
   - **Decision:** Redis-based solution is sufficient and simpler

**Implementation Notes:**

**Start by:**
1. Extend `RedisJobManager` with batch queue methods (Day 1)
2. Test queue operations with unit tests
3. Create `QueueProcessor` class (Day 2)
4. Integrate with FastAPI lifespan
5. Add batch endpoints (Day 3)
6. Update UI (Day 4)

**Watch out for:**
- **Race Conditions**: Use Redis atomic operations (RPOP, SETNX) for queue management
- **Memory Leaks**: Ensure TempFileManager cleans up files after each job
- **Error Propagation**: Don't let one job failure crash the queue processor
- **Redis Connection**: Handle Redis disconnection gracefully (retry logic)

**Coordinate with:**
- Redis operations should use existing `get_redis_job_manager()` singleton
- Video processing should use existing `VideoPipelineService`
- Temp file management should use existing `TempFileManager`

**Reference:**
- `docs/services/README_eng.md` - Service architecture
- `docs/api/README_eng.md` - API structure
- `langflix/core/redis_client.py` - RedisJobManager implementation
- `langflix/services/video_pipeline_service.py` - VideoPipelineService usage

**Estimated Timeline:** 4 days (refined from original estimate)
- Day 1: Redis queue methods + BatchQueueService
- Day 2: QueueProcessor + FastAPI integration
- Day 3: Batch API endpoints + Flask proxy
- Day 4: UI changes + Testing + Documentation

**Recommended Owner:** Senior engineer (backend + frontend experience)

---

## Architect Review Questions (Original)
**For the architect to consider:**

1. **Sequential vs. Parallel Processing**: ✅ **DECISION: Sequential for v1** - Safer, predictable, prevents resource overload. Parallel processing deferred to future enhancement.

2. **Queue Processor Architecture**: ✅ **DECISION: FastAPI Lifespan Background Task** - Simple, sufficient, integrates with existing architecture. Separate daemon rejected (over-engineering).

3. **Batch Size Limits**: ✅ **DECISION: Maximum 50 videos** - Prevents resource exhaustion, reasonable for workflows. Configurable via settings.

4. **Priority Queues**: ❌ **DECISION: Out of scope** - Future enhancement, not needed for v1.

5. **Batch Persistence**: ✅ **DECISION: Resume on restart** - QUEUED jobs automatically resume. PROCESSING jobs >1 hour marked FAILED.

6. **Error Handling Strategy**: ✅ **DECISION: Continue on failure** - Failed jobs marked FAILED, batch continues. Batch status shows PARTIALLY_FAILED if some failed.

7. **Progress Polling Interval**: ✅ **DECISION: 2 seconds acceptable** - Simple, sufficient for UX. WebSocket deferred to future enhancement.

## Success Criteria

How do we know this is successfully implemented?

- [ ] **UI Functionality**:
  - [ ] Users can select multiple videos via checkboxes
  - [ ] "Create Content" button creates batch with all selected videos
  - [ ] Batch progress panel appears showing all jobs
  - [ ] Each job shows individual progress bar and status

- [ ] **Backend Functionality**:
  - [ ] `POST /api/v1/batch` creates batch with multiple jobs
  - [ ] Jobs are stored in Redis queue (not executed immediately)
  - [ ] Queue processor processes jobs sequentially
  - [ ] Next job starts automatically when current completes
  - [ ] Batch status accurately reflects all jobs' states

- [ ] **Queue Management**:
  - [ ] Only one job processes at a time
  - [ ] Jobs process in FIFO order (first added, first processed)
  - [ ] Failed jobs don't block queue (remaining jobs continue)
  - [ ] Queue processor handles empty queue gracefully

- [ ] **Progress Tracking**:
  - [ ] UI updates show real-time progress for each job
  - [ ] Batch status updates as jobs complete
  - [ ] Completed/failed jobs are clearly indicated
  - [ ] Progress persists across page refreshes (localStorage)

- [ ] **Backward Compatibility**:
  - [ ] Single video processing still works (existing flow)
  - [ ] Existing API endpoints unchanged
  - [ ] Single-job progress modal still works

- [ ] **Testing**:
  - [ ] Unit tests for queue operations pass
  - [ ] Integration tests for batch API pass
  - [ ] End-to-end batch workflow test passes
  - [ ] No regression in single-job processing

- [ ] **Documentation**:
  - [ ] API documentation updated with batch endpoints
  - [ ] Service documentation updated
  - [ ] Code comments explain queue architecture

- [ ] **Performance**:
  - [ ] Batch with 10 videos completes successfully
  - [ ] No memory leaks during batch processing
  - [ ] Redis memory usage is reasonable
  - [ ] Queue processor doesn't consume excessive CPU when idle

## Implementation Phases

### Phase 1: Backend Queue Infrastructure (Day 1-2)
- [ ] Extend RedisJobManager with batch queue methods
- [ ] Create BatchQueueService
- [ ] Implement batch creation endpoint
- [ ] Add batch status endpoint
- [ ] Write unit tests for queue operations

### Phase 2: Queue Processor (Day 2-3)
- [ ] Create QueueProcessor class
- [ ] Implement sequential job processing
- [ ] Integrate queue processor with FastAPI startup
- [ ] Handle job failures gracefully
- [ ] Write tests for queue processor

### Phase 3: UI Changes (Day 3-4)
- [ ] Change radio buttons to checkboxes
- [ ] Update content creation function for batch
- [ ] Create batch progress modal component
- [ ] Implement progress polling and updates
- [ ] Add individual job progress cards

### Phase 4: Flask Proxy & Integration (Day 4)
- [ ] Add Flask batch proxy routes
- [ ] Test end-to-end batch workflow
- [ ] Update documentation
- [ ] Performance testing with large batches
- [ ] Fix any issues discovered

## Additional Notes

### Edge Cases to Handle

1. **Empty Selection**: User clicks "Create Content" with no videos selected
   - Show alert: "Please select at least one media file"

2. **Mixed Selection**: Some videos have subtitles, some don't
   - Only allow selection of videos with subtitles (disable checkboxes for videos without subtitles)

3. **Job Failure Mid-Batch**: One job fails in middle of batch
   - Continue processing remaining jobs
   - Mark batch as "PARTIALLY_FAILED" if some jobs failed
   - Show failed jobs clearly in UI

4. **Server Restart During Batch**: Server restarts while batch is processing
   - Queue processor restarts automatically
   - Jobs in QUEUED state resume processing
   - Currently processing job may need restart (mark as FAILED if timeout)

5. **Large Batch**: User creates batch with 50+ videos
   - Limit batch size in validation (e.g., max 50)
   - Or warn user about long processing time

6. **Duplicate Videos**: User selects same video multiple times
   - Allow it (user may want to process with different settings)
   - Or deduplicate based on video_path

### Future Enhancements (Out of Scope)

1. **Parallel Processing**: Process multiple jobs simultaneously (with concurrency limit)
2. **Priority Queues**: Allow users to set job priorities
3. **Pause/Resume**: Pause batch processing and resume later
4. **Batch Templates**: Save batch configurations for reuse
5. **WebSocket Updates**: Real-time progress updates via WebSocket instead of polling
6. **Job Retry**: Retry failed jobs with one click
7. **Batch Scheduling**: Schedule batches to run at specific times

---

**Ticket Created**: [Date will be set when ticket is created]
**Ticket Type**: Feature Request / Enhancement
**Estimated Effort**: 4 days
**Complexity**: High (multi-component feature affecting UI, API, and background processing)

