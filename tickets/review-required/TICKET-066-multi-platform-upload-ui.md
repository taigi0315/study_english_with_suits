# [TICKET-066] Multi-Platform Upload UI & Platform Selection

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
- **User Experience:** Users can easily select platforms for upload
- **Efficiency:** One-click multi-platform upload saves time
- **Visibility:** Clear upload status per platform
- **Risk of NOT implementing:** Poor UX, users may not use multi-platform feature

**Technical Impact:**
- Modified files: `langflix/youtube/web_ui.py`, `langflix/templates/video_dashboard.html`
- New components: Platform selection UI, per-platform status indicators
- Estimated files: 2-3 files (UI + templates + JavaScript)
- Breaking changes: None (additive feature)

**Effort Estimate:**
- Medium (2-3 days)

## Problem Description

Currently, the UI only supports YouTube upload. With multi-platform support, users need to:
1. Select which platforms to upload to
2. See upload status per platform
3. Configure platform-specific settings (privacy, scheduling)
4. Handle platform-specific authentication

The UI needs to be updated to support these requirements.

## Proposed Solution

### UI Components

1. **Platform Selection:**
   - Checkboxes for each available platform
   - Default: All platforms selected
   - Visual indicators for platform status (authenticated, not authenticated)

2. **Upload Status Display:**
   - Per-platform upload status (pending, uploading, success, failed)
   - Progress indicators per platform
   - Error messages per platform

3. **Platform Settings:**
   - Platform-specific settings modal/dialog
   - Privacy settings per platform
   - Scheduling options per platform
   - Metadata customization per platform

4. **Authentication UI:**
   - Platform authentication buttons
   - Auth status indicators
   - Re-authentication flow

### Implementation Details

#### 1. Platform Selection UI

```html
<!-- langflix/templates/video_dashboard.html -->
<div class="platform-selection">
    <h3>Select Platforms</h3>
    <div class="platform-checkboxes">
        <label>
            <input type="checkbox" name="platforms" value="youtube" checked>
            <span>YouTube</span>
            <span class="auth-status" data-platform="youtube">✓ Authenticated</span>
        </label>
        <label>
            <input type="checkbox" name="platforms" value="facebook" checked>
            <span>Facebook</span>
            <span class="auth-status" data-platform="facebook">⚠ Not Authenticated</span>
            <button class="auth-btn" data-platform="facebook">Authenticate</button>
        </label>
        <label>
            <input type="checkbox" name="platforms" value="tiktok" checked>
            <span>TikTok</span>
            <span class="auth-status" data-platform="tiktok">⚠ Not Authenticated</span>
            <button class="auth-btn" data-platform="tiktok">Authenticate</button>
        </label>
        <label>
            <input type="checkbox" name="platforms" value="instagram" checked>
            <span>Instagram</span>
            <span class="auth-status" data-platform="instagram">⚠ Not Authenticated</span>
            <button class="auth-btn" data-platform="instagram">Authenticate</button>
        </label>
    </div>
    <button id="select-all-platforms">Select All</button>
    <button id="deselect-all-platforms">Deselect All</button>
</div>
```

#### 2. Upload Status Display

```html
<div class="upload-status" id="upload-status-{{ video_id }}">
    <div class="platform-status" data-platform="youtube">
        <span class="platform-name">YouTube</span>
        <span class="status-badge status-success">✓ Uploaded</span>
        <a href="https://youtube.com/watch?v=VIDEO_ID" target="_blank">View</a>
    </div>
    <div class="platform-status" data-platform="facebook">
        <span class="platform-name">Facebook</span>
        <span class="status-badge status-uploading">⏳ Uploading... 45%</span>
        <div class="progress-bar"><div class="progress" style="width: 45%"></div></div>
    </div>
    <div class="platform-status" data-platform="tiktok">
        <span class="platform-name">TikTok</span>
        <span class="status-badge status-failed">✗ Failed</span>
        <span class="error-message">Authentication required</span>
        <button class="retry-btn" data-platform="tiktok">Retry</button>
    </div>
</div>
```

#### 3. Platform Settings Modal

```html
<div class="platform-settings-modal" id="settings-modal-{{ platform }}">
    <h3>{{ platform }} Settings</h3>
    <form>
        <label>
            Privacy:
            <select name="privacy">
                <option value="public">Public</option>
                <option value="unlisted">Unlisted</option>
                <option value="private">Private</option>
            </select>
        </label>
        <label>
            Schedule:
            <input type="datetime-local" name="scheduled_time">
        </label>
        <label>
            Custom Title (optional):
            <input type="text" name="custom_title">
        </label>
        <label>
            Custom Description (optional):
            <textarea name="custom_description"></textarea>
        </label>
        <button type="submit">Save Settings</button>
    </form>
</div>
```

