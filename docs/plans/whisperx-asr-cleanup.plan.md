<!-- b37d986b-c4cc-4e56-9261-1aed299348a9 5bd2ce04-151f-4c21-888d-57bfa67a6e0a -->
# Progress Bar Issue Analysis & Fix Plan

## Current Problem Summary

**What Users See:**

1. Click "Create Content" button
2. Modal dialog appears saying "Creating..." but stays at 0%
3. Modal blocks the entire page - can't interact with anything else
4. Modal doesn't close even when job finishes

**Root Causes:**

### Problem 1: Browser Cache

- Flask debug mode with auto-reload is running
- Template was updated to show bottom progress bar instead of modal
- Browser is still showing OLD cached version with the blocking modal
- Need hard refresh to see new template

### Problem 2: Status Field Case Mismatch

**File:** `templates/video_dashboard.html` lines 1318, 1327, 1333

Frontend checks for:

```javascript
if (job.status === 'completed')  // lowercase
if (job.status === 'failed')     // lowercase
```

But FastAPI returns:

```javascript
{ status: "PROCESSING" }  // uppercase
{ status: "COMPLETED" }   // uppercase
{ status: "FAILED" }      // uppercase
```

Result: Progress bar never recognizes job completion, stays stuck forever

### Problem 3: Missing current_step Field

**File:** `langflix/api/routes/jobs.py`

FastAPI updates progress like this:

```python
jobs_db[job_id]["progress"] = 10  # Line 49
jobs_db[job_id]["progress"] = 20  # Line 65
jobs_db[job_id]["progress"] = 30  # Line 78
```

But it NEVER sets `current_step`:

```python
jobs_db[job_id]["current_step"] = "Parsing subtitles..."  # MISSING
```

Frontend expects both fields:

```javascript
document.getElementById('progressText').textContent = job.current_step;
```

Result: Progress bar shows "undefined" or blank text for current step

## Current Architecture

```
┌─────────────────────────────────────────────────────────┐
│  User Browser (localhost:5000)                          │
│  ├─ Video Dashboard (Flask template)                    │
│  └─ JavaScript polling every 1 second                   │
└──────────────────┬──────────────────────────────────────┘
                   │
                   │ 1. POST /api/content/create
                   ↓
┌─────────────────────────────────────────────────────────┐
│  Flask Frontend (port 5000)                             │
│  ├─ Receives: media_id, video_path, language, level    │
│  ├─ Opens video/subtitle files                         │
│  └─ Forwards to FastAPI →                              │
└──────────────────┬──────────────────────────────────────┘
                   │
                   │ 2. POST multipart/form-data
                   │    with actual video/subtitle files
                   ↓
┌─────────────────────────────────────────────────────────┐
│  FastAPI Backend (port 8000)                            │
│  ├─ /api/v1/jobs endpoint                              │
│  ├─ Creates job_id                                      │
│  ├─ Stores in jobs_db dict:                            │
│  │   { job_id: { status, progress, ... } }            │
│  └─ Launches BackgroundTasks.add_task()                │
│      └─ process_video_task() runs async               │
│          ├─ Saves files to /tmp                        │
│          ├─ Runs LangFlix pipeline                     │
│          └─ Updates jobs_db[job_id] progress          │
└──────────────────┬──────────────────────────────────────┘
                   │
                   │ 3. GET /api/content/jobs/{job_id}
                   │    (polling every 1 second)
                   ↓
┌─────────────────────────────────────────────────────────┐
│  Flask Frontend                                         │
│  ├─ Checks local job_queue (empty)                     │
│  └─ Falls back to FastAPI: GET /api/v1/jobs/{job_id}   │
└──────────────────┬──────────────────────────────────────┘
                   │
                   │ 4. Returns job status
                   ↓
┌─────────────────────────────────────────────────────────┐
│  Browser updates progress bar                           │
└─────────────────────────────────────────────────────────┘
```

### Architecture Issues

**Unnecessary Complexity:**

- Files uploaded from browser → Flask → FastAPI (double transfer)
- Job status polled: Browser → Flask → FastAPI → Flask → Browser
- Flask has unused `job_queue` (JobQueue class) that never stores anything
- FastAPI has separate `jobs_db` dict that actually stores jobs
- Extra network hop adds latency

