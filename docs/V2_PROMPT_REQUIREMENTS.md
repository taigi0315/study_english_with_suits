# V2 Prompt Requirements: expression_analysis_prompt_v8.txt

## 🎯 Summary of Change

The V1 prompt (`expression_analysis_prompt_v7.txt`) was designed for a workflow where the LLM performs **both translation AND content selection**. 

V2 has shifted to dual-language subtitles from Netflix, meaning **translations are pre-provided**. The new prompt must:
1. **NOT ask for translation** - translations come from subtitle files
2. **Focus purely on content selection** - identifying the best expressions
3. **Return indices instead of timestamps** - timestamps are looked up post-processing
4. **Reduce token usage** - no redundant output

---

## 📥 CURRENT V1 PROMPT INPUT

```
{dialogues}  ← Single language with timestamps
{show_name}
{target_language}  
{level_description}
{max_expressions}
{min_expressions}
{target_duration}
```

## 📥 NEW V2 PROMPT INPUT

```
{source_dialogues}  ← English dialogues (no timestamps needed!)
{target_dialogues}  ← Korean/Spanish dialogues (no timestamps needed!)
{show_name}
{source_language}  ← NEW: e.g., "English"
{target_language}  ← e.g., "Korean"
{level_description}
{max_expressions}
{min_expressions}
{target_duration}
```

**Key Change:** Two dialogue streams instead of one, NO timestamps in input.

---

## 📤 CURRENT V1 PROMPT OUTPUT FIELDS

```json
{
  "title": "Catchy title in target_language",
  "dialogues": ["line1", "line2", ...],           // ❌ REMOVE
  "translation": ["trans1", "trans2", ...],       // ❌ REMOVE
  "expression_dialogue": "full sentence",          // ❌ CHANGE to index
  "expression_dialogue_translation": "...",        // ❌ REMOVE
  "expression": "key phrase",                      // ✅ KEEP
  "expression_translation": "...",                 // ❌ REMOVE (lookup from target)
  "intro_hook": "...",                             // ✅ KEEP
  "context_start_time": "00:00:00,000",            // ❌ CHANGE to index
  "context_end_time": "00:00:00,000",              // ❌ CHANGE to index
  "similar_expressions": [...],                    // ✅ KEEP
  "scene_type": "humor|drama|...",                 // ✅ KEEP
  "catchy_keywords": [...],                        // ✅ KEEP
  "vocabulary_annotations": [                      // ✅ KEEP (but simplified)
    {"word": "...", "translation": "...", "dialogue_index": 0}  // ❌ REMOVE translation
  ]
}
```

## 📤 NEW V2 PROMPT OUTPUT FIELDS

```json
{
  "title": "Catchy title in target_language",       // ✅ KEEP - LLM generates
  "expression": "knock it out of the park",         // ✅ KEEP - LLM identifies
  "expression_dialogue_index": 5,                   // 🆕 NEW - index, not text
  "context_start_index": 2,                         // 🆕 NEW - index, not timestamp
  "context_end_index": 8,                           // 🆕 NEW - index, not timestamp
  "catchy_keywords": ["keyword1", "keyword2"],      // ✅ KEEP - LLM generates
  "vocabulary_annotations": [                       // 🆕 SIMPLIFIED
    {"word": "douchebag", "dialogue_index": 3}      // NO translation! Lookup later
  ],
  "similar_expressions": ["alt1", "alt2"],          // ✅ KEEP
  "scene_type": "humor",                            // ✅ KEEP
  "intro_hook": "Hook in target_language"           // ✅ KEEP - LLM generates
}
```

---

## ❌ REMOVE FROM V1 PROMPT

