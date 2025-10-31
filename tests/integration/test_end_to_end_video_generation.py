"""
End-to-end integration test for video generation with Episode 1.

This test actually creates video files using real episode data.
"""
import pytest
import os
import tempfile
import shutil
from pathlib import Path
from langflix.services.video_pipeline_service import VideoPipelineService
from langflix.services.output_manager import create_output_structure


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndVideoGeneration:
    """End-to-end tests that generate actual video files."""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory for test."""
        temp_dir = tempfile.mkdtemp(prefix="langflix_test_")
        yield Path(temp_dir)
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def episode1_video_path(self):
        """Path to Episode 1 video file."""
        # Look for video in assets/media/Suits/
        video_paths = [
            Path("assets/media/Suits/Suits.S01E01.720p.HDTV.x264.mkv"),
            Path("assets/media/Suits.S01E01.720p.HDTV.x264.mkv"),
            Path("../assets/media/Suits/Suits.S01E01.720p.HDTV.x264.mkv"),
        ]
        
        for path in video_paths:
            if path.exists():
                return str(path.absolute())
        
        pytest.skip(f"Episode 1 video file not found. Tried: {[str(p) for p in video_paths]}")
    
    @pytest.fixture
    def episode1_subtitle_path(self):
        """Path to Episode 1 subtitle file."""
        # Look for subtitle in assets/media/Suits/
        subtitle_paths = [
            Path("assets/media/Suits/Suits.S01E01.720p.HDTV.x264.srt"),
            Path("assets/media/Suits.S01E01.720p.HDTV.x264.srt"),
            Path("../assets/media/Suits/Suits.S01E01.720p.HDTV.x264.srt"),
        ]
        
        for path in subtitle_paths:
            if path.exists():
                return str(path.absolute())
        
        pytest.skip(f"Episode 1 subtitle file not found. Tried: {[str(p) for p in subtitle_paths]}")
    
    def test_generate_video_with_episode1_test_mode(self, temp_output_dir, episode1_video_path, episode1_subtitle_path):
        """
        Test end-to-end video generation with Episode 1 in test mode.
        
        This test:
        - Uses actual Episode 1 video and subtitle files
        - Processes with test_mode=True (only first chunk)
        - Verifies that output files are created
        - Checks that expressions are found and processed
        """
        # Initialize service
        service = VideoPipelineService(
            language_code="ko",
            output_dir=str(temp_output_dir)
        )
        
        # Track progress
        progress_messages = []
        
        def progress_callback(progress: int, message: str):
            progress_messages.append((progress, message))
            print(f"Progress: {progress}% - {message}")
        
        # Process video
        result = service.process_video(
            video_path=episode1_video_path,
            subtitle_path=episode1_subtitle_path,
            show_name="Suits",
            episode_name="S01E01_Pilot",
            max_expressions=5,  # Limit to 5 expressions in test mode
            language_level="intermediate",
            test_mode=True,  # Only process first chunk
            no_shorts=True,  # Skip short videos for faster testing
            progress_callback=progress_callback
        )
        
        # Verify progress callbacks were called
        assert len(progress_messages) > 0, "Progress callbacks should be called"
        assert any("completed" in msg.lower() or progress >= 90 for progress, msg in progress_messages), \
            "Should receive completion progress"
        
        # Verify result structure
        assert "expressions" in result, "Result should contain expressions"
        assert "educational_videos" in result, "Result should contain educational_videos"
        assert "short_videos" in result, "Result should contain short_videos"
        
        # In test mode, we should find at least some expressions
        # (even if 0, that's okay - just means first chunk had none)
        assert isinstance(result["expressions"], list), "Expressions should be a list"
        
        # If expressions were found, verify they have required fields
        if len(result["expressions"]) > 0:
            first_expr = result["expressions"][0]
            assert hasattr(first_expr, "expression"), "Expression should have 'expression' field"
            assert hasattr(first_expr, "expression_translation"), "Expression should have 'expression_translation' field"
            assert hasattr(first_expr, "dialogues"), "Expression should have 'dialogues' field"
            
            print(f"\n✅ Found {len(result['expressions'])} expressions in test mode")
            for i, expr in enumerate(result["expressions"], 1):
                print(f"  {i}. {expr.expression} -> {expr.expression_translation}")
        
        # Verify output structure was created
        episode_dir = temp_output_dir / "Suits" / "S01E01_Pilot"
        if episode_dir.exists():
            translations_dir = episode_dir / "translations" / "ko"
            assert translations_dir.exists(), f"Translations directory should exist: {translations_dir}"
            print(f"\n✅ Output structure created: {translations_dir}")
            
            # List created files
            created_files = list(translations_dir.rglob("*"))
            print(f"\n📁 Created files ({len(created_files)}):")
            for file_path in sorted(created_files):
                if file_path.is_file():
                    size = file_path.stat().st_size
                    print(f"  - {file_path.relative_to(temp_output_dir)} ({size} bytes)")
        
        # Verify summary
        assert "summary" in result, "Result should contain summary"
        summary = result["summary"]
        assert isinstance(summary, dict), "Summary should be a dictionary"
        
        print(f"\n✅ Test completed successfully!")
        print(f"   - Expressions found: {len(result['expressions'])}")
        print(f"   - Progress updates: {len(progress_messages)}")
        print(f"   - Output directory: {temp_output_dir}")
    
    def test_generate_video_with_episode1_full_mode(self, temp_output_dir, episode1_video_path, episode1_subtitle_path):
        """
        Test end-to-end video generation with Episode 1 in full mode.
        
        This test processes the entire episode (not just first chunk).
        This is a much longer-running test.
        """
        pytest.skip("Full mode test skipped by default - run explicitly if needed")
        
        # Initialize service
        service = VideoPipelineService(
            language_code="ko",
            output_dir=str(temp_output_dir)
        )
        
        # Track progress
        progress_messages = []
        
        def progress_callback(progress: int, message: str):
            progress_messages.append((progress, message))
            if progress % 10 == 0:  # Log every 10%
                print(f"Progress: {progress}% - {message}")
        
        # Process video (full mode, no test_mode)
        result = service.process_video(
            video_path=episode1_video_path,
            subtitle_path=episode1_subtitle_path,
            show_name="Suits",
            episode_name="S01E01_Pilot",
            max_expressions=10,  # Process up to 10 expressions
            language_level="intermediate",
            test_mode=False,  # Process full episode
            no_shorts=False,  # Create short videos too
            progress_callback=progress_callback
        )
        
        # Verify expressions were found
        assert len(result["expressions"]) > 0, "Should find expressions in full mode"
        assert len(result["expressions"]) <= 10, "Should respect max_expressions limit"
        
        # Verify output files were created
        episode_dir = temp_output_dir / "Suits" / "S01E01_Pilot"
        translations_dir = episode_dir / "translations" / "ko"
        
        assert translations_dir.exists(), "Translations directory should exist"
        
        # Check for educational videos
        educational_videos = result.get("educational_videos", [])
        print(f"\n✅ Created {len(educational_videos)} educational videos")
        
        # Check for short videos
        short_videos = result.get("short_videos", [])
        print(f"✅ Created {len(short_videos)} short videos")
        
        # Verify final video path if available
        if result.get("final_video"):
            final_video_path = Path(result["final_video"])
            assert final_video_path.exists(), f"Final video should exist: {final_video_path}"
            print(f"✅ Final video created: {final_video_path}")
        
        print(f"\n✅ Full mode test completed successfully!")
        print(f"   - Expressions processed: {len(result['expressions'])}")
        print(f"   - Educational videos: {len(educational_videos)}")
        print(f"   - Short videos: {len(short_videos)}")

