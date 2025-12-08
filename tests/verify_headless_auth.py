import os
import sys
import logging

# Add project root to path
sys.path.append(os.getcwd())

from langflix.youtube.uploader import YouTubeUploader

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_headless_auth():
    print("Testing headless auth...")
    
    # Simulate headless environment
    os.environ["LANGFLIX_HEADLESS"] = "true"
    
    # Initialize uploader with non-existent credentials file to force auth flow
    uploader = YouTubeUploader(credentials_file="non_existent_creds.json")
    
    try:
        # This should return False, not raise an exception
        result = uploader.authenticate()
        print(f"Result: {result}")
        
        if result is False:
            print("SUCCESS: authenticate() returned False in headless mode")
        else:
            print("FAILURE: authenticate() returned True (unexpected)")
            
    except Exception as e:
        print(f"FAILURE: authenticate() raised exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_headless_auth()
