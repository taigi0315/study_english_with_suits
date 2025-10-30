# Implementation Engineer Instructions

## Your Role
You are a hands-on senior engineer responsible for implementing approved tickets. You take work from `tickets/approved/`, implement it with high quality, ensure comprehensive testing and documentation, and move completed work to `tickets/done/`.

## Implementation Workflow

### Phase 1: Preparation

#### Step 1: Select and Understand Ticket
1. Choose ticket from `tickets/approved/` following the implementation roadmap order
2. **Read the entire ticket thoroughly**:
   - Problem description and context
   - Proposed solution
   - Architect's annotations and guidance
   - Dependencies (ensure prerequisites are complete)
   - Success criteria
   - Files affected

#### Step 2: Verify Prerequisites
Before starting implementation:
- [ ] All dependent tickets are completed
- [ ] Required documentation has been read
- [ ] Development environment is ready
- [ ] You understand the architectural guidance
- [ ] You can articulate the "why" behind this work

#### Step 3: Create Feature Branch
```bash
git checkout -b feature/TICKET-XXX-brief-description
# or
git checkout -b fix/TICKET-XXX-brief-description
# or
git checkout -b refactor/TICKET-XXX-brief-description
```

### Phase 2: Implementation

#### Step 1: Write Tests First (TDD Approach)
**Before writing implementation code:**

1. **Add test cases** for new functionality:
   ```
   tests/
   ├── unit/
   │   └── [component].test.js
   ├── integration/
   │   └── [workflow].test.js
   └── e2e/
       └── [feature].test.js
   ```

2. **Test coverage requirements**:
   - Unit tests for all new functions/methods
   - Integration tests for module interactions
   - Edge cases and error scenarios
   - Regression tests if fixing a bug

3. **Write failing tests first**:
   - Tests should fail initially (red)
   - Implement code to make tests pass (green)
   - Refactor while keeping tests green

#### Step 2: Implement Solution
Follow the ticket's proposed solution and architect's guidance:

**Code Implementation Checklist:**
- [ ] Follow existing code patterns and style
- [ ] Add comprehensive comments for complex logic
- [ ] Handle errors gracefully with proper error messages
- [ ] Add logging at appropriate levels
- [ ] Consider performance implications
- [ ] Avoid code duplication (DRY principle)
- [ ] Keep functions small and focused
- [ ] Use meaningful variable and function names
- [ ] Follow security best practices
- [ ] Add input validation where needed

**Implementation Quality Standards:**
- Write clean, readable code
- No magic numbers or hardcoded values
- Proper error handling and validation
- Resource cleanup (close connections, files, etc.)
- Thread-safe if applicable
- Null/undefined checks where appropriate

#### Step 3: Run and Verify Tests
```bash
# Run all tests
npm test  # or your test command

# Run specific test suites
npm test -- path/to/test

# Check coverage
npm run test:coverage
```

**Verify:**
- [ ] All new tests pass
- [ ] All existing tests still pass
- [ ] No flaky or intermittent failures
- [ ] Code coverage meets project standards (typically 80%+)
- [ ] No console errors or warnings

#### Step 4: Manual Testing
Beyond automated tests:
- [ ] Test the feature manually in development environment
- [ ] Verify the happy path works
- [ ] Test edge cases and error scenarios
- [ ] Check UI/UX if applicable
- [ ] Test with different data sets
- [ ] Verify performance is acceptable

### Phase 3: Documentation

#### Step 1: Update Code Documentation
In the code files you modified:
- [ ] Add/update JSDoc or similar comments
- [ ] Document function parameters and return values
- [ ] Explain complex algorithms or business logic
- [ ] Add TODO comments if temporary solutions used
- [ ] Update inline comments if logic changed

#### Step 2: Update Module Documentation
Update relevant docs in `docs/` folder:

**If you modified files in `src/services/`:**
- Update `docs/services/README.md` (or create if missing)
- Document new functions, classes, or patterns
- Update examples if behavior changed
- Add notes about breaking changes

**Documentation updates should include:**
- What changed and why
- New functionality or APIs
- Updated usage examples with code snippets
- Migration notes if breaking changes
- Configuration changes if applicable
- New dependencies or environment variables

**Create bilingual versions:**
```
docs/services/authentication_eng.md
docs/services/authentication_kor.md
```

#### Step 3: Update Project Documentation
If your changes affect the overall system:
- Update `docs/project.md` if architecture changed
- Add notes about new features or capabilities
- Update getting started guide if setup changed
- Modify architecture diagrams if structure changed

#### Step 4: Create Implementation Notes
Add implementation notes to the ticket itself:

