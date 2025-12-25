# [TICKET-093] Codebase Cleanup and Optimization

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [x] High (Performance issues, significant tech debt)
- [ ] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [x] Refactoring
- [x] Performance Optimization
- [x] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [x] Technical Debt
- [x] Code Duplication

## Impact Assessment
**Business Impact:**
- **Maintainability**: Reduce technical debt and improve code maintainability
- **Test Coverage**: Address broken/archived tests to improve reliability
- **Developer Experience**: Cleaner codebase for faster feature development
- **Documentation Quality**: Ensure docs accurately reflect current implementation

**Technical Impact:**
- **Modules**: All modules (tests, core, services, documentation)
- **Files**: Multiple files across codebase
- **Effort**: Large (> 5 days, can be done incrementally)

## Problem Description

### Current State
**Comprehensive codebase review** on 2025-12-24 identified multiple areas for cleanup and optimization:

#### 1. Test Suite Issues (High Priority)
**Location:** `tests/`

- **42 test files** need attention:
  - 25 files in `tests/archive/` - review and consolidate or remove
  - 17 files in `tests/broken/` - fix or remove
- Test coverage unclear (no metrics documented)
- No CI/CD coverage checks in place

**Impact:**
- Unreliable test suite reduces confidence in deployments
- Broken tests accumulate and create noise
- Difficult to know actual test coverage

#### 2. Code Organization Issues (Medium Priority)

**Main Pipeline Complexity:**
- `langflix/main.py` is 2,135 lines (very large)
- Could be split into more granular services/modules
- Mixing orchestration with implementation details

**Subtitle Matching Logic Duplication:**
- Subtitle matching logic appears in multiple files
- Inconsistent dialogue format handling (dict vs list)
- Should standardize on dict format: `{'en': [...], 'ko': [...]}`

**Video Rendering Scattered:**
- Video rendering code scattered across `core/video/`
- Consider consolidating common patterns

#### 3. Documentation Issues (Medium Priority)

