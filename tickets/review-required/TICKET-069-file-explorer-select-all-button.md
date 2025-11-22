# [TICKET-069] Add "Select All" Button to File Explorer in Content Creation Modal

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

## Impact Assessment

**Business Impact:**
- **User Experience:** Improves workflow efficiency when selecting multiple media files
- **Time Savings:** Reduces clicks when processing multiple episodes
- **Risk of NOT implementing:** Users must manually select each file, which is tedious for batch operations

**Technical Impact:**
- **Files affected:** `langflix/templates/video_dashboard.html`
- **Estimated changes:** ~20-30 lines (JavaScript + HTML)
- **Breaking changes:** None

**Effort Estimate:**
- Small (< 1 day)

## Problem Description

### Current State
**Location:** `langflix/templates/video_dashboard.html:1448-1478`

In the "Create Content" modal, users can select multiple media files using checkboxes. However, there is no "Select All" button to quickly select all available files at once.

**Current UI:**
- Individual checkboxes for each media file
- Users must click each checkbox manually
- No bulk selection option

**User Workflow:**
1. Open "Create Content" modal
2. Manually click each checkbox for desired files
3. Select languages and settings
4. Start creation

**Problem:**
- When processing many episodes (e.g., entire season), clicking each checkbox is tedious
- No quick way to select all files
- No way to quickly deselect all

### Root Cause Analysis
The file explorer was implemented with individual checkboxes but no bulk selection controls were added.

### Evidence
- User feedback requesting "select all" functionality
- Common pattern in file browsers and content management systems
- Improves UX for batch operations

## Proposed Solution

### Approach
Add "Select All" and "Deselect All" buttons to the media file selection section in the Create Content modal.

### Implementation Details

**1. Add Control Buttons**

```html
<!-- langflix/templates/video_dashboard.html -->
<div style="margin-bottom: 20px;">
    <h3 style="color: #34495e; margin-bottom: 10px;">
        Select Media File(s) - You can select multiple
    </h3>
    <div style="margin-bottom: 10px; display: flex; gap: 10px;">
        <button type="button" id="selectAllMediaBtn" 
                style="padding: 8px 16px; background: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer;">
            Select All
        </button>
        <button type="button" id="deselectAllMediaBtn" 
                style="padding: 8px 16px; background: #95a5a6; color: white; border: none; border-radius: 5px; cursor: pointer;">
            Deselect All
        </button>
    </div>
    ${mediaListHTML}
</div>
```

**2. Add JavaScript Handlers**

```javascript
// langflix/templates/video_dashboard.html
// Inside showCreateContentModal function, after creating the modal

// Select All button
const selectAllBtn = dialog.querySelector('#selectAllMediaBtn');
if (selectAllBtn) {
    selectAllBtn.addEventListener('click', function() {
        dialog.querySelectorAll('.media-checkbox').forEach(cb => {
            cb.checked = true;
        });
    });
}

// Deselect All button
const deselectAllBtn = dialog.querySelector('#deselectAllMediaBtn');
if (deselectAllBtn) {
    deselectAllBtn.addEventListener('click', function() {
        dialog.querySelectorAll('.media-checkbox').forEach(cb => {
            cb.checked = false;
        });
    });
}
```

### Alternative Approaches Considered
- **Keyboard shortcut (Ctrl+A):** Could conflict with browser default
- **Checkbox in header:** Less discoverable than buttons
- **Select All checkbox:** Similar to buttons but less clear

**Selected approach:** Buttons are most intuitive and discoverable

### Benefits
- **Improved UX:** Quick selection of all files
- **Time savings:** Reduces clicks from N to 2 (select all + start)
- **Consistency:** Matches common UI patterns
- **Accessibility:** Clear button labels

### Risks & Considerations
- None identified - simple UI enhancement

## Testing Strategy
- **Manual testing:**
  1. Open Create Content modal
  2. Click "Select All" - verify all checkboxes are checked
  3. Click "Deselect All" - verify all checkboxes are unchecked
  4. Select some files manually, then click "Select All" - verify all are selected
  5. Verify selected files are correctly passed to content creation

## Files Affected
- `langflix/templates/video_dashboard.html` - Add buttons and JavaScript handlers

## Dependencies
- None

## References
- Related UI patterns: Batch operations in video dashboard
- Similar feature: Clear selection button in video list

## Success Criteria
- [ ] "Select All" button selects all media file checkboxes
- [ ] "Deselect All" button deselects all media file checkboxes
- [ ] Buttons work correctly with existing checkbox functionality
- [ ] Selected files are correctly passed to content creation
- [ ] UI is intuitive and discoverable

