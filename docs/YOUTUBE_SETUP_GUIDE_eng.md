# YouTube API Setup Guide

## Overview

To use YouTube upload features in LangFlix, you need to set up OAuth 2.0 credentials from Google Cloud Console. This is **different** from the Gemini API key used for LLM features.

## Step-by-Step Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **YouTube Data API v3**:
   - Go to "APIs & Services" → "Library"
   - Search for "YouTube Data API v3"
   - Click "Enable"

### Step 2: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - Choose "External" (for personal use) or "Internal" (for Google Workspace)
   - Fill in required fields (App name, User support email, etc.)
   - Add your email to "Test users" if using External type
   - Save and continue through the steps
4. For Application type, select **"Desktop app"**
5. Give it a name (e.g., "LangFlix YouTube Uploader")
6. Click "Create"
7. **Download the credentials JSON file**

### Step 3: Save Credentials File

1. The downloaded file will be named something like `client_secret_XXXXX.json`
2. Rename it to `youtube_credentials.json`
3. Place it in the **project root directory** (same level as `config.yaml`)

**Example file location:**
```
study_english_with_sutis/
├── config.yaml
├── youtube_credentials.json  ← Place it here
├── langflix/
└── ...
```

### Step 4: Verify File Location

The credentials file should be at:
```bash
/Users/changikchoi/Documents/study_english_with_sutis/youtube_credentials.json
```

You can verify it exists:
```bash
ls -la youtube_credentials.json
```

### Step 5: Test Authentication

1. Start the application
2. Click "Login" in the YouTube section of the UI
3. A browser window should open asking you to sign in with your Google account
4. After authorization, you'll be redirected and authenticated

## File Structure

The credentials file (`youtube_credentials.json`) should look like this:

```json
{
  "installed": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "project_id": "your-project-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uris": ["http://localhost"]
  }
}
```

## Important Notes

### Difference from Gemini API Key

- **Gemini API Key** (in `.env`): Used for LLM text generation
- **YouTube OAuth Credentials** (`youtube_credentials.json`): Used for YouTube API authentication
- These are **separate** and both are needed if you want to use both features

### Security

- `youtube_credentials.json` contains sensitive information
- **Never commit this file to git** (it should be in `.gitignore`)
- Keep it secure and don't share it publicly

### First-Time Authentication

- On first login, a browser window will open
- You'll be asked to sign in with your Google account
- After authorization, a token file (`youtube_token.json`) will be created automatically
- Subsequent logins will use the token file (no browser prompt needed)

## Troubleshooting

### Error: "Credentials file not found"

**Solution:**
1. Verify the file exists: `ls -la youtube_credentials.json`
2. Check it's in the project root directory
3. Verify the file name is exactly `youtube_credentials.json` (case-sensitive)

### Error: "Port 8080 is already in use"

**Solution:**
1. Close any other applications using port 8080
2. Or modify the code to use a different port (requires code change)

### Error: "Access blocked: This app's request is invalid"

**Solution:**
1. Check OAuth consent screen is configured properly
2. Add your email to "Test users" if using External type
3. Verify the OAuth client ID type is "Desktop app"

### Error: "Redirect URI mismatch"

**Solution:**
1. In Google Cloud Console, go to your OAuth 2.0 Client
2. Add `http://localhost:8080/` to authorized redirect URIs
3. If using different port, add that port instead

## Next Steps

After setting up credentials:

1. ✅ Place `youtube_credentials.json` in project root
2. ✅ Click "Login" in the UI
3. ✅ Authorize in browser window
4. ✅ Start scheduling video uploads!

## Related Documentation

- [YouTube Integration Guide](./archive/en/YOUTUBE_INTEGRATION.md) - Full API reference
- [Configuration Guide](./CONFIGURATION_GUIDE.md) - General configuration
- [Troubleshooting Guide](./TROUBLESHOOTING_GUIDE.md) - Common issues and solutions

