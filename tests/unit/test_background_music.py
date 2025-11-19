"""
Unit tests for background music functionality
"""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from langflix.core.models import ExpressionAnalysis
from langflix.core.video_editor import VideoEditor
from langflix.config.config_loader import ConfigLoader


class TestBackgroundMusicConfiguration:
    """Test background music configuration loading and validation"""

    def test_background_music_config_exists(self):
        """Test that background_music configuration section exists"""
        config_loader = ConfigLoader()
        bg_music_config = config_loader.config.get('background_music')

        assert bg_music_config is not None
        assert isinstance(bg_music_config, dict)

    def test_background_music_enabled_by_default(self):
        """Test that background music is enabled by default"""
        config_loader = ConfigLoader()
        bg_music_config = config_loader.config.get('background_music', {})

        assert bg_music_config.get('enabled') is True

    def test_background_music_volume_setting(self):
        """Test that volume setting exists and is reasonable"""
        config_loader = ConfigLoader()
        bg_music_config = config_loader.config.get('background_music', {})
        volume = bg_music_config.get('volume', 0)

        assert volume > 0
        assert volume <= 1.0
        # Default should be 20%
        assert volume == 0.20

    def test_background_music_fade_durations(self):
        """Test fade in/out duration settings"""
        config_loader = ConfigLoader()
        bg_music_config = config_loader.config.get('background_music', {})

        fade_in = bg_music_config.get('fade_in_duration')
        fade_out = bg_music_config.get('fade_out_duration')

        assert fade_in is not None
        assert fade_out is not None
        assert fade_in >= 0
        assert fade_out >= 0

    def test_background_music_library_exists(self):
        """Test that music library is defined in config"""
        config_loader = ConfigLoader()
        bg_music_config = config_loader.config.get('background_music', {})
        library = bg_music_config.get('library', {})

        assert library is not None
        assert isinstance(library, dict)
        assert len(library) == 12  # Should have all 12 categories

    def test_all_12_music_categories_defined(self):
        """Test that all 12 music categories are defined"""
        expected_categories = [
            'comedic_funny',
            'tense_suspenseful',
            'dramatic_serious',
            'romantic_tender',
            'action_energetic',
            'melancholic_sad',
            'mysterious_intriguing',
            'triumphant_victorious',
            'confrontational_angry',
            'inspirational_uplifting',
            'awkward_uncomfortable',
            'reflective_contemplative'
        ]

        config_loader = ConfigLoader()
        bg_music_config = config_loader.config.get('background_music', {})
        library = bg_music_config.get('library', {})

        for category in expected_categories:
            assert category in library
            assert 'file' in library[category]
            assert 'description' in library[category]

    def test_music_files_exist(self):
        """Test that all configured music files actually exist"""
        config_loader = ConfigLoader()
        bg_music_config = config_loader.config.get('background_music', {})
        library = bg_music_config.get('library', {})
        music_dir = bg_music_config.get('music_directory', 'assets/background_music')

        for music_id, music_info in library.items():
            filename = music_info.get('file')
            filepath = Path(music_dir) / filename
            assert filepath.exists(), f"Music file not found: {filepath}"


class TestExpressionAnalysisModel:
    """Test ExpressionAnalysis model for background music fields"""

    def test_expression_has_background_music_fields(self):
        """Test that ExpressionAnalysis model has background_music fields"""
        expression = ExpressionAnalysis(
            dialogues=["Test dialogue"],
            translation=["테스트 대화"],
            expression_dialogue="Test dialogue",
            expression_dialogue_translation="테스트 대화",
            expression="test",
            expression_translation="테스트",
            context_start_time="00:00:00,000",
            context_end_time="00:00:05,000",
            similar_expressions=["test phrase"],
            background_music_id="comedic_funny",
            background_music_reasoning="This is a funny scene"
        )

        assert hasattr(expression, 'background_music_id')
        assert hasattr(expression, 'background_music_reasoning')
        assert expression.background_music_id == "comedic_funny"
        assert expression.background_music_reasoning == "This is a funny scene"

    def test_expression_background_music_fields_optional(self):
        """Test that background_music fields are optional"""
        expression = ExpressionAnalysis(
            dialogues=["Test dialogue"],
            translation=["테스트 대화"],
            expression_dialogue="Test dialogue",
            expression_dialogue_translation="테스트 대화",
            expression="test",
            expression_translation="테스트",
            context_start_time="00:00:00,000",
            context_end_time="00:00:05,000",
            similar_expressions=["test phrase"]
        )

        assert expression.background_music_id is None
        assert expression.background_music_reasoning is None


