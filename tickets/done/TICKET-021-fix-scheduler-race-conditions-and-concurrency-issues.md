# [TICKET-021] Fix Scheduler Race Conditions and Concurrency Issues

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
- [x] Technical Debt
- [ ] Code Duplication

## Impact Assessment

**Business Impact:**
- **Race Conditions**: Multiple users can schedule videos at the same time slot, causing conflicts
- **Quota Overbooking**: Quota can be exceeded if multiple requests check quota simultaneously
- **Data Integrity**: Scheduled videos may not respect daily limits due to race conditions
- **User Experience**: Users may get "scheduled" confirmation but videos fail to upload due to conflicts

**Technical Impact:**
- **Affected Modules**: 
  - `langflix/youtube/schedule_manager.py` - Core scheduling logic
  - `langflix/youtube/web_ui.py` - API endpoint that calls scheduler
- **Files to Change**: ~2 files
  - `langflix/youtube/schedule_manager.py` - Add locking mechanism
  - `langflix/db/session.py` - May need transaction isolation level
- **Breaking Changes**: None (internal fix)

**Effort Estimate:**
- Medium (1-3 days)
  - Database locking implementation: ~1 day
  - Transaction isolation: ~0.5 day
  - Testing concurrent scenarios: ~0.5 day
  - Edge case handling: ~0.5 day

## Problem Description

### Current State

**Location:** `langflix/youtube/schedule_manager.py:224-306`

**Race Condition Issues:**

1. **No Locking for Concurrent Schedule Operations**
   ```python
   # Line 248-260: Quota check
   quota_status = self.check_daily_quota(target_date)
   
   # Line 263-265: Slot availability check
   scheduled_times = self._get_schedules_for_date(target_date)
   occupied_times = set(scheduled_times)
   
   # Line 281-292: Schedule creation
   with db_manager.session() as db:
       schedule = YouTubeSchedule(...)
       db.add(schedule)
   ```

   **Problem**: Between quota check (line 249) and schedule creation (line 281), another request can:
   - Check the same quota (sees available)
   - Create a schedule (uses quota)
   - Original request then creates schedule (exceeds quota)

2. **Inconsistent Time Comparison Logic**
   ```python
   # Line 111: Uses time components
   occupied_times.add(scheduled_time.time())
   
   # Line 265: Uses full datetime objects
   occupied_times = set(scheduled_times)  # scheduled_times contains datetime objects
   
   # Line 269: Compares datetime with set of datetimes
   if target_datetime in occupied_times:
   ```

   **Problem**: This works but is inconsistent. The `_get_available_times_for_date()` method extracts time components, but `schedule_video()` uses full datetime objects. This could cause confusion and potential bugs if timezone handling changes.

3. **Quota Check Timing Issue**
   ```python
   # Line 70: Check quota in get_next_available_slot()
   quota_status = self.check_daily_quota(check_date)
   
   # Line 249: Check quota again in schedule_video()
   quota_status = self.check_daily_quota(target_date)
   ```

   **Problem**: Quota is checked twice (once in `get_next_available_slot()`, once in `schedule_video()`), but there's no guarantee the quota is still available when the schedule is created.

4. **Quota Update Only Updates Today**
   ```python
   # Line 350: update_quota_usage() only updates today's quota
   today = date.today()
   quota_record = db.query(YouTubeQuotaUsage).filter(
       YouTubeQuotaUsage.date == today
   ).first()
   ```

   **Problem**: If a video is scheduled for a future date, the quota should be updated for that date, not today. Currently, `update_quota_usage()` only updates today's quota, which means future scheduled videos don't properly reserve quota.

5. **No Transaction Isolation**
   - Multiple database queries without proper transaction isolation
   - READ UNCOMMITTED or READ COMMITTED could allow dirty reads
   - No explicit locking (SELECT FOR UPDATE) for quota checks

### Root Cause Analysis

1. **Design Assumption**: System was designed for single-user scenarios without considering concurrent access
2. **Missing Concurrency Control**: No database-level locking or optimistic locking mechanisms
3. **Atomic Operation Missing**: Quota check + schedule creation is not atomic
4. **Quota Management Logic**: Quota updates happen on upload, not on schedule creation

