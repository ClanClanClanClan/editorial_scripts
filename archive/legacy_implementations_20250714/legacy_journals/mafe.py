import os
import time
import logging
import re
from typing import List, Dict, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from core.base import JournalBase
from core.credential_manager import get_credential_manager
from core.paper_downloader import get_paper_downloader

MAFE_URL = "https://www2.cloud.editorialmanager.com/mafe/default2.aspx"

# Get credentials from credential manager
cred_manager = get_credential_manager()
mafe_creds = cred_manager.get_journal_credentials("MAFE")
USERNAME = mafe_creds.get('username')
PASSWORD = mafe_creds.get('password')

def take_screenshot(driver, suffix):
    fname = f"mafe_debug_{suffix}_{int(time.time())}.png"
    try:
        driver.save_screenshot(fname)
        print(f"[MAFE] Screenshot saved: {fname}")
    except Exception:
        pass

def clean_author_name(raw):
    if not raw: return ""
    name = re.sub(r"(Pr\.|Prof\.|Dr\.|Ph\.?D\.?|Professor|,.*)", "", raw, flags=re.IGNORECASE)
    name = re.sub(r"\s+", " ", name)
    return name.strip()

def dismiss_cookies(driver, debug=True):
    """
    Dismisses cookie banners (accept all, cookie settings, etc.).
    Run this before interacting with the login form and after navigation.
    """
    keywords = [
        "Accept all cookies",
        "Accept cookies",
        "Accept",
        "Got it",
        "Agree",
    ]
    try:
        # Try by button text
        buttons = driver.find_elements(By.TAG_NAME, "button") + driver.find_elements(By.TAG_NAME, "input")
        for btn in buttons:
            try:
                text = (btn.text or btn.get_attribute("value") or "").strip()
                if not btn.is_displayed() or not btn.is_enabled():
                    continue
                if any(k.lower() in text.lower() for k in keywords):
                    btn.click()
                    if debug:
                        print("[MAFE] Cookie consent accepted via button:", text)
                    time.sleep(1)
                    return
            except Exception:
                continue
        # Try by XPath as fallback
        try:
            for keyword in keywords:
                xpath = f"//*[contains(text(), '{keyword}')]"
                btns = driver.find_elements(By.XPATH, xpath)
                for b in btns:
                    if b.is_displayed() and b.is_enabled():
                        b.click()
                        if debug:
                            print("[MAFE] Cookie consent accepted via xpath:", keyword)
                        time.sleep(1)
                        return
        except Exception:
            pass
        # Try by class
        classes = ["cc-btn", "cookie-accept", "accept-cookies"]
        for cls in classes:
            elems = driver.find_elements(By.CLASS_NAME, cls)
            for e in elems:
                if e.is_displayed() and e.is_enabled():
                    e.click()
                    if debug:
                        print("[MAFE] Cookie consent accepted via class:", cls)
                    time.sleep(1)
                    return
    except Exception:
        pass
    if debug:
        print("[MAFE] Cookie banner not found or already accepted.")

