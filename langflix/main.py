"""
LangFlix - Main execution script
End-to-end pipeline for learning English expressions from TV shows
"""
import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

# Import our modules
from .subtitle_parser import parse_srt_file, chunk_subtitles
from .expression_analyzer import analyze_chunk
from .video_processor import VideoProcessor
from .subtitle_processor import SubtitleProcessor
from .models import ExpressionAnalysis
from . import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('langflix.log')
    ]
)
logger = logging.getLogger(__name__)


class LangFlixPipeline:
    """
    Main pipeline class for processing TV show content into learning materials
    """
    
    def __init__(self, subtitle_file: str, video_dir: str = "assets/media", 
                 output_dir: str = "output"):
        """
        Initialize the LangFlix pipeline
        
        Args:
            subtitle_file: Path to subtitle file
            video_dir: Directory containing video files
            output_dir: Directory for output files
        """
        self.subtitle_file = Path(subtitle_file)
        self.video_dir = Path(video_dir)
        self.output_dir = Path(output_dir)
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize processors
        self.video_processor = VideoProcessor(str(self.video_dir))
        self.subtitle_processor = SubtitleProcessor(str(self.subtitle_file))
        
        # Pipeline state
        self.subtitles = []
        self.chunks = []
        self.expressions = []
        self.processed_expressions = 0
        
    def run(self, max_expressions: int = None, dry_run: bool = False, language_level: str = None, save_llm_output: bool = False) -> Dict[str, Any]:
        """
        Run the complete pipeline
        
        Args:
            max_expressions: Maximum number of expressions to process
            dry_run: If True, only analyze without creating video files
            language_level: Target language level (beginner, intermediate, advanced, mixed)
            save_llm_output: If True, save LLM responses to files for review
            
        Returns:
            Dictionary with processing results
        """
        try:
            logger.info("🎬 Starting LangFlix Pipeline")
            logger.info(f"Subtitle file: {self.subtitle_file}")
            logger.info(f"Video directory: {self.video_dir}")
            logger.info(f"Output directory: {self.output_dir}")
            
            # Step 1: Parse subtitles
            logger.info("Step 1: Parsing subtitles...")
            self.subtitles = self._parse_subtitles()
            if not self.subtitles:
                raise ValueError("No subtitles found")
            
            # Step 2: Chunk subtitles
            logger.info("Step 2: Chunking subtitles...")
            self.chunks = chunk_subtitles(self.subtitles)
            logger.info(f"Created {len(self.chunks)} chunks")
            
            # Step 3: Analyze expressions
            logger.info("Step 3: Analyzing expressions...")
            self.expressions = self._analyze_expressions(max_expressions, language_level, save_llm_output)
            if not self.expressions:
                raise ValueError("No expressions found")
            
            # Step 4: Process expressions (if not dry run)
            if not dry_run:
                logger.info("Step 4: Processing expressions...")
                self._process_expressions()
            else:
                logger.info("Step 4: Dry run - skipping video processing")
            
            # Step 5: Generate summary
            summary = self._generate_summary()
            logger.info("✅ Pipeline completed successfully!")
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            raise
    
    def _parse_subtitles(self) -> List[Dict[str, Any]]:
        """Parse subtitle file"""
        try:
            subtitles = parse_srt_file(str(self.subtitle_file))
            logger.info(f"Parsed {len(subtitles)} subtitle entries")
            return subtitles
        except Exception as e:
            logger.error(f"Error parsing subtitles: {e}")
            raise
    
    def _analyze_expressions(self, max_expressions: int = None, language_level: str = None, save_llm_output: bool = False) -> List[ExpressionAnalysis]:
        """Analyze expressions from subtitle chunks"""
        all_expressions = []
        
        for i, chunk in enumerate(self.chunks):
            if max_expressions is not None and len(all_expressions) >= max_expressions:
                break
                
            logger.info(f"Analyzing chunk {i+1}/{len(self.chunks)}...")
            
            try:
                expressions = analyze_chunk(chunk, language_level, save_llm_output, str(self.output_dir))
                if expressions:
                    all_expressions.extend(expressions)
                    logger.info(f"Found {len(expressions)} expressions in chunk {i+1}")
                else:
                    logger.warning(f"No expressions found in chunk {i+1}")
                    
            except Exception as e:
                logger.error(f"Error analyzing chunk {i+1}: {e}")
                continue
        
        # Limit to max_expressions
        limited_expressions = all_expressions[:max_expressions]
        logger.info(f"Total expressions found: {len(limited_expressions)}")
        
        return limited_expressions
    
    def _process_expressions(self):
        """Process each expression (video + subtitles)"""
        for i, expression in enumerate(self.expressions):
            try:
                logger.info(f"Processing expression {i+1}/{len(self.expressions)}: {expression.expression}")
                
                # Find video file
                video_file = self.video_processor.find_video_file(str(self.subtitle_file))
                if not video_file:
                    logger.warning(f"No video file found for expression {i+1}")
                    continue
                
                # Create output filenames
                safe_expression = "".join(c for c in expression.expression if c.isalnum() or c in (' ', '-', '_')).rstrip()
                video_output = self.output_dir / f"expression_{i+1:02d}_{safe_expression[:30]}.mkv"
                subtitle_output = self.output_dir / f"expression_{i+1:02d}_{safe_expression[:30]}.srt"
                
                # Extract video clip
                success = self.video_processor.extract_clip(
                    video_file,
                    expression.context_start_time,
                    expression.context_end_time,
                    video_output
                )
                
                if success:
                    logger.info(f"✅ Video clip created: {video_output}")
                    
                    # Create subtitle file
                    subtitle_success = self.subtitle_processor.create_dual_language_subtitle_file(
                        expression,
                        str(subtitle_output)
                    )
                    
                    if subtitle_success:
                        logger.info(f"✅ Subtitle file created: {subtitle_output}")
                        self.processed_expressions += 1
                    else:
                        logger.warning(f"❌ Failed to create subtitle file: {subtitle_output}")
                else:
                    logger.warning(f"❌ Failed to create video clip: {video_output}")
                    
            except Exception as e:
                logger.error(f"Error processing expression {i+1}: {e}")
                continue
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate processing summary"""
        return {
            "total_subtitles": len(self.subtitles),
            "total_chunks": len(self.chunks),
            "total_expressions": len(self.expressions),
            "processed_expressions": self.processed_expressions,
            "output_directory": str(self.output_dir),
            "timestamp": datetime.now().isoformat()
        }


def main():
    """Main entry point for LangFlix"""
    parser = argparse.ArgumentParser(
        description="LangFlix - Learn English expressions from TV shows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m langflix.main --subtitle assets/subtitles/Suits\ -\ season\ 1.en/Suits\ -\ 1x01\ -\ Pilot.720p.WEB-DL.en.srt
  python -m langflix.main --subtitle subtitle.srt --video-dir assets/media --output-dir results
  python -m langflix.main --subtitle subtitle.srt --max-expressions 5 --dry-run
        """
    )
    
    parser.add_argument(
        "--subtitle", 
        required=True,
        help="Path to subtitle file (.srt)"
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
        "--max-expressions",
        type=int,
        default=None,
        help="Maximum number of expressions to process (default: no limit - process all found expressions)"
    )
    
    parser.add_argument(
        "--language-level",
        type=str,
        default=settings.DEFAULT_LANGUAGE_LEVEL,
        choices=['beginner', 'intermediate', 'advanced', 'mixed'],
        help=f"Target language level for expression analysis (default: {settings.DEFAULT_LANGUAGE_LEVEL})"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze expressions without creating video files"
    )
    
    parser.add_argument(
        "--save-llm-output",
        action="store_true",
        help="Save LLM responses to files for review"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize pipeline
        pipeline = LangFlixPipeline(
            subtitle_file=args.subtitle,
            video_dir=args.video_dir,
            output_dir=args.output_dir
        )
        
        # Run pipeline
        summary = pipeline.run(
            max_expressions=args.max_expressions,
            dry_run=args.dry_run,
            language_level=args.language_level,
            save_llm_output=args.save_llm_output
        )
        
        # Print summary
        print("\n" + "="*50)
        print("🎬 LangFlix Pipeline Summary")
        print("="*50)
        print(f"📝 Total subtitles: {summary['total_subtitles']}")
        print(f"📦 Total chunks: {summary['total_chunks']}")
        print(f"💡 Total expressions: {summary['total_expressions']}")
        print(f"✅ Processed expressions: {summary['processed_expressions']}")
        print(f"📁 Output directory: {summary['output_directory']}")
        print(f"⏰ Completed at: {summary['timestamp']}")
        print("="*50)
        
        if not args.dry_run:
            print(f"\n🎉 Check your results in: {summary['output_directory']}")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()