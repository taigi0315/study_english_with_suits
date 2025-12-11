
import requests
import time
import json
import os
import sys
from pathlib import Path

# Configuration
API_URL = "http://localhost:8000/api/v1"
MEDIA_DIR = Path("assets/media/test_media")
VIDEO_File = "Suits.S02E04.720p.HDTV.x264-IMMERSE.mkv"
SUBTITLE_FILE = "Suits.S02E04.720p.HDTV.x264-IMMERSE.srt"

def test_video_generation():
    print(f"🚀 Starting API Test Script...")
    print(f"📂 Media Directory: {MEDIA_DIR}")
    
    # 1. Validate files
    video_path = MEDIA_DIR / VIDEO_File
    subtitle_path = MEDIA_DIR / SUBTITLE_FILE
    
    if not video_path.exists():
        print(f"❌ Video file not found: {video_path}")
        return
    if not subtitle_path.exists():
        print(f"❌ Subtitle file not found: {subtitle_path}")
        return
        
    print(f"✅ Found media files: {VIDEO_File}, {SUBTITLE_FILE}")
    
    # 2. Upload and Create Job
    print("📤 Uploading files and creating job...")
    
    url = f"{API_URL}/jobs"
    
    payload = {
        "language_code": "ko",
        "show_name": "Suits",
        "episode_name": "S02E04",
        "max_expressions": 3,
        "language_level": "intermediate",
        "test_mode": "true",  # String for Form
        "no_shorts": "false",
        "short_form_max_duration": 180.0,
        "create_long_form": "true",
        "create_short_form": "true",
        "target_languages": "Korean",
        "auto_upload_config": json.dumps({
            "enabled": False,  # No upload for test
            "timing": "immediate",
            "upload_shorts": False,
            "upload_long": False
        })
    }
    
    files = [
        ('video_file', (VIDEO_File, open(video_path, 'rb'), 'video/x-matroska')),
        ('subtitle_file', (SUBTITLE_FILE, open(subtitle_path, 'rb'), 'application/x-subrip'))
    ]
    
    try:
        response = requests.post(url, data=payload, files=files)
        response.raise_for_status()
        result = response.json()
        job_id = result['job_id']
        print(f"✅ Job Created Successfully! Job ID: {job_id}")
        print(f"📊 Initial Status: {result['status']}")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API. Is the server running on localhost:8000?")
        return
    except Exception as e:
        print(f"❌ Error creating job: {e}")
        if 'response' in locals():
            print(f"Response: {response.text}")
        return
    finally:
        # Close file handles
        for _, (name, f, _) in files:
            f.close()

    # 3. Poll for Progress
    print(f"\n⏳ Polling for job completion (Job: {job_id})...")
    
    status_url = f"{API_URL}/jobs/{job_id}"
    
    while True:
        try:
            res = requests.get(status_url)
            if res.status_code != 200:
                print(f"⚠️ Error checking status: {res.status_code}")
                time.sleep(5)
                continue
                
            job_info = res.json()
            status = job_info.get('status')
            progress = job_info.get('progress')
            current_step = job_info.get('current_step', '')
            
            # Clear line and print status
            sys.stdout.write(f"\r🔄 Status: {status} | Progress: {progress}% | Step: {current_step[:50]:<50}")
            sys.stdout.flush()
            
            if status in ['COMPLETED', 'FAILED']:
                print("\n")
                if status == 'COMPLETED':
                    print("🎉 Job Completed Successfully!")
                    print("📁 Results:")
                    print(json.dumps(job_info.get('expressions', [])[:1], indent=2)) # Print first expression as sample
                    print("...")
                    if 'upload_results' in job_info:
                         print("\n📤 Upload Results (Should be empty for this test):")
                         print(json.dumps(job_info.get('upload_results'), indent=2))

                else:
                    print(f"❌ Job Failed: {job_info.get('error')}")
                break
            
            time.sleep(3)
            
        except KeyboardInterrupt:
            print("\n🛑 Polling stopped by user.")
            break
        except Exception as e:
            print(f"\n❌ Error polling status: {e}")
            break

if __name__ == "__main__":
    test_video_generation()
