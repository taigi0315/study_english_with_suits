#!/usr/bin/env python3
"""
V2 Dual-Language Video Generation Test Script

Tests the V2 dual-language pipeline with Korean (source) and Spanish (target).
This script runs the pipeline directly without needing the API server.

Usage:
    python scripts/test_v2_generation.py [--test-mode]
"""
import sys
import os
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Test V2 dual-language video generation')
    parser.add_argument('--test-mode', action='store_true', default=True,
                        help='Run in test mode (1 expression only)')
    parser.add_argument('--full', action='store_true', 
                        help='Run full processing (all expressions)')
    parser.add_argument('--output-dir', type=str, default='output',
                        help='Output directory for generated videos')
    args = parser.parse_args()
    
    test_mode = not args.full
    
    logger.info("=" * 60)
    logger.info("V2 Dual-Language Video Generation Test")
    logger.info("=" * 60)
    logger.info(f"Test Mode: {test_mode}")
    logger.info(f"Output Dir: {args.output_dir}")
    
    # Test media paths
    video_path = "assets/media/test_media/The.Glory.S01E01.KOREAN.1080p.WEBRip.x265-RARBG[eztv.re].mp4"
    subtitle_path = "assets/media/test_media/The.Glory.S01E01.KOREAN.1080p.WEBRip.x265-RARBG[eztv.re]/Korean.srt"
    
    # Check files exist
    if not Path(video_path).exists():
        logger.error(f"Video file not found: {video_path}")
        return 1
    if not Path(subtitle_path).exists():
        logger.error(f"Subtitle file not found: {subtitle_path}")
        return 1
    
    logger.info(f"Video: {video_path}")
    logger.info(f"Subtitle: {subtitle_path}")
    logger.info("")
    
    # Import pipeline after path setup
    try:
        from langflix.main import LangFlixPipeline
        from langflix import settings
        
        # Verify V2 mode is enabled
        logger.info("Checking configuration...")
        logger.info(f"  - Dual language enabled: {settings.is_dual_language_enabled()}")
        logger.info(f"  - Source language: {settings.get_default_source_language()}")
        logger.info(f"  - Target language: {settings.get_default_target_language()}")
        logger.info("")
        
        if not settings.is_dual_language_enabled():
            logger.warning("V2 dual language mode is DISABLED in config!")
            logger.warning("Enable it in langflix/config/default.yaml: dual_language.enabled = true")
            return 1
            
    except Exception as e:
        logger.error(f"Failed to import pipeline: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    start_time = datetime.now()
    logger.info(f"Starting pipeline at {start_time.strftime('%H:%M:%S')}...")
    logger.info("")
    
    try:
        # Initialize pipeline
        pipeline = LangFlixPipeline(
            video_file=video_path,
            subtitle_file=subtitle_path,
            output_dir=str(output_dir),
            series_name="V2Test",
            episode_name="The.Glory.S01E01",
            target_languages=["es"],  # Spanish target
        )
        
        # Run pipeline with test_mode
        expressions = pipeline.run(test_mode=test_mode)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("RESULTS")
        logger.info("=" * 60)
        logger.info(f"Duration: {duration:.1f} seconds")
        logger.info(f"Expressions found: {len(expressions) if expressions else 0}")
        
        # Check for output files
        output_files = list(output_dir.rglob("*.mkv"))
        logger.info(f"Output files: {len(output_files)}")
        
        for f in output_files[:10]:  # Show up to 10 files
            logger.info(f"  - {f.relative_to(output_dir)}")
            
        if output_files:
            logger.info("")
            logger.info("✅ V2 Video Generation SUCCESSFUL!")
            return 0
        else:
            logger.error("")
            logger.error("❌ No output files generated!")
            return 1
            
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
