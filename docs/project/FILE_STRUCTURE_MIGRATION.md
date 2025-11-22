# File Structure Migration Guide

**Date:** 2025-01-21  
**Ticket:** TICKET-068

## Overview

The project root directory has been reorganized to improve structure and maintainability. This guide helps you migrate your local setup to the new structure.

## What Changed

### Directory Structure

**New Directories:**
- `auth/` - OAuth credentials and tokens
- `config/` - Configuration files
- `logs/` - Log files
- `build/` - Build artifacts
- `scripts/` - Utility scripts
- `docs/project/` - Project-level documentation
- `deploy/docker/` - Docker files

### File Moves

| Old Location | New Location |
|-------------|--------------|
| `youtube_credentials.json` | `auth/youtube_credentials.json` |
| `youtube_token.json` | `auth/youtube_token.json` |
| `config.yaml` | `config/config.yaml` |
| `config.example.yaml` | `config/config.example.yaml` |
| `env.example` | `config/env.example` |
| `alembic.ini` | `config/alembic.ini` |
| `Dockerfile` | `deploy/docker/Dockerfile` |
| `Dockerfile.dev` | `deploy/docker/Dockerfile.dev` |
| `docker-compose.dev.yml` | `deploy/docker/docker-compose.dev.yml` |
| `run_tests.py` | `scripts/run_tests.py` |
| `test-local.sh` | `scripts/test-local.sh` |
| `*.log` files | `logs/*.log` |
| `dist/`, `htmlcov/`, `cache/` | `build/dist/`, `build/htmlcov/`, `build/cache/` |

## Migration Steps

### 1. Update Configuration Files

If you have a local `config.yaml`:

```bash
# Move your config file
mv config.yaml config/config.yaml
```

If you don't have one yet:

```bash
# Copy from example
cp config/config.example.yaml config/config.yaml
```

### 2. Update OAuth Credentials

If you have YouTube credentials:

```bash
# Move credentials
mv youtube_credentials.json auth/youtube_credentials.json
mv youtube_token.json auth/youtube_token.json
```

**Note:** If you have credentials in `assets/`, they should be moved to `auth/` as well.

### 3. Update Docker Usage

If you use Docker Compose for development:

```bash
# Old command
docker-compose -f docker-compose.dev.yml up

# New command
docker-compose -f deploy/docker/docker-compose.dev.yml up
```

Or use the Makefile (already updated):

```bash
make docker-up
```

### 4. Update Script Usage

If you run tests manually:

```bash
# Old command
python run_tests.py

# New command
python scripts/run_tests.py
```

### 5. Update Environment Variables (Optional)

If you set custom paths via environment variables:

```bash
# Old
export YOUTUBE_CREDENTIALS_FILE="youtube_credentials.json"

# New
export YOUTUBE_CREDENTIALS_FILE="auth/youtube_credentials.json"
```

## Code Changes

The following code files have been updated automatically:

- `langflix/youtube/uploader.py` - Default paths updated
- `langflix/youtube/web_ui.py` - Default paths updated
- `langflix/config/config_loader.py` - Config path updated
- All Docker compose files - Volume mounts updated
- `Makefile` - Docker paths updated

## Docker Deployment

For Docker deployments, update volume mounts:

**Old:**
```yaml
volumes:
  - ../config.yaml:/app/config.yaml:ro
  - ../youtube_credentials.json:/app/youtube_credentials.json:ro
```

**New:**
```yaml
volumes:
  - ../config/config.yaml:/app/config/config.yaml:ro
  - ../auth/youtube_credentials.json:/app/auth/youtube_credentials.json:ro
```

## Alembic Migrations

If you use Alembic for database migrations:

```bash
# Alembic will automatically find config/alembic.ini
alembic upgrade head
```

If you need to specify the config file explicitly:

```bash
alembic -c config/alembic.ini upgrade head
```

## Verification

After migration, verify everything works:

1. **Check config loading:**
   ```bash
   python -c "from langflix.config.config_loader import ConfigLoader; print(ConfigLoader().config)"
   ```

2. **Check credentials (if using YouTube):**
   ```bash
   ls -la auth/youtube_credentials.json
   ```

3. **Test Docker (if using):**
   ```bash
   make docker-up
   ```

4. **Run tests:**
   ```bash
   python scripts/run_tests.py unit
   ```

## Troubleshooting

### "Config file not found"

**Solution:** Ensure `config/config.yaml` exists:
```bash
cp config/config.example.yaml config/config.yaml
```

### "YouTube credentials not found"

**Solution:** Move credentials to `auth/`:
```bash
mv youtube_credentials.json auth/youtube_credentials.json
mv youtube_token.json auth/youtube_token.json
```

### "Docker compose file not found"

**Solution:** Use the new path:
```bash
docker-compose -f deploy/docker/docker-compose.dev.yml up
```

### "Script not found"

**Solution:** Use the new path:
```bash
python scripts/run_tests.py
```

## Backward Compatibility

The code includes fallback logic to check old locations, but this is temporary. Please migrate to the new structure as soon as possible.

## Questions?

If you encounter issues during migration, please:
1. Check this guide first
2. Review the ticket: `tickets/review-required/TICKET-068-reorganize-root-level-files.md`
3. Check the updated documentation in `docs/`

