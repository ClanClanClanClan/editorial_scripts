#!/usr/bin/env python3
"""
MOR EXTRACTOR TEST - ULTRATHINK VERSION
========================================
Comprehensive test of the fixed MOR extractor with dynamic HTML handling.
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Import the fixed MOR extractor
from mor_extractor import MORExtractor

def test_mor_extraction():
    """Test the fixed MOR extractor with real manuscript data."""

    print("\n" + "="*70)
    print("🚀 MOR EXTRACTOR TEST - ULTRATHINK DYNAMIC VERSION")
    print("="*70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize extractor
    extractor = MORExtractor()

    try:
        # Step 1: Setup and login
        print("\n📌 Step 1: Setting up and logging in...")
        print("-"*50)

        # Setup browser manually (since MORExtractor initializes in run() method)
        extractor.setup_chrome_options()
        extractor.setup_directories()

        # Initialize driver manually
        extractor.driver = webdriver.Chrome(options=extractor.chrome_options)

        # Configure driver (same as in run() method)
        extractor.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        extractor.driver.set_page_load_timeout(30)
        extractor.driver.implicitly_wait(10)
        extractor.wait = WebDriverWait(extractor.driver, 10)
        extractor.original_window = extractor.driver.current_window_handle

        print("✅ Browser initialized")

        # Navigate to MOR
        extractor.driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(3)

        # Login with 2FA
        username = os.getenv('MOR_EMAIL')
        password = os.getenv('MOR_PASSWORD')

        if not username or not password:
            print("❌ Credentials not found! Loading...")
            # Try to load credentials
            import subprocess
            result = subprocess.run(['bash', '-c', 'source ~/.editorial_scripts/load_all_credentials.sh && echo "OK"'],
                                  capture_output=True, text=True)
            if "OK" in result.stdout:
                username = os.getenv('MOR_EMAIL')
                password = os.getenv('MOR_PASSWORD')

        print(f"✅ Using credentials for: {username}")

        # Perform login
        try:
            # Enter username
            username_field = extractor.driver.find_element(By.ID, "USERID")
            username_field.clear()
            username_field.send_keys(username)

            # Enter password
            password_field = extractor.driver.find_element(By.ID, "PASSWORD")
            password_field.clear()
            password_field.send_keys(password)

            # Submit login
            password_field.send_keys(Keys.RETURN)
            time.sleep(5)

            # Check if 2FA is needed
            if "two-factor" in extractor.driver.page_source.lower() or "verification" in extractor.driver.page_source.lower():
                print("⏳ 2FA required - waiting for Gmail verification...")

                # Call the 2FA handler
                if hasattr(extractor, 'handle_2fa_gmail'):
                    extractor.handle_2fa_gmail()
                else:
                    print("   ⚠️ Manual 2FA required - please complete in browser")
                    time.sleep(30)  # Give user time to complete 2FA

            print("✅ Login successful!")

        except Exception as e:
            print(f"❌ Login error: {e}")
            return

        # Step 2: Navigate to Associate Editor section
        print("\n📌 Step 2: Navigating to manuscripts...")
        print("-"*50)

        try:
            # Look for Associate Editor link
            ae_links = extractor.driver.find_elements(By.XPATH,
                "//a[contains(text(), 'Associate Editor') or contains(@href, 'ASSOCIATE_EDITOR')]")

            if ae_links:
                extractor.safe_click(ae_links[0])
                time.sleep(3)
                print("✅ Entered Associate Editor section")
            else:
                print("⚠️ Associate Editor link not found")

            # Look for manuscript categories or lists
            manuscript_links = extractor.driver.find_elements(By.XPATH,
                "//a[contains(@href, 'CURRENT_ACTIVE') or contains(text(), 'Active') or contains(text(), 'Manuscript')]")

            if manuscript_links:
                print(f"✅ Found {len(manuscript_links)} manuscript categories")
                # Click first category
                extractor.safe_click(manuscript_links[0])
                time.sleep(3)

                # Look for individual manuscripts
                manuscript_rows = extractor.driver.find_elements(By.XPATH,
                    "//tr[contains(., 'MOR-')]")

                if manuscript_rows:
                    print(f"✅ Found {len(manuscript_rows)} manuscripts")
                    # Click on first manuscript
                    manuscript_link = manuscript_rows[0].find_element(By.XPATH, ".//a")
                    extractor.safe_click(manuscript_link)
                    time.sleep(3)

        except Exception as e:
            print(f"⚠️ Navigation warning: {e}")

        # Step 3: Test referee extraction
        print("\n📌 Step 3: Testing referee extraction (ULTRATHINK)...")
        print("-"*50)

        # Test the enhanced extraction
        referees = extractor.extract_referees_enhanced()

        print(f"\n📊 EXTRACTION RESULTS:")
        print(f"Total referees found: {len(referees)}")

        if referees:
            print("\n🔍 DETAILED REFEREE DATA:")
            for i, referee in enumerate(referees, 1):
                print(f"\n  Referee #{i}:")
                print(f"  ├─ Name: {referee.get('name', 'N/A')}")
                print(f"  ├─ Status: {referee.get('status', 'N/A')}")
                print(f"  ├─ Institution: {referee.get('institution', 'N/A')}")
                if referee.get('department'):
                    print(f"  ├─ Department: {referee['department']}")
                if referee.get('orcid'):
                    verified = "✓" if referee.get('orcid_verified') else "✗"
                    print(f"  ├─ ORCID: {referee['orcid']} [{verified}]")
                if referee.get('invitation_date'):
                    print(f"  ├─ Invited: {referee['invitation_date']}")
                if referee.get('response_date'):
                    print(f"  ├─ Response: {referee['response_date']}")
                if referee.get('due_date'):
                    print(f"  ├─ Due: {referee['due_date']}")
                if referee.get('days_in_review'):
                    print(f"  ├─ Days in review: {referee['days_in_review']}")
                if referee.get('email_popup_id'):
                    print(f"  ├─ Email popup ID: {referee['email_popup_id']}")
                if referee.get('dates'):
                    print(f"  └─ All dates: {referee['dates']}")
        else:
            print("\n⚠️ No referees found - checking page structure...")

            # Debug: Check what's on the page
            print("\n🔍 PAGE ANALYSIS:")

            # Check for XIK_RP_ID inputs
            xik_inputs = extractor.driver.find_elements(By.XPATH,
                "//input[contains(@name, 'XIK_RP_ID')]")
            print(f"  • XIK_RP_ID inputs found: {len(xik_inputs)}")

            # Check for ORDER selects
            order_selects = extractor.driver.find_elements(By.XPATH,
                "//select[contains(@name, 'ORDER')]")
            print(f"  • ORDER selects found: {len(order_selects)}")

            # Check for mailpopup links
            mailpopup_links = extractor.driver.find_elements(By.XPATH,
                "//a[contains(@href, 'mailpopup')]")
            print(f"  • Mailpopup links found: {len(mailpopup_links)}")
            if mailpopup_links:
                for link in mailpopup_links[:3]:
                    print(f"    - {link.text}")

            # Check page title/content
            title_elem = extractor.driver.find_elements(By.XPATH, "//h1 | //h2 | //title")
            if title_elem:
                print(f"  • Page title: {title_elem[0].text}")

        # Step 4: Test document extraction
        print("\n📌 Step 4: Testing document extraction...")
        print("-"*50)

        try:
            # Look for document links
            doc_links = {
                'HTML': extractor.driver.find_elements(By.XPATH, "//a[contains(., 'HTML')]"),
                'PDF': extractor.driver.find_elements(By.XPATH, "//a[contains(., 'PDF')]"),
                'Supplemental': extractor.driver.find_elements(By.XPATH, "//a[contains(., 'Supplemental')]"),
                'Cover Letter': extractor.driver.find_elements(By.XPATH, "//a[contains(., 'Cover Letter')]"),
                'Abstract': extractor.driver.find_elements(By.XPATH, "//a[contains(., 'Abstract')]")
            }

            print("📄 Documents found:")
            for doc_type, links in doc_links.items():
                if links:
                    print(f"  ✅ {doc_type}: {len(links)} link(s)")

        except Exception as e:
            print(f"⚠️ Document extraction error: {e}")

        # Step 5: Save results
        print("\n📌 Step 5: Saving test results...")
        print("-"*50)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = {
            'test_timestamp': datetime.now().isoformat(),
            'referees_extracted': len(referees),
            'referee_data': referees,
            'extraction_method': 'ULTRATHINK Dynamic',
            'page_url': extractor.driver.current_url,
            'page_title': extractor.driver.title
        }

        # Save to file
        results_dir = Path(__file__).parent / "results" / "mor"
        results_dir.mkdir(parents=True, exist_ok=True)

        results_file = results_dir / f"test_results_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"✅ Results saved to: {results_file}")

        # Summary
        print("\n" + "="*70)
        print("📊 TEST SUMMARY:")
        print(f"  • Referees extracted: {len(referees)}")
        print(f"  • Test status: {'✅ SUCCESS' if referees else '⚠️ CHECK MANUALLY'}")
        print("="*70)

    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        print("\n🧹 Cleanup...")
        try:
            if hasattr(extractor, 'driver') and extractor.driver:
                extractor.driver.quit()
                print("✅ Browser closed")
        except:
            pass


if __name__ == "__main__":
    # Load credentials first
    import subprocess
    result = subprocess.run(['bash', '-c', 'source ~/.editorial_scripts/load_all_credentials.sh && echo "OK"'],
                          capture_output=True, text=True)
    if "OK" in result.stdout:
        print("✅ Credentials loaded from secure storage")

    # Run test
    test_mor_extraction()