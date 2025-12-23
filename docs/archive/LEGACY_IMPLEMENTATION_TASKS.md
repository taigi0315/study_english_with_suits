# V3 Implementation Task List

**Date Started**: December 21, 2025
**Goal**: Implement V3 Contextual Localization Pipeline as per V3_SDD.md
**Status**: 🟡 IN PROGRESS

---

## 📋 Implementation Phases

### ✅ Phase 0: Preparation & Cleanup

- [ ] **Task 0.1**: Remove V1 fallback code from main.py
  - Location: `langflix/main.py` lines 237-263
  - Status: 🔴 TODO
  - Notes: V1 fallback defeats V3 purpose

- [ ] **Task 0.2**: Update config to reflect V3 architecture
  - Location: `langflix/config/default.yaml`
  - Status: 🔴 TODO
  - Add: `v3_enabled`, `show_bible_cache_dir`, `wikipedia_enabled`

- [ ] **Task 0.3**: Create V3 directory structure
  - Status: 🔴 TODO
  - Create:
    - `langflix/v3/` (new module)
    - `langflix/v3/agents/` (agent implementations)
    - `langflix/v3/tools/` (Wikipedia tool)
    - `langflix/v3/artifacts/` (Show Bibles, Summaries)

---

### 🟡 Phase 1: Show Bible Creator (Once per Show)

**Goal**: Generate static context from Wikipedia about show/characters

- [ ] **Task 1.1**: Install Wikipedia dependencies
  - Status: 🔴 TODO
  - Dependencies: `wikipedia-api` or LangChain's `WikipediaQueryRun`
  - Command: `pip install wikipedia-api langchain-community`

- [ ] **Task 1.2**: Create Wikipedia Tool wrapper
  - File: `langflix/v3/tools/wikipedia_tool.py`
  - Status: 🔴 TODO
  - Implement:
    - `search_show_premise(show_name: str) -> str`
    - `search_show_characters(show_name: str) -> str`
    - Retry logic with exponential backoff
    - Error handling for API failures

