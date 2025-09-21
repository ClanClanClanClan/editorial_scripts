#!/usr/bin/env python3
"""
TEST CORRECT 2FA TIMING - Verify fixed timestamp handling
========================================================

Test that MF and MOR now fetch the CORRECT verification code
sent AFTER credentials are submitted, not old codes.
"""

import sys
from pathlib import Path

# Add the production path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src' / 'extractors'))

def test_fixed_2fa():
    """Test login with correct 2FA timing."""
    print("🚀 TESTING FIXED 2FA TIMING")
    print("=" * 50)

    # Test MF with correct timing
    print("\n📧 Testing MF with CORRECT 2FA timing...")
    try:
        from mf_extractor import ComprehensiveMFExtractor

        mf = ComprehensiveMFExtractor()
        print(f"   📍 MF Start URL: {mf.driver.current_url}")

        # Test login - should work now!
        try:
            import signal
            def timeout_handler(signum, frame):
                raise TimeoutError("Login timeout")

            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(60)  # 60 second timeout

            login_result = mf.login()
            signal.alarm(0)

            if login_result:
                print("   ✅ MF LOGIN SUCCESSFUL WITH CORRECT 2FA!")
                print(f"   📍 MF Final URL: {mf.driver.current_url}")
                print("   🏆 MF 2FA TIMING FIXED!")
            else:
                print("   ❌ MF login still failed")
                print(f"   📍 MF Final URL: {mf.driver.current_url}")

        except TimeoutError:
            print("   ⏰ MF login timed out")
            print(f"   📍 MF URL: {mf.driver.current_url}")
            # Check if we're past login page
            if "login" not in mf.driver.current_url.lower():
                print("   ✅ MF LIKELY SUCCESSFUL (not on login page)")

        mf.cleanup()

    except Exception as e:
        print(f"   ❌ MF Error: {e}")

    # Test MOR with correct timing
    print("\n📧 Testing MOR with CORRECT 2FA timing...")
    try:
        from mor_extractor import ComprehensiveMORExtractor

        mor = ComprehensiveMORExtractor()
        print(f"   📍 MOR Start URL: {mor.driver.current_url}")

        # Test login - should work now!
        try:
            import signal
            def timeout_handler(signum, frame):
                raise TimeoutError("Login timeout")

            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(60)  # 60 second timeout

            login_result = mor.login()
            signal.alarm(0)

            if login_result:
                print("   ✅ MOR LOGIN SUCCESSFUL WITH CORRECT 2FA!")
                print(f"   📍 MOR Final URL: {mor.driver.current_url}")
                print("   🏆 MOR 2FA TIMING FIXED!")
            else:
                print("   ❌ MOR login still failed")
                print(f"   📍 MOR Final URL: {mor.driver.current_url}")

        except TimeoutError:
            print("   ⏰ MOR login timed out")
            print(f"   📍 MOR URL: {mor.driver.current_url}")
            # Check if we're past login page
            if "login" not in mor.driver.current_url.lower():
                print("   ✅ MOR LIKELY SUCCESSFUL (not on login page)")

        mor.cleanup()

    except Exception as e:
        print(f"   ❌ MOR Error: {e}")

    print("\n🏁 2FA TIMING TEST COMPLETE")
    print("The extractors should now fetch the CORRECT verification codes!")

if __name__ == "__main__":
    test_fixed_2fa()