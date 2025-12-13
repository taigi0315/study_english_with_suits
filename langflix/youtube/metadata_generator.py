"""
YouTube Metadata Generator
Automatically generates titles, descriptions, and tags for YouTube videos
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from langflix.youtube.uploader import YouTubeVideoMetadata
from langflix.youtube.video_manager import VideoMetadata
from langflix.utils.filename_utils import extract_show_name
from langflix import settings

logger = logging.getLogger(__name__)

@dataclass
class YouTubeContentTemplate:
    """Template for YouTube content generation"""
    title_template: str
    description_template: str
    default_tags: List[str]
    category_mapping: Dict[str, str]

class YouTubeMetadataGenerator:
    """Generates YouTube metadata for educational videos"""
    
    def __init__(self):
        self.templates = self._load_templates()
        self.category_mapping = {
            "educational": "22",  # People & Blogs
            "short": "22",        # People & Blogs  
            "final": "22",        # People & Blogs
            "slide": "22",        # People & Blogs
            "context": "22"       # People & Blogs
        }
        # Translation mappings for template strings (TICKET-056)
        self.translations = self._load_translations()
    
    def _load_translations(self) -> Dict[str, Dict[str, str]]:
        """Load translations for template strings by target language (TICKET-056, TICKET-060, TICKET-074)"""
        return {
            "Korean": {
                "quick_lesson": "수트에서 배우는 빠른 영어 레슨!",
                "expression_label": "Expression",
                "meaning_label": "의미",
                "watch_and_learn": "좋아하는 쇼에서 보고 배우세요!",
                "title_template": "{expression} | {translation} | {episode}",
                # Long-form/Final video templates (TICKET-060)
                "long_form_title": "{expression} | {translation} | {episode}",
                "long_form_description_intro": "수트 드라마에서 배우는 실용적인 영어 표현들을 모았습니다.",
                "final_title": "완전한 영어 레슨: {episode} | 수트에서 배우는 5개 이상의 표현",
                "final_description_intro": "수트 {episode}의 완전한 영어 레슨!",
                "learn_expressions": "이 포괄적인 레슨에서 여러 영어 표현을 배우게 됩니다:",
                "what_you_master": "마스터할 내용:",
                "real_expressions": "원어민이 사용하는 실제 영어 표현",
                "context_usage": "맥락과 적절한 사용법",
                "pronunciation": "발음과 억양",
                "similar_expressions": "유사한 표현과 대안",
                "watch_original": "원본 장면을 보고 자연스럽게 배우세요!",
                "check_meaning": "의미를 영상에서 확인하세요"
            },
            "English": {
                "quick_lesson": "Quick English lesson from Suits!",
                "expression_label": "Expression",
                "meaning_label": "Meaning",
                "watch_and_learn": "Watch and learn from your favorite show!",
                "title_template": "{expression} | {translation} | from {episode}",
                # Long-form/Final video templates (TICKET-060)
                "long_form_title": "{expression} | {translation} | from {episode}",
                "long_form_description_intro": "Learn practical English expressions from the hit TV show Suits!",
                "final_title": "Complete English Lesson: {episode} | Learn 5+ Expressions from Suits",
                "final_description_intro": "Complete English lesson from Suits {episode}!",
                "learn_expressions": "In this comprehensive lesson, you'll learn multiple English expressions:",
                "what_you_master": "What you'll master:",
                "real_expressions": "Real English expressions used by native speakers",
                "context_usage": "Context and proper usage",
                "pronunciation": "Pronunciation and intonation",
                "similar_expressions": "Similar expressions and alternatives",
                "watch_original": "Watch the original scenes and learn naturally!",
                "check_meaning": "Check the meaning in the video"
            },
            "Japanese": {
                "quick_lesson": "スーツから学ぶクイック英語レッスン！",
                "expression_label": "Expression",
                "meaning_label": "意味",
                "watch_and_learn": "お気に入りの番組から見て学びましょう！",
                "title_template": "{expression} | {translation} | from {episode}",
                # Long-form/Final video templates (TICKET-060)
                "long_form_title": "{expression} | {translation} | from {episode}",
                "long_form_description_intro": "人気ドラマ「スーツ」から実用的な英語表現を学びましょう！",
                "final_title": "完全な英語レッスン: {episode} | スーツから5つ以上の表現を学ぶ",
                "final_description_intro": "スーツ {episode}の完全な英語レッスン！",
                "learn_expressions": "この包括的なレッスンでは、複数の英語表現を学びます:",
                "what_you_master": "マスターする内容:",
                "real_expressions": "ネイティブスピーカーが使用する実際の英語表現",
                "context_usage": "文脈と適切な使用方法",
                "pronunciation": "発音とイントネーション",
                "similar_expressions": "類似した表現と代替案",
                "watch_original": "オリジナルのシーンを見て自然に学びましょう！",
                "check_meaning": "動画で意味を確認してください"
            },
            "Chinese": {
                "quick_lesson": "从《金装律师》快速学习英语！",
                "expression_label": "Expression",
                "meaning_label": "含义",
                "watch_and_learn": "从你最喜欢的节目中观看和学习！",
                "title_template": "{expression} | {translation} | from {episode}",
                # Long-form/Final video templates (TICKET-060)
                "long_form_title": "{expression} | {translation} | from {episode}",
                "long_form_description_intro": "从热门电视剧《金装律师》中学习实用的英语表达！",
                "final_title": "完整英语课程: {episode} | 从《金装律师》学习5个以上表达",
                "final_description_intro": "《金装律师》{episode}的完整英语课程！",
                "learn_expressions": "在这门综合课程中，您将学习多个英语表达:",
                "what_you_master": "您将掌握:",
                "real_expressions": "母语者使用的真实英语表达",
                "context_usage": "语境和正确用法",
                "pronunciation": "发音和语调",
                "similar_expressions": "类似表达和替代方案",
                "watch_original": "观看原始场景并自然学习！",
                "check_meaning": "在视频中查看含义"
            },
            "Spanish": {
                "quick_lesson": "¡Lección rápida de inglés de Suits!",
                "expression_label": "Expression",
                "meaning_label": "Significado",
                "watch_and_learn": "¡Mira y aprende de tu programa favorito!",
                "title_template": "{expression} | {translation} | from {episode}",
                # Long-form/Final video templates (TICKET-060)
                "long_form_title": "{expression} | {translation} | from {episode}",
                "long_form_description_intro": "¡Aprende expresiones prácticas en inglés de la exitosa serie de TV Suits!",
                "final_title": "Lección completa de inglés: {episode} | Aprende 5+ expresiones de Suits",
                "final_description_intro": "¡Lección completa de inglés de Suits {episode}!",
                "learn_expressions": "En esta lección completa, aprenderás múltiples expresiones en inglés:",
                "what_you_master": "Lo que dominarás:",
                "real_expressions": "Expresiones reales en inglés usadas por hablantes nativos",
                "context_usage": "Contexto y uso apropiado",
                "pronunciation": "Pronunciación y entonación",
                "similar_expressions": "Expresiones similares y alternativas",
                "watch_original": "¡Mira las escenas originales y aprende naturalmente!",
                "check_meaning": "Consulta el significado en el video"
            },
            "French": {
                "quick_lesson": "Leçon d'anglais rapide de Suits !",
                "expression_label": "Expression",
                "meaning_label": "Signification",
                "watch_and_learn": "Regardez et apprenez de votre émission préférée !",
                "title_template": "{expression} | {translation} | from {episode}",
                # Long-form/Final video templates (TICKET-060)
                "long_form_title": "{expression} | {translation} | from {episode}",
                "long_form_description_intro": "Apprenez des expressions anglaises pratiques de la série à succès Suits !",
                "final_title": "Leçon d'anglais complète : {episode} | Apprenez 5+ expressions de Suits",
                "final_description_intro": "Leçon d'anglais complète de Suits {episode} !",
                "learn_expressions": "Dans cette leçon complète, vous apprendrez plusieurs expressions anglaises :",
                "what_you_master": "Ce que vous maîtriserez :",
                "real_expressions": "Expressions anglaises réelles utilisées par les locuteurs natifs",
                "context_usage": "Contexte et utilisation appropriée",
                "pronunciation": "Prononciation et intonation",
                "similar_expressions": "Expressions similaires et alternatives",
                "watch_original": "Regardez les scènes originales et apprenez naturellement !",
                "check_meaning": "Vérifiez la signification dans la vidéo"
            }
        }
    
    def _get_target_language(self) -> str:
        """Get target language from settings (TICKET-056)"""
        return getattr(settings, 'TARGET_LANGUAGE', 'Korean')
    
    def _get_template_translation(self, key: str, target_language: Optional[str] = None) -> str:
        """Get translated string for template (TICKET-056)"""
        if target_language is None:
            target_language = self._get_target_language()
        
        # Fallback to English if translation not found
        translations = self.translations.get(target_language, self.translations.get("English", {}))
        return translations.get(key, key)
    
    def _load_templates(self) -> Dict[str, YouTubeContentTemplate]:
        """Load content templates for different video types"""
        return {
            "educational": YouTubeContentTemplate(
                title_template="{expression} | {translation} | from {episode}",
                description_template="""🎬 Learn English expressions from the hit TV show Suits!

