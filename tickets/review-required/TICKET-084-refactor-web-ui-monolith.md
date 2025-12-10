# [TICKET-084] Refactor `web_ui.py` Monolith into Modular Routes

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [x] High (Performance issues, significant tech debt)
- [ ] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [x] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [x] Technical Debt
- [ ] Code Duplication

## Impact Assessment
**Business Impact:**
- Improves development velocity for new UI features.
- Reduces risk of regressions when modifying dashboard logic.

**Technical Impact:**
- Affects `langflix/youtube/web_ui.py` (2200+ lines).
- Requires separating Flask routes into Blueprint modules.
- Low risk of breaking changes if API contract is preserved.

**Effort Estimate:**
- Small (< 1 day)
- [x] Medium (1-3 days)
- Large (> 3 days)

## Problem Description

### Current State
**Location:** `langflix/youtube/web_ui.py`

The `VideoManagementUI` class (lines 82-2253) is a "God Class" that handles:
1. Flask Server Configuration
2. API Route Definitions (`_setup_routes` spans 1600+ lines)
3. Direct Database Access
4. File System Operations
5. YouTube API Interactions

```python
# Current problematic code (langflix/youtube/web_ui.py)
class VideoManagementUI:
    # ...
    def _setup_routes(self):
        # ... 1600 lines of route definitions ...
        @self.app.route('/')
        def index(): ...
        
        @self.app.route('/api/upload/batch/immediate', methods=['POST'])
        def batch_upload_immediate():
             # Complex logic mixed with routing
```

### Root Cause Analysis
- The file likely grew organically as the dashboard needed more features.
- Quick prototyping led to appending routes to the main class instead of creating modules.

### Evidence
- File size > 2200 lines.
- `_setup_routes` method is unmaintainable.
- Mixing of concerns (UI, API, Logic, DB).

## Proposed Solution

### Approach
Refactor `VideoManagementUI` to use Flask Blueprints and separate concerns.

1.  Create `langflix/youtube/routes/` directory.
2.  Extract routes into logical modules:
    -   `dashboard.py` (HTML serving)
    -   `api/videos.py` (Video management API)
    -   `api/upload.py` (YouTube upload API)
    -   `api/content.py` (Content creation API)
3.  Update `web_ui.py` to register these Blueprints.

### Implementation Details

```python
# langflix/youtube/routes/api/videos.py
from flask import Blueprint, jsonify
videos_bp = Blueprint('videos', __name__)

@videos_bp.route('/api/videos')
def get_videos():
    # ... logic relocated here ...
```

```python
# langflix/youtube/web_ui.py
from langflix.youtube.routes.api.videos import videos_bp

class VideoManagementUI:
    def _setup_routes(self):
        self.app.register_blueprint(videos_bp)
        # ...
```

### Benefits
- **Better maintainability:** Smaller files, clear responsibilities.
- **Enhanced testability:** Routes can be tested in isolation.
- **Scalability:** Easier to add new features without polluting the main file.

### Risks & Considerations
- Need to ensure `self` dependencies (like `video_manager`, `uploader`) are properly injected or accessible to Blueprints.

## Testing Strategy
- Verify all dashboard pages load correctly.
- Test Play, Upload, Delete actions manually.
- Run existing API tests.

## Files Affected
- `langflix/youtube/web_ui.py` - Major refactor.
- `langflix/youtube/routes/*` - New files.

## Dependencies
- None.

## References
- Flask Blueprints Documentation.
