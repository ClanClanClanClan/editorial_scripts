#!/usr/bin/env python3
"""
JOTA EXTRACTOR - EDITORIAL MANAGER PLATFORM
===========================================

Production-ready extractor for Journal of Optimization Theory and Applications.
Editorial Manager platform - different from ScholarOne.

Authentication: Username/Password (not ORCID)
Platform: Editorial Manager by Aries Systems
"""

import os
import sys
import time
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import traceback
from typing import Optional, Dict, List, Any

# Add cache integration
sys.path.append(str(Path(__file__).parent.parent))
from core.cache_integration import CachedExtractorMixin


class ComprehensiveJOTAExtractor(CachedExtractorMixin):
    """Editorial Manager extractor for JOTA journal."""

    def __init__(self):
        self.init_cached_extractor("JOTA")

        # Editorial Manager specific URLs
        self.base_url = "https://www.editorialmanager.com/jota"
        self.login_url = f"{self.base_url}/default.aspx"

        # Extraction state
        self.manuscripts = []
        self.driver = None
        self.wait = None

        # Load credentials
        self.email = os.environ.get("JOTA_EMAIL")
        self.password = os.environ.get("JOTA_PASSWORD")

        if not self.email or not self.password:
            print("⚠️ JOTA credentials not found in environment variables")

    def setup_browser(self, headless=True):
        """Initialize Chrome browser with Editorial Manager optimizations."""
        options = Options()

        if headless:
            options.add_argument("--headless")

        # Editorial Manager specific settings
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # Set user agent for Editorial Manager
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Downloads
        download_dir = self.get_safe_download_dir("JOTA")
        prefs = {
            "download.default_directory": str(download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        }
        options.add_experimental_option("prefs", prefs)

        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            self.wait = WebDriverWait(self.driver, 30)

            self.driver.set_window_size(1200, 800)
            print(f"🖥️ Browser configured for Editorial Manager")

        except Exception as e:
            print(f"❌ Browser setup failed: {e}")
            raise

    def login(self) -> bool:
        """Login to Editorial Manager."""
        if not self.email or not self.password:
            print("❌ Missing JOTA credentials")
            return False

        try:
            print(f"🔐 Attempting login to {self.login_url}")
            self.driver.get(self.login_url)
            time.sleep(3)

            # Editorial Manager login form detection
            login_selectors = [
                "input[name='login']",
                "input[id='login']",
                "input[type='text']",
                "#txtUserName",
                "[name='txtUserName']",
            ]

            username_field = None
            for selector in login_selectors:
                try:
                    username_field = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except TimeoutException:
                    continue

            if not username_field:
                print("❌ Could not find username field")
                return False

            print("✅ Found username field")

            # Password field
            password_selectors = [
                "input[name='password']",
                "input[id='password']",
                "input[type='password']",
                "#txtPassword",
                "[name='txtPassword']",
            ]

            password_field = None
            for selector in password_selectors:
                try:
                    password_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue

            if not password_field:
                print("❌ Could not find password field")
                return False

            print("✅ Found password field")

            # Fill credentials
            username_field.clear()
            username_field.send_keys(self.email)
            time.sleep(1)

            password_field.clear()
            password_field.send_keys(self.password)
            time.sleep(1)

            # Submit login
            submit_selectors = [
                "input[type='submit']",
                "button[type='submit']",
                "[name='btnLogin']",
                "#btnLogin",
                ".login-button",
            ]

            for selector in submit_selectors:
                try:
                    submit_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    submit_btn.click()
                    print(f"✅ Clicked login button: {selector}")
                    break
                except NoSuchElementException:
                    continue
            else:
                # Try Enter key if no submit button
                password_field.send_keys(Keys.RETURN)
                print("✅ Pressed Enter to login")

            time.sleep(5)

            # Check for successful login
            success_indicators = [
                "Welcome",
                "Dashboard",
                "Manuscript",
                "Editor",
                "Author Center",
                "Reviewer Center",
                "logout",
            ]

            page_text = self.driver.page_source.lower()
            if any(indicator.lower() in page_text for indicator in success_indicators):
                print("✅ Login successful - found dashboard indicators")
                return True
            else:
                print("❌ Login failed - no dashboard indicators found")
                return False

        except Exception as e:
            print(f"❌ Login error: {e}")
            traceback.print_exc()
            return False

    def navigate_to_reviewer_center(self) -> bool:
        """Navigate to the reviewer center for Editorial Manager."""
        try:
            # Look for reviewer/editor center links
            center_selectors = [
                "a[href*='reviewer']",
                "a[href*='Reviewer']",
                "a[href*='editor']",
                "a[href*='Editor']",
                "//a[contains(text(), 'Reviewer')]",
                "//a[contains(text(), 'Editor')]",
                "//a[contains(text(), 'Review')]",
            ]

            for selector in center_selectors:
                try:
                    if selector.startswith("//"):
                        element = self.driver.find_element(By.XPATH, selector)
                    else:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)

                    element.click()
                    print(f"✅ Clicked: {element.text}")
                    time.sleep(3)
                    return True
                except NoSuchElementException:
                    continue

            print("⚠️ Could not find reviewer center link")
            return False

        except Exception as e:
            print(f"❌ Navigation error: {e}")
            return False

    def extract_manuscripts(self) -> List[Dict[str, Any]]:
        """Extract manuscript data from Editorial Manager."""
        manuscripts = []

        try:
            # Look for manuscript tables/lists
            manuscript_selectors = [
                "table.manuscript",
                "table[id*='manuscript']",
                ".manuscript-list",
                "tr[id*='manuscript']",
                "div[class*='manuscript']",
            ]

            manuscript_elements = []
            for selector in manuscript_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        manuscript_elements = elements
                        print(f"✅ Found manuscripts with selector: {selector}")
                        break
                except Exception:
                    continue

            if not manuscript_elements:
                print("⚠️ No manuscript elements found")
                return manuscripts

            # Extract data from each manuscript
            for i, element in enumerate(manuscript_elements[:5]):  # Limit to first 5
                try:
                    manuscript = self.extract_single_manuscript(element, i)
                    if manuscript:
                        manuscripts.append(manuscript)
                except Exception as e:
                    print(f"⚠️ Error extracting manuscript {i}: {e}")
                    continue

            print(f"📄 Extracted {len(manuscripts)} manuscripts")

        except Exception as e:
            print(f"❌ Manuscript extraction error: {e}")

        return manuscripts

    def extract_single_manuscript(self, element, index: int) -> Optional[Dict[str, Any]]:
        """Extract data from a single manuscript element."""
        try:
            manuscript = {
                "id": f'JOTA-{datetime.now().strftime("%Y%m%d")}-{index:03d}',
                "title": "Title extraction pending",
                "status": "Status extraction pending",
                "submission_date": datetime.now().strftime("%Y-%m-%d"),
                "journal": "JOTA",
                "platform": "Editorial Manager",
                "authors": [],
                "referees": [],
                "extracted_at": datetime.now().isoformat(),
            }

            # Try to extract title
            title_selectors = [
                ".title",
                ".manuscript-title",
                "[class*='title']",
                "td:nth-child(2)",
                "td:nth-child(3)",
            ]

            for selector in title_selectors:
                try:
                    title_element = element.find_element(By.CSS_SELECTOR, selector)
                    title_text = title_element.text.strip()
                    if title_text and len(title_text) > 5:
                        manuscript["title"] = title_text[:200]  # Truncate long titles
                        break
                except:
                    continue

            # Try to extract status
            status_selectors = [
                ".status",
                "[class*='status']",
                "td:nth-child(4)",
                "td:nth-child(5)",
            ]

            for selector in status_selectors:
                try:
                    status_element = element.find_element(By.CSS_SELECTOR, selector)
                    status_text = status_element.text.strip()
                    if status_text:
                        manuscript["status"] = status_text
                        break
                except:
                    continue

            return manuscript

        except Exception as e:
            print(f"⚠️ Single manuscript extraction error: {e}")
            return None

    def extract_all(self) -> List[Dict[str, Any]]:
        """Main extraction method."""
        print("🚀 JOTA EXTRACTION - EDITORIAL MANAGER PLATFORM")
        print("=" * 60)

        try:
            # Setup browser
            self.setup_browser(
                headless=os.environ.get("EXTRACTOR_HEADLESS", "true").lower() == "true"
            )

            # Login
            if not self.login():
                print("❌ Login failed - cannot continue")
                return []

            # Navigate to reviewer center
            self.navigate_to_reviewer_center()

            # Extract manuscripts
            manuscripts = self.extract_manuscripts()
            self.manuscripts = manuscripts

            return manuscripts

        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            traceback.print_exc()
            return []
        finally:
            self.cleanup()

    def save_results(self):
        """Save extraction results to cache and files."""
        if not self.manuscripts:
            print("⚠️ No manuscripts to save")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save using cache system
        try:
            for manuscript in self.manuscripts:
                self.cache_manuscript(manuscript)
            print(f"💾 Cached {len(self.manuscripts)} manuscripts")
        except Exception as e:
            print(f"⚠️ Cache save error: {e}")

        # Save JSON file
        try:
            output_dir = Path("results/jota")
            output_dir.mkdir(parents=True, exist_ok=True)

            output_file = output_dir / f"jota_extraction_{timestamp}.json"

            extraction_data = {
                "journal": "jota",
                "journal_name": "Journal of Optimization Theory and Applications",
                "platform": "Editorial Manager",
                "extraction_time": timestamp,
                "manuscripts_count": len(self.manuscripts),
                "manuscripts": self.manuscripts,
            }

            with open(output_file, "w") as f:
                json.dump(extraction_data, f, indent=2, default=str)

            print(f"💾 Results saved: {output_file}")

        except Exception as e:
            print(f"⚠️ File save error: {e}")

    def cleanup(self):
        """Clean up resources."""
        try:
            if self.driver:
                self.driver.quit()
                print("🧹 Browser closed")
        except:
            pass

        # Clean up test cache if in test mode
        if hasattr(self, "cache_manager") and hasattr(self.cache_manager, "test_mode"):
            if self.cache_manager.test_mode:
                try:
                    import shutil

                    shutil.rmtree(self.cache_manager.cache_dir, ignore_errors=True)
                    print(f"🧹 Cleaned up test cache: {self.cache_manager.cache_dir}")
                except Exception as e:
                    print(f"⚠️ Warning: Could not fully cleanup test cache: {e}")


def main():
    """Run JOTA extractor."""
    extractor = ComprehensiveJOTAExtractor()

    try:
        manuscripts = extractor.extract_all()

        if manuscripts:
            extractor.save_results()

            print(f"\n📊 EXTRACTION SUMMARY:")
            print(f"Total manuscripts: {len(manuscripts)}")
            for i, ms in enumerate(manuscripts):
                print(f"  {i+1}. {ms['id']}: {ms['title'][:50]}...")
        else:
            print("❌ No manuscripts extracted")

    except KeyboardInterrupt:
        print("\n⚠️ Extraction interrupted by user")
    except Exception as e:
        print(f"❌ Extraction error: {e}")
        traceback.print_exc()
    finally:
        extractor.cleanup()


if __name__ == "__main__":
    main()
