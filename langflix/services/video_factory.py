import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
import ffmpeg

from langflix.core.models import ExpressionAnalysis
from langflix.core.video_processor import VideoProcessor
from langflix.core.subtitle_processor import SubtitleProcessor
from langflix.core.video_editor import VideoEditor
from langflix.utils.filename_utils import sanitize_for_expression_filename
from langflix.services.output_manager import OutputManager
from langflix.utils.temp_file_manager import get_temp_manager
from langflix.media.ffmpeg_utils import get_duration_seconds
from langflix import settings
from langflix.subtitles.overlay import apply_dual_subtitle_layers

logger = logging.getLogger(__name__)

# Helper to get attribute from dict or object (V2 returns dicts, V1 returns objects)
def get_expr_attr(expr, key, default=None):
    """Get attribute from expression - works with both dict and object types."""
    if isinstance(expr, dict):
        return expr.get(key, default)
    return getattr(expr, key, default)

class VideoFactory:
    """Service for orchestrating video creation."""

    def create_educational_videos(
        self,
        expressions: List[ExpressionAnalysis],
        translated_expressions: Dict[str, List[ExpressionAnalysis]],
        target_languages: List[str],
        paths: Dict[str, Any],
        video_processor: VideoProcessor,
        subtitle_processor: SubtitleProcessor,
        output_dir: Path,
        episode_name: str,
        subtitle_file: Path,
        no_long_form: bool = False,
        test_mode: bool = False,
        progress_callback: Optional[callable] = None
    ):
        """
        Create long-form videos for each expression using extracted video slices.
        """
        logger.info(f"Creating long-form videos for {len(expressions)} expressions in {len(target_languages)} languages...")
        
        original_video = video_processor.find_video_file(str(subtitle_file))
        if not original_video:
            logger.error("No original video file found, cannot create long-form videos")
            raise RuntimeError("Original video file not found")
        
        logger.info(f"Using original video file: {original_video}")
        
        # Step 1: Extract video slices (reused) - These are RAW clips (no subs)
        extracted_slices = self._extract_slices(expressions, video_processor, original_video, test_mode=test_mode)
        
        # Step 2: Create videos for each language
        all_long_form_videos = {}
        
        for lang_idx, lang in enumerate(target_languages):
            logger.info(f"Creating videos for language: {lang}")
            if progress_callback:
                 # Map 50-80% progress
                lang_progress = 50 + int((lang_idx / len(target_languages)) * 30)
                progress_callback(lang_progress, f"Creating videos for {lang} ({lang_idx+1}/{len(target_languages)})...")

            if lang not in translated_expressions:
                logger.warning(f"No translations found for language {lang}, skipping")
                continue
            
            lang_expressions = translated_expressions[lang]
            lang_paths = self._ensure_lang_paths(paths, lang, output_dir)
            
            # Asset Generation & Master Clip Creation
            # We generate subtitles and create the "Master Clip" (burned subs) here.
            # This ensures the video passed to VideoEditor ALREADY has perfect internal sync.
            subtitle_dir = lang_paths.get('subtitles') or lang_paths['language_dir'] / "subtitles"
            subtitle_dir.mkdir(parents=True, exist_ok=True)
            
            # Helper to store master clips for this language
            master_clips: Dict[int, Path] = {}
            
            logger.info(f"Preparing assets (Subtitles & Master Clips) for {len(lang_expressions)} expressions...")
            
            for i, expression in enumerate(lang_expressions):
                if i not in extracted_slices:
                    logger.warning(f"Skipping asset generation for expression {i+1}: No raw slice found")
                    continue
                    
                raw_clip_path = extracted_slices[i]
                
                try:
                    # 1. Generate Subtitle File
                    base_expression = expressions[i] if i < len(expressions) else expression
                    expr_text = get_expr_attr(base_expression, 'expression', '')
                    safe_expression_short = sanitize_for_expression_filename(expr_text)[:30]
                    subtitle_filename = f"expression_{i+1:02d}_{safe_expression_short}.srt"
                    subtitle_output_path = subtitle_dir / subtitle_filename
                    
                    success = subtitle_processor.create_dual_language_subtitle_file(
                        expression,
                        str(subtitle_output_path)
                    )
                    
                    if not success:
                        logger.warning(f"Failed to generate subtitle file for expression {i+1}, skipping master clip creation")
                        continue
                        
                    # 2. Create Master Clip (Burn Subtitles into Raw Clip)
                    # Input: Raw Clip (starts at 0)
                    # Subtitles: Relative (starts at 0)
                    # We use apply_dual_subtitle_layers with start=0, duration=full.
                    # This uses "Input Seeking" (ss=0) which is valid and ensures sync.
                    
                    temp_master_clip = lang_paths['videos'] / f"temp_master_clip_burned_{i+1:02d}_{safe_expression_short}.mkv"
                    temp_master_clip.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Note: apply_dual_subtitle_layers handles the ffmpeg call
                    # We pass 0 as start time because the raw clip is already cut.
                    # We MUST use the duration of the clip.
                    duration = get_duration_seconds(str(raw_clip_path))
                    
                    apply_dual_subtitle_layers(
                        str(raw_clip_path),
                        str(subtitle_output_path),
                        "", 
                        str(temp_master_clip),
                        0.0, 
                        duration,
                        encoding_params={
                            'preset': 'ultrafast' if test_mode else 'slow',
                            'crf': 28 if test_mode else 18
                        } if test_mode else None
                    )
                    
                    if temp_master_clip.exists():
                        master_clips[i] = temp_master_clip
                        logger.debug(f"Created Master Clip with burned subtitles: {temp_master_clip.name}")
                    else:
                        logger.error(f"Failed to create Master Clip for expression {i+1}")

                except ffmpeg.Error as e:
                    logger.error(f"FFmpeg error preparing assets for expression {i+1}: {e.stderr.decode('utf8') if e.stderr else str(e)}")
                except Exception as e:
                    logger.error(f"Error preparing assets for expression {i+1}: {e}")
            
            lang_video_editor = VideoEditor(
                str(lang_paths['final_videos']),
                lang,
                episode_name,
                subtitle_processor=subtitle_processor,
                test_mode=test_mode
            )
            lang_video_editor.paths = lang_paths
            
            lang_long_form_videos = []
            
            for expr_idx, expression in enumerate(lang_expressions):
                logger.info(f"Processing short video for expression {expr_idx + 1}/{len(lang_expressions)}")
                
                # Debug: Log vocabulary annotations
                vocab = getattr(expression, 'vocabulary_annotations', [])
                logger.info(f"DEBUG: Expression {expr_idx+1} vocab annotations raw: {vocab}")
                if isinstance(vocab, list):
                    logger.info(f"DEBUG: Found {len(vocab)} annotations in Factory")
                else:
                    logger.info(f"DEBUG: Vocab annotations is {type(vocab)}")
                
                if expr_idx not in master_clips:
                    logger.warning(f"Skipping video creation for expression {expr_idx+1}: No master clip")
                    continue
                
                try:
                    # We pass the MASTER CLIP (with burned subs) as the context clip.
                    # VideoEditor will see it has a pre-extracted clip and use it.
                    # Since it already has subs, we don't need to apply them again.
                    long_form_video = lang_video_editor.create_long_form_video(
                        expression,
                        str(original_video), # Still passed for reference/audio extraction if needed
                        str(original_video),
                        expression_index=expr_idx,
                        pre_extracted_context_clip=master_clips[expr_idx]
                    )
                    lang_long_form_videos.append(long_form_video)
                except Exception as e:
                    logger.error(f"Error creating long-form video for {lang} - expr {expr_idx+1}: {e}")
                    continue
            
            if lang_long_form_videos:
                all_long_form_videos[lang] = lang_long_form_videos
                
            # Cleanup temp files for this editor
            try:
                # We could also clean up master_clips here if they are temps
                # But VideoEditor might track them if we registered them?
                # We didn't register them in temp_manager explicitly here, but they are in 'videos' dir
                # VideoEditor.cleanup cleans 'videos' dir usually?
                lang_video_editor._cleanup_temp_files(preserve_short_format=False)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp files for {lang}: {e}")
                
            # Explicit cleanup of Master Clips (they are intermediate)
            for clip in master_clips.values():
                try:
                    if clip.exists():
                        clip.unlink()
                except: pass
        
        # Step 3: Combine videos
        combined_videos = {}
        for lang, videos in all_long_form_videos.items():
            if not no_long_form:
                 lang_paths = paths['languages'][lang]
                 path = self._create_combined_long_form_video(videos, lang_paths)
                 if path:
                     combined_videos[lang] = path
        
        # Cleanup extracted slices (they were persistent temps)
        temp_manager = get_temp_manager()
        for slice_path in extracted_slices.values():
            try:
                if slice_path.exists():
                    # If TempFileManager was used with delete=False, we should clean up if we tracked it or just unlink
                    # Note: create_temp_file with delete=False doesn't auto-delete on exit.
                    # We need to manually remove them or rely on temp_manager if it tracked them.
                    # The implementation in main.py relied on `temp_manager` context but `delete=False`.
                    # Actually `temp_manager.create_temp_file` returns a path and cleans up IF `delete=True`.
                    # If `delete=False`, it yields path.
                    slice_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete extracted slice {slice_path}: {e}")
                
        return combined_videos

    def create_short_videos(
        self,
        target_languages: List[str],
        paths: Dict[str, Any],
        translated_expressions: Dict[str, List[ExpressionAnalysis]],
        base_expressions: List[ExpressionAnalysis],
        episode_name: str,
        subtitle_processor: SubtitleProcessor,
        video_editor_factory_method: callable, # Should return a VideoEditor
        short_form_max_duration: float = 180.0,
        output_dir: Path = None,
        progress_callback: Optional[callable] = None
    ):
        """Create short videos for target languages."""
        
        if not settings.is_short_video_enabled():
            logger.info("Short video generation disabled in settings")
            return

        for lang_idx, lang in enumerate(target_languages):
            logger.info(f"Creating short-format videos for language: {lang}")
            if progress_callback:
                 # Map 80-95% progress
                 progress = 80 + int((lang_idx / len(target_languages)) * 15)
                 progress_callback(progress, f"Creating short videos for {lang} ({lang_idx+1}/{len(target_languages)})...")
                 
            lang_paths = paths.get('languages', {}).get(lang)
            if not lang_paths:
                logger.error(f"Language paths not found for {lang}, skipping shorts")
                continue
                
            # Create editor
            video_editor = video_editor_factory_method(lang, lang_paths)
            
            try:
                self._create_short_videos_for_lang(
                    lang,
                    lang_paths,
                    video_editor,
                    translated_expressions.get(lang, base_expressions),
                    base_expressions,
                    episode_name,
                    short_form_max_duration,
                    subtitle_processor
                )
            except Exception as e:
                logger.error(f"Error creating short videos for {lang}: {e}")

    def _extract_slices(self, expressions, video_processor, original_video, test_mode: bool = False) -> Dict[int, Path]:
        logger.info("Extracting video slices...")
        extracted_slices = {}
        temp_manager = get_temp_manager()
        
        for expr_idx, base_expression in enumerate(expressions):
            try:
                expr_text = get_expr_attr(base_expression, 'expression', '')
                safe_filename = sanitize_for_expression_filename(expr_text)
                # We need persistent temp file
                # Using create_temp_file matches main.py logic (yields path)
                with temp_manager.create_temp_file(
                    prefix=f"context_clip_{expr_idx:02d}_{safe_filename[:30]}_",
                    suffix=".mkv",
                    delete=False
                ) as temp_context_clip:
                    start_time = get_expr_attr(base_expression, 'context_start_time')
                    end_time = get_expr_attr(base_expression, 'context_end_time')
                    success = video_processor.extract_clip(
                        Path(original_video),
                        start_time,
                        end_time,
                        temp_context_clip,
                        strategy='encode',  # Force encode for frame accuracy (fix sync issues)
                        encoding_params={
                            'preset': 'ultrafast' if test_mode else None,
                            'crf': 28 if test_mode else None
                        } if test_mode else None
                    )
                    if success:
                        extracted_slices[expr_idx] = temp_context_clip
                        
            except Exception as e:
                logger.error(f"Error extracting context clip for expression {expr_idx+1}: {e}")
                continue
        return extracted_slices

    def _ensure_lang_paths(self, paths, lang, output_dir):
        if lang in paths.get('languages', {}):
             return paths['languages'][lang]
        
        output_manager = OutputManager(str(output_dir))
        episode_paths = paths.get('episode', {})
        lang_paths = output_manager.create_language_structure(episode_paths, lang)
        
        if 'languages' not in paths:
            paths['languages'] = {}
        paths['languages'][lang] = lang_paths
        return lang_paths

    def _create_combined_long_form_video(self, long_form_videos: List[str], lang_paths: Dict) -> Optional[Path]:
        if not long_form_videos: 
            return None
            
        valid_videos = [v for v in long_form_videos if Path(v).exists() and Path(v).stat().st_size > 1000]
        if not valid_videos:
            return None
            
        long_dir = lang_paths.get('long') or lang_paths.get('language_dir') / "long"
        output_path = long_dir / "combined.mkv"
        
        # Instantiate editor to use combine_videos
        # We don't need language/episode specific setting strictly for combination if we pass output path
        # But we need to match constructor signature
        editor = VideoEditor(
             output_dir=str(long_dir),
             language_code="unknown", # Not critical for combination
             episode_name="combined"
        )
        return editor.combine_videos(valid_videos, str(output_path))

    def _create_short_videos_for_lang(
        self,
        lang: str,
        lang_paths: Dict,
        video_editor: VideoEditor,
        lang_expressions: List[ExpressionAnalysis],
        base_expressions: List[ExpressionAnalysis],
        episode_name: str,
        max_duration: float,
        subtitle_processor: SubtitleProcessor
    ):
        expressions_dir = lang_paths.get('expressions') or lang_paths['language_dir'] / "expressions"
        long_form_videos = sorted(list(Path(expressions_dir).glob("*.mkv")))
        
        if not long_form_videos:
            return

        long_form_video_map = {v.stem: v for v in long_form_videos}
        
        # Generate subtitle files for all expressions before creating short videos
        subtitle_dir = lang_paths.get('subtitles') or lang_paths['language_dir'] / "subtitles"
        subtitle_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Generating subtitle files for {len(lang_expressions)} expressions...")
        
        for i, expression in enumerate(lang_expressions):
            try:
                # Get base expression for filename
                base_expression = base_expressions[i] if i < len(base_expressions) else expression
                expr_text = get_expr_attr(base_expression, 'expression', '')
                safe_expression_short = sanitize_for_expression_filename(expr_text)[:30]
                
                # Create subtitle filename matching the pattern expected by create_short_form_from_long_form
                subtitle_filename = f"expression_{i+1:02d}_{safe_expression_short}.srt"
                subtitle_output_path = subtitle_dir / subtitle_filename
                
                # Generate subtitle file
                success = subtitle_processor.create_dual_language_subtitle_file(
                    expression,
                    str(subtitle_output_path)
                )
                
                if success:
                    logger.info(f"Generated subtitle file: {subtitle_filename}")
                else:
                    logger.warning(f"Failed to generate subtitle file for expression {i+1}")
                    
            except Exception as e:
                logger.error(f"Error generating subtitle for expression {i+1}: {e}")
                continue
        
        short_format_videos = []
        
        for i, expression in enumerate(lang_expressions):
            # Match using base expression if available logic from main.py
            # Match using constructed filename pattern (matching video_editor.py logic)
            # Use 'expression' (localized) because create_long_form_video uses localized expression for filenames
            expr_text = get_expr_attr(expression, 'expression', '')
            safe_name = sanitize_for_expression_filename(expr_text)
            # Must match creation format: expression_{index}_{safe[:50]}
            expected_stem = f"expression_{i+1:02d}_{safe_name[:50]}"
            
            if expected_stem in long_form_video_map:
                long_form_video = long_form_video_map[expected_stem]
                try:
                    output_path = video_editor.create_short_form_from_long_form(
                        str(long_form_video),
                        expression,
                        expression_index=i
                    )
                    duration = get_duration_seconds(str(output_path))
                    short_format_videos.append({
                        "path": str(output_path),
                        "duration": duration,
                        "expression": get_expr_attr(expression, 'expression'),
                        "expression_translation": get_expr_attr(expression, 'expression_translation'),
                        "language": lang,
                        "episode": episode_name,
                        "source_short": Path(output_path).name
                    })
                except Exception as e:
                    logger.error(f"Error creating short for expr {i+1}: {e}")
            else:
                 logger.warning(f"Could not find long-form video for expression {i+1} (expected: {expected_stem}.mkv)")

        # No batching - 1 expression = 1 short video (TICKET-090)
        # Each short video is already created in the 'shorts' directory
        logger.info(f"Created {len(short_format_videos)} individual short videos")
        
        video_editor._cleanup_temp_files(preserve_short_format=True)


