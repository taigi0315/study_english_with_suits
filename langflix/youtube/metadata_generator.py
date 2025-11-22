"""
YouTube Metadata Generator
Automatically generates titles, descriptions, and tags for YouTube videos
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from langflix.youtube.uploader import YouTubeVideoMetadata
from langflix.youtube.video_manager import VideoMetadata
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
        """Load translations for template strings by target language (TICKET-056, TICKET-060)"""
        return {
            "Korean": {
                "quick_lesson": "수트에서 배우는 빠른 영어 레슨!",
                "expression_label": "표현",
                "meaning_label": "의미",
                "watch_and_learn": "좋아하는 쇼에서 보고 배우세요!",
                "title_template": "영어 표현 {expression} from {episode}",
                # Long-form/Final video templates (TICKET-060)
                "long_form_title": "수트에서 배우는 영어 표현 - {episode}",
                "long_form_description_intro": "수트 드라마에서 배우는 실용적인 영어 표현들을 모았습니다.",
                "final_title": "완전한 영어 레슨: {episode} | 수트에서 배우는 5개 이상의 표현",
                "final_description_intro": "수트 {episode}의 완전한 영어 레슨!",
                "learn_expressions": "이 포괄적인 레슨에서 여러 영어 표현을 배우게 됩니다:",
                "what_you_master": "마스터할 내용:",
                "real_expressions": "원어민이 사용하는 실제 영어 표현",
                "context_usage": "맥락과 적절한 사용법",
                "pronunciation": "발음과 억양",
                "similar_expressions": "유사한 표현과 대안",
                "watch_original": "원본 장면을 보고 자연스럽게 배우세요!"
            },
            "English": {
                "quick_lesson": "Quick English lesson from Suits!",
                "expression_label": "Expression",
                "meaning_label": "Meaning",
                "watch_and_learn": "Watch and learn from your favorite show!",
                "title_template": "English Expression {expression} from {episode}",
                # Long-form/Final video templates (TICKET-060)
                "long_form_title": "Learn English Expressions from Suits - {episode}",
                "long_form_description_intro": "Learn practical English expressions from the hit TV show Suits!",
                "final_title": "Complete English Lesson: {episode} | Learn 5+ Expressions from Suits",
                "final_description_intro": "Complete English lesson from Suits {episode}!",
                "learn_expressions": "In this comprehensive lesson, you'll learn multiple English expressions:",
                "what_you_master": "What you'll master:",
                "real_expressions": "Real English expressions used by native speakers",
                "context_usage": "Context and proper usage",
                "pronunciation": "Pronunciation and intonation",
                "similar_expressions": "Similar expressions and alternatives",
                "watch_original": "Watch the original scenes and learn naturally!"
            },
            "Japanese": {
                "quick_lesson": "スーツから学ぶクイック英語レッスン！",
                "expression_label": "表現",
                "meaning_label": "意味",
                "watch_and_learn": "お気に入りの番組から見て学びましょう！",
                "title_template": "英語表現 {expression} from {episode}",
                # Long-form/Final video templates (TICKET-060)
                "long_form_title": "スーツから学ぶ英語表現 - {episode}",
                "long_form_description_intro": "人気ドラマ「スーツ」から実用的な英語表現を学びましょう！",
                "final_title": "完全な英語レッスン: {episode} | スーツから5つ以上の表現を学ぶ",
                "final_description_intro": "スーツ {episode}の完全な英語レッスン！",
                "learn_expressions": "この包括的なレッスンでは、複数の英語表現を学びます:",
                "what_you_master": "マスターする内容:",
                "real_expressions": "ネイティブスピーカーが使用する実際の英語表現",
                "context_usage": "文脈と適切な使用方法",
                "pronunciation": "発音とイントネーション",
                "similar_expressions": "類似した表現と代替案",
                "watch_original": "オリジナルのシーンを見て自然に学びましょう！"
            },
            "Chinese": {
                "quick_lesson": "从《金装律师》快速学习英语！",
                "expression_label": "表达",
                "meaning_label": "含义",
                "watch_and_learn": "从你最喜欢的节目中观看和学习！",
                "title_template": "英语表达 {expression} from {episode}",
                # Long-form/Final video templates (TICKET-060)
                "long_form_title": "从《金装律师》学习英语表达 - {episode}",
                "long_form_description_intro": "从热门电视剧《金装律师》中学习实用的英语表达！",
                "final_title": "完整英语课程: {episode} | 从《金装律师》学习5个以上表达",
                "final_description_intro": "《金装律师》{episode}的完整英语课程！",
                "learn_expressions": "在这门综合课程中，您将学习多个英语表达:",
                "what_you_master": "您将掌握:",
                "real_expressions": "母语者使用的真实英语表达",
                "context_usage": "语境和正确用法",
                "pronunciation": "发音和语调",
                "similar_expressions": "类似表达和替代方案",
                "watch_original": "观看原始场景并自然学习！"
            },
            "Spanish": {
                "quick_lesson": "¡Lección rápida de inglés de Suits!",
                "expression_label": "Expresión",
                "meaning_label": "Significado",
                "watch_and_learn": "¡Mira y aprende de tu programa favorito!",
                "title_template": "Expresión en inglés {expression} from {episode}",
                # Long-form/Final video templates (TICKET-060)
                "long_form_title": "Aprende expresiones en inglés de Suits - {episode}",
                "long_form_description_intro": "¡Aprende expresiones prácticas en inglés de la exitosa serie de TV Suits!",
                "final_title": "Lección completa de inglés: {episode} | Aprende 5+ expresiones de Suits",
                "final_description_intro": "¡Lección completa de inglés de Suits {episode}!",
                "learn_expressions": "En esta lección completa, aprenderás múltiples expresiones en inglés:",
                "what_you_master": "Lo que dominarás:",
                "real_expressions": "Expresiones reales en inglés usadas por hablantes nativos",
                "context_usage": "Contexto y uso apropiado",
                "pronunciation": "Pronunciación y entonación",
                "similar_expressions": "Expresiones similares y alternativas",
                "watch_original": "¡Mira las escenas originales y aprende naturalmente!"
            },
            "French": {
                "quick_lesson": "Leçon d'anglais rapide de Suits !",
                "expression_label": "Expression",
                "meaning_label": "Signification",
                "watch_and_learn": "Regardez et apprenez de votre émission préférée !",
                "title_template": "Expression anglaise {expression} from {episode}",
                # Long-form/Final video templates (TICKET-060)
                "long_form_title": "Apprenez des expressions anglaises de Suits - {episode}",
                "long_form_description_intro": "Apprenez des expressions anglaises pratiques de la série à succès Suits !",
                "final_title": "Leçon d'anglais complète : {episode} | Apprenez 5+ expressions de Suits",
                "final_description_intro": "Leçon d'anglais complète de Suits {episode} !",
                "learn_expressions": "Dans cette leçon complète, vous apprendrez plusieurs expressions anglaises :",
                "what_you_master": "Ce que vous maîtriserez :",
                "real_expressions": "Expressions anglaises réelles utilisées par les locuteurs natifs",
                "context_usage": "Contexte et utilisation appropriée",
                "pronunciation": "Prononciation et intonation",
                "similar_expressions": "Expressions similaires et alternatives",
                "watch_original": "Regardez les scènes originales et apprenez naturellement !"
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
                title_template="Learn English: {expression} from Suits {episode} | English Expressions",
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
        
        # FIX (TICKET-071): Use original English expression and translation for title format
        # Get original English expression
        expression = (video_metadata.expression or "").strip()
        if not expression and video_metadata.expressions_included:
            first_expression = video_metadata.expressions_included[0]
            expression = first_expression.get("expression", "").strip()
        
        if not expression:
            # Try to extract from filename if expression is empty
            logger.debug(f"Expression is empty, trying to extract from filename: {video_metadata.path}")
            extracted = self._extract_expression_from_filename(video_metadata.path)
            if extracted:
                expression = extracted
                logger.debug(f"Extracted expression: {expression}")
            else:
                # For batch videos or when extraction fails, use a generic expression
                expression = "English Expressions"
                logger.debug(f"Using default expression: {expression}")
        
        # Get translation
        translation = video_metadata.expression_translation or ""
        if not translation and video_metadata.expressions_included:
            first_expression = video_metadata.expressions_included[0]
            translation = first_expression.get("translation", "")
        
        if not translation:
            translation = self._get_translation(video_metadata) or ""
        
        # Format episode as "Suits.S01E06" format (uppercase)
        episode_raw = video_metadata.episode or ""
        if not episode_raw:
            # Try to extract from filename if episode is empty
            logger.debug(f"Episode is empty, trying to extract from filename: {video_metadata.path}")
            episode_raw = self._extract_episode_from_filename(video_metadata.path) or ""
        
        # Format episode: ensure "Suits." prefix and uppercase (S01E06)
        episode = self._format_episode_for_title(episode_raw)
        # Ensure uppercase for episode code (S01E06, not s01e06)
        import re
        episode = re.sub(r'([Ss])(\d+)([Ee])(\d+)', r'S\2E\4', episode)
        logger.debug(f"Formatted episode: '{episode}'")
        
        logger.debug(f"Final values: expression='{expression}', translation='{translation}', episode='{episode}'")
        
        try:
            # FIX (TICKET-071): New title format: {expression} - {translation} from {series}.{episode}
            if expression and translation:
                title = f"{expression} - {translation} from {episode}"
            elif expression:
                # Fallback if translation is missing
                title = f"{expression} from {episode}"
            else:
                # Final fallback
                title = f"English Expression from {episode}"
            
            # Ensure title is not empty and strip whitespace
            title = title.strip()
            
            # Final validation - ensure title is not empty
            if not title or title.strip() == "":
                title = f"Learn English from {episode}"
                logger.error(f"All title generation methods failed for {video_metadata.path}, using minimal fallback")
            
            logger.info(f"✅ Final generated title: '{title}'")
            return title
        except (KeyError, AttributeError, ValueError) as e:
            logger.error(f"❌ Error generating title from template: {e}")
            logger.error(f"  Template: {title_template}")
            logger.error(f"  Expression: {expression}, Episode: {episode}, Language: {language}")
            logger.error(f"  Video path: {video_metadata.path}")
            # Fallback title based on video type
            if video_metadata.video_type == "short":
                if target_language:
                    fallback_template = self._get_template_translation("title_template", target_language)
                    fallback = fallback_template.format(expression=expression) if expression and "{expression}" in fallback_template else "English Learning Shorts"
                else:
                    fallback = f"English Expression: {expression} | #Shorts" if expression else "English Learning Shorts"
            else:
                fallback = f"Learn English: {expression} from {episode}"
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
        """Format episode as 'Suits.S01E02' format for title (uppercase)"""
        if not episode_raw:
            return "Suits"
        
        import re
        # Extract S01E02 pattern and ensure uppercase
        episode_match = re.search(r'[Ss](\d+)[Ee](\d+)', episode_raw)
        if episode_match:
            # Ensure uppercase: S01E02
            episode_code = f"S{episode_match.group(1)}E{episode_match.group(2)}".upper()
            # Check if "Suits" is already in the episode string
            if "Suits" in episode_raw or "suits" in episode_raw.lower():
                # If "Suits" is present, extract just "Suits.S01E02" part
                # Remove quality/resolution info (e.g., .720p.HDTV.x264)
                parts = episode_raw.split('.')
                suits_part = None
                episode_part = None
                for part in parts:
                    if "suits" in part.lower():
                        suits_part = "Suits"
                    if re.match(r'[Ss]\d+[Ee]\d+', part):
                        episode_part = part
                        break
                
                if suits_part and episode_part:
                    return f"{suits_part}.{episode_part}"
                elif episode_part:
                    return f"Suits.{episode_part}"
            else:
                # If "Suits" is not present, add it
                return f"Suits.{episode_code}"
        
        # Fallback: if no episode pattern found, try to extract from full string
        if "Suits" in episode_raw or "suits" in episode_raw.lower():
            # Extract "Suits.S01E02" part, removing quality info
            parts = episode_raw.split('.')
            result_parts = []
            for part in parts:
                if "suits" in part.lower() or re.match(r'[Ss]\d+[Ee]\d+', part):
                    if "suits" in part.lower():
                        result_parts.append("Suits")
                    else:
                        result_parts.append(part)
                    if len(result_parts) >= 2:
                        break
            if result_parts:
                return '.'.join(result_parts)
        
        # Final fallback
        return "Suits" if not episode_raw else episode_raw
    
    def _generate_description(self, video_metadata: VideoMetadata, template: YouTubeContentTemplate, custom_description: Optional[str], target_language: Optional[str] = None) -> str:
        """Generate video description (TICKET-056: Updated to use target language)"""
        if custom_description:
            return custom_description
        
        if target_language is None:
            target_language = self._get_target_language()
        
        # For "short" video type, generate target language description (TICKET-056, TICKET-060)
        if video_metadata.video_type == "short":
            quick_lesson = self._get_template_translation("quick_lesson", target_language)
            expression_label = self._get_template_translation("expression_label", target_language)
            meaning_label = self._get_template_translation("meaning_label", target_language)
            watch_and_learn = self._get_template_translation("watch_and_learn", target_language)
            
            # FIX (TICKET-071): Expression field should show original English, Meaning field shows translation
            # Get original English expression for Expression field
            expression_text = video_metadata.expression or ""
            if not expression_text and video_metadata.expressions_included:
                first_expression = video_metadata.expressions_included[0]
                expression_text = first_expression.get("expression", "")

            # Get translation for Meaning field
            translation_text = video_metadata.expression_translation
            if not translation_text and video_metadata.expressions_included:
                first_expression = video_metadata.expressions_included[0]
                translation_text = first_expression.get("translation")

            if not translation_text:
                translation_text = self._get_translation(video_metadata)

            # Fallback if expression is still empty
            if not expression_text:
                expression_text = video_metadata.expression or "Expression"

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
        expression = video_metadata.expression_translation or video_metadata.expression
        translation = video_metadata.expression_translation or self._get_translation(video_metadata)
        
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

📚 {self._get_template_translation("expression_label", target_language)}: "{expression}"
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
    
    def _get_translation(self, video_metadata: VideoMetadata) -> str:
        """Get translation for the expression"""
        # This would ideally come from the video metadata or expression analysis
        # For now, we'll use a placeholder
        # Note: This method name conflicts with _get_translation(key, target_language) 
        # but they serve different purposes - this one gets expression translation,
        # the other gets template string translation
        return "Learn the meaning and usage in the video"
    
    def _get_expression_translation(self, video_metadata: VideoMetadata) -> str:
        """Get translation for the expression (alias for clarity)"""
        return self._get_translation(video_metadata)
    
    def _generate_localized_tags(self, video_metadata: VideoMetadata, target_language: str) -> str:
        """Generate hashtags in target language (TICKET-060)
        
        Args:
            video_metadata: Video metadata object
            target_language: Target language name (e.g., "Korean", "English")
        
        Returns:
            String of localized hashtags
        """
        tag_translations = {
            "Korean": {
                "shorts": "#쇼츠",
                "english_learning": "#영어학습",
                "suits": "#수트",
                "english_expressions": "#영어표현",
                "learn_english": "#영어공부"
            },
            "English": {
                "shorts": "#Shorts",
                "english_learning": "#EnglishLearning",
                "suits": "#Suits",
                "english_expressions": "#EnglishExpressions",
                "learn_english": "#LearnEnglish"
            },
            "Japanese": {
                "shorts": "#ショート",
                "english_learning": "#英語学習",
                "suits": "#スーツ",
                "english_expressions": "#英語表現",
                "learn_english": "#英語勉強"
            },
            "Chinese": {
                "shorts": "#短片",
                "english_learning": "#英语学习",
                "suits": "#金装律师",
                "english_expressions": "#英语表达",
                "learn_english": "#学英语"
            },
            "Spanish": {
                "shorts": "#Shorts",
                "english_learning": "#AprenderInglés",
                "suits": "#Suits",
                "english_expressions": "#ExpresionesInglesas",
                "learn_english": "#AprendeInglés"
            },
            "French": {
                "shorts": "#Shorts",
                "english_learning": "#ApprendreAnglais",
                "suits": "#Suits",
                "english_expressions": "#ExpressionsAnglaises",
                "learn_english": "#ApprendsAnglais"
            }
        }
        
        # Get translations for target language, fallback to Korean if not found
        translations = tag_translations.get(target_language, tag_translations.get("Korean", {}))
        
        # For short videos, use all tags. For other types, use a subset
        if video_metadata.video_type == "short":
            return f"{translations.get('shorts', '#Shorts')} {translations.get('english_learning', '#EnglishLearning')} {translations.get('suits', '#Suits')} {translations.get('english_expressions', '#EnglishExpressions')} {translations.get('learn_english', '#LearnEnglish')}"
        else:
            # For long-form/final videos, use core tags
            return f"{translations.get('english_learning', '#EnglishLearning')} {translations.get('suits', '#Suits')} {translations.get('english_expressions', '#EnglishExpressions')} {translations.get('learn_english', '#LearnEnglish')}"
    
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

