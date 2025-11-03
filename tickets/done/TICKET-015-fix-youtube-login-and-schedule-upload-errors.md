# [TICKET-015] Fix YouTube Login and Schedule Upload Database Connection Errors

## Priority
- [x] High (Blocking user workflows, critical functionality broken)
- [ ] Critical (System stability, security, data loss risk)
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
- **User Experience**: Users cannot log in to YouTube to authenticate their channel, blocking all YouTube upload functionality
- **Workflow Blocking**: Scheduled upload feature is completely non-functional due to database connection errors
- **Risk of NOT fixing**: Core YouTube integration features are unusable, severely limiting product value

**Technical Impact:**
- **Modules Affected:**
  - `langflix/youtube/uploader.py` - OAuth authentication flow
  - `langflix/youtube/schedule_manager.py` - Database session management for scheduling
  - `langflix/youtube/web_ui.py` - API endpoints for login and scheduling
  - `langflix/db/session.py` - Database connection handling
- **Files Needing Changes**: ~4 files
- **Breaking Changes**: None (bug fixes only)

**Effort Estimate:**
- **Medium (1-3 days)**
  - Database session management fix: ~0.5 day
  - YouTube OAuth flow debugging: ~0.5 day
  - Error handling improvements: ~0.5 day
  - Testing & validation: ~0.5 day
  - **Total: ~2 days**

## Problem Description

### Current State

**Issue 1: YouTube Login Failure**
**Location:** 
- `langflix/youtube/web_ui.py:349-368` (Login endpoint)
- `langflix/youtube/uploader.py:66-100` (Authenticate method)

**Symptoms:**
- User reports: "I can not log in youtube" when clicking login button
- Login endpoint `/api/youtube/login` returns 401 or 500 error
- OAuth flow (`run_local_server`) may fail silently or encounter port conflicts

**Root Cause:**
- OAuth flow uses `InstalledAppFlow.run_local_server(port=8080, open_browser=True)`
- May conflict with existing Flask server (port 5000) or browser blocking
- Credentials file (`youtube_credentials.json`) may be missing or invalid
- Error handling doesn't provide clear feedback to user

**Evidence:**
```python
# langflix/youtube/uploader.py:85-87
flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
# Use fixed port 8080 for consistency
creds = flow.run_local_server(port=8080, open_browser=True)
```

**Issue 2: Schedule Upload Database Connection Error**
**Location:**
- `langflix/youtube/schedule_manager.py:44-46` (Initialization)
- `langflix/youtube/web_ui.py:432-533` (Schedule endpoint)
- `langflix/youtube/web_ui.py:388-410` (Next available time endpoint)

**Symptoms:**
- Terminal error: `psycopg2.OperationalError: connection to server at "localhost" (::1), port 5432 failed: Connection refused`
- Schedule upload endpoint `/api/upload/schedule` returns 500 error
- Next available time endpoint `/api/schedule/next-available` returns 500 error
- Error: "Is the server running on that host and accepting TCP/IP connections?"

**Root Cause:**
- `YouTubeScheduleManager` initializes with `self.db_session = get_db_session()` in `__init__`
- `get_db_session()` returns a Session that may attempt connection immediately
- If PostgreSQL is not running or connection fails, exception occurs but not handled gracefully
- Session is stored as instance variable and reused, but connection may be stale or invalid
- No fallback or error handling for database unavailability

**Evidence:**
```python
# langflix/youtube/schedule_manager.py:44-46
def __init__(self, config: Optional[ScheduleConfig] = None):
    self.config = config or ScheduleConfig()
    self.db_session = get_db_session()  # Connection attempt happens here
```

```python
# Terminal log showing error:
Error getting next available time: (psycopg2.OperationalError) connection to server at "localhost" (::1), port 5432 failed: Connection refused
Error scheduling upload: (psycopg2.OperationalError) connection to server at "localhost" (::1), port 5432 failed: Connection refused
```

**Additional Issues:**
- Session management pattern inconsistent: Should use context manager `db_manager.session()` instead of storing session
- Error messages don't guide users to start PostgreSQL service
- No graceful degradation when database is unavailable

### Root Cause Analysis

**Why do these problems exist?**

