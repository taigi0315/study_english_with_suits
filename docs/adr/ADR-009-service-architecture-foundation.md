# ADR-009: Service Architecture Foundation

**Date:** 2025-10-21  
**Status:** Accepted  
**Deciders:** Development Team  
**Related ADRs:** ADR-008 (Cursor Build Mode Instructions)

## Context

LangFlix has successfully built a powerful CLI-based content generation engine. The next evolution is to transform it from a tool into a platform - a web-based SaaS that anyone can use. This requires a fundamental architectural transformation while maintaining all existing CLI functionality.

### Current State
- CLI-only application
- Local file system for all storage
- Direct execution model (synchronous)
- No database (file-based output only)
- Single-user, local usage

### Desired State
- Dual-mode: CLI for development, API for production
- Cloud storage support (Google Cloud Storage)
- Asynchronous processing with job tracking
- Database for metadata and structured data
- Multi-user, web-accessible platform

## Decision

We will transform LangFlix using a phased approach that:

1. **Maintains Backward Compatibility**: CLI functionality remains unchanged
2. **Adds Service Layer Gradually**: New components added without disrupting existing code
3. **Uses Branch Isolation**: Each phase in separate Git branches
4. **Follows ADR-Driven Development**: Every phase documented before implementation
5. **Requires Comprehensive Testing**: All tests must pass at every stage

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         LangFlix                             │
├─────────────────────────┬───────────────────────────────────┤
│      CLI Mode           │         API Mode                  │
│  (Local Development)    │    (Production Service)           │
├─────────────────────────┼───────────────────────────────────┤
│  - Local File System    │  - Google Cloud Storage           │
│  - Optional Database    │  - Database Required              │
│  - Synchronous          │  - Asynchronous (Background Tasks)│
│  - Single User          │  - Multi-user                     │
└─────────────┬───────────┴───────────────┬───────────────────┘
              │                           │
              └───────────┬───────────────┘
                          │
                ┌─────────▼─────────┐
                │  Core Pipeline    │
                │  (Shared Logic)   │
                │  - VideoProcessor │
                │  - ExpressionAnalyzer │
                │  - VideoEditor    │
                └───────────────────┘
```

### Phase Breakdown

**Phase 0: Foundation & Planning**
- Create architectural documentation
- Design database schema
- Design storage abstraction layer
- Update development guidelines

**Phase 1a: Database Integration**
- PostgreSQL + SQLAlchemy + Alembic
- Store metadata alongside files
- CLI optionally uses DB

**Phase 1b: Storage Abstraction**
- Abstract storage interface
- LocalStorage backend (CLI default)
- GoogleCloudStorage backend (API default)

**Phase 1c: FastAPI Application**
- API structure and endpoints
- Request/response models
- OpenAPI documentation

**Phase 1d: Background Tasks**
- Async processing with FastAPI BackgroundTasks
- Job status tracking
- Integration of all components

## CLI vs API Separation Strategy

### CLI Mode (Development & Local Use)
- **Storage**: Local file system (default)
- **Database**: Optional (can be enabled for testing)
- **Processing**: Synchronous execution
- **Output**: Files in `output/` directory
- **Use Case**: Development, testing, single-user local processing

### API Mode (Production Service)
- **Storage**: Google Cloud Storage (required)
- **Database**: PostgreSQL (required)
- **Processing**: Asynchronous background tasks
- **Output**: URLs to cloud-stored files
- **Use Case**: Multi-user web service, production deployment

### Shared Components
Both modes use the same:
- `LangFlixPipeline` core logic
- `VideoProcessor` for video operations
- `ExpressionAnalyzer` for LLM processing
- `VideoEditor` for video editing
- All configuration management

## Storage Abstraction Layer Design

### Abstract Interface: `StorageBackend`

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    def save_file(self, local_path: Path, remote_path: str) -> str:
        """
        Save file to storage.
        
        Args:
            local_path: Path to local file
            remote_path: Destination path in storage
            
        Returns:
            URL or path to stored file
        """
        pass
    
    @abstractmethod
    def load_file(self, remote_path: str, local_path: Path) -> bool:
        """
        Load file from storage to local filesystem.
        
        Args:
            remote_path: Path in storage
            local_path: Destination local path
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def delete_file(self, remote_path: str) -> bool:
        """Delete file from storage."""
        pass
    
    @abstractmethod
    def list_files(self, prefix: str) -> List[str]:
        """List files with given prefix."""
        pass
    
    @abstractmethod
    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists in storage."""
        pass
```

### LocalStorage Implementation
- Uses local filesystem (current behavior)
- `save_file()` copies to output directory
- `load_file()` copies from output directory
- Returns local file paths

### GoogleCloudStorage Implementation
- Uses GCS Python client
- `save_file()` uploads to GCS bucket
- `load_file()` downloads from GCS bucket
- Returns GCS URLs

## Database Usage Guidelines

### What Goes in the Database

**DO Store:**
- **Metadata**: Show names, episode info, file references, timestamps
- **ExpressionAnalysis Data**: Structured LLM output (expressions, translations, similar expressions)
- **Job Tracking**: Processing status, progress, error messages
- **User Data** (Future): User accounts, preferences, saved decks

**DO NOT Store:**
- **Binary Files**: Videos, audio, images (use storage backend)
- **Large Text**: Subtitle files, prompt templates (use storage backend)
- **Temporary Data**: Processing intermediate files (use temp directory)

### Database Schema (Conceptual)

**Media Table**
- `id` (UUID, primary key)
- `show_name` (string)
- `episode_name` (string)
- `subtitle_file_path` (string, reference to storage)
- `video_file_path` (string, reference to storage)
- `language_code` (string)
- `created_at` (timestamp)
- `updated_at` (timestamp)

