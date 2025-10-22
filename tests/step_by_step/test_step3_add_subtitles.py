#!/usr/bin/env python3
"""
Step 3: Update sliced video with target language subtitles (create context_video)
"""
import sys
import logging
from pathlib import Path

# Import test utilities
from test_config import setup_test_environment, clean_step_directory, get_step_output_dir, SUBTITLE_FILE
from test_utils import (validate_file_exists, validate_video_properties, validate_subtitle_file, 
                       load_test_results, save_test_results, log_step_start, log_step_complete, time_to_seconds)

# Import LangFlix components
from langflix.core.models import ExpressionAnalysis
from langflix.core.subtitle_processor import SubtitleProcessor

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def test_step3():
    """Test Step 3: Add target language subtitles to context video"""
    log_step_start(3, "Update sliced video with target language subtitles (create context_video)")
    
    try:
        # Setup environment
        setup_test_environment()
        clean_step_directory(3)
        
        results = {
            "step": 3,
            "description": "Add target language subtitles to context video",
            "success": False,
            "errors": [],
            "videos_with_subs_created": 0,
            "subtitle_files_created": 0,
            "processed_expressions": []
        }
        
        # Step 3.1: Load data from previous steps
        logger.info("3.1 Loading data from previous steps...")
        try:
            step1_results = load_test_results(1)
            step2_results = load_test_results(2)
            
            expressions = step1_results["expressions"]
            video_clips = step2_results["clips"]
            
            if not expressions:
                results["errors"].append("No expressions found in step 1 results")
                return results
            if not video_clips:
                results["errors"].append("No video clips found in step 2 results")
                return results
            
            logger.info(f"✅ Loaded {len(expressions)} expressions and {len(video_clips)} video clips")
        except Exception as e:
            results["errors"].append(f"Failed to load previous step results: {e}")
            return results
        
        # Step 3.2: Initialize subtitle processor
        logger.info("3.2 Initializing subtitle processor...")
        subtitle_processor = SubtitleProcessor(str(SUBTITLE_FILE))
        
        # Step 3.3: Process each expression
        logger.info("3.3 Processing each expression...")
        
        for i, expr_data in enumerate(expressions):
            # Find corresponding video clip
            clip_info = None
            for clip in video_clips:
                if clip["expression_index"] == i + 1:
                    clip_info = clip
                    break
            
            if not clip_info:
                results["errors"].append(f"No video clip found for expression {i+1}")
                continue
            
            expr_name = expr_data["expression"].replace(" ", "_").replace("'", "").replace('"', "")
            expression_id = f"expression_{i+1:02d}_{expr_name}"
            
            logger.info(f"Processing expression {i+1}: '{expr_data['expression']}'")
            
            try:
                # Step 3.4: Create ExpressionAnalysis object
                expression = ExpressionAnalysis(
                    dialogues=expr_data["dialogues"],
                    translation=expr_data["translation"],
                    expression=expr_data["expression"],
                    expression_translation=expr_data["expression_translation"],
                    context_start_time=expr_data["context_start_time"],
                    context_end_time=expr_data["context_end_time"],
                    similar_expressions=expr_data["similar_expressions"]
                )
                
                # Step 3.5: Generate dual-language subtitle file (this will also extract subtitles)
                logger.info(f"  Generating dual-language subtitle file...")
                output_dir = get_step_output_dir(3)
                subtitle_output_path = output_dir / f"{expression_id}_subtitles.srt"
                
                success = subtitle_processor.create_dual_language_subtitle_file(
                    expression,
                    str(subtitle_output_path)
                )
                
                if not success:
                    results["errors"].append(f"Failed to create subtitle file for expression {i+1}")
                    continue
                
                # Step 3.7: Validate subtitle file
                if not validate_subtitle_file(subtitle_output_path):
                    results["errors"].append(f"Subtitle file validation failed for expression {i+1}")
                    continue
                
                logger.info(f"  ✅ Created subtitle file: {subtitle_output_path}")
                results["subtitle_files_created"] += 1
                
                # Step 3.8: Add subtitles to video using ffmpeg
                logger.info(f"  Adding subtitles to video...")
                context_clip_path = Path(clip_info["clip_path"])
                if not context_clip_path.exists():
                    results["errors"].append(f"Context clip not found: {context_clip_path}")
                    continue
                
                video_with_subs_path = output_dir / f"{expression_id}_context_with_subs.mkv"
                
                import ffmpeg
                try:
                    # Add subtitles to video
                    (
                        ffmpeg
                        .input(str(context_clip_path))
                        .output(
                            str(video_with_subs_path),
                            vf=f"subtitles={subtitle_output_path}:force_style='FontSize=24,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=1'",
                            vcodec='libx264',
                            acodec='copy',
                            preset='fast'
                        )
                        .overwrite_output()
                        .run(quiet=True)
                    )
                    
                    # Step 3.9: Validate video with subtitles
                    if not validate_file_exists(video_with_subs_path, min_size=10000):
                        results["errors"].append(f"Video with subtitles too small for expression {i+1}")
                        continue
                    
                    # Validate that duration is preserved
                    if not validate_video_properties(
                        video_with_subs_path,
                        expected_duration=clip_info["expected_duration"],
                        min_duration=clip_info["expected_duration"] * 0.95,
                        max_duration=clip_info["expected_duration"] * 1.05
                    ):
                        results["errors"].append(f"Video properties validation failed for expression {i+1}")
                        continue
                    
                    logger.info(f"  ✅ Created video with subtitles: {video_with_subs_path}")
                    results["videos_with_subs_created"] += 1
                    
                    # Record processing results
                    # Get subtitle count for reporting
                    context_subtitles = subtitle_processor.extract_subtitles_for_expression(expression)
                    processed_expr = {
                        "expression_index": i + 1,
                        "expression": expr_data["expression"],
                        "context_clip_path": str(context_clip_path),
                        "subtitle_file_path": str(subtitle_output_path),
                        "video_with_subs_path": str(video_with_subs_path),
                        "context_duration": clip_info["expected_duration"],
                        "subtitle_count": len(context_subtitles) if context_subtitles else 0
                    }
                    results["processed_expressions"].append(processed_expr)
                    
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
        if results["videos_with_subs_created"] > 0 and results["subtitle_files_created"] > 0:
            results["success"] = True
            logger.info(f"✅ Step 3 completed successfully: {results['videos_with_subs_created']} videos with subtitles created")
        else:
            results["errors"].append("No videos with subtitles were successfully created")
        
        # Save results
        save_test_results(3, results)
        
        # Print summary
        logger.info(f"\n📊 STEP 3 SUMMARY:")
        logger.info(f"  - Expressions processed: {len(expressions)}")
        logger.info(f"  - Video clips input: {len(video_clips)}")
        logger.info(f"  - Subtitle files created: {results['subtitle_files_created']}")
        logger.info(f"  - Videos with subtitles created: {results['videos_with_subs_created']}")
        
        for expr in results["processed_expressions"]:
            logger.info(f"    {expr['expression_index']}. {Path(expr['video_with_subs_path']).name}")
        
        if results["errors"]:
            logger.warning("⚠️  Errors encountered:")
            for error in results["errors"]:
                logger.warning(f"    - {error}")
        
        return results
        
    except Exception as e:
        error_msg = f"Step 3 failed with exception: {e}"
        logger.error(error_msg)
        results = {
            "step": 3,
            "description": "Add target language subtitles to context video",
            "success": False,
            "errors": [error_msg],
            "videos_with_subs_created": 0,
            "subtitle_files_created": 0,
            "processed_expressions": []
        }
        return results

def main():
    """Main test function"""
    try:
        results = test_step3()
        log_step_complete(3, results["success"], 
                         f"Created {results['videos_with_subs_created']} videos with subtitles" if results["success"] else f"Failed: {'; '.join(results['errors'])}")
        
        if not results["success"]:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
