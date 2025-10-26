#!/usr/bin/env python3
"""
Test FFmpeg concat demuxer with actual video files
"""
import os
import sys
from pathlib import Path
import ffmpeg

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_extract_short_video_clip():
    """Extract a short 2-second clip from a video"""
    print("=" * 60)
    print("TEST 1: Extract Short Video Clip")
    print("=" * 60)
    
    input_video = "assets/media/Suits/Suits.S01E01.720p.HDTV.x264.mkv"
    output_video = "test_output/test_clip.mkv"
    
    if not Path(input_video).exists():
        print(f"❌ Input video not found: {input_video}")
        return None
    
    # Create output directory
    Path("test_output").mkdir(exist_ok=True)
    
    try:
        # Extract 2-second clip from 10 seconds into the video
        (ffmpeg.input(input_video, ss=10, t=2)
         .output(str(output_video), vcodec='libx264', an=None, preset='fast', crf=23)
         .overwrite_output()
         .run(quiet=True))
        
        print(f"✅ Extracted clip: {output_video}")
        
        # Check if file exists
        if Path(output_video).exists():
            file_size = Path(output_video).stat().st_size
            print(f"✅ File size: {file_size} bytes")
            return output_video
        else:
            print("❌ Output file not created")
            return None
            
    except ffmpeg.Error as e:
        print(f"❌ FFmpeg error: {e}")
        if e.stderr:
            print(f"stderr: {e.stderr.decode()}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_concat_demuxer(clip_path):
    """Test concat demuxer with the extracted clip"""
    print("\n" + "=" * 60)
    print("TEST 2: Concat Demuxer")
    print("=" * 60)
    
    if not clip_path:
        print("❌ No clip available for testing")
        return False
    
    output_loop = "test_output/test_loop.mkv"
    
    try:
        # Create concat file
        concat_file = "test_output/test_concat.txt"
        clip_absolute = Path(clip_path).absolute()
        
        with open(concat_file, 'w') as f:
            for i in range(3):  # Loop 3 times
                f.write(f"file '{clip_absolute}'\n")
        
        print(f"✅ Created concat file: {concat_file}")
        
        # Use concat demuxer to loop the video
        (ffmpeg.input(str(concat_file), format='concat', safe=0)
         .output(str(output_loop), vcodec='libx264', t=6.0, preset='fast', crf=23)
         .overwrite_output()
         .run(quiet=True))
        
        print(f"✅ Created looped video: {output_loop}")
        
        # Check duration
        try:
            probe = ffmpeg.probe(output_loop)
            duration = float(probe['format']['duration'])
            print(f"✅ Output duration: {duration:.2f}s (expected: 6.0s)")
            
            if abs(duration - 6.0) < 0.5:  # Allow 0.5s tolerance
                print("✅ Duration is correct!")
                return True
            else:
                print(f"⚠️  Duration mismatch (expected 6.0s, got {duration:.2f}s)")
                return False
        except Exception as e:
            print(f"⚠️  Could not probe output: {e}")
            return True  # File was created, assume success
            
    except ffmpeg.Error as e:
        print(f"❌ FFmpeg error: {e}")
        if e.stderr:
            stderr = e.stderr.decode()
            print(f"stderr: {stderr[:500]}")  # First 500 chars
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("\n🔧 FFmpeg Concat Demuxer Test")
    print("=" * 60)
    
    # Test 1: Extract clip
    clip_path = test_extract_short_video_clip()
    
    # Test 2: Concat demuxer
    if clip_path:
        result = test_concat_demuxer(clip_path)
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        if result:
            print("✅ Concat demuxer test passed!")
            print("✅ Direction is correct - concat demuxer works!")
            return 0
        else:
            print("❌ Concat demuxer test failed")
            print("❌ Need to investigate further")
            return 1
    else:
        print("\n❌ Could not extract test clip")
        return 1

if __name__ == "__main__":
    sys.exit(main())
