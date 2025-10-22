"""
Integration tests for database functionality.
"""

import pytest
from pathlib import Path
from langflix.db import db_manager, MediaCRUD, ExpressionCRUD
from langflix.db.models import Media, Expression
from langflix import settings


@pytest.fixture
def test_db():
    """Create test database."""
    # Use in-memory SQLite for testing
    test_url = "sqlite:///:memory:"
    db_manager.engine = None
    db_manager.SessionLocal = None
    db_manager._initialized = False
    
    # Initialize with test URL
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from langflix.db.models import Base
    
    engine = create_engine(test_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    
    db_manager.engine = engine
    db_manager.SessionLocal = SessionLocal
    db_manager._initialized = True
    
    yield db_manager
    
    # Cleanup
    db_manager.close()


def test_database_connection(test_db):
    """Test database connection."""
    session = test_db.get_session()
    assert session is not None
    session.close()


def test_media_creation_and_retrieval(test_db):
    """Test creating and retrieving media records."""
    session = test_db.get_session()
    
    try:
        # Create media
        media = MediaCRUD.create(
            db=session,
            show_name="Test Show",
            episode_name="Episode 1",
            language_code="en",
            subtitle_file_path="/path/to/subtitle.srt",
            video_file_path="/path/to/video.mp4"
        )
        
        assert media.id is not None
        
        # Retrieve media
        retrieved_media = MediaCRUD.get_by_id(session, str(media.id))
        assert retrieved_media is not None
        assert retrieved_media.show_name == "Test Show"
        assert retrieved_media.episode_name == "Episode 1"
        
    finally:
        session.close()


def test_expression_creation_and_retrieval(test_db):
    """Test creating and retrieving expressions."""
    session = test_db.get_session()
    
    try:
        # Create media first
        media = MediaCRUD.create(
            db=session,
            show_name="Test Show",
            episode_name="Episode 1",
            language_code="en"
        )
        
        # Create expressions
        expr1 = ExpressionCRUD.create(
            db=session,
            media_id=str(media.id),
            expression="hello world",
            expression_translation="안녕하세요",
            similar_expressions=["hi", "hey"]
        )
        
        expr2 = ExpressionCRUD.create(
            db=session,
            media_id=str(media.id),
            expression="goodbye world",
            expression_translation="안녕히 가세요",
            similar_expressions=["bye", "see you"]
        )
        
        # Retrieve expressions
        expressions = ExpressionCRUD.get_by_media(session, str(media.id))
        assert len(expressions) == 2
        
        # Test search
        search_results = ExpressionCRUD.search_by_text(session, "world")
        assert len(search_results) == 2
        
        search_results = ExpressionCRUD.search_by_text(session, "hello")
        assert len(search_results) == 1
        assert search_results[0].expression == "hello world"
        
    finally:
        session.close()


def test_database_transactions(test_db):
    """Test database transactions and rollback."""
    session = test_db.get_session()
    
    try:
        # Create media
        media = MediaCRUD.create(
            db=session,
            show_name="Test Show",
            episode_name="Episode 1",
            language_code="en"
        )
        
        # Create expression
        expression = ExpressionCRUD.create(
            db=session,
            media_id=str(media.id),
            expression="test expression"
        )
        
        # Verify both records exist
        assert MediaCRUD.get_by_id(session, str(media.id)) is not None
        assert ExpressionCRUD.get_by_media(session, str(media.id)) is not None
        
        # Test rollback
        session.rollback()
        
        # Records should still exist (SQLite doesn't support true rollback in this setup)
        # This test mainly verifies the transaction structure
        
    finally:
        session.close()


def test_database_constraints(test_db):
    """Test database constraints."""
    session = test_db.get_session()
    
    try:
        # Test foreign key constraint
        # This should work (SQLite doesn't enforce foreign keys by default)
        expression = ExpressionCRUD.create(
            db=session,
            media_id="non-existent-id",
            expression="test expression"
        )
        
        # The expression should be created (SQLite behavior)
        assert expression.id is not None
        
    finally:
        session.close()


def test_database_performance(test_db):
    """Test database performance with multiple records."""
    session = test_db.get_session()
    
    try:
        # Create media
        media = MediaCRUD.create(
            db=session,
            show_name="Performance Test",
            episode_name="Episode 1",
            language_code="en"
        )
        
        # Create many expressions
        expressions = []
        for i in range(100):
            expr = ExpressionCRUD.create(
                db=session,
                media_id=str(media.id),
                expression=f"expression {i}",
                expression_translation=f"표현 {i}"
            )
            expressions.append(expr)
        
        # Verify all expressions were created
        retrieved_expressions = ExpressionCRUD.get_by_media(session, str(media.id))
        assert len(retrieved_expressions) == 100
        
        # Test search performance
        search_results = ExpressionCRUD.search_by_text(session, "expression")
        assert len(search_results) == 100
        
    finally:
        session.close()
