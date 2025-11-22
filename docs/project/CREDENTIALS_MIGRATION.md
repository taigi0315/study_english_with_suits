# YouTube Credentials Migration Guide

**Date:** 2025-01-22  
**Related:** TICKET-068 (File Structure Reorganization)

## Quick Fix

If you're getting "YouTube credentials file not found" error after the file structure reorganization:

### Option 1: Move Your Existing File (Recommended)

If you have `youtube_credentials.json` in an old location:

```bash
# Check if file exists in old locations
ls -la assets/youtube_credentials.json
ls -la youtube_credentials.json

# Move to new location
mv assets/youtube_credentials.json auth/youtube_credentials.json
# OR
mv youtube_credentials.json auth/youtube_credentials.json
```

### Option 2: Create New Credentials

If you don't have the file:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Download OAuth 2.0 credentials
3. Save as `auth/youtube_credentials.json`

See `docs/youtube/YOUTUBE_SETUP_GUIDE_eng.md` for detailed instructions.

## Backward Compatibility

The code now automatically checks multiple locations:
1. `auth/youtube_credentials.json` (new location)
2. `assets/youtube_credentials.json` (old location)
3. `youtube_credentials.json` (root, legacy)

**However, for best results, please move your file to `auth/` directory.**

## Verification

After moving the file:

```bash
# Check file exists
ls -la auth/youtube_credentials.json

# Test in Python
python -c "from langflix.youtube.uploader import YouTubeUploader; u = YouTubeUploader(); print('Credentials path:', u.credentials_file)"
```

## Troubleshooting

### "File not found" even after moving

1. Check file permissions:
   ```bash
   ls -la auth/youtube_credentials.json
   ```

2. Check file is valid JSON:
   ```bash
   python -c "import json; json.load(open('auth/youtube_credentials.json'))"
   ```

3. Check you're running from project root:
   ```bash
   pwd  # Should be /path/to/langflix
   ```

### Symlink Issues

If you see a broken symlink:
```bash
# Remove broken symlink
rm auth/youtube_credentials.json

# Copy actual file
cp assets/youtube_credentials.json auth/youtube_credentials.json
```

