"""
Unit tests for V2 content selection models and analyzer.
Updated to match current V2 model requirements.
"""
import pytest
from langflix.core.content_selection_models import (
    V2VocabularyAnnotation,
    V2Narration,
    V2ExpressionAnnotation,
    V2ContentSelection,
    V2ContentSelectionResponse,
    enrich_from_subtitles,
    convert_v2_to_v1_format,
)


class TestV2VocabularyAnnotation:
    """Tests for V2VocabularyAnnotation model."""
    
    def test_create_annotation(self):
        """Should create annotation with word, translation, and index."""
        annotation = V2VocabularyAnnotation(
            word="knock",
            translation="치다",
            dialogue_index=2
        )
        
        assert annotation.word == "knock"
        assert annotation.translation == "치다"
        assert annotation.dialogue_index == 2
    
    def test_default_dialogue_index(self):
        """Should use default dialogue_index of 0."""
        annotation = V2VocabularyAnnotation(
            word="test",
            translation="테스트"
        )
        assert annotation.dialogue_index == 0


class TestV2Narration:
    """Tests for V2Narration model."""
    
    def test_create_narration(self):
        """Should create narration with text and type."""
        narration = V2Narration(
            dialogue_index=1,
            text="¡Momento clave!",
            type="highlight"
        )
        
        assert narration.dialogue_index == 1
        assert narration.text == "¡Momento clave!"
        assert narration.type == "highlight"
    
    def test_default_type(self):
        """Should use default type of 'commentary'."""
        narration = V2Narration(
            dialogue_index=0,
            text="Test"
        )
        assert narration.type == "commentary"


class TestV2ExpressionAnnotation:
    """Tests for V2ExpressionAnnotation model."""
    
    def test_create_expression_annotation(self):
        """Should create expression annotation."""
        annotation = V2ExpressionAnnotation(
            expression="knock it out of the park",
            translation="완벽하게 해내다",
            dialogue_index=5
        )
        
        assert annotation.expression == "knock it out of the park"
        assert annotation.translation == "완벽하게 해내다"
        assert annotation.dialogue_index == 5


class TestV2ContentSelection:
    """Tests for V2ContentSelection model."""
    
    @pytest.fixture
    def minimal_selection(self):
        """Create minimal valid V2ContentSelection."""
        return V2ContentSelection(
            expression="knock it out of the park",
            expression_translation="완벽하게 해내다",
            title="자신감 표현",
            title_translation="Expresión de confianza",
            expression_dialogue_index=5,
            context_start_index=3,
            context_end_index=8,
        )
    
    def test_create_selection(self, minimal_selection):
        """Should create content selection with required fields."""
        assert minimal_selection.expression == "knock it out of the park"
        assert minimal_selection.expression_translation == "완벽하게 해내다"
        assert minimal_selection.expression_dialogue_index == 5
        assert minimal_selection.context_start_index == 3
        assert minimal_selection.context_end_index == 8
    
    def test_optional_fields(self):
        """Should handle optional fields correctly."""
        selection = V2ContentSelection(
            expression="test",
            expression_translation="테스트",
            title="테스트 제목",
            title_translation="Título de prueba",
            expression_dialogue_index=0,
            context_start_index=0,
            context_end_index=1,
            catchy_keywords=["키워드1", "키워드2"],
            scene_type="humor",
            viral_title="Viral Title",
            intro_hook="¿Sabías que...?",
        )
        
        assert selection.title == "테스트 제목"
        assert len(selection.catchy_keywords) == 2
        assert selection.scene_type == "humor"
        assert selection.viral_title == "Viral Title"
        assert selection.intro_hook == "¿Sabías que...?"
    
    def test_with_vocabulary_annotations(self):
        """Should handle vocabulary annotations."""
        selection = V2ContentSelection(
            expression="test",
            expression_translation="테스트",
            title="Title",
            title_translation="Título",
            expression_dialogue_index=0,
            context_start_index=0,
            context_end_index=1,
            vocabulary_annotations=[
                V2VocabularyAnnotation(word="knock", translation="치다", dialogue_index=0),
                V2VocabularyAnnotation(word="park", translation="공원", dialogue_index=0),
            ]
        )
        
        assert len(selection.vocabulary_annotations) == 2
        assert selection.vocabulary_annotations[0].word == "knock"


