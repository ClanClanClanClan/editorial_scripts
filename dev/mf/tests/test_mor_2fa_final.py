#!/usr/bin/env python3
"""
TEST MOR 2FA FINAL - Test with all fixes applied
"""

import sys
from pathlib import Path

# Add the production path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src' / 'extractors'))

print("🚀 TESTING MOR WITH ALL FIXES")
print("=" * 50)

try:
    from mor_extractor import ComprehensiveMORExtractor

    mor = ComprehensiveMORExtractor()
    print(f"📍 Start URL: {mor.driver.current_url}")

    # One login attempt with full debug
    login_result = mor.login()

    print(f"\n📊 FINAL RESULT: {login_result}")
    print(f"📍 Final URL: {mor.driver.current_url}")

    if login_result:
        print("✅ MOR LOGIN SUCCESSFUL WITH ALL FIXES!")
        print("🏆 2FA WORKING PERFECTLY!")
    else:
        print("❌ MOR login failed - check debug output above")

    mor.cleanup()

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()