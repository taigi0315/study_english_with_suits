#!/usr/bin/env python3
"""
LangFlix Test Runner

Run different types of tests:
- Unit tests: Individual component testing
- Functional tests: End-to-end workflow testing
- Integration tests: API interaction testing
- All tests: Complete test suite
"""

import sys
import subprocess
import argparse
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n🔧 {description}")
    print(f"Running: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running {description}")
        print(f"Exit code: {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False

def run_unit_tests():
    """Run unit tests"""
    return run_command([
        sys.executable, "-m", "pytest", 
        "tests/unit/", "-v", "--tb=short"
    ], "Unit Tests")

def run_functional_tests():
    """Run functional tests"""
    return run_command([
        sys.executable, "-m", "pytest", 
        "tests/functional/", "-v", "--tb=short"
    ], "Functional Tests")

def run_integration_tests():
    """Run integration tests"""
    return run_command([
        sys.executable, "-m", "pytest", 
        "tests/integration/", "-v", "--tb=short"
    ], "Integration Tests")

def run_all_tests():
    """Run all tests"""
    return run_command([
        sys.executable, "-m", "pytest", 
        "tests/", "-v", "--tb=short"
    ], "All Tests")

def main():
    parser = argparse.ArgumentParser(description="LangFlix Test Runner")
    parser.add_argument(
        "test_type", 
        choices=["unit", "functional", "integration", "all"],
        help="Type of tests to run"
    )
    parser.add_argument(
        "--coverage", 
        action="store_true",
        help="Run with coverage report"
    )
    
    args = parser.parse_args()
    
    print("🧪 LangFlix Test Runner")
    print("=" * 50)
    
    # Add coverage if requested
    if args.coverage:
        print("📊 Running with coverage report")
    
    success = False
    
    if args.test_type == "unit":
        success = run_unit_tests()
    elif args.test_type == "functional":
        success = run_functional_tests()
    elif args.test_type == "integration":
        success = run_integration_tests()
    elif args.test_type == "all":
        success = run_all_tests()
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