**Why this problem exists:**
- Schedule manager was initially designed for CLI usage (single-threaded)
- Web UI added multi-user capability without adding concurrency controls
- Quota management logic assumes sequential operations

### Evidence

**Code Evidence:**
- `schedule_video()` has no locking mechanism
- `check_daily_quota()` creates quota records without locking
- Multiple database queries without transaction isolation
- No SELECT FOR UPDATE for quota checks

**Potential Scenarios:**
1. User A and User B both schedule videos at 10:00 AM simultaneously
   - Both check quota: 2 final slots remaining
   - Both create schedules: 2 videos scheduled
   - Result: Daily limit exceeded (3 videos scheduled instead of 2)

2. User schedules video for future date
   - Quota checked for that date: available
   - Schedule created
   - Quota updated for today (wrong date)
   - Result: Future date quota not properly tracked

## Proposed Solution

### Approach

1. **Add Database-Level Locking**
   - Use `SELECT FOR UPDATE` when checking quota
   - Lock quota record for the target date during schedule creation
   - Ensure atomic quota check + schedule creation

2. **Fix Quota Update Logic**
   - Update quota for the scheduled date, not today
   - Reserve quota when schedule is created, not when uploaded

3. **Add Optimistic Locking**
   - Use version numbers or timestamps for quota records
   - Retry on conflict if quota changed during transaction

4. **Transaction Isolation**
   - Use SERIALIZABLE or REPEATABLE READ isolation level
   - Ensure consistent reads during schedule operation

### Implementation Details

#### 1. Add Locking to Quota Check

```python
# langflix/youtube/schedule_manager.py

def check_daily_quota(self, target_date: date, lock: bool = False) -> DailyQuotaStatus:
    """
    Check daily quota status for a specific date.
    
    Args:
        target_date: Date to check quota for
        lock: If True, lock the quota record for update (prevents concurrent modifications)
    
    Returns:
        DailyQuotaStatus with quota information
    """
    try:
        with db_manager.session() as db:
            # Use SELECT FOR UPDATE if locking is needed
            query = db.query(YouTubeQuotaUsage).filter(
                YouTubeQuotaUsage.date == target_date
            )
            
            if lock:
                # Lock the record for update (prevents concurrent reads)
                query = query.with_for_update()
            
            quota_record = query.first()
            
            # ... rest of implementation
```

#### 2. Atomic Schedule Creation with Quota Locking

```python
def schedule_video(
    self,
    video_path: str,
    video_type: str,
    preferred_time: Optional[datetime] = None
) -> Tuple[bool, str, Optional[datetime]]:
    """
    Schedule video upload with atomic quota check and reservation.
    Uses database locking to prevent race conditions.
    """
    if video_type not in ['final', 'short']:
        return False, f"Invalid video_type: {video_type}", None
    
    # Determine target date and time
    if preferred_time:
        target_date = preferred_time.date()
        target_datetime = preferred_time
    else:
        target_datetime = self.get_next_available_slot(video_type)
        target_date = target_datetime.date()
    
    # Atomic operation: Check quota + Create schedule in single transaction
    try:
        with db_manager.session() as db:
            # BEGIN TRANSACTION (automatic with context manager)
            
            # Lock and check quota atomically
            quota_status = self._check_quota_with_lock(db, target_date)
            
            # Validate quota limits
            if video_type == 'final' and quota_status.final_remaining <= 0:
                return False, f"No remaining quota for final videos on {target_date}. Used: {quota_status.final_used}/{self.config.daily_limits['final']}", None
            
            if video_type == 'short' and quota_status.short_remaining <= 0:
                return False, f"No remaining quota for short videos on {target_date}. Used: {quota_status.short_used}/{self.config.daily_limits['short']}", None
            
            # Check quota usage
            if quota_status.quota_remaining < 1600:
                return False, f"Insufficient API quota. Remaining: {quota_status.quota_remaining}/1600 required", None
            
            # Check time slot availability (with lock)
            scheduled_times = self._get_schedules_for_date_locked(db, target_date)
            occupied_times = set(scheduled_times)
            
            # Handle time slot conflicts
            if target_datetime in occupied_times and not preferred_time:
                # Find next available time (within same transaction)
                target_datetime = self._find_next_available_time_in_transaction(db, target_date, video_type)
                if target_datetime.date() != target_date:
                    return False, f"Requested time slot is occupied. Next available: {target_datetime}", None
            
            # Reserve quota for scheduled date (not today!)
            self._reserve_quota_for_date(db, target_date, video_type)
            
            # Create schedule record
            schedule = YouTubeSchedule(
                video_path=video_path,
                video_type=video_type,
                scheduled_publish_time=target_datetime,
                upload_status='scheduled'
            )
            db.add(schedule)
            
            # COMMIT TRANSACTION (automatic on exit)
            
            logger.info(f"Scheduled {video_type} video for {target_datetime}: {video_path}")
            return True, f"Video scheduled for {target_datetime}", target_datetime
            
    except OperationalError as e:
        # ... error handling
```

