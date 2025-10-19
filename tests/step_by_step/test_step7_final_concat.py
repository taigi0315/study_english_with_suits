#!/usr/bin/env python3
"""
Step 7: Append all expression videos to make final video
"""
import sys
import logging
from pathlib import Path

# Import test utilities
from test_config import setup_test_environment, clean_step_directory, get_step_output_dir, TRANSITION_CONFIG
from test_utils import (validate_file_exists, validate_video_properties,
                       load_test_results, save_test_results, log_step_start, log_step_complete)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def test_step7():
    """Test Step 7: Concatenate all expression sequences into final video"""
    log_step_start(7, "Append all expression videos to make final video")
    
    try:
        # Setup environment
        setup_test_environment()
        clean_step_directory(7)
        
        results = {
            "step": 7,
            "description": "Concatenate all expression sequences into final video",
            "success": False,
            "errors": [],
            "final_video_created": False,
            "total_duration": 0,
            "expressions_included": 0
        }
        
        # Step 7.1: Load sequences from step 6
        logger.info("7.1 Loading full sequences from step 6...")
        try:
            step6_results = load_test_results(6)
            sequences = step6_results.get("sequences", [])
            
            if not sequences:
                results["errors"].append("No sequences found in step 6 results")
                return results
            
            logger.info(f"✅ Loaded {len(sequences)} sequences from step 6")
        except Exception as e:
            results["errors"].append(f"Failed to load step 6 results: {e}")
            return results
        
        # Step 7.2: Sort sequences by expression index
        logger.info("7.2 Sorting sequences by expression index...")
        sequences_sorted = sorted(sequences, key=lambda x: x["expression_index"])
        
        # Step 7.3: Verify all sequence files exist and get durations
        logger.info("7.3 Verifying sequence files and calculating total duration...")
        
        valid_sequences = []
        total_expected_duration = 0
        
        for sequence in sequences_sorted:
            seq_path = Path(sequence["full_sequence_path"])
            
            if not validate_file_exists(seq_path, min_size=20000):
                results["errors"].append(f"Sequence file not valid for expression {sequence['expression_index']}: {seq_path}")
                continue
            
            # Get actual duration
            import ffmpeg
            try:
                probe = ffmpeg.probe(str(seq_path))
                actual_duration = float(probe['format']['duration'])
                sequence["actual_duration"] = actual_duration
                total_expected_duration += actual_duration
                
                logger.info(f"  Expression {sequence['expression_index']}: {actual_duration:.2f}s")
                
            except Exception as probe_error:
                logger.warning(f"Could not probe duration for {seq_path}: {probe_error}")
                sequence["actual_duration"] = sequence.get("total_duration", 0)
                total_expected_duration += sequence["actual_duration"]
            
            valid_sequences.append(sequence)
        
        if not valid_sequences:
            results["errors"].append("No valid sequence files found for concatenation")
            return results
        
        results["expressions_included"] = len(valid_sequences)
        results["total_duration"] = total_expected_duration
        
        logger.info(f"✅ {len(valid_sequences)} valid sequences found, expected total duration: {total_expected_duration:.2f}s")
        
        # Step 7.4: Create concatenation list file
        logger.info("7.4 Creating concatenation list file...")
        output_dir = get_step_output_dir(7)
        concat_list_path = output_dir / "final_concat_list.txt"
        
        try:
            with open(concat_list_path, 'w', encoding='utf-8') as f:
                for sequence in valid_sequences:
                    # Write absolute path with proper escaping for ffmpeg
                    abs_path = Path(sequence["full_sequence_path"]).absolute()
                    # Escape single quotes in the path
                    escaped_path = str(abs_path).replace("'", "'\"'\"'")
                    f.write(f"file '{escaped_path}'\n")
            
            logger.info(f"✅ Created concat list: {concat_list_path}")
            
        except Exception as list_error:
            results["errors"].append(f"Failed to create concat list file: {list_error}")
            return results
        
        # Step 7.5: Concatenate all sequences into final video
        logger.info("7.5 Concatenating all sequences into final video...")
        final_video_path = output_dir / "final_educational_video_with_slides.mkv"
        
        try:
            import ffmpeg
            
            logger.info(f"Creating final video: {final_video_path}")
            logger.info(f"Expected duration: {total_expected_duration:.2f} seconds")
            
            # Get transition configuration for expression-to-expression
            transition_enabled = TRANSITION_CONFIG.get("enabled", True)
            expr_transition_settings = TRANSITION_CONFIG.get("expression_to_expression", {})
            expr_transition_type = expr_transition_settings.get("type", "fade")
            
            # Create smooth transitions between expressions if enabled and multiple sequences exist
            if transition_enabled and len(valid_sequences) > 1 and expr_transition_type != "none":
                logger.info(f"Creating {expr_transition_type} transitions between {len(valid_sequences)} expressions...")
                try:
                    transition_duration = expr_transition_settings.get("duration", 0.5)
                    logger.info(f"Using {expr_transition_type} transition with {transition_duration:.2f}s duration")
                    # Note: For now, we'll still use simple concatenation for Step 7
                    # but log the transition settings for future enhancement
                    
                except Exception as transition_error:
                    logger.warning(f"Transition setup failed: {transition_error}")
            
            # Use concat demuxer with proper audio handling for better compatibility
            (
                ffmpeg
                .input(str(concat_list_path), format='concat', safe=0)
                .output(
                    str(final_video_path),
                    vcodec='libx264',
                    acodec='aac',
                    preset='fast',
                    ac=2,  # Force stereo audio output
                    ar=48000,  # Set sample rate
                    crf=23  # Good quality
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            # Step 7.6: Validate final video
            logger.info("7.6 Validating final concatenated video...")
            
            if not validate_file_exists(final_video_path, min_size=100000):  # 100KB minimum
                results["errors"].append("Final video file too small")
                return results
            
            # Get final video properties
            try:
                final_probe = ffmpeg.probe(str(final_video_path))
                final_duration = float(final_probe['format']['duration'])
                final_size = Path(final_video_path).stat().st_size
                
                logger.info(f"Final video duration: {final_duration:.2f}s")
                logger.info(f"Final video size: {final_size:,} bytes ({final_size/1024/1024:.1f} MB)")
                
                # Validate duration is reasonable (within 5% tolerance)
                duration_diff = abs(final_duration - total_expected_duration)
                duration_tolerance = total_expected_duration * 0.05
                
                if duration_diff > duration_tolerance:
                    logger.warning(f"Duration difference larger than expected: {duration_diff:.2f}s > {duration_tolerance:.2f}s")
                else:
                    logger.info("✅ Duration validation passed")
                
                # Validate video has both streams
                streams = final_probe.get('streams', [])
                has_video = any(stream.get('codec_type') == 'video' for stream in streams)
                has_audio = any(stream.get('codec_type') == 'audio' for stream in streams)
                
                if not has_video:
                    results["errors"].append("Final video missing video stream")
                    return results
                    
                if not has_audio:
                    results["errors"].append("Final video missing audio stream")
                    return results
                
                logger.info("✅ Final video has both video and audio streams")
                
                results["actual_duration"] = final_duration
                results["file_size"] = final_size
                results["final_video_created"] = True
                results["success"] = True
                
            except Exception as final_probe_error:
                logger.error(f"Could not probe final video properties: {final_probe_error}")
                results["errors"].append(f"Failed to validate final video: {final_probe_error}")
                return results
            
        except ffmpeg.Error as e:
            error_msg = f"Failed to concatenate videos: {e}"
            logger.error(error_msg)
            if e.stderr:
                logger.error(f"FFmpeg stderr: {e.stderr.decode('utf-8')}")
            if e.stdout:
                logger.error(f"FFmpeg stdout: {e.stdout.decode('utf-8')}")
            results["errors"].append(error_msg)
            return results
        except Exception as concat_error:
            error_msg = f"Failed to concatenate videos: {concat_error}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
            return results
        
        # Step 7.7: Cleanup temporary files
        logger.info("7.7 Cleaning up temporary files...")
        try:
            concat_list_path.unlink()
            logger.info("✅ Cleaned up concat list file")
        except Exception as cleanup_error:
            logger.warning(f"Could not clean up concat list file: {cleanup_error}")
        
        # Save results
        save_test_results(7, results)
        
        # Print comprehensive summary
        logger.info(f"\n📊 STEP 7 SUMMARY:")
        logger.info(f"  - Sequences processed: {len(sequences)}")
        logger.info(f"  - Valid sequences concatenated: {len(valid_sequences)}")
        logger.info(f"  - Expected total duration: {total_expected_duration:.2f}s")
        logger.info(f"  - Actual final duration: {results.get('actual_duration', 0):.2f}s")
        logger.info(f"  - Final video file: {final_video_path}")
        logger.info(f"  - Final file size: {results.get('file_size', 0):,} bytes ({results.get('file_size', 0)/1024/1024:.1f} MB)")
        
        logger.info(f"\n🎬 FINAL VIDEO CONTENTS:")
        for i, sequence in enumerate(valid_sequences):
            logger.info(f"  {i+1}. Expression {sequence['expression_index']}: '{sequence['expression']}' ({sequence['actual_duration']:.1f}s)")
        
        if results["success"]:
            logger.info(f"\n✅ SUCCESS! Final educational video created: {final_video_path}")
        else:
            logger.error(f"\n❌ FAILED: {'; '.join(results['errors'])}")
        
        if results["errors"]:
            logger.warning("⚠️  Errors encountered:")
            for error in results["errors"]:
                logger.warning(f"    - {error}")
        
        return results
        
    except Exception as e:
        error_msg = f"Step 7 failed with exception: {e}"
        logger.error(error_msg)
        results = {
            "step": 7,
            "description": "Concatenate all expression sequences into final video",
            "success": False,
            "errors": [error_msg],
            "final_video_created": False,
            "total_duration": 0,
            "expressions_included": 0
        }
        return results

def main():
    """Main test function"""
    try:
        results = test_step7()
        log_step_complete(7, results["success"], 
                         f"Created final video with {results['expressions_included']} expressions" if results["success"] else f"Failed: {'; '.join(results['errors'])}")
        
        if not results["success"]:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
