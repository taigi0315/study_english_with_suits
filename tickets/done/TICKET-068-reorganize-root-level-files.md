# [TICKET-068] Reorganize Root-Level File Structure

## Priority
- [ ] Critical
- [ ] High
- [x] Medium
- [ ] Low

## Type
- [x] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [ ] Feature Request

## Impact Assessment

**Business Impact:**
- **Developer Experience:** Cleaner root directory improves project navigation
- **Maintainability:** Better organization makes it easier to find files
- **Onboarding:** New developers can understand project structure faster
- **Risk of NOT fixing:** Root directory clutter makes project look unprofessional

**Technical Impact:**
- File moves: ~20-30 files
- Path updates: Scripts, docs, config references
- Estimated files affected: 10-15 files (scripts, docs, configs)
- Breaking changes: Minimal (mostly path updates in scripts/docs)

**Effort Estimate:**
- Medium (2-3 days) - Mostly file moves + path updates

## Problem Description

The root directory has accumulated many files over time, making it cluttered and hard to navigate:

**Current Root-Level Files:**
- Docker files: `Dockerfile`, `Dockerfile.dev`, `docker-compose.dev.yml` (plus more in `deploy/`)
- OAuth credentials: `youtube_credentials.json`, `youtube_token.json` (also in `assets/`)
- Config files: `config.yaml`, `config.example.yaml`, `env.example`, `alembic.ini`
- Documentation: `PHASE1_COMPLETION_SUMMARY.md`, `PHASE2_COMPLETION_SUMMARY.md`, `PR_TICKET_036.md`, `SETUP_GUIDE.md`, `YOUTUBE_CREDENTIALS_SETUP.md`, `FILE_ORGANIZATION_PLAN.md`
- Log files: `api.log`, `frontend.log`, `langflix.log`, `test_run.log`
- Build artifacts: `dist/`, `htmlcov/`, `cache/`
- Scripts: `run_tests.py`, `test-local.sh`
- Database: `langflix_youtube.db`
- Other: `Makefile`, `pytest.ini`, `CHANGELOG.md`, `CLAUDE.md`, `CLEANUP_PLAN.md`, `CLEANUP_COMPLETE.md`

**Issues:**
1. **Docker files scattered:** Some in root, some in `deploy/`
2. **OAuth files duplicated:** Both in root and `assets/`
3. **Documentation scattered:** Some in root, some in `docs/`
4. **Log files in root:** Should be in dedicated directory
5. **Build artifacts in root:** Should be in `.gitignore` or `build/`
6. **No clear organization:** Hard to find files

## Proposed Solution

### New Directory Structure

```
langflix/
├── .github/              # GitHub workflows (if any)
├── alembic/              # Database migrations (keep as is)
├── assets/               # Static assets (keep as is)
├── auth/                 # NEW: OAuth credentials and tokens
│   ├── .gitignore        # Ignore all files in this directory
│   ├── youtube_credentials.json.template
│   └── README.md         # Instructions for setting up credentials
├── build/                # NEW: Build artifacts (gitignored)
│   ├── dist/
│   ├── htmlcov/
│   └── cache/
├── config/               # NEW: Configuration files
│   ├── config.yaml
│   ├── config.example.yaml
│   ├── env.example
│   └── alembic.ini
├── deploy/               # Docker and deployment files (consolidate here)
│   ├── docker/
│   │   ├── Dockerfile
│   │   ├── Dockerfile.dev
│   │   └── docker-compose.dev.yml
│   ├── docker-compose.truenas.yml
│   ├── docker-compose.ec2.yml
│   ├── docker-compose.media-server.yml
│   ├── docker-compose.dockge.yml
│   ├── dockge-quick-start.yml
│   ├── Dockerfile.ec2
│   ├── Dockerfile.ec2.with-media
│   ├── ec2-setup.sh
│   ├── run.sh
│   ├── setup-media-mount.sh
│   └── shutdown.sh
├── docs/                 # Documentation (already exists, consolidate)
│   ├── deployment/
│   ├── youtube/
│   ├── ... (existing structure)
│   └── project/          # NEW: Project-level docs
│       ├── PHASE1_COMPLETION_SUMMARY.md
│       ├── PHASE2_COMPLETION_SUMMARY.md
│       ├── PHASE3_COMPLETION_SUMMARY.md
│       ├── PR_TICKET_036.md
│       ├── CHANGELOG.md
│       └── CLEANUP_PLAN.md
├── langflix/             # Source code (keep as is)
├── logs/                 # NEW: Log files (gitignored)
│   ├── .gitkeep
│   └── README.md
├── scripts/              # NEW: Utility scripts
│   ├── run_tests.py
│   ├── test-local.sh
│   └── setup.sh          # Setup script (if needed)
├── tests/                # Tests (keep as is)
├── tickets/              # Tickets (keep as is)
├── tools/                # Development tools (keep as is)
├── .env                  # Environment variables (keep in root, gitignored)
├── .gitignore            # Update to include new directories
├── CLAUDE.md             # Keep in root (important for AI)
├── FILE_ORGANIZATION_PLAN.md  # Move to docs/project/ or delete
├── Makefile              # Keep in root (common convention)
├── pytest.ini            # Keep in root (common convention)
├── README.md             # Keep in root (standard)
└── requirements.txt      # Keep in root (standard)
```

