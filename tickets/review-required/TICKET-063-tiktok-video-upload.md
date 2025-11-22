# [TICKET-063] TikTok Video Upload Integration

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
- **Reach:** TikTok has 1+ billion users, high engagement rates
- **Revenue:** Creator Fund, live gifts, brand partnerships
- **Trending:** Short-form video is trending, perfect for our content
- **Risk of NOT implementing:** Missing major short-form video platform

**Technical Impact:**
- New module: `langflix/platforms/tiktok.py`
- Dependencies: `requests` library (no official SDK)
- Estimated files: 3-4 files (uploader + browser flow + tests)
- Breaking changes: None (new feature)

**Effort Estimate:**
- Large (5-7 days) - Complex due to browser-based requirement

## Problem Description

TikTok is a major short-form video platform with high engagement. However, TikTok's API has limitations:
- **Deprecated:** Video Upload API was deprecated in Sept 2023
- **Current API:** Content Posting API (Web Video Kit) requires browser-based flow
- **Challenge:** No direct server-to-server upload

We need to implement TikTok upload using their Web Video Kit, which requires browser interaction.

## Proposed Solution

### Implementation Approach

1. **TikTok Web Video Kit Integration:**
   - Use TikTok's Web Video Kit for browser-based uploads
   - Implement OAuth 2.0 flow with browser redirect
   - Handle iframe/popup for upload flow
   - Manage upload state and callbacks

2. **Alternative Approach (If Web Video Kit insufficient):**
   - Use TikTok's Content Posting API
   - May require user interaction for each upload
   - Consider scheduled uploads vs immediate

3. **Metadata Adapter:**
   - Convert metadata to TikTok format
   - Handle TikTok-specific requirements (hashtags, descriptions)

### Implementation Details

#### 1. TikTok Uploader Class

```python
# langflix/platforms/tiktok.py
from langflix.platforms.base import AbstractPlatformUploader, UploadResult
import requests

class TikTokUploader(AbstractPlatformUploader):
    """TikTok video uploader using Content Posting API / Web Video Kit"""
    
    def __init__(self, client_key: str, client_secret: str, redirect_uri: str):
        self.client_key = client_key
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = None
        self.authenticated = False
    
    def authenticate(self) -> Dict[str, str]:
        """Get OAuth authorization URL for browser flow"""
        # Generate OAuth URL
        auth_url = f"https://www.tiktok.com/v2/auth/authorize/?client_key={self.client_key}&scope=video.upload&response_type=code&redirect_uri={self.redirect_uri}"
        return {"auth_url": auth_url, "state": generate_state()}
    
    def handle_oauth_callback(self, code: str) -> bool:
        """Exchange authorization code for access token"""
        # Implementation...
    
    def upload_video(self, video_path: str, metadata: VideoMetadata) -> UploadResult:
        """Upload video using Web Video Kit or Content Posting API"""
        # May require browser interaction
        # Implementation...
```

#### 2. Browser-Based Upload Flow

Since TikTok requires browser interaction, we need to:

1. **Option A: Iframe/Popup Flow:**
   - Open TikTok auth in iframe/popup
   - User authorizes in browser
   - Receive callback with code
   - Exchange for access token
   - Initiate upload (may still require browser)

2. **Option B: Web Video Kit:**
   - Use TikTok's Web Video Kit JavaScript SDK
   - Embed in web UI
   - Handle upload through browser
   - Receive upload status via webhooks

#### 3. Metadata Conversion

```python
def convert_to_tiktok_metadata(video_metadata: VideoMetadata) -> Dict:
    """Convert VideoMetadata to TikTok format"""
    return {
        "post_info": {
            "title": video_metadata.expression_translation or video_metadata.expression,
            "privacy_level": "PUBLIC_TO_EVERYONE",  # or other options
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
            "video_cover_timestamp_ms": 1000,  # Thumbnail time
        },
        "source_info": {
            "source": "FILE_UPLOAD",
        }
    }
```

### API Setup Requirements

