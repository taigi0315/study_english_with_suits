"""
YouTube API Uploader
Handles authentication and video uploads to YouTube
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import time

# YouTube API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow, Flow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False
    Flow = None
    logger.warning("YouTube API libraries not installed. Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")

logger = logging.getLogger(__name__)

# YouTube API scopes
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.readonly'
]

@dataclass
class YouTubeUploadResult:
    """Result of YouTube upload"""
    success: bool
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    error_message: Optional[str] = None
    upload_time: Optional[datetime] = None

@dataclass
class YouTubeVideoMetadata:
    """YouTube video metadata"""
    title: str
    description: str
    tags: List[str]
    category_id: str = "22"  # People & Blogs
    privacy_status: str = "private"  # private, public, unlisted
    thumbnail_path: Optional[str] = None

class YouTubeUploader:
    """Handles YouTube video uploads"""
    
    def __init__(self, credentials_file: str = "youtube_credentials.json", token_file: str = "youtube_token.json", oauth_state_storage=None):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.authenticated = False
        self.oauth_state_storage = oauth_state_storage  # Optional: Redis or dict for state storage
        
        if not YOUTUBE_API_AVAILABLE:
            raise ImportError("YouTube API libraries not available. Install required packages.")
    
    def authenticate(self) -> bool:
        """Authenticate with YouTube API"""
        try:
            # Validate credentials file exists
            if not os.path.exists(self.credentials_file):
                error_msg = (
                    f"YouTube credentials file not found: {self.credentials_file}\n"
                    "Please download OAuth2 credentials from Google Cloud Console and save as 'youtube_credentials.json'"
                )
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)
            
            creds = None
            
            # Load existing token
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            
            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                        logger.info("Successfully refreshed YouTube OAuth token")
                    except Exception as e:
                        logger.warning(f"Token refresh failed: {e}, starting new OAuth flow")
                        creds = None
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                    # Use fixed port 8080 for consistency
                    try:
                        creds = flow.run_local_server(port=8080, open_browser=True)
                    except OSError as e:
                        if "Address already in use" in str(e) or "address already in use" in str(e).lower():
                            error_msg = (
                                f"Port 8080 is already in use. Please close other applications using this port.\n"
                                f"Error: {str(e)}"
                            )
                            logger.error(error_msg)
                            raise OSError(error_msg)
                        raise
                
                # Save credentials for next run
                if creds:
                    with open(self.token_file, 'w') as token:
                        token.write(creds.to_json())
            
            # Build YouTube service
            self.service = build('youtube', 'v3', credentials=creds)
            self.authenticated = True
            
            logger.info("Successfully authenticated with YouTube API")
            return True
            
        except FileNotFoundError as e:
            logger.error(f"YouTube authentication failed: {e}")
            raise
        except OSError as e:
            logger.error(f"YouTube OAuth port conflict: {e}")
            raise
        except Exception as e:
            logger.error(f"YouTube authentication error: {e}", exc_info=True)
            raise
    
    def get_authorization_url(self, redirect_uri: str, email: Optional[str] = None) -> Dict[str, str]:
        """
        Generate OAuth authorization URL for web flow
        
        Args:
            redirect_uri: OAuth callback redirect URI
            email: Optional email to pre-fill (login_hint)
            
        Returns:
            dict with 'url' and 'state' for OAuth flow
        """
        if Flow is None:
            raise ImportError("Flow class not available. Install google-auth-oauthlib.")
        
        if not os.path.exists(self.credentials_file):
            error_msg = (
                f"YouTube credentials file not found: {self.credentials_file}\n"
                "Please download OAuth2 credentials from Google Cloud Console and save as 'youtube_credentials.json'"
            )
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        # Load client secrets
        with open(self.credentials_file, 'r') as f:
            client_config = json.load(f)
        
        # Convert 'installed' type to 'web' type for web flow
        # If credentials are for 'installed' app, we need to adapt them
        if 'installed' in client_config:
            installed_config = client_config['installed']
            if not all(k in installed_config for k in ['client_id', 'client_secret', 'auth_uri', 'token_uri']):
                raise ValueError(
                    "Invalid credentials file format. Missing required fields: "
                    "client_id, client_secret, auth_uri, or token_uri"
                )
            web_config = {
                'web': {
                    'client_id': installed_config['client_id'],
                    'client_secret': installed_config['client_secret'],
                    'auth_uri': installed_config['auth_uri'],
                    'token_uri': installed_config['token_uri'],
                    'redirect_uris': [redirect_uri]
                }
            }
            client_config = web_config
        elif 'web' not in client_config:
            raise ValueError(
                "Invalid credentials file format. Expected 'installed' or 'web' client configuration. "
                f"Found: {list(client_config.keys())}"
            )
        
        # Create Flow for web application
        try:
            flow = Flow.from_client_config(
                client_config,
                SCOPES,
                redirect_uri=redirect_uri
            )
        except Exception as e:
            logger.error(f"Failed to create OAuth Flow: {e}")
            raise ValueError(f"Failed to initialize OAuth flow: {str(e)}") from e
        
        # Add login hint if email provided
        auth_url_kwargs = {}
        if email:
            auth_url_kwargs['login_hint'] = email
        
        # Generate authorization URL
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',  # Force consent screen to get refresh token
            **auth_url_kwargs
        )
        
        # Store state for verification (expires in 10 minutes)
        self._store_oauth_state(state, expiration_seconds=600)
        
        logger.info(f"Generated OAuth URL for web flow (email hint: {email is not None})")
        
        return {
            'url': authorization_url,
            'state': state
        }
    
    def authenticate_from_callback(self, authorization_code: str, state: str, redirect_uri: str) -> bool:
        """
        Complete OAuth flow from callback code
        
        Args:
            authorization_code: OAuth authorization code from callback
            state: OAuth state for verification
            redirect_uri: OAuth callback redirect URI (must match the one used in get_authorization_url)
            
        Returns:
            True if authentication successful
        """
        if Flow is None:
            raise ImportError("Flow class not available. Install google-auth-oauthlib.")
        
        # Verify state
        if not self._verify_oauth_state(state):
            logger.error("Invalid OAuth state - possible CSRF attack")
            raise ValueError("Invalid OAuth state")
        
        if not os.path.exists(self.credentials_file):
            raise FileNotFoundError(f"Credentials file not found: {self.credentials_file}")
        
        # Load client secrets
        with open(self.credentials_file, 'r') as f:
            client_config = json.load(f)
        
        # Convert 'installed' type to 'web' type if needed
        if 'installed' in client_config:
            web_config = {
                'web': {
                    'client_id': client_config['installed']['client_id'],
                    'client_secret': client_config['installed']['client_secret'],
                    'auth_uri': client_config['installed']['auth_uri'],
                    'token_uri': client_config['installed']['token_uri'],
                    'redirect_uris': [redirect_uri]
                }
            }
            client_config = web_config
        
        # Create Flow
        flow = Flow.from_client_config(
            client_config,
            SCOPES,
            redirect_uri=redirect_uri
        )
        
        # Exchange code for credentials
        flow.fetch_token(code=authorization_code)
        creds = flow.credentials
        
        # Save credentials
        if creds:
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
            logger.info("OAuth credentials saved to token file")
        
        # Build YouTube service
        self.service = build('youtube', 'v3', credentials=creds)
        self.authenticated = True
        
        # Remove verified state
        self._remove_oauth_state(state)
        
        logger.info("Successfully authenticated with YouTube API via web flow")
        return True
    
    def _store_oauth_state(self, state: str, expiration_seconds: int = 600):
        """Store OAuth state temporarily with expiration"""
        if self.oauth_state_storage is None:
            # Fallback to in-memory dict if no storage provided
            if not hasattr(self, '_oauth_states'):
                self._oauth_states = {}
            self._oauth_states[state] = time.time() + expiration_seconds
        else:
            # Use provided storage (e.g., Redis)
            try:
                if hasattr(self.oauth_state_storage, 'setex'):
                    # Redis-like interface
                    self.oauth_state_storage.setex(f"oauth:state:{state}", expiration_seconds, state)
                elif hasattr(self.oauth_state_storage, 'set'):
                    # Dict-like interface with TTL support
                    self.oauth_state_storage[state] = {
                        'expires_at': time.time() + expiration_seconds
                    }
                else:
                    # Simple dict
                    self.oauth_state_storage[state] = time.time() + expiration_seconds
            except Exception as e:
                logger.warning(f"Failed to store OAuth state in storage: {e}, using fallback")
                if not hasattr(self, '_oauth_states'):
                    self._oauth_states = {}
                self._oauth_states[state] = time.time() + expiration_seconds
    
    def _verify_oauth_state(self, state: str) -> bool:
        """Verify OAuth state matches stored state"""
        if self.oauth_state_storage is None:
            # Check in-memory dict
            if not hasattr(self, '_oauth_states'):
                return False
            stored_expiry = self._oauth_states.get(state)
            if stored_expiry is None:
                return False
            if time.time() > stored_expiry:
                # Expired
                del self._oauth_states[state]
                return False
            return True
        else:
            # Check provided storage
            try:
                if hasattr(self.oauth_state_storage, 'get'):
                    # Redis-like or dict-like
                    if hasattr(self.oauth_state_storage, 'get') and callable(self.oauth_state_storage.get):
                        stored = self.oauth_state_storage.get(f"oauth:state:{state}")
                        if stored:
                            return True
                    # Dict-like
                    stored = self.oauth_state_storage.get(state)
                    if stored is None:
                        return False
                    if isinstance(stored, dict):
                        expires_at = stored.get('expires_at', 0)
                        if time.time() > expires_at:
                            return False
                    return True
            except Exception as e:
                logger.warning(f"Failed to verify OAuth state from storage: {e}")
                return False
        return False
    
    def _remove_oauth_state(self, state: str):
        """Remove OAuth state after successful verification"""
        if self.oauth_state_storage is None:
            if hasattr(self, '_oauth_states'):
                self._oauth_states.pop(state, None)
        else:
            try:
                if hasattr(self.oauth_state_storage, 'delete'):
                    self.oauth_state_storage.delete(f"oauth:state:{state}")
                elif hasattr(self.oauth_state_storage, 'pop'):
                    self.oauth_state_storage.pop(state, None)
            except Exception as e:
                logger.warning(f"Failed to remove OAuth state: {e}")
    
    def upload_video(
        self, 
        video_path: str, 
        metadata: YouTubeVideoMetadata,
        progress_callback: Optional[callable] = None
    ) -> YouTubeUploadResult:
        """Upload video to YouTube"""
        
        if not self.authenticated:
            if not self.authenticate():
                return YouTubeUploadResult(
                    success=False,
                    error_message="Authentication failed"
                )
        
        try:
            video_file = Path(video_path)
            if not video_file.exists():
                return YouTubeUploadResult(
                    success=False,
                    error_message=f"Video file not found: {video_path}"
                )
            
            logger.info(f"Starting upload: {video_file.name}")
            
            # Prepare video metadata
            body = {
                'snippet': {
                    'title': metadata.title,
                    'description': metadata.description,
                    'tags': metadata.tags,
                    'categoryId': metadata.category_id
                },
                'status': {
                    'privacyStatus': metadata.privacy_status
                }
            }
            
            # Create media upload
            media = MediaFileUpload(
                str(video_file),
                chunksize=-1,
                resumable=True,
                mimetype='video/*'
            )
            
            # Start upload
            insert_request = self.service.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            # Execute upload with progress tracking
            response = self._resumable_upload(insert_request, progress_callback)
            
            if response:
                video_id = response['id']
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                
                logger.info(f"Upload successful: {video_url}")
                
                # Upload thumbnail if provided
                if metadata.thumbnail_path and os.path.exists(metadata.thumbnail_path):
                    self._upload_thumbnail(video_id, metadata.thumbnail_path)
                
                return YouTubeUploadResult(
                    success=True,
                    video_id=video_id,
                    video_url=video_url,
                    upload_time=datetime.now()
                )
            else:
                return YouTubeUploadResult(
                    success=False,
                    error_message="Upload failed - no response received"
                )
                
        except HttpError as e:
            error_msg = f"YouTube API error: {e}"
            logger.error(error_msg)
            return YouTubeUploadResult(
                success=False,
                error_message=error_msg
            )
        except Exception as e:
            error_msg = f"Upload error: {e}"
            logger.error(error_msg)
            return YouTubeUploadResult(
                success=False,
                error_message=error_msg
            )
    
    def _resumable_upload(self, insert_request, progress_callback=None):
        """Handle resumable upload with progress tracking"""
        response = None
        error = None
        retry = 0
        max_retries = 3
        max_iterations = 1000  # Prevent infinite loop
        iteration = 0
        start_time = time.time()
        timeout_seconds = 3600  # 1 hour timeout
        
        logger.info("Starting resumable upload...")
        
        while response is None and iteration < max_iterations:
            iteration += 1
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                logger.error(f"Upload timeout after {elapsed:.1f} seconds")
                return None
            
            try:
                status, response = insert_request.next_chunk()
                if response is not None:
                    if 'id' in response:
                        logger.info(f"Upload completed successfully: video_id={response['id']}")
                        return response
                    else:
                        error_msg = f"Upload response missing video ID: {response}"
                        logger.error(error_msg)
                        return None
                else:
                    # Still uploading, update progress
                    if status:
                        progress = status.progress() * 100
                        if progress_callback:
                            progress_callback(progress)
                        if iteration % 10 == 0:  # Log every 10 iterations to avoid spam
                            logger.info(f"Upload progress: {progress:.1f}% (iteration {iteration})")
                    
            except HttpError as e:
                error_msg = str(e)
                status_code = e.resp.status if hasattr(e, 'resp') and e.resp else None
                
                if status_code in [500, 502, 503, 504]:
                    # Retriable error
                    retry += 1
                    if retry > max_retries:
                        logger.error(f"Max retries exceeded for retriable error: {error_msg} (status: {status_code})")
                        return None
                    logger.warning(f"Retriable error (status {status_code}), retrying upload (attempt {retry}/{max_retries}): {error_msg}")
                    time.sleep(2 ** retry)  # Exponential backoff
                    # Reset iteration counter on retry
                    iteration = 0
                else:
                    # Non-retriable error
                    logger.error(f"Non-retriable HTTP error (status {status_code}): {error_msg}")
                    if hasattr(e, 'content'):
                        try:
                            error_details = json.loads(e.content.decode('utf-8'))
                            logger.error(f"Error details: {error_details}")
                        except:
                            logger.error(f"Raw error content: {e.content}")
                    return None
            except Exception as e:
                error_msg = f"Unexpected error during upload: {type(e).__name__}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return None
        
        if iteration >= max_iterations:
            logger.error(f"Upload exceeded maximum iterations ({max_iterations}) without completing")
            return None
        
        return response
    
    def _upload_thumbnail(self, video_id: str, thumbnail_path: str) -> bool:
        """Upload custom thumbnail"""
        try:
            self.service.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
            
            logger.info(f"Thumbnail uploaded for video: {video_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload thumbnail: {e}")
            return False
    
    def get_video_info(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get video information from YouTube"""
        if not self.authenticated:
            return None
        
        try:
            response = self.service.videos().list(
                part='snippet,statistics,status',
                id=video_id
            ).execute()
            
            if response['items']:
                return response['items'][0]
            return None
            
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return None
    
    def update_video_metadata(self, video_id: str, metadata: YouTubeVideoMetadata) -> bool:
        """Update video metadata"""
        if not self.authenticated:
            return False
        
        try:
            # Get current video info
            video_info = self.get_video_info(video_id)
            if not video_info:
                return False
            
            # Update snippet
            video_info['snippet']['title'] = metadata.title
            video_info['snippet']['description'] = metadata.description
            video_info['snippet']['tags'] = metadata.tags
            
            # Update video
            self.service.videos().update(
                part='snippet',
                body=video_info
            ).execute()
            
            logger.info(f"Updated metadata for video: {video_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update video metadata: {e}")
            return False
    
    def delete_video(self, video_id: str) -> bool:
        """Delete video from YouTube"""
        if not self.authenticated:
            return False
        
        try:
            self.service.videos().delete(id=video_id).execute()
            logger.info(f"Deleted video: {video_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete video: {e}")
            return False
    
    def list_my_videos(self, max_results: int = 50) -> List[Dict[str, Any]]:
        """List user's uploaded videos"""
        if not self.authenticated:
            return []
        
        try:
            response = self.service.videos().list(
                part='snippet,statistics',
                mySubscriptions=False,
                maxResults=max_results,
                order='date'
            ).execute()
            
            return response.get('items', [])
            
        except Exception as e:
            logger.error(f"Failed to list videos: {e}")
            return []
    
    def get_upload_status(self, video_id: str) -> Optional[str]:
        """Get upload status of a video"""
        video_info = self.get_video_info(video_id)
        if video_info:
            return video_info.get('status', {}).get('uploadStatus')
        return None
    
    def get_channel_info(self) -> Optional[Dict[str, Any]]:
        """Get authenticated channel information"""
        if not self.authenticated:
            if not self.authenticate():
                return None
        
        try:
            # Get channel information
            response = self.service.channels().list(
                part='snippet,contentDetails',
                mine=True
            ).execute()
            
            if response['items']:
                channel = response['items'][0]
                snippet = channel['snippet']
                
                return {
                    'channel_id': channel['id'],
                    'title': snippet['title'],
                    'description': snippet.get('description', ''),
                    'thumbnail_url': snippet['thumbnails']['default']['url'],
                    'country': snippet.get('country', ''),
                    'published_at': snippet['publishedAt']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get channel info: {e}")
            return None
    
    def schedule_video_publish(
        self, 
        video_id: str, 
        publish_at: datetime
    ) -> bool:
        """Schedule video to be published at specific time"""
        if not self.authenticated:
            return False
        
        try:
            # Get current video info
            video_info = self.get_video_info(video_id)
            if not video_info:
                return False
            
            # Update video with scheduled publish time
            video_info['status']['privacyStatus'] = 'private'
            video_info['status']['publishAt'] = publish_at.isoformat() + 'Z'
            
            # Update video
            self.service.videos().update(
                part='status',
                body=video_info
            ).execute()
            
            logger.info(f"Scheduled video {video_id} for {publish_at}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to schedule video publish: {e}")
            return False
    
    def update_video_publish_time(self, video_id: str, new_publish_time: datetime) -> bool:
        """Update video's scheduled publish time"""
        if not self.authenticated:
            return False
        
        try:
            # Get current video info
            video_info = self.get_video_info(video_id)
            if not video_info:
                return False
            
            # Update publish time
            video_info['status']['publishAt'] = new_publish_time.isoformat() + 'Z'
            
            # Update video
            self.service.videos().update(
                part='status',
                body=video_info
            ).execute()
            
            logger.info(f"Updated publish time for video {video_id} to {new_publish_time}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update video publish time: {e}")
            return False
    
    def get_quota_usage(self) -> Dict[str, Any]:
        """Get current YouTube API quota usage (approximate)"""
        # Note: YouTube API doesn't provide exact quota usage
        # This is an approximation based on operations performed
        return {
            'quota_used_estimate': 0,  # Would need to track this manually
            'quota_limit': 10000,
            'operations_performed': []
        }

class YouTubeUploadManager:
    """Manages YouTube uploads with queue and status tracking"""
    
    def __init__(self, credentials_file: str = "youtube_credentials.json", oauth_state_storage=None):
        self.uploader = YouTubeUploader(credentials_file, oauth_state_storage=oauth_state_storage)
        self.upload_queue = []
        self.upload_history = []
    
    def add_to_queue(self, video_path: str, metadata: YouTubeVideoMetadata):
        """Add video to upload queue"""
        self.upload_queue.append({
            'video_path': video_path,
            'metadata': metadata,
            'status': 'queued',
            'added_at': datetime.now()
        })
        logger.info(f"Added to upload queue: {Path(video_path).name}")
    
    def process_queue(self, progress_callback: Optional[callable] = None) -> List[YouTubeUploadResult]:
        """Process all videos in upload queue"""
        results = []
        
        for i, item in enumerate(self.upload_queue):
            if item['status'] == 'queued':
                logger.info(f"Processing upload {i+1}/{len(self.upload_queue)}: {Path(item['video_path']).name}")
                
                result = self.uploader.upload_video(
                    item['video_path'],
                    item['metadata'],
                    progress_callback
                )
                
                results.append(result)
                
                # Update queue item
                item['status'] = 'completed' if result.success else 'failed'
                item['result'] = result
                item['completed_at'] = datetime.now()
                
                # Add to history
                self.upload_history.append(item)
                
                if progress_callback:
                    progress_callback(f"Completed {i+1}/{len(self.upload_queue)}")
        
        return results
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        queued = len([item for item in self.upload_queue if item['status'] == 'queued'])
        completed = len([item for item in self.upload_queue if item['status'] == 'completed'])
        failed = len([item for item in self.upload_queue if item['status'] == 'failed'])
        
        return {
            'total': len(self.upload_queue),
            'queued': queued,
            'completed': completed,
            'failed': failed
        }
