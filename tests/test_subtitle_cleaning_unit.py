
import pytest
from langflix.utils.expression_utils import clean_display_text, clean_text_for_matching

def test_clean_display_text_with_user_example():
    """
    Test clean_display_text with the specific example provided by the user.
    It should remove square brackets [Sound] but keep parentheses (Speaker).
    """
    # Case 1: Korean with sound effect and speaker label
    korean_input = "[익살스러운 효과음]\n(여자1) 네?"
    expected_korean = "(여자1) 네?"
    
    cleaned_korean = clean_display_text(korean_input)
    assert cleaned_korean == expected_korean, f"Expected '{expected_korean}', got '{cleaned_korean}'"

    # Case 2: English with sound effect and speaker label
    english_input = "[Witty sound effect]\n(Woman 1) Huh?"
    expected_english = "(Woman 1) Huh?"
    
    cleaned_english = clean_display_text(english_input)
    assert cleaned_english == expected_english, f"Expected '{expected_english}', got '{cleaned_english}'"

def test_clean_text_for_matching_with_user_example():
    """
    Test clean_text_for_matching with the specific example.
    It should remove square brackets [Sound] AND parentheses (Speaker) for matching.
    """
    # Case 1: Korean with sound effect and speaker label
    korean_input = "[익살스러운 효과음]\n(여자1) 네?"
    # clean_text_for_matching removes punctuation, breaks, parens, brackets, lowers case
    # (여자1) -> removed parens content? Yes, current logic removes content in parens too.
    # So expected result is just "네"
    expected_korean = "네"
    
    cleaned_korean = clean_text_for_matching(korean_input)
    assert cleaned_korean == expected_korean, f"Expected '{expected_korean}', got '{cleaned_korean}'"

    # Case 2: English
    english_input = "[Witty sound effect]\n(Woman 1) Huh?"
    # (Woman 1) -> removed
    expected_english = "huh"
    
    cleaned_english = clean_text_for_matching(english_input)
    assert cleaned_english == expected_english, f"Expected '{expected_english}', got '{cleaned_english}'"

if __name__ == "__main__":
    # Allow running directly if pytest is not available
    try:
        test_clean_display_text_with_user_example()
        test_clean_text_for_matching_with_user_example()
        print("✅ All unit tests passed!")
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        exit(1)
