"""
Pydantic models for structured output from Gemini API
"""
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, field_validator


class VocabularyAnnotation(BaseModel):
    """
    Model for a vocabulary word annotation that appears dynamically in the video
    """
    word: str = Field(
        description="The vocabulary word or phrase to annotate"
    )
    translation: str = Field(
        description="Translation of the word in the target language"
    )
    dialogue_index: int = Field(
        default=0,
        description="0-indexed position in the dialogues array where this word appears",
        ge=0
    )


class ExpressionAnalysis(BaseModel):
    """
    Model for a single expression analysis result
    """
    title: Optional[str] = Field(
        default=None,
        description="Catchy Korean title (8-15 words) for video, in target language NOT English. Examples: '회사에서 상사에게 참교육 당하는 순간', '어제 나를 해고한 상사가 백지수표를 들고 찾아왔다'"
    )
    dialogues: List[str] = Field(
        description="Complete dialogue lines in the scene",
        min_length=1
    )
    translation: List[str] = Field(
        description="Translations of all dialogue lines in the same order",
        min_length=1
    )
    expression_dialogue: str = Field(
        description="The complete dialogue line that contains the expression",
        min_length=1
    )
    expression_dialogue_translation: str = Field(
        description="Translation of the dialogue line containing the expression",
        min_length=1
    )
    expression: str = Field(
        description="The main expression/phrase to learn (key part extracted from expression_dialogue)",
        min_length=1
    )
    expression_translation: str = Field(
        description="Translation of the main expression",
        min_length=1
    )
    context_start_time: Optional[str] = Field(
        default=None,
        description="Timestamp where conversational context should BEGIN",
        pattern=r"^\d{2}:\d{2}:\d{2}[.,]\d{3,6}$"
    )
    context_end_time: Optional[str] = Field(
        default=None,
        description="Timestamp where conversational context should END", 
        pattern=r"^\d{2}:\d{2}:\d{2}[.,]\d{3,6}$"
    )
    expression_start_time: Optional[str] = Field(
        default=None,
        description="Exact timestamp where the expression phrase begins (for audio extraction)",
        pattern=r"^\d{2}:\d{2}:\d{2}[.,]\d{3,6}$"
    )
    expression_end_time: Optional[str] = Field(
        default=None,
        description="Exact timestamp where the expression phrase ends (for audio extraction)",
        pattern=r"^\d{2}:\d{2}:\d{2}[.,]\d{3,6}$"
    )
    similar_expressions: List[str] = Field(
        description="List of 1-3 similar expressions or alternative ways to say the same thing",
        min_length=1,
    )
    scene_type: Optional[str] = Field(
        default=None,
        description="Type of scene: humor, drama, tension, emotional, witty, confrontation, etc."
    )
    catchy_keywords: Optional[List[str]] = Field(
        default=None,
        description="2-3 catchy Korean phrases (3-6 words each) in target language, NOT English. Examples: '상사의 뼈때리는 한마디', '숨겨진 속내 드러나다'"
    )
    vocabulary_annotations: Optional[List[VocabularyAnnotation]] = Field(
        default=None,
        description="1-3 vocabulary words with translations for dynamic video overlays"
    )

    # New fields for expression-based learning
    difficulty: Optional[int] = Field(
        default=5,
        description="Difficulty level from 1 (beginner) to 10 (advanced)",
        ge=1,
        le=10
    )
    category: Optional[str] = Field(
        default="general",
        description="Expression category (idiom, slang, formal, greeting, cultural, etc.)"
    )
    educational_value: Optional[str] = Field(
        default="",
        description="Explanation of why this expression is valuable for learning"
    )
    usage_notes: Optional[str] = Field(
        default="",
        description="Additional context about when and how to use this expression"
    )
    
    # Phase 2: Expression ranking fields
    educational_value_score: float = Field(
        default=5.0,
        description="Educational value score (0-10) for ranking expressions",
        ge=0.0,
        le=10.0
    )
    frequency: int = Field(
        default=1,
        description="Frequency of the expression in the content",
        ge=1
    )
    context_relevance: float = Field(
        default=5.0,
        description="Relevance of the context to the expression (0-10)",
        ge=0.0,
        le=10.0
    )
    ranking_score: float = Field(
        default=0.0,
        description="Calculated ranking score for expression selection"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "dialogues": [
                    "I'm paying you millions,",
                    "and you're telling me I'm gonna get screwed?"
                ],
                "translation": [
                    "나는 당신에게 수백만 달러를 지불하고 있는데,",
                    "당신은 내가 속임을 당할 것이라고 말하고 있나요?"
                ],
                "expression_dialogue": "and you're telling me I'm gonna get screwed?",
                "expression_dialogue_translation": "당신은 내가 속임을 당할 것이라고 말하고 있나요?",
                "expression": "I'm gonna get screwed",
                "expression_translation": "속임을 당할 것 같아요",
                "context_start_time": "00:01:25,657",
                "context_end_time": "00:01:32,230",
                "similar_expressions": [
                    "I'm going to be cheated",
                    "I'm getting the short end of the stick"
                ]
            }
        }
    }


class ExpressionAnalysisResponse(BaseModel):
    """
    Model for the complete response from Gemini API
    """
    expressions: List[ExpressionAnalysis] = Field(
        description="List of analyzed expressions",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "expressions": [
                    {
                        "dialogues": [
                            "I'm paying you millions,",
                            "and you're telling me I'm gonna get screwed?"
                        ],
                        "translation": [
                            "나는 당신에게 수백만 달러를 지불하고 있는데,",
                            "당신은 내가 속임을 당할 것이라고 말하고 있나요?"
                        ],
                        "expression_dialogue": "and you're telling me I'm gonna get screwed?",
                        "expression_dialogue_translation": "당신은 내가 속임을 당할 것이라고 말하고 있나요?",
                        "expression": "I'm gonna get screwed",
                        "expression_translation": "속임을 당할 것 같아요",
                        "context_start_time": "00:01:25,657",
                        "context_end_time": "00:01:32,230",
                        "similar_expressions": [
                            "I'm going to be cheated",
                            "I'm getting the short end of the stick"
                        ]
                    }
                ]
            }
        }
    }
