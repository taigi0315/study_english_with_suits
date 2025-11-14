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
from .subtitle_parser import parse_srt_file, parse_subtitle_file_by_extension

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
            # Use extension-based parser to support multiple formats (SRT, SMI, etc.)
            subtitles = parse_subtitle_file_by_extension(self.subtitle_file_path)
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
    
    def _find_expression_with_advanced_matching(self, context_subtitles, expression_text, expression_clean, expression_words):
        """
        Advanced matching algorithm to find expression timing with multiple strategies.
        
        Returns:
            Tuple of (start_time, end_time, score) or None if no match found
        """
        best_match = None
        best_score = 0
        
        # Strategy 1: Exact substring match (highest priority)
        for subtitle in context_subtitles:
            subtitle_text = subtitle['text'].lower().strip()
            if expression_text in subtitle_text:
                logger.debug(f"Found exact match in subtitle: {subtitle['text']}")
                return subtitle['start_time'], subtitle['end_time'], 1.0
        
        # Strategy 2: Fuzzy word sequence matching
        expression_word_list = expression_clean.split()
        for i, subtitle in enumerate(context_subtitles):
            subtitle_clean = self._clean_text_for_matching(subtitle['text'])
            subtitle_word_list = subtitle_clean.split()
            
            # Check for consecutive word sequence match
            score = self._calculate_sequence_match_score(expression_word_list, subtitle_word_list)
            if score > best_score and score > 0.6:
                best_match = (subtitle['start_time'], subtitle['end_time'], score)
                best_score = score
                logger.debug(f"Found sequence match (score {score:.2f}): {subtitle['text']}")
        
        # Strategy 3: Word overlap with position weighting
        if not best_match or best_score < 0.8:
            for subtitle in context_subtitles:
                subtitle_clean = self._clean_text_for_matching(subtitle['text'])
                subtitle_words = set(subtitle_clean.split())
                
                if expression_words and subtitle_words:
                    # Calculate weighted overlap considering word position
                    overlap_score = self._calculate_weighted_overlap(expression_clean, subtitle_clean)
                    if overlap_score > best_score and overlap_score > 0.5:
                        best_match = (subtitle['start_time'], subtitle['end_time'], overlap_score)
                        best_score = overlap_score
                        logger.debug(f"Found weighted overlap match (score {overlap_score:.2f}): {subtitle['text']}")
        
        # Strategy 4: Multi-subtitle span matching for longer expressions
        if not best_match and len(expression_word_list) > 3:
            best_match = self._find_multi_subtitle_match(context_subtitles, expression_word_list)
        
        return best_match
    
    def _calculate_sequence_match_score(self, expression_words, subtitle_words):
        """Calculate score for consecutive word sequence matching"""
        if not expression_words or not subtitle_words:
            return 0.0
        
        # Look for the best consecutive sequence match
        best_match_length = 0
        for i in range(len(subtitle_words) - len(expression_words) + 1):
            match_length = 0
            for j, expr_word in enumerate(expression_words):
                if i + j < len(subtitle_words) and subtitle_words[i + j] == expr_word:
                    match_length += 1
                else:
                    break
            best_match_length = max(best_match_length, match_length)
        
        return best_match_length / len(expression_words) if expression_words else 0.0
    
    def _calculate_weighted_overlap(self, expression_clean, subtitle_clean):
        """Calculate weighted overlap with position consideration"""
        expression_words = expression_clean.split()
        subtitle_words = subtitle_clean.split()
        
        if not expression_words or not subtitle_words:
            return 0.0
        
        # Simple word overlap
        expr_set = set(expression_words)
        sub_set = set(subtitle_words)
        overlap = len(expr_set.intersection(sub_set))
        base_score = overlap / len(expr_set)
        
        # Bonus for word order preservation (simplified)
        order_bonus = 0.0
        if len(expression_words) > 1:
            consecutive_matches = 0
            for i in range(min(len(expression_words), len(subtitle_words))):
                if expression_words[i] == subtitle_words[i]:
                    consecutive_matches += 1
                else:
                    break
            order_bonus = consecutive_matches / len(expression_words) * 0.2
        
        return min(1.0, base_score + order_bonus)
    
    def _find_multi_subtitle_match(self, context_subtitles, expression_words):
        """Find matches that span multiple subtitles for longer expressions"""
        if len(context_subtitles) < 2:
            return None
        
        # Try to find expression across 2-3 consecutive subtitles
        for i in range(min(len(context_subtitles), 3)):
            combined_text = " ".join([
                self._clean_text_for_matching(sub['text']) 
                for sub in context_subtitles[i:i+2]
            ])
            combined_words = combined_text.split()
            
            score = self._calculate_sequence_match_score(expression_words, combined_words)
            if score > 0.7:
                # Use the timing of the first subtitle as start
                start_subtitle = context_subtitles[i]
                end_subtitle = context_subtitles[min(i+1, len(context_subtitles)-1)]
                return start_subtitle['start_time'], end_subtitle['end_time'], score
            
        return None

    def find_expression_timing(self, expression: ExpressionAnalysis) -> tuple[str, str]:
        """
        Find the exact start and end time of the expression phrase within the context time.
        This searches through subtitle text to find where the expression appears.
        
        Args:
            expression: ExpressionAnalysis object with expression text and context times
            
        Returns:
            Tuple of (expression_start_time, expression_end_time) in "HH:MM:SS,mmm" format
        """
        try:
            # Get context time range
            context_start = self._time_to_seconds(expression.context_start_time)
            context_end = self._time_to_seconds(expression.context_end_time)
            
            # Extract subtitles within context range
            context_subtitles = self.extract_subtitles_for_expression(expression)
            
            if not context_subtitles:
                logger.warning(f"No context subtitles found for expression: {expression.expression}")
                return expression.context_start_time, expression.context_end_time
            
            # Clean the expression text for matching
            expression_text = expression.expression.lower().strip()
            expression_clean = self._clean_text_for_matching(expression.expression)
            expression_words = set(expression_clean.split())
            
            best_match_start = None
            best_match_end = None
            best_score = 0
            
            # Try multiple matching strategies
            match_result = self._find_expression_with_advanced_matching(
                context_subtitles, expression_text, expression_clean, expression_words
            )
            
            if match_result:
                best_match_start, best_match_end, best_score = match_result
            
            if best_match_start and best_match_end:
                logger.info(f"Found expression timing: {best_match_start} to {best_match_end} (score: {best_score:.2f})")
                return best_match_start, best_match_end
            else:
                # Fallback: use a shorter section in the middle of context
                context_duration = context_end - context_start
                mid_point = context_start + context_duration / 2
                # Create a 3-second window around the middle point
                fallback_start = mid_point - 1.5
                fallback_end = mid_point + 1.5
                
                # Convert back to time format
                fallback_start_str = self._seconds_to_time(fallback_start)
                fallback_end_str = self._seconds_to_time(fallback_end)
                
                logger.warning(f"Could not find exact expression timing, using fallback: {fallback_start_str} to {fallback_end_str}")
                return fallback_start_str, fallback_end_str
                
        except Exception as e:
            logger.error(f"Error finding expression timing: {e}")
            return expression.context_start_time, expression.context_end_time
    
    def _seconds_to_time(self, seconds: float) -> str:
        """Convert seconds to HH:MM:SS,mmm format"""
        try:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace('.', ',')
        except Exception:
            return "00:00:00,000"
    
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
            
            # Ensure the output directory exists
            from pathlib import Path
            output_path_obj = Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to file
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(srt_content)
                
                logger.info(f"Created dual-language subtitle file: {output_path}")
                return True
            except Exception as write_error:
                logger.error(f"Failed to write subtitle file to {output_path}: {write_error}")
                logger.error(f"Directory exists: {output_path_obj.parent.exists()}")
                logger.error(f"Directory is writable: {output_path_obj.parent.is_dir()}")
                raise write_error
            
        except Exception as e:
            logger.error(f"Error creating dual-language subtitle file for expression '{expression.expression}': {e}")
            logger.error(f"Output path: {output_path}")
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
        
        # Get context start time to adjust all subtitle timestamps
        # Context video starts at context_start_time, so we need to subtract that offset
        context_start_time = self._time_to_timedelta(expression.context_start_time)
        
        # Create a mapping between dialogue text and translations
        dialogue_translation_map = {}
        if len(expression.dialogues) == len(expression.translation):
            for dialogue, translation in zip(expression.dialogues, expression.translation):
                clean_dialogue = self._clean_text_for_matching(dialogue)
                dialogue_translation_map[clean_dialogue] = translation
        
        # For better matching, we'll track which dialogue line each subtitle belongs to
        # by accumulating subtitle text and matching against complete dialogues
        subtitle_to_dialogue_map = self._map_subtitles_to_dialogues(subtitles, expression.dialogues)
        
        subtitle_entry_num = 1
        for i, subtitle in enumerate(subtitles):
            # Get absolute timestamps from subtitle
            start_time = self._time_to_timedelta(subtitle['start_time'])
            end_time = self._time_to_timedelta(subtitle['end_time'])
            
            # Calculate relative times from context_start_time (not first subtitle)
            # This ensures subtitles align with the sliced context video
            relative_start = start_time - context_start_time
            relative_end = end_time - context_start_time
            
            # Skip subtitles that are completely before context start
            if relative_end.total_seconds() <= 0:
                continue
            
            # For subtitles that start before context_start_time but end after it:
            # The subtitle should start at 0 in the context video (since context video starts at 0)
            # but we need to preserve the actual duration for proper sync
            # The end time is already calculated correctly relative to context_start_time
            if relative_start.total_seconds() < 0:
                # Subtitle starts before context video begins
                # In the context video (which starts at 0), this subtitle should start at 0
                # The duration is preserved by keeping the correctly calculated relative_end
                relative_start = timedelta(seconds=0)
                # Note: This ensures the subtitle appears from the start of the context video
                # while maintaining the correct duration for synchronization
            
            # SRT entry number (renumber sequentially for valid entries only)
            srt_lines.append(str(subtitle_entry_num))
            subtitle_entry_num += 1
            
            # Format adjusted times
            start_time_str = self._timedelta_to_srt_time(relative_start)
            end_time_str = self._timedelta_to_srt_time(relative_end)
            srt_lines.append(f"{start_time_str} --> {end_time_str}")
            
            # Original text
            srt_lines.append(subtitle['text'])
            
            # Find translation using improved mapping
            translation_text = self._get_translation_for_subtitle(i, subtitle, subtitle_to_dialogue_map, expression)
            srt_lines.append(translation_text)
            
            # Empty line between entries
            srt_lines.append("")
        
        return "\n".join(srt_lines)
    
    def _map_subtitles_to_dialogues(self, subtitles: List[Dict[str, Any]], dialogues: List[str]) -> List[int]:
        """Map each subtitle to its corresponding dialogue index"""
        subtitle_to_dialogue = []
        
        # Clean dialogues for matching
        clean_dialogues = [self._clean_text_for_matching(dialogue) for dialogue in dialogues]
        
        # For each subtitle, find which dialogue it belongs to
        for i, subtitle in enumerate(subtitles):
            best_match_idx = -1
            best_score = 0
            clean_subtitle = self._clean_text_for_matching(subtitle['text'])
            
            for j, clean_dialogue in enumerate(clean_dialogues):
                # Check if this subtitle text is part of this dialogue
                if clean_subtitle in clean_dialogue:
                    # Calculate word overlap score
                    subtitle_words = set(clean_subtitle.split())
                    dialogue_words = set(clean_dialogue.split())
                    if subtitle_words and dialogue_words:
                        overlap = len(subtitle_words.intersection(dialogue_words))
                        score = overlap / len(subtitle_words)
                        if score > best_score:
                            best_score = score
                            best_match_idx = j
            
            subtitle_to_dialogue.append(best_match_idx)
        
        return subtitle_to_dialogue
    
    def _get_translation_for_subtitle(self, subtitle_idx: int, subtitle: Dict[str, Any], 
                                    subtitle_to_dialogue_map: List[int], expression: ExpressionAnalysis) -> str:
        """Get the appropriate translation for a subtitle"""
        dialogue_idx = subtitle_to_dialogue_map[subtitle_idx]
        
        if dialogue_idx >= 0 and dialogue_idx < len(expression.translation):
            return expression.translation[dialogue_idx]
        
        # Fallback: use improved matching
        return self._find_matching_translation(
            subtitle['text'], 
            dict(zip([self._clean_text_for_matching(d) for d in expression.dialogues], expression.translation)),
            expression
        )
    
    def _clean_text_for_matching(self, text: str) -> str:
        """Clean text for better matching between dialogue and subtitle"""
        if not text:
            return ""
        
        # Remove extra whitespace, normalize case, remove punctuation
        cleaned = " ".join(text.strip().lower().split())
        # Remove common punctuation that might cause mismatch
        cleaned = ''.join(c for c in cleaned if c.isalnum() or c.isspace())
        return cleaned
    
    def _find_matching_translation(self, subtitle_text: str, dialogue_translation_map: dict, expression: ExpressionAnalysis) -> str:
        """Find the best matching translation for a subtitle text"""
        if not subtitle_text or not dialogue_translation_map:
            return expression.expression_translation
        
        # Clean the subtitle text for matching
        clean_subtitle = self._clean_text_for_matching(subtitle_text)
        
        # Try exact match first
        for dialogue_key, translation in dialogue_translation_map.items():
            if dialogue_key == clean_subtitle:
                return translation
        
        # Try partial match (check if subtitle text is contained in dialogue)
        for dialogue_key, translation in dialogue_translation_map.items():
            if clean_subtitle in dialogue_key or dialogue_key in clean_subtitle:
                return translation
        
        # Try word overlap
        subtitle_words = set(clean_subtitle.split())
        best_match_score = 0
        best_translation = expression.expression_translation
        
        for dialogue_key, translation in dialogue_translation_map.items():
            dialogue_words = set(dialogue_key.split())
            if subtitle_words and dialogue_words:
                overlap = len(subtitle_words.intersection(dialogue_words))
                score = overlap / len(subtitle_words)
                if score > best_match_score and score > 0.3:  # At least 30% word overlap
                    best_match_score = score
                    best_translation = translation
        
        return best_translation
    
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
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """
        Convert seconds to SRT time format (HH:MM:SS,mmm).
        
        Args:
            seconds: Time in seconds as float
            
        Returns:
            SRT formatted time string
        """
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        milliseconds = int((seconds - total_seconds) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    def generate_expression_subtitle_srt(
        self,
        expression: ExpressionAnalysis,
        expression_start_relative: float,
        expression_end_relative: float
    ) -> str:
        """
        Generate SRT file with expression text only, positioned at top.
        
        TICKET-040: Creates expression-only subtitle for top overlay.
        
        Args:
            expression: ExpressionAnalysis object
            expression_start_relative: Expression start time relative to context (seconds)
            expression_end_relative: Expression end time relative to context (seconds)
            
        Returns:
            SRT formatted string with expression text
        """
        srt_lines = []
        
        # Single subtitle entry for expression
        srt_lines.append("1")
        
        # Format times
        start_time_str = self._seconds_to_srt_time(expression_start_relative)
        end_time_str = self._seconds_to_srt_time(expression_end_relative)
        srt_lines.append(f"{start_time_str} --> {end_time_str}")
        
        # Expression text (not dialogue)
        srt_lines.append(expression.expression)
        srt_lines.append("")
        
        return "\n".join(srt_lines)


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
