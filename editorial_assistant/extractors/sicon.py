"""SIAM Journal on Control and Optimization (SICON) extractor."""

from typing import List, Dict, Any, Tuple
import logging
import time
from bs4 import BeautifulSoup
import re

from editorial_assistant.core.data_models import JournalConfig
from editorial_assistant.extractors.base_platform_extractors import SIAMExtractor


class SICONExtractor(SIAMExtractor):
    """SIAM Journal on Control and Optimization extractor using ORCID authentication."""
    
    def __init__(self, journal: JournalConfig):
        super().__init__(journal)
        self.site_prefix = "https://sicon.siam.org/"
        
    def _login(self) -> None:
        """Login to SICON using ORCID authentication."""
        try:
            # Navigate to SICON URL
            self.driver.get(self.journal.url)
            time.sleep(2)
            
            # Remove cookie banners
            self._remove_cookie_banner()
            self._dismiss_cookie_modal()
            
            # Check if already logged in
            if self._is_logged_in():
                logging.info(f"[{self.journal.code}] Already logged in")
                return
            
            # Look for and click ORCID login link
            orcid_login_link = self._wait_for_element_by_xpath(
                "//a[contains(@href, 'orcid') or contains(text(), 'ORCID')]", 
                timeout=10
            )
            
            if not orcid_login_link:
                # Try alternative selectors
                orcid_links = self.driver.find_elements("xpath", "//a[contains(@href, 'orcid')]")
                if orcid_links:
                    orcid_login_link = orcid_links[0]
            
            if not orcid_login_link:
                raise Exception("No ORCID login link found on SICON page")
            
            # Click ORCID login
            orcid_login_link.click()
            logging.info(f"[{self.journal.code}] Clicked ORCID login link")
            time.sleep(2)
            
            # Handle ORCID authentication
            if not self._handle_orcid_authentication():
                raise Exception("ORCID authentication failed")
            
            # Wait for redirect back to SICON
            self._wait_for_url_contains("sicon.siam.org", timeout=30)
            
            # Handle any post-login popups
            self._handle_post_login_popups()
            
            logging.info(f"[{self.journal.code}] Successfully logged in")
            
        except Exception as e:
            logging.error(f"[{self.journal.code}] Login failed: {e}")
            raise
    
    def _is_logged_in(self) -> bool:
        """Check if already logged in by looking for AE dashboard elements."""
        try:
            dashboard_indicators = [
                "//tbody[@role='assoc_ed']",
                "//tr[@class='ndt_task']",
                "//a[@class='ndt_task_link']"
            ]
            
            for indicator in dashboard_indicators:
                elements = self.driver.find_elements("xpath", indicator)
                if elements:
                    return True
            
            return False
            
        except Exception:
            return False
    
    def _remove_cookie_banner(self) -> None:
        """Remove cookie banners using JavaScript."""
        js_hide = """
        for(let sel of [
            '#cookie-policy-layer-bg',
            '.cc_banner-wrapper',
            '#cookie-policy-layer',
            '#onetrust-banner-sdk',
            '.onetrust-pc-dark-filter'
        ]) {
            let el = document.querySelector(sel);
            if(el) el.style.display='none';
        }
        """
        try:
            self.driver.execute_script(js_hide)
        except Exception:
            pass
    
    def _handle_post_login_popups(self) -> None:
        """Handle any popups that appear after login."""
        try:
            # Remove cookie banners
            self._remove_cookie_banner()
            self._dismiss_cookie_modal()
            
            # Handle privacy/terms popups
            popup_buttons = [
                "//input[@type='button' and @value='Continue']",
                "//button[contains(text(), 'Continue')]",
                "//button[contains(text(), 'Accept')]",
                "//input[@type='button' and @value='Accept']"
            ]
            
            for button_xpath in popup_buttons:
                try:
                    button = self._wait_for_element_by_xpath(button_xpath, timeout=3)
                    if button and button.is_displayed() and button.is_enabled():
                        button.click()
                        logging.info(f"[{self.journal.code}] Clicked post-login popup button")
                        time.sleep(1)
                        break
                except Exception:
                    continue
            
        except Exception as e:
            logging.debug(f"[{self.journal.code}] Post-login popup handling: {e}")
    
    def extract_manuscripts(self) -> List[Dict[str, Any]]:
        """Extract manuscripts from SICON dashboard."""
        try:
            # Navigate to dashboard
            self.driver.get(self.journal.url)
            self._remove_cookie_banner()
            self._login()
            self._remove_cookie_banner()
            time.sleep(1)
            
            # Find manuscript links in AE sections
            manuscript_links = self._collect_manuscript_links()
            
            if not manuscript_links:
                logging.warning(f"[{self.journal.code}] No assigned manuscripts found")
                return []
            
            # Extract data from each manuscript
            manuscripts = []
            email_urls = []
            
            for url in manuscript_links:
                try:
                    self.driver.get(url)
                    time.sleep(1.0)
                    
                    manuscript_data, ms_email_urls = self._extract_manuscript_table()
                    if manuscript_data:
                        manuscripts.append(manuscript_data)
                        email_urls.extend(ms_email_urls)
                        
                except Exception as e:
                    logging.error(f"[{self.journal.code}] Error scraping {url}: {e}")
                    continue
            
            # Batch fetch referee emails
            email_cache = self._batch_fetch_emails(email_urls)
            
            # Add emails to manuscript data
            for manuscript in manuscripts:
                for referee in manuscript.get("Referees", []):
                    referee_url = referee.get("Referee URL", "")
                    referee["Referee Email"] = email_cache.get(referee_url, "")
            
            logging.info(f"[{self.journal.code}] Extracted {len(manuscripts)} manuscripts")
            return manuscripts
            
        except Exception as e:
            logging.error(f"[{self.journal.code}] Manuscript extraction failed: {e}")
            return []
    
    def _collect_manuscript_links(self) -> List[str]:
        """Collect manuscript links from AE dashboard."""
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        manuscript_links = []
        
        # Find associate editor sections
        for assoc_ed_section in soup.find_all("tbody", {"role": "assoc_ed"}):
            for row in assoc_ed_section.find_all("tr", class_="ndt_task"):
                link = row.find("a", class_="ndt_task_link")
                if not link:
                    continue
                    
                # Check if it's a manuscript link (starts with #)
                if not link.text.strip().startswith("#"):
                    continue
                
                href = link.get("href", "")
                if "form_type=view_ms" in href:
                    full_url = href if href.startswith("http") else self.site_prefix + href.lstrip("/")
                    manuscript_links.append(full_url)
        
        return manuscript_links
    
    def _extract_manuscript_table(self) -> Tuple[Dict[str, Any], List[str]]:
        """Extract manuscript data from the manuscript details table."""
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        table = soup.find("table", id="ms_details_expanded")
        
        if not table:
            return None, []
        
        manuscript_info = {}
        referees = []
        email_urls = []
        
        for row in table.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            
            if not th or not td:
                continue
            
            label = th.get_text(strip=True)
            value = td.decode_contents()
            
            if label.startswith("Manuscript #"):
                manuscript_info["Manuscript #"] = td.get_text(strip=True)
            elif label == "Title":
                manuscript_info["Title"] = td.get_text(strip=True)
            elif label == "Submission Date":
                manuscript_info["Submitted"] = td.get_text(strip=True)
            elif label == "Current Stage":
                manuscript_info["Current Stage"] = td.get_text(strip=True)
            elif label == "Referees":
                if "N/A" in value:
                    continue
                
                # Extract accepted referees
                for ref_link in td.find_all("a"):
                    referee_name = ref_link.get_text(strip=True)
                    referee_url = ref_link.get("href")
                    
                    # Extract due date if present
                    due_date = ""
                    next_font = ref_link.find_next("font")
                    if next_font and "Due:" in next_font.text:
                        match = re.search(r"Due:\s*([\d\-]+)", next_font.text)
                        if match:
                            due_date = match.group(1)
                    
                    abs_url = referee_url if referee_url.startswith("http") else self.site_prefix + referee_url.lstrip("/")
                    email_urls.append(abs_url)
                    
                    referees.append({
                        "Referee Name": referee_name,
                        "Referee URL": abs_url,
                        "Status": "Accepted",
                        "Due Date": due_date
                    })
            
            elif "Potential Referees" in label:
                # Extract potential referees
                soup_inner = BeautifulSoup(str(td), "html.parser")
                
                for ref_link in soup_inner.find_all("a"):
                    referee_name = ref_link.get_text(strip=True)
                    referee_url = ref_link.get("href", "")
                    
                    abs_url = referee_url if referee_url.startswith("http") else self.site_prefix + referee_url.lstrip("/")
                    
                    # Extract status from surrounding text
                    status = self._extract_referee_status(ref_link)
                    
                    if status.lower().strip() == "declined":
                        continue
                    
                    if status.lower().strip() == "contacted":
                        email_urls.append(abs_url)
                        referees.append({
                            "Referee Name": referee_name,
                            "Referee URL": abs_url,
                            "Status": "Contacted",
                            "Due Date": ""
                        })
        
        result = {
            "Manuscript #": manuscript_info.get("Manuscript #", ""),
            "Title": manuscript_info.get("Title", ""),
            "Submitted": manuscript_info.get("Submitted", ""),
            "Current Stage": manuscript_info.get("Current Stage", ""),
            "Referees": referees,
        }
        
        return result, email_urls
    
    def _extract_referee_status(self, ref_link) -> str:
        """Extract referee status from surrounding text."""
        try:
            # Look for status in following siblings
            siblings = []
            node = ref_link.next_sibling
            count = 0
            
            while node and count < 8:
                if hasattr(node, "name") and node.name == "a":
                    break
                if isinstance(node, str):
                    siblings.append(node.strip())
                node = node.next_sibling
                count += 1
            
            text = " ".join(siblings)
            match = re.search(r"Status:\s*([^)]+)", text)
            
            return match.group(1) if match else ""
            
        except Exception:
            return ""
    
    def _batch_fetch_emails(self, email_urls: List[str]) -> Dict[str, str]:
        """Batch fetch emails from referee profile URLs."""
        email_cache = {}
        unique_urls = set(url for url in email_urls if url)
        
        for url in unique_urls:
            full_url = url if url.startswith("http") else self.site_prefix + url.lstrip("/")
            
            try:
                self.driver.get(full_url)
                self._dismiss_cookie_modal()
                
                # Wait for email to appear
                self._wait_for_page_load(timeout=5)
                
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                
                # Look for mailto links
                email_link = soup.find("a", href=re.compile(r"mailto:"))
                if email_link:
                    email_cache[url] = email_link.text.strip()
                    continue
                
                # Look for email patterns in text
                found = False
                for td in soup.find_all("td"):
                    text = td.get_text(strip=True)
                    if "@" in text and "." in text:
                        email_cache[url] = text
                        found = True
                        break
                
                if not found:
                    email_cache[url] = ""
                    
            except Exception as e:
                logging.warning(f"[{self.journal.code}] Failed to fetch email from {url}: {e}")
                email_cache[url] = ""
        
        return email_cache
    
    def _navigate_to_manuscripts(self) -> None:
        """Navigate to the manuscripts list page."""
        try:
            # For SICON, we navigate to the main dashboard
            self.driver.get(self.journal.url)
            self._remove_cookie_banner()
            
            # Wait for dashboard to load
            self._wait_for_page_load(timeout=10)
            
            logging.info(f"[{self.journal.code}] Navigated to manuscripts dashboard")
            
        except Exception as e:
            logging.error(f"[{self.journal.code}] Navigation failed: {e}")
            from editorial_assistant.core.exceptions import NavigationError
            raise NavigationError(f"Failed to navigate to manuscripts: {str(e)}")
    
    def _extract_manuscripts(self) -> List:
        """Extract list of manuscripts from the current page."""
        try:
            from editorial_assistant.core.data_models import Manuscript, ManuscriptStatus
            
            # Use existing extract_manuscripts method but convert to Manuscript objects
            manuscripts_data = self.extract_manuscripts()
            manuscripts = []
            
            for ms_data in manuscripts_data:
                manuscript = Manuscript(
                    manuscript_id=ms_data.get("Manuscript #", ""),
                    title=ms_data.get("Title", ""),
                    contact_author=ms_data.get("Contact Author", ""),
                    status=ManuscriptStatus.UNDER_REVIEW,  # Default status
                    submission_date=ms_data.get("Submitted", ""),
                    referees=[]  # Will be populated in _process_manuscript
                )
                manuscripts.append(manuscript)
            
            logging.info(f"[{self.journal.code}] Extracted {len(manuscripts)} manuscripts")
            return manuscripts
            
        except Exception as e:
            logging.error(f"[{self.journal.code}] Manuscript extraction failed: {e}")
            return []
    
    def _process_manuscript(self, manuscript) -> None:
        """Process a single manuscript to extract detailed information."""
        try:
            from editorial_assistant.core.data_models import Referee, RefereeStatus
            
            # Use existing extraction logic to get full manuscript data
            manuscript_links = self._collect_manuscript_links()
            
            # Find the matching manuscript link
            matching_url = None
            for url in manuscript_links:
                if manuscript.manuscript_id in url:
                    matching_url = url
                    break
            
            if not matching_url:
                logging.warning(f"[{self.journal.code}] No URL found for manuscript {manuscript.manuscript_id}")
                return
            
            # Navigate to manuscript details
            self.driver.get(matching_url)
            time.sleep(1.0)
            
            # Extract detailed data
            manuscript_data, email_urls = self._extract_manuscript_table()
            
            if manuscript_data:
                # Update manuscript with detailed information
                manuscript.title = manuscript_data.get("Title", manuscript.title)
                manuscript.current_stage = manuscript_data.get("Current Stage", "")
                
                # Process referees
                for ref_data in manuscript_data.get("Referees", []):
                    referee = Referee(
                        name=ref_data.get("Referee Name", ""),
                        email=ref_data.get("Referee Email", ""),
                        status=RefereeStatus.CONTACTED if ref_data.get("Status") == "Contacted" else RefereeStatus.ACCEPTED,
                        due_date=ref_data.get("Due Date", ""),
                        contacted_date=""
                    )
                    manuscript.referees.append(referee)
            
            logging.info(f"[{self.journal.code}] Processed manuscript {manuscript.manuscript_id}")
            
        except Exception as e:
            logging.error(f"[{self.journal.code}] Error processing manuscript {manuscript.manuscript_id}: {e}")
