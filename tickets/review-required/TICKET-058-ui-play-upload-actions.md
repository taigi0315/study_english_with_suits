# [TICKET-058] Missing UI action handlers after dashboard refactor

## Priority
- [ ] Critical
- [x] High
- [ ] Medium
- [ ] Low

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
- Upload and preview buttons on the video management dashboard silently fail. Content creators cannot verify or upload assets even though jobs complete, so the dashboard is unusable for its primary purpose.

**Technical Impact:**
- The frontend throws `Unexpected end of input` and `loadVideos is not defined` errors because the new script layout removed/relocated the helper that re-renders the grid.
- The `/api/video/<path>` endpoint now receives raw absolute paths and fails after the JS code tries to fetch without encoding, so `previewVideo()` never shows anything.
- Several components (load videos, preview / upload fetch) depend on working JS; fixing this restores parsing of `/api/video` requests and keeps buttons enabled.

**Effort Estimate:** Medium (changes touch UI JS and server helper, requires manual verification)

## Problem Description
### Current State
- Frontend console reports multiple `SyntaxError: Unexpected end of input` and `ReferenceError: loadVideos is not defined` after refactoring the dashboard script.
- Clicking the play/upload icons triggers no requests (buttons stay idle) because the helper that was supposed to encode/emit `/api/video` and `/api/upload` calls was removed.
- The Flask `/api/video/<path:video_path>` route receives decoded absolute paths with unescaped slashes, so the route can't find files even when requests reach the server.

### Root Cause Analysis
- A recent restructure relocated the `loadVideos()` helper and introduced dynamic navigation calls without updating all call sites, so the script errors out before wiring button handlers.
- The `previewVideo()` function now builds `/api/video/${encodedPath}` but `encodedPath` is still the raw absolute path; Flask isn't decoding it correctly, and the server logs show path parsing errors (missing `re` imports).

### Evidence
- Browser console screenshot with recurring `Unexpected end of input` errors and inactive buttons.
- Server logs show `Error parsing path ...: cannot access local variable 're'` for every preview attempt.
- `loadVideos` function missing from latest JS bundle but still referenced from event listeners.

## Proposed Solution
### Approach
1. Reintroduce `loadVideos()` (or equivalent) near the top of the dashboard `<script>` so `DOMContentLoaded` and button helpers can safely call it without JS parse errors.
2. Update `previewVideo()` to call `encodeURIComponent(videoPath)` before building the `/api/video` URL and ensure server-side `serve_video()` decodes the path with `urllib.parse.unquote` before using `Path`.
3. Verify `uploadToYouTube()` still fires `/api/content/create` and `Upload` buttons remain enabled (watch for `ready_for_upload` gating). If not, ensure the metadata builder (`VideoFileManager`) marks ready videos correctly for new naming scheme.

### Implementation Details
- Move the `loadVideos()` definition up so it exists before any `DOMContentLoaded` handler or button click logic.
- In `langflix/youtube/web_ui.py::serve_video`, `from urllib.parse import unquote` at top, and in route do `video_path = unquote(video_path.replace('%2F','/'))` before calling `Path`.
- Update JS to encode the path once (no manual `%2F` replacement) and to show upload preview by fetching `loadVideos()` again after job completion.

### Alternatives Considered
- Reverting to previous dashboard layout (not preferred due to other fixes).
- Serving video blobs from the Flask API rather than static files (too big a change).

### Benefits
- Restores the primary dashboard actions and prevents silent failures.
- Ensures metrics about uploaded files remain accurate and belt-and-suspenders encoding avoids security issues.

### Risks & Considerations
- Need to confirm no other script errors occurred due to async load order; run `npm run lint` or similar if available.
- Must retest both preview and upload flows with the updated JS to make sure the encoded path is consumed correctly.

## Testing Strategy
- Manual test: click play button and ensure `Network` tab shows `/api/video/...` returning 200 and video plays.
- Manual test: click upload button after a job completes, verify `/api/content/create` call succeeds and button state updates.
- Regression: run relevant frontend lint/test scripts (if any) or reload the dashboard to confirm no `ReferenceError` occurs anymore.

## Files Affected
- `langflix/templates/video_dashboard.html` – reinstate helper, ensure encoded path + event wiring.
- `langflix/youtube/web_ui.py` – decode/validate incoming video paths before calling `send_file`.
- `langflix/youtube/video_manager.py` – verify `VideoMetadata` exposes `ready_for_upload` flags used by buttons.

## Dependencies
- Depends on no other tickets.

## References
- Browser console errors (tokenized in user screenshot).
- Logs showing `Error parsing path ... cannot access local variable 're'`.
*** End Patch*** 


