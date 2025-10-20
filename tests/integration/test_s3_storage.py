"""
Integration tests for S3 storage backend
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import storage modules
from langflix.storage.base import StorageBackend
from langflix.storage.local import LocalStorage
from langflix.storage.s3 import S3Storage


class TestLocalStorage:
    """Test LocalStorage backend"""
    
    def test_backend_type(self):
        """Test backend type property"""
        storage = LocalStorage()
        assert storage.backend_type == 'local'
    
    def test_download_file_local(self):
        """Test downloading file locally (no-op)"""
        storage = LocalStorage()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file
            source_file = Path(temp_dir) / "test.txt"
            source_file.write_text("test content")
            
            dest_file = Path(temp_dir) / "copied.txt"
            
            # Test download (copy operation)
            result = storage.download_file(str(source_file), dest_file)
            
            assert result is True
            assert dest_file.exists()
            assert dest_file.read_text() == "test content"
    
    def test_upload_file_local(self):
        """Test uploading file locally (copy operation)"""
        storage = LocalStorage()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file
            source_file = Path(temp_dir) / "source.txt"
            source_file.write_text("test content")
            
            dest_file = Path(temp_dir) / "dest.txt"
            
            # Test upload (copy operation)
            result = storage.upload_file(source_file, str(dest_file))
            
            assert result is True
            assert dest_file.exists()
            assert dest_file.read_text() == "test content"
    
    def test_exists_local(self):
        """Test checking file existence locally"""
        storage = LocalStorage()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            
            # Test non-existent file
            assert storage.exists(str(test_file)) is False
            
            # Create file and test existence
            test_file.write_text("test")
            assert storage.exists(str(test_file)) is True


class TestS3Storage:
    """Test S3Storage backend with mocking"""
    
    @patch('langflix.storage.s3.boto3')
    def test_backend_type(self, mock_boto3):
        """Test backend type property"""
        mock_s3_client = Mock()
        mock_boto3.client.return_value = mock_s3_client
        
        storage = S3Storage(bucket="test-bucket", region="us-east-1")
        assert storage.backend_type == 's3'
    
    @patch('langflix.storage.s3.boto3')
    def test_s3_path_detection(self, mock_boto3):
        """Test S3 path detection and key extraction"""
        mock_s3_client = Mock()
        mock_boto3.client.return_value = mock_s3_client
        
        storage = S3Storage(bucket="test-bucket", region="us-east-1")
        
        # Test S3 path detection
        assert storage.is_s3_path("s3://bucket/key") is True
        assert storage.is_s3_path("/local/path") is False
        
        # Test key extraction
        assert storage.extract_s3_key("s3://bucket/path/to/file.txt") == "path/to/file.txt"
        
        # Test invalid S3 path
        with pytest.raises(ValueError):
            storage.extract_s3_key("/local/path")
    
    @patch('langflix.storage.s3.boto3')
    def test_download_file_success(self, mock_boto3):
        """Test successful file download from S3"""
        mock_s3_client = Mock()
        mock_boto3.client.return_value = mock_s3_client
        
        storage = S3Storage(bucket="test-bucket", region="us-east-1")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            local_file = Path(temp_dir) / "downloaded.txt"
            
            # Mock successful download
            mock_s3_client.download_file.return_value = None
            
            result = storage.download_file("test/key.txt", local_file)
            
            assert result is True
            mock_s3_client.download_file.assert_called_once_with(
                "test-bucket", "test/key.txt", str(local_file)
            )
    
    @patch('langflix.storage.s3.boto3')
    def test_download_file_client_error(self, mock_boto3):
        """Test download failure with ClientError"""
        from botocore.exceptions import ClientError
        
        mock_s3_client = Mock()
        mock_boto3.client.return_value = mock_s3_client
        
        storage = S3Storage(bucket="test-bucket", region="us-east-1")
        
        # Mock ClientError
        mock_s3_client.download_file.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey'}}, 'DownloadFile'
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            local_file = Path(temp_dir) / "downloaded.txt"
            
            result = storage.download_file("test/key.txt", local_file)
            
            assert result is False
    
    @patch('langflix.storage.s3.boto3')
    def test_upload_file_success(self, mock_boto3):
        """Test successful file upload to S3"""
        mock_s3_client = Mock()
        mock_boto3.client.return_value = mock_s3_client
        
        storage = S3Storage(bucket="test-bucket", region="us-east-1")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            local_file = Path(temp_dir) / "upload.txt"
            local_file.write_text("test content")
            
            # Mock successful upload
            mock_s3_client.upload_file.return_value = None
            
            result = storage.upload_file(local_file, "test/upload.txt")
            
            assert result is True
            mock_s3_client.upload_file.assert_called_once_with(
                str(local_file), "test-bucket", "test/upload.txt"
            )
    
    @patch('langflix.storage.s3.boto3')
    def test_exists_success(self, mock_boto3):
        """Test checking file existence in S3"""
        mock_s3_client = Mock()
        mock_boto3.client.return_value = mock_s3_client
        
        storage = S3Storage(bucket="test-bucket", region="us-east-1")
        
        # Mock successful head_object (file exists)
        mock_s3_client.head_object.return_value = {}
        
        result = storage.exists("test/key.txt")
        
        assert result is True
        mock_s3_client.head_object.assert_called_once_with(
            Bucket="test-bucket", Key="test/key.txt"
        )
    
    @patch('langflix.storage.s3.boto3')
    def test_exists_not_found(self, mock_boto3):
        """Test checking non-existent file in S3"""
        from botocore.exceptions import ClientError
        
        mock_s3_client = Mock()
        mock_boto3.client.return_value = mock_s3_client
        
        storage = S3Storage(bucket="test-bucket", region="us-east-1")
        
        # Mock 404 error (file not found)
        mock_s3_client.head_object.side_effect = ClientError(
            {'Error': {'Code': '404'}}, 'HeadObject'
        )
        
        result = storage.exists("test/key.txt")
        
        assert result is False


class TestStorageIntegration:
    """Integration tests for storage backend factory"""
    
    @patch('langflix.storage.get_storage_backend')
    @patch('langflix.storage.ConfigLoader')
    def test_local_storage_factory(self, mock_config, mock_factory):
        """Test factory returns LocalStorage for local backend"""
        from langflix.storage import get_storage_backend
        
        # Mock config to return local backend
        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.get.return_value = 'local'
        
        storage = get_storage_backend()
        
        assert isinstance(storage, LocalStorage)
        assert storage.backend_type == 'local'
    
    @patch('langflix.storage.ConfigLoader')
    def test_s3_storage_factory(self, mock_config):
        """Test factory returns S3Storage for S3 backend"""
        from langflix.storage import get_storage_backend
        
        # Mock config to return S3 backend with settings
        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.get.return_value = 's3'
        mock_config_instance.get_section.return_value = {
            'input_bucket': 'test-bucket',
            'region': 'us-east-1'
        }
        
        with patch('langflix.storage.boto3') as mock_boto3:
            mock_s3_client = Mock()
            mock_boto3.client.return_value = mock_s3_client
            
            storage = get_storage_backend()
            
            assert isinstance(storage, S3Storage)
            assert storage.backend_type == 's3'


if __name__ == "__main__":
    pytest.main([__file__])
