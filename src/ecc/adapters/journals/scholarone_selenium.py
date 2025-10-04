"""ScholarOne adapter using Selenium (proven to bypass anti-bot detection)."""

import asyncio
import os
import re

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.ecc.adapters.journals.base import JournalConfig
from src.ecc.core.domain.models import (
    Manuscript,
    ManuscriptStatus,
)
from src.ecc.core.logging_system import ExtractorLogger


class ScholarOneSeleniumAdapter:
    """Selenium-based adapter for ScholarOne (MF/MOR) - bypasses anti-bot detection."""

    def __init__(self, config: JournalConfig):
        self.config = config
        self.logger = ExtractorLogger(f"{config.journal_id}_selenium")
        self.driver = None
        self.manuscript_pattern = self._get_manuscript_pattern()

    def _get_manuscript_pattern(self) -> str:
        """Get journal-specific manuscript ID pattern."""
        patterns = {
            "MF": r"MAFI-\d{4}-\d{4}",
            "MOR": r"MOR-\d{4}-\d{4}",
        }
        return patterns.get(self.config.journal_id, r"\w+-\d{4}-\d{4}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()

    async def initialize(self):
        """Initialize Selenium WebDriver."""
        self.logger.info(f"Initializing Selenium adapter for {self.config.journal_id}")

        # Set up synchronously - simpler and more reliable
        chrome_options = Options()

        if self.config.headless:
            chrome_options.add_argument("--headless=new")

        # Anti-detection options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(f"user-agent={self.config.user_agent}")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.maximize_window()

        # Override navigator.webdriver
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        self.logger.info("Selenium WebDriver initialized successfully")

    async def cleanup(self):
        """Clean up Selenium resources."""
        if self.driver:
            self.driver.quit()
            self.logger.info("Selenium WebDriver cleaned up")

    async def authenticate(self) -> bool:
        """Authenticate with ScholarOne using Selenium."""
        try:
            self.logger.info("Starting ScholarOne authentication (Selenium)")

            # Navigate to login page
            self.driver.get(self.config.url)

            # Wait for login form
            wait = WebDriverWait(self.driver, 15)

            try:
                userid_field = wait.until(EC.presence_of_element_located((By.ID, "USERID")))
                self.logger.info("Login form found!")
            except TimeoutException:
                self.logger.error("Login form not found")
                return False

            # Get credentials
            credentials = await self._get_credentials()

            # Fill login form
            userid_field.send_keys(credentials["username"])
            password_field = self.driver.find_element(By.ID, "PASSWORD")
            password_field.send_keys(credentials["password"])

            # Record timestamp before submitting login
            import time

            login_timestamp = time.time()

            # Submit login
            login_button = self.driver.find_element(By.ID, "logInButton")
            login_button.click()

            # Wait for page load
            await asyncio.sleep(3)

            # Check for 2FA
            try:
                token_field = self.driver.find_element(By.ID, "TOKEN_VALUE")
                if token_field:
                    self.logger.info("2FA required - fetching code from Gmail")

                    # Fetch verification code using production Gmail API
                    import sys
                    from pathlib import Path

                    # Get project root and add production/src/core to path
                    # From src/ecc/adapters/journals -> go up 5 levels to project root
                    project_root = Path(__file__).parent.parent.parent.parent.parent
                    prod_core = project_root / "production" / "src" / "core"
                    prod_core = prod_core.resolve()
                    if str(prod_core) not in sys.path:
                        sys.path.insert(0, str(prod_core))

                    import gmail_verification

                    fetch_latest_verification_code = (
                        gmail_verification.fetch_latest_verification_code
                    )

                    code = None
                    for attempt in range(3):
                        self.logger.info(f"Gmail fetch attempt {attempt + 1}/3...")
                        await asyncio.sleep(10 if attempt == 0 else 5)

                        code = fetch_latest_verification_code(
                            self.config.journal_id,
                            max_wait=30,
                            poll_interval=2,
                            start_timestamp=login_timestamp,
                        )

                        if code and len(code) == 6 and code.isdigit():
                            self.logger.info(f"Found verification code: {code[:3]}***")
                            break
                        else:
                            code = None

                    if not code:
                        # Fallback to manual entry when Gmail not available
                        self.logger.warning("Gmail fetch failed - falling back to manual entry")
                        try:
                            code = input(
                                "   📱 Please enter the 6-digit verification code from your email: "
                            ).strip()
                            if not code or len(code) != 6 or not code.isdigit():
                                self.logger.error("Invalid code format")
                                return False
                        except (EOFError, KeyboardInterrupt):
                            self.logger.error("No input provided")
                            return False

                    # Enter verification code
                    self.logger.info("Entering verification code...")
                    token_field = self.driver.find_element(By.ID, "TOKEN_VALUE")
                    token_field.clear()
                    token_field.send_keys(code)

                    # Click verify button
                    verify_btn = self.driver.find_element(By.ID, "VERIFY_BTN")
                    verify_btn.click()

                    # Wait for verification
                    await asyncio.sleep(3)

            except Exception as e:
                # No 2FA required or error
                self.logger.debug(f"2FA check: {e}")

            # Verify login success - look for role center links (not on login page)
            try:
                # Wait for page to load and check for success indicators
                wait_extended = WebDriverWait(self.driver, 30)

                # First, ensure we're NOT still on login page
                await asyncio.sleep(2)
                current_url = self.driver.current_url
                if "page=LOGIN" in current_url or "login" in current_url.lower():
                    self.logger.error("Still on login page - authentication failed")
                    return False

                # Look for role center links (these only appear when logged in)
                success_selectors = [
                    (By.LINK_TEXT, "Associate Editor Center"),
                    (By.LINK_TEXT, "Author"),
                    (By.LINK_TEXT, "Reviewer"),
                    (By.PARTIAL_LINK_TEXT, "Center"),
                    (By.XPATH, "//a[contains(@href, 'ASSOCIATE_EDITOR')]"),
                    (By.XPATH, "//a[contains(text(), 'Log Out') or contains(text(), 'Logout')]"),
                ]

                for selector in success_selectors:
                    try:
                        element = wait_extended.until(EC.presence_of_element_located(selector))
                        if element:
                            self.logger.info(f"Authentication successful! (found {selector})")
                            return True
                    except TimeoutException:
                        continue

                self.logger.error("No role center links found - authentication failed")
                return False

            except Exception as e:
                self.logger.error(f"Dashboard check error: {e}")
                return False

        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False

    async def _get_credentials(self) -> dict[str, str]:
        """Get credentials from environment."""
        return {
            "username": os.environ.get(f"{self.config.journal_id}_EMAIL", ""),
            "password": os.environ.get(f"{self.config.journal_id}_PASSWORD", ""),
        }

    async def navigate_to_ae_center(self) -> bool:
        """Navigate to Associate Editor Center."""
        try:
            self.logger.info("Navigating to Associate Editor Center...")

            # Wait for page to stabilize
            await asyncio.sleep(2)

            # Check if we're already at AE Center
            current_url = self.driver.current_url
            if "ASSOCIATE_EDITOR" in current_url or "AE_HOME" in current_url:
                self.logger.info("Already at AE Center")
                return True

            # Try to find AE Center link
            try:
                wait = WebDriverWait(self.driver, 10)
                ae_link = wait.until(
                    EC.presence_of_element_located((By.LINK_TEXT, "Associate Editor Center"))
                )
                ae_link.click()
                await asyncio.sleep(3)
                self.logger.info("Successfully clicked AE Center link")
                return True
            except:
                # Link not found - might already be there or different page structure
                self.logger.warning("AE Center link not found, checking current page...")

                # Check if we can find category links (which means we're at the right place)
                try:
                    self.driver.find_element(By.XPATH, "//a[contains(text(), 'Awaiting')]")
                    self.logger.info("Found category links - assuming we're at AE Center")
                    return True
                except:
                    self.logger.error("Not at AE Center and can't navigate there")
                    return False

        except Exception as e:
            self.logger.error(f"Failed to navigate to AE Center: {e}")
            return False

    async def get_manuscript_categories(self) -> list[dict]:
        """Get all manuscript categories from AE Center."""
        try:
            self.logger.info("Finding manuscript categories...")

            categories = []

            # Common category names for ScholarOne journals
            category_names = [
                "Awaiting AE Recommendation",
                "Awaiting Reviewer Reports",
                "Under Review",
                "Awaiting AE Assignment",
                "Awaiting Final Decision",
                "Awaiting Reviewer Selection",
                "With Editor",
            ]

            # Find category links on page
            for category_name in category_names:
                try:
                    # Try to find the category link
                    category_link = self.driver.find_element(
                        By.XPATH, f"//a[contains(text(), '{category_name}')]"
                    )

                    # Try to get manuscript count from same row
                    count = 0
                    try:
                        row = category_link.find_element(By.XPATH, "./ancestor::tr[1]")
                        # Look for <b> tag with number
                        count_elem = row.find_element(By.TAG_NAME, "b")
                        count_text = count_elem.text.strip()
                        if count_text.isdigit():
                            count = int(count_text)
                    except:
                        pass  # Count not found, use 0

                    categories.append(
                        {
                            "name": category_name,
                            "count": count,
                            "element": category_link,
                        }
                    )

                    self.logger.info(f"Found category: {category_name} ({count} manuscripts)")

                except Exception:
                    # Category not found, skip
                    continue

            self.logger.info(f"Found {len(categories)} categories total")
            return categories

        except Exception as e:
            self.logger.error(f"Error getting categories: {e}")
            return []

    async def fetch_manuscripts(self, categories: list[str]) -> list[Manuscript]:
        """Fetch manuscripts from specified categories."""
        try:
            self.logger.info(f"Fetching manuscripts from {len(categories)} categories")

            manuscripts = []

            # Navigate to AE Center first
            if not await self.navigate_to_ae_center():
                return []

            # Get available categories
            available_categories = await self.get_manuscript_categories()

            # Filter to requested categories
            categories_to_process = [
                cat for cat in available_categories if cat["name"] in categories
            ]

            self.logger.info(f"Processing {len(categories_to_process)} categories")

            for category in categories_to_process:
                self.logger.info(f"Processing category: {category['name']}")

                # Click category link
                try:
                    category["element"].click()
                    await asyncio.sleep(3)
                except Exception as e:
                    self.logger.error(f"Failed to click category: {e}")
                    continue

                # Find "Take Action" links (check_off.gif icons)
                take_action_links = self.driver.find_elements(
                    By.XPATH, "//a[.//img[contains(@src, 'check_off.gif')]]"
                )

                if not take_action_links:
                    self.logger.info(f"No manuscripts in {category['name']}")
                    # Navigate back to AE Center for next category
                    await self.navigate_to_ae_center()
                    continue

                self.logger.info(f"Found {len(take_action_links)} manuscripts")

                # Extract manuscript IDs from table before clicking
                manuscript_ids = []
                for link in take_action_links:
                    try:
                        # Get the row containing this link
                        row = link.find_element(By.XPATH, "./ancestor::tr[1]")
                        # Get first cell (manuscript ID)
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if cells:
                            manuscript_id = cells[0].text.strip()
                            # Validate ID format (e.g., MAFI-2024-0123)
                            if re.match(self.manuscript_pattern, manuscript_id):
                                manuscript_ids.append(manuscript_id)
                                self.logger.info(f"Found manuscript: {manuscript_id}")
                    except:
                        continue

                # Now extract details for each manuscript
                for manuscript_id in manuscript_ids:
                    try:
                        manuscript = await self.extract_manuscript_details(manuscript_id)
                        manuscripts.append(manuscript)
                    except Exception as e:
                        self.logger.error(f"Error extracting {manuscript_id}: {e}")
                        continue

                # Navigate back to AE Center for next category
                await self.navigate_to_ae_center()

            self.logger.info(f"Successfully fetched {len(manuscripts)} manuscripts")
            return manuscripts

        except Exception as e:
            self.logger.error(f"Error fetching manuscripts: {e}")
            return []

    async def extract_manuscript_details(self, manuscript_id: str) -> Manuscript:
        """Extract manuscript details for a specific ID."""
        try:
            self.logger.info(f"Extracting details for {manuscript_id}")

            # For now, return basic manuscript object
            # TODO: Click into manuscript and extract full details
            manuscript = Manuscript(
                journal_id=self.config.journal_id,
                external_id=manuscript_id,
                title=f"Manuscript {manuscript_id}",  # Placeholder
                status=ManuscriptStatus.UNDER_REVIEW,
            )

            return manuscript

        except Exception as e:
            self.logger.error(f"Error extracting details for {manuscript_id}: {e}")
            return Manuscript(journal_id=self.config.journal_id, external_id=manuscript_id)
