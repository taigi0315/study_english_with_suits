# ADR-008: Cursor "For Build" Mode Instructions

**Date:** 2025-10-21  
**Status:** Accepted  
**Deciders:** Development Team  

## Context

The development team needs clear instructions for using Cursor's "for build" mode effectively when working on LangFlix. This mode is particularly useful for large-scale refactoring, documentation updates, and systematic code improvements.

## Decision

We will establish comprehensive guidelines for using Cursor's "for build" mode specifically tailored to LangFlix development workflow, including service architecture transformation phases.

## Instructions for Cursor "For Build" Mode

### When to Use "For Build" Mode

**Use "For Build" mode for:**
- Large-scale documentation updates
- Systematic code refactoring
- Multi-file changes across the codebase
- Architecture decision implementation
- Legacy code cleanup
- Configuration management updates

**Do NOT use "For Build" mode for:**
- Single file bug fixes
- Simple feature additions
- Quick edits
- Experimental changes

### LangFlix-Specific Guidelines

#### 1. Documentation Updates
When updating documentation in "For Build" mode:

```markdown
# Task: Update LangFlix Documentation
## Objective: Synchronize all documentation with current codebase

## Files to Update:
- docs/USER_MANUAL.md
- docs/USER_MANUAL_KOR.md
- docs/API_REFERENCE.md
- docs/API_REFERENCE_KOR.md
- docs/TROUBLESHOOTING.md
- docs/TROUBLESHOOTING_KOR.md
- README.md

## Requirements:
1. Ensure all features are documented
2. Update examples to match current implementation
3. Maintain consistency between English and Korean versions
4. Update troubleshooting sections with latest issues
```

#### 2. Code Refactoring
When refactoring code in "For Build" mode:

```markdown
# Task: LangFlix Code Refactoring
## Objective: Improve code maintainability and structure

## Focus Areas:
- Remove deprecated code
- Consolidate duplicate functionality
- Improve error handling
- Update configuration management
- Enhance logging and debugging

## Files to Review:
- langflix/settings.py
- langflix/video_editor.py
- langflix/tts/
- langflix/config/
```

#### 3. Feature Implementation
When implementing new features in "For Build" mode:

```markdown
# Task: Implement LangFlix Feature
## Objective: Add new functionality to LangFlix

## Implementation Plan:
1. Update data models (models.py)
2. Modify core logic (video_editor.py, etc.)
3. Update configuration (default.yaml)
4. Add tests (tests/)
5. Update documentation (docs/)
6. Update API reference (API_REFERENCE.md)

## Testing Requirements:
- Unit tests for new functionality
- Integration tests for end-to-end workflow
- Documentation updates
- Backward compatibility verification
```

### LangFlix Project Structure Awareness

When working in "For Build" mode, be aware of:

```
langflix/
├── langflix/                 # Core package
│   ├── config/              # Configuration management
│   ├── tts/                 # Text-to-Speech clients
│   ├── templates/           # Prompt templates
│   └── [core modules]
├── docs/                    # Documentation
│   ├── adr/                 # Architecture Decision Records
│   ├── [user guides]
│   └── [technical docs]
├── tests/                   # Test suite
│   ├── unit/                # Unit tests
│   ├── functional/          # End-to-end tests
│   └── step_by_step/        # Workflow tests
└── assets/                  # Media files
```

### Configuration Management

When updating configuration in "For Build" mode:

1. **Update `langflix/config/default.yaml`** - Core configuration
2. **Update `langflix/settings.py`** - Configuration accessors
3. **Update `config.example.yaml`** - Example configuration
4. **Update documentation** - User guides and API reference

### Testing Requirements

For any "For Build" mode changes:

1. **Run existing tests**: `python run_tests.py all`
2. **Test new functionality**: Create appropriate test cases
3. **Verify backward compatibility**: Ensure existing workflows still work
4. **Update test documentation**: If test structure changes

### Documentation Standards

When updating documentation in "For Build" mode:

1. **Maintain dual language support**: Update both English and Korean versions
2. **Keep examples current**: Ensure all code examples work with current implementation
3. **Update troubleshooting**: Add solutions for new issues
4. **Create ADRs**: Document significant architectural decisions

### Quality Assurance

Before completing "For Build" mode work:

1. **Code review**: Ensure all changes are necessary and well-implemented
2. **Documentation review**: Verify all documentation is updated and accurate
3. **Testing**: Run full test suite and verify all functionality works
4. **Cleanup**: Remove any temporary files or debug code

## Consequences

### Positive

- **Systematic Approach**: Ensures comprehensive updates across the codebase
- **Quality Control**: Reduces risk of missing related files or documentation
- **Consistency**: Maintains consistency across all project components
- **Documentation**: Keeps documentation synchronized with code changes

### Negative

- **Time Investment**: Requires more time than quick fixes
- **Complexity**: Can be overwhelming for simple changes
- **Risk**: Higher risk of introducing errors due to scope

### Best Practices

1. **Start with planning**: Create a clear plan before beginning
2. **Work systematically**: Update related files in logical order
3. **Test frequently**: Run tests after each major change
4. **Document changes**: Update relevant documentation as you go
5. **Review thoroughly**: Double-check all changes before completion

## Examples

### Example 1: Adding New TTS Provider
```markdown
# Task: Add New TTS Provider to LangFlix
## Files to Update:
- langflix/tts/[new_provider]_client.py
- langflix/tts/factory.py
- langflix/config/default.yaml
- docs/USER_MANUAL.md
- docs/USER_MANUAL_KOR.md
- docs/API_REFERENCE.md
- docs/TROUBLESHOOTING.md
- tests/unit/test_tts_[new_provider].py
```

