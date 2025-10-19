#!/usr/bin/env python3
"""
Run all step-by-step tests sequentially
"""
import sys
import logging
from pathlib import Path

# Import test utilities
from test_config import setup_test_environment, clean_all_test_outputs
from test_utils import log_step_start, log_step_complete

# Import all test step modules
from test_step1_load_and_analyze import test_step1
from test_step2_slice_video import test_step2
from test_step3_add_subtitles import test_step3
from test_step4_extract_audio import test_step4
from test_step5_create_slide import test_step5
from test_step6_append_to_context import test_step6
from test_step7_final_concat import test_step7

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def run_all_steps():
    """Run all test steps sequentially"""
    print("=" * 80)
    print("🚀 LANGFLIX STEP-BY-STEP TESTING SUITE")
    print("=" * 80)
    
    # Setup environment first
    try:
        setup_test_environment()
        print("✅ Test environment setup complete")
    except Exception as e:
        logger.error(f"Failed to setup test environment: {e}")
        return False
    
    # Initialize results tracking
    all_results = {}
    failed_steps = []
    
    # Define test steps in order
    test_steps = [
        (1, "Load and analyze subtitles", test_step1),
        (2, "Slice video based on expression context", test_step2),
        (3, "Add target language subtitles to context video", test_step3),
        (4, "Extract audio of specific expression phrases", test_step4),
        (5, "Create educational slides with background and text", test_step5),
        (6, "Append education slide to context video with smooth transition", test_step6),
        (7, "Concatenate all expression sequences into final video", test_step7)
    ]
    
    # Run each step
    for step_num, description, test_func in test_steps:
        try:
            logger.info(f"Starting Step {step_num}: {description}")
            results = test_func()
            all_results[step_num] = results
            
            if results["success"]:
                logger.info(f"✅ Step {step_num} completed successfully")
            else:
                logger.error(f"❌ Step {step_num} failed")
                failed_steps.append(step_num)
                # Continue with remaining steps even if one fails
                
        except Exception as e:
            logger.error(f"❌ Step {step_num} crashed: {e}")
            all_results[step_num] = {
                "step": step_num,
                "success": False,
                "errors": [f"Test crashed: {e}"]
            }
            failed_steps.append(step_num)
    
    # Print final summary
    print("\n" + "=" * 80)
    print("📊 FINAL TEST SUMMARY")
    print("=" * 80)
    
    successful_steps = len(test_steps) - len(failed_steps)
    total_steps = len(test_steps)
    
    print(f"Total steps: {total_steps}")
    print(f"Successful: {successful_steps}")
    print(f"Failed: {len(failed_steps)}")
    
    if failed_steps:
        print(f"Failed steps: {', '.join(map(str, failed_steps))}")
    
    # Print summary for each step
    print(f"\n📋 DETAILED RESULTS:")
    for step_num, description, _ in test_steps:
        results = all_results.get(step_num, {})
        status = "✅ PASSED" if results.get("success", False) else "❌ FAILED"
        print(f"  Step {step_num}: {status} - {description}")
        
        if results.get("errors"):
            for error in results["errors"][:3]:  # Show first 3 errors
                print(f"    Error: {error}")
            if len(results["errors"]) > 3:
                print(f"    ... and {len(results['errors']) - 3} more errors")
    
    # Final video summary
    if 7 in all_results and all_results[7].get("success"):
        step7_results = all_results[7]
        print(f"\n🎬 FINAL VIDEO CREATED:")
        print(f"  Duration: {step7_results.get('actual_duration', 0):.1f} seconds")
        print(f"  Size: {step7_results.get('file_size', 0):,} bytes ({step7_results.get('file_size', 0)/1024/1024:.1f} MB)")
        print(f"  Expressions included: {step7_results.get('expressions_included', 0)}")
        print(f"  Location: test_output/step7/final_educational_video_with_slides.mkv")
    else:
        print(f"\n❌ Final video was not created successfully")
    
    print("\n" + "=" * 80)
    
    if failed_steps:
        print(f"❌ TESTING FAILED - {len(failed_steps)} step(s) failed")
        return False
    else:
        print("✅ ALL TESTS PASSED!")
        return True

def main():
    """Main execution function"""
    try:
        success = run_all_steps()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Testing suite crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
