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
        
        NOTE: The initial expression analysis LLM call already provides translations
        in the target language specified in the prompt. This service is only needed
        when translating to ADDITIONAL languages beyond the initial target.
        
        Args:
            expressions: List of expressions to translate.
            source_language_code: The source language code (usually the code used for analysis).
            target_languages: List of target language codes.
            progress_callback: Optional callback for progress.
            
        Returns:
            Dictionary mapping language code to list of translated expressions.
        """
        translated_expressions = {}
        
        # Check if expressions already have translations from initial LLM call
        has_existing_translations = False
        if expressions and len(expressions) > 0:
            first_expr = expressions[0]
            if (first_expr.translation and len(first_expr.translation) > 0 and 
                first_expr.expression_translation):
                has_existing_translations = True
                logger.info(f"Expressions already have translations from initial LLM analysis")
        
        for lang_idx, lang in enumerate(target_languages):
            # Normalize language codes for comparison (case-insensitive)
            lang_normalized = lang.lower().strip()
            source_normalized = source_language_code.lower().strip()
            
            # Check if this is the source/target language from initial analysis
            # Expressions already have translations from the initial LLM call
            if lang_normalized == source_normalized or has_existing_translations:
                # Use original expressions (already translated during analysis)
                translated_expressions[lang] = expressions
                logger.info(f"✅ Using existing translations for {lang} (from initial LLM analysis - no extra API calls needed)")
                continue
            
            # Only make additional LLM calls if we need to translate to a NEW language
            # that wasn't covered in the initial analysis
            logger.info(f"Translating {len(expressions)} expressions to NEW language: {lang}...")
            lang_expressions = []
            
            for expr_idx, expr in enumerate(expressions):
                if progress_callback:
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

