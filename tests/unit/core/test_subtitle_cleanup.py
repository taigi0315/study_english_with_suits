import pytest
from langflix.core.subtitle_processor import SubtitleProcessor

def test_subtitle_cleanup_removes_brackets():
    """Test that text within square brackets is removed from subtitles."""
    # Mock data with hearing impaired subtitles
    raw_subtitles = [
        {'index': 1, 'start_time': '00:00:01,000', 'end_time': '00:00:02,000', 'text': 'Hello [sound of door opening]'},
        {'index': 2, 'start_time': '00:00:02,500', 'end_time': '00:00:03,500', 'text': '[Music plays]'},
        {'index': 3, 'start_time': '00:00:04,000', 'end_time': '00:00:05,000', 'text': 'Nice to meet you'},
        {'index': 4, 'start_time': '00:00:06,000', 'end_time': '00:00:07,000', 'text': '[Sigh] I am tired [Cough]'},
    ]
    
    # Create the processor (mocking __init__ effectively or just using the helper directly if it was static, but it's an instance method)
    # Since we can't easily mock __init__ without side effects if it loads files, we'll instantiate and then inject/call the method. 
    # However, SubtitleProcessor loads file in __init__. 
    # Let's bypass __init__ or use a dummy file. 
    # Better approach for unit testing: method should be testable.
    # The method _clean_subtitles will be what we test.
    
    # We will use a subclass to avoid __init__ logic for testing
    class TestableSubtitleProcessor(SubtitleProcessor):
        def __init__(self):
            self.subtitles = []

    processor = TestableSubtitleProcessor()
    
    cleaned = processor._clean_subtitles(raw_subtitles)
    
    assert len(cleaned) == 3 # One should be removed completely
    
    assert cleaned[0]['text'] == 'Hello'
    assert cleaned[1]['text'] == 'Nice to meet you'
    assert cleaned[2]['text'] == 'I am tired' # [Sigh] and [Cough] removed

    # Verify indices might not be re-calculated here depending on implementation, 
    # but the content is what matters.
    
def test_subtitle_cleanup_nested_brackets():
    """Test handling of multiple brackets."""
    raw_subtitles = [
         {'index': 1, 'start_time': '00:00:00,000', 'end_time': '00:00:01,000', 'text': 'Normal text'},
         {'index': 2, 'start_time': '00:00:02,000', 'end_time': '00:00:03,000', 'text': '[Bracket 1] [Bracket 2]'},
    ]
    
    class TestableSubtitleProcessor(SubtitleProcessor):
        def __init__(self):
            self.subtitles = []
            
    processor = TestableSubtitleProcessor()
    cleaned = processor._clean_subtitles(raw_subtitles)
    
    assert len(cleaned) == 1
    assert cleaned[0]['text'] == 'Normal text'
