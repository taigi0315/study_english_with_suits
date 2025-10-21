# ADR-010: Database Schema Design

**Date:** 2025-10-21  
**Status:** Draft  
**Deciders:** Development Team  
**Related ADRs:** ADR-009 (Service Architecture Foundation)

## Context

LangFlix needs a database to store metadata, structured data, and job tracking information for the service architecture transformation. The database will work alongside the existing file-based system, not replace it.

## Decision

We will design a PostgreSQL database schema that stores metadata and structured data while keeping binary files (videos, audio, images) in the storage backend.

## Database Schema Design

### Core Principles

1. **Metadata Only**: Store structured data, not binary files
2. **Backward Compatibility**: File-based outputs continue to work
3. **Job Tracking**: Track processing status and progress
4. **Future-Ready**: Support for user accounts and saved content

### Entity Relationship Diagram

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Media       │    │   Expression    │    │ ProcessingJob   │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ id (UUID)       │◄───┤ id (UUID)       │    │ id (UUID)       │
│ show_name       │    │ media_id (FK)   │    │ media_id (FK)   │
│ episode_name    │    │ expression      │    │ status          │
│ language_code   │    │ translation     │    │ progress        │
│ subtitle_path   │    │ dialogue        │    │ error_message   │
│ video_path      │    │ dialogue_trans  │    │ started_at      │
│ created_at      │    │ similar_exprs   │    │ completed_at    │
│ updated_at      │    │ context_start   │    │ created_at      │
└─────────────────┘    │ context_end     │    └─────────────────┘
                       │ scene_type      │
                       │ context_video   │
                       │ slide_video     │
                       │ created_at      │
                       └─────────────────┘
