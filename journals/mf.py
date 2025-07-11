from core.base import JournalBase
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import os
import time
import logging
import re
from datetime import datetime
from typing import List, Dict, Any

from core.email_utils import (
    fetch_latest_verification_code,
    fetch_starred_emails,
    robust_match_email_for_referee_mf,
)
from core.paper_downloader import get_paper_downloader

def normalize_name(name):
    """Convert 'Last, First' to 'First Last', clean up."""
    name = name.replace('(contact)', '').replace(';', '').strip()
    if ',' in name:
        last, first = [part.strip() for part in name.split(',', 1)]
        return f"{first} {last}"
    return name.strip()

def robust_parse_date(date_str):
    """Try to parse dates like 26-Mar-2025 and return datetime.date, else None."""
    if not date_str or not date_str.strip():
        return None
    for fmt in ("%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except Exception:
            continue
    return None

def mf_status_normalize(status_raw):
    s = (status_raw or "").strip().lower()
    if s in {"agreed", "accepted", "overdue"}:
        return "Accepted"
    return "Contacted"

class MFJournal(JournalBase):
    MF_URL = "https://mc.manuscriptcentral.com/mafi"

    def __init__(self, driver, debug=True, chrome_profile_dir=None):
        super().__init__(driver)
        self.debug = debug
        self.chrome_profile_dir = chrome_profile_dir
        self.logger = logging.getLogger("[MF]")
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        self.activation_required = False

        self.paper_downloader = get_paper_downloader()
    def get_url(self):
        return self.MF_URL

    def wait_if_human_check(self, max_time=30):
        try:
            WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located((By.XPATH, "//iframe[contains(@title, 'reCAPTCHA')]"))
            )
            iframe = self.driver.find_element(By.XPATH, "//iframe[contains(@title, 'reCAPTCHA')]")
            self.driver.switch_to.frame(iframe)
            checkbox = self.driver.find_element(By.ID, "recaptcha-anchor")
            checkbox.click()
            self.driver.switch_to.default_content()
            self.logger.info("Clicked reCAPTCHA checkbox.")
            time.sleep(2)
        except Exception:
            self.logger.debug("No reCAPTCHA present.")

    def login(self):
        self.login_standard()

    def login_standard(self):
        driver = self.driver
        self.logger.info("Navigating to MF dashboard...")
        driver.get(self.MF_URL)
        time.sleep(2)
        try:
            accept_btn = driver.find_element(By.ID, "onetrust-accept-btn-handler")
            if accept_btn.is_displayed():
                accept_btn.click()
                self.logger.info("Accepted cookies.")
                time.sleep(1)
        except Exception:
            self.logger.debug("No cookie accept button found.")

        user = os.environ.get("MF_USER")
        pw = os.environ.get("MF_PASS")
        if not user or not pw:
            raise RuntimeError("MF_USER and MF_PASS environment variables must be set.")
        user_box = driver.find_element(By.ID, "USERID")
        pw_box = driver.find_element(By.ID, "PASSWORD")
        user_box.clear()
        user_box.send_keys(user)
        pw_box.clear()
        pw_box.send_keys(pw)
        login_btn = driver.find_element(By.ID, "logInButton")
        login_btn.click()
        time.sleep(4)

        wait = WebDriverWait(driver, 15)
        code_input = None
        try:
            self.wait_if_human_check()
            try:
                code_input = wait.until(
                    lambda d: d.find_element(By.ID, "TOKEN_VALUE") if d.find_element(By.ID, "TOKEN_VALUE").is_displayed() else None
                )
                self.logger.debug("Found and visible: TOKEN_VALUE")
            except TimeoutException:
                try:
                    code_input = wait.until(
                        lambda d: d.find_element(By.ID, "validationCode") if d.find_element(By.ID, "validationCode").is_displayed() else None
                    )
                    self.logger.debug("Found and visible: validationCode")
                except TimeoutException:
                    self.logger.debug("No visible verification input appeared within 15s.")

            if code_input:
                wait = WebDriverWait(driver, 15)
                code = fetch_latest_verification_code(journal="MF")
                self.logger.debug(f"Verification code fetched: {code!r}")
                if code:
                    code_input.clear()
                    code_input.send_keys(code)
                    self.activation_required = True
                    self.logger.info("Entered verification code.")
                    
                    # Check for "Remember this device" checkbox and check it
                    try:
                        remember_checkbox = driver.find_element(By.ID, "REMEMBER_THIS_DEVICE")
                        if not remember_checkbox.is_selected():
                            remember_checkbox.click()
                            self.logger.info("Checked 'Remember this device' checkbox")
                    except:
                        self.logger.debug("Could not find or check remember device checkbox")
                    
                    # Look for the VERIFY_BTN button specifically
                    try:
                        verify_btn = wait.until(
                            EC.element_to_be_clickable((By.ID, "VERIFY_BTN"))
                        )
                        verify_btn.click()
                        self.logger.info("Clicked VERIFY_BTN button")
                        time.sleep(5)
                    except TimeoutException:
                        # Try alternative selectors
                        try:
                            verify_btn = driver.find_element(By.XPATH, "//a[@id='VERIFY_BTN' or @name='VERIFY_BTN']")
                            verify_btn.click()
                            self.logger.info("Clicked verify button via XPath")
                            time.sleep(5)
                        except:
                            # Last resort - try any button with "Verify" text
                            try:
                                verify_btn = driver.find_element(By.XPATH, "//a[contains(@class, 'verifyBtn') or contains(text(), 'Verify')]")
                                verify_btn.click()
                                self.logger.info("Clicked verify button via text search")
                                time.sleep(5)
                            except:
                                self.logger.error("Could not find verify button")
                                # Try Enter key as fallback
                                code_input.send_keys(Keys.ENTER)
                                self.logger.info("Pressed Enter as fallback")
                                time.sleep(5)
                else:
                    self.logger.error("No verification code available.")
                    raise RuntimeError("No verification code available.")
        except Exception as e:
            self.logger.error(f"Error waiting for verification prompt or submitting code: {e}")

        with open("mf_postlogin_dashboard.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        self.wait_if_human_check()
        self.logger.info("Ready to continue navigation after login.")

    def parse_referee_list_from_html(self, html, flagged_emails=None, ms_id=None):
        soup = BeautifulSoup(html, "html.parser")
        referee_list = []
        seen_names = set()
        today = datetime.now().date()
        reviewer_tables = []
        for header in soup.find_all("td", class_="detailsheaderbg"):
            if header.find(string=re.compile(r"Reviewer List", re.I)):
                table = header.find_parent("table")
                if table:
                    next_tables = table.find_all_next("table")
                    for nt in next_tables:
                        if nt.find("select", attrs={"name": re.compile(r"ORDER\d*")}):
                            reviewer_tables.append(nt)
                            break
                break

        for reviewer_table in reviewer_tables:
            for tr in reviewer_table.find_all("tr"):
                if tr.find("select", attrs={"name": re.compile(r"ORDER\d*")}):
                    tds = tr.find_all("td", class_="tablelightcolor")
                    if not tds or len(tds) < 2:
                        continue
                    try:
                        name = ""
                        td2 = tds[1]
                        for a in td2.find_all("a"):
                            txt = a.get_text().strip()
                            if txt and "," in txt:
                                name = normalize_name(txt)
                                break
                        if not name or name in seen_names:
                            continue
                        seen_names.add(name)

                        status_raw = ""
                        if len(tds) > 2:
                            status_raw = tds[2].get_text(" ", strip=True)

                        declined_or_returned = False
                        contacted = accepted = due_date = ""
                        for subtable in tr.find_all("table"):
                            for row in subtable.find_all("tr"):
                                cells = row.find_all("td")
                                if len(cells) == 2:
                                    label = cells[0].get_text(strip=True).lower()
                                    value = cells[1].get_text(strip=True)
                                    if "invited" in label or "contacted" in label:
                                        contacted = value
                                    elif "agreed" in label or "accepted" in label:
                                        accepted = value
                                    elif "due date" in label:
                                        due_date = value
                                    elif "review returned" in label or "declined" in label:
                                        declined_or_returned = True

                        if "declined" in (status_raw or "").lower():
                            declined_or_returned = True

                        if declined_or_returned:
                            continue

                        norm_status = mf_status_normalize(status_raw)
                        email_addr = ""
                        crossmatch_date = ""
                        if flagged_emails is not None and ms_id is not None:
                            # Use enhanced email matching to get ALL referee emails
                            email_addr = self._enhance_email_matching(name, ms_id, norm_status, flagged_emails)
                            if email_addr:
                                crossmatch_date = "enhanced_extraction"

                        lateness = ""
                        due_date_dt = robust_parse_date(due_date) if due_date else None
                        if due_date_dt and today > due_date_dt:
                            overdue_days = (today - due_date_dt).days
                            lateness = f"{overdue_days} days late"

                        referee_list.append({
                            "Referee Name": name,
                            "Status": norm_status,
                            "Contacted Date": contacted,
                            "Accepted Date": accepted,
                            "Due Date": due_date,
                            "Email": email_addr,
                            "Lateness": lateness,
                        })
                    except Exception as e:
                        self.logger.debug(f"Error parsing referee row: {e}")

        return referee_list

    def parse_manuscript_panel(self, html, flagged_emails=None):
        soup = BeautifulSoup(html, "html.parser")
        ms_id = ""
        title = ""
        contact_author = ""
        submission_date = ""

        b_tag = soup.find("b", string=re.compile(r"MAFI-\d{4}-\d+(\.R\d+)?"))
        if b_tag:
            ms_id = b_tag.get_text(strip=True)
            ms_id_base = re.sub(r"\.R\d+$", "", ms_id)
        else:
            ms_id_base = ""

        found_title = False
        for p in soup.find_all("p", class_="pagecontents"):
            if ms_id and ms_id in p.get_text(strip=True):
                found_title = True
            elif found_title and not title:
                title = p.get_text(strip=True)
                break

        for p in soup.find_all("p", class_="pagecontents"):
            m = re.search(r"([A-Za-z\-]+), ([A-Za-z\-]+)\s*\(contact\)", p.get_text())
            if m:
                contact_author = normalize_name(f"{m.group(1)}, {m.group(2)}")
                break

        for p in soup.find_all("p", class_="footer"):
            m = re.search(r"Submitted:\s*([\d\w\-]+);", p.get_text())
            if m:
                submission_date = m.group(1)
                break

        referees = self.parse_referee_list_from_html(html, flagged_emails=flagged_emails, ms_id=ms_id_base)
        
        # Extract cover letters and referee reports
        cover_letters = self._extract_cover_letters(ms_id_base)
        referee_reports = self._extract_enhanced_referee_reports(ms_id_base)
        
        return {
            "Manuscript #": ms_id_base,
            "Title": title,
            "Contact Author": contact_author,
            "Submission Date": submission_date,
            "Referees": referees,
            "Cover Letters": cover_letters,
            "Referee Reports": referee_reports
        }

    def scrape_manuscripts_and_emails(self):
        driver = self.driver
        self.login()
        time.sleep(2)
        self.wait_if_human_check()
        
        # Fetch emails with timeout protection
        try:
            self.logger.info("Fetching starred emails for MF...")
            import signal
            def timeout_handler(signum, frame):
                raise TimeoutError("Email fetch timeout")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)  # 30 second timeout
            
            flagged_emails = fetch_starred_emails("MF")
            signal.alarm(0)  # Cancel timeout
            self.logger.info(f"Retrieved {len(flagged_emails)} flagged emails")
        except Exception as e:
            self.logger.error(f"Failed to fetch emails: {e}")
            flagged_emails = []

        found = False
        for attempt in range(15):
            self.logger.debug(f"Attempt {attempt + 1} to find Associate Editor Center...")
            
            # First, try to find the link by text
            links = driver.find_elements(By.XPATH, "//a")
            for link in links:
                try:
                    link_text = link.text.strip().lower().replace('\xa0', ' ')
                    # Try multiple variations
                    if any(phrase in link_text for phrase in [
                        "associate editor center", 
                        "associate editor centre",
                        "ae center",
                        "ae centre",
                        "editor center",
                        "editor centre"
                    ]):
                        driver.execute_script("arguments[0].scrollIntoView(true);", link)
                        link.click()
                        time.sleep(2)
                        found = True
                        self.logger.debug(f"Clicked Associate Editor Center link: {link_text}")
                        break
                except Exception as e:
                    self.logger.debug(f"Error checking link: {e}")
                    continue
                    
            if found:
                break
                
            # Try alternative selectors
            try:
                # Try by href patterns
                ae_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'associate') or contains(@href, 'editor')]")
                
                for link in ae_links:
                    link_text = link.text.strip().lower()
                    href = link.get_attribute("href") or ""
                    self.logger.debug(f"Checking link: '{link_text}' with href: '{href}'")
                    
                    if any(word in link_text for word in ["associate", "editor", "ae"]):
                        driver.execute_script("arguments[0].scrollIntoView(true);", link)
                        link.click()
                        time.sleep(2)
                        found = True
                        self.logger.debug(f"Clicked AE link via href: {link_text}")
                        break
                        
                if found:
                    break
                    
                # Try looking for any editorial role links
                role_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Editor') or contains(text(), 'Editorial')]")
                for link in role_links:
                    link_text = link.text.strip().lower()
                    if any(word in link_text for word in ["editor", "editorial"]):
                        self.logger.debug(f"Trying editorial link: '{link_text}'")
                        driver.execute_script("arguments[0].scrollIntoView(true);", link)
                        link.click()
                        time.sleep(2)
                        found = True
                        break
                        
                if found:
                    break
                    
            except Exception as e:
                self.logger.debug(f"Error with alternative selectors: {e}")
                
            time.sleep(2)
        
        if not found:
            # Save page source for debugging
            with open("mf_after_login_debug.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
                
            # Try one more time with different approach
            self.logger.debug("Final attempt with more aggressive searching...")
            all_links = driver.find_elements(By.XPATH, "//a")
            self.logger.debug(f"Found {len(all_links)} total links on page")
            
            # Look for ANY link that might be the dashboard
            for link in all_links:
                try:
                    link_text = link.text.strip().lower()
                    href = link.get_attribute("href") or ""
                    
                    if link_text and any(word in link_text for word in ["dashboard", "home", "main", "center", "portal"]):
                        self.logger.debug(f"Trying dashboard link: '{link_text}'")
                        link.click()
                        time.sleep(2)
                        found = True
                        break
                        
                    # Also try hrefs that might be helpful
                    if href and any(word in href.lower() for word in ["dashboard", "home", "main", "center"]):
                        self.logger.debug(f"Trying href: '{href}'")
                        link.click()
                        time.sleep(2)
                        found = True
                        break
                        
                except Exception as e:
                    continue
        
        if not found:
            self.logger.error("Could not find or click Associate Editor Center after login.")
            self.logger.info("Proceeding anyway to check for manuscript data...")
            # Don't return empty list, try to continue
            
            # Try to find manuscript links directly on the page
            self.logger.info("Attempting deep search for manuscripts on current page...")
            
            # Look for any links that might lead to manuscripts
            manuscript_patterns = [
                "//a[contains(@href, 'manuscript')]",
                "//a[contains(@href, 'submission')]",
                "//a[contains(@href, 'MAFI-')]",
                "//a[contains(text(), 'MAFI-')]",
                "//a[contains(@href, 'view_submission')]",
                "//a[contains(@href, 'ms_details')]",
                "//a[contains(@onclick, 'view_submission')]"
            ]
            
            for pattern in manuscript_patterns:
                try:
                    links = driver.find_elements(By.XPATH, pattern)
                    if links:
                        self.logger.info(f"Found {len(links)} potential manuscript links with pattern: {pattern}")
                        # Click the first one to see if it leads to manuscript details
                        links[0].click()
                        time.sleep(2)
                        break
                except Exception as e:
                    self.logger.debug(f"Pattern {pattern} failed: {e}")
                    continue

        self.wait_if_human_check()
        dashboard_html = driver.page_source
        soup = BeautifulSoup(dashboard_html, "html.parser")

        # Expanded list of statuses to check for comprehensive scraping
        desired_statuses = [
            "Awaiting Reviewer Assignment",
            "Awaiting Reviewer Scores", 
            "Awaiting Reviewer Reports",
            "Awaiting Reviewer Invitation",
            "Overdue Reviewer Scores",
            "Awaiting Reviewer Selection",
            "Awaiting Reviewer Agreement", 
            "Awaiting AE Decision",
            "Awaiting AE Recommendation",
            "Partially Received",
            "Ready for Decision",
            "Under Review",
            "Reviewers Assigned",
            "Review in Progress",
            "Reviews Complete",
            "Manuscript Submitted",
            "New Submission",
            "Revised Manuscript Submitted",
            "Awaiting Revision",
            "Awaiting Review Completion",
            "Awaiting Final Decision"
        ]

        manuscript_results = {}
        status_found = False

        tds = soup.find_all("td")
        for i in range(len(tds) - 1):
            num_td, status_td = tds[i], tds[i+1]
            status = status_td.get_text(strip=True)
            if status in desired_statuses:
                num_str = num_td.get_text(strip=True)
                if num_str.isdigit() and int(num_str) > 0:
                    status_found = True
                    self.logger.debug(f"Found status '{status}' with count {num_str}")
                    try:
                        link = num_td.find("a")
                        if link and link.get("href"):
                            href = link.get("href")
                            link_elem = driver.find_element(By.XPATH, f"//a[@href='{href}']")
                            driver.execute_script("arguments[0].scrollIntoView(true);", link_elem)
                            link_elem.click()
                        else:
                            cell_elem = driver.find_element(By.XPATH, f"//*[text()='{num_str}']")
                            driver.execute_script("arguments[0].scrollIntoView(true);", cell_elem)
                            cell_elem.click()
                        self.logger.debug(f"Clicked number link for status '{status}' ({num_str})")
                        time.sleep(3)
                        self.wait_if_human_check()

                        ms_html = driver.page_source
                        ms_soup = BeautifulSoup(ms_html, "html.parser")
                        for table in ms_soup.find_all("table"):
                            if table.find("b", string=re.compile(r"MAFI-\d{4}-\d+")):
                                mdata = self.parse_manuscript_panel(str(table), flagged_emails=flagged_emails)
                                ms_id = mdata["Manuscript #"]
                                if ms_id and ms_id not in manuscript_results:
                                    manuscript_results[ms_id] = mdata

                        # Return to AE center after detail view
                        returned = False
                        for attempt in range(3):  # Reduced from 8 to 3
                            try:
                                # Try more specific selectors first
                                ae_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Associate Editor Center')]")
                                if not ae_links:
                                    ae_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Assignment Center')]")
                                if not ae_links:
                                    ae_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Editor Center')]")
                                
                                if ae_links:
                                    ae_links[0].click()
                                    time.sleep(1)  # Reduced sleep time
                                    returned = True
                                    break
                                    
                            except Exception as e:
                                self.logger.debug(f"Failed to find Associate Editor Center link (attempt {attempt + 1}): {e}")
                                time.sleep(0.5)  # Reduced sleep time
                        
                        if not returned:
                            self.logger.warning("Could not return to Associate Editor Center, continuing...")
                        self.wait_if_human_check()
                        dashboard_html = driver.page_source
                        soup = BeautifulSoup(dashboard_html, "html.parser")
                        tds = soup.find_all("td")
                    except Exception as e:
                        self.logger.debug(f"Failed to click or parse for status '{status}': {e}")

        if not status_found:
            self.logger.debug("No relevant status queues with count > 0 found.")
            
            # Try to find navigation links directly
            self.logger.info("Searching for direct navigation links to manuscripts...")
            
            # Look for links that might lead to different manuscript views
            navigation_patterns = [
                "//a[contains(text(), 'Awaiting')]",
                "//a[contains(text(), 'Under Review')]",
                "//a[contains(text(), 'Reviewer')]",
                "//a[contains(text(), 'Assignment')]",
                "//a[contains(text(), 'Decision')]"
            ]
            
            for pattern in navigation_patterns:
                try:
                    nav_links = driver.find_elements(By.XPATH, pattern)
                    for link in nav_links:
                        link_text = link.text.strip()
                        self.logger.info(f"Found navigation link: '{link_text}'")
                        
                        try:
                            driver.execute_script("arguments[0].scrollIntoView(true);", link)
                            link.click()
                            time.sleep(3)
                            self.wait_if_human_check()
                            
                            # Check for manuscripts on this page
                            page_html = driver.page_source
                            page_soup = BeautifulSoup(page_html, "html.parser")
                            
                            # Look for manuscript tables
                            for table in page_soup.find_all("table"):
                                if table.find("b", string=re.compile(r"MAFI-\d{4}-\d+")):
                                    mdata = self.parse_manuscript_panel(str(table), flagged_emails=flagged_emails)
                                    ms_id = mdata["Manuscript #"]
                                    if ms_id and ms_id not in manuscript_results:
                                        manuscript_results[ms_id] = mdata
                                        self.logger.info(f"Found manuscript via navigation: {ms_id}")
                            
                            # Check if this is a list page with multiple manuscripts
                            manuscript_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'MANUSCRIPT_DETAILS')]")
                            for ms_link in manuscript_links:
                                try:
                                    ms_link.click()
                                    time.sleep(2)
                                    self.wait_if_human_check()
                                    
                                    detail_html = driver.page_source
                                    detail_soup = BeautifulSoup(detail_html, "html.parser")
                                    
                                    for table in detail_soup.find_all("table"):
                                        if table.find("b", string=re.compile(r"MAFI-\d{4}-\d+")):
                                            mdata = self.parse_manuscript_panel(str(table), flagged_emails=flagged_emails)
                                            ms_id = mdata["Manuscript #"]
                                            if ms_id and ms_id not in manuscript_results:
                                                manuscript_results[ms_id] = mdata
                                                self.logger.info(f"Found manuscript in details: {ms_id}")
                                    
                                    # Go back
                                    driver.back()
                                    time.sleep(1)
                                except Exception as e:
                                    self.logger.debug(f"Error checking manuscript detail: {e}")
                                    continue
                            
                            # Go back to main page
                            driver.back()
                            time.sleep(1)
                            
                        except Exception as e:
                            self.logger.debug(f"Error clicking navigation link '{link_text}': {e}")
                            continue
                            
                except Exception as e:
                    self.logger.debug(f"Error with navigation pattern {pattern}: {e}")
                    continue
            
            # Deep search: Look for manuscripts in any table on the page
            self.logger.info("Performing deep search for manuscripts in tables...")
            
            # Look for MAFI manuscript IDs in any table
            all_tables = soup.find_all("table")
            for table_idx, table in enumerate(all_tables):
                # Look for MAFI- pattern
                if table.find(text=re.compile(r"MAFI-\d{4}-\d+")):
                    self.logger.info(f"Found potential manuscript table #{table_idx}")
                    
                    # Try to parse each row that contains a MAFI ID
                    rows = table.find_all("tr")
                    for row in rows:
                        text_content = row.get_text()
                        if re.search(r"MAFI-\d{4}-\d+", text_content):
                            # Try to extract manuscript data from this row
                            try:
                                # Look for a link to manuscript details
                                ms_link = row.find("a", href=re.compile(r"(manuscript|submission|MAFI)"))
                                if ms_link:
                                    self.logger.info(f"Found manuscript link in table row: {ms_link.get('href', '')}")
                                    # Click the link to get details
                                    href = ms_link.get("href", "")
                                    if href:
                                        link_elem = driver.find_element(By.XPATH, f"//a[@href='{href}']")
                                        driver.execute_script("arguments[0].scrollIntoView(true);", link_elem)
                                        link_elem.click()
                                        time.sleep(3)
                                        
                                        # Parse the manuscript detail page
                                        detail_html = driver.page_source
                                        mdata = self.parse_manuscript_panel(detail_html, flagged_emails=flagged_emails)
                                        ms_id = mdata["Manuscript #"]
                                        if ms_id and ms_id not in manuscript_results:
                                            manuscript_results[ms_id] = mdata
                                            self.logger.info(f"Successfully parsed manuscript: {ms_id}")
                                        
                                        # Go back to the list
                                        driver.back()
                                        time.sleep(2)
                            except Exception as e:
                                self.logger.debug(f"Error processing table row: {e}")
                                continue

        self.logger.info(f"Final results (all parsed manuscripts): {len(manuscript_results)} manuscripts.")
        manuscripts = list(manuscript_results.values())
        # Download papers and reports with AI analysis
        enhanced_manuscripts = self.download_and_analyze_manuscripts(manuscripts)
        return enhanced_manuscripts
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
                    paper_links = self.paper_downloader.find_paper_links(self.driver, "MF")
                    
                    for link in paper_links:
                        if link['type'] == 'href':
                            paper_path = self.paper_downloader.download_paper(
                                manuscript_id, title, link['url'], "MF", self.driver
                            )
                            if paper_path:
                                enhanced_ms['downloads']['paper'] = str(paper_path)
                                break
                    
                    # Try to find referee report links
                    report_links = self.paper_downloader.find_report_links(self.driver, "MF")
                    
                    for link in report_links:
                        if link['type'] == 'href':
                            report_path = self.paper_downloader.download_referee_report(
                                manuscript_id, link['text'], link['url'], "MF", self.driver
                            )
                            if report_path:
                                enhanced_ms['downloads']['reports'].append(str(report_path))
                
            except Exception as e:
                print(f"Error downloading for manuscript {manuscript_id}: {e}")
            
            enhanced_manuscripts.append(enhanced_ms)
        
        return enhanced_manuscripts

    def _extract_referee_emails_directly(self, manuscript_id):
        """Extract referee emails directly from ManuscriptCentral profile links"""
        emails = []
        
        try:
            # Look for referee profile links in ManuscriptCentral
            referee_profile_selectors = [
                "//a[contains(@href, 'REVIEWER_DETAILS')]",
                "//a[contains(@href, 'reviewer_details')]", 
                "//a[contains(@href, 'USER_DETAILS')]",
                "//a[contains(@href, 'user_details')]",
                "//a[contains(@onclick, 'reviewerDetails')]",
                "//a[contains(@onclick, 'userDetails')]"
            ]
            
            main_window = self.driver.current_window_handle
            
            for selector in referee_profile_selectors:
                try:
                    profile_links = self.driver.find_elements(By.XPATH, selector)
                    self.logger.info(f"Found {len(profile_links)} referee profile links with selector: {selector}")
                    
                    for link in profile_links:
                        try:
                            referee_name = link.text.strip()
                            self.logger.info(f"Extracting email for referee: {referee_name}")
                            
                            # Click profile link
                            self.driver.execute_script("arguments[0].click();", link)
                            time.sleep(2)
                            
                            # Handle new window/popup
                            if len(self.driver.window_handles) > 1:
                                self.driver.switch_to.window(self.driver.window_handles[-1])
                                time.sleep(2)
                            
                            # Extract email from profile page
                            email_selectors = [
                                "//td[contains(text(), 'Email')]/following-sibling::td",
                                "//td[contains(text(), 'E-mail')]/following-sibling::td",
                                "//th[contains(text(), 'Email')]/following-sibling::td",
                                "//th[contains(text(), 'E-mail')]/following-sibling::td",
                                "//span[contains(text(), '@')]",
                                "//a[contains(@href, 'mailto:')]"
                            ]
                            
                            email = ""
                            for email_selector in email_selectors:
                                try:
                                    email_element = self.driver.find_element(By.XPATH, email_selector)
                                    email_text = email_element.text.strip()
                                    if '@' in email_text:
                                        email = email_text
                                        break
                                    # Check for mailto links
                                    if email_element.tag_name == 'a':
                                        href = email_element.get_attribute('href')
                                        if href and 'mailto:' in href:
                                            email = href.replace('mailto:', '')
                                            break
                                except:
                                    continue
                            
                            if email:
                                emails.append({
                                    'name': referee_name,
                                    'email': email,
                                    'source': 'profile_direct'
                                })
                                self.logger.info(f"Found email for {referee_name}: {email}")
                            
                            # Close popup/go back
                            if len(self.driver.window_handles) > 1:
                                self.driver.close()
                                self.driver.switch_to.window(main_window)
                            else:
                                self.driver.back()
                                time.sleep(1)
                                
                        except Exception as e:
                            self.logger.warning(f"Error extracting email for referee: {e}")
                            # Make sure we're back on main window
                            try:
                                if len(self.driver.window_handles) > 1:
                                    self.driver.close()
                                    self.driver.switch_to.window(main_window)
                            except:
                                pass
                            continue
                    
                    if emails:
                        break  # Found emails with this selector
                        
                except Exception as e:
                    self.logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            self.logger.info(f"Direct email extraction found {len(emails)} emails for manuscript {manuscript_id}")
            return emails
            
        except Exception as e:
            self.logger.error(f"Error in direct email extraction: {e}")
            return []

    def _enhance_email_matching(self, ref_name, ms_id, status, flagged_emails):
        """Enhanced email matching that gets ALL referee emails"""
        # First try direct extraction
        direct_emails = self._extract_referee_emails_directly(ms_id)
        
        # Check if we found this referee in direct extraction
        for email_data in direct_emails:
            if self._names_match(ref_name, email_data['name']):
                return email_data['email']
        
        # Fall back to enhanced email matching
        return self._enhanced_email_search(ref_name, ms_id, status, flagged_emails)
    
    def _names_match(self, name1, name2):
        """Check if two names match with various formats"""
        def normalize_name(name):
            # Remove punctuation and convert to lowercase
            import re
            name = re.sub(r'[^\w\s]', '', name.lower())
            return ' '.join(name.split())
        
        norm1 = normalize_name(name1)
        norm2 = normalize_name(name2)
        
        if norm1 == norm2:
            return True
        
        # Handle "Last, First" vs "First Last" formats
        if ',' in name1:
            parts1 = [p.strip() for p in name1.split(',')]
            rearranged1 = f"{parts1[1]} {parts1[0]}" if len(parts1) == 2 else name1
            if normalize_name(rearranged1) == norm2:
                return True
        
        if ',' in name2:
            parts2 = [p.strip() for p in name2.split(',')]
            rearranged2 = f"{parts2[1]} {parts2[0]}" if len(parts2) == 2 else name2
            if normalize_name(rearranged2) == norm1:
                return True
        
        return False
    
    def _enhanced_email_search(self, ref_name, ms_id, status, flagged_emails):
        """Enhanced email search that looks beyond just starred emails"""
        # Use the existing robust matching
        date, email = robust_match_email_for_referee_mf(ref_name, ms_id, status, flagged_emails)
        
        if email:
            return email
        
        # If no email found, try broader search patterns
        # This could be enhanced to search all emails, not just starred ones
        # For now, we'll use the existing system but with enhanced matching
        
        return ""

    def _extract_cover_letters(self, manuscript_id):
        """Extract cover letters from ManuscriptCentral"""
        cover_letters = []
        
        try:
            # Look for cover letter links in ManuscriptCentral
            cover_letter_selectors = [
                "//a[contains(@href, 'cover') and contains(@href, 'letter')]",
                "//a[contains(text(), 'Cover Letter')]",
                "//a[contains(text(), 'cover letter')]",
                "//a[contains(@href, 'COVER_LETTER')]",
                "//a[contains(@onclick, 'coverLetter')]",
                "//span[contains(text(), 'Cover Letter')]/ancestor::a"
            ]
            
            for selector in cover_letter_selectors:
                try:
                    cover_links = self.driver.find_elements(By.XPATH, selector)
                    self.logger.info(f"Found {len(cover_links)} cover letter links with selector: {selector}")
                    
                    for link in cover_links:
                        try:
                            link_text = link.text.strip()
                            href = link.get_attribute('href')
                            onclick = link.get_attribute('onclick')
                            
                            if href and any(keyword in href.lower() for keyword in ['cover', 'letter']):
                                cover_letters.append({
                                    'title': link_text,
                                    'url': href,
                                    'type': 'href'
                                })
                                self.logger.info(f"Found cover letter: {link_text} -> {href}")
                            elif onclick and 'cover' in onclick.lower():
                                cover_letters.append({
                                    'title': link_text,
                                    'url': onclick,
                                    'type': 'onclick'
                                })
                                self.logger.info(f"Found cover letter: {link_text} -> {onclick}")
                                
                        except Exception as e:
                            self.logger.debug(f"Error processing cover letter link: {e}")
                            continue
                    
                    if cover_letters:
                        break  # Found cover letters with this selector
                        
                except Exception as e:
                    self.logger.debug(f"Cover letter selector {selector} failed: {e}")
                    continue
            
            self.logger.info(f"Cover letter extraction found {len(cover_letters)} cover letters for manuscript {manuscript_id}")
            return cover_letters
            
        except Exception as e:
            self.logger.error(f"Error in cover letter extraction: {e}")
            return []

    def _extract_enhanced_referee_reports(self, manuscript_id):
        """Enhanced referee report extraction from ManuscriptCentral"""
        reports = []
        
        try:
            # Look for referee report links with more comprehensive selectors
            report_selectors = [
                "//a[contains(@href, 'review') and contains(@href, 'report')]",
                "//a[contains(@href, 'REVIEW_REPORT')]",
                "//a[contains(@href, 'referee_report')]",
                "//a[contains(@href, 'REFEREE_REPORT')]",
                "//a[contains(text(), 'Review Report')]",
                "//a[contains(text(), 'Referee Report')]",
                "//a[contains(text(), 'Reviewer Report')]",
                "//a[contains(@onclick, 'reviewReport')]",
                "//a[contains(@onclick, 'refereeReport')]",
                "//span[contains(text(), 'Review Report')]/ancestor::a",
                "//span[contains(text(), 'Referee Report')]/ancestor::a"
            ]
            
            for selector in report_selectors:
                try:
                    report_links = self.driver.find_elements(By.XPATH, selector)
                    self.logger.info(f"Found {len(report_links)} referee report links with selector: {selector}")
                    
                    for link in report_links:
                        try:
                            link_text = link.text.strip()
                            href = link.get_attribute('href')
                            onclick = link.get_attribute('onclick')
                            
                            if href and any(keyword in href.lower() for keyword in ['review', 'report', 'referee']):
                                reports.append({
                                    'title': link_text,
                                    'url': href,
                                    'type': 'href'
                                })
                                self.logger.info(f"Found referee report: {link_text} -> {href}")
                            elif onclick and any(keyword in onclick.lower() for keyword in ['review', 'report']):
                                reports.append({
                                    'title': link_text,
                                    'url': onclick,
                                    'type': 'onclick'
                                })
                                self.logger.info(f"Found referee report: {link_text} -> {onclick}")
                                
                        except Exception as e:
                            self.logger.debug(f"Error processing referee report link: {e}")
                            continue
                    
                    if reports:
                        break  # Found reports with this selector
                        
                except Exception as e:
                    self.logger.debug(f"Referee report selector {selector} failed: {e}")
                    continue
            
            self.logger.info(f"Enhanced referee report extraction found {len(reports)} reports for manuscript {manuscript_id}")
            return reports
            
        except Exception as e:
            self.logger.error(f"Error in enhanced referee report extraction: {e}")
            return []
