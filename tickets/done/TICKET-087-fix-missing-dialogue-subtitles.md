# [TICKET-087] Fix Missing Dialogue Subtitles in Output Video

## Priority
- [x] Critical (System stability, security, data loss risk)
- [ ] High (Performance issues, significant tech debt)
- [ ] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [ ] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [x] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [ ] Code Duplication

## Impact Assessment
**Business Impact:**
- **CRITICAL:** The core value proposition of the app (learning languages from video) is broken if subtitles don't display.
- Users cannot understand the dialogue without text.

**Technical Impact:**
- Affects `langflix/core/video_editor.py`.
- Two potential failure points:
  1. **Video Clip Subtitles:** `create_long_form_video` (Lines 247-286) failing to find or burn the `.srt` file.
  2. **Educational Slide Text:** `_create_educational_slide` (Lines 1726-1732) failing to render `expression_dialogue`.

**Effort Estimate:**
- [x] Small (< 1 day)
- Medium (1-3 days)
- Large (> 3 days)

## Problem Description

### Current State
**Location:** `langflix/core/video_editor.py`

User reports: "output video does not include dialougue subtitle"

**analysis 1: Video Clip Subtitles**
The code attempts to find a matching subtitle file:
```python
# Strict matching
subtitle_filename = f"expression_{expression_index+1:02d}_{safe_expression_short}.srt"
# Fallback matching
pattern = f"expression_*_{safe_expression_short}*.srt"
```
If `safe_expression_short` doesn't match exactly how the file was saved, no subtitle is found, and it logs "No subtitle file found" (Line 288), proceeding without subtitles.

**Analysis 2: Educational Slide Text**
The code cleans text aggressively:
```python
def clean_text_for_slide(text):
    # Removes ', ", :, , which handles 90% of dialogue punctuation
    cleaned = text.replace("'", "").replace('"', "").replace(":", "").replace(",", "")
    # ...
```
And then renders:
```python
if expression_dialogue:
    drawtext_filters.append(f"drawtext=text='{expression_dialogue}'...")
```
If `expression_dialogue` is missing from the data object, nothing renders.

### Root Cause Analysis
- **Likely Cause:** Filename mismatch prevents `.srt` finding for the video clip.
- **Secondary Cause:** Metadata missing `expression_dialogue` field.

### Evidence
- User report.
- "No subtitle file found" would be in logs (need to verify).

## Proposed Solution

### Approach
1.  **Relax Subtitle Matching:** logic in `create_long_form_video`.
    - If exact match fails, try fuzzy match or matching just the index `expression_{index:02d}_*.srt`.
2.  **Verify Data Flow:** Ensure `expression_dialogue` is populated in `models.py` or input JSON.
3.  **Debug Logging:** Add explicit logs for "Burning subtitles: [Yes/No]" and "Rendering Slide Text: [Text]".

### Implementation Details
```python
# Improved matching logic
subtitle_candidates = list(subtitles_dir.glob(f"expression_{expression_index+1:02d}_*.srt"))
if subtitle_candidates:
    subtitle_file = subtitle_candidates[0]
```

### Benefits
- Reliability: Subtitles appear even if expression text varies slightly in filename.
- Visibility: Logs will confirm if subtitles are being attempted.

### Risks & Considerations
- If multiple expressions have same index (unlikely in sequential processing), might pick wrong one.

## Testing Strategy
- Run pipeline with a sample video.
- Check logs for "Found subtitle file".
- Verify output video visually.

## Files Affected
- `langflix/core/video_editor.py`

## Dependencies
- None.
