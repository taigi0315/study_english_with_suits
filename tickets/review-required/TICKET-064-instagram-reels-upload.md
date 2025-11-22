# [TICKET-064] Instagram Reels Upload Integration

## Priority
- [ ] Critical
- [ ] High
- [x] Medium
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
- **Reach:** Instagram has 2+ billion users
- **Revenue:** IGTV ads, branded content, shopping features
- **Format Match:** Reels (15-90 seconds, 9:16) matches our short-form content
- **Risk of NOT implementing:** Missing Instagram audience, especially younger demographics

**Technical Impact:**
- New module: `langflix/platforms/instagram.py`
- Dependencies: Facebook SDK (Instagram uses Facebook Graph API)
- Estimated files: 2-3 files (uploader + tests + metadata adapter)
- Breaking changes: None (new feature)

**Effort Estimate:**
- Medium (2-3 days) - Similar to Facebook, can reuse auth

## Problem Description

Instagram Reels is a major short-form video platform. Instagram uses Facebook's Graph API, so we can leverage similar patterns to Facebook upload. However, Instagram has specific requirements:
- Requires Instagram Business/Creator account
- Must have connected Facebook Page
- Reels-specific API endpoints
- Different metadata requirements

## Proposed Solution

### Implementation Approach

1. **Instagram Graph API Integration:**
   - Use Instagram Graph API (part of Facebook Graph API)
   - Reuse Facebook OAuth flow (same auth system)
   - Implement Reels-specific upload endpoints
   - Handle Instagram-specific metadata

2. **Account Requirements:**
   - Ensure Instagram Business account
   - Connect to Facebook Page
   - Get Instagram Business Account ID
   - Use Facebook Page access token

3. **Metadata Adapter:**
   - Convert metadata to Instagram Reels format
   - Handle Instagram-specific fields (caption, hashtags, location)

### Implementation Details

#### 1. Instagram Uploader Class

```python
# langflix/platforms/instagram.py
from langflix.platforms.base import AbstractPlatformUploader, UploadResult
from langflix.platforms.facebook import FacebookUploader  # Reuse auth

class InstagramUploader(AbstractPlatformUploader):
    """Instagram Reels uploader using Instagram Graph API"""
    
    def __init__(self, facebook_uploader: FacebookUploader, instagram_business_account_id: str):
        self.facebook_uploader = facebook_uploader
        self.instagram_account_id = instagram_business_account_id
        self.graph = facebook_uploader.graph  # Reuse Facebook Graph API
        self.authenticated = False
    
    def authenticate(self) -> bool:
        """Authenticate using Facebook credentials"""
        # Reuse Facebook authentication
        return self.facebook_uploader.authenticate()
    
    def upload_reel(self, video_path: str, metadata: VideoMetadata) -> UploadResult:
        """Upload video as Instagram Reel"""
        # Use Instagram Graph API Reels endpoint
        # POST /{ig-user-id}/media
        # Then publish with POST /{ig-user-id}/media_publish
```

#### 2. Reels Upload Flow

Instagram Reels upload is a two-step process:
1. **Create Media Container:**
   - POST to `/{ig-user-id}/media` with video URL or file
   - Get container ID
2. **Publish Reel:**
   - POST to `/{ig-user-id}/media_publish` with container ID
   - Reel is published

#### 3. Metadata Conversion

```python
def convert_to_instagram_metadata(video_metadata: VideoMetadata) -> Dict:
    """Convert VideoMetadata to Instagram Reels format"""
    caption = generate_instagram_caption(video_metadata)
    
    return {
        "media_type": "REELS",
        "video_url": video_url,  # Or file upload
        "caption": caption,  # Can include hashtags
        "thumb_offset": 1000,  # Thumbnail timestamp in ms
        "location_id": None,  # Optional location
        "access_token": page_access_token
    }
```

### API Setup Requirements

**Instagram/Facebook Developer Setup:**
1. Same as Facebook (Instagram uses Facebook Graph API)
2. Create Facebook app
3. Add Instagram Basic Display product
4. Get Instagram Business Account ID
5. Connect Instagram account to Facebook Page
6. Request permissions: `instagram_basic`, `instagram_content_publish`, `pages_read_engagement`

**Required Permissions:**
- `instagram_basic` - Basic Instagram account info
- `instagram_content_publish` - Publish content to Instagram
- `pages_read_engagement` - Read page data
- `pages_manage_posts` - Manage posts (for Facebook Page connection)

**API Endpoints:**
- Create Media: `POST /{ig-user-id}/media`
- Publish: `POST /{ig-user-id}/media_publish`
- Status: `GET /{ig-user-id}/media?fields=status_code`

**Account Requirements:**
- Instagram Business or Creator account (not personal)
- Connected to Facebook Page
- Instagram Business Account ID
- Facebook Page access token

**Video Requirements:**
- Format: MP4, MOV
- Duration: 15-90 seconds (Reels)
- Resolution: 1080x1920 (9:16) recommended
- Max file size: 100MB (may vary)

## Testing Strategy

### Unit Tests
- Test authentication (reuse Facebook tests)
- Test metadata conversion
- Test media container creation
- Test publish flow
- Test error handling

### Integration Tests
- Test Reels upload to Instagram Business account
- Test metadata application (caption, hashtags)
- Test two-step upload flow
- Test status checking

### Manual Testing
- Upload test Reel to Instagram
- Verify Reel appears correctly
- Check caption and hashtags
- Verify video quality

## Files Affected

**New Files:**
- `langflix/platforms/instagram.py` - Instagram uploader implementation
- `langflix/metadata/instagram_metadata.py` - Instagram metadata adapter
- `tests/platforms/test_instagram.py` - Unit tests
- `tests/integration/test_instagram_upload.py` - Integration tests

**Modified Files:**
- `langflix/platform_manager.py` - Add Instagram to platform list
- `langflix/youtube/web_ui.py` - Add Instagram to UI

## Dependencies

- **Depends on:** 
  - TICKET-067 (Platform base class and manager)
  - TICKET-062 (Facebook) - Can reuse auth and patterns
- **Blocks:** None
- **Related to:** TICKET-061 (Epic), TICKET-062 (Facebook)

## API Documentation References

- Instagram Graph API: https://developers.facebook.com/docs/instagram-api
- Reels Publishing: https://developers.facebook.com/docs/instagram-api/guides/content-publishing
- Media Creation: https://developers.facebook.com/docs/instagram-api/reference/ig-user/media#create
- Account Setup: https://developers.facebook.com/docs/instagram-api/getting-started

## Success Criteria

- [ ] Instagram uploader class implements AbstractPlatformUploader
- [ ] Reuses Facebook authentication
- [ ] Reels upload successfully to Instagram Business account
- [ ] Two-step upload flow works (create container + publish)
- [ ] Metadata (caption, hashtags) appears correctly
- [ ] Error handling works gracefully
- [ ] Unit tests pass (80%+ coverage)
- [ ] Integration tests pass
- [ ] Documentation includes setup guide
- [ ] Account requirements documented

## Known Limitations

- **Account Type:** Requires Instagram Business/Creator account
- **Facebook Page:** Must have connected Facebook Page
- **API Approval:** Some features may require Instagram Partner Program approval
- **File Size:** Max 100MB (may vary)
- **Duration:** 15-90 seconds for Reels
- **Format:** MP4, MOV only
- **Rate Limits:** May have rate limits

## Additional Notes

- Can implement in parallel with Facebook (same auth system)
- Reuse Facebook uploader patterns
- Instagram API is part of Facebook Graph API
- Consider implementing after Facebook for code reuse
- Reels format matches our short-form content perfectly

