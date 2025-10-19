"""
Utility functions for step-by-step testing validation
"""
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import ffmpeg

logger = logging.getLogger(__name__)

def validate_file_exists(file_path: Path, min_size: int = 0) -> bool:
    """Validate that file exists and meets minimum size requirement"""
    if not file_path.exists():
        logger.error(f"File does not exist: {file_path}")
        return False
    
    if file_path.stat().st_size < min_size:
        logger.error(f"File too small: {file_path} ({file_path.stat().st_size} < {min_size})")
        return False
    
    logger.info(f"✅ File validated: {file_path} ({file_path.stat().st_size} bytes)")
    return True

def get_video_properties(video_path: Path) -> Dict[str, Any]:
    """Get video properties using ffprobe"""
    try:
        probe = ffmpeg.probe(str(video_path))
        
        # Find video stream
        video_stream = None
        audio_stream = None
        
        for stream in probe['streams']:
            if stream['codec_type'] == 'video' and video_stream is None:
                video_stream = stream
            elif stream['codec_type'] == 'audio' and audio_stream is None:
                audio_stream = stream
        
        if not video_stream:
            raise ValueError("No video stream found")
        
        # Extract properties
        properties = {
            'duration_seconds': float(probe['format']['duration']),
            'size_bytes': int(probe['format']['size']),
            'video_codec': video_stream.get('codec_name', 'unknown'),
            'video_width': int(video_stream.get('width', 0)),
            'video_height': int(video_stream.get('height', 0)),
            'video_fps': eval(video_stream.get('r_frame_rate', '0/1')),
            'has_audio': audio_stream is not None,
        }
        
        if audio_stream:
            properties.update({
                'audio_codec': audio_stream.get('codec_name', 'unknown'),
                'audio_sample_rate': int(audio_stream.get('sample_rate', 0)),
                'audio_channels': int(audio_stream.get('channels', 0)),
            })
        
        return properties
        
    except Exception as e:
        logger.error(f"Error getting video properties for {video_path}: {e}")
        raise

def validate_video_properties(video_path: Path, expected_duration: Optional[float] = None, 
                            min_duration: Optional[float] = None, max_duration: Optional[float] = None) -> bool:
    """Validate video properties"""
    try:
        props = get_video_properties(video_path)
        
        # Check basic file size
        if props['size_bytes'] < 1000:
            logger.error(f"Video file too small: {props['size_bytes']} bytes")
            return False
        
        # Check duration
        if expected_duration is not None:
            diff = abs(props['duration_seconds'] - expected_duration)
            if diff > 0.2:  # 200ms tolerance (video processing can have small timing differences)
                logger.error(f"Duration mismatch: expected {expected_duration:.2f}s, got {props['duration_seconds']:.2f}s (diff: {diff:.2f}s)")
                return False
            elif diff > 0.1:  # Warn if difference is > 100ms but <= 200ms
                logger.warning(f"⚠️  Small duration difference: expected {expected_duration:.2f}s, got {props['duration_seconds']:.2f}s (diff: {diff:.2f}s)")
        
        if min_duration is not None and props['duration_seconds'] < min_duration:
            logger.error(f"Duration too short: {props['duration_seconds']:.2f}s < {min_duration:.2f}s")
            return False
            
        if max_duration is not None and props['duration_seconds'] > max_duration:
            logger.error(f"Duration too long: {props['duration_seconds']:.2f}s > {max_duration:.2f}s")
            return False
        
        # Check video stream
        if props['video_width'] == 0 or props['video_height'] == 0:
            logger.error("Invalid video dimensions")
            return False
        
        logger.info(f"✅ Video validated: {props['video_width']}x{props['video_height']}, "
                   f"{props['duration_seconds']:.2f}s, {props['size_bytes']} bytes")
        return True
        
    except Exception as e:
        logger.error(f"Video validation failed: {e}")
        return False

def get_audio_properties(audio_path: Path) -> Dict[str, Any]:
    """Get audio properties using ffprobe"""
    try:
        probe = ffmpeg.probe(str(audio_path))
        
        # Find audio stream
        audio_stream = None
        for stream in probe['streams']:
            if stream['codec_type'] == 'audio':
                audio_stream = stream
                break
        
        if not audio_stream:
            raise ValueError("No audio stream found")
        
        properties = {
            'duration_seconds': float(probe['format']['duration']),
            'size_bytes': int(probe['format']['size']),
            'sample_rate': int(audio_stream.get('sample_rate', 0)),
            'channels': int(audio_stream.get('channels', 0)),
            'codec': audio_stream.get('codec_name', 'unknown'),
        }
        
        return properties
        
    except Exception as e:
        logger.error(f"Error getting audio properties for {audio_path}: {e}")
        raise

def validate_audio_properties(audio_path: Path, expected_duration: Optional[float] = None,
                            min_sample_rate: int = 44100, min_channels: int = 1) -> bool:
    """Validate audio properties"""
    try:
        props = get_audio_properties(audio_path)
        
        # Check basic file size
        if props['size_bytes'] < 1000:
            logger.error(f"Audio file too small: {props['size_bytes']} bytes")
            return False
        
        # Check duration
        if expected_duration is not None:
            diff = abs(props['duration_seconds'] - expected_duration)
            if diff > 0.1:  # 100ms tolerance
                logger.error(f"Audio duration mismatch: expected {expected_duration:.2f}s, got {props['duration_seconds']:.2f}s")
                return False
        
        # Check sample rate and channels
        if props['sample_rate'] < min_sample_rate:
            logger.error(f"Sample rate too low: {props['sample_rate']} < {min_sample_rate}")
            return False
            
        if props['channels'] < min_channels:
            logger.error(f"Too few channels: {props['channels']} < {min_channels}")
            return False
        
        logger.info(f"✅ Audio validated: {props['duration_seconds']:.2f}s, "
                   f"{props['sample_rate']}Hz, {props['channels']}ch, {props['size_bytes']} bytes")
        return True
        
    except Exception as e:
        logger.error(f"Audio validation failed: {e}")
        return False

