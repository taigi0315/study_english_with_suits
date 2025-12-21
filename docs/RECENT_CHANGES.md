# Recent Changes and Updates - LangFlix V2

**Last Updated**: December 21, 2025

## Overview

This document describes the recent major changes to LangFlix, including the integration of Gemini 1.5 Pro for subtitle translation, non-split mode for processing entire subtitle files, and the V2 dual-language subtitle workflow.

---

## 🚀 Major Changes

### 1. Gemini 1.5 Pro for Subtitle Translation

**Purpose**: Leverage Gemini 1.5 Pro's massive context window (2M tokens) for better translation quality

**Configuration** (`langflix/config/default.yaml` lines 92-102):
```yaml
llm:
  translation:
    model_name: "gemini-1.5-pro"  # Using 1.5 Pro for large context
    batch_size: -1                 # Process all subtitles in one request
```

**Benefits**:
- **Full context awareness**: The model sees the entire episode script, resulting in more natural and context-aware translations
- **Better consistency**: Character names, idioms, and recurring themes are translated consistently throughout
- **Single API call**: Instead of batch requests, the entire subtitle file is translated in one shot
- **Improved quality**: Understanding full narrative arc leads to better translation choices

**Implementation Details**:
- **Location**: `langflix/services/subtitle_translation_service.py` lines 283-291
- **Logic**: When `batch_size == -1`, all subtitle entries are processed as a single batch
- **Model**: Uses `gemini-1.5-pro` (specified in config)
- **Fallback**: If translation fails, continues with remaining batches (resilient design)

---

### 2. Non-Split Mode (Process Entire Script)

**Purpose**: Enable processing of entire subtitle files without chunking

**Configuration** (`langflix/config/default.yaml` line 62):
```yaml
llm:
  max_input_length: 0  # 0 = process entire script at once
```

**How It Works**:
- **Legacy behavior** (`max_input_length > 0`): Subtitles are chunked into segments
- **New behavior** (`max_input_length == 0`): Entire subtitle file is sent to LLM as one chunk
- **Requires**: Large context model like Gemini 1.5 Pro or Gemini 2.5 Flash

**Implementation Details**:
- **Location**: `langflix/core/subtitle_parser.py` lines 396-422
- **Logic** (lines 411-417):
  ```python
  if settings.MAX_LLM_INPUT_LENGTH > 0 and current_length + text_length > settings.MAX_LLM_INPUT_LENGTH:
      chunks.append(current_chunk)
      current_chunk = [sub]
      current_length = text_length
  else:
      current_chunk.append(sub)
  ```
  When `MAX_LLM_INPUT_LENGTH == 0`, the condition is always false, so all subtitles go into a single chunk.

**Benefits**:
- **Better expression selection**: LLM sees full episode narrative
- **No context loss**: Eliminates chunk boundary issues
- **Simpler processing**: Single LLM call instead of multiple

**Trade-offs**:
- **Higher cost**: Single large request may cost more than smaller batches
- **Longer latency**: Must wait for entire response before proceeding
- **Requires large context**: Only works with models that support long inputs

---

### 3. V2 Dual-Language Subtitle Workflow

**Purpose**: Use Netflix-style dual-language subtitles for better translation accuracy

**Structure**:
```
assets/media/
├── video_name.mkv                    # Media file
└── Subs/                             # Main subtitles folder (NEW)
    └── video_name/                   # Subtitle folder (matches video name)
        ├── 3_Korean.srt              # Indexed subtitle files
        ├── 6_English.srt
        ├── Spanish.srt               # Translated subtitle files (simple naming)
        └── Korean.srt                # Translated subtitle files (simple naming)
```

**OR Legacy Structure** (still supported):
```
assets/media/
├── video_name.mkv
└── video_name/                       # Subtitle folder directly next to media
    ├── 3_Korean.srt
    └── ...
```