### Example 2: Refactoring Configuration System
```markdown
# Task: Refactor LangFlix Configuration System
## Files to Update:
- langflix/settings.py
- langflix/config/config_loader.py
- langflix/config/default.yaml
- config.example.yaml
- docs/USER_MANUAL.md (configuration section)
- docs/API_REFERENCE.md (settings functions)
- tests/unit/test_settings.py
```

## Service Architecture Development Guidelines

### Phase-Based Development

When working on service architecture transformation (Phase 0, 1a, 1b, 1c, 1d):

**Core Requirements:**
- **Backward Compatibility**: All existing CLI features must continue to work during and after changes
- **Branch Isolation**: Each phase developed in a separate Git branch (e.g., `phase-1a-db-schema`)
- **ADR-Driven Development**: Every implementation phase must have an ADR created **before** implementation begins
- **Comprehensive Testing**: All existing tests must pass; new features require new tests
- **Documentation Maintenance**: Update all affected documentation for each change

### ADR Standards for Implementation Phases

Each implementation ADR must include:

1. **Context**: Why this change is needed
2. **Decision**: What approach was chosen and why
3. **Task List**: Specific implementation tasks with checkboxes
   ```markdown
   - [ ] Task 1
   - [ ] Task 2
     - [ ] Subtask 2.1
     - [ ] Subtask 2.2
   ```
4. **Feature List**: New features being added
5. **Test Cases**: Required test scenarios to verify the implementation
   ```markdown
   - [ ] Existing tests must pass (backward compatibility)
   - [ ] New: Feature X unit tests
   - [ ] New: Feature X integration tests
   - [ ] New: End-to-end workflow test
   ```
6. **Impact Analysis**:
   - **Code files affected**: List all files that will be modified
   - **Documentation files requiring updates**: List docs to update
   - **Breaking changes**: If any (should be avoided)
   - **Migration tasks**: If data or config migration needed

### Testing Requirements for Service Components

**Test Categories:**
- **Existing Tests**: Must pass without modification (backward compatibility)
- **Test Updates**: Only modify tests if the underlying behavior intentionally changes
- **New Tests**: Required for all new features (API endpoints, new classes, new functionality)
- **Shared Functionality**: CLI and API should use the same core logic, tested together where possible
- **API-Specific Tests**: Test API-specific features (authentication, request validation, response formatting)

**Test Execution Strategy:**
```bash
# Before starting work
python run_tests.py all  # All tests must pass

# During development
python run_tests.py unit  # Run frequently
python run_tests.py integration  # After major changes

# Before committing
python run_tests.py all  # All tests must pass
python run_tests.py all --coverage  # Check coverage
```

### Branch Strategy for Service Architecture

**Branch Naming Convention:**
- `phase-0-foundation` - Foundation and planning
- `phase-1a-db-schema` - Database integration
- `phase-1b-storage-abstraction` - Storage layer
- `phase-1c-api-scaffold` - FastAPI application
- `phase-1d-background-tasks` - Async processing
- `phase-1-complete` - Integration branch before merging to main

**Branch Workflow:**
```bash
# Create phase branch from main
git checkout main
git pull
git checkout -b phase-1a-db-schema

# Work on phase, commit frequently
git add .
git commit -m "feat(db): implement Media model"

# Before merging, ensure all tests pass
python run_tests.py all

# Merge to phase-complete branch
git checkout phase-1-complete
git merge phase-1a-db-schema

# After all sub-phases complete, merge to main
git checkout main
git merge phase-1-complete
```

### Development Checklist for Each Phase

**Before Starting:**
- [ ] ADR created and reviewed
- [ ] Impact analysis completed
- [ ] Test plan documented
- [ ] Branch created from correct base

**During Development:**
- [ ] Follow ADR task list
- [ ] Run tests frequently
- [ ] Update documentation as you go
- [ ] Commit with descriptive messages

**Before Completing:**
- [ ] All ADR tasks completed
- [ ] All tests passing (existing + new)
- [ ] All documentation updated
- [ ] Code reviewed
- [ ] ADR updated with any deviations from plan

### Example: Phase 1a Database Integration

```markdown
# Task: Implement Database Integration for LangFlix
## Objective: Add PostgreSQL database to store metadata

## ADR Reference: ADR-010-database-schema-implementation.md

## Files to Modify:
- langflix/db/models.py (new)
- langflix/db/session.py (new)
- langflix/db/crud.py (new)
- langflix/main.py (update to save to DB)
- langflix/config/default.yaml (add DB config)
- requirements.txt (add PostgreSQL dependencies)

## Files to Create:
- tests/unit/test_db_models.py
- tests/unit/test_db_crud.py
- tests/integration/test_db_integration.py

## Documentation to Update:
- docs/adr/ADR-010-database-schema-implementation.md (new)
- docs/en/API_REFERENCE.md (add database models section)
- docs/ko/API_REFERENCE_KOR.md (add database models section)
- README.md (add database setup instructions)

## Testing Requirements:
- [ ] All existing CLI tests must pass
- [ ] New database connection tests
- [ ] New CRUD operation tests
- [ ] New integration test (CLI run saves to both files and DB)

## Success Criteria:
- [ ] PostgreSQL running and accessible
- [ ] SQLAlchemy models defined
- [ ] CLI saves metadata to DB after processing
- [ ] All file-based outputs still created (backward compatible)
- [ ] All tests passing
```

## References

- [Cursor Documentation](https://cursor.sh/docs)
- [LangFlix Development Diary](../development_diary.md)
- [LangFlix System Design](../system_design_and_development_plan.md)
- [ADR-009: Service Architecture Foundation](ADR-009-service-architecture-foundation.md)