1. **Database Session Pattern:**
   - `get_db_session()` is legacy method that returns raw Session
   - TICKET-011 added `db_manager.session()` context manager, but `YouTubeScheduleManager` wasn't updated
   - Session stored as instance variable creates connection immediately, not on-demand
   - Connection failures happen at initialization, not when actually needed

2. **OAuth Flow:**
   - OAuth flow is synchronous and blocking
   - No retry logic or alternative flow if browser doesn't open
   - Error handling doesn't surface specific issues (missing credentials, port conflict, etc.)

3. **Error Handling:**
   - Exceptions are caught but not user-friendly
   - No actionable error messages for users
   - No fallback modes when services unavailable

### Evidence

**Database Connection Failures:**
- Terminal logs show repeated `psycopg2.OperationalError` for port 5432
- Errors occur in:
  - `get_next_available_time()` 
  - `schedule_upload()`
  - `check_daily_quota()`

**Code Patterns:**
```python
# langflix/youtube/schedule_manager.py:118-127
def _get_schedules_for_date(self, target_date: date) -> List[YouTubeSchedule]:
    return self.db_session.query(YouTubeSchedule).filter(
        YouTubeSchedule.scheduled_publish_time >= datetime.combine(target_date, time.min),
        YouTubeSchedule.scheduled_publish_time < datetime.combine(target_date + timedelta(days=1), time.min),
        YouTubeSchedule.upload_status.in_(['scheduled', 'uploading'])
    ).all()
```
Direct query on stored session - if connection failed at init, this will fail.

## Proposed Solution

### Approach

**1. Fix Database Session Management**
- Refactor `YouTubeScheduleManager` to use context manager pattern
- Remove session from `__init__`, use `db_manager.session()` on-demand
- Add proper error handling with user-friendly messages
- Add database availability check before attempting operations

**2. Fix YouTube Login**
- Improve error handling in OAuth flow
- Add validation for credentials file existence
- Provide clearer error messages to user
- Add retry logic or alternative authentication methods

**3. Error Handling Improvements**
- Add graceful degradation when database unavailable
- Return meaningful error messages with actionable guidance
- Log detailed errors for debugging while showing user-friendly messages

### Implementation Details

**Database Session Refactoring:**

```python
# langflix/youtube/schedule_manager.py
class YouTubeScheduleManager:
    """Manages YouTube upload scheduling with daily limits"""
    
    def __init__(self, config: Optional[ScheduleConfig] = None):
        self.config = config or ScheduleConfig()
        # Remove: self.db_session = get_db_session()
        # Use db_manager.session() context manager instead
    
    def get_next_available_slot(self, video_type: str, preferred_date: Optional[date] = None) -> datetime:
        """Calculate next available upload slot"""
        try:
            from langflix.db.session import db_manager
            with db_manager.session() as db:
                # All database operations within context manager
                # ...
        except Exception as e:
            logger.error(f"Database error getting next available slot: {e}")
            # Return fallback time or raise user-friendly error
            raise ValueError(f"Unable to connect to database. Please ensure PostgreSQL is running. Error: {str(e)}")
    
    def schedule_video(self, video_path: str, video_type: str, preferred_time: Optional[datetime] = None):
        """Schedule video upload"""
        try:
            from langflix.db.session import db_manager
            with db_manager.session() as db:
                schedule = YouTubeSchedule(...)
                db.add(schedule)
                # Commit happens automatically via context manager
        except Exception as e:
            logger.error(f"Database error scheduling video: {e}")
            return False, f"Database connection failed. Please ensure PostgreSQL is running.", None
```

**YouTube Login Improvements:**

```python
# langflix/youtube/uploader.py
def authenticate(self) -> bool:
    """Authenticate with YouTube API"""
    try:
        # Validate credentials file exists
        if not os.path.exists(self.credentials_file):
            logger.error(f"Credentials file not found: {self.credentials_file}")
            raise FileNotFoundError(
                f"YouTube credentials file not found: {self.credentials_file}\n"
                "Please download OAuth2 credentials from Google Cloud Console and save as 'youtube_credentials.json'"
            )
        
        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.warning(f"Token refresh failed: {e}, starting new OAuth flow")
                    creds = None
            
            if not creds:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                try:
                    creds = flow.run_local_server(port=8080, open_browser=True)
                except OSError as e:
                    if "Address already in use" in str(e):
                        raise OSError(
                            f"Port 8080 is already in use. Please close other applications using this port.\n"
                            f"Error: {str(e)}"
                        )
                    raise
        
        # Save credentials
        with open(self.token_file, 'w') as token:
            token.write(creds.to_json())
        
        self.service = build('youtube', 'v3', credentials=creds)
        self.authenticated = True
        return True
        
    except FileNotFoundError as e:
        logger.error(f"YouTube authentication failed: {e}")
        raise
    except Exception as e:
        logger.error(f"YouTube authentication error: {e}", exc_info=True)
        raise
```