**Configuration** (`langflix/config/default.yaml` lines 16-37):
```yaml
dual_language:
  enabled: true                       # V2 mode enabled
  default_source_language: "Korean"   # Language being learned
  default_target_language: "Spanish"  # User's native language
  subtitle_pattern: "{index}_{Language}.srt"
  variant_selection: "first"
  v2_template_file: "content_selection_prompt_v1.txt"
```

**Subtitle File Naming**:
1. **Netflix indexed format** (for original files): `{index}_{Language}.srt`
   - Examples: `3_Korean.srt`, `6_English.srt`, `13_Spanish.srt`
   - Index can be any positive integer
   - Language name must be capitalized (case-sensitive)

2. **Simple format** (for generated/translated files): `{Language}.srt`
   - Examples: `Korean.srt`, `English.srt`, `Spanish.srt`
   - Used for files created by subtitle translation service

**Discovery Logic** (`langflix/utils/path_utils.py`):
- `get_subtitle_folder()`: Discovers subtitle folder using both structures
- `discover_subtitle_languages()`: Finds all available subtitle languages
- `parse_subtitle_filename()`: Parses indexed filenames

**Main Pipeline Integration** (`langflix/main.py` lines 364-568):
- `_ensure_subtitles_exist()`: Ensures all required language subtitles exist
- Creates Netflix folder structure if needed
- Copies uploaded subtitles to persistent location
- Calls `SubtitleTranslationService` to translate missing languages

---

## 📝 Detailed Component Changes

### Subtitle Translation Service

**File**: `langflix/services/subtitle_translation_service.py`

**Key Changes**:
1. **Batch size configuration** (lines 45-62):
   - Loads `batch_size` from config (defaults to settings)
   - Supports `-1` for "process all at once" mode
   - Uses `gemini-1.5-pro` model by default for translation

2. **Smart folder structure detection** (lines 97-115):
   ```python
   if subtitle_folder.parent.name == "Subs":
       # New structure: Subs/{media_name}/ - media is in grandparent
       search_folder = subtitle_folder.parent.parent
   else:
       # Legacy structure: {media_name}/ - media is in parent
       search_folder = subtitle_folder.parent
   ```

3. **Output file naming** (line 159):
   ```python
   output_path = subtitle_folder / f"{target_language}.srt"
   ```
   Uses simple naming pattern for translated files

### Main Pipeline

**File**: `langflix/main.py`

**Key Changes**:
1. **Subtitle folder creation** (lines 442-480):
   - Creates Netflix folder structure in persistent location
   - Prefers creating relative to media file (NEW structure)
   - Falls back to persistent media root

2. **Subtitle copying** (lines 487-502):
   - Copies uploaded subtitle to source language file: `{source_language}.srt`
   - Updates self.subtitle_file to point to persistent copy

3. **Translation integration** (lines 548-568):
   - Calls `SubtitleTranslationService.ensure_subtitles_exist()`
   - Translates to all required languages in `target_languages`
   - Continues with available subtitles if translation fails

### Settings

**File**: `langflix/settings.py`

**Key Changes**:
1. **Subtitle translation configuration accessors** (lines 364-391):
   - `get_subtitle_translation_model()`: Returns model name for translation
   - `get_subtitle_translation_batch_size()`: Returns batch size (-1 or positive int)
   - `get_subtitle_translation_config()`: Returns full translation config section

2. **Dual language configuration accessors** (lines 118-151):
   - `is_dual_language_enabled()`: Check if V2 mode is enabled
   - `get_default_source_language()`: Get source language (being learned)
   - `get_default_target_language()`: Get target language (native)

---

## ⚠️ Known Issues and Inconsistencies

### 1. File Naming Inconsistency ⚠️ **CRITICAL**

**Problem**: Mixed naming conventions in subtitle folders

**Details**:
- **Input files** from Netflix: Indexed format `{index}_{Language}.srt` (e.g., `3_Korean.srt`)
- **Translated/Generated files**: Simple format `{Language}.srt` (e.g., `Korean.srt`)

