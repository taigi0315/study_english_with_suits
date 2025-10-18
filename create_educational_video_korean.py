#!/usr/bin/env python3
"""
Create educational video with Korean font support
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

def create_educational_slide_korean(expression: str, translation: str, audio_duration: float, output_path: str):
    """Create educational slide with Korean font support"""
    try:
        # Calculate total duration: audio duration + 3 seconds
        total_duration = audio_duration + 3.0
        
        logger.info(f"Creating educational slide with Korean font: {expression} (duration: {total_duration:.1f}s)")
        
        # Sanitize text
        safe_expression = sanitize_text(expression)
        safe_translation = sanitize_text(translation)
        
        # Korean font path
        korean_font = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
        
        # Create educational slide with Korean font
        (
            ffmpeg
            .input('color=c=black:size=1280x720', f='lavfi', t=total_duration)
            .output(str(output_path),
                   vf=f"drawtext=text='{safe_expression}':fontfile={korean_font}:fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-50,drawtext=text='{safe_translation}':fontfile={korean_font}:fontsize=32:fontcolor=yellow:x=(w-text_w)/2:y=(h-text_h)/2+50",
                   vcodec='libx264',
                   acodec='aac',
                   preset='fast',
                   crf=23,
                   t=total_duration)
            .overwrite_output()
            .run(quiet=True)
        )
        
        logger.info(f"✅ Educational slide with Korean font created: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"❌ Error creating educational slide: {e}")
        raise

def process_all_videos_korean():
    """Process all expression videos with Korean font support"""
    
    output_dir = Path("output")
    video_files = list(output_dir.glob("expression_*.mkv"))
    video_files.sort()
    
    if not video_files:
        logger.error("No video files found")
        return
    
    logger.info(f"Processing {len(video_files)} videos with Korean font support...")
    
    # Create final sequence list
    final_sequence = []
    
    for i, video_file in enumerate(video_files):
        try:
            logger.info(f"Processing {i+1}/{len(video_files)}: {video_file.name}")
            
            # 1. Add original video
            final_sequence.append(str(video_file))
            
            # 2. Create educational slide with Korean font
            expression_name = video_file.stem.replace('expression_', '').replace('_', ' ')
            translation = "번역"  # Placeholder - should be from actual data
            
            # Get audio duration for proper slide timing
            audio_duration = get_audio_duration(str(video_file))
            
            slide_path = output_dir / f"korean_slide_{i+1:02d}_{expression_name.replace(' ', '_')}.mkv"
            create_educational_slide_korean(expression_name, translation, audio_duration, str(slide_path))
            final_sequence.append(str(slide_path))
            
        except Exception as e:
            logger.error(f"Error processing {video_file.name}: {e}")
            continue
    
    # 3. Concatenate all videos with consistent encoding
    concat_file = output_dir / "korean_sequence_list.txt"
    with open(concat_file, 'w') as f:
        for video_path in final_sequence:
            f.write(f"file '{Path(video_path).absolute()}'\n")
    
    # Create final educational video
    final_output = output_dir / "final_educational_korean.mkv"
    
    try:
        logger.info("Creating final educational video with Korean font...")
        
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
        
        logger.info(f"✅ Final educational video with Korean font created: {final_output}")
        
        # Get video info
        probe = ffmpeg.probe(str(final_output))
        duration = float(probe['format']['duration'])
        logger.info(f"📹 Video duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        
    except Exception as e:
        logger.error(f"❌ Error creating final video: {e}")
        raise

if __name__ == "__main__":
    process_all_videos_korean()