**API Endpoint Error Handling:**

```python
# langflix/youtube/web_ui.py
@self.app.route('/api/upload/schedule', methods=['POST'])
def schedule_upload():
    try:
        if not self.schedule_manager:
            return jsonify({
                "error": "Schedule manager not available",
                "hint": "Please ensure database is configured and PostgreSQL is running"
            }), 503
        
        # ... rest of logic
        
    except ValueError as e:
        # Database connection errors
        error_msg = str(e)
        if "database" in error_msg.lower() or "postgresql" in error_msg.lower():
            return jsonify({
                "error": "Database connection failed",
                "details": error_msg,
                "hint": "Please ensure PostgreSQL is running: docker-compose up -d postgres (or start your PostgreSQL service)"
            }), 503
        return jsonify({"error": error_msg}), 400
    except Exception as e:
        logger.error(f"Error scheduling upload: {e}", exc_info=True)
        return jsonify({
            "error": "Failed to schedule upload",
            "details": str(e)
        }), 500
```

### Alternative Approaches Considered

**Option 1: Lazy Database Initialization**
- Initialize session on first use instead of in `__init__`
- **Why not chosen**: Still stores session as instance variable, same pattern issues

**Option 2: Connection Pooling Only**
- Keep current pattern but add connection retry logic
- **Why not chosen**: Doesn't fix root cause of improper session management

**Option 3: Make Database Optional**
- Allow schedule manager to work without database (use Redis/JSON fallback)
- **Why not chosen**: Too much architectural change for bug fix ticket

**Selected approach**: Refactor to use context manager pattern (proper session lifecycle) + improve error messages

### Benefits

- **Fixed Functionality**: Both login and scheduling work correctly
- **Better Error Messages**: Users get actionable guidance
- **Proper Resource Management**: Database sessions properly closed
- **Consistent Patterns**: Uses same pattern as rest of codebase (TICKET-011)
- **Graceful Degradation**: Clear error messages when services unavailable

### Risks & Considerations

- **Breaking Changes**: None - bug fixes only
- **Database Migration**: None needed
- **Dependencies**: None
- **Testing Needed**: 
  - Test with PostgreSQL running
  - Test with PostgreSQL stopped (error handling)
  - Test YouTube login with/without credentials file
  - Test OAuth flow with port conflicts

## Testing Strategy

**Unit Tests:**
- `YouTubeScheduleManager` with database unavailable
- `YouTubeScheduleManager` with database available
- `YouTubeUploader.authenticate()` with missing credentials
- `YouTubeUploader.authenticate()` with invalid credentials
- Error message validation

**Integration Tests:**
- Schedule upload endpoint with database down
- Schedule upload endpoint with database up
- Login endpoint error scenarios
- Next available time endpoint error scenarios

**Manual Testing:**
- Verify login works when credentials file exists
- Verify clear error message when credentials file missing
- Verify schedule upload works when PostgreSQL running
- Verify clear error message when PostgreSQL stopped
- Test error recovery (start PostgreSQL after error)

## Files Affected

- `langflix/youtube/schedule_manager.py` - Refactor database session management
  - Remove `self.db_session` from `__init__`
  - Update all methods to use `db_manager.session()` context manager
  - Add error handling with user-friendly messages
  
- `langflix/youtube/uploader.py` - Improve OAuth error handling
  - Add credentials file validation
  - Improve error messages
  - Handle port conflicts
  
- `langflix/youtube/web_ui.py` - Improve API error handling
  - Add database connection error detection
  - Return user-friendly error messages
  - Add hints for fixing issues

- `tests/youtube/test_schedule_manager.py` - Add error scenario tests
  - Test database unavailable scenarios
  - Test error message format

## Dependencies

- Depends on: TICKET-011 (database session context manager - already implemented)
- Blocks: None
- Related to: TICKET-010 (API dependencies - may have similar patterns)

