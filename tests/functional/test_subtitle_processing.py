"""
Functional test for subtitle processing
Tests the complete subtitle processing pipeline with real files
"""
import os
import sys
import tempfile
from pathlib import Path
import logging

# Add the project root to the path so we can import langflix
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from langflix.subtitle_processor import SubtitleProcessor, create_subtitle_file_for_expression
from langflix.models import ExpressionAnalysis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_subtitle_processing():
    """
    Test subtitle processing with real Suits episode
    """
    # Test parameters
    subtitle_file = "assets/subtitles/Suits - season 1.en/Suits - 1x01 - Pilot.720p.WEB-DL.en.srt"
    output_dir = "tests/test_output"
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        # Step 1: Initialize subtitle processor
        logger.info("Step 1: Initializing subtitle processor...")
        processor = SubtitleProcessor(subtitle_file)
        
        if not processor.subtitles:
            logger.error("Failed to load subtitles")
            return False
        
        # Step 2: Create test expression
        logger.info("Step 2: Creating test expression...")
        test_expression = ExpressionAnalysis(
            dialogues=["I'm paying you millions,", "and you're telling me I'm gonna get screwed?"],
            translation=["나는 당신에게 수백만 달러를 지불하고 있는데,", "당신은 내가 속임을 당할 것이라고 말하고 있나요?"],
            expression="I'm gonna get screwed",
            expression_translation="속임을 당할 것 같아요",
            context_start_time="00:01:25,657",
            context_end_time="00:01:32,230",
            similar_expressions=["I'm going to be cheated", "I'm getting the short end of the stick"]
        )
        
        # Step 3: Extract subtitles for expression
        logger.info("Step 3: Extracting subtitles for expression...")
        matching_subtitles = processor.extract_subtitles_for_expression(test_expression)
        
        if not matching_subtitles:
            logger.warning("No matching subtitles found")
            return False
        
        logger.info(f"Found {len(matching_subtitles)} matching subtitles")
        
        # Step 4: Create dual-language subtitle file
        logger.info("Step 4: Creating dual-language subtitle file...")
        output_path = Path(output_dir) / "test_expression.srt"
        
        success = processor.create_dual_language_subtitle_file(test_expression, str(output_path))
        
        if not success:
            logger.error("Failed to create subtitle file")
            return False
        
        # Step 5: Verify output file
        logger.info("Step 5: Verifying output file...")
        if not output_path.exists():
            logger.error("Output file not created")
            return False
        
        file_size = output_path.stat().st_size
        logger.info(f"Created subtitle file: {output_path} ({file_size} bytes)")
        
        # Step 6: Display content preview
        logger.info("Step 6: Displaying content preview...")
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            preview_lines = lines[:20]  # First 20 lines
            logger.info("Content preview:")
            for line in preview_lines:
                if line.strip():
                    logger.info(f"  {line}")
        
        # Step 7: Test convenience function
        logger.info("Step 7: Testing convenience function...")
        convenience_output = Path(output_dir) / "test_convenience.srt"
        success = create_subtitle_file_for_expression(
            test_expression, 
            subtitle_file, 
            str(convenience_output)
        )
        
        if success:
            logger.info(f"Convenience function test passed: {convenience_output}")
        else:
            logger.warning("Convenience function test failed")
        
        # Step 8: Summary
        logger.info("Subtitle processing completed!")
        logger.info(f"Output directory: {output_dir}")
        
        # List output files
        output_files = list(Path(output_dir).glob("*.srt"))
        logger.info(f"Generated subtitle files: {[f.name for f in output_files]}")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("📝 Testing Subtitle Processing")
    print("=" * 50)
    
    success = test_subtitle_processing()
    
    if success:
        print("\n✅ Subtitle processing test PASSED!")
        print("Check the 'tests/test_output' directory for generated subtitle files.")
    else:
        print("\n❌ Subtitle processing test FAILED!")
        print("Check the logs above for error details.")