class TestEnrichFromSubtitles:
    """Tests for enrich_from_subtitles function."""
    
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
            {"index": 0, "text": "¡Hola!", "start": "00:00:01,000", "end": "00:00:02,000"},
            {"index": 1, "text": "¿Cómo estás?", "start": "00:00:03,000", "end": "00:00:04,000"},
            {"index": 2, "text": "Lo haré perfectamente.", "start": "00:00:05,000", "end": "00:00:07,000"},
            {"index": 3, "text": "¡Genial!", "start": "00:00:08,000", "end": "00:00:09,000"},
        ]
        return source, target
    
    def test_enrich_populates_times(self, sample_dialogues):
        """Should populate context times from source dialogues."""
        source, target = sample_dialogues
        
        selection = V2ContentSelection(
            expression="knock it out of the park",
            expression_translation="Lo haré perfectamente",
            title="Expression Title",
            title_translation="Título",
            expression_dialogue_index=2,
            context_start_index=1,
            context_end_index=3,
        )
        
        enriched = enrich_from_subtitles(selection, source, target)
        
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
            {"index": 0, "text": "¡Hola!", "start": "00:00:01,000", "end": "00:00:02,000"},
            {"index": 1, "text": "Lo haré perfectamente.", "start": "00:00:03,000", "end": "00:00:05,000"},
            {"index": 2, "text": "¡Genial!", "start": "00:00:06,000", "end": "00:00:07,000"},
        ]
        return source, target
    
    def test_convert_creates_v1_format(self, sample_dialogues):
        """Should convert V2 selection to V1-compatible dict."""
        source, target = sample_dialogues
        
        selection = V2ContentSelection(
            expression="knock it out of the park",
            expression_translation="Lo haré perfectamente",
            title="완벽한 자신감",
            title_translation="Confianza perfecta",
            expression_dialogue_index=1,
            context_start_index=0,
            context_end_index=2,
            catchy_keywords=["자신감 폭발"],
            scene_type="drama",
            similar_expressions=["hit it out of the park"],
        )
        
        # Enrich first
        enriched = enrich_from_subtitles(selection, source, target)
        
        # Convert to V1
        v1 = convert_v2_to_v1_format(enriched, source, target)
        
        assert v1['expression'] == "knock it out of the park"
        assert v1['expression_translation'] == "Lo haré perfectamente"
        assert v1['title'] == "완벽한 자신감"
        assert v1['title_translation'] == "Confianza perfecta"
        assert len(v1['dialogues']) == 3
        assert len(v1['translation']) == 3
        assert v1['dialogues'][1] == "I'll knock it out of the park."
        assert v1['translation'][1] == "Lo haré perfectamente."
        assert v1['scene_type'] == "drama"
        
        # V2 addition: dialogue_entries with timing
        assert 'dialogue_entries' in v1
        assert len(v1['dialogue_entries']) == 3
        assert v1['dialogue_entries'][1]['text'] == "I'll knock it out of the park."
        assert v1['dialogue_entries'][1]['translation'] == "Lo haré perfectamente."
        assert v1['dialogue_entries'][1]['start_time'] == "00:00:03,000"


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
                expression_translation="테스트1",
                title="Title1",
                title_translation="Título1",
                expression_dialogue_index=0,
                context_start_index=0,
                context_end_index=1,
            ),
            V2ContentSelection(
                expression="test2",
                expression_translation="테스트2",
                title="Title2",
                title_translation="Título2",
                expression_dialogue_index=2,
                context_start_index=2,
                context_end_index=3,
            ),
        ]
        
        response = V2ContentSelectionResponse(expressions=selections)
        
        assert len(response.expressions) == 2
        assert response.expressions[0].expression == "test1"
        assert response.expressions[1].expression == "test2"
