"""
LangFlix - Main execution script
End-to-end pipeline for learning English expressions from TV shows
Deconstructed into services (TICKET-082)
"""
import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Union, Callable
import time

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# DB Imports
try:
    from langflix.db import db_manager, MediaCRUD, ExpressionCRUD
    from langflix.db.models import Media
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

# Services & Core
from langflix.core.video_processor import VideoProcessor
from langflix.core.subtitle_processor import SubtitleProcessor
from langflix.services.output_manager import create_output_structure, OutputManager
from langflix.profiling import PipelineProfiler, profile_stage
from langflix import settings

# New Services
from langflix.services.subtitle_service import SubtitleService
from langflix.services.expression_service import ExpressionService
from langflix.services.translation_service import TranslationService
from langflix.services.video_factory import VideoFactory
from langflix.services.upload_service import UploadService

logger = logging.getLogger(__name__)

def setup_logging(verbose: bool = False):
    """Setup structured logging configuration"""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-15s:%(lineno)-4d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_formatter)
    
    file_handler = logging.FileHandler('langflix.log', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    logging.basicConfig(
        level=log_level,
        handlers=[console_handler, file_handler],
        force=True
    )
    logging.getLogger('ffmpeg').setLevel(logging.WARNING)

setup_logging()

def validate_and_sanitize_path(path_str: str, path_type: str = "file") -> Path:
    """Validate and sanitize user-provided file/directory paths."""
    if not path_str:
        raise ValueError(f"{path_type} path cannot be empty")
    
    path_str = path_str.strip()
    path = Path(path_str).resolve()
    
    if path_type == "subtitle":
        if not path.exists():
            raise FileNotFoundError(f"Subtitle file not found: {path}")
        if not path.is_file():
            raise ValueError(f"Subtitle path is not a file: {path}")
    elif path_type == "video":
        if path.is_file() and not path.exists():
            raise FileNotFoundError(f"Video file not found: {path}")
        elif path.is_dir() and not path.exists():
            raise FileNotFoundError(f"Video directory not found: {path}")
    elif path_type == "dir":
        if not path.parent.exists():
            raise FileNotFoundError(f"Parent directory for {path} does not exist")
            
    return path

class LangFlixPipeline:
    """
    Orchestrator for the LangFlix video generation pipeline.
    Coordinates specialized services to process subtitles, analyze expressions,
    translate content, and generate videos.
    """
    
    def __init__(self, subtitle_file: str, video_dir: str = "assets/media",
                 output_dir: str = "output", language_code: str = "ko",
                 target_languages: Optional[List[str]] = None,
                 progress_callback: Optional[Callable[[int, str], None]] = None,
                 series_name: str = None, episode_name: str = None,
                 video_file: str = None,
                 profiler: Optional[PipelineProfiler] = None):
        
        self.subtitle_file = Path(subtitle_file)
        self.video_dir = Path(video_dir)
        self.output_dir = Path(output_dir)
        self.video_file = Path(video_file) if video_file else None
        
        # If series_name is not provided, try to extract it from video filename
        if not series_name and self.video_file:
            from langflix.utils.filename_utils import extract_show_name
            extracted_name = extract_show_name(self.video_file.name)
            if extracted_name and extracted_name != "Unknown Show":
                series_name = extracted_name
                logging.info(f"Extracted show name from filename: {series_name}")
        
        # If still no series_name, fallback to config (legacy behavior)
        if not series_name:
            series_name = settings.get_show_name()
            
        self.language_code = language_code
        self.target_languages = target_languages or [language_code]
        self.profiler = profiler
        self.progress_callback = progress_callback

        # Initialize Services
        self.subtitle_service = SubtitleService()
        # ExpressionService needs the TARGET language (for LLM translations), not source language
        # target_languages[0] is the primary language we want translations in
        translation_target_language = self.target_languages[0] if self.target_languages else language_code
        self.expression_service = ExpressionService(translation_target_language)
        self.translation_service = TranslationService()
        self.video_factory = VideoFactory()
        self.upload_service = UploadService()

        # Initialize Processors (Core logic still needed by services)
        self.video_processor = VideoProcessor(str(self.video_dir), video_file=str(self.video_file) if self.video_file else None)
        self.subtitle_processor = SubtitleProcessor(str(self.subtitle_file))

        # Setup Paths
        self.paths = create_output_structure(
            str(self.subtitle_file), 
            language_code, 
            str(self.output_dir),
            series_name=series_name,
            episode_name=episode_name
        )
        self.series_name = self.paths['series_name']
        self.episode_name = self.paths['episode_name']

        # Ensure multi-language paths (moved from setup to run or helper)
        output_manager = OutputManager(str(self.output_dir))
        episode_paths = self.paths.get('episode', {})
        if 'languages' not in self.paths:
            self.paths['languages'] = {}
        for lang in self.target_languages:
            if lang not in self.paths['languages']:
                self.paths['languages'][lang] = output_manager.create_language_structure(episode_paths, lang)

        # State (Reduced)
        self.expressions = []
        self.translated_expressions = {}

    def run(self, max_expressions: int = None, dry_run: bool = False, language_level: str = None, 
            save_llm_output: bool = False, test_mode: bool = False, no_shorts: bool = False, 
            no_long_form: bool = False, short_form_max_duration: float = 180.0, 
            target_languages: Optional[List[str]] = None, schedule_upload: bool = False) -> Dict[str, Any]:
        
        if target_languages:
            self.target_languages = target_languages
            # Update paths for new languages
            output_manager = OutputManager(str(self.output_dir))
            for lang in self.target_languages:
                if lang not in self.paths['languages']:
                    self.paths['languages'][lang] = output_manager.create_language_structure(self.paths['episode'], lang)

        if self.profiler:
            self.profiler.start(metadata={"subtitle": str(self.subtitle_file)})

        try:
            logger.info("🎬 Starting LangFlix Pipeline (Orchestrator Mode)")
            
            # DB Integration
            media_id = self._init_db_media() if DB_AVAILABLE and settings.get_database_enabled() else None

            # V2 MODE: Check if dual-language mode is enabled
            if settings.is_dual_language_enabled():
                # V2 Workflow: Use dual subtitles from Netflix
                logger.info("🆕 V2 Mode: Using dual-language subtitle workflow")
                # In test mode, limit to 1 expression (matching V1 behavior)
                v2_max_expressions = 1 if test_mode else (max_expressions or 5)
                self.expressions = self._run_v2_analysis(language_level, v2_max_expressions)
            else:
                # V1 Workflow: Traditional single subtitle + LLM translation
                # Step 1: Parse & Chunk Subtitles
                self._update_progress(10, "Parsing subtitles...")
                subtitles = self.subtitle_service.parse(self.subtitle_file)
                chunks = self.subtitle_service.chunk(subtitles)

                # Step 2: Analyze Expressions
                self._update_progress(30, "Analyzing expressions...")
                self.expressions = self.expression_service.analyze(
                    chunks, 
                    self.subtitle_processor,
                    max_expressions=max_expressions,
                    language_level=language_level,
                    save_llm_output=save_llm_output,
                    test_mode=test_mode,
                    output_dir=self._get_llm_output_dir() if save_llm_output else None,
                    target_duration=short_form_max_duration,
                    progress_callback=lambda p, m=None: None
                )

            # Step 3: Translate
            # Optimization: If we only have 1 target language, the Analysis step already did the work (translation in target lang).
            # We only need TranslationService if we have *multiple* target languages (to translate to the others).
            if len(self.target_languages) > 1:
                self._update_progress(40, f"Translating to {len(self.target_languages)} languages...")
                self.translated_expressions = self.translation_service.translate(
                    self.expressions, 
                    self.language_code, 
                    self.target_languages
                )
            else:
                # Single target language -> Expression Analysis already provided it
                target_lang = self.target_languages[0]
                self.translated_expressions = {target_lang: self.expressions}

            # DB Save
            if media_id:
                self._save_expressions_to_db(media_id)

            if not dry_run and self.expressions:
                # Step 4: Create Videos
                self._update_progress(50, "Creating videos...")
                
                # Educational Videos
                self.video_factory.create_educational_videos(
                    self.expressions,
                    self.translated_expressions,
                    self.target_languages,
                    self.paths,
                    self.video_processor,
                    self.subtitle_processor,
                    self.output_dir,
                    episode_name=self.episode_name,
                    subtitle_file=self.subtitle_file,
                    no_long_form=no_long_form,
                    test_mode=test_mode,
                    progress_callback=lambda p, m: self._update_progress(p, f"[Video] {m}")
                )

                # Short Videos
                if not no_shorts:
                    self._update_progress(80, "Creating short videos...")
                    from langflix.core.video_editor import VideoEditor # For factory
                    
                    def create_editor(lang, paths):
                        e = VideoEditor(str(paths['final_videos']), lang, self.episode_name, subtitle_processor=self.subtitle_processor, test_mode=test_mode)
                        e.paths = paths
                        return e

                    self.video_factory.create_short_videos(
                        self.target_languages,
                        self.paths,
                        self.translated_expressions,
                        self.expressions,
                        self.episode_name,
                        self.subtitle_processor,
                        create_editor,
                        short_form_max_duration=short_form_max_duration,
                        output_dir=self.output_dir,
                        progress_callback=lambda p, m: self._update_progress(p, f"[Shorts] {m}")
                    )
                
                # Upload
                if schedule_upload:
                    self._update_progress(95, "Uploading videos...")
                    self.upload_service.upload_videos(
                        self.target_languages,
                        self.paths,
                        self.output_dir
                    )

            # Step 5: Verify output was created
            self._update_progress(98, "Verifying output...")
            output_stats = self._verify_output()
            
            if output_stats['total_videos'] == 0:
                logger.warning("⚠️ Pipeline completed but NO VIDEO FILES were created!")
                logger.warning(f"Check logs for errors. Output dir: {self.output_dir}")
                self._update_progress(100, "Pipeline completed with warnings - no videos created")
            else:
                logger.info(f"✅ Created {output_stats['total_videos']} video(s): {output_stats['short_videos']} shorts, {output_stats['long_videos']} long-form")
                self._update_progress(100, f"Pipeline completed successfully! Created {output_stats['total_videos']} video(s)")
            
            self._cleanup_resources()
            
            return self._generate_summary(output_stats)

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            raise
        finally:
             if self.profiler:
                self.profiler.stop()
                self.profiler.save_report()

    def _update_progress(self, percent: int, message: str):
        if self.progress_callback:
            self.progress_callback(percent, message)
        logger.info(message)

    def _get_llm_output_dir(self):
        try:
            return str(self.paths['episode']['metadata']['llm_outputs'])
        except:
            return None

    def _init_db_media(self):
        try:
            with db_manager.session() as db:
                media = MediaCRUD.create(
                    db=db,
                    show_name=settings.get_show_name(),
                    episode_name=self.episode_name,
                    language_code=self.language_code,
                    subtitle_file_path=str(self.subtitle_file),
                    video_file_path=str(self.video_dir)
                )
                return str(media.id)
        except Exception as e:
            logger.error(f"DB Error: {e}")
            return None

    def _save_expressions_to_db(self, media_id):
        try:
             with db_manager.session() as db:
                for expr in self.expressions:
                    try:
                        ExpressionCRUD.create_from_analysis(db=db, media_id=media_id, analysis_data=expr)
                    except Exception as e:
                        logger.error(f"Failed to save expression to DB: {e}")
        except Exception as e:
             logger.error(f"DB Error saving expressions: {e}")

    def _generate_summary(self, output_stats: Dict[str, int] = None):
        summary = {
            "status": "success" if (output_stats and output_stats.get('total_videos', 0) > 0) else "warning",
            "expressions_count": len(self.expressions),
            "languages": self.target_languages,
            "output_dir": str(self.output_dir)
        }
        if output_stats:
            summary["videos_created"] = output_stats
        return summary

    def _verify_output(self) -> Dict[str, int]:
        """
        Verify that output files were created.
        
        Returns:
            Dict with counts of created videos
        """
        stats = {
            'short_videos': 0,
            'long_videos': 0,
            'total_videos': 0
        }
        
        logger.info(f"Checking for short videos in {len(self.paths.get('languages', {}))} language directories")
        
        for lang, lang_paths in self.paths.get('languages', {}).items():
            # Check shorts directory
            shorts_dir = lang_paths.get('shorts')
            if shorts_dir:
                shorts_path = Path(shorts_dir)
                if shorts_path.exists():
                    logger.info(f"Scanning for shorts in: {shorts_path}")
                    short_files = list(shorts_path.glob("*.mkv")) + list(shorts_path.glob("*.mp4"))
                    stats['short_videos'] += len(short_files)
            
            # Check expressions directory (long-form)
            expressions_dir = lang_paths.get('expressions')
            if expressions_dir:
                expressions_path = Path(expressions_dir)
                if expressions_path.exists():
                    long_files = list(expressions_path.glob("*.mkv")) + list(expressions_path.glob("*.mp4"))
                    stats['long_videos'] += len(long_files)
        
        stats['total_videos'] = stats['short_videos'] + stats['long_videos']
        logger.info(f"Total short videos found: {stats['short_videos']}")
        
        return stats

    def _cleanup_resources(self):
        from langflix.utils.temp_file_manager import get_temp_manager
        get_temp_manager().cleanup_all()

    def _run_v2_analysis(self, language_level: str = None, max_expressions: int = None) -> List[Dict[str, Any]]:
        """
        V2 Analysis: Use dual-language subtitles from Netflix.
        
        Instead of LLM translating, we load both source and target subtitles
        and let the LLM focus purely on content selection.
        
        Returns:
            List of V1-compatible expression dicts
        """
        from langflix.core.dual_subtitle import get_dual_subtitle_service
        from langflix.core.content_selection_analyzer import analyze_with_dual_subtitles
        from langflix.utils.language_utils import language_name_to_code
        from langflix.utils.path_utils import get_subtitle_folder, discover_subtitle_languages
        
        self._update_progress(10, "Loading dual-language subtitles...")
        
        # Get media path from video file
        media_path = self.video_file if self.video_file else self.video_dir
        
        # Try to discover subtitle folder from media path
        subtitle_folder = get_subtitle_folder(media_path)
        
        # If not found (e.g., video in temp folder), try to find by episode name in assets/media
        if not subtitle_folder and self.episode_name:
            logger.info(f"Searching for Netflix folder by episode name: {self.episode_name}")
            # Search in common media directories
            for media_root in ["assets/media", "assets/media/test_media"]:
                potential_folder = Path(media_root) / self.episode_name
                if potential_folder.exists() and potential_folder.is_dir():
                    # Check if this folder has subtitle files
                    srt_files = list(potential_folder.glob("*.srt"))
                    if srt_files:
                        subtitle_folder = str(potential_folder)
                        logger.info(f"Found Netflix folder by episode name: {subtitle_folder}")
                        break
        
        if not subtitle_folder:
            logger.warning("No subtitle folder found, falling back to V1")
            return []
        
        languages = discover_subtitle_languages(subtitle_folder)
        if not languages:
            logger.warning("No subtitle languages found, falling back to V1")
            return []
        
        # Get source and target languages from config
        source_lang = settings.get_default_source_language()  # e.g., "English"
        target_lang = settings.get_default_target_language()  # e.g., "Korean"
        
        # Validate availability
        lang_names = list(languages.keys())
        if source_lang not in lang_names or target_lang not in lang_names:
            logger.warning(f"Required languages not available. Need {source_lang} + {target_lang}, have: {lang_names}")
            return []
        
        # Load dual subtitles
        self._update_progress(20, f"Loading {source_lang} + {target_lang} subtitles...")
        try:
            service = get_dual_subtitle_service()
            dual_sub = service.load_dual_subtitles(
                media_path=subtitle_folder,  # Use discovered Netflix folder, not temp video path
                source_lang=source_lang,
                target_lang=target_lang,
            )
        except Exception as e:
            logger.error(f"Failed to load dual subtitles: {e}")
            return []
        
        # Analyze for content selection
        self._update_progress(40, "Selecting educational content...")
        try:
            expressions = analyze_with_dual_subtitles(
                dual_subtitle=dual_sub,
                show_name=self.series_name,
                language_level=language_level or "intermediate",
                min_expressions=1,
                max_expressions=max_expressions or 5,
                target_duration=45.0,
            )
            
            # Store source language code for video editor
            source_lang_code = language_name_to_code(source_lang)
            for expr in expressions:
                expr['_source_language_code'] = source_lang_code
            
            logger.info(f"V2 analysis found {len(expressions)} expressions")
            return expressions
            
        except Exception as e:
            import traceback
            logger.error(f"V2 content selection failed: {e}")
            logger.error(f"Full error details: {repr(e)}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            return []


def validate_input_arguments(args) -> None:
    """Validate all input arguments before processing."""
    try:
        logger.info(f"Validating subtitle file: {args.subtitle}")
        subtitle_path = validate_and_sanitize_path(args.subtitle, "subtitle")
        
        logger.info(f"Validating video directory: {args.video_dir}")
        video_path = validate_and_sanitize_path(args.video_dir, "video")
        if not video_path.is_dir():
             # If it's a file, maybe it's the video file and parent is dir?
             # But arg is video_dir.
             # Existing logic said: "Video directory path is not a directory".
             # But validate_and_sanitize_path handles checking logic.
             pass

        logger.info(f"Validating output directory: {args.output_dir}")
        output_path = validate_and_sanitize_path(args.output_dir, "dir")

        args.subtitle = str(subtitle_path)
        args.video_dir = str(video_path)
        args.output_dir = str(output_path)
        
    except (ValueError, FileNotFoundError) as e:
        logger.error(f"Input validation failed: {e}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LangFlix Pipeline")
    parser.add_argument("subtitle", help="Path to subtitle file")
    parser.add_argument("--video-dir", default="assets/media", help="Video directory (default: assets/media)")
    parser.add_argument("--output-dir", default="output", help="Output directory (default: output)")
    parser.add_argument("--lang", default="ko", help="Target language code (default: ko)")
    
    args = parser.parse_args()
    
    try:
        validate_input_arguments(args)
        pipeline = LangFlixPipeline(
            args.subtitle, 
            args.video_dir,
            output_dir=args.output_dir,
            language_code=args.lang
        )
        pipeline.run()
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        sys.exit(1)