class MAFEJournal(JournalBase):
    def __init__(self, driver, debug=True):
        super().__init__(driver)
        self.debug = debug
        
        # Detect if we're using Playwright or Selenium
        self.is_playwright = self._is_playwright_driver(driver)
        
        self.paper_downloader = get_paper_downloader()
    
    def get_url(self):
        return MAFE_URL
    
    def _is_playwright_driver(self, driver):
        """Detect if the driver is a Playwright page object"""
        try:
            # Check for Playwright page methods
            return hasattr(driver, 'goto') and hasattr(driver, 'locator')
        except Exception:
            return False
    def wait_for_elem(self, by, sel, timeout=15):
        if self.is_playwright:
            return self._playwright_wait_for_elem(sel, timeout)
        else:
            try:
                return WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((by, sel))
                )
            except TimeoutException:
                return None

    def wait_for_clickable(self, by, sel, timeout=10):
        if self.is_playwright:
            return self._playwright_wait_for_clickable(sel, timeout)
        else:
            try:
                return WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((by, sel))
                )
            except TimeoutException:
                return None

    def _playwright_wait_for_elem(self, selector, timeout=15):
        """Wait for element with Playwright"""
        try:
            # Convert Selenium selector to Playwright selector
            playwright_selector = self._convert_to_playwright_selector(selector)
            return self.driver.wait_for_selector(playwright_selector, timeout=timeout * 1000)
        except Exception:
            return None

    def _playwright_wait_for_clickable(self, selector, timeout=10):
        """Wait for clickable element with Playwright"""
        try:
            playwright_selector = self._convert_to_playwright_selector(selector)
            element = self.driver.wait_for_selector(playwright_selector, timeout=timeout * 1000)
            if element:
                return element
        except Exception:
            return None

    def _convert_to_playwright_selector(self, selector):
        """Convert Selenium selector to Playwright selector"""
        if selector.startswith('#'):
            return selector  # ID selector
        elif selector.startswith('.'):
            return selector  # Class selector  
        elif selector.startswith('['):
            return selector  # Attribute selector
        else:
            return selector  # Assume it's already a valid CSS selector

    def _get_page_source(self):
        """Get page source for both Selenium and Playwright"""
        if self.is_playwright:
            return self.driver.content()
        else:
            return self.driver.page_source

    def _navigate_to_url(self, url):
        """Navigate to URL for both Selenium and Playwright"""
        if self.is_playwright:
            self.driver.goto(url)
        else:
            self.driver.get(url)

    def _find_elements(self, by, selector):
        """Find elements for both Selenium and Playwright"""
        if self.is_playwright:
            playwright_selector = self._convert_to_playwright_selector(selector)
            return self.driver.query_selector_all(playwright_selector)
        else:
            return self.driver.find_elements(by, selector)

    def _find_element(self, by, selector):
        """Find single element for both Selenium and Playwright"""
        if self.is_playwright:
            playwright_selector = self._convert_to_playwright_selector(selector)
            return self.driver.query_selector(playwright_selector)
        else:
            elements = self.driver.find_elements(by, selector)
            return elements[0] if elements else None

    def _playwright_login(self):
        """Playwright-specific login implementation"""
        try:
            # Wait for page to load
            time.sleep(5)
            
            # Try to find login fields in iframes with Playwright
            iframes = self.driver.query_selector_all('iframe')
            
            if self.debug:
                print(f"[MAFE] Found {len(iframes)} iframes with Playwright")
            
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
                        if self.debug:
                            print(f"[MAFE] Found login fields in iframe {i} with Playwright")
                        
                        # Fill in credentials
                        username_field.fill(USERNAME)
                        password_field.fill(PASSWORD)
                        
                        # Find and click login button
                        login_button = frame.query_selector('input[name="editorLogin"]')
                        if not login_button:
                            login_button = frame.query_selector('input[value="Editor Login"]')
                        
                        if login_button:
                            login_button.click()
                            if self.debug:
                                print("[MAFE] Clicked Editor Login with Playwright")
                            
                            # Wait for navigation
                            time.sleep(5)
                            
                            # Wait for dashboard
                            self.driver.wait_for_selector('text=Associate Editor', timeout=25000)
                            return
                        else:
                            if self.debug:
                                print("[MAFE] Login button not found in iframe")
                    
                except Exception as e:
                    if self.debug:
                        print(f"[MAFE] Error with iframe {i}: {e}")
                    continue
            
            raise Exception("Login fields not found in any iframe")
            
        except Exception as e:
            if self.debug:
                print(f"[MAFE] Playwright login failed: {e}")
            raise

    def login(self):
        driver = self.driver
        try:
            self._navigate_to_url(MAFE_URL)
            time.sleep(3)
            if not self.is_playwright:
                dismiss_cookies(driver, debug=self.debug)
            
            # MAFE login form is in an iframe - need to switch to it
            if self.debug: print("[MAFE] Looking for login iframe...")
            
            # Wait for page to load completely and check for login fields in main frame first
            time.sleep(8)
            
            # First, try to find login fields in the main frame (maybe the page structure changed)
            if self.debug: print("[MAFE] Checking main frame for login fields...")
            main_u = self._find_elements(By.ID, "username")
            main_p = self._find_elements(By.ID, "passwordTextbox")
            
            if main_u and main_p:
                if self.debug: print("[MAFE] Found login fields in main frame!")
                u = main_u[0]
                p = main_p[0]
                
                u.clear()
                u.send_keys(USERNAME)
                p.clear()
                p.send_keys(PASSWORD)
                
                # Look for Editor Login button
                btn = self.wait_for_elem(By.NAME, "editorLogin", 10)
                if not btn:
                    btn = self.wait_for_elem(By.XPATH, "//input[@value='Editor Login']", 5)
                
                if btn:
                    btn.click()
                    if self.debug: print("[MAFE] Clicked Editor Login in main frame")
                    
                    # Wait for dashboard
                    WebDriverWait(driver, 25).until(
                        lambda d: "Associate Editor" in d.page_source or "aries-accordion-item" in d.page_source
                    )
                    dismiss_cookies(driver, debug=self.debug)
                    return
                else:
                    if self.debug: print("[MAFE] Login fields found in main frame but no login button")
            
            if self.debug: print("[MAFE] No login fields in main frame, checking iframes...")
            
            # For Playwright, we need to use a different approach
            if self.is_playwright:
                return self._playwright_login()
            
            # Find all iframes (Selenium only)
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if self.debug: print(f"[MAFE] Found {len(iframes)} iframes")
            
            login_iframe = None
            
            for i, iframe in enumerate(iframes):
                try:
                    iframe_src = iframe.get_attribute("src")
                    if self.debug: print(f"[MAFE] Iframe {i+1}: {iframe_src}")
                    
                    # Check for login.asp or any iframe that might contain login
                    if iframe_src and ("login.asp" in iframe_src or "login" in iframe_src):
                        login_iframe = iframe
                        if self.debug: print(f"[MAFE] Found login iframe: {iframe_src}")
                        break
                except Exception as e:
                    if self.debug: print(f"[MAFE] Error checking iframe {i+1}: {e}")
                    continue
            
            # If we didn't find login.asp specifically, try each iframe until we find login fields
            if not login_iframe:
                if self.debug: print("[MAFE] Trying each iframe to find login fields")
                
                for i, iframe in enumerate(iframes):
                    try:
                        if self.debug: print(f"[MAFE] Trying iframe {i+1}")
                        driver.switch_to.frame(iframe)
                        time.sleep(1)
                        
                        # Check if this iframe has login fields
                        u = driver.find_elements(By.ID, "username")
                        p = driver.find_elements(By.ID, "passwordTextbox")
                        
                        if u and p:
                            if self.debug: print(f"[MAFE] Found login fields in iframe {i+1}")
                            login_iframe = iframe
                            break
                        else:
                            # Try alternative field names
                            u = driver.find_elements(By.NAME, "username")
                            p = driver.find_elements(By.NAME, "password")
                            
                            if u and p:
                                if self.debug: print(f"[MAFE] Found alternative login fields in iframe {i+1}")
                                login_iframe = iframe
                                break
                        
                        # Switch back to main frame to try next iframe
                        driver.switch_to.default_content()
                        
                    except Exception as e:
                        if self.debug: print(f"[MAFE] Error trying iframe {i+1}: {e}")
                        try:
                            driver.switch_to.default_content()
                        except:
                            pass
                        continue
            
            if not login_iframe:
                take_screenshot(driver, "no_login_iframe")
                raise Exception("MAFE: Login iframe not found")
            
            # If we haven't switched to the login iframe yet, do it now
            if login_iframe:
                try:
                    driver.switch_to.default_content()
                    driver.switch_to.frame(login_iframe)
                    time.sleep(2)
                except:
                    pass
            
            # Now find the login fields in the iframe
            u = self.wait_for_elem(By.ID, "username", 15)
            p = self.wait_for_elem(By.ID, "passwordTextbox", 10)
            
            # Try alternative field names if standard ones don't work
            if not u:
                u = self.wait_for_elem(By.NAME, "username", 5)
            if not p:
                p = self.wait_for_elem(By.NAME, "password", 5)
            
            if not (u and p):
                take_screenshot(driver, "no_login_fields_in_iframe")
                raise Exception("MAFE: Login fields not found in iframe")
            
            if self.debug: print(f"[MAFE] Found username and password fields in iframe")
            
            u.clear()
            u.send_keys(USERNAME)
            p.clear()
            p.send_keys(PASSWORD)
            
            # Look for Editor Login button
            btn = self.wait_for_elem(By.NAME, "editorLogin", 10)
            if not btn:
                # Try alternative selectors for Editor Login
                btn = self.wait_for_elem(By.XPATH, "//input[@value='Editor Login']", 5)
            
            if not btn:
                take_screenshot(driver, "no_login_btn_in_iframe")
                raise Exception("MAFE: Editor Login button not found in iframe")
            
            btn.click()
            if self.debug: print("[MAFE] Clicked Editor Login")
            
            # Switch back to main frame
            driver.switch_to.default_content()
            time.sleep(2)
            
            # Wait for dashboard/main page
            WebDriverWait(driver, 25).until(
                lambda d: "Associate Editor" in d.page_source or "aries-accordion-item" in d.page_source
            )
            dismiss_cookies(driver, debug=self.debug)
            
        except Exception as e:
            # Make sure we switch back to main frame
            try:
                driver.switch_to.default_content()
            except:
                pass
            take_screenshot(driver, "login_fail")
            logging.error(f"[MAFE] Login failed: {e}")
            raise

    def collect_folder_links(self):
        driver = self.driver
        if not self.is_playwright:
            dismiss_cookies(driver, debug=self.debug)
        folder_links = []
        soup = BeautifulSoup(self._get_page_source(), "html.parser")
        for folder in soup.find_all("aries-folder-item"):
            text = folder.get_text(strip=True)
            m = re.search(r"\((\d+)\)", text)
            if not m or int(m.group(1)) == 0:
                continue
            nvgurl = folder.get("nvgurl")
            if not nvgurl or "void(0);" in (folder.get("folder-url") or ""):
                continue
            folder_links.append((text, nvgurl))
        return folder_links

    def click_folder(self, nvgurl):
        driver = self.driver
        if not nvgurl.endswith(".aspx"):
            return False
        url = MAFE_URL.rsplit("/", 1)[0] + "/" + nvgurl
        try:
            self._navigate_to_url(url)
            time.sleep(2.0)
            if not self.is_playwright:
                dismiss_cookies(driver, debug=self.debug)
            return True
        except Exception as e:
            if not self.is_playwright:
                take_screenshot(driver, "folder_click")
            logging.error(f"[MAFE] Could not click folder {nvgurl}: {e}")
            return False

    def extract_reviewer_emails(self, reviewer_links):
        driver = self.driver
        reviewer_emails = {}
        orig_window = driver.current_window_handle

        for link_elem, name in reviewer_links:
            try:
                link_elem.click()
                WebDriverWait(driver, 5).until(
                    lambda d: len(d.window_handles) > 1
                )
                new_win = [h for h in driver.window_handles if h != orig_window][0]
                driver.switch_to.window(new_win)
                time.sleep(1)
                dismiss_cookies(driver, debug=self.debug)
                soup = BeautifulSoup(driver.page_source, "html.parser")
                a = soup.find("a", href=re.compile(r"mailto:"))
                email = ""
                if a:
                    email = a.get_text(strip=True)
                reviewer_emails[name.strip()] = email
                driver.close()
                driver.switch_to.window(orig_window)
            except Exception as e:
                try:
                    if driver.current_window_handle != orig_window:
                        driver.close()
                        driver.switch_to.window(orig_window)
                except Exception:
                    pass
                logging.warning(f"[MAFE] Could not get reviewer email for {name}: {e}")
        return reviewer_emails

    def extract_manuscripts_from_table(self):
        driver = self.driver
        ms_list = []
        soup = BeautifulSoup(self._get_page_source(), "html.parser")
        table = soup.find("table")
        if not table:
            take_screenshot(driver, "no_table")
            return []
        seen_ids = set()
        for row in table.find_all("tr"):
            tds = row.find_all("td")
            if len(tds) < 10: continue
            try:
                ms_num = tds[1].get_text(strip=True)
                if not ms_num or ms_num in seen_ids:
                    continue
                seen_ids.add(ms_num)
                title = tds[3].get_text(strip=True)
                author = clean_author_name(tds[4].get_text(strip=True))
                status = tds[7].get_text(strip=True)
                reviewers_col = tds[8]
                reviewer_links = []
                reviewers = []
                reviewer_details_divs = reviewers_col.find_all("div", class_="reviewerHoverDetails")
                for detail_div in reviewer_details_divs:
                    name = None
                    link_elem = None
                    prev_a = detail_div.find_previous("a", class_="linkWithFlags")
                    if prev_a:
                        name = prev_a.get_text(strip=True)
                        link_elem = None
                        for selem in driver.find_elements(By.CSS_SELECTOR, "a.linkWithFlags"):
                            if selem.text.strip() == name:
                                link_elem = selem
                                break
                    if not name or not link_elem:
                        continue
                    status_text = ""
                    for d2 in detail_div.find_all("div", class_="rs-headerRow"):
                        cells = d2.find_all("span", class_="rs-overlay-cell")
                        if len(cells) >= 2:
                            status_text = cells[1].get_text(strip=True)
                        elif len(cells) == 1:
                            status_text = cells[0].get_text(strip=True)
                        status_text = status_text or ""
                        status_text = status_text.lower()
                        if "declined" in status_text or "complete" in status_text:
                            continue
                        elif "agreed" in status_text or "pending" in status_text or "invited" in status_text:
                            reviewer_links.append((link_elem, name))
                            reviewers.append({
                                "Referee Name": name,
                                "Status": status_text.capitalize()
                            })
                emails = self.extract_reviewer_emails(reviewer_links) if reviewer_links else {}
                for ref in reviewers:
                    ref["Referee Email"] = emails.get(ref["Referee Name"], "")
                ms_list.append({
                    "Manuscript #": ms_num,
                    "Title": title,
                    "Contact Author": author,
                    "Current Stage": "All Referees Assigned" if "Requiring Additional Reviewer" not in status else "Pending Referee Assignments",
                    "Referees": reviewers
                })
            except Exception as e:
                logging.error(f"[MAFE] Row parse error: {e}")
                continue
        return ms_list

    def scrape_manuscripts_and_emails(self):
        driver = self.driver
        try:
            self.login()
            folders = self.collect_folder_links()
            if not folders:
                return []
            all_ms = {}
            for folder_text, nvgurl in folders:
                if not self.click_folder(nvgurl):
                    continue
                ms = self.extract_manuscripts_from_table()
                for m in ms:
                    mid = m["Manuscript #"]
                    if mid in all_ms: continue
                    all_ms[mid] = m
            
            # Download papers and reports with AI analysis
            enhanced_manuscripts = self.download_and_analyze_manuscripts(list(all_ms.values()))
            return enhanced_manuscripts
        except Exception as e:
            if not self.is_playwright:
                take_screenshot(driver, "fatal")
            logging.error(f"[MAFE] scrape_manuscripts_and_emails failed: {e}")
            return []

    def download_manuscripts(self, manuscripts: List[Dict]) -> List[Dict]:
        """Download papers and referee reports for manuscripts"""
        if not hasattr(self, 'paper_downloader'):
            self.paper_downloader = get_paper_downloader()
        
        enhanced_manuscripts = []
        
        for manuscript in manuscripts:
            enhanced_ms = manuscript.copy()
            enhanced_ms['downloads'] = {
                'paper': None,
                'reports': []
            }
            
            try:
                manuscript_id = manuscript.get('Manuscript #', manuscript.get('manuscript_id', ''))
                title = manuscript.get('Title', manuscript.get('title', ''))
                
                if manuscript_id and title:
                    # Try to find paper download links
                    paper_links = self.paper_downloader.find_paper_links(self.driver, "MAFE")
                    
                    for link in paper_links:
                        if link['type'] == 'href':
                            paper_path = self.paper_downloader.download_paper(
                                manuscript_id, title, link['url'], "MAFE", self.driver
                            )
                            if paper_path:
                                enhanced_ms['downloads']['paper'] = str(paper_path)
                                break
                    
                    # Try to find referee report links
                    report_links = self.paper_downloader.find_report_links(self.driver, "MAFE")
                    
                    for link in report_links:
                        if link['type'] == 'href':
                            report_path = self.paper_downloader.download_referee_report(
                                manuscript_id, link['text'], link['url'], "MAFE", self.driver
                            )
                            if report_path:
                                enhanced_ms['downloads']['reports'].append(str(report_path))
                
            except Exception as e:
                print(f"Error downloading for manuscript {manuscript_id}: {e}")
            
            enhanced_manuscripts.append(enhanced_ms)
        
        return enhanced_manuscripts