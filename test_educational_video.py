#!/usr/bin/env python3
"""
Test script for educational video creation
"""

import sys
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from langflix.video_editor import VideoEditor
from langflix.models import ExpressionAnalysis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

def create_test_educational_video():
    """Create a test educational video"""
    
    # Create a test expression
    test_expression = ExpressionAnalysis(
        dialogues=[
            "Consider it done.",
            "I'll take care of it."
        ],
        translation=[
            "완료되었습니다.",
            "제가 처리하겠습니다."
        ],
        expression="Consider it done",
        expression_translation="완료되었습니다",
        context_start_time="00:00:00,000",
        context_end_time="00:00:05,000",
        similar_expressions=[
            "I'll handle it",
            "Leave it to me"
        ],
        scene_type="professional",
        why_valuable="Common business expression for taking responsibility"
    )
    
    # Initialize video editor
    editor = VideoEditor("output")
    
    # Test with first available video
    test_video = "output/expression_01_Consider it done.mkv"
    
    if not Path(test_video).exists():
        logger.error(f"Test video not found: {test_video}")
        return
    
    try:
        logger.info("Creating test educational video...")
        
        # Create educational sequence
        educational_video = editor.create_educational_sequence(
            test_expression,
            test_video,  # context video
            test_video   # expression video (same for now)
        )
        
        logger.info(f"✅ Educational video created: {educational_video}")
        
    except Exception as e:
        logger.error(f"❌ Error creating educational video: {e}")
        raise

if __name__ == "__main__":
    create_test_educational_video()
