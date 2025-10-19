"""
Configuration and setup for step-by-step testing scripts
"""
import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Test file paths
SUBTITLE_FILE = project_root / "assets/media/Suits/Suits.S01E01.720p.HDTV.x264.srt"
VIDEO_FILE = project_root / "assets/media/Suits/Suits.S01E01.720p.HDTV.x264.mkv"

# Output directories for each step
TEST_OUTPUT_ROOT = project_root / "test_output"
STEP_OUTPUTS = {
    1: TEST_OUTPUT_ROOT / "step1",
    2: TEST_OUTPUT_ROOT / "step2", 
    3: TEST_OUTPUT_ROOT / "step3",
    4: TEST_OUTPUT_ROOT / "step4",
    5: TEST_OUTPUT_ROOT / "step5",
    6: TEST_OUTPUT_ROOT / "step6",
    7: TEST_OUTPUT_ROOT / "step7",
    8: TEST_OUTPUT_ROOT / "step8",
    9: TEST_OUTPUT_ROOT / "step9"
}

# Validation thresholds
VALIDATION_CONFIG = {
    "min_video_size_bytes": 1000,  # 1KB minimum
    "min_audio_size_bytes": 1000,  # 1KB minimum
    "min_subtitle_size_bytes": 10,  # 10 bytes minimum
    "max_duration_difference_ms": 100,  # 100ms tolerance for duration
    "required_video_streams": ["video"],
    "required_audio_streams": ["audio"],
    "expected_video_resolutions": [(1280, 720), (1920, 1080)],
    "min_audio_sample_rate": 44100,
    "min_audio_channels": 1,
}

# Test settings
TEST_SETTINGS = {
    "max_expressions": None,  # No limit - process all expressions
    "language_code": "es",  # Spanish language code
    "language_level": None,
    "save_llm_output": True,
    "test_mode": True  # Process only first chunk
}

# Available transition types for FFmpeg xfade filter
XFADE_TRANSITIONS = [
    "fade",      # Simple crossfade (default)
    "wipeleft",  # Wipe from left to right
    "wiperight", # Wipe from right to left  
    "wipeup",    # Wipe from bottom to top
    "wipedown",  # Wipe from top to bottom
    "slideleft", # Slide left (new video comes from right)
    "slideright",# Slide right (new video comes from left)
    "slideup",   # Slide up (new video comes from bottom)
    "slidedown", # Slide down (new video comes from top)
    "circlecrop",# Circular crop with zoom out
    "rectcrop",  # Rectangular crop with zoom out
    "distance",  # Distance-based transition
    "fadeblack", # Fade to black between videos
    "fadewhite", # Fade to white between videos
    "radial",    # Radial transition
    "smoothleft",# Smooth left transition
    "smoothright",# Smooth right transition
    "smoothup",  # Smooth up transition
    "smoothdown",# Smooth down transition
]

# Transition settings for smooth video effects
TRANSITION_CONFIG = {
    "enabled": True,  # Enable/disable transitions
    "context_to_slide": {
        "type": "xfade",  # Options: "xfade", "fade", "none"
        "transition": "slideup",  # One of XFADE_TRANSITIONS above
        "duration": 0.5,  # Transition duration in seconds
        "max_duration_ratio": 0.15  # Max 15% of shorter clip duration
    },
    "expression_to_expression": {
        "type": "fade",  # Options: "fade", "xfade", "none"  
        "duration": 0.5,  # Transition duration in seconds
        "fade_in_out": True,  # Apply fade-in and fade-out at boundaries
        "transition": "slideleft"  # For xfade type: transition effect
    }
}

def setup_test_environment():
    """Setup test environment and verify input files exist"""
    # Verify input files
    if not SUBTITLE_FILE.exists():
        raise FileNotFoundError(f"Subtitle file not found: {SUBTITLE_FILE}")
    
    if not VIDEO_FILE.exists():
        raise FileNotFoundError(f"Video file not found: {VIDEO_FILE}")
    
    print(f"✅ Test files verified:")
    print(f"  - Subtitle: {SUBTITLE_FILE}")
    print(f"  - Video: {VIDEO_FILE}")

def get_step_output_dir(step_num: int) -> Path:
    """Get output directory for a specific step"""
    if step_num not in STEP_OUTPUTS:
        raise ValueError(f"Invalid step number: {step_num}")
    return STEP_OUTPUTS[step_num]

def clean_step_directory(step_num: int):
    """Clean output directory for a specific step"""
    step_dir = get_step_output_dir(step_num)
    if step_dir.exists():
        import shutil
        shutil.rmtree(step_dir)
        print(f"🧹 Cleaned directory: {step_dir}")
    step_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Created directory: {step_dir}")

def clean_all_test_outputs():
    """Clean all test output directories"""
    if TEST_OUTPUT_ROOT.exists():
        import shutil
        shutil.rmtree(TEST_OUTPUT_ROOT)
        print(f"🧹 Cleaned all test outputs: {TEST_OUTPUT_ROOT}")
    
    # Recreate base directory
    TEST_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    print(f"📁 Created base test output directory: {TEST_OUTPUT_ROOT}")
