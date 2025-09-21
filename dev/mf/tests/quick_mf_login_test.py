#!/usr/bin/env python3
"""
QUICK MF LOGIN TEST - Test one login attempt with debug output
"""

import sys
from pathlib import Path

# Add the production path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src' / 'extractors'))

from mf_extractor import ComprehensiveMFExtractor

print("🚀 QUICK MF LOGIN TEST")
print("=" * 50)

try:
    mf = ComprehensiveMFExtractor()
    print(f"📍 Start URL: {mf.driver.current_url}")

    # One single login attempt
    result = mf.login()

    print(f"\n📊 LOGIN RESULT: {result}")
    print(f"📍 Final URL: {mf.driver.current_url}")

    if result:
        print("✅ LOGIN SUCCESSFUL!")
    else:
        print("❌ Login failed")

    mf.cleanup()

except Exception as e:
    print(f"❌ Error: {e}")