from typing import Optional
import logging
from typing import List, Dict
from langflix.core.models import ExpressionAnalysis
from langflix.core.translator import translate_expression_to_languages

logger = logging.getLogger(__name__)

class TranslationService:
    """Service for translating expressions."""

    def translate(
        self,
        expressions: List[ExpressionAnalysis],
        source_language_code: str,
        target_languages: List[str],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, List[ExpressionAnalysis]]:
        """
        Translate expressions to multiple target languages.
        
        Args:
            expressions: List of expressions to translate.
            source_language_code: The source language code (usually the code used for analysis).
            target_languages: List of target language codes.
            progress_callback: Optional callback for progress.
            
        Returns:
            Dictionary mapping language code to list of translated expressions.
        """
        translated_expressions = {}
        
        for lang_idx, lang in enumerate(target_languages):
            # Normalize language codes for comparison (case-insensitive)
            lang_normalized = lang.lower().strip()
            source_normalized = source_language_code.lower().strip()
            
            # Check if this is the source language - expressions already have translations
            # from the initial expression analysis LLM call
            if lang_normalized == source_normalized:
                # Use original expressions (already translated during analysis)
                translated_expressions[lang] = expressions
                logger.info(f"✅ Using existing translations for {lang} (already in ExpressionAnalysis from initial LLM call)")
                continue
            
            # Check if expressions already have translations (sanity check)
            if expressions and len(expressions) > 0:
                first_expr = expressions[0]
                if first_expr.translation and len(first_expr.translation) > 0:
                    if first_expr.expression_translation:
                        # Expressions already have translations - this is the source language
                        logger.debug(f"Expressions already have translations, skipping redundant translation for {lang}")

            logger.info(f"Translating {len(expressions)} expressions to {lang}...")
            lang_expressions = []
            
            for expr_idx, expr in enumerate(expressions):
                if progress_callback:
                    # Generic progress generic across languages isn't perfect but sufficient
                    progress_callback(lang_idx, len(target_languages), expr_idx, len(expressions))
                    
                try:
                    translated_dict = translate_expression_to_languages(expr, [lang])
                    if lang in translated_dict:
                        lang_expressions.append(translated_dict[lang])
                    else:
                        logger.warning(f"Translation to {lang} failed for expression {expr_idx+1}, skipping")
                except Exception as e:
                    logger.error(f"Error translating expression {expr_idx+1} to {lang}: {e}")
                    continue
            
            translated_expressions[lang] = lang_expressions
            logger.info(f"✅ Translated {len(lang_expressions)} expressions to {lang}")
            
        return translated_expressions

