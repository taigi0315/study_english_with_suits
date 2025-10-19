#!/usr/bin/env python3
"""
Step 4: Extract audio of the specific expression phrase
"""
import sys
import logging
from pathlib import Path

# Import test utilities
from test_config import setup_test_environment, clean_step_directory, get_step_output_dir, VIDEO_FILE, SUBTITLE_FILE
from test_utils import (validate_file_exists, validate_audio_properties, 
                       load_test_results, save_test_results, log_step_start, log_step_complete, time_to_seconds)

# Import LangFlix components
from langflix.video_processor import VideoProcessor
from langflix.subtitle_processor import SubtitleProcessor
from langflix.models import ExpressionAnalysis

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def _time_to_seconds(time_str: str) -> float:
    """Convert time string (HH:MM:SS,mmm or HH:MM:SS.mmm) to seconds"""
    try:
        # Handle both comma and dot formats
        if ',' in time_str:
            time_part, ms_part = time_str.split(',')
        elif '.' in time_str:
            # For HH:MM:SS.mmmmmm format, take only the first 3 digits
            parts = time_str.split('.')
            time_part = parts[0]
            ms_full = parts[1]
            # Take only first 3 digits of milliseconds
            ms_part = ms_full[:3].ljust(3, '0')
        else:
            raise ValueError(f"No time separator found in: {time_str}")
        
        hours, minutes, seconds = map(int, time_part.split(':'))
        milliseconds = int(ms_part)
        
        return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000
    except Exception as e:
        raise ValueError(f"Invalid time format: {time_str}") from e