def validate_subtitle_file(subtitle_path: Path, expected_lines: Optional[int] = None) -> bool:
    """Validate subtitle file format and content"""
    try:
        if not validate_file_exists(subtitle_path, min_size=10):
            return False
        
        # Read and parse subtitle file
        with open(subtitle_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if not content:
            logger.error("Subtitle file is empty")
            return False
        
        # Basic SRT format validation
        lines = content.split('\n')
        subtitle_count = 0
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            if line and line.isdigit():
                subtitle_count += 1
                # Should have timestamp on next line
                if i + 1 < len(lines):
                    timestamp_line = lines[i + 1].strip()
                    if '-->' not in timestamp_line:
                        logger.error(f"Invalid timestamp format at subtitle {subtitle_count}")
                        return False
                i += 2  # Skip sequence number and timestamp
            else:
                i += 1
        
        if expected_lines and subtitle_count != expected_lines:
            logger.error(f"Subtitle count mismatch: expected {expected_lines}, got {subtitle_count}")
            return False
        
        logger.info(f"✅ Subtitle validated: {subtitle_count} subtitles, {len(content)} characters")
        return True
        
    except Exception as e:
        logger.error(f"Subtitle validation failed: {e}")
        return False

def validate_expression_data(expression_data: Dict[str, Any]) -> bool:
    """Validate expression data structure"""
    required_fields = ['dialogues', 'translation', 'expression', 'expression_translation', 
                      'context_start_time', 'context_end_time', 'similar_expressions']
    
    for field in required_fields:
        if field not in expression_data:
            logger.error(f"Missing required field '{field}' in expression data")
            return False
    
    # Validate dialogues and translations
    dialogues_count = len(expression_data['dialogues']) if isinstance(expression_data['dialogues'], list) else 0
    translation_count = len(expression_data['translation']) if isinstance(expression_data['translation'], list) else 0
    
    if dialogues_count != translation_count:
        logger.error(f"❌ Dialogues and translations count mismatch: {dialogues_count} dialogues vs {translation_count} translations")
        logger.error(f"❌ Dialogues: {expression_data['dialogues']}")
        logger.error(f"❌ Translations: {expression_data['translation']}")
        logger.error(f"❌ This expression should be filtered out: {expression_data.get('expression', 'unknown')}")
        # This is now an error that should cause the expression to be dropped
        return False
    else:
        logger.info(f"✅ Dialogues and translations match: {dialogues_count} items each")
    
    # Validate timestamps format (basic check)
    import re
    timestamp_pattern = r'^\d{2}:\d{2}:\d{2}[.,]\d{3,6}$'
    
    if not re.match(timestamp_pattern, expression_data['context_start_time']):
        logger.error(f"Invalid context_start_time format: {expression_data['context_start_time']}")
        return False
        
    if not re.match(timestamp_pattern, expression_data['context_end_time']):
        logger.error(f"Invalid context_end_time format: {expression_data['context_end_time']}")
        return False
    
    if not isinstance(expression_data['similar_expressions'], list):
        logger.error("similar_expressions should be a list")
        return False
    
    logger.info(f"✅ Expression data validated: '{expression_data['expression']}'")
    return True

def time_to_seconds(time_str: str) -> float:
    """Convert time string (HH:MM:SS,mmm) to seconds"""
    try:
        # Handle both comma and dot separators
        if ',' in time_str:
            time_part, ms_part = time_str.split(',')
        else:
            time_part, ms_part = time_str.split('.')
        
        hours, minutes, seconds = map(int, time_part.split(':'))
        milliseconds = int(ms_part)
        
        total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000
        return total_seconds
    except Exception as e:
        logger.error(f"Error parsing time string '{time_str}': {e}")
        raise

def save_test_results(step_num: int, results: Dict[str, Any], filename: str = "test_results.json"):
    """Save test results to JSON file"""
    output_dir = Path(f"test_output/step{step_num}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results_file = output_dir / filename
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"💾 Test results saved: {results_file}")

def load_test_results(step_num: int, filename: str = "test_results.json") -> Dict[str, Any]:
    """Load test results from JSON file"""
    results_file = Path(f"test_output/step{step_num}") / filename
    
    if not results_file.exists():
        raise FileNotFoundError(f"Test results not found: {results_file}")
    
    with open(results_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def log_step_start(step_num: int, description: str):
    """Log the start of a test step"""
    print(f"\n{'='*60}")
    print(f"🧪 STEP {step_num}: {description}")
    print(f"{'='*60}")

def log_step_complete(step_num: int, success: bool, message: str = ""):
    """Log the completion of a test step"""
    status = "✅ PASSED" if success else "❌ FAILED"
    print(f"\n{'='*60}")
    print(f"{status} - STEP {step_num} COMPLETE")
    if message:
        print(f"📝 {message}")
    print(f"{'='*60}\n")
