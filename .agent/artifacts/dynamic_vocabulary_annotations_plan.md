# Dynamic Vocabulary Annotations - Implementation Plan

## Feature Goal
Display vocabulary words/slang with translations as overlays that appear **dynamically** when that word is spoken in the video, enhancing the learning experience without extra LLM costs.

## Visual Design (from mock)
```
┌─────────────────────────────────┐
│  #Movie quote threat            │  <- Catchy keywords (existing)
│  #Playful confrontation         │
│  #Code Red warning              │
├─────────────────────────────────┤
│                                 │
│  ┌──────────────────┐           │
│  │ Douchebag: 멍청이 │  <-------- Dynamic vocabulary annotation
│  └──────────────────┘           │  (appears when word is spoken)
│        [VIDEO CONTENT]          │
│                                 │
│  Hi, is this the location of    │
│  the douchebag convention?      │  <- Subtitle (existing)
│  안녕하세요, 여기 멍청이들 모임   │
├─────────────────────────────────┤
│  give someone a code red        │  <- Expression (existing)
│  누군가에게 강력한 경고나 처벌을  │
└─────────────────────────────────┘
```

## Implementation Steps

### Phase 1: Extend LLM Response (No extra API calls)

**File: `langflix/templates/expression_analysis_prompt_v6.txt`**

Add to the JSON output schema:
```json
"vocabulary_annotations": [
  {
    "word": "douchebag",
    "translation": "멍청이",
    "dialogue_index": 0,  // Index in the dialogues array
    "part_of_speech": "noun/slang"  // Optional
  }
]
```

**Rules for LLM:**
- Extract 1-3 interesting/difficult words from the dialogues
- Words that learners would benefit from seeing annotated
- Slang, idioms, or culturally-specific terms
- NOT the main expression (that's already shown separately)

### Phase 2: Update Pydantic Model

**File: `langflix/core/models.py`**

```python
class VocabularyAnnotation(BaseModel):
    word: str
    translation: str
    dialogue_index: int  # Which dialogue line this word appears in
    part_of_speech: Optional[str] = None

class ExpressionAnalysis(BaseModel):
    # ... existing fields ...
    vocabulary_annotations: Optional[List[VocabularyAnnotation]] = []
```

### Phase 3: Map Vocabulary to Timestamps

**Logic:**
1. Each dialogue line has a subtitle timestamp
2. `dialogue_index: 0` → timestamp of first dialogue line
3. Show annotation for ~3 seconds starting when that dialogue begins

```python
def get_annotation_timestamps(vocab_annot, subtitles, dialogues):
    dialogue_idx = vocab_annot.dialogue_index
    # Find the corresponding subtitle timestamp
    if dialogue_idx < len(subtitles):
        start_time = subtitles[dialogue_idx]['start_time']
        end_time = start_time + 3.0  # Show for 3 seconds
        return start_time, end_time
```

### Phase 4: FFmpeg Dynamic Overlay

**File: `langflix/core/video_editor.py`**

In `_create_short_form_video()` or `_create_long_form_video()`:

```python
# For each vocabulary annotation
for annot in vocabulary_annotations:
    start_time, end_time = get_annotation_timestamps(annot, subtitles, dialogues)
    
    # Create drawtext with enable condition
    annotation_text = f"{annot.word}: {annot.translation}"
    overlay_filter = (
        f"drawtext=text='{escape_text(annotation_text)}':"
        f"fontsize=28:fontcolor=yellow:borderw=2:bordercolor=black:"
        f"x=50:y=100:"  # Position: top-left of video
        f"enable='between(t,{start_time:.2f},{end_time:.2f})'"  # Dynamic timing!
    )
```

### Phase 5: Testing

1. Run with existing episode
2. Verify annotations appear at correct times
3. Ensure no overlap with subtitles
4. Check annotation positioning on short-form (vertical) videos

## Technical Notes

### FFmpeg `enable` Filter
The key to dynamic overlays is FFmpeg's `enable` parameter:
```
enable='between(t,START,END)'
```
Where `t` is the current playback time in seconds.

### No Extra LLM Cost
This uses the SAME initial LLM call - we're just asking for more fields in the response.
The prompt template is already ~20KB, adding vocabulary annotations adds <500 bytes.

### Fallback Behavior
If LLM doesn't return vocabulary_annotations (old cached responses), 
the video generation continues normally without them.

## Files to Modify

1. `langflix/templates/expression_analysis_prompt_v6.txt` - Add vocabulary request
2. `langflix/core/models.py` - Add VocabularyAnnotation model
3. `langflix/core/video_editor.py` - Add dynamic overlay logic
4. `langflix/utils/subtitle_utils.py` (optional) - Helper for timestamp matching

## Estimated Impact

- **LLM cost**: +0% (same API call, slightly longer response)
- **Video quality**: Significantly enhanced learning experience
- **Processing time**: +<1s per video (minimal FFmpeg overhead)
