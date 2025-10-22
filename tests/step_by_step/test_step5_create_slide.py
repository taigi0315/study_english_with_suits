#!/usr/bin/env python3
"""
Step 5: Build education slide with background, expression, and translation text
"""
import sys
import logging
from pathlib import Path

# Import test utilities
from test_config import setup_test_environment, clean_step_directory, get_step_output_dir, VIDEO_FILE, TEST_SETTINGS
from test_utils import (validate_file_exists, validate_video_properties, 
                       load_test_results, save_test_results, log_step_start, log_step_complete)

# Import LangFlix components
from langflix.core.video_editor import VideoEditor
from langflix.core.models import ExpressionAnalysis

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def test_step5():
    """Test Step 5: Create educational slides"""
    log_step_start(5, "Build education slide with background, expression, and translation text")
    
    try:
        # Setup environment
        setup_test_environment()
        clean_step_directory(5)
        
        results = {
            "step": 5,
            "description": "Create educational slides with background and text",
            "success": False,
            "errors": [],
            "slides_created": 0,
            "slides": []
        }
        
        # Step 5.1: Load expression data from step 1
        logger.info("5.1 Loading expression data from step 1...")
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
        
        # Step 5.2: Load audio data from step 4
        logger.info("5.2 Loading audio data from step 4...")
        try:
            step4_results = load_test_results(4)
            audio_extractions = step4_results.get("audio_extractions", [])
            
            if not audio_extractions:
                results["errors"].append("No audio extractions found in step 4 results")
                return results
            
            logger.info(f"✅ Loaded {len(audio_extractions)} audio extractions from step 4")
        except Exception as e:
            results["errors"].append(f"Failed to load step 4 results: {e}")
            return results
        
        # Step 5.3: Initialize video editor
        logger.info("5.3 Initializing video editor...")
        output_dir = get_step_output_dir(5)
        language_code = TEST_SETTINGS.get("language_code", "es")
        video_editor = VideoEditor(str(output_dir), language_code)
        
        # Step 5.4: Create slides for each expression
        logger.info("5.4 Creating educational slides...")
        
        for i, expr_data in enumerate(expressions):
            # Find corresponding audio extraction
            audio_info = None
            for audio in audio_extractions:
                if audio["expression_index"] == i + 1:
                    audio_info = audio
                    break
            
            if not audio_info:
                results["errors"].append(f"No audio found for expression {i+1}")
                continue
            
            expr_name = expr_data["expression"].replace(" ", "_").replace("'", "").replace('"', "")
            expression_id = f"expression_{i+1:02d}_{expr_name}"
            
            logger.info(f"Processing expression {i+1}: '{expr_data['expression']}'")
            
            try:
                # Step 5.5: Create ExpressionAnalysis object with exact timing from step 4
                expression = ExpressionAnalysis(
                    dialogues=expr_data["dialogues"],
                    translation=expr_data["translation"],
                    expression=expr_data["expression"],
                    expression_translation=expr_data["expression_translation"],
                    context_start_time=expr_data["context_start_time"],
                    context_end_time=expr_data["context_end_time"],
                    expression_start_time=audio_info["start_time"],
                    expression_end_time=audio_info["end_time"],
                    similar_expressions=expr_data["similar_expressions"]
                )
                
                # Step 5.6: Create educational slide
                logger.info(f"  Creating educational slide...")
                
                slide_output_path = output_dir / f"{expression_id}_slide.mkv"
                
                # Use the expected audio duration to calculate slide duration
                # Slide duration = expression_duration * 3 + 3 seconds padding
                audio_duration = audio_info["expected_duration"]
                expected_slide_duration = audio_duration * 3 + 1
                
                logger.info(f"  Expected slide duration: {expected_slide_duration:.2f} seconds")
                
                # Create the slide using video editor
                # Method signature: _create_educational_slide(self, expression_source_video: str, expression: ExpressionAnalysis) -> str
                try:
                    slide_path = video_editor._create_educational_slide(
                        str(VIDEO_FILE),  # expression_source_video
                        expression
                    )
                    
                    if not slide_path:
                        results["errors"].append(f"Failed to create slide for expression {i+1}")
                        continue
                    
                    # Copy the slide to our desired output location
                    import shutil
                    shutil.copy2(slide_path, slide_output_path)
                    logger.info(f"  Slide created: {slide_output_path}")
                    
                except Exception as slide_error:
                    error_msg = f"Failed to create slide for expression {i+1}: {slide_error}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    continue
                
                # Step 5.7: Validate created slide
                logger.info(f"  Validating slide: {slide_output_path}")
                
                if not validate_file_exists(slide_output_path, min_size=10000):
                    results["errors"].append(f"Slide file too small for expression {i+1}")
                    continue
                
                # Validate slide properties
                if not validate_video_properties(
                    slide_output_path,
                    expected_duration=expected_slide_duration,
                    min_duration=expected_slide_duration * 0.9,
                    max_duration=expected_slide_duration * 1.2  # Allow more tolerance for slides
                ):
                    results["errors"].append(f"Slide video properties validation failed for expression {i+1}")
                    continue
                
                # Get actual video properties for reporting
                import ffmpeg
                try:
                    probe = ffmpeg.probe(str(slide_output_path))
                    video_stream = next(
                        (stream for stream in probe['streams'] if stream['codec_type'] == 'video'), 
                        None
                    )
                    
                    if video_stream:
                        actual_width = int(video_stream.get('width', 0))
                        actual_height = int(video_stream.get('height', 0))
                        actual_duration = float(probe['format']['duration'])
                        
                        logger.info(f"  ✅ Slide properties: {actual_width}x{actual_height}, {actual_duration:.2f}s")
                    else:
                        logger.warning("Could not get video properties from slide")
                        actual_width = actual_height = actual_duration = 0
                        
                except Exception as props_error:
                    logger.warning(f"Could not read slide properties: {props_error}")
                    actual_width = actual_height = actual_duration = 0
                
                logger.info(f"  ✅ Successfully created slide for expression {i+1}")
                results["slides_created"] += 1
                
                # Record slide creation results
                slide_info = {
                    "expression_index": i + 1,
                    "expression": expr_data["expression"],
                    "slide_file_path": str(slide_output_path),
                    "expected_duration": expected_slide_duration,
                    "actual_duration": actual_duration if 'actual_duration' in locals() else 0,
                    "video_width": actual_width if 'actual_width' in locals() else 0,
                    "video_height": actual_height if 'actual_height' in locals() else 0,
                    "file_size": slide_output_path.stat().st_size
                }
                
                results["slides"].append(slide_info)
                
            except Exception as e:
                error_msg = f"Failed to create slide for expression {i+1}: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                continue
        
        # Determine overall success
        if results["slides_created"] > 0:
            results["success"] = True
            logger.info(f"✅ Step 5 completed successfully: {results['slides_created']} slides created")
        else:
            results["errors"].append("No slides were successfully created")
        
        # Save results
        save_test_results(5, results)
        
        # Print summary
        logger.info(f"\n📊 STEP 5 SUMMARY:")
        logger.info(f"  - Expressions processed: {len(expressions)}")
        logger.info(f"  - Audio extractions available: {len(audio_extractions)}")
        logger.info(f"  - Slides created: {results['slides_created']}")
        logger.info(f"  - Errors: {len(results['errors'])}")
        
        for slide in results["slides"]:
            logger.info(f"    {slide['expression_index']}. {Path(slide['slide_file_path']).name} "
                       f"({slide['file_size']} bytes, {slide['actual_duration']:.1f}s)")
        
        if results["errors"]:
            logger.warning("⚠️  Errors encountered:")
            for error in results["errors"]:
                logger.warning(f"    - {error}")
        
        return results
        
    except Exception as e:
        error_msg = f"Step 5 failed with exception: {e}"
        logger.error(error_msg)
        results = {
            "step": 5,
            "description": "Create educational slides with background and text",
            "success": False,
            "errors": [error_msg],
            "slides_created": 0,
            "slides": []
        }
        return results

def main():
    """Main test function"""
    try:
        results = test_step5()
        log_step_complete(5, results["success"], 
                         f"Created {results['slides_created']} slides" if results["success"] else f"Failed: {'; '.join(results['errors'])}")
        
        if not results["success"]:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
