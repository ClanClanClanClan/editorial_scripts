import os
import time
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

from core.base import JournalBase
from core.paper_downloader import get_paper_downloader

class NACOJournal(JournalBase):
    NACO_URL = "https://ef.msp.org/login.php"

    def __init__(self, driver, debug=True, chrome_profile_dir=None):
        super().__init__(driver)
        self.debug = debug
        self.chrome_profile_dir = chrome_profile_dir

        self.paper_downloader = get_paper_downloader()
    def get_url(self):
        return self.NACO_URL
    
    def _find_mine_link(self, driver, timeout=10):
        """Find the 'Mine' link using multiple selectors"""
        # Try different selectors for the Mine link
        selectors = [
            (By.LINK_TEXT, "Mine"),
            (By.PARTIAL_LINK_TEXT, "Mine"),
            (By.XPATH, "//a[contains(text(), 'Mine')]"),
            (By.XPATH, "//a[contains(@href, 'mine')]"),
            (By.XPATH, "//a[contains(@href, 'Mine')]"),
            (By.CSS_SELECTOR, "a[href*='mine']"),
            (By.CSS_SELECTOR, "a[href*='Mine']"),
            (By.XPATH, "//a[text()='Mine']"),
            (By.XPATH, "//span[contains(text(), 'Mine')]/parent::a"),
            (By.XPATH, "//li[contains(text(), 'Mine')]//a"),
        ]
        
        for by, selector in selectors:
            try:
                element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((by, selector))
                )
                if element and element.is_displayed():
                    if self.debug:
                        print(f"[NACO] Found 'Mine' link with selector: {selector}")
                    return element
            except TimeoutException:
                continue
        
        # If not found, try a broader search
        try:
            all_links = driver.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                try:
                    text = link.text.strip().lower()
                    href = link.get_attribute("href") or ""
                    if ("mine" in text or "mine" in href.lower()) and link.is_displayed():
                        if self.debug:
                            print(f"[NACO] Found 'Mine' link via broad search: {link.text}")
                        return link
                except:
                    continue
        except:
            pass
        
        return None

    def _parse_manuscript_from_article(self, article):
        """Extract manuscript data from an article element"""
        try:
            manuscript_data = {
                "Manuscript #": "",
                "Title": "",
                "Contact Author": "",
                "Current Stage": "",
                "Submission Date": "",
                "Referees": []
            }
            
            # Extract manuscript ID from links or spans
            id_links = article.find_all("a", href=True)
            for link in id_links:
                href = link.get("href", "")
                text = link.text.strip()
                
                # Look for NACO manuscript ID pattern
                if "NACO-" in text.upper() or "manuscript" in href.lower():
                    manuscript_data["Manuscript #"] = text.upper()
                    break
                    
                # Try to extract from href if not found in text
                if not manuscript_data["Manuscript #"]:
                    import re
                    match = re.search(r'id=(\d+)', href)
                    if match:
                        manuscript_data["Manuscript #"] = f"NACO-{match.group(1)}"
            
            # Extract title - usually in h3 or strong tags
            title_elements = article.find_all(['h3', 'strong', 'b'])
            for element in title_elements:
                text = element.text.strip()
                if text and len(text) > 10 and not text.startswith("Associate"):
                    manuscript_data["Title"] = text
                    break
            
            # Extract author information - often in italics or specific spans
            author_elements = article.find_all(['i', 'em', 'span'])
            for element in author_elements:
                text = element.text.strip()
                if text and ("by " in text.lower() or "@" in text):
                    # Clean up author name
                    author = text.replace("by ", "").replace("By ", "").strip()
                    if author:
                        manuscript_data["Contact Author"] = author
                        break
            
            # Extract current stage from status indicators
            status_elements = article.find_all(['span', 'div'])
            for element in status_elements:
                text = element.text.strip().lower()
                if any(keyword in text for keyword in ['under review', 'awaiting', 'assigned', 'pending']):
                    manuscript_data["Current Stage"] = element.text.strip()
                    break
            
            # Extract submission date
            date_elements = article.find_all(['span', 'div', 'small'])
            for element in date_elements:
                text = element.text.strip()
                if any(keyword in text.lower() for keyword in ['submitted', 'received', 'date']):
                    import re
                    date_match = re.search(r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}', text)
                    if date_match:
                        manuscript_data["Submission Date"] = date_match.group(0)
                        break
            
            # Extract referee information from nested elements
            referee_elements = article.find_all(['ul', 'ol', 'div'])
            for element in referee_elements:
                if 'referee' in element.text.lower() or 'reviewer' in element.text.lower():
                    referees = self._extract_referees_from_element(element)
                    if referees:
                        manuscript_data["Referees"] = referees
                        break
            
            # Only return if we have at least a manuscript ID or title
            if manuscript_data["Manuscript #"] or manuscript_data["Title"]:
                if self.debug:
                    print(f"[NACO] Parsed manuscript: {manuscript_data['Manuscript #']} - {manuscript_data['Title']}")
                return manuscript_data
            
        except Exception as e:
            if self.debug:
                print(f"[NACO] Error parsing manuscript from article: {e}")
        
        return None

    def _extract_referees_from_element(self, element):
        """Extract referee information from a container element"""
        referees = []
        
        try:
            # Look for referee entries in list items or divs
            referee_items = element.find_all(['li', 'div', 'p'])
            
            for item in referee_items:
                text = item.text.strip()
                if not text or len(text) < 5:
                    continue
                
                # Extract email addresses
                import re
                email_matches = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
                
                if email_matches:
                    # Try to extract name (usually before the email)
                    name_part = text.split('@')[0] if '@' in text else text
                    name = re.sub(r'[^\w\s]', '', name_part).strip()
                    
                    # Determine status from keywords
                    status = "Contacted"
                    if any(keyword in text.lower() for keyword in ['accepted', 'agreed', 'confirmed']):
                        status = "Accepted"
                    elif any(keyword in text.lower() for keyword in ['declined', 'rejected', 'refused']):
                        status = "Declined"
                    
                    referee = {
                        "Referee Name": name,
                        "Referee Email": email_matches[0],
                        "Status": status,
                        "Contacted Date": "",
                        "Due Date": ""
                    }
                    
                    # Try to extract dates
                    date_matches = re.findall(r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}', text)
                    if date_matches:
                        referee["Contacted Date"] = date_matches[0]
                    
                    referees.append(referee)
        
        except Exception as e:
            if self.debug:
                print(f"[NACO] Error extracting referees: {e}")
        
        return referees

    def login(self):
        driver = self.driver
        driver.get(self.NACO_URL)
        time.sleep(1.0)

        # 1. If already logged in, "Mine" should be present
        try:
            mine_link = self._find_mine_link(driver, timeout=5)
            if mine_link and mine_link.is_displayed():
                if self.debug:
                    print("[NACO] Already logged in, skipping login form.")
                return  # Already logged in!
        except TimeoutException:
            pass  # Not yet logged in, continue to login

        # 2. Try normal login if not already logged in
        user = os.environ.get("NACO_USER")
        pw = os.environ.get("NACO_PASS")
        try:
            user_field = WebDriverWait(driver, 12).until(
                EC.presence_of_element_located((By.ID, "login"))
            )
            pw_field = driver.find_element(By.NAME, "password")
        except TimeoutException:
            # If neither "Mine" nor login fields, something is wrong
            raise Exception("[NACO] Login fields not found (page did not load?)")
        user_field.clear()
        user_field.send_keys(user)
        pw_field.clear()
        pw_field.send_keys(pw)
        login_btn = driver.find_element(By.NAME, "signin")
        login_btn.click()
        if self.debug:
            print("[NACO] Submitted login form.")
        time.sleep(2)

    def scrape_manuscripts_and_emails(self):
        driver = self.driver
        self.login()
        time.sleep(1.5)
        # Try to find and click the "Mine" link robustly
        try:
            mine_link = self._find_mine_link(driver, timeout=12)
            if not mine_link:
                raise Exception("Mine link not found")
            
            driver.execute_script("arguments[0].scrollIntoView(true);", mine_link)
            # Sometimes in headless mode, element is present but not yet clickable
            for attempt in range(5):
                if mine_link.is_displayed() and mine_link.is_enabled():
                    try:
                        mine_link.click()
                        if self.debug:
                            print("[NACO] Clicked 'Mine' link.")
                        break
                    except ElementClickInterceptedException:
                        time.sleep(0.8)
                else:
                    time.sleep(0.8)
            else:
                print("[NACO] 'Mine' link found but never became clickable.")
                with open("naco_debug_nomine.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                return []
        except Exception as e:
            print(f"[NACO] Could not find/click 'Mine' link: {e}")
            with open("naco_debug_nomine.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            return []

        # Wait briefly for Mine page to load (no error if no articles)
        time.sleep(2.0)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        articles = soup.find_all("article", class_="JournalView-Listing")

        # If no articles, just save the HTML and quietly return
        if not articles:
            if self.debug:
                print("[NACO] No articles assigned (empty AE queue).")
            with open("naco_mine.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            return []

        # Parse AE blocks and manuscripts
        manuscripts = []
        for article in articles:
            name_span = article.find("span", {"data-tooltip": "Associate Editor"})
            if not name_span or "Possamaï" not in name_span.text:
                continue  # not your AE block
            h2 = article.find("h2")
            if h2 and "no articles" in h2.text.lower():
                continue  # nothing assigned
            
            # Extract manuscript details from the article
            manuscript_data = self._parse_manuscript_from_article(article)
            if manuscript_data:
                manuscripts.append(manuscript_data)

        # Save page source for reference
        with open("naco_mine.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
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
                    paper_links = self.paper_downloader.find_paper_links(self.driver, "NACO")
                    
                    for link in paper_links:
                        if link['type'] == 'href':
                            paper_path = self.paper_downloader.download_paper(
                                manuscript_id, title, link['url'], "NACO", self.driver
                            )
                            if paper_path:
                                enhanced_ms['downloads']['paper'] = str(paper_path)
                                break
                    
                    # Try to find referee report links
                    report_links = self.paper_downloader.find_report_links(self.driver, "NACO")
                    
                    for link in report_links:
                        if link['type'] == 'href':
                            report_path = self.paper_downloader.download_referee_report(
                                manuscript_id, link['text'], link['url'], "NACO", self.driver
                            )
                            if report_path:
                                enhanced_ms['downloads']['reports'].append(str(report_path))
                
            except Exception as e:
                print(f"Error downloading for manuscript {manuscript_id}: {e}")
            
            enhanced_manuscripts.append(enhanced_ms)
        
        return enhanced_manuscripts
