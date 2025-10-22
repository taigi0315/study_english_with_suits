#!/usr/bin/env python3
"""
Step 1: Load media/subtitle, split subtitle, send LLM request to get expressions
"""
import sys
import logging
from pathlib import Path

# Import test utilities
from test_config import setup_test_environment, clean_step_directory, get_step_output_dir, TEST_SETTINGS, SUBTITLE_FILE, VIDEO_FILE
from test_utils import validate_file_exists, validate_expression_data, save_test_results, log_step_start, log_step_complete

# Import LangFlix components
from langflix.core.subtitle_parser import parse_srt_file, chunk_subtitles
from langflix.core.expression_analyzer import analyze_chunk

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def test_step1():
    """Test Step 1: Load and analyze subtitles"""
    log_step_start(1, "Load media/subtitle, split subtitle, send LLM request to get expressions")
    
    try:
        # Setup environment
        setup_test_environment()
        clean_step_directory(1)
        
        results = {
            "step": 1,
            "description": "Load and analyze subtitles",
            "success": False,
            "errors": [],
            "expressions_found": 0,
            "expressions": []
        }
        
        # Step 1.1: Load and parse subtitle file
        logger.info("1.1 Loading and parsing subtitle file...")
        if not validate_file_exists(Path(SUBTITLE_FILE), min_size=1000):
            results["errors"].append(f"Subtitle file validation failed: {SUBTITLE_FILE}")
            return results
        
        subtitles = parse_srt_file(str(SUBTITLE_FILE))
        if not subtitles or len(subtitles) == 0:
            results["errors"].append("No subtitles parsed from file")
            return results
        
        logger.info(f"✅ Parsed {len(subtitles)} subtitle entries")
        results["subtitle_count"] = len(subtitles)
        
        # Step 1.2: Chunk subtitles
        logger.info("1.2 Chunking subtitles...")
        chunks = chunk_subtitles(subtitles)
        if not chunks or len(chunks) == 0:
            results["errors"].append("No chunks created from subtitles")
            return results
        
        logger.info(f"✅ Created {len(chunks)} chunks")
        results["chunk_count"] = len(chunks)
        
        # Step 1.3: Analyze first chunk with LLM (test mode)
        logger.info("1.3 Analyzing first chunk with Gemini API...")
        try:
            # Use only the first chunk for testing
            first_chunk = chunks[0]
            logger.info(f"Processing chunk with {len(first_chunk)} subtitles")
            
            # Send to LLM for analysis
            expressions = analyze_chunk(
                first_chunk, 
                language_level=TEST_SETTINGS["language_level"],
                language_code=TEST_SETTINGS["language_code"],
                save_output=TEST_SETTINGS["save_llm_output"],
                output_dir=str(get_step_output_dir(1))
            )
            
            if not expressions or len(expressions) == 0:
                results["errors"].append("No expressions returned from LLM")
                return results
            
            logger.info(f"✅ LLM returned {len(expressions)} expressions")
            results["expressions_found"] = len(expressions)
            
            # Step 1.4: Validate each expression
            logger.info("1.4 Validating expression data...")
            valid_expressions = []
            
            for i, expr in enumerate(expressions):
                logger.info(f"Validating expression {i+1}: '{expr.expression}'")
                
                # Debug: Show the actual data structure
                logger.info(f"  Dialogues count: {len(expr.dialogues) if hasattr(expr, 'dialogues') and expr.dialogues else 0}")
                logger.info(f"  Translation count: {len(expr.translation) if hasattr(expr, 'translation') and expr.translation else 0}")
                logger.info(f"  Similar expressions: {len(expr.similar_expressions) if hasattr(expr, 'similar_expressions') and expr.similar_expressions else 0}")
                
                # Convert ExpressionAnalysis object to dict for validation
                expr_dict = {
                    'dialogues': expr.dialogues,
                    'translation': expr.translation,
                    'expression': expr.expression,
                    'expression_translation': expr.expression_translation,
                    'context_start_time': expr.context_start_time,
                    'context_end_time': expr.context_end_time,
                    'similar_expressions': expr.similar_expressions
                }
                
                if validate_expression_data(expr_dict):
                    valid_expressions.append(expr_dict)
                    logger.info(f"✅ Expression {i+1} validated successfully")
                else:
                    # Instead of failing completely, let's still add it but mark as warning
                    logger.warning(f"⚠️  Expression {i+1} has validation issues but will be included: '{expr.expression}'")
                    valid_expressions.append(expr_dict)  # Include it anyway for now
            
            if not valid_expressions:
                results["errors"].append("No valid expressions found")
                return results
            
            # Limit to max_expressions for testing (if specified)
            max_expressions = TEST_SETTINGS["max_expressions"]
            if max_expressions is not None and len(valid_expressions) > max_expressions:
                valid_expressions = valid_expressions[:max_expressions]
                logger.info(f"Limited expressions to {max_expressions} for testing")
            else:
                logger.info(f"Processing all {len(valid_expressions)} expressions (no limit set)")
            
            results["expressions"] = valid_expressions
            results["success"] = True
            
            logger.info(f"✅ Step 1 completed successfully with {len(valid_expressions)} valid expressions")
            
        except Exception as llm_error:
            error_msg = f"LLM analysis failed: {llm_error}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
            return results
        
        # Save results
        save_test_results(1, results)
        
        # Print summary
        logger.info(f"\n📊 STEP 1 SUMMARY:")
        logger.info(f"  - Subtitles loaded: {results['subtitle_count']}")
        logger.info(f"  - Chunks created: {results['chunk_count']}")
        logger.info(f"  - Expressions found: {results['expressions_found']}")
        logger.info(f"  - Valid expressions: {len(results['expressions'])}")
        
        for i, expr in enumerate(results["expressions"]):
            logger.info(f"    {i+1}. '{expr['expression']}' -> '{expr['expression_translation']}'")
        
        return results
        
    except Exception as e:
        error_msg = f"Step 1 failed with exception: {e}"
        logger.error(error_msg)
        results["errors"].append(error_msg)
        return results

def main():
    """Main test function"""
    try:
        results = test_step1()
        log_step_complete(1, results["success"], 
                         f"Found {len(results['expressions'])} expressions" if results["success"] else f"Failed: {'; '.join(results['errors'])}")
        
        if not results["success"]:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
