# [TICKET-022] Improve Test Coverage for Scheduler and YouTube Modules

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [ ] High (Performance issues, significant tech debt)
- [x] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

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
- **Risk Reduction**: Better test coverage prevents bugs from reaching production
- **Confidence**: Developers can refactor scheduler code with confidence
- **Regression Prevention**: Tests catch regressions before deployment
- **Documentation**: Tests serve as living documentation of expected behavior

**Technical Impact:**
- **Modules Affected**: 
  - `langflix/youtube/schedule_manager.py` - Scheduler core logic
  - `langflix/youtube/video_manager.py` - Video scanning and metadata
  - `langflix/youtube/uploader.py` - Upload functionality
  - `langflix/youtube/web_ui.py` - API endpoints
- **Files to Change**: ~4-6 test files
- **Test Coverage Target**: Increase from ~60% to ~85% for YouTube modules
- **Breaking Changes**: None (tests only)

**Effort Estimate:**
- Medium (1-3 days)
  - Analyze current coverage: ~0.5 day
  - Write missing tests: ~1.5 days
  - Edge case tests: ~0.5 day
  - Integration tests: ~0.5 day

## Problem Description

### Current State

**Test Coverage Analysis:**

**Existing Tests:**
- `tests/youtube/test_schedule_manager.py` - 67 test cases (good coverage)
- `tests/youtube/test_web_ui_api.py` - Some API endpoint tests
- `tests/youtube/test_uploader.py` - Basic upload tests
- `tests/youtube/test_integration.py` - Some integration tests

**Missing Test Coverage:**

1. **Scheduler Edge Cases:**
   - Timezone handling (UTC vs local time)
   - Concurrent schedule operations (race conditions)
   - Quota exhaustion scenarios
   - Invalid time formats in preferred_times
   - Database connection failures during quota check
   - Schedule cancellation edge cases
   - Schedule update with video_id

2. **Video Manager:**
   - Redis cache invalidation
   - Video path parsing with various naming conventions
   - Language detection edge cases
   - Upload readiness validation edge cases
   - Database integration for upload status

3. **Uploader:**
   - OAuth state storage (Redis vs in-memory)
   - OAuth callback handling
   - Upload retry logic
   - Upload timeout handling
   - Metadata validation
   - publishAt parameter handling

4. **Web UI:**
   - Error handling for all endpoints
   - Authentication flow (Desktop vs Web)
   - Schedule endpoint with various scenarios
   - Video listing with filters

**Location:** Coverage gaps across multiple files

### Root Cause Analysis

1. **Test Development Pattern**: Tests were written incrementally as features were added
2. **Edge Case Neglect**: Edge cases and error scenarios not fully covered
3. **Integration Test Gaps**: Limited integration tests for end-to-end workflows
4. **Concurrency Tests Missing**: No tests for concurrent operations

### Evidence

**Coverage Analysis:**
```bash
# Current test coverage (estimated)
schedule_manager.py: ~70% coverage
video_manager.py: ~40% coverage (mostly untested)
uploader.py: ~50% coverage
web_ui.py: ~30% coverage (API endpoints partially tested)
```

**Missing Test Scenarios:**
- No tests for concurrent schedule operations
- No tests for timezone edge cases
- No tests for Redis cache behavior
- Limited tests for error recovery
- No tests for quota reservation logic (from TICKET-021)

## Proposed Solution

### Approach

1. **Coverage Analysis**
   - Use pytest-cov to identify coverage gaps
   - Create coverage report for YouTube modules
   - Prioritize critical paths and edge cases

2. **Add Missing Unit Tests**
   - Edge cases for scheduler
   - Error scenarios
   - Boundary conditions
   - Invalid input handling

3. **Add Integration Tests**
   - End-to-end schedule workflow
   - Upload with scheduling
   - Quota management across multiple requests

4. **Add Concurrency Tests**
   - Concurrent schedule requests
   - Race condition scenarios
   - Lock behavior tests

### Implementation Details

#### 1. Scheduler Edge Case Tests

