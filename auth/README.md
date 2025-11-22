# Authentication Credentials Directory

This directory contains OAuth credentials and tokens for various platforms.

## Setup Instructions

### YouTube Credentials

1. Download OAuth 2.0 credentials from [Google Cloud Console](https://console.cloud.google.com/)
2. Rename the downloaded file to `youtube_credentials.json`
3. Place it in this directory: `auth/youtube_credentials.json`
4. The `youtube_token.json` file will be created automatically after first authentication

### Template Files

- `youtube_credentials.json.template` - Template showing the expected structure

## Security

⚠️ **IMPORTANT:** Never commit credential files to git!

All credential files (`.json`) are automatically ignored by `.gitignore`. Only template files are tracked.

## File Structure

```
auth/
├── .gitignore                    # Ignores all credential files
├── README.md                     # This file
├── youtube_credentials.json      # Your YouTube OAuth credentials (gitignored)
├── youtube_token.json           # YouTube access token (gitignored)
└── youtube_credentials.json.template  # Template file (tracked)
```

## Troubleshooting

If you see "Credentials file not found" errors:
1. Verify the file exists: `ls -la auth/youtube_credentials.json`
2. Check the file name is exactly correct (case-sensitive)
3. Ensure you're running from the project root directory

