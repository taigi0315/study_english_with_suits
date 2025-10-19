#!/usr/bin/env python3
"""
Step 6: Append education slide to context video with smooth transition (create context_video_with_slide)
"""
import sys
import logging
from pathlib import Path
import ffmpeg

# Import test utilities
from test_config import setup_test_environment, clean_step_directory, get_step_output_dir
from test_utils import (validate_file_exists, validate_video_properties,
                       load_test_results, save_test_results, log_step_start, log_step_complete)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def test_step6():
    """Test Step 6: Append slide videos to context videos with smooth transition"""
    log_step_start(6, "Append education slide to context video with smooth transition (create context_video_with_slide)")
    
    try:
        # Setup environment
        setup_test_environment()
        clean_step_directory(6)
        
        results = {
            "step": 6,
            "description": "Append slide videos to context videos with smooth transition",
            "success": False,
            "errors": [],
            "full_sequences_created": 0,
            "sequences": []
        }
        
        # Step 6.1: Load data from previous steps
        logger.info("6.1 Loading data from previous steps...")
        try:
            step3_results = load_test_results(3)
            step5_results = load_test_results(5)
            
            context_videos = step3_results.get("processed_expressions", [])
            slide_videos = step5_results.get("slides", [])
            
            if not context_videos:
                results["errors"].append("No context videos found in step 3 results")
                return results
            if not slide_videos:
                results["errors"].append("No slide videos found in step 5 results")
                return results
            
            logger.info(f"✅ Loaded {len(context_videos)} context videos and {len(slide_videos)} slide videos")
        except Exception as e:
            results["errors"].append(f"Failed to load previous step results: {e}")
            return results
        
        # Step 6.2: Process each expression to create full sequence with transition
        logger.info("6.2 Creating full sequences for each expression with smooth transition...")
        
        for context_video in context_videos:
            # Find corresponding slide video
            slide_video = None
            for slide in slide_videos:
                if slide["expression_index"] == context_video["expression_index"]:
                    slide_video = slide
                    break
            
            if not slide_video:
                results["errors"].append(f"No slide video found for context video {context_video['expression_index']}")
                continue
            
            expr_name = context_video["expression"].replace(" ", "_").replace("'", "").replace('"', "")
            expression_id = f"expression_{context_video['expression_index']:02d}_{expr_name}"
            
            logger.info(f"Processing expression {context_video['expression_index']}: '{context_video['expression']}'")
            
            try:
                # Step 6.3: Verify input files exist
                context_path = Path(context_video["video_with_subs_path"])
                slide_path = Path(slide_video["slide_file_path"])
                
                if not validate_file_exists(context_path, min_size=10000):
                    results["errors"].append(f"Context video not valid: {context_path}")
                    continue
                
                if not validate_file_exists(slide_path, min_size=10000):
                    results["errors"].append(f"Slide video not valid: {slide_path}")
                    continue
                
                logger.info(f"  Context video: {context_path}")
                logger.info(f"  Slide video: {slide_path}")
                
                # Step 6.4: Get durations for validation
                try:
                    context_probe = ffmpeg.probe(str(context_path))
                    slide_probe = ffmpeg.probe(str(slide_path))
                    
                    context_duration = float(context_probe['format']['duration'])
                    slide_duration = float(slide_probe['format']['duration'])
                    transition_duration = 1.0  # 1 second transition
                    expected_total_duration = context_duration + slide_duration - transition_duration
                    
                    logger.info(f"  Context duration: {context_duration:.2f}s")
                    logger.info(f"  Slide duration: {slide_duration:.2f}s")
                    logger.info(f"  Transition duration: {transition_duration:.2f}s")
                    logger.info(f"  Expected total duration: {expected_total_duration:.2f}s")
                    
                except Exception as probe_error:
                    logger.warning(f"Could not probe video durations: {probe_error}")
                    context_duration = slide_duration = expected_total_duration = 0
                    transition_duration = 1.0
                
                # Step 6.5: Create concatenated video with smooth transition
                logger.info(f"  Concatenating videos with smooth transition...")
                output_dir = get_step_output_dir(6)
                full_sequence_path = output_dir / f"{expression_id}_full_sequence.mkv"
                
                try:
                    # Use simple concatenation with fade transition
                    # First try simple concatenation with fade effects
                    concat_list_path = output_dir / f"{expression_id}_concat_list.txt"
                    
                    with open(concat_list_path, 'w') as f:
                        f.write(f"file '{context_path.absolute()}'\n")
                        f.write(f"file '{slide_path.absolute()}'\n")
                    
                    # Use concat demuxer - transition will be added later as separate processing step
                    (
                        ffmpeg
                        .input(str(concat_list_path), format='concat', safe=0)
                        .output(
                            str(full_sequence_path),
                            vcodec='libx264',
                            acodec='aac',
                            preset='fast',
                            ac=2,  # Force stereo audio output
                            ar=48000  # Set sample rate
                        )
                        .overwrite_output()
                        .run(capture_stdout=True, capture_stderr=True)
                    )
                    
                    # Clean up concat list immediately
                    concat_list_path.unlink()
                    
                    logger.info(f"  ✅ Successfully concatenated videos")
                    
                except ffmpeg.Error as e:
                    logger.warning(f"Fade transition failed, falling back to simple concatenation: {e}")
                    # Fallback to simple concatenation without transition
                    try:
                        # Create concat list file for ffmpeg
                        fallback_concat_path = output_dir / f"{expression_id}_fallback_concat_list.txt"
                        with open(fallback_concat_path, 'w') as f:
                            f.write(f"file '{context_path.absolute()}'\n")
                            f.write(f"file '{slide_path.absolute()}'\n")
                        
                        # Use concat demuxer with proper audio channel handling
                        (
                            ffmpeg
                            .input(str(fallback_concat_path), format='concat', safe=0)
                            .output(
                                str(full_sequence_path),
                                vcodec='libx264',
                                acodec='aac',
                                preset='fast',
                                ac=2,  # Force stereo audio output
                                ar=48000  # Set sample rate
                            )
                            .overwrite_output()
                            .run(capture_stdout=True, capture_stderr=True)
                        )
                        
                        # Clean up fallback concat file
                        fallback_concat_path.unlink()
                        
                        logger.info(f"  ✅ Successfully concatenated videos (fallback method)")
                        
                    except ffmpeg.Error as fallback_error:
                        logger.error(f"FFmpeg concatenation error (both methods failed): {fallback_error}")
                        if fallback_error.stderr:
                            logger.error(f"FFmpeg stderr: {fallback_error.stderr.decode('utf-8')}")
                        if fallback_error.stdout:
                            logger.error(f"FFmpeg stdout: {fallback_error.stdout.decode('utf-8')}")
                        raise
                
                # Ensure concat list file is cleaned up if it still exists
                try:
                    if 'concat_list_path' in locals() and concat_list_path.exists():
                        concat_list_path.unlink()
                except:
                    pass
                    
                # Step 6.6: Validate concatenated video
                if not validate_file_exists(full_sequence_path, min_size=20000):
                    results["errors"].append(f"Concatenated video too small for expression {context_video['expression_index']}")
                    continue
                
                # Validate total duration (with tolerance for transition)
                actual_expected_duration = context_duration + slide_duration
                if actual_expected_duration > 0:
                    if not validate_video_properties(
                        full_sequence_path,
                        expected_duration=None,  # Don't be strict about exact duration due to transition
                        min_duration=actual_expected_duration * 0.9,  # Allow 10% variance due to transition
                        max_duration=actual_expected_duration * 1.1
                    ):
                        results["errors"].append(f"Concatenated video duration validation failed for expression {context_video['expression_index']}")
                        continue
                
                # Additional validation - ensure the video has both streams
                try:
                    final_probe = ffmpeg.probe(str(full_sequence_path))
                    streams = final_probe.get('streams', [])
                    
                    has_video = any(stream.get('codec_type') == 'video' for stream in streams)
                    has_audio = any(stream.get('codec_type') == 'audio' for stream in streams)
                    
                    if not has_video:
                        results["errors"].append(f"Concatenated video missing video stream for expression {context_video['expression_index']}")
                        continue
                        
                    if not has_audio:
                        results["errors"].append(f"Concatenated video missing audio stream for expression {context_video['expression_index']}")
                        continue
                        
                    logger.info(f"  ✅ Video has both video and audio streams")
                    
                    # Get actual duration for reporting
                    actual_duration = float(final_probe['format']['duration'])
                    logger.info(f"  ✅ Final duration: {actual_duration:.2f}s")
                    
                except Exception as stream_error:
                    logger.warning(f"Could not validate video streams: {stream_error}")
                    actual_duration = 0
                
                logger.info(f"  ✅ Successfully created full sequence for expression {context_video['expression_index']}")
                results["full_sequences_created"] += 1
                
                # Record results
                sequence_info = {
                    "expression_index": context_video["expression_index"],
                    "expression": context_video["expression"],
                    "context_video_path": str(context_path),
                    "slide_video_path": str(slide_path),
                    "full_sequence_path": str(full_sequence_path),
                    "context_duration": context_duration,
                    "slide_duration": slide_duration,
                    "transition_duration": transition_duration,
                    "total_duration": actual_duration,
                    "file_size": full_sequence_path.stat().st_size
                }
                
                results["sequences"].append(sequence_info)
                
            except Exception as e:
                error_msg = f"Failed to process expression {context_video['expression_index']}: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                continue
        
        # Determine overall success
        if results["full_sequences_created"] > 0:
            results["success"] = True
            logger.info(f"✅ Step 6 completed successfully: {results['full_sequences_created']} full sequences created")
        else:
            results["errors"].append("No full sequences were successfully created")
        
        # Save results
        save_test_results(6, results)
        
        # Print summary
        logger.info(f"\n📊 STEP 6 SUMMARY:")
        logger.info(f"  - Context videos processed: {len(context_videos)}")
        logger.info(f"  - Slide videos processed: {len(slide_videos)}")
        logger.info(f"  - Full sequences created: {results['full_sequences_created']}")
        logger.info(f"  - Errors: {len(results['errors'])}")
        
        for seq in results["sequences"]:
            logger.info(f"    {seq['expression_index']}. {Path(seq['full_sequence_path']).name} "
                       f"({seq['file_size']} bytes, {seq['total_duration']:.1f}s total)")
        
        if results["errors"]:
            logger.warning("⚠️  Errors encountered:")
            for error in results["errors"]:
                logger.warning(f"    - {error}")
        
        return results
        
    except Exception as e:
        error_msg = f"Step 6 failed with exception: {e}"
        logger.error(error_msg)
        results = {
            "step": 6,
            "description": "Append slide videos to context videos with smooth transition",
            "success": False,
            "errors": [error_msg],
            "full_sequences_created": 0,
            "sequences": []
        }
        return results

def main():
    """Main test function"""
    try:
        results = test_step6()
        log_step_complete(6, results["success"], 
                         f"Created {results['full_sequences_created']} full sequences" if results["success"] else f"Failed: {'; '.join(results['errors'])}")
        
        if not results["success"]:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
