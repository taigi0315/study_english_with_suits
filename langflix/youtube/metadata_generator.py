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
        """Load translations for template strings by target language (TICKET-056)"""
        return {
            "Korean": {
                "quick_lesson": "수트에서 배우는 빠른 영어 레슨!",
                "expression_label": "표현",
                "meaning_label": "의미",
                "watch_and_learn": "좋아하는 쇼에서 보고 배우세요!",
                "title_template": "영어 표현: {expression} | #Shorts #영어학습"
            },
            "English": {
                "quick_lesson": "Quick English lesson from Suits!",
                "expression_label": "Expression",
                "meaning_label": "Meaning",
                "watch_and_learn": "Watch and learn from your favorite show!",
                "title_template": "English Expression: {expression} | #Shorts #EnglishLearning"
            },
            "Japanese": {
                "quick_lesson": "スーツから学ぶクイック英語レッスン！",
                "expression_label": "表現",
                "meaning_label": "意味",
                "watch_and_learn": "お気に入りの番組から見て学びましょう！",
                "title_template": "英語表現: {expression} | #Shorts #英語学習"
            },
            "Chinese": {
                "quick_lesson": "从《金装律师》快速学习英语！",
                "expression_label": "表达",
                "meaning_label": "含义",
                "watch_and_learn": "从你最喜欢的节目中观看和学习！",
                "title_template": "英语表达: {expression} | #Shorts #英语学习"
            },
            "Spanish": {
                "quick_lesson": "¡Lección rápida de inglés de Suits!",
                "expression_label": "Expresión",
                "meaning_label": "Significado",
                "watch_and_learn": "¡Mira y aprende de tu programa favorito!",
                "title_template": "Expresión en inglés: {expression} | #Shorts #AprenderInglés"
            },
            "French": {
                "quick_lesson": "Leçon d'anglais rapide de Suits !",
                "expression_label": "Expression",
                "meaning_label": "Signification",
                "watch_and_learn": "Regardez et apprenez de votre émission préférée !",
                "title_template": "Expression anglaise: {expression} | #Shorts #ApprendreAnglais"
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
        
        # Generate tags
        tags = self._generate_tags(video_metadata, template, additional_tags)
        
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
        
        # For "short" video type, use target language template (TICKET-056)
        if video_metadata.video_type == "short" and target_language:
            title_template = self._get_template_translation("title_template", target_language)
        else:
            title_template = template.title_template
        
        # Extract episode number for better formatting
        episode_display = self._format_episode_display(video_metadata.episode) if video_metadata.episode else None
        
        # Validate required fields with better fallbacks
        expression = (video_metadata.expression or "").strip()
        if not expression:
            # Try to extract from filename if expression is empty
            logger.debug(f"Expression is empty, trying to extract from filename: {video_metadata.path}")
            expression = self._extract_expression_from_filename(video_metadata.path) or "English Expressions"
            logger.debug(f"Extracted expression: {expression}")
        
        episode = (episode_display or video_metadata.episode or "").strip()
        if not episode:
            # Try to extract from filename if episode is empty
            logger.debug(f"Episode is empty, trying to extract from filename: {video_metadata.path}")
            episode = self._extract_episode_from_filename(video_metadata.path) or "Episode"
            logger.debug(f"Extracted episode: {episode}")
        
        language = (video_metadata.language or "en").upper()
        
        logger.debug(f"Final values: expression='{expression}', episode='{episode}', language='{language}'")
        
        try:
            # Prepare format arguments based on template requirements
            format_args = {}
            
            # Check which placeholders are in the template
            if "{expression}" in title_template:
                format_args["expression"] = expression
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
                        title = fallback_template.format(expression=expression) if "{expression}" in fallback_template else f"{expression} | #Shorts"
                    else:
                        title = f"English Expression: {expression} | #Shorts"
                else:
                    title = f"Learn English: {expression} from {episode}"
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
            # Try to extract expression from filename patterns
            # This is a simple fallback - can be improved based on actual naming patterns
            parts = filename.split('_')
            if len(parts) > 1:
                return parts[-1]  # Usually expression is at the end
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
    
    def _generate_description(self, video_metadata: VideoMetadata, template: YouTubeContentTemplate, custom_description: Optional[str], target_language: Optional[str] = None) -> str:
        """Generate video description (TICKET-056: Updated to use target language)"""
        if custom_description:
            return custom_description
        
        if target_language is None:
            target_language = self._get_target_language()
        
        # For "short" video type, generate target language description (TICKET-056)
        if video_metadata.video_type == "short":
            quick_lesson = self._get_template_translation("quick_lesson", target_language)
            expression_label = self._get_template_translation("expression_label", target_language)
            meaning_label = self._get_template_translation("meaning_label", target_language)
            watch_and_learn = self._get_template_translation("watch_and_learn", target_language)
            
            # Get translation (meaning) - use existing method
            translation = self._get_translation(video_metadata)
            
            # Build description without episode line (TICKET-056)
            description = f"""🎬 {quick_lesson}

📚 {expression_label}: "{video_metadata.expression}"
📖 {meaning_label}: {translation}

💡 {watch_and_learn}

#Shorts #EnglishLearning #Suits #EnglishExpressions #LearnEnglish"""
            
            return description
        
        # For other video types, use existing template
        # Extract episode number for better formatting
        episode_display = self._format_episode_display(video_metadata.episode)
        
        # For final videos, we might want to list multiple expressions
        expressions_list = video_metadata.expression
        if video_metadata.video_type == "final":
            # This would ideally come from the video metadata or be passed as a parameter
            expressions_list = f"• {video_metadata.expression}"
        
        return template.description_template.format(
            expression=video_metadata.expression,
            translation=self._get_translation(video_metadata),
            episode=episode_display,
            language=video_metadata.language.upper(),
            expressions_list=expressions_list
        )
    
    def _generate_tags(self, video_metadata: VideoMetadata, template: YouTubeContentTemplate, additional_tags: Optional[List[str]]) -> List[str]:
        """Generate video tags (TICKET-056: Reduced to 3-5 most relevant tags)"""
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
        
        # Then add default template tags (already limited to 5 in template)
        for tag in template.default_tags:
            if tag not in final_tags and char_count + len(tag) + 1 <= 500 and len(final_tags) < max_tags:
                final_tags.append(tag)
                char_count += len(tag) + 1
        
        # For short videos, we already have 5 tags, so we're done
        # For other video types, we can add a few more if space allows
        if video_metadata.video_type != "short" and len(final_tags) < max_tags:
            # Add expression-specific tags only if we have space
            expression_words = video_metadata.expression.lower().split()
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
    
    def preview_metadata(self, video_metadata: VideoMetadata) -> Dict[str, Any]:
        """Preview generated metadata without creating the full object"""
        template = self.templates.get(video_metadata.video_type, self.templates["educational"])
        
        return {
            "title": self._generate_title(video_metadata, template, None),
            "description_preview": self._generate_description(video_metadata, template, None)[:200] + "...",
            "tags": self._generate_tags(video_metadata, template, None),
            "category_id": self.category_mapping.get(video_metadata.video_type, "22"),
            "template_used": video_metadata.video_type
        }
