#!/usr/bin/env python3
"""
Debug script to test concat demuxer with actual files
"""
import sys
sys.path.insert(0, '.')
from pathlib import Path
import ffmpeg
import subprocess

# Test concat demuxer with actual files from context_videos
context_videos_dir = Path("output/Suits/S01E02_720p.HDTV.x264/translations/ja/context_videos")
context_videos = sorted(list(context_videos_dir.glob("context_*.mkv")))

if not context_videos:
    print("No context videos found!")
    sys.exit(1)

test_video = context_videos[0]
print(f"Testing with: {test_video}")

# Create concat file
concat_file = Path("test_concat.txt")
with open(concat_file, 'w') as f:
    f.write(f"file '{test_video.absolute()}'\n")
    f.write(f"file '{test_video.absolute()}'\n")

print(f"\nConcat file created:")
with open(concat_file) as f:
    print(f.read())

# Try concat
output_path = Path("test_concat_output.mkv")
print(f"\nRunning concat...")

try:
    (ffmpeg.input(str(concat_file), format='concat', safe=0)
     .output(str(output_path), vcodec='libx264', preset='fast', crf=23)
     .overwrite_output()
     .run(quiet=True))
    print(f"✅ Success! Output: {output_path}")
    if output_path.exists():
        # Probe the output
        probe = ffmpeg.probe(str(output_path))
        duration = float(probe['format']['duration'])
        print(f"   Duration: {duration:.2f}s")
except ffmpeg.Error as e:
    print(f"❌ FFmpeg error: {e}")
    if e.stderr:
        print(f"Stderr: {e.stderr.decode()}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Cleanup
if concat_file.exists():
    concat_file.unlink()
if output_path.exists():
    output_path.unlink()
    print(f"\nCleaned up test files")
