"""
LangFlix - Main execution script
End-to-end pipeline for learning English expressions from TV shows
"""
import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Union, Callable
from datetime import datetime
import ffmpeg

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import our modules
from langflix.core.subtitle_parser import parse_srt_file, chunk_subtitles
from langflix.core.expression_analyzer import analyze_chunk, group_expressions_by_context
from langflix.core.video_processor import VideoProcessor
from langflix.core.subtitle_processor import SubtitleProcessor
from langflix.core.video_editor import VideoEditor
from langflix.services.output_manager import OutputManager, create_output_structure
from langflix.core.models import ExpressionAnalysis, ExpressionGroup
from langflix.utils.filename_utils import sanitize_for_expression_filename
from langflix import settings

# Database imports (optional)
try:
    from langflix.db import db_manager, MediaCRUD, ExpressionCRUD, ProcessingJobCRUD
    from langflix.db.models import Media, Expression, ProcessingJob
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    logger.warning("Database modules not available. Database integration disabled.")

# Configure structured logging
def setup_logging(verbose: bool = False):
    """
    Setup structured logging configuration
    
    Args:
        verbose: If True, enable DEBUG level logging
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-15s:%(lineno)-4d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Clear existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Console handler (simple format)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_formatter)
    
    # File handler (detailed format)
    file_handler = logging.FileHandler('langflix.log', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # Always debug level in file
    file_handler.setFormatter(detailed_formatter)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=[console_handler, file_handler],
        force=True
    )
    
    # Set specific logger levels
    logging.getLogger('ffmpeg').setLevel(logging.WARNING)  # Reduce ffmpeg noise

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)
logger.info(f"Logging configured with level: {logging.getLevelName(logger.level)}")


def validate_and_sanitize_path(path_str: str, path_type: str = "file") -> Path:
    """
    Validate and sanitize user-provided file/directory paths.
    
    Args:
        path_str: Input path string from user
        path_type: Type of path ("file", "dir", "subtitle", "video")
        
    Returns:
        Validated and sanitized Path object
        
    Raises:
        ValueError: If path is invalid or doesn't exist when required
        FileNotFoundError: If required file/directory doesn't exist
    """
    if not path_str:
        raise ValueError(f"{path_type} path cannot be empty")
    
    # Basic sanitization - prevent path traversal attacks
    path_str = path_str.strip()
    if ".." in path_str:
        logger.warning(f"Path traversal detected in path: {path_str}")
        # Don't raise error immediately, let resolve() handle it, but log the warning
    
    path = Path(path_str).resolve()  # This will resolve any .. and normalize the path
    
    # Additional validation based on path type
    if path_type == "subtitle":
        if not path.exists():
            raise FileNotFoundError(f"Subtitle file not found: {path}")
        if not path.suffix.lower() in ['.srt', '.vtt']:
            raise ValueError(f"Invalid subtitle file format. Expected .srt or .vtt, got: {path.suffix}")
        if not path.is_file():
            raise ValueError(f"Subtitle path is not a file: {path}")
    
    elif path_type == "video":
        if path.is_file() and not path.exists():
            raise FileNotFoundError(f"Video file not found: {path}")
        elif path.is_dir() and not path.exists():
            raise FileNotFoundError(f"Video directory not found: {path}")
    
    elif path_type == "dir":
        # For output directories, we can create them if they don't exist
        # But validate the parent directory exists
        if not path.parent.exists():
            raise FileNotFoundError(f"Parent directory for {path} does not exist")
    
    return path


def validate_input_arguments(args) -> None:
    """
    Validate all input arguments before processing.
    
    Args:
        args: Parsed command line arguments
    """
    try:
        # Validate subtitle file
        logger.info(f"Validating subtitle file: {args.subtitle}")
        subtitle_path = validate_and_sanitize_path(args.subtitle, "subtitle")
        logger.info(f"✅ Subtitle file validated: {subtitle_path}")
        
        # Validate video directory
        logger.info(f"Validating video directory: {args.video_dir}")
        video_path = validate_and_sanitize_path(args.video_dir, "video")
        if not video_path.is_dir():
            raise ValueError(f"Video directory path is not a directory: {video_path}")
        logger.info(f"✅ Video directory validated: {video_path}")
        
        # Validate output directory (will be created if needed)
        logger.info(f"Validating output directory: {args.output_dir}")
        output_path = validate_and_sanitize_path(args.output_dir, "dir")
        logger.info(f"✅ Output directory validated: {output_path}")
        
        # Update args with resolved paths
        args.subtitle = str(subtitle_path)
        args.video_dir = str(video_path)
        args.output_dir = str(output_path)
        
        logger.info("All input paths validated successfully")
        
    except (ValueError, FileNotFoundError) as e:
        logger.error(f"Input validation failed: {e}")
        raise


class LangFlixPipeline:
    """
    Main pipeline class for processing TV show content into learning materials
    """
    
    def __init__(self, subtitle_file: str, video_dir: str = "assets/media", 
                 output_dir: str = "output", language_code: str = "ko",
                 progress_callback: Optional[Callable[[int, str], None]] = None,
                 series_name: str = None, episode_name: str = None,
                 video_file: str = None,
                 enable_expression_grouping: bool = True):
        """
        Initialize the LangFlix pipeline
        
        Args:
            subtitle_file: Path to subtitle file
            video_dir: Directory containing video files
            output_dir: Directory for output files
            language_code: Target language code (e.g., 'ko', 'ja', 'zh')
            progress_callback: Optional callback function(progress: int, message: str) -> None
            series_name: Optional series name (if not provided, extracted from subtitle path)
            episode_name: Optional episode name (if not provided, extracted from subtitle path)
            video_file: Optional direct path to video file (if not provided, searched in video_dir)
        """
        self.subtitle_file = Path(subtitle_file)
        self.video_dir = Path(video_dir)
        self.output_dir = Path(output_dir)
        self.language_code = language_code
        self.progress_callback = progress_callback
        self.video_file = Path(video_file) if video_file else None
        
        # Create organized output structure (pass series_name/episode_name if provided)
        self.paths = create_output_structure(
            str(self.subtitle_file), 
            language_code, 
            str(self.output_dir),
            series_name=series_name,
            episode_name=episode_name
        )
        
        # Extract series and episode names from paths
        self.series_name = self.paths['series_name']
        self.episode_name = self.paths['episode_name']
        
        # Initialize processors
        self.video_processor = VideoProcessor(str(self.video_dir), video_file=str(self.video_file) if self.video_file else None)
        self.subtitle_processor = SubtitleProcessor(str(self.subtitle_file))
        self.video_editor = VideoEditor(str(self.paths['language']['final_videos']), self.language_code, self.episode_name)
        
        # Pipeline state
        self.subtitles = []
        self.chunks = []
        self.expressions = []
        self.expression_groups = []  # Grouped expressions by context
        self.processed_expressions = 0
        self.enable_expression_grouping = enable_expression_grouping
        
    def run(self, max_expressions: int = None, dry_run: bool = False, language_level: str = None, save_llm_output: bool = False, test_mode: bool = False, no_shorts: bool = False) -> Dict[str, Any]:
        """
        Run the complete pipeline
        
        Args:
            max_expressions: Maximum number of expressions to process
            dry_run: If True, only analyze without creating video files
            language_level: Target language level (beginner, intermediate, advanced, mixed)
            save_llm_output: If True, save LLM responses to files for review
            test_mode: If True, process only the first chunk for testing
            no_shorts: If True, skip creating short-format videos
            
        Returns:
            Dictionary with processing results
        """
        try:
            logger.info("🎬 Starting LangFlix Pipeline")
            logger.info(f"Subtitle file: {self.subtitle_file}")
            logger.info(f"Video directory: {self.video_dir}")
            logger.info(f"Output directory: {self.output_dir}")
            
            # Initialize database if enabled
            media_id = None
            if DB_AVAILABLE and settings.get_database_enabled():
                logger.info("📊 Database integration enabled")
                try:
                    db_manager.initialize()
                    db = db_manager.get_session()
                    try:
                        # Create media record
                        media = MediaCRUD.create(
                            db=db,
                            show_name=settings.get_show_name(),
                            episode_name=self.episode_name,
                            language_code=self.language_code,
                            subtitle_file_path=str(self.subtitle_file),
                            video_file_path=str(self.video_dir)
                        )
                        media_id = str(media.id)
                        logger.info(f"Created media record: {media_id}")
                    except Exception as e:
                        logger.error(f"Failed to create media record: {e}")
                        logger.warning("⚠️ Continuing pipeline without database integration")
                        db.rollback()
                        media_id = None  # Disable database operations for this run
                    finally:
                        db.close()
                except Exception as e:
                    logger.error(f"Failed to initialize database connection: {e}")
                    logger.warning("⚠️ Database connection failed. Continuing pipeline in file-only mode.")
                    logger.warning("⚠️ To disable database integration, set 'database.enabled: false' in config.yaml")
                    media_id = None  # Disable database operations for this run
            else:
                logger.info("📁 File-only mode (database disabled)")
            
            # Step 1: Parse subtitles
            logger.info("Step 1: Parsing subtitles...")
            if self.progress_callback:
                self.progress_callback(10, "Parsing subtitles...")
            self.subtitles = self._parse_subtitles()
            if not self.subtitles:
                raise ValueError("No subtitles found")
            
            # Step 2: Chunk subtitles
            logger.info("Step 2: Chunking subtitles...")
            if self.progress_callback:
                self.progress_callback(20, "Chunking subtitles...")
            self.chunks = chunk_subtitles(self.subtitles)
            logger.info(f"Created {len(self.chunks)} chunks")
            
            # Step 3: Analyze expressions
            logger.info("Step 3: Analyzing expressions...")
            if test_mode:
                logger.info("🧪 TEST MODE: Processing only first chunk")
            if self.progress_callback:
                self.progress_callback(30, "Analyzing expressions...")
            self.expressions = self._analyze_expressions(max_expressions, language_level, save_llm_output, test_mode)
            if not self.expressions:
                logger.error("❌ No expressions found after analysis")
                logger.error("This could be due to:")
                logger.error("  1. LLM API response parsing failure")
                logger.error("  2. All expressions failed validation")
                logger.error("  3. Empty or invalid subtitle chunks")
                logger.error("  4. Gemini API response format issue")
                # In test mode, allow continuing with empty expressions for debugging
                if test_mode:
                    logger.warning("⚠️ TEST MODE: Continuing with empty expressions for debugging")
                    self.expressions = []
                    self.expression_groups = []
                else:
                    raise ValueError("No expressions found")
            
            # Group expressions by context (if enabled and we have expressions)
            if self.enable_expression_grouping and len(self.expressions) > 0:
                logger.info("Grouping expressions by shared context...")
                self.expression_groups = group_expressions_by_context(self.expressions)
                
                # Log grouping statistics
                single_expr_groups = sum(1 for g in self.expression_groups if len(g.expressions) == 1)
                multi_expr_groups = sum(1 for g in self.expression_groups if len(g.expressions) > 1)
                
                logger.info(
                    f"Created {len(self.expression_groups)} expression groups: "
                    f"{single_expr_groups} single-expression groups, {multi_expr_groups} multi-expression groups"
                )
                
                if multi_expr_groups > 0:
                    logger.info(f"Efficiency gain: {len(self.expressions) - len(self.expression_groups)} duplicate context clips avoided")
            else:
                # Create single-expression groups for backward compatibility
                logger.info("Creating single-expression groups (grouping disabled or single expression)")
                self.expression_groups = [
                    ExpressionGroup(
                        context_start_time=expr.context_start_time,
                        context_end_time=expr.context_end_time,
                        expressions=[expr]
                    )
                    for expr in self.expressions
                ]
            
            # Save expressions to database if enabled and media_id is available
            if DB_AVAILABLE and settings.get_database_enabled() and media_id:
                try:
                    logger.info("Step 3.5: Saving expressions to database...")
                    self._save_expressions_to_database(media_id)
                except Exception as e:
                    logger.error(f"Failed to save expressions to database: {e}")
                    logger.warning("⚠️ Continuing pipeline without saving expressions to database")
            
            # Step 4: Process expressions (if not dry run and expressions exist)
            if not dry_run and self.expressions:
                logger.info("Step 4: Processing expressions...")
                if self.progress_callback:
                    self.progress_callback(50, "Processing expressions...")
                self._process_expressions()
                
                # Step 5: Create educational videos (only if expressions exist)
                logger.info("Step 5: Creating educational videos...")
                if self.progress_callback:
                    self.progress_callback(70, "Creating educational videos...")
                self._create_educational_videos()
                
                # Step 6: Create short-format videos (unless disabled)
                if not no_shorts:
                    logger.info("Step 6: Creating short-format videos...")
                    if self.progress_callback:
                        self.progress_callback(80, "Creating short-format videos...")
                    self._create_short_videos()
                else:
                    logger.info("Step 6: Skipping short-format videos (--no-shorts flag)")
            elif not dry_run and not self.expressions:
                logger.warning("⚠️ Skipping expression processing - no expressions found")
                if self.progress_callback:
                    self.progress_callback(80, "No expressions found, skipping video creation...")
            else:
                logger.info("Step 4: Dry run - skipping video processing")
            
            # Step 7: Generate summary
            if self.progress_callback:
                self.progress_callback(95, "Generating summary...")
            summary = self._generate_summary()
            
            # Step 8: Cleanup temporary files
            logger.info("Step 8: Cleaning up temporary files...")
            if self.progress_callback:
                self.progress_callback(98, "Cleaning up temporary files...")
            self._cleanup_resources()
            
            if self.progress_callback:
                self.progress_callback(100, "Pipeline completed successfully!")
            logger.info("✅ Pipeline completed successfully!")
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            raise
    
    def _parse_subtitles(self) -> List[Dict[str, Any]]:
        """Parse subtitle file"""
        try:
            subtitles = parse_srt_file(str(self.subtitle_file))
            logger.info(f"Parsed {len(subtitles)} subtitle entries")
            return subtitles
        except Exception as e:
            logger.error(f"Error parsing subtitles: {e}")
            raise
    
    def _analyze_expressions(self, max_expressions: int = None, language_level: str = None, save_llm_output: bool = False, test_mode: bool = False) -> List[ExpressionAnalysis]:
        """Analyze expressions from subtitle chunks (parallel or sequential)"""
        import time
        
        # In test mode, process only the first chunk
        chunks_to_process = [self.chunks[0]] if test_mode and self.chunks else self.chunks
        
        # Check if parallel processing is enabled
        parallel_enabled = settings.get_parallel_llm_processing_enabled()
        
        # Use parallel processing if enabled and we have multiple chunks (or not in test mode with multiple chunks)
        should_use_parallel = parallel_enabled and len(chunks_to_process) > 1 and not test_mode
        
        if should_use_parallel:
            logger.info(f"Using PARALLEL processing for {len(chunks_to_process)} chunks")
            return self._analyze_expressions_parallel(chunks_to_process, max_expressions, language_level, save_llm_output)
        else:
            logger.info(f"Using SEQUENTIAL processing for {len(chunks_to_process)} chunks")
            return self._analyze_expressions_sequential(chunks_to_process, max_expressions, language_level, save_llm_output, test_mode)
    
    def _analyze_expressions_parallel(
        self,
        chunks: List[List[Dict[str, Any]]],
        max_expressions: int = None,
        language_level: str = None,
        save_llm_output: bool = False
    ) -> List[ExpressionAnalysis]:
        """Analyze expressions in parallel using ExpressionBatchProcessor"""
        import time
        from langflix.core.parallel_processor import ExpressionBatchProcessor
        
        # Get parallel processor configuration
        max_workers = settings.get_parallel_llm_max_workers()
        timeout_per_chunk = settings.get_parallel_llm_timeout()
        
        # Get output directory for LLM outputs if save_llm_output is enabled
        output_dir = None
        if save_llm_output:
            try:
                metadata_paths = self.paths.get('episode', {}).get('metadata', {})
                if metadata_paths and 'llm_outputs' in metadata_paths:
                    output_dir = str(metadata_paths['llm_outputs'])
                else:
                    episode_dir = self.paths.get('episode', {}).get('episode_dir')
                    if episode_dir:
                        output_dir = str(episode_dir / 'llm_outputs')
                        Path(output_dir).mkdir(parents=True, exist_ok=True)
            except (KeyError, AttributeError) as e:
                logger.warning(f"Could not determine LLM output directory: {e}. LLM outputs will not be saved.")
                output_dir = None
        
        # Progress callback
        completed_chunks = [0]
        total_chunks = len(chunks)
        
        def progress_callback(completed: int, total: int):
            completed_chunks[0] = completed
            progress_pct = int((completed / total) * 100) if total > 0 else 0
            logger.info(f"Analyzed {completed}/{total} chunks ({progress_pct}%)")
            if self.progress_callback:
                self.progress_callback(30 + (progress_pct * 0.5), f"Analyzing expressions... {completed}/{total} chunks")
        
        # Create ExpressionBatchProcessor with configuration
        processor = ExpressionBatchProcessor(max_workers=max_workers)
        
        # Analyze chunks in parallel
        logger.info(f"Starting parallel analysis of {len(chunks)} chunks with {max_workers} workers")
        start_time = time.time()
        
        # Use ExpressionBatchProcessor directly (no sequential loop!)
        all_results = processor.analyze_expression_chunks(
            chunks,
            language_level=language_level,
            language_code=self.language_code,
            save_output=save_llm_output,
            output_dir=output_dir,
            progress_callback=progress_callback
        )
        
        duration = time.time() - start_time
        logger.info(f"Parallel analysis complete in {duration:.2f}s")
        
        # Flatten results from all chunks
        all_expressions = []
        for chunk_results in all_results:
            if chunk_results:  # Skip empty results (failed chunks)
                all_expressions.extend(chunk_results)
        
        logger.info(f"Total expressions found: {len(all_expressions)}")
        
        # Limit to max_expressions if specified
        limited_expressions = all_expressions[:max_expressions] if max_expressions else all_expressions
        logger.info(f"Processing {len(limited_expressions)} expressions")
        
        # Find expression timing for each expression
        logger.info("Finding exact expression timings from subtitles...")
        for expression in limited_expressions:
            try:
                expression_start, expression_end = self.subtitle_processor.find_expression_timing(expression)
                expression.expression_start_time = expression_start
                expression.expression_end_time = expression_end
                logger.info(f"Expression '{expression.expression}' timing: {expression_start} to {expression_end}")
            except Exception as e:
                logger.warning(f"Could not find timing for expression '{expression.expression}': {e}")
        
        return limited_expressions
    
    def _analyze_expressions_sequential(
        self,
        chunks: List[List[Dict[str, Any]]],
        max_expressions: int = None,
        language_level: str = None,
        save_llm_output: bool = False,
        test_mode: bool = False
    ) -> List[ExpressionAnalysis]:
        """Analyze expressions sequentially (original implementation)"""
        all_expressions = []
        
        for i, chunk in enumerate(chunks):
            if max_expressions is not None and len(all_expressions) >= max_expressions:
                break
                
            chunk_index = 0 if test_mode else i
            total_chunks = 1 if test_mode else len(self.chunks)
            
            logger.info(f"Analyzing chunk {chunk_index+1}/{total_chunks}{' (TEST MODE)' if test_mode else ''}...")
            
            try:
                # Get output directory for LLM outputs if save_llm_output is enabled
                output_dir = None
                if save_llm_output:
                    try:
                        metadata_paths = self.paths.get('episode', {}).get('metadata', {})
                        if metadata_paths and 'llm_outputs' in metadata_paths:
                            output_dir = str(metadata_paths['llm_outputs'])
                        else:
                            episode_dir = self.paths.get('episode', {}).get('episode_dir')
                            if episode_dir:
                                output_dir = str(episode_dir / 'llm_outputs')
                                Path(output_dir).mkdir(parents=True, exist_ok=True)
                    except (KeyError, AttributeError) as e:
                        logger.warning(f"Could not determine LLM output directory: {e}. LLM outputs will not be saved.")
                        output_dir = None
                
                expressions = analyze_chunk(chunk, language_level, self.language_code, save_llm_output, output_dir)
                if expressions:
                    all_expressions.extend(expressions)
                    logger.info(f"Found {len(expressions)} expressions in chunk {chunk_index+1}")
                else:
                    logger.warning(f"No expressions found in chunk {chunk_index+1}")
                    
            except Exception as e:
                logger.error(f"Error analyzing chunk {chunk_index+1}: {e}")
                continue
                
            # In test mode, break after first chunk
            if test_mode:
                break
        
        # Limit to max_expressions
        limited_expressions = all_expressions[:max_expressions] if max_expressions else all_expressions
        logger.info(f"Total expressions found: {len(limited_expressions)}")
        
        # Find expression timing for each expression
        logger.info("Finding exact expression timings from subtitles...")
        for expression in limited_expressions:
            try:
                expression_start, expression_end = self.subtitle_processor.find_expression_timing(expression)
                expression.expression_start_time = expression_start
                expression.expression_end_time = expression_end
                logger.info(f"Expression '{expression.expression}' timing: {expression_start} to {expression_end}")
            except Exception as e:
                logger.warning(f"Could not find timing for expression '{expression.expression}': {e}")
        
        return limited_expressions
    
    def _save_expressions_to_database(self, media_id: str):
        """Save expressions to database."""
        if not DB_AVAILABLE or not settings.get_database_enabled():
            return
        
        try:
            db = db_manager.get_session()
            try:
                for expression in self.expressions:
                    try:
                        ExpressionCRUD.create_from_analysis(
                            db=db,
                            media_id=media_id,
                            analysis_data=expression
                        )
                        logger.debug(f"Saved expression to database: {expression.expression}")
                    except Exception as e:
                        logger.error(f"Failed to save expression '{expression.expression}': {e}")
                        continue
                
                db.commit()
                logger.info(f"Saved {len(self.expressions)} expressions to database")
                
            except Exception as e:
                logger.error(f"Database error during expression save: {e}")
                db.rollback()
                logger.warning("⚠️ Failed to save expressions to database. Pipeline will continue.")
                # Don't raise - allow pipeline to continue
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            logger.warning("⚠️ Failed to connect to database. Pipeline will continue in file-only mode.")
            # Don't raise - allow pipeline to continue
    
    def _process_expressions(self):
        """Process each expression group (shared context clip + individual subtitles)"""
        from langflix.utils.temp_file_manager import get_temp_manager
        temp_manager = get_temp_manager()
        
        # Find video file (shared for all groups)
        video_file = self.video_processor.find_video_file(str(self.subtitle_file))
        if not video_file:
            logger.warning("No video file found, skipping expression processing")
            return
        
        # Cache for context clips to avoid duplicate extractions
        context_clip_cache: Dict[str, Path] = {}
        
        for group_idx, expression_group in enumerate(self.expression_groups):
            try:
                logger.info(
                    f"Processing expression group {group_idx+1}/{len(self.expression_groups)}: "
                    f"{len(expression_group.expressions)} expression(s)"
                )
                
                # Create context key for caching
                context_key = f"{expression_group.context_start_time}_{expression_group.context_end_time}"
                
                # Extract ONE context clip for the entire group (shared by all expressions)
                if context_key in context_clip_cache:
                    logger.info(f"Reusing cached context clip for group {group_idx+1}")
                    video_output = context_clip_cache[context_key]
                else:
                    # Create temp file for context clip
                    safe_group_name = f"group_{group_idx+1:02d}"
                    if len(expression_group.expressions) == 1:
                        safe_filename = sanitize_for_expression_filename(expression_group.expressions[0].expression)
                    else:
                        # For multi-expression groups, use a generic name
                        safe_filename = f"multi_expr_{len(expression_group.expressions)}"
                    
                    with temp_manager.create_temp_file(
                        suffix='.mkv',
                        prefix=f'temp_group_{group_idx+1:02d}_{safe_filename[:30]}_',
                        delete=False
                    ) as temp_file_path:
                        video_output = temp_file_path
                        temp_manager.register_file(video_output)
                    
                    # Extract context clip (shared by all expressions in group)
                    success = self.video_processor.extract_clip(
                        video_file,
                        expression_group.context_start_time,
                        expression_group.context_end_time,
                        video_output
                    )
                    
                    if success:
                        logger.info(f"✅ Shared context clip created for group {group_idx+1}: {video_output}")
                        context_clip_cache[context_key] = video_output
                    else:
                        logger.warning(f"❌ Failed to create context clip for group {group_idx+1}")
                        continue
                
                # Create subtitle files for EACH expression in the group
                for expr_idx, expression in enumerate(expression_group.expressions):
                    try:
                        safe_filename = sanitize_for_expression_filename(expression.expression)
                        
                        # Create subtitle file with group and expression index
                        if len(expression_group.expressions) > 1:
                            subtitle_filename = f"group_{group_idx+1:02d}_expr_{expr_idx+1:02d}_{safe_filename[:30]}.srt"
                        else:
                            # Single expression: use simple naming (backward compatible)
                            subtitle_filename = f"expression_{group_idx+1:02d}_{safe_filename[:30]}.srt"
                        
                        subtitle_output = self.paths['language']['subtitles'] / subtitle_filename
                        subtitle_output.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Create subtitle file
                        subtitle_success = self.subtitle_processor.create_dual_language_subtitle_file(
                            expression,
                            str(subtitle_output)
                        )
                        
                        if subtitle_success:
                            logger.info(f"✅ Subtitle file created: {subtitle_output}")
                            self.processed_expressions += 1
                        else:
                            logger.warning(f"❌ Failed to create subtitle file: {subtitle_output}")
                            
                    except Exception as e:
                        logger.error(f"Error processing expression {expr_idx+1} in group {group_idx+1}: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error processing expression group {group_idx+1}: {e}")
                continue
    
    def _create_educational_videos(self):
        """Create educational video sequences for each expression (using groups)"""
        logger.info(f"Creating educational videos for {len(self.expressions)} expressions in {len(self.expression_groups)} groups...")
        
        # Find all group context video files from temp directory
        from langflix.utils.temp_file_manager import get_temp_manager
        temp_manager = get_temp_manager()
        temp_dir = temp_manager.base_dir
        
        # Find temp_group_*.mkv files (shared context clips)
        group_video_files = list(temp_dir.glob("temp_group_*.mkv"))
        group_video_files.sort()
        
        # Create mapping from group index to video file
        # Pattern: temp_group_{group_idx:02d}_*.mkv
        group_video_map: Dict[int, Path] = {}
        for video_file in group_video_files:
            # Extract group index from filename
            filename = video_file.stem
            parts = filename.split('_')
            if len(parts) >= 3 and parts[0] == 'temp' and parts[1] == 'group':
                try:
                    group_idx = int(parts[2]) - 1  # Convert to 0-based index
                    group_video_map[group_idx] = video_file
                except ValueError:
                    logger.warning(f"Could not parse group index from filename: {filename}")
        
        # Get original video file for expression audio extraction
        original_video = self.video_processor.find_video_file(str(self.subtitle_file))
        
        logger.info(f"Found {len(group_video_map)} group context video files")
        logger.info(f"Original video file: {original_video}")
        
        educational_videos = []
        global_expression_index = 0  # Global index across all expressions for voice alternation
        
        # Iterate over expression groups
        for group_idx, expression_group in enumerate(self.expression_groups):
            try:
                # Get shared context video for this group
                if group_idx not in group_video_map:
                    logger.warning(f"No context video found for group {group_idx+1}, skipping")
                    # Increment global index for skipped expressions
                    global_expression_index += len(expression_group.expressions)
                    continue
                
                context_video = group_video_map[group_idx]
                expression_source_video = str(original_video) if original_video else str(context_video)
                
                logger.info(
                    f"Processing group {group_idx+1}/{len(self.expression_groups)}: "
                    f"{len(expression_group.expressions)} expression(s), "
                    f"using shared context clip: {context_video.name}"
                )
                
                # Check if this is a multi-expression group
                is_multi_expression = len(expression_group.expressions) > 1
                
                if is_multi_expression:
                    # Multi-expression group: Create context video with multi-expression slide FIRST
                    try:
                        logger.info(
                            f"Creating context video with multi-expression slide for group {group_idx+1} "
                            f"({len(expression_group.expressions)} expressions)"
                        )
                        
                        # Add subtitles to context video first
                        context_with_subtitles = self.video_editor._add_subtitles_to_context(
                            str(context_video), expression_group.expressions[0]  # Use first expression for subtitle context
                        )
                        
                        # Create context video with multi-expression slide
                        context_video_with_slide = self.video_editor.create_context_video_with_multi_slide(
                            context_with_subtitles,  # Context video with subtitles
                            expression_group
                        )
                        
                        educational_videos.append(context_video_with_slide)
                        logger.info(f"✅ Context video with multi-expression slide created: {context_video_with_slide}")
                        
                    except Exception as e:
                        logger.error(
                            f"Error creating context video with multi-slide for group {group_idx+1}: {e}"
                        )
                        # Continue to create expression videos even if context video failed
                
                # Create educational video for EACH expression in the group
                # Each expression gets its own video with its own slide
                for expr_idx, expression in enumerate(expression_group.expressions):
                    try:
                        logger.info(
                            f"Creating educational video for expression {global_expression_index+1}/{len(self.expressions)}: "
                            f"'{expression.expression}' (group {group_idx+1}, expr {expr_idx+1})"
                        )
                        
                        # Create educational sequence with global expression index for voice alternation
                        # This creates: left (context + expression repeat) | right (expression's own slide)
                        educational_video = self.video_editor.create_educational_sequence(
                            expression,
                            str(context_video),  # Shared context clip for the group
                            expression_source_video,  # Original video for expression audio
                            expression_index=global_expression_index  # Global index for voice alternation
                        )
                        
                        educational_videos.append(educational_video)
                        logger.info(f"✅ Educational video created for expression: {educational_video}")
                        global_expression_index += 1
                        
                    except Exception as e:
                        logger.error(
                            f"Error creating educational video for expression {expr_idx+1} "
                            f"in group {group_idx+1}: {e}"
                        )
                        global_expression_index += 1
                        continue
                        
            except Exception as e:
                logger.error(f"Error processing expression group {group_idx+1}: {e}")
                # Increment global index for all expressions in failed group
                global_expression_index += len(expression_group.expressions)
                continue
        
        # Create final concatenated video
        if educational_videos:
            self._create_final_video(educational_videos)
        else:
            # Fallback: Try to create final video from temp files if available
            self._create_final_video_from_temp_files()
        
        # Clean up temp video clips after processing using temp manager
        logger.info("Cleaning up temporary video clips...")
        for video_file in group_video_files:
            try:
                if video_file.exists():
                    # Remove from manager's tracking if registered
                    if Path(video_file) in temp_manager.temp_files:
                        temp_manager.temp_files.remove(Path(video_file))
                    Path(video_file).unlink()
                    logger.debug(f"Deleted temp file: {video_file}")
            except Exception as e:
                logger.warning(f"Could not delete temp file {video_file}: {e}")
    
    def _create_short_videos(self):
        """Create short-format videos for social media."""
        try:
            # Check if short video generation is enabled
            from langflix import settings
            if not settings.is_short_video_enabled():
                logger.info("Short video generation is disabled in configuration")
                return
                
            logger.info("Creating short-format videos...")
            
            # Get context videos with subtitles
            context_videos_dir = self.paths['language']['context_videos']
            context_videos = sorted(list(context_videos_dir.glob("context_*.mkv")))
            
            logger.info(f"Found {len(context_videos)} context videos for short video creation")
            
            if not context_videos:
                logger.warning("No context videos found for short video creation")
                return
            
            short_format_videos = []
            
            # Create a mapping from expression names to context videos
            context_video_map = {}
            for context_video in context_videos:
                # Extract expression name from filename: context_{expression_name}.mkv
                video_name = context_video.stem  # Remove .mkv extension
                if video_name.startswith('context_'):
                    expression_name = video_name[8:]  # Remove 'context_' prefix
                    context_video_map[expression_name] = context_video
            
            logger.info(f"Context video mapping: {list(context_video_map.keys())}")
            
            for i, expression in enumerate(self.expressions):
                # Sanitize expression name to match filename format
                safe_expression_name = sanitize_for_expression_filename(expression.expression)
                logger.info(f"Looking for context video: context_{safe_expression_name}.mkv")
                
                if safe_expression_name in context_video_map:
                    context_video = context_video_map[safe_expression_name]
                    logger.info(f"Creating short format video {i+1}/{len(self.expressions)}: {expression.expression}")
                    logger.info(f"Using context video: {context_video.name}")
                    
                    try:
                        output_path, duration = self.video_editor.create_short_format_video(
                            str(context_video), expression, i, str(self.subtitle_file)
                        )
                        short_format_videos.append((output_path, duration))
                        logger.info(f"✅ Short format video created: {output_path} (duration: {duration:.2f}s)")
                    except Exception as e:
                        logger.error(f"Error creating short format video for expression {i+1}: {e}")
                        continue
                else:
                    logger.warning(f"No context video found for expression '{expression.expression}' (sanitized: '{safe_expression_name}')")
                    continue
            
            if short_format_videos:
                # Batch into ~120s videos using configuration
                from langflix import settings
                target_duration = settings.get_short_video_target_duration()
                batch_videos = self.video_editor.create_batched_short_videos(
                    short_format_videos, target_duration=target_duration
                )
                
                logger.info(f"✅ Created {len(batch_videos)} short video batches")
                for batch_path in batch_videos:
                    logger.info(f"  - {batch_path}")
            else:
                logger.warning("No short format videos were created successfully")
                
        except Exception as e:
            logger.error(f"Error creating short videos: {e}")
            raise
    
    def _create_final_video(self, educational_videos: List[str]):
        """Create final concatenated educational video with fade transitions"""
        try:
            logger.info(f"Creating final video from {len(educational_videos)} educational sequences...")
            
            if not educational_videos:
                logger.error("No educational videos provided for final video creation")
                return
            
            # Validate that all video files exist and are individual expression videos
            valid_videos = []
            for video_path in educational_videos:
                video_name = Path(video_path).name
                # Only include individual educational videos, not slides or context videos
                if video_name.startswith('educational_') and Path(video_path).exists() and Path(video_path).stat().st_size > 1000:
                    valid_videos.append(video_path)
                    logger.info(f"Valid video: {video_name}")
                else:
                    logger.warning(f"Skipping invalid or non-educational video: {video_path}")
            
            if not valid_videos:
                logger.error("No valid educational videos found for final video creation")
                return
            
            logger.info(f"Using {len(valid_videos)} valid videos for final concatenation")
            
            # Use long-form naming convention
            episode_name = self.paths.get('episode_name', 'Unknown_Episode')
            original_filename = Path(self.subtitle_file).stem if hasattr(self, 'subtitle_file') else 'content'
            final_video_filename = f"long-form_{episode_name}_{original_filename}.mkv"
            final_video_path = self.paths['language']['final_videos'] / final_video_filename
            
            # Create concat file
            concat_file = self.paths['language']['final_videos'] / "final_concat.txt"
            with open(concat_file, 'w') as f:
                for video_path in valid_videos:
                    f.write(f"file '{Path(video_path).absolute()}'\n")
            
            # Concatenate all educational videos with proper audio handling
            # Use fade transitions between expressions for smoother viewing
            (
                ffmpeg
                .input(str(concat_file), format='concat', safe=0)
                .output(str(final_video_path), 
                       vcodec='libx264', 
                       acodec='aac', 
                       preset='fast',
                       ac=2,  # Force stereo audio
                       ar=48000,  # Set sample rate
                       crf=23)  # Good quality
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            # Verify final video was created successfully
            if final_video_path.exists() and final_video_path.stat().st_size > 10000:
                logger.info(f"✅ Final educational video created: {final_video_path} ({final_video_path.stat().st_size} bytes)")
            else:
                logger.error(f"Final video creation failed or resulted in empty file: {final_video_path}")
                
        except Exception as e:
            logger.error(f"Error creating final video: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def _create_final_video_from_temp_files(self):
        """Create final video from existing temp files"""
        try:
            logger.info("Attempting to create final video from temp files...")
            
            final_videos_dir = self.paths['language']['final_videos']
            
            # Find temp files
            context_videos = sorted(list(final_videos_dir.glob("temp_context_with_subs_*.mkv")))
            slide_videos = sorted(list(final_videos_dir.glob("temp_slide_*.mkv")))
            
            logger.info(f"Found {len(context_videos)} context videos and {len(slide_videos)} slide videos")
            
            if not context_videos or not slide_videos:
                logger.warning("No temp files found for final video creation")
                return
            
            # Create sequence: context1, slide1, context2, slide2, ...
            video_sequence = []
            for i in range(min(len(context_videos), len(slide_videos))):
                video_sequence.append(str(context_videos[i].absolute()))
                video_sequence.append(str(slide_videos[i].absolute()))
            
            logger.info(f"Creating final video from {len(video_sequence)} components")
            
            # Final video path - use long-form naming convention
            episode_name = self.paths.get('episode_name', 'Unknown_Episode')
            original_filename = Path(self.subtitle_file).stem if hasattr(self, 'subtitle_file') else 'content'
            final_video_filename = f"long-form_{episode_name}_{original_filename}.mkv"
            final_video_path = final_videos_dir / final_video_filename
            
            # Create concat file
            concat_file = final_videos_dir / "final_concat.txt"
            with open(concat_file, 'w') as f:
                for video_path in video_sequence:
                    f.write(f"file '{video_path}'\n")
            
            # Concatenate videos
            (
                ffmpeg
                .input(str(concat_file), format='concat', safe=0)
                .output(str(final_video_path),
                       vcodec='libx264',
                       acodec='aac',
                       preset='fast',
                       crf=23)
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info(f"✅ Final video created from temp files: {final_video_path}")
            
        except Exception as e:
            logger.error(f"Error creating final video from temp files: {e}")
    
    def _cleanup_resources(self):
        """Clean up temporary files and resources"""
        try:
            # Clean up VideoEditor temporary files
            if hasattr(self, 'video_editor'):
                self.video_editor._cleanup_temp_files()
                logger.info("✅ VideoEditor temporary files cleaned up")
        except Exception as e:
            logger.warning(f"Failed to cleanup VideoEditor resources: {e}")
    
    def _generate_summary(self) -> Dict[str, Union[int, str]]:
        """Generate processing summary"""
        return {
            "total_subtitles": len(self.subtitles),
            "total_chunks": len(self.chunks),
            "total_expressions": len(self.expressions),
            "processed_expressions": self.processed_expressions,
            "output_directory": str(self.paths['episode']['episode_dir']),
            "language_code": self.language_code,
            "series_name": self.paths['series_name'],
            "episode_name": self.paths['episode_name'],
            "timestamp": datetime.now().isoformat()
        }


def main():
    """Main entry point for LangFlix"""
    parser = argparse.ArgumentParser(
        description="LangFlix - Learn English expressions from TV shows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m langflix.main --subtitle "assets/subtitles/Suits - season 1.en/Suits - 1x01 - Pilot.720p.WEB-DL.en.srt"
  python -m langflix.main --subtitle subtitle.srt --video-dir assets/media --output-dir results
  python -m langflix.main --subtitle subtitle.srt --max-expressions 5 --dry-run
        """
    )
    
    parser.add_argument(
        "--subtitle", 
        required=True,
        help="Path to subtitle file (.srt)"
    )
    
    parser.add_argument(
        "--video-dir",
        default="assets/media",
        help="Directory containing video files (default: assets/media)"
    )
    
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Output directory for generated files (default: output)"
    )
    
    parser.add_argument(
        "--max-expressions",
        type=int,
        default=None,
        help="Maximum number of expressions to process (default: no limit - process all found expressions)"
    )
    
    parser.add_argument(
        "--language-level",
        type=str,
        default=settings.DEFAULT_LANGUAGE_LEVEL,
        choices=['beginner', 'intermediate', 'advanced', 'mixed'],
        help=f"Target language level for expression analysis (default: {settings.DEFAULT_LANGUAGE_LEVEL})"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze expressions without creating video files"
    )
    
    parser.add_argument(
        "--save-llm-output",
        action="store_true",
        help="Save LLM responses to files for review"
    )
    
    parser.add_argument(
        "--language-code", "--language",
        type=str,
        default="ko",
        choices=['ko', 'ja', 'zh', 'es', 'fr'],
        help="Target language code for output (default: ko for Korean)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Process only the first chunk for faster testing"
    )
    
    parser.add_argument(
        "--no-shorts",
        action="store_true",
        help="Skip creating short-format videos (default: create short videos)"
    )
    
    args = parser.parse_args()

    # Setup logging based on verbose flag
    setup_logging(verbose=args.verbose)
    
    try:
        # Validate input arguments before processing
        validate_input_arguments(args)
        
        # Initialize pipeline
        pipeline = LangFlixPipeline(
            subtitle_file=args.subtitle,
            video_dir=args.video_dir,
            output_dir=args.output_dir,
            language_code=args.language_code
        )
        
        # Run pipeline
        summary = pipeline.run(
            max_expressions=args.max_expressions,
            dry_run=args.dry_run,
            language_level=args.language_level,
            save_llm_output=args.save_llm_output,
            test_mode=args.test_mode,
            no_shorts=args.no_shorts
        )
        
        # Print summary
        print("\n" + "="*50)
        print("🎬 LangFlix Pipeline Summary")
        print("="*50)
        print(f"📝 Total subtitles: {summary['total_subtitles']}")
        print(f"📦 Total chunks: {summary['total_chunks']}")
        print(f"💡 Total expressions: {summary['total_expressions']}")
        print(f"✅ Processed expressions: {summary['processed_expressions']}")
        print(f"📁 Output directory: {summary['output_directory']}")
        print(f"⏰ Completed at: {summary['timestamp']}")
        print("="*50)
        
        if not args.dry_run:
            print(f"\n🎉 Check your results in: {summary['output_directory']}")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()