def test_step4():
    """Test Step 4: Extract audio of specific expression phrases"""
    log_step_start(4, "Extract audio of the specific expression phrase")
    
    try:
        # Setup environment
        setup_test_environment()
        clean_step_directory(4)
        
        results = {
            "step": 4,
            "description": "Extract audio of specific expression phrases",
            "success": False,
            "errors": [],
            "audio_files_created": 0,
            "audio_extractions": []
        }
        
        # Step 4.1: Load expression data from step 1
        logger.info("4.1 Loading expression data from step 1...")
        try:
            step1_results = load_test_results(1)
            expressions = step1_results["expressions"]
            
            if not expressions:
                results["errors"].append("No expressions found in step 1 results")
                return results
            
            logger.info(f"✅ Loaded {len(expressions)} expressions from step 1")
        except Exception as e:
            results["errors"].append(f"Failed to load step 1 results: {e}")
            return results
        
        # Step 4.2: Verify video file exists
        logger.info("4.2 Verifying video file...")
        if not validate_file_exists(Path(VIDEO_FILE), min_size=1000000):  # 1MB minimum
            results["errors"].append(f"Video file validation failed: {VIDEO_FILE}")
            return results
        logger.info(f"✅ Video file validated: {VIDEO_FILE}")
        
        # Step 4.3: Initialize subtitle processor for exact timing lookup
        logger.info("4.3 Initializing subtitle processor for exact expression timing...")
        subtitle_processor = SubtitleProcessor(str(SUBTITLE_FILE))
        
        # Step 4.4: Process each expression to extract audio
        logger.info("4.3 Extracting audio for each expression...")
        
        for i, expr_data in enumerate(expressions):
            expr_name = expr_data["expression"].replace(" ", "_").replace("'", "").replace('"', "")
            expression_id = f"expression_{i+1:02d}_{expr_name}"
            
            logger.info(f"Processing expression {i+1}: '{expr_data['expression']}'")
            
            try:
                # Step 4.5: Create ExpressionAnalysis object and find exact timing
                expression = ExpressionAnalysis(
                    dialogues=expr_data["dialogues"],
                    translation=expr_data["translation"],
                    expression=expr_data["expression"],
                    expression_translation=expr_data["expression_translation"],
                    context_start_time=expr_data["context_start_time"],
                    context_end_time=expr_data["context_end_time"],
                    similar_expressions=expr_data["similar_expressions"]
                )
                
                # Check if LLM provided exact timing
                if hasattr(expression, 'expression_start_time') and hasattr(expression, 'expression_end_time') and \
                   expression.expression_start_time and expression.expression_end_time:
                    expr_start_time = expression.expression_start_time
                    expr_end_time = expression.expression_end_time
                    logger.info(f"  Using LLM-provided exact timing: {expr_start_time} -> {expr_end_time}")
                else:
                    # Use subtitle processor to find exact expression timing
                    logger.info(f"  Finding exact expression timing in subtitles...")
                    expr_start_time, expr_end_time = subtitle_processor.find_expression_timing(expression)
                    logger.info(f"  Found exact timing: {expr_start_time} -> {expr_end_time}")
                
                # Convert to seconds for duration calculation
                expr_start_sec = _time_to_seconds(expr_start_time)
                expr_end_sec = _time_to_seconds(expr_end_time)
                expression_duration = expr_end_sec - expr_start_sec
                
                logger.info(f"  Expression audio range: {expr_start_time} -> {expr_end_time}")
                logger.info(f"  Expected duration: {expression_duration:.2f} seconds")
                
                # Create output path for audio
                output_dir = get_step_output_dir(4)
                audio_output_path = output_dir / f"{expression_id}_audio.wav"
                
                # Step 4.6: Extract audio using ffmpeg
                logger.info(f"  Extracting audio to: {audio_output_path}")
                
                import ffmpeg
                try:
                    # Step 4.6: Extract audio using ffmpeg with exact timing
                    logger.info(f"  Extracting audio from {expr_start_sec:.3f}s to {expr_end_sec:.3f}s")
                    
                    (
                        ffmpeg
                        .input(str(VIDEO_FILE), ss=expr_start_sec, t=expression_duration)
                        .output(str(audio_output_path), acodec='pcm_s16le', ar=44100, ac=2)
                        .overwrite_output()
                        .run(quiet=True)
                    )
                    
                    # Step 4.7: Validate extracted audio
                    if not validate_file_exists(audio_output_path, min_size=1000):
                        results["errors"].append(f"Extracted audio too small for expression {i+1}")
                        continue
                    
                    if not validate_audio_properties(
                        audio_output_path,
                        expected_duration=expression_duration,
                        min_sample_rate=44100,
                        min_channels=1
                    ):
                        results["errors"].append(f"Audio properties validation failed for expression {i+1}")
                        continue
                    
                    logger.info(f"  ✅ Successfully extracted exact expression audio for: '{expr_data['expression']}'")
                    results["audio_files_created"] += 1
                    
                    # Record extraction results
                    audio_info = {
                        "expression_index": i + 1,
                        "expression": expr_data["expression"],
                        "audio_file_path": str(audio_output_path),
                        "start_time": expr_start_time,
                        "end_time": expr_end_time,
                        "expected_duration": expression_duration,
                        "file_size": audio_output_path.stat().st_size
                    }
                    
                    results["audio_extractions"].append(audio_info)
                    
                except Exception as ffmpeg_error:
                    error_msg = f"FFmpeg failed for expression {i+1}: {ffmpeg_error}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    continue
                
            except Exception as e:
                error_msg = f"Failed to process expression {i+1}: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                continue
        
        # Determine overall success
        if results["audio_files_created"] > 0:
            results["success"] = True
            logger.info(f"✅ Step 4 completed successfully: {results['audio_files_created']} audio files created")
        else:
            results["errors"].append("No audio files were successfully created")
        
        # Save results
        save_test_results(4, results)
        
        # Print summary
        logger.info(f"\n📊 STEP 4 SUMMARY:")
        logger.info(f"  - Expressions processed: {len(expressions)}")
        logger.info(f"  - Audio files created: {results['audio_files_created']}")
        logger.info(f"  - Errors: {len(results['errors'])}")
        
        for audio in results["audio_extractions"]:
            logger.info(f"    {audio['expression_index']}. {Path(audio['audio_file_path']).name} ({audio['file_size']} bytes)")
        
        if results["errors"]:
            logger.warning("⚠️  Errors encountered:")
            for error in results["errors"]:
                logger.warning(f"    - {error}")
        
        return results
        
    except Exception as e:
        error_msg = f"Step 4 failed with exception: {e}"
        logger.error(error_msg)
        results = {
            "step": 4,
            "description": "Extract audio of specific expression phrases",
            "success": False,
            "errors": [error_msg],
            "audio_files_created": 0,
            "audio_extractions": []
        }
        return results

def main():
    """Main test function"""
    try:
        results = test_step4()
        log_step_complete(4, results["success"], 
                         f"Created {results['audio_files_created']} audio files" if results["success"] else f"Failed: {'; '.join(results['errors'])}")
        
        if not results["success"]:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
