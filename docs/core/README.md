# Core Module Documentation

This directory contains documentation for the core video processing and expression analysis modules.

## Documentation Files

### Current Architecture (2025-01-XX)

- **`structured_video_creation_eng.md`** - Complete documentation of the new structured video creation architecture
  - Structured videos (1:1 expression mapping)
  - Combined structured videos
  - Short-form video creation from structured videos
  - Configuration and API changes

- **`structured_video_creation_kor.md`** - Korean version of structured video creation documentation

### Legacy Documentation

- **`video_layout_redesign_knowledge_transfer_eng.md`** - Previous video layout redesign (TICKET-038, 039, 040)
  - ⚠️ **Note**: This describes the OLD architecture. See `structured_video_creation_eng.md` for current architecture.

- **`video_layout_redesign_knowledge_transfer_kor.md`** - Korean version of legacy documentation

- **`short_format_preservation_eng.md`** - Short format video expression preservation (TICKET-029)

- **`short_format_preservation_kor.md`** - Korean version

## Quick Reference

### For New Developers

1. **Start here**: `structured_video_creation_eng.md` - Understand the current architecture
2. **Implementation details**: See code comments in `langflix/core/video_editor.py`
3. **API usage**: See `docs/api/` directory

### For Understanding Changes

- **Recent changes (2025-01-XX)**:
  - ExpressionGroup removed → Individual expression processing
  - Long-form/short-form distinction removed → Structured videos
  - New `create_structured_video()` method
  - New `create_short_form_from_structured()` method
  - Short-form max duration configuration added

### Key Methods

- `create_structured_video()` - Create structured video for single expression
- `_create_combined_structured_video()` - Combine all structured videos
- `create_short_form_from_structured()` - Convert structured video to 9:16 format
- `_create_batched_short_videos_with_max_duration()` - Batch short-form videos with max duration

## Related Documentation

- **API Documentation**: `docs/api/`
- **Configuration**: `docs/config/`
- **Architecture Decisions**: `docs/adr/`

---

**Last Updated**: 2025-01-XX






