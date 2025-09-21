#!/usr/bin/env python3
"""
MOR Test with Manual 2FA Entry Option
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from extractors.mor_extractor import MORExtractor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

print("="*60)
print("🚀 MOR EXTRACTOR WITH MANUAL 2FA OPTION")
print("="*60)

mor = None
try:
    # Create MOR instance
    print("\n1. Creating MOR extractor...")
    mor = MORExtractor(use_cache=False)

    # Setup driver manually for better control
    print("\n2. Setting up Chrome...")
    mor.driver = webdriver.Chrome(options=mor.chrome_options)
    mor.driver.set_page_load_timeout(30)
    mor.driver.implicitly_wait(10)
    mor.wait = WebDriverWait(mor.driver, 10)
    mor.original_window = mor.driver.current_window_handle
    print("   ✅ Chrome ready")

    # Navigate to MOR
    print("\n3. Navigating to MOR...")
    mor.driver.get("https://mc.manuscriptcentral.com/mathor")
    mor.smart_wait(3)

    # Handle cookies
    try:
        reject_btn = mor.driver.find_element(By.ID, "onetrust-reject-all-handler")
        mor.safe_click(reject_btn)
        mor.smart_wait(2)
    except:
        pass

    # Enter credentials
    print("\n4. Entering credentials...")
    userid_field = mor.driver.find_element(By.ID, "USERID")
    userid_field.clear()
    userid_field.send_keys(os.getenv('MOR_EMAIL'))

    password_field = mor.driver.find_element(By.ID, "PASSWORD")
    password_field.clear()
    password_field.send_keys(os.getenv('MOR_PASSWORD'))

    # Login
    login_btn = mor.driver.find_element(By.ID, "logInButton")
    mor.safe_click(login_btn)
    mor.smart_wait(5)

    # Check for 2FA
    try:
        token_field = mor.driver.find_element(By.ID, "TOKEN_VALUE")
        print("\n5. 2FA required")

        print("\n" + "="*60)
        print("⚠️  MANUAL INTERVENTION REQUIRED")
        print("="*60)
        print("\nMOR has rate limiting on verification emails.")
        print("Please check your email for a verification code.")
        print("\nIf you have a recent code (from today), you can use it.")
        print("Otherwise, you may need to wait for the rate limit to reset.\n")

        # Manual entry
        code = input("Enter the 6-digit verification code: ").strip()

        if code and len(code) == 6 and code.isdigit():
            print(f"\n6. Entering code: {code}")
            mor.driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")

            verify_btn = mor.driver.find_element(By.ID, "VERIFY_BTN")
            mor.safe_click(verify_btn)
            mor.smart_wait(8)

            print("\n7. Checking login result...")
            # Check for successful login
            if "Associate Editor" in mor.driver.page_source:
                print("   ✅ LOGIN SUCCESSFUL!")

                # Navigate to AE Center
                print("\n8. Navigating to AE Center...")
                if mor.navigate_to_ae_center():
                    print("   ✅ In AE Center")

                    # Process manuscripts
                    print("\n9. Processing manuscripts...")
                    categories = [
                        "Awaiting Reviewer Reports",
                        "Overdue Reviewer Reports",
                        "Awaiting AE Recommendation",
                        "Awaiting Editor Decision"
                    ]

                    all_manuscripts = []
                    for category in categories:
                        print(f"\n   Processing: {category}")
                        try:
                            manuscripts = mor.process_category(category)
                            all_manuscripts.extend(manuscripts)
                            print(f"   ✅ Found {len(manuscripts)} manuscripts")
                        except Exception as e:
                            print(f"   ❌ Error: {str(e)[:100]}")

                    # Save results
                    if all_manuscripts:
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        output_file = Path(f'/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/dev/mf/outputs/mor_manual_{timestamp}.json')
                        output_file.parent.mkdir(parents=True, exist_ok=True)

                        results = {
                            'extraction_timestamp': datetime.now().isoformat(),
                            'journal': 'MOR',
                            'manuscripts': all_manuscripts,
                            'summary': {
                                'total_manuscripts': len(all_manuscripts),
                                'total_referees': sum(len(ms.get('referees', [])) for ms in all_manuscripts)
                            }
                        }

                        with open(output_file, 'w') as f:
                            json.dump(results, f, indent=2, default=str)

                        print(f"\n📄 Results saved to: {output_file.name}")

                        # Print summary
                        print("\n" + "="*60)
                        print("📊 EXTRACTION SUMMARY")
                        print("="*60)
                        print(f"Total manuscripts: {len(all_manuscripts)}")

                        for i, ms in enumerate(all_manuscripts[:3], 1):
                            print(f"\n{i}. {ms.get('manuscript_id', 'Unknown')}")
                            print(f"   Referees: {len(ms.get('referees', []))}")

                else:
                    print("   ❌ Could not navigate to AE Center")
            else:
                print("   ❌ Login failed - code may be invalid or expired")
        else:
            print("   ❌ Invalid code format")

    except Exception as e:
        print(f"   No 2FA required or error: {e}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if mor and hasattr(mor, 'driver'):
        try:
            print("\n🔍 Browser will remain open for inspection")
            input("Press Enter to close browser...")
            mor.driver.quit()
        except:
            pass

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)