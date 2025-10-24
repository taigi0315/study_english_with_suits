"""
YouTube Metadata Generator
Automatically generates titles, descriptions, and tags for YouTube videos
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from langflix.youtube.uploader import YouTubeVideoMetadata
from langflix.youtube.video_manager import VideoMetadata

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
                title_template="English Expression: {expression} | #Shorts #EnglishLearning",
                description_template="""🎬 Quick English lesson from Suits!

📚 Expression: "{expression}"
📖 Meaning: {translation}
🎯 Episode: {episode}

💡 Use this expression in your daily conversations!

#Shorts #EnglishLearning #Suits #EnglishExpressions #LearnEnglish #EnglishWithTV #EnglishConversation #EnglishGrammar #EnglishVocabulary #EnglishSpeaking #EnglishPractice #SuitsTVShow #EnglishLessons #EnglishTips #EnglishStudy #EnglishFluency""",
                default_tags=[
                    "Shorts", "English Learning", "Suits", "English Expressions",
                    "Learn English", "English with TV", "English Conversation",
                    "English Grammar", "English Vocabulary", "English Speaking"
                ],
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
        privacy_status: str = "private"
    ) -> YouTubeVideoMetadata:
        """Generate YouTube metadata for a video"""
        
        template = self.templates.get(video_metadata.video_type, self.templates["educational"])
        
        # Generate title
        title = self._generate_title(video_metadata, template, custom_title)
        
        # Generate description
        description = self._generate_description(video_metadata, template, custom_description)
        
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
    
    def _generate_title(self, video_metadata: VideoMetadata, template: YouTubeContentTemplate, custom_title: Optional[str]) -> str:
        """Generate video title"""
        if custom_title:
            return custom_title
        
        # Extract episode number for better formatting
        episode_display = self._format_episode_display(video_metadata.episode)
        
        return template.title_template.format(
            expression=video_metadata.expression,
            episode=episode_display,
            language=video_metadata.language.upper()
        )
    
    def _generate_description(self, video_metadata: VideoMetadata, template: YouTubeContentTemplate, custom_description: Optional[str]) -> str:
        """Generate video description"""
        if custom_description:
            return custom_description
        
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
        """Generate video tags"""
        # Start with additional tags first (highest priority)
        final_tags = []
        char_count = 0
        
        # Add additional custom tags first
        if additional_tags:
            for tag in additional_tags:
                if char_count + len(tag) + 1 <= 500 and len(final_tags) < 15:
                    final_tags.append(tag)
                    char_count += len(tag) + 1
        
        # Then add default template tags
        for tag in template.default_tags:
            if tag not in final_tags and char_count + len(tag) + 1 <= 500 and len(final_tags) < 15:
                final_tags.append(tag)
                char_count += len(tag) + 1
        
        # Add expression-specific tags
        expression_words = video_metadata.expression.lower().split()
        for word in expression_words:
            if len(word) > 3:  # Only add meaningful words
                tag = f"English {word.title()}"
                if tag not in final_tags and char_count + len(tag) + 1 <= 500 and len(final_tags) < 15:
                    final_tags.append(tag)
                    char_count += len(tag) + 1
        
        # Add episode-specific tags
        if "S01E" in video_metadata.episode:
            episode_num = video_metadata.episode.split("S01E")[1].split("_")[0]
            tag = f"Suits Season 1 Episode {episode_num}"
            if tag not in final_tags and char_count + len(tag) + 1 <= 500 and len(final_tags) < 15:
                final_tags.append(tag)
                char_count += len(tag) + 1
        
        # Add language-specific tags
        if video_metadata.language == "ko":
            for tag in ["Korean English Learning", "한국어 영어학습"]:
                if tag not in final_tags and char_count + len(tag) + 1 <= 500 and len(final_tags) < 15:
                    final_tags.append(tag)
                    char_count += len(tag) + 1
        elif video_metadata.language == "ja":
            for tag in ["Japanese English Learning", "日本語英語学習"]:
                if tag not in final_tags and char_count + len(tag) + 1 <= 500 and len(final_tags) < 15:
                    final_tags.append(tag)
                    char_count += len(tag) + 1
        
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
        return "Learn the meaning and usage in the video"
    
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
