# ADR-010: Database Schema Implementation

**Date:** 2025-10-21  
**Status:** Draft  
**Deciders:** Development Team  
**Related ADRs:** ADR-009 (Service Architecture Foundation), ADR-010 (Database Schema Design)

## Context

LangFlix needs to implement the database schema designed in ADR-010 to store metadata and structured data alongside the existing file-based system. This implementation will add PostgreSQL integration while maintaining full backward compatibility.

## Decision

We will implement the database schema using SQLAlchemy ORM with Alembic migrations, integrating database writes into the existing pipeline as an additional step (not a replacement).

## Implementation Plan

### Database Infrastructure Setup

#### Dependencies
```txt
# requirements.txt additions
sqlalchemy>=2.0.0
alembic>=1.12.0
psycopg2-binary>=2.9.0
```

#### Configuration
```yaml
# default.yaml additions
database:
  enabled: false  # CLI defaults to disabled
  url: "postgresql://user:password@localhost:5432/langflix"
  pool_size: 5
  max_overflow: 10
  echo: false  # Set to true for SQL logging
```

### Database Models Implementation

#### File Structure
```
langflix/
├── db/
│   ├── __init__.py
│   ├── models.py      # SQLAlchemy models
│   ├── session.py      # Database session management
│   ├── crud.py         # CRUD operations
│   └── migrations/     # Alembic migrations
│       ├── env.py
│       ├── script.py.mako
│       └── versions/
```

#### Core Models

**Media Model**
```python
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

class Media(Base):
    __tablename__ = "media"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    show_name = Column(String(255), nullable=False)
    episode_name = Column(String(255), nullable=False)
    language_code = Column(String(10), nullable=False)
    subtitle_file_path = Column(Text)  # Reference to storage backend
    video_file_path = Column(Text)     # Reference to storage backend
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    expressions = relationship("Expression", back_populates="media", cascade="all, delete-orphan")
    processing_jobs = relationship("ProcessingJob", back_populates="media", cascade="all, delete-orphan")
```

**Expression Model**
```python
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

class Expression(Base):
    __tablename__ = "expressions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False)
    expression = Column(Text, nullable=False)
    expression_translation = Column(Text)
    expression_dialogue = Column(Text)
    expression_dialogue_translation = Column(Text)
    similar_expressions = Column(JSONB)  # Array of similar expressions
    context_start_time = Column(String(20))  # e.g., "00:01:23,456"
    context_end_time = Column(String(20))    # e.g., "00:01:25,789"
    scene_type = Column(String(50))          # e.g., "dialogue", "action"
    context_video_path = Column(Text)        # Reference to storage backend
    slide_video_path = Column(Text)         # Reference to storage backend
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    media = relationship("Media", back_populates="expressions")
```

**ProcessingJob Model**
```python
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False, default="PENDING")  # PENDING, PROCESSING, COMPLETED, FAILED
    progress = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint("progress >= 0 AND progress <= 100", name="check_progress_range"),
    )
    
    # Relationships
    media = relationship("Media", back_populates="processing_jobs")
```

### Database Session Management

#### Session Factory
```python
# langflix/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from langflix.config import settings
from langflix.db.models import Base

class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
    
    def initialize(self):
        """Initialize database connection."""
        if self._initialized:
            return
        
        database_url = settings.get_database_url()
        self.engine = create_engine(
            database_url,
            pool_size=settings.get_database_pool_size(),
            max_overflow=settings.get_database_max_overflow(),
            echo=settings.get_database_echo()
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self._initialized = True
    
    def get_session(self) -> Session:
        """Get database session."""
        if not self._initialized:
            self.initialize()
        return self.SessionLocal()
    
    def create_tables(self):
        """Create all tables."""
        if not self._initialized:
            self.initialize()
        Base.metadata.create_all(bind=self.engine)

# Global database manager
db_manager = DatabaseManager()
```

### CRUD Operations

#### Media CRUD
```python
# langflix/db/crud.py
from typing import Optional, List
from sqlalchemy.orm import Session
from langflix.db.models import Media, Expression, ProcessingJob

class MediaCRUD:
    @staticmethod
    def create(db: Session, show_name: str, episode_name: str, language_code: str, 
               subtitle_file_path: str = None, video_file_path: str = None) -> Media:
        """Create new media record."""
        media = Media(
            show_name=show_name,
            episode_name=episode_name,
            language_code=language_code,
            subtitle_file_path=subtitle_file_path,
            video_file_path=video_file_path
        )
        db.add(media)
        db.commit()
        db.refresh(media)
        return media
    
    @staticmethod
    def get_by_id(db: Session, media_id: str) -> Optional[Media]:
        """Get media by ID."""
        return db.query(Media).filter(Media.id == media_id).first()
    
    @staticmethod
    def get_by_show_episode(db: Session, show_name: str, episode_name: str) -> Optional[Media]:
        """Get media by show and episode."""
        return db.query(Media).filter(
            Media.show_name == show_name,
            Media.episode_name == episode_name
        ).first()
    
    @staticmethod
    def update_file_paths(db: Session, media_id: str, subtitle_path: str = None, 
                          video_path: str = None) -> Optional[Media]:
        """Update file paths."""
        media = db.query(Media).filter(Media.id == media_id).first()
        if media:
            if subtitle_path:
                media.subtitle_file_path = subtitle_path
            if video_path:
                media.video_file_path = video_path
            db.commit()
            db.refresh(media)
        return media
```

