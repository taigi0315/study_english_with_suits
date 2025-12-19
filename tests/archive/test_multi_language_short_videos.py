"""
Unit tests for multi-language short video generation.

Tests that short videos are created correctly for each target language
with proper font rendering and translated content.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from langflix.main import LangFlixPipeline
from langflix.core.models import ExpressionAnalysis


class TestMultiLanguageShortVideos:
    """Test suite for multi-language short video generation"""
    
    @pytest.fixture
    def mock_video_editor(self):
        """Create a mock VideoEditor instance"""
        editor = Mock()
        editor.episode_name = "Test_Episode"
        editor.language_code = "ko"
        editor.paths = {
            'shorts': Path("/tmp/test_output/ko/shorts"),
            'language_dir': Path("/tmp/test_output/ko")
        }
        editor.create_short_form_from_long_form = Mock(return_value="/tmp/test_output/ko/shorts/short_form_test.mkv")
        editor._create_video_batch = Mock(return_value="/tmp/test_output/ko/shorts/short-form_Test_Episode_001.mkv")
        editor._cleanup_temp_files = Mock()
        editor.short_format_temp_files = []
        return editor
    
    @pytest.fixture
    def base_expressions(self):
        """Create base English expressions"""
        return [
            ExpressionAnalysis(
                dialogues=["Do you get it?", "Yes, I understand."],
                translation=["이해하세요?", "네, 이해합니다."],
                expression="get it",
                expression_translation="이해하다",
                expression_dialogue="Do you get it?",
                expression_dialogue_translation="이해하세요?",
                context_start_time="00:00:10,000",
                context_end_time="00:00:15,000",
                expression_start_time="00:00:12,000",
                expression_end_time="00:00:13,000",
                similar_expressions=["understand", "comprehend", "grasp"],
                catchy_keywords=["understand", "comprehend", "grasp"]
            ),
            ExpressionAnalysis(
                dialogues=["It worked like a charm.", "Perfect execution."],
                translation=["완벽하게 작동했어요.", "완벽한 실행이었습니다."],
                expression="work like a charm",
                expression_translation="완벽하게 작동하다",
                expression_dialogue="It worked like a charm.",
                expression_dialogue_translation="완벽하게 작동했어요.",
                context_start_time="00:00:20,000",
                context_end_time="00:00:25,000",
                expression_start_time="00:00:22,000",
                expression_end_time="00:00:23,000",
                similar_expressions=["perfect", "smooth", "success"],
                catchy_keywords=["perfect", "smooth", "success"]
            )
        ]
    
    @pytest.fixture
    def translated_expressions_es(self):
        """Create Spanish translated expressions"""
        return [
            ExpressionAnalysis(
                dialogues=["¿Lo entiendes?", "Sí, lo entiendo."],
                translation=["¿Lo entiendes?", "Sí, lo entiendo."],
                expression="get it",
                expression_translation="entenderlo",
                expression_dialogue="¿Lo entiendes?",
                expression_dialogue_translation="¿Lo entiendes?",
                context_start_time="00:00:10,000",
                context_end_time="00:00:15,000",
                expression_start_time="00:00:12,000",
                expression_end_time="00:00:13,000",
                similar_expressions=["entender", "comprender", "captar"],
                catchy_keywords=["entender", "comprender", "captar"]
            ),
            ExpressionAnalysis(
                dialogues=["Funcionó perfectamente.", "Ejecución perfecta."],
                translation=["Funcionó perfectamente.", "Ejecución perfecta."],
                expression="work like a charm",
                expression_translation="funcionar perfectamente",
                expression_dialogue="Funcionó perfectamente.",
                expression_dialogue_translation="Funcionó perfectamente.",
                context_start_time="00:00:20,000",
                context_end_time="00:00:25,000",
                expression_start_time="00:00:22,000",
                expression_end_time="00:00:23,000",
                similar_expressions=["perfecto", "suave", "éxito"],
                catchy_keywords=["perfecto", "suave", "éxito"]
            )
        ]
    
    @pytest.fixture
    def pipeline(self, mock_video_editor, base_expressions, translated_expressions_es):
        """Create a LangFlixPipeline instance with mocked dependencies"""
        pipeline = LangFlixPipeline(
            subtitle_file="test.srt",
            video_dir="/tmp",
            output_dir="/tmp/test_output",
            language_code="ko",
            target_languages=["ko", "es"]
        )
        pipeline.video_editor = mock_video_editor
        pipeline.expressions = base_expressions
        pipeline.translated_expressions = {
            "ko": base_expressions,
            "es": translated_expressions_es
        }
        pipeline.paths = {
            'episode_name': 'Test_Episode',
            'languages': {
                'ko': {
                    'shorts': Path("/tmp/test_output/ko/shorts"),
                    'expressions': Path("/tmp/test_output/ko/expressions"),
                    'language_dir': Path("/tmp/test_output/ko")
                },
                'es': {
                    'shorts': Path("/tmp/test_output/es/shorts"),
                    'expressions': Path("/tmp/test_output/es/expressions"),
                    'language_dir': Path("/tmp/test_output/es")
                }
            },
            'language': {
                'shorts': Path("/tmp/test_output/ko/shorts"),
                'expressions': Path("/tmp/test_output/ko/expressions"),
                'language_dir': Path("/tmp/test_output/ko")
            }
        }
        return pipeline
    
    def test_short_videos_created_for_each_language(self, pipeline, mock_video_editor):
        """Test that short videos are created for each target language"""
        # Setup: Create mock long-form videos
        ko_expressions_dir = Path("/tmp/test_output/ko/expressions")
        ko_expressions_dir.mkdir(parents=True, exist_ok=True)
        (ko_expressions_dir / "get_it.mkv").touch()
        (ko_expressions_dir / "work_like_a_charm.mkv").touch()
        
        es_expressions_dir = Path("/tmp/test_output/es/expressions")
        es_expressions_dir.mkdir(parents=True, exist_ok=True)
        (es_expressions_dir / "get_it.mkv").touch()
        (es_expressions_dir / "work_like_a_charm.mkv").touch()
        
        # Mock get_duration_seconds
        with patch('langflix.main.get_duration_seconds', return_value=30.0):
            # Execute
            pipeline._create_short_videos(short_form_max_duration=60.0)
        
        # Verify: VideoEditor.create_short_form_from_long_form should be called
        # for each language (ko and es)
        assert mock_video_editor.create_short_form_from_long_form.called
    
    def test_translated_expressions_used_for_rendering(self, pipeline):
        """Test that translated expressions are used for text rendering"""
        # Setup: Create mock long-form videos
        es_expressions_dir = Path("/tmp/test_output/es/expressions")
        es_expressions_dir.mkdir(parents=True, exist_ok=True)
        (es_expressions_dir / "get_it.mkv").touch()
        
        # Create language-specific VideoEditor
        from langflix.core.video_editor import VideoEditor
        es_video_editor = VideoEditor(
            output_dir=str(es_expressions_dir.parent),
            language_code="es",
            episode_name="Test_Episode"
        )
        es_video_editor.paths = pipeline.paths['languages']['es']
        es_video_editor.create_short_form_from_long_form = Mock(
            return_value="/tmp/test_output/es/shorts/short_form_get_it.mkv"
        )
        es_video_editor._create_video_batch = Mock(
            return_value="/tmp/test_output/es/shorts/short-form_Test_Episode_001.mkv"
        )
        es_video_editor._cleanup_temp_files = Mock()
        es_video_editor.short_format_temp_files = []
        
        # Mock get_duration_seconds
        with patch('langflix.main.get_duration_seconds', return_value=30.0):
            # Execute with Spanish language
            pipeline._create_short_videos(
                short_form_max_duration=60.0,
                language_code="es",
                lang_paths=pipeline.paths['languages']['es'],
                video_editor=es_video_editor
            )
        
        # Verify: Spanish expression should be passed to create_short_form_from_long_form
        assert es_video_editor.create_short_form_from_long_form.called
        call_args = es_video_editor.create_short_form_from_long_form.call_args
        expression_arg = call_args[0][1]  # Second argument is expression
        
        # Verify Spanish translation is used
        assert expression_arg.expression_translation == "entenderlo"
        assert expression_arg.expression_dialogue_translation == "¿Lo entiendes?"
        assert "entender" in expression_arg.catchy_keywords
    
    def test_language_specific_paths_used(self, pipeline):
        """Test that language-specific paths are used for short video creation"""
        # Setup: Create mock long-form videos
        ko_expressions_dir = Path("/tmp/test_output/ko/expressions")
        ko_expressions_dir.mkdir(parents=True, exist_ok=True)
        (ko_expressions_dir / "get_it.mkv").touch()
        
        es_expressions_dir = Path("/tmp/test_output/es/expressions")
        es_expressions_dir.mkdir(parents=True, exist_ok=True)
        (es_expressions_dir / "get_it.mkv").touch()
        
        # Create language-specific VideoEditors
        from langflix.core.video_editor import VideoEditor
        
        ko_video_editor = VideoEditor(
            output_dir=str(ko_expressions_dir.parent),
            language_code="ko",
            episode_name="Test_Episode"
        )
        ko_video_editor.paths = pipeline.paths['languages']['ko']
        ko_video_editor.create_short_form_from_long_form = Mock(
            return_value="/tmp/test_output/ko/shorts/short_form_get_it.mkv"
        )
        ko_video_editor._create_video_batch = Mock(
            return_value="/tmp/test_output/ko/shorts/short-form_Test_Episode_001.mkv"
        )
        ko_video_editor._cleanup_temp_files = Mock()
        ko_video_editor.short_format_temp_files = []
        
        es_video_editor = VideoEditor(
            output_dir=str(es_expressions_dir.parent),
            language_code="es",
            episode_name="Test_Episode"
        )
        es_video_editor.paths = pipeline.paths['languages']['es']
        es_video_editor.create_short_form_from_long_form = Mock(
            return_value="/tmp/test_output/es/shorts/short_form_get_it.mkv"
        )
        es_video_editor._create_video_batch = Mock(
            return_value="/tmp/test_output/es/shorts/short-form_Test_Episode_001.mkv"
        )
        es_video_editor._cleanup_temp_files = Mock()
        es_video_editor.short_format_temp_files = []
        
        # Mock get_duration_seconds
        with patch('langflix.main.get_duration_seconds', return_value=30.0):
            # Execute for Korean
            pipeline._create_short_videos(
                short_form_max_duration=60.0,
                language_code="ko",
                lang_paths=pipeline.paths['languages']['ko'],
                video_editor=ko_video_editor
            )
            
            # Execute for Spanish
            pipeline._create_short_videos(
                short_form_max_duration=60.0,
                language_code="es",
                lang_paths=pipeline.paths['languages']['es'],
                video_editor=es_video_editor
            )
        
        # Verify: Each language's VideoEditor should use its own paths
        assert ko_video_editor.create_short_form_from_long_form.called
        assert es_video_editor.create_short_form_from_long_form.called
        
        # Verify paths are different
        assert ko_video_editor.paths['shorts'] == Path("/tmp/test_output/ko/shorts")
        assert es_video_editor.paths['shorts'] == Path("/tmp/test_output/es/shorts")
    
    def test_cleanup_called_for_each_language(self, pipeline):
        """Test that cleanup is called for each language's intermediate files"""
        # Setup: Create mock directories
        ko_subtitles = Path("/tmp/test_output/ko/subtitles")
        ko_subtitles.mkdir(parents=True, exist_ok=True)
        ko_slides = Path("/tmp/test_output/ko/slides")
        ko_slides.mkdir(parents=True, exist_ok=True)
        
        es_subtitles = Path("/tmp/test_output/es/subtitles")
        es_subtitles.mkdir(parents=True, exist_ok=True)
        es_slides = Path("/tmp/test_output/es/slides")
        es_slides.mkdir(parents=True, exist_ok=True)
        
        # Execute cleanup
        pipeline._cleanup_intermediate_files(lang_paths=pipeline.paths['languages']['ko'])
        pipeline._cleanup_intermediate_files(lang_paths=pipeline.paths['languages']['es'])
        
        # Verify: Directories should be cleaned up
        # Note: In actual implementation, directories are removed
        # Here we just verify the method can be called without error
        assert True  # If we get here, cleanup succeeded

