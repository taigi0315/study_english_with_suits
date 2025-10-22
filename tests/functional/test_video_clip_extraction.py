"""
Functional test for video clip extraction
Tests the complete video processing pipeline with real files
"""
import os
import sys
import tempfile
from pathlib import Path
import logging

# Add the project root to the path so we can import langflix
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from langflix.core.video_processor import VideoProcessor
from langflix.core.subtitle_parser import parse_srt_file, chunk_subtitles
from langflix.core.expression_analyzer import analyze_chunk

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_video_clip_extraction():
    """
    Test video clip extraction with real Suits episode
    """
    # Test parameters
    subtitle_file = "assets/subtitles/Suits - season 1.en/Suits - 1x01 - Pilot.720p.WEB-DL.en.srt"
    video_file = "assets/media/Suits - 1x01 - Pilot.720p.WEB-DL.en.mkv"
    output_dir = "tests/test_output"
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        # Step 1: Parse subtitles
        logger.info("Step 1: Parsing subtitles...")
        subtitles = parse_srt_file(subtitle_file)
        logger.info(f"Parsed {len(subtitles)} subtitle entries")
        
        # Step 2: Chunk subtitles
        logger.info("Step 2: Chunking subtitles...")
        chunks = chunk_subtitles(subtitles)
        logger.info(f"Created {len(chunks)} chunks")
        
        # Step 3: Analyze first chunk with expressions
        logger.info("Step 3: Analyzing first chunk for expressions...")
        if not chunks:
            logger.error("No subtitle chunks found")
            return False
            
        # Analyze the first chunk
        expressions = analyze_chunk(chunks[0])
        logger.info(f"Found {len(expressions)} expressions in first chunk")
        
        if not expressions:
            logger.warning("No expressions found, using dummy data for testing")
            # Create dummy expression for testing
            from langflix.models import ExpressionAnalysis
            dummy_expression = ExpressionAnalysis(
                dialogues=["I'm paying you millions,", "and you're telling me I'm gonna get screwed?"],
                translation=["나는 당신에게 수백만 달러를 지불하고 있는데,", "당신은 내가 속임을 당할 것이라고 말하고 있나요?"],
                expression="I'm gonna get screwed",
                expression_translation="속임을 당할 것 같아요",
                context_start_time="00:01:25,657",
                context_end_time="00:01:32,230",
                similar_expressions=["I'm going to be cheated", "I'm getting the short end of the stick"]
            )
            expressions = [dummy_expression]
        
        # Step 4: Initialize video processor
        logger.info("Step 4: Initializing video processor...")
        processor = VideoProcessor("assets/media")
        
        # Step 5: Validate video file
        logger.info("Step 5: Validating video file...")
        video_path = Path(video_file)
        if not video_path.exists():
            logger.error(f"Video file not found: {video_file}")
            return False
            
        validation_result = processor.validate_video_file(video_path)
        if not validation_result['valid']:
            logger.error(f"Video validation failed: {validation_result['error']}")
            return False
            
        logger.info(f"Video metadata: {validation_result['metadata']}")
        
        # Step 6: Extract clips for each expression
        logger.info("Step 6: Extracting video clips...")
        successful_extractions = 0
        
        for i, expression in enumerate(expressions):
            logger.info(f"Processing expression {i+1}/{len(expressions)}: {expression.expression}")
            
            # Create output filename
            safe_expression = "".join(c for c in expression.expression if c.isalnum() or c in (' ', '-', '_')).rstrip()
            output_filename = f"clip_{i+1:02d}_{safe_expression[:30]}.mkv"
            output_path = Path(output_dir) / output_filename
            
            # Extract clip
            success = processor.extract_clip(
                video_path,
                expression.context_start_time,
                expression.context_end_time,
                output_path
            )
            
            if success:
                logger.info(f"✅ Successfully extracted clip: {output_path}")
                successful_extractions += 1
            else:
                logger.error(f"❌ Failed to extract clip for expression: {expression.expression}")
        
        # Step 7: Summary
        logger.info(f"Video clip extraction completed!")
        logger.info(f"Successfully extracted {successful_extractions}/{len(expressions)} clips")
        logger.info(f"Output directory: {output_dir}")
        
        # List output files
        output_files = list(Path(output_dir).glob("*.mkv"))
        logger.info(f"Generated files: {[f.name for f in output_files]}")
        
        return successful_extractions > 0
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🎬 Testing Video Clip Extraction")
    print("=" * 50)
    
    success = test_video_clip_extraction()
    
    if success:
        print("\n✅ Video clip extraction test PASSED!")
        print("Check the 'tests/test_output' directory for generated clips.")
    else:
        print("\n❌ Video clip extraction test FAILED!")
        print("Check the logs above for error details.")