```python
# tests/youtube/test_schedule_manager_edge_cases.py

class TestSchedulerEdgeCases:
    """Test scheduler edge cases and error scenarios"""
    
    def test_timezone_handling_utc(self, schedule_manager):
        """Test scheduler handles UTC timezones correctly"""
        # Create schedule with UTC timezone
        utc_time = datetime.now(timezone.utc)
        success, msg, scheduled = schedule_manager.schedule_video(
            video_path="/test/video.mp4",
            video_type="short",
            preferred_time=utc_time
        )
        assert success is True
        assert scheduled.tzinfo is not None
    
    def test_invalid_time_format_in_preferred_times(self, schedule_manager):
        """Test scheduler handles invalid time formats gracefully"""
        config = ScheduleConfig(preferred_times=['invalid', '10:00', '25:00'])
        manager = YouTubeScheduleManager(config=config)
        # Should skip invalid times and use valid ones
        slot = manager.get_next_available_slot('short')
        assert slot is not None
    
    def test_database_connection_failure_during_quota_check(self, schedule_manager):
        """Test graceful handling of database failures"""
        with patch('langflix.db.session.db_manager') as mock_db:
            mock_db.session.side_effect = OperationalError("Connection failed", None, None)
            quota = schedule_manager.check_daily_quota(date.today())
            # Should return default quota, not crash
            assert quota.final_remaining == 2
    
    def test_schedule_update_with_video_id(self, schedule_manager):
        """Test updating schedule with YouTube video ID"""
        # Create schedule
        success, _, scheduled = schedule_manager.schedule_video(
            video_path="/test/video.mp4",
            video_type="short"
        )
        assert success is True
        
        # Update with video ID
        result = schedule_manager.update_schedule_with_video_id(
            video_path="/test/video.mp4",
            youtube_video_id="test_video_id",
            status="completed"
        )
        assert result is True
    
    def test_cancel_schedule_edge_cases(self, schedule_manager):
        """Test schedule cancellation edge cases"""
        # Test canceling non-existent schedule
        result = schedule_manager.cancel_schedule("non-existent-id")
        assert result is False
        
        # Test canceling already completed schedule
        # (should fail)
        # ... implementation
```

#### 2. Video Manager Tests

```python
# tests/youtube/test_video_manager_edge_cases.py

class TestVideoManagerEdgeCases:
    """Test video manager edge cases"""
    
    def test_redis_cache_invalidation(self, video_manager):
        """Test cache invalidation after video creation"""
        # Scan videos (should cache)
        videos1 = video_manager.scan_all_videos()
        
        # Create new video file
        # ... create test video
        
        # Force refresh (should bypass cache)
        videos2 = video_manager.scan_all_videos(force_refresh=True)
        assert len(videos2) > len(videos1)
    
    def test_video_path_parsing_various_formats(self, video_manager):
        """Test parsing various video naming conventions"""
        test_cases = [
            ("long-form_Suits.S01E01.mkv", "long-form", "S01E01"),
            ("short-form_Suits.S01E01_008.mkv", "short", "S01E01"),
            ("final_expression_name.mkv", "final", None),
            ("educational_test.mkv", "educational", None),
        ]
        
        for path, expected_type, expected_episode in test_cases:
            video_type, episode, _, _ = video_manager._parse_video_path(Path(path))
            assert video_type == expected_type
            if expected_episode:
                assert episode == expected_episode
    
    def test_language_detection_edge_cases(self, video_manager):
        """Test language detection from various path structures"""
        test_cases = [
            ("output/translations/ko/video.mkv", "ko"),
            ("output/translations/japanese/video.mkv", "ja"),
            ("output/korean_video.mkv", "ko"),
            ("output/video.mkv", "unknown"),
        ]
        
        for path, expected_lang in test_cases:
            _, _, _, language = video_manager._parse_video_path(Path(path))
            assert language == expected_lang
    
    def test_upload_readiness_validation(self, video_manager):
        """Test upload readiness validation for various video types"""
        test_cases = [
            ("short", 5.0, False),  # Too short
            ("short", 30.0, True),   # Valid
            ("short", 61.0, False),  # Too long
            ("long-form", 5.0, False),  # Too short
            ("long-form", 3600.0, True),  # Valid
            ("educational", 5.0, False),  # Too short
            ("educational", 180.0, True),  # Valid
            ("educational", 301.0, False),  # Too long
        ]
        
        for video_type, duration, expected in test_cases:
            result = video_manager._is_ready_for_upload(video_type, duration)
            assert result == expected
```

#### 3. Uploader Tests

