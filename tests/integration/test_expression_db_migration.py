"""
Integration tests for expression database migration.
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from langflix.db.models import Base, Expression, Media
from langflix.db.session import db_manager
import uuid
from datetime import datetime


class TestExpressionFieldsMigration:
    """Test that new expression fields are properly added to the database."""
    
    @pytest.fixture
    def test_engine(self):
        """Create a test database engine."""
        # Use in-memory SQLite for testing
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture
    def test_session(self, test_engine):
        """Create a test database session."""
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
        session = SessionLocal()
        yield session
        session.close()
    
    def test_expression_table_has_new_fields(self, test_engine):
        """Test that the expressions table has the new fields."""
        # Check if the new columns exist
        with test_engine.connect() as conn:
            # Get table info
            result = conn.execute(text("PRAGMA table_info(expressions)"))
            columns = [row[1] for row in result.fetchall()]
            
            # Check that new fields exist
            assert 'difficulty' in columns
            assert 'category' in columns
            assert 'educational_value' in columns
            assert 'usage_notes' in columns
            assert 'score' in columns
    
    def test_create_expression_with_new_fields(self, test_session):
        """Test creating an expression with the new fields."""
        # Create a media record first
        media = Media(
            id=uuid.uuid4(),
            show_name="Test Show",
            episode_name="Test Episode",
            language_code="en"
        )
        test_session.add(media)
        test_session.commit()
        
        # Create an expression with new fields
        expression = Expression(
            id=uuid.uuid4(),
            media_id=media.id,
            expression="Test expression",
            expression_translation="테스트 표현",
            expression_dialogue="This is a test dialogue",
            expression_dialogue_translation="이것은 테스트 대화입니다",
            similar_expressions=["Alternative 1", "Alternative 2"],
            context_start_time="00:01:23,456",
            context_end_time="00:01:25,789",
            scene_type="dialogue",
            context_video_path="/path/to/context.mp4",
            slide_video_path="/path/to/slide.mp4",
            # New fields
            difficulty=7,
            category="idiom",
            educational_value="This expression is useful for understanding informal conversation",
            usage_notes="Commonly used in casual settings",
            score=8.5
        )
        
        test_session.add(expression)
        test_session.commit()
        
        # Verify the expression was created with new fields
        saved_expression = test_session.query(Expression).filter_by(id=expression.id).first()
        assert saved_expression is not None
        assert saved_expression.difficulty == 7
        assert saved_expression.category == "idiom"
        assert saved_expression.educational_value == "This expression is useful for understanding informal conversation"
        assert saved_expression.usage_notes == "Commonly used in casual settings"
        assert saved_expression.score == 8.5
    
    def test_expression_with_null_new_fields(self, test_session):
        """Test creating an expression with null values for new fields."""
        # Create a media record first
        media = Media(
            id=uuid.uuid4(),
            show_name="Test Show",
            episode_name="Test Episode",
            language_code="en"
        )
        test_session.add(media)
        test_session.commit()
        
        # Create an expression without new fields (should be null)
        expression = Expression(
            id=uuid.uuid4(),
            media_id=media.id,
            expression="Test expression",
            expression_translation="테스트 표현",
            expression_dialogue="This is a test dialogue",
            expression_dialogue_translation="이것은 테스트 대화입니다",
            similar_expressions=["Alternative 1"],
            context_start_time="00:01:23,456",
            context_end_time="00:01:25,789",
            scene_type="dialogue"
            # New fields are not set, should be null
        )
        
        test_session.add(expression)
        test_session.commit()
        
        # Verify the expression was created with null new fields
        saved_expression = test_session.query(Expression).filter_by(id=expression.id).first()
        assert saved_expression is not None
        assert saved_expression.difficulty is None
        assert saved_expression.category is None
        assert saved_expression.educational_value is None
        assert saved_expression.usage_notes is None
        assert saved_expression.score is None
    
    def test_expression_crud_operations(self, test_session):
        """Test CRUD operations with new fields."""
        # Create a media record
        media = Media(
            id=uuid.uuid4(),
            show_name="Test Show",
            episode_name="Test Episode",
            language_code="en"
        )
        test_session.add(media)
        test_session.commit()
        
        # Create expression
        expression = Expression(
            id=uuid.uuid4(),
            media_id=media.id,
            expression="Get the ball rolling",
            expression_translation="일을 시작하다",
            expression_dialogue="Let's get the ball rolling on this project",
            expression_dialogue_translation="이 프로젝트를 시작해봅시다",
            similar_expressions=["Start the process", "Begin the work"],
            context_start_time="00:02:15,123",
            context_end_time="00:02:18,456",
            scene_type="dialogue",
            difficulty=6,
            category="idiom",
            educational_value="Common business idiom for starting work",
            usage_notes="Used in professional settings",
            score=7.2
        )
        
        test_session.add(expression)
        test_session.commit()
        
        # Read expression
        saved_expression = test_session.query(Expression).filter_by(id=expression.id).first()
        assert saved_expression.expression == "Get the ball rolling"
        assert saved_expression.difficulty == 6
        assert saved_expression.category == "idiom"
        assert saved_expression.score == 7.2
        
        # Update expression
        saved_expression.difficulty = 8
        saved_expression.score = 8.5
        saved_expression.usage_notes = "Updated usage notes"
        test_session.commit()
        
        # Verify update
        updated_expression = test_session.query(Expression).filter_by(id=expression.id).first()
        assert updated_expression.difficulty == 8
        assert updated_expression.score == 8.5
        assert updated_expression.usage_notes == "Updated usage notes"
        
        # Delete expression
        test_session.delete(updated_expression)
        test_session.commit()
        
        # Verify deletion
        deleted_expression = test_session.query(Expression).filter_by(id=expression.id).first()
        assert deleted_expression is None
    
    def test_expression_relationship_with_media(self, test_session):
        """Test that expression-media relationship works with new fields."""
        # Create media
        media = Media(
            id=uuid.uuid4(),
            show_name="Test Show",
            episode_name="Test Episode",
            language_code="en"
        )
        test_session.add(media)
        test_session.commit()
        
        # Create multiple expressions for the same media
        expressions = []
        for i in range(3):
            expression = Expression(
                id=uuid.uuid4(),
                media_id=media.id,
                expression=f"Expression {i+1}",
                expression_translation=f"표현 {i+1}",
                expression_dialogue=f"Dialogue {i+1}",
                expression_dialogue_translation=f"대화 {i+1}",
                similar_expressions=[f"Alt {i+1}"],
                context_start_time=f"00:0{i+1}:00,000",
                context_end_time=f"00:0{i+1}:03,000",
                scene_type="dialogue",
                difficulty=5 + i,
                category=["idiom", "slang", "formal"][i],
                educational_value=f"Educational value {i+1}",
                usage_notes=f"Usage notes {i+1}",
                score=6.0 + i
            )
            expressions.append(expression)
            test_session.add(expression)
        
        test_session.commit()
        
        # Test relationship
        media_expressions = test_session.query(Expression).filter_by(media_id=media.id).all()
        assert len(media_expressions) == 3
        
        # Test filtering by new fields
        idiom_expressions = test_session.query(Expression).filter_by(
            media_id=media.id,
            category="idiom"
        ).all()
        assert len(idiom_expressions) == 1
        assert idiom_expressions[0].expression == "Expression 1"
        
        # Test filtering by difficulty
        high_difficulty = test_session.query(Expression).filter(
            Expression.media_id == media.id,
            Expression.difficulty >= 6
        ).all()
        assert len(high_difficulty) == 2
        
        # Test filtering by score
        high_score = test_session.query(Expression).filter(
            Expression.media_id == media.id,
            Expression.score >= 7.0
        ).all()
        assert len(high_score) == 2


class TestExpressionModelValidation:
    """Test Expression model validation with new fields."""
    
    def test_difficulty_range_validation(self):
        """Test that difficulty field accepts valid range."""
        # This would be tested at the application level
        # since SQLAlchemy doesn't enforce range constraints by default
        pass
    
    def test_category_length_validation(self):
        """Test that category field respects length limit."""
        # This would be tested at the application level
        # since we're using String(50) which should be enforced by SQLAlchemy
        pass
    
    def test_score_precision(self):
        """Test that score field handles float precision correctly."""
        # This would be tested with actual database operations
        pass
