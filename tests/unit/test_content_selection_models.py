"""
Unit tests for V2 content selection models and analyzer.
"""
import pytest
from langflix.core.content_selection_models import (
    V2VocabularyAnnotation,
    V2ContentSelection,
    V2ContentSelectionResponse,
    enrich_content_selection,
    convert_v2_to_v1_format,
)


class TestV2VocabularyAnnotation:
    """Tests for V2VocabularyAnnotation model."""
    
    def test_create_annotation(self):
        """Should create annotation with word and index."""
        annotation = V2VocabularyAnnotation(word="knock", dialogue_index=2)
        
        assert annotation.word == "knock"
        assert annotation.dialogue_index == 2


class TestV2ContentSelection:
    """Tests for V2ContentSelection model."""
    
    def test_create_selection(self):
        """Should create content selection with required fields."""
        selection = V2ContentSelection(
            expression="knock it out of the park",
            expression_dialogue_index=5,
            context_start_index=3,
            context_end_index=8,
        )
        
        assert selection.expression == "knock it out of the park"
        assert selection.expression_dialogue_index == 5
        assert selection.context_start_index == 3
        assert selection.context_end_index == 8
    
    def test_optional_fields(self):
        """Should handle optional fields correctly."""
        selection = V2ContentSelection(
            expression="test",
            expression_dialogue_index=0,
            context_start_index=0,
            context_end_index=1,
            title="테스트 제목",
            catchy_keywords=["키워드1", "키워드2"],
            scene_type="humor",
        )
        
        assert selection.title == "테스트 제목"
        assert len(selection.catchy_keywords) == 2
        assert selection.scene_type == "humor"


class TestEnrichContentSelection:
    """Tests for enrich_content_selection function."""
    
    @pytest.fixture
    def sample_dialogues(self):
        """Create sample dialogue data."""
        source = [
            {"index": 0, "text": "Hello!", "start": "00:00:01,000", "end": "00:00:02,000"},
            {"index": 1, "text": "How are you?", "start": "00:00:03,000", "end": "00:00:04,000"},
            {"index": 2, "text": "I'll knock it out of the park.", "start": "00:00:05,000", "end": "00:00:07,000"},
            {"index": 3, "text": "Great!", "start": "00:00:08,000", "end": "00:00:09,000"},
        ]
        target = [
            {"index": 0, "text": "안녕!", "start": "00:00:01,000", "end": "00:00:02,000"},
            {"index": 1, "text": "어떻게 지내?", "start": "00:00:03,000", "end": "00:00:04,000"},
            {"index": 2, "text": "완벽하게 해낼게요.", "start": "00:00:05,000", "end": "00:00:07,000"},
            {"index": 3, "text": "좋아!", "start": "00:00:08,000", "end": "00:00:09,000"},
        ]
        return source, target
    
    def test_enrich_populates_translation(self, sample_dialogues):
        """Should populate expression_translation from target dialogues."""
        source, target = sample_dialogues
        
        selection = V2ContentSelection(
            expression="knock it out of the park",
            expression_dialogue_index=2,
            context_start_index=1,
            context_end_index=3,
        )
        
        enriched = enrich_content_selection(selection, source, target)
        
        assert enriched.expression_translation == "완벽하게 해낼게요."
    
    def test_enrich_populates_times(self, sample_dialogues):
        """Should populate context times from source dialogues."""
        source, target = sample_dialogues
        
        selection = V2ContentSelection(
            expression="test",
            expression_dialogue_index=2,
            context_start_index=1,
            context_end_index=3,
        )
        
        enriched = enrich_content_selection(selection, source, target)
        
        assert enriched.context_start_time == "00:00:03,000"
        assert enriched.context_end_time == "00:00:09,000"


class TestConvertV2ToV1Format:
    """Tests for convert_v2_to_v1_format function."""
    
    @pytest.fixture
    def sample_dialogues(self):
        """Create sample dialogue data."""
        source = [
            {"index": 0, "text": "Hello!", "start": "00:00:01,000", "end": "00:00:02,000"},
            {"index": 1, "text": "I'll knock it out of the park.", "start": "00:00:03,000", "end": "00:00:05,000"},
            {"index": 2, "text": "Great!", "start": "00:00:06,000", "end": "00:00:07,000"},
        ]
        target = [
            {"index": 0, "text": "안녕!", "start": "00:00:01,000", "end": "00:00:02,000"},
            {"index": 1, "text": "완벽하게 해낼게요.", "start": "00:00:03,000", "end": "00:00:05,000"},
            {"index": 2, "text": "좋아!", "start": "00:00:06,000", "end": "00:00:07,000"},
        ]
        return source, target
    
    def test_convert_creates_v1_format(self, sample_dialogues):
        """Should convert V2 selection to V1-compatible dict."""
        source, target = sample_dialogues
        
        selection = V2ContentSelection(
            expression="knock it out of the park",
            expression_dialogue_index=1,
            context_start_index=0,
            context_end_index=2,
            title="완벽한 자신감",
            catchy_keywords=["자신감 폭발"],
            scene_type="drama",
            similar_expressions=["hit it out of the park"],
        )
        
        # Enrich first
        enriched = enrich_content_selection(selection, source, target)
        
        # Convert to V1
        v1 = convert_v2_to_v1_format(enriched, source, target)
        
        assert v1['expression'] == "knock it out of the park"
        assert v1['expression_translation'] == "완벽하게 해낼게요."
        assert v1['title'] == "완벽한 자신감"
        assert len(v1['dialogues']) == 3
        assert len(v1['translation']) == 3
        assert v1['dialogues'][1] == "I'll knock it out of the park."
        assert v1['translation'][1] == "완벽하게 해낼게요."
        assert v1['scene_type'] == "drama"


class TestV2ContentSelectionResponse:
    """Tests for V2ContentSelectionResponse model."""
    
    def test_create_empty_response(self):
        """Should create response with empty expressions list."""
        response = V2ContentSelectionResponse()
        assert response.expressions == []
    
    def test_create_with_expressions(self):
        """Should create response with expression list."""
        selections = [
            V2ContentSelection(
                expression="test1",
                expression_dialogue_index=0,
                context_start_index=0,
                context_end_index=1,
            ),
            V2ContentSelection(
                expression="test2",
                expression_dialogue_index=2,
                context_start_index=2,
                context_end_index=3,
            ),
        ]
        
        response = V2ContentSelectionResponse(expressions=selections)
        
        assert len(response.expressions) == 2
        assert response.expressions[0].expression == "test1"
        assert response.expressions[1].expression == "test2"
