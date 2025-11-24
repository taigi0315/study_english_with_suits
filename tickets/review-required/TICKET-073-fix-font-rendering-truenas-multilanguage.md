# [TICKET-073] Fix Font Rendering for Multi-language Support in TrueNAS/Docker Deployment

## Priority
- [x] Critical (System stability, security, data loss risk)
- [ ] High (Performance issues, significant tech debt)
- [ ] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

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
- Korean, Japanese, Chinese, Spanish, and other non-ASCII characters are rendered as broken characters (boxes) in educational slides
- Affects video quality and user experience for all non-English target languages
- Critical for international users and multi-language content generation

**Technical Impact:**
- Affects `langflix/slides/generator.py` - `create_silent_slide()` function
- Affects `langflix/core/video_editor.py` - `drawtext` filter usage
- Affects `langflix/subtitles/overlay.py` - `drawtext_fallback_single_line()` function
- Requires platform-specific font path detection and validation
- May require additional font packages in Dockerfile

**Effort Estimate:**
- Medium (1-3 days)

## Problem Description

### Current State
**Location:** 
- `langflix/slides/generator.py:90-128` - `create_silent_slide()` function
- `langflix/core/video_editor.py:920-945` - Expression text overlay
- `langflix/subtitles/overlay.py:297-333` - `drawtext_fallback_single_line()`

**Issue:**
When generating videos in TrueNAS Docker deployment, Korean (and potentially other CJK languages) characters in:
1. **Catchy keywords** (similar expressions section)
2. **Expression translation** (bottom of video)
3. **Dialogue translation** (in slides)

Are rendered as broken characters (boxes: ▢▢▢) instead of proper text.

**Main dialogue subtitles work correctly** because they use the `subtitles` filter with proper `fontsdir` configuration (fixed in TICKET-072 related work).

However, **FFmpeg `drawtext` filter** used for:
- Educational slide text overlays
- Expression text overlays on videos
- Fallback subtitle rendering

Does not properly find or use Korean/CJK fonts in Docker containers.

### Root Cause Analysis

1. **Font Path Issue:**
   - `settings.get_font_file(None)` may return macOS paths (`/System/Library/Fonts/...`) even in Linux containers
   - `font_utils.py` has platform detection but may not be used consistently
   - Docker containers have Noto Sans CJK installed at `/usr/share/fonts/opentype/noto/` but code doesn't reference it correctly

2. **FFmpeg drawtext Filter:**
   - `drawtext` filter requires `fontfile` parameter with absolute path to font file
   - Current code uses `fontfile={font_file}:` format but font_file may be wrong path
   - FFmpeg needs TTF/OTF file, not TTC (TrueType Collection) without proper handling

3. **Language-Specific Font Selection:**
   - Code doesn't pass `language_code` to `get_font_file()` in slide generation
   - No language-specific font selection for drawtext filters
   - Default font fallback doesn't support CJK characters

### Evidence

**Error Logs:**
```
langflix-api | 07:52:19 | WARNING  | Language-specific font not found for ko, falling back to default
```

**Screenshot Evidence:**
- Main dialogue subtitles: ✅ Working (uses subtitles filter)
- Catchy keywords: ❌ Broken (uses drawtext filter)
- Expression translation: ❌ Broken (uses drawtext filter)

**Code Locations:**
```python
# langflix/slides/generator.py:90-96
font_file_opt = ""
try:
    font_file = settings.get_font_file(None)  # ❌ No language_code passed
    if font_file:
        font_file_opt = f"fontfile={font_file}:"
except Exception:
    pass
```

## Proposed Solution

### Approach

1. **Update `get_font_file()` calls to pass language_code:**
   - Modify `create_silent_slide()` to accept and use `language_code`
   - Update `video_editor.py` expression overlay to use language-specific font
   - Update `drawtext_fallback_single_line()` to use language-specific font

2. **Improve Font Path Resolution:**
   - Ensure `font_utils.py` functions return Linux paths in Docker containers
   - Add validation that font file exists before using in drawtext
   - Use Noto Sans CJK for Korean/Japanese/Chinese in Linux

3. **Fix FFmpeg drawtext Font Parameter:**
   - Use absolute path to TTF file (not TTC)
   - Handle TTC files by extracting or using fontconfig
   - Add fallback to DejaVu Sans if CJK font not found

4. **Add Font Validation:**
   - Check font file exists before using in FFmpeg commands
   - Log warnings when font not found
   - Provide clear error messages

### Implementation Details

**1. Update `langflix/slides/generator.py`:**

```python
def create_silent_slide(
    text: SlideText,
    duration: float,
    output_path: Path,
    language_code: Optional[str] = None,  # Add language_code parameter
) -> Path:
    # ... existing code ...
    
    font_file_opt = ""
    try:
        # Use language-specific font
        from langflix.config.font_utils import get_font_file_for_language, get_font_name_for_ffmpeg
        
        font_path = get_font_file_for_language(language_code)
        if font_path and os.path.exists(font_path):
            # For drawtext, we need TTF file, not TTC
            # If TTC, try to find equivalent TTF or use fontconfig
            if font_path.endswith('.ttc'):
                # Try to find Noto Sans CJK TTF in Linux
                if platform.system() == "Linux":
                    noto_ttf = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
                    # For TTC, FFmpeg can use it but may need fontconfig
                    # Better: use font name instead of file path
                    font_name = get_font_name_for_ffmpeg(font_path, language_code)
                    # Use font name with fontsdir instead
                    fonts_dir = get_fonts_dir()
                    font_file_opt = f"fontfile={font_path}:"
                else:
                    font_file_opt = f"fontfile={font_path}:"
            else:
                font_file_opt = f"fontfile={font_path}:"
        else:
            logger.warning(f"Font not found for language {language_code}, using default")
    except Exception as e:
        logger.warning(f"Error getting font: {e}")
        font_file_opt = ""
```