#### Expression CRUD
```python
class ExpressionCRUD:
    @staticmethod
    def create_from_analysis(db: Session, media_id: str, analysis_data) -> Expression:
        """Create expression from ExpressionAnalysis data."""
        expression = Expression(
            media_id=media_id,
            expression=analysis.expression,
            expression_translation=analysis.expression_translation,
            expression_dialogue=analysis.expression_dialogue,
            expression_dialogue_translation=analysis.expression_dialogue_translation,
            similar_expressions=analysis.similar_expressions,
            context_start_time=analysis.context_start_time,
            context_end_time=analysis.context_end_time,
            scene_type=analysis.scene_type,
            context_video_path=analysis.context_video_path,
            slide_video_path=analysis.slide_video_path
        )
        db.add(expression)
        db.commit()
        db.refresh(expression)
        return expression
    
    @staticmethod
    def get_by_media(db: Session, media_id: str) -> List[Expression]:
        """Get all expressions for a media."""
        return db.query(Expression).filter(Expression.media_id == media_id).all()
    
    @staticmethod
    def search_by_text(db: Session, search_text: str) -> List[Expression]:
        """Search expressions by text."""
        return db.query(Expression).filter(
            Expression.expression.ilike(f"%{search_text}%")
        ).all()
```

#### ProcessingJob CRUD
```python
class ProcessingJobCRUD:
    @staticmethod
    def create(db: Session, media_id: str) -> ProcessingJob:
        """Create new processing job."""
        job = ProcessingJob(media_id=media_id, status="PENDING")
        db.add(job)
        db.commit()
        db.refresh(job)
        return job
    
    @staticmethod
    def update_status(db: Session, job_id: str, status: str, progress: int = None, 
                     error_message: str = None) -> Optional[ProcessingJob]:
        """Update job status."""
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if job:
            job.status = status
            if progress is not None:
                job.progress = progress
            if error_message:
                job.error_message = error_message
            if status == "PROCESSING":
                job.started_at = func.now()
            elif status in ["COMPLETED", "FAILED"]:
                job.completed_at = func.now()
            db.commit()
            db.refresh(job)
        return job
    
    @staticmethod
    def get_by_id(db: Session, job_id: str) -> Optional[ProcessingJob]:
        """Get job by ID."""
        return db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
```

### Pipeline Integration

#### Database Integration Points
```python
# langflix/main.py modifications
from langflix.db.session import db_manager
from langflix.db.crud import MediaCRUD, ExpressionCRUD, ProcessingJobCRUD

def process_episode_with_database(video_path, subtitle_path, config):
    """Process episode with database integration."""
    # Initialize database if enabled
    if config.get('database', {}).get('enabled', False):
        db_manager.initialize()
        db = db_manager.get_session()
        
        try:
            # Create media record
            media = MediaCRUD.create(
                db=db,
                show_name=config['show_name'],
                episode_name=config['episode_name'],
                language_code=config['language_code'],
                subtitle_file_path=subtitle_path,
                video_file_path=video_path
            )
            
            # Process expressions (existing logic)
            expressions = analyze_expressions(subtitle_path, config)
            
            # Save expressions to database
            for expr_data in expressions:
                ExpressionCRUD.create_from_analysis(
                    db=db,
                    media_id=media.id,
                    analysis_data=expr_data
                )
            
            # Continue with existing file processing
            # ... existing video processing logic ...
            
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
    
    # Always run existing file processing (backward compatibility)
    return process_episode_files_only(video_path, subtitle_path, config)
```

### Alembic Migrations

