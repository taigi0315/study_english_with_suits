# [TICKET-083] Refactor Deployment Script (run.sh)

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [ ] High (Performance issues, significant tech debt)
- [x] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [x] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [x] Technical Debt
- [ ] Code Duplication

## Impact Assessment
**Business Impact:**
- **Deployment Reliability**: Complex shell scripts hide errors and make deployments flaky.
- **Onboarding**: New engineers struggle to understand how the system starts.

**Technical Impact:**
- **Files**: `deploy/run.sh`
- **Effort**: Medium (1-2 days)

## Problem Description

### Current State
**Location:** `deploy/run.sh`

The `run.sh` script is 23KB (500 lines) of Bash. It handles:
- Environment variable loading
- Docker Compose v1 vs v2 detection
- Database migrations
- "Dev" vs "Prod" modes
- Sudo/Functions/Traps

Large bash scripts are brittle, hard to debug, and platform-dependent (macOS vs Linux `sed` differences, etc).

### Root Cause Analysis
- **Organic Growth**: Features added one by one ("Add database check", "Add network check", "Add dry run").

## Proposed Solution

### Approach
Migrate complex orchestration logic to Python (`deploy/cli.py`) or use a `Makefile` for simple command aliasing. Python is preferred for cross-platform compatibility and readability.

### Implementation Details

**Option A: Python CLI (`manage.py` style)**

```python
# deploy/manager.py
import subprocess
import argparse
import sys

def check_docker():
    # python logic to check docker
    pass

def load_env():
    # python-dotenv logic
    pass

def up(args):
    # build docker-compose command list
    cmd = ["docker-compose", "-f", "docker-compose.yml", "up"]
    subprocess.run(cmd)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    # ...
```

**Option B: Modular Bash + Makefile**
Split `run.sh` into `scripts/check_env.sh`, `scripts/docker_up.sh`, etc., and use a simple Makefile:

```makefile
setup:
    ./scripts/check_env.sh

run: setup
    ./scripts/docker_up.sh
```

**Recommendation**: Option A (Python) is robust for "Langflix" since it's a Python project.

### Benefits
- **Debuggability**: Can use PDB or print debugging.
- **Readability**: Python is more readable than Bash for complex logic.
- **Error Handling**: Try/Except blocks are better than `set -e` or `trap`.

## Risks & Considerations
- **Python Dependency**: Requires Python to be installed on the host machine (which is true, but requires `requirements.txt` potentially).
    - **Mitigation**: Use standard library only (`subprocess`, `os`, `sys`, `argparse`) so no `pip install` is needed on host.

## Testing Strategy
- Verify all commands (start, stop, build, shell) work on macOS and Linux (TrueNAS).

## Files Affected
- `deploy/run.sh` (Deprecated/Removed)
- `deploy/manager.py` (New)
- `README.md` (Update instructions)

## Success Criteria
- [ ] `deploy/run.sh` replaced by `python3 deploy/manager.py` (or similar).
- [ ] Deployment logic is readable and organized.
