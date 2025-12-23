# Pipeline Architecture Flow

## Data Flow Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    INPUT: Subtitle Files                          │
├──────────────────────────────────────────────────────────────────┤
│  Source (English):        Target (Korean):                        │
│  [0] [00:00:49,460 -->   [0] [00:00:49,460 -->                   │
│       00:00:50,527]           00:00:50,527]                       │
│       Gerald Tate's here.    제럴드 테이트가 왔어요.                │
│                                                                   │
│  [1] [00:00:50,595 -->   [1] [00:00:50,595 -->                   │
│       00:00:51,929]           00:00:51,929]                       │
│       He wants to know...    자기 거래가 어떻게...                 │
└─────────────────┬────────────────────────────────────────────────┘
                  │
                  │ main.py: Loads both files
                  │
┌─────────────────▼────────────────────────────────────────────────┐
│           Phase 1: ScriptAgent (ONE LLM CALL)                     │
├──────────────────────────────────────────────────────────────────┤
│  Receives:                                                        │
│  • source_dialogues: "[0] [timestamp] English text..."           │
│  • target_dialogues: "[0] [timestamp] Korean text..."            │
│  • show_bible: "Background info about the show"                  │
│                                                                   │
│  LLM Prompt includes BOTH languages:                             │
│  ----------------------------------------------------------       │
│  SOURCE DIALOGUES (English):                                     │
│  [0] [00:00:49,460 --> 00:00:50,527] Gerald Tate's here.        │
│  [1] [00:00:50,595 --> 00:00:51,929] He wants to know...        │
│                                                                   │
│  TARGET DIALOGUES (Korean):                                      │
│  [0] [00:00:49,460 --> 00:00:50,527] 제럴드 테이트가 왔어요.       │
│  [1] [00:00:50,595 --> 00:00:51,929] 자기 거래가 어떻게...         │
│  ----------------------------------------------------------       │
│                                                                   │
│  LLM Returns (SINGLE RESPONSE):                                  │
│  {                                                                │
│    "expressions": [                                               │
│      {                                                            │
│        "title": "...",                                            │
│        "expression": "wants to know",                             │
│        "expression_translation": "알고 싶어하다",                  │
│        "context_start_index": 0,                                  │
│        "context_end_index": 1,                                    │
│        "dialogues": {           ← NEW! Both languages             │
│          "en": [                                                  │
│            {"index": 0,                                           │
│             "timestamp": "00:00:49,460 --> 00:00:50,527",        │
│             "text": "Gerald Tate's here."},                      │
│            {"index": 1,                                           │
│             "timestamp": "00:00:50,595 --> 00:00:51,929",        │
│             "text": "He wants to know..."}                       │
│          ],                                                       │
│          "ko": [                                                  │
│            {"index": 0,                                           │
│             "timestamp": "00:00:49,460 --> 00:00:50,527",        │
│             "text": "제럴드 테이트가 왔어요."},                     │
│            {"index": 1,                                           │
│             "timestamp": "00:00:50,595 --> 00:00:51,929",        │
│             "text": "자기 거래가 어떻게..."}                       │
│          ]                                                        │
│        },                                                         │
│        "narrations": [...],                                       │
│        "vocabulary_annotations": [...]                            │
│      }                                                            │
│    ]                                                              │
│  }                                                                │
└─────────────────┬────────────────────────────────────────────────┘
                  │
                  │ Returns ChunkResult with expressions
                  │
┌─────────────────▼────────────────────────────────────────────────┐
│           Phase 2: Aggregator                                     │
├──────────────────────────────────────────────────────────────────┤
│  • Combines chunk summaries                                       │
│  • Creates master episode summary                                │
│  • Returns EpisodeData                                            │
└─────────────────┬────────────────────────────────────────────────┘
                  │
                  │ Returns EpisodeData
                  │
┌─────────────────▼────────────────────────────────────────────────┐
│           pipeline.translate_episode() [DEPRECATED]               │
├──────────────────────────────────────────────────────────────────┤
│  • NO LLM calls                                                   │
│  • NO TranslatorAgent                                             │
│  • Just converts expressions to TranslationResult format          │
│  • Dialogues field already contains both languages                │
└─────────────────┬────────────────────────────────────────────────┘
                  │
┌─────────────────▼────────────────────────────────────────────────┐
│                 OUTPUT: TranslationResult[]                       │
├──────────────────────────────────────────────────────────────────┤
│  Each TranslationResult has:                                      │
│  • expression: "wants to know"                                    │
│  • expression_translation: "알고 싶어하다"                         │
│  • dialogues: {                                                   │
│      "en": [{"index": 0, "timestamp": "...", "text": "..."}],    │
│      "ko": [{"index": 0, "timestamp": "...", "text": "..."}]     │
│    }                                                              │
│  • narrations, vocab, timestamps, etc.                            │
│                                                                   │
│  ✅ Ready for video generation!                                   │
└──────────────────────────────────────────────────────────────────┘
```

## Key Points

### 1. **TranslatorAgent File Still Exists** (`translator.py`)
   - **Location**: `langflix/pipeline/agents/translator.py`
   - **Status**: Present but **NOT IMPORTED** anywhere
   - **Reason**: Kept for backward compatibility in case other code references it
   - **Usage**: Zero - not used in any pipeline flow

### 2. **Pipeline Orchestrator Changes**
   ```python
   # OLD CODE (removed):
   from langflix.pipeline.agents.translator import TranslatorAgent
   self.translator = TranslatorAgent(model_name=config.translator_model)
   translations = self.translator.translate_to_multiple_languages(...)

   # NEW CODE:
   # No TranslatorAgent import
   # No translator initialization
   # No translation LLM calls
   ```

### 3. **ScriptAgent Does Everything**
   - **Input**: Source dialogues + Target dialogues
   - **Output**: Complete expression analysis WITH translations
   - **LLM Calls**: 1 per chunk (instead of 2)

### 4. **Data Flow**
   ```
   OLD: Source → ScriptAgent → TranslatorAgent → Result (2 LLM calls)
   NEW: Source + Target → ScriptAgent → Result (1 LLM call)
   ```

## Unused Legacy Components

The following files are no longer part of the pipeline:

### translator.py
- **Status**: Unused
- **Original Purpose**: Separate translation agent
- **Can be deleted**: No code references it

### aggregator.py
- **Status**: Unused
- **Original Purpose**: Combined chunk summaries into episode summary
- **Can be deleted**: Output was never used in video generation

To verify nothing uses these files:
```bash
grep -r "TranslatorAgent\|AggregatorAgent" langflix/ --include="*.py" | grep -v "translator.py\|aggregator.py"
```

## Summary

**Pipeline uses a single-agent architecture**:
- ✅ One LLM call per chunk (instead of 3)
- ✅ Simpler codebase
- ✅ Better performance
- ✅ Lower cost
- ✅ More reliable alignment between languages
