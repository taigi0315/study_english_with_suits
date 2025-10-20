"""
LangFlix - Main execution script
End-to-end pipeline for learning English expressions from TV shows
"""
import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import ffmpeg

# Import our modules
from .subtitle_parser import parse_srt_file, chunk_subtitles
from .expression_analyzer import analyze_chunk
from .video_processor import VideoProcessor
from .subtitle_processor import SubtitleProcessor
from .video_editor import VideoEditor
from .output_manager import OutputManager, create_output_structure
from .models import ExpressionAnalysis
from . import settings
from .storage import get_storage_backend
from .config.config_loader import ConfigLoader

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
                 output_dir: str = "output", language_code: str = "ko"):
        """
        Initialize the LangFlix pipeline
        
        Args:
            subtitle_file: Path to subtitle file
            video_dir: Directory containing video files
            output_dir: Directory for output files
            language_code: Target language code (e.g., 'ko', 'ja', 'zh')
        """
        self.original_subtitle_file = subtitle_file
        self.original_video_dir = video_dir
        self.language_code = language_code
        
        # Initialize storage backend
        self.storage = get_storage_backend()
        logger.info(f"Initialized storage backend: {self.storage.backend_type}")
        
        # Handle input file downloads from S3 if needed
        self.subtitle_file, self.video_dir = self._prepare_input_files(subtitle_file, video_dir, output_dir)
        self.output_dir = Path(output_dir)
        
        # Create organized output structure
        self.paths = create_output_structure(str(self.subtitle_file), language_code, str(self.output_dir))
        
        # Initialize processors
        self.video_processor = VideoProcessor(str(self.video_dir))
        self.subtitle_processor = SubtitleProcessor(str(self.subtitle_file))
        self.video_editor = VideoEditor(str(self.paths['language']['final_videos']), self.language_code)
        
        # Pipeline state
        self.subtitles = []
        self.chunks = []
        self.expressions = []
        self.processed_expressions = 0
        self.temp_files_created = []  # Track temporary files for cleanup
        
    def run(self, max_expressions: int = None, dry_run: bool = False, language_level: str = None, save_llm_output: bool = False, test_mode: bool = False) -> Dict[str, Any]:
        """
        Run the complete pipeline
        
        Args:
            max_expressions: Maximum number of expressions to process
            dry_run: If True, only analyze without creating video files
            language_level: Target language level (beginner, intermediate, advanced, mixed)
            save_llm_output: If True, save LLM responses to files for review
            test_mode: If True, process only the first chunk for testing
            
        Returns:
            Dictionary with processing results
        """
        try:
            logger.info("🎬 Starting LangFlix Pipeline")
            logger.info(f"Subtitle file: {self.subtitle_file}")
            logger.info(f"Video directory: {self.video_dir}")
            logger.info(f"Output directory: {self.output_dir}")
            
            # Step 1: Parse subtitles
            logger.info("Step 1: Parsing subtitles...")
            self.subtitles = self._parse_subtitles()
            if not self.subtitles:
                raise ValueError("No subtitles found")
            
            # Step 2: Chunk subtitles
            logger.info("Step 2: Chunking subtitles...")
            self.chunks = chunk_subtitles(self.subtitles)
            logger.info(f"Created {len(self.chunks)} chunks")
            
            # Step 3: Analyze expressions
            logger.info("Step 3: Analyzing expressions...")
            if test_mode:
                logger.info("🧪 TEST MODE: Processing only first chunk")
            self.expressions = self._analyze_expressions(max_expressions, language_level, save_llm_output, test_mode)
            if not self.expressions:
                raise ValueError("No expressions found")
            
            # Step 4: Process expressions (if not dry run)
            if not dry_run:
                logger.info("Step 4: Processing expressions...")
                self._process_expressions()
                
                # Step 5: Create educational videos
                logger.info("Step 5: Creating educational videos...")
                self._create_educational_videos()
                
                # Step 6: Upload outputs to S3 if needed
                logger.info("Step 6: Uploading outputs to storage...")
                self._upload_outputs()
            else:
                logger.info("Step 4: Dry run - skipping video processing")
            
            # Step 7: Generate summary
            summary = self._generate_summary()
            
            # Step 8: Cleanup temporary files
            logger.info("Step 8: Cleaning up temporary files...")
            self._cleanup_resources()
            
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
        """Analyze expressions from subtitle chunks"""
        all_expressions = []
        
        # In test mode, process only the first chunk
        chunks_to_process = [self.chunks[0]] if test_mode and self.chunks else self.chunks
        
        for i, chunk in enumerate(chunks_to_process):
            if max_expressions is not None and len(all_expressions) >= max_expressions:
                break
                
            chunk_index = 0 if test_mode else i
            total_chunks = 1 if test_mode else len(self.chunks)
            
            logger.info(f"Analyzing chunk {chunk_index+1}/{total_chunks}{' (TEST MODE)' if test_mode else ''}...")
            
            try:
                expressions = analyze_chunk(chunk, language_level, self.language_code, save_llm_output, str(self.paths['episode']['metadata']['llm_outputs']))
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
        limited_expressions = all_expressions[:max_expressions]
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
    
    def _process_expressions(self):
        """Process each expression (video + subtitles)"""
        for i, expression in enumerate(self.expressions):
            try:
                logger.info(f"Processing expression {i+1}/{len(self.expressions)}: {expression.expression}")
                
                # Find video file (handle S3 if needed)
                video_file = self._find_video_file_for_expression()
                if not video_file:
                    logger.warning(f"No video file found for expression {i+1}")
                    continue
                
                # Create output filenames using organized structure
                safe_expression = "".join(c for c in expression.expression if c.isalnum() or c in (' ', '-', '_')).rstrip()
                # Don't save raw clips - use temp directory
                import tempfile
                temp_dir = Path(tempfile.gettempdir())
                video_output = temp_dir / f"temp_expression_{i+1:02d}_{safe_expression[:30]}.mkv"
                subtitle_output = self.paths['language']['subtitles'] / f"expression_{i+1:02d}_{safe_expression[:30]}.srt"
                
                # Extract video clip to temp location
                success = self.video_processor.extract_clip(
                    video_file,
                    expression.context_start_time,
                    expression.context_end_time,
                    video_output
                )
                
                if success:
                    logger.info(f"✅ Video clip created: {video_output}")
                    
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
                else:
                    logger.warning(f"❌ Failed to create video clip: {video_output}")
                    
            except Exception as e:
                logger.error(f"Error processing expression {i+1}: {e}")
                continue
    
    def _create_educational_videos(self):
        """Create educational video sequences for each expression"""
        logger.info(f"Creating educational videos for {len(self.expressions)} expressions...")
        
        # First, find all actual video files that were created from temp directory
        import tempfile
        temp_dir = Path(tempfile.gettempdir())
        video_files = list(temp_dir.glob("temp_expression_*.mkv"))
        video_files.sort()
        
        # Get original video file for expression audio extraction
        original_video = self.video_processor.find_video_file(str(self.subtitle_file))
        
        logger.info(f"Found {len(video_files)} video files to process")
        logger.info(f"Original video file: {original_video}")
        
        educational_videos = []
        
        for i, expression in enumerate(self.expressions):
            try:
                logger.info(f"Creating educational video {i+1}/{len(self.expressions)}: {expression.expression}")
                
                # Find the corresponding video file - match by index
                if i < len(video_files):
                    context_video = video_files[i]
                    # Use original video for expression audio extraction
                    expression_source_video = str(original_video) if original_video else str(context_video)
                    
                    logger.info(f"Using context video: {context_video}")
                    logger.info(f"Using original video for expression audio: {expression_source_video}")
                    
                    # Create educational sequence
                    educational_video = self.video_editor.create_educational_sequence(
                        expression, 
                        str(context_video), 
                        expression_source_video  # Pass original video for expression audio
                    )
                    
                    educational_videos.append(educational_video)
                    logger.info(f"✅ Educational video created: {educational_video}")
                else:
                    logger.warning(f"No video file found for expression {i+1}")
                    continue
                
            except Exception as e:
                logger.error(f"Error creating educational video {i+1}: {e}")
                continue
        
        # Create final concatenated video
        if educational_videos:
            self._create_final_video(educational_videos)
        else:
            # Fallback: Try to create final video from temp files if available
            self._create_final_video_from_temp_files()
        
        # Clean up temp video clips after processing
        logger.info("Cleaning up temporary video clips...")
        for video_file in video_files:
            try:
                if video_file.exists():
                    video_file.unlink()
                    logger.debug(f"Deleted temp file: {video_file}")
            except Exception as e:
                logger.warning(f"Could not delete temp file {video_file}: {e}")
    
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
            
            final_video_path = self.paths['language']['final_videos'] / "final_educational_video_with_slides.mkv"
            
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
            
            # Final video path
            final_video_path = final_videos_dir / "final_educational_video_with_slides.mkv"
            
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
    
    def _sanitize_filename(self, text: str) -> str:
        """Sanitize text for filename"""
        import re
        sanitized = re.sub(r'[^\w\s-]', '', text)
        sanitized = re.sub(r'[-\s]+', '_', sanitized)
        return sanitized[:50]
    
    def _find_video_file_for_expression(self) -> Optional[Path]:
        """
        Find video file for processing, handling S3 downloads if needed
        
        Returns:
            Path to local video file, or None if not found
        """
        try:
            # First try to find video file using existing logic
            video_file = self.video_processor.find_video_file(str(self.subtitle_file))
            
            if video_file and video_file.exists():
                return video_file
            
            # If we have S3 video directory and no local file found, try to download from S3
            if hasattr(self, 's3_video_dir') and self.s3_video_dir:
                logger.info(f"Attempting to find video files in S3 directory: {self.s3_video_dir}")
                
                # Extract the base name from subtitle file
                subtitle_name = Path(self.subtitle_file).stem
                if subtitle_name.endswith('.en'):
                    base_name = subtitle_name[:-3]
                else:
                    base_name = subtitle_name
                
                # Try to find and download the video file from S3
                video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv']
                
                for ext in video_extensions:
                    video_filename = f"{base_name}{ext}"
                    s3_video_path = f"{self.s3_video_dir}/{video_filename}"
                    
                    # Check if video exists in S3
                    if self.storage.is_s3_path(s3_video_path) and self.storage.exists(s3_video_path):
                        # Download to local temp directory
                        local_video_dir = self.video_processor.media_dir
                        local_video_file = local_video_dir / video_filename
                        
                        logger.info(f"Downloading video from S3: {s3_video_path}")
                        if self.storage.download_file(s3_video_path, local_video_file):
                            self.temp_files_created.append(local_video_file)
                            logger.info(f"Downloaded video: {local_video_file}")
                            return local_video_file
                        else:
                            logger.warning(f"Failed to download video: {s3_video_path}")
            
            return video_file
            
        except Exception as e:
            logger.error(f"Error finding video file: {e}")
            return None
    
    def _prepare_input_files(self, subtitle_file: str, video_dir: str, output_dir: str):
        """
        Prepare input files by downloading from S3 if needed
        
        Args:
            subtitle_file: Original subtitle file path (may be S3)
            video_dir: Original video directory path (may be S3)
            output_dir: Local output directory for temporary files
            
        Returns:
            Tuple of (local_subtitle_file, local_video_dir)
        """
        try:
            # Get config for temp directory setup
            config_loader = ConfigLoader()
            local_config = config_loader.get_section('storage').get('local', {})
            
            # Setup temp directories
            temp_dir = Path(local_config.get('temp_dir', '/tmp/langflix'))
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Handle subtitle file
            if self.storage.is_s3_path(subtitle_file):
                logger.info(f"Downloading subtitle file from S3: {subtitle_file}")
                subtitle_name = Path(subtitle_file).name
                local_subtitle = temp_dir / "input" / subtitle_name
                
                if self.storage.download_file(subtitle_file, local_subtitle):
                    self.temp_files_created.append(local_subtitle)
                    local_subtitle_path = local_subtitle
                else:
                    raise ValueError(f"Failed to download subtitle file: {subtitle_file}")
            else:
                local_subtitle_path = Path(subtitle_file)
            
            # Handle video directory
            if self.storage.is_s3_path(video_dir):
                logger.info(f"Setting up for S3 video directory: {video_dir}")
                # For S3, we'll download videos as needed during processing
                # Create a temp directory for video files
                local_video_dir = temp_dir / "videos"
                local_video_dir.mkdir(parents=True, exist_ok=True)
                self.temp_files_created.append(local_video_dir)
                
                # Store original S3 path for later use
                self.s3_video_dir = video_dir
            else:
                local_video_dir = Path(video_dir)
                self.s3_video_dir = None
            
            return local_subtitle_path, local_video_dir
            
        except Exception as e:
            logger.error(f"Failed to prepare input files: {e}")
            # Fallback to original paths
            return Path(subtitle_file), Path(video_dir)
    
    def _upload_outputs(self):
        """Upload processed outputs to S3 if using S3 storage"""
        try:
            if self.storage.backend_type != 's3':
                logger.info("Using local storage - no upload needed")
                return
            
            # Get S3 config
            config_loader = ConfigLoader()
            s3_config = config_loader.get_section('storage').get('s3', {})
            output_bucket = s3_config.get('output_bucket', 'langflix-output')
            output_prefix = s3_config.get('output_prefix', 'processed/')
            
            # Create S3 storage instance for output bucket
            from .storage.s3 import S3Storage
            output_storage = S3Storage(bucket=output_bucket, region=s3_config.get('region', 'us-east-1'))
            
            # Upload final videos
            final_videos_dir = self.paths['language']['final_videos']
            if final_videos_dir.exists():
                for video_file in final_videos_dir.glob('*.mkv'):
                    if video_file.is_file() and video_file.stat().st_size > 0:
                        s3_key = f"{output_prefix}{video_file.name}"
                        logger.info(f"Uploading {video_file} to s3://{output_bucket}/{s3_key}")
                        
                        if output_storage.upload_file(video_file, s3_key):
                            logger.info(f"✅ Uploaded {video_file.name}")
                        else:
                            logger.error(f"❌ Failed to upload {video_file.name}")
            
            # Upload subtitle files
            subtitles_dir = self.paths['language']['subtitles']
            if subtitles_dir.exists():
                for subtitle_file in subtitles_dir.glob('*.srt'):
                    if subtitle_file.is_file():
                        s3_key = f"{output_prefix}{subtitle_file.name}"
                        logger.info(f"Uploading {subtitle_file} to s3://{output_bucket}/{s3_key}")
                        
                        if output_storage.upload_file(subtitle_file, s3_key):
                            logger.info(f"✅ Uploaded {subtitle_file.name}")
                        else:
                            logger.error(f"❌ Failed to upload {subtitle_file.name}")
            
            logger.info("✅ All outputs uploaded to S3")
            
        except Exception as e:
            logger.error(f"Failed to upload outputs to S3: {e}")
            # Don't raise - this shouldn't stop the pipeline
    
    def _cleanup_resources(self):
        """Clean up temporary files and resources"""
        try:
            # Clean up VideoEditor temporary files
            if hasattr(self, 'video_editor'):
                self.video_editor._cleanup_temp_files()
                logger.info("✅ VideoEditor temporary files cleaned up")
            
            # Clean up downloaded temporary files
            for temp_file in self.temp_files_created:
                try:
                    if temp_file.is_file() and temp_file.exists():
                        temp_file.unlink()
                        logger.debug(f"Deleted temp file: {temp_file}")
                    elif temp_file.is_dir() and temp_file.exists():
                        import shutil
                        shutil.rmtree(temp_file, ignore_errors=True)
                        logger.debug(f"Deleted temp directory: {temp_file}")
                except Exception as e:
                    logger.warning(f"Could not delete temp file {temp_file}: {e}")
            
            logger.info("✅ Temporary files cleaned up")
            
        except Exception as e:
            logger.warning(f"Failed to cleanup resources: {e}")
    
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
            test_mode=args.test_mode
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