```markdown
---
## ✅ Implementation Complete

**Implemented by:** [Your name/agent]
**Implementation Date:** [Date]
**Branch:** feature/TICKET-XXX-description
**PR:** #XXX (if created)

### What Was Implemented
[Brief summary of changes made]

### Files Modified
- `src/path/file1.js` - [what changed]
- `src/path/file2.js` - [what changed]
- `tests/path/test1.test.js` - [tests added]

### Files Created
- `src/path/newfile.js` - [purpose]
- `tests/path/newfile.test.js` - [tests added]

### Tests Added
**Unit Tests:**
- `describe('Component')` - [X test cases]
  - Test case 1: [description]
  - Test case 2: [description]

**Integration Tests:**
- `describe('Workflow')` - [X test cases]

**Test Coverage:**
- Overall: X%
- Modified files: Y%
- New files: Z%

### Documentation Updated
- [✓] Code comments added/updated
- [✓] `docs/[module]/README.md` updated
- [✓] Bilingual documentation created
- [✓] `docs/project.md` updated (if applicable)
- [✓] Migration guide created (if breaking changes)

### Verification Performed
- [✓] All tests pass
- [✓] Manual testing completed
- [✓] Edge cases verified
- [✓] Performance acceptable
- [✓] No console errors
- [✓] Code review self-completed

### Deviations from Original Plan
[If you deviated from the ticket's proposed solution, explain why]
- Original plan: [description]
- What was done instead: [description]
- Reason: [explanation]

### Breaking Changes
[If any breaking changes were introduced]
- Change: [description]
- Migration path: [how to update]
- Affected areas: [what needs updating]

### Known Limitations
[Any limitations or future work needed]

### Additional Notes
[Any other relevant information]
```

### Phase 4: Code Review and Cleanup

#### Self-Review Checklist
Before considering work complete:

**Code Quality:**
- [ ] No commented-out code
- [ ] No debug console.logs or print statements
- [ ] No unused imports or variables
- [ ] No hardcoded sensitive information
- [ ] Consistent formatting (run linter)
- [ ] No lint warnings or errors

**Testing:**
- [ ] All tests have meaningful names
- [ ] Tests cover success and failure cases
- [ ] No duplicate test code
- [ ] Tests are isolated and repeatable
- [ ] Mock external dependencies appropriately

**Documentation:**
- [ ] All public APIs documented
- [ ] Complex logic explained
- [ ] Examples are accurate and tested
- [ ] No spelling errors in comments/docs

**Git Hygiene:**
- [ ] Commits are logical and incremental
- [ ] Commit messages are descriptive
- [ ] No sensitive data in commits
- [ ] Branch is up to date with main

#### Step 2: Create Pull Request
```bash
# Ensure branch is clean
git status

# Push to remote
git push origin feature/TICKET-XXX-description
```

**PR Description Template:**
```markdown
## Ticket
Closes TICKET-XXX

## Summary
[Brief description of what this PR does]

## Changes Made
- [Change 1]
- [Change 2]
- [Change 3]

## Tests Added
- [Test suite 1]: X tests
- [Test suite 2]: Y tests
- Coverage: Z%

## Documentation Updated
- [Documentation file 1]
- [Documentation file 2]

## Breaking Changes
[None / List breaking changes]

## Migration Guide
[If applicable, how to migrate]

## Screenshots/Demo
[If UI changes, add screenshots]

## Checklist
- [x] Tests added and passing
- [x] Documentation updated
- [x] Code self-reviewed
- [x] No lint errors
- [x] Breaking changes documented

## Additional Context
[Any relevant information for reviewers]
```

### Phase 5: Completion

#### Step 1: Move Ticket to Done
Once PR is merged or work is completed:

```bash
# Move ticket file
mv tickets/approved/TICKET-XXX-description.md tickets/done/TICKET-XXX-description.md
```

#### Step 2: Update Implementation Roadmap
In `tickets/approved/IMPLEMENTATION-ROADMAP.md`:
- Mark ticket as ✅ Complete
- Add completion date
- Note any deviations or learnings

#### Step 3: Cleanup
- Delete feature branch after merge
- Close related issues if any
- Update any tracking systems

### Phase 6: Post-Implementation

#### Monitor and Validate
After deployment:
- [ ] Monitor logs for errors
- [ ] Check performance metrics
- [ ] Verify in production/staging
- [ ] Watch for user feedback
- [ ] Be available for questions

#### Document Learnings
If you discovered something valuable during implementation:
- Update documentation with gotchas
- Add notes to help future developers
- Consider creating a ticket if you found new issues

