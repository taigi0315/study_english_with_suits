#!/usr/bin/env python3
"""
Unit tests for subtitle validation and parsing
"""

import pytest
import tempfile
import os
from pathlib import Path

from langflix.core.subtitle_parser import (
    validate_subtitle_file,
    detect_encoding,
    parse_srt_file,
    SUPPORTED_FORMATS
)
from langflix.core.subtitle_exceptions import (
    SubtitleNotFoundError,
    SubtitleFormatError,
    SubtitleEncodingError,
    SubtitleParseError
)


class TestSubtitleValidation:
    """Test subtitle file validation"""
    
    def test_validate_existing_srt_file(self):
        """Test validation of existing .srt file"""
        # Create a temporary .srt file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False) as f:
            f.write("1\n00:00:01,000 --> 00:00:02,000\nTest subtitle\n\n")
            temp_path = f.name
        
        try:
            # Should not raise exception
            result, error = validate_subtitle_file(temp_path)
            assert result is True
            assert error is None
        finally:
            os.unlink(temp_path)
    
    def test_validate_nonexistent_file(self):
        """Test validation fails for non-existent file"""
        with pytest.raises(SubtitleNotFoundError) as exc_info:
            validate_subtitle_file("/nonexistent/path/to/file.srt")
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_validate_unsupported_format(self):
        """Test validation fails for unsupported format"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Not a subtitle file")
            temp_path = f.name
        
        try:
            with pytest.raises(SubtitleFormatError) as exc_info:
                validate_subtitle_file(temp_path)
            
            assert "unsupported format" in str(exc_info.value).lower()
        finally:
            os.unlink(temp_path)
    
    def test_validate_directory_not_file(self):
        """Test validation fails when path is a directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(SubtitleFormatError) as exc_info:
                validate_subtitle_file(temp_dir)
            
            assert "not a file" in str(exc_info.value).lower()
    
    def test_supported_formats(self):
        """Test all supported formats are recognized"""
        for format_ext in SUPPORTED_FORMATS:
            with tempfile.NamedTemporaryFile(mode='w', suffix=format_ext, delete=False) as f:
                f.write("Test content")
                temp_path = f.name
            
            try:
                result, error = validate_subtitle_file(temp_path)
                assert result is True
            finally:
                os.unlink(temp_path)


class TestEncodingDetection:
    """Test encoding detection functionality"""
    
    def test_detect_utf8_encoding(self):
        """Test detection of UTF-8 encoding"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', encoding='utf-8', delete=False) as f:
            f.write("1\n00:00:01,000 --> 00:00:02,000\nTest subtitle\n\n")
            temp_path = f.name
        
        try:
            encoding = detect_encoding(temp_path)
            assert encoding.lower() in ['utf-8', 'utf8', 'ascii']  # ascii is compatible with utf-8
        finally:
            os.unlink(temp_path)
    
    def test_detect_latin1_encoding(self):
        """Test detection of Latin-1 encoding"""
        content = "1\n00:00:01,000 --> 00:00:02,000\nCafé\n\n"
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.srt', delete=False) as f:
            f.write(content.encode('latin-1'))
            temp_path = f.name
        
        try:
            encoding = detect_encoding(temp_path)
            # chardet should detect some encoding
            assert encoding is not None
            assert len(encoding) > 0
        finally:
            os.unlink(temp_path)


class TestSubtitleParsing:
    """Test subtitle parsing with validation"""
    
    def test_parse_valid_srt_file(self):
        """Test parsing a valid .srt file"""
        content = """1
00:00:01,000 --> 00:00:02,000
First subtitle

2
00:00:02,500 --> 00:00:04,000
Second subtitle
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', encoding='utf-8', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            result = parse_srt_file(temp_path)
            
            assert len(result) == 2
            assert result[0]['text'] == 'First subtitle'
            assert result[1]['text'] == 'Second subtitle'
        finally:
            os.unlink(temp_path)
    
    def test_parse_with_validation_disabled(self):
        """Test parsing with validation disabled"""
        content = "1\n00:00:01,000 --> 00:00:02,000\nTest\n\n"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', encoding='utf-8', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            result = parse_srt_file(temp_path, validate=False)
            assert len(result) == 1
        finally:
            os.unlink(temp_path)
    
    def test_parse_nonexistent_file_with_validation(self):
        """Test parsing non-existent file raises exception with validation"""
        with pytest.raises(SubtitleNotFoundError):
            parse_srt_file("/nonexistent/file.srt", validate=True)
    
    def test_parse_unsupported_format_with_validation(self):
        """Test parsing unsupported format raises exception"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Not a subtitle")
            temp_path = f.name
        
        try:
            with pytest.raises(SubtitleFormatError):
                parse_srt_file(temp_path, validate=True)
        finally:
            os.unlink(temp_path)
    
    def test_parse_with_different_encodings(self):
        """Test parsing with various encodings"""
        content = "1\n00:00:01,000 --> 00:00:02,000\nHello 안녕하세요\n\n"
        encodings = ['utf-8', 'cp949']
        
        for encoding in encodings:
            try:
                with tempfile.NamedTemporaryFile(mode='wb', suffix='.srt', delete=False) as f:
                    f.write(content.encode(encoding))
                    temp_path = f.name
                
                # Should handle encoding automatically
                result = parse_srt_file(temp_path)
                assert len(result) > 0
                
            except UnicodeEncodeError:
                # Skip if encoding doesn't support the characters
                continue
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)


class TestErrorHandling:
    """Test error handling and error messages"""
    
    def test_subtitle_not_found_error_message(self):
        """Test SubtitleNotFoundError contains file path"""
        path = "/test/path/file.srt"
        error = SubtitleNotFoundError(path)
        
        assert path in str(error)
        assert error.path == path
    
    def test_subtitle_format_error_message(self):
        """Test SubtitleFormatError contains format and reason"""
        format_type = ".xyz"
        reason = "Unsupported"
        error = SubtitleFormatError(format_type, reason)
        
        assert format_type in str(error)
        assert reason in str(error)
        assert error.format == format_type
        assert error.reason == reason
    
    def test_subtitle_encoding_error_message(self):
        """Test SubtitleEncodingError contains path and encodings"""
        path = "/test/file.srt"
        encodings = ['utf-8', 'latin-1']
        error = SubtitleEncodingError(path, encodings)
        
        assert path in str(error)
        assert error.path == path
        assert error.attempted_encodings == encodings
    
    def test_subtitle_parse_error_message(self):
        """Test SubtitleParseError contains useful information"""
        path = "/test/file.srt"
        reason = "Invalid timestamp format"
        line_number = 5
        error = SubtitleParseError(path, reason, line_number)
        
        assert path in str(error)
        assert reason in str(error)
        assert str(line_number) in str(error)
        assert error.path == path
        assert error.reason == reason
        assert error.line_number == line_number