**What's Missing for "Phase 7 Complete Architecture":**

- Redis for shared job state (currently unused)
- Celery for distributed task queue (workers created but jobs don't use it)
- Database persistence for jobs (SQLAlchemy models exist but not used for jobs)
- Proper WebSocket for real-time updates (currently polling)

**Is Phase 7 Architecture Necessary?**

For current usage (single user, local development): **NO**

- Simple in-process job queue would work fine
- No need for Redis/Celery complexity
- Current architecture is over-engineered

For production/scale: **YES**

- Multiple users creating content simultaneously
- Jobs need to survive server restarts (DB persistence)
- Distributed processing across multiple workers
- Real-time progress updates via WebSocket

**Current Recommendation:** Keep Phase 7 architecture but mark as "incomplete". Don't roll back, as foundation is useful for future scaling.

## Implementation Plan

### Fix 1: Status Field Case Matching

**File:** `templates/video_dashboard.html`

Change lines 1318, 1327, 1333 from:

```javascript
if (job.status === 'completed')
if (job.status === 'failed')  
if (job.status === 'cancelled')
```

To:

```javascript
if (job.status === 'COMPLETED' || job.status === 'completed')
if (job.status === 'FAILED' || job.status === 'failed')
if (job.status === 'CANCELLED' || job.status === 'cancelled')
```

### Fix 2: Add current_step Updates

**File:** `langflix/api/routes/jobs.py`

Add after each progress update:

```python
jobs_db[job_id]["progress"] = 10
jobs_db[job_id]["current_step"] = "Initializing..."  # ADD THIS

jobs_db[job_id]["progress"] = 20
jobs_db[job_id]["current_step"] = "Parsing subtitles..."  # ADD THIS

jobs_db[job_id]["progress"] = 30
jobs_db[job_id]["current_step"] = "Analyzing expressions..."  # ADD THIS
```

Approximately 8-10 locations throughout the file need this.

### Fix 3: Ensure Template is Loaded

- Restart Flask app cleanly (kill all processes, start fresh)
- Hard refresh browser (Cmd+Shift+R on Mac, Ctrl+Shift+R on Windows)
- Verify progress bar appears at bottom, not as modal

## Testing Steps

1. **Verify Services Running**

   - Flask on port 5000: `curl http://localhost:5000`
   - FastAPI on port 8000: `curl http://localhost:8000/api/v1/jobs`

2. **Test Progress Bar UI**

   - Open http://localhost:5000
   - Hard refresh (Cmd+Shift+R)
   - Click "Create Content"
   - Select: Suits S01E02, Japanese, Beginner
   - Click "Create Content" button
   - **Expected:** Modal closes, bottom progress bar appears

3. **Verify Progress Updates**

   - Watch progress bar for 30 seconds
   - **Expected:** Progress increases (10% → 30% → 50%)
   - **Expected:** Text shows: "Parsing subtitles...", "Analyzing expressions...", etc.

4. **Verify Non-Blocking**

   - While job runs, scroll video list
   - Click other videos
   - **Expected:** All interactions work

5. **Verify Completion**

   - Wait for job to complete (~2-5 minutes)
   - **Expected:** Progress bar shows "Completed successfully!"
   - **Expected:** "Cancel" button changes to "Close"
   - Click "Close"
   - **Expected:** Progress bar disappears

## Files to Modify

1. `templates/video_dashboard.html` - Fix status matching (3 lines)
2. `langflix/api/routes/jobs.py` - Add current_step updates (8-10 locations)

## Time Estimate

- Modifications: 10 minutes
- Testing: 10 minutes  
- **Total: 20 minutes**

### To-dos

- [ ] Create new git branch cleanup/remove-whisperx-asr
- [ ] Delete langflix/asr/ directory (5 files)
- [ ] Delete 5 ASR-related test files
- [ ] Delete docs/adr/ADR-015-whisperx-integration.md
- [ ] Clean requirements.txt and requirements-dev.txt
- [ ] Remove whisper section from langflix/config/default.yaml
- [ ] Remove get_expression_whisper() from langflix/settings.py
- [ ] Update code files with ASR/WhisperX references
- [ ] Remove WhisperX mentions from documentation files
- [ ] Verify no remaining whisperx/asr references with grep