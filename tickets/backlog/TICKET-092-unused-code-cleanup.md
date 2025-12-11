# TICKET-092: Unused Code Cleanup

## Summary
Audit the codebase for unused/unnecessary code and remove it to improve maintainability.

## Areas to Review

### 1. Unused Modules
- Check for imports that are never used
- Identify dead code paths
- Remove commented-out code blocks

### 2. Deprecated Functions
- Functions marked as deprecated but still present
- Old utility functions replaced by new implementations

### 3. Potential Candidates
Based on preliminary review:
- `langflix/video/` - Only 1 file, may be obsolete
- `langflix/subtitles/` - Only 1 file (overlay.py)
- Check for duplicate utility functions

## Acceptance Criteria
- [ ] Run static analysis to identify unused imports
- [ ] Review each module for dead code
- [ ] Remove confirmed unused code
- [ ] Ensure tests still pass after removal

## Commands for Analysis
```bash
# Find unused imports
pip install vulture
vulture langflix/

# Check import usage
grep -r "from langflix" langflix/ | sort | uniq -c | sort -n
```

## Priority
Low - Technical debt cleanup

## Estimated Effort
2-4 hours
