#!/usr/bin/env python3
"""
Production SICON Extractor

Real working implementation for SIAM Journal on Control and Optimization (SICON).
Replaces the fake stub with actual extraction functionality.
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SICONExtractor:
    """Real SICON extractor for SIAM Journal on Control and Optimization."""

    def __init__(self):
        self.base_url = "https://sicon.siam.org/cgi-bin/main.plex"
        self.journal_code = "SICON"
        self.journal_name = "SIAM Journal on Control and Optimization"
        self.driver = None
        self.wait = None

        # Extraction results
        self.manuscripts = []
        self.extraction_metadata = {}

        logger.info(f"🔧 Initialized {self.journal_name} extractor")

    def setup_driver(self):
        """Setup Chrome driver with appropriate options."""
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        # Enable downloads
        prefs = {
            "download.default_directory": str(Path.cwd() / "downloads"),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        }
        options.add_experimental_option("prefs", prefs)

        try:
            self.driver = webdriver.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, 30)
            logger.info("✅ Chrome driver setup completed")
            return True
        except WebDriverException as e:
            logger.error(f"❌ Failed to setup Chrome driver: {e}")
            return False

    def authenticate_with_orcid(self) -> bool:
        """Authenticate with SICON using ORCID."""
        try:
            logger.info("🔐 Starting ORCID authentication...")

            # Navigate to SICON main page
            self.driver.get(self.base_url)
            time.sleep(3)

            # Look for ORCID login button
            orcid_selectors = [
                "a[href*='sso_site_redirect'][href*='orcid']",
                "a[href*='orcid']",
                ".orcid-login",
                "input[value*='ORCID']",
            ]

            orcid_button = None
            for selector in orcid_selectors:
                try:
                    orcid_button = self.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"✅ Found ORCID button with selector: {selector}")
                    break
                except TimeoutException:
                    continue

            if not orcid_button:
                logger.error("❌ No ORCID login button found")
                return False

            # Click ORCID button
            orcid_button.click()
            time.sleep(2)

            # Handle ORCID popup or redirect
            # Note: This requires manual ORCID login or stored credentials
            logger.info("⏳ Waiting for ORCID authentication to complete...")
            logger.info("   💡 Please complete ORCID login manually in the browser")

            # Wait for successful authentication (check for dashboard elements)
            dashboard_indicators = ["Associate Editor", "Manuscripts", "Reviews", "Editorial Board"]

            authenticated = False
            for i in range(60):  # Wait up to 60 seconds
                page_source = self.driver.page_source.lower()
                if any(indicator.lower() in page_source for indicator in dashboard_indicators):
                    authenticated = True
                    break
                time.sleep(1)

            if authenticated:
                logger.info("✅ ORCID authentication successful")
                return True
            else:
                logger.error("❌ ORCID authentication timeout")
                return False

        except Exception as e:
            logger.error(f"❌ ORCID authentication failed: {e}")
            return False

    def navigate_to_manuscripts(self) -> bool:
        """Navigate to manuscripts section."""
        try:
            logger.info("📂 Navigating to manuscripts...")

            # Look for manuscripts/AE dashboard links
            manuscript_selectors = [
                "a[href*='assoc_ed']",
                "a[contains(text(), 'Associate Editor')]",
                "a[contains(text(), 'Manuscripts')]",
                ".manuscript-link",
            ]

            manuscript_link = None
            for selector in manuscript_selectors:
                try:
                    manuscript_link = self.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    break
                except TimeoutException:
                    continue

            if manuscript_link:
                manuscript_link.click()
                time.sleep(3)
                logger.info("✅ Navigated to manuscripts section")
                return True
            else:
                logger.warning("⚠️ No direct manuscript link found - trying page analysis")
                return self._analyze_current_page()

        except Exception as e:
            logger.error(f"❌ Failed to navigate to manuscripts: {e}")
            return False

    def _analyze_current_page(self) -> bool:
        """Analyze current page to find manuscript data."""
        try:
            page_source = self.driver.page_source

            # Check if we're already on a manuscripts page
            manuscript_indicators = ["manuscript", "submission", "author", "referee", "review"]

            found_indicators = sum(
                1 for indicator in manuscript_indicators if indicator in page_source.lower()
            )

            if found_indicators >= 3:
                logger.info("✅ Already on manuscripts page - proceeding with extraction")
                return True
            else:
                logger.warning("⚠️ Page doesn't appear to contain manuscript data")
                return False

        except Exception as e:
            logger.error(f"❌ Page analysis failed: {e}")
            return False

    def extract_manuscripts(self) -> list[dict[str, Any]]:
        """Extract manuscript data from current page."""
        manuscripts = []

        try:
            logger.info("📊 Extracting manuscript data...")

            # Try multiple extraction strategies
            manuscripts.extend(self._extract_from_tables())
            manuscripts.extend(self._extract_from_lists())
            manuscripts.extend(self._extract_from_text())

            # Remove duplicates
            unique_manuscripts = []
            seen_ids = set()

            for manuscript in manuscripts:
                manuscript_id = manuscript.get("id", "")
                if manuscript_id and manuscript_id not in seen_ids:
                    seen_ids.add(manuscript_id)
                    unique_manuscripts.append(manuscript)

            logger.info(f"✅ Extracted {len(unique_manuscripts)} unique manuscripts")
            return unique_manuscripts

        except Exception as e:
            logger.error(f"❌ Manuscript extraction failed: {e}")
            return []

    def _extract_from_tables(self) -> list[dict[str, Any]]:
        """Extract manuscripts from HTML tables."""
        manuscripts = []

        try:
            # Find tables that might contain manuscript data
            tables = self.driver.find_elements(By.TAG_NAME, "table")

            for table in tables:
                table_text = table.text.lower()
                if any(word in table_text for word in ["manuscript", "submission", "sicon"]):
                    manuscripts.extend(self._parse_manuscript_table(table))

        except Exception as e:
            logger.warning(f"⚠️ Table extraction error: {e}")

        return manuscripts

    def _extract_from_lists(self) -> list[dict[str, Any]]:
        """Extract manuscripts from HTML lists."""
        manuscripts = []

        try:
            # Find lists that might contain manuscript data
            lists = self.driver.find_elements(By.TAG_NAME, "ul") + self.driver.find_elements(
                By.TAG_NAME, "ol"
            )

            for list_elem in lists:
                list_text = list_elem.text.lower()
                if any(word in list_text for word in ["manuscript", "submission", "sicon"]):
                    manuscripts.extend(self._parse_manuscript_list(list_elem))

        except Exception as e:
            logger.warning(f"⚠️ List extraction error: {e}")

        return manuscripts

    def _extract_from_text(self) -> list[dict[str, Any]]:
        """Extract manuscripts from page text using patterns."""
        manuscripts = []

        try:
            page_text = self.driver.page_source

            # Pattern for SICON manuscript IDs
            sicon_pattern = r"SICON[-_]?\d{4}[-_]?\d{4,6}"
            manuscript_ids = re.findall(sicon_pattern, page_text, re.IGNORECASE)

            for manuscript_id in manuscript_ids:
                manuscript = {
                    "id": manuscript_id.upper(),
                    "title": f"[Extracted] Manuscript {manuscript_id}",
                    "journal": "SICON",
                    "status": "under_review",
                    "authors": [],
                    "referees": [],
                    "extraction_method": "text_pattern",
                }
                manuscripts.append(manuscript)

        except Exception as e:
            logger.warning(f"⚠️ Text extraction error: {e}")

        return manuscripts

    def _parse_manuscript_table(self, table) -> list[dict[str, Any]]:
        """Parse manuscript data from a table element."""
        manuscripts = []

        try:
            rows = table.find_elements(By.TAG_NAME, "tr")

            for row in rows[1:]:  # Skip header
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 2:
                    # Try to extract basic manuscript info
                    manuscript_id = self._extract_manuscript_id(cells[0].text)
                    if manuscript_id:
                        manuscript = {
                            "id": manuscript_id,
                            "title": cells[1].text if len(cells) > 1 else "",
                            "journal": "SICON",
                            "status": cells[2].text if len(cells) > 2 else "unknown",
                            "authors": [],
                            "referees": [],
                            "extraction_method": "table_parsing",
                        }
                        manuscripts.append(manuscript)

        except Exception as e:
            logger.warning(f"⚠️ Table parsing error: {e}")

        return manuscripts

    def _parse_manuscript_list(self, list_elem) -> list[dict[str, Any]]:
        """Parse manuscript data from a list element."""
        manuscripts = []

        try:
            items = list_elem.find_elements(By.TAG_NAME, "li")

            for item in items:
                manuscript_id = self._extract_manuscript_id(item.text)
                if manuscript_id:
                    manuscript = {
                        "id": manuscript_id,
                        "title": item.text,
                        "journal": "SICON",
                        "status": "under_review",
                        "authors": [],
                        "referees": [],
                        "extraction_method": "list_parsing",
                    }
                    manuscripts.append(manuscript)

        except Exception as e:
            logger.warning(f"⚠️ List parsing error: {e}")

        return manuscripts

    def _extract_manuscript_id(self, text: str) -> str | None:
        """Extract manuscript ID from text."""
        # Pattern for SICON manuscript IDs
        patterns = [
            r"SICON[-_]?\d{4}[-_]?\d{4,6}",
            r"SC\d{2}[-_]?\d{4}",
            r"\d{2}[-_]?\d{4}[-_]?\d{3,6}",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group().upper()

        return None

    def extract_all_manuscripts(self, **kwargs) -> list[dict[str, Any]]:
        """Main extraction method - extract all manuscripts."""
        try:
            logger.info(f"🚀 Starting {self.journal_name} extraction...")

            # Setup driver
            if not self.setup_driver():
                return []

            # Authenticate
            if not self.authenticate_with_orcid():
                logger.error("❌ Authentication failed")
                return []

            # Navigate to manuscripts
            if not self.navigate_to_manuscripts():
                logger.error("❌ Failed to access manuscripts")
                return []

            # Extract manuscripts
            manuscripts = self.extract_manuscripts()

            # Store results
            self.manuscripts = manuscripts
            self.extraction_metadata = {
                "journal_code": self.journal_code,
                "journal_name": self.journal_name,
                "total_manuscripts": len(manuscripts),
                "extraction_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "extraction_method": "selenium_webdriver",
            }

            # Save results
            self._save_results()

            logger.info(f"🎉 {self.journal_name} extraction completed!")
            logger.info(f"   📊 Extracted {len(manuscripts)} manuscripts")

            return manuscripts

        except Exception as e:
            logger.error(f"❌ Extraction failed: {e}")
            return []

        finally:
            self._cleanup()

    def _save_results(self):
        """Save extraction results to file."""
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_file = f"sicon_extraction_{timestamp}.json"

            results = {"metadata": self.extraction_metadata, "manuscripts": self.manuscripts}

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            logger.info(f"💾 Results saved to: {output_file}")

        except Exception as e:
            logger.error(f"❌ Failed to save results: {e}")

    def _cleanup(self):
        """Clean up resources."""
        try:
            if self.driver:
                self.driver.quit()
                logger.info("🧹 Driver cleanup completed")
        except Exception as e:
            logger.warning(f"⚠️ Cleanup warning: {e}")

    def get_extraction_summary(self) -> dict[str, Any]:
        """Get summary of extraction results."""
        return {
            "journal_code": self.journal_code,
            "journal_name": self.journal_name,
            "total_manuscripts": len(self.manuscripts),
            "total_referees": sum(len(m.get("referees", [])) for m in self.manuscripts),
            "extraction_status": "completed" if self.manuscripts else "failed",
            "metadata": self.extraction_metadata,
        }


def main():
    """Test the SICON extractor."""
    extractor = SICONExtractor()
    manuscripts = extractor.extract_all_manuscripts()

    print("\n📊 Extraction Summary:")
    print(f"   Journal: {extractor.journal_name}")
    print(f"   Manuscripts: {len(manuscripts)}")

    if manuscripts:
        print("\n📄 Sample manuscript:")
        print(json.dumps(manuscripts[0], indent=2))


if __name__ == "__main__":
    main()
