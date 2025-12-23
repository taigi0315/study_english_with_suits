
import sys
import os
import logging
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from langflix.core.video_editor import VideoEditor
from langflix.core.models import ExpressionAnalysis, VocabularyAnnotation
from langflix import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting isolated vocabulary visibility test")
    
    video_path = "output/whatever.mkv"
    if not os.path.exists(video_path):
        import glob
        # Try finding any MKV in current dir or assets
        possible_videos = ["test_video.mkv", "assets/media/test_media/test_video.mkv"]
        found = False
        for v in possible_videos:
            if os.path.exists(v):
                video_path = v
                logger.info(f"Fallback to: {video_path}")
                found = True
                break
        
        if not found:
            mkvs = glob.glob("**/*.mkv", recursive=True)
            if mkvs:
                video_path = mkvs[0]
                logger.info(f"Fallback to glob found: {video_path}")
            else:
                # Last resort: use the original large file if present
                video_path = "assets/media/test_media/The.Glory.S01E01.KOREAN.1080p.WEBRip.x265-RARBG[eztv.re].mp4"
                if not os.path.exists(video_path):
                     logger.error("No video found anywhere!")
                     return
        import glob
        mkvs = glob.glob("output/**/*.mkv", recursive=True)
        if mkvs:
            video_path = mkvs[0]
            logger.info(f"Fallback to: {video_path}")
        else:
            return
        
    output_dir = Path("output/debug_vocab")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Dummy Expression
    expr = ExpressionAnalysis(
        expression="안녕하세요",
        expression_translation="Hello",
        expression_start_time="00:00:10,000",
        expression_end_time="00:00:15,000",
        context_start_time="00:00:00,000", # 10s start
        context_end_time="00:00:30,000",
        
        # Missing required fields
        dialogues=["안녕하세요. 처음 뵙겠습니다."], 
        translation=["Hello. Nice to meet you."],
        expression_dialogue="안녕하세요. 처음 뵙겠습니다.",
        expression_dialogue_translation="Hello. Nice to meet you.",
        similar_expressions=["반갑습니다"],
        
        vocabulary_annotations=[
            VocabularyAnnotation(word="TEST_VOCAB", translation="TEST_TRANS", dialogue_index=0),
            VocabularyAnnotation(word="VISIBLE?", translation="YES", dialogue_index=1)
        ]
    )
    
    # Init Editor
    editor = VideoEditor(
        output_dir=str(output_dir),
        language_code="es",
        episode_name="DebugEpisode",
        test_mode=True
    )
    # mock subtitle processor
    editor.subtitle_processor = MagicMock()
    
    # Run short form creation
    # We use the raw video as master clip for simplicity (it's 9:16? No, probably 16:9)
    # create_short_form expects a master clip (which is usually the context clip).
    # If we pass the full episode, it might be too long/wrong aspect.
    # But for drawtext testing, it should overlay on top regardless of aspect (if mapped correctly).
    # Wait, create_short_form does crop/scale? 
    # It assumes master clip is pre-processed?
    # Note: master clip is 9:16 already?
    # No, create_long_form returns a video.
    
    # Let's verify what create_short_form expects.
    # It takes pre_extracted_context_clip.
    
    # We will try to run create_short_form_from_long_form with the raw video.
    # It might look weird but text should be drawn.
    try:
        output_path = editor.create_short_form_from_long_form(
            expression=expr,
            long_form_video_path=video_path,
            expression_index=1
        )
        logger.info(f"Success! Output: {output_path}")
    except Exception as e:
        logger.error(f"Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
