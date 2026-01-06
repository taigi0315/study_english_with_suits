# YouTube Multi-Account Support & Upload Fixes

## Description

Support multiple YouTube channels (Brand Accounts) and fix upload issues including title generation failures.

## Tasks

- [x] Implement multi-token architecture in backend (YouTubeUploadManager)
- [x] Update frontend to fetch and display channel list
- [x] Add "Add Account" flow with popup authentication
- [x] Fix "Invalid Title" error by implementing smart fallback logic (Expression | Show Name)
- [x] Enforce 100-character title limit in YouTubeUploader to prevent API rejection
