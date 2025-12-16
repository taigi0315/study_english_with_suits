#!/usr/bin/env python3
"""
Test script for FontResolver - Spanish language configuration.

Usage:
    python scripts/test_font_resolution.py
"""

import sys
from pathlib import Path

# Add langflix to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from langflix.core.video.font_resolver import FontResolver


def test_spanish_fonts():
    """Test Spanish font resolution for all use cases."""
    print("\n" + "="*70)
    print("Testing Spanish Font Resolution")
    print("="*70 + "\n")

    resolver = FontResolver(default_language_code="es")

    # Test validation
    print("1. Validating Spanish font support...")
    is_supported = resolver.validate_font_support("es")
    status = "✅ PASS" if is_supported else "❌ FAIL"
    print(f"   {status}: Spanish font support = {is_supported}\n")

    # Test all use cases
    print("2. Testing all use cases:")
    use_cases = [
        "default", "expression", "keywords", "translation",
        "vocabulary", "narration", "dialogue", "title", "educational_slide"
    ]

    all_fonts = resolver.get_all_fonts_for_language("es")
    found_count = 0
    missing_count = 0

    for use_case in use_cases:
        font_path = all_fonts.get(use_case)
        if font_path:
            status = "✅"
            found_count += 1
            print(f"   {status} {use_case:20s}: {font_path}")
        else:
            status = "❌"
            missing_count += 1
            print(f"   {status} {use_case:20s}: NOT FOUND")

    print(f"\n   Summary: {found_count} found, {missing_count} missing")

    # Test FFmpeg font option string
    print("\n3. Testing FFmpeg font option generation:")
    for use_case in ["keywords", "translation", "title"]:
        option = resolver.get_font_option_string(language_code="es", use_case=use_case)
        if option:
            print(f"   ✅ {use_case:20s}: {option}")
        else:
            print(f"   ❌ {use_case:20s}: Empty option string")

    # Test caching
    print("\n4. Testing font caching:")
    print(f"   Initial cache state: {repr(resolver)}")

    # Trigger cache population
    _ = resolver.get_font_for_language(use_case="keywords")
    _ = resolver.get_font_for_language(use_case="translation")
    print(f"   After 2 lookups: {repr(resolver)}")

    # Clear cache
    resolver.clear_cache()
    print(f"   After clear_cache(): {repr(resolver)}")

    print("\n" + "="*70)
    print("Spanish Font Resolution Test Complete")
    print("="*70 + "\n")

    return is_supported


def test_dual_language_korean_spanish():
    """Test dual-language configuration: Korean → Spanish."""
    print("\n" + "="*70)
    print("Testing Dual-Language Configuration: Korean → Spanish")
    print("="*70 + "\n")

    resolver = FontResolver(
        default_language_code="es",    # Target: Spanish
        source_language_code="ko"      # Source: Korean
    )

    print("1. Resolver configuration:")
    print(f"   {repr(resolver)}\n")

    # Validate dual-language support
    print("2. Validating dual-language support:")
    validation = resolver.validate_dual_language_support()

    for key, value in validation.items():
        if isinstance(value, bool):
            status = "✅" if value else "❌"
            print(f"   {status} {key}: {value}")
        else:
            print(f"   ℹ️  {key}: {value}")

    # Test source font methods
    print("\n3. Testing source language (Korean) fonts:")
    for use_case in ["expression", "vocabulary", "dialogue"]:
        font = resolver.get_source_font(use_case)
        option = resolver.get_source_font_option(use_case)
        status = "✅" if font else "❌"
        print(f"   {status} {use_case:15s}: {font or 'NOT FOUND'}")
        if option:
            print(f"      FFmpeg option: {option[:60]}...")

    # Test target font methods
    print("\n4. Testing target language (Spanish) fonts:")
    for use_case in ["translation", "keywords", "narration"]:
        font = resolver.get_target_font(use_case)
        option = resolver.get_target_font_option(use_case)
        status = "✅" if font else "❌"
        print(f"   {status} {use_case:15s}: {font or 'NOT FOUND'}")
        if option:
            print(f"      FFmpeg option: {option[:60]}...")

    # Test dual fonts method
    print("\n5. Testing dual fonts for vocabulary:")
    source_font, target_font = resolver.get_dual_fonts(use_case="vocabulary")
    print(f"   Source (Korean): {source_font or 'NOT FOUND'}")
    print(f"   Target (Spanish): {target_font or 'NOT FOUND'}")

    both_found = source_font and target_font
    status = "✅ PASS" if both_found else "❌ FAIL"
    print(f"\n   {status}: Both fonts {'found' if both_found else 'missing'}")

    print("\n" + "="*70)
    print("Dual-Language Test Complete")
    print("="*70 + "\n")

    return validation["source"] and validation["target"]


def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n" + "="*70)
    print("Testing Edge Cases and Error Handling")
    print("="*70 + "\n")

    # Test 1: Unknown language
    print("1. Testing unknown language:")
    resolver = FontResolver(default_language_code="unknown")
    font = resolver.get_font_for_language(use_case="default")
    status = "✅ PASS" if font is None else "❌ FAIL"
    print(f"   {status}: Unknown language returns None = {font is None}")

    # Test 2: No default language
    print("\n2. Testing no default language:")
    resolver = FontResolver()
    print(f"   Resolver: {repr(resolver)}")
    # Should require explicit language_code
    font = resolver.get_font_for_language(language_code="es", use_case="default")
    status = "✅ PASS" if font else "❌ FAIL"
    print(f"   {status}: Can resolve with explicit language_code = {font is not None}")

    # Test 3: Cache key uniqueness
    print("\n3. Testing cache key uniqueness (language + use_case):")
    resolver = FontResolver(default_language_code="es")

    font1 = resolver.get_font_for_language(use_case="default")
    font2 = resolver.get_font_for_language(use_case="keywords")

    print(f"   Cache after 2 different use_cases: {repr(resolver)}")
    expected_cache_size = 2 if (font1 and font2) else (1 if (font1 or font2) else 0)
    actual_cache_size = len(resolver.font_cache)
    status = "✅ PASS" if actual_cache_size >= expected_cache_size else "❌ FAIL"
    print(f"   {status}: Cache has separate entries for each use_case")

    print("\n" + "="*70)
    print("Edge Cases Test Complete")
    print("="*70 + "\n")


def main():
    """Run all font resolution tests."""
    print("\n" + "="*70)
    print("FontResolver Test Suite - Spanish Configuration")
    print("="*70)

    # Run tests
    spanish_ok = test_spanish_fonts()
    dual_lang_ok = test_dual_language_korean_spanish()
    test_edge_cases()

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    status_spanish = "✅ PASS" if spanish_ok else "❌ FAIL"
    status_dual = "✅ PASS" if dual_lang_ok else "❌ FAIL"

    print(f"{status_spanish}: Spanish font resolution")
    print(f"{status_dual}: Korean→Spanish dual-language")

    overall_status = spanish_ok and dual_lang_ok
    if overall_status:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed. Check font configuration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
