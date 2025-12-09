# [TICKET-080] Optimize Memory Usage in Video Upload Endpoint

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [x] High (Performance issues, significant tech debt)
- [ ] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [x] Refactoring
- [x] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [x] Security Issue
- [ ] Technical Debt
- [ ] Code Duplication

## Impact Assessment
**Business Impact:**
- **Risk of Crash**: Concurrent uploads of large video files can exhaust server RAM, causing the API to crash (OOM Kill).
- **Scalability**: Limits the number of concurrent users to very few.
- **Cost**: Requires larger instance sizes (RAM) than necessary.

**Technical Impact:**
- **Module**: `langflix.api.routes.jobs`
- **Files**: `langflix/api/routes/jobs.py`
- **Effort**: Small (< 1 day)

## Problem Description

### Current State
**Location:** `langflix/api/routes/jobs.py:326` and `langflix/api/routes/jobs.py:359`

The `create_job` endpoint defines `video_file` as `UploadFile` but then immediately attempts to read the *entire* content into memory using `await video_file.read()`. It then passes this massive byte object to `process_video_task` as an argument, which keeps it in referenced memory.

```python
# Current problematic code in langflix/api/routes/jobs.py
@router.post("/jobs")
async def create_job(
    video_file: UploadFile = File(...),
    # ...
):
    # ...
    # DANGEROUS: Reads entire file into RAM
    video_content = await video_file.read()
    subtitle_content = await subtitle_file.read()
    
    # ...
    
    # Passes huge bytes object to background task
    background_tasks.add_task(
        process_video_task,
        video_content=video_content,
        # ...
    )
```

And in `process_video_task`:
```python
async def process_video_task(
    # ...
    video_content: bytes,  # Keeps entire video in RAM
    # ...
):
    # ...
    with temp_manager.create_temp_file(...) as temp_video_path:
        temp_video_path.write_bytes(video_content)  # Writes to disk
```

### Root Cause Analysis
- **Development Convenience**: It is easier to pass `bytes` around than to manage file streams and temporary file lifecycles across async boundaries.
- **Pattern**: Likely started with small files where this wasn't an issue.

## Proposed Solution

### Approach
1.  **Stream to Disk Immediately**: In `create_job`, do not read into memory. Instead, stream the `UploadFile` directly to a temporary file using `shutil.copyfileobj` or `aiofiles`.
2.  **Pass Path, Not Content**: Pass the *path* of the temporary file to `process_video_task`, not the content bytes.
3.  **Lifecycle Management**: Ensure the temporary file is persisted long enough for the background task to pick it up, then cleaned up.

### Implementation Details

```python
# Proposed solution in langflix/api/routes/jobs.py

from langflix.utils.temp_file_manager import get_temp_manager
import shutil

@router.post("/jobs")
async def create_job(
    video_file: UploadFile = File(...),
    # ...
):
    temp_manager = get_temp_manager()
    
    # Create temp file immediately
    temp_video_path = temp_manager.create_persistent_temp_file(suffix=Path(video_file.filename).suffix)
    
    # Stream content to disk
    with open(temp_video_path, 'wb') as buffer:
        shutil.copyfileobj(video_file.file, buffer)
        
    # Repeat for subtitle...
    
    # Pass PATH to background task
    background_tasks.add_task(
        process_video_task,
        video_path=str(temp_video_path),
        # ...
    )

# Updated process_video_task
async def process_video_task(
    video_path: str,
    # ...
):
    try:
        # Use the file at video_path
        # ...
    finally:
        # Clean up
        if os.path.exists(video_path):
            os.remove(video_path)
```

### Benefits
- **Constant Memory Usage**: Memory usage becomes independent of video size.
- **Stability**: Server won't crash on 2GB+ uploads.
- **Speed**: Slightly faster "time to first byte" for processing, though disk I/O remains same.

## Risks & Considerations
- **Disk Space**: Need to ensure disk has enough space (TrueNAS volume should be fine).
- **Cleanup**: If the background task crashes hard or the server restarts before processing, these temp files might be orphaned. Need a cron job or startup script to clean `tmp/` or use a managed temp directory.

## Testing Strategy
- **Load Test**: upload a 2GB dummy file and monitor RAM usage.
- **Unit Test**: Test `create_job` with a mocked large file stream.

## Files Affected
- `langflix/api/routes/jobs.py`

## Success Criteria
- [ ] `create_job` no longer calls `.read()` on video files.
- [ ] `process_video_task` signature accepts `str` path instead of `bytes`.
- [ ] Uploading large files does not spike RAM.
