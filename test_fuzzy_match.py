#!/usr/bin/env python3
"""
Quick test to demonstrate fuzzy subtitle matching results.
"""
import sys
sys.path.insert(0, '/Users/changikchoi/Documents/langflix')

from langflix.core.dual_subtitle import (
    get_dual_subtitle_service,
    is_dialogue_entry,
    filter_dialogue_entries,
    fuzzy_match_by_timestamp,
)
from langflix.core.subtitle_parser import parse_srt_file

# File paths
korean_srt = "/Users/changikchoi/Documents/langflix/assets/media/test_media/The.Glory.S01E01.KOREAN.1080p.WEBRip.x265-RARBG[eztv.re]/Korean.srt"
english_srt = "/Users/changikchoi/Documents/langflix/assets/media/test_media/The.Glory.S01E01.KOREAN.1080p.WEBRip.x265-RARBG[eztv.re]/English.srt"

print("=" * 60)
print("FUZZY SUBTITLE MATCHING TEST")
print("=" * 60)

# Parse raw subtitles
from langflix.core.dual_subtitle import SubtitleEntry

def parse_to_entries(path):
    parsed = parse_srt_file(path)
    entries = []
    for i, item in enumerate(parsed, start=1):
        entry = SubtitleEntry(
            index=i,
            start_time=item.get('start_time', '00:00:00,000'),
            end_time=item.get('end_time', '00:00:00,000'),
            text=item.get('text', ''),
        )
        entries.append(entry)
    return entries

korean_raw = parse_to_entries(korean_srt)
english_raw = parse_to_entries(english_srt)

print(f"\n📊 RAW SUBTITLE COUNTS:")
print(f"   Korean:  {len(korean_raw)} entries")
print(f"   English: {len(english_raw)} entries")
print(f"   Difference: {abs(len(korean_raw) - len(english_raw))} entries")

# Show examples of filtered entries
print(f"\n🔍 EXAMPLES OF FILTERED (NON-DIALOGUE) ENTRIES:")
filtered_count = 0
for entry in korean_raw[:100]:  # Check first 100
    if not is_dialogue_entry(entry.text):
        filtered_count += 1
        if filtered_count <= 5:
            print(f"   ❌ [{entry.index}] {entry.text[:50]}...")

# Filter non-dialogue
korean_filtered = filter_dialogue_entries(korean_raw)
english_filtered = filter_dialogue_entries(english_raw)

print(f"\n📊 AFTER FILTERING NON-DIALOGUE:")
print(f"   Korean:  {len(korean_filtered)} entries (removed {len(korean_raw) - len(korean_filtered)})")
print(f"   English: {len(english_filtered)} entries (removed {len(english_raw) - len(english_filtered)})")

# Fuzzy match
print(f"\n⏱️  RUNNING FUZZY TIMESTAMP MATCHING...")
matched_pairs = fuzzy_match_by_timestamp(
    korean_filtered,
    english_filtered,
    tolerance_seconds=1.0
)

print(f"\n📊 MATCHING RESULTS:")
print(f"   Matched pairs: {len(matched_pairs)}")
print(f"   Match rate: {len(matched_pairs) / len(korean_filtered) * 100:.1f}% of Korean entries")

# Show sample matched pairs
print(f"\n✅ SAMPLE MATCHED PAIRS (first 10):")
print("-" * 60)
for i, (korean, english) in enumerate(matched_pairs[:10]):
    kr_text = korean.text.replace('\n', ' ')[:40]
    en_text = english.text.replace('\n', ' ')[:40]
    time_diff = abs(korean.start_seconds - english.start_seconds)
    print(f"{i+1}. [{korean.start_time}] Δ{time_diff:.2f}s")
    print(f"   KR: {kr_text}...")
    print(f"   EN: {en_text}...")
    print()

print("=" * 60)
print("TEST COMPLETE")
print("=" * 60)
