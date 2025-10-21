# ADR-012: File-based to Database Migration Strategy

**Date:** 2025-10-21  
**Status:** Draft  
**Deciders:** Development Team  
**Related ADRs:** ADR-009 (Service Architecture Foundation), ADR-010 (Database Schema)

## Context

LangFlix currently operates as a file-based system where all outputs (videos, subtitles, educational slides) are stored as files in the local filesystem. The service architecture transformation requires adding a database layer while maintaining backward compatibility.

## Decision

We will implement a **parallel operation strategy** where both file-based and database systems operate simultaneously, with gradual migration and no immediate deprecation of the file-based system.

## Migration Strategy Overview

### Core Principles

1. **Zero Disruption**: Existing CLI workflows remain unchanged
2. **Parallel Operation**: Both systems run simultaneously
3. **Gradual Migration**: No forced migration timeline
4. **Backward Compatibility**: File outputs continue to be created
5. **Future Flexibility**: API can use database primarily, CLI can use files primarily

### Migration Phases

#### Phase 1: Parallel Operation (Phase 1a-1d)
**Duration**: Throughout Phase 1 implementation
**Approach**: Add database writes alongside existing file writes

```
Current Flow:
Input → LangFlixPipeline → Files

New Flow:
Input → LangFlixPipeline → Files + Database
```

**Benefits:**
- Zero disruption to existing workflows
- Gradual adoption of database features
- Easy rollback if issues arise
- Testing both systems simultaneously

#### Phase 2: API Optimization (Future)
**Duration**: After Phase 1 completion
**Approach**: API uses database primarily, files for legacy support

```
CLI Flow:
Input → LangFlixPipeline → Files + Database (optional)

API Flow:
Input → LangFlixPipeline → Database + GCS Storage
```

#### Phase 3: Legacy Support (Future)
**Duration**: Long-term maintenance
**Approach**: Files maintained for CLI, API uses database/GCS

## Implementation Details

### Database Integration Points

#### 1. Media Processing
```python
# Before (file-only)
def process_episode(video_path, subtitle_path):
    # Process video
    # Save files to output/
    pass

# After (files + database)
def process_episode(video_path, subtitle_path):
    # Process video
    # Save files to output/ (existing)
    # Save metadata to database (new)
    media = Media(
        show_name=show_name,
        episode_name=episode_name,
        language_code=language_code,
        subtitle_file_path=subtitle_path,
        video_file_path=video_path
    )
    db.session.add(media)
    db.session.commit()
```

#### 2. Expression Analysis
```python
# Before (file-only)
def analyze_expressions(expressions_data):
    # Process expressions
    # Save to files
    pass

# After (files + database)
def analyze_expressions(expressions_data, media_id):
    # Process expressions
    # Save to files (existing)
    # Save to database (new)
    for expr_data in expressions_data:
        expression = Expression(
            media_id=media_id,
            expression=expr_data.expression,
            expression_translation=expr_data.expression_translation,
            # ... other fields
        )
        db.session.add(expression)
    db.session.commit()
```

#### 3. Job Tracking
```python
# Before (no tracking)
def process_video():
    # Process video
    # Save results
    pass

# After (with tracking)
def process_video(job_id=None):
    if job_id:
        job = ProcessingJob.query.get(job_id)
        job.status = 'PROCESSING'
        job.started_at = datetime.utcnow()
        db.session.commit()
    
    try:
        # Process video
        # Save results to files + database
        
        if job_id:
            job.status = 'COMPLETED'
            job.completed_at = datetime.utcnow()
            job.progress = 100
            db.session.commit()
    except Exception as e:
        if job_id:
            job.status = 'FAILED'
            job.error_message = str(e)
            db.session.commit()
        raise
```

### Configuration Strategy

#### CLI Mode (Default)
```yaml
# default.yaml
database:
  enabled: false  # CLI can work without database

storage:
  backend: "local"
```

#### API Mode
```yaml
# api-config.yaml
database:
  enabled: true
  url: "postgresql://user:pass@localhost/langflix"

storage:
  backend: "gcs"
  gcs:
    bucket_name: "langflix-storage"
```

### Data Consistency Strategy

#### File-Database Synchronization
```python
def ensure_data_consistency(media_id):
    """Ensure file and database data are consistent."""
    media = Media.query.get(media_id)
    
    # Check if files exist
    if not Path(media.subtitle_file_path).exists():
        logger.warning(f"Subtitle file missing: {media.subtitle_file_path}")
    
    if not Path(media.video_file_path).exists():
        logger.warning(f"Video file missing: {media.video_file_path}")
    
    # Check expressions
    expressions = Expression.query.filter_by(media_id=media_id).all()
    for expr in expressions:
        if not Path(expr.context_video_path).exists():
            logger.warning(f"Context video missing: {expr.context_video_path}")
```

#### Conflict Resolution
```python
def resolve_data_conflicts(media_id):
    """Resolve conflicts between file and database data."""
    # Priority: Database > Files
    # If database has newer timestamp, trust database
    # If files are newer, update database
    
    media = Media.query.get(media_id)
    file_mtime = Path(media.video_file_path).stat().st_mtime
    db_mtime = media.updated_at.timestamp()
    
    if file_mtime > db_mtime:
        # Files are newer, update database
        update_database_from_files(media_id)
    else:
        # Database is newer, files should be consistent
        verify_files_exist(media_id)
```

### Rollback Strategy

#### Database Rollback
```python
def rollback_database_changes(media_id):
    """Rollback database changes for specific media."""
    # Delete from database
    Expression.query.filter_by(media_id=media_id).delete()
    Media.query.filter_by(id=media_id).delete()
    db.session.commit()
    
    # Files remain untouched
    logger.info(f"Rolled back database changes for media {media_id}")
```

