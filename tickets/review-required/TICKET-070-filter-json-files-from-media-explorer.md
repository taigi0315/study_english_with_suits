# [TICKET-070] Filter JSON Metadata Files from Media File Explorer

## Priority
- [ ] Critical
- [ ] High
- [x] Medium
- [ ] Low

## Type
- [ ] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [x] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [ ] Feature Request

## Impact Assessment

**Business Impact:**
- **User Experience:** Cleaner file list showing only actual media files
- **Reduced Confusion:** Users won't accidentally select metadata files
- **Risk of NOT implementing:** Users may see confusing .json files in media selection

**Technical Impact:**
- **Files affected:** 
  - `langflix/youtube/web_ui.py` (API endpoint)
  - `langflix/media/media_scanner.py` (optional enhancement)
- **Estimated changes:** ~10-20 lines
- **Breaking changes:** None

**Effort Estimate:**
- Small (< 1 day)

## Problem Description

### Current State
**Location:** `langflix/youtube/web_ui.py` (media scan endpoint), `langflix/templates/video_dashboard.html` (file explorer)

The media file explorer in the "Create Content" modal shows all files in the media directory, including `.json` metadata files (e.g., `.meta.json` files created during video processing).

**Current Behavior:**
- Media scanner returns all files or includes metadata files
- File explorer displays `.json` files alongside video files
- Users can accidentally select metadata files instead of video files

**Example:**
```
Media Files:
☐ Suits.S01E01.720p.mkv
☐ Suits.S01E01.720p.meta.json  ← Should not be shown
☐ Suits.S01E02.720p.mkv
☐ short-form_batch_001.mkv
☐ short-form_batch_001.meta.json  ← Should not be shown
```

### Root Cause Analysis
The media scanning endpoint (`/api/media/scan`) returns all files or doesn't filter out non-video files properly. The file explorer displays whatever is returned from the API.

### Evidence
- User feedback: "Why are .json files showing in media selection?"
- `.meta.json` files are created during video processing (TICKET-059)
- These files are not media files and shouldn't be selectable

## Proposed Solution

### Approach
Filter out `.json` files (and other non-media files) from the media file list in the API endpoint.

### Implementation Details

**Option 1: Filter in API Endpoint (Recommended)**

```python
# langflix/youtube/web_ui.py
@self.app.route('/api/media/scan')
def scan_media_files():
    """Scan and return available media files"""
    try:
        from langflix.media.media_scanner import MediaScanner
        
        media_dir = self.media_dir
        scanner = MediaScanner(media_dir, scan_recursive=True)
        media_files = scanner.scan_media_directory()
        
        # Filter out non-video files (e.g., .json metadata files)
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.m4v', '.webm']
        filtered_files = [
            f for f in media_files 
            if any(f['video_path'].lower().endswith(ext) for ext in video_extensions)
        ]
        
        return jsonify(filtered_files)
    except Exception as e:
        logger.error(f"Error scanning media files: {e}")
        return jsonify({"error": str(e)}), 500
```

**Option 2: Filter in MediaScanner (Alternative)**

```python
# langflix/media/media_scanner.py
def scan_media_directory(self) -> List[Dict[str, Any]]:
    """Scan media directory and return list of available media files"""
    media_files = []
    
    # ... existing scan logic ...
    
    # Filter: Only return files with video extensions
    video_files = [
        f for f in media_files 
        if any(f['video_path'].lower().endswith(ext) for ext in self.SUPPORTED_VIDEO_EXTENSIONS)
    ]
    
    return video_files
```

**Selected Approach:** Option 1 (filter in API endpoint) - keeps MediaScanner generic, filtering is UI-specific

### Alternative Approaches Considered
- **Filter in frontend:** Less efficient, still loads unnecessary data
- **Filter in MediaScanner:** Changes core behavior, might affect other use cases
- **File extension whitelist:** More explicit, easier to maintain

**Selected approach:** Filter in API endpoint for UI-specific needs

### Benefits
- **Cleaner UI:** Only shows actual media files
- **Better UX:** Users can't accidentally select wrong files
- **Consistent:** Matches user expectations
- **Maintainable:** Easy to add more filters if needed

### Risks & Considerations
- Need to ensure all video extensions are covered
- Should not break existing functionality

## Testing Strategy
- **Unit tests:**
  - Test that `.json` files are filtered out
  - Test that all video extensions are included
  - Test that empty results are handled correctly
  
- **Manual testing:**
  1. Create test directory with video files and `.json` files
  2. Open Create Content modal
  3. Verify only video files are shown
  4. Verify `.json` files are not in the list

## Files Affected
- `langflix/youtube/web_ui.py` - Add filtering logic to `/api/media/scan` endpoint

## Dependencies
- None

## References
- TICKET-059: Created `.meta.json` files during video processing
- `langflix/media/media_scanner.py`: Media scanning logic

## Success Criteria
- [ ] `.json` files are not shown in media file explorer
- [ ] Only video files (`.mp4`, `.mkv`, `.avi`, `.mov`, `.m4v`, `.webm`) are shown
- [ ] Existing functionality is not broken
- [ ] All supported video extensions are included

