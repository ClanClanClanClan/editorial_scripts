#!/usr/bin/env python3
"""
TEST MF LOGIN - Compare with MOR
================================

Test if MF login actually works as claimed.
"""

import sys
from pathlib import Path

# Add the production path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src' / 'extractors'))

def test_mf_login():
    """Test MF login process."""
    print("🚀 Testing MF login process...")

    try:
        from mf_extractor import ComprehensiveMFExtractor
        print("✅ MF extractor imported successfully")

        # Create extractor
        print("📝 Creating MF extractor...")
        extractor = ComprehensiveMFExtractor()

        # Test login method - just see how far it gets
        print("🔐 Testing MF login method...")
        try:
            # Use a very short timeout to avoid waiting
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError("Login test timeout")

            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)  # 30 second timeout

            login_result = extractor.login()
            signal.alarm(0)  # Cancel alarm

            print(f"🔍 MF Login result: {login_result}")

            if login_result:
                print("✅ MF Login succeeded!")
                current_url = extractor.driver.current_url
                print(f"📍 MF URL after login: {current_url}")
            else:
                print("❌ MF Login failed!")
                current_url = extractor.driver.current_url
                print(f"📍 MF URL after failed login: {current_url}")

        except TimeoutError:
            print("⏰ MF Login test timed out (probably waiting for 2FA)")
            current_url = extractor.driver.current_url
            print(f"📍 MF URL when timeout occurred: {current_url}")

        except Exception as e:
            print(f"❌ MF Exception during login: {e}")
            try:
                current_url = extractor.driver.current_url
                print(f"📍 MF URL when exception occurred: {current_url}")
            except:
                print("❌ Could not get current URL")

        # Cleanup
        print("🧹 Cleaning up MF...")
        extractor.cleanup()

    except ImportError as e:
        print(f"❌ Could not import MF extractor: {e}")
        return False
    except Exception as e:
        print(f"❌ Error during MF test: {e}")
        return False

if __name__ == "__main__":
    test_mf_login()