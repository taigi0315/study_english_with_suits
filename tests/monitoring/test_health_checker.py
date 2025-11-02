"""
Tests for SystemHealthChecker class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from langflix.monitoring.health_checker import SystemHealthChecker


class TestSystemHealthChecker:
    """Test SystemHealthChecker class"""
    
    def test_check_database_disabled(self):
        """Test database check when database is disabled."""
        checker = SystemHealthChecker()
        
        with patch('langflix.settings.get_database_enabled', return_value=False):
            result = checker.check_database()
            
            assert result["status"] == "disabled"
            assert "message" in result
    
    def test_check_database_healthy(self):
        """Test database check when database is healthy."""
        checker = SystemHealthChecker()
        
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_db = Mock()
        mock_db.execute.return_value = mock_result
        
        mock_db_manager = Mock()
        mock_db_manager.session.return_value.__enter__ = Mock(return_value=mock_db)
        mock_db_manager.session.return_value.__exit__ = Mock(return_value=None)
        
        with patch('langflix.settings.get_database_enabled', return_value=True):
            with patch('langflix.db.session.db_manager', mock_db_manager):
                result = checker.check_database()
                
                assert result["status"] == "healthy"
                assert "message" in result
                assert "Database connection successful" in result["message"]
    
    def test_check_database_unhealthy(self):
        """Test database check when database connection fails."""
        checker = SystemHealthChecker()
        
        mock_db_manager = Mock()
        mock_db_manager.session.side_effect = Exception("Connection error")
        
        with patch('langflix.settings.get_database_enabled', return_value=True):
            with patch('langflix.db.session.db_manager', mock_db_manager):
                result = checker.check_database()
                
                assert result["status"] == "unhealthy"
                assert "message" in result
                assert "Connection error" in result["message"]
    
    def test_check_storage_healthy(self):
        """Test storage check when storage is healthy."""
        checker = SystemHealthChecker()
        
        mock_storage = Mock()
        mock_storage.list_files.return_value = []
        type(mock_storage).__name__ = 'LocalStorage'
        
        with patch('langflix.storage.factory.create_storage_backend', return_value=mock_storage):
            result = checker.check_storage()
            
            assert result["status"] == "healthy"
            assert "message" in result
            assert "LocalStorage" in result["message"]
    
    def test_check_storage_unhealthy(self):
        """Test storage check when storage has error."""
        checker = SystemHealthChecker()
        
        with patch('langflix.storage.factory.create_storage_backend', side_effect=Exception("Storage error")):
            result = checker.check_storage()
            
            assert result["status"] == "unhealthy"
            assert "message" in result
            assert "Storage error" in result["message"]
    
    def test_check_redis_healthy(self):
        """Test Redis check when Redis is healthy."""
        checker = SystemHealthChecker()
        
        mock_redis_manager = Mock()
        mock_redis_manager.health_check.return_value = {
            "status": "healthy",
            "active_jobs": 5
        }
        
        with patch('langflix.core.redis_client.get_redis_job_manager', return_value=mock_redis_manager):
            result = checker.check_redis()
            
            assert result["status"] == "healthy"
            assert result["active_jobs"] == 5
    
    def test_check_redis_unhealthy(self):
        """Test Redis check when Redis connection fails."""
        checker = SystemHealthChecker()
        
        with patch('langflix.core.redis_client.get_redis_job_manager', side_effect=Exception("Redis error")):
            result = checker.check_redis()
            
            assert result["status"] == "unhealthy"
            assert "message" in result
            assert "Redis error" in result["message"]
    
    def test_check_tts_gemini_healthy(self):
        """Test TTS check when Gemini is configured correctly."""
        checker = SystemHealthChecker()
        
        with patch('langflix.settings.get_tts_provider', return_value="gemini"):
            with patch('os.getenv', return_value='test_key'):
                result = checker.check_tts()
                
                assert result["status"] == "healthy"
                assert "message" in result
                assert "Gemini" in result["message"]
    
    def test_check_tts_gemini_unhealthy(self):
        """Test TTS check when Gemini API key is missing."""
        checker = SystemHealthChecker()
        
        with patch('langflix.settings.get_tts_provider', return_value="gemini"):
            with patch('os.getenv', return_value=None):
                result = checker.check_tts()
                
                assert result["status"] == "unhealthy"
                assert "message" in result
                assert "Gemini API key not configured" in result["message"]
    
    def test_check_tts_lemonfox_healthy(self):
        """Test TTS check when LemonFox is configured correctly."""
        checker = SystemHealthChecker()
        
        with patch('langflix.settings.get_tts_provider', return_value="lemonfox"):
            with patch('os.getenv', return_value='test_key'):
                result = checker.check_tts()
                
                assert result["status"] == "healthy"
                assert "message" in result
                assert "LemonFox" in result["message"]
    
    def test_check_tts_lemonfox_unhealthy(self):
        """Test TTS check when LemonFox API key is missing."""
        checker = SystemHealthChecker()
        
        with patch('langflix.settings.get_tts_provider', return_value="lemonfox"):
            with patch('os.getenv', return_value=None):
                result = checker.check_tts()
                
                assert result["status"] == "unhealthy"
                assert "message" in result
                assert "LemonFox API key not configured" in result["message"]
    
    def test_check_tts_unknown_provider(self):
        """Test TTS check with unknown provider."""
        checker = SystemHealthChecker()
        
        with patch('langflix.settings.get_tts_provider', return_value="unknown"):
            result = checker.check_tts()
            
            assert result["status"] == "unknown"
            assert "message" in result
            assert "unknown" in result["message"]
    
    def test_get_overall_health_all_healthy(self):
        """Test overall health when all components are healthy."""
        checker = SystemHealthChecker()
        
        with patch.object(checker, 'check_database', return_value={"status": "healthy", "message": "OK"}):
            with patch.object(checker, 'check_storage', return_value={"status": "healthy", "message": "OK"}):
                with patch.object(checker, 'check_redis', return_value={"status": "healthy"}):
                    with patch.object(checker, 'check_tts', return_value={"status": "healthy", "message": "OK"}):
                        result = checker.get_overall_health()
                        
                        assert result["status"] == "healthy"
                        assert "components" in result
                        assert "timestamp" in result
                        assert "database" in result["components"]
                        assert "storage" in result["components"]
                        assert "redis" in result["components"]
                        assert "tts" in result["components"]
    
    def test_get_overall_health_unhealthy(self):
        """Test overall health when one component is unhealthy."""
        checker = SystemHealthChecker()
        
        with patch.object(checker, 'check_database', return_value={"status": "unhealthy", "message": "Error"}):
            with patch.object(checker, 'check_storage', return_value={"status": "healthy", "message": "OK"}):
                with patch.object(checker, 'check_redis', return_value={"status": "healthy"}):
                    with patch.object(checker, 'check_tts', return_value={"status": "healthy", "message": "OK"}):
                        result = checker.get_overall_health()
                        
                        assert result["status"] == "unhealthy"
    
    def test_get_overall_health_degraded(self):
        """Test overall health when one component is unknown."""
        checker = SystemHealthChecker()
        
        with patch.object(checker, 'check_database', return_value={"status": "healthy", "message": "OK"}):
            with patch.object(checker, 'check_storage', return_value={"status": "healthy", "message": "OK"}):
                with patch.object(checker, 'check_redis', return_value={"status": "healthy"}):
                    with patch.object(checker, 'check_tts', return_value={"status": "unknown", "message": "Unknown"}):
                        result = checker.get_overall_health()
                        
                        assert result["status"] == "degraded"

