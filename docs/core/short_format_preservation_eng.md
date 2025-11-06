# Short Format Video Expression Preservation

**Last Updated:** 2025-01-30  
**Related Ticket:** TICKET-029

## Overview

When creating short format (vertical 9:16) videos, LangFlix now preserves individual expression videos for copyright compliance. These videos are typically 10-60 seconds in duration, making them perfect for platforms that require <60 second content to avoid copyright restrictions.

## Why This Feature Exists

Some video content is under copyright, requiring videos shorter than 60 seconds to avoid copyright issues. The individual expression videos created during short video processing are already perfect for this use case, but they were previously deleted immediately after batch creation.

## How It Works

### Automatic Preservation

When short format videos are created:

1. **During Video Creation**: The system tracks `temp_vstack_short_{expression}.mkv` files (complete individual expression videos)
2. **After Batch Creation**: These files are automatically preserved instead of being deleted
3. **File Organization**: Preserved files are moved to `short_form_videos/expressions/` directory
4. **File Naming**: Files are renamed from `temp_vstack_short_{expression}.mkv` to `expression_{expression_name}.mkv`

### Directory Structure

```
output/Series/Episode/translations/ko/
└── short_form_videos/
    ├── short-form_{episode}_{batch_number}.mkv  # Batched videos (~120s)
    └── expressions/                              # Individual expression videos (<60s)
        ├── expression_{expression_1}.mkv
        ├── expression_{expression_2}.mkv
        └── ...
```

### File Locations

- **Batched Videos**: `short_form_videos/short-form_{episode}_{batch_number}.mkv` - ~120 seconds, multiple expressions combined
- **Individual Expression Videos**: `short_form_videos/expressions/expression_{expression_name}.mkv` - 10-60 seconds, single expression
- **Final Individual Videos**: `context_slide_combined/short_{expression}.mkv` - Also available, created before batching

## Usage

### Accessing Preserved Videos

Preserved expression videos are automatically available in the `expressions/` subdirectory:

```python
from pathlib import Path

# Get preserved expression videos
short_videos_dir = Path("output/Series/Episode/translations/ko/short_form_videos")
expressions_dir = short_videos_dir / "expressions"

# List all preserved expression videos
expression_videos = list(expressions_dir.glob("expression_*.mkv"))
```

### Video Duration

Preserved expression videos are typically:
- **Minimum**: ~10 seconds (context clip + expression)
- **Maximum**: ~60 seconds (longer context + expression repetition)
- **Average**: 15-30 seconds

All preserved videos are <60 seconds, making them suitable for copyright-compliant uploads.

## Technical Details

### Implementation

- **Tracking**: `VideoEditor.short_format_temp_files` list tracks files to preserve
- **Preservation**: `_preserve_short_format_files()` method moves files to permanent location
- **Cleanup**: Conditional cleanup with `preserve_short_format` parameter
- **Long Form**: Long form videos continue to delete all temp files (unchanged behavior)

### Cleanup Behavior

- **Short Format Videos**: Preserve expression videos when `preserve_short_format=True`
- **Long Form Videos**: Delete all temp files when `preserve_short_format=False` (default)
- **Cleanup Timing**: Preservation happens after short video batch creation, before long form cleanup

## Configuration

No configuration needed - preservation is automatic for short format videos.

## File Naming Convention

- **Original**: `temp_vstack_short_{expression_name}.mkv`
- **Preserved**: `expression_{expression_name}.mkv`

The "temp_" prefix is removed for clarity, and "vstack_short_" is simplified to "expression_" to indicate these are complete individual expression videos.

## Related Features

- **TICKET-019**: Short video duration limit (<60 seconds)
- **TICKET-025**: Multiple expressions per context for short videos
- **ADR-006**: Short video architecture

## Troubleshooting

### Files Not Preserved

If expression videos are not being preserved:

1. Check that short video generation is enabled (`short_video.enabled: true`)
2. Verify that `_create_short_videos()` is being called
3. Check logs for preservation messages: `✅ Preserved short format expression video`
4. Ensure `short_form_videos/expressions/` directory exists

### Disk Space

Preserved expression videos use additional disk space:
- Each video: ~5-20 MB (depending on duration)
- Typical episode: 10-20 expressions = ~50-400 MB additional space
- Monitor disk usage in production environments

## Examples

### Finding Copyright-Compliant Videos

```python
from pathlib import Path

def find_short_videos_for_upload(episode_path: Path):
    """Find all expression videos <60 seconds for copyright-compliant uploads"""
    expressions_dir = episode_path / "short_form_videos" / "expressions"
    
    if not expressions_dir.exists():
        return []
    
    # All videos in expressions directory are <60 seconds
    return list(expressions_dir.glob("expression_*.mkv"))
```

### Video Duration Check

```python
from langflix.media.ffmpeg_utils import get_duration_seconds

def verify_copyright_compliance(video_path: Path) -> bool:
    """Verify video is <60 seconds for copyright compliance"""
    duration = get_duration_seconds(str(video_path))
    return duration < 60.0
```