#### Initial Migration
```python
# alembic/versions/001_initial_schema.py
"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2025-10-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create media table
    op.create_table('media',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('show_name', sa.String(length=255), nullable=False),
        sa.Column('episode_name', sa.String(length=255), nullable=False),
        sa.Column('language_code', sa.String(length=10), nullable=False),
        sa.Column('subtitle_file_path', sa.Text(), nullable=True),
        sa.Column('video_file_path', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_media_show_episode', 'media', ['show_name', 'episode_name'])
    op.create_index('idx_media_language', 'media', ['language_code'])
    
    # Create expressions table
    op.create_table('expressions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('media_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('expression', sa.Text(), nullable=False),
        sa.Column('expression_translation', sa.Text(), nullable=True),
        sa.Column('expression_dialogue', sa.Text(), nullable=True),
        sa.Column('expression_dialogue_translation', sa.Text(), nullable=True),
        sa.Column('similar_expressions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('context_start_time', sa.String(length=20), nullable=True),
        sa.Column('context_end_time', sa.String(length=20), nullable=True),
        sa.Column('scene_type', sa.String(length=50), nullable=True),
        sa.Column('context_video_path', sa.Text(), nullable=True),
        sa.Column('slide_video_path', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['media_id'], ['media.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_expressions_media', 'expressions', ['media_id'])
    op.create_index('idx_expressions_text', 'expressions', [sa.text("to_tsvector('english', expression)")], postgresql_using='gin')
    
    # Create processing_jobs table
    op.create_table('processing_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('media_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('progress', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['media_id'], ['media.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('progress >= 0 AND progress <= 100', name='check_progress_range')
    )
    op.create_index('idx_jobs_status', 'processing_jobs', ['status'])
    op.create_index('idx_jobs_media', 'processing_jobs', ['media_id'])

def downgrade():
    op.drop_table('processing_jobs')
    op.drop_table('expressions')
    op.drop_table('media')
```

### Configuration Updates

#### Settings Functions
```python
# langflix/settings.py additions
def get_database_enabled() -> bool:
    """Check if database is enabled."""
    return settings.get("database.enabled", False)

def get_database_url() -> str:
    """Get database URL."""
    return settings.get("database.url", "postgresql://user:password@localhost:5432/langflix")

def get_database_pool_size() -> int:
    """Get database pool size."""
    return settings.get("database.pool_size", 5)

def get_database_max_overflow() -> int:
    """Get database max overflow."""
    return settings.get("database.max_overflow", 10)

def get_database_echo() -> bool:
    """Get database echo setting."""
    return settings.get("database.echo", False)
```

## Testing Strategy

### Unit Tests
```python
# tests/unit/test_db_models.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from langflix.db.models import Media, Expression, ProcessingJob

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()

def test_media_creation(db_session):
    media = Media(
        show_name="Test Show",
        episode_name="Episode 1",
        language_code="en"
    )
    db_session.add(media)
    db_session.commit()
    assert media.id is not None
    assert media.show_name == "Test Show"

def test_expression_creation(db_session):
    # Create media first
    media = Media(show_name="Test", episode_name="E1", language_code="en")
    db_session.add(media)
    db_session.commit()
    
    expression = Expression(
        media_id=media.id,
        expression="test expression",
        expression_translation="테스트 표현"
    )
    db_session.add(expression)
    db_session.commit()
    assert expression.id is not None
    assert expression.media_id == media.id
```

### Integration Tests
```python
# tests/integration/test_db_integration.py
def test_cli_with_database():
    """Test CLI processing with database enabled."""
    config = {
        'database': {'enabled': True},
        'show_name': 'Test Show',
        'episode_name': 'Episode 1',
        'language_code': 'en'
    }
    
    # Process episode
    result = process_episode_with_database("test_video.mp4", "test_subtitle.srt", config)
    
    # Verify files exist (backward compatibility)
    assert Path("output/Test Show/Episode 1/context_video.mkv").exists()
    
    # Verify database entries
    db = db_manager.get_session()
    media = MediaCRUD.get_by_show_episode(db, "Test Show", "Episode 1")
    assert media is not None
    assert media.language_code == "en"
    
    expressions = ExpressionCRUD.get_by_media(db, media.id)
    assert len(expressions) > 0
    db.close()
```

## Success Criteria

### Phase 1a Complete When:
- [ ] PostgreSQL running and accessible
- [ ] SQLAlchemy models defined and tested
- [ ] Alembic migrations working
- [ ] CLI saves metadata to DB after processing
- [ ] All file-based outputs still created (backward compatible)
- [ ] All existing tests passing
- [ ] New database tests passing

## Consequences

### Positive
- **Structured Data**: Easy querying and analysis
- **Job Tracking**: Monitor processing status
- **Scalability**: Foundation for multi-user platform
- **Search**: Full-text search capabilities
- **Backward Compatibility**: CLI unchanged

### Negative
- **Complexity**: Additional database layer
- **Dependencies**: PostgreSQL requirement
- **Configuration**: Additional setup required

### Risks and Mitigations

**Risk: Database Connection Failures**
- Mitigation: Graceful fallback to file-only mode, clear error messages

**Risk: Performance Impact**
- Mitigation: Optional database mode, performance benchmarks

**Risk: Data Inconsistency**
- Mitigation: Database transactions, validation

## References

- [ADR-009: Service Architecture Foundation](ADR-009-service-architecture-foundation.md)
- [ADR-010: Database Schema Design](ADR-010-database-schema-design.md)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)

## Next Steps

1. Get this ADR approved
2. Set up database infrastructure
3. Implement models and CRUD operations
4. Integrate with existing pipeline
5. Add comprehensive tests
