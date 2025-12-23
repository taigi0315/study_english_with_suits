#!/usr/bin/env python3
"""
LangFlix Test Runner

Run different types of tests:
- Unit tests: Individual component testing
- Functional tests: End-to-end workflow testing
- Integration tests: API interaction testing
- YouTube tests: YouTube automation system tests
- All tests: Complete test suite
"""

import sys
import subprocess
import argparse
import os
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

def run_youtube_tests(detailed=False):
    """Run YouTube automation tests with optional detailed reporting"""
    if detailed:
        return run_youtube_tests_detailed()
    else:
        return run_command([
            sys.executable, "-m", "pytest", 
            "tests/youtube/", "-v", "--tb=short"
        ], "YouTube Tests")

def run_youtube_tests_detailed():
    """Run YouTube tests with detailed category-based reporting"""
    print("🧪 Running YouTube Automation Tests")
    print("=" * 50)
    
    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # Test categories
    test_categories = [
        {
            "name": "Schedule Manager Tests",
            "path": "tests/youtube/test_schedule_manager.py",
            "description": "Tests scheduling logic, daily limits, and quota management"
        },
        {
            "name": "Uploader Tests", 
            "path": "tests/youtube/test_uploader.py",
            "description": "Tests YouTube uploader, authentication, and channel management"
        },
        {
            "name": "Video Manager Tests",
            "path": "tests/youtube/test_video_manager.py", 
            "description": "Tests video scanning, metadata extraction, and filtering"
        },
        {
            "name": "Metadata Generator Tests",
            "path": "tests/youtube/test_metadata_generator.py",
            "description": "Tests metadata generation and template handling"
        },
        {
            "name": "Web UI API Tests",
            "path": "tests/youtube/test_web_ui_api.py",
            "description": "Tests all API endpoints and error handling"
        },
        {
            "name": "Integration Tests",
            "path": "tests/youtube/test_integration.py",
            "description": "Tests end-to-end workflows and system integration"
        }
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for category in test_categories:
        print(f"\n📋 {category['name']}")
        print(f"   {category['description']}")
        print("-" * 50)
        
        try:
            # Run tests for this category
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                category["path"],
                "-v",
                "--tb=short",
                "--color=yes"
            ], capture_output=True, text=True)
            
            # Parse results
            passed = 0
            failed = 0
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if "passed" in line and "failed" in line:
                    # Extract test counts
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "passed":
                            passed = int(parts[i-1])
                        elif part == "failed":
                            failed = int(parts[i-1])
                    
                    total_tests += passed + failed
                    passed_tests += passed
                    failed_tests += failed
                    break
                elif "passed" in line and "failed" not in line:
                    # Only passed tests
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "passed":
                            passed = int(parts[i-1])
                    
                    total_tests += passed
                    passed_tests += passed
                    break
            
            if result.returncode == 0:
                print(f"✅ {category['name']} - PASSED")
            else:
                print(f"❌ {category['name']} - FAILED")
                print("Error output:")
                print(result.stderr)
                
        except Exception as e:
            print(f"❌ {category['name']} - ERROR: {e}")
            failed_tests += 1
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    
    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ YouTube automation system is ready for production")
        return True
    else:
        print(f"\n⚠️  {failed_tests} TESTS FAILED")
        print("❌ Please fix failing tests before deployment")
        return False

def run_all_tests():
    """Run all tests"""
    return run_command([
        sys.executable, "-m", "pytest", 
        "tests/", "-v", "--tb=short", "--ignore=tests/broken"
    ], "All Tests")

def run_coverage_tests(test_path="tests/"):
    """Run tests with coverage reporting"""
    print("📊 Running tests with coverage analysis")
    print("=" * 50)
    
    try:
        cmd = [
            sys.executable, "-m", "pytest",
            test_path,
            "--cov=langflix",
            "--cov-report=html",
            "--cov-report=term-missing",
            "-v"
        ]
        
        result = subprocess.run(cmd, check=True)
        print("\n📈 Coverage report generated in htmlcov/index.html")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running coverage tests: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="LangFlix Test Runner")
    parser.add_argument(
        "test_type", 
        choices=["unit", "functional", "integration", "youtube", "all"],
        help="Type of tests to run"
    )
    parser.add_argument(
        "--coverage", 
        action="store_true",
        help="Run with coverage report"
    )
    parser.add_argument(
        "--detailed", 
        action="store_true",
        help="Run with detailed reporting (applies to YouTube tests)"
    )
    parser.add_argument(
        "--pattern", 
        help="Run tests matching pattern (e.g., test_schedule_manager.py for YouTube tests)"
    )
    
    args = parser.parse_args()
    
    print("🧪 LangFlix Test Runner")
    print("=" * 50)
    
    # Handle coverage mode
    if args.coverage:
        print("📊 Running with coverage report")
        if args.test_type == "youtube":
            success = run_coverage_tests("tests/youtube/")
        else:
            success = run_coverage_tests()
        
        if success:
            print("\n✅ Coverage tests completed!")
            sys.exit(0)
        else:
            print("\n❌ Coverage tests failed!")
            sys.exit(1)
    
    # Handle pattern matching for YouTube tests
    if args.pattern and args.test_type == "youtube":
        print(f"🔍 Running YouTube tests matching: {args.pattern}")
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest",
                f"tests/youtube/{args.pattern}",
                "-v",
                "--tb=short",
                "--color=yes"
            ])
            sys.exit(result.returncode)
        except Exception as e:
            print(f"❌ Error running pattern tests: {e}")
            sys.exit(1)
    
    success = False
    
    if args.test_type == "unit":
        success = run_unit_tests()
    elif args.test_type == "functional":
        success = run_functional_tests()
    elif args.test_type == "integration":
        success = run_integration_tests()
    elif args.test_type == "youtube":
        success = run_youtube_tests(detailed=args.detailed)
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
