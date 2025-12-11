# Bug Fix Workflow

> Step-by-step process for fixing bugs

---

## 1. Reproduce

- [ ] Reproduce the bug locally
- [ ] Identify exact steps to trigger
- [ ] Note error messages and logs
- [ ] Check `langflix.log` for details

---

## 2. Analyze

- [ ] Use step-by-step tests to isolate the stage:

```bash
python tests/step_by_step/test_step1_load_and_analyze.py
python tests/step_by_step/test_step2_slice_video.py
python tests/step_by_step/test_step3_add_subtitles.py
# ... etc
```

- [ ] Read related code thoroughly
- [ ] Identify root cause (not just symptoms)

---

## 3. Create Ticket

Create ticket in `tickets/review-required/TICKET-XXX-fix-description.md`:

```markdown
# [TICKET-XXX] Fix: Bug Title

## Priority
- [x] High (bug fix)

## Type
- [x] Bug Fix

## Bug Description
What happens vs what should happen...

## Reproduction Steps
1. Step 1
2. Step 2
3. Error occurs

## Root Cause
Why this is happening...

## Proposed Fix
How to fix it...

## Files Affected
- `langflix/path/to/file.py`
```

---

## 4. Create Branch

```bash
git checkout main
git pull origin main
git checkout -b fix/TICKET-XXX-brief-description
```

---

## 5. Write Failing Test

First, write a test that demonstrates the bug:

```python
def test_bug_scenario_should_not_fail():
    """Test that reproduces the bug - should pass after fix."""
    # Setup that triggers the bug
    result = buggy_function()
    assert result is not None  # Currently fails
```

---

## 6. Implement Fix

- [ ] Fix the root cause
- [ ] Don't just patch symptoms
- [ ] Follow existing patterns

---

## 7. Verify Tests Pass

```bash
# Run the specific test
pytest tests/unit/test_buggy_module.py -v

# Run all tests to check for regressions
make test

# Integration test
python -m langflix.main --subtitle "test.srt" --test-mode
```

---

## 8. Move Ticket

```bash
mv tickets/review-required/TICKET-XXX-*.md tickets/approved/
```

---

## 9. Update Documentation

- [ ] Add to TROUBLESHOOTING if common issue
- [ ] Update comments if logic was confusing

---

## 10. Commit & PR

```bash
git add .
git commit -m "fix: brief description of fix"
git push origin fix/TICKET-XXX-brief-description
```

Create PR with:
- Root cause explanation
- What the fix does
- How to verify