## References

- Related documentation: 
  - `docs/db/README_eng.md` - Database session management
  - `docs/archive/en/YOUTUBE_INTEGRATION.md` - YouTube integration guide
- Design patterns: Context Manager pattern for resource management
- Similar issues: 
  - TICKET-011 added `db_manager.session()` context manager
  - Database connection issues in other endpoints may need similar fixes

## Architect Review Questions

**For the architect to consider:**
1. Should we make database optional for scheduling (fallback to Redis/file)?
2. Should we add health checks before attempting database operations?
3. Is there a broader pattern of database session misuse elsewhere in codebase?
4. Should YouTube authentication support multiple auth methods (API key fallback)?
5. Do we need connection pooling configuration tuning?

## Success Criteria

How do we know this is successfully implemented?
- [ ] YouTube login works when credentials file exists
- [ ] Clear error message when credentials file missing
- [ ] Schedule upload works when PostgreSQL running
- [ ] Clear error message when PostgreSQL stopped with actionable hint
- [ ] All database sessions use context manager pattern
- [ ] No database connection leaks (sessions properly closed)
- [ ] Error messages guide users to fix issues
- [ ] Unit tests cover error scenarios
- [ ] Integration tests verify API error handling
- [ ] Code review approved

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-11-02
**Decision:** ✅ APPROVED

**Strategic Rationale:**
Why this aligns with our architectural vision:
- Fixes critical blocking issues preventing core YouTube integration functionality
- Aligns with established database session management pattern (TICKET-011)
- Improves user experience with actionable error messages
- Maintains backward compatibility (bug fixes only)
- Enables YouTube workflow which is a key product feature

**Implementation Phase:** Phase 0 - Immediate (Critical Functionality)
**Sequence Order:** #1 in implementation queue

**Architectural Guidance:**
Key considerations for implementation:
- Follow established pattern: Use `db_manager.session()` context manager (from TICKET-011)
- Check for similar database session misuse in `_save_youtube_account()` method (`web_ui.py:744`) - also uses `get_db_session()` directly
- Ensure error messages are user-friendly and include actionable hints
- Consider adding health check endpoint to verify database before scheduling operations
- Follow existing error handling patterns from FastAPI routes

**Dependencies:**
- **Must complete first:** None (blocking bug fix)
- **Should complete first:** TICKET-011 (already implemented - provides context manager)
- **Blocks:** Any future YouTube upload feature development
- **Related work:** None

**Risk Mitigation:**
- Risk: Refactoring session management might break existing functionality
  - Mitigation: Test all schedule manager methods thoroughly, verify no regressions
- Risk: OAuth flow changes might affect existing authenticated users
  - Mitigation: Ensure token refresh logic works correctly, test with existing tokens
- Risk: Database connection error handling might hide real issues
  - Mitigation: Log detailed errors for debugging, show user-friendly messages in UI
- **Rollback strategy:** Git revert if issues found, changes are isolated to 3-4 files

**Enhanced Success Criteria:**
Beyond original ticket criteria:
- [ ] `_save_youtube_account()` method also uses context manager pattern
- [ ] All YouTube-related database operations use proper session management
- [ ] Error messages tested with actual user scenarios
- [ ] Documentation updated if error messages change significantly

**Alternative Approaches Considered:**
- Original proposal: Refactor to context manager + improve error messages
- Alternative 1: Add connection retry logic only - Why not chosen: Doesn't fix root cause
- Alternative 2: Make database optional with fallback - Why not chosen: Too architectural for bug fix
- **Selected approach:** Context manager refactor + error message improvements (best balance of fix quality and scope)

**Implementation Notes:**
- Start by: Refactoring `YouTubeScheduleManager.__init__()` to remove `self.db_session`
- Watch out for: Methods that assume `self.db_session` exists (need to use context manager)
- Coordinate with: Verify `_save_youtube_account()` in same file needs similar fix
- Reference: 
  - `docs/db/README_eng.md` for session management patterns
  - `langflix/api/dependencies.py:32` for FastAPI pattern example
  - `langflix/monitoring/health_checker.py:586` for context manager usage

**Estimated Timeline:** 2 days (as estimated)
**Recommended Owner:** Backend engineer familiar with database patterns and OAuth flows

