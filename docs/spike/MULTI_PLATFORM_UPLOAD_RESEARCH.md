# Multi-Platform Video Upload - Research Spike

**Date:** 2025-01-21  
**Purpose:** Research platforms for video upload and revenue potential  
**Status:** ✅ Complete

## Executive Summary

This spike research identifies viable video platforms for multi-platform upload functionality, their monetization options, API capabilities, and implementation requirements.

## Target Platforms Analysis

### 1. YouTube ✅ (Already Implemented)

**Monetization Options:**
- Ad revenue (AdSense)
- Channel memberships
- Super Chat/Stickers
- Merchandise shelf
- YouTube Premium revenue share

**API Status:**
- ✅ Fully implemented in `langflix/youtube/uploader.py`
- API: YouTube Data API v3
- Authentication: OAuth 2.0
- SDK: `google-api-python-client`, `google-auth-oauthlib`
- Documentation: https://developers.google.com/youtube/v3

**Requirements:**
- Google Cloud Console project
- OAuth 2.0 credentials
- API quota: 10,000 units/day (default)

**Implementation Notes:**
- Already has upload, scheduling, metadata generation
- Can be used as reference pattern for other platforms

---

### 2. TikTok

**Monetization Options:**
- TikTok Creator Fund
- Live gifts
- Brand partnerships
- Creator Marketplace
- TikTok Shop (affiliate)

**API Status:**
- ⚠️ **Important:** Video Upload API deprecated (Sept 2023)
- Current API: Content Posting API (Web Video Kit)
- Authentication: OAuth 2.0
- SDK: REST API (no official Python SDK)
- Documentation: https://developers.tiktok.com/doc/web-video-kit-with-web/

**API Requirements:**
- TikTok for Developers account
- App registration
- OAuth 2.0 setup
- Video format: MP4, MOV (max 287MB for web upload)
- Duration: 15 seconds to 10 minutes
- Resolution: 1080x1920 (9:16) recommended

**Limitations:**
- Web Video Kit requires browser-based upload flow
- No direct server-to-server upload
- Requires user interaction for authentication

**Implementation Complexity:** Medium-High
- Need to handle browser-based OAuth flow
- May require iframe or popup for upload

---

### 3. Facebook

**Monetization Options:**
- In-stream ads (videos 3+ minutes)
- Fan subscriptions
- Branded content partnerships
- Facebook Stars (live)
- Instant Articles revenue

**API Status:**
- API: Facebook Graph API
- Authentication: OAuth 2.0
- SDK: `facebook-sdk` (Python)
- Documentation: https://developers.facebook.com/docs/graph-api

**API Requirements:**
- Facebook Developer account
- App creation
- Page access token (for page uploads)
- Video format: MP4, MOV, AVI
- Max file size: 1.75GB
- Duration: No strict limit

**Video Upload Methods:**
1. **Resumable Upload** (recommended for large files)
   - POST to `/videos` endpoint
   - Supports chunked upload
2. **Simple Upload** (small files < 1GB)
   - Direct POST with video file

**Implementation Complexity:** Medium
- Similar to YouTube OAuth pattern
- Supports resumable uploads (good for large files)

---

### 4. Instagram

**Monetization Options:**
- IGTV ads
- Branded content partnerships
- Shopping features
- Instagram Reels bonuses (limited)

**API Status:**
- API: Instagram Graph API
- Authentication: OAuth 2.0 (via Facebook)
- SDK: Uses Facebook SDK
- Documentation: https://developers.facebook.com/docs/instagram-api

**API Requirements:**
- Facebook Developer account (Instagram is part of Facebook)
- Instagram Business/Creator account
- Facebook Page connected to Instagram account
- Video format: MP4, MOV
- Reels: 15-90 seconds, 9:16 aspect ratio
- IGTV: 1 minute to 15 minutes

**Limitations:**
- Requires Instagram Business account
- Must have Facebook Page
- Reels API requires specific permissions
- Some features require Instagram Partner Program approval

**Implementation Complexity:** Medium
- Similar to Facebook (same auth system)
- Reels-specific requirements

---

### 5. Vimeo

**Monetization Options:**
- Vimeo On Demand (sell/rent videos)
- Subscription revenue
- Tip jar
- Live streaming monetization

**API Status:**
- API: Vimeo API v3
- Authentication: OAuth 2.0
- SDK: `pyvimeo` (unofficial), REST API
- Documentation: https://developer.vimeo.com/api

**API Requirements:**
- Vimeo Developer account
- OAuth 2.0 app
- Video format: Most formats supported
- Max file size: Depends on plan (5GB-250GB)
- No duration limit

**Implementation Complexity:** Low-Medium
- Well-documented API
- Similar OAuth pattern to YouTube

---

### 6. Dailymotion

**Monetization Options:**
- Partner program (ad revenue)
- Subscription channels
- Pay-per-view

**API Status:**
- API: Dailymotion API
- Authentication: OAuth 2.0
- SDK: REST API
- Documentation: https://www.dailymotion.com/developer

