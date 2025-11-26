# Update YouTube Posting Format

## User Review Required
None. The changes are straightforward refactoring of string templates and logic to match the requested format.

## Proposed Changes
### YouTube Metadata Generator
#### [MODIFY] [metadata_generator.py](file:///Users/changikchoi/Documents/langflix/langflix/youtube/metadata_generator.py)
- Update `_load_translations` to use the new title template `{expression} | {translation} | from {episode}`.
- Update `_load_templates` to reflect the new default title template.
- Update `_generate_title` to extract `translation` and pass it to the template formatter.
- Update `_generate_description` to ensure the body format matches the requirement:
    - `Expression: {Original Expression}` (English label)
    - `Meaning: {Translation}` (Localized label)
    - Localized "Watch and learn" message.
    - Localized tags.

## Verification Plan
### Automated Tests
- Create a new test file `tests/unit/test_metadata_generator_ticket_074.py` to verify the metadata generation logic.
- The test will mock `VideoMetadata` and check if the generated title, description, and tags match the expected format for a target language (e.g., Korean).

### Manual Verification
- Run the newly created test and ensure it passes.
