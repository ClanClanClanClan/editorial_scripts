"""Mathematics and Financial Economics (MAFE) journal extractor."""

from typing import List, Dict, Any
import logging
import time
import re
from bs4 import BeautifulSoup

from editorial_assistant.core.data_models import JournalConfig
from editorial_assistant.extractors.base_platform_extractors import EditorialManagerExtractor


class MAFEExtractor(EditorialManagerExtractor):
    """MAFE extractor using Editorial Manager Cloud platform."""
    
    def __init__(self, journal: JournalConfig):
        super().__init__(journal)
        self.is_playwright = self._detect_playwright_driver()
        
    def _detect_playwright_driver(self) -> bool:
        """Detect if the driver is a Playwright page object."""
        try:
            return hasattr(self.driver, 'goto') and hasattr(self.driver, 'locator')
        except Exception:
            return False
    
    def _login(self) -> None:
        """Login to MAFE using Editorial Manager Cloud."""
        try:
            # Navigate to MAFE login page
            if self.is_playwright:
                self.driver.goto(self.journal.url)
            else:
                self.driver.get(self.journal.url)
            
            time.sleep(3)
            
            if not self.is_playwright:
                self._dismiss_cookie_banner()
            
            # Check if already logged in
            if self._is_logged_in():
                logging.info(f"[{self.journal.code}] Already logged in")
                return
            
            # MAFE login is typically in an iframe
            if self._login_in_iframe():
                return
            
            # Try main frame login as fallback
            self._try_main_frame_login()
            
            logging.info(f"[{self.journal.code}] Successfully logged in")
            
        except Exception as e:
            logging.error(f"[{self.journal.code}] Login failed: {e}")
            raise
    
    def _login_in_iframe(self) -> bool:
        """Try to login within iframe (MAFE-specific implementation)."""
        try:
            if self.is_playwright:
                return self._playwright_login_in_iframe()
            else:
                return self._selenium_login_in_iframe()
                
        except Exception as e:
            logging.warning(f"[{self.journal.code}] Iframe login failed: {e}")
            return False
    
    def _selenium_login_in_iframe(self) -> bool:
        """Selenium-specific iframe login."""
        # Wait for page to load
        time.sleep(8)
        
        # First check main frame for login fields
        main_username = self.driver.find_elements("id", "username")
        main_password = self.driver.find_elements("id", "passwordTextbox")
        
        if main_username and main_password:
            return self._perform_login(main_username[0], main_password[0])
        
        # Look for login iframe
        iframes = self.driver.find_elements("tag name", "iframe")
        
        for i, iframe in enumerate(iframes):
            try:
                iframe_src = iframe.get_attribute("src")
                logging.debug(f"[{self.journal.code}] Checking iframe {i+1}: {iframe_src}")
                
                # Switch to iframe
                self.driver.switch_to.frame(iframe)
                time.sleep(2)
                
                # Look for login fields
                username_field = self.driver.find_elements("id", "username")
                password_field = self.driver.find_elements("id", "passwordTextbox")
                
                if username_field and password_field:
                    logging.info(f"[{self.journal.code}] Found login fields in iframe {i+1}")
                    
                    success = self._perform_login(username_field[0], password_field[0])
                    
                    # Switch back to main frame
                    self.driver.switch_to.default_content()
                    
                    if success:
                        return True
                
                # Switch back to main frame for next iteration
                self.driver.switch_to.default_content()
                
            except Exception as e:
                logging.debug(f"[{self.journal.code}] Error with iframe {i+1}: {e}")
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass
                continue
        
        return False
    
    def _playwright_login_in_iframe(self) -> bool:
        """Playwright-specific iframe login."""
        try:
            # Wait for page to load
            time.sleep(5)
            
            # Find iframes
            iframes = self.driver.query_selector_all('iframe')
            logging.debug(f"[{self.journal.code}] Found {len(iframes)} iframes with Playwright")
            
            for i, iframe in enumerate(iframes):
                try:
                    # Get the frame
                    frame = iframe.content_frame()
                    if not frame:
                        continue
                    
                    # Check if this frame has login fields
                    username_field = frame.query_selector('#username')
                    password_field = frame.query_selector('#passwordTextbox')
                    
                    if username_field and password_field:
                        logging.info(f"[{self.journal.code}] Found login fields in iframe {i} with Playwright")
                        
                        # Get credentials
                        username = self.journal.credentials.get('username_env')
                        password = self.journal.credentials.get('password_env')
                        
                        if not username or not password:
                            raise Exception("Credentials not found")
                        
                        # Fill in credentials
                        username_field.fill(username)
                        password_field.fill(password)
                        
                        # Find and click login button
                        login_button = frame.query_selector('input[name="editorLogin"]')
                        if not login_button:
                            login_button = frame.query_selector('input[value="Editor Login"]')
                        
                        if login_button:
                            login_button.click()
                            logging.info(f"[{self.journal.code}] Clicked Editor Login with Playwright")
                            
                            # Wait for dashboard
                            time.sleep(5)
                            self.driver.wait_for_selector('text=Associate Editor', timeout=25000)
                            return True
                
                except Exception as e:
                    logging.debug(f"[{self.journal.code}] Error with iframe {i}: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logging.error(f"[{self.journal.code}] Playwright iframe login failed: {e}")
            return False
    
    def _try_main_frame_login(self) -> None:
        """Try login in main frame as fallback."""
        try:
            # Look for login fields in main frame
            if self.is_playwright:
                username_field = self.driver.query_selector('#username')
                password_field = self.driver.query_selector('#passwordTextbox')
            else:
                username_elements = self.driver.find_elements("id", "username")
                password_elements = self.driver.find_elements("id", "passwordTextbox")
                username_field = username_elements[0] if username_elements else None
                password_field = password_elements[0] if password_elements else None
            
            if username_field and password_field:
                logging.info(f"[{self.journal.code}] Found login fields in main frame")
                self._perform_login(username_field, password_field)
            else:
                raise Exception("Login fields not found in main frame or iframes")
                
        except Exception as e:
            logging.error(f"[{self.journal.code}] Main frame login failed: {e}")
            raise
    
    def _perform_login(self, username_field, password_field) -> bool:
        """Perform the actual login with given fields."""
        try:
            # Get credentials
            username = self.journal.credentials.get('username_env')
            password = self.journal.credentials.get('password_env')
            
            if not username or not password:
                raise Exception("Credentials not found in environment variables")
            
            # Fill credentials
            if self.is_playwright:
                username_field.fill(username)
                password_field.fill(password)
            else:
                username_field.clear()
                username_field.send_keys(username)
                password_field.clear()
                password_field.send_keys(password)
            
            # Find and click login button
            if self.is_playwright:
                login_button = self.driver.query_selector('input[name="editorLogin"]')
                if not login_button:
                    login_button = self.driver.query_selector('input[value="Editor Login"]')
            else:
                login_button = self._wait_for_element_by_name("editorLogin", timeout=10)
                if not login_button:
                    login_button = self._wait_for_element_by_xpath("//input[@value='Editor Login']", timeout=5)
            
            if not login_button:
                raise Exception("Login button not found")
            
            if self.is_playwright:
                login_button.click()
            else:
                login_button.click()
            
            logging.info(f"[{self.journal.code}] Login credentials submitted")
            
            # Wait for dashboard
            if self.is_playwright:
                time.sleep(5)
                self.driver.wait_for_selector('text=Associate Editor', timeout=25000)
            else:
                time.sleep(2)
                self._wait_for_dashboard()
            
            return True
            
        except Exception as e:
            logging.error(f"[{self.journal.code}] Login performance failed: {e}")
            return False
    
    def _wait_for_dashboard(self) -> None:
        """Wait for dashboard to load after login."""
        from selenium.webdriver.support.ui import WebDriverWait
        
        WebDriverWait(self.driver, 25).until(
            lambda d: "Associate Editor" in d.page_source or "aries-accordion-item" in d.page_source
        )
        
        if not self.is_playwright:
            self._dismiss_cookie_banner()
    
    def extract_manuscripts(self) -> List[Dict[str, Any]]:
        """Extract manuscripts from MAFE dashboard."""
        try:
            # Login to MAFE
            self._login()
            
            # Collect folder links from dashboard
            folder_links = self._collect_folder_links()
            
            if not folder_links:
                logging.warning(f"[{self.journal.code}] No folders found with manuscripts")
                return []
            
            # Extract manuscripts from each folder
            all_manuscripts = {}
            
            for folder_text, nvgurl in folder_links:
                try:
                    if self._click_folder(nvgurl):
                        manuscripts = self._extract_manuscripts_from_table()
                        
                        for manuscript in manuscripts:
                            manuscript_id = manuscript["Manuscript #"]
                            if manuscript_id and manuscript_id not in all_manuscripts:
                                all_manuscripts[manuscript_id] = manuscript
                                
                except Exception as e:
                    logging.error(f"[{self.journal.code}] Error processing folder {folder_text}: {e}")
                    continue
            
            result = list(all_manuscripts.values())
            logging.info(f"[{self.journal.code}] Extracted {len(result)} manuscripts")
            return result
            
        except Exception as e:
            logging.error(f"[{self.journal.code}] Manuscript extraction failed: {e}")
            return []
    
    def _collect_folder_links(self) -> List[tuple]:
        """Collect folder links from MAFE dashboard."""
        try:
            if not self.is_playwright:
                self._dismiss_cookie_banner()
            
            page_source = self.driver.content() if self.is_playwright else self.driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")
            
            folder_links = []
            
            for folder in soup.find_all("aries-folder-item"):
                text = folder.get_text(strip=True)
                
                # Check if folder has manuscripts (count > 0)
                match = re.search(r"\((\d+)\)", text)
                if not match or int(match.group(1)) == 0:
                    continue
                
                nvgurl = folder.get("nvgurl")
                if not nvgurl or "void(0);" in (folder.get("folder-url") or ""):
                    continue
                
                folder_links.append((text, nvgurl))
            
            logging.info(f"[{self.journal.code}] Found {len(folder_links)} folders with manuscripts")
            return folder_links
            
        except Exception as e:
            logging.error(f"[{self.journal.code}] Failed to collect folder links: {e}")
            return []
    
    def _click_folder(self, nvgurl: str) -> bool:
        """Navigate to folder containing manuscripts."""
        try:
            if not nvgurl.endswith(".aspx"):
                return False
            
            # Construct full URL
            base_url = self.journal.url.rsplit("/", 1)[0]
            url = f"{base_url}/{nvgurl}"
            
            # Navigate to folder
            if self.is_playwright:
                self.driver.goto(url)
            else:
                self.driver.get(url)
            
            time.sleep(2.0)
            
            if not self.is_playwright:
                self._dismiss_cookie_banner()
            
            return True
            
        except Exception as e:
            logging.error(f"[{self.journal.code}] Could not navigate to folder {nvgurl}: {e}")
            return False
    
    def _extract_manuscripts_from_table(self) -> List[Dict[str, Any]]:
        """Extract manuscripts from table in current folder."""
        try:
            page_source = self.driver.content() if self.is_playwright else self.driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")
            
            table = soup.find("table")
            if not table:
                return []
            
            manuscripts = []
            seen_ids = set()
            
            for row in table.find_all("tr"):
                tds = row.find_all("td")
                if len(tds) < 10:
                    continue
                
                try:
                    # Extract manuscript data (MAFE table structure)
                    manuscript_id = tds[1].get_text(strip=True)
                    
                    if not manuscript_id or manuscript_id in seen_ids:
                        continue
                    
                    seen_ids.add(manuscript_id)
                    
                    title = tds[3].get_text(strip=True)
                    author = self._clean_author_name(tds[4].get_text(strip=True))
                    status = tds[7].get_text(strip=True)
                    
                    # Extract referee information from column 8
                    referees = self._extract_referees_from_column(tds[8])
                    
                    manuscripts.append({
                        "Manuscript #": manuscript_id,
                        "Title": title,
                        "Contact Author": author,
                        "Current Stage": self._normalize_status(status),
                        "Referees": referees
                    })
                    
                except Exception as e:
                    logging.warning(f"[{self.journal.code}] Failed to parse table row: {e}")
                    continue
            
            return manuscripts
            
        except Exception as e:
            logging.error(f"[{self.journal.code}] Table extraction failed: {e}")
            return []
    
    def _extract_referees_from_column(self, reviewers_col) -> List[Dict[str, Any]]:
        """Extract referee information from reviewers column."""
        referees = []
        
        try:
            # Look for reviewer detail divs
            reviewer_details_divs = reviewers_col.find_all("div", class_="reviewerHoverDetails")
            
            for detail_div in reviewer_details_divs:
                try:
                    # Find the associated reviewer link
                    prev_link = detail_div.find_previous("a", class_="linkWithFlags")
                    if not prev_link:
                        continue
                    
                    referee_name = prev_link.get_text(strip=True)
                    
                    # Extract status from detail div
                    status_text = ""
                    for header_row in detail_div.find_all("div", class_="rs-headerRow"):
                        cells = header_row.find_all("span", class_="rs-overlay-cell")
                        if len(cells) >= 2:
                            status_text = cells[1].get_text(strip=True)
                        elif len(cells) == 1:
                            status_text = cells[0].get_text(strip=True)
                        
                        if status_text:
                            break
                    
                    status_text = status_text.lower() if status_text else ""
                    
                    # Skip declined or completed referees
                    if "declined" in status_text or "complete" in status_text:
                        continue
                    
                    # Include active referees
                    if any(keyword in status_text for keyword in ["agreed", "pending", "invited"]):
                        # Get referee email
                        referee_email = self._get_referee_email(prev_link, referee_name)
                        
                        referees.append({
                            "Referee Name": referee_name,
                            "Referee Email": referee_email,
                            "Status": status_text.capitalize() if status_text else "Unknown"
                        })
                
                except Exception as e:
                    logging.warning(f"[{self.journal.code}] Failed to extract referee details: {e}")
                    continue
        
        except Exception as e:
            logging.warning(f"[{self.journal.code}] Failed to extract referees from column: {e}")
        
        return referees
    
    def _get_referee_email(self, link_element, referee_name: str) -> str:
        """Get referee email by clicking profile link in new window."""
        if self.is_playwright:
            return self._get_referee_email_playwright(referee_name)
        else:
            return self._get_referee_email_selenium(link_element, referee_name)
    
    def _get_referee_email_selenium(self, link_element, referee_name: str) -> str:
        """Get referee email using Selenium."""
        try:
            # Find clickable element in current page
            clickable_elements = self.driver.find_elements("css selector", "a.linkWithFlags")
            
            target_element = None
            for element in clickable_elements:
                if element.text.strip() == referee_name:
                    target_element = element
                    break
            
            if not target_element:
                return ""
            
            # Store current window
            original_window = self.driver.current_window_handle
            
            try:
                # Click link (opens new window)
                target_element.click()
                
                # Wait for new window
                self._wait_for_new_window(original_window)
                
                if len(self.driver.window_handles) > 1:
                    new_window = [h for h in self.driver.window_handles if h != original_window][0]
                    self.driver.switch_to.window(new_window)
                    
                    time.sleep(1)
                    self._dismiss_cookie_banner()
                    
                    # Extract email
                    soup = BeautifulSoup(self.driver.page_source, "html.parser")
                    email_link = soup.find("a", href=re.compile(r"mailto:"))
                    
                    email = email_link.get_text(strip=True) if email_link else ""
                    
                    # Close new window
                    self.driver.close()
                    self.driver.switch_to.window(original_window)
                    
                    return email
                
            except Exception as e:
                # Ensure we return to original window
                try:
                    if self.driver.current_window_handle != original_window:
                        self.driver.close()
                        self.driver.switch_to.window(original_window)
                except:
                    pass
                
                logging.warning(f"[{self.journal.code}] Failed to get email for {referee_name}: {e}")
            
            return ""
            
        except Exception as e:
            logging.warning(f"[{self.journal.code}] Email extraction failed for {referee_name}: {e}")
            return ""
    
    def _get_referee_email_playwright(self, referee_name: str) -> str:
        """Get referee email using Playwright (simplified - may need popup handling)."""
        # Playwright implementation would be more complex with popup handling
        # For now, return empty string
        return ""
    
    def _clean_author_name(self, raw_name: str) -> str:
        """Clean author name by removing titles and extra text."""
        if not raw_name:
            return ""
        
        name = re.sub(r"(Pr\.|Prof\.|Dr\.|Ph\.?D\.?|Professor|,.*)", "", raw_name, flags=re.IGNORECASE)
        name = re.sub(r"\s+", " ", name)
        
        return name.strip()
    
    def _normalize_status(self, status: str) -> str:
        """Normalize manuscript status."""
        if "Requiring Additional Reviewer" in status:
            return "Pending Referee Assignments"
        else:
            return "All Referees Assigned"
    
    def _wait_for_new_window(self, original_window: str, timeout: int = 5) -> None:
        """Wait for new window to open."""
        for _ in range(timeout):
            if len(self.driver.window_handles) > 1:
                return
            time.sleep(1)