### File Moves

#### 1. Docker Files → `deploy/docker/`
- `Dockerfile` → `deploy/docker/Dockerfile`
- `Dockerfile.dev` → `deploy/docker/Dockerfile.dev`
- `docker-compose.dev.yml` → `deploy/docker/docker-compose.dev.yml`
- Update all references in scripts and docs

#### 2. OAuth Files → `auth/`
- `youtube_credentials.json` → `auth/youtube_credentials.json`
- `youtube_token.json` → `auth/youtube_token.json`
- `youtube_credentials.json.template` → `auth/youtube_credentials.json.template`
- Remove duplicates from `assets/` (keep only in `auth/`)
- Update code references in `langflix/youtube/uploader.py`, `langflix/youtube/web_ui.py`

#### 3. Config Files → `config/`
- `config.yaml` → `config/config.yaml`
- `config.example.yaml` → `config/config.example.yaml`
- `env.example` → `config/env.example`
- `alembic.ini` → `config/alembic.ini`
- Update references in code, scripts, docs

#### 4. Documentation → `docs/project/`
- `PHASE1_COMPLETION_SUMMARY.md` → `docs/project/PHASE1_COMPLETION_SUMMARY.md`
- `PHASE2_COMPLETION_SUMMARY.md` → `docs/project/PHASE2_COMPLETION_SUMMARY.md`
- `PHASE3_COMPLETION_SUMMARY.md` → `docs/project/PHASE3_COMPLETION_SUMMARY.md`
- `PR_TICKET_036.md` → `docs/project/PR_TICKET_036.md`
- `CHANGELOG.md` → `docs/project/CHANGELOG.md`
- `CLEANUP_PLAN.md` → `docs/project/CLEANUP_PLAN.md`
- `CLEANUP_COMPLETE.md` → `docs/project/CLEANUP_COMPLETE.md`
- `SETUP_GUIDE.md` → `docs/SETUP_GUIDE.md` (already exists, merge or replace)
- `YOUTUBE_CREDENTIALS_SETUP.md` → `docs/youtube/YOUTUBE_CREDENTIALS_SETUP.md` (already exists, merge or replace)
- `FILE_ORGANIZATION_PLAN.md` → `docs/project/FILE_ORGANIZATION_PLAN.md` or delete

#### 5. Log Files → `logs/`
- `api.log` → `logs/api.log`
- `frontend.log` → `logs/frontend.log`
- `langflix.log` → `logs/langflix.log`
- `test_run.log` → `logs/test_run.log`
- Update logging configuration in code

#### 6. Build Artifacts → `build/`
- `dist/` → `build/dist/`
- `htmlcov/` → `build/htmlcov/`
- `cache/` → `build/cache/`
- Update `.gitignore`

#### 7. Scripts → `scripts/`
- `run_tests.py` → `scripts/run_tests.py`
- `test-local.sh` → `scripts/test-local.sh`
- Update any references

#### 8. Database Files
- `langflix_youtube.db` → Keep in root (SQLite convention) OR move to `data/` directory
- Consider adding to `.gitignore` if it's a local dev database

### Path Updates Required

#### Code Files
1. **`langflix/youtube/uploader.py`:**
   - Update default paths: `youtube_credentials.json` → `auth/youtube_credentials.json`
   - Update default paths: `youtube_token.json` → `auth/youtube_token.json`

