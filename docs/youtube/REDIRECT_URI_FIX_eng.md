# Redirect URI Mismatch Error Resolution Guide

## 🔴 Error: "Error 400: redirect_uri_mismatch"

This error occurs when the redirect URI registered in Google Cloud Console doesn't match the URI used in the code.

## ✅ Solution

### Step 1: Add Redirect URI in Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select project: **gen-lang-client-0804178165**
3. Navigate to "APIs & Services" → "Credentials"
4. Click on OAuth 2.0 Client ID (the one starting with 560775166705-...)
5. Find "Authorized redirect URIs" section
6. Click "ADD URI" button
7. Enter the following URI:
   ```
   http://localhost:5000/api/youtube/auth/callback
   ```
8. (Optional) Add additional URI:
   ```
   http://127.0.0.1:5000/api/youtube/auth/callback
   ```
9. Click "SAVE" button

### Step 2: Verification

Redirect URI used in code:
- `http://localhost:5000/api/youtube/auth/callback`

The `youtube_credentials.json` file already contains this:
```json
"redirect_uris": [
  ...
  "http://localhost:5000/api/youtube/auth/callback"
]
```

**However, you MUST also add it in Google Cloud Console!**

### Step 3: Wait for Changes to Apply

After adding the URI in Google Cloud Console:
- Changes may apply immediately, but sometimes it can take 1-2 minutes
- Clear browser cache and try again

### Step 4: Test

1. Complete redirect URI addition in Google Cloud Console
2. Restart application (optional)
3. Enter email and click "Login to YouTube"
4. Proceed with Google login in popup

## 🔍 Debugging

If the error still occurs:

1. **Verify exact URI:**
   ```bash
   # Check URI used in code
   grep -r "redirect_uri" langflix/youtube/web_ui.py
   ```

2. **Verify in Google Cloud Console:**
   - OAuth client ID edit screen
   - Check that "Authorized redirect URIs" list contains:
     - `http://localhost:5000/api/youtube/auth/callback`
   
3. **Verify in file:**
   ```bash
   cat youtube_credentials.json | grep -A 5 redirect
   ```

## 📌 Important Notes

- Even if the URI exists in the **file (`youtube_credentials.json`)**, you **MUST also add it in Google Cloud Console**
- URIs must match exactly (case-sensitive, including slashes)
- Verify port number matches (5000)
