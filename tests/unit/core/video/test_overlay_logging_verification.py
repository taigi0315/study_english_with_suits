import logging
import sys
from unittest.mock import Mock, MagicMock, patch
from langflix.core.video.overlay_renderer import OverlayRenderer

# Create a mock ffmpeg module
mock_ffmpeg_module = MagicMock()

@patch.dict(sys.modules, {'ffmpeg': mock_ffmpeg_module})
def test_verify_logging_viral_title(caplog):
    caplog.set_level(logging.INFO)
    renderer = OverlayRenderer(source_language_code="ko", target_language_code="es")
    mock_stream = MagicMock()
    mock_settings = MagicMock()
    mock_settings.get_viral_title_chars_per_line.return_value = 20
    mock_settings.get_viral_title_display_duration.return_value = 5.0
    
    # Configure mock ffmpeg to return mock_stream when filtered
    mock_ffmpeg_module.filter.return_value = mock_stream

    renderer.add_viral_title(mock_stream, "MY VIRAL TITLE", mock_settings)
    
    # Check log
    assert 'overlaying title: "MY VIRAL TITLE"' in caplog.text

@patch.dict(sys.modules, {'ffmpeg': mock_ffmpeg_module})
def test_verify_logging_narrations(caplog):
    caplog.set_level(logging.INFO)
    renderer = OverlayRenderer(source_language_code="ko", target_language_code="es")
    mock_stream = MagicMock()
    mock_settings = MagicMock()
    # Mock settings required by narrations
    mock_settings.get_narrations_type_color.return_value = "white"
    mock_settings.get_narrations_duration.return_value = 5.0
    mock_settings.get_narrations_chars_per_line.return_value = 30
    
    mock_ffmpeg_module.filter.return_value = mock_stream
    
    narrations = [{"text": "TEST NARRATION", "dialogue_index": 0, "type": "commentary"}]
    
    renderer.add_narrations(mock_stream, narrations, 5, 30.0, mock_settings)
    
    assert 'overlaying narration: "TEST NARRATION" at t=0.00s' in caplog.text

@patch.dict(sys.modules, {'ffmpeg': mock_ffmpeg_module})
def test_verify_logging_vocabulary(caplog):
    caplog.set_level(logging.INFO)
    renderer = OverlayRenderer(source_language_code="ko", target_language_code="es")
    mock_stream = MagicMock()
    mock_settings = MagicMock()
    mock_settings.get_vocabulary_duration.return_value = 5.0
    
    mock_ffmpeg_module.filter.return_value = mock_stream
    
    vocab = [{"word": "WORD", "translation": "TRANS", "dialogue_index": 0}]
    
    renderer.add_vocabulary_annotations(mock_stream, vocab, 5, 30.0, mock_settings)
    
    assert 'overlaying vocabulary: "WORD" -> "TRANS"' in caplog.text

@patch.dict(sys.modules, {'ffmpeg': mock_ffmpeg_module})
def test_verify_logging_expression(caplog):
    caplog.set_level(logging.INFO)
    renderer = OverlayRenderer(source_language_code="ko", target_language_code="es")
    mock_stream = MagicMock()
    mock_settings = MagicMock()
    mock_settings.get_expression_annotations_duration.return_value = 5.0
    mock_settings.get_expression_annotations_font_size.return_value = 30
    
    mock_ffmpeg_module.filter.return_value = mock_stream
    
    exprs = [{"expression": "EXPR", "translation": "E_TRANS", "dialogue_index": 0}]
    
    renderer.add_expression_annotations(mock_stream, exprs, 5, 30.0, mock_settings)
    
    assert 'overlaying expression annotation: "EXPR" -> "E_TRANS"' in caplog.text