2. **`langflix/youtube/web_ui.py`:**
   - Update credential file paths

3. **`langflix/config/config_loader.py`:**
   - Update default config path: `config.yaml` → `config/config.yaml`

4. **`alembic/env.py`:**
   - Update `alembic.ini` path: `alembic.ini` → `config/alembic.ini`

#### Scripts
1. **`scripts/run_tests.py`:**
   - Update any config paths

2. **`scripts/test-local.sh`:**
   - Update any config paths

3. **`Makefile`:**
   - Update Docker file paths
   - Update config paths

#### Docker Files
1. **All `docker-compose.*.yml` files:**
   - Update volume mounts for config files
   - Update volume mounts for auth files
   - Update build context paths

2. **All `Dockerfile*` files:**
   - Update COPY paths for config files
   - Update COPY paths for auth files

#### Documentation
1. **All docs referencing file paths:**
   - Update setup guides
   - Update deployment guides
   - Update README files

## Implementation Steps

### Phase 1: Create New Directories
1. Create `auth/` directory with `.gitignore`
2. Create `config/` directory
3. Create `logs/` directory with `.gitkeep`
4. Create `build/` directory (gitignored)
5. Create `scripts/` directory
6. Create `docs/project/` directory
7. Create `deploy/docker/` directory

### Phase 2: Move Files
1. Move Docker files to `deploy/docker/`
2. Move OAuth files to `auth/`
3. Move config files to `config/`
4. Move documentation to `docs/project/`
5. Move log files to `logs/`
6. Move build artifacts to `build/`
7. Move scripts to `scripts/`

### Phase 3: Update References
1. Update code references (credentials, config paths)
2. Update script references
3. Update Docker compose files
4. Update Dockerfiles
5. Update Makefile
6. Update documentation

### Phase 4: Update .gitignore
1. Add `auth/*` (except templates)
2. Add `logs/*`
3. Add `build/*`
4. Add `*.db` (if moving database)

### Phase 5: Testing
1. Verify all paths work
2. Test Docker builds
3. Test scripts
4. Test application startup
5. Verify documentation links

## Testing Strategy

### Unit Tests
- Test config loading with new paths
- Test credential file loading with new paths

### Integration Tests
- Test Docker builds with new file structure
- Test application startup with new paths
- Test scripts with new paths

### Manual Testing
- Run full application
- Test Docker compose setups
- Verify all file references work
- Check documentation links

## Files Affected

**New Directories:**
- `auth/`
- `config/`
- `logs/`
- `build/`
- `scripts/`
- `docs/project/`
- `deploy/docker/`

**Files to Move:** ~25-30 files

**Files to Update:**
- `langflix/youtube/uploader.py`
- `langflix/youtube/web_ui.py`
- `langflix/config/config_loader.py`
- `alembic/env.py`
- `Makefile`
- All `docker-compose.*.yml` files
- All `Dockerfile*` files
- Documentation files
- `.gitignore`

## Dependencies

- **Depends on:** None
- **Blocks:** None (can be done independently)
- **Related to:** TICKET-061 (Multi-platform upload - will need to update paths for new platforms)

## Success Criteria

- [ ] All files moved to appropriate directories
- [ ] All code references updated
- [ ] All script references updated
- [ ] All Docker files updated
- [ ] All documentation updated
- [ ] Application starts successfully
- [ ] Docker builds work
- [ ] Scripts work
- [ ] Tests pass
- [ ] `.gitignore` updated
- [ ] Root directory is clean and organized
- [ ] Documentation includes migration guide

## Known Limitations

- Some tools/scripts may have hardcoded paths
- Docker volume mounts need careful updating
- Documentation links need updating
- May require coordination if team members have local changes

## Migration Guide

After reorganization, users need to:
1. Move their local `config.yaml` to `config/config.yaml`
2. Move their local `youtube_credentials.json` to `auth/youtube_credentials.json`
3. Update any custom scripts referencing old paths
4. Pull latest changes and adapt

## Additional Notes

- This is a **breaking change** for local development setups
- Should be done before major feature work (like multi-platform upload)
- Consider creating a migration script to help users
- Update all setup documentation
- Consider semantic versioning if this affects users

