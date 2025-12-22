"""
Translator Agent: Context-Aware Localization
Uses Show Bible + Master Summary for culturally-appropriate translations
"""
import logging
import json
from typing import List, Dict, Any
from pathlib import Path

from langflix.pipeline.models import LocalizationData
from langflix.core.llm_client import get_gemini_client
from langflix.utils.language_utils import convert_language_code_to_name

logger = logging.getLogger(__name__)


class TranslatorAgent:
    """
    Translator that applies context-aware localization
    Uses Show Bible for relationship dynamics and Master Summary for emotional tone
    """

    # Language code to full name mapping
    LANGUAGE_NAMES = {
        "ko": "Korean",
        "ja": "Japanese",
        "es": "Spanish",
        "zh": "Chinese",
        "fr": "French",
        "de": "German",
        "en": "English"
    }

    def __init__(self, model_name: str = "gemini-1.5-pro"):
        """
        Initialize Translator Agent

        Args:
            model_name: LLM model to use (should be smart model like 1.5 Pro)
        """
        self.model_name = model_name
        self.client = get_gemini_client()

        # Load prompt template
        prompt_path = Path(__file__).parent.parent / "prompts" / "translator.txt"
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.prompt_template = f.read()

        logger.info(f"TranslatorAgent initialized with model: {self.model_name}")

    def translate_expressions(
        self,
        expressions: List[Dict[str, Any]],
        show_bible: str,
        master_summary: str,
        target_lang: str
    ) -> List[LocalizationData]:
        """
        Translate expressions with full context awareness

        Args:
            expressions: List of expression dictionaries
            show_bible: Show Bible content
            master_summary: Master episode summary
            target_lang: Target language code (e.g., 'ko', 'ja', 'es')

        Returns:
            List of LocalizationData with context-aware translations
        """
        if not expressions:
            logger.warning("No expressions to translate")
            return []

        target_lang_name = self.LANGUAGE_NAMES.get(target_lang, target_lang.upper())
        logger.info(f"🌐 Translating {len(expressions)} expressions to {target_lang_name}")

        # Format expressions for prompt
        expressions_json = self._format_expressions(expressions)

        # Build prompt
        prompt = self.prompt_template.format(
            target_lang_name=target_lang_name,
            show_bible=show_bible,
            master_summary=master_summary,
            expressions_json=expressions_json
        )

        # Call LLM
        try:
            response = self._call_llm(prompt)
            localizations = self._parse_response(response, target_lang, target_lang_name)

            logger.info(f"✅ Translated {len(localizations)} expressions to {target_lang_name}")
            return localizations

        except Exception as e:
            logger.error(f"❌ Translation failed for {target_lang_name}: {e}")
            # Return empty localizations as fallback
            return []

    def translate_to_multiple_languages(
        self,
        expressions: List[Dict[str, Any]],
        show_bible: str,
        master_summary: str,
        target_languages: List[str]
    ) -> Dict[str, List[LocalizationData]]:
        """
        Translate to multiple target languages

        Args:
            expressions: List of expressions
            show_bible: Show Bible content
            master_summary: Master episode summary
            target_languages: List of language codes

        Returns:
            Dictionary mapping language code to localizations
        """
        results = {}

        for target_lang in target_languages:
            localizations = self.translate_expressions(
                expressions=expressions,
                show_bible=show_bible,
                master_summary=master_summary,
                target_lang=target_lang
            )
            results[target_lang] = localizations

        return results

    def _format_expressions(self, expressions: List[Dict[str, Any]]) -> str:
        """
        Format expressions as JSON for prompt

        Args:
            expressions: List of expression dictionaries

        Returns:
            JSON string
        """
        # Simplify expression data for translation (only need key fields)
        simplified = []
        for idx, expr in enumerate(expressions):
            simplified.append({
                "id": idx,
                "expression": expr.get("expression", ""),
                "expression_dialogue": expr.get("expression_dialogue", ""),
                "catchy_keywords": expr.get("catchy_keywords", [])
            })

        return json.dumps(simplified, indent=2, ensure_ascii=False)

    def _call_llm(self, prompt: str) -> str:
        """
        Call LLM with translation prompt

        Args:
            prompt: Formatted prompt

        Returns:
            LLM response text
        """
        model = self.client.GenerativeModel(self.model_name)

        generation_config = {
            "temperature": 0.2,  # Lower for more consistent translations
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 8192,
        }

        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )

        return response.text

    def _parse_response(
        self,
        response: str,
        target_lang: str,
        target_lang_name: str
    ) -> List[LocalizationData]:
        """
        Parse LLM JSON response into LocalizationData objects

        Args:
            response: Raw LLM response
            target_lang: Language code
            target_lang_name: Language full name

        Returns:
            List of LocalizationData objects
        """
        # Clean response (remove markdown code blocks if present)
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)

            localizations = []
            for item in data:
                loc = LocalizationData(
                    target_lang=target_lang,
                    target_lang_name=target_lang_name,
                    expression_translated=item.get("translated_expression", ""),
                    expression_dialogue_translated=item.get("translated_dialogue", ""),
                    catchy_keywords_translated=item.get("catchy_keywords_translated", []),
                    translation_notes=item.get("translation_notes", "")
                )
                localizations.append(loc)

            return localizations

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse translation JSON: {e}")
            logger.debug(f"Response was: {response[:500]}...")
            raise ValueError(f"Invalid JSON response from translator: {e}")


# Backward compatibility alias
TranslatorAgentV3 = TranslatorAgent
