#!/usr/bin/env python3
"""
End-to-End Test Runner for LangFlix
Tests the complete pipeline from subtitle parsing to final video generation
"""
import os
import sys
import logging
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path (go up to project root from tests/functional/)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from langflix.main import LangFlixPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(project_root / 'test_run.log'))
    ]
)
logger = logging.getLogger(__name__)

def clean_test_output():
    """Clean previous test outputs"""
    test_output_dir = project_root / "test_output"
    if test_output_dir.exists():
        logger.info("🧹 Cleaning previous test output...")
        shutil.rmtree(test_output_dir)
    test_output_dir.mkdir(exist_ok=True)
    
    # Also clean log files
    for log_file in ["langflix.log", "test_run.log"]:
        log_path = project_root / log_file
        if log_path.exists():
            log_path.unlink()

def run_end_to_end_test():
    """Run complete end-to-end test"""
    try:
        logger.info("🚀 Starting End-to-End LangFlix Test")
        logger.info("=" * 60)
        
        # Clean previous outputs
        clean_test_output()
        
        # Test parameters
        subtitle_file = str(project_root / "assets/media/Suits/Suits.S01E01.720p.HDTV.x264/Subs/English.srt")
        video_dir = str(project_root / "assets/media/Suits/Suits.S01E01.720p.HDTV.x264")
        language_code = "ko"
        max_expressions = 5
        test_mode = True
        
        # Verify input files exist
        if not Path(subtitle_file).exists():
            raise FileNotFoundError(f"Subtitle file not found: {subtitle_file}")
            
        video_file = project_root / "assets/media/Suits/Suits.S01E01.720p.HDTV.x264/Suits.S01E01.720p.HDTV.x264.mkv"
        if not video_file.exists():
            raise FileNotFoundError(f"Video file not found: {video_file}")
        
        logger.info(f"📁 Input files verified:")
        logger.info(f"  - Subtitle: {subtitle_file}")
        logger.info(f"  - Video: {video_file}")
        logger.info(f"  - Target language: {language_code}")
        logger.info(f"  - Max expressions: {max_expressions}")
        logger.info(f"  - Test mode: {test_mode}")
        logger.info("=" * 60)
        
        # Initialize pipeline (Legacy Mode by providing subtitle_file)
        pipeline = LangFlixPipeline(
            subtitle_file=subtitle_file,
            video_dir=video_dir,
            output_dir="test_output",
            language_code=language_code,
            source_language="en"
        )
        
        logger.info("🔄 Running pipeline...")
        
        # Run the complete pipeline
        result = pipeline.run(
            max_expressions=max_expressions,
            test_mode=test_mode,
            save_llm_output=True
        )
        
        logger.info("=" * 60)
        logger.info("✅ Pipeline Execution Completed")
        logger.info("=" * 60)
        
        # Analyze results
        if isinstance(result, dict):
             expressions_found = len(result.get('expressions', []))
        else:
             expressions_found = 0
             
        logger.info(f"📊 Results Summary:")
        logger.info(f"  - Expressions found: {expressions_found}")
        
        # Check output files
        output_dir = project_root / "test_output"
        if output_dir.exists():
            logger.info(f"\n📁 Generated files in test_output/:")
            
            def list_files_recursive(path, prefix="  "):
                for item in sorted(path.iterdir()):
                    if item.is_file():
                        size = item.stat().st_size
                        logger.info(f"{prefix}📄 {item.relative_to(output_dir)} ({size:,} bytes)")
                    elif item.is_dir():
                        logger.info(f"{prefix}📁 {item.relative_to(output_dir)}/")
                        list_files_recursive(item, prefix + "  ")
            
            list_files_recursive(output_dir)
            
        logger.info("\n" + "=" * 60)
        logger.info("🎉 End-to-End Test Completed Successfully!")
        logger.info("=" * 60)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def verify_test_results():
    """Verify that test results meet expectations"""
    logger.info("\n🔍 Verifying Test Results...")
    
    output_dir = project_root / "test_output"
    if not output_dir.exists():
        logger.error("❌ Test output directory not found!")
        return False
    
    checks_passed = 0
    total_checks = 0
    
    # Dynamic search for generated files matching pattern
    
    # Check 1: Video clips exist
    total_checks += 1
    video_clips = list(output_dir.rglob("context_clip_*.mkv"))
    if video_clips:
        logger.info(f"✅ Found {len(video_clips)} video clips")
        checks_passed += 1
    else:
        logger.error("❌ No video clips found")
    
    # Check 2: Subtitle files exist
    total_checks += 1
    subtitles = list(output_dir.rglob("expression_*.srt"))
    if subtitles:
        logger.info(f"✅ Found {len(subtitles)} subtitle files")
        checks_passed += 1
    else:
        logger.error("❌ No subtitle files found")
    
    # Check 3: Final videos (educational/shorts)
    total_checks += 1
    final_videos = list(output_dir.rglob("short_form_*.mkv"))
    if final_videos:
        logger.info(f"✅ Found {len(final_videos)} short videos")
        checks_passed += 1
    else:
        logger.error("❌ No short videos found")
    
    success_rate = (checks_passed / total_checks) * 100
    logger.info(f"\n📊 Verification Results: {checks_passed}/{total_checks} checks passed ({success_rate:.1f}%)")
    
    return success_rate >= 80

if __name__ == "__main__":
    result = run_end_to_end_test()
    
    if result:
        success = verify_test_results()
        if success:
            logger.info("\n🎉 All tests passed! The system is working correctly.")
        else:
            logger.warning("\n⚠️  Some tests failed. Check the log for details.")
    else:
        logger.error("\n💥 Test execution failed completely.")
