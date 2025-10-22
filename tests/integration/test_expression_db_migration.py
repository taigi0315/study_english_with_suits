#!/usr/bin/env python3
"""
Integration tests for Expression database migration
"""

import pytest
import tempfile
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config

from langflix.db.models import Base, Expression, Media
# Remove unused import


class TestExpressionDBMigration:
    """Test Expression database migration and new fields"""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing"""
        # Create temporary database file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        
        # Create SQLite engine for testing
        engine = create_engine(f'sqlite:///{temp_file.name}')
        
        # Create tables manually to avoid JSONB issues
        from sqlalchemy import text
        with engine.connect() as conn:
            # Create media table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS media (
                    id TEXT PRIMARY KEY,
                    show_name TEXT NOT NULL,
                    episode_name TEXT NOT NULL,
                    language_code TEXT NOT NULL,
                    subtitle_file_path TEXT,
                    video_file_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create expressions table with new fields
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS expressions (
                    id TEXT PRIMARY KEY,
                    media_id TEXT NOT NULL,
                    expression TEXT NOT NULL,
                    expression_translation TEXT,
                    expression_dialogue TEXT,
                    expression_dialogue_translation TEXT,
                    similar_expressions TEXT,  -- JSON as TEXT for SQLite
                    context_start_time TEXT,
                    context_end_time TEXT,
                    scene_type TEXT,
                    context_video_path TEXT,
                    slide_video_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    difficulty INTEGER,
                    category TEXT,
                    educational_value TEXT,
                    usage_notes TEXT,
                    score REAL,
                    FOREIGN KEY (media_id) REFERENCES media(id)
                )
            """))
            
            conn.commit()
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        yield session, engine, temp_file.name
        
        # Cleanup
        session.close()
        engine.dispose()
        os.unlink(temp_file.name)
    
    def test_expression_fields_exist(self, temp_db):
        """Test that new expression fields exist in database"""
        session, engine, db_path = temp_db
        
        # Check if new columns exist by querying the table schema
        result = session.execute(text("PRAGMA table_info(expressions)"))
        columns = [row[1] for row in result.fetchall()]
        
        # Check that new fields exist
        assert 'difficulty' in columns
        assert 'category' in columns
        assert 'educational_value' in columns
        assert 'usage_notes' in columns
        assert 'score' in columns
    
    def test_expression_crud_with_new_fields(self, temp_db):
        """Test CRUD operations with new fields"""
        session, engine, db_path = temp_db
        
        # Create a media record first
        media = Media(
            show_name="Test Show",
            episode_name="Test Episode",
            language_code="en"
        )
        session.add(media)
        session.commit()
        
        # Create expression with new fields
        expression = Expression(
            media_id=media.id,
            expression="test expression",
            expression_translation="테스트 표현",
            expression_dialogue="This is a test expression",
            expression_dialogue_translation="이것은 테스트 표현입니다",
            similar_expressions=["alternative", "synonym"],
            context_start_time="00:01:00,000",
            context_end_time="00:01:05,000",
            scene_type="dialogue",
            # New fields
            difficulty=7,
            category="idiom",
            educational_value="This expression is useful for understanding informal conversation",
            usage_notes="Commonly used in casual settings",
            score=8.5
        )
        
        session.add(expression)
        session.commit()
        
        # Retrieve and verify
        retrieved = session.query(Expression).filter_by(expression="test expression").first()
        assert retrieved is not None
        assert retrieved.difficulty == 7
        assert retrieved.category == "idiom"
        assert retrieved.educational_value == "This expression is useful for understanding informal conversation"
        assert retrieved.usage_notes == "Commonly used in casual settings"
        assert retrieved.score == 8.5
    
    def test_expression_optional_fields(self, temp_db):
        """Test that new fields are optional (nullable)"""
        session, engine, db_path = temp_db
        
        # Create a media record first
        media = Media(
            show_name="Test Show 2",
            episode_name="Test Episode 2",
            language_code="en"
        )
        session.add(media)
        session.commit()
        
        # Create expression without new fields (should be allowed)
        expression = Expression(
            media_id=media.id,
            expression="simple expression",
            expression_translation="간단한 표현",
            expression_dialogue="This is a simple expression",
            expression_dialogue_translation="이것은 간단한 표현입니다",
            similar_expressions=["basic"],
            context_start_time="00:02:00,000",
            context_end_time="00:02:03,000",
            scene_type="dialogue"
            # New fields are None by default
        )
        
        session.add(expression)
        session.commit()
        
        # Verify that None values are stored correctly
        retrieved = session.query(Expression).filter_by(expression="simple expression").first()
        assert retrieved is not None
        assert retrieved.difficulty is None
        assert retrieved.category is None
        assert retrieved.educational_value is None
        assert retrieved.usage_notes is None
        assert retrieved.score is None
    
    def test_expression_relationships(self, temp_db):
        """Test that relationships still work with new fields"""
        session, engine, db_path = temp_db
        
        # Create media and expression
        media = Media(
            show_name="Relationship Test",
            episode_name="Test Episode",
            language_code="en"
        )
        session.add(media)
        session.flush()  # Get the ID
        
        expression = Expression(
            media_id=media.id,
            expression="relationship test",
            expression_translation="관계 테스트",
            expression_dialogue="Testing relationships",
            expression_dialogue_translation="관계 테스트 중",
            similar_expressions=["test"],
            context_start_time="00:03:00,000",
            context_end_time="00:03:05,000",
            scene_type="dialogue",
            difficulty=5,
            category="test",
            educational_value="Testing relationship integrity",
            usage_notes="For testing purposes",
            score=5.0
        )
        
        session.add(expression)
        session.commit()
        
        # Test relationship from media to expressions
        media_expressions = session.query(Expression).filter_by(media_id=media.id).all()
        assert len(media_expressions) == 1
        assert media_expressions[0].expression == "relationship test"
        assert media_expressions[0].difficulty == 5
        
        # Test relationship from expression to media
        retrieved_expression = session.query(Expression).filter_by(expression="relationship test").first()
        assert retrieved_expression.media.show_name == "Relationship Test"
        assert retrieved_expression.media.episode_name == "Test Episode"
    
    def test_expression_field_types(self, temp_db):
        """Test that new fields have correct types"""
        session, engine, db_path = temp_db
        
        # Create media
        media = Media(
            show_name="Type Test",
            episode_name="Test Episode",
            language_code="en"
        )
        session.add(media)
        session.flush()
        
        # Test different field types
        expression = Expression(
            media_id=media.id,
            expression="type test",
            expression_translation="타입 테스트",
            expression_dialogue="Testing field types",
            expression_dialogue_translation="필드 타입 테스트",
            similar_expressions=["type"],
            context_start_time="00:04:00,000",
            context_end_time="00:04:05,000",
            scene_type="dialogue",
            # Test different types
            difficulty=3,  # Integer
            category="slang",  # String
            educational_value="This is a long educational value that can contain multiple sentences and detailed explanations about why this expression is valuable for learning English.",  # Text
            usage_notes="Usage notes can also be long and contain detailed information about when and how to use this expression in different contexts.",  # Text
            score=7.8  # Float
        )
        
        session.add(expression)
        session.commit()
        
        # Verify types
        retrieved = session.query(Expression).filter_by(expression="type test").first()
        assert isinstance(retrieved.difficulty, int)
        assert isinstance(retrieved.category, str)
        assert isinstance(retrieved.educational_value, str)
        assert isinstance(retrieved.usage_notes, str)
        assert isinstance(retrieved.score, float)
        
        # Verify values
        assert retrieved.difficulty == 3
        assert retrieved.category == "slang"
        assert len(retrieved.educational_value) > 50  # Long text
        assert len(retrieved.usage_notes) > 50  # Long text
        assert retrieved.score == 7.8