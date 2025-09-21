#!/usr/bin/env python3
"""
Debug MOR hang issue
"""

import sys
import traceback
from pathlib import Path

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

print("Starting MOR debug test...")

try:
    print("\n1. Importing MOR extractor...")
    from extractors.mor_extractor import MORExtractor
    print("   ✅ MOR imported")

    print("\n2. Creating MOR instance...")
    mor = MORExtractor(use_cache=False)
    print("   ✅ MOR instance created")

    print("\n3. Setting up Chrome driver...")
    from selenium import webdriver
    from selenium.webdriver.support.ui import WebDriverWait

    print("   Creating Chrome driver...")
    mor.driver = webdriver.Chrome(options=mor.chrome_options)
    print("   ✅ Chrome driver created")

    print("   Setting timeouts...")
    mor.driver.set_page_load_timeout(30)
    mor.driver.implicitly_wait(10)
    mor.wait = WebDriverWait(mor.driver, 10)
    mor.original_window = mor.driver.current_window_handle
    print("   ✅ Driver initialized")

    print("\n4. Testing login...")
    login_success = mor.login()

    if login_success:
        print("   ✅ Login successful!")
    else:
        print("   ❌ Login failed")

    print("\n5. Closing driver...")
    mor.driver.quit()
    print("   ✅ Driver closed")

except KeyboardInterrupt:
    print("\n⚠️  Interrupted by user")
except Exception as e:
    print(f"\n❌ Error at step: {e}")
    traceback.print_exc()
finally:
    # Cleanup
    if 'mor' in locals() and hasattr(mor, 'driver'):
        try:
            mor.driver.quit()
            print("\n🧹 Driver closed in cleanup")
        except:
            pass
    print("\n" + "="*60)
    print("DEBUG COMPLETE")
    print("="*60)