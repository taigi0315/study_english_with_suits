"""
Pydantic models for structured output from Gemini API
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class ExpressionAnalysis(BaseModel):
    """
    Model for a single expression analysis result
    """
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
    context_start_time: str = Field(
        description="Timestamp where conversational context should BEGIN",
        pattern=r"^\d{2}:\d{2}:\d{2}[.,]\d{3,6}$"
    )
    context_end_time: str = Field(
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
