"""
Unit tests for short video batching logic.

Tests the _create_batched_short_videos_with_max_duration() method
to ensure videos are properly batched according to max_duration constraints.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from langflix.main import LangFlixPipeline


class TestShortVideoBatching:
    """Test suite for short video batching logic"""
    
    @pytest.fixture
    def mock_video_editor(self):
        """Create a mock VideoEditor instance"""
        editor = Mock()
        editor.episode_name = "Test_Episode"
        editor.short_videos_dir = Path("/tmp/test_short_videos")
        editor.short_videos_dir.mkdir(parents=True, exist_ok=True)
        
        # Mock _create_video_batch to return a path
        def create_batch(video_paths, batch_number):
            batch_path = editor.short_videos_dir / f"short-form_Test_Episode_{batch_number:03d}.mkv"
            batch_path.touch()  # Create empty file for testing
            return str(batch_path)
        
        editor._create_video_batch = Mock(side_effect=create_batch)
        return editor
    
    @pytest.fixture
    def pipeline(self, mock_video_editor):
        """Create a LangFlixPipeline instance with mocked dependencies"""
        pipeline = LangFlixPipeline(
            subtitle_file="test.srt",
            video_dir="/tmp",
            output_dir="/tmp/test_output"
        )
        pipeline.video_editor = mock_video_editor
        pipeline.paths = {
            'episode_name': 'Test_Episode',
            'language': {
                'videos': Path("/tmp/test_output/ko/videos")
            }
        }
        return pipeline
    
    def test_basic_batching(self, pipeline):
        """Test basic batching with 4 expressions (20s, 30s, 50s, 30s) and 60s max_duration"""
        # Setup: 4 videos with durations 20s, 30s, 50s, 30s
        short_format_videos = [
            ("/tmp/video1.mkv", 20.0),
            ("/tmp/video2.mkv", 30.0),
            ("/tmp/video3.mkv", 50.0),
            ("/tmp/video4.mkv", 30.0),
        ]
        
        max_duration = 60.0
        
        # Execute
        batch_videos = pipeline._create_batched_short_videos_with_max_duration(
            short_format_videos, max_duration=max_duration
        )
        
        # Verify: Should create 3 batches
        # Batch 1: video1 (20s) + video2 (30s) = 50s
        # Batch 2: video3 (50s) = 50s
        # Batch 3: video4 (30s) = 30s
        assert len(batch_videos) == 3
        
        # Verify batch creation was called 3 times
        assert pipeline.video_editor._create_video_batch.call_count == 3
        
        # Verify batch compositions
        calls = pipeline.video_editor._create_video_batch.call_args_list
        assert len(calls[0][0][0]) == 2  # Batch 1: 2 videos
        assert len(calls[1][0][0]) == 1  # Batch 2: 1 video
        assert len(calls[2][0][0]) == 1  # Batch 3: 1 video
        
        # Verify specific videos in batches
        assert "/tmp/video1.mkv" in calls[0][0][0]
        assert "/tmp/video2.mkv" in calls[0][0][0]
        assert "/tmp/video3.mkv" in calls[1][0][0]
        assert "/tmp/video4.mkv" in calls[2][0][0]
    
    def test_single_expression_fits(self, pipeline):
        """Test single expression that fits within max_duration"""
        short_format_videos = [("/tmp/video1.mkv", 30.0)]
        max_duration = 60.0
        
        batch_videos = pipeline._create_batched_short_videos_with_max_duration(
            short_format_videos, max_duration=max_duration
        )
        
        assert len(batch_videos) == 1
        assert pipeline.video_editor._create_video_batch.call_count == 1
        calls = pipeline.video_editor._create_video_batch.call_args_list
        assert len(calls[0][0][0]) == 1
        assert "/tmp/video1.mkv" in calls[0][0][0]
    
    def test_single_expression_exceeds_max_duration(self, pipeline):
        """Test single expression that exceeds max_duration (should be dropped)"""
        short_format_videos = [("/tmp/video1.mkv", 100.0)]
        max_duration = 60.0
        
        batch_videos = pipeline._create_batched_short_videos_with_max_duration(
            short_format_videos, max_duration=max_duration
        )
        
        # Should create no batches (video was dropped)
        assert len(batch_videos) == 0
        assert pipeline.video_editor._create_video_batch.call_count == 0
    
    def test_all_expressions_fit_in_one_batch(self, pipeline):
        """Test all expressions fit in one batch"""
        short_format_videos = [
            ("/tmp/video1.mkv", 10.0),
            ("/tmp/video2.mkv", 15.0),
            ("/tmp/video3.mkv", 20.0),
        ]
        max_duration = 60.0
        
        batch_videos = pipeline._create_batched_short_videos_with_max_duration(
            short_format_videos, max_duration=max_duration
        )
        
        assert len(batch_videos) == 1
        assert pipeline.video_editor._create_video_batch.call_count == 1
        calls = pipeline.video_editor._create_video_batch.call_args_list
        assert len(calls[0][0][0]) == 3  # All 3 videos in one batch
    
    def test_each_expression_needs_own_batch(self, pipeline):
        """Test each expression needs its own batch"""
        short_format_videos = [
            ("/tmp/video1.mkv", 50.0),
            ("/tmp/video2.mkv", 55.0),
            ("/tmp/video3.mkv", 45.0),
        ]
        max_duration = 60.0
        
        batch_videos = pipeline._create_batched_short_videos_with_max_duration(
            short_format_videos, max_duration=max_duration
        )
        
        # Each video needs its own batch (50+55 > 60, 55+45 > 60)
        assert len(batch_videos) == 3
        assert pipeline.video_editor._create_video_batch.call_count == 3
        calls = pipeline.video_editor._create_video_batch.call_args_list
        assert len(calls[0][0][0]) == 1  # Batch 1: video1
        assert len(calls[1][0][0]) == 1  # Batch 2: video2
        assert len(calls[2][0][0]) == 1  # Batch 3: video3
    
    def test_empty_input(self, pipeline):
        """Test empty input list"""
        short_format_videos = []
        max_duration = 60.0
        
        batch_videos = pipeline._create_batched_short_videos_with_max_duration(
            short_format_videos, max_duration=max_duration
        )
        
        assert len(batch_videos) == 0
        assert pipeline.video_editor._create_video_batch.call_count == 0
    
    def test_expression_exact_max_duration(self, pipeline):
        """Test expression with duration exactly equal to max_duration"""
        short_format_videos = [("/tmp/video1.mkv", 60.0)]
        max_duration = 60.0
        
        batch_videos = pipeline._create_batched_short_videos_with_max_duration(
            short_format_videos, max_duration=max_duration
        )
        
        # Should be included (duration <= max_duration)
        assert len(batch_videos) == 1
        assert pipeline.video_editor._create_video_batch.call_count == 1
    
    def test_expression_exceeds_max_duration_by_one(self, pipeline):
        """Test expression that exceeds max_duration by 1 second (should be dropped)"""
        short_format_videos = [("/tmp/video1.mkv", 61.0)]
        max_duration = 60.0
        
        batch_videos = pipeline._create_batched_short_videos_with_max_duration(
            short_format_videos, max_duration=max_duration
        )
        
        # Should be dropped
        assert len(batch_videos) == 0
        assert pipeline.video_editor._create_video_batch.call_count == 0
    
    def test_multiple_small_expressions_exact_max_duration(self, pipeline):
        """Test multiple small expressions that sum to exactly max_duration"""
        short_format_videos = [
            ("/tmp/video1.mkv", 20.0),
            ("/tmp/video2.mkv", 20.0),
            ("/tmp/video3.mkv", 20.0),
        ]
        max_duration = 60.0
        
        batch_videos = pipeline._create_batched_short_videos_with_max_duration(
            short_format_videos, max_duration=max_duration
        )
        
        # All should fit in one batch (20+20+20 = 60)
        assert len(batch_videos) == 1
        assert pipeline.video_editor._create_video_batch.call_count == 1
        calls = pipeline.video_editor._create_video_batch.call_args_list
        assert len(calls[0][0][0]) == 3
    
    def test_multiple_small_expressions_exceed_max_duration_by_one(self, pipeline):
        """Test multiple small expressions that sum to max_duration + 1"""
        short_format_videos = [
            ("/tmp/video1.mkv", 20.0),
            ("/tmp/video2.mkv", 20.0),
            ("/tmp/video3.mkv", 21.0),  # Total: 61
        ]
        max_duration = 60.0
        
        batch_videos = pipeline._create_batched_short_videos_with_max_duration(
            short_format_videos, max_duration=max_duration
        )
        
        # First two should be in batch 1, third should start batch 2
        assert len(batch_videos) == 2
        assert pipeline.video_editor._create_video_batch.call_count == 2
        calls = pipeline.video_editor._create_video_batch.call_args_list
        assert len(calls[0][0][0]) == 2  # Batch 1: video1 + video2 (40s)
        assert len(calls[1][0][0]) == 1  # Batch 2: video3 (21s)
        assert "/tmp/video1.mkv" in calls[0][0][0]
        assert "/tmp/video2.mkv" in calls[0][0][0]
        assert "/tmp/video3.mkv" in calls[1][0][0]
    
    def test_real_world_scenario_10_expressions_180s(self, pipeline):
        """Test real-world scenario: 10 expressions with varying durations and 180s max_duration"""
        short_format_videos = [
            ("/tmp/video1.mkv", 25.0),
            ("/tmp/video2.mkv", 30.0),
            ("/tmp/video3.mkv", 45.0),
            ("/tmp/video4.mkv", 20.0),
            ("/tmp/video5.mkv", 35.0),
            ("/tmp/video6.mkv", 40.0),
            ("/tmp/video7.mkv", 28.0),
            ("/tmp/video8.mkv", 32.0),
            ("/tmp/video9.mkv", 22.0),
            ("/tmp/video10.mkv", 38.0),
        ]
        max_duration = 180.0
        
        batch_videos = pipeline._create_batched_short_videos_with_max_duration(
            short_format_videos, max_duration=max_duration
        )
        
        # Verify all videos are included (none exceed 180s individually)
        total_videos_in_batches = sum(
            len(call[0][0]) for call in pipeline.video_editor._create_video_batch.call_args_list
        )
        assert total_videos_in_batches == 10  # All videos should be included
        
        # Verify batches are created
        assert len(batch_videos) > 0
        assert len(batch_videos) <= 10  # At most one batch per video
    
    def test_real_world_scenario_5_expressions_60s(self, pipeline):
        """Test real-world scenario: 5 expressions with varying durations and 60s max_duration"""
        short_format_videos = [
            ("/tmp/video1.mkv", 15.0),
            ("/tmp/video2.mkv", 25.0),
            ("/tmp/video3.mkv", 30.0),
            ("/tmp/video4.mkv", 20.0),
            ("/tmp/video5.mkv", 35.0),
        ]
        max_duration = 60.0
        
        batch_videos = pipeline._create_batched_short_videos_with_max_duration(
            short_format_videos, max_duration=max_duration
        )
        
        # Verify all videos are included
        total_videos_in_batches = sum(
            len(call[0][0]) for call in pipeline.video_editor._create_video_batch.call_args_list
        )
        assert total_videos_in_batches == 5
        
        # Expected batching:
        # Batch 1: video1 (15) + video2 (25) + video4 (20) = 60s
        # Batch 2: video3 (30) + video5 (35) = 65s > 60, so separate
        # Batch 3: video5 (35)
        # Actually, let's trace:
        # video1 (15): batch 1, duration = 15
        # video2 (25): batch 1, duration = 40
        # video3 (30): 40 + 30 = 70 > 60, so batch 1 done, start batch 2 with video3
        # video4 (20): batch 2, duration = 50
        # video5 (35): 50 + 35 = 85 > 60, so batch 2 done, start batch 3 with video5
        
        assert len(batch_videos) == 3
        calls = pipeline.video_editor._create_video_batch.call_args_list
        assert len(calls[0][0][0]) == 2  # Batch 1: video1 + video2
        assert len(calls[1][0][0]) == 2  # Batch 2: video3 + video4
        assert len(calls[2][0][0]) == 1  # Batch 3: video5
    
    def test_mixed_valid_and_invalid_durations(self, pipeline):
        """Test mix of valid and invalid (exceeding max_duration) videos"""
        short_format_videos = [
            ("/tmp/video1.mkv", 20.0),   # Valid
            ("/tmp/video2.mkv", 100.0),  # Exceeds 60s, should be dropped
            ("/tmp/video3.mkv", 30.0),   # Valid
            ("/tmp/video4.mkv", 40.0),   # Valid
        ]
        max_duration = 60.0
        
        batch_videos = pipeline._create_batched_short_videos_with_max_duration(
            short_format_videos, max_duration=max_duration
        )
        
        # video2 should be dropped, others should be batched
        total_videos_in_batches = sum(
            len(call[0][0]) for call in pipeline.video_editor._create_video_batch.call_args_list
        )
        assert total_videos_in_batches == 3  # video1, video3, video4
        
        # Verify video2 is not in any batch
        all_videos_in_batches = []
        for call in pipeline.video_editor._create_video_batch.call_args_list:
            all_videos_in_batches.extend(call[0][0])
        assert "/tmp/video2.mkv" not in all_videos_in_batches
    
    def test_batch_numbering(self, pipeline):
        """Test that batch numbers are sequential"""
        short_format_videos = [
            ("/tmp/video1.mkv", 20.0),
            ("/tmp/video2.mkv", 30.0),
            ("/tmp/video3.mkv", 50.0),
            ("/tmp/video4.mkv", 30.0),
        ]
        max_duration = 60.0
        
        batch_videos = pipeline._create_batched_short_videos_with_max_duration(
            short_format_videos, max_duration=max_duration
        )
        
        # Verify batch numbers are sequential (1, 2, 3)
        calls = pipeline.video_editor._create_video_batch.call_args_list
        assert calls[0][0][1] == 1  # First batch: number 1
        assert calls[1][0][1] == 2  # Second batch: number 2
        assert calls[2][0][1] == 3  # Third batch: number 3

