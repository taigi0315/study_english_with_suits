# [TICKET-081] Refactor Frontend Monolith (video_dashboard.html)

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
- **Development Speed**: Frontend changes are slow and risky because HTML/CSS/JS are tangled.
- **Bugs**: Hard to find DOM element references due to lack of structure.
- **UI/UX**: Hard to implement consistent design systems when CSS is inline.

**Technical Impact:**
- **Module**: Frontend (`templates/`)
- **Files**: `langflix/templates/video_dashboard.html` (2400 lines)
- **Effort**: Medium (2-3 days)

## Problem Description

### Current State
**Location:** `langflix/templates/video_dashboard.html`

The file `video_dashboard.html` is 2400+ lines long. It contains:
1.  Jinja2 templating logic.
2.  Massive blocks of inline CSS (style tags and `style=""` attributes).
3.  1000+ lines of inline JavaScript within `<script>` tags.

```html
<!-- video_dashboard.html -->
<style>
    /* 500 lines of CSS */
</style>

<div style="display: flex; ...">...</div>

<script>
    // 1000 lines of complex async logic, API calls, DOM manipulation
    async function startContentCreation() { ... }
    // ...
</script>
```

### Root Cause Analysis
- **Prototyping**: Started as a simple Flask template and grew organically.
- **Lack of Build Step**: No Webpack/Vite pipeline, so everything was kept in one file for simplicity of deployment (no static file serving configuration needed initially).

## Proposed Solution

### Approach
1.  **Extract CSS**: Move all `<style>` block content to `langflix/static/css/dashboard.css`. Replace inline styles with classes where possible (Tailwind or semantic CSS).
2.  **Extract JS**: Move all `<script>` block content to `langflix/static/js/dashboard.js`.
3.  **Use ES Modules**: Use `<script type="module">` to allow splitting JS into smaller files (e.g., `api.js`, `ui.js`, `utils.js`) without a bundler.

### Implementation Details

**File Structure:**
```
langflix/
  static/
    css/
      dashboard.css
    js/
      dashboard/
        main.js
        api.js
        ui.js
        types.js
  templates/
    video_dashboard.html
```

**video_dashboard.html:**
```html
{% extends "base.html" %}

{% block styles %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/dashboard.css') }}">
{% endblock %}

{% block content %}
<!-- specialized markup only -->
<div id="app-container" class="dashboard-container">
   <!-- ... -->
</div>
{% endblock %}

{% block scripts %}
<script type="module" src="{{ url_for('static', filename='js/dashboard/main.js') }}"></script>
{% endblock %}
```

### Benefits
- **Caching**: Browser caches JS/CSS files.
- **IDE Support**: Full linting, formatting, and autocomplete for JS/CSS files.
- **Maintainability**: Clear separation of concerns.

## Risks & Considerations
- **Jinja2 Variables**: Inline JS often uses `{{ variable }}`. This isn't possible in external `.js` files.
    - **Mitigation**: Pass server-side variables via `data-attributes` on a root element, or a small logical `<script>` block that defines a global `window.APP_CONFIG` object before loading the main script.

## Testing Strategy
- Manual verification of all UI features (Creation, Upload, Filtering).
- No automated UI tests exist currently; good time to add basic Cypress/Playwright test?

## Files Affected
- `langflix/templates/video_dashboard.html`
- `langflix/static/css/dashboard.css` (New)
- `langflix/static/js/dashboard/*.js` (New)

## Success Criteria
- [ ] `video_dashboard.html` reduced to < 500 lines.
- [ ] No inline JavaScript logic (limit to config injection).
- [ ] No large `<style>` blocks.
