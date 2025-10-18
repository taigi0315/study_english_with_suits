#!/usr/bin/env python3
"""
Add subtitles directly to video files
"""

import sys
from pathlib import Path
import logging
import ffmpeg
import json

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

def add_subtitles_to_video(video_path: str, subtitle_path: str, output_path: str):
    """Add subtitles directly to video"""
    try:
        logger.info(f"Adding subtitles to {video_path}")
        
        (
            ffmpeg
            .input(str(video_path))
            .output(str(output_path),
                   vf=f"subtitles={subtitle_path}:force_style='FontSize=24,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2'",
                   vcodec='libx264',
                   acodec='copy')
            .overwrite_output()
            .run(quiet=True)
        )
        
        logger.info(f"✅ Subtitles added: {output_path}")
        
    except Exception as e:
        logger.error(f"❌ Error adding subtitles: {e}")
        raise

def create_educational_slide(expression: str, translation: str, duration: float = 3.0, output_path: str = None):
    """Create educational slide with text overlay"""
    try:
        if output_path is None:
            output_path = f"output/educational_slide_{expression.replace(' ', '_')}.mkv"
        
        logger.info(f"Creating educational slide: {expression}")
        
        # Create a simple colored background with text
        (
            ffmpeg
            .input('color=c=black:size=1280x720:duration=3', f='lavfi')
            .output(str(output_path),
                   vf=f"drawtext=text='{expression}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-50:fontfile=/System/Library/Fonts/Arial.ttf,drawtext=text='{translation}':fontsize=32:fontcolor=yellow:x=(w-text_w)/2:y=(h-text_h)/2+50:fontfile=/System/Library/Fonts/Arial.ttf",
                   vcodec='libx264',
                   acodec='aac',
                   t=duration)
            .overwrite_output()
            .run(quiet=True)
        )
        
        logger.info(f"✅ Educational slide created: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"❌ Error creating educational slide: {e}")
        raise

def process_all_videos():
    """Process all expression videos and add subtitles + educational slides"""
    
    output_dir = Path("output")
    video_files = list(output_dir.glob("expression_*.mkv"))
    video_files.sort()
    
    if not video_files:
        logger.error("No video files found")
        return
    
    logger.info(f"Processing {len(video_files)} videos...")
    
    # Create final sequence list
    final_sequence = []
    
    for i, video_file in enumerate(video_files):
        try:
            logger.info(f"Processing {i+1}/{len(video_files)}: {video_file.name}")
            
            # 1. Add subtitles to original video
            subtitle_file = video_file.with_suffix('.srt')
            if subtitle_file.exists():
                video_with_subs = output_dir / f"with_subs_{video_file.name}"
                add_subtitles_to_video(str(video_file), str(subtitle_file), str(video_with_subs))
                final_sequence.append(str(video_with_subs))
            else:
                logger.warning(f"No subtitle file found for {video_file.name}")
                final_sequence.append(str(video_file))
            
            # 2. Create educational slide
            # Extract expression from filename
            expression_name = video_file.stem.replace('expression_', '').replace('_', ' ')
            translation = "번역"  # Placeholder translation
            
            slide_path = output_dir / f"slide_{i+1:02d}_{expression_name.replace(' ', '_')}.mkv"
            create_educational_slide(expression_name, translation, 3.0, str(slide_path))
            final_sequence.append(str(slide_path))
            
        except Exception as e:
            logger.error(f"Error processing {video_file.name}: {e}")
            continue
    
    # 3. Concatenate all videos and slides
    concat_file = output_dir / "final_sequence_list.txt"
    with open(concat_file, 'w') as f:
        for video_path in final_sequence:
            f.write(f"file '{Path(video_path).absolute()}'\n")
    
    # Create final video
    final_output = output_dir / "final_educational_with_slides.mkv"
    
    try:
        logger.info("Creating final educational video with slides...")
        
        (
            ffmpeg
            .input(str(concat_file), format='concat', safe=0)
            .output(str(final_output),
                   vcodec='libx264',
                   acodec='aac',
                   preset='fast',
                   crf=23,
                   af='pan=stereo|c0=c0+c2+c4|c1=c1+c3+c5')
            .overwrite_output()
            .run(quiet=True)
        )
        
        logger.info(f"✅ Final educational video created: {final_output}")
        
        # Get video info
        probe = ffmpeg.probe(str(final_output))
        duration = float(probe['format']['duration'])
        logger.info(f"📹 Video duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        
    except Exception as e:
        logger.error(f"❌ Error creating final video: {e}")
        raise

if __name__ == "__main__":
    process_all_videos()
