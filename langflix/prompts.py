from typing import List
from . import config

def get_prompt_for_chunk(subtitle_chunk: List[dict]) -> str:
    """
    Generates the prompt for the LLM based on a chunk of subtitles.
    """
    dialogues = "\\n".join([f"[{sub['start_time']}-{sub['end_time']}] {sub['text']}" for sub in subtitle_chunk])

    prompt = f"""
Here is a segment of dialogue from the TV show "Suits":

---
{dialogues}
---

Your task is to act as an English language expert. From the dialogue provided, identify ONLY the MOST VALUABLE expressions, idioms, or phrases that would be extremely useful for an English learner.

**SELECTION CRITERIA - Choose ONLY expressions that are:**
- Commonly used in real conversations
- Not too basic (avoid simple words like "hello", "yes", "no")
- Not too advanced (avoid highly technical legal/business jargon)
- Idiomatic expressions, phrasal verbs, or colloquial phrases
- Maximum 5 expressions (can be fewer if not enough good ones)

For each expression you identify, you MUST provide the following in a valid JSON format:
1.  `dialogues`: A list of ALL dialogue lines in the scene (complete conversation between start and end time)
2.  `translation`: A list of translations of ALL dialogue lines into {config.TARGET_LANGUAGE} (same order as dialogues)
3.  `expression`: The main expression/phrase to learn (string)
4.  `expression_translation`: Translation of the main expression into {config.TARGET_LANGUAGE} (string)
5.  `context_start_time`: The timestamp where the conversational context should BEGIN
6.  `context_end_time`: The timestamp where the conversational context should END
7.  `similar_expressions`: A list of 1-2 similar expressions or alternative ways to say the same thing

**CRITICAL REQUIREMENTS:**
- `dialogues` must include ALL dialogue lines in the scene (complete conversation)
- `translation` must include CONTEXTUAL translations of ALL dialogue lines - understand the full context, character relationships, and situation before translating. Do NOT provide literal word-for-word translations.
- `expression` should be the key phrase/idiom to learn from the scene
- `expression_translation` should be the CONTEXTUAL translation of just the main expression - understand the meaning and context, not just literal translation
- Context should be wide enough to show the full conversational flow and meaning
- Choose ONLY the most valuable expressions - quality over quantity
- Maximum 5 expressions total

**TRANSLATION GUIDELINES:**
- Understand the ENTIRE context of the conversation, character relationships, and situation
- Provide translations that capture the MEANING and INTENT, not just literal words
- Consider the tone, emotion, and cultural context of the dialogue
- Make translations natural and understandable in {config.TARGET_LANGUAGE}

Example of a single JSON object in the list:
{{
  "dialogues": [
    "I'm paying you millions,",
    "and you're telling me I'm gonna get screwed?"
  ],
  "translation": [
    "나는 당신에게 수백만 달러를 지불하고 있는데,",
    "당신은 내가 속임을 당할 것이라고 말하고 있나요?"
  ],
  "expression": "I'm gonna get screwed",
  "expression_translation": "속임을 당할 것 같아요",
  "context_start_time": "00:01:25,657",
  "context_end_time": "00:01:32,230",
  "similar_expressions": [
    "I'm going to be cheated",
    "I'm getting the short end of the stick"
  ]
}}

Now, analyze the provided dialogue and return the JSON list with ONLY the most valuable expressions.
"""
    return prompt
