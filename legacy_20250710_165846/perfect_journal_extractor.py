#!/usr/bin/env python3
"""
Perfect Journal Extractor - Production-ready extractor for MF/MOR with full PDF/data extraction
Features:
- Headless mode support
- Robust retry mechanisms
- Complete PDF and text extraction
- Proper error handling and fallbacks
- Works for both MF and MOR journals
"""

import os
import sys
import time
import logging
import traceback
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import json
import re
from typing import List, Dict, Any, Optional, Tuple
import requests
from urllib.parse import urljoin, urlparse

# Load environment variables
load_dotenv()

# Import selenium components
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from bs4 import BeautifulSoup

# Setup comprehensive logging
def setup_logging(journal: str):
    """Setup comprehensive logging for the journal"""
    log_dir = Path("production_logs")
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"{journal.lower()}_extraction_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(f"PERFECT_{journal}")
    logger.info(f"🚀 Starting perfect {journal} extraction - Log: {log_file}")
    return logger

class PerfectJournalExtractor:
    """Perfect production-ready journal extractor"""
    
    def __init__(self, journal: str, headless: bool = True, max_retries: int = 3):
        self.journal = journal.upper()
        self.headless = headless
        self.max_retries = max_retries
        self.logger = setup_logging(journal)
        self.driver = None
        
        # Setup directories
        self.base_dir = Path(f"perfect_results_{journal.lower()}")
        self.base_dir.mkdir(exist_ok=True)
        self.pdfs_dir = self.base_dir / "pdfs"
        self.pdfs_dir.mkdir(exist_ok=True)
        self.reports_dir = self.base_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        # Journal configurations
        self.journal_configs = {
            "MF": {
                "name": "Mathematical Finance",
                "url": "https://mc.manuscriptcentral.com/mafi",
                "categories": ["Awaiting Reviewer Scores", "Awaiting Final Decision"],
                "user_env": "MF_USER",
                "pass_env": "MF_PASS",
                "email_prefix": "MF"
            },
            "MOR": {
                "name": "Mathematics of Operations Research", 
                "url": "https://mc.manuscriptcentral.com/mathor",
                "categories": ["Awaiting Reviewer Reports", "Awaiting Final Decision"],
                "user_env": "MOR_USER",
                "pass_env": "MOR_PASS",
                "email_prefix": "MOR"
            }
        }
        
        if journal not in self.journal_configs:
            raise ValueError(f"Unsupported journal: {journal}")
        
        self.config = self.journal_configs[journal]
        self.logger.info(f"📋 Configured for {self.config['name']}")
        self.logger.info(f"🖥️  Headless mode: {headless}")
        self.logger.info(f"🔄 Max retries: {max_retries}")
    
    def create_driver_with_retries(self) -> bool:
        """Create Chrome driver with comprehensive retry logic"""
        self.logger.info("🚀 Creating Chrome driver with retry fallbacks")
        
        # Multiple driver creation strategies
        strategies = [
            {"name": "undetected_chrome_default", "version": None, "extra_args": []},
            {"name": "undetected_chrome_126", "version": 126, "extra_args": ["--disable-extensions"]},
            {"name": "undetected_chrome_stable", "version": None, "extra_args": ["--disable-gpu", "--disable-software-rasterizer"]},
            {"name": "undetected_chrome_compatibility", "version": 125, "extra_args": ["--no-first-run", "--disable-default-apps"]}
        ]
        
        for attempt, strategy in enumerate(strategies, 1):
            try:
                self.logger.info(f"   Attempt {attempt}/{len(strategies)}: {strategy['name']}")
                
                options = uc.ChromeOptions()
                
                # Essential arguments
                essential_args = [
                    '--no-sandbox',
                    '--disable-dev-shm-usage', 
                    '--window-size=1920,1080',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--allow-running-insecure-content',
                    '--disable-background-timer-throttling',
                    '--disable-renderer-backgrounding',
                    '--disable-backgrounding-occluded-windows'
                ]
                
                # Add headless mode if requested
                if self.headless:
                    essential_args.extend([
                        '--headless=new',  # Use new headless mode
                        '--disable-gpu',
                        '--no-first-run',
                        '--disable-default-apps'
                    ])
                
                # Add strategy-specific arguments
                all_args = essential_args + strategy['extra_args']
                
                for arg in all_args:
                    options.add_argument(arg)
                
                # Set additional options for stability
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                
                # Create driver
                self.driver = uc.Chrome(
                    options=options, 
                    version_main=strategy['version'],
                    driver_executable_path=None
                )
                
                # Test driver with simple navigation
                self.driver.get("https://www.google.com")
                time.sleep(2)
                
                self.logger.info(f"✅ Driver created successfully: {strategy['name']}")
                return True
                
            except Exception as e:
                self.logger.warning(f"   ❌ Strategy {strategy['name']} failed: {str(e)[:100]}...")
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
                continue
        
        self.logger.error("❌ All driver creation strategies failed")
        return False
    
    def robust_login(self) -> bool:
        """Login with comprehensive error handling and retries"""
        self.logger.info(f"🔐 Logging into {self.journal}")
        
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"   Login attempt {attempt + 1}/{self.max_retries}")
                
                # Navigate to journal
                self.logger.info(f"   Navigating to: {self.config['url']}")
                self.driver.get(self.config['url'])
                time.sleep(3)
                
                # Handle cookies with retries
                self._handle_cookies()
                
                # Get credentials with fallbacks
                user, password = self._get_credentials()
                
                # Fill login form with waits
                self._fill_login_form(user, password)
                
                # Handle verification if needed
                self._handle_verification()
                
                # Verify successful login
                if self._verify_login():
                    self.logger.info("✅ Login successful")
                    return True
                else:
                    self.logger.warning(f"   Login verification failed on attempt {attempt + 1}")
                    
            except Exception as e:
                self.logger.error(f"   Login attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    self.logger.info(f"   Retrying in 5 seconds...")
                    time.sleep(5)
                continue
        
        self.logger.error("❌ All login attempts failed")
        return False
    
    def _handle_cookies(self):
        """Handle cookie consent banners"""
        try:
            # Try multiple cookie button selectors
            cookie_selectors = [
                "onetrust-accept-btn-handler",
                "onetrust-close-btn-container", 
                "accept-cookies",
                "cookie-accept"
            ]
            
            for selector in cookie_selectors:
                try:
                    accept_btn = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.ID, selector))
                    )
                    if accept_btn.is_displayed():
                        accept_btn.click()
                        self.logger.info(f"   Accepted cookies via {selector}")
                        time.sleep(1)
                        return
                except TimeoutException:
                    continue
                    
        except Exception as e:
            self.logger.debug(f"   Cookie handling: {e}")
    
    def _get_credentials(self) -> Tuple[str, str]:
        """Get login credentials with fallbacks"""
        # Try journal-specific credentials first
        user = os.environ.get(self.config['user_env'])
        password = os.environ.get(self.config['pass_env'])
        
        # Fallback to MF credentials if MOR not set
        if not user or not password:
            user = user or os.environ.get("MF_USER")
            password = password or os.environ.get("MF_PASS")
        
        if not user or not password:
            raise RuntimeError(f"Credentials not found. Set {self.config['user_env']}/{self.config['pass_env']} or MF_USER/MF_PASS")
        
        self.logger.info(f"   Using credentials for user: {user[:3]}***")
        return user, password
    
    def _fill_login_form(self, user: str, password: str):
        """Fill login form with robust element waiting"""
        # Wait for and fill username
        user_box = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "USERID"))
        )
        user_box.clear()
        user_box.send_keys(user)
        
        # Wait for and fill password
        pw_box = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "PASSWORD"))
        )
        pw_box.clear() 
        pw_box.send_keys(password)
        
        # Submit login
        login_btn = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "logInButton"))
        )
        login_btn.click()
        time.sleep(4)
        self.logger.info("   Login form submitted")
    
    def _handle_verification(self):
        """Handle 2FA verification with email fetching"""
        try:
            code_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "TOKEN_VALUE"))
            )
            
            if code_input.is_displayed():
                self.logger.info("   2FA verification required")
                
                # Import email utilities
                sys.path.insert(0, str(Path(__file__).parent))
                from core.email_utils import fetch_latest_verification_code
                
                # Wait for email to arrive
                time.sleep(5)
                verification_code = fetch_latest_verification_code(journal=self.journal)
                
                if verification_code:
                    code_input.clear()
                    code_input.send_keys(verification_code)
                    code_input.send_keys(Keys.RETURN)
                    time.sleep(3)
                    self.logger.info(f"   Verification code submitted: {verification_code}")
                else:
                    self.logger.warning("   No verification code received")
                    
        except TimeoutException:
            self.logger.debug("   No verification required")
        except Exception as e:
            self.logger.warning(f"   Verification handling error: {e}")
    
    def _verify_login(self) -> bool:
        """Verify that login was successful"""
        try:
            current_url = self.driver.current_url
            expected_domain = self.config['url'].split('/')[2]
            
            if expected_domain in current_url:
                self.logger.info(f"   Login verified - URL: {current_url}")
                return True
            else:
                self.logger.warning(f"   Unexpected URL after login: {current_url}")
                return False
                
        except Exception as e:
            self.logger.error(f"   Login verification error: {e}")
            return False
    
    def navigate_to_manuscripts_with_retries(self) -> bool:
        """Navigate to manuscript categories with retries"""
        self.logger.info("🧭 Navigating to manuscript categories")
        
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"   Navigation attempt {attempt + 1}/{self.max_retries}")
                
                # Navigate to Associate Editor Center
                ae_link = WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
                )
                ae_link.click()
                time.sleep(3)
                self.logger.info("   ✅ Reached Associate Editor Center")
                
                # Try each category until we find manuscripts
                for category in self.config['categories']:
                    try:
                        self.logger.info(f"   Trying category: {category}")
                        category_link = self.driver.find_element(By.LINK_TEXT, category)
                        category_link.click()
                        time.sleep(3)
                        
                        # Check if we found manuscripts
                        manuscripts = self._find_manuscripts_on_page()
                        if manuscripts:
                            self.logger.info(f"   ✅ Found {len(manuscripts)} manuscripts in {category}")
                            return True
                        else:
                            self.logger.info(f"   No manuscripts in {category}")
                            
                    except NoSuchElementException:
                        self.logger.info(f"   Category '{category}' not found")
                        continue
                
                self.logger.warning(f"   No manuscripts found in any category on attempt {attempt + 1}")
                
            except Exception as e:
                self.logger.error(f"   Navigation attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(5)
                continue
        
        self.logger.error("❌ All navigation attempts failed")
        return False
    
    def _find_manuscripts_on_page(self) -> List[str]:
        """Find manuscripts on current page"""
        try:
            manuscripts = []
            rows = self.driver.find_elements(By.TAG_NAME, "tr")
            
            patterns = [
                r'MAFI-\d{4}-\d{4}',  # MF pattern
                r'MOR-\d{4}-\d{4}',   # MOR pattern
                r'MATHOR-\d{4}-\d{4}' # Alternative MOR pattern
            ]
            
            for row in rows:
                try:
                    row_text = row.text.strip()
                    for pattern in patterns:
                        matches = re.findall(pattern, row_text)
                        manuscripts.extend(matches)
                except:
                    continue
            
            # Remove duplicates while preserving order
            unique_manuscripts = []
            seen = set()
            for ms in manuscripts:
                if ms not in seen:
                    unique_manuscripts.append(ms)
                    seen.add(ms)
            
            return unique_manuscripts
            
        except Exception as e:
            self.logger.error(f"Error finding manuscripts: {e}")
            return []
    
    def extract_complete_manuscript_data(self, manuscript_id: str) -> Dict[str, Any]:
        """Extract complete data for a manuscript with retries"""
        self.logger.info(f"📊 Extracting complete data for {manuscript_id}")
        
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"   Extraction attempt {attempt + 1}/{self.max_retries}")
                
                # Click manuscript checkbox
                if self._click_manuscript_checkbox_with_retries(manuscript_id):
                    
                    # Extract referee data
                    referees = self._extract_referees_with_improved_parsing()
                    
                    # Extract PDFs and reports
                    pdf_info = self._extract_all_pdfs_and_reports(manuscript_id)
                    
                    # Extract manuscript metadata
                    manuscript_meta = self._extract_manuscript_metadata()
                    
                    result = {
                        'manuscript_id': manuscript_id,
                        'title': manuscript_meta.get('title', ''),
                        'submitted_date': manuscript_meta.get('submitted_date', ''),
                        'due_date': manuscript_meta.get('due_date', ''),
                        'status': manuscript_meta.get('status', ''),
                        'authors': manuscript_meta.get('authors', ''),
                        'abstract': manuscript_meta.get('abstract', ''),
                        'keywords': manuscript_meta.get('keywords', ''),
                        'referees': referees,
                        'pdf_info': pdf_info,
                        'extraction_status': 'success',
                        'extraction_time': datetime.now().isoformat()
                    }
                    
                    self.logger.info(f"   ✅ Successfully extracted data for {manuscript_id}")
                    self.logger.info(f"      Referees: {len(referees)}")
                    self.logger.info(f"      Manuscript PDF: {bool(pdf_info.get('manuscript_pdf_file'))}")
                    self.logger.info(f"      Referee reports: {len(pdf_info.get('referee_reports', []))}")
                    self.logger.info(f"      Text reviews: {len(pdf_info.get('text_reviews', []))}")
                    
                    return result
                else:
                    self.logger.warning(f"   Could not click checkbox for {manuscript_id} on attempt {attempt + 1}")
                    
            except Exception as e:
                self.logger.error(f"   Extraction attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(3)
                continue
        
        self.logger.error(f"❌ All extraction attempts failed for {manuscript_id}")
        return {
            'manuscript_id': manuscript_id,
            'extraction_status': 'failed',
            'error': 'All extraction attempts failed',
            'extraction_time': datetime.now().isoformat()
        }
    
    def _click_manuscript_checkbox_with_retries(self, manuscript_id: str) -> bool:
        """Click manuscript checkbox with comprehensive retry logic"""
        for attempt in range(self.max_retries):
            try:
                checkboxes = self.driver.find_elements(By.XPATH, "//img[contains(@src, 'check_off.gif')]")
                rows = self.driver.find_elements(By.TAG_NAME, "tr")
                
                for i, row in enumerate(rows):
                    try:
                        row_text = row.text.strip()
                        if row_text.startswith(manuscript_id):
                            row_checkboxes = row.find_elements(By.XPATH, ".//img[contains(@src, 'check_off.gif')]")
                            if row_checkboxes:
                                checkbox = row_checkboxes[0]
                                
                                # Scroll into view and click
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                                time.sleep(0.5)
                                
                                # Try multiple click methods
                                click_methods = [
                                    lambda: checkbox.click(),
                                    lambda: self.driver.execute_script("arguments[0].click();", checkbox),
                                    lambda: self.driver.execute_script("arguments[0].dispatchEvent(new Event('click'));", checkbox)
                                ]
                                
                                for method in click_methods:
                                    try:
                                        method()
                                        time.sleep(2)
                                        self.logger.info(f"   ✅ Clicked checkbox for {manuscript_id} in row {i}")
                                        return True
                                    except:
                                        continue
                    except:
                        continue
                        
                self.logger.warning(f"   Could not find/click checkbox for {manuscript_id} on attempt {attempt + 1}")
                time.sleep(2)
                
            except Exception as e:
                self.logger.error(f"   Checkbox click attempt {attempt + 1} failed: {e}")
                time.sleep(2)
                continue
        
        return False
    
    def _extract_referees_with_improved_parsing(self) -> List[Dict[str, Any]]:
        """Extract referees with improved HTML parsing"""
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find reviewer list section with multiple strategies
            reviewer_section = None
            search_texts = ['reviewer list', 'reviewers', 'referee list', 'referees']
            
            for search_text in search_texts:
                for elem in soup.find_all(['div', 'table', 'tr', 'td', 'span']):
                    if elem.get_text() and search_text in elem.get_text().lower():
                        reviewer_section = elem
                        break
                if reviewer_section:
                    break
            
            if not reviewer_section:
                self.logger.warning("   Could not find reviewer section")
                return []
            
            self.logger.info("   ✅ Found reviewer section")
            
            # Extract referees from table
            referees = []
            table = reviewer_section.find_parent('table') or soup.find('table')
            
            if table:
                rows = table.find_all('tr')
                self.logger.info(f"   Processing {len(rows)} table rows")
                
                for row in rows:
                    referee_data = self._extract_referee_from_row_improved(row)
                    if referee_data:
                        referees.append(referee_data)
                        self.logger.info(f"      ✅ {referee_data['name']} ({referee_data['status']})")
            
            return referees
            
        except Exception as e:
            self.logger.error(f"   Error extracting referees: {e}")
            return []
    
    def _extract_referee_from_row_improved(self, row) -> Optional[Dict[str, Any]]:
        """Improved referee extraction from table row"""
        try:
            row_text = row.get_text(strip=True)
            if not row_text or len(row_text) < 10:
                return None
            
            # Skip header rows
            skip_keywords = ['name', 'status', 'history', 'order', 'remove', 'reviewer list']
            if any(keyword in row_text.lower() for keyword in skip_keywords):
                return None
            
            # Enhanced name extraction patterns
            name_patterns = [
                # Pattern 1: Last, First followed by institution/uppercase
                r'^([A-Za-z\-\'\s]+,\s*[A-Za-z\-\'\s]+?)(?=\s+[A-Z][a-z]|University|College|Institute|School|Department)',
                # Pattern 2: Last, First followed by (R0) or similar
                r'([A-Za-z\-\'\s]+,\s*[A-Za-z\-\'\s]+)(?:\s*\([R0-9]+\))',
                # Pattern 3: Last, First followed by multiple capitals (institution abbreviation)
                r'^([A-Za-z\-\'\s]+,\s*[A-Za-z\-\'\s]+?)(?=\s+[A-Z]{2,})',
                # Pattern 4: Standard Last, First format
                r'^([A-Za-z\-\'\s]+,\s*[A-Za-z\-\'\s]+)',
                # Pattern 5: Any Last, First in the text
                r'([A-Za-z\-\'\s]+,\s*[A-Za-z\-\'\s]+)'
            ]
            
            referee_name = None
            for pattern in name_patterns:
                match = re.search(pattern, row_text)
                if match:
                    referee_name = match.group(1).strip()
                    # Validate name (should have comma and reasonable length)
                    if ',' in referee_name and 3 <= len(referee_name) <= 50:
                        break
                    referee_name = None
            
            if not referee_name or referee_name in ['reasons, your', ', ']:
                return None
            
            # Extract institution
            institution = ""
            name_end = row_text.find(referee_name) + len(referee_name)
            remaining_text = row_text[name_end:].strip()
            
            # Find where status keywords start
            status_keywords = ['agreed', 'declined', 'invited', 'completed', 'pending', 'due date', 'time in review']
            status_pos = float('inf')
            for keyword in status_keywords:
                pos = remaining_text.lower().find(keyword)
                if pos != -1 and pos < status_pos:
                    status_pos = pos
            
            if status_pos != float('inf'):
                institution = remaining_text[:status_pos].strip()
                # Clean institution text
                institution = re.sub(r'^[^\w]*', '', institution)
                institution = re.sub(r'\s+', ' ', institution).strip()
            
            # Extract status with more patterns
            status = "Unknown"
            status_text = remaining_text.lower()
            if 'agreed' in status_text:
                status = "Agreed"
            elif 'declined' in status_text:
                status = "Declined"
            elif 'completed' in status_text:
                status = "Completed"
            elif 'pending' in status_text:
                status = "Pending"
            elif 'invited' in status_text and 'agreed' not in status_text:
                status = "Invited"
            
            # Extract dates
            dates = self._extract_dates_from_text_improved(row_text)
            
            # Calculate time in review
            time_in_review = self._calculate_time_in_review(dates.get('invited', ''))
            
            return {
                'name': referee_name,
                'institution': institution,
                'email': '',
                'status': status,
                'dates': dates,
                'time_in_review': time_in_review,
                'report_submitted': status.lower() in ['completed', 'submitted'],
                'submission_date': '',
                'review_decision': '',
                'report_url': '',
                'acceptance_date': '',
                'raw_text': row_text  # For debugging
            }
            
        except Exception as e:
            self.logger.debug(f"   Error parsing referee row: {e}")
            return None
    
    def _extract_dates_from_text_improved(self, text: str) -> Dict[str, str]:
        """Improved date extraction from text"""
        dates = {'invited': '', 'agreed': '', 'due': ''}
        
        # Enhanced date patterns
        date_patterns = [
            (r'invited[:\s]*(\d{1,2}-[A-Za-z]{3}-\d{4})', 'invited'),
            (r'agreed[:\s]*(\d{1,2}-[A-Za-z]{3}-\d{4})', 'agreed'),
            (r'due date[:\s]*(\d{1,2}-[A-Za-z]{3}-\d{4})', 'due'),
            (r'due[:\s]*(\d{1,2}-[A-Za-z]{3}-\d{4})', 'due'),
            # Alternative formats
            (r'invited[:\s]*(\d{1,2}/\d{1,2}/\d{4})', 'invited'),
            (r'agreed[:\s]*(\d{1,2}/\d{1,2}/\d{4})', 'agreed'),
            (r'due[:\s]*(\d{1,2}/\d{1,2}/\d{4})', 'due')
        ]
        
        for pattern, date_type in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and not dates[date_type]:  # Don't overwrite if already found
                dates[date_type] = match.group(1)
        
        return dates
    
    def _calculate_time_in_review(self, invited_date: str) -> str:
        """Calculate time in review from invited date"""
        if not invited_date:
            return ""
        
        try:
            # Handle different date formats
            date_formats = ["%d-%b-%Y", "%d/%m/%Y", "%m/%d/%Y"]
            invited = None
            
            for fmt in date_formats:
                try:
                    invited = datetime.strptime(invited_date, fmt)
                    break
                except ValueError:
                    continue
            
            if invited:
                now = datetime.now()
                delta = now - invited
                return f"{delta.days} Days"
        except:
            pass
        
        return ""
    
    def _extract_manuscript_metadata(self) -> Dict[str, str]:
        """Extract manuscript metadata from page"""
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            metadata = {
                'title': '',
                'submitted_date': '',
                'due_date': '',
                'status': '',
                'authors': '',
                'abstract': '',
                'keywords': ''
            }
            
            # Extract title - look for long text that looks like a title
            text_elements = soup.find_all(['span', 'div', 'td', 'p'])
            for elem in text_elements:
                text = elem.get_text(strip=True)
                if len(text) > 30 and len(text) < 200 and ':' not in text[:20]:
                    # Looks like a title
                    if not metadata['title'] or len(text) > len(metadata['title']):
                        metadata['title'] = text
            
            # Extract dates from page text
            page_text = soup.get_text()
            date_patterns = [
                (r'submitted[:\s]*(\d{1,2}-[A-Za-z]{3}-\d{4})', 'submitted_date'),
                (r'due[:\s]*(\d{1,2}-[A-Za-z]{3}-\d{4})', 'due_date')
            ]
            
            for pattern, field in date_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    metadata[field] = match.group(1)
            
            return metadata
            
        except Exception as e:
            self.logger.debug(f"   Error extracting manuscript metadata: {e}")
            return {}
    
    def _extract_all_pdfs_and_reports(self, manuscript_id: str) -> Dict[str, Any]:
        """Extract all PDFs and reports with comprehensive coverage"""
        self.logger.info(f"   📥 Extracting all PDFs and reports for {manuscript_id}")
        
        pdf_info = {
            'manuscript_pdf_url': '',
            'manuscript_pdf_file': '',
            'referee_reports': [],
            'additional_files': [],
            'text_reviews': []
        }
        
        try:
            # 1. Get manuscript PDF
            manuscript_pdf = self._get_manuscript_pdf_robust(manuscript_id)
            if manuscript_pdf:
                pdf_info['manuscript_pdf_url'] = manuscript_pdf['url']
                pdf_info['manuscript_pdf_file'] = manuscript_pdf['file']
                self.logger.info(f"      ✅ Manuscript PDF: {manuscript_pdf['file']}")
            
            # 2. Get all referee reports and text reviews
            referee_data = self._get_all_referee_reports_robust(manuscript_id)
            pdf_info['referee_reports'] = referee_data['pdf_reports']
            pdf_info['text_reviews'] = referee_data['text_reviews']
            pdf_info['additional_files'] = referee_data['additional_files']
            
            self.logger.info(f"      ✅ Found {len(pdf_info['referee_reports'])} PDF reports")
            self.logger.info(f"      ✅ Found {len(pdf_info['text_reviews'])} text reviews")
            self.logger.info(f"      ✅ Found {len(pdf_info['additional_files'])} additional files")
            
            # Save detailed PDF metadata
            pdf_metadata_file = self.pdfs_dir / f"{manuscript_id}_complete_metadata.json"
            with open(pdf_metadata_file, 'w') as f:
                json.dump(pdf_info, f, indent=2)
            
            return pdf_info
            
        except Exception as e:
            self.logger.error(f"      ❌ Error extracting PDFs for {manuscript_id}: {e}")
            return pdf_info
    
    def _get_manuscript_pdf_robust(self, manuscript_id: str) -> Optional[Dict[str, str]]:
        """Get manuscript PDF with robust tab handling"""
        self.logger.info(f"      🔍 Looking for manuscript PDF tabs")
        
        try:
            original_windows = self.driver.window_handles
            
            # Try each tab type
            tab_types = ['PDF', 'Original Files', 'HTML', 'Submission Files']
            
            for tab_name in tab_types:
                try:
                    # Find tab links with flexible matching
                    tab_selectors = [
                        f"//a[contains(text(), '{tab_name}')]",
                        f"//a[contains(text(), '{tab_name.lower()}')]",
                        f"//span[contains(text(), '{tab_name}')]/parent::a",
                        f"//*[contains(text(), '{tab_name}') and (self::a or parent::a)]"
                    ]
                    
                    for selector in tab_selectors:
                        tab_links = self.driver.find_elements(By.XPATH, selector)
                        
                        for tab_link in tab_links:
                            try:
                                link_text = tab_link.text.strip()
                                if len(link_text) > 20:  # Skip long text that's not a tab
                                    continue
                                
                                self.logger.info(f"         Trying {tab_name} tab: '{link_text}'")
                                
                                # Click tab with multiple methods
                                clicked = False
                                for click_method in [
                                    lambda: tab_link.click(),
                                    lambda: self.driver.execute_script("arguments[0].click();", tab_link),
                                    lambda: self.driver.execute_script("arguments[0].dispatchEvent(new Event('click'));", tab_link)
                                ]:
                                    try:
                                        click_method()
                                        time.sleep(2)
                                        clicked = True
                                        break
                                    except:
                                        continue
                                
                                if not clicked:
                                    continue
                                
                                # Check for new window
                                new_windows = self.driver.window_handles
                                if len(new_windows) > len(original_windows):
                                    new_window = [w for w in new_windows if w not in original_windows][0]
                                    self.driver.switch_to.window(new_window)
                                    
                                    current_url = self.driver.current_url
                                    self.logger.info(f"         {tab_name} window URL: {current_url[:100]}...")
                                    
                                    # Try to download
                                    if '.pdf' in current_url.lower() or 'DOWNLOAD=TRUE' in current_url:
                                        pdf_file = self._download_pdf_robust(
                                            current_url,
                                            self.pdfs_dir / f"{manuscript_id}_manuscript.pdf"
                                        )
                                        
                                        # Close window and return
                                        self.driver.close()
                                        self.driver.switch_to.window(original_windows[0])
                                        
                                        if pdf_file:
                                            return {'url': current_url, 'file': pdf_file}
                                    else:
                                        # Look for PDF links in the new window
                                        pdf_links = self.driver.find_elements(By.XPATH, 
                                            "//a[contains(@href, '.pdf') or contains(@href, 'DOWNLOAD=TRUE')]")
                                        
                                        for pdf_link in pdf_links:
                                            href = pdf_link.get_attribute('href')
                                            if href and ('.pdf' in href.lower() or 'DOWNLOAD=TRUE' in href):
                                                pdf_file = self._download_pdf_robust(
                                                    href,
                                                    self.pdfs_dir / f"{manuscript_id}_manuscript.pdf"
                                                )
                                                
                                                self.driver.close()
                                                self.driver.switch_to.window(original_windows[0])
                                                
                                                if pdf_file:
                                                    return {'url': href, 'file': pdf_file}
                                    
                                    # Close window if no PDF found
                                    self.driver.close()
                                    self.driver.switch_to.window(original_windows[0])
                                
                            except Exception as e:
                                self.logger.debug(f"         Error with {tab_name} tab: {e}")
                                # Ensure we're back on original window
                                try:
                                    if len(self.driver.window_handles) > 1:
                                        self.driver.switch_to.window(original_windows[0])
                                except:
                                    pass
                                continue
                except Exception as e:
                    self.logger.debug(f"      Error finding {tab_name} tabs: {e}")
                    continue
            
            self.logger.warning(f"      ❌ No manuscript PDF found in any tab")
            return None
            
        except Exception as e:
            self.logger.error(f"      ❌ Error getting manuscript PDF: {e}")
            return None
    
    def _get_all_referee_reports_robust(self, manuscript_id: str) -> Dict[str, List]:
        """Get all referee reports with comprehensive extraction"""
        self.logger.info(f"      🔍 Looking for all referee reports")
        
        reports = {
            'pdf_reports': [],
            'text_reviews': [],
            'additional_files': []
        }
        
        try:
            # Find all "view review" links with flexible selectors
            review_selectors = [
                "//a[contains(text(), 'view review')]",
                "//a[contains(text(), 'View Review')]", 
                "//a[contains(text(), 'review')]",
                "//a[contains(@href, 'review')]",
                "//a[contains(@onclick, 'review')]"
            ]
            
            view_review_links = []
            for selector in review_selectors:
                links = self.driver.find_elements(By.XPATH, selector)
                view_review_links.extend(links)
            
            # Remove duplicates
            unique_links = []
            seen_hrefs = set()
            for link in view_review_links:
                href = link.get_attribute('href') or link.get_attribute('onclick') or ''
                if href and href not in seen_hrefs:
                    unique_links.append(link)
                    seen_hrefs.add(href)
            
            self.logger.info(f"         Found {len(unique_links)} unique review links")
            
            original_windows = self.driver.window_handles
            
            for i, review_link in enumerate(unique_links):
                try:
                    self.logger.info(f"         📝 Processing review link {i+1}/{len(unique_links)}")
                    
                    # Handle any overlaying elements
                    self._dismiss_overlays()
                    
                    # Try multiple click methods
                    clicked = False
                    for click_method in [
                        lambda: self.driver.execute_script("arguments[0].scrollIntoView(true); arguments[0].click();", review_link),
                        lambda: self.driver.execute_script("arguments[0].click();", review_link),
                        lambda: review_link.click()
                    ]:
                        try:
                            click_method()
                            time.sleep(3)
                            clicked = True
                            break
                        except Exception as e:
                            self.logger.debug(f"            Click method failed: {e}")
                            continue
                    
                    if not clicked:
                        self.logger.warning(f"            Could not click review link {i+1}")
                        continue
                    
                    # Check for new window
                    new_windows = self.driver.window_handles
                    if len(new_windows) > len(original_windows):
                        new_window = [w for w in new_windows if w not in original_windows][0]
                        self.driver.switch_to.window(new_window)
                        self.logger.info(f"            ✅ Opened review window {i+1}")
                        
                        # Extract comprehensive review data
                        review_data = self._extract_comprehensive_review_data(manuscript_id, i+1)
                        
                        # Add to appropriate lists
                        if review_data['pdf_files']:
                            reports['pdf_reports'].extend(review_data['pdf_files'])
                        
                        if review_data['text_content']:
                            reports['text_reviews'].append({
                                'referee_number': i+1,
                                'content': review_data['text_content'],
                                'extraction_time': datetime.now().isoformat(),
                                'content_length': len(review_data['text_content'])
                            })
                        
                        if review_data['additional_files']:
                            reports['additional_files'].extend(review_data['additional_files'])
                        
                        # Close review window
                        self.driver.close()
                        self.driver.switch_to.window(original_windows[0])
                        time.sleep(1)
                    
                except Exception as e:
                    self.logger.error(f"            Error processing review link {i+1}: {e}")
                    # Ensure we're back on original window
                    try:
                        if len(self.driver.window_handles) > 1:
                            self.driver.switch_to.window(original_windows[0])
                    except:
                        pass
                    continue
            
            return reports
            
        except Exception as e:
            self.logger.error(f"      ❌ Error getting referee reports: {e}")
            return reports
    
    def _dismiss_overlays(self):
        """Dismiss any overlay elements that might interfere with clicking"""
        try:
            overlay_selectors = [
                "#onetrust-close-btn-container",
                "#onetrust-accept-btn-handler",
                ".cookie-banner button",
                ".modal-close",
                ".overlay-close"
            ]
            
            for selector in overlay_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if elem.is_displayed():
                            elem.click()
                            time.sleep(0.5)
                except:
                    continue
        except:
            pass
    
    def _extract_comprehensive_review_data(self, manuscript_id: str, referee_num: int) -> Dict[str, Any]:
        """Extract comprehensive review data including PDFs, text, and files"""
        self.logger.info(f"            🔍 Extracting comprehensive review data for referee {referee_num}")
        
        result = {
            'pdf_files': [],
            'text_content': '',
            'additional_files': []
        }
        
        try:
            # 1. Look for all file attachments (PDFs and others)
            file_selectors = [
                "//a[contains(@href, '.pdf')]",
                "//a[contains(text(), 'attached') or contains(text(), 'attachment')]",
                "//a[contains(text(), 'file') or contains(text(), 'download')]",
                "//a[contains(text(), 'report')]",
                "//*[contains(text(), 'Files attached')]/following-sibling::*//a",
                "//*[contains(text(), 'Attachments')]/following-sibling::*//a"
            ]
            
            all_file_links = []
            for selector in file_selectors:
                try:
                    links = self.driver.find_elements(By.XPATH, selector)
                    all_file_links.extend(links)
                except:
                    continue
            
            # Process file links
            for file_link in all_file_links:
                try:
                    href = file_link.get_attribute('href')
                    link_text = file_link.text.strip()
                    
                    if href and (
                        '.pdf' in href.lower() or 
                        'download' in href.lower() or 
                        'attachment' in href.lower() or
                        'file' in href.lower()
                    ):
                        self.logger.info(f"               Found file: {link_text} -> {href[:50]}...")
                        
                        # Determine file type and naming
                        if '.pdf' in href.lower():
                            filename = f"{manuscript_id}_referee_report_{referee_num}_{link_text[:20]}.pdf"
                            save_path = self.pdfs_dir / filename
                        else:
                            # Extract file extension from URL or link text
                            ext = 'txt'
                            for common_ext in ['.docx', '.doc', '.txt', '.zip']:
                                if common_ext in href.lower():
                                    ext = common_ext[1:]
                                    break
                            filename = f"{manuscript_id}_referee_file_{referee_num}_{link_text[:20]}.{ext}"
                            save_path = self.reports_dir / filename
                        
                        # Download file
                        downloaded_file = self._download_pdf_robust(href, save_path)
                        
                        if downloaded_file:
                            file_info = {
                                'referee_number': referee_num,
                                'url': href,
                                'file': downloaded_file,
                                'link_text': link_text,
                                'file_type': 'pdf' if '.pdf' in href.lower() else 'other',
                                'download_time': datetime.now().isoformat()
                            }
                            
                            if '.pdf' in href.lower():
                                result['pdf_files'].append(file_info)
                                self.logger.info(f"               ✅ Downloaded PDF: {link_text}")
                            else:
                                result['additional_files'].append(file_info)
                                self.logger.info(f"               ✅ Downloaded file: {link_text}")
                
                except Exception as e:
                    self.logger.debug(f"               Error processing file link: {e}")
                    continue
            
            # 2. Extract text content from multiple sources
            text_selectors = [
                "//*[contains(text(), 'Comments to the Author')]//following-sibling::*",
                "//*[contains(text(), 'comments to author')]//following-sibling::*",
                "//*[contains(text(), 'Review')]//textarea",
                "//*[contains(text(), 'Comments')]//following-sibling::*",
                "//textarea",
                "//*[contains(@class, 'review') or contains(@class, 'comment')]",
                "//pre",  # Sometimes review text is in <pre> tags
                "//*[contains(text(), 'Reviewer')]//following-sibling::*"
            ]
            
            all_text_content = []
            
            for selector in text_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        text_content = ""
                        
                        if element.tag_name == 'textarea':
                            text_content = element.get_attribute('value') or element.text
                        elif element.tag_name == 'pre':
                            text_content = element.text
                        else:
                            # For other elements, get text content
                            text_content = element.text.strip()
                        
                        if text_content and len(text_content) > 50:  # Meaningful content
                            # Clean up text
                            text_content = re.sub(r'\s+', ' ', text_content).strip()
                            all_text_content.append({
                                'content': text_content,
                                'source': selector,
                                'length': len(text_content)
                            })
                            self.logger.info(f"               Found text content ({len(text_content)} chars) from: {selector[:50]}...")
                            
                except Exception as e:
                    self.logger.debug(f"               Error with text selector {selector}: {e}")
                    continue
            
            # 3. If no specific content found, capture entire page text as fallback
            if not result['pdf_files'] and not all_text_content:
                try:
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text
                    if len(page_text) > 200:
                        all_text_content.append({
                            'content': page_text,
                            'source': 'full_page_fallback',
                            'length': len(page_text)
                        })
                        self.logger.info(f"               Captured full page text as fallback ({len(page_text)} chars)")
                except Exception as e:
                    self.logger.debug(f"               Could not capture page text: {e}")
            
            # Combine all text content
            if all_text_content:
                # Sort by length (longest first) and combine
                all_text_content.sort(key=lambda x: x['length'], reverse=True)
                combined_text = "\n\n---SECTION---\n\n".join([item['content'] for item in all_text_content])
                result['text_content'] = combined_text
                self.logger.info(f"               ✅ Combined {len(all_text_content)} text sections ({len(combined_text)} total chars)")
            
            return result
            
        except Exception as e:
            self.logger.error(f"            ❌ Error extracting review data: {e}")
            return result
    
    def _download_pdf_robust(self, url: str, filepath: Path) -> Optional[str]:
        """Download file with robust error handling and validation"""
        try:
            # Get cookies from selenium session
            selenium_cookies = self.driver.get_cookies()
            cookies = {cookie['name']: cookie['value'] for cookie in selenium_cookies}
            
            # Set comprehensive headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin'
            }
            
            # Make request with retries
            for attempt in range(3):
                try:
                    self.logger.info(f"            Downloading (attempt {attempt+1}): {url[:80]}...")
                    response = requests.get(url, cookies=cookies, headers=headers, timeout=30, stream=True)
                    
                    if response.status_code == 200:
                        content_type = response.headers.get('content-type', '').lower()
                        is_download_url = 'DOWNLOAD=TRUE' in url
                        
                        # Download file
                        with open(filepath, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        
                        file_size = filepath.stat().st_size
                        
                        # Validate file based on expected type
                        if filepath.suffix.lower() == '.pdf':
                            # Check if it's a valid PDF
                            with open(filepath, 'rb') as f:
                                header = f.read(4)
                                if header.startswith(b'%PDF'):
                                    self.logger.info(f"            ✅ PDF downloaded: {filepath.name} ({file_size} bytes)")
                                    return str(filepath)
                                else:
                                    self.logger.warning(f"            ⚠️  Downloaded file is not a valid PDF")
                                    filepath.unlink()
                                    return None
                        else:
                            # For non-PDF files, just check size
                            if file_size > 100:  # Minimum reasonable file size
                                self.logger.info(f"            ✅ File downloaded: {filepath.name} ({file_size} bytes)")
                                return str(filepath)
                            else:
                                self.logger.warning(f"            ⚠️  Downloaded file too small ({file_size} bytes)")
                                filepath.unlink()
                                return None
                    else:
                        self.logger.warning(f"            ⚠️  HTTP {response.status_code}: {url}")
                        if attempt < 2:
                            time.sleep(2)
                            continue
                        return None
                        
                except requests.exceptions.RequestException as e:
                    self.logger.warning(f"            Request failed (attempt {attempt+1}): {e}")
                    if attempt < 2:
                        time.sleep(2)
                        continue
                    return None
            
            return None
                
        except Exception as e:
            self.logger.error(f"            Download error: {e}")
            return None
    
    def run_perfect_extraction(self) -> bool:
        """Run complete perfect extraction process"""
        self.logger.info(f"🚀 Starting perfect {self.journal} extraction")
        self.logger.info(f"   Headless: {self.headless}, Max retries: {self.max_retries}")
        
        try:
            # Create driver with retries
            if not self.create_driver_with_retries():
                self.logger.error("❌ Failed to create driver")
                return False
            
            # Login with retries
            if not self.robust_login():
                self.logger.error("❌ Failed to login")
                return False
            
            # Navigate to manuscripts with retries
            if not self.navigate_to_manuscripts_with_retries():
                self.logger.error("❌ Failed to navigate to manuscripts")
                return False
            
            # Find all manuscripts
            manuscripts = self._find_manuscripts_on_page()
            if not manuscripts:
                self.logger.warning("⚠️  No manuscripts found")
                return False
            
            self.logger.info(f"📄 Found {len(manuscripts)} manuscripts to process")
            
            # Process each manuscript
            all_results = []
            successful_count = 0
            
            for i, manuscript_id in enumerate(manuscripts[:5], 1):  # Process first 5
                self.logger.info(f"\n{'='*80}")
                self.logger.info(f"📄 Processing manuscript {i}/{min(len(manuscripts), 5)}: {manuscript_id}")
                self.logger.info(f"{'='*80}")
                
                try:
                    result = self.extract_complete_manuscript_data(manuscript_id)
                    all_results.append(result)
                    
                    if result.get('extraction_status') == 'success':
                        successful_count += 1
                        self.logger.info(f"✅ Successfully processed {manuscript_id}")
                    else:
                        self.logger.error(f"❌ Failed to process {manuscript_id}")
                    
                    # Brief pause between manuscripts
                    if i < len(manuscripts):
                        time.sleep(3)
                        
                except Exception as e:
                    self.logger.error(f"❌ Error processing {manuscript_id}: {e}")
                    all_results.append({
                        'manuscript_id': manuscript_id,
                        'extraction_status': 'error',
                        'error': str(e),
                        'extraction_time': datetime.now().isoformat()
                    })
            
            # Generate final results
            final_results = {
                'journal': self.journal,
                'journal_name': self.config['name'],
                'extraction_date': datetime.now().isoformat(),
                'extraction_method': 'perfect_production_extractor',
                'headless_mode': self.headless,
                'max_retries': self.max_retries,
                'total_manuscripts_found': len(manuscripts),
                'total_manuscripts_processed': len(all_results),
                'successful_extractions': successful_count,
                'success_rate': (successful_count / len(all_results) * 100) if all_results else 0,
                'manuscripts': all_results
            }
            
            # Save results
            self._save_final_results(final_results)
            
            self.logger.info(f"\n🎉 Perfect {self.journal} extraction completed!")
            self.logger.info(f"   Processed: {len(all_results)} manuscripts")
            self.logger.info(f"   Successful: {successful_count}")
            self.logger.info(f"   Success rate: {final_results['success_rate']:.1f}%")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Fatal error in extraction: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False
            
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    self.logger.info("🔄 Driver closed")
                except:
                    pass
    
    def _save_final_results(self, results: Dict[str, Any]):
        """Save final results in multiple formats"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON results
        json_file = self.base_dir / f"{self.journal.lower()}_perfect_results_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save human-readable report
        report_file = self.base_dir / f"{self.journal.lower()}_perfect_report_{timestamp}.txt"
        self._generate_detailed_report(results, report_file)
        
        # Save summary
        summary_file = self.base_dir / f"{self.journal.lower()}_summary_{timestamp}.txt"
        self._generate_summary(results, summary_file)
        
        self.logger.info(f"📄 Results saved:")
        self.logger.info(f"   JSON: {json_file}")
        self.logger.info(f"   Report: {report_file}")
        self.logger.info(f"   Summary: {summary_file}")
    
    def _generate_detailed_report(self, results: Dict[str, Any], report_file: Path):
        """Generate detailed human-readable report"""
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("PERFECT JOURNAL EXTRACTION REPORT\n")
                f.write("=" * 80 + "\n\n")
                
                f.write(f"Journal: {results['journal_name']} ({results['journal']})\n")
                f.write(f"Extraction Date: {results['extraction_date']}\n")
                f.write(f"Method: {results['extraction_method']}\n")
                f.write(f"Headless Mode: {results['headless_mode']}\n")
                f.write(f"Max Retries: {results['max_retries']}\n\n")
                
                f.write("SUMMARY:\n")
                f.write("-" * 40 + "\n")
                f.write(f"Total Manuscripts Found: {results['total_manuscripts_found']}\n")
                f.write(f"Total Manuscripts Processed: {results['total_manuscripts_processed']}\n")
                f.write(f"Successful Extractions: {results['successful_extractions']}\n")
                f.write(f"Success Rate: {results['success_rate']:.1f}%\n\n")
                
                # Manuscript details
                f.write("MANUSCRIPT DETAILS:\n")
                f.write("=" * 80 + "\n\n")
                
                for i, manuscript in enumerate(results['manuscripts'], 1):
                    f.write(f"{i}. {manuscript['manuscript_id']}\n")
                    f.write("-" * 60 + "\n")
                    
                    if manuscript.get('extraction_status') == 'success':
                        f.write(f"Status: ✅ SUCCESS\n")
                        f.write(f"Title: {manuscript.get('title', 'N/A')}\n")
                        f.write(f"Submitted: {manuscript.get('submitted_date', 'N/A')}\n")
                        f.write(f"Due: {manuscript.get('due_date', 'N/A')}\n")
                        f.write(f"Authors: {manuscript.get('authors', 'N/A')}\n\n")
                        
                        f.write(f"Referees ({len(manuscript.get('referees', []))}):\n")
                        for referee in manuscript.get('referees', []):
                            f.write(f"  • {referee['name']} ({referee['status']})\n")
                            if referee.get('institution'):
                                f.write(f"    Institution: {referee['institution']}\n")
                            if referee['dates'].get('invited'):
                                f.write(f"    Invited: {referee['dates']['invited']}\n")
                            if referee.get('time_in_review'):
                                f.write(f"    Time in Review: {referee['time_in_review']}\n")
                        f.write("\n")
                        
                        pdf_info = manuscript.get('pdf_info', {})
                        f.write("Files Downloaded:\n")
                        if pdf_info.get('manuscript_pdf_file'):
                            filename = pdf_info['manuscript_pdf_file'].split('/')[-1]
                            f.write(f"  • Manuscript PDF: {filename}\n")
                        
                        for report in pdf_info.get('referee_reports', []):
                            filename = report['file'].split('/')[-1] if report.get('file') else 'N/A'
                            f.write(f"  • Referee Report {report.get('referee_number', '?')}: {filename}\n")
                        
                        for review in pdf_info.get('text_reviews', []):
                            char_count = review.get('content_length', len(review.get('content', '')))
                            f.write(f"  • Text Review {review.get('referee_number', '?')}: {char_count} characters\n")
                        
                        for file_info in pdf_info.get('additional_files', []):
                            filename = file_info['file'].split('/')[-1] if file_info.get('file') else 'N/A'
                            f.write(f"  • Additional File: {filename}\n")
                    
                    else:
                        f.write(f"Status: ❌ FAILED\n")
                        f.write(f"Error: {manuscript.get('error', 'Unknown error')}\n")
                    
                    f.write(f"Extraction Time: {manuscript.get('extraction_time', 'N/A')}\n\n")
                
        except Exception as e:
            self.logger.error(f"Error generating detailed report: {e}")
    
    def _generate_summary(self, results: Dict[str, Any], summary_file: Path):
        """Generate concise summary"""
        try:
            with open(summary_file, 'w') as f:
                f.write(f"PERFECT {results['journal']} EXTRACTION SUMMARY\n")
                f.write("=" * 50 + "\n\n")
                
                f.write(f"Date: {results['extraction_date'][:10]}\n")
                f.write(f"Success Rate: {results['success_rate']:.1f}%\n")
                f.write(f"Manuscripts: {results['successful_extractions']}/{results['total_manuscripts_processed']}\n\n")
                
                total_referees = sum(len(m.get('referees', [])) for m in results['manuscripts'] if m.get('extraction_status') == 'success')
                total_manuscript_pdfs = sum(1 for m in results['manuscripts'] if m.get('pdf_info', {}).get('manuscript_pdf_file'))
                total_referee_reports = sum(len(m.get('pdf_info', {}).get('referee_reports', [])) for m in results['manuscripts'])
                total_text_reviews = sum(len(m.get('pdf_info', {}).get('text_reviews', [])) for m in results['manuscripts'])
                
                f.write("TOTALS:\n")
                f.write(f"Referees Extracted: {total_referees}\n")
                f.write(f"Manuscript PDFs: {total_manuscript_pdfs}\n")
                f.write(f"Referee Report PDFs: {total_referee_reports}\n")
                f.write(f"Text Reviews: {total_text_reviews}\n\n")
                
                f.write("FILES LOCATION:\n")
                f.write(f"PDFs: {self.pdfs_dir}\n")
                f.write(f"Reports: {self.reports_dir}\n")
                
        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")

def main():
    """Main function to run perfect extraction"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Perfect Journal Extractor")
    parser.add_argument("journal", choices=["MF", "MOR"], help="Journal to extract (MF or MOR)")
    parser.add_argument("--headless", action="store_true", default=True, help="Run in headless mode (default: True)")
    parser.add_argument("--visible", action="store_true", help="Run with visible browser (overrides headless)")
    parser.add_argument("--retries", type=int, default=3, help="Max retries per operation (default: 3)")
    
    args = parser.parse_args()
    
    # Handle headless mode
    headless = args.headless and not args.visible
    
    try:
        extractor = PerfectJournalExtractor(
            journal=args.journal,
            headless=headless,
            max_retries=args.retries
        )
        
        success = extractor.run_perfect_extraction()
        
        if success:
            print(f"\n🎉 Perfect {args.journal} extraction completed successfully!")
            sys.exit(0)
        else:
            print(f"\n❌ Perfect {args.journal} extraction failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Extraction interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()