**Example folder**:
```
Subs/episode/
├── 3_Korean.srt       ← Original Netflix file (indexed)
├── 6_English.srt      ← Original Netflix file (indexed)
├── Spanish.srt        ← Generated translation (simple)
└── French.srt         ← Generated translation (simple)
```

**Impact**:
- Code handles both patterns correctly
- May cause user confusion
- Documentation should clarify this is intentional

**Location**:
- `subtitle_translation_service.py` line 159
- `main.py` line 487

**Mitigation**:
- System correctly discovers both formats
- Simple format files get priority (inserted at index 0 in language variant lists)

### 2. Language Name Case Sensitivity ⚠️

**Problem**: Language names must be capitalized (`Korean`, not `korean`)

**Issue**: No validation or normalization in naming functions

**Risk**: Files named `3_korean.srt` (lowercase) will not be recognized

**Mitigation**: Tests verify capitalization works, but runtime doesn't enforce it

**Recommendation**: Add case normalization in `parse_subtitle_filename()`

### 3. Simple Pattern Priority Logic ⚠️

**Location**: `discover_subtitle_languages()` lines 149-157

**Current behavior**: Simple pattern files get inserted at index 0 (priority over indexed variants)

**Code**:
```python
if simple_match:
    # Insert at beginning (priority over indexed variants)
    languages[language].insert(0, str(srt_file))
```

**Question**: Should simple files really have priority over indexed originals?

**Possible intent**: Maybe simple files are preferred for user-provided subtitles?

### 4. No Folder Structure Validation

**Problem**: `_ensure_subtitles_exist()` creates folders but doesn't validate structure afterward

**Risk**: If folder creation succeeds but subsequent operations fail, inconsistent state

**Recommendation**: Add validation checks after folder creation

### 5. Media File Search Extension Hardcoding

**Location**: `subtitle_translation_service.py` lines 107-112

**Issue**: Only checks `.mp4, .mkv, .avi, .mov` - misses others like `.webm`

**Better approach**: Use common `video_extensions` set (as used in `find_media_subtitle_pairs()`)

### 6. Fragile Legacy Structure Detection

**Location**: `subtitle_translation_service.py` lines 100-105

**Detection method**: Checks if `subtitle_folder.parent.name == "Subs"`

**Issue**: Fragile - folder named "Subs" could exist elsewhere accidentally

**Better approach**: Check for media file in expected locations instead

---

## ✅ Testing Coverage

### Unit Tests

**File**: `tests/archive/test_path_utils.py`

**Coverage**:
- ✅ `parse_subtitle_filename()` - indexed format parsing
- ✅ `get_subtitle_folder()` - both structures
- ✅ `discover_subtitle_languages()` - multiple languages and variants
- ✅ `find_media_subtitle_pairs()` - bulk discovery
- ✅ Error cases (missing folders, invalid patterns)

### Subtitle Validation Tests

**File**: `tests/unit/test_subtitle_validation.py`

**Coverage**:
- ✅ File format validation
- ✅ Encoding detection (UTF-8, Latin-1, CP949)
- ✅ Multi-format support (SRT, VTT, SMI, ASS, SSA)
- ✅ Error handling with custom exceptions

---

## 🔧 Configuration Reference

### Full Translation Configuration

```yaml
llm:
  # Main LLM settings
  max_input_length: 0  # 0 = process entire script at once
  model_name: "gemini-2.5-flash"

  # Subtitle Translation Settings
  translation:
    model_name: "gemini-1.5-pro"  # Large context for full scripts
    batch_size: -1                # -1 = process all at once

dual_language:
  enabled: true
  default_source_language: "Korean"
  default_target_language: "Spanish"
  subtitle_pattern: "{index}_{Language}.srt"
  variant_selection: "first"
  v2_template_file: "content_selection_prompt_v1.txt"
```

