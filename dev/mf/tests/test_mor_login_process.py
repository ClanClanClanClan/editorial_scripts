#!/usr/bin/env python3
"""
TEST MOR LOGIN PROCESS - Find exactly where login fails
=======================================================

Test the complete MOR login process step by step.
"""

import sys
from pathlib import Path

# Add the production path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src' / 'extractors'))

try:
    from mor_extractor import ComprehensiveMORExtractor
    print("✅ MOR extractor imported successfully")
except ImportError as e:
    print(f"❌ Could not import MOR extractor: {e}")
    sys.exit(1)

def test_mor_login_process():
    """Test the complete MOR login process."""
    print("🚀 Testing MOR login process...")

    try:
        # Create extractor
        print("📝 Creating MOR extractor...")
        extractor = ComprehensiveMORExtractor()

        # Test login method
        print("🔐 Testing login method...")
        try:
            login_result = extractor.login()
            print(f"🔍 Login result: {login_result}")

            if login_result:
                print("✅ Login succeeded!")

                # Check current URL after login
                current_url = extractor.driver.current_url
                print(f"📍 URL after login: {current_url}")

                # Check page title
                page_title = extractor.driver.title
                print(f"📄 Page title: {page_title}")

            else:
                print("❌ Login failed!")

                # Check where we ended up
                current_url = extractor.driver.current_url
                print(f"📍 URL after failed login: {current_url}")

        except Exception as e:
            print(f"❌ Exception during login: {e}")

            # Get current state
            try:
                current_url = extractor.driver.current_url
                print(f"📍 URL when exception occurred: {current_url}")
            except:
                print("❌ Could not get current URL")

        # Cleanup
        print("🧹 Cleaning up...")
        extractor.cleanup()

    except Exception as e:
        print(f"❌ Error during MOR login test: {e}")
        try:
            extractor.cleanup()
        except:
            pass
        return False

if __name__ == "__main__":
    test_mor_login_process()