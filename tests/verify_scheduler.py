
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from langflix.youtube.last_schedule import YouTubeLastScheduleService, LastScheduleConfig

def test_scheduler():
    print("Testing YouTubeLastScheduleService...")
    try:
        scheduler = YouTubeLastScheduleService(LastScheduleConfig())
        print("✅ Service initialized")
        
        # Mock the uploader to avoid actual API calls if possible, or just catch the error if no creds
        # But the user has creds, so it might try to call API.
        # Let's just check if get_next_available_slot returns a datetime
        
        # We can mock the internal map to avoid API call for this test
        scheduler._schedule_map = {
            datetime.now().date().isoformat(): {'00:00': 1}
        }
        
        slot = scheduler.get_next_available_slot()
        print(f"✅ Got next slot: {slot}")
        
        if isinstance(slot, datetime):
            print("✅ Slot is a valid datetime object")
        else:
            print("❌ Slot is not a datetime object")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_scheduler()
