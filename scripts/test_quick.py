#!/usr/bin/env python3
"""
Quick Test Script for LangFlix Pipeline

Runs the pipeline in test mode using local test media.
No UI needed, no YouTube upload.

Usage:
    python scripts/test_quick.py
    
    # Or with custom settings:
    python scripts/test_quick.py --source ko --target es,en
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def find_test_media(test_media_dir: Path) -> tuple:
    """Find first available test media (video + subtitle)."""
    for episode_dir in test_media_dir.iterdir():
        if episode_dir.is_dir() and not episode_dir.name.startswith('.'):
            # Look for video
            video_file = None
            for ext in ['.mp4', '.mkv', '.avi']:
                videos = list(episode_dir.glob(f'*{ext}'))
                if videos:
                    video_file = videos[0]
                    break
            
            # Look for subtitle in Subs folder
            subs_folder = episode_dir / 'Subs'
            subtitle_file = None
            if subs_folder.exists():
                srt_files = list(subs_folder.glob('*.srt'))
                if srt_files:
                    subtitle_file = srt_files[0]
            
            if video_file and subtitle_file:
                return video_file, subtitle_file, subs_folder
    
    return None, None, None


def main():
    parser = argparse.ArgumentParser(description='Quick test of LangFlix pipeline')
    parser.add_argument('--source', '-s', default='ko', help='Source language code (default: ko)')
    parser.add_argument('--target', '-t', default='es,en', help='Target language codes, comma-separated (default: es,en)')
    parser.add_argument('--output', '-o', default='output/test_quick', help='Output directory')
    parser.add_argument('--media-dir', '-m', default='assets/media/test_media', help='Test media directory')
    parser.add_argument('--dry-run', action='store_true', help='Dry run - analyze only, no video creation')
    parser.add_argument('--no-shorts', action='store_true', help='Skip short video creation')
    parser.add_argument('--duration', '-d', type=float, default=120.0, help='Target duration in seconds (default: 120.0)')
    args = parser.parse_args()
    
    # Find test media
    test_media_dir = project_root / args.media_dir
    if not test_media_dir.exists():
        logger.error(f"Test media directory not found: {test_media_dir}")
        sys.exit(1)
    
    video_file, subtitle_file, subs_folder = find_test_media(test_media_dir)
    
    if not video_file:
        logger.error(f"No test video found in {test_media_dir}")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("🎬 LangFlix Quick Test")
    logger.info("=" * 60)
    logger.info(f"Video: {video_file.name}")
    logger.info(f"Subtitle: {subtitle_file.name if subtitle_file else 'None'}")
    logger.info(f"Source: {args.source}")
    logger.info(f"Target: {args.target}")
    logger.info(f"Output: {args.output}")
    logger.info(f"Duration: {args.duration}s")
    logger.info("=" * 60)
    
    # Parse target languages
    target_languages = [lang.strip() for lang in args.target.split(',')]
    
    # Create output directory
    output_dir = project_root / args.output
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        from langflix.main import LangFlixPipeline
        
        # Initialize pipeline
        pipeline = LangFlixPipeline(
            subtitle_file=str(subtitle_file) if subtitle_file else None,
            video_dir=str(video_file.parent),
            video_file=str(video_file),
            output_dir=str(output_dir),
            language_code=args.source,
            target_languages=target_languages,
        )
        
        # Run in test mode (limit to 1 expression)
        logger.info("🚀 Starting pipeline in TEST MODE (1 expression)...")
        result = pipeline.run(
            test_mode=True,
            dry_run=args.dry_run,
            no_shorts=args.no_shorts,
            schedule_upload=False,  # Never upload in test
            target_duration=args.duration,
        )
        
        logger.info("=" * 60)
        logger.info("✅ Pipeline completed!")
        logger.info(f"Result: {result}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
