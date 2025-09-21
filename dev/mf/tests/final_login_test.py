#!/usr/bin/env python3
"""
FINAL LOGIN TEST - Test both MF and MOR login with fixes
=======================================================

Quick test to see if both extractors can login successfully.
"""

import sys
from pathlib import Path

# Add the production path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src' / 'extractors'))

def test_final_login():
    """Test login for both MF and MOR."""
    print("🚀 FINAL LOGIN TEST - BOTH EXTRACTORS")
    print("=" * 50)

    # Test MF Login
    print("\n🔍 Testing MF Login...")
    try:
        from mf_extractor import ComprehensiveMFExtractor

        mf = ComprehensiveMFExtractor()
        print(f"   📍 MF Start URL: {mf.driver.current_url}")

        # Quick login attempt (will timeout on 2FA)
        try:
            import signal
            def timeout_handler(signum, frame):
                raise TimeoutError("Login timeout")

            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(75)  # 75 second timeout

            login_result = mf.login()
            signal.alarm(0)

            if login_result:
                print("   ✅ MF LOGIN SUCCESSFUL!")
                print(f"   📍 MF Final URL: {mf.driver.current_url}")
            else:
                print("   ❌ MF login failed")
                print(f"   📍 MF Final URL: {mf.driver.current_url}")

        except TimeoutError:
            print("   ⏰ MF login timed out (probably at 2FA)")
            print(f"   📍 MF URL: {mf.driver.current_url}")

        mf.cleanup()

    except Exception as e:
        print(f"   ❌ MF Error: {e}")

    # Test MOR Login
    print("\n🔍 Testing MOR Login...")
    try:
        from mor_extractor import ComprehensiveMORExtractor

        mor = ComprehensiveMORExtractor()
        print(f"   📍 MOR Start URL: {mor.driver.current_url}")

        # Quick login attempt (will timeout on 2FA)
        try:
            import signal
            def timeout_handler(signum, frame):
                raise TimeoutError("Login timeout")

            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(75)  # 75 second timeout

            login_result = mor.login()
            signal.alarm(0)

            if login_result:
                print("   ✅ MOR LOGIN SUCCESSFUL!")
                print(f"   📍 MOR Final URL: {mor.driver.current_url}")
            else:
                print("   ❌ MOR login failed")
                print(f"   📍 MOR Final URL: {mor.driver.current_url}")

        except TimeoutError:
            print("   ⏰ MOR login timed out (probably at 2FA)")
            print(f"   📍 MOR URL: {mor.driver.current_url}")

        mor.cleanup()

    except Exception as e:
        print(f"   ❌ MOR Error: {e}")

    print("\n🏁 FINAL LOGIN TEST COMPLETE")

if __name__ == "__main__":
    test_final_login()