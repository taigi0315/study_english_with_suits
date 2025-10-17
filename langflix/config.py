# Configuration for the LangFlix application

# The maximum number of characters to include in a single prompt to the LLM.
# This is to avoid exceeding the model's context window limit.
# Subtitles will be chunked to respect this limit.
MAX_LLM_INPUT_LENGTH = 4000

# The target language for translation.
TARGET_LANGUAGE = "Korean"
