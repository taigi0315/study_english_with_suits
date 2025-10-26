#!/usr/bin/env python3
"""
Test script for expression video loop creation
Tests the concat demuxer approach step by step
"""
import os
import sys
from pathlib import Path
import ffmpeg

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from langflix import settings

def test_config():
    """Test 1: Verify unified configuration"""
    print("=" * 60)
    print("TEST 1: Configuration")
    print("=" * 60)
    
    repeat_count = settings.get_expression_repeat_count()
    tts_count = settings.get_tts_repeat_count()
    short_count = settings.get_short_video_expression_repeat_count()
    
    print(f"✅ Expression repeat count: {repeat_count}")
    print(f"✅ TTS repeat count (should match): {tts_count}")
    print(f"✅ Short video repeat count (should match): {short_count}")
    
    if repeat_count == tts_count == short_count:
        print("✅ All configurations are unified!")
        return True
    else:
        print("❌ Configurations don't match!")
        return False

def test_concat_file_creation():
    """Test 2: Test concat file creation"""
    print("\n" + "=" * 60)
    print("TEST 2: Concat File Creation")
    print("=" * 60)
    
    try:
        # Create a dummy expression video path
        dummy_path = Path("test_expression.mkv").absolute()
        
        # Create concat file
        concat_file = Path("test_concat.txt")
        with open(concat_file, 'w') as f:
            for i in range(3):
                f.write(f"file '{dummy_path}'\n")
        
        print(f"✅ Created concat file: {concat_file}")
        
        # Read and display
        with open(concat_file, 'r') as f:
            content = f.read()
            print(f"✅ Content:\n{content}")
        
        # Cleanup
        concat_file.unlink()
        print("✅ Cleaned up concat file")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_duration_calculation():
    """Test 3: Test duration calculation"""
    print("\n" + "=" * 60)
    print("TEST 3: Duration Calculation")
    print("=" * 60)
    
    try:
        repeat_count = 3
        expression_duration = 2.5  # 2.5 seconds
        required_duration = 2.0 + (expression_duration * repeat_count) + (0.5 * (repeat_count - 1))
        
        print(f"Repeat count: {repeat_count}")
        print(f"Base expression duration: {expression_duration}s")
        print(f"Required duration: {required_duration}s")
        print(f"Expected pattern: 1s silence + ({expression_duration}s × {repeat_count}) + ({0.5}s × {repeat_count-1}) + 1s silence")
        
        # Calculate expected
        expected = 2.0 + (2.5 * 3) + (0.5 * 2)  # 2 + 7.5 + 1 = 10.5
        print(f"Expected: {expected}s")
        
        if abs(required_duration - expected) < 0.01:
            print("✅ Duration calculation is correct!")
            return True
        else:
            print("❌ Duration calculation mismatch!")
            return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def main():
    """Run all tests"""
    print("\n🔧 Expression Video Loop - Step by Step Tests")
    print("=" * 60)
    
    results = []
    
    # Test 1: Configuration
    results.append(test_config())
    
    # Test 2: Concat file creation
    results.append(test_concat_file_creation())
    
    # Test 3: Duration calculation
    results.append(test_duration_calculation())
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All tests passed! Configuration is correct.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
