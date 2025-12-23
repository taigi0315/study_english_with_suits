# [TICKET-V2-004] File Structure Documentation & Utilities

## Priority
- [ ] Critical
- [x] High
- [ ] Medium
- [ ] Low

## Type
- [ ] Feature Request
- [x] Refactoring
- [ ] Bug Fix

## Parent Epic
[EPIC-V2-001](./EPIC-V2-001-dual-language-architecture.md)

## Summary
Document the V2 file structure convention and create utility functions for navigating it.

## Background
The V2 file structure already exists (discovered in test_media) but there's no documentation or standardized utilities for working with it.

### Current File Structure
```
{media_name}.mp4                      # Media file
{media_name}/                         # Subtitle folder (same base name)
├── {index}_{Language}.srt            # Numbered language files
├── 3_Korean.srt
├── 6_English.srt
└── ...
```

## Requirements

### 1. Documentation
- Update `docs/ARCHITECTURE.md` with file structure
- Update `docs/CONFIGURATION.md` with path conventions
- Create migration guide for V1 users

### 2. Path Utility Functions
```python
# langflix/utils/path_utils.py

def get_subtitle_folder(media_path: str) -> Path:
    """Given media file, return subtitle folder path"""
    # /path/to/video.mp4 → /path/to/video/
    
def parse_subtitle_filename(filename: str) -> Tuple[int, str]:
    """Parse '3_Korean.srt' → (3, 'Korean')"""
    
def find_media_subtitle_pairs(media_dir: str) -> List[Tuple[Path, Path]]:
    """Find all media files with corresponding subtitle folders"""
```

### 3. Validation
- Check subtitle folder exists
- Validate at least 2 languages available
- Log warning for expected but missing structure

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| MODIFY | `docs/ARCHITECTURE.md` | Add file structure section |
| MODIFY | `docs/CONFIGURATION.md` | Update path conventions |
| CREATE | `langflix/utils/path_utils.py` | Path utility functions |
| CREATE | `tests/unit/test_path_utils.py` | Unit tests |

## Acceptance Criteria

- [ ] Documentation updated with V2 file structure
- [ ] Path utility functions implemented
- [ ] Validation functions log appropriate warnings
- [ ] Unit tests pass

## Dependencies
- None

## Notes
- This ticket provides foundation utilities used by other V2 tickets
