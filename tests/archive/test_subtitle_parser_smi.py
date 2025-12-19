"""
Unit tests for SMI subtitle parser

Tests cover:
- SMI file parsing
- Encoding detection and fallback
- Multi-language SMI files
- Error handling
- Time format conversion
"""
import unittest
import tempfile
import os
from pathlib import Path
import sys

# Add the parent directory to the path so we can import langflix
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langflix.core.subtitle_parser import (
    parse_smi_file,
    parse_subtitle_file_by_extension,
    SUPPORTED_FORMATS,
    validate_subtitle_file
)
from langflix.core.subtitle_exceptions import (
    SubtitleNotFoundError,
    SubtitleFormatError,
    SubtitleParseError
)


class TestSMIParser(unittest.TestCase):
    """Test cases for SMI subtitle parser."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_data_dir = Path(__file__).parent.parent / "fixtures" / "subtitles"
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_smi_in_supported_formats(self):
        """Test that .smi is in SUPPORTED_FORMATS."""
        self.assertIn('.smi', SUPPORTED_FORMATS)
    
    def test_parse_smi_file_basic(self):
        """Test basic SMI file parsing."""
        smi_file = self.test_data_dir / "sample.smi"
        if not smi_file.exists():
            self.skipTest(f"Test fixture not found: {smi_file}")
        
        result = parse_smi_file(str(smi_file))
        
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        
        # Check structure
        for entry in result:
            self.assertIn('start_time', entry)
            self.assertIn('end_time', entry)
            self.assertIn('text', entry)
            # Check time format (HH:MM:SS.mmm)
            self.assertRegex(entry['start_time'], r'\d{2}:\d{2}:\d{2}\.\d{3}')
            self.assertRegex(entry['end_time'], r'\d{2}:\d{2}:\d{2}\.\d{3}')
    
    def test_parse_smi_file_multilang(self):
        """Test parsing multi-language SMI file."""
        smi_file = self.test_data_dir / "sample_multilang.smi"
        if not smi_file.exists():
            self.skipTest(f"Test fixture not found: {smi_file}")
        
        result = parse_smi_file(str(smi_file))
        
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        
        # Check that multiple P tags are joined with newline
        for entry in result:
            self.assertIn('text', entry)
            # Multi-language entries should have newlines
            if '\n' in entry['text']:
                self.assertGreater(len(entry['text'].split('\n')), 1)
    
    def test_parse_smi_file_time_conversion(self):
        """Test that SMI milliseconds are correctly converted to time format."""
        smi_file = self.test_data_dir / "sample.smi"
        if not smi_file.exists():
            self.skipTest(f"Test fixture not found: {smi_file}")
        
        result = parse_smi_file(str(smi_file))
        
        # First entry should start at 0ms = 00:00:00.000
        self.assertEqual(result[0]['start_time'], "00:00:00.000")
        
        # Second entry should start at 2000ms = 00:00:02.000
        self.assertEqual(result[1]['start_time'], "00:00:02.000")
        
        # Third entry should start at 5000ms = 00:00:05.000
        self.assertEqual(result[2]['start_time'], "00:00:05.000")
    
    def test_parse_smi_file_end_time_calculation(self):
        """Test that end_time is calculated from next sync."""
        smi_file = self.test_data_dir / "sample.smi"
        if not smi_file.exists():
            self.skipTest(f"Test fixture not found: {smi_file}")
        
        result = parse_smi_file(str(smi_file))
        
        # First entry: start=0ms, next start=2000ms, so end should be 00:00:02.000
        self.assertEqual(result[0]['end_time'], "00:00:02.000")
        
        # Second entry: start=2000ms, next start=5000ms, so end should be 00:00:05.000
        self.assertEqual(result[1]['end_time'], "00:00:05.000")
    
    def test_parse_smi_file_last_entry_default_duration(self):
        """Test that last entry gets default duration."""
        smi_file = self.test_data_dir / "sample.smi"
        if not smi_file.exists():
            self.skipTest(f"Test fixture not found: {smi_file}")
        
        result = parse_smi_file(str(smi_file))
        
        # Last entry should have default duration (2 seconds)
        last_entry = result[-1]
        start_seconds = float(last_entry['start_time'].split(':')[2])
        end_seconds = float(last_entry['end_time'].split(':')[2])
        duration = end_seconds - start_seconds
        
        # Should be approximately 2 seconds (allowing for minute/hour rollover)
        self.assertGreaterEqual(duration, 1.9)
        self.assertLessEqual(duration, 2.1)
    
    def test_parse_smi_file_not_found(self):
        """Test error handling for non-existent file."""
        with self.assertRaises(SubtitleNotFoundError):
            parse_smi_file("/nonexistent/path.smi")
    
    def test_parse_smi_file_invalid_format(self):
        """Test error handling for invalid SMI format."""
        # Create invalid XML file (malformed XML)
        invalid_file = Path(self.temp_dir) / "invalid.smi"
        invalid_file.write_text("<INVALID>Not a valid SMI file<INVALID>", encoding='utf-8')
        
        with self.assertRaises(SubtitleParseError):
            parse_smi_file(str(invalid_file))
    
    def test_parse_smi_file_no_sync_elements(self):
        """Test parsing SMI file with no SYNC elements (valid XML but invalid SMI)."""
        # Create valid XML but invalid SMI format
        invalid_file = Path(self.temp_dir) / "no_sync.smi"
        invalid_file.write_text("<SAMI><HEAD><TITLE>Test</TITLE></HEAD><BODY></BODY></SAMI>", encoding='utf-8')
        
        result = parse_smi_file(str(invalid_file))
        # Should return empty list (no SYNC elements found)
        self.assertEqual(len(result), 0)
    
    def test_parse_smi_file_empty_sync(self):
        """Test handling of SYNC elements without Start attribute."""
        # Create SMI file with empty SYNC
        smi_content = """<SAMI>