**2. Update `langflix/core/video_editor.py`:**

```python
# Around line 920
from langflix.config.font_utils import get_font_file_for_language

# Get language-specific font
font_path = get_font_file_for_language(self.language_code)
if font_path and os.path.exists(font_path):
    drawtext_args_1['fontfile'] = font_path
else:
    logger.warning(f"Font not found for {self.language_code}, using default")
```

**3. Update `langflix/subtitles/overlay.py`:**

```python
def drawtext_fallback_single_line(
    input_video: Path, 
    text: str, 
    output_path: Path,
    language_code: Optional[str] = None  # Add parameter
) -> Path:
    # ... existing code ...
    
    try:
        from langflix.config.font_utils import get_font_file_for_language
        font_path = get_font_file_for_language(language_code)
        if font_path and os.path.exists(font_path):
            font_opt = f"fontfile={font_path}:"
        else:
            font_opt = ""
    except Exception:
        font_opt = ""
```

**4. Enhance `langflix/config/font_utils.py`:**

```python
def get_font_file_for_language(language_code: Optional[str] = None) -> str:
    """
    Get font file path for the given language or default.
    Prioritizes TTF files over TTC for FFmpeg compatibility.
    """
    # ... existing code ...
    
    # For Linux/Docker, prefer Noto Sans CJK TTF
    if platform.system() == "Linux":
        if language_code in ['ko', 'ja', 'zh']:
            # Try Noto Sans CJK TTF first
            noto_paths = [
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/nanum/NanumGothic.ttc",
            ]
            for path in noto_paths:
                if os.path.exists(path):
                    return path
    
    # ... rest of existing logic ...
```

### Alternative Approaches Considered

**Option 1: Use fontconfig and font names instead of file paths**
- Pros: More portable, handles TTC files better
- Cons: Requires fontconfig setup, may not work in all Docker images
- **Not chosen:** Current approach with file paths is more reliable

**Option 2: Convert TTC to TTF at runtime**
- Pros: FFmpeg prefers TTF
- Cons: Complex, requires additional tools, slow
- **Not chosen:** Too complex for the benefit

**Option 3: Bundle fonts in Docker image**
- Pros: Guaranteed font availability
- Cons: Increases image size, licensing concerns
- **Not chosen:** System fonts (Noto) are sufficient

### Benefits

- ✅ Korean, Japanese, Chinese characters render correctly in all video components
- ✅ Spanish and other languages with special characters work properly
- ✅ Consistent font rendering across all text overlays
- ✅ Better user experience for international users
- ✅ Proper fallback handling when fonts unavailable

### Risks & Considerations

- **Breaking changes:** May affect existing video generation if font paths change
- **Performance:** Font file existence checks add minimal overhead
- **Docker image size:** Already includes Noto Sans CJK (no additional size)
- **Compatibility:** Need to test on macOS, Linux, and Windows

## Testing Strategy

**Unit Tests:**
- Test `get_font_file_for_language()` with different language codes
- Test font path resolution in Linux vs macOS
- Test TTC vs TTF handling

**Integration Tests:**
- Generate test video with Korean text in TrueNAS Docker
- Verify catchy keywords render correctly
- Verify expression translation renders correctly
- Test with Japanese, Chinese, Spanish languages

**Manual Testing:**
1. Deploy to TrueNAS
2. Generate video with Korean target language
3. Verify all text elements render correctly:
   - Main dialogue subtitles ✅
   - Catchy keywords ✅
   - Expression translation ✅
   - Dialogue translation in slides ✅

## Files Affected

- `langflix/slides/generator.py` - Add language_code parameter, fix font path
- `langflix/core/video_editor.py` - Use language-specific font for drawtext
- `langflix/subtitles/overlay.py` - Add language_code parameter
- `langflix/config/font_utils.py` - Improve Linux font detection, TTC handling
- `langflix/settings.py` - May need to pass language_code through call chain
- `tests/unit/test_font_utils.py` - Add tests for language-specific fonts
- `tests/integration/test_slide_generation.py` - Test multi-language slide generation

## Dependencies

- Depends on: TICKET-072 (Korean font support in Dockerfile) - ✅ Already completed
- Blocks: None
- Related to: Multi-language support, TrueNAS deployment

## References

- Related documentation: `docs/core/subtitle_sync_guide_eng.md`
- Font installation: `deploy/docker/Dockerfile` (Noto Sans CJK)
- Similar issues: TICKET-072 (subtitle font fix)
- FFmpeg drawtext documentation: https://ffmpeg.org/ffmpeg-filters.html#drawtext

## Architect Review Questions

**For the architect to consider:**
1. Should we standardize on font names vs file paths for FFmpeg?
2. Is there a better approach for handling TTC files in Docker?
3. Should we add font validation as a startup check?
4. Do we need to support custom font uploads for users?

## Success Criteria

How do we know this is successfully implemented?
- [ ] Korean characters render correctly in catchy keywords
- [ ] Korean characters render correctly in expression translation
- [ ] Japanese, Chinese, Spanish characters also render correctly
- [ ] No broken character boxes (▢▢▢) in any video component
- [ ] Font fallback works when preferred font unavailable
- [ ] Tests pass for all supported languages
- [ ] Manual testing on TrueNAS confirms fix

