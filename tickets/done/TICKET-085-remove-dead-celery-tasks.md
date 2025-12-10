# [TICKET-085] Remove Dead Code: Celery Tasks and Mocks

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [ ] High (Performance issues, significant tech debt)
- [x] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [ ] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [x] Technical Debt
- [ ] Code Duplication

## Impact Assessment
**Business Impact:**
- Zero direct business impact, but improves developer experience by removing confusing/misleading code.

**Technical Impact:**
- Removes `langflix/tasks/tasks.py`.
- Removes any lingering references to Celery which is not a project dependency.
- Risk is Low (verified via `grep` and `requirements.txt`).

**Effort Estimate:**
- [x] Small (< 1 day)
- Medium (1-3 days)
- Large (> 3 days)

## Problem Description

### Current State
**Location:** `langflix/tasks/tasks.py`

The file contains mock implementations of Celery tasks using `time.sleep` and `TODO` comments.
Celery is **not** listed in `requirements.txt`, meaning this code cannot run and is likely dead/legacy.

```python
# langflix/tasks/tasks.py
@celery_app.task(bind=True)
def process_video_content(self, video_path: str, output_dir: str):
    # ...
    # TODO: Implement actual video processing
    # ...
    # Simulate processing
    import time
    for i in range(1, 11):
        time.sleep(1) 
```

### Root Cause Analysis
- Likely an early architectural experiment with Celery that was abandoned in favor of FastAPI BackgroundTasks or another mechanism (like `jobs.py`).

### Evidence
- `requirements.txt` does not include `celery`.
- Code contains "Simulate processing" logic.
- TODOs indicate "Implement actual..." which implies it's never been used.

## Proposed Solution

### Approach
1.  Delete `langflix/tasks/tasks.py`.
2.  Delete `langflix/tasks/celery_app.py` (if exists and unused).
3.  Remove references in `docker-compose.dev.yml` if present (saw a grep match).
4.  Remove `langflix/tasks` directory if empty.

### Implementation Details
```bash
rm langflix/tasks/tasks.py
rm -rf langflix/tasks/
```

### Benefits
- **Reduced complexity:** Less noise in the codebase.
- **Better maintainability:** No confusion about which task queue is being used.

### Risks & Considerations
- Verify `docker-compose.dev.yml` doesn't try to start a celery worker (which would fail anyway).

## Testing Strategy
- Search code for imports of `langflix.tasks`.
- Verify application startup.

## Files Affected
- `langflix/tasks/tasks.py` (Delete)
- `docker-compose.dev.yml` (Update)

## Dependencies
- None.

## References
- None.
