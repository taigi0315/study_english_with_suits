#!/usr/bin/env python3
"""
Pipeline profiling script for LangFlix.

TICKET-037: Runs the video processing pipeline with profiling enabled
and saves performance reports for baseline measurement and optimization tracking.

Usage:
    python tools/profile_video_pipeline.py \
        --subtitle "path/to/subtitle.srt" \
        --video-dir "assets/media" \
        --output-dir "output" \
        [--profile-output "profiles/baseline.json"]
"""

import argparse
import sys
import logging
from pathlib import Path

# Add parent directory to path to import langflix modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from langflix.main import LangFlixPipeline, setup_logging
from langflix.profiling import PipelineProfiler

logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run LangFlix pipeline with profiling enabled",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic profiling run
  python tools/profile_video_pipeline.py \\
      --subtitle "assets/subtitles/episode.srt" \\
      --video-dir "assets/media"
  
  # Save to specific location
  python tools/profile_video_pipeline.py \\
      --subtitle "assets/subtitles/episode.srt" \\
      --video-dir "assets/media" \\
      --profile-output "profiles/baseline_20250127.json"
  
  # Test mode (faster, first chunk only)
  python tools/profile_video_pipeline.py \\
      --subtitle "assets/subtitles/episode.srt" \\
      --video-dir "assets/media" \\
      --test-mode
        """
    )
    
    parser.add_argument(
        "--subtitle",
        required=True,
        help="Path to subtitle file (.srt, .vtt, .smi, etc.)"
    )
    
    parser.add_argument(
        "--video-dir",
        default="assets/media",
        help="Directory containing video files (default: assets/media)"
    )
    
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Output directory for generated files (default: output)"
    )
    
    parser.add_argument(
        "--profile-output",
        type=str,
        default=None,
        help="Path to save profiling report (default: profiles/profile_<timestamp>.json)"
    )
    
    parser.add_argument(
        "--max-expressions",
        type=int,
        default=None,
        help="Maximum number of expressions to process (default: no limit)"
    )
    
    parser.add_argument(
        "--language-level",
        type=str,
        default="intermediate",
        choices=['beginner', 'intermediate', 'advanced', 'mixed'],
        help="Target language level (default: intermediate)"
    )
    
    parser.add_argument(
        "--language-code",
        type=str,
        default="ko",
        choices=['ko', 'ja', 'zh', 'es', 'fr'],
        help="Target language code (default: ko)"
    )
    
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Process only the first chunk for faster testing"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze expressions without creating video files"
    )
    
    parser.add_argument(
        "--no-shorts",
        action="store_true",
        help="Skip creating short-format videos"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser.parse_args()


def main():
    """Main entry point for profiling script."""
    args = parse_args()
    
    # Setup logging
    setup_logging(verbose=args.verbose)
    
    logger.info("="*60)
    logger.info("📊 LangFlix Pipeline Profiling")
    logger.info("="*60)
    logger.info(f"Subtitle: {args.subtitle}")
    logger.info(f"Video directory: {args.video_dir}")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Profile output: {args.profile_output or 'profiles/profile_<timestamp>.json'}")
    logger.info("="*60)
    
    try:
        # Initialize profiler
        output_path = Path(args.profile_output) if args.profile_output else None
        profiler = PipelineProfiler(output_path=output_path)
        
        # Initialize pipeline with profiler
        pipeline = LangFlixPipeline(
            subtitle_file=args.subtitle,
            video_dir=args.video_dir,
            output_dir=args.output_dir,
            language_code=args.language_code,
            profiler=profiler
        )
        
        # Run pipeline
        logger.info("Starting pipeline execution with profiling...")
        summary = pipeline.run(
            max_expressions=args.max_expressions,
            dry_run=args.dry_run,
            language_level=args.language_level,
            save_llm_output=False,
            test_mode=args.test_mode,
            no_shorts=args.no_shorts
        )
        
        # Print summary
        print("\n" + "="*60)
        print("📊 Profiling Summary")
        print("="*60)
        print(f"📝 Total subtitles: {summary['total_subtitles']}")
        print(f"📦 Total chunks: {summary['total_chunks']}")
        print(f"💡 Total expressions: {summary['total_expressions']}")
        print(f"✅ Processed expressions: {summary['processed_expressions']}")
        
        if 'profiling_report' in summary:
            print(f"\n📊 Profiling report saved to: {summary['profiling_report']}")
            print("\nTo view the report:")
            print(f"  cat {summary['profiling_report']}")
            print(f"  # or")
            print(f"  python -m json.tool {summary['profiling_report']}")
        
        print("="*60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Profiling failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

