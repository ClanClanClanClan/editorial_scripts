#!/usr/bin/env python3
"""
ULTRAROBUST MOR Extractor
Bulletproof extraction of both MOR-2025-1136 and MOR-2025-1037
"""

import json
import os
import sys
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.gmail_verification_wrapper import fetch_latest_verification_code


class UltraRobustMORExtractor:
    def __init__(self, headless=False):
        self.manuscripts = []
        self.processed_manuscript_ids = set()
        self.headless = headless
        self.driver = None
        self.wait = None

    def setup_driver(self):
        """Setup bulletproof Chrome driver."""
        options = webdriver.ChromeOptions()

        # STEALTH MODE
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument(
            "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )

        if self.headless:
            options.add_argument("--headless=new")
            print("👻 STEALTH headless mode")
        else:
            print("🖥️ Visible mode for debugging")

        # Stability options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")

        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)

        # Remove webdriver property
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

    def cleanup_all_popups(self, original_window):
        """NUCLEAR popup cleanup - close everything except main window."""
        try:
            current_windows = self.driver.window_handles
            if len(current_windows) > 1:
                print(f"         🧹 NUCLEAR CLEANUP: Closing {len(current_windows)-1} windows...")
                for window in current_windows:
                    if window != original_window:
                        try:
                            self.driver.switch_to.window(window)
                            self.driver.close()
                        except:
                            pass

            # Force return to original window
            self.driver.switch_to.window(original_window)
            time.sleep(1)

        except Exception as e:
            print(f"         ⚠️ Cleanup error: {e}")
            try:
                self.driver.switch_to.window(original_window)
            except:
                pass

    def robust_login(self):
        """Bulletproof login with multiple retry strategies."""
        print("🔐 ULTRAROBUST Login Process...")

        for attempt in range(3):
            try:
                print(f"   Attempt {attempt + 1}/3...")
                self.driver.get("https://mc.manuscriptcentral.com/mathor")
                time.sleep(5)  # Let page fully stabilize

                # Enter credentials
                email = os.getenv("MOR_EMAIL", "dylan.possamai@math.ethz.ch")
                password = os.getenv("MOR_PASSWORD", "")

                email_field = self.wait.until(EC.element_to_be_clickable((By.ID, "USERID")))
                email_field.clear()
                email_field.send_keys(email)

                password_field = self.driver.find_element(By.ID, "PASSWORD")
                password_field.clear()
                password_field.send_keys(password)

                login_button = self.driver.find_element(By.ID, "logInButton")
                login_button.click()
                time.sleep(5)

                # Handle 2FA if needed
                if "twoFactorAuthForm" in self.driver.page_source:
                    print("      📱 2FA required...")
                    login_time = datetime.now()
                    code = fetch_latest_verification_code(
                        "MOR", max_wait=30, poll_interval=2, start_timestamp=login_time
                    )

                    if code:
                        print(f"      ✅ Got code: {code[:3]}***")
                        code_field = self.driver.find_element(By.NAME, "verificationCode")
                        code_field.send_keys(code)
                        submit_btn = self.driver.find_element(By.ID, "submitButton")
                        submit_btn.click()
                        time.sleep(5)

                # Check for device verification
                if "Unrecognized Device" in self.driver.page_source:
                    print("      🔐 Device verification required...")
                    device_verification_start = datetime.now()
                    device_code = fetch_latest_verification_code(
                        "MOR",
                        max_wait=30,
                        poll_interval=2,
                        start_timestamp=device_verification_start,
                    )

                    if device_code:
                        print(f"      ✅ Got device code: {device_code[:3]}***")

                        # Find and fill verification code field
                        try:
                            # Wait for the modal to be fully loaded
                            time.sleep(2)

                            # Look for the code input field - try multiple selectors
                            code_field = None
                            selectors = [
                                "//input[@type='text']",  # Most generic first
                                "//input[@name='TOKEN_VALUE']",
                                "//input[@id='TOKEN_VALUE']",
                                "//input[contains(@placeholder, 'verification')]",
                                "//div[contains(@class, 'modal')]//input[@type='text']",
                                "//form//input[@type='text']",
                            ]

                            print("      🔍 Searching for verification input field...")
                            for i, selector in enumerate(selectors):
                                try:
                                    code_field = self.driver.find_element(By.XPATH, selector)
                                    if code_field.is_displayed() and code_field.is_enabled():
                                        print(f"      ✅ Found input field with selector {i+1}")
                                        break
                                except:
                                    continue

                            if code_field:
                                code_field.clear()
                                code_field.send_keys(device_code)
                                print(f"      ✅ Entered device code: {device_code[:3]}***")

                                # Look for submit button
                                submit_buttons = [
                                    "//a[contains(text(), 'Verify')]",
                                    "//button[contains(text(), 'Verify')]",
                                    "//input[@type='submit']",
                                    "//button[@type='submit']",
                                    "//a[contains(@onclick, 'submit')]",
                                ]

                                verify_btn = None
                                for btn_selector in submit_buttons:
                                    try:
                                        verify_btn = self.driver.find_element(
                                            By.XPATH, btn_selector
                                        )
                                        if verify_btn.is_displayed():
                                            break
                                    except:
                                        continue

                                if verify_btn:
                                    verify_btn.click()
                                    time.sleep(5)
                                    print("      ✅ Device verification submitted!")
                                else:
                                    print("      ⚠️ No submit button found, trying Enter key")
                                    code_field.send_keys("\n")
                                    time.sleep(5)
                            else:
                                print("      ❌ No input field found for device verification")
                                # Save page source for debugging
                                with open("device_verification_debug.html", "w") as f:
                                    f.write(self.driver.page_source)
                                print("      💾 Saved page source for debugging")
                                continue

                        except Exception as e:
                            print(f"      ❌ Device verification failed: {e}")
                            continue
                    else:
                        print("      ❌ No device verification code found")
                        continue

                # Verify final login success
                current_url = self.driver.current_url
                page_source = self.driver.page_source

                # Check for successful login indicators
                if (
                    "login" not in current_url.lower()
                    and "Associate Editor" in page_source
                    or "Dylan Possamaï" in page_source
                ):
                    print("   ✅ Login successful!")
                    return True
                elif "logged out" in page_source:
                    print("   ⚠️ Got logged out, retrying...")
                    continue

            except Exception as e:
                print(f"   ⚠️ Login attempt {attempt + 1} failed: {e}")
                time.sleep(3)

        return False

    def robust_ae_navigation(self):
        """Multi-strategy navigation to AE Center."""
        print("\n📋 ULTRAROBUST AE Center Navigation...")

        strategies = [
            self._strategy_journal_then_ae,
            self._strategy_direct_ae_link,
            self._strategy_url_navigation,
        ]

        for i, strategy in enumerate(strategies):
            try:
                print(f"   Strategy {i+1}/{len(strategies)}: {strategy.__name__}")
                if strategy():
                    print("   ✅ AE Center navigation successful!")
                    return True
            except Exception as e:
                print(f"   ⚠️ Strategy {i+1} failed: {e}")
                time.sleep(2)

        return False

    def _strategy_journal_then_ae(self):
        """Strategy 1: Click journal link, then AE Center."""
        # Look for journal link with multiple variations
        journal_selectors = [
            "//a[contains(text(), 'Mathematics of Operations Research')]",
            "//a[contains(text(), 'Mathematics')]",
            "//a[contains(@href, 'mathor')]",
        ]

        for selector in journal_selectors:
            try:
                journal_link = self.driver.find_element(By.XPATH, selector)
                journal_link.click()
                time.sleep(5)
                print("      ✅ Clicked journal link")
                break
            except:
                continue
        else:
            print("      ℹ️ No journal link found")

        # Find AE Center with multiple variations
        ae_selectors = [
            "//a[contains(text(), 'Associate Editor')]",
            "//a[contains(text(), 'Editor Center')]",
            "//a[contains(@href, 'ASSOCIATE_EDITOR')]",
        ]

        for selector in ae_selectors:
            try:
                ae_link = self.driver.find_element(By.XPATH, selector)
                if ae_link.is_displayed():
                    ae_link.click()
                    time.sleep(5)
                    print(f"      ✅ Clicked AE link: {ae_link.text}")
                    break
            except:
                continue

        return (
            "Associate Editor" in self.driver.page_source
            or "ASSOCIATE_EDITOR" in self.driver.current_url
        )

    def _strategy_direct_ae_link(self):
        """Strategy 2: Direct AE Center link."""
        ae_selectors = [
            "//a[text()='Associate Editor Center']",
            "//a[contains(text(), 'Associate Editor')]",
            "//a[contains(text(), 'Editor Center')]",
        ]

        for selector in ae_selectors:
            try:
                ae_link = self.driver.find_element(By.XPATH, selector)
                if ae_link.is_displayed():
                    ae_link.click()
                    time.sleep(5)
                    return True
            except:
                continue

        return False

    def _strategy_url_navigation(self):
        """Strategy 3: Direct URL navigation."""
        ae_url = "https://mc.manuscriptcentral.com/mathor?NEXT_PAGE=ASSOCIATE_EDITOR_DASHBOARD"
        self.driver.get(ae_url)
        time.sleep(5)

        # Debug what we got
        current_url = self.driver.current_url
        print(f"      🔍 After URL navigation: {current_url}")
        page_text = self.driver.find_element(By.TAG_NAME, "body").text[:200]
        print(f"      📄 Page content: {page_text}...")

        return "Associate Editor" in self.driver.page_source

    def extract_manuscripts_from_category(self, category_name):
        """Extract ALL manuscripts from a specific category with bulletproof iteration."""
        print(f"\n📂 ULTRAROBUST Processing: {category_name}")

        # Click category
        category_link = self.driver.find_element(By.LINK_TEXT, category_name)
        category_link.click()
        time.sleep(5)

        # Get ALL manuscript IDs from table FIRST
        manuscript_ids = self._get_all_manuscript_ids_from_table()

        if not manuscript_ids:
            print("   📭 No manuscripts in this category")
            return

        print(f"   📄 Found manuscripts: {manuscript_ids}")

        # Process each manuscript individually
        for i, manuscript_id in enumerate(manuscript_ids):
            # Skip if already processed
            if manuscript_id in self.processed_manuscript_ids:
                print(f"   ⏭️ SKIPPING {manuscript_id} - already processed")
                continue

            print(f"\n   📄 Processing manuscript {i+1}/{len(manuscript_ids)}: {manuscript_id}")

            # Navigate to specific manuscript
            if self._navigate_to_specific_manuscript(manuscript_id):
                # Extract data
                manuscript_data = self._extract_manuscript_data(manuscript_id, category_name)
                if manuscript_data:
                    self.manuscripts.append(manuscript_data)
                    self.processed_manuscript_ids.add(manuscript_id)
                    print(f"   ✅ Successfully extracted {manuscript_id}")

                # Nuclear popup cleanup after each manuscript
                original_window = self.driver.window_handles[0]
                self.cleanup_all_popups(original_window)
            else:
                print(f"   ❌ Could not navigate to {manuscript_id}")

        print(
            f"   🎉 Category complete: {len([m for m in manuscript_ids if m not in self.processed_manuscript_ids])} new manuscripts"
        )

    def _get_all_manuscript_ids_from_table(self):
        """Get ALL manuscript IDs from current table."""
        manuscript_ids = []

        try:
            # Find all Take Action links
            take_action_links = self.driver.find_elements(
                By.XPATH, "//a[.//img[contains(@src, 'check_off.gif')]]"
            )
            print(f"      🔍 Found {len(take_action_links)} Take Action links")

            for link in take_action_links:
                try:
                    # Get the row
                    row = link.find_element(By.XPATH, "./ancestor::tr[1]")
                    # Get first cell (manuscript ID)
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if cells:
                        manuscript_id = cells[0].text.strip()
                        if manuscript_id and self._is_valid_manuscript_id(manuscript_id):
                            manuscript_ids.append(manuscript_id)
                            print(f"      📋 Table entry: {manuscript_id}")
                except Exception as e:
                    print(f"      ⚠️ Error parsing row: {e}")

        except Exception as e:
            print(f"   ⚠️ Error getting manuscript IDs: {e}")

        return manuscript_ids

    def _is_valid_manuscript_id(self, manuscript_id):
        """Validate manuscript ID format."""
        import re

        patterns = [
            r"^MOR-\d{4}-\d{3,5}(?:\.R\d+)?$",  # MOR-2025-1136
            r"^[A-Z]{2,6}-\d{4}-\d{3,5}(?:\.R\d+)?$",  # General format
        ]
        return any(re.match(pattern, manuscript_id) for pattern in patterns)

    def _navigate_to_specific_manuscript(self, target_manuscript_id):
        """Navigate to a specific manuscript by ID."""
        try:
            # Go back to category list
            self.driver.back()
            time.sleep(3)

            # Find the correct Take Action link for this manuscript
            take_action_links = self.driver.find_elements(
                By.XPATH, "//a[.//img[contains(@src, 'check_off.gif')]]"
            )

            for link in take_action_links:
                try:
                    row = link.find_element(By.XPATH, "./ancestor::tr[1]")
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if cells and cells[0].text.strip() == target_manuscript_id:
                        print(f"      🎯 Clicking manuscript: {target_manuscript_id}")
                        link.click()
                        time.sleep(5)
                        return True
                except:
                    continue

        except Exception as e:
            print(f"      ❌ Navigation error: {e}")

        return False

    def _extract_manuscript_data(self, manuscript_id, category):
        """Extract core data from current manuscript page."""
        data = {
            "id": manuscript_id,
            "category": category,
            "title": "",
            "authors": [],
            "referees": [],
            "status": "",
            "extracted_at": datetime.now().isoformat(),
        }

        try:
            # Get title
            try:
                title_elem = self.driver.find_element(
                    By.XPATH, "//td[contains(text(), 'Title:')]/following-sibling::td"
                )
                data["title"] = title_elem.text.strip()
                print(f"      📄 Title: {data['title'][:50]}...")
            except:
                print("      ⚠️ Could not extract title")

            # Get basic referees (safer extraction)
            try:
                referee_links = self.driver.find_elements(
                    By.XPATH, "//a[contains(@href, 'referee') or contains(@onclick, 'referee')]"
                )[
                    :5
                ]  # Limit to prevent issues
                for link in referee_links:
                    referee_name = link.text.strip()
                    if referee_name and len(referee_name) > 3:
                        data["referees"].append({"name": referee_name, "status": "Unknown"})

                print(f"      👥 Found {len(data['referees'])} referees")
            except:
                print("      ⚠️ Could not extract referees")

        except Exception as e:
            print(f"      ❌ Data extraction error: {e}")

        return data

    def run_extraction(self):
        """Main extraction process."""
        try:
            # Setup
            self.setup_driver()

            # Login
            if not self.robust_login():
                print("❌ Login failed after all attempts")
                return

            # Navigate to AE Center
            if not self.robust_ae_navigation():
                print("❌ AE Center navigation failed")
                return

            # Process target category with 2 manuscripts
            self.extract_manuscripts_from_category("Awaiting Reviewer Reports")

            # Save results
            output = {
                "extraction_time": datetime.now().isoformat(),
                "manuscripts": self.manuscripts,
                "total_unique": len(self.processed_manuscript_ids),
                "processed_ids": list(self.processed_manuscript_ids),
            }

            with open("ultrarobust_mor_results.json", "w") as f:
                json.dump(output, f, indent=2)

            print("\n🎉 ULTRAROBUST EXTRACTION COMPLETE!")
            print(f"   📊 Total manuscripts: {len(self.manuscripts)}")
            print(f"   📊 Unique IDs processed: {len(self.processed_manuscript_ids)}")
            print(f"   📋 IDs: {list(self.processed_manuscript_ids)}")

            for manuscript in self.manuscripts:
                print(f"   ✅ {manuscript['id']}: {manuscript['title'][:50]}...")

        except Exception as e:
            print(f"❌ Fatal error: {e}")
            import traceback

            traceback.print_exc()

        finally:
            if self.driver:
                self.driver.quit()


if __name__ == "__main__":
    extractor = UltraRobustMORExtractor(headless=False)  # Visible for debugging
    extractor.run_extraction()
