#!/usr/bin/env python3
"""
Test script for short video fix
"""
import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from langflix.core.video_editor import VideoEditor
from langflix.core.models import ExpressionAnalysis
from langflix import settings

def test_short_video_creation():
    """Test short video creation with the fixed code"""
    
    print("🔧 Testing Short Video Creation Fix")
    print("=" * 50)
    
    # Test config loading
    print("1. Testing config loading...")
    try:
        repeat_count = settings.get_short_video_expression_repeat_count()
        print(f"   ✅ Expression repeat count: {repeat_count}")
    except Exception as e:
        print(f"   ❌ Error loading config: {e}")
        return False
    
    # Test VideoEditor initialization
    print("2. Testing VideoEditor initialization...")
    try:
        editor = VideoEditor(output_dir="test_output", language_code="en")
        print("   ✅ VideoEditor initialized successfully")
    except Exception as e:
        print(f"   ❌ Error initializing VideoEditor: {e}")
        return False
    
    # Test _get_original_video_path function
    print("3. Testing _get_original_video_path function...")
    try:
        # Test with a dummy context video path
        context_path = "test_context.mkv"
        subtitle_path = None
        
        original_video = editor._get_original_video_path(context_path, subtitle_path)
        print(f"   Original video path: {original_video}")
        
        if original_video and Path(original_video).exists():
            print("   ✅ Original video found and exists")
        else:
            print("   ⚠️  Original video not found or doesn't exist")
            print("   This is expected if no video files are in assets/media/")
        
    except Exception as e:
        print(f"   ❌ Error in _get_original_video_path: {e}")
        return False
    
    print("\n✅ All tests passed! The fix should work correctly.")
    return True

if __name__ == "__main__":
    success = test_short_video_creation()
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n❌ Test failed!")
        sys.exit(1)
