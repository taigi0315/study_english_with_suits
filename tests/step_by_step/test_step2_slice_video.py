#!/usr/bin/env python3
"""
Step 2: Use start/end time to slice video based on expression context
"""
import sys
import logging
from pathlib import Path

# Import test utilities
from test_config import setup_test_environment, clean_step_directory, get_step_output_dir, VIDEO_FILE
from test_utils import (validate_file_exists, validate_video_properties, load_test_results, 
                       save_test_results, log_step_start, log_step_complete, time_to_seconds)

# Import LangFlix components
from langflix.video_processor import VideoProcessor

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def test_step2():
    """Test Step 2: Slice video based on expression context"""
    log_step_start(2, "Use start/end time to slice video based on expression context")
    
    try:
        # Setup environment
        setup_test_environment()
        clean_step_directory(2)
        
        results = {
            "step": 2,
            "description": "Slice video based on expression context",
            "success": False,
            "errors": [],
            "video_clips_created": 0,
            "clips": []
        }
        
        # Step 2.1: Load expression data from step 1
        logger.info("2.1 Loading expression data from step 1...")
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
        
        # Step 2.2: Verify video file exists
        logger.info("2.2 Verifying video file...")
        if not validate_file_exists(Path(VIDEO_FILE), min_size=1000000):  # 1MB minimum
            results["errors"].append(f"Video file validation failed: {VIDEO_FILE}")
            return results
        logger.info(f"✅ Video file validated: {VIDEO_FILE}")
        
        # Step 2.3: Initialize video processor
        logger.info("2.3 Initializing video processor...")
        video_dir = str(VIDEO_FILE.parent)
        video_processor = VideoProcessor(video_dir)
        
        # Find video file
        video_path = video_processor.find_video_file(str(VIDEO_FILE.name))
        if not video_path:
            # Try to use the video file directly
            video_path = Path(VIDEO_FILE)
            if not video_path.exists():
                results["errors"].append(f"Could not find video file for: {VIDEO_FILE}")
                return results
        
        logger.info(f"✅ Using video file: {video_path}")
        
        # Step 2.4: Extract video clips for each expression
        logger.info("2.4 Extracting video clips for each expression...")
        
        for i, expr in enumerate(expressions):
            expr_name = expr["expression"].replace(" ", "_").replace("'", "").replace('"', "")
            clip_name = f"expression_{i+1:02d}_{expr_name}"
            
            logger.info(f"Processing expression {i+1}: '{expr['expression']}'")
            logger.info(f"  Context: {expr['context_start_time']} -> {expr['context_end_time']}")
            
            try:
                # Calculate expected duration
                start_seconds = time_to_seconds(expr['context_start_time'])
                end_seconds = time_to_seconds(expr['context_end_time'])
                expected_duration = end_seconds - start_seconds
                
                if expected_duration <= 0:
                    results["errors"].append(f"Invalid duration for expression {i+1}: {expected_duration}")
                    continue
                
                logger.info(f"  Expected duration: {expected_duration:.2f} seconds")
                
                # Create output path
                output_dir = get_step_output_dir(2)
                output_path = output_dir / f"{clip_name}_context_clip.mkv"
                
                # Extract video clip
                success = video_processor.extract_clip(
                    video_path=str(video_path),
                    start_time=expr['context_start_time'],
                    end_time=expr['context_end_time'],
                    output_path=str(output_path)
                )
                
                if not success:
                    results["errors"].append(f"Failed to extract clip for expression {i+1}")
                    continue
                
                # Step 2.5: Validate extracted clip
                logger.info(f"  Validating extracted clip: {output_path}")
                
                if not validate_file_exists(output_path, min_size=10000):  # 10KB minimum
                    results["errors"].append(f"Extracted clip too small for expression {i+1}")
                    continue
                
                # Validate video properties
                if not validate_video_properties(
                    output_path, 
                    expected_duration=expected_duration,
                    min_duration=expected_duration * 0.9,  # 90% tolerance
                    max_duration=expected_duration * 1.1   # 110% tolerance
                ):
                    results["errors"].append(f"Video properties validation failed for expression {i+1}")
                    continue
                
                # Record successful clip creation
                clip_info = {
                    "expression_index": i + 1,
                    "expression": expr["expression"],
                    "clip_path": str(output_path),
                    "start_time": expr['context_start_time'],
                    "end_time": expr['context_end_time'],
                    "expected_duration": expected_duration,
                    "file_size": output_path.stat().st_size
                }
                
                results["clips"].append(clip_info)
                results["video_clips_created"] += 1
                
                logger.info(f"✅ Successfully created clip for expression {i+1}")
                
            except Exception as e:
                error_msg = f"Failed to process expression {i+1}: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                continue
        
        # Determine overall success
        if results["video_clips_created"] > 0:
            results["success"] = True
            logger.info(f"✅ Step 2 completed successfully: {results['video_clips_created']} clips created")
        else:
            results["errors"].append("No video clips were successfully created")
        
        # Save results
        save_test_results(2, results)
        
        # Print summary
        logger.info(f"\n📊 STEP 2 SUMMARY:")
        logger.info(f"  - Expressions processed: {len(expressions)}")
        logger.info(f"  - Video clips created: {results['video_clips_created']}")
        logger.info(f"  - Errors: {len(results['errors'])}")
        
        for clip in results["clips"]:
            logger.info(f"    {clip['expression_index']}. {clip['clip_path']} ({clip['file_size']} bytes)")
        
        if results["errors"]:
            logger.warning("⚠️  Errors encountered:")
            for error in results["errors"]:
                logger.warning(f"    - {error}")
        
        return results
        
    except Exception as e:
        error_msg = f"Step 2 failed with exception: {e}"
        logger.error(error_msg)
        results = {
            "step": 2,
            "description": "Slice video based on expression context",
            "success": False,
            "errors": [error_msg],
            "video_clips_created": 0,
            "clips": []
        }
        return results

def main():
    """Main test function"""
    try:
        results = test_step2()
        log_step_complete(2, results["success"], 
                         f"Created {results['video_clips_created']} clips" if results["success"] else f"Failed: {'; '.join(results['errors'])}")
        
        if not results["success"]:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
