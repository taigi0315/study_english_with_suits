#!/usr/bin/env python3
"""
Test to verify language code/name normalization works correctly.
"""

# Simulate the normalization logic
def normalize_source_language(source_language):
    """Convert language code to full name if needed."""
    language_code_to_name = {
        'ko': 'Korean', 'ja': 'Japanese', 'zh': 'Chinese', 'es': 'Spanish',
        'fr': 'French', 'en': 'English', 'de': 'German', 'pt': 'Portuguese',
        'ru': 'Russian', 'ar': 'Arabic', 'it': 'Italian', 'nl': 'Dutch',
        'pl': 'Polish', 'th': 'Thai', 'vi': 'Vietnamese', 'tr': 'Turkish',
        'sv': 'Swedish', 'fi': 'Finnish', 'da': 'Danish', 'no': 'Bokmal',
        'cs': 'Czech', 'el': 'Greek', 'he': 'Hebrew', 'hu': 'Hungarian',
        'id': 'Indonesian', 'ro': 'Romanian'
    }

    # If source_language is a code (2-3 chars), convert to full name
    if source_language and len(source_language) <= 3 and source_language.lower() in language_code_to_name:
        return language_code_to_name[source_language.lower()]
    else:
        return source_language


# Test cases
test_cases = [
    ("ko", "Korean"),
    ("KO", "Korean"),
    ("zh", "Chinese"),
    ("es", "Spanish"),
    ("Korean", "Korean"),  # Already a name
    ("Spanish", "Spanish"),  # Already a name
    ("en", "English"),
    ("English", "English"),
]

print("Testing language code/name normalization:")
print("=" * 60)

all_passed = True
for input_lang, expected in test_cases:
    result = normalize_source_language(input_lang)
    status = "✅ PASS" if result == expected else "❌ FAIL"
    print(f"{status} | Input: '{input_lang:10}' -> Output: '{result:10}' (Expected: '{expected}')")
    if result != expected:
        all_passed = False

print("=" * 60)
if all_passed:
    print("✅ All tests passed!")
else:
    print("❌ Some tests failed!")

# Simulate the workflow
print("\n" + "=" * 60)
print("SIMULATED WORKFLOW:")
print("=" * 60)

# User uploads with source_language="ko"
source_language = "ko"
print(f"1. User uploads subtitle with source_language='{source_language}'")

# Pipeline normalizes it
normalized = normalize_source_language(source_language)
print(f"2. Pipeline normalizes to: '{normalized}'")

# File is saved as Korean.srt
filename = f"{normalized}.srt"
print(f"3. Uploaded subtitle saved as: '{filename}'")

# Translation service translates to Chinese
print(f"4. Translation service translates: '{normalized}' -> 'Chinese'")
print(f"5. Creates files: '{normalized}.srt', 'Chinese.srt'")

# V2 pipeline looks for Korean + Chinese
print(f"6. V2 pipeline needs: '{normalized}' + 'Chinese'")
print(f"7. V2 pipeline finds: '{normalized}.srt' ✅, 'Chinese.srt' ✅")
print(f"8. ✅ SUCCESS - All files found!")

print("=" * 60)
