#!/usr/bin/env python3
"""
Quick test script to verify background music application works
"""

import sys
from pathlib import Path
from langflix.core.models import ExpressionAnalysis
from langflix.core.video_editor import VideoEditor

# Create a test expression with background music
test_expression = ExpressionAnalysis(
    dialogues=["This is hilarious!", "I can't stop laughing!"],
    translation=["이건 정말 웃겨!", "웃음이 멈추지 않아!"],
    expression_dialogue="This is hilarious!",
    expression_dialogue_translation="이건 정말 웃겨!",
    expression="this is hilarious",
    expression_translation="정말 웃긴",
    context_start_time="00:00:00,000",
    context_end_time="00:00:05,000",
    similar_expressions=["this is funny", "this is amusing"],
    background_music_id="comedic_funny",  # ← Background music ID
    background_music_reasoning="Humorous scene with laughter"
)

print("=" * 60)
print("🎵 Background Music Application Test")
print("=" * 60)
print()
print(f"Expression: {test_expression.expression}")
print(f"Music ID: {test_expression.background_music_id}")
print(f"Reasoning: {test_expression.background_music_reasoning}")
print()

# Check if music file exists
from langflix.config.config_loader import ConfigLoader
config_loader = ConfigLoader()
bg_music_config = config_loader.config.get('background_music') or {}
music_dir = bg_music_config.get('music_directory', 'assets/background_music')
music_library = bg_music_config.get('library', {})

if test_expression.background_music_id in music_library:
    music_file = music_library[test_expression.background_music_id].get('file')
    music_path = Path(music_dir) / music_file
    print(f"Music file: {music_path}")
    print(f"File exists: {music_path.exists()}")

    if music_path.exists():
        # Get file size
        file_size = music_path.stat().st_size / 1024 / 1024  # MB
        print(f"File size: {file_size:.2f} MB")

        # Get duration
        import subprocess
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', str(music_path)],
            capture_output=True,
            text=True
        )
        duration = float(result.stdout.strip())
        print(f"Duration: {duration:.2f} seconds")
        print()
        print("✅ Music file is ready!")
    else:
        print(f"❌ Music file not found: {music_path}")
else:
    print(f"❌ Music ID '{test_expression.background_music_id}' not in library")

print()
print("=" * 60)
print("To test with actual video:")
print("1. Clear cache: rm -rf cache/")
print("2. Run pipeline with a subtitle file")
print("3. Check logs for: 'Applying background music: comedic_funny'")
print("=" * 60)