### Environment Variable Overrides

```bash
# Override subtitle translation model
export GEMINI_MODEL="gemini-1.5-pro"

# Override batch size
export LANGFLIX_LLM_TRANSLATION_BATCH_SIZE=-1

# Override max input length
export LANGFLIX_LLM_MAX_INPUT_LENGTH=0
```

---

## 📚 Usage Examples

### Translate Subtitle Files

The subtitle translation happens automatically when running the main pipeline:

```bash
# Run pipeline - subtitles will be translated automatically
python -m langflix.main \
  --subtitle "assets/media/Suits/Subs/Suits.S01E01/English.srt" \
  --video-dir "assets/media" \
  --lang ko  # Target language (Korean)
```

**What happens**:
1. Pipeline discovers subtitle folder: `assets/media/Suits/Subs/Suits.S01E01/`
2. Checks for existing subtitles: finds `English.srt`
3. Determines required languages: `English` (source), `Korean` (target)
4. Translates `English.srt` → `Korean.srt` using Gemini 1.5 Pro in single batch
5. Saves translated subtitle as `Korean.srt` in same folder
6. Continues with V2 dual-language workflow

### Process Entire Script (Non-Split Mode)

Configuration is already set to use non-split mode by default:

```yaml
# In langflix/config/default.yaml
llm:
  max_input_length: 0  # Already set to 0
```

No CLI changes needed - it just works!

### Use Different Models

```bash
# Use Gemini Flash instead of Pro (faster, cheaper, smaller context)
export GEMINI_MODEL="gemini-2.5-flash"
python -m langflix.main --subtitle "..." --video-dir "..."

# Use Gemini Pro (large context, high quality)
export GEMINI_MODEL="gemini-1.5-pro"
python -m langflix.main --subtitle "..." --video-dir "..."
```

### Force Batch Processing

If you want to use batch processing instead of single-request mode:

```bash
# Override batch size to 75 (process 75 subtitles per request)
export LANGFLIX_LLM_TRANSLATION_BATCH_SIZE=75
python -m langflix.main --subtitle "..." --video-dir "..."
```

---

## 🚀 Recommended Workflow

### 1. Organize Media Files

```bash
# New Netflix-style structure (recommended)
assets/media/ShowName/
├── ShowName.S01E01.mkv
└── Subs/
    └── ShowName.S01E01/
        ├── 3_Korean.srt      # Original Netflix subtitle
        └── 6_English.srt     # Original Netflix subtitle

# OR Legacy structure (still supported)
assets/media/ShowName/
├── ShowName.S01E01.mkv
└── ShowName.S01E01/
    ├── 3_Korean.srt
    └── 6_English.srt
```

### 2. Run Pipeline

```bash
# V2 mode will automatically:
# - Discover available subtitle languages
# - Translate missing languages using Gemini 1.5 Pro
# - Use non-split mode (entire script context)
# - Generate educational videos

python -m langflix.main \
  --subtitle "assets/media/ShowName/Subs/ShowName.S01E01/English.srt" \
  --video-dir "assets/media" \
  --lang ko
```

### 3. Check Output

```bash
# Translated subtitles saved here:
assets/media/ShowName/Subs/ShowName.S01E01/
├── 3_Korean.srt      # Original
├── 6_English.srt     # Original
└── Korean.srt        # Translated (simple naming)

# Educational videos saved here:
output/{episode_name}/ko/
├── expressions/      # Long-form educational videos
└── shorts/          # Short-form social media videos
```

---

## 🔍 Troubleshooting

### Translation Fails

**Symptom**: Warning message "Failed to translate subtitle to {language}"

**Causes**:
1. API quota exceeded (Gemini 1.5 Pro has lower quota than Flash)
2. Subtitle file too large (exceeds model context window)
3. Network issues

