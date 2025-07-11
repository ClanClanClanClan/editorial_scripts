import os
import time
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class JournalBase(ABC):
    """
    Abstract base class for all journal scrapers.
    Provides default ORCID login only for SICON/SIFIN;
    other journals MUST override login().
    """

    def __init__(self, driver):
        if driver is None:
            raise ValueError("A Selenium driver must be provided to JournalBase.")
        self.driver = driver
        self.ORCID_EMAIL = os.environ.get("ORCID_EMAIL")
        self.ORCID_PASSWORD = os.environ.get("ORCID_PASSWORD")
        if not (self.ORCID_EMAIL and self.ORCID_PASSWORD):
            logging.warning("ORCID credentials not set. If this journal doesn't use ORCID, this is safe to ignore.")
        
        # Initialize AI analyzer for this journal
        self.journal_name = self._get_journal_name()
        self.ai_analyzer = None  # Will be initialized when needed

    @abstractmethod
    def get_url(self):
        """
        Return the main dashboard or login URL for the journal.
        """
        pass

    def login(self):
        """
        Default login: ORCID workflow with consent/cookie banner removal.
        Only allowed for SICON/SIFIN journals! All others must override.
        """
        # Only allow direct subclasses SICONJournal/SIFINJournal
        allowed = {"SICONJournal", "SIFINJournal"}
        if self.__class__.__name__ not in allowed:
            raise NotImplementedError(
                f"Base ORCID login should NOT be called by {self.__class__.__name__}! "
                "Override login() in your subclass."
            )

        driver = self.driver
        logging.info("Using default ORCID login flow.")
        try:
            orcid_btn = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'orcid')]"))
            )
            orcid_btn.click()
            WebDriverWait(driver, 15).until(
                lambda d: "orcid.org" in d.current_url or d.find_elements(By.ID, "username-input")
            )
            self.remove_orcid_cookie_banner(max_wait=18)

            email_input = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.ID, "username-input"))
            )
            password_input = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.ID, "password"))
            )
            email_input.clear()
            email_input.send_keys(self.ORCID_EMAIL)
            password_input.clear()
            password_input.send_keys(self.ORCID_PASSWORD)

            # Try different selectors for the sign-in button
            conn_btn = None
            try:
                conn_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Sign in to ORCID')]"))
                )
            except:
                try:
                    conn_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(), 'Sign in to ORCID')]]"))
                    )
                except:
                    try:
                        conn_btn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Sign in')]"))
                        )
                    except:
                        conn_btn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.ID, "signin-button"))
                        )
            
            if not conn_btn:
                raise Exception("Could not find ORCID sign-in button")
            
            conn_btn.click()
            self.remove_orcid_cookie_banner(max_wait=7)

            try:
                authorize_btn = WebDriverWait(driver, 7).until(
                    EC.element_to_be_clickable((By.ID, "authorize"))
                )
                authorize_btn.click()
            except Exception:
                pass

            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'logout')]"))
            )
            logging.info("ORCID login successful.")
        except Exception as e:
            logging.error(f"ORCID login failed: {e}")
            raise

    def remove_cookie_banner(self):
        """Remove standard site cookie banners by element ID."""
        driver = self.driver
        for el_id in ["cookie-policy-layer", "cookie-policy-layer-bg"]:
            try:
                driver.execute_script(
                    f"var el = document.getElementById('{el_id}'); if (el) el.remove();"
                )
            except Exception:
                pass

    def remove_orcid_cookie_banner(self, max_wait=18):
        """Remove ORCID cookie/consent overlays if present."""
        driver = self.driver
        cookie_selectors = [
            '//button[contains(translate(., "ACEPTTURL", "aceptturl"), "accept all cookies")]',
            '//button[contains(text(), "Reject Unnecessary Cookies")]',
            '//button[contains(text(), "Reject all")]',
            '//button[contains(text(), "Reject")]',
            '//button[contains(text(), "OK")]',
            '//button[contains(text(), "Continue")]',
            '//button[contains(@id, "onetrust-reject-all-handler")]',
            '//button[contains(@id, "onetrust-accept-btn-handler")]',
        ]
        deadline = time.time() + max_wait
        while time.time() < deadline:
            for sel in cookie_selectors:
                try:
                    btns = driver.find_elements(By.XPATH, sel)
                    for btn in btns:
                        if btn.is_displayed():
                            driver.execute_script("arguments[0].click();", btn)
                except Exception:
                    continue
            overlays = driver.find_elements(
                By.CSS_SELECTOR,
                '#onetrust-banner-sdk, #onetrust-pc-sdk, #cookie-policy-layer, #cookie-policy-layer-bg'
            )
            if not any(ov.is_displayed() for ov in overlays):
                break

    def _get_journal_name(self) -> str:
        """Extract journal name from class name"""
        class_name = self.__class__.__name__
        # Remove 'Journal' suffix if present
        if class_name.endswith('Journal'):
            return class_name[:-7].upper()
        return class_name.upper()

    def _get_ai_analyzer(self):
        """Get or create AI analyzer for this journal"""
        if self.ai_analyzer is None:
            from core.ai_referee_suggestions import get_ai_analyzer
            self.ai_analyzer = get_ai_analyzer(self.journal_name, debug=True)
        return self.ai_analyzer

    def generate_ai_suggestions(self, pdf_path: str, manuscript: Dict) -> Dict:
        """
        Generate AI-powered referee suggestions for a manuscript PDF.
        Available to ALL journals.
        
        Args:
            pdf_path: Path to the downloaded PDF file
            manuscript: Manuscript data dictionary
            
        Returns:
            Dictionary with AI analysis and referee suggestions
        """
        try:
            analyzer = self._get_ai_analyzer()
            return analyzer.analyze_and_suggest(pdf_path, manuscript)
        except Exception as e:
            logging.error(f"[{self.journal_name}] AI suggestion generation failed: {e}")
            return {
                'status': 'error',
                'journal': self.journal_name,
                'error': str(e),
                'suggestions': []
            }

    def download_and_analyze_manuscripts(self, manuscripts: List[Dict]) -> List[Dict]:
        """
        Enhanced manuscript download with AI analysis.
        Downloads papers and generates AI referee suggestions for all manuscripts.
        
        Args:
            manuscripts: List of manuscript dictionaries
            
        Returns:
            List of enhanced manuscript dictionaries with AI suggestions
        """
        try:
            # Import paper downloader
            from core.paper_downloader import get_paper_downloader
            paper_downloader = get_paper_downloader()
            
            enhanced_manuscripts = []
            
            for manuscript in manuscripts:
                enhanced_ms = manuscript.copy()
                enhanced_ms['downloads'] = {
                    'paper': None,
                    'reports': [],
                    'ai_suggestions': None
                }
                
                try:
                    manuscript_id = manuscript.get('Manuscript #', manuscript.get('manuscript_id', ''))
                    title = manuscript.get('Title', manuscript.get('title', ''))
                    
                    if manuscript_id and title:
                        # Try to find and download paper
                        paper_links = paper_downloader.find_paper_links(self.driver, self.journal_name)
                        
                        for link in paper_links:
                            if link['type'] == 'href':
                                paper_path = paper_downloader.download_paper(
                                    manuscript_id, title, link['url'], self.journal_name, self.driver
                                )
                                if paper_path:
                                    enhanced_ms['downloads']['paper'] = str(paper_path)
                                    
                                    # Generate AI suggestions for downloaded PDF
                                    ai_suggestions = self.generate_ai_suggestions(paper_path, manuscript)
                                    if ai_suggestions:
                                        enhanced_ms['downloads']['ai_suggestions'] = ai_suggestions
                                    
                                    break
                        
                        # Try to find referee report links
                        report_links = paper_downloader.find_report_links(self.driver, self.journal_name)
                        
                        for link in report_links:
                            if link['type'] == 'href':
                                report_path = paper_downloader.download_referee_report(
                                    manuscript_id, link['text'], link['url'], self.journal_name, self.driver
                                )
                                if report_path:
                                    enhanced_ms['downloads']['reports'].append(str(report_path))
                
                except Exception as e:
                    logging.error(f"[{self.journal_name}] Error processing manuscript {manuscript_id}: {e}")
                
                enhanced_manuscripts.append(enhanced_ms)
            
            return enhanced_manuscripts
            
        except Exception as e:
            logging.error(f"[{self.journal_name}] Enhanced manuscript processing failed: {e}")
            return manuscripts  # Return original manuscripts if enhancement fails

    @abstractmethod
    def scrape_manuscripts_and_emails(self):
        """
        Must be implemented by each journal subclass.
        Should return a list of manuscript dicts, each with all necessary referee data.
        """
        pass