```

### Table Definitions

#### Media Table
Stores information about processed episodes/shows.

```sql
CREATE TABLE media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    show_name VARCHAR(255) NOT NULL,
    episode_name VARCHAR(255) NOT NULL,
    language_code VARCHAR(10) NOT NULL,
    subtitle_file_path TEXT,  -- Reference to storage backend
    video_file_path TEXT,    -- Reference to storage backend
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_media_show_episode ON media(show_name, episode_name);
CREATE INDEX idx_media_language ON media(language_code);
```

#### Expression Table
Stores individual expressions and their analysis data.

```sql
CREATE TABLE expressions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    media_id UUID NOT NULL REFERENCES media(id) ON DELETE CASCADE,
    expression TEXT NOT NULL,
    expression_translation TEXT,
    expression_dialogue TEXT,
    expression_dialogue_translation TEXT,
    similar_expressions JSONB,  -- Array of similar expressions
    context_start_time VARCHAR(20),  -- e.g., "00:01:23,456"
    context_end_time VARCHAR(20),    -- e.g., "00:01:25,789"
    scene_type VARCHAR(50),          -- e.g., "dialogue", "action"
    context_video_path TEXT,         -- Reference to storage backend
    slide_video_path TEXT,          -- Reference to storage backend
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_expressions_media ON expressions(media_id);
CREATE INDEX idx_expressions_text ON expressions USING gin(to_tsvector('english', expression));
CREATE INDEX idx_expressions_similar ON expressions USING gin(similar_expressions);
```

#### ProcessingJob Table
Tracks asynchronous processing jobs.

```sql
CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    media_id UUID NOT NULL REFERENCES media(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',  -- PENDING, PROCESSING, COMPLETED, FAILED
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_jobs_status ON processing_jobs(status);
CREATE INDEX idx_jobs_media ON processing_jobs(media_id);
CREATE INDEX idx_jobs_created ON processing_jobs(created_at);
```

### Data Types and Constraints

#### Status Enums
```sql
-- ProcessingJob status values
CREATE TYPE job_status AS ENUM (
    'PENDING',     -- Job created, not started
    'PROCESSING',  -- Currently processing
    'COMPLETED',   -- Successfully finished
    'FAILED'       -- Encountered error
);
```

#### JSONB Usage
- `similar_expressions`: Array of strings
  ```json
  ["get screwed", "be in trouble", "face consequences"]
  ```

#### File Path References
- All file paths are TEXT fields that reference storage backend
- Format: `{storage_backend}://{bucket}/{path}`
- Examples:
  - `local://output/Suits/S01E01/subtitles.srt`
  - `gcs://langflix-bucket/Suits/S01E01/context_video.mkv`

### Indexing Strategy

#### Primary Indexes
- **Primary Keys**: UUID with default `gen_random_uuid()`
- **Foreign Keys**: All FK relationships indexed
- **Timestamps**: Created/updated timestamps for querying

#### Search Indexes
- **Text Search**: GIN index on expression text for full-text search
- **JSON Search**: GIN index on similar_expressions for array queries
- **Composite Indexes**: Show + episode for common queries

#### Query Optimization
```sql
-- Common query patterns
SELECT * FROM expressions 
WHERE media_id = ? 
ORDER BY created_at;

SELECT * FROM media 
WHERE show_name = ? AND episode_name = ?;

SELECT * FROM processing_jobs 
WHERE status = 'PROCESSING' 
ORDER BY created_at DESC;
```

## Database Usage Guidelines

### What Goes in the Database

**✅ DO Store:**
- **Metadata**: Show names, episode info, file references, timestamps
- **ExpressionAnalysis Data**: All fields from LLM output (structured)
- **Job Tracking**: Processing status, progress, error messages
- **User Data** (Future): User accounts, preferences, saved decks

**❌ DO NOT Store:**
- **Binary Files**: Videos, audio, images (use storage backend)
- **Large Text**: Subtitle files, prompt templates (use storage backend)
- **Temporary Data**: Processing intermediate files (use temp directory)

### Migration Strategy

#### Phase 1a: Parallel Operation
1. **Add DB writes** alongside existing file writes
2. **Keep both systems** running simultaneously
3. **No immediate deprecation** of file-based system
4. **Future phases** may deprecate file-only mode for API

#### Data Flow
```
CLI Processing:
Input → LangFlixPipeline → Files (existing) + DB (new)

API Processing:
Input → LangFlixPipeline → GCS (storage) + DB (metadata)
```

### Database Configuration

#### Connection Settings
```yaml
# default.yaml
database:
  url: "postgresql://user:password@localhost:5432/langflix"
  pool_size: 5
  max_overflow: 10
  echo: false  # Set to true for SQL logging
```

#### Environment Variables
```bash
# .env
DATABASE_URL=postgresql://user:password@localhost:5432/langflix
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
```

## Implementation Plan

### Phase 1a Tasks
- [ ] Create SQLAlchemy models
- [ ] Set up Alembic migrations
- [ ] Add database configuration
- [ ] Implement CRUD operations
- [ ] Integrate with existing pipeline

### Dependencies
- PostgreSQL 12+
- SQLAlchemy 2.0+
- Alembic for migrations
- psycopg2-binary for PostgreSQL driver

## Consequences

### Positive
- **Structured Data**: Easy querying and analysis
- **Job Tracking**: Monitor processing status
- **Scalability**: Foundation for multi-user platform
- **Search**: Full-text search capabilities
- **Analytics**: Data for usage insights

### Negative
- **Complexity**: Additional database layer
- **Dependencies**: PostgreSQL requirement
- **Migration**: Data migration from files to DB
- **Maintenance**: Database administration

### Risks and Mitigations

**Risk: Data Inconsistency**
- Mitigation: Database transactions, foreign key constraints

**Risk: Performance Issues**
- Mitigation: Proper indexing, query optimization

**Risk: Migration Complexity**
- Mitigation: Parallel operation, gradual migration

## Success Criteria

### Phase 1a Complete When:
- [ ] PostgreSQL running and accessible
- [ ] SQLAlchemy models defined and tested
- [ ] Alembic migrations working
- [ ] CLI saves metadata to DB after processing
- [ ] All file-based outputs still created (backward compatible)
- [ ] All existing tests passing
- [ ] New database tests passing

## References

- [ADR-009: Service Architecture Foundation](ADR-009-service-architecture-foundation.md)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)

## Next Steps

1. Get this ADR approved
2. Create `phase-1a-db-schema` branch
3. Implement SQLAlchemy models
4. Set up Alembic migrations
5. Begin database integration
