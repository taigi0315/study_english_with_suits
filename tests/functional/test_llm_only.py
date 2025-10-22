#!/usr/bin/env python3
"""
LLM-only test script for LangFlix
Tests expression analysis without video processing
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from langflix.core.subtitle_parser import parse_srt_file, chunk_subtitles
from langflix.core.expression_analyzer import analyze_chunk
from langflix.settings import DEFAULT_LANGUAGE_LEVEL
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_llm_analysis(subtitle_file: str, language_level: str = None, max_expressions: int = 5, save_output: bool = True):
    """
    Test LLM analysis without video processing
    
    Args:
        subtitle_file: Path to subtitle file
        language_level: Target language level
        max_expressions: Maximum expressions to find
        save_output: Whether to save LLM output for review
    """
    if language_level is None:
        language_level = DEFAULT_LANGUAGE_LEVEL
    
    logger.info(f"🧪 Testing LLM Analysis")
    logger.info(f"Subtitle file: {subtitle_file}")
    logger.info(f"Language level: {language_level}")
    logger.info(f"Max expressions: {max_expressions}")
    logger.info(f"Save output: {save_output}")
    
    try:
        # Step 1: Parse subtitles
        logger.info("Step 1: Parsing subtitles...")
        subtitles = parse_srt_file(subtitle_file)
        logger.info(f"Parsed {len(subtitles)} subtitle entries")
        
        # Step 2: Chunk subtitles
        logger.info("Step 2: Chunking subtitles...")
        chunks = chunk_subtitles(subtitles)
        logger.info(f"Created {len(chunks)} chunks")
        
        # Step 3: Analyze expressions
        logger.info("Step 3: Analyzing expressions...")
        all_expressions = []
        
        for i, chunk in enumerate(chunks):
            if len(all_expressions) >= max_expressions:
                break
                
            logger.info(f"Analyzing chunk {i+1}/{len(chunks)}...")
            
            try:
                # Create output directory for LLM output
                output_dir = "output/llm_review" if save_output else None
                
                expressions = analyze_chunk(
                    chunk, 
                    language_level=language_level,
                    save_output=save_output,
                    output_dir=output_dir
                )
                
                if expressions:
                    all_expressions.extend(expressions)
                    logger.info(f"Found {len(expressions)} expressions in chunk {i+1}")
                    
                    # Print found expressions
                    for j, expr in enumerate(expressions):
                        print(f"\n📝 Expression {len(all_expressions)-len(expressions)+j+1}:")
                        print(f"   Text: {expr.expression}")
                        print(f"   Translation: {expr.expression_translation}")
                        print(f"   Context: {expr.context_start_time} - {expr.context_end_time}")
                        print(f"   Similar: {', '.join(expr.similar_expressions)}")
                else:
                    logger.warning(f"No expressions found in chunk {i+1}")
                    
            except Exception as e:
                logger.error(f"Error analyzing chunk {i+1}: {e}")
                continue
        
        # Summary
        print(f"\n{'='*50}")
        print(f"🎯 LLM Analysis Summary")
        print(f"{'='*50}")
        print(f"📝 Total subtitles: {len(subtitles)}")
        print(f"📦 Total chunks: {len(chunks)}")
        print(f"💡 Total expressions: {len(all_expressions)}")
        print(f"🎯 Language level: {language_level}")
        
        if save_output:
            print(f"📁 LLM output saved to: output/llm_review/")
        
        print(f"{'='*50}")
        
        return all_expressions
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return []

def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test LLM analysis without video processing")
    parser.add_argument("--subtitle", required=True, help="Path to subtitle file")
    parser.add_argument("--language-level", default=DEFAULT_LANGUAGE_LEVEL, 
                       choices=['beginner', 'intermediate', 'advanced', 'mixed'],
                       help="Target language level")
    parser.add_argument("--max-expressions", type=int, default=5,
                       help="Maximum expressions to find")
    parser.add_argument("--no-save", action="store_true",
                       help="Don't save LLM output files")
    
    args = parser.parse_args()
    
    # Run test
    expressions = test_llm_analysis(
        subtitle_file=args.subtitle,
        language_level=args.language_level,
        max_expressions=args.max_expressions,
        save_output=not args.no_save
    )
    
    if expressions:
        print(f"\n✅ Test completed successfully! Found {len(expressions)} expressions.")
    else:
        print(f"\n❌ Test failed or no expressions found.")

if __name__ == "__main__":
    main()
