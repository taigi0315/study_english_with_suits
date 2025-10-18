#!/usr/bin/env python3
"""
Video Editor for LangFlix
Creates educational video sequences with context, expression clips, and educational slides
"""

import ffmpeg
import logging
import os
from pathlib import Path
from typing import List, Dict, Any
from .models import ExpressionAnalysis

logger = logging.getLogger(__name__)

class VideoEditor:
    """
    Creates educational video sequences from expression analysis results
    """
    
    def __init__(self, output_dir: str = "output"):
        """
        Initialize VideoEditor
        
        Args:
            output_dir: Directory for output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def create_educational_sequence(self, expression: ExpressionAnalysis, 
                                  context_video_path: str, 
                                  expression_video_path: str) -> str:
        """
        Create educational video sequence:
        1. Context video with subtitles
        2. Expression clip (short, expression part only)
        3. Educational slide (background + text + audio 3x)
        
        Args:
            expression: ExpressionAnalysis object
            context_video_path: Path to context video
            expression_video_path: Path to expression video
            
        Returns:
            Path to created educational video
        """
        try:
            # Create output filename
            safe_expression = self._sanitize_filename(expression.expression)
            output_filename = f"educational_{safe_expression}.mkv"
            output_path = self.output_dir / output_filename
            
            logger.info(f"Creating educational sequence for: {expression.expression}")
            
            # Step 1: Create context video with subtitles
            context_with_subtitles = self._add_subtitles_to_context(
                context_video_path, expression
            )
            
            # Step 2: Create expression clip (short version)
            expression_clip = self._create_expression_clip(
                expression_video_path, expression
            )
            
            # Step 3: Create educational slide
            educational_slide = self._create_educational_slide(
                expression_video_path, expression
            )
            
            # Step 4: Concatenate all parts
            final_video = self._concatenate_sequence([
                context_with_subtitles,
                expression_clip,
                educational_slide
            ], str(output_path))
            
            logger.info(f"Educational sequence created: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error creating educational sequence: {e}")
            raise
    
    def _sanitize_filename(self, text: str) -> str:
        """Sanitize text for filename"""
        import re
        # Remove special characters and replace spaces with underscores
        sanitized = re.sub(r'[^\w\s-]', '', text)
        sanitized = re.sub(r'[-\s]+', '_', sanitized)
        return sanitized[:50]  # Limit length
    
    def _add_subtitles_to_context(self, video_path: str, expression: ExpressionAnalysis) -> str:
        """Add dual-language subtitles to context video"""
        try:
            # Create subtitle file for context
            subtitle_path = self.output_dir / f"temp_context_{self._sanitize_filename(expression.expression)}.srt"
            
            # Generate subtitle content
            subtitle_content = self._generate_context_subtitles(expression)
            
            with open(subtitle_path, 'w', encoding='utf-8') as f:
                f.write(subtitle_content)
            
            # Add subtitles to video
            output_path = self.output_dir / f"temp_context_with_subs_{self._sanitize_filename(expression.expression)}.mkv"
            
            (
                ffmpeg
                .input(str(video_path))
                .output(str(output_path), 
                       vf=f"subtitles={subtitle_path}",
                       vcodec='libx264',
                       acodec='copy')
                .overwrite_output()
                .run(quiet=True)
            )
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error adding subtitles to context: {e}")
            raise
    
    def _create_expression_clip(self, video_path: str, expression: ExpressionAnalysis) -> str:
        """Create short expression clip (expression part only)"""
        try:
            # For now, use the full video as expression clip
            # TODO: Implement precise expression timing extraction
            output_path = self.output_dir / f"temp_expression_{self._sanitize_filename(expression.expression)}.mkv"
            
            # Copy video as-is for now
            (
                ffmpeg
                .input(str(video_path))
                .output(str(output_path), 
                       vcodec='copy',
                       acodec='copy')
                .overwrite_output()
                .run(quiet=True)
            )
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error creating expression clip: {e}")
            raise
    
    def _create_educational_slide(self, video_path: str, expression: ExpressionAnalysis) -> str:
        """Create educational slide with background, text, and audio 3x"""
        try:
            output_path = self.output_dir / f"temp_slide_{self._sanitize_filename(expression.expression)}.mkv"
            
            # Get last frame as background
            last_frame = self.output_dir / f"temp_last_frame_{self._sanitize_filename(expression.expression)}.jpg"
            
            # Extract last frame
            (
                ffmpeg
                .input(str(video_path))
                .output(str(last_frame), 
                       vframes=1,
                       vf="select=eq(n\\,0)")
                .overwrite_output()
                .run(quiet=True)
            )
            
            # Create educational slide with text overlay
            # This is a simplified version - in production, you'd use more sophisticated text rendering
            slide_duration = 6.0  # 6 seconds for slide
            
            (
                ffmpeg
                .input(str(last_frame), loop=1, t=slide_duration)
                .output(str(output_path),
                       vf=f"scale=1920:1080,blur=5,drawtext=text='{expression.expression}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-50,drawtext=text='{expression.expression_translation}':fontsize=32:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2+50",
                       vcodec='libx264',
                       acodec='aac',
                       t=slide_duration)
                .overwrite_output()
                .run(quiet=True)
            )
            
            # Add audio 3x repetition
            audio_path = self.output_dir / f"temp_audio_{self._sanitize_filename(expression.expression)}.wav"
            
            # Extract audio from original video
            (
                ffmpeg
                .input(str(video_path))
                .output(str(audio_path), acodec='pcm_s16le')
                .overwrite_output()
                .run(quiet=True)
            )
            
            # Create 3x repeated audio
            audio_3x_path = self.output_dir / f"temp_audio_3x_{self._sanitize_filename(expression.expression)}.wav"
            
            (
                ffmpeg
                .input(str(audio_path))
                .filter('aloop', loop=2, size=2e+09)  # Loop 2 more times (total 3x)
                .output(str(audio_3x_path))
                .overwrite_output()
                .run(quiet=True)
            )
            
            # Combine slide with 3x audio
            final_slide_path = self.output_dir / f"temp_final_slide_{self._sanitize_filename(expression.expression)}.mkv"
            
            (
                ffmpeg
                .input(str(output_path))
                .input(str(audio_3x_path))
                .output(str(final_slide_path),
                       vcodec='copy',
                       acodec='aac',
                       map=['0:v:0', '1:a:0'])
                .overwrite_output()
                .run(quiet=True)
            )
            
            return str(final_slide_path)
            
        except Exception as e:
            logger.error(f"Error creating educational slide: {e}")
            raise
    
    def _concatenate_sequence(self, video_paths: List[str], output_path: str) -> str:
        """Concatenate video sequence"""
        try:
            # Create concat file for ffmpeg
            concat_file = self.output_dir / "temp_concat.txt"
            
            with open(concat_file, 'w') as f:
                for video_path in video_paths:
                    f.write(f"file '{video_path}'\n")
            
            # Concatenate videos
            (
                ffmpeg
                .input(str(concat_file), format='concat', safe=0)
                .output(str(output_path),
                       vcodec='libx264',
                       acodec='aac')
                .overwrite_output()
                .run(quiet=True)
            )
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error concatenating sequence: {e}")
            raise
    
    def _generate_context_subtitles(self, expression: ExpressionAnalysis) -> str:
        """Generate SRT subtitle content for context video"""
        srt_content = []
        
        for i, (dialogue, translation) in enumerate(zip(expression.dialogues, expression.translation)):
            # Calculate timing (simplified - in production, use actual timing)
            start_time = f"00:00:{i*2:02d},000"
            end_time = f"00:00:{i*2+1:02d},500"
            
            srt_content.append(f"{i+1}")
            srt_content.append(f"{start_time} --> {end_time}")
            srt_content.append(dialogue)
            srt_content.append(translation)
            srt_content.append("")
        
        return "\n".join(srt_content)


def create_educational_video(expression: ExpressionAnalysis, 
                           context_video_path: str, 
                           expression_video_path: str,
                           output_dir: str = "output") -> str:
    """
    Convenience function to create educational video
    
    Args:
        expression: ExpressionAnalysis object
        context_video_path: Path to context video
        expression_video_path: Path to expression video
        output_dir: Output directory
        
    Returns:
        Path to created educational video
    """
    editor = VideoEditor(output_dir)
    return editor.create_educational_sequence(expression, context_video_path, expression_video_path)
