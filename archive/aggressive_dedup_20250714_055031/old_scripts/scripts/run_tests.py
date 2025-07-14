#!/usr/bin/env python3
"""
Run all tests for the unified extraction system
"""

import sys
import subprocess
from pathlib import Path

def run_tests():
    """Run all tests and display results"""
    print("🧪 RUNNING UNIFIED SYSTEM TESTS")
    print("=" * 60)
    
    # Find all test files
    test_dir = Path("unified_system/tests")
    test_files = list(test_dir.glob("test_*.py"))
    
    if not test_files:
        print("❌ No test files found!")
        return 1
    
    print(f"📋 Found {len(test_files)} test files:")
    for test_file in test_files:
        print(f"  - {test_file.name}")
    
    print("\n" + "=" * 60)
    
    # Run pytest
    cmd = [
        sys.executable, "-m", "pytest",
        "unified_system/tests",
        "-v",  # Verbose
        "--tb=short",  # Short traceback
        "--color=yes",  # Colored output
    ]
    
    try:
        # Run tests
        result = subprocess.run(cmd, capture_output=False)
        
        print("\n" + "=" * 60)
        
        if result.returncode == 0:
            print("✅ ALL TESTS PASSED!")
        else:
            print("❌ SOME TESTS FAILED!")
            print("Please check the output above for details.")
        
        return result.returncode
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running tests: {e}")
        return 1
    except FileNotFoundError:
        print("❌ pytest not found. Install with: pip install pytest")
        return 1


def check_dependencies():
    """Check if required test dependencies are installed"""
    print("🔍 Checking test dependencies...")
    
    required = ["pytest", "pytest-asyncio"]
    missing = []
    
    for package in required:
        try:
            __import__(package.replace("-", "_"))
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package}")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        return False
    
    return True


if __name__ == "__main__":
    print("🚀 UNIFIED SYSTEM TEST RUNNER")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    print()
    
    # Run tests
    exit_code = run_tests()
    
    # Summary
    print("\n💡 Test Coverage Areas:")
    print("  - Base extractor functionality")
    print("  - SIAM extractor implementation") 
    print("  - Data models (Manuscript, Referee)")
    print("  - PDF download capabilities")
    print("  - Authentication flows")
    
    print("\n📝 To run specific tests:")
    print("  pytest unified_system/tests/test_base_extractor.py")
    print("  pytest unified_system/tests/test_siam_extractors.py -k 'test_manuscript_extraction'")
    
    sys.exit(exit_code)