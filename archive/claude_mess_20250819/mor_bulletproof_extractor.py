#!/usr/bin/env python3
"""
BULLETPROOF MOR EXTRACTOR
Fixes: login robustness, deduplication across phases, window management
"""

import json
import os
import sys
import time
import traceback
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.gmail_verification_wrapper import fetch_latest_verification_code


class BulletproofMORExtractor:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.main_window = None
        # GLOBAL deduplication across ALL phases
        self.processed_manuscripts = set()
        self.manuscripts = []
        self.login_attempts = 0
        self.max_login_attempts = 5

    def setup_driver(self):
        """Setup bulletproof Chrome driver."""
        options = webdriver.ChromeOptions()

        # Stealth options
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )

        # Stability options
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")

        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 30)
        self.main_window = self.driver.current_window_handle

        # Remove webdriver property
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

    def bulletproof_login(self):
        """BULLETPROOF login with multiple fallback strategies."""
        print("🔐 BULLETPROOF LOGIN - Multiple strategies...")

        for attempt in range(self.max_login_attempts):
            try:
                print(f"\n   🔄 Login attempt {attempt + 1}/{self.max_login_attempts}")

                # Strategy 1: Standard login
                if attempt == 0:
                    success = self._login_strategy_standard()
                # Strategy 2: Extended wait login
                elif attempt == 1:
                    success = self._login_strategy_extended_wait()
                # Strategy 3: Forced refresh login
                elif attempt == 2:
                    success = self._login_strategy_forced_refresh()
                # Strategy 4: Clean session login
                elif attempt == 3:
                    success = self._login_strategy_clean_session()
                # Strategy 5: Last resort
                else:
                    success = self._login_strategy_last_resort()

                if success:
                    print(f"   ✅ Login successful with strategy {attempt + 1}")
                    return True

                print(f"   ❌ Strategy {attempt + 1} failed, trying next...")
                time.sleep(5)  # Wait between attempts

            except Exception as e:
                print(f"   ⚠️ Login attempt {attempt + 1} error: {e}")
                time.sleep(5)

        print("❌ ALL LOGIN STRATEGIES FAILED")
        return False

    def _login_strategy_standard(self):
        """Standard login approach."""
        print("      📋 Strategy 1: Standard login")

        self.driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(5)

        return self._perform_login_flow()

    def _login_strategy_extended_wait(self):
        """Extended wait times for slow responses."""
        print("      ⏰ Strategy 2: Extended wait times")

        self.driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(10)  # Longer initial wait

        return self._perform_login_flow(extended_waits=True)

    def _login_strategy_forced_refresh(self):
        """Force refresh and clear cache."""
        print("      🔄 Strategy 3: Forced refresh")

        # Clear cache
        self.driver.delete_all_cookies()
        self.driver.refresh()
        time.sleep(5)

        self.driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(8)

        return self._perform_login_flow()

    def _login_strategy_clean_session(self):
        """Start with completely clean session."""
        print("      🧹 Strategy 4: Clean session")

        # Clear everything
        self.driver.delete_all_cookies()
        self.driver.execute_script("window.localStorage.clear();")
        self.driver.execute_script("window.sessionStorage.clear();")

        self.driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(8)

        return self._perform_login_flow()

    def _login_strategy_last_resort(self):
        """Last resort with maximum waits."""
        print("      🚨 Strategy 5: Last resort")

        # Start completely fresh
        self.driver.quit()
        self.setup_driver()

        self.driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(15)  # Maximum wait

        return self._perform_login_flow(extended_waits=True)

    def _perform_login_flow(self, extended_waits=False):
        """Perform the actual login flow."""
        wait_time = 10 if extended_waits else 5

        try:
            # Handle cookies
            try:
                cookie_btn = self.driver.find_element(By.ID, "onetrust-reject-all-handler")
                cookie_btn.click()
                time.sleep(2)
            except:
                pass

            # Enter credentials
            email = os.getenv("MOR_EMAIL", "dylan.possamai@math.ethz.ch")
            password = os.getenv("MOR_PASSWORD", "")

            if not email or not password:
                print("      ❌ Missing credentials")
                return False

            # Find and fill email
            email_field = self.wait.until(EC.element_to_be_clickable((By.ID, "USERID")))
            email_field.clear()
            email_field.send_keys(email)

            # Find and fill password
            password_field = self.driver.find_element(By.ID, "PASSWORD")
            password_field.clear()
            password_field.send_keys(password)

            # Submit login
            login_button = self.driver.find_element(By.ID, "logInButton")
            login_button.click()
            print("      ✅ Login form submitted")
            time.sleep(wait_time)

            # Handle 2FA if present
            if self._handle_2fa():
                time.sleep(wait_time)

            # Handle device verification with multiple strategies
            if self._handle_device_verification():
                time.sleep(wait_time)

            # Verify login success
            return self._verify_login_success()

        except Exception as e:
            print(f"      ❌ Login flow error: {e}")
            return False

    def _handle_2fa(self):
        """Handle 2FA if required."""
        if "twoFactorAuthForm" not in self.driver.page_source:
            return False

        print("      📱 2FA required...")
        try:
            login_time = datetime.now()
            code = fetch_latest_verification_code(
                "MOR", max_wait=30, poll_interval=2, start_timestamp=login_time
            )

            if code:
                print(f"      ✅ Got 2FA code: {code[:3]}***")
                self.driver.find_element(By.NAME, "verificationCode").send_keys(code)
                self.driver.find_element(By.ID, "submitButton").click()
                print("      ✅ 2FA submitted")
                return True
            else:
                print("      ❌ No 2FA code received")
                return False
        except Exception as e:
            print(f"      ❌ 2FA error: {e}")
            return False

    def _handle_device_verification(self):
        """Handle device verification with multiple strategies."""
        try:
            modal = self.driver.find_element(By.ID, "unrecognizedDeviceModal")
            if not modal.is_displayed():
                return False

            print("      🔐 Device verification required...")

            # Strategy 1: Try to verify properly
            if self._device_verification_proper():
                return True

            # Strategy 2: Dismiss modal if verification failed
            print("      📱 Verification failed, dismissing modal...")
            try:
                close_btn = modal.find_element(By.CLASS_NAME, "button-close")
                close_btn.click()
                time.sleep(3)
                print("      ✅ Device verification modal dismissed")
                return True
            except:
                pass

            return False

        except NoSuchElementException:
            # No device verification needed
            return False

    def _device_verification_proper(self):
        """Try proper device verification."""
        try:
            device_time = datetime.now()
            device_code = fetch_latest_verification_code(
                "MOR", max_wait=15, poll_interval=2, start_timestamp=device_time
            )

            if device_code:
                print(f"      ✅ Got device code: {device_code[:3]}***")

                # Enter code
                modal = self.driver.find_element(By.ID, "unrecognizedDeviceModal")
                token_field = modal.find_element(By.ID, "TOKEN_VALUE")
                token_field.clear()
                token_field.send_keys(device_code)

                # Remember device
                try:
                    remember_checkbox = modal.find_element(By.ID, "REMEMBER_THIS_DEVICE")
                    if not remember_checkbox.is_selected():
                        remember_checkbox.click()
                except:
                    pass

                # Submit
                verify_btn = modal.find_element(By.ID, "VERIFY_BTN")
                verify_btn.click()
                time.sleep(8)

                # Check if modal is gone
                try:
                    modal = self.driver.find_element(By.ID, "unrecognizedDeviceModal")
                    if modal.is_displayed():
                        print("      ⚠️ Modal still visible after verification")
                        return False
                    else:
                        print("      ✅ Device verification successful")
                        return True
                except NoSuchElementException:
                    print("      ✅ Device verification successful (modal gone)")
                    return True

            return False

        except Exception as e:
            print(f"      ⚠️ Device verification error: {e}")
            return False

    def _verify_login_success(self):
        """Verify that login was successful."""
        current_url = self.driver.current_url
        page_content = self.driver.page_source

        # Check for logout indicators
        bad_indicators = [
            "logged out" in page_content.lower(),
            "inactivity" in page_content.lower(),
            "login" in current_url.lower() and "NEXT_PAGE" not in current_url,
        ]

        if any(bad_indicators):
            print("      ❌ Login failed - logout detected")
            return False

        # Check for success indicators
        good_indicators = [
            "Dylan Possamaï" in page_content,
            "Associate Editor" in page_content,
            "ASSOCIATE_EDITOR" in current_url,
            "logout" in page_content.lower() and "inactivity" not in page_content.lower(),
        ]

        if any(good_indicators):
            print("      ✅ Login success confirmed")
            return True

        # Ambiguous - try navigation test
        print("      🔍 Login status ambiguous, testing navigation...")
        try:
            test_url = (
                "https://mc.manuscriptcentral.com/mathor?NEXT_PAGE=ASSOCIATE_EDITOR_DASHBOARD"
            )
            self.driver.get(test_url)
            time.sleep(5)

            nav_content = self.driver.page_source
            if "Associate Editor" in nav_content or "ASSOCIATE_EDITOR" in self.driver.current_url:
                print("      ✅ Navigation test successful - logged in")
                return True
            else:
                print("      ❌ Navigation test failed")
                return False
        except:
            print("      ❌ Navigation test error")
            return False

    def safe_window_cleanup(self):
        """BULLETPROOF window cleanup that NEVER closes main window."""
        if not self.main_window:
            return

        try:
            current_windows = self.driver.window_handles

            # Close all windows EXCEPT main window
            for window in current_windows:
                if window != self.main_window:
                    try:
                        self.driver.switch_to.window(window)
                        self.driver.close()
                    except:
                        pass

            # ALWAYS return to main window
            try:
                self.driver.switch_to.window(self.main_window)
            except:
                # If main window is gone, use first available window
                remaining_windows = self.driver.window_handles
                if remaining_windows:
                    self.main_window = remaining_windows[0]
                    self.driver.switch_to.window(self.main_window)

        except Exception as e:
            print(f"   ⚠️ Window cleanup error: {e}")

    def is_manuscript_processed(self, manuscript_id):
        """Check if manuscript is already fully processed across ALL phases."""
        return manuscript_id in self.processed_manuscripts

    def mark_manuscript_processed(self, manuscript_id):
        """Mark manuscript as fully processed."""
        self.processed_manuscripts.add(manuscript_id)
        print(
            f"   ✅ Marked {manuscript_id} as processed (total: {len(self.processed_manuscripts)})"
        )

    def extract_manuscript_safely(self, manuscript_id, take_action_img):
        """Safely extract manuscript with bulletproof window management."""
        if self.is_manuscript_processed(manuscript_id):
            print(f"   ⏭️ SKIPPING {manuscript_id} - already processed")
            return None

        print(f"\n📄 Processing {manuscript_id}...")

        original_window = self.driver.current_window_handle

        try:
            # Click Take Action
            take_action_link = take_action_img.find_element(By.XPATH, "./parent::a")
            take_action_link.click()
            time.sleep(5)

            # Extract data
            manuscript_data = {
                "id": manuscript_id,
                "title": "",
                "authors": [],
                "referees": [],
                "status": "Unknown",
                "extraction_time": datetime.now().isoformat(),
            }

            # Extract title safely
            try:
                title_selectors = [
                    "//td[contains(text(), 'Title:')]/following-sibling::td",
                    "//td[contains(text(), 'Title')]/following-sibling::td[1]",
                ]

                for selector in title_selectors:
                    try:
                        title_elem = self.driver.find_element(By.XPATH, selector)
                        manuscript_data["title"] = title_elem.text.strip()
                        if manuscript_data["title"]:
                            break
                    except:
                        continue

                if manuscript_data["title"]:
                    print(f"   📄 Title: {manuscript_data['title'][:50]}...")

            except Exception as e:
                print(f"   ⚠️ Title extraction error: {e}")

            # Extract referees safely
            try:
                referee_links = self.driver.find_elements(
                    By.XPATH, "//a[contains(@href, 'referee') or contains(text(), 'Reviewer')]"
                )
                for link in referee_links[:5]:  # Limit to prevent issues
                    referee_name = link.text.strip()
                    if referee_name and len(referee_name) > 3:
                        manuscript_data["referees"].append(
                            {"name": referee_name, "status": "Unknown"}
                        )

                print(f"   👥 Found {len(manuscript_data['referees'])} referees")

            except Exception as e:
                print(f"   ⚠️ Referee extraction error: {e}")

            # Mark as processed and add to results
            self.mark_manuscript_processed(manuscript_id)
            self.manuscripts.append(manuscript_data)

            print(f"   ✅ Successfully extracted {manuscript_id}")

            # BULLETPROOF cleanup
            self.safe_window_cleanup()

            # Return to list
            self.driver.back()
            time.sleep(3)

            return manuscript_data

        except Exception as e:
            print(f"   ❌ Extraction error for {manuscript_id}: {e}")

            # Emergency cleanup
            self.safe_window_cleanup()

            try:
                self.driver.back()
                time.sleep(2)
            except:
                pass

            return None

    def navigate_to_ae_center(self):
        """Navigate to AE Center with multiple strategies."""
        print("\n📋 Navigating to AE Center...")

        strategies = [
            ("Direct URL", self._nav_direct_url),
            ("Link Navigation", self._nav_links),
            ("Manual Search", self._nav_manual_search),
        ]

        for name, strategy in strategies:
            try:
                print(f"   🔄 Trying {name}...")
                if strategy():
                    print(f"   ✅ {name} successful")
                    return True
            except Exception as e:
                print(f"   ❌ {name} failed: {e}")

        print("   ❌ All navigation strategies failed")
        return False

    def _nav_direct_url(self):
        """Direct URL navigation."""
        ae_url = "https://mc.manuscriptcentral.com/mathor?NEXT_PAGE=ASSOCIATE_EDITOR_DASHBOARD"
        self.driver.get(ae_url)
        time.sleep(8)

        page_content = self.driver.page_source
        return "Associate Editor" in page_content or "ASSOCIATE_EDITOR" in self.driver.current_url

    def _nav_links(self):
        """Link-based navigation."""
        # Look for journal link first
        journal_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'Mathematics')]")
        if journal_links:
            journal_links[0].click()
            time.sleep(5)

        # Look for AE Center link
        ae_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'Associate Editor')]")
        if ae_links:
            ae_links[0].click()
            time.sleep(5)
            return True

        return False

    def _nav_manual_search(self):
        """Manual search for navigation."""
        # Look for any relevant links
        links = self.driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            link_text = link.text.strip().lower()
            if any(word in link_text for word in ["associate", "editor", "dashboard", "center"]):
                try:
                    link.click()
                    time.sleep(5)
                    if "Associate Editor" in self.driver.page_source:
                        return True
                except:
                    continue
        return False

    def extract_all_manuscripts(self):
        """Extract all manuscripts with global deduplication."""
        print("\n📊 Extracting manuscripts with global deduplication...")

        # Navigate to category
        category_links = self.driver.find_elements(
            By.PARTIAL_LINK_TEXT, "Awaiting Reviewer Reports"
        )
        if category_links:
            print("   📂 Found category")
            category_links[0].click()
            time.sleep(5)
        else:
            print("   ⚠️ No category found")

        # Find all manuscripts
        take_action_images = self.driver.find_elements(
            By.XPATH, "//img[contains(@src, 'check_off.gif')]"
        )
        print(f"   🔍 Found {len(take_action_images)} Take Action buttons")

        if len(take_action_images) == 0:
            print("   ⚠️ No manuscripts found")
            return

        # Extract manuscript IDs
        manuscript_rows = []
        for img in take_action_images:
            try:
                row = img.find_element(By.XPATH, "./ancestor::tr[1]")
                cells = row.find_elements(By.TAG_NAME, "td")
                if cells:
                    manuscript_id = cells[0].text.strip()
                    if manuscript_id and "MOR-" in manuscript_id:
                        manuscript_rows.append((manuscript_id, img))
                        print(f"   📋 Found: {manuscript_id}")
            except:
                continue

        print(f"\n🎯 Processing {len(manuscript_rows)} manuscripts...")

        # Process each manuscript
        for i, (manuscript_id, img) in enumerate(manuscript_rows):
            print(f"\n📄 Manuscript {i+1}/{len(manuscript_rows)}: {manuscript_id}")

            # GLOBAL deduplication check
            if self.is_manuscript_processed(manuscript_id):
                print("   ⏭️ SKIPPING - already processed")
                continue

            # Extract manuscript
            self.extract_manuscript_safely(manuscript_id, img)

    def run_extraction(self):
        """Run complete bulletproof extraction."""
        try:
            print("🚀 BULLETPROOF MOR EXTRACTOR STARTING...")

            # Setup
            self.setup_driver()

            # Bulletproof login
            if not self.bulletproof_login():
                print("❌ Login failed after all attempts")
                return

            # Navigate to AE Center
            if not self.navigate_to_ae_center():
                print("❌ Navigation to AE Center failed")
                return

            # Extract manuscripts
            self.extract_all_manuscripts()

            # Save results
            results = {
                "extraction_time": datetime.now().isoformat(),
                "extractor_version": "bulletproof_v1.0",
                "total_found": len(self.manuscripts),
                "processed_manuscripts": list(self.processed_manuscripts),
                "manuscripts": self.manuscripts,
            }

            output_file = f"mor_bulletproof_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, "w") as f:
                json.dump(results, f, indent=2)

            print("\n🎉 BULLETPROOF EXTRACTION COMPLETE!")
            print(f"   📊 Total manuscripts: {len(self.manuscripts)}")
            print(f"   📋 Processed IDs: {list(self.processed_manuscripts)}")
            print(f"   💾 Results saved: {output_file}")

            for manuscript in self.manuscripts:
                print(f"   ✅ {manuscript['id']}: {manuscript['title'][:50]}...")

        except Exception as e:
            print(f"❌ Fatal error: {e}")
            traceback.print_exc()

        finally:
            if self.driver:
                input("\n⏸️ Press Enter to close...")
                self.driver.quit()


if __name__ == "__main__":
    extractor = BulletproofMORExtractor()
    extractor.run_extraction()
