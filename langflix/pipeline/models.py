"""
Pipeline Data Models
Defines data structures for the Contextual Localization Pipeline
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ChunkResult(BaseModel):
    """
    Result from Script Agent processing a single chunk
    Includes both expressions and chunk summary
    """
    chunk_id: int = Field(..., description="Sequential chunk number")
    chunk_summary: str = Field(..., description="2-3 sentence summary with emotional context")
    expressions: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted expressions")

    class Config:
        json_schema_extra = {
            "example": {
                "chunk_id": 1,
                "chunk_summary": "Harvey angrily confronts Mike about a missing document, asserting his authority. Mike is apologetic but defensive.",
                "expressions": [
                    {
                        "expression": "cut him loose",
                        "expression_dialogue": "You need to cut him loose before he drags you down.",
                    }
                ]
            }
        }


class EpisodeData(BaseModel):
    """
    Complete data for an episode
    Includes all chunk results
    """
    episode_id: str = Field(..., description="Unique episode identifier")
    show_name: str = Field(..., description="Name of the show")
    show_bible: str = Field(..., description="Show Bible content")
    chunks: List[ChunkResult] = Field(default_factory=list, description="All processed chunks")
    master_summary: Optional[str] = Field(None, description="DEPRECATED: No longer generated (Aggregator removed)")

    def get_all_expressions(self) -> List[Dict[str, Any]]:
        """Get all expressions from all chunks"""
        all_expressions = []
        for chunk in self.chunks:
            all_expressions.extend(chunk.expressions)
        return all_expressions

    def get_all_chunk_summaries(self) -> List[str]:
        """Get all chunk summaries in order"""
        return [chunk.chunk_summary for chunk in self.chunks]


class DialogueEntry(BaseModel):
    """
    Single dialogue entry with timing information
    Used in bilingual subtitle extraction
    """
    index: int = Field(..., description="Subtitle index matching original")
    timestamp: str = Field(..., description="SRT timestamp format (HH:MM:SS,mmm --> HH:MM:SS,mmm)")
    text: str = Field(..., description="Dialogue text in respective language")


class LocalizationData(BaseModel):
    """
    Localization data for a single expression
    Context-aware translations

    NOTE: This model is no longer actively used. The unified architecture
    includes translations directly in the dialogues field.
    """
    target_lang: str = Field(..., description="Target language code (e.g., 'ko', 'ja', 'es')")
    target_lang_name: str = Field(..., description="Target language name (e.g., 'Korean', 'Japanese')")
    expression_translated: str = Field(..., description="Naturalized translation of expression")
    expression_dialogue_translated: str = Field(..., description="Translation reflecting tone/hierarchy")
    catchy_keywords_translated: List[str] = Field(default_factory=list, description="Localized keywords")
    viral_title: Optional[str] = Field(None, description="Viral/Clickbaity string for the video title")
    narrations: List[Any] = Field(default_factory=list, description="Short narration lines explaining text")
    vocabulary_annotations: List[Dict[str, Any]] = Field(default_factory=list, description="List of vocab items: [{'word': '...', 'meaning': '...', 'example': '...', 'dialogue_index': 5}]")
    expression_annotations: List[Dict[str, Any]] = Field(default_factory=list, description="List of expression parts: [{'word': '...', 'translation': '...', 'dialogue_index': 7}]")
    translation_notes: Optional[str] = Field(None, description="Notes about honorifics/formality applied")

    class Config:
        json_schema_extra = {
            "example": {
                "target_lang": "ko",
                "target_lang_name": "Korean",
                "expression_translated": "손절해",
                "expression_dialogue_translated": "그 사람이 너까지 끌어내리기 전에 손절해야 돼.",
                "catchy_keywords_translated": ["냉정한 손절", "하비의 조언", "위기 상황"],
                "translation_notes": "Used 반말 for Harvey (senior) speaking"
            }
        }


class TranslationResult(BaseModel):
    """
    Final multilingual expression data combining English + localization
    """
    # Original English data
    expression: str
    expression_dialogue: str
    context_summary_eng: Optional[str] = None

    # Context timing (for video clip extraction)
    start_time: str  # context_start_time
    end_time: str    # context_end_time

    # Expression timing (for highlighting the specific expression)
    expression_start_time: Optional[str] = None
    expression_end_time: Optional[str] = None

    # Bilingual dialogues (for subtitle mapping)
    # Format: {"en": [{"index": 3, "timestamp": "...", "text": "..."}], "ko": [...]}
    dialogues: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    
    scene_type: Optional[str] = None
    similar_expressions: List[str] = Field(default_factory=list)
    catchy_keywords: List[str] = Field(default_factory=list)

    # Chunk context
    chunk_id: int
    chunk_summary: str = Field(..., description="Micro-context from Script Agent")

    # Episode context
    episode_summary: Optional[str] = Field(None, description="DEPRECATED: No longer generated (Aggregator removed)")

    # Multilingual localizations
    localizations: List[LocalizationData] = Field(default_factory=list, description="Translations with context")

    def get_localization(self, target_lang: str) -> Optional[LocalizationData]:
        """Get localization for specific language"""
        for loc in self.localizations:
            if loc.target_lang == target_lang:
                return loc
        return None

    class Config:
        json_schema_extra = {
            "example": {
                "expression": "cut him loose",
                "expression_dialogue": "You need to cut him loose before he drags you down.",
                "chunk_id": 5,
                "chunk_summary": "Harvey advises Jessica to fire a problematic client, showing his pragmatic authority.",
                "start_time": "00:12:30.500",
                "end_time": "00:12:35.000",
                "localizations": [
                    {
                        "target_lang": "ko",
                        "target_lang_name": "Korean",
                        "expression_translated": "손절해",
                        "expression_dialogue_translated": "그 사람이 너까지 끌어내리기 전에 손절해야 돼."
                    }
                ]
            }
        }


class PipelineConfig(BaseModel):
    """
    Configuration for pipeline execution
    """
    show_name: str
    episode_name: str
    source_language: Optional[str] = Field("English", description="Source language name (e.g. English, Korean)")
    target_languages: List[str] = Field(default_factory=list, description="DEPRECATED: Language codes - now handled in ScriptAgent via settings")
    use_wikipedia: bool = Field(True, description="Whether to fetch Show Bible from Wikipedia")
    cache_show_bible: bool = Field(True, description="Cache Show Bible for reuse")
    output_dir: Optional[str] = Field(None, description="Output directory for results and debug info")

    class Config:
        json_schema_extra = {
            "example": {
                "show_name": "Suits",
                "episode_name": "S01E01",
                "target_languages": ["ko", "ja", "es"],
                "use_wikipedia": True
            }
        }
