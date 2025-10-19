from typing import List
from . import settings
from .language_config import LanguageConfig

def get_prompt_for_chunk(subtitle_chunk: List[dict], language_level: str = None, language_code: str = "ko") -> str:
    """
    Generates the prompt for the LLM based on a chunk of subtitles.
    
    Args:
        subtitle_chunk: List of subtitle dictionaries
        language_level: Target language level (beginner, intermediate, advanced, mixed)
        language_code: Target language code (ko, ja, zh, es, fr)
    """
    # Use default language level if not specified
    if language_level is None:
        language_level = settings.DEFAULT_LANGUAGE_LEVEL
    
    # Get level description
    level_description = settings.LANGUAGE_LEVELS[language_level]["description"]
    
    # Get language-specific settings
    lang_config = LanguageConfig.get_config(language_code)
    target_language = lang_config['prompt_language']
    
    dialogues = "\\n".join([f"[{sub['start_time']}-{sub['end_time']}] {sub['text']}" for sub in subtitle_chunk])

    prompt = f"""
Here is a segment of dialogue from the TV show "Suits":

---
{dialogues}
---

**YOUR ROLE:**
You are an expert English language educator specializing in teaching through authentic media content.

**LANGUAGE LEVEL TARGET:**
{level_description}

**YOUR TASK:**
Analyze this dialogue and identify the MOST VALUABLE expressions for learners at this level. Extract scenes that are:
1. **Educationally Valuable** - Contains useful, practical expressions
2. **Engaging & Entertaining** - Dynamic, humorous, dramatic, tense, emotional, or compelling moments
3. **Contextually Clear** - Can be understood as a standalone short video

---

**EXPRESSION SELECTION CRITERIA:**

Choose ONLY expressions that meet your target language level AND are:
- Commonly used in real conversations (not overly formal or archaic)
- Idiomatic expressions, phrasal verbs, or colloquial phrases
- Practical and reusable in various contexts
- Natural-sounding in modern English

**AVOID:**
- Boring, plain, or mundane exchanges with no emotional energy
- Overly simple greetings (unless they have interesting usage)
- Very formal legal jargon (unless it's a commonly used phrase)
- Expressions that are too obvious or self-explanatory

---

**SCENE ENGAGEMENT CRITERIA (HIGH PRIORITY):**

Prioritize scenes that are:
✓ **Humorous** - Funny moments, jokes, witty comebacks
✓ **Dramatic** - Tension, conflict, confrontation, revelations
✓ **Emotional** - Anger, surprise, excitement, frustration, joy
✓ **Dynamic** - Fast-paced exchanges, heated debates
✓ **Intriguing** - Plot twists, secrets revealed, power dynamics
✓ **Relatable** - Universal situations people encounter

**REJECT scenes that are:**
✗ Mundane procedural dialogue
✗ Boring exposition or background information
✗ Flat, emotionless exchanges
✗ Simple information delivery without personality

---

**CONTEXT & TIME SLICING REQUIREMENTS (CRITICAL):**

**BEFORE selecting start/end times, you MUST:**
1. **Understand the full narrative** - What happens before, during, and after the expression
2. **Identify the dramatic arc** - Where does the tension/humor/emotion build and resolve?
3. expression should be in the middle of the context
4. Use comma separated for multiple expressions (no othe special characters)

**When selecting `context_start_time` and `context_end_time`:**

✓ **Start EARLY enough** to establish:
   - WHO is speaking (character introduction/identification)
   - WHERE they are (setting/situation)
   - WHAT is happening (the problem/topic/conflict)
   - WHY this conversation is happening (motivation/stakes)

✓ **End LATE enough** to include:
   - The complete expression and its immediate impact
   - The reaction or response to the expression
   - A sense of closure or completion (not mid-thought)

✓ **Target Duration:** 10-25 seconds
   - Must feel complete, not abruptly cut

✓ **Self-Contained Understanding:**
   - Someone watching ONLY this clip (no prior knowledge of the show) should understand:
     * What situation they're in
     * Why this expression matters
     * The emotional tone/stakes

✓ **Natural Cut Points - Start the clip:**
   - At the beginning of a new conversational topic
   - When a character enters or initiates a new exchange
   - After a natural pause or scene shift
   - At the start of a question-answer sequence

✓ **Natural Cut Points - End the clip:**
   - After a complete thought or statement
   - After a reaction that provides closure
   - At a natural pause or transition
   - When the tension/humor/emotion resolves or reaches a peak

**AVOID:**
✗ Starting mid-sentence or mid-thought
✗ Ending abruptly without any response or closure
✗ Clips that feel like random fragments
✗ Requiring prior knowledge of the show to understand
✗ Cutting off important reactions or payoffs

---

**OUTPUT FORMAT:**

Return a JSON list where each object contains:

{{
  "dialogues": [
    // ALL dialogue lines in the scene (complete conversation between start and end time)
    // IMPORTANT: Use EXACT dialogue text from subtitles - DO NOT add speaker names like "Mike:" or "Rachel:"
    // Keep the original subtitle format as-is
  ],
  "translation": [
    // CRITICAL: EXACT 1:1 MAPPING - MUST have same number of items as dialogues array
    // CONTEXTUAL translations of ALL dialogue lines in {target_language}
    // Translate MEANING and INTENT, not literal words
    // Consider tone, emotion, relationships, and cultural context
    // REQUIRED: Each dialogue line MUST have exactly one corresponding translation line
  ],
  "expression": "the main expression/phrase to learn",
  "expression_translation": "contextual translation of the main expression in {target_language}",
  "context_start_time": "00:00:00,000",  // When context begins
  "context_end_time": "00:00:00,000",    // When context ends
  "similar_expressions": [
    // 1-3 similar expressions or alternative ways to say the same thing
    // Include both formal and informal alternatives when relevant
  ],
  "scene_type": "humor|drama|tension|emotional|witty|confrontation",  // What makes this scene engaging
  "why_valuable": "Brief explanation of why this expression and scene are valuable for learners"
}}

**FINAL REQUIREMENTS:**
- Maximum 5 expressions total
- Quality over quantity - be selective
- Each scene must be engaging AND educational
- Prioritize expressions at the target language level: {level_description}
- Ensure each clip is self-contained and understandable
- Verify start/end times create natural, complete moments

**CRITICAL: DIALOGUE FORMAT REQUIREMENTS:**
- Use EXACT dialogue text from the provided subtitles
- DO NOT add speaker names like "Mike:", "Rachel:", "Harvey:" etc.
- DO NOT modify the original dialogue text
- Keep the subtitle format exactly as provided
- The dialogues array should contain the raw subtitle text only

**CRITICAL: VALIDATION REQUIREMENTS:**
- The `dialogues` and `translation` arrays MUST have EXACTLY the same number of elements
- Each dialogue line must have exactly one corresponding translation line
- NO EXCEPTIONS: If you cannot provide a translation for every dialogue line, DO NOT include that expression
- Double-check your arrays before returning the JSON

Now analyze the provided dialogue and return the JSON list with ONLY the most valuable, engaging expressions.
"""
    return prompt
