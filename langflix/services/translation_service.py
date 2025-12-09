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
            if lang == source_language_code:
                # Use original expressions (already translated during analysis)
                translated_expressions[lang] = expressions
                logger.info(f"Using original expressions for {lang} (already translated)")
                continue

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
