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
                 output_dir: str = "output", 
                 language_code: Optional[str] = None,
                 source_language: Optional[str] = None,
                 target_languages: Optional[List[str]] = None,
                 progress_callback: Optional[Callable[[int, str], None]] = None,
                 series_name: str = None, episode_name: str = None,
                 video_file: str = None,
                 profiler: Optional[PipelineProfiler] = None):
        
        # Subtitle file may be empty - subtitles discovered from Subs/ folder
        self.subtitle_file = Path(subtitle_file) if subtitle_file and subtitle_file.strip() else None
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
        
        # Use utility functions for robust language name/code conversion
        from langflix.utils.language_utils import language_code_to_name, language_name_to_code
        
        # 1. Handle Target Languages
        self.target_languages = target_languages or []
        if not self.target_languages and language_code:
            self.target_languages = [language_code]
            
        if not self.target_languages:
            raise ValueError("Target language is required (TICKET-VIDEO-002)")
            
        # Primary language code MUST match the first target language (TICKET-VIDEO-002)
        self.language_code = self.target_languages[0]
        
        # 2. Handle Source Language
        if not source_language:
            raise ValueError("Source language is required (TICKET-VIDEO-002)")
        
        input_source_lang = source_language
        
        # If still no series_name, fallback to config (legacy behavior)
        if not series_name:
            series_name = settings.get_show_name()

        # Update source language if subtitle file indicates otherwise
        if input_source_lang == "English" and self.subtitle_file:
            sub_name = self.subtitle_file.name.lower()
            if 'korean' in sub_name or 'ko.' in sub_name:
                input_source_lang = "Korean"
            elif 'japanese' in sub_name or 'ja.' in sub_name:
                input_source_lang = "Japanese"
            elif 'spanish' in sub_name or 'es.' in sub_name:
                input_source_lang = "Spanish"
            elif 'french' in sub_name or 'fr.' in sub_name:
                input_source_lang = "French"
            elif 'german' in sub_name or 'de.' in sub_name:
                input_source_lang = "German"
            elif 'chinese' in sub_name or 'zh.' in sub_name:
                input_source_lang = "Chinese"

        self.source_language = input_source_lang
        # Normalize source_language: convert code to full name if needed
        if len(self.source_language) <= 3:
            self.source_language = language_code_to_name(self.source_language)
            logger.info(f"Converted source language code to name: '{self.source_language}'")
            
        self.source_lang_code = language_name_to_code(self.source_language)

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
        # Subtitle file may be None - SubtitleProcessor handles this
        self.subtitle_processor = SubtitleProcessor(str(self.subtitle_file) if self.subtitle_file else "")

        # Setup Paths - use video file name if subtitle file not provided
        path_reference = str(self.subtitle_file) if self.subtitle_file else (str(self.video_file) if self.video_file else "")
        self.paths = create_output_structure(
            path_reference, 
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
            save_llm_output: bool = False, test_mode: bool = False, test_llm: bool = False,
            no_shorts: bool = False, no_long_form: bool = False, short_form_max_duration: float = 180.0, 
            target_languages: Optional[List[str]] = None, schedule_upload: bool = False,
            target_duration: float = 120.0) -> Dict[str, Any]:
        
        if target_languages:
            self.target_languages = target_languages
            # Update primary language code (TICKET-VIDEO-002)
            if self.target_languages:
                self.language_code = self.target_languages[0]
                
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

            # Check if using legacy single file mode
            # Legacy logic removed - using Streaming Mode for ALL inputs
            
            # Streaming Mode (Chunk-by-Chunk)
            logger.info("Running in Streaming Mode (Chunk-by-Chunk)")
            
            # Ensure subtitles exist and environment is set up
            self._ensure_subtitles_exist()
            
            self.expressions = []
            self.translated_expressions = {lang: [] for lang in self.target_languages}
            
            # Streaming Generator
            logger.info(f"[PIPELINE] LangFlixPipeline.run(): Calling _run_analysis_streaming with target_duration={target_duration}")
            chunk_stream = self._run_analysis_streaming(
                language_level=language_level,
                max_expressions=max_expressions,
                test_llm=test_llm,
                target_duration=target_duration,
                test_mode=test_mode
            )
            
            # Track global index for short videos to ensure sequential naming (e.g. short_01, short_02)
            expression_counter = 1
            
            # Iterate through chunks and create videos immediately
            for chunk_idx, chunk_expressions in enumerate(chunk_stream):
                if not chunk_expressions:
                    continue
                    
                logger.info(f"🎬 Processing Chunk {chunk_idx+1}: Generating videos for {len(chunk_expressions)} expressions (Starts at #{expression_counter})...")
                
                # Accumulate for final report
                self.expressions.extend(chunk_expressions)
                
                # Process translations for this chunk
                chunk_translated = {lang: [] for lang in self.target_languages}
                
                # Group by language (needed for video factory)
                for expr in chunk_expressions:
                    # Add to main lists
                    for lang in self.target_languages:
                        if '_localizations' in expr and lang in expr['_localizations']:
                            lang_expr = expr['_localizations'][lang].copy()
                            lang_expr['source_lang'] = self.source_lang_code
                            # Add shared fields
                            lang_expr.update({k:v for k,v in expr.items() if k not in ['_localizations']})
                            
                            self.translated_expressions[lang].append(lang_expr)
                            chunk_translated[lang].append(lang_expr)
                
                # Create Videos for THIS chunk immediately
                if not dry_run:
                    # Filter out source language from target languages to prevent unwanted output generation
                    processing_languages = [l for l in self.target_languages if l != self.source_lang_code]

                    # Educational Videos
                    self.video_factory.create_educational_videos(
                        chunk_expressions,
                        chunk_translated,
                        processing_languages,
                        self.paths,
                        self.video_processor,
                        self.subtitle_processor,
                        self.output_dir,
                        episode_name=self.episode_name,
                        subtitle_file=self.subtitle_file,
                        video_file=self.video_file,
                        no_long_form=no_long_form,
                        test_mode=test_mode,
                        progress_callback=lambda p, m: self._update_progress(p, f"[Chunk {chunk_idx+1}] {m}"),
                        start_index=expression_counter
                    )

                    # Short Videos
                    if not no_shorts:
                        from langflix.core.video_editor import VideoEditor
                        def create_editor(lang, paths):
                            e = VideoEditor(
                                str(paths['final_videos']), lang, self.episode_name, 
                                subtitle_processor=self.subtitle_processor, 
                                test_mode=test_mode,
                                show_name=self.series_name
                            )
                            e.paths = paths
                            return e

                        self.video_factory.create_short_videos(
                            processing_languages,
                            self.paths,
                            chunk_translated, # Use chunk specific translations
                            chunk_expressions, # Use chunk specific expressions
                            self.episode_name,
                            self.subtitle_processor,
                            create_editor,
                            short_form_max_duration=short_form_max_duration,
                            output_dir=self.output_dir,
                            progress_callback=lambda p, m: self._update_progress(p, f"[Chunk {chunk_idx+1} Shorts] {m}"),
                            start_index=expression_counter # Pass start index to keep numbering correct
                        )
                        
                # Increment counter for next chunk
                expression_counter += len(chunk_expressions)

                # Memory Cleanup after chunk
                logger.info(f"🧹 Clearing memory for Chunk {chunk_idx+1}...")
                del chunk_translated
                # Note: we kept chunk_expressions in self.expressions via extend(), so we can't fully delete the objects 
                # if we want a final report, but we can delete the local list reference. 
                # The video assets (large objects) should be handled by the Factory.
                import gc
                gc.collect()


            # DB Save (At end)
            if media_id and self.expressions:
                self._save_expressions_to_db(media_id)

            # Upload (At end - batch upload is safer)
            if schedule_upload and not dry_run and self.expressions:
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

    def _ensure_subtitles_exist(self):
        """
        Ensure all required subtitle files exist, translating if necessary.
        Called BEFORE subtitle loading.
        """
        import shutil
        from langflix.utils.path_utils import get_subtitle_folder

        # Determine media path
        media_path = self.video_file if self.video_file else self.video_dir

        subtitle_folder = None

        # PRIORITY 1: use the folder of the provided subtitle file
        # BUT ONLY IF it is not a temporary file (uploaded)
        # If it is temp, we want to discover/create the proper persistent folder later
        if self.subtitle_file and self.subtitle_file.exists():
            is_temp = str(self.subtitle_file).startswith("/tmp") or "temp" in str(self.subtitle_file.parent).lower()
            
            if not is_temp:
                subtitle_folder = self.subtitle_file.parent
                logger.info(f"Using provided subtitle directory: {subtitle_folder}")
            else:
                logger.info(f"Provided subtitle is temp file ({self.subtitle_file}), will find/create persistent folder")

        # Try to discover subtitle folder from media path
        if not subtitle_folder:
            subtitle_folder = get_subtitle_folder(str(media_path))

        # Get persistent media base path from env (defaults to assets/media for backward compat, but run.sh sets /media/shows)
        persistent_media_root = os.getenv("LANGFLIX_STORAGE_LOCAL_BASE_PATH", "assets/media")

        # If not found (e.g., video in temp folder), try to find by episode name in persistent media path
        if not subtitle_folder and self.episode_name:
            logger.info(f"Searching for Netflix folder by episode name: {self.episode_name}")
            # Search in persistent media path and legacy paths
            search_paths = [
                persistent_media_root,
                "assets/media", # Keep legacy just in case
            ]
            
            # Add show-specific path if series name is known
            if self.series_name:
                show_path = Path("assets/media") / self.series_name
                search_paths.insert(1, str(show_path))

            # Also try to extract show name from episode name (robustness for test mode)
            from langflix.utils.filename_utils import extract_show_name
            derived_show = extract_show_name(self.episode_name)
            if derived_show and derived_show != self.series_name and derived_show != "Unknown Show":
                derived_path = Path("assets/media") / derived_show
                logger.info(f"Checking derived show path for translation: {derived_path}")
                search_paths.insert(2, str(derived_path))

            # Deduplicate paths
            search_paths = list(dict.fromkeys(search_paths))

            found_existing = False
            for media_root in search_paths:
                # Check NEW structure: {media_root}/Subs/{episode_name}/
                subs_folder = Path(media_root) / "Subs" / self.episode_name
                if subs_folder.exists() and subs_folder.is_dir():
                    srt_files = list(subs_folder.glob("*.srt"))
                    if srt_files:
                        subtitle_folder = str(subs_folder)
                        logger.info(f"Found Netflix folder (Subs structure): {subtitle_folder}")
                        found_existing = True
                        break
                
                # Check LEGACY structure: {media_root}/{episode_name}/
                legacy_folder = Path(media_root) / self.episode_name
                if legacy_folder.exists() and legacy_folder.is_dir():
                    srt_files = list(legacy_folder.glob("*.srt"))
                    if srt_files:
                        subtitle_folder = str(legacy_folder)
                        logger.info(f"Found Netflix folder (legacy structure): {subtitle_folder}")
                        found_existing = True
                        break
            
            if not found_existing and self.episode_name:
                logger.info(f"Deep scan: searching 'assets/media' for '{self.episode_name}'...")
                root_search = Path("assets/media")
                if root_search.exists():
                    # Manual iteration needed because glob fails on special chars like []
                    # Limit depth is implicit by how many dirs we follow, but here we just iterate everything
                    for path in root_search.rglob("*"):
                         if path.is_dir() and path.name == self.episode_name:
                             # Check if it contains subtitles
                             srt_files = list(path.glob("*.srt"))
                             if srt_files:
                                 subtitle_folder = str(path)
                                 logger.info(f"Found subtitle folder via deep scan: {subtitle_folder}")
                                 found_existing = True
                                 break
            
            if not found_existing:
                # If still not found, create Netflix folder in persistent media path (permanent location)
                if self.episode_name:
                    # 1. Try to create relative to persistent media file (preferred)
                    # Check if media_path is not a temp location
                    is_media_temp = any(p in str(media_path).lower() for p in ['/tmp/', '/var/folders/', 'temp'])
                    
                    created_relative = False
                    if not is_media_temp and media_path.exists():
                        try:
                            # assets/media/ShowName/Video.mkv -> assets/media/ShowName/Subs/EpisodeName
                            if media_path.is_file():
                                relative_subs = media_path.parent / "Subs" / self.episode_name
                            else: # directory
                                relative_subs = media_path / "Subs" / self.episode_name
                                
                            relative_subs.mkdir(parents=True, exist_ok=True)
                            subtitle_folder = relative_subs
                            logger.info(f"Created subtitle folder relative to media: {subtitle_folder}")
                            created_relative = True
                        except Exception as e:
                            logger.warning(f"Could not create relative subtitle folder: {e}")

                    # 2. Fallback: Create in persistent media path (e.g., /media/shows/{ShowName}/Subs/{EpisodeName})
                    if not created_relative:
                        if self.series_name:
                            subtitle_folder = Path(persistent_media_root) / self.series_name / "Subs" / self.episode_name
                        else:
                            subtitle_folder = Path(persistent_media_root) / self.episode_name
                        
                        subtitle_folder.mkdir(parents=True, exist_ok=True)
                        logger.info(f"Created persistent subtitle folder (fallback): {subtitle_folder}")
                else:
                    # Fallback: create based on media path (temp location - not ideal)
                    media_path_obj = Path(media_path)
                    if media_path_obj.is_file():
                        subtitle_folder = media_path_obj.parent / media_path_obj.stem
                    else:
                        subtitle_folder = media_path_obj
                    subtitle_folder.mkdir(parents=True, exist_ok=True)
                    logger.warning(f"Created subtitle folder in temp location (no episode name): {subtitle_folder}")

        subtitle_folder = Path(subtitle_folder)

        # Copy uploaded subtitle file to Netflix folder
        # logic:
        # 1. If valid subtitle provided, copy it to the folder
        # 2. Do NOT rename to {source_language}.srt immediately - let discovery logic handle it
        # 3. If filename is non-standard, rename to 'Original.srt' so discovery picks it up as a valid fallback
        if self.subtitle_file and self.subtitle_file.exists():
            import re
            # Check if filename is standard (supported by discovery)
            is_standard = re.match(r'^(\d+_)?([A-Za-z]+)\.srt$', self.subtitle_file.name)
            
            dest_name = self.subtitle_file.name
            if not is_standard:
                # Rename to source language to ensure correct discovery
                dest_name = f"{self.source_language}.srt"
                logger.info(f"Renaming non-standard subtitle {self.subtitle_file.name} to {dest_name} for discovery")

            dest_path = subtitle_folder / dest_name
            
            if not dest_path.exists() or self.subtitle_file.resolve() != dest_path.resolve():
                try:
                    shutil.copy2(str(self.subtitle_file), str(dest_path))
                    logger.info(f"Copied uploaded subtitle to: {dest_path}")
                except Exception as copy_err:
                     logger.warning(f"Failed to copy subtitle to persistent location: {copy_err}")

        # Update self.subtitle_file to point to the canonical source language file
        # This file will be created by ensure_subtitles_exist if it doesn't exist
        self.subtitle_file = subtitle_folder / f"{self.source_language}.srt"

        # Get required languages (convert codes to names)
        language_code_to_name = {
            'ko': 'Korean',
            'ja': 'Japanese',
            'zh': 'Chinese',
            'es': 'Spanish',
            'fr': 'French',
            'en': 'English',
            'de': 'German',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'ar': 'Arabic',
            'it': 'Italian',
            'nl': 'Dutch',
            'pl': 'Polish',
            'th': 'Thai',
            'vi': 'Vietnamese',
            'tr': 'Turkish',
            'sv': 'Swedish',
            'fi': 'Finnish',
            'da': 'Danish',
            'no': 'Bokmal',
            'cs': 'Czech',
            'el': 'Greek',
            'he': 'Hebrew',
            'hu': 'Hungarian',
            'id': 'Indonesian',
            'ro': 'Romanian'
        }

        # Convert target language codes to names
        target_lang_names = []
        for lang_code in self.target_languages:
            lang_name = language_code_to_name.get(lang_code, lang_code.capitalize())
            target_lang_names.append(lang_name)

        # Check if source subtitle file exists
        # Target language translation is handled by the LLM during expression analysis
        expected_sub = Path(subtitle_folder) / f"{self.source_language}.srt"
        if expected_sub.exists():
            logger.info(f"Found source subtitle file: {expected_sub}")
            self.subtitle_file = expected_sub
            self.subtitle_processor = SubtitleProcessor(str(expected_sub))
        else:
            logger.warning(f"Source subtitle file not found at {expected_sub}")

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
                    subtitle_file_path=str(self.subtitle_file) if self.subtitle_file else "",
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
        
        # Clean up any leftover temp files in shorts directories
        self._cleanup_temp_files_in_output()
    
    def _cleanup_temp_files_in_output(self):
        """Clean up temp_ prefixed files left in output directories."""
        import glob
        
        # Find all temp_* files in output paths
        for lang in self.target_languages:
            lang_paths = self.paths.get('languages', {}).get(lang, {})
            shorts_dir = lang_paths.get('shorts')
            videos_dir = lang_paths.get('final_videos')
            
            for dir_path in [shorts_dir, videos_dir]:
                if dir_path and Path(dir_path).exists():
                    temp_files = list(Path(dir_path).glob('temp_*'))
                    for temp_file in temp_files:
                        try:
                            if temp_file.is_file():
                                temp_file.unlink()
                                logger.debug(f"Cleaned up temp file: {temp_file}")
                        except Exception as e:
                            logger.warning(f"Failed to clean up temp file {temp_file}: {e}")
                    
                    if temp_files:
                        logger.info(f"Cleaned up {len(temp_files)} temp files from {dir_path}")

    def _save_llm_debug_files(self, target_lang_names: List[str]) -> None:
        """
        Copy latest LLM debug files to output directory structure.
        
        Saves:
        - Expression analyst response -> output/{series}/{episode}/llm_responses/
        - Translation response per lang -> output/{series}/{episode}/{lang}/llm_responses/
        """
        import shutil
        import glob
        
        debug_dir = Path("langflix/pipeline/artifacts/debug")
        if not debug_dir.exists():
            logger.warning("Debug directory not found, skipping LLM response saving")
            return
        
        try:
            # 1. Save expression analyst responses to episode level
            # Use structured episode path found in self.paths
            output_base = self.paths.get('episode', {}).get('episode_dir', self.output_dir)
            episode_llm_dir = output_base / "llm_responses"
            episode_llm_dir.mkdir(parents=True, exist_ok=True)
            
            # Find latest script_agent files
            script_prompts = sorted(glob.glob(str(debug_dir / "script_agent_prompt_*.txt")), reverse=True)
            script_responses = sorted(glob.glob(str(debug_dir / "script_agent_response_*.txt")), reverse=True)
            
            if script_prompts:
                shutil.copy(script_prompts[0], episode_llm_dir / "expression_analyst_prompt.txt")
                logger.info(f"💾 Saved expression analyst prompt to {episode_llm_dir}")
            if script_responses:
                shutil.copy(script_responses[0], episode_llm_dir / "expression_analyst_response.txt")
                logger.info(f"💾 Saved expression analyst response to {episode_llm_dir}")
            
            # 2. Save translation responses to language-specific directories
            translator_prompts = sorted(glob.glob(str(debug_dir / "translator_prompt_*.txt")), reverse=True)
            translator_responses = sorted(glob.glob(str(debug_dir / "translator_response_*.txt")), reverse=True)
            
            for lang_name in target_lang_names:
                lang_code = settings.language_name_to_code(lang_name) or lang_name.lower()[:2]
                
                # Use structured episode path
                output_base = self.paths.get('episode', {}).get('episode_dir', self.output_dir)
                lang_llm_dir = output_base / lang_code / "llm_responses"
                lang_llm_dir.mkdir(parents=True, exist_ok=True)
                
                if translator_prompts:
                    shutil.copy(translator_prompts[0], lang_llm_dir / "translator_prompt.txt")
                if translator_responses:
                    shutil.copy(translator_responses[0], lang_llm_dir / "translator_response.txt")
                    logger.info(f"💾 Saved translator response to {lang_llm_dir}")
                    
        except Exception as e:
            logger.warning(f"Failed to save LLM debug files: {e}")

    def _run_dual_subtitle_analysis(self, language_level: str = None, max_expressions: int = None, test_llm: bool = False) -> List[Dict[str, Any]]:
        """
        Dual-Subtitle Analysis: Use dual-language subtitles from Netflix.
        
        Instead of LLM translating, we load both source and target subtitles
        and let the LLM focus purely on content selection.
        
        Returns:
            List of expression dicts
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
            # Search in common media directories and their Subs/ subfolders
            search_paths = [
                str(self.video_dir),  # Check configured video dir first
                str(self.video_dir),  # Check configured video dir first
            ]
            
            # Add show-specific path if series name is known
            if self.series_name:
                show_path = Path("assets/media") / self.series_name
                search_paths.insert(1, str(show_path))

            # Also try to extract show name from episode name (robustness for test mode)
            # e.g. "Suits.S01E01..." -> "Suits"
            if self.episode_name:
                from langflix.utils.filename_utils import extract_show_name
                derived_show = extract_show_name(self.episode_name)
                if derived_show and derived_show != self.series_name and derived_show != "Unknown Show":
                    derived_path = Path("assets/media") / derived_show
                    logger.info(f"Checking derived show path: {derived_path}")
                    search_paths.insert(2, str(derived_path))
                
            # Deduplicate paths
            search_paths = list(dict.fromkeys([str(p) for p in search_paths]))
            for media_root in search_paths:
                media_path = Path(media_root)
                
                # Check NEW structure: {media_root}/Subs/{folder containing episode_name}/
                subs_parent = media_path / "Subs"
                if subs_parent.exists():
                    # Look for folders that START with episode_name
                    for folder in subs_parent.iterdir():
                        if folder.is_dir() and folder.name.startswith(self.episode_name):
                            srt_files = list(folder.glob("*.srt"))
                            if srt_files:
                                subtitle_folder = folder
                                logger.info(f"Found Netflix folder (Subs structure): {subtitle_folder}")
                                break
                    if subtitle_folder:
                        break
                
                # Check LEGACY structure: {media_root}/{folder containing episode_name}/
                if media_path.exists() and media_path.is_dir():
                    for folder in media_path.iterdir():
                        if folder.is_dir() and folder.name.startswith(self.episode_name):
                            srt_files = list(folder.glob("*.srt"))
                            if srt_files:
                                subtitle_folder = folder
                                logger.info(f"Found Netflix folder (legacy structure): {subtitle_folder}")
                                break
                    if subtitle_folder:
                        break
        
        if not subtitle_folder:
            error_msg = f"No subtitle folder found for: {media_path}. Dual-subtitle mode requires subtitles in Subs folder."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        languages = discover_subtitle_languages(subtitle_folder)
        if not languages:
            error_msg = f"No valid subtitles found in: {subtitle_folder}. Dual-subtitle mode requires subtitles."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Get source and target languages
        # Use provided source language
        source_lang = self.source_language
        
        # Use PRIMARY target language from request (not defaults from config)
        if self.target_languages:
            # We need the full name (e.g., 'Korean') not the code (e.g., 'ko')
            # Assuming self.target_languages stores codes, we convert the first one
            primary_target_code = self.target_languages[0]
            
            # Simple mapping (expand as needed or import unified map)
            language_code_to_name = {
                'ko': 'Korean', 'ja': 'Japanese', 'zh': 'Chinese', 'es': 'Spanish',
                'fr': 'French', 'en': 'English', 'de': 'German', 'pt': 'Portuguese',
                'ru': 'Russian', 'it': 'Italian'
            }
            target_lang = language_code_to_name.get(primary_target_code, primary_target_code.capitalize())
        else:
            # Fallback only if no target languages specified
            target_lang = settings.get_default_target_language()

        logger.info(f"Dual-subtitle analysis using Source: {source_lang}, Target: {target_lang}")
        
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
            # Get episode output directory for saving LLM response
            episode_output_dir = str(self.paths.get('episode', {}).get('base', self.output_dir))
            
            expressions = analyze_with_dual_subtitles(
                dual_subtitle=dual_sub,
                show_name=self.series_name,
                language_level=language_level or "intermediate",
                min_expressions=1,
                max_expressions=max_expressions,  # Already set correctly by caller
                target_duration=45.0,
                test_llm=test_llm,
                output_dir=episode_output_dir,  # Save LLM response in episode folder
            )
            
            # Store source language code for video editor
            source_lang_code = language_name_to_code(source_lang)
            for expr in expressions:
                expr['_source_language_code'] = source_lang_code
            
            logger.info(f"Dual-subtitle analysis found {len(expressions)} expressions")
            return expressions
            
        except Exception as e:
            import traceback
            logger.error(f"Dual-subtitle content selection failed: {e}")
            logger.error(f"Full error details: {repr(e)}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            return []

    def _run_analysis_single_subtitle(self, language_level: str = None, max_expressions: int = None, test_mode: bool = False, test_llm: bool = False, target_duration: int = None) -> List[Dict]:
        """
        Run pipeline with single subtitle file (legacy/API upload workflow).
        Uses source subtitles for both source and target - LLM will translate in its response.
        """
        from langflix.core.subtitle_parser import parse_subtitle_file_by_extension as parse_subtitle_file

        logger.info("Using single-subtitle workflow (LLM will translate dialogues)")

        # Parse source subtitle
        self._update_progress(15, "Parsing source subtitle...")
        source_subtitles = parse_subtitle_file(str(self.subtitle_file))

        if not source_subtitles:
            raise ValueError(f"Failed to parse subtitle file: {self.subtitle_file}")

        logger.info(f"Parsed {len(source_subtitles)} source subtitles")

        # Use source subtitles for both source and target
        # The LLM will translate the target dialogues in its response
        self._update_progress(30, "Preparing dialogues for LLM...")
        target_subtitles = source_subtitles  # LLM will translate these

        logger.info("LLM will translate dialogues to target language in response")

        # Proceed with dual-subtitle pipeline (source used for both)
        return self._run_dual_subtitle_pipeline(
            source_subtitles=source_subtitles,
            target_subtitles=target_subtitles,
            language_level=language_level,
            max_expressions=max_expressions,
            test_mode=test_mode,
            test_llm=test_llm,
            target_duration=target_duration
        )

    def _run_dual_subtitle_pipeline(self, source_subtitles: List[Dict], target_subtitles: List[Dict], language_level: str = None, max_expressions: int = None, test_mode: bool = False, test_llm: bool = False, target_duration: int = None) -> List[Dict]:
        """
        Core pipeline logic for analyzing with both source and target subtitles.
        Shared between folder-based and single-file workflows.
        """
        from langflix.pipeline.orchestrator import Pipeline
        from langflix.pipeline.models import PipelineConfig

        self._update_progress(45, "Creating subtitle chunks...")

        # Create chunks - same logic as in dual-folder workflow
        MAX_SUBTITLES_PER_CHUNK = 200
        chunk_size = settings.get_llm_config().get('max_input_length', 0)

        if chunk_size == 0:
            num_chunks = (len(source_subtitles) + MAX_SUBTITLES_PER_CHUNK - 1) // MAX_SUBTITLES_PER_CHUNK
            chunks = []
            target_chunks = []

            for i in range(num_chunks):
                start_idx = i * MAX_SUBTITLES_PER_CHUNK
                end_idx = min((i + 1) * MAX_SUBTITLES_PER_CHUNK, len(source_subtitles))
                chunk_subs = source_subtitles[start_idx:end_idx]
                target_chunk_subs = target_subtitles[start_idx:end_idx]

                chunks.append({
                    'chunk_id': i + 1,
                    'script': '\n'.join([f"[{idx}] [{sub['start_time']} --> {sub['end_time']}] {sub['text']}" for idx, sub in enumerate(chunk_subs)]),
                    'start_time': chunk_subs[0]['start_time'] if chunk_subs else '00:00:00,000',
                    'end_time': chunk_subs[-1]['end_time'] if chunk_subs else '00:00:00,000',
                    'subtitles': chunk_subs,
                })
                target_chunks.append({
                    'chunk_id': i + 1,
                    'script': '\n'.join([f"[{idx}] [{sub['start_time']} --> {sub['end_time']}] {sub['text']}" for idx, sub in enumerate(target_chunk_subs)]),
                    'start_time': target_chunk_subs[0]['start_time'] if target_chunk_subs else '00:00:00,000',
                    'end_time': target_chunk_subs[-1]['end_time'] if target_chunk_subs else '00:00:00,000',
                    'subtitles': target_chunk_subs,
                })
            logger.info(f"Created {len(chunks)} chunks")
        else:
            chunks = [{'chunk_id': 1, 'script': '\n'.join([f"[{idx}] [{sub['start_time']} --> {sub['end_time']}] {sub['text']}" for idx, sub in enumerate(source_subtitles)]), 'start_time': source_subtitles[0]['start_time'] if source_subtitles else '00:00:00,000', 'end_time': source_subtitles[-1]['end_time'] if source_subtitles else '00:00:00,000', 'subtitles': source_subtitles}]
            target_chunks = [{'chunk_id': 1, 'script': '\n'.join([f"[{idx}] [{sub['start_time']} --> {sub['end_time']}] {sub['text']}" for idx, sub in enumerate(target_subtitles)]), 'start_time': target_subtitles[0]['start_time'] if target_subtitles else '00:00:00,000', 'end_time': target_subtitles[-1]['end_time'] if target_subtitles else '00:00:00,000', 'subtitles': target_subtitles}]

        if test_mode or settings.is_test_mode_enabled() or (max_expressions is not None and max_expressions <= 5):
            logger.info("TEST MODE: Limiting to 1 chunk only")
            chunks = chunks[:1]
            target_chunks = target_chunks[:1]

        # Run pipeline
        self._update_progress(55, "Initializing pipeline...")
        
        from langflix.utils.language_utils import language_code_to_name
        target_lang_names = [language_code_to_name(code) for code in self.target_languages]
        
        config = PipelineConfig(
            show_name=self.series_name, 
            episode_name=self.episode_name, 
            source_language=self.source_language,
            target_languages=target_lang_names,  # Use full names (TICKET-VIDEO-002)
            use_wikipedia=settings.get_use_wikipedia(), 
            cache_show_bible=not settings.get_force_refresh_bible(),
            output_dir=str(self.paths.get('episode', {}).get('path', self.output_dir))
        )
        pipeline = Pipeline(config)

        try:
            self._update_progress(60, "Analyzing expressions...")
            expressions_per_chunk = settings.get_test_mode_max_expressions_per_chunk() if test_mode else settings.get_max_expressions_per_chunk()
            episode_data = pipeline.run(subtitle_chunks=chunks, target_subtitle_chunks=target_chunks, language_level=language_level or "intermediate", max_expressions_per_chunk=expressions_per_chunk, max_total_expressions=max_expressions)

            self._update_progress(80, "Converting results...")
            translation_results = pipeline.translate_episode(episode_data)

            expressions = []
            for result in translation_results:
                # Convert Result to dict and add _localizations for main.py run logic
                expr_dict = result.model_dump()
                
                # Add timings with legacy keys if needed
                expr_dict['context_start_time'] = result.start_time
                expr_dict['context_end_time'] = result.end_time
                
                # Format localizations for legacy run loop
                localizations_dict = {}
                for loc in result.localizations:
                    localizations_dict[loc.target_lang] = loc.model_dump()
                
                expr_dict['_localizations'] = localizations_dict
                expressions.append(expr_dict)

            logger.info(f"✅ Pipeline complete: {len(expressions)} expressions extracted")
            return expressions
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise

    def _run_analysis(self, language_level: str = None, max_expressions: int = None, test_llm: bool = False, target_duration: float = 120.0, test_mode: bool = False) -> List[Dict[str, Any]]:
        """
        Run contextual localization pipeline.

        Workflow:
        1. Load source language subtitle (ONE file only)
        2. Create Show Bible from Wikipedia
        3. Extract expressions + Generate chunk summaries (Script Agent)
        4. Aggregate summaries into Master Summary (Aggregator)
        5. Translate with context awareness (Translator)

        Returns:
            List of expression dicts with translations
        """
        from langflix.pipeline.orchestrator import Pipeline
        from langflix.pipeline.models import PipelineConfig
        from langflix.utils.language_utils import language_name_to_code
        from langflix.core.subtitle_parser import parse_subtitle_file_by_extension as parse_subtitle_file

        self._update_progress(10, "Loading source and target subtitles...")

        # Check if we have a direct subtitle file (API upload workflow)
        # or need to discover subtitle folder (dual-language workflow)
        if self.subtitle_file and self.subtitle_file.exists():
            # Legacy workflow: Single subtitle file provided
            logger.info(f"Using provided subtitle file: {self.subtitle_file}")
            # For single file, we'll generate synthetic target subtitles or use translation
            # This maintains backward compatibility with API uploads
            return self._run_analysis_single_subtitle(
                language_level=language_level,
                max_expressions=max_expressions,
                test_mode=test_mode,
                test_llm=test_llm,
                target_duration=target_duration
            )

        # New workflow: Discover subtitle folder with both source and target
        from langflix.utils.path_utils import get_subtitle_folder, discover_subtitle_languages
        media_path = self.video_file if self.video_file else self.video_dir
        subtitle_folder = get_subtitle_folder(media_path)

        if not subtitle_folder:
            error_msg = f"No subtitle folder found for: {media_path}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        languages = discover_subtitle_languages(subtitle_folder)

        # Load source subtitle
        if self.source_language not in languages:
            error_msg = f"Source language '{self.source_language}' subtitle not found in {subtitle_folder}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        source_sub_info = languages[self.source_language]
        source_subtitle_file = Path(source_sub_info['path'])
        logger.info(f"Found source subtitle: {source_subtitle_file}")

        # Load target subtitle
        # Determine target language from self.language_code or first target language
        from langflix.utils.language_utils import language_code_to_name, language_name_to_code
        
        target_language = language_code_to_name(self.language_code)

        if not target_language or target_language not in languages:
            error_msg = f"Target language '{target_language}' (code: {self.language_code}) subtitle not found in {subtitle_folder}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        target_sub_info = languages[target_language]
        target_subtitle_file = Path(target_sub_info['path'])
        logger.info(f"Found target subtitle: {target_subtitle_file}")

        # Parse both subtitles into chunks
        self._update_progress(20, "Parsing subtitles...")
        source_subtitles = parse_subtitle_file(str(source_subtitle_file))
        target_subtitles = parse_subtitle_file(str(target_subtitle_file))

        if source_subtitles:
            logger.debug(f"First source subtitle (raw): {source_subtitles[0]}")
            logger.debug(f"Last source subtitle (raw): {source_subtitles[-1]}")

        if target_subtitles:
            logger.debug(f"First target subtitle (raw): {target_subtitles[0]}")
            logger.debug(f"Last target subtitle (raw): {target_subtitles[-1]}")

        # Create chunks from both source and target subtitles
        # For Pipeline, limit subtitles per chunk to avoid LLM truncation
        MAX_SUBTITLES_PER_CHUNK = 200
        chunk_size = settings.get_llm_config().get('max_input_length', 0)

        if chunk_size == 0:
            # Split subtitles into manageable chunks (both source and target)
            num_chunks = (len(source_subtitles) + MAX_SUBTITLES_PER_CHUNK - 1) // MAX_SUBTITLES_PER_CHUNK

            chunks = []
            target_chunks = []

            for i in range(num_chunks):
                start_idx = i * MAX_SUBTITLES_PER_CHUNK
                end_idx = min((i + 1) * MAX_SUBTITLES_PER_CHUNK, len(source_subtitles))

                chunk_subs = source_subtitles[start_idx:end_idx]
                target_chunk_subs = target_subtitles[start_idx:end_idx]

                # Format with indices AND timestamps for LLM to reference and copy
                chunks.append({
                    'chunk_id': i + 1,
                    'script': '\n'.join([f"[{idx}] [{sub['start_time']} --> {sub['end_time']}] {sub['text']}" for idx, sub in enumerate(chunk_subs)]),
                    'start_time': chunk_subs[0]['start_time'] if chunk_subs else '00:00:00,000',
                    'end_time': chunk_subs[-1]['end_time'] if chunk_subs else '00:00:00,000',
                    'subtitles': chunk_subs,  # Keep subtitle entries for timestamp lookup
                })

                target_chunks.append({
                    'chunk_id': i + 1,
                    'script': '\n'.join([f"[{idx}] [{sub['start_time']} --> {sub['end_time']}] {sub['text']}" for idx, sub in enumerate(target_chunk_subs)]),
                    'start_time': target_chunk_subs[0]['start_time'] if target_chunk_subs else '00:00:00,000',
                    'end_time': target_chunk_subs[-1]['end_time'] if target_chunk_subs else '00:00:00,000',
                    'subtitles': target_chunk_subs,  # Keep subtitle entries for timestamp lookup
                })

            logger.info(f"Created {len(chunks)} source and {len(target_chunks)} target chunks from {len(source_subtitles)} subtitles (max {MAX_SUBTITLES_PER_CHUNK} per chunk)")
        else:
            # Chunked mode based on character length (legacy)
            chunks = [{
                'chunk_id': 1,
                'script': '\n'.join([f"[{idx}] [{sub['start_time']} --> {sub['end_time']}] {sub['text']}" for idx, sub in enumerate(source_subtitles)]),
                'start_time': source_subtitles[0]['start_time'] if source_subtitles else '00:00:00,000',
                'end_time': source_subtitles[-1]['end_time'] if source_subtitles else '00:00:00,000',
                'subtitles': source_subtitles,
            }]
            target_chunks = [{
                'chunk_id': 1,
                'script': '\n'.join([f"[{idx}] [{sub['start_time']} --> {sub['end_time']}] {sub['text']}" for idx, sub in enumerate(target_subtitles)]),
                'start_time': target_subtitles[0]['start_time'] if target_subtitles else '00:00:00,000',
                'end_time': target_subtitles[-1]['end_time'] if target_subtitles else '00:00:00,000',
                'subtitles': target_subtitles,
            }]

        # If test mode, strictly limit to 1 chunk
        if test_mode or settings.is_test_mode_enabled() or (max_expressions is not None and max_expressions <= 5):
             logger.info("TEST MODE: Limiting to 1 chunk only")
             chunks = chunks[:1]
             target_chunks = target_chunks[:1]

        # Create Pipeline Config
        self._update_progress(30, "Initializing pipeline...")

        from langflix.utils.language_utils import language_code_to_name
        target_lang_names = [
            language_code_to_name(code)
            for code in self.target_languages
        ]

        config = PipelineConfig(
            show_name=self.series_name,
            episode_name=self.episode_name,
            source_language=self.source_language,
            target_languages=target_lang_names,
            use_wikipedia=settings.get_use_wikipedia(),
            cache_show_bible=not settings.get_force_refresh_bible(),
            output_dir=str(self.paths.get('episode', {}).get('path', self.output_dir))
        )

        # Run Pipeline
        pipeline = Pipeline(config)

        try:
            # Phase 1: Extract + Translate
            self._update_progress(40, "Analyzing expressions and translating dialogues...")
            
            # Use test mode limits if test_mode parameter is True (not just config)
            expressions_per_chunk = (
                settings.get_test_mode_max_expressions_per_chunk() 
                if test_mode else 
                settings.get_max_expressions_per_chunk()
            )
            
            episode_data = pipeline.run(
                subtitle_chunks=chunks,
                target_subtitle_chunks=target_chunks,
                language_level=language_level or "intermediate",
                max_expressions_per_chunk=expressions_per_chunk,
                max_total_expressions=max_expressions
            )

            # Phase 2: Convert to TranslationResult format
            self._update_progress(60, "Converting results...")
            translation_results = pipeline.translate_episode(episode_data)

            # Save debug files to output directory
            self._save_llm_debug_files(target_lang_names)

            # Convert results to expression format
            self._update_progress(80, "Converting results...")
            expressions = []

            for result in translation_results:
                # Expression dictionary
                expr = {
                    'expression': result.expression,
                    'expression_dialogue': result.expression_dialogue,
                    'context_summary_eng': result.context_summary_eng,
                    'context_start_time': result.start_time,
                    'context_end_time': result.end_time,
                    'expression_start_time': result.expression_start_time,
                    'expression_end_time': result.expression_end_time,
                    'dialogues': result.dialogues,
                    'scene_type': result.scene_type,
                    'similar_expressions': result.similar_expressions,
                    'catchy_keywords': result.catchy_keywords,

                    # Pipeline metadata
                    'chunk_id': result.chunk_id,
                    'chunk_summary': result.chunk_summary,
                }

                # Define target language name for matching (uses utility)
                from langflix.utils.language_utils import language_code_to_name
                target_lang_name = language_code_to_name(self.language_code)

                # Add translations from localization data
                for loc in result.localizations:
                    logger.debug(f"Processing loc for {loc.target_lang}: Title='{loc.viral_title}', Vocab={len(loc.vocabulary_annotations)}")
                    # Match against the configured target language (checking both name and potential code)
                    # Handle precise matching (e.g. 'Spanish' vs 'SPANISH')
                    if (loc.target_lang.lower() == target_lang_name.lower() or 
                        loc.target_lang.lower() == self.language_code.lower()):
                        
                        expr['expression_translated'] = loc.expression_translated
                        expr['expression_dialogue_translated'] = loc.expression_dialogue_translated
                        expr['catchy_keywords_translated'] = loc.catchy_keywords_translated
                        
                        # Add aliases for backward compatibility with SubtitleProcessor and VideoEditor
                        expr['expression_translation'] = loc.expression_translated
                        expr['expression_dialogue_translation'] = loc.expression_dialogue_translated
                        expr['context_translation'] = loc.expression_dialogue_translated
                        expr['translation'] = loc.expression_dialogue_translated
                        expr['cultural_notes'] = getattr(loc, 'cultural_notes', '')

                        # Map overlay fields
                        expr['viral_title'] = getattr(loc, 'viral_title', '')
                        expr['narrations'] = getattr(loc, 'narrations', [])
                        expr['vocabulary_annotations'] = getattr(loc, 'vocabulary_annotations', [])
                        expr['expression_annotations'] = getattr(loc, 'expression_annotations', [])

                    # Store all localizations for multi-language support
                    if '_localizations' not in expr:
                        expr['_localizations'] = {}
                    expr['_localizations'][loc.target_lang] = {
                        'expression_translated': loc.expression_translated,
                        'expression_dialogue_translated': loc.expression_dialogue_translated,
                        'expression_dialogue_translation': loc.expression_dialogue_translated,  # Alias
                        'catchy_keywords_translated': loc.catchy_keywords_translated,
                        'viral_title': getattr(loc, 'viral_title', ''),
                        'narrations': getattr(loc, 'narrations', []),
                        'vocabulary_annotations': getattr(loc, 'vocabulary_annotations', []),
                        'expression_annotations': getattr(loc, 'expression_annotations', []),
                        'translation_notes': getattr(loc, 'translation_notes', '')
                    }

                # Add source language code (for compatibility with video editor)
                source_lang_code = language_name_to_code(self.source_language)
                expr['_source_language_code'] = source_lang_code

                expressions.append(expr)

            logger.info(f"Pipeline found {len(expressions)} expressions")
            return expressions

        except Exception as e:
            import traceback
            logger.error(f"Pipeline failed: {e}")
            logger.error(f"Full error details: {repr(e)}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            return []

    def _run_analysis_streaming(self, language_level: str = None, max_expressions: int = None, test_llm: bool = False, target_duration: float = 120.0, test_mode: bool = False):
        """
        Run contextual localization pipeline in STREAMING mode (Generator).
        Yields a list of expressions for each processed chunk.
        """
        logger.info(f"[PIPELINE] _run_analysis_streaming() ENTRY: target_duration={target_duration}")
        from langflix.pipeline.orchestrator import Pipeline
        from langflix.pipeline.models import PipelineConfig
        from langflix.utils.language_utils import language_name_to_code, language_code_to_name
        from langflix.core.subtitle_parser import parse_subtitle_file_by_extension as parse_subtitle_file
        from langflix.utils.path_utils import get_subtitle_folder, discover_subtitle_languages

        self._update_progress(10, "Loading source and target subtitles (Streaming)...")

        source_subtitles = []
        target_subtitles = []

        # Check for direct file input (API / Single File Mode)
        if self.subtitle_file and self.subtitle_file.exists():
            logger.info(f"Using provided subtitle file for streaming: {self.subtitle_file}")
            source_subtitles = parse_subtitle_file(str(self.subtitle_file))
            # In single file mode, target subtitles are initially empty (LLM will translate)
            target_subtitles = []
        else:
            # Discover subtitle folder with both source and target
            media_path = self.video_file if self.video_file else self.video_dir
            subtitle_folder = get_subtitle_folder(media_path)

            if not subtitle_folder:
                raise ValueError(f"No subtitle folder found for: {media_path}")

            languages = discover_subtitle_languages(subtitle_folder)

            # Load source subtitle
            if self.source_language not in languages:
                raise ValueError(f"Source language '{self.source_language}' subtitle not found in {subtitle_folder}")

            source_sub_paths = languages[self.source_language]
            source_subtitle_file = Path(source_sub_paths[0])
            logger.info(f"Found source subtitle: {source_subtitle_file}")

            # Load target subtitle
            target_language = language_code_to_name(self.language_code)

            if target_language and target_language in languages:
                target_sub_paths = languages[target_language]
                target_subtitle_file = Path(target_sub_paths[0])
                logger.info(f"Found target subtitle: {target_subtitle_file}")
                target_subtitles = parse_subtitle_file(str(target_subtitle_file))
            else:
                 logger.warning(f"Target language '{target_language}' (code: {self.language_code}) subtitle not found. Proceeding with Source Only (Translation Mode).")
                 target_subtitles = []

            # Parse source subtitles
            source_subtitles = parse_subtitle_file(str(source_subtitle_file))

        # Create chunks logic (Shared with _run_analysis - simplified duplication for now)
        MAX_SUBTITLES_PER_CHUNK = 200
        
        chunks = []
        target_chunks = []
        
        # Simplified chunk creation for cleaner code
        num_chunks = (len(source_subtitles) + MAX_SUBTITLES_PER_CHUNK - 1) // MAX_SUBTITLES_PER_CHUNK
        for i in range(num_chunks):
            start_idx = i * MAX_SUBTITLES_PER_CHUNK
            end_idx = min((i + 1) * MAX_SUBTITLES_PER_CHUNK, len(source_subtitles))
            
            chunk_subs = source_subtitles[start_idx:end_idx]
            target_chunk_subs = target_subtitles[start_idx:end_idx]
            
            chunks.append({
                'chunk_id': i + 1,
                'script': '\n'.join([f"[{idx}] [{sub['start_time']} --> {sub['end_time']}] {sub['text']}" for idx, sub in enumerate(chunk_subs)]),
                'start_time': chunk_subs[0]['start_time'] if chunk_subs else '00:00:00,000',
                'end_time': chunk_subs[-1]['end_time'] if chunk_subs else '00:00:00,000',
                'subtitles': chunk_subs
            })
            target_chunks.append({
                'chunk_id': i + 1,
                'script': '\n'.join([f"[{idx}] [{sub['start_time']} --> {sub['end_time']}] {sub['text']}" for idx, sub in enumerate(target_chunk_subs)]),
                'subtitles': target_chunk_subs
            })

        if test_mode or settings.is_test_mode_enabled() or (max_expressions is not None and max_expressions <= 5):
             logger.info("TEST MODE: Limiting to 1 chunk only")
             chunks = chunks[:1]
             target_chunks = target_chunks[:1]

        # Init Pipeline
        target_lang_names = [language_code_to_name(code) for code in self.target_languages]
        config = PipelineConfig(
            show_name=self.series_name,
            episode_name=self.episode_name,
            source_language=self.source_language,
            target_languages=target_lang_names,
            use_wikipedia=settings.get_use_wikipedia(),
            cache_show_bible=not settings.get_force_refresh_bible(),
            output_dir=str(self.paths.get('episode', {}).get('episode_dir', self.output_dir))
        )
        pipeline = Pipeline(config)

        # streaming Run
        expressions_per_chunk = (settings.get_test_mode_max_expressions_per_chunk() if test_mode else settings.get_max_expressions_per_chunk())

        generator = pipeline.run_generator(
            subtitle_chunks=chunks,
            target_subtitle_chunks=target_chunks,
            language_level=language_level or "intermediate",
            max_expressions_per_chunk=expressions_per_chunk,
            max_total_expressions=max_expressions,
            target_duration=target_duration
        )

        for chunk_result in generator:
            # Convert single chunk result to translation results
            translation_results = pipeline.translate_chunk_result(chunk_result)
            
            # Save Debug
            self._save_llm_debug_files(target_lang_names) 

            # Convert to expressions list (local to this chunk)
            chunk_expressions = []
            
            for result in translation_results:
                # Expression dictionary (Same logic as _run_analysis)
                expr = {
                    'expression': result.expression,
                    'expression_dialogue': result.expression_dialogue,
                    'context_summary_eng': result.context_summary_eng,
                    'context_start_time': result.start_time,
                    'context_end_time': result.end_time,
                    'expression_start_time': result.expression_start_time,
                    'expression_end_time': result.expression_end_time,
                    'dialogues': result.dialogues,
                    'scene_type': result.scene_type,
                    'similar_expressions': result.similar_expressions,
                    'catchy_keywords': result.catchy_keywords,
                    'chunk_id': result.chunk_id,
                    'chunk_summary': result.chunk_summary,
                }
                
                # ... [Localization logic shared with _run_analysis] ...
                target_lang_name = language_code_to_name(self.language_code)
                for loc in result.localizations:
                     if (loc.target_lang.lower() == target_lang_name.lower() or loc.target_lang.lower() == self.language_code.lower()):
                        expr['expression_translated'] = loc.expression_translated
                        expr['expression_dialogue_translated'] = loc.expression_dialogue_translated
                        expr['catchy_keywords_translated'] = loc.catchy_keywords_translated
                        # Aliases
                        expr['expression_translation'] = loc.expression_translated
                        expr['expression_dialogue_translation'] = loc.expression_dialogue_translated
                        expr['context_translation'] = loc.expression_dialogue_translated
                        expr['translation'] = loc.expression_dialogue_translated
                        
                        expr['viral_title'] = getattr(loc, 'viral_title', '')
                        expr['narrations'] = getattr(loc, 'narrations', [])
                        expr['vocabulary_annotations'] = getattr(loc, 'vocabulary_annotations', [])
                        expr['expression_annotations'] = getattr(loc, 'expression_annotations', [])

                     if '_localizations' not in expr: expr['_localizations'] = {}
                     expr['_localizations'][loc.target_lang] = loc.model_dump()

                source_lang_code = language_name_to_code(self.source_language)
                expr['_source_language_code'] = source_lang_code
                
                expr['_source_language_code'] = source_lang_code
                
                chunk_expressions.append(expr)

            # FORCE LIMIT in test mode causing strict 1 expression processing
            if test_mode or settings.is_test_mode_enabled():
                if len(chunk_expressions) > 1:
                     logger.info(f"TEST MODE: Limiting expressions from {len(chunk_expressions)} to 1")
                     chunk_expressions = chunk_expressions[:1]

            yield chunk_expressions


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