### 1. All dialogue/translation output instructions
The V1 prompt says:
> "dialogues": [ // EXACT dialogue text from subtitles ]
> "translation": [ // MUST have SAME NUMBER of items as dialogues ]

**V2 removes this entirely.** Dialogues come from source subtitles, translations from target subtitles. LLM just needs to say WHICH indices to use.

### 2. All translation guidance sections
Remove sections:
- "TRANSLATION STRATEGY - 의역 (Natural Translation)"
- "For DIALOGUE translations..."
- "For EXPRESSION translations..."
- All references to 직역/의역

**V2 doesn't translate anything.**

### 3. Timestamp output fields
Replace:
- `context_start_time` → `context_start_index`
- `context_end_time` → `context_end_index`

**V2 uses indices.** System looks up timestamps from subtitles.

### 4. expression_dialogue text
Replace:
- `expression_dialogue` (full text) → `expression_dialogue_index` (number)
- Remove `expression_dialogue_translation`

---

## ✅ KEEP FROM V1 PROMPT (IMPORTANT!)

### 1. Scene Energy / North Star Principle
This is crucial! Keep all the guidance about:
- HIGH-ENERGY, MEMORABLE MOMENTS (😂 HUMOROUS, 🔥 DRAMATIC, 😍 ROMANTIC, 😲 SURPRISING)
- "Would I be excited to share THIS clip?"
- "Think about what would make a short video clip go viral"

### 2. Expression Quality Criteria
Keep all guidance about:
- Multi-word phrases (3+ words)
- Phrasal verbs
- NOT simple phrases like "I agree"
- Complexity requirements

### 3. Context Design - Mini Story
Keep the concept but adapt:
- Still need Beginning/Middle/End
- Expression in middle, not at edges
- Complete sentences at boundaries
- Use indices instead of timestamps

### 4. Catchy Keywords Generation
Keep all the guidance for generating engaging {target_language} keywords:
- 3-6 words each
- NEVER English
- TikTok/Reel caption style

### 5. Non-Overlapping Clips Rule
Keep but simplify:
- No overlapping `context_start_index`/`context_end_index` ranges
- Chronological order

---

## 🆕 ADD TO V2 PROMPT

### 1. Explicit "NO TRANSLATION NEEDED" statement
Add prominently:
> **V2 MODE: Both source AND target language subtitles are provided.**
> **You do NOT need to translate anything.**
> **Focus purely on content selection.**

### 2. Index Explanation
Explain clearly:
> The input format is: `[index] dialogue_text`
> Use these indices in your output to reference specific dialogues.
> The system will look up actual text and timestamps from the indices.

### 3. Vocabulary Annotation Simplification
New format:
```json
"vocabulary_annotations": [
  {"word": "douchebag", "dialogue_index": 3}
]
```
**No `translation` field** - system looks it up from target_dialogues[dialogue_index].

---

## 📊 TOKEN REDUCTION SUMMARY

| Field | V1 (tokens) | V2 (tokens) | Saved |
|-------|-------------|-------------|-------|
| dialogues | ~200 | 0 | 200 |
| translation | ~200 | 0 | 200 |
| context_start_time | ~10 | 3 | 7 |
| context_end_time | ~10 | 3 | 7 |
| expression_translation | ~20 | 0 | 20 |
| vocab translation | ~30 | 0 | 30 |
| **Total per expression** | **~470** | **~150** | **~320** |

**Estimated 68% reduction in output tokens per expression.**

---

## 📝 OUTPUT JSON SCHEMA (V2)

```json
{
  "expressions": [
    {
      "title": "Catchy title in {target_language} (8-15 words)",
      "expression": "key phrase from source dialogues (4-8 words)",
      "expression_dialogue_index": 5,
      "context_start_index": 2,
      "context_end_index": 8,
      "catchy_keywords": [
        "keyword 1 in {target_language}",
        "keyword 2 in {target_language}"
      ],
      "vocabulary_annotations": [
        {"word": "word from source", "dialogue_index": 3}
      ],
      "similar_expressions": ["alt1 in {source_language}", "alt2"],
      "scene_type": "humor|drama|tension|emotional|witty|sexy|surprising",
      "intro_hook": "Short hook in {target_language}"
    }
  ]
}
```

---

## ✅ V2 FINAL CHECKLIST (for new prompt)

Include this at the end:

- ✓ Expression is substantive (3+ words, non-obvious meaning)
- ✓ Scene has high emotional energy (not boring/procedural)
- ✓ `expression_dialogue_index` correctly points to source line with expression
- ✓ `context_start_index` to `context_end_index` creates complete mini-story
- ✓ Context is approximately {target_duration} seconds worth
- ✓ Expression appears in MIDDLE of context (not at edges)
- ✓ No overlapping index ranges between expressions
- ✓ All `catchy_keywords` and `title` are in {target_language} (NOT SOURCE!)
- ✓ All `similar_expressions` are in {source_language}
- ✓ vocabulary_annotations reference actual words from source dialogues
