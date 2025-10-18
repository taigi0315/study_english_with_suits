"""
Subtitle processing module for LangFlix
Handles subtitle extraction, translation, and file generation
"""
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import re

from .models import ExpressionAnalysis
from .subtitle_parser import parse_srt_file

logger = logging.getLogger(__name__)


class SubtitleProcessor:
    """
    Handles subtitle processing including extraction, translation, and file generation
    """
    
    def __init__(self, subtitle_file_path: str):
        """
        Initialize subtitle processor
        
        Args:
            subtitle_file_path: Path to the subtitle file
        """
        self.subtitle_file_path = subtitle_file_path
        self.subtitles = self._load_subtitles()
        
    def _load_subtitles(self) -> List[Dict[str, Any]]:
        """
        Load and parse subtitle file
        
        Returns:
            List of subtitle dictionaries
        """
        try:
            subtitles = parse_srt_file(self.subtitle_file_path)
            logger.info(f"Loaded {len(subtitles)} subtitle entries")
            return subtitles
        except Exception as e:
            logger.error(f"Error loading subtitles: {e}")
            return []
    
    def extract_subtitles_for_expression(self, expression: ExpressionAnalysis) -> List[Dict[str, Any]]:
        """
        Extract subtitles that fall within the expression's context time range
        
        Args:
            expression: ExpressionAnalysis object with context times
            
        Returns:
            List of subtitle dictionaries within the time range
        """
        try:
            start_time = self._time_to_seconds(expression.context_start_time)
            end_time = self._time_to_seconds(expression.context_end_time)
            
            logger.info(f"Extracting subtitles from {expression.context_start_time} to {expression.context_end_time}")
            
            matching_subtitles = []
            
            for subtitle in self.subtitles:
                sub_start = self._time_to_seconds(subtitle['start_time'])
                sub_end = self._time_to_seconds(subtitle['end_time'])
                
                # Check if subtitle overlaps with the expression's context time
                if (sub_start < end_time and sub_end > start_time):
                    matching_subtitles.append(subtitle)
            
            logger.info(f"Found {len(matching_subtitles)} matching subtitles")
            return matching_subtitles
            
        except Exception as e:
            logger.error(f"Error extracting subtitles for expression: {e}")
            return []
    
    def create_translated_subtitle_file(self, expression: ExpressionAnalysis, 
                                      output_path: str) -> bool:
        """
        Create a translated subtitle file for the expression
        
        Args:
            expression: ExpressionAnalysis object with translation data
            output_path: Path for the output subtitle file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract subtitles for this expression
            subtitles = self.extract_subtitles_for_expression(expression)
            
            if not subtitles:
                logger.warning(f"No subtitles found for expression: {expression.expression}")
                return False
            
            # Create SRT content
            srt_content = self._generate_srt_content(subtitles, expression)
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            logger.info(f"Created translated subtitle file: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating translated subtitle file: {e}")
            return False
    
    def _generate_srt_content(self, subtitles: List[Dict[str, Any]], 
                            expression: ExpressionAnalysis) -> str:
        """
        Generate SRT content with original and translated text
        
        Args:
            subtitles: List of subtitle dictionaries
            expression: ExpressionAnalysis object with translation data
            
        Returns:
            SRT formatted string
        """
        srt_lines = []
        
        for i, subtitle in enumerate(subtitles):
            # SRT entry number
            srt_lines.append(str(i + 1))
            
            # Time range
            start_time = self._format_srt_time(subtitle['start_time'])
            end_time = self._format_srt_time(subtitle['end_time'])
            srt_lines.append(f"{start_time} --> {end_time}")
            
            # Original text
            srt_lines.append(subtitle['text'])
            
            # Translated text (if available)
            if i < len(expression.translation):
                srt_lines.append(expression.translation[i])
            else:
                # Fallback to expression translation
                srt_lines.append(expression.expression_translation)
            
            # Empty line between entries
            srt_lines.append("")
        
        return "\n".join(srt_lines)
    
    def _format_srt_time(self, time_str: str) -> str:
        """
        Format time string for SRT format (HH:MM:SS,mmm)
        
        Args:
            time_str: Time string in format "HH:MM:SS.mmm"
            
        Returns:
            SRT formatted time string
        """
        # Convert from "HH:MM:SS.mmm" to "HH:MM:SS,mmm"
        return time_str.replace('.', ',')
    
    def _time_to_seconds(self, time_str: str) -> float:
        """
        Convert time string to seconds
        
        Args:
            time_str: Time string in format "HH:MM:SS.mmm" or "HH:MM:SS,mmm"
            
        Returns:
            Time in seconds as float
        """
        try:
            # Normalize time format
            time_str = time_str.replace(',', '.')
            
            # Split by colon and dot
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            
            return hours * 3600 + minutes * 60 + seconds
            
        except Exception as e:
            logger.error(f"Error parsing time string '{time_str}': {e}")
            return 0.0
    
    def create_dual_language_subtitle_file(self, expression: ExpressionAnalysis, 
                                         output_path: str) -> bool:
        """
        Create a dual-language subtitle file (original + translation)
        
        Args:
            expression: ExpressionAnalysis object with translation data
            output_path: Path for the output subtitle file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract subtitles for this expression
            subtitles = self.extract_subtitles_for_expression(expression)
            
            if not subtitles:
                logger.warning(f"No subtitles found for expression: {expression.expression}")
                return False
            
            # Create dual-language SRT content
            srt_content = self._generate_dual_language_srt(subtitles, expression)
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            logger.info(f"Created dual-language subtitle file: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating dual-language subtitle file: {e}")
            return False
    
    def _generate_dual_language_srt(self, subtitles: List[Dict[str, Any]], 
                                   expression: ExpressionAnalysis) -> str:
        """
        Generate dual-language SRT content with adjusted timing for video clips
        
        Args:
            subtitles: List of subtitle dictionaries
            expression: ExpressionAnalysis object with translation data
            
        Returns:
            SRT formatted string with both languages and adjusted timing
        """
        srt_lines = []
        
        # Get the start time of the first subtitle to adjust all times
        first_start_time = self._time_to_timedelta(subtitles[0]['start_time'])
        
        for i, subtitle in enumerate(subtitles):
            # SRT entry number
            srt_lines.append(str(i + 1))
            
            # Adjust timing to start from 00:00:00
            start_time = self._time_to_timedelta(subtitle['start_time'])
            end_time = self._time_to_timedelta(subtitle['end_time'])
            
            # Calculate relative times from the first subtitle
            relative_start = start_time - first_start_time
            relative_end = end_time - first_start_time
            
            # Format adjusted times
            start_time_str = self._timedelta_to_srt_time(relative_start)
            end_time_str = self._timedelta_to_srt_time(relative_end)
            srt_lines.append(f"{start_time_str} --> {end_time_str}")
            
            # Original text
            srt_lines.append(subtitle['text'])
            
            # Translated text (if available)
            if i < len(expression.translation):
                srt_lines.append(expression.translation[i])
            else:
                # Fallback to expression translation
                srt_lines.append(expression.expression_translation)
            
            # Empty line between entries
            srt_lines.append("")
        
        return "\n".join(srt_lines)
    
    def _timedelta_to_srt_time(self, td: timedelta) -> str:
        """
        Convert timedelta to SRT time format (HH:MM:SS,mmm)
        
        Args:
            td: timedelta object
            
        Returns:
            SRT formatted time string
        """
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        milliseconds = int(td.microseconds / 1000)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    def _time_to_timedelta(self, time_str: str) -> timedelta:
        """
        Convert a time string (HH:MM:SS,mmm) to a timedelta object.
        """
        try:
            # Replace comma with dot for milliseconds
            time_str = time_str.replace(',', '.')
            
            # Handle cases where milliseconds might be missing or have fewer digits
            if '.' not in time_str:
                time_str += '.000'
            
            # Parse using datetime.strptime and convert to timedelta
            dt_object = datetime.strptime(time_str, "%H:%M:%S.%f")
            return timedelta(
                hours=dt_object.hour,
                minutes=dt_object.minute,
                seconds=dt_object.second,
                microseconds=dt_object.microsecond
            )
        except ValueError as e:
            logger.error(f"Error parsing time string '{time_str}': {e}")
            # Fallback for simpler formats if needed, or raise
            h, m, s = map(int, time_str.split(':'))
            return timedelta(hours=h, minutes=m, seconds=s)


