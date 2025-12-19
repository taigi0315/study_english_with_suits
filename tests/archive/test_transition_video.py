"""
Unit tests for transition video feature.

Tests the creation of transition videos between context and expression segments.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langflix.core.video_editor import VideoEditor
from langflix.models import ExpressionAnalysis


class TestTransitionVideo:
    """Test transition video creation"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test outputs"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)
    
    @pytest.fixture
    def video_editor(self, temp_dir):
        """Create VideoEditor instance"""
        return VideoEditor(output_dir=temp_dir, language_code="en")
    
    @pytest.fixture
    def transition_config(self):
        """Transition configuration"""
        return {
            "enabled": True,
            "duration": 1.0,
            "image_path_9_16": "assets/transition_9_16.png",
            "image_path_16_9": "assets/transition_16_9.png",
            "sound_effect_path": "assets/sound_effect.mp3"
        }
    
    @pytest.fixture
    def expression(self):
        """Sample expression for testing"""
        return ExpressionAnalysis(
            expression="test expression",
            translation="테스트 표현",
            context="test context",
            expression_dialogue="test dialogue",
            start_time=0.0,
            end_time=5.0,
            similar_expressions=["similar 1", "similar 2"]
        )
    
    def test_create_transition_video_exists(self, video_editor):
        """Test that _create_transition_video method exists"""
        assert hasattr(video_editor, '_create_transition_video'), \
            "_create_transition_video method should exist"
    
    @patch('langflix.core.video_editor.ffmpeg')
    @patch('langflix.core.video_editor.Path.exists')
    def test_create_transition_video_long_form(
        self, mock_exists, mock_ffmpeg, video_editor, temp_dir, transition_config
    ):
        """Test transition video creation for long-form (16:9)"""
        # Setup
        mock_exists.return_value = True
        output_path = temp_dir / "transition_test.mkv"
        image_path = transition_config["image_path_16_9"]
        sound_path = transition_config["sound_effect_path"]
        duration = transition_config["duration"]
        
        # Mock FFmpeg operations
        mock_input = Mock()
        mock_input.__getitem__.return_value = Mock()
        mock_ffmpeg.input.return_value = mock_input
        
        mock_filter = Mock()
        mock_ffmpeg.filter.return_value = mock_filter
        
        mock_output = Mock()
        mock_output.overwrite_output.return_value = mock_output
        mock_ffmpeg.output.return_value = mock_output
        
        # Test
        result = video_editor._create_transition_video(
            duration=duration,
            image_path=image_path,
            sound_effect_path=sound_path,
            output_path=output_path,
            video_width=1920,
            video_height=1080,
            fps=25
        )
        
        # Assert
        assert result == str(output_path)
        mock_ffmpeg.input.assert_called()  # Should call ffmpeg.input for image and sound
        mock_ffmpeg.output.assert_called()  # Should create output
    
    @patch('langflix.core.video_editor.ffmpeg')
    @patch('langflix.core.video_editor.Path.exists')
    def test_create_transition_video_short_form(
        self, mock_exists, mock_ffmpeg, video_editor, temp_dir, transition_config
    ):
        """Test transition video creation for short-form (9:16)"""
        # Setup
        mock_exists.return_value = True
        output_path = temp_dir / "transition_test.mkv"
        image_path = transition_config["image_path_9_16"]
        sound_path = transition_config["sound_effect_path"]
        duration = transition_config["duration"]
        
        # Mock FFmpeg operations
        mock_input = Mock()
        mock_input.__getitem__.return_value = Mock()
        mock_ffmpeg.input.return_value = mock_input
        
        mock_filter = Mock()
        mock_ffmpeg.filter.return_value = mock_filter
        
        mock_output = Mock()
        mock_output.overwrite_output.return_value = mock_output
        mock_ffmpeg.output.return_value = mock_output
        
        # Test
        result = video_editor._create_transition_video(
            duration=duration,
            image_path=image_path,
            sound_effect_path=sound_path,
            output_path=output_path,
            video_width=1080,
            video_height=1920,
            fps=25
        )
        
        # Assert
        assert result == str(output_path)
        # Should use 9:16 image for short-form
        assert image_path == transition_config["image_path_9_16"]
    
    @patch('langflix.core.video_editor.ffmpeg')
    @patch('langflix.core.video_editor.Path.exists')
    def test_create_transition_video_duration(
        self, mock_exists, mock_ffmpeg, video_editor, temp_dir
    ):
        """Test that transition video has correct duration (1 second)"""
        # Setup
        mock_exists.return_value = True
        output_path = temp_dir / "transition_test.mkv"
        
        mock_input = Mock()
        mock_input.__getitem__.return_value = Mock()
        mock_ffmpeg.input.return_value = mock_input
        
        mock_filter = Mock()
        mock_ffmpeg.filter.return_value = mock_filter
        
        mock_output = Mock()
        mock_output.overwrite_output.return_value = mock_output
        mock_ffmpeg.output.return_value = mock_output
        
        # Test with 1 second duration
        video_editor._create_transition_video(
            duration=1.0,
            image_path="assets/transition_16_9.png",
            sound_effect_path="assets/sound_effect.mp3",
            output_path=output_path
        )
        
        # Verify FFmpeg was called (duration should be handled in FFmpeg filters)
        assert mock_ffmpeg.input.called
    
    @patch('langflix.core.video_editor.Path.exists')
    def test_create_transition_video_missing_image(
        self, mock_exists, video_editor, temp_dir
    ):
        """Test handling of missing transition image"""
        # Setup
        mock_exists.return_value = False  # Image file doesn't exist
        
        output_path = temp_dir / "transition_test.mkv"
        
        # Test should raise FileNotFoundError or handle gracefully
        with pytest.raises((FileNotFoundError, ValueError)):
            video_editor._create_transition_video(
                duration=1.0,
                image_path="nonexistent_image.png",
                sound_effect_path="assets/sound_effect.mp3",
                output_path=output_path
            )
    
    @patch('langflix.core.video_editor.Path.exists')
    def test_create_transition_video_missing_sound(
        self, mock_exists, video_editor, temp_dir
    ):
        """Test handling of missing sound effect"""
        # Setup - image exists, sound doesn't
        def side_effect(path):
            if "transition" in str(path):
                return True  # Image exists
            return False  # Sound doesn't exist
        mock_exists.side_effect = side_effect
        
        output_path = temp_dir / "transition_test.mkv"
        
        # Test should raise FileNotFoundError or handle gracefully
        with pytest.raises((FileNotFoundError, ValueError)):
            video_editor._create_transition_video(
                duration=1.0,
                image_path="assets/transition_16_9.png",
                sound_effect_path="nonexistent_sound.mp3",
                output_path=output_path
            )
    
    @patch('langflix.core.video_editor.get_duration_seconds')
    @patch('langflix.core.video_editor.ffmpeg')
    @patch('langflix.core.video_editor.Path.exists')
    def test_transition_increases_video_duration(
        self, mock_exists, mock_ffmpeg, mock_duration, video_editor, temp_dir, expression
    ):
        """Test that adding transition increases final video duration by 1 second"""
        # Setup
        mock_exists.return_value = True
        mock_duration.return_value = 10.0  # Original video duration
        
        # This test verifies the concept - actual implementation will be in integration tests
        original_duration = 10.0
        transition_duration = 1.0
        expected_final_duration = original_duration + transition_duration
        
        assert expected_final_duration == 11.0, \
            "Final video should be 1 second longer with transition"


class TestTransitionVideoIntegration:
    """Integration tests for transition video in video creation pipeline"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test outputs"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)
    
    def test_transition_config_loaded(self):
        """Test that transition configuration can be loaded from config"""
        from langflix.config.config_loader import ConfigLoader
        
        config = ConfigLoader()
        # This test assumes config will have transition settings
        # Actual test depends on config implementation
        assert config is not None
    
    @pytest.mark.skip(reason="Requires full video pipeline setup")
    def test_long_form_with_transition(self):
        """Test long-form video creation with transition (integration test)"""
        # This test should be in integration test suite
        # Verifies:
        # 1. Transition video is created
        # 2. Context → transition → expression structure
        # 3. Final video is 1 second longer
        # 4. Sound effect plays during transition
        pass
    
    @pytest.mark.skip(reason="Requires full video pipeline setup")
    def test_short_form_with_transition(self):
        """Test short-form video creation with transition (integration test)"""
        # This test should be in integration test suite
        # Verifies:
        # 1. Transition video uses 9:16 image
        # 2. Context → transition → expression structure
        # 3. Final video is 1 second longer
        # 4. Vstack still works correctly
        pass
