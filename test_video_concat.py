#!/usr/bin/env python3
"""
Test script for video concatenation
"""

import sys
from pathlib import Path
import logging
import ffmpeg

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

def test_video_concatenation():
    """Test concatenating multiple videos into one"""
    
    # Get all expression videos
    output_dir = Path("output")
    video_files = list(output_dir.glob("expression_*.mkv"))
    
    if not video_files:
        logger.error("No video files found in output directory")
        return
    
    # Sort by filename
    video_files.sort()
    
    logger.info(f"Found {len(video_files)} video files")
    for video in video_files:
        logger.info(f"  - {video.name}")
    
    # Create concat file
    concat_file = output_dir / "concat_list.txt"
    with open(concat_file, 'w') as f:
        for video in video_files:
            f.write(f"file '{video.absolute()}'\n")
    
    # Output file
    output_video = output_dir / "final_educational_sequence.mkv"
    
    try:
        logger.info("Concatenating videos...")
        
        # Concatenate all videos
        (
            ffmpeg
            .input(str(concat_file), format='concat', safe=0)
            .output(str(output_video),
                   vcodec='libx264',
                   acodec='aac',
                   preset='fast',
                   crf=23,
                   af='pan=stereo|c0=c0+c2+c4|c1=c1+c3+c5')  # Convert 5.1 to stereo
            .overwrite_output()
            .run(quiet=False)
        )
        
        logger.info(f"✅ Final video created: {output_video}")
        
        # Get video info
        probe = ffmpeg.probe(str(output_video))
        duration = float(probe['format']['duration'])
        logger.info(f"📹 Video duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        
    except Exception as e:
        logger.error(f"❌ Error concatenating videos: {e}")
        raise

if __name__ == "__main__":
    test_video_concatenation()