#### 4. Backend API Updates

```python
# langflix/youtube/web_ui.py

@self.app.route('/api/platforms/list', methods=['GET'])
def list_platforms():
    """Get list of available platforms and their auth status"""
    platforms = [
        {
            "id": "youtube",
            "name": "YouTube",
            "authenticated": self.upload_manager.uploader.authenticated,
            "enabled": True
        },
        {
            "id": "facebook",
            "name": "Facebook",
            "authenticated": self.platform_manager.is_authenticated("facebook"),
            "enabled": True
        },
        # ... other platforms
    ]
    return jsonify({"platforms": platforms})

@self.app.route('/api/platforms/upload', methods=['POST'])
def upload_to_platforms():
    """Upload video to selected platforms"""
    data = request.get_json()
    video_path = data.get('video_path')
    platforms = data.get('platforms', [])  # List of platform IDs
    settings = data.get('settings', {})  # Per-platform settings
    
    results = self.platform_manager.upload_to_platforms(
        video_path=video_path,
        platforms=platforms,
        settings=settings
    )
    
    return jsonify({"results": results})

@self.app.route('/api/platforms/<platform>/auth', methods=['POST'])
def authenticate_platform(platform):
    """Authenticate with specific platform"""
    # Platform-specific auth flow
    return jsonify({"status": "success"})
```

#### 5. JavaScript for Platform Selection

```javascript
// Handle platform selection
document.querySelectorAll('input[name="platforms"]').forEach(checkbox => {
    checkbox.addEventListener('change', function() {
        updateUploadButton();
        savePlatformPreferences();
    });
});

// Upload to selected platforms
async function uploadToSelectedPlatforms(videoPath) {
    const selectedPlatforms = Array.from(
        document.querySelectorAll('input[name="platforms"]:checked')
    ).map(cb => cb.value);
    
    if (selectedPlatforms.length === 0) {
        alert('Please select at least one platform');
        return;
    }
    
    const settings = getPlatformSettings(); // Get per-platform settings
    
    const response = await fetch('/api/platforms/upload', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            video_path: videoPath,
            platforms: selectedPlatforms,
            settings: settings
        })
    });
    
    const results = await response.json();
    updateUploadStatus(results);
}

// Update upload status display
function updateUploadStatus(results) {
    results.forEach(result => {
        const statusDiv = document.querySelector(
            `.platform-status[data-platform="${result.platform}"]`
        );
        updateStatusBadge(statusDiv, result.status, result.progress);
    });
}
```

## Testing Strategy

### Unit Tests
- Test platform list API
- Test upload API with multiple platforms
- Test platform selection persistence
- Test settings application

### Integration Tests
- Test multi-platform upload flow
- Test per-platform status updates
- Test error handling per platform
- Test authentication flows

### Manual Testing
- Select/deselect platforms
- Upload to multiple platforms
- Verify status updates
- Test platform-specific settings
- Test authentication flows
- Test error scenarios

## Files Affected

**Modified Files:**
- `langflix/youtube/web_ui.py` - Add platform APIs
- `langflix/templates/video_dashboard.html` - Add platform selection UI
- `langflix/static/js/video_dashboard.js` - Add platform selection logic (if exists)

**New Files:**
- `langflix/static/js/platform_upload.js` - Platform upload JavaScript
- `langflix/static/css/platform_ui.css` - Platform UI styles (if needed)

## Dependencies

- **Depends on:** 
  - TICKET-067 (Platform manager)
  - TICKET-062 (Facebook) - For Facebook UI
  - TICKET-063 (TikTok) - For TikTok UI
  - TICKET-064 (Instagram) - For Instagram UI
- **Blocks:** None
- **Related to:** TICKET-061 (Epic)

## Success Criteria

- [ ] Platform selection checkboxes work
- [ ] Default: All platforms selected
- [ ] Platform selection persists (localStorage or backend)
- [ ] Upload status displayed per platform
- [ ] Progress indicators work per platform
- [ ] Error messages shown per platform
- [ ] Platform authentication buttons work
- [ ] Auth status indicators update correctly
- [ ] Platform settings modal works
- [ ] Per-platform settings are applied
- [ ] Upload to multiple platforms works
- [ ] UI is responsive and user-friendly
- [ ] Tests pass

## Known Limitations

- Platform authentication may require browser redirects
- Some platforms may need separate auth flows
- Status updates may require polling or WebSocket
- Platform settings may vary significantly

## Additional Notes

- Can implement incrementally as platforms are added
- Start with basic selection, enhance with settings later
- Consider using WebSocket for real-time status updates
- Platform icons/logos would improve UX
- Consider platform-specific upload requirements in UI