- [ ] **Task 1.3**: Create Show Bible Generator
  - File: `langflix/v3/agents/show_bible_creator.py`
  - Status: 🔴 TODO
  - Implement:
    - `create_show_bible(show_name: str) -> str`
    - Generate formatted `Show_Bible.txt`
    - Cache show bibles (don't regenerate)
    - Template format:
      ```
      === SHOW BIBLE: {Show Name} ===
      [PREMISE]
      {premise_text}
      [CHARACTERS & RELATIONSHIPS]
      {characters_text}
      ```

- [ ] **Task 1.4**: Add Show Bible cache management
  - File: `langflix/v3/bible_manager.py`
  - Status: 🔴 TODO
  - Implement:
    - `get_or_create_bible(show_name: str) -> str`
    - `cache_bible(show_name: str, content: str)`
    - `list_cached_bibles() -> List[str]`

- [ ] **Task 1.5**: Create Show Bible CLI command
  - File: `langflix/cli/bible.py`
  - Status: 🔴 TODO
  - Command: `python -m langflix.cli.bible create "Suits"`
  - Test with "Suits" TV series

---

### 🔴 Phase 2: Script Agent V3 (Extract + Summarize)

**Goal**: Extract expressions AND generate chunk summaries with emotional context

- [ ] **Task 2.1**: Create V3 Script Agent prompt template
  - File: `langflix/v3/prompts/script_agent_v3.txt`
  - Status: 🔴 TODO
  - Include:
    - Speaker inference instructions
    - Micro-summarization task
    - V2 expression extraction criteria (keep existing)
    - Context injection placeholders: `{show_bible}`

- [ ] **Task 2.2**: Update ExpressionAnalyzer for V3
  - File: `langflix/core/expression_analyzer.py`
  - Status: 🔴 TODO
  - Add method: `analyze_with_context(chunk, show_bible) -> V3ChunkResult`
  - Return structure:
    ```python
    {
      "chunk_id": int,
      "chunk_summary": str,  # NEW in V3
      "expressions": List[Expression]  # Existing V2 structure
    }
    ```

- [ ] **Task 2.3**: Create V3 data models
  - File: `langflix/v3/models.py`
  - Status: 🔴 TODO
  - Define:
    - `V3ChunkResult` (chunk summary + expressions)
    - `V3EpisodeData` (all chunks + master summary)
    - `V3TranslationResult` (localized data)

- [ ] **Task 2.4**: Update subtitle chunking to include Show Bible
  - File: `langflix/core/subtitle_parser.py`
  - Status: 🔴 TODO
  - Pass show bible to each chunk analysis

- [ ] **Task 2.5**: Test Script Agent V3 with sample chunk
  - Status: 🔴 TODO
  - Test data: First 5-minute chunk from Suits S01E01
  - Verify: Chunk summary includes emotional context

---

### 🔴 Phase 3: Aggregator (Master Summary Creator)

**Goal**: Combine all chunk summaries into cohesive episode narrative

- [ ] **Task 3.1**: Create Aggregator prompt template
  - File: `langflix/v3/prompts/aggregator.txt`
  - Status: 🔴 TODO
  - Prompt: "Rewrite chronological scene summaries into single cohesive narrative"

- [ ] **Task 3.2**: Implement Aggregator Agent
  - File: `langflix/v3/agents/aggregator.py`
  - Status: 🔴 TODO
  - Method: `aggregate_summaries(chunk_summaries: List[str]) -> str`
  - Use cheaper model (Gemini Flash or GPT-3.5 Turbo)
  - Output: `Master_Episode_Summary.txt`

- [ ] **Task 3.3**: Add Master Summary caching
  - File: `langflix/v3/summary_manager.py`
  - Status: 🔴 TODO
  - Cache summaries by episode ID
  - Reuse if episode already processed

- [ ] **Task 3.4**: Test Aggregator with Suits S01E01
  - Status: 🔴 TODO
  - Input: All chunk summaries from Phase 2
  - Verify: Cohesive narrative captures story arc

---

### 🔴 Phase 4: Translator Agent V3 (Contextual Localization)

**Goal**: Translate expressions with full context awareness

- [ ] **Task 4.1**: Create Translator V3 prompt template
  - File: `langflix/v3/prompts/translator_v3.txt`
  - Status: 🔴 TODO
  - Include:
    - Context mapping instructions (Show Bible usage)
    - Honorifics/formality rules (Korean 반말/존댓말)
    - Emotional tone adaptation
    - Localization (의역) emphasis

- [ ] **Task 4.2**: Implement Translator Agent V3
  - File: `langflix/v3/agents/translator.py`
  - Status: 🔴 TODO
  - Method: `translate_with_context(expressions, show_bible, master_summary, target_lang) -> List[V3TranslationResult]`
  - Support multiple target languages: Korean, Japanese, Spanish

- [ ] **Task 4.3**: Update data structure for multilingual output
  - File: `langflix/models.py`
  - Status: 🔴 TODO
  - Add `localization` field to Expression model:
    ```python
    {
      "target_lang": "Korean",
      "expression_translated": str,
      "expression_dialogue_translated": str,
      "catchy_keywords_translated": List[str]
    }
    ```

- [ ] **Task 4.4**: Create language-specific translation rules
  - File: `langflix/v3/language_rules/`
  - Status: 🔴 TODO
  - Create:
    - `korean_rules.py` (honorifics mapping)
    - `japanese_rules.py` (keigo system)
    - `spanish_rules.py` (formal/informal)

- [ ] **Task 4.5**: Test Translator V3 with Korean
  - Status: 🔴 TODO
  - Test case: Harvey (senior) speaking to Mike (junior)
  - Verify: Korean translation uses 반말 for Harvey, 존댓말 for Mike

---

### 🔴 Phase 5: Main Pipeline Integration

**Goal**: Update main.py to use V3 workflow instead of V2

- [ ] **Task 5.1**: Create V3 Pipeline orchestrator
  - File: `langflix/v3/pipeline.py`
  - Status: 🔴 TODO
  - Method: `run_v3_pipeline(video_path, subtitle_path, show_name, target_languages) -> V3EpisodeData`
  - Workflow:
    1. Get/Create Show Bible
    2. Run Script Agent V3 on all chunks
    3. Run Aggregator
    4. Run Translator for each target language

- [ ] **Task 5.2**: Update main.py to use V3 pipeline
  - File: `langflix/main.py`
  - Status: 🔴 TODO
  - Replace V2 analysis with V3 pipeline
  - Remove V1 fallback code
  - Keep V2 as optional legacy mode (config flag)

- [ ] **Task 5.3**: Add V3 config settings
  - File: `langflix/config/default.yaml`
  - Status: 🔴 TODO
  - Add:
    ```yaml
    v3:
      enabled: true  # Use V3 pipeline
      show_bible_cache_dir: "artifacts/show_bibles"
      master_summary_cache_dir: "artifacts/summaries"
      use_wikipedia: true
      aggregator_model: "gemini-2.5-flash"  # Cheaper model for summaries
      translator_model: "gemini-1.5-pro"    # Smart model for translation
    ```

- [ ] **Task 5.4**: Update settings.py for V3 config
  - File: `langflix/settings.py`
  - Status: 🔴 TODO
  - Add getters:
    - `is_v3_enabled()`
    - `get_v3_aggregator_model()`
    - `get_v3_translator_model()`

---

### 🔴 Phase 6: Testing & Validation

**Goal**: Verify V3 works end-to-end with Suits S01E01

- [ ] **Task 6.1**: Create V3 unit tests
  - File: `tests/unit/test_v3_pipeline.py`
  - Status: 🔴 TODO
  - Test:
    - Show Bible creation
    - Script Agent V3 chunk processing
    - Aggregator summary generation
    - Translator context awareness

- [ ] **Task 6.2**: Create V3 integration test
  - File: `tests/integration/test_v3_end_to_end.py`
  - Status: 🔴 TODO
  - Test: Full pipeline from subtitle → multilingual JSON

- [ ] **Task 6.3**: Test with Suits S01E01
  - Status: 🔴 TODO
  - Input: English subtitle only
  - Target languages: Korean, Spanish
  - Verify:
    - Show Bible has Suits character info
    - Master Summary captures episode arc
    - Korean translation uses proper honorifics
    - Spanish translation is natural

- [ ] **Task 6.4**: Performance testing
  - Status: 🔴 TODO
  - Measure:
    - Token usage (compare to V2 + full script translation)
    - Processing time per episode
    - Cost per target language

- [ ] **Task 6.5**: Test mode validation
  - Status: 🔴 TODO
  - Verify: Test mode works with ANY video (only needs 1 subtitle)

---

### 🔴 Phase 7: Documentation & Cleanup

**Goal**: Document V3 architecture and update user guides

- [ ] **Task 7.1**: Update README with V3 info
  - File: `README.md`
  - Status: 🔴 TODO
  - Add V3 features section
  - Document new workflow

- [ ] **Task 7.2**: Create V3 User Guide
  - File: `docs/V3_USER_GUIDE.md`
  - Status: 🔴 TODO
  - Explain:
    - Show Bible creation
    - Multi-language workflow
    - Context-aware translation benefits

- [ ] **Task 7.3**: Create V3 API documentation
  - File: `docs/V3_API_REFERENCE.md`
  - Status: 🔴 TODO
  - Document:
    - V3Pipeline class
    - Show Bible API
    - Translation API

- [ ] **Task 7.4**: Update RECENT_CHANGES.md
  - File: `docs/RECENT_CHANGES.md`
  - Status: 🔴 TODO
  - Add V3 implementation details

---

## 📊 Progress Summary

| Phase | Tasks | Completed | In Progress | Not Started | Status |
|-------|-------|-----------|-------------|-------------|--------|
| Phase 0: Cleanup | 3 | 1 | 0 | 2 | 🟡 33% |
| Phase 1: Show Bible | 5 | 3 | 0 | 2 | 🟡 60% |
| Phase 2: Script Agent V3 | 5 | 3 | 0 | 2 | 🟡 60% |
| Phase 3: Aggregator | 4 | 2 | 0 | 2 | 🟡 50% |
| Phase 4: Translator V3 | 5 | 3 | 0 | 2 | 🟡 60% |
| Phase 5: Integration | 4 | 4 | 0 | 0 | ✅ 100% |
| Phase 6: Testing | 5 | 0 | 0 | 5 | 🔴 TODO |
| Phase 7: Documentation | 4 | 1 | 0 | 3 | 🟡 25% |
| **TOTAL** | **35** | **17** | **0** | **18** | **49%** |

---

## ✅ Completed Tasks

### Phase 0: Cleanup
- [x] Task 0.1: Remove V1 fallback code from main.py

### Phase 1: Show Bible
- [x] Task 1.2: Create Wikipedia Tool wrapper (`langflix/v3/tools/wikipedia_tool.py`)
- [x] Task 1.3: Create Show Bible Generator (integrated in wikipedia_tool.py)
- [x] Task 1.4: Add Show Bible cache management (`langflix/v3/bible_manager.py`)

### Phase 2: Script Agent V3
- [x] Task 2.1: Create V3 Script Agent prompt template (`langflix/v3/prompts/script_agent_v3.txt`)
- [x] Task 2.2: Implement Script Agent V3 (`langflix/v3/agents/script_agent_v3.py`)
- [x] Task 2.3: Create V3 data models (`langflix/v3/models.py`)

### Phase 3: Aggregator
- [x] Task 3.1: Create Aggregator prompt template (`langflix/v3/prompts/aggregator.txt`)
- [x] Task 3.2: Implement Aggregator Agent (`langflix/v3/agents/aggregator.py`)

### Phase 4: Translator V3
- [x] Task 4.1: Create Translator V3 prompt template (`langflix/v3/prompts/translator_v3.txt`)
- [x] Task 4.2: Implement Translator Agent V3 (`langflix/v3/agents/translator.py`)
- [x] Task 4.3: Update data structure for multilingual output (in models.py)

### Phase 5: Integration
- [x] Task 5.1: Create V3 Pipeline orchestrator (`langflix/v3/pipeline.py`)
- [x] Task 5.2: Update main.py to use V3 pipeline (`langflix/main.py`)
- [x] Task 5.3: Add V3 config settings (`langflix/config/default.yaml`)
- [x] Task 5.4: Update settings.py for V3 config (`langflix/settings.py`)

### Phase 7: Documentation
- [x] Task 7.4: Update V3_IMPLEMENTATION_TASKS.md (this file)

---

## 🎯 Current Focus

**Next Task**: Phase 6 Testing - Test V3 with Suits S01E01

---

## 📝 Notes & Decisions

### Decision Log

1. **2025-12-21**: Started V3 implementation based on V3_SDD.md
2. **2025-12-21**: User confirmed V1 fallback should NOT exist - V3 is the future

### Key Insights

- V3 only needs ONE subtitle file (source language)
- Test mode should work with any video (no dual subtitles required)
- Context injection is the core innovation (Show Bible + Summaries)
- Cost savings: Only translate expressions, not entire scripts

### Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Wikipedia API failure | High - No Show Bible = No V3 | Implement retry logic + fallback to cached bibles |
| LLM hallucination in speaker inference | Medium - Incorrect context | Use "likely" language, don't claim certainty |
| Token costs for V3 | Medium - More LLM calls | Use cheaper models for aggregation, cache aggressively |

---

**Last Updated**: 2025-12-21 2:15 PM
**Updated By**: AI Assistant
**Next Update**: After completing Phase 6 testing