#### File System Rollback
```python
def rollback_file_changes(media_id):
    """Rollback file changes (if needed)."""
    media = Media.query.get(media_id)
    
    # Delete files
    if Path(media.subtitle_file_path).exists():
        Path(media.subtitle_file_path).unlink()
    
    if Path(media.video_file_path).exists():
        Path(media.video_file_path).unlink()
    
    # Delete database entries
    rollback_database_changes(media_id)
```

## Testing Strategy

### Migration Testing
```python
def test_parallel_operation():
    """Test that both file and database systems work together."""
    # Process video
    result = process_episode("test_video.mp4", "test_subtitle.srt")
    
    # Verify files exist
    assert Path("output/test_video/context_video.mkv").exists()
    assert Path("output/test_video/slides/expression_01.mp4").exists()
    
    # Verify database entries
    media = Media.query.filter_by(episode_name="test_video").first()
    assert media is not None
    assert media.subtitle_file_path is not None
    
    expressions = Expression.query.filter_by(media_id=media.id).all()
    assert len(expressions) > 0
```

### Consistency Testing
```python
def test_data_consistency():
    """Test that file and database data are consistent."""
    media = Media.query.first()
    
    # Check file paths in database exist
    assert Path(media.subtitle_file_path).exists()
    assert Path(media.video_file_path).exists()
    
    # Check expressions
    expressions = Expression.query.filter_by(media_id=media.id).all()
    for expr in expressions:
        assert Path(expr.context_video_path).exists()
        assert Path(expr.slide_video_path).exists()
```

### Performance Testing
```python
def test_migration_performance():
    """Test that adding database writes doesn't significantly impact performance."""
    import time
    
    # Test file-only processing
    start_time = time.time()
    process_episode_file_only("test_video.mp4", "test_subtitle.srt")
    file_only_time = time.time() - start_time
    
    # Test file + database processing
    start_time = time.time()
    process_episode_with_db("test_video.mp4", "test_subtitle.srt")
    file_db_time = time.time() - start_time
    
    # Database overhead should be < 10% of total time
    overhead = (file_db_time - file_only_time) / file_only_time
    assert overhead < 0.1, f"Database overhead too high: {overhead:.2%}"
```

## Monitoring and Observability

### Migration Metrics
```python
def track_migration_metrics():
    """Track migration progress and health."""
    metrics = {
        'total_media_processed': Media.query.count(),
        'files_with_db_entries': Media.query.filter(
            Media.subtitle_file_path.isnot(None)
        ).count(),
        'inconsistent_entries': count_inconsistent_entries(),
        'migration_errors': count_migration_errors()
    }
    return metrics
```

### Health Checks
```python
def health_check():
    """Check system health during migration."""
    health = {
        'database_connected': check_database_connection(),
        'file_system_accessible': check_file_system_access(),
        'data_consistency': check_data_consistency(),
        'performance_acceptable': check_performance_metrics()
    }
    return health
```

## Timeline and Milestones

### Phase 1a: Database Integration
- **Week 1**: Database schema implementation
- **Week 2**: CRUD operations and integration
- **Week 3**: Testing and validation
- **Week 4**: Documentation and deployment

### Phase 1b: Storage Abstraction
- **Week 1**: Storage interface implementation
- **Week 2**: LocalStorage backend
- **Week 3**: GoogleCloudStorage backend
- **Week 4**: Integration and testing

### Phase 1c: API Scaffold
- **Week 1**: FastAPI application setup
- **Week 2**: Endpoint implementation
- **Week 3**: Documentation and testing
- **Week 4**: Integration with database and storage

### Phase 1d: Background Tasks
- **Week 1**: Task processing implementation
- **Week 2**: Job tracking integration
- **Week 3**: Full pipeline integration
- **Week 4**: Testing and optimization

## Success Criteria

### Phase 1a Complete When:
- [ ] Database schema implemented and tested
- [ ] CLI saves metadata to database after processing
- [ ] All file-based outputs still created (backward compatible)
- [ ] All existing tests passing
- [ ] New database tests passing

### Phase 1b Complete When:
- [ ] Storage abstraction layer implemented
- [ ] LocalStorage backend working (CLI default)
- [ ] GoogleCloudStorage backend working (API default)
- [ ] All existing tests passing
- [ ] New storage tests passing

### Phase 1c Complete When:
- [ ] FastAPI application running
- [ ] Basic endpoints functional
- [ ] API documentation accessible
- [ ] All tests passing (CLI + API)

### Phase 1d Complete When:
- [ ] API processes videos asynchronously
- [ ] Job status tracked in database
- [ ] Results stored in appropriate backend
- [ ] CLI unchanged and working
- [ ] All tests passing

## Risk Mitigation

### Risk: Data Inconsistency
- **Mitigation**: Regular consistency checks, automated reconciliation
- **Monitoring**: Data consistency metrics, automated alerts

### Risk: Performance Degradation
- **Mitigation**: Performance benchmarks, database optimization
- **Monitoring**: Processing time metrics, database query performance

### Risk: Migration Failures
- **Mitigation**: Rollback procedures, parallel operation
- **Monitoring**: Error rates, success metrics

### Risk: User Disruption
- **Mitigation**: Backward compatibility, gradual rollout
- **Monitoring**: User feedback, error reports

## References

- [ADR-009: Service Architecture Foundation](ADR-009-service-architecture-foundation.md)
- [ADR-010: Database Schema Design](ADR-010-database-schema-design.md)
- [ADR-011: Storage Abstraction Layer](ADR-011-storage-abstraction-layer.md)

## Next Steps

1. Get this ADR approved
2. Begin Phase 1a implementation
3. Set up monitoring and metrics
4. Plan Phase 1b implementation