def create_subtitle_file_for_expression(expression: ExpressionAnalysis, 
                                       subtitle_file_path: str, 
                                       output_path: str) -> bool:
    """
    Convenience function to create subtitle file for an expression
    
    Args:
        expression: ExpressionAnalysis object
        subtitle_file_path: Path to original subtitle file
        output_path: Path for output subtitle file
        
    Returns:
        True if successful, False otherwise
    """
    processor = SubtitleProcessor(subtitle_file_path)
    return processor.create_dual_language_subtitle_file(expression, output_path)


if __name__ == "__main__":
    # Test the subtitle processor
    import sys
    
    if len(sys.argv) > 1:
        subtitle_path = sys.argv[1]
        processor = SubtitleProcessor(subtitle_path)
        
        # Test with dummy expression
        from langflix.models import ExpressionAnalysis
        dummy_expression = ExpressionAnalysis(
            dialogues=["I'm paying you millions,", "and you're telling me I'm gonna get screwed?"],
            translation=["나는 당신에게 수백만 달러를 지불하고 있는데,", "당신은 내가 속임을 당할 것이라고 말하고 있나요?"],
            expression="I'm gonna get screwed",
            expression_translation="속임을 당할 것 같아요",
            context_start_time="00:01:25,657",
            context_end_time="00:01:32,230",
            similar_expressions=["I'm going to be cheated", "I'm getting the short end of the stick"]
        )
        
        # Extract subtitles
        subtitles = processor.extract_subtitles_for_expression(dummy_expression)
        print(f"Found {len(subtitles)} subtitles for expression")
        
        # Create subtitle file
        output_path = "test_output.srt"
        success = processor.create_dual_language_subtitle_file(dummy_expression, output_path)
        
        if success:
            print(f"Created subtitle file: {output_path}")
        else:
            print("Failed to create subtitle file")
    else:
        print("Usage: python subtitle_processor.py <subtitle_file_path>")
