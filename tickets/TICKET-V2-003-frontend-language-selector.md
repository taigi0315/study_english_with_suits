# [TICKET-V2-003] Frontend Language Selector

## Priority
- [ ] Critical
- [x] High
- [ ] Medium
- [ ] Low

## Type
- [x] Feature Request
- [ ] Refactoring
- [ ] Bug Fix

## Parent Epic
[EPIC-V2-001](./EPIC-V2-001-dual-language-architecture.md)

## Summary
Add UI components for users to select source language (what they're learning) and target language (their native language) in the web interface.

## Background
Currently the system assumes a fixed source/target language pair. In V2, users should be able to select from any available languages found in the subtitle folder.

## Requirements

### 1. Language Discovery API
```
GET /api/media/{media_id}/languages
```
Response:
```json
{
  "available_languages": ["Korean", "English", "Spanish", "Japanese", ...],
  "suggested_source": "English",  // Most common source
  "suggested_target": "Korean"     // Based on user preference or default
}
```

### 2. Source Language Selector
- Dropdown showing available subtitle languages
- Label: "Learn from:" or "Source Language:"
- Default: First language or "English"

### 3. Target Language Selector
- Dropdown showing available subtitle languages
- Label: "Your Language:" or "Target Language:"
- Default: User preference or "Korean"

### 4. Validation
- Source and target cannot be the same
- Both languages must have subtitle files available

### 5. Persistence
- Save user preference to local storage
- Use as default for next session

## UI Mockup

```
┌─────────────────────────────────────────────────────────┐
│  Generate Learning Video                                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Media: The.Glory.S01E01.mp4                           │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Learn from (Source):  [English          ▼]      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Your Language (Target): [Korean         ▼]      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Available: 36 languages                               │
│                                                         │
│  [Generate Video]                                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| MODIFY | `langflix/api/routes/media.py` | Add languages endpoint |
| MODIFY | `langflix/templates/file_explorer.html` | Add language dropdowns |
| MODIFY | `langflix/static/js/file_explorer.js` | Language selector logic |
| MODIFY | `langflix/youtube/web_ui.py` | Pass language params to pipeline |

## Acceptance Criteria

- [ ] API returns available languages for a media file
- [ ] UI shows source language dropdown
- [ ] UI shows target language dropdown
- [ ] Validation prevents same source/target
- [ ] Language selection persists in local storage
- [ ] Selected languages passed to video generation pipeline

## Dependencies
- TICKET-V2-001: Dual Language Subtitle Support (for discovery)

## Notes
- Consider language name localization (e.g., "한국어" instead of "Korean")
- Handle edge case of only 1 language available