```python
# tests/youtube/test_uploader_edge_cases.py

class TestUploaderEdgeCases:
    """Test uploader edge cases"""
    
    def test_oauth_state_storage_redis(self, mock_redis):
        """Test OAuth state storage with Redis"""
        uploader = YouTubeUploader(oauth_state_storage=mock_redis)
        auth_data = uploader.get_authorization_url(
            redirect_uri="http://localhost/callback",
            email="test@example.com"
        )
        # Verify state stored in Redis
        assert mock_redis.get(f"oauth_state:{auth_data['state']}") is not None
    
    def test_upload_retry_logic(self, uploader):
        """Test upload retry on transient errors"""
        # Mock upload to fail twice, then succeed
        with patch('uploader._resumable_upload') as mock_upload:
            mock_upload.side_effect = [
                HttpError(resp=Mock(status=500), content=b'Server Error'),
                HttpError(resp=Mock(status=500), content=b'Server Error'),
                {'id': 'test_video_id'}
            ]
            result = uploader.upload_video(...)
            assert result.success is True
            assert mock_upload.call_count == 3
    
    def test_upload_timeout_handling(self, uploader):
        """Test upload timeout behavior"""
        # Mock upload to exceed timeout
        # ... implementation
    
    def test_publish_at_parameter_handling(self, uploader):
        """Test publishAt parameter in upload"""
        publish_time = datetime.now(timezone.utc) + timedelta(days=1)
        result = uploader.upload_video(
            video_path="/test/video.mp4",
            metadata=YouTubeVideoMetadata(...),
            publish_at=publish_time
        )
        # Verify publishAt was set correctly
        # ... verify in mock
```

#### 4. Concurrency Tests

```python
# tests/youtube/test_scheduler_concurrency.py

import asyncio
from concurrent.futures import ThreadPoolExecutor

class TestSchedulerConcurrency:
    """Test scheduler concurrency and race conditions"""
    
    def test_concurrent_schedule_requests(self, schedule_manager):
        """Test multiple concurrent schedule requests"""
        def schedule_video():
            return schedule_manager.schedule_video(
                video_path=f"/test/video_{threading.current_thread().name}.mp4",
                video_type="short"
            )
        
        # Create 10 concurrent schedule requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(schedule_video) for _ in range(10)]
            results = [f.result() for f in futures]
        
        # Verify all succeeded
        successful = [r for r in results if r[0] is True]
        assert len(successful) == 10
        
        # Verify quota was respected (should schedule 5 shorts max per day)
        # Check quota status
        quota = schedule_manager.check_daily_quota(date.today())
        assert quota.short_used <= 5
    
    def test_race_condition_quota_check(self, schedule_manager):
        """Test race condition in quota checking"""
        # Simulate concurrent quota checks
        # ... implementation
```

### Benefits

- **Bug Prevention**: Tests catch bugs before production
- **Refactoring Confidence**: Developers can refactor with tests as safety net
- **Documentation**: Tests document expected behavior
- **Regression Prevention**: Tests prevent regressions
- **Coverage Increase**: Target 85% coverage for YouTube modules

### Risks & Considerations

- **Test Maintenance**: More tests require more maintenance
- **Test Execution Time**: More tests increase CI/CD time
- **Flaky Tests**: Some tests may be flaky (retry logic needed)

## Testing Strategy

### Coverage Goals
- `schedule_manager.py`: 85% coverage (currently ~70%)
- `video_manager.py`: 80% coverage (currently ~40%)
- `uploader.py`: 80% coverage (currently ~50%)
- `web_ui.py`: 70% coverage (currently ~30%)

### Test Categories
1. **Unit Tests**: Individual function/method tests
2. **Integration Tests**: Multi-component workflows
3. **Concurrency Tests**: Race condition scenarios
4. **Error Tests**: Error handling and recovery

### Test Execution
```bash
# Run with coverage
pytest tests/youtube/ --cov=langflix.youtube --cov-report=html

# Run specific test categories
pytest tests/youtube/test_schedule_manager_edge_cases.py
pytest tests/youtube/test_scheduler_concurrency.py
```

## Files Affected

**New Test Files:**
- `tests/youtube/test_schedule_manager_edge_cases.py` - Scheduler edge cases
- `tests/youtube/test_video_manager_edge_cases.py` - Video manager edge cases
- `tests/youtube/test_uploader_edge_cases.py` - Uploader edge cases
- `tests/youtube/test_scheduler_concurrency.py` - Concurrency tests

**Modified Test Files:**
- `tests/youtube/test_schedule_manager.py` - Add missing scenarios
- `tests/youtube/test_web_ui_api.py` - Add error scenario tests

