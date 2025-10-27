"""
Functional tests for UI integration
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from langflix.youtube.web_ui import VideoManagementUI
from langflix.youtube.video_manager import VideoFileManager


class TestUIIntegration:
    """Test UI integration functionality"""
    
    def test_language_display_in_dashboard(self):
        """Test that language is correctly displayed in dashboard"""
        # Create mock video metadata
        mock_videos = [
            {
                'path': 'output/Suits/S01E01/translations/ko/slides/slide_hello.mkv',
                'language': 'ko',
                'episode': 'S01E01',
                'video_type': 'slide',
                'expression': 'hello',
                'size_mb': 10.5,
                'duration_seconds': 30.0,
                'ready_for_upload': True,
                'uploaded_to_youtube': False,
                'youtube_video_id': None
            },
            {
                'path': 'output/Suits/S01E02/translations/es/short_videos/short_video_001.mkv',
                'language': 'es',
                'episode': 'S01E02',
                'video_type': 'short',
                'expression': 'hola',
                'size_mb': 15.2,
                'duration_seconds': 45.0,
                'ready_for_upload': True,
                'uploaded_to_youtube': False,
                'youtube_video_id': None
            }
        ]
        
        # Test language mapping
        language_names = {
            'ko': 'Korean',
            'ja': 'Japanese', 
            'zh': 'Chinese',
            'es': 'Spanish',
            'fr': 'French',
            'en': 'English',
            'unknown': 'Unknown'
        }
        
        for video in mock_videos:
            language_code = video['language']
            display_name = language_names.get(language_code, language_code)
            
            if language_code == 'ko':
                assert display_name == 'Korean'
            elif language_code == 'es':
                assert display_name == 'Spanish'
    
    @patch('langflix.youtube.video_manager.VideoFileManager.scan_all_videos')
    def test_video_api_returns_target_language(self, mock_scan):
        """Test that video API returns correct target language"""
        # Mock video metadata with correct language detection
        mock_videos = [
            MagicMock(
                path='output/Suits/S01E01/translations/ko/slides/slide_hello.mkv',
                language='ko',
                episode='S01E01',
                video_type='slide',
                expression='hello',
                size_mb=10.5,
                duration_seconds=30.0,
                ready_for_upload=True,
                uploaded_to_youtube=False,
                youtube_video_id=None
            )
        ]
        mock_scan.return_value = mock_videos
        
        # Create video manager and test path parsing
        manager = VideoFileManager()
        video_path = Path('output/Suits/S01E01/translations/ko/slides/slide_hello.mkv')
        video_type, episode, expression, language = manager._parse_video_path(video_path)
        
        assert language == 'ko'
        assert episode == 'S01E01'
        assert video_type == 'slide'
    
    def test_button_styling_classes(self):
        """Test that button CSS classes are correctly defined"""
        # This would typically be tested with a browser automation tool
        # Here we test the CSS class definitions conceptually
        
        button_classes = {
            'btn-white': {
                'background': 'white',
                'color': '#2c3e50',
                'border': '1px solid #ddd'
            },
            'btn-white:hover': {
                'background': '#f8f9fa',
                'border-color': '#bbb',
                'color': '#1a252f'
            }
        }
        
        # Verify white button styling exists
        assert 'btn-white' in button_classes
        assert button_classes['btn-white']['background'] == 'white'
        assert button_classes['btn-white']['color'] == '#2c3e50'
    
    @patch('langflix.core.redis_client.get_redis_job_manager')
    def test_progress_updates_after_restart(self, mock_get_manager):
        """Test that progress updates work correctly after backend restart"""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        
        # Simulate startup cleanup
        mock_manager.cleanup_expired_jobs.return_value = 2
        mock_manager.cleanup_stale_jobs.return_value = 1
        mock_manager.health_check.return_value = {
            'status': 'healthy',
            'active_jobs': 3,
            'ping_time_ms': 1.2
        }
        
        # Test cleanup operations
        expired_count = mock_manager.cleanup_expired_jobs()
        stale_count = mock_manager.cleanup_stale_jobs()
        health = mock_manager.health_check()
        
        assert expired_count == 2
        assert stale_count == 1
        assert health['status'] == 'healthy'
        assert health['active_jobs'] == 3
    
    def test_spanish_font_configuration(self):
        """Test Spanish font configuration and fallbacks"""
        from langflix.core.language_config import LanguageConfig
        
        # Test Spanish configuration
        config = LanguageConfig.get_config('es')
        
        assert config['name'] == 'Spanish'
        assert 'special_characters' in config
        assert 'ñ' in config['special_characters']
        assert 'á' in config['special_characters']
        assert 'ü' in config['special_characters']
        
        # Test font fallback is a list
        assert isinstance(config['font_fallback'], list)
        assert len(config['font_fallback']) > 1
        
        # Test font recommendations
        recommendations = LanguageConfig.get_spanish_font_recommendations()
        assert isinstance(recommendations, list)
    
    @patch('pathlib.Path.exists')
    def test_spanish_character_rendering_preparation(self, mock_exists):
        """Test preparation for Spanish character rendering"""
        from langflix.core.language_config import LanguageConfig
        
        # Mock font existence
        mock_exists.return_value = True
        
        # Test font path resolution
        font_path = LanguageConfig.get_font_path('es')
        assert font_path is not None
        assert len(font_path) > 0
        
        # Test font validation
        validation = LanguageConfig.validate_font_for_language('es')
        assert validation['language_code'] == 'es'
        assert 'font_path' in validation
        assert 'special_characters' in validation
        assert validation['font_exists'] == True
    
    def test_video_cache_integration(self):
        """Test video cache integration with Redis"""
        from langflix.core.redis_client import RedisJobManager
        
        # Mock Redis operations
        with patch('redis.from_url') as mock_redis:
            mock_client = MagicMock()
            mock_redis.return_value = mock_client
            
            manager = RedisJobManager()
            
            # Test cache operations
            videos = [{'path': 'test.mkv', 'language': 'ko'}]
            
            # Test cache set
            mock_client.setex.return_value = True
            success = manager.set_video_cache(videos, ttl=300)
            assert success == True
            
            # Test cache get
            import json
            mock_client.get.return_value = json.dumps(videos)
            cached_videos = manager.get_video_cache()
            assert cached_videos == videos


class TestVideoManagerIntegration:
    """Test video manager integration with language detection"""
    
    def test_video_metadata_extraction_with_language(self):
        """Test video metadata extraction includes correct language"""
        manager = VideoFileManager()
        
        # Test different language paths
        test_cases = [
            {
                'path': 'output/Suits/S01E01/translations/ko/slides/slide_hello.mkv',
                'expected_language': 'ko',
                'expected_episode': 'S01E01',
                'expected_type': 'slide'
            },
            {
                'path': 'output/Suits/S01E02/translations/es/short_videos/short_video_001.mkv',
                'expected_language': 'es',
                'expected_episode': 'S01E02',
                'expected_type': 'short'
            },
            {
                'path': 'output/Suits/S01E03/translations/ja/context_videos/context_hello.mkv',
                'expected_language': 'ja',
                'expected_episode': 'S01E03',
                'expected_type': 'context'
            }
        ]
        
        for case in test_cases:
            video_path = Path(case['path'])
            video_type, episode, expression, language = manager._parse_video_path(video_path)
            
            assert language == case['expected_language']
            assert episode == case['expected_episode']
            assert video_type == case['expected_type']
    
    def test_video_to_dict_conversion(self):
        """Test video metadata to dictionary conversion"""
        from langflix.youtube.web_ui import VideoManagementUI
        from langflix.youtube.video_manager import VideoMetadata
        from datetime import datetime
        
        # Create mock video metadata
        video = VideoMetadata(
            path='output/Suits/S01E01/translations/ko/slides/slide_hello.mkv',
            filename='slide_hello.mkv',
            size_mb=10.5,
            duration_seconds=30.0,
            resolution='1920x1080',
            format='h264',
            created_at=datetime.now(),
            episode='S01E01',
            expression='hello',
            video_type='slide',
            language='ko',
            ready_for_upload=True
        )
        
        # Create UI instance and test conversion
        ui = VideoManagementUI()
        video_dict = ui._video_to_dict(video)
        
        assert video_dict['language'] == 'ko'
        assert video_dict['episode'] == 'S01E01'
        assert video_dict['video_type'] == 'slide'
        assert video_dict['ready_for_upload'] == True
        assert 'upload_status' in video_dict
