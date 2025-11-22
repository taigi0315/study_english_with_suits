# [TICKET-067] Platform Upload Manager & Base Architecture

## Priority
- [ ] Critical
- [x] High
- [ ] Medium
- [ ] Low

## Type
- [x] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [ ] Feature Request

## Parent Epic
TICKET-061: Multi-Platform Video Upload - Epic

## Impact Assessment

**Business Impact:**
- **Foundation:** Enables all multi-platform upload features
- **Maintainability:** Unified architecture makes adding new platforms easy
- **Reliability:** Centralized error handling and retry logic
- **Risk of NOT implementing:** Cannot implement other platform tickets without this

**Technical Impact:**
- New module: `langflix/platforms/` directory
- Refactor: Move YouTube uploader to platforms directory
- Estimated files: 3-4 files (base class + manager + refactored YouTube)
- Breaking changes: Minimal (YouTube uploader moved, but interface maintained)

**Effort Estimate:**
- Medium (3-5 days)

## Problem Description

Currently, YouTube upload is implemented directly in `langflix/youtube/uploader.py`. To support multiple platforms, we need:
1. **Abstract base class** for platform uploaders (common interface)
2. **Platform manager** to coordinate multi-platform uploads
3. **Refactor YouTube** to use base class pattern
4. **Unified error handling** and retry logic
5. **Metadata adapters** for platform-specific requirements

## Proposed Solution

### Architecture Overview

```
langflix/
├── platforms/
│   ├── __init__.py
│   ├── base.py              # AbstractPlatformUploader
│   ├── youtube.py            # YouTube (refactored)
│   └── manager.py            # MultiPlatformUploadManager
└── metadata/
    └── adapters.py           # Platform metadata adapters
```

### Implementation Details

#### 1. Abstract Base Class

```python
# langflix/platforms/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass
class UploadResult:
    """Result of platform upload"""
    platform: str
    success: bool
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    error_message: Optional[str] = None
    upload_time: Optional[datetime] = None
    progress: Optional[float] = None  # 0.0 to 1.0

@dataclass
class UploadStatus:
    """Status of platform upload"""
    platform: str
    status: str  # pending, uploading, completed, failed
    progress: float  # 0.0 to 1.0
    video_id: Optional[str] = None
    error_message: Optional[str] = None

class AbstractPlatformUploader(ABC):
    """Abstract base class for platform uploaders"""
    
    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.authenticated = False
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with platform API"""
        pass
    
    @abstractmethod
    def upload_video(self, video_path: str, metadata: 'VideoMetadata', 
                     **kwargs) -> UploadResult:
        """Upload video to platform"""
        pass
    
    @abstractmethod
    def get_upload_status(self, video_id: str) -> UploadStatus:
        """Get upload status"""
        pass
    
    @abstractmethod
    def is_authenticated(self) -> bool:
        """Check if authenticated"""
        return self.authenticated
    
    def validate_video(self, video_path: str) -> bool:
        """Validate video file (can be overridden)"""
        import os
        return os.path.exists(video_path) and os.path.getsize(video_path) > 0
```

#### 2. Refactor YouTube Uploader

```python
# langflix/platforms/youtube.py
from langflix.platforms.base import AbstractPlatformUploader, UploadResult, UploadStatus
from langflix.youtube.uploader import YouTubeUploader as OriginalYouTubeUploader

class YouTubeUploader(AbstractPlatformUploader):
    """YouTube uploader using base class pattern"""
    
    def __init__(self, credentials_file: str = "youtube_credentials.json", 
                 token_file: str = "youtube_token.json", oauth_state_storage=None):
        super().__init__("youtube")
        self.original_uploader = OriginalYouTubeUploader(
            credentials_file, token_file, oauth_state_storage
        )
    
    def authenticate(self) -> bool:
        """Authenticate with YouTube"""
        try:
            result = self.original_uploader.authenticate()
            self.authenticated = result
            return result
        except Exception as e:
            logger.error(f"YouTube authentication failed: {e}")
            return False
    
    def upload_video(self, video_path: str, metadata: VideoMetadata, 
                     **kwargs) -> UploadResult:
        """Upload video to YouTube"""
        # Convert VideoMetadata to YouTubeVideoMetadata
        youtube_metadata = convert_to_youtube_metadata(metadata)
        
        # Use original uploader
        result = self.original_uploader.upload_video(
            video_path, 
            youtube_metadata,
            scheduled_time=kwargs.get('scheduled_time')
        )
        
        return UploadResult(
            platform="youtube",
            success=result.success,
            video_id=result.video_id,
            video_url=result.video_url,
            error_message=result.error_message,
            upload_time=result.upload_time
        )
    
    def get_upload_status(self, video_id: str) -> UploadStatus:
        """Get YouTube upload status"""
        # Implementation...
```

#### 3. Platform Manager

