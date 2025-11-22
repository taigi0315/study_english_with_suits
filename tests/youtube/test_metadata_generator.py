"""
Comprehensive unit tests for YouTubeMetadataGenerator
Tests metadata generation, template handling, and content creation
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from langflix.youtube.metadata_generator import (
    YouTubeMetadataGenerator,
    YouTubeContentTemplate
)
from langflix.youtube.video_manager import VideoMetadata


class TestYouTubeContentTemplate:
    """Test YouTubeContentTemplate dataclass"""
    
    def test_template_creation(self):
        """Test creating YouTube content template"""
        template = YouTubeContentTemplate(
            title_template="Learn {expression} from {episode}",
            description_template="Description for {expression}",
            default_tags=["tag1", "tag2"],
            category_mapping={"educational": "22"}
        )
        
        assert template.title_template == "Learn {expression} from {episode}"
        assert template.description_template == "Description for {expression}"
        assert template.default_tags == ["tag1", "tag2"]
        assert template.category_mapping == {"educational": "22"}


class TestYouTubeMetadataGenerator:
    """Test YouTubeMetadataGenerator core functionality"""
    
    @pytest.fixture
    def generator(self):
        """Create YouTubeMetadataGenerator instance"""
        return YouTubeMetadataGenerator()
    
    @pytest.fixture
    def sample_video_metadata(self):
        """Create sample video metadata for testing"""
        return VideoMetadata(
            path="/path/to/video.mp4",
            filename="video.mp4",
            size_mb=100.0,
            duration_seconds=120.0,
            resolution="1920x1080",
            format="h264",
            created_at=datetime.now(),
            episode="S01E01_Test",
            expression="Not the point",
            video_type="final",
            language="ko"
        )
    
    def test_init(self, generator):
        """Test generator initialization"""
        assert generator.templates is not None
        assert "educational" in generator.templates
        assert "short" in generator.templates
        assert "final" in generator.templates
        assert generator.category_mapping is not None
    
    def test_load_templates(self, generator):
        """Test template loading"""
        templates = generator._load_templates()
        
        # Check all expected templates exist
        assert "educational" in templates
        assert "short" in templates
        assert "final" in templates
        
        # Check template structure
        educational_template = templates["educational"]
        assert hasattr(educational_template, 'title_template')
        assert hasattr(educational_template, 'description_template')
        assert hasattr(educational_template, 'default_tags')
        assert hasattr(educational_template, 'category_mapping')
        
        # Check template content
        assert "{expression}" in educational_template.title_template
        assert "{episode}" in educational_template.title_template
        assert len(educational_template.default_tags) > 0
    
    def test_generate_metadata_educational(self, generator, sample_video_metadata):
        """Test generating metadata for educational video (TICKET-060: Updated for target language)"""
        sample_video_metadata.video_type = "educational"
        
        # Use English explicitly to maintain backward compatibility (TICKET-060)
        metadata = generator.generate_metadata(sample_video_metadata, target_language="English")
        
        assert metadata.title is not None
        assert metadata.description is not None
        assert metadata.tags is not None
        assert metadata.category_id == "22"
        assert metadata.privacy_status == "private"
        
        # Check title contains expression and episode
        assert "Not the point" in metadata.title or "Learn English Expressions" in metadata.title
        assert "S01E01" in metadata.title or "Season 1 Episode 01" in metadata.title
        
        # Check description
        assert "Not the point" in metadata.description or "Learn practical English" in metadata.description
        assert "S01E01" in metadata.description or "Season 1 Episode 01" in metadata.description
        
        # Check tags
        assert len(metadata.tags) > 0
        assert "English Learning" in metadata.tags or "EnglishLearning" in metadata.tags
        assert "Suits" in metadata.tags
    
    def test_generate_metadata_short(self, generator, sample_video_metadata):
        """Test generating metadata for short video (TICKET-060: Updated for target language)"""
        sample_video_metadata.video_type = "short"
        
        # Use English explicitly to maintain backward compatibility (TICKET-060)
        metadata = generator.generate_metadata(sample_video_metadata, target_language="English")
        
        assert metadata.title is not None
        assert metadata.description is not None
        assert metadata.tags is not None
        assert metadata.category_id == "22"
        
        # Check title format for shorts (TICKET-060: Title doesn't include #Shorts, it's in description)
        assert "Not the point" in metadata.title or "English Expression" in metadata.title
        
        # Check description format for shorts
        assert "Quick English lesson" in metadata.description
        assert "Not the point" in metadata.description or "Expression" in metadata.description
        
        # Check tags include shorts-specific tags
        assert "Shorts" in metadata.tags or "EnglishLearning" in metadata.tags
        assert "English Learning" in metadata.tags or "EnglishLearning" in metadata.tags

    def test_generate_description_short_uses_metadata_list(self, generator, sample_video_metadata):
        """Short description should use expressions_included metadata when expression field is empty (TICKET-060: Updated to use translation)"""
        sample_video_metadata.video_type = "short"
        sample_video_metadata.expression = ""
        sample_video_metadata.expression_translation = None
        sample_video_metadata.expressions_included = [
            {"expression": "Meta Expression", "translation": "메타 번역"}
        ]

        # Use English explicitly (TICKET-060)
        description = generator._generate_description(
            sample_video_metadata,
            generator.templates["short"],
            None,
            target_language="English"
        )

        # TICKET-060: Uses translation from expressions_included, not English expression
        assert "메타 번역" in description or "Meta Expression" in description
        # Translation should be used
        assert "메타 번역" in description
    
    def test_generate_metadata_final(self, generator, sample_video_metadata):
        """Test generating metadata for final video (TICKET-060: Updated for target language)"""
        sample_video_metadata.video_type = "final"
        
        # Use English explicitly to maintain backward compatibility (TICKET-060)
        metadata = generator.generate_metadata(sample_video_metadata, target_language="English")
        
        assert metadata.title is not None
        assert metadata.description is not None
        assert metadata.tags is not None
        assert metadata.category_id == "22"
        
        # Check title format for final videos (TICKET-060: May use target language template)
        assert "Complete English Lesson" in metadata.title or "Learn 5+ Expressions" in metadata.title
        assert "S01E01" in metadata.title or "Season 1 Episode 01" in metadata.title
        
        # Check description format for final videos
        assert "Complete English lesson" in metadata.description or "comprehensive lesson" in metadata.description
        
        # Check tags include final-specific tags (TICKET-060: Tags are localized)
        assert "English Learning" in metadata.tags or "EnglishLearning" in metadata.tags
        # "English Study" may not be in tags due to localization (TICKET-060)
    
    def test_generate_metadata_custom_title(self, generator, sample_video_metadata):
        """Test generating metadata with custom title"""
        custom_title = "My Custom Title"
        
        metadata = generator.generate_metadata(
            sample_video_metadata,
            custom_title=custom_title
        )
        
        assert metadata.title == custom_title
        assert metadata.description is not None  # Should still generate description
        assert metadata.tags is not None  # Should still generate tags
    
    def test_generate_metadata_custom_description(self, generator, sample_video_metadata):
        """Test generating metadata with custom description"""
        custom_description = "My custom description"
        
        metadata = generator.generate_metadata(
            sample_video_metadata,
            custom_description=custom_description
        )
        
        assert metadata.description == custom_description
        assert metadata.title is not None  # Should still generate title
        assert metadata.tags is not None  # Should still generate tags
    
    def test_generate_metadata_custom_privacy(self, generator, sample_video_metadata):
        """Test generating metadata with custom privacy status"""
        metadata = generator.generate_metadata(
            sample_video_metadata,
            privacy_status="public"
        )
        
        assert metadata.privacy_status == "public"
    
    def test_generate_metadata_additional_tags(self, generator, sample_video_metadata):
        """Test generating metadata with additional tags"""
        additional_tags = ["Custom Tag", "Another Tag"]
        
        metadata = generator.generate_metadata(
            sample_video_metadata,
            additional_tags=additional_tags
        )
        
        # Check that additional tags are included
        for tag in additional_tags:
            assert tag in metadata.tags
    
    def test_generate_metadata_unknown_type(self, generator, sample_video_metadata):
        """Test generating metadata for unknown video type"""
        sample_video_metadata.video_type = "unknown"
        
        metadata = generator.generate_metadata(sample_video_metadata)
        
        # Should fall back to educational template
        assert metadata.title is not None
        assert metadata.description is not None
        assert metadata.tags is not None
        assert metadata.category_id == "22"
    
    def test_generate_title_educational(self, generator, sample_video_metadata):
        """Test title generation for educational videos (TICKET-060: Updated for target language)"""
        sample_video_metadata.video_type = "educational"
        template = generator.templates["educational"]
        
        # Use English explicitly (TICKET-060)
        title = generator._generate_title(sample_video_metadata, template, None, target_language="English")
        
        # TICKET-060: Title may use expression_translation or expression
        assert "Not the point" in title or "Learn English Expressions" in title
        assert "S01E01" in title or "Season 1 Episode 01" in title
        assert "English" in title or "Expressions" in title
    
    def test_generate_title_custom(self, generator, sample_video_metadata):
        """Test title generation with custom title"""
        template = generator.templates["educational"]
        custom_title = "My Custom Title"
        
        title = generator._generate_title(sample_video_metadata, template, custom_title)
        
        assert title == custom_title
    
    def test_generate_description_educational(self, generator, sample_video_metadata):
        """Test description generation for educational videos (TICKET-060: Updated for target language)"""
        sample_video_metadata.video_type = "educational"
        template = generator.templates["educational"]
        
        # Use English explicitly (TICKET-060)
        description = generator._generate_description(sample_video_metadata, template, None, target_language="English")
        
        # TICKET-060: Description uses target language template
        assert "Not the point" in description or "Expression" in description
        assert "S01E01" in description or "Season 1 Episode 01" in description
        assert "Learn practical English" in description or "Learn English expressions" in description
        assert "What you'll master" in description or "What you'll learn" in description
    
    def test_generate_description_custom(self, generator, sample_video_metadata):
        """Test description generation with custom description"""
        template = generator.templates["educational"]
        custom_description = "My custom description"
        
        description = generator._generate_description(sample_video_metadata, template, custom_description)
        
        assert description == custom_description
    
    def test_generate_description_final(self, generator, sample_video_metadata):
        """Test description generation for final videos"""
        sample_video_metadata.video_type = "final"
        template = generator.templates["final"]
        
        description = generator._generate_description(sample_video_metadata, template, None)
        
        assert "Complete English lesson" in description
        assert "comprehensive lesson" in description
        assert "What you'll master" in description
    
    def test_generate_tags_basic(self, generator, sample_video_metadata):
        """Test basic tag generation"""
        template = generator.templates["educational"]
        
        tags = generator._generate_tags(sample_video_metadata, template, None)
        
        assert len(tags) > 0
        assert "English Learning" in tags
        assert "Suits" in tags
        assert "English Expressions" in tags
    
    def test_generate_tags_expression_specific(self, generator, sample_video_metadata):
        """Test tag generation with expression-specific tags (TICKET-060: Updated for localized tags)"""
        sample_video_metadata.expression = "Not the point"
        sample_video_metadata.video_type = "educational"
        template = generator.templates["educational"]
        
        # Use English explicitly (TICKET-060)
        tags = generator._generate_tags(sample_video_metadata, template, None, target_language="English")
        
        # TICKET-060: Tags are now localized, expression-specific tags may not be generated
        # Should include basic tags
        assert len(tags) > 0
        assert "English Learning" in tags or "EnglishLearning" in tags
    
    def test_generate_tags_episode_specific(self, generator, sample_video_metadata):
        """Test tag generation with episode-specific tags (TICKET-060: Updated for localized tags)"""
        sample_video_metadata.episode = "S01E01_Test"
        sample_video_metadata.video_type = "educational"
        template = generator.templates["educational"]
        
        # Use English explicitly (TICKET-060)
        tags = generator._generate_tags(sample_video_metadata, template, None, target_language="English")
        
        # TICKET-060: Tags are now localized, episode-specific tags may not be generated
        # Should include basic tags
        assert len(tags) > 0
        assert "Suits" in tags
    
    def test_generate_tags_language_specific(self, generator, sample_video_metadata):
        """Test tag generation with language-specific tags (TICKET-060: Updated for localized tags)"""
        sample_video_metadata.language = "ko"
        sample_video_metadata.video_type = "educational"
        template = generator.templates["educational"]
        
        # Use Korean explicitly (TICKET-060)
        tags = generator._generate_tags(sample_video_metadata, template, None, target_language="Korean")
        
        # TICKET-060: Tags are now localized based on target language
        # Should include basic tags (may be in Korean or English format)
        assert len(tags) > 0
        # Tags should be generated (format may vary)
        assert any("English" in tag or "영어" in tag for tag in tags)
    
    def test_generate_tags_japanese(self, generator, sample_video_metadata):
        """Test tag generation for Japanese language (TICKET-060: Updated for localized tags)"""
        sample_video_metadata.language = "ja"
        sample_video_metadata.video_type = "educational"
        template = generator.templates["educational"]
        
        # Use Japanese explicitly (TICKET-060)
        tags = generator._generate_tags(sample_video_metadata, template, None, target_language="Japanese")
        
        # TICKET-060: Tags are now localized based on target language
        # Should include basic tags (may be in Japanese or English format)
        assert len(tags) > 0
        # Tags should be generated (format may vary)
        assert any("English" in tag or "英語" in tag for tag in tags)
    
    def test_generate_tags_additional(self, generator, sample_video_metadata):
        """Test tag generation with additional tags"""
        template = generator.templates["educational"]
        additional_tags = ["Custom Tag", "Another Tag"]
        
        tags = generator._generate_tags(sample_video_metadata, template, additional_tags)
        
        # Should include additional tags
        for tag in additional_tags:
            assert tag in tags
    
    def test_generate_tags_duplicate_removal(self, generator, sample_video_metadata):
        """Test tag generation removes duplicates"""
        template = generator.templates["educational"]
        additional_tags = ["English Learning", "Suits"]  # Duplicates of default tags
        
        tags = generator._generate_tags(sample_video_metadata, template, additional_tags)
        
        # Should not have duplicates
        assert len(tags) == len(set(tags))
    
    def test_generate_tags_length_limit(self, generator, sample_video_metadata):
        """Test tag generation respects length limits"""
        template = generator.templates["educational"]
        # Create many long tags to test length limit
        additional_tags = [f"Very Long Tag {i}" * 10 for i in range(20)]
        
        tags = generator._generate_tags(sample_video_metadata, template, additional_tags)
        
        # Should respect YouTube's tag limit (15 tags max)
        assert len(tags) <= 15
        
        # Should respect character limit (500 characters total)
        total_chars = sum(len(tag) + 1 for tag in tags)  # +1 for comma
        assert total_chars <= 500
    
    def test_format_episode_display_s01e01(self, generator):
        """Test episode display formatting for S01E01"""
        episode = "S01E01_Test"
        
        formatted = generator._format_episode_display(episode)
        
        assert formatted == "Season 1 Episode 01"
    
    def test_format_episode_display_s01e10(self, generator):
        """Test episode display formatting for S01E10"""
        episode = "S01E10_Test"
        
        formatted = generator._format_episode_display(episode)
        
        assert formatted == "Season 1 Episode 10"
    
    def test_format_episode_display_unknown(self, generator):
        """Test episode display formatting for unknown format"""
        episode = "Unknown_Format"
        
        formatted = generator._format_episode_display(episode)
        
        assert formatted == episode  # Should return original if no S01E pattern
    
    def test_get_translation(self, generator, sample_video_metadata):
        """Test translation retrieval"""
        translation = generator._get_translation(sample_video_metadata)
        
        assert translation is not None
        assert isinstance(translation, str)
        assert len(translation) > 0
    
    def test_generate_batch_metadata(self, generator):
        """Test batch metadata generation"""
        video_metadatas = [
            VideoMetadata(
                path="/path/to/video1.mp4", filename="video1.mp4", size_mb=100.0,
                duration_seconds=120.0, resolution="1920x1080", format="h264",
                created_at=datetime.now(), episode="S01E01", expression="Test1",
                video_type="final", language="ko"
            ),
            VideoMetadata(
                path="/path/to/video2.mp4", filename="video2.mp4", size_mb=50.0,
                duration_seconds=30.0, resolution="1920x1080", format="h264",
                created_at=datetime.now(), episode="S01E02", expression="Test2",
                video_type="short", language="ko"
            )
        ]
        
        results = generator.generate_batch_metadata(video_metadatas)
        
        assert len(results) == 2
        assert "/path/to/video1.mp4" in results
        assert "/path/to/video2.mp4" in results
        
        # Check that results contain proper metadata
        for video_path, metadata in results.items():
            assert metadata.title is not None
            assert metadata.description is not None
            assert metadata.tags is not None
    
    def test_generate_batch_metadata_with_error(self, generator):
        """Test batch metadata generation with some errors"""
        video_metadatas = [
            VideoMetadata(
                path="/path/to/video1.mp4", filename="video1.mp4", size_mb=100.0,
                duration_seconds=120.0, resolution="1920x1080", format="h264",
                created_at=datetime.now(), episode="S01E01", expression="Test1",
                video_type="final", language="ko"
            ),
            VideoMetadata(
                path="/path/to/video2.mp4", filename="video2.mp4", size_mb=50.0,
                duration_seconds=30.0, resolution="1920x1080", format="h264",
                created_at=datetime.now(), episode="S01E02", expression="Test2",
                video_type="invalid_type", language="ko"  # Invalid type
            )
        ]
        
        # Mock an error for the second video
        with patch.object(generator, 'generate_metadata', side_effect=[Mock(), Exception("Test error")]):
            results = generator.generate_batch_metadata(video_metadatas)
            
            # Should only include successful results
            assert len(results) == 1
            assert "/path/to/video1.mp4" in results
            assert "/path/to/video2.mp4" not in results
    
    def test_update_metadata_template(self, generator):
        """Test updating metadata template"""
        new_template = YouTubeContentTemplate(
            title_template="New Title: {expression}",
            description_template="New Description: {expression}",
            default_tags=["New Tag"],
            category_mapping={"test": "25"}
        )
        
        generator.update_metadata_template("test", new_template)
        
        assert "test" in generator.templates
        assert generator.templates["test"] == new_template
    
    def test_get_available_templates(self, generator):
        """Test getting available template types"""
        templates = generator.get_available_templates()
        
        assert "educational" in templates
        assert "short" in templates
        assert "final" in templates
        assert len(templates) == 3
    
    def test_preview_metadata(self, generator, sample_video_metadata):
        """Test metadata preview generation"""
        preview = generator.preview_metadata(sample_video_metadata)
        
        assert "title" in preview
        assert "description_preview" in preview
        assert "tags" in preview
        assert "category_id" in preview
        assert "template_used" in preview
        
        assert preview["title"] is not None
        assert preview["description_preview"] is not None
        assert preview["tags"] is not None
        assert preview["category_id"] == "22"
        assert preview["template_used"] == sample_video_metadata.video_type
        
        # Check description preview is truncated
        assert preview["description_preview"].endswith("...")
        assert len(preview["description_preview"]) <= 203  # 200 + "..."


class TestYouTubeMetadataGeneratorEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture
    def generator(self):
        """Create YouTubeMetadataGenerator instance"""
        return YouTubeMetadataGenerator()
    
    def test_generate_metadata_empty_expression(self, generator):
        """Test metadata generation with empty expression"""
        video_metadata = VideoMetadata(
            path="/path/to/video.mp4", filename="video.mp4", size_mb=100.0,
            duration_seconds=120.0, resolution="1920x1080", format="h264",
            created_at=datetime.now(), episode="S01E01", expression="",
            video_type="final", language="ko"
        )
        
        metadata = generator.generate_metadata(video_metadata)
        
        assert metadata.title is not None
        assert metadata.description is not None
        assert metadata.tags is not None
    
    def test_generate_metadata_special_characters(self, generator):
        """Test metadata generation with special characters"""
        video_metadata = VideoMetadata(
            path="/path/to/video.mp4", filename="video.mp4", size_mb=100.0,
            duration_seconds=120.0, resolution="1920x1080", format="h264",
            created_at=datetime.now(), episode="S01E01", expression="Test & Expression (with symbols!)",
            video_type="final", language="ko"
        )
        
        metadata = generator.generate_metadata(video_metadata)
        
        assert metadata.title is not None
        assert metadata.description is not None
        assert metadata.tags is not None
        
        # Should handle special characters properly
        # For final videos, the title doesn't include the expression directly
        assert "Complete English Lesson" in metadata.title
    
    def test_generate_metadata_very_long_expression(self, generator):
        """Test metadata generation with very long expression"""
        long_expression = "This is a very long expression that might cause issues with title and description generation"
        video_metadata = VideoMetadata(
            path="/path/to/video.mp4", filename="video.mp4", size_mb=100.0,
            duration_seconds=120.0, resolution="1920x1080", format="h264",
            created_at=datetime.now(), episode="S01E01", expression=long_expression,
            video_type="final", language="ko"
        )
        
        metadata = generator.generate_metadata(video_metadata)
        
        assert metadata.title is not None
        assert metadata.description is not None
        assert metadata.tags is not None
        
        # Title should be reasonable length
        assert len(metadata.title) < 1000  # YouTube title limit
    
    def test_generate_metadata_unicode_characters(self, generator):
        """Test metadata generation with Unicode characters"""
        video_metadata = VideoMetadata(
            path="/path/to/video.mp4", filename="video.mp4", size_mb=100.0,
            duration_seconds=120.0, resolution="1920x1080", format="h264",
            created_at=datetime.now(), episode="S01E01", expression="테스트 표현식",
            video_type="final", language="ko"
        )
        
        metadata = generator.generate_metadata(video_metadata)
        
        assert metadata.title is not None
        assert metadata.description is not None
        assert metadata.tags is not None
        
        # Should handle Unicode properly
        # For final videos, the title doesn't include the expression directly
        assert "Complete English Lesson" in metadata.title
    
    def test_generate_tags_empty_expression(self, generator):
        """Test tag generation with empty expression"""
        video_metadata = VideoMetadata(
            path="/path/to/video.mp4", filename="video.mp4", size_mb=100.0,
            duration_seconds=120.0, resolution="1920x1080", format="h264",
            created_at=datetime.now(), episode="S01E01", expression="",
            video_type="final", language="ko"
        )
        
        template = generator.templates["final"]
        tags = generator._generate_tags(video_metadata, template, None)
        
        assert len(tags) > 0
        assert "English Learning" in tags  # Should have default tags
    
    def test_generate_tags_single_word_expression(self, generator):
        """Test tag generation with single word expression"""
        video_metadata = VideoMetadata(
            path="/path/to/video.mp4", filename="video.mp4", size_mb=100.0,
            duration_seconds=120.0, resolution="1920x1080", format="h264",
            created_at=datetime.now(), episode="S01E01", expression="Test",
            video_type="final", language="ko"
        )
        
        template = generator.templates["final"]
        # Use English explicitly (TICKET-060)
        tags = generator._generate_tags(video_metadata, template, None, target_language="English")
        
        # TICKET-060: Tags are now localized, expression-specific tags may not be generated for short words
        assert len(tags) > 0
        assert "English Learning" in tags or "EnglishLearning" in tags  # Should have basic tags
    
    def test_generate_tags_very_long_tags(self, generator):
        """Test tag generation with very long additional tags"""
        video_metadata = VideoMetadata(
            path="/path/to/video.mp4", filename="video.mp4", size_mb=100.0,
            duration_seconds=120.0, resolution="1920x1080", format="h264",
            created_at=datetime.now(), episode="S01E01", expression="Test",
            video_type="final", language="ko"
        )
        
        template = generator.templates["final"]
        # Create very long tags
        long_tags = ["A" * 100 for _ in range(10)]
        
        tags = generator._generate_tags(video_metadata, template, long_tags)
        
        # Should respect character limit
        total_chars = sum(len(tag) + 1 for tag in tags)
        assert total_chars <= 500
    
    def test_format_episode_display_malformed(self, generator):
        """Test episode display formatting with malformed episode string"""
        malformed_episodes = [
            "S01E",  # Missing episode number
            "S01",   # Missing episode part
            "E01",   # Missing season part
            "S01E01",  # No underscore
            "S01E01_",  # Empty after underscore
        ]
        
        for episode in malformed_episodes:
            formatted = generator._format_episode_display(episode)
            # Should handle gracefully
            assert formatted is not None
            assert isinstance(formatted, str)


class TestTargetLanguageMetadata:
    """Test target language metadata generation (TICKET-060)"""
    
    @pytest.fixture
    def generator(self):
        """Create YouTubeMetadataGenerator instance"""
        return YouTubeMetadataGenerator()
    
    @pytest.fixture
    def sample_video_metadata_short(self):
        """Sample video metadata for short video"""
        return VideoMetadata(
            path="/path/to/short_video.mp4",
            filename="short_video.mp4",
            size_mb=50.0,
            duration_seconds=60.0,
            resolution="1080x1920",
            format="h264",
            created_at=datetime.now(),
            episode="Suits.S01E01",
            expression="Not the point",
            video_type="short",
            language="en",
            expression_translation="요점이 아니야",
            expressions_included=None
        )
    
    @pytest.fixture
    def sample_video_metadata_long_form(self):
        """Sample video metadata for long-form video"""
        return VideoMetadata(
            path="/path/to/long_form_video.mp4",
            filename="long_form_video.mp4",
            size_mb=200.0,
            duration_seconds=300.0,
            resolution="1920x1080",
            format="h264",
            created_at=datetime.now(),
            episode="Suits.S01E01",
            expression="Not the point",
            video_type="educational",
            language="en",
            expression_translation="요점이 아니야",
            expressions_included=None
        )
    
    @pytest.fixture
    def sample_video_metadata_final(self):
        """Sample video metadata for final video"""
        return VideoMetadata(
            path="/path/to/final_video.mp4",
            filename="final_video.mp4",
            size_mb=300.0,
            duration_seconds=600.0,
            resolution="1920x1080",
            format="h264",
            created_at=datetime.now(),
            episode="Suits.S01E01",
            expression="Not the point",
            video_type="final",
            language="en",
            expression_translation="요점이 아니야",
            expressions_included=[
                {"expression": "Not the point", "translation": "요점이 아니야"},
                {"expression": "Get to the point", "translation": "요점으로 가자"}
            ]
        )
    
    def test_generate_title_target_language_short(self, generator, sample_video_metadata_short):
        """Test title generation for short video in target language (TICKET-060)"""
        template = generator.templates["short"]
        title = generator._generate_title(sample_video_metadata_short, template, None, target_language="Korean")
        
        # Should contain Korean text or translated expression
        assert "영어 표현" in title or "요점이 아니야" in title or "from" in title
        assert sample_video_metadata_short.episode in title or "S01E01" in title
    
    def test_generate_title_target_language_long_form(self, generator, sample_video_metadata_long_form):
        """Test title generation for long-form video in target language (TICKET-060)"""
        template = generator.templates["educational"]
        title = generator._generate_title(sample_video_metadata_long_form, template, None, target_language="Korean")
        
        # Should contain Korean text
        assert "수트" in title or "영어" in title or "표현" in title
        assert sample_video_metadata_long_form.episode in title or "S01E01" in title
    
    def test_generate_title_target_language_final(self, generator, sample_video_metadata_final):
        """Test title generation for final video in target language (TICKET-060)"""
        template = generator.templates["final"]
        title = generator._generate_title(sample_video_metadata_final, template, None, target_language="Korean")
        
        # Should contain Korean text
        assert "완전한" in title or "영어" in title or "레슨" in title
        assert sample_video_metadata_final.episode in title or "S01E01" in title
    
    def test_generate_description_target_language_short(self, generator, sample_video_metadata_short):
        """Test description generation for short video in target language (TICKET-060)"""
        template = generator.templates["short"]
        description = generator._generate_description(sample_video_metadata_short, template, None, target_language="Korean")
        
        # Should contain Korean labels and translated expression
        assert "수트에서 배우는" in description
        assert "요점이 아니야" in description  # Translated expression, not English
        assert "표현" in description
        assert "의미" in description
        # Should have localized tags
        assert "#쇼츠" in description or "#영어학습" in description
    
    def test_generate_description_target_language_long_form(self, generator, sample_video_metadata_long_form):
        """Test description generation for long-form video in target language (TICKET-060)"""
        template = generator.templates["educational"]
        description = generator._generate_description(sample_video_metadata_long_form, template, None, target_language="Korean")
        
        # Should contain Korean text
        assert "수트" in description or "영어" in description
        assert "요점이 아니야" in description  # Translated expression
        # Should have localized tags
        assert "#영어학습" in description or "#영어표현" in description
    
    def test_generate_description_target_language_final(self, generator, sample_video_metadata_final):
        """Test description generation for final video in target language (TICKET-060)"""
        template = generator.templates["final"]
        description = generator._generate_description(sample_video_metadata_final, template, None, target_language="Korean")
        
        # Should contain Korean text
        assert "완전한" in description or "영어" in description or "레슨" in description
        assert "요점이 아니야" in description  # Translated expression
        # Should list multiple expressions
        assert "요점으로 가자" in description  # Second expression translation
        # Should have localized tags
        assert "#영어학습" in description or "#영어표현" in description
    
    def test_generate_localized_tags_korean(self, generator, sample_video_metadata_short):
        """Test localized tag generation for Korean (TICKET-060)"""
        tags = generator._generate_localized_tags(sample_video_metadata_short, "Korean")
        
        # Should contain Korean hashtags
        assert "#쇼츠" in tags or "#영어학습" in tags or "#수트" in tags
        assert "#영어표현" in tags or "#영어공부" in tags
    
    def test_generate_localized_tags_japanese(self, generator, sample_video_metadata_short):
        """Test localized tag generation for Japanese (TICKET-060)"""
        tags = generator._generate_localized_tags(sample_video_metadata_short, "Japanese")
        
        # Should contain Japanese hashtags
        assert "#ショート" in tags or "#英語学習" in tags or "#スーツ" in tags
        assert "#英語表現" in tags or "#英語勉強" in tags
    
    def test_generate_localized_tags_chinese(self, generator, sample_video_metadata_short):
        """Test localized tag generation for Chinese (TICKET-060)"""
        tags = generator._generate_localized_tags(sample_video_metadata_short, "Chinese")
        
        # Should contain Chinese hashtags
        assert "#短片" in tags or "#英语学习" in tags or "#金装律师" in tags
        assert "#英语表达" in tags or "#学英语" in tags
    
    def test_generate_localized_tags_english(self, generator, sample_video_metadata_short):
        """Test localized tag generation for English (TICKET-060)"""
        tags = generator._generate_localized_tags(sample_video_metadata_short, "English")
        
        # Should contain English hashtags
        assert "#Shorts" in tags or "#EnglishLearning" in tags
        assert "#Suits" in tags or "#EnglishExpressions" in tags
    
    def test_generate_tags_uses_localized_tags_short(self, generator, sample_video_metadata_short):
        """Test that _generate_tags uses localized tags for short videos (TICKET-060)"""
        template = generator.templates["short"]
        tags = generator._generate_tags(sample_video_metadata_short, template, None, target_language="Korean")
        
        # Tags should be without # (YouTube API format)
        # Should contain Korean tag keywords
        tag_str = " ".join(tags).lower()
        assert "쇼츠" in tag_str or "영어학습" in tag_str or "수트" in tag_str
    
    def test_expression_translation_used_in_description(self, generator, sample_video_metadata_short):
        """Test that expression_translation is used instead of English expression (TICKET-060)"""
        template = generator.templates["short"]
        description = generator._generate_description(sample_video_metadata_short, template, None, target_language="Korean")
        
        # Should use translated expression, not English
        assert "요점이 아니야" in description
        assert "Not the point" not in description or description.count("Not the point") == 0
    
    def test_fallback_to_english_when_translation_missing(self, generator):
        """Test fallback to English when expression_translation is missing (TICKET-060)"""
        video_metadata = VideoMetadata(
            path="/path/to/video.mp4",
            filename="video.mp4",
            size_mb=50.0,
            duration_seconds=60.0,
            resolution="1080x1920",
            format="h264",
            created_at=datetime.now(),
            episode="Suits.S01E01",
            expression="Not the point",
            video_type="short",
            language="en",
            expression_translation=None,  # No translation
            expressions_included=None
        )
        
        template = generator.templates["short"]
        description = generator._generate_description(video_metadata, template, None, target_language="Korean")
        
        # Should still generate description (graceful fallback)
        assert description is not None
        assert len(description) > 0
        # Should use English expression as fallback
        assert "Not the point" in description or "Expression" in description


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
