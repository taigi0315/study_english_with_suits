# Project: LangFlix - Learn English with Your Favorite Shows

## 1. High-Level Goal

The goal of this project is to create a tool that automatically generates short, educational videos from a given TV show episode and its subtitle file. These videos will be designed to help users learn English expressions in context.

## 2. Features

*   **Expression Extraction:** Identify and extract English expressions, idioms, and useful vocabulary from the subtitle file.
*   **Contextual Video Clips:** For each expression, create a video clip that includes the dialogue where the expression is used, along with some surrounding context to aid understanding.
*   **Learning Content Generation:** For each expression, the tool will generate:
    *   The definition and meaning of the expression.
    *   The start and end times of the relevant video segment.
    *   Translation of the expression into a user-specified language (e.g., Korean).
    *   Examples of similar expressions or alternative ways to say the same thing.
*   **Automated Video Creation:** Stitch together the video clips and the generated learning content into a final educational video.

## 3. Project Workflow

### 3.1. Inputs

*   A video file of a TV show episode (e.g., `Suits_S01E01.mp4`).
*   A corresponding subtitle file in a standard format like `.srt` or `.vtt`, which includes dialogue and timestamps.

### 3.2. Processing Pipeline

1.  **Subtitle Parsing:**
    *   Read the subtitle file.
    *   Parse the dialogues and their corresponding timestamps. Each dialogue entry should have a start time, end time, and the text.

2.  **Expression Analysis (using LLM):**
    *   Feed the dialogues into a Large Language Model (LLM).
    *   The LLM will be prompted to:
        *   Identify key expressions worth learning.
        *   For each expression, determine the most relevant time range `[start_time, end_time]` in the video. This range should be slightly wider than the exact moment the expression is spoken to provide context.
        *   Provide a simple definition of the expression.
        *   Translate the expression into a target language.
        *   Generate a few examples of similar expressions or usage in different contexts.

3.  **Video Clip Extraction:**
    *   Using a video processing library (like `ffmpeg` or `moviepy`), extract the video segments based on the `[start_time, end_time]` ranges identified by the LLM.

4.  **Educational Video Assembly:**
    *   For each expression:
        1.  Create a title card with the expression and its translation.
        2.  Show the extracted video clip.
        3.  Display an explanation card with the definition and similar expressions.
    *   Combine all these small segments into a single output video file.

### 3.3. Outputs

*   A final video file (e.g., `Suits_S01E01_study_guide.mp4`) that is ready for viewing.
*   A structured data file (e.g., JSON) containing the extracted expressions, timestamps, translations, and examples for potential future use.

## 4. Technical Considerations

*   **Subtitle Parsing:** Use a Python library like `pysrt` or `webvtt-py` to handle different subtitle formats.
*   **LLM Integration:** Use a library like `openai` to interact with a powerful Large Language Model for the analysis part. Careful prompt engineering will be crucial to get the desired output quality.
*   **Video Processing:** `ffmpeg-python` is a good choice for programmatically cutting and merging video clips.
*   **Configuration:** The target language for translation and other parameters should be configurable.
