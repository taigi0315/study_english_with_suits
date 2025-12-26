"""
Pipeline Orchestrator: Contextual Localization Pipeline
Coordinates all agents to produce context-aware multilingual content
"""
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from langflix.pipeline.models import (
    EpisodeData,
    TranslationResult,
    PipelineConfig,
    ChunkResult
)
from langflix.pipeline.bible_manager import ShowBibleManager
from langflix.pipeline.agents.script_agent import ScriptAgent

logger = logging.getLogger(__name__)


class Pipeline:
    """
    Contextual Localization Pipeline

    Workflow:
    1. Phase 0: Get/Create Show Bible (Wikipedia)
    2. Phase 1: Extract expressions + Translate dialogues (Script Agent)

    Note: Translation is now handled by the Script Agent in Phase 1.
    Aggregator has been removed as episode_summary was not used anywhere.
    """

    def __init__(self, config: PipelineConfig):
        """
        Initialize Pipeline

        Args:
            config: Pipeline configuration
        """
        self.config = config

        # Clean up old debug files to prevent pollution from previous jobs
        self._cleanup_debug_files()

        # Initialize managers and agents
        self.bible_manager = ShowBibleManager()
        self.script_agent = ScriptAgent(output_dir=None, show_name=config.show_name)

        logger.info(f"Pipeline initialized for show: {config.show_name}")

    def run(
        self,
        subtitle_chunks: List[Dict[str, Any]],
        target_subtitle_chunks: List[Dict[str, Any]],
        language_level: str = "intermediate",
        max_expressions_per_chunk: int = 3,
        max_total_expressions: Optional[int] = None,
        target_duration: Optional[float] = None
    ) -> EpisodeData:
        """
        Run the complete pipeline
        """
        logger.info("🚀 Starting Pipeline execution")

        # Phase 0: Get Show Bible
        show_bible = self._get_show_bible()
        if not show_bible:
            raise ValueError(f"Failed to get Show Bible for: {self.config.show_name}")

        # Phase 1: Extract + Translate
        logger.info("📝 Phase 1: Running Script Agent (includes expression extraction and dialogue translation)...")
        
        from langflix import settings
        target_lang_name = None
        target_lang_code = None
        
        if self.config.target_languages:
            target_lang_input = self.config.target_languages[0]
            # Try to resolve code and name
            if len(target_lang_input) <= 3:
                target_lang_code = target_lang_input.lower()
                target_lang_name = settings.language_code_to_name(target_lang_code) or target_lang_code.capitalize()
            else:
                target_lang_name = target_lang_input
                target_lang_code = settings.language_name_to_code(target_lang_name) or target_lang_input
        
        # Get source language code if possible
        source_lang_name = self.config.source_language
        source_lang_code = settings.language_name_to_code(source_lang_name) if source_lang_name else None

        chunk_results = self.script_agent.analyze_chunks_batch(
            chunks=subtitle_chunks,
            target_chunks=target_subtitle_chunks,
            show_bible=show_bible,
            language_level=language_level,
            max_expressions_per_chunk=max_expressions_per_chunk,
            max_total_expressions=max_total_expressions,
            target_language=target_lang_name,
            target_language_code=target_lang_code,
            source_language=source_lang_name,
            source_language_code=source_lang_code,
            target_duration=target_duration
        )

        # Create episode data
        episode_data = EpisodeData(
            episode_id=f"{self.config.show_name}_{self.config.episode_name}",
            show_name=self.config.show_name,
            show_bible=show_bible,
            chunks=chunk_results
        )

        logger.info(
            f"✅ Pipeline complete: "
            f"{len(chunk_results)} chunks, "
            f"{len(episode_data.get_all_expressions())} expressions"
        )

        return episode_data

    # ... (skipping translate_episode and helpers which are unchanged)

    def _get_show_bible(self) -> str:
        """
        Get or create Show Bible
        """
        if not self.config.use_wikipedia:
            logger.info("Wikipedia disabled, using empty Show Bible")
            return f"=== SHOW BIBLE: {self.config.show_name} ===\n[No Wikipedia data]"

        logger.info(f"📖 Getting Show Bible for: {self.config.show_name}")

        bible = self.bible_manager.get_or_create_bible(
            show_name=self.config.show_name,
            force_refresh=not self.config.cache_show_bible
        )

        if not bible:
            logger.warning("Failed to create Show Bible, using minimal fallback")
            bible = f"=== SHOW BIBLE: {self.config.show_name} ===\n[Failed to retrieve data]"

        return bible

    def _find_chunk_for_expression(self, expression_idx, chunks):
        # Unchanged
        current_idx = 0
        for chunk in chunks:
            chunk_len = len(chunk.expressions)
            if current_idx + chunk_len > expression_idx:
                return chunk.chunk_id, chunk.chunk_summary
            current_idx += chunk_len
        if chunks: return chunks[-1].chunk_id, chunks[-1].chunk_summary
        return 0, ""

    def _cleanup_debug_files(self):
        # Unchanged
        debug_dir = Path(__file__).parent / "artifacts" / "debug"
        if not debug_dir.exists(): return
        try:
            import glob
            for pattern in ["script_agent_*.txt", "translator_*.txt"]:
                for file_path in glob.glob(str(debug_dir / pattern)):
                    try: Path(file_path).unlink()
                    except: pass
            logger.info("🧹 Cleaned up old debug files")
        except: pass

    def run_generator(
        self,
        subtitle_chunks: List[Dict[str, Any]],
        target_subtitle_chunks: List[Dict[str, Any]],
        language_level: str = "intermediate",
        max_expressions_per_chunk: int = 3,
        max_total_expressions: Optional[int] = None,
        target_duration: Optional[float] = None
    ):
        """
        Run the pipeline yielding chunk results
        """
        logger.info("🚀 Starting Pipeline execution (Streaming Mode)")

        # Phase 0: Get Show Bible
        show_bible = self._get_show_bible()
        if not show_bible:
            raise ValueError(f"Failed to get Show Bible for: {self.config.show_name}")

        # Phase 1: Extract + Translate
        logger.info("📝 Phase 1: Running Script Agent...")
        
        from langflix import settings
        target_lang_name = None
        target_lang_code = None
        
        if self.config.target_languages:
            target_lang_input = self.config.target_languages[0]
            # Try to resolve code and name
            if len(target_lang_input) <= 3:
                target_lang_code = target_lang_input.lower()
                target_lang_name = settings.language_code_to_name(target_lang_code) or target_lang_code.capitalize()
            else:
                target_lang_name = target_lang_input
                target_lang_code = settings.language_name_to_code(target_lang_name) or target_lang_input
        
        # Get source language code if possible
        source_lang_name = self.config.source_language
        source_lang_code = settings.language_name_to_code(source_lang_name) if source_lang_name else None

        generator = self.script_agent.analyze_chunks_generator(
            chunks=subtitle_chunks,
            target_chunks=target_subtitle_chunks,
            show_bible=show_bible,
            language_level=language_level,
            max_expressions_per_chunk=max_expressions_per_chunk,
            max_total_expressions=max_total_expressions,
            target_language=target_lang_name,
            target_language_code=target_lang_code,
            source_language=source_lang_name,
            source_language_code=source_lang_code,
            target_duration=target_duration
        )
        
        for chunk_result in generator:
            yield chunk_result

    def translate_chunk_result(
        self,
        chunk_result: ChunkResult
    ) -> List[TranslationResult]:
        """
        Convert a single chunk's expressions to TranslationResult format.
        """
        from langflix.pipeline.models import LocalizationData
        from langflix import settings
        
        translation_results = []
        
        # Determine target language from config/settings (same logic as translate_episode)
        if self.config.target_languages:
            target_lang_input = self.config.target_languages[0]
            if len(target_lang_input) <= 3:
                target_lang_code = target_lang_input.lower()
                target_lang_name = settings.language_code_to_name(target_lang_code) or target_lang_code.capitalize()
            else:
                target_lang_name = target_lang_input
                target_lang_code = settings.language_name_to_code(target_lang_name) or target_lang_input
        else:
            target_lang_code = settings.get_target_language_code()
            target_lang_name = settings.get_default_target_language()

        for idx, expression in enumerate(chunk_result.expressions):
            # Extract localized dialogue if possible
            expr_dial_trans = ""
            expr_idx = expression.get("expression_dialogue_index")
            dialogues = expression.get("dialogues", [])

            # New format: dialogues is a list of {index, timestamp, en, ko, ...}
            if expr_idx is not None and isinstance(dialogues, list):
                for dial_entry in dialogues:
                    if dial_entry.get("index") == expr_idx:
                        expr_dial_trans = dial_entry.get(target_lang_code, "")
                        break
            
            # Create LocalizationData
            loc_data = LocalizationData(
                target_lang=target_lang_code,
                target_lang_name=target_lang_name,
                expression_translated=expression.get("expression_translation") or expression.get("expression_translated", ""),
                expression_dialogue_translated=expr_dial_trans,
                catchy_keywords_translated=expression.get("catchy_keywords", []),
                viral_title=expression.get("title") or expression.get("viral_title", ""),
                narrations=expression.get("narrations", []),
                vocabulary_annotations=expression.get("vocabulary_annotations", []),
                expression_annotations=expression.get("expression_annotations", []),
                translation_notes=expression.get("translation_notes", "")
            )

            # Create TranslationResult
            result = TranslationResult(
                expression=expression.get("expression", ""),
                expression_dialogue=expression.get("expression_dialogue", ""),
                context_summary_eng=expression.get("context_summary_eng"),
                start_time=expression.get("context_start_time", "00:00:00.000"),
                end_time=expression.get("context_end_time", "00:00:00.000"),
                expression_start_time=expression.get("expression_start_time"),
                expression_end_time=expression.get("expression_end_time"),
                dialogues=dialogues,
                scene_type=expression.get("scene_type"),
                similar_expressions=expression.get("similar_expressions", []),
                catchy_keywords=expression.get("catchy_keywords", []),
                chunk_id=chunk_result.chunk_id,
                chunk_summary=chunk_result.chunk_summary,
                localizations=[loc_data]
            )
            translation_results.append(result)
            
        return translation_results