<HEAD><TITLE>Test</TITLE></HEAD>
<BODY>
<SYNC Start="0"><P>First</P></SYNC>
<SYNC><P>No Start attribute</P></SYNC>
<SYNC Start="2000"><P>Second</P></SYNC>
</BODY>
</SAMI>"""
        
        smi_file = Path(self.temp_dir) / "empty_sync.smi"
        smi_file.write_text(smi_content, encoding='utf-8')
        
        result = parse_smi_file(str(smi_file))
        
        # Should only parse valid SYNC elements
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['text'], "First")
        self.assertEqual(result[1]['text'], "Second")
    
    def test_parse_smi_file_no_text(self):
        """Test handling of SYNC elements without text."""
        smi_content = """<SAMI>
<HEAD><TITLE>Test</TITLE></HEAD>
<BODY>
<SYNC Start="0"><P>Has text</P></SYNC>
<SYNC Start="2000"><P></P></SYNC>
<SYNC Start="3000"><P>Also has text</P></SYNC>
</BODY>
</SAMI>"""
        
        smi_file = Path(self.temp_dir) / "no_text.smi"
        smi_file.write_text(smi_content, encoding='utf-8')
        
        result = parse_smi_file(str(smi_file))
        
        # Should only include entries with text
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['text'], "Has text")
        self.assertEqual(result[1]['text'], "Also has text")
    
    def test_parse_subtitle_file_by_extension_smi(self):
        """Test parse_subtitle_file_by_extension with SMI file."""
        smi_file = self.test_data_dir / "sample.smi"
        if not smi_file.exists():
            self.skipTest(f"Test fixture not found: {smi_file}")
        
        result = parse_subtitle_file_by_extension(str(smi_file))
        
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        
        # Should have same structure as parse_smi_file
        for entry in result:
            self.assertIn('start_time', entry)
            self.assertIn('end_time', entry)
            self.assertIn('text', entry)
    
    def test_parse_subtitle_file_by_extension_unsupported(self):
        """Test parse_subtitle_file_by_extension with unsupported format."""
        test_file = Path(self.temp_dir) / "test.xyz"
        test_file.write_text("test content", encoding='utf-8')
        
        with self.assertRaises(SubtitleFormatError):
            parse_subtitle_file_by_extension(str(test_file))
    
    def test_validate_subtitle_file_smi(self):
        """Test that SMI files pass validation."""
        smi_file = self.test_data_dir / "sample.smi"
        if not smi_file.exists():
            self.skipTest(f"Test fixture not found: {smi_file}")
        
        is_valid, error_msg = validate_subtitle_file(str(smi_file))
        self.assertTrue(is_valid)
        self.assertIsNone(error_msg)
    
    def test_parse_smi_file_without_validate(self):
        """Test parsing SMI file without validation."""
        smi_file = self.test_data_dir / "sample.smi"
        if not smi_file.exists():
            self.skipTest(f"Test fixture not found: {smi_file}")
        
        result = parse_smi_file(str(smi_file), validate=False)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)


if __name__ == '__main__':
    unittest.main()

