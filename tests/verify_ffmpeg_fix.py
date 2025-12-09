import ffmpeg
import os
from pathlib import Path
from langflix.media.ffmpeg_utils import concat_filter_with_explicit_map

def create_dummy_video(filename, width, height, duration=1, color='red'):
    """Create a dummy video with specific resolution"""
    input_video = ffmpeg.input(f'color=c={color}:s={width}x{height}:d={duration}', f='lavfi')
    input_audio = ffmpeg.input('anullsrc=channel_layout=stereo:sample_rate=44100', f='lavfi')
    (
        ffmpeg
        .output(input_video, input_audio, filename, vcodec='libx264', acodec='aac', pix_fmt='yuv420p', r=25, shortest=None)
        .overwrite_output()
        .run(quiet=True)
    )

def test_concat():
    v1 = "test_720.mp4"
    v2 = "test_724.mp4"
    out = "test_concat.mkv"
    
    try:
        print("Creating dummy videos...")
        create_dummy_video(v1, 1280, 720, color='red')
        create_dummy_video(v2, 1280, 724, color='blue')  # Intentional mismatch
        
        print(f"Created {v1} (1280x720) and {v2} (1280x724)")
        print("Attempting concatenation with fix...")
        
        concat_filter_with_explicit_map(v1, v2, out)
        
        if os.path.exists(out):
            print("✅ Concatenation successful! Output file created.")
            # Verify output resolution
            probe = ffmpeg.probe(out)
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            w = video_stream['width']
            h = video_stream['height']
            print(f"Output resolution: {w}x{h}")
            if w == 1280 and h == 720:
                print("✅ Resolution correct (1280x720)")
            else:
                print(f"❌ Resolution incorrect: {w}x{h}")
        else:
            print("❌ Output file not created.")

    except Exception as e:
        print(f"❌ Concatenation failed: {e}")
    finally:
        # Cleanup
        for f in [v1, v2, out]:
            if os.path.exists(f):
                os.remove(f)

if __name__ == "__main__":
    test_concat()