## Dependencies

- Depends on: TICKET-021 (scheduler race condition fixes)
- Blocks: None
- Related to: All YouTube module tickets

## References

- pytest-cov documentation: https://pytest-cov.readthedocs.io/
- Current test files: `tests/youtube/`
- Coverage report: Run `pytest --cov` to generate

## Architect Review Questions

1. What is the target coverage percentage for YouTube modules?
2. Should we prioritize unit tests or integration tests?
3. How should we handle flaky tests in CI/CD?

## Success Criteria

- [ ] Test coverage for YouTube modules reaches 80%+
- [ ] All edge cases are covered with tests
- [ ] Concurrency scenarios are tested
- [ ] Integration tests cover end-to-end workflows
- [ ] CI/CD pipeline includes coverage reporting
- [ ] No flaky tests in the test suite

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-01-30
**Decision:** ✅ APPROVED

**Strategic Rationale:**
Why this aligns with our architectural vision:
- **Quality Foundation**: Test coverage is fundamental to maintaining code quality as system grows
- **Refactoring Confidence**: Enables safe refactoring of scheduler and YouTube modules
- **Production Reliability**: Better tests prevent bugs from reaching production
- **Documentation Value**: Tests serve as living documentation of expected behavior
- **Regression Prevention**: Critical for maintaining system stability during future changes

**Implementation Phase:** Phase 1 - Sprint 1 (After TICKET-021)
**Sequence Order:** #2 in implementation queue

**Architectural Guidance:**
Key considerations for implementation:
- **Coverage Target**: 80% is reasonable target. Don't chase 100% - focus on critical paths and edge cases.
- **Test Priorities**: 
  1. Concurrency tests (race conditions from TICKET-021)
  2. Error scenarios (database failures, invalid inputs)
  3. Edge cases (timezone, boundary conditions)
  4. Integration tests (end-to-end workflows)
- **Test Organization**: Follow existing test structure (`tests/unit/`, `tests/integration/`)
- **Test Execution**: Add to CI/CD pipeline. Use pytest-cov for coverage reporting.
- **Flaky Tests**: Avoid flaky tests. Use proper mocking, avoid time-dependent tests without proper setup.

**Dependencies:**
- **Must complete first:** TICKET-021 (scheduler race condition fixes - tests need to cover the new locking behavior)
- **Should complete first:** None
- **Blocks:** None
- **Related work:** TICKET-021 (adds tests for new locking), TICKET-023 (adds tests for threshold fix)

**Risk Mitigation:**
- **Risk:** Test maintenance burden
  - **Mitigation:** Focus on stable, maintainable tests. Use fixtures and helpers to reduce duplication.
- **Risk:** Slow test execution
  - **Mitigation:** Run unit tests in parallel. Integration tests can be slower but should be clearly separated.
- **Risk:** Flaky tests
  - **Mitigation:** Proper mocking, avoid time-dependent tests, use deterministic test data.

**Enhanced Success Criteria:**
Beyond original ticket criteria:
- [ ] Concurrency tests specifically cover TICKET-021 locking behavior
- [ ] Test fixtures are reusable and well-documented
- [ ] CI/CD pipeline fails if coverage drops below 80%
- [ ] Test execution time < 2 minutes for unit tests
- [ ] Integration tests clearly separated and documented
- [ ] Coverage report generated in CI/CD artifacts

**Alternative Approaches Considered:**
- **Original proposal:** Comprehensive test coverage improvement
  - **Selected:** ✅ Balanced approach - focus on gaps, not 100% coverage
- **Alternative 1: Property-based testing**
  - **Why not chosen:** Overkill for current needs. Consider for future if needed.
- **Alternative 2: Test-driven development for new features only**
  - **Why not chosen:** Current approach is better - fill gaps in existing code first.

**Implementation Notes:**
- Start by: Running pytest-cov to identify actual coverage gaps
- Watch out for: Don't test implementation details, test behavior
- Coordinate with: Review existing test patterns in `tests/youtube/` to maintain consistency
- Reference: `tests/youtube/test_schedule_manager.py` for existing test patterns

**Estimated Timeline:** 2-3 days (refined from 1-3 days)
- Day 1: Coverage analysis, identify gaps, create test files
- Day 2: Write edge case and error scenario tests
- Day 3: Write concurrency and integration tests, add CI/CD coverage reporting

**Recommended Owner:** Engineer with testing experience (can be junior with senior review)