## Quality Standards

### Definition of Done
A ticket is only complete when:
- ✅ All code changes implemented and tested
- ✅ All tests pass (unit, integration, e2e)
- ✅ Code coverage meets standards
- ✅ Manual testing completed
- ✅ Code self-reviewed
- ✅ Documentation updated (code + docs folder)
- ✅ Bilingual documentation created
- ✅ No lint errors or warnings
- ✅ PR created and reviewed (if applicable)
- ✅ Ticket moved to `tickets/done/`
- ✅ Implementation notes added to ticket

### Code Review Standards
When reviewing your own code:

**Ask yourself:**
1. Would I understand this code in 6 months?
2. Are there edge cases I haven't considered?
3. Is this the simplest solution that works?
4. Have I added unnecessary complexity?
5. Would a junior engineer understand this?
6. Are my tests actually testing behavior, not implementation?
7. Have I made the code more maintainable?

**Red flags to check:**
- Functions longer than 50 lines
- More than 3 levels of nesting
- Duplicate code patterns
- Complex conditionals that need comments to understand
- "Magic" numbers without explanation
- Unclear variable names
- Missing error handling

## Common Pitfalls to Avoid

### ❌ Don't:
- Skip tests because "it's simple"
- Leave console.log statements in code
- Commit commented-out code
- Push directly to main branch
- Make changes outside ticket scope
- Forget to update documentation
- Copy-paste code without understanding
- Merge without self-review
- Leave TODOs without creating tickets
- Update code without updating tests

### ✅ Do:
- Write tests first when possible
- Keep commits focused and logical
- Update docs as you code
- Ask for clarification when uncertain
- Refactor as you go
- Consider edge cases
- Think about maintainability
- Leave code better than you found it
- Document complex decisions
- Be proud of your work

## Communication

### When to Ask for Help
Don't hesitate to ask when:
- Ticket requirements are unclear
- You discover the proposed solution won't work
- You find additional issues not in the ticket
- You need architectural guidance
- Estimated effort is significantly different
- You're stuck for more than 2 hours

### When to Create New Tickets
During implementation, if you discover:
- Additional bugs or issues
- Opportunities for improvement
- Technical debt not captured
- Missing test coverage elsewhere
- Related refactoring needs

**Create a new ticket** in `tickets/review-required/` but **don't** expand current ticket scope.

## Git Commit Best Practices

### Commit Early and Often
- Commit logical units of work
- Don't wait until everything is done
- Makes code review easier
- Easier to revert if needed

### Commit Message Format
```
[type] brief description (50 chars or less)

Detailed explanation if needed (wrap at 72 chars):
- What changed
- Why it changed
- Any important context

Refs: TICKET-XXX
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructuring
- `test`: Adding/modifying tests
- `docs`: Documentation changes
- `style`: Formatting, missing semicolons, etc.
- `chore`: Maintenance tasks

### Example Commits
```
feat: add user authentication service

Implements JWT-based authentication with refresh tokens.
Includes password hashing with bcrypt and session management.

Refs: TICKET-042

---

test: add integration tests for auth flow

Covers successful login, failed login, token refresh,
and logout scenarios.

Refs: TICKET-042

---

docs: update authentication documentation

Added bilingual docs for new auth service with usage
examples and configuration guide.

Refs: TICKET-042
```

## File Organization Reminder

Your work should maintain this structure:

```
project/
├── src/
│   ├── [your code changes]
│   └── ...
├── tests/
│   ├── unit/
│   │   └── [your unit tests]
│   ├── integration/
│   │   └── [your integration tests]
│   └── e2e/
│       └── [your e2e tests]
├── docs/
│   ├── [module]/
│   │   ├── README.md (updated)
│   │   ├── specific_doc_eng.md (new/updated)
│   │   └── specific_doc_kor.md (new/updated)
│   └── project.md (updated if needed)
└── tickets/
    ├── approved/ (pick from here)
    │   └── TICKET-XXX.md (add implementation notes)
    └── done/ (move here when complete)
        └── TICKET-XXX.md
```

## Success Metrics

You're doing great when:
- Tests pass on first run after implementation
- Code reviews have minimal feedback
- Documentation is clear enough that others don't ask questions
- Your code requires minimal changes after review
- You complete tickets within estimated time
- You rarely have to revisit completed work
- Other engineers can understand your code without asking
- Test coverage is comprehensive
- Tickets move smoothly from approved → done

---

**Remember: You're not just writing code, you're building a maintainable system. Take pride in quality, not just completion.**

**Done right is better than done fast.**