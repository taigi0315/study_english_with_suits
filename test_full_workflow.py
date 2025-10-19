#!/usr/bin/env python3
"""
Test full workflow end-to-end with Korean language (default)
This script runs the complete LangFlix pipeline on Suits S01E01
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from langflix.main import LangFlixPipeline
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

def test_full_workflow_korean():
    """Test complete workflow with Korean language (default)"""
    logger.info("=" * 60)
    logger.info("FULL WORKFLOW TEST - KOREAN (DEFAULT)")
    logger.info("=" * 60)
    
    # File paths
    subtitle_file = "assets/media/Suits/Suits.S01E01.720p.HDTV.x264.srt"
    video_dir = "assets/media"
    output_dir = "output"
    
    logger.info(f"Subtitle: {subtitle_file}")
    logger.info(f"Video dir: {video_dir}")
    logger.info(f"Output dir: {output_dir}")
    logger.info(f"Language: Korean (ko)")
    
    # Initialize pipeline
    pipeline = LangFlixPipeline(
        subtitle_file=subtitle_file,
        video_dir=video_dir,
        output_dir=output_dir,
        language_code="ko"
    )
    
    # Run pipeline
    logger.info("\nStarting pipeline...")
    results = pipeline.run(
        max_expressions=None,  # Process all expressions
        test_mode=False,  # Process all chunks (not just first)
        save_llm_output=True,
        language_level="intermediate"
    )
    
    # Print results
    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE RESULTS")
    logger.info("=" * 60)
    logger.info(f"Total subtitles: {results['total_subtitles']}")
    logger.info(f"Total chunks: {results['total_chunks']}")
    logger.info(f"Total expressions: {results['total_expressions']}")
    logger.info(f"Processed expressions: {results['processed_expressions']}")
    logger.info(f"Output directory: {results['output_directory']}")
    logger.info(f"Series: {results['series_name']}")
    logger.info(f"Episode: {results['episode_name']}")
    logger.info(f"Language: {results['language_code']}")
    logger.info("=" * 60)
    
    # Verify outputs
    output_path = Path(results['output_directory'])
    final_videos_dir = output_path / "translations" / "ko" / "final_videos"
    final_video = final_videos_dir / "final_educational_video_with_slides.mkv"
    
    logger.info("\nVERIFICATION:")
    logger.info(f"Output directory exists: {output_path.exists()}")
    logger.info(f"Final videos directory: {final_videos_dir}")
    logger.info(f"Final video exists: {final_video.exists()}")
    
    if final_video.exists():
        file_size = final_video.stat().st_size / (1024 * 1024)  # MB
        logger.info(f"Final video size: {file_size:.2f} MB")
        logger.info(f"✅ SUCCESS! Final video created: {final_video}")
    else:
        logger.error(f"❌ FAILED! Final video not found at: {final_video}")
        return False
    
    return True

if __name__ == "__main__":
    try:
        success = test_full_workflow_korean()
        if success:
            print("\n✅ Full workflow test PASSED!")
            sys.exit(0)
        else:
            print("\n❌ Full workflow test FAILED!")
            sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Full workflow test FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

