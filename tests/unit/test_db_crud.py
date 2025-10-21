"""
Unit tests for database CRUD operations.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from langflix.db.models import Media, Expression, ProcessingJob, Base
from langflix.db.crud import MediaCRUD, ExpressionCRUD, ProcessingJobCRUD


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_media_crud_create(db_session):
    """Test Media CRUD create operation."""
    media = MediaCRUD.create(
        db=db_session,
        show_name="Test Show",
        episode_name="Episode 1",
        language_code="en",
        subtitle_file_path="/path/to/subtitle.srt",
        video_file_path="/path/to/video.mp4"
    )
    
    assert media.id is not None
    assert media.show_name == "Test Show"
    assert media.episode_name == "Episode 1"
    assert media.language_code == "en"


def test_media_crud_get_by_id(db_session):
    """Test Media CRUD get by ID."""
    media = MediaCRUD.create(
        db=db_session,
        show_name="Test Show",
        episode_name="Episode 1",
        language_code="en"
    )
    
    retrieved_media = MediaCRUD.get_by_id(db_session, str(media.id))
    assert retrieved_media is not None
    assert retrieved_media.show_name == "Test Show"


def test_media_crud_get_by_show_episode(db_session):
    """Test Media CRUD get by show and episode."""
    MediaCRUD.create(
        db=db_session,
        show_name="Test Show",
        episode_name="Episode 1",
        language_code="en"
    )
    
    media = MediaCRUD.get_by_show_episode(db_session, "Test Show", "Episode 1")
    assert media is not None
    assert media.show_name == "Test Show"
    assert media.episode_name == "Episode 1"


def test_media_crud_update_file_paths(db_session):
    """Test Media CRUD update file paths."""
    media = MediaCRUD.create(
        db=db_session,
        show_name="Test Show",
        episode_name="Episode 1",
        language_code="en"
    )
    
    updated_media = MediaCRUD.update_file_paths(
        db=db_session,
        media_id=str(media.id),
        subtitle_path="/new/subtitle.srt",
        video_path="/new/video.mp4"
    )
    
    assert updated_media is not None
    assert updated_media.subtitle_file_path == "/new/subtitle.srt"
    assert updated_media.video_file_path == "/new/video.mp4"


def test_expression_crud_create(db_session):
    """Test Expression CRUD create operation."""
    # Create media first
    media = MediaCRUD.create(
        db=db_session,
        show_name="Test Show",
        episode_name="Episode 1",
        language_code="en"
    )
    
    expression = ExpressionCRUD.create(
        db=db_session,
        media_id=str(media.id),
        expression="test expression",
        expression_translation="테스트 표현",
        similar_expressions=["similar1", "similar2"]
    )
    
    assert expression.id is not None
    assert expression.media_id == media.id
    assert expression.expression == "test expression"
    assert expression.similar_expressions == ["similar1", "similar2"]


def test_expression_crud_get_by_media(db_session):
    """Test Expression CRUD get by media."""
    # Create media and expressions
    media = MediaCRUD.create(
        db=db_session,
        show_name="Test Show",
        episode_name="Episode 1",
        language_code="en"
    )
    
    ExpressionCRUD.create(
        db=db_session,
        media_id=str(media.id),
        expression="expression 1"
    )
    ExpressionCRUD.create(
        db=db_session,
        media_id=str(media.id),
        expression="expression 2"
    )
    
    expressions = ExpressionCRUD.get_by_media(db_session, str(media.id))
    assert len(expressions) == 2
    assert expressions[0].expression == "expression 1"
    assert expressions[1].expression == "expression 2"


def test_expression_crud_search_by_text(db_session):
    """Test Expression CRUD search by text."""
    # Create media and expressions
    media = MediaCRUD.create(
        db=db_session,
        show_name="Test Show",
        episode_name="Episode 1",
        language_code="en"
    )
    
    ExpressionCRUD.create(
        db=db_session,
        media_id=str(media.id),
        expression="hello world"
    )
    ExpressionCRUD.create(
        db=db_session,
        media_id=str(media.id),
        expression="goodbye world"
    )
    
    # Search for expressions containing "world"
    expressions = ExpressionCRUD.search_by_text(db_session, "world")
    assert len(expressions) == 2
    
    # Search for expressions containing "hello"
    expressions = ExpressionCRUD.search_by_text(db_session, "hello")
    assert len(expressions) == 1
    assert expressions[0].expression == "hello world"


def test_processing_job_crud_create(db_session):
    """Test ProcessingJob CRUD create operation."""
    # Create media first
    media = MediaCRUD.create(
        db=db_session,
        show_name="Test Show",
        episode_name="Episode 1",
        language_code="en"
    )
    
    job = ProcessingJobCRUD.create(
        db=db_session,
        media_id=str(media.id)
    )
    
    assert job.id is not None
    assert job.media_id == media.id
    assert job.status == "PENDING"
    assert job.progress == 0


def test_processing_job_crud_update_status(db_session):
    """Test ProcessingJob CRUD update status."""
    # Create media and job
    media = MediaCRUD.create(
        db=db_session,
        show_name="Test Show",
        episode_name="Episode 1",
        language_code="en"
    )
    
    job = ProcessingJobCRUD.create(
        db=db_session,
        media_id=str(media.id)
    )
    
    # Update status
    updated_job = ProcessingJobCRUD.update_status(
        db=db_session,
        job_id=str(job.id),
        status="PROCESSING",
        progress=50
    )
    
    assert updated_job is not None
    assert updated_job.status == "PROCESSING"
    assert updated_job.progress == 50
    
    # Complete job
    ProcessingJobCRUD.update_status(
        db=db_session,
        job_id=str(job.id),
        status="COMPLETED",
        progress=100
    )
    
    completed_job = ProcessingJobCRUD.get_by_id(db_session, str(job.id))
    assert completed_job.status == "COMPLETED"
    assert completed_job.progress == 100


def test_processing_job_crud_get_by_status(db_session):
    """Test ProcessingJob CRUD get by status."""
    # Create media and jobs
    media = MediaCRUD.create(
        db=db_session,
        show_name="Test Show",
        episode_name="Episode 1",
        language_code="en"
    )
    
    job1 = ProcessingJobCRUD.create(db=db_session, media_id=str(media.id))
    job2 = ProcessingJobCRUD.create(db=db_session, media_id=str(media.id))
    
    # Update one job to PROCESSING
    ProcessingJobCRUD.update_status(
        db=db_session,
        job_id=str(job1.id),
        status="PROCESSING"
    )
    
    # Get jobs by status
    pending_jobs = ProcessingJobCRUD.get_by_status(db_session, "PENDING")
    processing_jobs = ProcessingJobCRUD.get_by_status(db_session, "PROCESSING")
    
    assert len(pending_jobs) == 1
    assert len(processing_jobs) == 1
    assert pending_jobs[0].id == job2.id
    assert processing_jobs[0].id == job1.id
