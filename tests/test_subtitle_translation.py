#!/usr/bin/env python3
"""
Test script for subtitle translation service.
Tests the new subtitle translation functionality.
"""

import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from langflix.services.subtitle_translation_service import SubtitleTranslationService
from langflix.utils.path_utils import discover_subtitle_languages


def test_subtitle_translation():
    """Test subtitle translation with existing test media."""

    print("=" * 80)
    print("SUBTITLE TRANSLATION SERVICE TEST")
    print("=" * 80)
    print()

    # Use existing test media folder
    test_media_folder = Path("assets/media/test_media/The.Glory.S01E01.KOREAN.1080p.WEBRip.x265-RARBG[eztv.re]")

    if not test_media_folder.exists():
        print(f"❌ Test media folder not found: {test_media_folder}")
        return False

    print(f"📁 Test folder: {test_media_folder}")
    print()

    # Discover existing subtitles
    print("🔍 Discovering existing subtitles...")
    media_path = test_media_folder.parent / (test_media_folder.name + ".mp4")
    available_languages = discover_subtitle_languages(str(media_path))

    print(f"✅ Found {len(available_languages)} languages:")
    for lang in sorted(available_languages.keys())[:10]:
        print(f"   - {lang}")
    if len(available_languages) > 10:
        print(f"   ... and {len(available_languages) - 10} more")
    print()

    # Test scenario: Ensure French subtitle exists (translate from English if missing)
    print("🧪 TEST SCENARIO:")
    print("   Source Language: English")
    print("   Required Languages: English, French, Japanese")
    print()

    # Check which languages need translation
    required = ["English", "French", "Japanese"]
    missing = [lang for lang in required if lang not in available_languages]

    print(f"📋 Required languages: {required}")
    print(f"❓ Missing languages: {missing if missing else 'None (all exist!)'}")
    print()

    if not missing:
        print("✅ All required subtitles already exist!")
        print("   To test translation, we'll temporarily remove French.srt")

        # Find and backup French subtitle if it exists
        french_backup = None
        if "French" in available_languages:
            french_file = Path(available_languages["French"][0])
            french_backup = french_file.with_suffix('.srt.backup')
            if french_file.exists():
                import shutil
                shutil.move(str(french_file), str(french_backup))
                print(f"   Backed up: {french_file.name} → {french_backup.name}")
                missing = ["French"]

    try:
        # Initialize translation service
        print()
        print("🚀 Starting subtitle translation service...")
        print()

        service = SubtitleTranslationService(batch_size=50)

        # Progress callback
        def progress_callback(percent, message):
            print(f"   [{percent:3d}%] {message}")

        # Ensure subtitles exist
        results = service.ensure_subtitles_exist(
            subtitle_folder=test_media_folder,
            source_language="English",
            required_languages=required,
            progress_callback=progress_callback
        )

        print()
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)

        # Display results
        for lang, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"   {lang}: {status}")

        # Check if new files were created
        print()
        print("📄 Checking created files...")
        for lang in missing:
            expected_file = test_media_folder / f"{lang}.srt"
            if expected_file.exists():
                file_size = expected_file.stat().st_size
                print(f"   ✅ Created: {expected_file.name} ({file_size:,} bytes)")

                # Show first few lines
                with open(expected_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:10]
                print(f"      First few lines:")
                for line in lines[:6]:
                    print(f"      {line.rstrip()}")
                if len(lines) > 6:
                    print(f"      ...")
            else:
                print(f"   ❌ Not found: {expected_file.name}")

        print()
        print("=" * 80)
        print("✅ TEST COMPLETE!")
        print("=" * 80)

        return True

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ TEST FAILED!")
        print("=" * 80)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Restore backup if exists
        if 'french_backup' in locals() and french_backup and french_backup.exists():
            import shutil
            french_file = french_backup.with_suffix('.srt')
            if not french_file.exists():
                shutil.move(str(french_backup), str(french_file))
                print(f"   Restored backup: {french_backup.name} → {french_file.name}")


def test_simple_translation():
    """Test simple subtitle translation with minimal entries."""

    print()
    print("=" * 80)
    print("SIMPLE TRANSLATION TEST")
    print("=" * 80)
    print()

    # Create a simple test subtitle file
    test_folder = Path("test_translation_output")
    test_folder.mkdir(exist_ok=True)

    # Create a simple Korean subtitle for testing
    simple_korean = """1
00:00:01,000 --> 00:00:03,000
안녕하세요

2
00:00:03,500 --> 00:00:05,000
어떻게 지내세요?

3
00:00:05,500 --> 00:00:07,000
오늘 날씨가 좋네요

4
00:00:07,500 --> 00:00:09,000
점심 먹었어요?

5
00:00:09,500 --> 00:00:11,000
같이 가요
"""

    korean_file = test_folder / "Korean.srt"
    korean_file.write_text(simple_korean, encoding='utf-8')
    print(f"✅ Created test Korean subtitle: {korean_file}")
    print()

    try:
        # Test translation
        service = SubtitleTranslationService(batch_size=10)

        def progress_callback(percent, message):
            print(f"   [{percent:3d}%] {message}")

        print("🚀 Translating Korean → English...")
        print()

        results = service.ensure_subtitles_exist(
            subtitle_folder=test_folder,
            source_language="Korean",
            required_languages=["Korean", "English"],
            progress_callback=progress_callback
        )

        print()
        print("📊 Results:")
        for lang, success in results.items():
            status = "✅" if success else "❌"
            print(f"   {status} {lang}")

        # Check English output
        english_file = test_folder / "English.srt"
        if english_file.exists():
            print()
            print("📄 Generated English subtitle:")
            print("-" * 80)
            print(english_file.read_text(encoding='utf-8'))
            print("-" * 80)
            print()
            print("✅ Simple translation test PASSED!")
            return True
        else:
            print()
            print("❌ English subtitle not created!")
            return False

    except Exception as e:
        print()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print()
    print("🧪 SUBTITLE TRANSLATION TEST SUITE")
    print()

    # Check if GEMINI_API_KEY is set
    import os
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ ERROR: GEMINI_API_KEY not set in environment")
        print("   Please set GEMINI_API_KEY in your .env file")
        sys.exit(1)

    print("✅ GEMINI_API_KEY found")
    print()

    # Run tests
    print("Running Test 1: Simple Translation Test")
    test1_passed = test_simple_translation()

    print()
    print("Running Test 2: Real Media Translation Test")
    test2_passed = test_subtitle_translation()

    # Summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Test 1 (Simple): {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Test 2 (Real Media): {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    print("=" * 80)

    sys.exit(0 if (test1_passed and test2_passed) else 1)
