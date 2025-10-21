"""
Unit tests for database models.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from langflix.db.models import Media, Expression, ProcessingJob, Base


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_media_creation(db_session):
    """Test Media model creation."""
    media = Media(
        show_name="Test Show",
        episode_name="Episode 1",
        language_code="en",
        subtitle_file_path="/path/to/subtitle.srt",
        video_file_path="/path/to/video.mp4"
    )
    db_session.add(media)
    db_session.commit()
    
    assert media.id is not None
    assert media.show_name == "Test Show"
    assert media.episode_name == "Episode 1"
    assert media.language_code == "en"
    assert media.subtitle_file_path == "/path/to/subtitle.srt"
    assert media.video_file_path == "/path/to/video.mp4"
    assert media.created_at is not None
    assert media.updated_at is not None


def test_expression_creation(db_session):
    """Test Expression model creation."""
    # Create media first
    media = Media(
        show_name="Test Show",
        episode_name="Episode 1",
        language_code="en"
    )
    db_session.add(media)
    db_session.commit()
    
    expression = Expression(
        media_id=media.id,
        expression="test expression",
        expression_translation="테스트 표현",
        expression_dialogue="This is a test dialogue",
        expression_dialogue_translation="이것은 테스트 대화입니다",
        similar_expressions=["similar1", "similar2"],
        context_start_time="00:01:23,456",
        context_end_time="00:01:25,789",
        scene_type="dialogue",
        context_video_path="/path/to/context.mkv",
        slide_video_path="/path/to/slide.mp4"
    )
    db_session.add(expression)
    db_session.commit()
    
    assert expression.id is not None
    assert expression.media_id == media.id
    assert expression.expression == "test expression"
    assert expression.expression_translation == "테스트 표현"
    assert expression.similar_expressions == ["similar1", "similar2"]
    assert expression.context_start_time == "00:01:23,456"
    assert expression.scene_type == "dialogue"
    assert expression.created_at is not None


def test_processing_job_creation(db_session):
    """Test ProcessingJob model creation."""
    # Create media first
    media = Media(
        show_name="Test Show",
        episode_name="Episode 1",
        language_code="en"
    )
    db_session.add(media)
    db_session.commit()
    
    job = ProcessingJob(
        media_id=media.id,
        status="PENDING",
        progress=0
    )
    db_session.add(job)
    db_session.commit()
    
    assert job.id is not None
    assert job.media_id == media.id
    assert job.status == "PENDING"
    assert job.progress == 0
    assert job.created_at is not None


def test_media_relationships(db_session):
    """Test Media model relationships."""
    media = Media(
        show_name="Test Show",
        episode_name="Episode 1",
        language_code="en"
    )
    db_session.add(media)
    db_session.commit()
    
    # Create expressions
    expr1 = Expression(
        media_id=media.id,
        expression="expression 1"
    )
    expr2 = Expression(
        media_id=media.id,
        expression="expression 2"
    )
    db_session.add_all([expr1, expr2])
    
    # Create processing job
    job = ProcessingJob(
        media_id=media.id,
        status="PENDING"
    )
    db_session.add(job)
    db_session.commit()
    
    # Test relationships
    assert len(media.expressions) == 2
    assert len(media.processing_jobs) == 1
    assert media.expressions[0].expression == "expression 1"
    assert media.processing_jobs[0].status == "PENDING"


def test_expression_media_relationship(db_session):
    """Test Expression-Media relationship."""
    media = Media(
        show_name="Test Show",
        episode_name="Episode 1",
        language_code="en"
    )
    db_session.add(media)
    db_session.commit()
    
    expression = Expression(
        media_id=media.id,
        expression="test expression"
    )
    db_session.add(expression)
    db_session.commit()
    
    assert expression.media.id == media.id
    assert expression.media.show_name == "Test Show"


def test_processing_job_status_update(db_session):
    """Test ProcessingJob status updates."""
    media = Media(
        show_name="Test Show",
        episode_name="Episode 1",
        language_code="en"
    )
    db_session.add(media)
    db_session.commit()
    
    job = ProcessingJob(
        media_id=media.id,
        status="PENDING",
        progress=0
    )
    db_session.add(job)
    db_session.commit()
    
    # Update status
    job.status = "PROCESSING"
    job.progress = 50
    db_session.commit()
    
    assert job.status == "PROCESSING"
    assert job.progress == 50
    
    # Complete job
    job.status = "COMPLETED"
    job.progress = 100
    db_session.commit()
    
    assert job.status == "COMPLETED"
    assert job.progress == 100