**Outdated Documentation:**
- Some docs refer to old file locations (e.g., `langflix/media/media_scanner.py` doesn't exist)
- Architecture docs reference components that may have moved
- No documentation for some service modules
- ADRs in `docs/adr/` could be better indexed

**Missing Documentation:**
- Service layer modules lack comprehensive docstrings
- No architecture diagrams (only mermaid in markdown)
- Code coverage metrics not documented
- Configuration options need better examples

#### 4. Configuration Management (Low-Medium Priority)

**Configuration Complexity:**
- `config/default.yaml` is comprehensive but could be split by domain
- Should add config validation schema
- Need better documentation for all config options with examples

#### 5. Database Schema (Low Priority)

**Schema Documentation:**
- Multiple migration versions suggest evolving schema
- Should document final schema clearly
- Consider index optimization for media/expression queries

#### 6. Dependency Management (Low Priority)

**Dependency Audit:**
- 24+ direct dependencies - audit for unused packages
- Google Cloud TTS appears legacy - consider removal if unused
- Consider `poetry` or `pipenv` for better dependency management
- Currently using basic `requirements.txt`

#### 7. API Organization (Low Priority)

**API Documentation:**
- 7 route modules could benefit from clearer documentation
- Should improve OpenAPI schema generation
- Add request/response examples to docs

### Root Cause Analysis
- **Rapid Development**: Features added quickly without time for cleanup
- **Lack of Automated Checks**: No code coverage, no broken test alerts
- **Documentation Lag**: Code evolved faster than documentation updates
- **Test Debt**: Tests archived instead of fixed/maintained

## Proposed Solution

### Phase 1: Test Suite Cleanup (Week 1)
**Estimated Effort:** 2-3 days

1. **Review Archived Tests** (`tests/archive/`)
   - [ ] Categorize tests: useful, obsolete, or needs-fixing
   - [ ] Consolidate useful tests into main test suite
   - [ ] Remove obsolete tests
   - [ ] Document decision for each test file

2. **Fix or Remove Broken Tests** (`tests/broken/`)
   - [ ] Triage each broken test
   - [ ] Fix tests that cover critical functionality
   - [ ] Remove tests for deprecated features
   - [ ] Document why each test was removed

3. **Add Test Coverage Metrics**
   - [ ] Install and configure `pytest-cov`
   - [ ] Add coverage report to `make test`
   - [ ] Document current coverage baseline
   - [ ] Set coverage target (e.g., 70% for core modules)
   - [ ] Add coverage badge to README

### Phase 2: Code Cleanup (Week 2)
**Estimated Effort:** 3-4 days

1. **Standardize Dialogue Format**
   - [ ] Audit all expression format handling
   - [ ] Standardize on dict format: `{'en': [...], 'ko': [...]}`
   - [ ] Update all matching logic to expect dict format
   - [ ] Add validation to ensure consistency

2. **Consolidate Subtitle Matching Logic**
   - [ ] Identify all subtitle matching code locations
   - [ ] Create centralized `subtitle_matcher.py` utility
   - [ ] Migrate all matching logic to centralized module
   - [ ] Add comprehensive tests for matching logic

3. **Refactor Main Pipeline** (if time permits)
   - [ ] Extract logical phases from `main.py`
   - [ ] Create separate service modules for each phase
   - [ ] Maintain backward compatibility
   - [ ] Add integration tests for refactored code

4. **Video Rendering Consolidation**
   - [ ] Audit video rendering patterns in `core/video/`
   - [ ] Extract common patterns into utilities
   - [ ] Document rendering pipeline clearly

### Phase 3: Documentation Updates (Week 2-3)
**Estimated Effort:** 2 days

1. **Update Architecture Documentation**
   - [ ] Verify all file paths in documentation
   - [ ] Update component diagrams to reflect current state
   - [ ] Add missing service layer documentation
   - [ ] Create index for ADRs with status and dates

2. **Add Missing Documentation**
   - [ ] Add docstrings to service modules
   - [ ] Document configuration options comprehensively
   - [ ] Create configuration examples for common scenarios
   - [ ] Add troubleshooting guide for common issues

3. **Update README and Guides**
   - [ ] Ensure README matches current codebase
   - [ ] Update setup guide with latest requirements
   - [ ] Add deployment guide improvements
   - [ ] Document all Makefile commands

### Phase 4: Configuration & Dependency Cleanup (Week 3)
**Estimated Effort:** 1-2 days

1. **Configuration Management**
   - [ ] Consider splitting `default.yaml` by domain (video, llm, fonts, etc.)
   - [ ] Add Pydantic validation schemas for all config sections
   - [ ] Document all configuration options in a reference guide
   - [ ] Add configuration validation tests

2. **Dependency Audit**
   - [ ] List all dependencies with usage locations
   - [ ] Identify unused dependencies
   - [ ] Check for outdated packages
   - [ ] Consider migration to `poetry` or `pipenv`
   - [ ] Update `requirements.txt` or add `pyproject.toml`

3. **Database Schema Documentation**
   - [ ] Document current schema comprehensively
   - [ ] Add ER diagram for database
   - [ ] Review and optimize indexes
   - [ ] Document migration strategy

### Phase 5: API & Miscellaneous (Ongoing)
**Estimated Effort:** 1 day

1. **API Documentation Improvements**
   - [ ] Add detailed docstrings to all API routes
   - [ ] Improve OpenAPI schema with examples
   - [ ] Add request/response examples to docs
   - [ ] Document error responses

2. **Code Quality Improvements**
   - [ ] Run linters (flake8, pylint, mypy)
   - [ ] Fix type hint issues
   - [ ] Address code smell warnings
   - [ ] Ensure consistent code style

## Implementation Plan

### Week 1: Test Suite
1. Day 1-2: Review and triage archived/broken tests
2. Day 3: Fix critical broken tests
3. Day 4: Add test coverage metrics and CI integration
4. Day 5: Document test coverage baseline

### Week 2: Code & Docs
1. Day 1-2: Standardize dialogue format and consolidate matching logic
2. Day 3: Video rendering consolidation
3. Day 4-5: Update documentation (architecture, services, guides)

### Week 3: Config & Finalization
1. Day 1: Configuration management improvements
2. Day 2: Dependency audit and cleanup
3. Day 3: Database schema documentation
4. Day 4: API documentation
5. Day 5: Final code quality pass and review

## Testing Strategy

### Test Coverage Goals
- Core modules: 70% minimum
- Service layer: 60% minimum
- API routes: 80% minimum
- Overall: 65% minimum

### Validation Steps
1. All existing tests pass after each phase
2. New tests added for refactored code
3. Coverage metrics tracked and reported
4. Integration tests verify end-to-end workflows
5. Manual testing of critical paths

## Success Criteria
- [ ] All tests in main suite passing (no broken/archived tests)
- [ ] Test coverage >= 65% overall
- [ ] Dialogue format standardized across codebase
- [ ] Subtitle matching logic centralized
- [ ] All documentation updated and accurate
- [ ] Configuration properly validated
- [ ] Unused dependencies removed
- [ ] API documentation comprehensive
- [ ] Code quality checks passing

## Risks and Mitigation

### Risk: Breaking Changes
**Mitigation:**
- Make changes incrementally
- Maintain backward compatibility where possible
- Add deprecation warnings before removing code
- Comprehensive testing after each change

### Risk: Time Overrun
**Mitigation:**
- Prioritize phases (tests > code > docs > misc)
- Can pause after any phase
- Document progress for future continuation

### Risk: New Bugs Introduced
**Mitigation:**
- Extensive testing before/after changes
- Code review for major refactorings
- Keep git history clean for easy rollback
- Test in staging before production

## Future Considerations

### Additional Cleanup (Future Tickets)
- [ ] Main pipeline refactoring (if not done in Phase 2)
- [ ] Migration to poetry for dependency management
- [ ] Add more architectural diagrams
- [ ] Performance profiling and optimization
- [ ] Security audit

### Monitoring & Maintenance
- [ ] Set up automated test coverage tracking
- [ ] Add linting to CI/CD pipeline
- [ ] Schedule quarterly dependency updates
- [ ] Regular documentation review process

## Notes
- This ticket represents a comprehensive cleanup effort
- Can be executed incrementally over multiple sprints
- Prioritize based on team availability and business needs
- Some sub-tasks can be split into separate tickets if needed

## Related Tickets
- TICKET-082: Deconstruct God Pipeline (related to main.py refactoring)
- TICKET-092: Unused Code Cleanup (related effort)

## References
- Codebase exploration: `/Users/changikchoi/Documents/langflix`
- Test directories: `tests/archive/`, `tests/broken/`
- Documentation: `docs/`
- Configuration: `langflix/config/default.yaml`

---

**Created:** 2025-12-24
**Status:** Backlog
**Assignee:** TBD
**Labels:** `refactoring`, `technical-debt`, `testing`, `documentation`, `cleanup`
