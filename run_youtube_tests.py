#!/usr/bin/env python3
"""
YouTube Automation Test Runner
Runs comprehensive tests for YouTube automation system
"""
import sys
import subprocess
import os
from pathlib import Path

def run_tests():
    """Run all YouTube automation tests"""
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
        return 0
    else:
        print(f"\n⚠️  {failed_tests} TESTS FAILED")
        print("❌ Please fix failing tests before deployment")
        return 1

def run_specific_tests(test_pattern=None):
    """Run specific tests based on pattern"""
    if test_pattern:
        print(f"🔍 Running tests matching: {test_pattern}")
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest",
                f"tests/youtube/{test_pattern}",
                "-v",
                "--tb=short",
                "--color=yes"
            ])
            return result.returncode
        except Exception as e:
            print(f"❌ Error running tests: {e}")
            return 1
    else:
        return run_tests()

def run_coverage_tests():
    """Run tests with coverage reporting"""
    print("📊 Running tests with coverage analysis")
    print("=" * 50)
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            "tests/youtube/",
            "--cov=langflix.youtube",
            "--cov-report=html",
            "--cov-report=term-missing",
            "-v"
        ])
        
        print("\n📈 Coverage report generated in htmlcov/index.html")
        return result.returncode
        
    except Exception as e:
        print(f"❌ Error running coverage tests: {e}")
        return 1

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="YouTube Automation Test Runner")
    parser.add_argument("--pattern", help="Run tests matching pattern (e.g., test_schedule_manager.py)")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage analysis")
    
    args = parser.parse_args()
    
    if args.coverage:
        exit_code = run_coverage_tests()
    elif args.pattern:
        exit_code = run_specific_tests(args.pattern)
    else:
        exit_code = run_tests()
    
    sys.exit(exit_code)
