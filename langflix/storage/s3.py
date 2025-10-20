"""
AWS S3 storage backend
"""

import logging
from pathlib import Path
from typing import Optional

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from .base import StorageBackend

logger = logging.getLogger(__name__)


class S3Storage(StorageBackend):
    """
    AWS S3 storage backend
    """
    
    def __init__(self, bucket: str, region: str = 'us-east-1'):
        """
        Initialize S3 storage backend
        
        Args:
            bucket: S3 bucket name
            region: AWS region
        """
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 is required for S3Storage. Install with: pip install boto3")
        
        self.bucket = bucket
        self.region = region
        
        try:
            self.s3_client = boto3.client('s3', region_name=region)
            logger.info(f"Initialized S3 storage backend for bucket: {bucket} in region: {region}")
        except NoCredentialsError:
            logger.error("AWS credentials not configured")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise
    
    @property
    def backend_type(self) -> str:
        return 's3'
    
    def download_file(self, s3_key: str, local_path: Path) -> bool:
        """
        Download file from S3 to local path
        
        Args:
            s3_key: S3 key (path within bucket)
            local_path: Local path to save the file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Handle S3 URLs (s3://bucket/key format)
            if self.is_s3_path(s3_key):
                # Validate that bucket matches
                if not s3_key.startswith(f's3://{self.bucket}/'):
                    logger.error(f"S3 path bucket mismatch. Expected {self.bucket}, got: {s3_key}")
                    return False
                s3_key = self.extract_s3_key(s3_key)
            
            # Ensure local directory exists
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Downloading s3://{self.bucket}/{s3_key} to {local_path}")
            self.s3_client.download_file(self.bucket, s3_key, str(local_path))
            logger.info(f"Successfully downloaded {s3_key} to {local_path}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.error(f"S3 key does not exist: s3://{self.bucket}/{s3_key}")
            elif error_code == 'NoSuchBucket':
                logger.error(f"S3 bucket does not exist: {self.bucket}")
            else:
                logger.error(f"S3 download failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to download file from S3: {e}")
            return False
    
    def upload_file(self, local_path: Path, s3_key: str) -> bool:
        """
        Upload file from local path to S3
        
        Args:
            local_path: Local path of the file to upload
            s3_key: S3 key (path within bucket)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not local_path.exists():
                logger.error(f"Local file does not exist: {local_path}")
                return False
            
            logger.info(f"Uploading {local_path} to s3://{self.bucket}/{s3_key}")
            self.s3_client.upload_file(str(local_path), self.bucket, s3_key)
            logger.info(f"Successfully uploaded {local_path} to s3://{self.bucket}/{s3_key}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                logger.error(f"S3 bucket does not exist: {self.bucket}")
            else:
                logger.error(f"S3 upload failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to upload file to S3: {e}")
            return False
    
    def exists(self, s3_key: str) -> bool:
        """
        Check if file exists in S3
        
        Args:
            s3_key: S3 key (path within bucket)
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            # Handle S3 URLs (s3://bucket/key format)
            if self.is_s3_path(s3_key):
                # Validate that bucket matches
                if not s3_key.startswith(f's3://{self.bucket}/'):
                    logger.error(f"S3 path bucket mismatch. Expected {self.bucket}, got: {s3_key}")
                    return False
                s3_key = self.extract_s3_key(s3_key)
            
            self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)
            logger.debug(f"S3 object exists: s3://{self.bucket}/{s3_key}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.debug(f"S3 object does not exist: s3://{self.bucket}/{s3_key}")
                return False
            else:
                logger.error(f"Error checking S3 object existence: {e}")
                return False
        except Exception as e:
            logger.error(f"Failed to check S3 object existence: {e}")
            return False
    
    def list_objects(self, prefix: str = '') -> list:
        """
        List objects in S3 bucket with optional prefix
        
        Args:
            prefix: Prefix to filter objects
            
        Returns:
            List of object keys
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )
            
            objects = []
            if 'Contents' in response:
                objects = [obj['Key'] for obj in response['Contents']]
            
            logger.debug(f"Found {len(objects)} objects with prefix {prefix}")
            return objects
            
        except ClientError as e:
            logger.error(f"Failed to list S3 objects: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing S3 objects: {e}")
            return []