**Expression Table**
- `id` (UUID, primary key)
- `media_id` (UUID, foreign key to Media)
- `expression` (string)
- `expression_translation` (string)
- `expression_dialogue` (text)
- `expression_dialogue_translation` (text)
- `similar_expressions` (JSON array)
- `context_start_time` (string)
- `context_end_time` (string)
- `scene_type` (string)
- `context_video_path` (string, reference to storage)
- `slide_video_path` (string, reference to storage)
- `created_at` (timestamp)

**ProcessingJob Table**
- `id` (UUID, primary key)
- `media_id` (UUID, foreign key to Media)
- `status` (enum: PENDING, PROCESSING, COMPLETED, FAILED)
- `progress` (integer, 0-100)
- `error_message` (text, nullable)
- `started_at` (timestamp, nullable)
- `completed_at` (timestamp, nullable)
- `created_at` (timestamp)

## Phase Dependencies

```
Phase 0 (Foundation)
    │
    ├─> Phase 1a (Database)
    │       │
    │       └─> Phase 1c (API Scaffold)
    │               │
    └─> Phase 1b (Storage)  ──┘
            │
            └─> Phase 1d (Background Tasks)
                    │
                    └─> Phase 1 Complete
```

**Dependency Rules:**
- Phase 1c requires both 1a and 1b to be complete
- Phase 1d requires 1c to be complete
- All phases require Phase 0 documentation

## Migration Strategy

### File-based to Database Migration

**Approach: Parallel Operation**
1. Add database writes alongside file writes
2. Keep both systems running
3. No immediate deprecation of files
4. Future phases may deprecate file-only mode for API

**Benefits:**
- Zero disruption to existing workflows
- Gradual adoption of database
- Easy rollback if issues arise
- Testing both systems simultaneously

### Timeline
- **Phase 1a**: Add DB writes, keep all file outputs
- **Phase 1b-1d**: Both systems operational
- **Phase 2+**: API uses DB primarily, files for legacy support
- **Future**: Potential deprecation of file-only mode (TBD)

## Development Guidelines

### Branch Naming Convention
- `phase-0-foundation` - Foundation and planning
- `phase-1a-db-schema` - Database integration
- `phase-1b-storage-abstraction` - Storage layer
- `phase-1c-api-scaffold` - FastAPI application
- `phase-1d-background-tasks` - Async processing
- `phase-1-complete` - Integration branch

### ADR Requirements for Each Phase

Every implementation phase must have an ADR that includes:

1. **Context**: Why is this change needed?
2. **Decision**: What approach was chosen and why?
3. **Task List**: Specific implementation tasks with checkboxes
4. **Feature List**: New features being added
5. **Test Cases**: Required test scenarios
6. **Impact Analysis**:
   - Code files affected
   - Documentation files requiring updates
   - Breaking changes (if any)
   - Migration tasks (if needed)

### Testing Requirements

**For Each Phase:**
- All existing tests must pass (backward compatibility)
- New tests required for new features
- Integration tests for CLI and API where applicable
- Performance benchmarks for critical paths

**Test Categories:**
- Unit tests: Individual components
- Integration tests: Component interactions
- End-to-end tests: Full workflows (CLI and API)
- API-specific tests: Request/response validation

## Consequences

### Positive

- **Backward Compatibility**: CLI users unaffected
- **Gradual Transformation**: Reduced risk, easier to manage
- **Flexible Architecture**: Support multiple use cases
- **Scalability**: Foundation for multi-user platform
- **Testability**: All changes thoroughly tested
- **Documentation**: Comprehensive ADR trail

### Negative

- **Complexity**: Maintaining two modes (CLI and API)
- **Duplication**: Some configuration and setup duplicated
- **Development Time**: Phased approach takes longer
- **Resource Requirements**: Need PostgreSQL and GCS for full testing

### Risks and Mitigations

**Risk: Breaking Existing Functionality**
- Mitigation: Comprehensive test suite, backward compatibility requirement

**Risk: Scope Creep**
- Mitigation: Strict phase boundaries, ADR-driven development

**Risk: Performance Degradation**
- Mitigation: Performance benchmarks at each phase

**Risk: Complex Codebase**
- Mitigation: Clear abstraction layers, comprehensive documentation

## Success Criteria

### Phase 0 Complete When:
- [ ] This ADR approved and merged
- [ ] ADR-008 updated with service guidelines
- [ ] Database schema designed and documented
- [ ] Storage abstraction interface designed
- [ ] All team members understand the plan

### Phase 1 Complete When:
- [ ] Database integration working (1a)
- [ ] Storage abstraction working (1b)
- [ ] FastAPI application running (1c)
- [ ] Background tasks processing videos (1d)
- [ ] All tests passing (CLI + API)
- [ ] All documentation updated
- [ ] CLI functionality unchanged and working

## References

- [Next Steps & Final Form: Strategic Vision](../Next%20Steps%20&%20Final%20Form:%20A%20Strategic%20Vision%20for%20LangFlix.md)
- [ADR-008: Cursor Build Mode Instructions](ADR-008-cursor-build-mode-instructions.md)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://www.sqlalchemy.org/)
- [Google Cloud Storage Python Client](https://cloud.google.com/storage/docs/reference/libraries#client-libraries-install-python)

## Next Steps

1. Get this ADR approved
2. Create `phase-0-foundation` branch
3. Update ADR-008 with service development guidelines
4. Design detailed database schema
5. Create storage abstraction interface
6. Begin Phase 1a implementation
