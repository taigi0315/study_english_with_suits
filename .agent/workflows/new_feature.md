# New Feature Workflow

> Step-by-step process for implementing new features

---

## 1. Analyze

- [ ] Read existing code/docs related to the feature
- [ ] Understand how similar features are implemented
- [ ] Identify affected modules and files
- [ ] Check test files for expected behavior patterns

---

## 2. Create Ticket

Create ticket in `tickets/review-required/TICKET-XXX-description.md`:

```markdown
# [TICKET-XXX] Feature Title

## Priority
- [ ] Critical / High / Medium / Low

## Type
- [x] New Feature

## Description
What the feature does...

## Implementation Plan
1. Step 1
2. Step 2

## Files Affected
- `langflix/path/to/file.py`
- `tests/unit/test_file.py`

## Testing Strategy
- Unit tests for...
- Integration test for...
```

---

## 3. Create Branch

```bash
git checkout main
git pull origin main
git checkout -b feature/TICKET-XXX-brief-description
```

---

## 4. Implement

- [ ] Write code following project patterns
- [ ] Use type hints for all functions
- [ ] Add docstrings
- [ ] Use `@handle_error_decorator` for error handling
- [ ] No hardcoded values - use settings

---

## 5. Test

```bash
# Write unit tests
pytest tests/unit/test_new_feature.py -v

# Run all tests
make test

# Integration test - generate video
python -m langflix.main --subtitle "test.srt" --test-mode --max-expressions 2
```

---

## 6. Verify Video Output

- [ ] Watch generated video
- [ ] Check subtitles are correct
- [ ] Verify audio sync
- [ ] Confirm video quality

---

## 7. Move Ticket

```bash
mv tickets/review-required/TICKET-XXX-*.md tickets/approved/
```

---

## 8. Update Documentation

- [ ] Update docstrings if API changed
- [ ] Update relevant `docs/*.md` files
- [ ] Update `AGENTS.md` if patterns changed
- [ ] Add to CHANGELOG if significant

---

## 9. Commit & PR

```bash
git add .
git commit -m "feat: brief description of feature"
git push origin feature/TICKET-XXX-brief-description
```

Create PR with:
- Summary of changes
- Link to ticket
- Screenshots/videos if UI-related