**Solutions**:
1. Check API key and quota in Google Cloud Console
2. Reduce batch size: Set `batch_size: 75` instead of `-1`
3. Use smaller model: `gemini-2.5-flash` instead of `gemini-1.5-pro`
4. Check network connectivity

### Subtitles Not Discovered

**Symptom**: Error "No subtitle folder found for: {path}"

**Causes**:
1. Folder structure doesn't match expected format
2. Subtitle files not named correctly
3. Media path is temporary location

**Solutions**:
1. Verify folder structure matches one of the two supported formats
2. Check subtitle file naming:
   - Indexed: `{number}_{Language}.srt` (e.g., `3_Korean.srt`)
   - Simple: `{Language}.srt` (e.g., `Korean.srt`)
3. Ensure media files are in persistent location (not `/tmp`)

### Mixed Naming Patterns

**Symptom**: Folder contains both `3_Korean.srt` and `Korean.srt`

**This is normal**: The system intentionally uses different naming for:
- **Original Netflix files**: Indexed format (`3_Korean.srt`)
- **Translated files**: Simple format (`Korean.srt`)

Both are discovered and simple format gets priority in language variant selection.

---

## 📈 Performance Considerations

### API Costs

**Gemini 1.5 Pro** (translation):
- **Input**: ~$3.50 per 1M tokens
- **Output**: ~$10.50 per 1M tokens
- **Typical subtitle file**: ~50k tokens (entire episode)
- **Cost per episode**: ~$0.18-0.50

**Gemini 2.5 Flash** (expression analysis):
- **Input**: ~$0.075 per 1M tokens
- **Output**: ~$0.30 per 1M tokens
- **Typical processing**: ~100k tokens (full episode)
- **Cost per episode**: ~$0.03-0.10

### Processing Time

**With Gemini 1.5 Pro** (batch_size=-1):
- Single API call for entire subtitle file
- **Time**: ~30-60 seconds per language
- **Advantage**: Faster than multiple batches

**With batch processing** (batch_size=75):
- Multiple API calls (e.g., 10 batches for 750 subtitles)
- **Time**: ~2-5 minutes per language
- **Advantage**: More resilient, incremental progress saving

### Recommendations

**For production** (quality over speed):
```yaml
llm:
  translation:
    model_name: "gemini-1.5-pro"
    batch_size: -1  # Single request, best quality
```

**For development** (speed over cost):
```yaml
llm:
  translation:
    model_name: "gemini-2.5-flash"
    batch_size: 75  # Smaller batches, faster iteration
```

**For large files** (>1000 subtitles):
```yaml
llm:
  translation:
    model_name: "gemini-1.5-pro"
    batch_size: 100  # Balance quality and reliability
```

---

## 🎯 Summary

### What Changed

1. **Gemini 1.5 Pro Integration**: Better translation quality with full context awareness
2. **Non-Split Mode**: Process entire subtitle files without chunking
3. **V2 Dual-Language Workflow**: Netflix-style folder structure and subtitle discovery
4. **Flexible File Naming**: Support both indexed and simple naming patterns
5. **Automatic Translation**: Missing subtitle languages are translated automatically

### What Works Well

- ✅ Robust folder structure detection (both new and legacy)
- ✅ Flexible file naming support
- ✅ Comprehensive error handling
- ✅ Well-tested implementation
- ✅ Configuration-driven design

### What Needs Improvement

- ⚠️ File naming inconsistency (indexed vs simple patterns)
- ⚠️ No case normalization for language names
- ⚠️ Fragile legacy structure detection
- ⚠️ Limited extension support in media file search
- ⚠️ No folder structure validation after creation

---

## 📝 Next Steps

### Short Term
1. Add case normalization for language names
2. Improve folder structure validation
3. Add more media file extensions
4. Document file naming rationale

### Long Term
1. Add folder migration utility (legacy → new structure)
2. Implement subtitle folder cleanup/management
3. Add metadata file for subtitle variants
4. Create validation tool for folder structure integrity