```python
# langflix/platforms/manager.py
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)

class MultiPlatformUploadManager:
    """Manages uploads to multiple platforms"""
    
    def __init__(self):
        self.uploaders: Dict[str, AbstractPlatformUploader] = {}
        self.upload_status: Dict[str, Dict[str, UploadStatus]] = {}  # video_id -> platform -> status
    
    def register_uploader(self, platform: str, uploader: AbstractPlatformUploader):
        """Register a platform uploader"""
        self.uploaders[platform] = uploader
        logger.info(f"Registered uploader for platform: {platform}")
    
    def upload_to_platforms(self, video_path: str, platforms: List[str], 
                           metadata: VideoMetadata, 
                           settings: Optional[Dict[str, Dict]] = None) -> List[UploadResult]:
        """Upload video to multiple platforms"""
        results = []
        settings = settings or {}
        
        # Filter to only registered platforms
        available_platforms = [p for p in platforms if p in self.uploaders]
        
        if not available_platforms:
            logger.warning("No available platforms for upload")
            return results
        
        # Upload to each platform (can be parallel)
        with ThreadPoolExecutor(max_workers=len(available_platforms)) as executor:
            futures = {}
            for platform in available_platforms:
                uploader = self.uploaders[platform]
                platform_settings = settings.get(platform, {})
                
                future = executor.submit(
                    self._upload_to_platform,
                    uploader, platform, video_path, metadata, platform_settings
                )
                futures[future] = platform
            
            for future in as_completed(futures):
                platform = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Upload to {platform} failed: {e}")
                    results.append(UploadResult(
                        platform=platform,
                        success=False,
                        error_message=str(e)
                    ))
        
        return results
    
    def _upload_to_platform(self, uploader: AbstractPlatformUploader, 
                          platform: str, video_path: str, metadata: VideoMetadata,
                          settings: Dict) -> UploadResult:
        """Upload to single platform (with error handling)"""
        try:
            # Check authentication
            if not uploader.is_authenticated():
                logger.warning(f"{platform} not authenticated, attempting auth...")
                if not uploader.authenticate():
                    return UploadResult(
                        platform=platform,
                        success=False,
                        error_message="Authentication failed"
                    )
            
            # Validate video
            if not uploader.validate_video(video_path):
                return UploadResult(
                    platform=platform,
                    success=False,
                    error_message="Invalid video file"
                )
            
            # Upload
            result = uploader.upload_video(video_path, metadata, **settings)
            return result
            
        except Exception as e:
            logger.error(f"Error uploading to {platform}: {e}", exc_info=True)
            return UploadResult(
                platform=platform,
                success=False,
                error_message=str(e)
            )
    
    def get_upload_status(self, video_id: str, platform: Optional[str] = None) -> Dict[str, UploadStatus]:
        """Get upload status for video"""
        if platform:
            return {platform: self.upload_status.get(video_id, {}).get(platform)}
        return self.upload_status.get(video_id, {})
    
    def list_platforms(self) -> List[str]:
        """List available platforms"""
        return list(self.uploaders.keys())
    
    def is_platform_authenticated(self, platform: str) -> bool:
        """Check if platform is authenticated"""
        if platform not in self.uploaders:
            return False
        return self.uploaders[platform].is_authenticated()
```

#### 4. Metadata Adapters

```python
# langflix/metadata/adapters.py
from langflix.core.models import VideoMetadata
from typing import Dict, Any

def convert_to_youtube_metadata(video_metadata: VideoMetadata) -> Dict[str, Any]:
    """Convert VideoMetadata to YouTube format"""
    from langflix.youtube.metadata_generator import YouTubeMetadataGenerator
    generator = YouTubeMetadataGenerator()
    return generator.generate_metadata(video_metadata)

def convert_to_facebook_metadata(video_metadata: VideoMetadata) -> Dict[str, Any]:
    """Convert VideoMetadata to Facebook format"""
    # Implementation...
    pass

def convert_to_tiktok_metadata(video_metadata: VideoMetadata) -> Dict[str, Any]:
    """Convert VideoMetadata to TikTok format"""
    # Implementation...
    pass
```

## Testing Strategy

### Unit Tests
- Test abstract base class interface
- Test platform manager registration
- Test multi-platform upload coordination
- Test error handling per platform
- Test metadata conversion

### Integration Tests
- Test YouTube uploader refactoring (should work same as before)
- Test platform manager with multiple uploaders
- Test parallel uploads
- Test error scenarios (one platform fails)

### Manual Testing
- Verify YouTube upload still works after refactoring
- Test platform manager with multiple platforms
- Test error handling

## Files Affected

**New Files:**
- `langflix/platforms/__init__.py`
- `langflix/platforms/base.py` - Abstract base class
- `langflix/platforms/youtube.py` - Refactored YouTube uploader
- `langflix/platforms/manager.py` - Platform manager
- `langflix/metadata/adapters.py` - Metadata adapters
- `tests/platforms/test_base.py` - Base class tests
- `tests/platforms/test_manager.py` - Manager tests

**Modified Files:**
- `langflix/youtube/uploader.py` - Keep original, but may extract common patterns
- `langflix/youtube/web_ui.py` - Update to use platform manager
- `langflix/main.py` - Update to use platform manager (if needed)

## Dependencies

- **Depends on:** Existing YouTube upload implementation (to refactor)
- **Blocks:** TICKET-062 (Facebook), TICKET-063 (TikTok), TICKET-064 (Instagram), TICKET-066 (UI)
- **Related to:** TICKET-061 (Epic)

## Success Criteria

- [ ] Abstract base class defined with all required methods
- [ ] YouTube uploader refactored to use base class
- [ ] YouTube upload functionality unchanged (backward compatible)
- [ ] Platform manager coordinates multi-platform uploads
- [ ] Parallel uploads work correctly
- [ ] Error handling works per platform
- [ ] Metadata adapters convert VideoMetadata correctly
- [ ] All tests pass
- [ ] Documentation updated

## Known Limitations

- YouTube refactoring must maintain backward compatibility
- Platform manager may need rate limiting per platform
- Some platforms may have different upload patterns (e.g., TikTok browser flow)

## Additional Notes

- This is the foundation for all platform integrations
- Must be completed before other platform tickets
- YouTube refactoring should be careful to not break existing functionality
- Consider adding retry logic to base class
- Consider adding upload progress callbacks

