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
                 source_language: str = "English",
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
        
        # If still no series_name, fallback to config (legacy behavior)
        if not series_name:
            series_name = settings.get_show_name()
            
        self.language_code = language_code

        # Normalize source_language: convert code to full name if needed
        language_code_to_name = {
            'ko': 'Korean', 'ja': 'Japanese', 'zh': 'Chinese', 'es': 'Spanish',
            'fr': 'French', 'en': 'English', 'de': 'German', 'pt': 'Portuguese',
            'ru': 'Russian', 'ar': 'Arabic', 'it': 'Italian', 'nl': 'Dutch',
            'pl': 'Polish', 'th': 'Thai', 'vi': 'Vietnamese', 'tr': 'Turkish',
            'sv': 'Swedish', 'fi': 'Finnish', 'da': 'Danish', 'no': 'Bokmal',
            'cs': 'Czech', 'el': 'Greek', 'he': 'Hebrew', 'hu': 'Hungarian',
            'id': 'Indonesian', 'ro': 'Romanian'
        }
        # If source_language is a code (2-3 chars), convert to full name
        if source_language and len(source_language) <= 3 and source_language.lower() in language_code_to_name:
            self.source_language = language_code_to_name[source_language.lower()]
            logger.info(f"Converted source language code '{source_language}' to '{self.source_language}'")
        else:
            self.source_language = source_language

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

            # Pipeline Mode: The Translator Agent (Phase 3) translates only the extracted expressions.
            # Full subtitle file translation is not needed as the pipeline works with source subtitles only.
            # Expression translations are handled contextually in _run_analysis() -> Phase 3.

            # Run contextual localization pipeline
            logger.info("🚀 Starting contextual localization pipeline")
            # Test mode ALWAYS uses test limit (1 expression), regardless of other settings
            if test_mode:
                max_expr = settings.get_max_total_expressions(test_mode=True)
                logger.info(f"TEST MODE: Limiting to {max_expr} expression(s)")
            else:
                max_expr = max_expressions or settings.get_max_total_expressions(test_mode=False)

            # Run analysis
            self.expressions = self._run_analysis(language_level, max_expr, test_llm=test_llm, target_duration=target_duration)

            # Step 3: Format Translations
            # The Pipeline (_run_analysis) handles translation to ALL target languages in Phase 3.
            # We just need to restructure the data into self.translated_expressions for the VideoFactory.
            # self.expressions already contains '_localizations' with all target languages.
            
            self._update_progress(40, f"Processing translations for {len(self.target_languages)} languages...")
            self.translated_expressions = {}
            
            # Initialize lists for each target language
            for lang in self.target_languages:
                self.translated_expressions[lang] = []

            # Populate from expressions
            for expr_data in self.expressions:
                # Base expression data (shared across languages)
                base_data = expr_data.copy()
                # Remove _localizations from the individual copies to avoid circular/bloated data
                if '_localizations' in base_data:
                    del base_data['_localizations']
                
                localizations = expr_data.get('_localizations', {})
                
                for lang in self.target_languages:
                    # Get localization for this language
                    # Mapping: lang code -> lang name (Pipeline uses names/mixed)
                    # For now, we trust the pipeline put the key as the language name or code
                    # The pipeline uses whatever 'target_lang' was passed to it.
                    # In _run_analysis, we passed FULL NAMES.
                    
                    # We need to find the matching key in localizations
                    # Localizations keys are likely Full Names (e.g. "Spanish")
                    # self.target_languages are codes (e.g. "es")
                    
                    # Helper to find data
                    lang_data = None
                    
                    # Try code directly
                    if lang in localizations:
                        lang_data = localizations[lang]
                    else:
                        # Try name mapping
                        from langflix.utils.language_utils import language_code_to_name
                        lang_name = language_code_to_name(lang)
                        if lang_name in localizations:
                            lang_data = localizations[lang_name]
                        # Try case-insensitive
                        else:
                            for loc_key, loc_val in localizations.items():
                                if loc_key.lower() == lang.lower() or loc_key.lower() == lang_name.lower():
                                    lang_data = loc_val
                                    break
                    
                    # Create language-specific expression object
                    lang_expr = base_data.copy()
                    
                    if lang_data:
                        logger.info(f"DEBUG: Found data for {lang}: Title='{lang_data.get('viral_title')}', Annotations={len(lang_data.get('vocabulary_annotations', []))}")
                        # Merge localization data
                        lang_expr.update(lang_data)
                        
                        # Populate legacy fields for compatibility
                        lang_expr['expression_translation'] = lang_data.get('expression_translated', '')
                        lang_expr['translation'] = lang_data.get('expression_dialogue_translated', '')
                    else:
                        logger.warning(f"Missing localization for lang '{lang}' in expression: {expr_data.get('expression', 'Unknown')}")
                        # Fallback: Just use English/Source? Or invalid?
                        # Video generation might fail or show placeholders.
                        pass
                        
                    self.translated_expressions[lang].append(lang_expr)
            
            logger.info(f"Populated translations for: {list(self.translated_expressions.keys())}")

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
                    video_file=self.video_file,  # Explicit video file path
                    no_long_form=no_long_form,
                    test_mode=test_mode,
                    progress_callback=lambda p, m: self._update_progress(p, f"[Video] {m}")
                )

                # Short Videos
                if not no_shorts:
                    self._update_progress(80, "Creating short videos...")
                    from langflix.core.video_editor import VideoEditor # For factory
                    
                    def create_editor(lang, paths):
                        e = VideoEditor(
                            str(paths['final_videos']), lang, self.episode_name, 
                            subtitle_processor=self.subtitle_processor, 
                            test_mode=test_mode,
                            show_name=self.series_name  # For YouTube metadata
                        )
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

    def _ensure_subtitles_exist(self):
        """
        Ensure all required subtitle files exist, translating if necessary.
        Called BEFORE subtitle loading.
        """
        import shutil
        from langflix.services.subtitle_translation_service import SubtitleTranslationService
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

            for media_root in search_paths:
                # Check NEW structure: {media_root}/Subs/{episode_name}/
                subs_folder = Path(media_root) / "Subs" / self.episode_name
                if subs_folder.exists() and subs_folder.is_dir():
                    srt_files = list(subs_folder.glob("*.srt"))
                    if srt_files:
                        subtitle_folder = str(subs_folder)
                        logger.info(f"Found Netflix folder (Subs structure): {subtitle_folder}")
                        break
                
                # Check LEGACY structure: {media_root}/{episode_name}/
                legacy_folder = Path(media_root) / self.episode_name
                if legacy_folder.exists() and legacy_folder.is_dir():
                    srt_files = list(legacy_folder.glob("*.srt"))
                    if srt_files:
                        subtitle_folder = str(legacy_folder)
                        logger.info(f"Found Netflix folder (legacy structure): {subtitle_folder}")
                        break

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

        # Copy uploaded subtitle file to Netflix folder as source language
        # The uploaded subtitle file is the source language subtitle
        # Note: subtitle_file may be None - subtitles discovered from Subs/ folder
        source_subtitle_path = subtitle_folder / f"{self.source_language}.srt"
        
        # Logic to copy self.subtitle_file to source_subtitle_path
        # We do this if:
        # a) source_subtitle_path doesn't exist
        # b) OR self.subtitle_file is explicitly provided AND different from source_subtitle_path
        if self.subtitle_file and self.subtitle_file.exists():
            if not source_subtitle_path.exists() or self.subtitle_file.resolve() != source_subtitle_path.resolve():
                # Only copy if we are not overwriting the exact same file
                try:
                    shutil.copy2(str(self.subtitle_file), str(source_subtitle_path))
                    logger.info(f"Copied uploaded/provided subtitle to persistent location: {source_subtitle_path}")
                    # Update self.subtitle_file to point to the persistent copy
                    self.subtitle_file = source_subtitle_path
                except Exception as copy_err:
                     logger.warning(f"Failed to copy subtitle to persistent location: {copy_err}")

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

        # Combine source + target languages
        required_langs = list(set([self.source_language] + target_lang_names))

        logger.info(f"Ensuring subtitles exist for languages: {required_langs}")

        # Initialize translation service
        translation_service = SubtitleTranslationService()

        # Ensure subtitles exist
        try:
            results = translation_service.ensure_subtitles_exist(
                subtitle_folder=subtitle_folder,
                source_language=self.source_language,
                required_languages=required_langs,
                progress_callback=lambda p, m: self._update_progress(5 + int(p * 0.05), m)
            )

            # Log results
            successful = [lang for lang, success in results.items() if success]
            failed = [lang for lang, success in results.items() if not success]

            if successful:
                logger.info(f"Subtitles available for: {successful}")
            if failed:
                logger.warning(f"Failed to ensure subtitles for: {failed}")

        except Exception as e:
            logger.warning(f"Subtitle translation failed: {e}")
            logger.info("Continuing with available subtitles...")

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
                "assets/media",
                "assets/media/test_media",
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

    def _run_analysis(self, language_level: str = None, max_expressions: int = None, test_llm: bool = False, target_duration: float = 120.0) -> List[Dict[str, Any]]:
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

        self._update_progress(10, "Loading source subtitle...")

        # Pipeline only needs ONE subtitle file (source language)
        # Try to find source subtitle
        if not self.subtitle_file or not self.subtitle_file.exists():
            # Try to discover from Subs folder
            from langflix.utils.path_utils import get_subtitle_folder, discover_subtitle_languages
            media_path = self.video_file if self.video_file else self.video_dir
            subtitle_folder = get_subtitle_folder(media_path)

            if subtitle_folder:
                languages = discover_subtitle_languages(subtitle_folder)
                if self.source_language in languages:
                    # Found source subtitle
                    source_sub_info = languages[self.source_language]
                    self.subtitle_file = Path(source_sub_info['path'])
                    logger.info(f"Found source subtitle: {self.subtitle_file}")
                else:
                    error_msg = f"Source language '{self.source_language}' subtitle not found in {subtitle_folder}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            else:
                error_msg = f"No subtitle folder found for: {media_path}"
                logger.error(error_msg)
                raise ValueError(error_msg)

        # Parse subtitle into chunks
        self._update_progress(20, "Parsing subtitle...")
        subtitles = parse_subtitle_file(str(self.subtitle_file))
        if subtitles:
            logger.info(f"DEBUG: First parsed subtitle (raw): {subtitles[0]}")
            logger.info(f"DEBUG: Last parsed subtitle (raw): {subtitles[-1]}")

        # Create chunks from subtitles
        # For Pipeline, limit subtitles per chunk to avoid LLM truncation
        MAX_SUBTITLES_PER_CHUNK = 100  # ~3-5 minutes of dialogue
        chunk_size = settings.get_llm_config().get('max_input_length', 0)
        
        if chunk_size == 0:
            # Split subtitles into manageable chunks
            subtitle_chunks = []
            for i in range(0, len(subtitles), MAX_SUBTITLES_PER_CHUNK):
                chunk_subtitles = subtitles[i:i + MAX_SUBTITLES_PER_CHUNK]
                subtitle_chunks.append(chunk_subtitles)
            
            chunks = []
            for idx, chunk_subs in enumerate(subtitle_chunks, 1):
                chunks.append({
                    'chunk_id': idx,
                    'script': '\n'.join([f"[{sub['start_time']} --> {sub['end_time']}] {sub['text']}" for sub in chunk_subs]),
                    'start_time': chunk_subs[0]['start_time'] if chunk_subs else '00:00:00,000',
                    'end_time': chunk_subs[-1]['end_time'] if chunk_subs else '00:00:00,000',
                })
            
            logger.info(f"Created {len(chunks)} chunks from {len(subtitles)} subtitles (max {MAX_SUBTITLES_PER_CHUNK} per chunk)")
        else:
            # Chunked mode based on character length (legacy)
            chunks = [{
                'chunk_id': 1,
                'script': '\n'.join([f"[{sub['start_time']} --> {sub['end_time']}] {sub['text']}" for sub in subtitles]),
                'start_time': subtitles[0]['start_time'] if subtitles else '00:00:00,000',
                'end_time': subtitles[-1]['end_time'] if subtitles else '00:00:00,000',
            }]


        # Create Pipeline Config
        self._update_progress(30, "Initializing pipeline...")

        # Convert target language codes to full names
        language_code_to_name = {
            'ko': 'Korean', 'ja': 'Japanese', 'zh': 'Chinese', 'es': 'Spanish',
            'fr': 'French', 'en': 'English', 'de': 'German', 'pt': 'Portuguese',
            'ru': 'Russian', 'it': 'Italian'
        }
        target_lang_names = [
            language_code_to_name.get(code, code.capitalize())
            for code in self.target_languages
        ]

        config = PipelineConfig(
            show_name=self.series_name,
            episode_name=self.episode_name,
            target_languages=target_lang_names,
            use_wikipedia=settings.get_use_wikipedia(),
            cache_show_bible=not settings.get_force_refresh_bible(),
            aggregator_model=settings.get_aggregator_model(),
            translator_model=settings.get_translator_model()
        )

        # Run Pipeline
        pipeline = Pipeline(config)

        try:
            # Phase 1-2: Extract + Summarize
            self._update_progress(40, "Analyzing expressions + Creating summaries...")
            episode_data = pipeline.run(
                subtitle_chunks=chunks,
                language_level=language_level or "intermediate",
                max_expressions_per_chunk=max_expressions or 50,
                max_total_expressions=max_expressions
            )

            # Phase 3: Translate
            self._update_progress(60, f"Translating to {len(target_lang_names)} languages...")
            translation_results = pipeline.translate_episode(episode_data)

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
                    'episode_summary': result.episode_summary,
                }

                # Define language map for code-to-name conversion
                language_code_to_name = {
                    'ko': 'Korean', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
                    'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian', 'ja': 'Japanese',
                    'zh': 'Chinese', 'hi': 'Hindi', 'ar': 'Arabic', 'nl': 'Dutch',
                    'pl': 'Polish', 'th': 'Thai', 'vi': 'Vietnamese', 'tr': 'Turkish',
                    'sv': 'Swedish', 'fi': 'Finnish', 'da': 'Danish', 'no': 'Bokmal'
                }
                target_lang_name = language_code_to_name.get(self.language_code, self.language_code.capitalize())

                # Add translations from localization data
                for loc in result.localizations:
                    logger.info(f"DEBUG: Processing loc for {loc.target_lang}: Title='{loc.viral_title}', Vocab={len(loc.vocabulary_annotations)}")
                    # Match against the configured target language (checking both name and potential code)
                    # Handle precise matching (e.g. 'Spanish' vs 'SPANISH')
                    if (loc.target_lang.lower() == target_lang_name.lower() or 
                        loc.target_lang.lower() == self.language_code.lower()):
                        
                        expr['expression_translated'] = loc.expression_translated
                        expr['expression_dialogue_translated'] = loc.expression_dialogue_translated
                        expr['catchy_keywords_translated'] = loc.catchy_keywords_translated
                        
                        # Add aliases for backward compatibility with SubtitleProcessor
                        expr['expression_translation'] = loc.expression_translated
                        expr['translation'] = loc.dialogue_translations
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