**TikTok Developer Setup:**
1. Create TikTok for Developers account
2. Create application
3. Request Content Posting API access (may require approval)
4. Get Client Key and Client Secret
5. Configure redirect URI
6. Request necessary scopes: `video.upload`

**Required Scopes:**
- `video.upload` - Upload videos
- `user.info.basic` - Basic user info

**API Endpoints:**
- Auth: `https://www.tiktok.com/v2/auth/authorize/`
- Token: `https://open.tiktokapis.com/v2/oauth/token/`
- Upload: `https://open.tiktokapis.com/v2/post/publish/video/init/` (init) + upload chunks
- Status: Check upload status endpoint

**Limitations:**
- Content Posting API requires approval
- May have rate limits
- Video format: MP4, MOV (max 287MB for web)
- Duration: 15 seconds to 10 minutes
- Resolution: 1080x1920 (9:16) recommended

## Testing Strategy

### Unit Tests
- Test OAuth URL generation
- Test token exchange
- Test metadata conversion
- Test error handling

### Integration Tests
- Test OAuth flow (with test account)
- Test video upload (may require manual browser interaction)
- Test metadata application
- Test upload status checking

### Manual Testing
- Complete OAuth flow in browser
- Upload test video
- Verify video appears on TikTok
- Check metadata (title, description, hashtags)

## Files Affected

**New Files:**
- `langflix/platforms/tiktok.py` - TikTok uploader implementation
- `langflix/platforms/tiktok_browser.py` - Browser flow handler (if needed)
- `langflix/metadata/tiktok_metadata.py` - TikTok metadata adapter
- `tests/platforms/test_tiktok.py` - Unit tests
- `tests/integration/test_tiktok_upload.py` - Integration tests

**Modified Files:**
- `langflix/platform_manager.py` - Add TikTok to platform list
- `langflix/youtube/web_ui.py` - Add TikTok upload UI with browser flow
- `langflix/templates/video_dashboard.html` - Add TikTok upload button/flow

## Dependencies

- **Depends on:** TICKET-067 (Platform base class and manager)
- **Blocks:** None
- **Related to:** TICKET-061 (Epic), TICKET-062 (Facebook), TICKET-064 (Instagram)

## API Documentation References

- TikTok Content Posting API: https://developers.tiktok.com/doc/content-posting-api-overview/
- Web Video Kit: https://developers.tiktok.com/doc/web-video-kit-with-web/
- OAuth 2.0: https://developers.tiktok.com/doc/tiktok-api-v2-get-access-token/
- Migration Notice: https://developers.tiktok.com/bulletin/migration-notice-share-video-api/

## Success Criteria

- [ ] TikTok uploader class implements AbstractPlatformUploader
- [ ] OAuth 2.0 flow works (browser-based)
- [ ] Videos upload successfully to TikTok
- [ ] Metadata (title, description, hashtags) appears correctly
- [ ] Browser flow is user-friendly (iframe/popup)
- [ ] Error handling works gracefully
- [ ] Unit tests pass (80%+ coverage)
- [ ] Integration tests pass (may require manual steps)
- [ ] Documentation includes setup guide
- [ ] Web UI supports TikTok upload flow

## Known Limitations

- **Browser Requirement:** Cannot do pure server-to-server upload
- **API Approval:** Content Posting API may require TikTok approval
- **Rate Limits:** May have strict rate limits
- **File Size:** Max 287MB for web upload
- **Format:** MP4, MOV only
- **Duration:** 15 seconds to 10 minutes
- **Resolution:** 9:16 aspect ratio recommended

## Alternative Approaches Considered

1. **Web Video Kit Only:**
   - Pros: Official TikTok solution
   - Cons: Requires browser, less automation

2. **Content Posting API:**
   - Pros: More programmatic control
   - Cons: Requires approval, still may need browser

3. **Third-party Services:**
   - Pros: May simplify integration
   - Cons: Additional cost, dependency

**Selected:** Content Posting API with browser flow support

## Additional Notes

- This will be the most complex platform integration
- Consider implementing after Facebook (easier) for pattern reference
- May need to handle uploads differently than other platforms
- Browser flow integration will require UI work
- Consider scheduling vs immediate upload trade-offs

