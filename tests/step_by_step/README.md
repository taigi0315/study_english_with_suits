# Step-by-Step Testing Scripts for LangFlix

This directory contains independent test scripts that verify each stage of the LangFlix workflow. Each script tests one specific step and can be run independently or as part of a complete test suite.

## Overview

The testing scripts are designed to help debug the LangFlix pipeline by validating each processing stage separately. This allows you to identify exactly where the workflow fails and inspect intermediate outputs.

## Test Steps

### Step 1: Load and Analyze Subtitles
- **Script**: `test_step1_load_and_analyze.py`
- **Purpose**: Load SRT subtitle file, chunk subtitles, send to LLM for expression analysis
- **Input**: `assets/media/Suits/Suits.S01E01.720p.HDTV.x264.srt`
- **Output**: `test_output/step1/test_results.json` with expressions

### Step 2: Slice Video
- **Script**: `test_step2_slice_video.py`
- **Purpose**: Extract video clips based on expression context timing
- **Input**: Results from Step 1, video file
- **Output**: `test_output/step2/expression_XX_context_clip.mkv`

### Step 3: Add Subtitles
- **Script**: `test_step3_add_subtitles.py`
- **Purpose**: Overlay target language subtitles on context video clips
- **Input**: Results from Step 2
- **Output**: `test_output/step3/expression_XX_context_with_subs.mkv` and `.srt`

### Step 4: Extract Audio
- **Script**: `test_step4_extract_audio.py`
- **Purpose**: Extract audio for specific expression phrases
- **Input**: Results from Step 1, original video file
- **Output**: `test_output/step4/expression_XX_audio.wav`

### Step 5: Create Slides
- **Script**: `test_step5_create_slide.py`
- **Purpose**: Generate educational slides with expression text and translation
- **Input**: Results from Steps 1 and 4
- **Output**: `test_output/step5/expression_XX_slide.mkv`

### Step 6: Append Slide to Context (with Transition)
- **Script**: `test_step6_append_to_context.py`
- **Purpose**: Combine context videos with educational slides using smooth transitions
- **Input**: Results from Steps 3 and 5
- **Output**: `test_output/step6/expression_XX_full_sequence.mkv`

**Note:** The step-by-step testing system focuses on the core 6-step workflow. Final concatenation is handled by the main pipeline (`langflix.main`) which produces the complete educational video in the production environment.

## Usage

### Run Individual Steps

```bash
# Test a specific step only
python tests/step_by_step/test_step1_load_and_analyze.py

# Test multiple specific steps
python tests/step_by_step/test_step2_slice_video.py
python tests/step_by_step/test_step3_add_subtitles.py
```

### Run All Steps Sequentially

```bash
# Run complete test suite
python tests/step_by_step/run_all_steps.py
```

### Clean Up Test Outputs

```bash
# Clean all test outputs before running
python tests/step_by_step/cleanup_all.py
```

## Expected Outputs

Each step creates detailed validation reports and intermediate files:

```
test_output/
├── step1/
│   ├── test_results.json          # LLM analysis results
│   └── llm_output_*.txt           # Raw LLM responses
├── step2/
│   ├── expression_01_*.mkv        # Context video clips
│   └── test_results.json
├── step3/
│   ├── expression_01_*.mkv        # Videos with subtitles
│   ├── expression_01_*.srt        # Subtitle files
│   └── test_results.json
├── step4/
│   ├── expression_01_*.wav        # Extracted audio
│   └── test_results.json
├── step5/
│   ├── expression_01_*.mkv        # Educational slides
│   └── test_results.json
└── step6/
    ├── expression_01_*.mkv        # Combined context + slides
    └── test_results.json
```

**Complete Pipeline Output:** For the final educational video with all expressions combined, use the main pipeline:
```bash
python -m langflix.main --subtitle "file.srt"
```

## Validation

Each step includes comprehensive validation:

- **File existence and size checks**
- **Video/Audio property validation** (duration, resolution, codec)
- **Subtitle format validation**
- **Expression data structure validation**
- **Cross-step dependency verification**

## Troubleshooting

### Common Issues

1. **Missing Input Files**
   - Ensure `assets/media/Suits/Suits.S01E01.720p.HDTV.x264.srt` exists
   - Ensure `assets/media/Suits/Suits.S01E01.720p.HDTV.x264.mkv` exists

2. **API Key Issues**
   - Set `GEMINI_API_KEY` environment variable
   - Ensure API key has sufficient quota

3. **FFmpeg Issues**
   - Verify FFmpeg is installed and available in PATH
   - Check video codec compatibility

4. **Step Dependencies**
   - Steps 2-6 depend on previous steps
   - Run steps sequentially or ensure required outputs exist

### Debugging Tips

- **Check step logs**: Each step provides detailed logging
- **Inspect intermediate files**: Validate outputs between steps
- **Check test_results.json**: Contains validation details for each step
- **Run individual steps**: Isolate problematic stages

### Error Messages

- `File not found`: Verify input files exist
- `Validation failed`: Check file properties and formats
- `LLM analysis failed`: Verify API key and network connectivity
- `FFmpeg error`: Check video file compatibility and FFmpeg installation

## Configuration

Test configuration is in `test_config.py`:
- File paths for test data
- Output directories
- Validation thresholds
- Test settings (max expressions, language codes, etc.)

### Transition Settings

Smooth transitions between videos can be configured in `test_config.py`:

```python
TRANSITION_CONFIG = {
    "enabled": True,  # Enable/disable all transitions
    "context_to_slide": {
        "type": "xfade",  # Options: "xfade", "fade", "none"
        "transition": "fade",  # Transition effect type
        "duration": 0.8,  # Transition duration in seconds
        "max_duration_ratio": 0.15  # Max 15% of shorter clip
    },
    "expression_to_expression": {
        "type": "fade",  # Options: "fade", "none"
        "duration": 0.5,  # Transition duration in seconds
        "fade_in_out": True  # Apply fade-in and fade-out
    }
}
```

#### Available Transition Effects

For `context_to_slide` transitions (xfade type), you can use:
- `"fade"` - Simple crossfade (default, smooth)
- `"wipeleft"` - Wipe from left to right
- `"wiperight"` - Wipe from right to left  
- `"wipeup"` - Wipe from bottom to top
- `"wipedown"` - Wipe from top to bottom
- `"slideleft"` - Slide left (new video comes from right)
- `"slideright"` - Slide right (new video comes from left)
- `"slideup"` - Slide up (new video comes from bottom)
- `"slidedown"` - Slide down (new video comes from top)
- `"circlecrop"` - Circular crop with zoom out
- `"rectcrop"` - Rectangular crop with zoom out
- `"fadeblack"` - Fade to black between videos
- `"fadewhite"` - Fade to white between videos

To change transition settings, edit `test_config.py` and modify the `TRANSITION_CONFIG` values.

## Test Data

- **Subtitle**: Suits S01E01 episode subtitles
- **Video**: Corresponding video file
- **Max Expressions**: Limited to 2 expressions for faster testing
- **Language**: Korean (ko) translations

## Contributing

When adding new test steps:
1. Follow the naming convention: `test_stepN_description.py`
2. Include comprehensive validation
3. Save results using `save_test_results()`
4. Update this README with step description
