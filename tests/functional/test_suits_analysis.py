#!/usr/bin/env python3
"""
Test script for analyzing Suits subtitle file with Gemini API
"""
import os
import sys
import json
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from langflix.core.subtitle_parser import parse_srt_file
from langflix.core.expression_analyzer import analyze_chunk


def test_suits_analysis():
    """Test the complete analysis pipeline with Suits subtitle file."""
    
    # Path to the Suits subtitle file
    subtitle_path = "assets/subtitles/Suits - season 1.en/Suits - 1x01 - Pilot.720p.WEB-DL.en.srt"
    
    print("🎬 LangFlix - Suits Analysis Test")
    print("=" * 50)
    
    # Check if file exists
    if not os.path.exists(subtitle_path):
        print(f"❌ Error: Subtitle file not found at {subtitle_path}")
        return
    
    print(f"📁 Loading subtitle file: {subtitle_path}")
    
    try:
        # Parse the subtitle file
        print("📝 Parsing subtitle file...")
        subtitles = parse_srt_file(subtitle_path)
        print(f"✅ Successfully parsed {len(subtitles)} subtitle entries")
        
        # Show first few entries
        print("\n📋 First 3 subtitle entries:")
        for i, sub in enumerate(subtitles[:3]):
            print(f"  {i+1}. [{sub['start_time']} - {sub['end_time']}] {sub['text']}")
        
        # Take a small chunk for testing (first 10 entries)
        test_chunk = subtitles[:10]
        print(f"\n🔍 Testing with first {len(test_chunk)} entries...")
        
        # Analyze the chunk
        print("🤖 Sending to Gemini API for analysis...")
        results = analyze_chunk(test_chunk)
        
        if results:
            print(f"✅ Analysis complete! Found {len(results)} expressions:")
            print("\n📊 Analysis Results:")
            print("=" * 30)
            
            for i, result in enumerate(results, 1):
                print(f"\n{i}. Expression: {result.expression}")
                print(f"   Translation: {result.expression_translation}")
                print(f"   Context: {result.context_start_time} - {result.context_end_time}")
                print(f"   Similar: {', '.join(result.similar_expressions)}")
                print(f"   Dialogues: {' | '.join(result.dialogues)}")
                print(f"   Dialogue Translations: {' | '.join(result.translation)}")
        else:
            print("❌ No expressions found or analysis failed")
            
        # Save results to file (convert to dict for JSON serialization)
        output_file = "suits_analysis_results.json"
        results_dict = [result.model_dump() for result in results]
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check if API key is set
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ Error: GEMINI_API_KEY environment variable not set")
        print("Please set your Gemini API key in the .env file or environment")
        sys.exit(1)
    
    test_suits_analysis()
