# LangFlix CLI Reference

## Command Line Interface Usage

### Basic Commands

```bash
# Standard processing
python -m langflix.main --subtitle "file.srt"

# With language selection
python -m langflix.main \
  --subtitle "file.srt" \
  --language-code ja \
  --language-level advanced

# Skip short videos
python -m langflix.main \
  --subtitle "file.srt" \
  --no-shorts

# Dry run (analysis only, no videos)
python -m langflix.main \
  --subtitle "file.srt" \
  --dry-run
```

### Common Workflows

**Learning Different Levels**:
```bash
# Beginner: Simple, practical expressions
python -m langflix.main --subtitle "file.srt" --language-level beginner

# Advanced: Complex idioms and phrases
python -m langflix.main --subtitle "file.srt" --language-level advanced
```

**Target Different Languages**:
```bash
# Korean
python -m langflix.main --subtitle "file.srt" --language-code ko

# Japanese
python -m langflix.main --subtitle "file.srt" --language-code ja

# Spanish
python -m langflix.main --subtitle "file.srt" --language-code es
```

**Control Processing**:
```bash
# Limit expressions
python -m langflix.main --subtitle "file.srt" --max-expressions 5

# Test mode (first chunk only)
python -m langflix.main --subtitle "file.srt" --test-mode

# Save LLM output for review
python -m langflix.main --subtitle "file.srt" --save-llm-output
```

---

## Command Line Arguments

### Required Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `--subtitle` | Path to subtitle file (.srt) | `--subtitle "path/to/file.srt"` |

### Optional Arguments

| Argument | Description | Default | Example |
|----------|-------------|---------|---------|
| `--video-dir` | Directory containing video files | `assets/media` | `--video-dir "videos/"` |
| `--output-dir` | Output directory for generated files | `output` | `--output-dir "results/"` |
| `--max-expressions` | Maximum number of expressions to process | No limit | `--max-expressions 5` |
| `--language-level` | Target language level | `intermediate` | `--language-level beginner` |
| `--language-code` | Target language code | `ko` | `--language-code ja` |
| `--dry-run` | Analyze expressions without creating video files | `False` | `--dry-run` |
| `--save-llm-output` | Save LLM responses to files for review | `False` | `--save-llm-output` |
| `--verbose` | Enable verbose logging | `False` | `--verbose` |
| `--test-mode` | Process only the first chunk for faster testing | `False` | `--test-mode` |
| `--no-shorts` | Skip creating short-format videos | `False` | `--no-shorts` |

### Language Levels

- `beginner`: Simple, practical expressions
- `intermediate`: Moderate complexity expressions
- `advanced`: Complex idioms and phrases
- `mixed`: Combination of all levels

### Language Codes

- `ko`: Korean
- `ja`: Japanese
- `zh`: Chinese
- `es`: Spanish
- `fr`: French

---

## Usage Examples

### Basic Processing

```bash
# Process a single subtitle file
python -m langflix.main --subtitle "episode.srt"

# Process with custom output directory
python -m langflix.main \
  --subtitle "episode.srt" \
  --output-dir "my_results"
```

### Testing and Debugging

```bash
# Test mode - process only first chunk
python -m langflix.main \
  --subtitle "episode.srt" \
  --test-mode

# Dry run - analysis only
python -m langflix.main \
  --subtitle "episode.srt" \
  --dry-run

# Save LLM output for debugging
python -m langflix.main \
  --subtitle "episode.srt" \
  --save-llm-output \
  --verbose
```

### Language-Specific Processing

```bash
# Korean output
python -m langflix.main \
  --subtitle "episode.srt" \
  --language-code ko \
  --language-level intermediate

# Japanese output for beginners
python -m langflix.main \
  --subtitle "episode.srt" \
  --language-code ja \
  --language-level beginner
```

### Performance Control

```bash
# Limit expressions for faster processing
python -m langflix.main \
  --subtitle "episode.srt" \
  --max-expressions 3

# Skip short video generation
python -m langflix.main \
  --subtitle "episode.srt" \
  --no-shorts
```

---

## File Organization

### Recommended Directory Structure

```
assets/
├── media/
│   └── Suits/                    # Series folder
│       ├── Suits.S01E01.720p.HDTV.x264.mkv
│       ├── Suits.S01E01.720p.HDTV.x264.srt
│       ├── Suits.S01E02.720p.HDTV.x264.mkv
│       ├── Suits.S01E02.720p.HDTV.x264.srt
│       └── ...
└── subtitles/                    # Alternative subtitle location
    └── Suits - season 1.en/
        ├── Suits - 1x01 - Pilot.720p.WEB-DL.en.srt
        └── ...
```

### File Requirements

- **Subtitle files**: `.srt` format required
- **Video files**: `.mp4`, `.mkv`, `.avi` supported formats
- **Filename matching**: Subtitle and video files must have matching names
- **Folder structure**: Series-organized folder structure recommended

---

## Output Structure

### Generated Files

```
output/
├── Suits/
    ├── S02E01/
        └── translations/
            └── ko/
                ├── videos/              # All video outputs (unified)
                │   ├── structured_video_{expression}.mkv
                │   ├── combined_structured_video_{episode}.mkv
                │   ├── short_form_{expression}.mkv
                │   └── short-form_{episode}_{batch}.mkv
                ├── subtitles/           # Subtitle files
                ├── context_videos/      # Context video clips
                └── slides/              # Educational slide videos
```

### File Types

- **Structured Videos**: Individual expression videos (context → expression → slide)
- **Combined Structured Video**: All structured videos concatenated
- **Short-form Videos**: 9:16 format for social media (vertical)
- **Context Videos**: Original video clips with subtitles
- **Slides**: Educational slide videos

---

## Error Handling

### Common Issues

1. **File not found**: Check file paths and names
2. **API key missing**: Verify `.env` file configuration
3. **Permission errors**: Check file permissions
4. **Memory issues**: Reduce `--max-expressions`

### Debugging

```bash
# Enable verbose logging
python -m langflix.main --subtitle "file.srt" --verbose

# Save LLM output for inspection
python -m langflix.main --subtitle "file.srt" --save-llm-output

# Test mode for quick debugging
python -m langflix.main --subtitle "file.srt" --test-mode
```

---

## Performance Tips

### Optimization

1. **Use test mode** for initial testing
2. **Limit expressions** for faster processing
3. **Skip short videos** if not needed
4. **Use appropriate language level** for your needs

### Resource Management

```bash
# For low-memory systems
python -m langflix.main \
  --subtitle "file.srt" \
  --max-expressions 3 \
  --no-shorts

# For testing
python -m langflix.main \
  --subtitle "file.srt" \
  --test-mode \
  --max-expressions 1
```
