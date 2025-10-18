#!/usr/bin/env python3
"""
Create educational video with proper terminology and improved slides
"""

import sys
from pathlib import Path
import logging
import ffmpeg
import json
import re

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

def sanitize_text(text: str) -> str:
    """Sanitize text for ffmpeg drawtext"""
    # Remove special characters that cause issues
    text = re.sub(r'[^\w\s\-.,!?]', '', text)
    # Escape single quotes
    text = text.replace("'", "\\'")
    return text

def get_audio_duration(video_path: str) -> float:
    """Get audio duration of video"""
    try:
        probe = ffmpeg.probe(str(video_path))
        duration = float(probe['format']['duration'])
        return duration
    except Exception as e:
        logger.warning(f"Could not get duration for {video_path}: {e}")
        return 3.0  # Default fallback

def add_subtitles_to_video(video_path: str, subtitle_path: str, output_path: str):
    """Add subtitles to video with consistent encoding"""
    try:
        logger.info(f"Adding subtitles to {video_path}")
        
        (
            ffmpeg
            .input(str(video_path))
            .output(str(output_path),
                   vf=f"subtitles={subtitle_path}:force_style='FontSize=24,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2'",
                   vcodec='libx264',
                   acodec='aac',
                   preset='fast',
                   crf=23)
            .overwrite_output()
            .run(quiet=True)
        )
        
        logger.info(f"✅ Subtitles added: {output_path}")
        
    except Exception as e:
        logger.error(f"❌ Error adding subtitles: {e}")
        raise

def create_educational_slide(expression: str, translation: str, audio_duration: float, output_path: str):
    """Create educational slide with proper duration and readable text"""
    try:
        # Calculate total duration: audio duration + 3 seconds
        total_duration = audio_duration + 3.0
        
        logger.info(f"Creating educational slide: {expression} (duration: {total_duration:.1f}s)")
        
        # Sanitize text
        safe_expression = sanitize_text(expression)
        safe_translation = sanitize_text(translation)
        
        # Create educational slide with better text rendering
        (
            ffmpeg
            .input('color=c=black:size=1280x720', f='lavfi', t=total_duration)
            .output(str(output_path),
                   vf=f"drawtext=text='{safe_expression}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-50,drawtext=text='{safe_translation}':fontsize=32:fontcolor=yellow:x=(w-text_w)/2:y=(h-text_h)/2+50",
                   vcodec='libx264',
                   acodec='aac',
                   preset='fast',
                   crf=23,
                   t=total_duration)
            .overwrite_output()
            .run(quiet=True)
        )
        
        logger.info(f"✅ Educational slide created: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"❌ Error creating educational slide: {e}")
        raise

def create_expression_repeat_clip(video_path: str, output_path: str):
    """Create expression clip that repeats 3 times"""
    try:
        logger.info(f"Creating 3x repeat clip: {video_path}")
        
        # Get original duration
        duration = get_audio_duration(video_path)
        
        # Create 3x repeated version
        (
            ffmpeg
            .input(str(video_path))
            .filter('aloop', loop=2, size=2e+09)  # Loop 2 more times (total 3x)
            .output(str(output_path),
                   vcodec='libx264',
                   acodec='aac',
                   preset='fast',
                   crf=23)
            .overwrite_output()
            .run(quiet=True)
        )
        
        logger.info(f"✅ 3x repeat clip created: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"❌ Error creating repeat clip: {e}")
        raise

def process_all_videos():
    """Process all expression videos with improved educational sequence"""
    
    output_dir = Path("output")
    video_files = list(output_dir.glob("expression_*.mkv"))
    video_files.sort()
    
    if not video_files:
        logger.error("No video files found")
        return
    
    logger.info(f"Processing {len(video_files)} videos with educational sequence...")
    
    # Create final sequence list
    final_sequence = []
    
    for i, video_file in enumerate(video_files):
        try:
            logger.info(f"Processing {i+1}/{len(video_files)}: {video_file.name}")
            
            # 1. Add subtitles to original video (Context Video)
            subtitle_file = video_file.with_suffix('.srt')
            if subtitle_file.exists():
                context_video = output_dir / f"context_{video_file.name}"
                add_subtitles_to_video(str(video_file), str(subtitle_file), str(context_video))
                final_sequence.append(str(context_video))
            else:
                logger.warning(f"No subtitle file found for {video_file.name}")
                final_sequence.append(str(video_file))
            
            # 2. Create expression repeat clip (3x)
            expression_repeat = output_dir / f"expression_repeat_{i+1:02d}_{video_file.stem.replace('expression_', '')}.mkv"
            create_expression_repeat_clip(str(video_file), str(expression_repeat))
            final_sequence.append(str(expression_repeat))
            
            # 3. Create educational slide
            expression_name = video_file.stem.replace('expression_', '').replace('_', ' ')
            translation = "번역"  # Placeholder - should be from actual data
            
            # Get audio duration for proper slide timing
            audio_duration = get_audio_duration(str(video_file))
            
            slide_path = output_dir / f"educational_slide_{i+1:02d}_{expression_name.replace(' ', '_')}.mkv"
            create_educational_slide(expression_name, translation, audio_duration, str(slide_path))
            final_sequence.append(str(slide_path))
            
        except Exception as e:
            logger.error(f"Error processing {video_file.name}: {e}")
            continue
    
    # 4. Concatenate all videos with consistent encoding
    concat_file = output_dir / "educational_sequence_list.txt"
    with open(concat_file, 'w') as f:
        for video_path in final_sequence:
            f.write(f"file '{Path(video_path).absolute()}'\n")
    
    # Create final educational video
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