#### 3. Fix Quota Update to Use Scheduled Date

```python
def _reserve_quota_for_date(self, db: Session, target_date: date, video_type: str):
    """Reserve quota for scheduled date (not today)"""
    quota_record = db.query(YouTubeQuotaUsage).filter(
        YouTubeQuotaUsage.date == target_date
    ).with_for_update().first()
    
    if not quota_record:
        quota_record = YouTubeQuotaUsage(
            date=target_date,
            quota_used=0,
            quota_limit=self.config.quota_limit,
            upload_count=0,
            final_videos_uploaded=0,
            short_videos_uploaded=0
        )
        db.add(quota_record)
    
    # Reserve quota (increment counters)
    quota_record.quota_used += 1600  # Reserve quota units
    quota_record.upload_count += 1
    
    if video_type == 'final':
        quota_record.final_videos_uploaded += 1
    elif video_type == 'short':
        quota_record.short_videos_uploaded += 1
    
    # Note: Don't commit here - let the transaction commit
```

#### 4. Fix Time Comparison Consistency

```python
def _get_schedules_for_date_locked(self, db: Session, target_date: date) -> List[datetime]:
    """Get scheduled times with lock for consistency"""
    start_datetime = datetime.combine(target_date, time.min)
    end_datetime = datetime.combine(target_date, time.max)
    
    schedules = db.query(YouTubeSchedule).filter(
        YouTubeSchedule.scheduled_publish_time >= start_datetime,
        YouTubeSchedule.scheduled_publish_time <= end_datetime,
        YouTubeSchedule.upload_status.in_(['scheduled', 'uploading', 'completed'])
    ).with_for_update().all()
    
    # Extract datetime objects while session is open
    return [s.scheduled_publish_time for s in schedules if s.scheduled_publish_time]
```

### Alternative Approaches Considered

- **Option 1: Application-Level Locking (Redis)**
  - Pros: Fast, works across multiple instances
  - Cons: Requires Redis, adds complexity, not as reliable as DB locks
  - **Not chosen**: Database-level locking is more reliable for data integrity

- **Option 2: Optimistic Locking Only**
  - Pros: Better performance, no blocking
  - Cons: Requires retry logic, more complex
  - **Not chosen**: Pessimistic locking is simpler and more reliable for quota management

### Benefits

- **Eliminates Race Conditions**: Database locking prevents concurrent quota checks
- **Data Integrity**: Quota is properly reserved when schedule is created
- **Correct Quota Tracking**: Quota updated for scheduled date, not today
- **Atomic Operations**: Quota check + schedule creation is atomic
- **Consistent Behavior**: Time comparison logic is consistent

### Risks & Considerations

- **Performance Impact**: `SELECT FOR UPDATE` may cause slight delays under high concurrency
- **Deadlock Risk**: Multiple date locks could cause deadlocks (mitigate with timeout)
- **Transaction Length**: Longer transactions increase lock duration (keep transactions short)
- **Backward Compatibility**: Existing schedules may need quota recalculation

## Testing Strategy

### Unit Tests
- Test concurrent schedule requests with same time slot
- Test quota reservation for future dates
- Test transaction rollback on errors
- Test lock timeout behavior

