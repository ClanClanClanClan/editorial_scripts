#!/usr/bin/env python3
"""
Fix referee name clicking and email extraction
"""

import os

# Add parent directory to path
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

sys.path.append(str(Path(__file__).parent.parent))

from src.core.secure_credentials import SecureCredentialManager


def fix_referee_clicking():
    """Test proper referee clicking"""

    # Setup Chrome
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()

    try:
        # Load credentials
        print("🔐 Loading credentials...")
        creds = SecureCredentialManager()
        email, password = creds.load_credentials()
        os.environ["MF_EMAIL"] = email
        os.environ["MF_PASSWORD"] = password

        # Quick login (assuming we know it works)
        print("\n🔐 Logging in...")
        driver.get("https://mc.manuscriptcentral.com/mafi")
        time.sleep(3)

        # Reject cookies
        try:
            driver.find_element(By.ID, "onetrust-reject-all-handler").click()
        except:
            pass

        # Login
        driver.find_element(By.ID, "USERID").send_keys(email)
        driver.find_element(By.ID, "PASSWORD").send_keys(password)
        driver.execute_script("document.getElementById('logInButton').click();")
        time.sleep(5)

        # Handle 2FA if needed
        try:
            token_field = driver.find_element(By.ID, "TOKEN_VALUE")
            print("   📱 2FA required, entering code...")

            # Wait a bit for email to arrive
            time.sleep(10)

            # Get code from Gmail
            import sys
            from pathlib import Path

            sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
            from core.gmail_verification_wrapper import fetch_latest_verification_code

            print("   🔍 Fetching verification code from Gmail...")
            code = fetch_latest_verification_code("MF", max_wait=45)

            if code:
                print(f"   ✅ Found verification code: {code}")
                token_field.clear()
                token_field.send_keys(code)
                driver.find_element(By.ID, "VERIFY_BTN").click()
                print("   🔑 Entered code and clicked verify")
                time.sleep(8)
            else:
                print("   ❌ Could not fetch verification code")
        except Exception as e:
            print(f"   ℹ️ No 2FA needed or error: {e}")

        print("   ✅ Logged in successfully")

        # Wait for page to fully load after login
        print("\n⏳ Waiting for main page to load...")
        max_wait = 30
        wait_count = 0
        while wait_count < max_wait:
            current_url = driver.current_url
            if "page=LOGIN" not in current_url and "login" not in current_url.lower():
                break
            print(f"   Still on login page, waiting... ({wait_count + 1}/{max_wait})")
            time.sleep(2)
            wait_count += 1

        if wait_count >= max_wait:
            print("   ❌ Login failed - still on login page")
            return

        print(f"   ✅ Successfully reached main page: {driver.current_url}")

        # Take a screenshot for debugging
        driver.save_screenshot("debug_after_login.png")
        print("   📸 Saved screenshot: debug_after_login.png")

        # Wait a bit more for page to fully load
        time.sleep(5)

        # Check if we're on a dashboard page
        if "dashboard" in driver.current_url.lower():
            print("   📊 Already on dashboard")

        # Navigate to AE Center
        print("\n📊 Looking for navigation links...")

        # First, look for main navigation area
        try:
            # ScholarOne has navigation typically in a nav or menu area
            nav_areas = driver.find_elements(
                By.XPATH, "//div[@class='nav' or @class='menu' or contains(@class,'navigation')]"
            )
            print(f"   Found {len(nav_areas)} navigation areas")
        except:
            pass

        # Debug what's on the page
        all_links = driver.find_elements(By.TAG_NAME, "a")
        print(f"   Found {len(all_links)} total links on page")

        # Filter for meaningful links (exclude empty, very short)
        text_links = []
        for link in all_links:
            text = link.text.strip()
            if text and len(text) > 3:  # Skip very short links
                text_links.append(text)

        print(f"   Found {len(text_links)} text links")
        if text_links:
            print(f"   Links found: {text_links[:20]}")  # Show first 20

        # Try multiple methods to find AE Center
        ae_link = None

        # Method 1: Exact text
        try:
            ae_link = driver.find_element(By.LINK_TEXT, "Associate Editor Center")
            print("   ✅ Found AE link via exact text")
        except:
            pass

        # Method 2: Partial text
        if not ae_link:
            try:
                ae_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Associate Editor")
                print("   ✅ Found AE link via partial text")
            except:
                pass

        # Method 3: Check if already in AE Center
        if not ae_link and "ASSOCIATE_EDITOR" in driver.current_url.upper():
            print("   ✅ Already in Associate Editor Center")
            ae_link = "already_there"

        if ae_link and ae_link != "already_there":
            ae_link.click()
            time.sleep(5)
        elif not ae_link:
            print("   ❌ Could not find Associate Editor Center link")
            return

        # Find which categories have manuscripts
        print("\n📋 Finding manuscript categories...")

        # Look for all category links
        category_names = [
            "Awaiting Reviewer Selection",
            "Awaiting Reviewer Invitation",
            "Awaiting Reviewer Assignment",
            "Awaiting Reviewer Scores",
            "Overdue Reviewer Scores",
            "Awaiting AE Recommendation",
        ]

        found_category = None
        for cat_name in category_names:
            try:
                cat_link = driver.find_element(By.LINK_TEXT, cat_name)
                # Check if it has manuscripts (usually shown with a number)
                row = cat_link.find_element(By.XPATH, "./ancestor::tr[1]")
                row_text = row.text
                print(f"   Checking '{cat_name}': {row_text[:80]}...")

                # Look for a number indicating manuscripts
                import re

                numbers = re.findall(r"\b\d+\b", row_text)
                if numbers and int(numbers[-1]) > 0:
                    print(f"   ✅ Found {numbers[-1]} manuscripts in '{cat_name}'")
                    found_category = cat_link
                    break
            except:
                pass

        if not found_category:
            print("   ❌ No categories with manuscripts found!")
            return

        print("\n   🖱️ Clicking on category...")
        found_category.click()
        time.sleep(3)
        print("   ✅ Clicked on category with manuscripts")

        # NOW we need to click Take Action to get to a manuscript page
        print("\n📄 Finding manuscripts with 'Take Action' buttons...")

        # Debug what's on the page
        print("\n   🔍 Debugging page content...")

        # Check page title to confirm we're on the right page
        page_title = driver.title
        print(f"   Page title: {page_title}")

        # Look for manuscript IDs (common pattern)
        manuscript_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'MAFI-')]")
        print(f"   Found {len(manuscript_links)} manuscript ID links")
        if manuscript_links:
            for i, link in enumerate(manuscript_links[:3]):
                print(f"     - {link.text}")

        # Look for all links
        all_links = driver.find_elements(By.TAG_NAME, "a")
        link_texts = [l.text.strip() for l in all_links if l.text.strip()]
        print(f"   Total links found: {len(link_texts)}")
        print(f"   Sample links: {link_texts[:10]}")

        # Look specifically for action-related links
        action_links = [l.text for l in all_links if "action" in l.text.lower()]
        print(f"   Found {len(action_links)} links with 'action': {action_links[:5]}")

        # Try different methods
        take_action_links = driver.find_elements(By.LINK_TEXT, "Take Action")
        if not take_action_links:
            # Try partial text
            take_action_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Take Action")

        if take_action_links:
            print(f"   ✅ Found {len(take_action_links)} manuscripts")
            print("   🖱️ Clicking 'Take Action' on first manuscript...")
            take_action_links[0].click()
            time.sleep(3)
            print("   ✅ Now on manuscript details page")
        else:
            print("   ❌ No 'Take Action' buttons found!")
            # Save screenshot for debugging
            driver.save_screenshot("debug_no_take_action.png")
            print("   📸 Saved screenshot: debug_no_take_action.png")
            return

        # NOW we're on a manuscript page - verify this
        print(f"\n📍 Current URL: {driver.current_url}")
        if "CURRENT_STAGE" in driver.current_url:
            print("   ✅ Confirmed: On manuscript details page")
        else:
            print("   ⚠️ May not be on correct page")

        print("\n👥 NOW looking for referee table on the manuscript page...")

        # Find all table rows with referee info
        # The referee table has class 'tablelines'
        referee_table = driver.find_element(By.XPATH, "//td[@class='tablelines']//table")

        # Get all rows that have mailpopup links
        referee_rows = referee_table.find_elements(
            By.XPATH, ".//tr[.//a[contains(@href,'mailpopup')]]"
        )
        print(f"   Found {len(referee_rows)} referee rows")

        # Filter out non-referee rows (like Editor, Author)
        actual_referees = []
        for row in referee_rows:
            row_text = row.text.lower()
            # Skip rows that are editors or authors
            if (
                "associate editor" not in row_text
                and "author" not in row_text
                and "editor" not in row_text
            ):
                actual_referees.append(row)

        print(f"   Filtered to {len(actual_referees)} actual referees")

        # Test clicking first referee
        if actual_referees:
            print("\n🧪 Testing first referee...")
            row = actual_referees[0]

            # Find the name link
            name_link = row.find_element(By.XPATH, ".//a[contains(@href,'mailpopup')]")
            referee_name = name_link.text.strip()
            print(f"   Referee: {referee_name}")

            # Get href
            href = name_link.get_attribute("href")
            print(f"   Full href: {href}")

            # Store current window
            main_window = driver.current_window_handle
            windows_before = len(driver.window_handles)

            # Click the link
            print("   Clicking referee name...")
            name_link.click()

            # Wait for popup
            time.sleep(3)

            # Check if popup opened
            windows_after = len(driver.window_handles)
            if windows_after > windows_before:
                print("   ✅ Popup opened!")

                # Switch to popup
                driver.switch_to.window(driver.window_handles[-1])

                # Check for frames
                frames = driver.find_elements(By.TAG_NAME, "frame")
                print(f"   Frames in popup: {len(frames)}")

                if frames:
                    # Try first frame
                    driver.switch_to.frame(frames[0])

                    # Look for EMAIL_TEMPLATE_TO field
                    try:
                        to_field = driver.find_element(By.NAME, "EMAIL_TEMPLATE_TO")
                        email_value = to_field.get_attribute("value")
                        print(f"   ✅ Found email: {email_value}")
                    except:
                        print("   ❌ EMAIL_TEMPLATE_TO not found")

                        # Try to find email in page
                        body_text = driver.find_element(By.TAG_NAME, "body").text
                        emails = re.findall(
                            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", body_text
                        )
                        if emails:
                            print(f"   Found emails in text: {emails}")

                    driver.switch_to.default_content()

                # Close popup
                driver.close()
                driver.switch_to.window(main_window)
            else:
                print("   ❌ No popup opened!")

        # Also test cover letter
        print("\n📋 Looking for cover letter...")

        # Method 1: Look for text containing "Cover Letter"
        cover_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Cover Letter')]")
        print(f"   Method 1 - Found {len(cover_links)} cover letter links by text")

        # Method 2: Look for links with cover in href
        cover_href_links = driver.find_elements(
            By.XPATH, "//a[contains(@href, 'cover') or contains(@href, 'COVER')]"
        )
        print(f"   Method 2 - Found {len(cover_href_links)} links with 'cover' in href")

        # Method 3: Look in document section
        try:
            doc_section = driver.find_element(By.XPATH, "//td[@class='headerbg2']//table")
            doc_links = doc_section.find_elements(By.TAG_NAME, "a")
            print(f"   Method 3 - Found {len(doc_links)} links in document section")
            for link in doc_links:
                text = link.text.strip()
                if text:
                    print(f"     - Link: {text}")
        except:
            print("   Method 3 - Could not find document section")

        if cover_links:
            print("\n   📄 Testing cover letter click...")
            href = cover_links[0].get_attribute("href")
            print(f"   Cover letter href: {href}")

            # Try clicking it
            windows_before = len(driver.window_handles)
            cover_links[0].click()
            time.sleep(3)

            windows_after = len(driver.window_handles)
            if windows_after > windows_before:
                print("   ✅ Cover letter opened in new window!")
                # Switch back
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            else:
                print("   ❌ Cover letter did not open new window")

        print("\n✅ Test complete!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        print("\n⏸️  Browser will close in 10 seconds...")
        time.sleep(10)
        driver.quit()


if __name__ == "__main__":
    fix_referee_clicking()
