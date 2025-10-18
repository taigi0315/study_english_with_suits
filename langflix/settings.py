# Settings for the LangFlix application

# The maximum number of characters to include in a single prompt to the LLM.
# Gemini 2.5 Flash supports up to 1,048,576 tokens (~4M characters)
# We use a conservative limit to ensure prompt + dialogue fits comfortably
MAX_LLM_INPUT_LENGTH = 5000  # Further reduced to ensure API success

# The target language for translation.
TARGET_LANGUAGE = "Korean"

# Default language level for expression analysis
DEFAULT_LANGUAGE_LEVEL = "intermediate"

LANGUAGE_LEVELS = {
    "beginner": {
        "description": "A1-A2 level. Focus on basic everyday expressions, simple phrasal verbs, and common conversational phrases used in daily life. Avoid complex idioms or advanced vocabulary.",
        "examples": "Let's go, I'm sorry, How are you, Can you help me, What's up"
    },
    "intermediate": {
        "description": "B1-B2 level. Focus on commonly used idiomatic expressions, standard phrasal verbs, and colloquial phrases that appear frequently in casual and professional contexts.",
        "examples": "Get the ball rolling, Call it a day, Piece of cake, Break the ice, On the same page"
    },
    "advanced": {
        "description": "C1-C2 level. Focus on sophisticated idioms, nuanced expressions, professional jargon, and complex colloquialisms that native speakers use in various contexts.",
        "examples": "Read between the lines, Cut to the chase, Play devil's advocate, Bite off more than you can chew"
    },
    "mixed": {
        "description": "All levels. Extract valuable expressions regardless of difficulty level, but prioritize practical, commonly-used phrases that appear in authentic conversations.",
        "examples": "Any useful expression from basic to advanced"
    }
}