**API Requirements:**
- Dailymotion Partner account
- API key
- Video format: MP4, MOV, AVI, etc.
- Max file size: 2GB
- Duration: Up to 2 hours

**Implementation Complexity:** Medium
- Less popular, smaller community
- API documentation adequate

---

## Platform Comparison Matrix

| Platform | Monetization | API Maturity | Upload Complexity | Revenue Potential | Priority |
|----------|-------------|-------------|-------------------|------------------|----------|
| YouTube | ⭐⭐⭐⭐⭐ | ✅ Excellent | Low (done) | Very High | ✅ Done |
| TikTok | ⭐⭐⭐⭐ | ⚠️ Limited | High (browser) | High | High |
| Facebook | ⭐⭐⭐⭐ | ✅ Good | Medium | High | High |
| Instagram | ⭐⭐⭐ | ✅ Good | Medium | Medium-High | Medium |
| Vimeo | ⭐⭐⭐ | ✅ Good | Low-Medium | Medium | Low |
| Dailymotion | ⭐⭐ | ⚠️ Moderate | Medium | Low | Low |

## Recommended Implementation Order

### Phase 1: High Priority (Revenue + Reach)
1. **Facebook** - High reach, good API, similar to YouTube pattern
2. **TikTok** - High engagement, but complex implementation

### Phase 2: Medium Priority
3. **Instagram** - Good reach, shares auth with Facebook
4. **Vimeo** - Professional platform, good for long-form

### Phase 3: Low Priority
5. **Dailymotion** - Lower reach, but easy to add

## Technical Architecture Considerations

### Common Patterns Across Platforms

1. **Authentication:**
   - All use OAuth 2.0
   - Similar token refresh patterns
   - Can create abstract base class

2. **Upload Methods:**
   - Direct upload (small files)
   - Resumable/chunked upload (large files)
   - URL-based upload (some platforms)

3. **Metadata:**
   - Title, description, tags
   - Thumbnail upload
   - Privacy settings
   - Scheduling (varies by platform)

### Proposed Architecture

```
langflix/
├── platforms/
│   ├── base.py              # Abstract base class for platform uploaders
│   ├── youtube.py            # YouTube (existing, move here)
│   ├── facebook.py           # Facebook uploader
│   ├── tiktok.py             # TikTok uploader
│   ├── instagram.py          # Instagram uploader
│   └── vimeo.py              # Vimeo uploader
├── platform_manager.py       # Multi-platform upload coordinator
└── metadata/
    └── platform_metadata.py  # Platform-specific metadata adapters
```

### Key Design Decisions

1. **Abstract Base Class Pattern:**
   ```python
   class PlatformUploader(ABC):
       @abstractmethod
       def authenticate(self) -> bool: ...
       @abstractmethod
       def upload_video(self, video_path, metadata) -> UploadResult: ...
       @abstractmethod
       def get_upload_status(self, video_id) -> Status: ...
   ```

2. **Unified Metadata Interface:**
   - Convert from `VideoMetadata` to platform-specific format
   - Handle platform-specific requirements (tags, descriptions, etc.)

3. **Error Handling:**
   - Platform-specific error codes
   - Retry logic per platform
   - Graceful degradation (if one platform fails, others continue)

4. **UI Integration:**
   - Platform selection checkboxes
   - Per-platform upload status
   - Platform-specific settings (privacy, scheduling)

## API Key & SDK Requirements Summary

### TikTok
- **API Key:** OAuth App credentials from TikTok for Developers
- **SDK:** REST API (requests library)
- **Install:** `pip install requests`

### Facebook
- **API Key:** App ID + App Secret from Facebook Developers
- **SDK:** `facebook-sdk` (optional, can use requests)
- **Install:** `pip install facebook-sdk` or use `requests`

### Instagram
- **API Key:** Same as Facebook (uses Facebook Graph API)
- **SDK:** Same as Facebook
- **Install:** Same as Facebook

### Vimeo
- **API Key:** Access token from Vimeo Developer
- **SDK:** `pyvimeo` (unofficial) or REST API
- **Install:** `pip install pyvimeo` or use `requests`

### Dailymotion
- **API Key:** API key + API secret from Dailymotion Developer
- **SDK:** REST API
- **Install:** Use `requests`

## Next Steps

1. ✅ **Spike Complete** - Research done
2. ⏭️ **Create Epic Ticket** - Multi-platform upload epic
3. ⏭️ **Create Platform Tickets** - One ticket per platform
4. ⏭️ **Create UI Ticket** - Platform selection interface
5. ⏭️ **Architect Review** - Get approval for approach

## References

- YouTube API: https://developers.google.com/youtube/v3
- TikTok API: https://developers.tiktok.com/doc/web-video-kit-with-web/
- Facebook Graph API: https://developers.facebook.com/docs/graph-api
- Instagram Graph API: https://developers.facebook.com/docs/instagram-api
- Vimeo API: https://developer.vimeo.com/api
- Dailymotion API: https://www.dailymotion.com/developer