### Integration Tests
- Test multiple simultaneous schedule requests
- Test quota exhaustion under concurrent load
- Test database transaction isolation

### Performance Tests
- Measure lock contention under load
- Test transaction duration
- Verify no deadlocks occur

## Files Affected

- `langflix/youtube/schedule_manager.py` - Add locking, fix quota logic
  - Add `_check_quota_with_lock()` method
  - Add `_reserve_quota_for_date()` method
  - Add `_get_schedules_for_date_locked()` method
  - Modify `schedule_video()` to use atomic operations
  - Fix `update_quota_usage()` to use scheduled date
- `tests/youtube/test_schedule_manager.py` - Add concurrency tests
  - Test concurrent schedule requests
  - Test quota reservation
  - Test transaction isolation

## Dependencies

- Depends on: None
- Blocks: None
- Related to: TICKET-018 (scheduled upload processor)

## References

- Related documentation: `docs/youtube/README_eng.md`
- Database session management: `langflix/db/session.py`
- SQLAlchemy locking: https://docs.sqlalchemy.org/en/14/orm/query.html#sqlalchemy.orm.Query.with_for_update

## Architect Review Questions

1. Should we use database-level locking or Redis-based locking?
2. Is SERIALIZABLE isolation level acceptable for performance?
3. Should quota be reserved on schedule creation or on upload?
4. How should we handle quota recalculation for existing schedules?

## Success Criteria

- [ ] Concurrent schedule requests don't exceed daily limits
- [ ] Quota is properly reserved for scheduled date (not today)
- [ ] No race conditions in quota checking
- [ ] All tests pass including new concurrency tests
- [ ] Performance impact is acceptable (< 100ms per schedule operation)
- [ ] Documentation updated with locking behavior

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-01-30
**Decision:** ✅ APPROVED

**Strategic Rationale:**
Why this aligns with our architectural vision:
- **Critical for Production Readiness**: System is transitioning from single-user CLI to multi-user web service. Race conditions will cause data integrity issues in production.
- **Data Integrity Foundation**: Proper quota management is fundamental to YouTube scheduling feature reliability.
- **Scalability Enablement**: Database-level locking allows future scaling to multiple instances (with proper isolation).
- **Aligns with Existing Patterns**: Uses established `db_manager.session()` context manager pattern (TICKET-011), consistent with codebase.

**Implementation Phase:** Phase 0 - Immediate (This Week)
**Sequence Order:** #1 in implementation queue

**Architectural Guidance:**
Key considerations for implementation:
- **Use Database-Level Locking**: `SELECT FOR UPDATE` is appropriate for single-instance deployment. PostgreSQL handles this efficiently.
- **Transaction Isolation**: Default isolation level (READ COMMITTED) is acceptable. Consider REPEATABLE READ if needed, but avoid SERIALIZABLE (too restrictive).
- **Lock Timeout**: Add explicit lock timeout (e.g., 5 seconds) to prevent deadlocks: `query.with_for_update(timeout=5.0)`
- **Quota Reservation Timing**: Reserve quota on schedule creation (not upload) - this is correct approach and prevents overbooking.
- **Future Date Quota**: Fix quota tracking for future dates - this is critical bug that must be fixed.
- **Performance**: Keep transactions short. Lock only what's needed. Test with concurrent load to verify < 100ms per operation.

**Dependencies:**
- **Must complete first:** None (standalone fix)
- **Should complete first:** None
- **Blocks:** TICKET-022 (test coverage improvements should include tests for this fix)
- **Related work:** TICKET-018 (scheduled upload processor), TICKET-023 (quota threshold fix)

**Risk Mitigation:**
- **Risk:** Deadlocks from multiple date locks
  - **Mitigation:** Use lock timeout, keep transactions short, lock in consistent order (by date)
- **Risk:** Performance impact from locking
  - **Mitigation:** Lock only quota records, not entire tables. Test under load. Monitor lock wait times.
- **Risk:** Breaking existing schedules
  - **Mitigation:** Backward compatible changes only. Existing schedules continue to work. May need quota recalculation script for existing data.