class TestVideoEditorBackgroundMusic:
    """Test VideoEditor background music functionality"""

    @pytest.fixture
    def video_editor(self, tmp_path):
        """Create VideoEditor instance for testing"""
        return VideoEditor(output_dir=str(tmp_path))

    @pytest.fixture
    def sample_expression(self):
        """Create sample expression with background music"""
        return ExpressionAnalysis(
            dialogues=["This is hilarious!"],
            translation=["이건 정말 웃겨!"],
            expression_dialogue="This is hilarious!",
            expression_dialogue_translation="이건 정말 웃겨!",
            expression="hilarious",
            expression_translation="웃긴",
            context_start_time="00:00:00,000",
            context_end_time="00:00:05,000",
            similar_expressions=["funny", "amusing"],
            background_music_id="comedic_funny",
            background_music_reasoning="Humorous scene with laughter"
        )

    def test_apply_background_music_method_exists(self, video_editor):
        """Test that _apply_background_music method exists"""
        assert hasattr(video_editor, '_apply_background_music')
        assert callable(getattr(video_editor, '_apply_background_music'))

    @patch('langflix.settings.config')
    def test_apply_background_music_disabled(self, mock_config, video_editor, sample_expression, tmp_path):
        """Test that background music is skipped when disabled"""
        # Mock config to disable background music
        mock_config.get.return_value = {'enabled': False}

        input_video = tmp_path / "input.mp4"
        output_video = tmp_path / "output.mp4"
        input_video.touch()  # Create dummy file

        with patch('shutil.copy') as mock_copy:
            result = video_editor._apply_background_music(
                str(input_video),
                sample_expression,
                str(output_video)
            )

            # Should copy file without processing
            mock_copy.assert_called_once()
            assert result == str(output_video)

    @patch('langflix.settings.config')
    def test_apply_background_music_no_music_id(self, mock_config, video_editor, tmp_path):
        """Test that background music is skipped when no music_id provided"""
        mock_config.get.return_value = {'enabled': True}

        expression_no_music = ExpressionAnalysis(
            dialogues=["Test"],
            translation=["테스트"],
            expression_dialogue="Test",
            expression_dialogue_translation="테스트",
            expression="test",
            expression_translation="테스트",
            context_start_time="00:00:00,000",
            context_end_time="00:00:05,000",
            similar_expressions=["test"]
            # No background_music_id
        )

        input_video = tmp_path / "input.mp4"
        output_video = tmp_path / "output.mp4"
        input_video.touch()

        with patch('shutil.copy') as mock_copy:
            result = video_editor._apply_background_music(
                str(input_video),
                expression_no_music,
                str(output_video)
            )

            mock_copy.assert_called_once()

    @patch('langflix.settings.config')
    def test_apply_background_music_invalid_music_id(self, mock_config, video_editor, tmp_path):
        """Test that background music is skipped for invalid music_id"""
        mock_config.get.return_value = {
            'enabled': True,
            'library': {
                'comedic_funny': {'file': 'comedic_funny.mp3'}
            }
        }

        expression_invalid_music = ExpressionAnalysis(
            dialogues=["Test"],
            translation=["테스트"],
            expression_dialogue="Test",
            expression_dialogue_translation="테스트",
            expression="test",
            expression_translation="테스트",
            context_start_time="00:00:00,000",
            context_end_time="00:00:05,000",
            similar_expressions=["test"],
            background_music_id="invalid_music_category"  # Invalid ID
        )

        input_video = tmp_path / "input.mp4"
        output_video = tmp_path / "output.mp4"
        input_video.touch()

        with patch('shutil.copy') as mock_copy:
            result = video_editor._apply_background_music(
                str(input_video),
                expression_invalid_music,
                str(output_video)
            )

            # Should skip and copy
            mock_copy.assert_called_once()


