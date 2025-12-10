# TICKET-091: Integration Test for Duplicate Translation Fix

## Summary
Create an integration test that runs the full video creation pipeline in **test mode** for Korean (`ko`) using the provided test media. The test must verify that no redundant LLM translation calls are made and that the output video is generated successfully.

## Acceptance Criteria
- A new branch `feature/TICKET-091-integration-test-translation` is created.
- Test script runs `make dev-all` (or appropriate make target) with `TEST_MODE=1` and target language `ko`.
- The pipeline processes the media located at `assets/media/test_media`.
- The logs contain the message `✅ Using existing translations for ko` confirming the duplicate‑translation fix.
- The final short‑form video file path is printed and the file exists.
- Documentation is updated (or created) under `docs/integration_tests.md` describing how to run the test.
- No duplicate documentation entries exist.
- Unit/integration test added under `tests/integration/test_translation_fix.py`.

## Implementation Steps
1. **Create branch** `feature/TICKET-091-integration-test-translation`.
2. **Add integration test** `tests/integration/test_translation_fix.py` that:
   - Sets up a temporary output directory.
   - Calls the main pipeline (`langflix.main`) with arguments pointing to the test media and `--test-mode`.
   - Captures stdout and asserts the presence of the expected log line.
   - Asserts that the output video file exists and prints its path.
3. **Add script** `scripts/run_translation_integration_test.sh` that runs the test via `make dev-all`.
4. **Update documentation** `docs/integration_tests.md` with a new section for this test.
5. **Deduplicate docs** – search for existing similar sections and merge if needed.
6. **Run `make dev-all`** to ensure the test passes.
7. **Commit** all changes with a clear message.

## Estimated Effort
- Development & testing: ~3 hours
- Documentation & cleanup: ~30 minutes

## Risks
- The test media must be compatible with the pipeline (correct format, subtitles). If not, the test will fail – ensure the media includes a subtitle file.
- Running the full pipeline may take a few minutes; keep the test timeout reasonable (e.g., 10 min).