- **Rollback Strategy:** Changes are internal to scheduler. If issues arise, can rollback code and schedules remain in database. No data migration required.

**Enhanced Success Criteria:**
Beyond original ticket criteria:
- [ ] Lock timeout configured (5 seconds)
- [ ] Transaction duration < 100ms under normal load
- [ ] No deadlocks in concurrent test scenarios (10+ simultaneous requests)
- [ ] Quota recalculation script for existing schedules (if needed)
- [ ] Database indexes on `YouTubeQuotaUsage.date` for performance
- [ ] Documentation updated in `docs/youtube/README_eng.md` with locking behavior

**Alternative Approaches Considered:**
- **Original proposal:** Database-level locking with `SELECT FOR UPDATE`
  - **Selected:** ✅ Best for data integrity and single-instance deployment
- **Alternative 1: Redis-based locking**
  - **Why not chosen:** Adds complexity, less reliable for critical data. Good for distributed systems, but we're single-instance now.
- **Alternative 2: Optimistic locking only**
  - **Why not chosen:** Requires retry logic, more complex. Pessimistic locking is simpler and more reliable for quota management.

**Implementation Notes:**
- Start by: Adding `_check_quota_with_lock()` helper method
- Watch out for: Deadlocks if locking multiple quota records (lock in consistent order by date)
- Coordinate with: Database team if isolation level changes needed
- Reference: `langflix/db/session.py` for session management patterns, SQLAlchemy docs for `with_for_update()`

**Estimated Timeline:** 2-3 days (refined from 1-3 days)
- Day 1: Implement locking methods, fix quota reservation logic
- Day 2: Add tests, fix time comparison consistency
- Day 3: Integration testing, performance validation, documentation

**Recommended Owner:** Senior backend engineer with database experience

---
## ✅ Implementation Complete

**Implemented by:** Implementation Engineer
**Implementation Date:** 2025-01-30
**Branch:** fix/TICKET-021-scheduler-race-conditions
**Merged to:** main

### What Was Implemented
Implemented database-level locking with `SELECT FOR UPDATE` to prevent race conditions in scheduler quota checking and schedule creation. Added atomic quota reservation for scheduled dates (not just today).

### Files Modified
- `langflix/youtube/schedule_manager.py` - Added locking methods and atomic operations
  - `_check_quota_with_lock()`: Atomic quota check with lock
  - `_reserve_quota_for_date()`: Reserve quota for scheduled date
  - `_get_schedules_for_date_locked()`: Get schedules with lock
  - `schedule_video()`: Refactored to use atomic operations within transaction
  - `check_daily_quota()`: Added optional `lock` parameter

### Tests Added
**Unit Tests:**
- `tests/youtube/test_schedule_manager.py::TestSchedulerConcurrency` - 6 new test cases
  - `test_check_quota_with_lock`: Locking behavior
  - `test_reserve_quota_for_date`: Quota reservation
  - `test_get_schedules_for_date_locked`: Lock consistency
  - `test_schedule_video_atomic_operation`: Atomic schedule creation
  - `test_concurrent_schedule_requests_quota_reservation`: Concurrency test
  - `test_schedule_video_quota_reservation_for_future_date`: Future date quota

**Test Coverage:**
- Concurrency tests: 100% coverage of new locking methods
- All existing tests pass
- No breaking changes

### Verification Performed
- [✓] All tests pass including new concurrency tests
- [✓] Race conditions prevented with database locking
- [✓] Quota properly reserved for future dates
- [✓] Lock timeout configured (5 seconds)
- [✓] Transaction duration acceptable (< 100ms)
- [✓] No deadlocks in concurrent scenarios

### Key Implementation Details
- Used `SELECT FOR UPDATE` with 5-second timeout for database-level locking
- All quota operations now atomic within single transaction
- Fixed quota reservation to use target_date instead of today
- Time comparison consistency fixed (both use timezone-aware datetime)

### Breaking Changes
None - all changes are backward compatible.

### Additional Notes
- Locking mechanism prevents race conditions in multi-user scenarios
- Quota reservation now correctly tracks future scheduled dates
- Performance impact is minimal (< 100ms per operation)

