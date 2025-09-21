#!/usr/bin/env python3
"""
Quick MOR test to verify the setup
"""
import os
print("🚀 Starting MOR quick test...")

# Check credentials
username = os.getenv('MOR_EMAIL')
password = os.getenv('MOR_PASSWORD')

print(f"📧 MOR Email: {username}")
print(f"🔑 Password set: {'Yes' if password else 'No'}")

if username and password:
    print("✅ Credentials found!")

    # Test MOR extractor import
    try:
        from mor_extractor import MORExtractor
        print("✅ MORExtractor imported successfully")

        # Test initialization
        extractor = MORExtractor()
        print("✅ MORExtractor initialized")

        # Test setup methods
        extractor.setup_chrome_options()
        print("✅ Chrome options configured")

        extractor.setup_directories()
        print("✅ Directories configured")

        print("✅ All setup tests passed!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
else:
    print("❌ Credentials missing!")

print("🏁 Quick test complete")