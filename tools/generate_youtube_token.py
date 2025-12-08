#!/usr/bin/env python3
"""
YouTube Token Generator

This script helps generate a valid youtube_token.json file locally,
which can then be deployed to the TrueNAS server.
"""
import os
import sys
import json
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Error: Required libraries not found.")
    print("Please run: pip install google-auth-oauthlib google-api-python-client")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.readonly'
]

def generate_token():
    # Locate credentials file
    auth_dir = project_root / "auth"
    creds_file = auth_dir / "youtube_credentials.json"
    token_file = auth_dir / "youtube_token.json"
    
    if not creds_file.exists():
        # Check legacy location
        assets_creds = project_root / "assets" / "youtube_credentials.json"
        if assets_creds.exists():
            logger.info(f"Found credentials in assets/, copying to auth/...")
            auth_dir.mkdir(exist_ok=True)
            import shutil
            shutil.copy(assets_creds, creds_file)
        else:
            logger.error(f"Credentials file not found at {creds_file}")
            logger.info("Please download OAuth 2.0 Client IDs from Google Cloud Console")
            logger.info(f"and save it as: {creds_file}")
            return False

    logger.info(f"Using credentials from: {creds_file}")
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
        logger.info("Starting OAuth flow...")
        logger.info("A browser window should open. If not, click the link below.")
        
        # Use port 8080 which is commonly allowed in Google Cloud Console
        creds = flow.run_local_server(port=8080)
        
        # Save token
        auth_dir.mkdir(exist_ok=True)
        with open(token_file, 'w') as f:
            f.write(creds.to_json())
            
        logger.info(f"Success! Token saved to: {token_file}")
        logger.info("-" * 50)
        logger.info("NEXT STEPS FOR TRUENAS DEPLOYMENT:")
        logger.info("1. Copy this token file to your TrueNAS server:")
        logger.info(f"   scp {token_file} truenas_user@your-truenas-ip:/mnt/Pool_2/Projects/langflix/auth/")
        logger.info("2. Restart the application container.")
        logger.info("-" * 50)
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate token: {e}")
        return False

if __name__ == "__main__":
    generate_token()
