# [TICKET-062] Facebook Video Upload Integration

## Priority
- [ ] Critical
- [x] High
- [ ] Medium
- [ ] Low

## Type
- [ ] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [x] Feature Request

## Parent Epic
TICKET-061: Multi-Platform Video Upload - Epic

## Impact Assessment

**Business Impact:**
- **Reach:** Facebook has 3+ billion users, significant audience potential
- **Revenue:** In-stream ads, fan subscriptions, branded content opportunities
- **Engagement:** Facebook video engagement rates are high
- **Risk of NOT implementing:** Missing large audience segment, single-platform dependency

**Technical Impact:**
- New module: `langflix/platforms/facebook.py`
- Dependencies: `facebook-sdk` or `requests` library
- Estimated files: 2-3 files (uploader + tests + metadata adapter)
- Breaking changes: None (new feature)

**Effort Estimate:**
- Medium (3-4 days)

## Problem Description

Currently, videos can only be uploaded to YouTube. Facebook is a major platform with significant revenue potential and user reach. We need to integrate Facebook Graph API to enable video uploads to Facebook Pages.

## Proposed Solution

### Implementation Approach

1. **Create Facebook Uploader Class:**
   - Extend `AbstractPlatformUploader` base class
   - Implement OAuth 2.0 authentication
   - Implement resumable video upload (for large files)
   - Handle Facebook-specific metadata requirements

2. **Facebook API Integration:**
   - Use Facebook Graph API v18+
   - OAuth 2.0 with Page access tokens
   - Resumable upload for files > 1GB
   - Simple upload for files < 1GB

3. **Metadata Adapter:**
   - Convert `VideoMetadata` to Facebook video format
   - Handle Facebook-specific fields (description, tags, privacy)
   - Support scheduling (if available)

### Implementation Details

#### 1. Facebook Uploader Class

```python
# langflix/platforms/facebook.py
from langflix.platforms.base import AbstractPlatformUploader, UploadResult
import facebook

class FacebookUploader(AbstractPlatformUploader):
    """Facebook video uploader using Graph API"""
    
    def __init__(self, app_id: str, app_secret: str, page_access_token: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.page_access_token = page_access_token
        self.graph = facebook.GraphAPI(page_access_token)
        self.authenticated = False
    
    def authenticate(self) -> bool:
        """Authenticate with Facebook Graph API"""
        try:
            # Validate token
            user = self.graph.get_object('me')
            self.authenticated = True
            return True
        except facebook.GraphAPIError as e:
            logger.error(f"Facebook authentication failed: {e}")
            return False
    
    def upload_video(self, video_path: str, metadata: VideoMetadata, 
                     page_id: str, privacy: str = "PUBLIC") -> UploadResult:
        """Upload video to Facebook Page"""
        # Implementation details...
```

#### 2. Resumable Upload Implementation

Facebook supports resumable uploads for large files:
1. Initialize upload session
2. Upload chunks
3. Finalize upload
4. Update metadata

#### 3. Metadata Conversion

```python
def convert_to_facebook_metadata(video_metadata: VideoMetadata) -> Dict:
    """Convert VideoMetadata to Facebook video format"""
    return {
        "title": video_metadata.expression_translation or video_metadata.expression,
        "description": generate_facebook_description(video_metadata),
        "privacy": {"value": "PUBLIC"},  # or UNLISTED, PRIVATE
        # Facebook doesn't support tags directly, use description hashtags
    }
```

### API Setup Requirements

**Facebook Developer Setup:**
1. Create Facebook Developer account
2. Create new app in Facebook Developers
3. Add "Video Upload" permission
4. Get App ID and App Secret
5. Generate Page Access Token (for page uploads)
6. Add redirect URI for OAuth

**Required Permissions:**
- `pages_manage_posts` - Post videos to pages
- `pages_read_engagement` - Read page insights
- `pages_show_list` - List user's pages

**API Endpoints:**
- Upload: `POST /{page-id}/videos`
- Resumable: `POST /{page-id}/videos` with upload session
- Status: `GET /{video-id}`

## Testing Strategy

### Unit Tests
- Test authentication flow
- Test metadata conversion
- Test upload initiation
- Test error handling

### Integration Tests
- Test actual video upload to Facebook test page
- Test resumable upload for large files
- Test metadata application
- Test privacy settings

### Manual Testing
- Upload test video to Facebook Page
- Verify metadata appears correctly
- Check video quality and format
- Test with different privacy settings

## Files Affected

**New Files:**
- `langflix/platforms/facebook.py` - Facebook uploader implementation
- `langflix/metadata/facebook_metadata.py` - Facebook metadata adapter
- `tests/platforms/test_facebook.py` - Unit tests
- `tests/integration/test_facebook_upload.py` - Integration tests

**Modified Files:**
- `langflix/platform_manager.py` - Add Facebook to platform list
- `langflix/youtube/web_ui.py` - Add Facebook to UI (if needed)

## Dependencies

- **Depends on:** TICKET-067 (Platform base class and manager)
- **Blocks:** None
- **Related to:** TICKET-061 (Epic), TICKET-063 (TikTok), TICKET-064 (Instagram)

## API Documentation References

- Facebook Graph API: https://developers.facebook.com/docs/graph-api
- Video Upload: https://developers.facebook.com/docs/graph-api/reference/video
- Resumable Upload: https://developers.facebook.com/docs/graph-api/video-uploads
- OAuth 2.0: https://developers.facebook.com/docs/facebook-login/guides/advanced/manual-flow

## Success Criteria

- [ ] Facebook uploader class implements AbstractPlatformUploader
- [ ] OAuth 2.0 authentication works
- [ ] Videos upload successfully to Facebook Pages
- [ ] Resumable upload works for large files
- [ ] Metadata (title, description) appears correctly
- [ ] Privacy settings are respected
- [ ] Error handling works gracefully
- [ ] Unit tests pass (80%+ coverage)
- [ ] Integration tests pass
- [ ] Documentation includes setup guide

## Known Limitations

- Requires Facebook Page (not personal profile)
- Page access token needs periodic refresh
- Video format requirements: MP4, MOV, AVI
- Max file size: 1.75GB (use resumable for larger)
- Some features require Page verification

## Additional Notes

- Facebook and Instagram share same auth system (can reuse for Instagram)
- Consider implementing both in parallel
- Facebook API is well-documented and stable
- Good starting point for multi-platform expansion

