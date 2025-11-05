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

### Step 5: Configure Redirect URI (For Email-Based Login) ⚠️ Required!

**Important:** To use email-based login (Web OAuth flow), you **must** add the redirect URI in Google Cloud Console. Without this, you'll get "Error 400: redirect_uri_mismatch".

1. Go back to Google Cloud Console → "APIs & Services" → "Credentials"
2. Click on your OAuth 2.0 Client ID
3. Under "Authorized redirect URIs", click "ADD URI"
4. Add: `http://localhost:5000/api/youtube/auth/callback`
5. (Optional) Also add: `http://127.0.0.1:5000/api/youtube/auth/callback`
6. Click "Save"

**Important:** Even if you downloaded "Desktop app" credentials, you can still add this redirect URI for web flow support. The redirect URI in the credentials file will be updated automatically, but you **must also add it in Google Cloud Console**.

**Note:** After adding the URI in Google Cloud Console, it may take 1-2 minutes for changes to propagate.

### Step 6: Test Authentication

LangFlix supports two authentication methods:

**Option 1: Email-Based Login (Recommended)**
- **Requires:** Redirect URI configured in Step 5
- **Steps:**
  1. Start the application
  2. Enter your Google email address in the input field (optional but recommended)
  3. Click "Login to YouTube"
  4. A popup window will open asking you to sign in with your Google account
  5. After authorization, the popup will close automatically and you'll be authenticated
- **Benefits:**
  - Better control over which Google account to use
  - More user-friendly web-based experience
  - No automatic browser opening

**Option 2: Default Browser Login (Desktop Flow)**
- **Requires:** Only `youtube_credentials.json` file
- **Steps:**
  1. Start the application
  2. Leave the email field empty
  3. Click "Login to YouTube"
  4. Your default browser will open automatically for authentication
- **Benefits:**
  - No redirect URI configuration needed
  - Simpler setup for basic usage

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

### Error: "Redirect URI mismatch" or "Error 400: redirect_uri_mismatch"

This error occurs when the redirect URI used by the application doesn't match what's configured in Google Cloud Console.

**Solution:**
1. In Google Cloud Console, go to "APIs & Services" → "Credentials"
2. Click on your OAuth 2.0 Client ID
3. Under "Authorized redirect URIs", add:
   - `http://localhost:5000/api/youtube/auth/callback` (required for email login)
   - `http://127.0.0.1:5000/api/youtube/auth/callback` (optional)
4. Click "Save"
5. Wait 1-2 minutes for changes to propagate
6. Try logging in again

**Note:** The redirect URI in your `youtube_credentials.json` file will be updated automatically by the application, but you **must also add it manually in Google Cloud Console**.

For more detailed troubleshooting, see [REDIRECT_URI_FIX_eng.md](./youtube/REDIRECT_URI_FIX_eng.md).

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

