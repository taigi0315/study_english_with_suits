#!/usr/bin/env python3
"""
Test script to regenerate short videos for S01E02 to verify the fix
"""
import sys
sys.path.insert(0, '.')

from langflix.main import LangFlixPipeline
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

# Initialize pipeline for S01E02, ja language
pipeline = LangFlixPipeline(
    subtitle_file='assets/media/Suits/Suits.S01E02.720p.HDTV.x264.srt',
    video_dir='assets/media/Suits',
    output_dir='output',
    language_code='ja'
)

print("\n=== Creating short videos for S01E02 ===")
try:
    pipeline._create_short_videos()
    print("\n✅ Short videos created successfully!")
except Exception as e:
    print(f"\n❌ Error creating short videos: {e}")
    import traceback
    traceback.print_exc()
