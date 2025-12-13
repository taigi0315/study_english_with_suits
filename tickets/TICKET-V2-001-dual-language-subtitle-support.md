# [TICKET-V2-001] Dual Language Subtitle Support

## Priority
- [x] Critical
- [ ] High
- [ ] Medium
- [ ] Low

## Type
- [x] Feature Request
- [ ] Refactoring
- [ ] Bug Fix

## Parent Epic
[EPIC-V2-001](./EPIC-V2-001-dual-language-architecture.md)

## Summary
Implement the core infrastructure for loading and managing dual language subtitles (source + target) from the new file structure.

## Background
Currently the system loads a single subtitle file and relies on LLM for translation. In V2, we have subtitles for both languages available from Netflix. This ticket creates the foundation for loading and aligning both.

## File Structure (Already Exists)
```
{media_name}.mp4
{media_name}/
├── 3_Korean.srt
├── 6_English.srt
├── 13_Spanish.srt
└── ...
```

## Requirements

### 1. Subtitle Discovery Service
```python
class SubtitleDiscoveryService:
    def discover_subtitles(self, media_path: str) -> Dict[str, List[str]]:
        """
        Given a media file path, discover all available subtitles.
        
        Returns: {"Korean": ["3_Korean.srt", "4_Korean.srt"], 
                  "English": ["5_English.srt", "6_English.srt", "7_English.srt"], 
                  ...}
        """
```

### 2. DualSubtitle Model
```python
class SubtitleEntry(BaseModel):
    start_time: str
    end_time: str
    text: str
    index: int

class DualSubtitle(BaseModel):
    source_language: str
    target_language: str
    source_entries: List[SubtitleEntry]
    target_entries: List[SubtitleEntry]
    
    def get_aligned_pair(self, index: int) -> Tuple[SubtitleEntry, SubtitleEntry]:
        """Returns aligned source and target entries"""
```

### 3. Subtitle Loading Service
```python
class DualSubtitleService:
    def load_dual_subtitles(
        self, 
        media_path: str, 
        source_lang: str,  # e.g., "English"
        target_lang: str   # e.g., "Korean"
    ) -> DualSubtitle:
        """Load both subtitle files and create aligned pairs"""
```

### 4. Subtitle Alignment
- Match subtitles by index (1:1 mapping)
- Handle cases where counts don't match (log warning, use available)
- Language variant selection (prefer first file if multiple)

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| CREATE | `langflix/core/dual_subtitle.py` | New DualSubtitle model and service |
| MODIFY | `langflix/core/models.py` | Add SubtitleEntry if not exists |
| MODIFY | `langflix/services/subtitle_service.py` | Add discovery and loading methods |
| CREATE | `tests/unit/test_dual_subtitle.py` | Unit tests for new functionality |

## Acceptance Criteria

- [ ] Can discover all available subtitle languages for a media file
- [ ] Can load source and target subtitle files
- [ ] DualSubtitle model provides aligned pairs
- [ ] Handles missing languages gracefully
- [ ] Handles multiple variants per language
- [ ] Unit tests pass

## Dependencies
- None (this is foundational)

## Blocked By
- None

## Notes
- The file structure already exists in test_media, no migration needed
- Language parsing: extract language name from filename pattern `{index}_{Language}.srt`
