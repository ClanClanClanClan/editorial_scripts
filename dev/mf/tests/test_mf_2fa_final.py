#!/usr/bin/env python3
"""
TEST MF 2FA FINAL - Test with all fixes applied
"""

import sys
from pathlib import Path

# Add the production path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src' / 'extractors'))

print("🚀 TESTING MF WITH ALL FIXES")
print("=" * 50)

try:
    from mf_extractor import ComprehensiveMFExtractor

    mf = ComprehensiveMFExtractor()
    print(f"📍 Start URL: {mf.driver.current_url}")

    # One login attempt with full debug
    login_result = mf.login()

    print(f"\n📊 FINAL RESULT: {login_result}")
    print(f"📍 Final URL: {mf.driver.current_url}")

    if login_result:
        print("✅ MF LOGIN SUCCESSFUL WITH ALL FIXES!")
        print("🏆 2FA WORKING PERFECTLY!")
    else:
        print("❌ MF login failed - check debug output above")

    mf.cleanup()

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()