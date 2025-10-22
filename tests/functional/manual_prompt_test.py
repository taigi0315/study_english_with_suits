#!/usr/bin/env python3
"""
Manual prompt testing script for LangFlix
Allows you to see the generated prompt and test it manually with Gemini API
"""
import os
import sys
import json
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from langflix.core.subtitle_parser import parse_srt_file, chunk_subtitles
from langflix.utils.prompts import get_prompt_for_chunk
from langflix import settings


def print_separator(title=""):
    """Print a visual separator with optional title"""
    print("\n" + "=" * 60)
    if title:
        print(f" {title}")
        print("=" * 60)
    print()


def test_manual_prompt():
    """Test manual prompt generation and display"""
    
    print("🔧 LangFlix - Manual Prompt Testing Tool")
    print_separator()
    
    # Configuration
    subtitle_path = "assets/subtitles/Suits - season 1.en/Suits - 1x01 - Pilot.720p.WEB-DL.en.srt"
    max_chunk_size = 5  # Number of subtitle entries per chunk for testing
    
    print(f"📁 Subtitle file: {subtitle_path}")
    print(f"📏 Max chunk size: {max_chunk_size} entries")
        print(f"📏 Max LLM input length: {settings.MAX_LLM_INPUT_LENGTH} characters")
    print(f"🌍 Target language: {settings.TARGET_LANGUAGE}")
    
    # Check if file exists
    if not os.path.exists(subtitle_path):
        print(f"❌ Error: Subtitle file not found at {subtitle_path}")
        return
    
    try:
        # Parse subtitle file
        print_separator("PARSING SUBTITLE FILE")
        print("📝 Loading subtitle file...")
        subtitles = parse_srt_file(subtitle_path)
        print(f"✅ Successfully parsed {len(subtitles)} subtitle entries")
        
        # Show first few entries
        print("\n📋 First 5 subtitle entries:")
        for i, sub in enumerate(subtitles[:5]):
            print(f"  {i+1:2d}. [{sub['start_time']} - {sub['end_time']}] {sub['text']}")
        
        # Create chunks
        print_separator("CREATING CHUNKS")
        chunks = chunk_subtitles(subtitles)
        print(f"📦 Created {len(chunks)} chunks")
        
        # Show chunk sizes
        print("\n📊 Chunk sizes:")
        for i, chunk in enumerate(chunks[:10]):  # Show first 10 chunks
            total_length = sum(len(sub['text']) for sub in chunk)
            print(f"  Chunk {i+1:2d}: {len(chunk):2d} entries, {total_length:4d} characters")
        
        # Test with first chunk
        if chunks:
            test_chunk = chunks[0]
            print_separator("TESTING FIRST CHUNK")
            print(f"🔍 Testing with chunk 1 ({len(test_chunk)} entries)")
            
            # Show chunk content
            print("\n📝 Chunk content:")
            for i, sub in enumerate(test_chunk):
                print(f"  {i+1:2d}. [{sub['start_time']} - {sub['end_time']}] {sub['text']}")
            
            # Generate prompt
            print_separator("GENERATED PROMPT")
            prompt = get_prompt_for_chunk(test_chunk)
            print("🤖 Generated prompt for Gemini API:")
            print("-" * 60)
            print(prompt)
            print("-" * 60)
            
            # Prompt statistics
            prompt_length = len(prompt)
            print(f"\n📊 Prompt statistics:")
            print(f"  Total length: {prompt_length} characters")
            print(f"  Max allowed: {config.MAX_LLM_INPUT_LENGTH} characters")
            print(f"  Usage: {prompt_length/config.MAX_LLM_INPUT_LENGTH*100:.1f}%")
            
            # Save prompt to file for manual testing
            prompt_file = "manual_test_prompt.txt"
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(prompt)
            print(f"\n💾 Prompt saved to: {prompt_file}")
            
            # Instructions for manual testing
            print_separator("MANUAL TESTING INSTRUCTIONS")
            print("🔧 To test this prompt manually:")
            print("1. Copy the prompt above")
            print("2. Go to https://aistudio.google.com/")
            print("3. Paste the prompt into the chat")
            print("4. Check the JSON response format")
            print("5. Modify prompts.py if needed")
            print("\n📝 You can also modify the prompt in langflix/prompts.py")
            print("   and run this script again to see the changes.")
            
            # Show how to modify prompts
            print_separator("PROMPT MODIFICATION GUIDE")
            print("📝 To modify the prompt:")
            print("1. Edit langflix/prompts.py")
            print("2. Modify the get_prompt_for_chunk() function")
            print("3. Run this script again: python manual_prompt_test.py")
            print("4. Test the new prompt manually")
            
            # Show current prompt template
            print("\n🔍 Current prompt template structure:")
            print("   - Dialogue section with timestamps")
            print("   - Task description for LLM")
            print("   - JSON format requirements")
            print("   - Example JSON structure")
            print("   - Analysis instructions")
            
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


def test_specific_chunk(chunk_index=0):
    """Test a specific chunk by index"""
    subtitle_path = "assets/subtitles/Suits - season 1.en/Suits - 1x01 - Pilot.720p.WEB-DL.en.srt"
    
    print(f"🔍 Testing specific chunk {chunk_index}")
    
    subtitles = parse_srt_file(subtitle_path)
    chunks = chunk_subtitles(subtitles)
    
    if chunk_index >= len(chunks):
        print(f"❌ Chunk {chunk_index} not found. Available chunks: 0-{len(chunks)-1}")
        return
    
    chunk = chunks[chunk_index]
    prompt = get_prompt_for_chunk(chunk)
    
    print(f"\n📝 Chunk {chunk_index} content ({len(chunk)} entries):")
    for i, sub in enumerate(chunk):
        print(f"  {i+1:2d}. [{sub['start_time']} - {sub['end_time']}] {sub['text']}")
    
    print(f"\n🤖 Generated prompt:")
    print("-" * 60)
    print(prompt)
    print("-" * 60)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test specific chunk
        try:
            chunk_index = int(sys.argv[1])
            test_specific_chunk(chunk_index)
        except ValueError:
            print("Usage: python manual_prompt_test.py [chunk_index]")
    else:
        # Run full test
        test_manual_prompt()
