# [TICKET-075] Fully Automated Content Creation & YouTube Upload Workflow

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [x] High (Performance issues, significant tech debt)
- [ ] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [ ] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [x] Technical Debt (Automation)
- [ ] Code Duplication

## Impact Assessment
**Business Impact:**
- Significantly reduces manual effort by automating the upload process immediately after content creation.
- Ensures consistent and timely uploads of generated content.
- Streamlines the workflow for creating and publishing multiple episodes.

**Technical Impact:**
- Affects `langflix/templates/video_dashboard.html` (UI) and `langflix/youtube/web_ui.py` (Backend).
- Requires modification of the content creation workflow to chain the upload task.
- Low risk of breaking changes if implemented with backward compatibility (optional parameters).

**Effort Estimate:**
- [ ] Small (< 1 day)
- [x] Medium (1-3 days)
- [ ] Large (> 3 days)

## Problem Description

### Current State
**Location:** `langflix/templates/video_dashboard.html:1500` (Modal UI) and `langflix/templates/video_dashboard.html:1623` (Frontend Logic)

Currently, the content creation workflow is completely decoupled from the upload workflow. Users must:
1.  Open "Create Content" modal and generate videos.
2.  Wait for generation to finish.
3.  Manually select the generated videos in the dashboard.
4.  Click "Batch Actions" -> "Schedule Upload" or "Upload to YouTube".

This manual step is inefficient, especially when processing multiple episodes.

```javascript
// Current startContentCreation function (simplified)
async function startContentCreation() {
    // ... gathers basic params ...
    const response = await fetch('/api/content/create', {
        method: 'POST',
        body: JSON.stringify({
            media_id: mediaId,
            video_path: videoPath,
            // ... no upload parameters ...
        })
    });
    // ...
}
```

### Root Cause Analysis
- The system was built with modularity in mind, keeping generation and upload separate.
- As the system matures, the need for an end-to-end automated pipeline has become a priority to reduce operator friction.

## Proposed Solution

### Approach
1.  **UI Update**: Modify the "Create Content" modal in `video_dashboard.html` to include an "Upload" section.
    - Checkbox: "Auto Upload to YouTube" (default: unchecked)
    - Options (visible only if checked):
        - Radio: "Immediate" vs "Scheduled"
        - Checkboxes: "Short Form" and "Long Form" (to select which output types to upload)
2.  **Frontend Logic**: Update `startContentCreation` and `startBatchContentCreation` to gather these new parameters and include them in the API request.
3.  **Backend Logic**: Update `/api/content/create` in `web_ui.py` to accept `auto_upload_config`.
4.  **Workflow Integration**: Modify the content generation workflow (likely in `web_ui.py` or a core workflow manager) to:
    - Receive the `auto_upload_config`.
    - After *each* video is successfully generated (and passed quality checks), trigger the `YouTubeUploader` or `ScheduleManager`.
    - Handle "Immediate" uploads directly.
    - Handle "Scheduled" uploads by finding the next available slot.

### Implementation Details

**UI Changes (`video_dashboard.html`):**
```html
<!-- New Upload Section in Modal -->
<div style="margin-bottom: 20px;">
    <h3 style="color: #34495e; margin-bottom: 10px;">Auto Upload</h3>
    <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; margin-bottom: 10px;">
        <input type="checkbox" id="autoUploadCheckbox" onchange="toggleUploadOptions(this.checked)" style="width: 18px; height: 18px;">
        <span style="font-weight: 500;">Auto Upload to YouTube</span>
    </label>
    
    <div id="uploadOptions" style="display: none; margin-left: 28px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
        <div style="margin-bottom: 15px;">
            <label style="display: block; margin-bottom: 5px; font-weight: 500;">Timing</label>
            <div style="display: flex; gap: 15px;">
                <label><input type="radio" name="uploadTiming" value="scheduled" checked> Scheduled</label>
                <label><input type="radio" name="uploadTiming" value="immediate"> Immediate</label>
            </div>
        </div>
        <div>
            <label style="display: block; margin-bottom: 5px; font-weight: 500;">Content Types</label>
            <div style="display: flex; gap: 15px;">
                <label><input type="checkbox" id="uploadShorts" checked> Short Form</label>
                <label><input type="checkbox" id="uploadLong" checked> Long Form</label>
            </div>
        </div>
    </div>
</div>
```

**Backend Changes (`web_ui.py`):**
```python
@self.app.route('/api/content/create', methods=['POST'])
def create_content():
    data = request.get_json()
    # ... existing params ...
    auto_upload_config = data.get('auto_upload_config')
    
    # Pass this config to the background job
    job_id = self.job_manager.start_job(
        target=self._run_content_creation_workflow,
        args=(media_id, ..., auto_upload_config)
    )
    # ...
```

### Benefits
- **Efficiency**: Eliminates manual steps between generation and upload.
- **Scalability**: Allows "set and forget" processing for large batches of episodes.
- **Consistency**: Ensures all generated content follows the same upload rules (e.g., always scheduled).

### Risks & Considerations
- **Error Handling**: If upload fails, the generation job should probably still succeed but report the upload error.
- **Quota Management**: "Immediate" uploads might hit quotas faster; "Scheduled" is safer.
- **Verification**: Users won't review the video before upload. This assumes high confidence in the generation quality.

## Testing Strategy
- **Manual Test**: Run a "Test Mode" generation with "Auto Upload" (Immediate) checked. Verify video appears on YouTube (private).
- **Unit Tests**: Test the API endpoint with and without upload config.
- **Integration Tests**: Mock the `YouTubeUploader` and verify it's called after generation in the workflow.

## Files Affected
- `langflix/templates/video_dashboard.html` - Add UI and update JS.
- `langflix/youtube/web_ui.py` - Update API and workflow logic.
- `langflix/core/workflow.py` (if applicable) - Update workflow execution.

## Dependencies
- Depends on: None
- Blocks: None
- Related to: TICKET-061 (Multi-platform upload epic)

## Success Criteria
- [ ] "Create Content" modal has the new "Auto Upload" section.
- [ ] Checking "Auto Upload" triggers the upload process after generation.
- [ ] "Immediate" and "Scheduled" options work as expected.
- [ ] Only selected content types (Short/Long) are uploaded.
- [ ] Batch processing works: 10 episodes generated -> 10 episodes uploaded automatically.
