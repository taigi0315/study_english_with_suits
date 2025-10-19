#!/usr/bin/env python3
"""
Clean up all test outputs from step-by-step testing
"""
import sys
import logging
from pathlib import Path

# Import test utilities
from test_config import clean_all_test_outputs

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main cleanup function"""
    try:
        print("🧹 Cleaning up all step-by-step test outputs...")
        clean_all_test_outputs()
        print("✅ Cleanup completed successfully!")
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