📚 In this video, we'll learn the expression: "{expression}"
📖 Translation: {translation}
🎯 Episode: {episode}
🌍 Language: {language}

💡 What you'll learn:
• How to use "{expression}" in real conversations
• Context and meaning of the expression
• Similar expressions you can use
• Pronunciation tips

📺 Watch the original scene from Suits and learn naturally!

#EnglishLearning #Suits #EnglishExpressions #LearnEnglish #EnglishWithTV #EnglishConversation #EnglishGrammar #EnglishVocabulary #EnglishSpeaking #EnglishPractice #SuitsTVShow #EnglishLessons #EnglishTips #EnglishStudy #EnglishFluency""",
                default_tags=[
                    "English Learning", "Suits", "English Expressions", "Learn English",
                    "English with TV", "English Conversation", "English Grammar",
                    "English Vocabulary", "English Speaking", "English Practice"
                ],
                category_mapping={"educational": "22"}
            ),
            
            "short": YouTubeContentTemplate(
                title_template="{title_template}",  # Will be replaced with target language version
                description_template="{description_template}",  # Will be replaced with target language version
                default_tags=[
                    "Shorts", "EnglishLearning", "Suits", "EnglishExpressions", "LearnEnglish"
                ],  # Reduced to 3-5 most relevant tags (TICKET-056)
                category_mapping={"short": "22"}
            ),
            
            "final": YouTubeContentTemplate(
                title_template="Complete English Lesson: {episode} | Learn 5+ Expressions from Suits",
                description_template="""🎬 Complete English lesson from Suits {episode}!

📚 In this comprehensive lesson, you'll learn multiple English expressions:
• {expressions_list}

🎯 What you'll master:
• Real English expressions used by native speakers
• Context and proper usage
• Pronunciation and intonation
• Similar expressions and alternatives

📺 Watch the original scenes and learn naturally!

#EnglishLearning #Suits #EnglishExpressions #LearnEnglish #EnglishWithTV #EnglishConversation #EnglishGrammar #EnglishVocabulary #EnglishSpeaking #EnglishPractice #SuitsTVShow #EnglishLessons #EnglishTips #EnglishStudy #EnglishFluency""",
                default_tags=[
                    "English Learning", "Suits", "English Expressions", "Learn English",
                    "English with TV", "English Conversation", "English Grammar",
                    "English Vocabulary", "English Speaking", "English Practice",
                    "Complete Lesson", "English Study"
                ],
                category_mapping={"final": "22"}
            )
        }
    
    def generate_metadata(
        self, 
        video_metadata: VideoMetadata,
        custom_title: Optional[str] = None,
        custom_description: Optional[str] = None,
        additional_tags: Optional[List[str]] = None,
        privacy_status: str = "private",
        target_language: Optional[str] = None
    ) -> YouTubeVideoMetadata:
        """Generate YouTube metadata for a video
        
        Args:
            video_metadata: Video metadata object
            custom_title: Optional custom title override
            custom_description: Optional custom description override
            additional_tags: Optional additional tags
            privacy_status: Privacy status (default: "private")
            target_language: Target language name (e.g., "Korean", "English"). 
                           If None, uses settings.TARGET_LANGUAGE (TICKET-056)
        """
        if target_language is None:
            target_language = self._get_target_language()
        
        template = self.templates.get(video_metadata.video_type, self.templates["educational"])
        
        # Generate title
        title = self._generate_title(video_metadata, template, custom_title, target_language)
        
        # Generate description
        description = self._generate_description(video_metadata, template, custom_description, target_language)
        
        # Generate tags (TICKET-060: Use target language)
        tags = self._generate_tags(video_metadata, template, additional_tags, target_language)
        
        # Get category
        category_id = self.category_mapping.get(video_metadata.video_type, "22")
        
        return YouTubeVideoMetadata(
            title=title,
            description=description,
            tags=tags,
            category_id=category_id,
            privacy_status=privacy_status
        )
    
    def _generate_title(self, video_metadata: VideoMetadata, template: YouTubeContentTemplate, custom_title: Optional[str], target_language: Optional[str] = None) -> str:
        """Generate video title"""
        if custom_title:
            logger.debug(f"Using custom title: {custom_title}")
            return custom_title.strip()
        
        logger.debug(f"Generating title for video_type={video_metadata.video_type}, template='{template.title_template}'")
        logger.debug(f"  Input metadata: expression='{video_metadata.expression}', episode='{video_metadata.episode}', language='{video_metadata.language}'")
        
        # Get target language if not provided (TICKET-060)
        if target_language is None:
            target_language = self._get_target_language()
        
        # Use target language template for ALL video types (TICKET-060)
        if target_language:
            if video_metadata.video_type == "short":
                title_template = self._get_template_translation("title_template", target_language)
            elif video_metadata.video_type == "final":
                title_template = self._get_template_translation("final_title", target_language)
            elif video_metadata.video_type in ["educational", "long-form"]:
                title_template = self._get_template_translation("long_form_title", target_language)
            else:
                # Fallback to English template for unknown types
                title_template = template.title_template
        else:
            title_template = template.title_template
        
        # Use translated expression if available (TICKET-060)
        # Prefer expression_translation for target language, fallback to English expression
        expression = (video_metadata.expression or "").strip()
        translation = (video_metadata.expression_translation or self._get_translation(video_metadata, target_language)).strip()
        
        if not expression:
            # Try to extract from filename if expression is empty
            logger.debug(f"Expression is empty, trying to extract from filename: {video_metadata.path}")
            extracted = self._extract_expression_from_filename(video_metadata.path)
            if extracted:
                expression = extracted
                logger.debug(f"Extracted expression: {expression}")
            else:
                # For batch videos or when extraction fails, use a generic expression
                # This ensures title generation doesn't fail
                expression = "English Expressions"
                logger.debug(f"Using default expression: {expression}")
        
        # Format episode as "Suits.S01E02" format
        episode_raw = video_metadata.episode or ""
        if not episode_raw:
            # Try to extract from filename if episode is empty
            logger.debug(f"Episode is empty, trying to extract from filename: {video_metadata.path}")
            episode_raw = self._extract_episode_from_filename(video_metadata.path) or ""
        
        # Format episode: ensure "Suits." prefix and remove quality/resolution info
        episode = self._format_episode_for_title(episode_raw)
        logger.debug(f"Formatted episode: '{episode}'")
        
        language = (video_metadata.language or "en").upper()
        
        logger.debug(f"Final values: expression='{expression}', translation='{translation}', episode='{episode}', language='{language}'")
        
        try:
            # Prepare format arguments based on template requirements
            format_args = {}
            
            # Check which placeholders are in the template
            if "{expression}" in title_template:
                format_args["expression"] = expression
            if "{translation}" in title_template:
                format_args["translation"] = translation
            if "{episode}" in title_template:
                format_args["episode"] = episode
            if "{language}" in title_template:
                format_args["language"] = language
            
            logger.debug(f"Format args: {format_args}, template: {title_template}")
            
            # Format with only the required arguments
            title = title_template.format(**format_args)
            logger.debug(f"Formatted title: '{title}'")
            
            # Ensure title is not empty and strip whitespace
            title = title.strip()
            if not title or title == "":
                # Fallback title based on video type and target language
                if video_metadata.video_type == "short":
                    if target_language:
                        fallback_template = self._get_template_translation("title_template", target_language)
                        title = fallback_template.format(expression=expression, translation=translation, episode=episode) if "{expression}" in fallback_template else f"{expression} | {translation} | from {episode}"
                    else:
                        title = f"{expression} | {translation} | from {episode}"
                else:
                    title = f"{expression} | {translation} | from {episode}"
                logger.warning(f"Generated empty title, using fallback: {title}")
            
            # Final validation - ensure title is not empty
            if not title or title.strip() == "":
                title = "Learn English Video"
                logger.error(f"All title generation methods failed for {video_metadata.path}, using minimal fallback")
            
            logger.info(f"✅ Final generated title: '{title}'")
            return title
        except (KeyError, AttributeError, ValueError) as e:
            logger.error(f"❌ Error generating title from template: {e}")
            logger.error(f"  Template: {title_template}")
            logger.error(f"  Expression: {expression}, Translation: {translation}, Episode: {episode}, Language: {language}")
            logger.error(f"  Video path: {video_metadata.path}")
            # Fallback title based on video type
            if video_metadata.video_type == "short":
                fallback = f"{expression} | {translation} | from {episode}"
            else:
                fallback = f"{expression} | {translation} | from {episode}"
            final_fallback = fallback if fallback.strip() else "Learn English Video"
            logger.warning(f"Using error fallback: '{final_fallback}'")
            return final_fallback
    
    def _extract_expression_from_filename(self, filepath: str) -> Optional[str]:
        """Try to extract expression from filename as fallback"""
        try:
            from pathlib import Path
            filename = Path(filepath).stem
            
            # For short-form batch videos (short-form_episode_batch), expression is not in filename
            # Check if it's a batch video
            if filename.startswith("short-form_"):
                # This is a batch video - expression is not available in filename
                # Return None to use default fallback
                return None
            
            # For individual short_form_{expression} videos, extract expression
            if filename.startswith("short_form_"):
                # Format: short_form_{expression}
                parts = filename.split("_", 2)  # Split into ['short', 'form', '{expression}']
                if len(parts) >= 3:
                    return parts[2].replace("_", " ").title()  # Convert underscores to spaces
            
            # Try to extract expression from other filename patterns
            parts = filename.split('_')
            if len(parts) > 1:
                return parts[-1].replace("_", " ").title()  # Usually expression is at the end
            return None
        except Exception:
            return None
    
    def _extract_episode_from_filename(self, filepath: str) -> Optional[str]:
        """Try to extract episode from filename as fallback"""
        try:
            from pathlib import Path
            filename = Path(filepath).stem
            # Try to extract episode patterns like S01E01, S1E1, etc.
            import re
            episode_match = re.search(r'[Ss](\d+)[Ee](\d+)', filename)
            if episode_match:
                return f"S{episode_match.group(1)}E{episode_match.group(2)}"
            return None
        except Exception:
            return None
    
    def _format_episode_for_title(self, episode_raw: str) -> str:
        """Format episode as 'Suits.S01E02' format for title"""
        if not episode_raw:
            return "Suits"
        
        import re
        # Extract S01E02 pattern
        episode_match = re.search(r'[Ss](\d+)[Ee](\d+)', episode_raw)
        
        # If we have a show name in the string, extract it cleanly
        # Use our improved extract_show_name to clean up garbage (WEB-RIP, 1080p, etc)
        # Check if the raw string is just garbage metadata (e.g. "2025.1080p.webrip")
        # If it doesn't look like an episode code or show name, be careful
        
        cleaned_name = extract_show_name(episode_raw)
        if cleaned_name == "Unknown Show":
             # Try to find "Suits" or just use "Suits" as fallback if it looks really bad
             if "suits" in episode_raw.lower():
                 cleaned_name = "Suits"
             else:
                 # If we have an episode code, use that at least
                 if episode_match:
                     return f"Suits.S{episode_match.group(1)}E{episode_match.group(2)}"
                 return "Suits"

        if episode_match:
            # We have SxxExx
            # If cleaned_name already has SxxExx, return it
            if re.search(r'[Ss]\d+[Ee]\d+', cleaned_name):
                return cleaned_name
            else:
                 return f"{cleaned_name}.S{episode_match.group(1)}E{episode_match.group(2)}"
        
        # No episode code, but improved name
        return cleaned_name
    
    def _generate_description(self, video_metadata: VideoMetadata, template: YouTubeContentTemplate, custom_description: Optional[str], target_language: Optional[str] = None) -> str:
        """Generate video description (TICKET-056: Updated to use target language)"""
        if custom_description:
            return custom_description
        
        if target_language is None:
            target_language = self._get_target_language()
        
        # For "short" video type, generate target language description (TICKET-056, TICKET-060)
        if video_metadata.video_type == "short":
            quick_lesson = self._get_template_translation("quick_lesson", target_language)
            expression_label = "Expression" # Always English as per request
            meaning_label = self._get_template_translation("meaning_label", target_language)
            watch_and_learn = self._get_template_translation("watch_and_learn", target_language)
            
            # Get expression metadata from video data first (TICKET-060: Use expression_translation)
            expression_text = video_metadata.expression
            translation_text = video_metadata.expression_translation

            if not expression_text and video_metadata.expressions_included:
                first_expression = video_metadata.expressions_included[0]
                expression_text = expression_text or first_expression.get("expression")
                translation_text = translation_text or first_expression.get("translation")

            if not translation_text:
                translation_text = self._get_translation(video_metadata, target_language)

            # Ensure expression_text is the original expression (English)
            expression_text = expression_text or "Expression"

            # Generate localized tags (TICKET-060)
            tags = self._generate_localized_tags(video_metadata, target_language)

            # Build description in simplified format
            description = f"""🎬 {quick_lesson}
📚 {expression_label}: {expression_text}
📖 {meaning_label}: {translation_text}
💡 {watch_and_learn}
{tags}"""
            
            return description
        
        # For long-form/final video types, generate target language description (TICKET-060)
        episode_display = self._format_episode_display(video_metadata.episode)
        
        # Get translated expression (TICKET-060)
        expression = video_metadata.expression
        translation = video_metadata.expression_translation or self._get_translation(video_metadata, target_language)
        
        # For final videos, list multiple expressions
        expressions_list = expression
        if video_metadata.video_type == "final":
            if video_metadata.expressions_included:
                # Use translated expressions if available
                expr_items = []
                for expr_data in video_metadata.expressions_included:
                    expr_text = expr_data.get("translation") or expr_data.get("expression", "")
                    if expr_text:
                        expr_items.append(f"• {expr_text}")
                if expr_items:
                    expressions_list = "\n".join(expr_items)
                else:
                    expressions_list = f"• {expression}"
            else:
                expressions_list = f"• {expression}"
        
        # Generate target language description for long-form/final videos (TICKET-060)
        if target_language and video_metadata.video_type in ["educational", "final", "long-form"]:
            intro = self._get_template_translation("long_form_description_intro", target_language) if video_metadata.video_type != "final" else self._get_template_translation("final_description_intro", target_language)
            learn_expr = self._get_template_translation("learn_expressions", target_language)
            what_master = self._get_template_translation("what_you_master", target_language)
            real_expr = self._get_template_translation("real_expressions", target_language)
            context_usage = self._get_template_translation("context_usage", target_language)
            pronunciation = self._get_template_translation("pronunciation", target_language)
            similar_expr = self._get_template_translation("similar_expressions", target_language)
            watch_original = self._get_template_translation("watch_original", target_language)
            
            # Generate localized tags
            tags = self._generate_localized_tags(video_metadata, target_language)
            
            if video_metadata.video_type == "final":
                description = f"""🎬 {intro}

📚 {learn_expr}
{expressions_list}

🎯 {what_master}
• {real_expr}
• {context_usage}
• {pronunciation}
• {similar_expr}

📺 {watch_original}

{tags}"""
            else:
                description = f"""🎬 {intro}

📚 Expression: "{expression}"
📖 {self._get_template_translation("meaning_label", target_language)}: {translation}
🎯 {episode_display}
🌍 {video_metadata.language.upper()}

💡 {what_master}:
• {real_expr}
• {context_usage}
• {pronunciation}
• {similar_expr}

📺 {watch_original}

{tags}"""
            
            return description
        
        # Fallback to English template for unknown types or if target language not available
        return template.description_template.format(
            expression=expression,
            translation=translation,
            episode=episode_display,
            language=video_metadata.language.upper(),
            expressions_list=expressions_list
        )
    
    def _generate_tags(self, video_metadata: VideoMetadata, template: YouTubeContentTemplate, additional_tags: Optional[List[str]], target_language: Optional[str] = None) -> List[str]:
        """Generate video tags (TICKET-056: Reduced to 3-5 most relevant tags, TICKET-060: Localized tags)"""
        if target_language is None:
            target_language = self._get_target_language()
        
        # Start with additional tags first (highest priority)
        final_tags = []
        char_count = 0
        max_tags = 5  # Reduced from 15 to 5 (TICKET-056)
        
        # Add additional custom tags first
        if additional_tags:
            for tag in additional_tags:
                if char_count + len(tag) + 1 <= 500 and len(final_tags) < max_tags:
                    final_tags.append(tag)
                    char_count += len(tag) + 1
        
        # For short videos, use localized hashtags from description (TICKET-060)
        if video_metadata.video_type == "short" and target_language:
            # Extract hashtags from localized tag string
            localized_tags_str = self._generate_localized_tags(video_metadata, target_language)
            # Parse hashtags (they're space-separated)
            hashtags = [tag.strip() for tag in localized_tags_str.split() if tag.strip().startswith("#")]
            for tag in hashtags:
                # Remove # for tag list (YouTube API expects tags without #)
                tag_clean = tag.replace("#", "")
                if tag_clean not in final_tags and char_count + len(tag_clean) + 1 <= 500 and len(final_tags) < max_tags:
                    final_tags.append(tag_clean)
                    char_count += len(tag_clean) + 1
        else:
            # For other video types, use default template tags (already limited to 5 in template)
            for tag in template.default_tags:
                if tag not in final_tags and char_count + len(tag) + 1 <= 500 and len(final_tags) < max_tags:
                    final_tags.append(tag)
                    char_count += len(tag) + 1
        
        # For long-form/final videos, we can add a few more if space allows
        if video_metadata.video_type not in ["short"] and len(final_tags) < max_tags:
            # Add expression-specific tags only if we have space
            expression = video_metadata.expression_translation or video_metadata.expression
            if expression:
                expression_words = expression.lower().split()
                for word in expression_words:
                    if len(word) > 3 and len(final_tags) < max_tags:  # Only add meaningful words
                        tag = f"English {word.title()}"
                        if tag not in final_tags and char_count + len(tag) + 1 <= 500:
                            final_tags.append(tag)
                            char_count += len(tag) + 1
                            if len(final_tags) >= max_tags:
                                break
        
        return final_tags
    
    def _format_episode_display(self, episode: str) -> str:
        """Format episode string for display"""
        if "S01E" in episode:
            episode_num = episode.split("S01E")[1].split("_")[0]
            return f"Season 1 Episode {episode_num}"
        return episode
    
    def _get_translation(self, video_metadata: VideoMetadata, target_language: Optional[str] = None) -> str:
        """Get translation for the expression"""
        # Return the translation from metadata if available
        if video_metadata.expression_translation:
            return video_metadata.expression_translation
            
        # Fallback if no translation found
        if target_language is None:
            target_language = self._get_target_language()

        # Use localized "check meaning" string, fallback to English
        return self._get_template_translation("check_meaning", target_language)
    
    def _get_expression_translation(self, video_metadata: VideoMetadata) -> str:
        """Get translation for the expression (alias for clarity)"""
        return self._get_translation(video_metadata)
    
    def _generate_localized_tags(self, video_metadata: VideoMetadata, target_language: str) -> str:
        """Generate hashtags in target language with dynamic show name (TICKET-060)
        
        Args:
            video_metadata: Video metadata object
            target_language: Target language name (e.g., "Korean", "English")
        
        Returns:
            String of localized hashtags
        """
        # Determine show name for hashtag
        # Try extracting from video path first, then episode string, default to "Suits"
        show_name = "Suits" # Default
        
        # Helper to check if extracted name is valid (not generic)
        generic_names = {"video", "unknown", "untitled", "short", "expression", "form"}
        def is_valid_show_name(name: str) -> bool:
            if not name or name == "Unknown Show":
                return False
            # Check if it's a generic/invalid name
            name_lower = name.lower().replace(" ", "").replace("_", "")
            for generic in generic_names:
                if name_lower == generic or name_lower.startswith(generic + "0") or name_lower.endswith(generic):
                    return False
            # Valid if it has at least 2 significant words or >5 chars
            return len(name) > 5 or len(name.split()) >= 2
        
        # Try extracting from video path first (most reliable source)
        if video_metadata.path:
            from pathlib import Path
            video_filename = Path(video_metadata.path).stem
            extracted = extract_show_name(video_filename)
            if is_valid_show_name(extracted):
                show_name = extracted
        
        # Fallback: Try extracting from episode string
        if show_name == "Suits" and video_metadata.episode:
             # Try clean extraction
             extracted = extract_show_name(video_metadata.episode)
             if is_valid_show_name(extracted):
                 show_name = extracted
        
        # Remove spaces for hashtag
        show_hashtag = f"#{show_name.replace(' ', '')}"
        
        # Dynamic #Learn{TargetLanguage}
        # e.g., #LearnKorean, #LearnEnglish
        learn_target_hashtag = f"#Learn{target_language.replace(' ', '')}"

        tag_translations = {
            "Korean": {
                "shorts": "#쇼츠",
                "english_learning": "#영어학습",
                "english_expressions": "#영어표현",
                # "suits" and "learn_english" are now dynamic
            },
            "English": {
                "shorts": "#Shorts",
                "english_learning": "#EnglishLearning",
                "english_expressions": "#EnglishExpressions",
            },
            # ... preserve other languages structure but we use dynamic logic mainly
            "Japanese": {
                "shorts": "#ショート",
                "english_learning": "#英語学習",
                "english_expressions": "#英語表現",
            },
            "Chinese": {
                "shorts": "#短片",
                "english_learning": "#英语学习",
                "english_expressions": "#英语表达",
            },
            "Spanish": {
                "shorts": "#Shorts",
                "english_learning": "#AprenderInglés",
                "english_expressions": "#ExpresionesInglesas",
            },
            "French": {
                "shorts": "#Shorts",
                "english_learning": "#ApprendreAnglais",
                "english_expressions": "#ExpressionsAnglaises",
            }
        }
        
        # Get translations for target language, fallback to English
        translations = tag_translations.get(target_language, tag_translations.get("English", {}))
        
        # Construct hashtags: #Shorts #EnglishLearning #ShowName #EnglishExpressions #LearnTarget
        # Base tags
        shorts_tag = translations.get('shorts', '#Shorts')
        learning_tag = translations.get('english_learning', '#EnglishLearning')
        exp_tag = translations.get('english_expressions', '#EnglishExpressions')
        
        # For short videos, use all tags.
        if video_metadata.video_type == "short":
            return f"{shorts_tag} {learning_tag} {show_hashtag} {exp_tag} {learn_target_hashtag}"
        else:
            # For long-form/final videos, use core tags
            return f"{learning_tag} {show_hashtag} {exp_tag} {learn_target_hashtag}"
    
    def generate_batch_metadata(
        self, 
        videos: List[VideoMetadata],
        privacy_status: str = "private"
    ) -> Dict[str, YouTubeVideoMetadata]:
        """Generate metadata for multiple videos"""
        results = {}
        
        for video in videos:
            try:
                metadata = self.generate_metadata(video, privacy_status=privacy_status)
                results[video.path] = metadata
            except Exception as e:
                logger.error(f"Failed to generate metadata for {video.path}: {e}")
                continue
        
        return results
    
    def update_metadata_template(self, video_type: str, template: YouTubeContentTemplate):
        """Update metadata template for a video type"""
        self.templates[video_type] = template
        logger.info(f"Updated template for video type: {video_type}")
    
    def get_available_templates(self) -> List[str]:
        """Get list of available template types"""
        return list(self.templates.keys())
    
    def preview_metadata(self, video_metadata: VideoMetadata, target_language: Optional[str] = None) -> Dict[str, Any]:
        """Preview generated metadata without creating the full object (TICKET-060: Support target language)"""
        template = self.templates.get(video_metadata.video_type, self.templates["educational"])
        
        if target_language is None:
            target_language = self._get_target_language()
        
        return {
            "title": self._generate_title(video_metadata, template, None, target_language),
            "description_preview": self._generate_description(video_metadata, template, None, target_language)[:200] + "...",
            "tags": self._generate_tags(video_metadata, template, None, target_language),
            "category_id": self.category_mapping.get(video_metadata.video_type, "22"),
            "template_used": video_metadata.video_type
        }