class TestBackgroundMusicFileProperties:
    """Test properties of actual music files"""

    @pytest.mark.parametrize("music_id", [
        'comedic_funny',
        'tense_suspenseful',
        'dramatic_serious',
        'romantic_tender',
        'action_energetic',
        'melancholic_sad',
        'mysterious_intriguing',
        'triumphant_victorious',
        'confrontational_angry',
        'inspirational_uplifting',
        'awkward_uncomfortable',
        'reflective_contemplative'
    ])
    def test_music_file_duration_around_60_seconds(self, music_id):
        """Test that music files are approximately 60 seconds"""
        import subprocess

        config_loader = ConfigLoader()
        bg_music_config = config_loader.config.get('background_music', {})
        library = bg_music_config.get('library', {})
        music_dir = bg_music_config.get('music_directory', 'assets/background_music')

        filename = library[music_id]['file']
        filepath = Path(music_dir) / filename

        # Get duration using ffprobe
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', str(filepath)],
            capture_output=True,
            text=True
        )

        duration = float(result.stdout.strip())

        # Should be approximately 60 seconds (allow 55-65 second range)
        assert 55 <= duration <= 65, f"{music_id} duration is {duration}s, expected ~60s"

    @pytest.mark.parametrize("music_id", [
        'comedic_funny',
        'tense_suspenseful',
        'dramatic_serious',
        'romantic_tender',
        'action_energetic',
        'melancholic_sad',
        'mysterious_intriguing',
        'triumphant_victorious',
        'confrontational_angry',
        'inspirational_uplifting',
        'awkward_uncomfortable',
        'reflective_contemplative'
    ])
    def test_music_file_has_audio_stream(self, music_id):
        """Test that music files have valid audio streams"""
        import subprocess

        config_loader = ConfigLoader()
        bg_music_config = config_loader.config.get('background_music', {})
        library = bg_music_config.get('library', {})
        music_dir = bg_music_config.get('music_directory', 'assets/background_music')

        filename = library[music_id]['file']
        filepath = Path(music_dir) / filename

        # Check for audio stream
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'a:0',
             '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', str(filepath)],
            capture_output=True,
            text=True
        )

        assert result.stdout.strip() == 'audio', f"{music_id} does not have valid audio stream"

    def test_all_music_files_same_size_roughly(self):
        """Test that all music files are roughly the same size (indicating similar quality/duration)"""
        config_loader = ConfigLoader()
        bg_music_config = config_loader.config.get('background_music', {})
        library = bg_music_config.get('library', {})
        music_dir = bg_music_config.get('music_directory', 'assets/background_music')

        file_sizes = []
        for music_id, music_info in library.items():
            filename = music_info['file']
            filepath = Path(music_dir) / filename
            file_size = filepath.stat().st_size
            file_sizes.append(file_size)

        # Check that all files are within 20% of average size
        avg_size = sum(file_sizes) / len(file_sizes)
        for size in file_sizes:
            assert 0.8 * avg_size <= size <= 1.2 * avg_size, \
                f"File size {size} too different from average {avg_size}"


class TestBackgroundMusicIntegration:
    """Integration tests for background music in video pipeline"""

    def test_background_music_config_matches_prompt(self):
        """Test that config music categories match those in LLM prompt"""
        # Read prompt template v6 (which has background music support)
        prompt_path = Path("langflix/templates/expression_analysis_prompt_v6.txt")
        assert prompt_path.exists(), "Template v6 with background music support not found"

        with open(prompt_path, 'r') as f:
            prompt_content = f.read()

        # Check that all 12 categories are mentioned in prompt
        config_loader = ConfigLoader()
        bg_music_config = config_loader.config.get('background_music', {})
        library = bg_music_config.get('library', {})

        for music_id in library.keys():
            assert music_id in prompt_content, \
                f"Music category '{music_id}' not found in LLM prompt v6"

    def test_database_model_has_background_music_fields(self):
        """Test that database Expression model has background_music fields"""
        from langflix.db.models import Expression

        # Check that Expression model has the fields
        assert hasattr(Expression, 'background_music_id')
        assert hasattr(Expression, 'background_music_reasoning')
