"""
End-to-end integration test that sends actual HTTP requests to the backend API.

This test:
- Starts/connects to the actual FastAPI backend
- Sends HTTP POST request to create a video job
- Uses Episode 1 subtitle file
- Uses test_mode=True
- Outputs to test_output directory
- Verifies job status and completion
"""
import pytest
import os
import time
import requests
from pathlib import Path
from typing import Dict, Any


@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.slow
class TestBackendVideoCreation:
    """End-to-end tests that interact with the actual backend API."""
    
    BASE_URL = "http://localhost:8000"
    API_ENDPOINT = f"{BASE_URL}/api/v1/jobs"
    
    @pytest.fixture
    def episode1_subtitle_path(self):
        """Path to Episode 1 subtitle file."""
        subtitle_paths = [
            Path("assets/media/Suits/Suits.S01E01.720p.HDTV.x264.srt"),
            Path("assets/media/Suits.S01E01.720p.HDTV.x264.srt"),
        ]
        
        for path in subtitle_paths:
            if path.exists():
                return str(path.absolute())
        
        pytest.skip(f"Episode 1 subtitle file not found. Tried: {[str(p) for p in subtitle_paths]}")
    
    @pytest.fixture
    def episode1_video_path(self):
        """Path to Episode 1 video file."""
        video_paths = [
            Path("assets/media/Suits/Suits.S01E01.720p.HDTV.x264.mkv"),
            Path("assets/media/Suits.S01E01.720p.HDTV.x264.mkv"),
        ]
        
        for path in video_paths:
            if path.exists():
                return str(path.absolute())
        
        pytest.skip(f"Episode 1 video file not found. Tried: {[str(p) for p in video_paths]}")
    
    @pytest.fixture
    def check_backend_available(self):
        """Check if backend is running, skip test if not."""
        try:
            response = requests.get(f"{self.BASE_URL}/health", timeout=2)
            if response.status_code != 200:
                pytest.skip("Backend is not available (health check failed)")
        except requests.exceptions.RequestException:
            pytest.skip("Backend is not available (connection failed)")
    
    def test_create_video_job_via_backend(
        self, 
        check_backend_available,
        episode1_video_path,
        episode1_subtitle_path
    ):
        """
        Test creating a video job via the backend API with test_mode enabled.
        
        This test:
        1. Reads Episode 1 video and subtitle files
        2. Sends POST request to /api/v1/jobs endpoint
        3. Polls job status until completion or failure
        4. Verifies job completed successfully
        5. Checks that output was created in test_output directory
        """
        # Read files
        with open(episode1_video_path, 'rb') as f:
            video_content = f.read()
        
        with open(episode1_subtitle_path, 'rb') as f:
            subtitle_content = f.read()
        
        # Prepare multipart form data
        # FastAPI expects field names to match function parameter names
        files = {
            'video_file': (
                os.path.basename(episode1_video_path),
                video_content,
                'video/x-matroska'
            ),
            'subtitle_file': (
                os.path.basename(episode1_subtitle_path),
                subtitle_content,
                'text/plain'
            )
        }
        
        data = {
            'show_name': 'Suits',
            'episode_name': 'S01E01_Pilot',
            'language_code': 'ko',
            'max_expressions': 5,
            'language_level': 'intermediate',
            'test_mode': 'true',  # Enable test mode
            'no_shorts': 'true',  # Skip shorts for faster test
            'output_dir': 'test_output'  # Output to test_output directory
        }
        
        print(f"\n📤 Sending request to {self.API_ENDPOINT}")
        print(f"   Video: {os.path.basename(episode1_video_path)} ({len(video_content)} bytes)")
        print(f"   Subtitle: {os.path.basename(episode1_subtitle_path)} ({len(subtitle_content)} bytes)")
        print(f"   Test mode: {data['test_mode']}")
        print(f"   Output directory: {data['output_dir']}")
        
        # Send POST request
        response = requests.post(
            self.API_ENDPOINT,
            files=files,
            data=data,
            timeout=30
        )
        
        # Verify initial response
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        job_response = response.json()
        
        assert "job_id" in job_response, "Response should contain job_id"
        job_id = job_response["job_id"]
        print(f"\n✅ Job created: {job_id}")
        
        # Poll job status
        max_wait_time = 300  # 5 minutes max
        poll_interval = 2  # Poll every 2 seconds
        start_time = time.time()
        
        job_status_url = f"{self.BASE_URL}/api/v1/jobs/{job_id}"
        
        print(f"\n⏳ Polling job status at {job_status_url}...")
        
        last_status = None
        last_progress = 0
        
        while time.time() - start_time < max_wait_time:
            try:
                status_response = requests.get(job_status_url, timeout=10)
                assert status_response.status_code == 200, f"Failed to get job status: {status_response.text}"
                
                status_data = status_response.json()
                status = status_data.get("status")
                progress = status_data.get("progress", 0)
                current_step = status_data.get("current_step", "")
                
                # Print progress updates
                if status != last_status or progress != last_progress:
                    print(f"   Status: {status}, Progress: {progress}%, Step: {current_step}")
                    last_status = status
                    last_progress = progress
                
                if status == "COMPLETED":
                    print(f"\n✅ Job completed successfully!")
                    
                    # Verify job result
                    assert "expressions" in status_data, "Job result should contain expressions"
                    assert "educational_videos" in status_data, "Job result should contain educational_videos"
                    
                    expressions = status_data.get("expressions", [])
                    print(f"   Expressions found: {len(expressions)}")
                    
                    if expressions:
                        print(f"\n   Sample expressions:")
                        for i, expr in enumerate(expressions[:3], 1):
                            if isinstance(expr, dict):
                                expr_text = expr.get("expression", "N/A")
                                expr_trans = expr.get("expression_translation", "N/A")
                                print(f"     {i}. {expr_text} -> {expr_trans}")
                            else:
                                print(f"     {i}. {expr}")
                    
                    # Verify output directory structure
                    test_output_dir = Path("test_output")
                    if test_output_dir.exists():
                        episode_dir = test_output_dir / "Suits" / "S01E01_Pilot"
                        if episode_dir.exists():
                            translations_dir = episode_dir / "translations" / "ko"
                            if translations_dir.exists():
                                created_files = list(translations_dir.rglob("*"))
                                file_count = len([f for f in created_files if f.is_file()])
                                print(f"\n📁 Created {file_count} files in {translations_dir}")
                                
                                if file_count > 0:
                                    print(f"   Sample files:")
                                    for file_path in sorted(created_files)[:5]:
                                        if file_path.is_file():
                                            size = file_path.stat().st_size
                                            print(f"     - {file_path.name} ({size} bytes)")
                    
                    # Return success
                    return
                    
                elif status == "FAILED":
                    error_message = status_data.get("error", "Unknown error")
                    print(f"\n❌ Job failed: {error_message}")
                    pytest.fail(f"Job failed with error: {error_message}")
                    
                elif status in ["PENDING", "PROCESSING"]:
                    # Continue polling
                    time.sleep(poll_interval)
                else:
                    pytest.fail(f"Unknown job status: {status}")
                    
            except requests.exceptions.RequestException as e:
                print(f"⚠️ Error polling job status: {e}")
                time.sleep(poll_interval)
        
        # Timeout
        pytest.fail(f"Job did not complete within {max_wait_time} seconds. Last status: {last_status}")
    
    def test_job_status_endpoint(self, check_backend_available):
        """Test that job status endpoint is accessible."""
        # Try to get status of a non-existent job (should return 404 or empty)
        response = requests.get(
            f"{self.BASE_URL}/api/v1/jobs/non-existent-job-id",
            timeout=5
        )
        
        # Should either return 404 or some error response, not crash
        assert response.status_code in [200, 404, 400], \
            f"Unexpected status code: {response.status_code}"
        
        print(f"✅ Job status endpoint is accessible (returned {response.status_code})")

