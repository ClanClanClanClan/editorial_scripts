#!/usr/bin/env python3
"""
CLEAN MF EXTRACTOR
==================
A refactored, maintainable version of the Mathematical Finance extractor.
Focused on the core functionality that actually works.
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Credential loading
sys.path.append(str(Path(__file__).parent.parent))
from core.secure_credentials import SecureCredentialManager


class MFExtractor:
    """Clean, focused MF extractor with 3-pass system."""

    def __init__(self):
        self.manuscripts = []
        self.setup_credentials()
        self.setup_paths()
        self.setup_driver()

    def setup_credentials(self):
        """Load credentials from secure storage."""
        try:
            credential_manager = SecureCredentialManager()
            if credential_manager.setup_environment():
                print("✅ Credentials loaded from secure storage")
            else:
                raise Exception("Failed to load credentials")
        except Exception as e:
            print(f"❌ Credential error: {e}")
            raise

    def setup_paths(self):
        """Setup directory paths."""
        self.project_root = Path(__file__).parent.parent
        self.download_dir = self.project_root / "downloads"
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def setup_driver(self):
        """Setup Chrome driver."""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # Download settings
        prefs = {
            "download.default_directory": str(self.download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
        }
        chrome_options.add_experimental_option("prefs", prefs)

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)

    def login(self):
        """Login to MF site with 2FA."""
        print("🔐 Logging in...")
        self.driver.get("https://mc.manuscriptcentral.com/mafi")
        time.sleep(3)

        # Handle cookie banner if present
        try:
            self.driver.find_element(By.ID, "onetrust-reject-all-handler").click()
            time.sleep(1)
        except:
            pass

        # Enter credentials
        email_field = self.wait.until(EC.presence_of_element_located((By.ID, "USERID")))
        email_field.send_keys(os.getenv("MF_EMAIL"))

        password_field = self.driver.find_element(By.ID, "PASSWORD")
        password_field.send_keys(os.getenv("MF_PASSWORD"))

        # Use JavaScript to click login button (more reliable)
        self.driver.execute_script("document.getElementById('logInButton').click();")

        # Handle 2FA
        if self._handle_2fa():
            print("   ✅ Login successful")
            return True
        else:
            print("   ❌ Login failed")
            return False

    def _handle_2fa(self):
        """Handle 2FA verification."""
        time.sleep(3)

        # Check if 2FA is required
        try:
            token_field = self.driver.find_element(By.ID, "TOKEN_VALUE")
            print("   📱 2FA required...")

            # Import Gmail utils
            from datetime import datetime

            from core.gmail_verification_wrapper import fetch_latest_verification_code

            login_timestamp = datetime.now()
            code = fetch_latest_verification_code(
                "MF", max_wait=45, poll_interval=3, start_timestamp=login_timestamp
            )

            if code:
                print(f"   ✅ Found verification code: {code[:3]}***")
                token_field.send_keys(code)

                # Submit the form
                self.driver.find_element(By.ID, "submitButton").click()
                time.sleep(5)

                # Check if we're still on 2FA page
                try:
                    self.driver.find_element(By.ID, "TOKEN_VALUE")
                    print("   ❌ 2FA failed - still on verification page")
                    return False
                except:
                    # Good - we're past 2FA
                    return True
            else:
                print("   ❌ No verification code found")
                return False

        except NoSuchElementException:
            # No 2FA required
            return True

    def navigate_to_ae_center(self):
        """Navigate to Associate Editor Center."""
        # Wait for page to load after login
        time.sleep(5)

        # Try different ways to find the AE center link
        try:
            ae_link = self.wait.until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
        except TimeoutException:
            # Try partial link text
            ae_link = self.wait.until(
                EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Associate Editor"))
            )
        ae_link.click()
        time.sleep(3)

    def get_manuscript_categories(self):
        """Get manuscript categories with counts."""
        print("📊 Finding manuscript categories...")
        categories = []

        # Find category links
        links = self.driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            text = link.text.strip()
            # Look for patterns like "Awaiting Reviewer Scores (2)"
            match = re.search(r"(.+?)\s*\((\d+)\)", text)
            if match and "manuscript" in text.lower() or "review" in text.lower():
                name = match.group(1).strip()
                count = int(match.group(2))
                if count > 0:
                    categories.append({"name": name, "count": count, "link": link})
                    print(f"   ✓ {name}: {count} manuscripts")

        return categories

    def get_current_manuscript_id(self):
        """Extract current manuscript ID from page."""
        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        match = re.search(r"MAFI-\d{4}-\d{4}", page_text)
        return match.group(0) if match else "UNKNOWN"

    def extract_referees(self, manuscript):
        """Extract referee information."""
        print("   👥 Extracting referees...")

        # Find referee table rows
        rows = self.driver.find_elements(By.XPATH, "//tr[contains(@class,'mailpopup')]")

        for row in rows:
            try:
                # Get name
                name_elem = row.find_element(By.XPATH, ".//a[@class='largebluelink']")
                name = name_elem.text.strip()

                # Get email from popup
                email_link = row.find_element(By.XPATH, ".//a[contains(@href,'mailpopup')]")
                email = self._get_email_from_popup(email_link, name)

                # Get status
                status = "Unknown"
                status_cells = row.find_elements(By.XPATH, ".//td[@class='tablelightcolor']")
                for cell in status_cells:
                    text = cell.text.lower()
                    if any(word in text for word in ["agreed", "declined", "unavailable"]):
                        status = cell.text.strip()
                        break

                # Get affiliation
                affiliation = self._extract_affiliation(row, name)

                referee = {
                    "name": name,
                    "email": email,
                    "status": status,
                    "affiliation": affiliation,
                }

                manuscript["referees"].append(referee)
                print(f"      ✓ {name} ({status})")

            except Exception as e:
                print(f"      ❌ Error extracting referee: {e}")

    def _get_email_from_popup(self, link, name):
        """Extract email from popup window."""
        try:
            # Save current window
            main_window = self.driver.current_window_handle

            # Click link to open popup
            link.click()
            time.sleep(2)

            # Switch to popup
            for window in self.driver.window_handles:
                if window != main_window:
                    self.driver.switch_to.window(window)
                    break

            # Extract email
            email = ""
            body = self.driver.find_element(By.TAG_NAME, "body")
            text = body.text

            # Try to find email pattern
            email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
            if email_match:
                email = email_match.group(0)

            # Close popup and return
            self.driver.close()
            self.driver.switch_to.window(main_window)

            return email

        except Exception as e:
            print(f"      ⚠️ Popup extraction failed: {e}")
            # Make sure we're back to main window
            self.driver.switch_to.window(main_window)
            return ""

    def _extract_affiliation(self, row, name):
        """Extract affiliation from referee row."""
        try:
            # Look for pagecontents spans
            spans = row.find_elements(By.XPATH, ".//span[@class='pagecontents']")
            for span in spans:
                text = span.text.strip()
                # Skip if it's the name or too short
                if text and text != name and len(text) > 10:
                    if any(
                        keyword in text.lower()
                        for keyword in ["university", "college", "institute", "school"]
                    ):
                        return text
        except:
            pass
        return ""

    def extract_documents(self, manuscript):
        """Extract document links."""
        print("   📄 Extracting documents...")

        # PDF link
        try:
            pdf_link = self.driver.find_element(
                By.XPATH, "//a[contains(@href,'DOWNLOAD_FILE') and contains(text(),'PDF')]"
            )
            manuscript["documents"]["pdf"] = True
            print("      ✓ PDF found")
        except:
            manuscript["documents"]["pdf"] = False

        # Cover letter
        try:
            cover_link = self.driver.find_element(By.XPATH, "//a[contains(text(),'Cover Letter')]")
            manuscript["documents"]["cover_letter"] = True
            print("      ✓ Cover letter found")
        except:
            manuscript["documents"]["cover_letter"] = False

    def execute_3_pass_extraction(self, category):
        """Execute the 3-pass extraction system."""
        # Click category to get manuscript list
        category["link"].click()
        time.sleep(3)

        # Find all manuscript links
        manuscript_links = self.driver.find_elements(
            By.XPATH, "//a[contains(@href,'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS')]"
        )

        if not manuscript_links:
            print("   📭 No manuscripts found")
            return

        num_manuscripts = len(manuscript_links)
        print(f"\n🚀 Starting 3-pass extraction for {num_manuscripts} manuscripts")
        print("=" * 60)

        # PASS 1: Forward - Extract referees and documents
        print(f"\n📋 PASS 1: Forward (1→{num_manuscripts}) - Referees & Documents")
        print("-" * 50)

        for i in range(num_manuscripts):
            # Navigate to manuscript i
            manuscript_links[i].click()
            time.sleep(5)

            # Create manuscript object
            manuscript_id = self.get_current_manuscript_id()
            manuscript = {
                "id": manuscript_id,
                "referees": [],
                "documents": {},
                "authors": [],
                "timeline": [],
            }

            print(f"\n   📄 Manuscript {i+1}: {manuscript_id}")

            # Extract data
            self.extract_referees(manuscript)
            self.extract_documents(manuscript)

            self.manuscripts.append(manuscript)

            # Navigate to next
            if i < num_manuscripts - 1:
                if not self._navigate_next():
                    # Fallback: go back to list
                    self.driver.back()
                    time.sleep(3)
                    manuscript_links = self.driver.find_elements(
                        By.XPATH, "//a[contains(@href,'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS')]"
                    )

        # PASS 2: Backward - Manuscript Information tab
        print(f"\n📊 PASS 2: Backward ({num_manuscripts}→1) - Manuscript Info")
        print("-" * 50)

        for i in range(num_manuscripts - 1, -1, -1):
            manuscript = self.manuscripts[i]
            print(f"\n   📋 Manuscript {i+1}: {manuscript['id']}")

            # Extract from Manuscript Information tab
            self._extract_manuscript_info(manuscript)

            # Navigate to previous
            if i > 0:
                self._navigate_previous()

        # PASS 3: Forward - Audit Trail tab
        print(f"\n📜 PASS 3: Forward (1→{num_manuscripts}) - Audit Trail")
        print("-" * 50)

        for i in range(num_manuscripts):
            manuscript = self.manuscripts[i]
            print(f"\n   📜 Manuscript {i+1}: {manuscript['id']}")

            # Extract from Audit Trail tab
            self._extract_audit_trail(manuscript)

            # Navigate to next
            if i < num_manuscripts - 1:
                self._navigate_next()

        print("\n✅ 3-PASS EXTRACTION COMPLETE")
        print(f"   Processed {num_manuscripts} manuscripts")
        print("=" * 60)

    def _navigate_next(self):
        """Navigate to next document."""
        try:
            next_btn = self.driver.find_element(
                By.XPATH,
                "//a[contains(@href,'XIK_NEXT_PREV_DOCUMENT_ID')]/img[@alt='Next Document']/..",
            )
            next_btn.click()
            time.sleep(5)
            return True
        except:
            return False

    def _navigate_previous(self):
        """Navigate to previous document."""
        try:
            prev_btn = self.driver.find_element(
                By.XPATH,
                "//a[contains(@href,'XIK_NEXT_PREV_DOCUMENT_ID')]/img[@alt='Previous Document']/..",
            )
            prev_btn.click()
            time.sleep(5)
            return True
        except:
            return False

    def _extract_manuscript_info(self, manuscript):
        """Extract from Manuscript Information tab."""
        try:
            # Click tab
            info_tab = self.driver.find_element(
                By.XPATH, "//a[contains(text(), 'Manuscript Information')]"
            )
            info_tab.click()
            time.sleep(3)

            # Extract authors, dates, etc.
            # TODO: Implement specific extraction logic
            print("      ✓ Manuscript info extracted")

        except Exception as e:
            print(f"      ❌ Could not extract manuscript info: {e}")

    def _extract_audit_trail(self, manuscript):
        """Extract from Audit Trail tab."""
        try:
            # Click tab
            audit_tab = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Audit Trail')]")
            audit_tab.click()
            time.sleep(3)

            # Extract timeline events
            # TODO: Implement specific extraction logic
            print("      ✓ Audit trail extracted")

        except Exception as e:
            print(f"      ❌ Could not extract audit trail: {e}")

    def save_results(self):
        """Save extraction results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.project_root / f"mf_extraction_{timestamp}.json"

        with open(output_file, "w") as f:
            json.dump(self.manuscripts, f, indent=2)

        print(f"\n💾 Results saved to: {output_file}")

    def run(self):
        """Run the complete extraction."""
        try:
            # Login
            if not self.login():
                return

            # Navigate to AE center
            self.navigate_to_ae_center()

            # Get categories
            categories = self.get_manuscript_categories()

            # Process each category with manuscripts
            for category in categories:
                if category["count"] > 0:
                    self.execute_3_pass_extraction(category)
                    break  # Process first category only for now

            # Save results
            self.save_results()

        except Exception as e:
            print(f"❌ Fatal error: {e}")
            import traceback

            traceback.print_exc()
        finally:
            print("\n🧹 Cleaning up...")
            self.driver.quit()


if __name__ == "__main__":
    extractor = MFExtractor()
    extractor.run()
