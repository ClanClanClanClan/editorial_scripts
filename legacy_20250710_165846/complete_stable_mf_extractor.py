#!/usr/bin/env python3
"""
Complete Stable MF Extractor - Adds PDF downloads to stable working system
"""

import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import json
import re
from typing import List, Dict, Any, Optional
import requests
from urllib.parse import urljoin, urlparse

# Load environment variables
load_dotenv()

# Import exact same driver approach as working system
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('complete_stable_extraction.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("COMPLETE_STABLE_MF")

class CompleteStableMFExtractor:
    """Complete stable MF extractor with PDF downloads"""
    
    def __init__(self):
        self.driver = None
        self.debug_dir = Path("complete_debug")
        self.debug_dir.mkdir(exist_ok=True)
        self.results_dir = Path("complete_results")
        self.results_dir.mkdir(exist_ok=True)
        self.pdfs_dir = self.results_dir / "pdfs"
        self.pdfs_dir.mkdir(exist_ok=True)
        
        # Expected manuscripts (from working system)
        self.expected_manuscripts = {
            'MAFI-2024-0167': {
                'title': 'Competitive optimal portfolio selection in a non-Markovian financial market',
                'expected_referees': 2
            },
            'MAFI-2025-0166': {
                'title': 'Optimal investment and consumption under forward utilities with relative performance concerns',
                'expected_referees': 2
            }
        }
    
    def create_driver(self, headless=False):
        """Create driver with fallback approaches (proven working)"""
        logger.info("🚀 Creating Chrome driver with fallback approaches")
        
        # Try approach 1: undetected chromedriver (proven working)
        try:
            logger.info("   Attempting undetected chromedriver...")
            options = uc.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            
            if headless:
                options.add_argument('--headless')
            
            self.driver = uc.Chrome(options=options, version_main=None)
            logger.info("✅ Undetected Chrome driver created successfully")
            return True
            
        except Exception as e:
            logger.warning(f"Undetected chromedriver failed: {e}")
            return False
    
    def login_mf(self):
        """Login to MF using exact working system approach"""
        logger.info("🔐 Logging into MF (exact working system approach)")
        
        try:
            # Navigate to MF (exact same URL)
            mf_url = "https://mc.manuscriptcentral.com/mafi"
            logger.info(f"Navigating to MF dashboard: {mf_url}")
            self.driver.get(mf_url)
            time.sleep(2)
            
            # Handle cookies (exact same approach)
            try:
                accept_btn = self.driver.find_element(By.ID, "onetrust-accept-btn-handler")
                if accept_btn.is_displayed():
                    accept_btn.click()
                    logger.info("Accepted cookies.")
                    time.sleep(1)
            except Exception:
                logger.debug("No cookie accept button found.")
            
            # Get credentials (exact same env vars)
            user = os.environ.get("MF_USER")
            pw = os.environ.get("MF_PASS")
            if not user or not pw:
                raise RuntimeError("MF_USER and MF_PASS environment variables must be set.")
            
            # Fill login form (exact same field IDs)
            user_box = self.driver.find_element(By.ID, "USERID")
            pw_box = self.driver.find_element(By.ID, "PASSWORD")
            user_box.clear()
            user_box.send_keys(user)
            pw_box.clear()
            pw_box.send_keys(pw)
            
            # Submit login (exact same button ID)
            login_btn = self.driver.find_element(By.ID, "logInButton")
            login_btn.click()
            time.sleep(4)
            
            # Handle verification (exact same approach as working system)
            wait = WebDriverWait(self.driver, 15)
            code_input = None
            
            try:
                # Check for reCAPTCHA (exact same as working system)
                try:
                    recaptcha_iframe = self.driver.find_element(By.XPATH, "//iframe[contains(@title, 'reCAPTCHA')]")
                    if recaptcha_iframe.is_displayed():
                        self.driver.switch_to.frame(recaptcha_iframe)
                        checkbox = self.driver.find_element(By.ID, "recaptcha-anchor")
                        checkbox.click()
                        self.driver.switch_to.default_content()
                        logger.info("Clicked reCAPTCHA checkbox.")
                        time.sleep(2)
                except Exception:
                    logger.debug("No reCAPTCHA present.")
                
                # Check for verification code (exact same as working system)
                try:
                    code_input = wait.until(
                        lambda d: d.find_element(By.ID, "TOKEN_VALUE") if d.find_element(By.ID, "TOKEN_VALUE").is_displayed() else None
                    )
                    logger.debug("Found and visible: TOKEN_VALUE")
                except TimeoutException:
                    try:
                        code_input = wait.until(
                            lambda d: d.find_element(By.ID, "validationCode") if d.find_element(By.ID, "validationCode").is_displayed() else None
                        )
                        logger.debug("Found and visible: validationCode")
                    except TimeoutException:
                        logger.debug("No visible verification input appeared within 15s.")
                
                if code_input:
                    logger.info("Verification prompt visible. Fetching code from email...")
                    
                    # Import exact same email function
                    sys.path.insert(0, str(Path(__file__).parent))
                    from core.email_utils import fetch_latest_verification_code
                    
                    # Wait and fetch code (exact same timing)
                    logger.info("Waiting 5 seconds for verification email to arrive...")
                    time.sleep(5)
                    
                    verification_code = fetch_latest_verification_code(journal="MF")
                    
                    if verification_code:
                        logger.debug(f"Verification code fetched: '{verification_code}'")
                        code_input.clear()
                        code_input.send_keys(verification_code)
                        code_input.send_keys(Keys.RETURN)
                        logger.info("Submitted verification code.")
                        time.sleep(3)
                    else:
                        logger.error("Failed to fetch verification code from email.")
                        return False
                        
            except Exception as e:
                logger.error(f"Verification handling error: {e}")
                return False
            
            logger.info("Ready to continue navigation after login.")
            return True
            
        except Exception as e:
            logger.error(f"❌ MF login failed: {e}")
            return False
    
    def find_and_download_pdfs(self, manuscript_id: str) -> Dict[str, Any]:
        """Find and download PDFs using specific ScholarOne workflow"""
        logger.info(f"📥 Looking for PDFs for manuscript: {manuscript_id}")
        
        pdf_info = {
            'manuscript_pdf_url': '',
            'manuscript_pdf_file': '',
            'referee_reports': [],
            'additional_files': [],
            'text_reviews': []
        }
        
        try:
            # 1. Get manuscript PDF via "view submission"
            manuscript_pdf = self.get_manuscript_pdf(manuscript_id)
            if manuscript_pdf:
                pdf_info['manuscript_pdf_url'] = manuscript_pdf['url']
                pdf_info['manuscript_pdf_file'] = manuscript_pdf['file']
                logger.info(f"✅ Manuscript PDF: {manuscript_pdf['file']}")
            
            # 2. Get referee reports via "view review" links
            referee_reports = self.get_referee_reports(manuscript_id)
            pdf_info['referee_reports'] = referee_reports['pdf_reports']
            pdf_info['text_reviews'] = referee_reports['text_reviews']
            
            logger.info(f"✅ Found {len(pdf_info['referee_reports'])} PDF reports + {len(pdf_info['text_reviews'])} text reviews")
            
            # Save PDF info metadata
            pdf_metadata_file = self.pdfs_dir / f"{manuscript_id}_pdf_metadata.json"
            with open(pdf_metadata_file, 'w') as f:
                json.dump(pdf_info, f, indent=2)
            
            logger.info(f"📄 PDF metadata saved: {pdf_metadata_file}")
            return pdf_info
            
        except Exception as e:
            logger.error(f"❌ PDF discovery error for {manuscript_id}: {e}")
            return pdf_info
    
    def get_manuscript_pdf(self, manuscript_id: str) -> Optional[Dict[str, str]]:
        """Get manuscript PDF by clicking PDF or Original Files tabs"""
        logger.info(f"🔍 Looking for manuscript PDF tabs for {manuscript_id}")
        
        try:
            # Look for PDF, HTML, Original Files tabs (these appear to be the submission files)
            tab_selectors = [
                "//a[contains(text(), 'pdf') or contains(text(), 'PDF')]",
                "//a[contains(text(), 'original files') or contains(text(), 'Original Files')]",
                "//a[contains(text(), 'html') or contains(text(), 'HTML')]"
            ]
            
            original_windows = self.driver.window_handles
            
            for tab_name in ['PDF', 'Original Files', 'HTML']:
                try:
                    # Look for tab link
                    tab_links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{tab_name}') or contains(text(), '{tab_name.lower()}')]")
                    
                    for tab_link in tab_links:
                        try:
                            # Skip if this link is too long (likely part of content, not a tab)
                            link_text = tab_link.text.strip()
                            if len(link_text) > 20:
                                continue
                                
                            logger.info(f"🔍 Trying {tab_name} tab: '{link_text}'")
                            
                            # Click the tab
                            tab_link.click()
                            time.sleep(2)
                            
                            # Check for new window
                            new_windows = self.driver.window_handles
                            if len(new_windows) > len(original_windows):
                                # Switch to new window
                                new_window = [w for w in new_windows if w not in original_windows][0]
                                self.driver.switch_to.window(new_window)
                                logger.info(f"✅ Opened {tab_name} tab in new window")
                                
                                # Get PDF URL from new window
                                current_url = self.driver.current_url
                                logger.info(f"📄 {tab_name} window URL: {current_url}")
                                
                                # Check if this is a direct PDF or download URL
                                if '.pdf' in current_url.lower() or 'DOWNLOAD=TRUE' in current_url:
                                    pdf_file = self.download_direct_pdf(
                                        current_url, 
                                        self.pdfs_dir / f"{manuscript_id}_manuscript.pdf"
                                    )
                                    
                                    # Close window and return result
                                    self.driver.close()
                                    self.driver.switch_to.window(original_windows[0])
                                    
                                    if pdf_file:
                                        return {'url': current_url, 'file': pdf_file}
                                else:
                                    # Look for PDF links in this window
                                    pdf_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf') or contains(@href, 'DOWNLOAD=TRUE')]")
                                    
                                    for pdf_link in pdf_links:
                                        href = pdf_link.get_attribute('href')
                                        if href and ('.pdf' in href.lower() or 'DOWNLOAD=TRUE' in href):
                                            pdf_file = self.download_direct_pdf(
                                                href,
                                                self.pdfs_dir / f"{manuscript_id}_manuscript.pdf"
                                            )
                                            
                                            # Close window and return result
                                            self.driver.close()
                                            self.driver.switch_to.window(original_windows[0])
                                            
                                            if pdf_file:
                                                return {'url': href, 'file': pdf_file}
                                
                                # Close window if no PDF found
                                self.driver.close()
                                self.driver.switch_to.window(original_windows[0])
                            
                        except Exception as tab_error:
                            logger.warning(f"Error with {tab_name} tab: {tab_error}")
                            # Make sure we're back on original window
                            try:
                                if len(self.driver.window_handles) > 1:
                                    self.driver.switch_to.window(original_windows[0])
                            except:
                                pass
                            continue
                            
                except Exception as selector_error:
                    logger.warning(f"Error finding {tab_name} tab: {selector_error}")
                    continue
            
            logger.warning("❌ No manuscript PDF found in any tab")
            return None
                
        except Exception as e:
            logger.error(f"❌ Error getting manuscript PDF: {e}")
            # Make sure we're back on original window
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return None
    
    def get_referee_reports(self, manuscript_id: str) -> Dict[str, list]:
        """Get referee reports by clicking 'view review' links"""
        logger.info(f"🔍 Looking for referee 'view review' links for {manuscript_id}")
        
        reports = {
            'pdf_reports': [],
            'text_reviews': []
        }
        
        try:
            # Look for "view review" links in Status column
            view_review_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'view review') or contains(text(), 'View Review')]")
            logger.info(f"Found {len(view_review_links)} 'view review' links")
            
            original_windows = self.driver.window_handles
            
            for i, review_link in enumerate(view_review_links):
                try:
                    logger.info(f"📝 Processing review link {i+1}/{len(view_review_links)}")
                    
                    # Click review link
                    review_link.click()
                    time.sleep(2)
                    
                    # Check for new window
                    new_windows = self.driver.window_handles
                    if len(new_windows) > len(original_windows):
                        # Switch to review window
                        new_window = [w for w in new_windows if w not in original_windows][0]
                        self.driver.switch_to.window(new_window)
                        
                        # Look for "Files attached" section
                        pdf_found = False
                        file_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf')]")
                        
                        for file_link in file_links:
                            href = file_link.get_attribute('href')
                            if href and '.pdf' in href.lower():
                                # Download referee report PDF
                                pdf_file = self.download_direct_pdf(
                                    href, 
                                    self.pdfs_dir / f"{manuscript_id}_referee_report_{i+1}.pdf"
                                )
                                if pdf_file:
                                    reports['pdf_reports'].append({
                                        'referee_number': i+1,
                                        'url': href,
                                        'file': pdf_file,
                                        'download_time': datetime.now().isoformat()
                                    })
                                    pdf_found = True
                                    logger.info(f"✅ Downloaded referee report PDF {i+1}")
                        
                        # If no PDF, look for text review in "Comments to the Author"
                        if not pdf_found:
                            try:
                                # Look for comments section
                                comment_elements = self.driver.find_elements(By.XPATH, 
                                    "//*[contains(text(), 'Comments to the Author') or contains(text(), 'comments to author')]")
                                
                                for comment_elem in comment_elements:
                                    # Find associated text content
                                    parent = comment_elem.find_element(By.XPATH, ".//..")
                                    text_content = parent.text.strip()
                                    
                                    if len(text_content) > 50:  # Meaningful review text
                                        reports['text_reviews'].append({
                                            'referee_number': i+1,
                                            'content': text_content,
                                            'extraction_time': datetime.now().isoformat()
                                        })
                                        logger.info(f"✅ Extracted text review {i+1} ({len(text_content)} chars)")
                                        break
                            except Exception as text_error:
                                logger.warning(f"Could not extract text review {i+1}: {text_error}")
                        
                        # Close review window and switch back
                        self.driver.close()
                        self.driver.switch_to.window(original_windows[0])
                        time.sleep(1)
                    
                except Exception as link_error:
                    logger.warning(f"Error processing review link {i+1}: {link_error}")
                    # Make sure we're back on original window
                    try:
                        if len(self.driver.window_handles) > 1:
                            self.driver.switch_to.window(original_windows[0])
                    except:
                        pass
                    continue
            
            return reports
            
        except Exception as e:
            logger.error(f"❌ Error getting referee reports: {e}")
            return reports
    
    def download_pdf(self, url: str, manuscript_id: str, pdf_type: str, link_text: str) -> Optional[str]:
        """Download PDF file"""
        try:
            # Clean filename
            safe_text = re.sub(r'[^\w\s-]', '', link_text).strip()
            safe_text = re.sub(r'[-\s]+', '_', safe_text)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{manuscript_id}_{pdf_type}_{safe_text}_{timestamp}.pdf"
            filepath = self.pdfs_dir / filename
            
            # Check if it's a JavaScript link or direct URL
            if url.startswith('javascript:'):
                # Handle JavaScript popup URLs
                logger.info(f"   Handling JavaScript link: {url[:100]}...")
                
                # Try to click the link to trigger download
                try:
                    # Find the link element and click it
                    link_element = self.driver.find_element(By.XPATH, f"//a[@href='{url}']")
                    
                    # Store current window handles
                    original_windows = self.driver.window_handles
                    
                    # Click the link
                    link_element.click()
                    time.sleep(2)
                    
                    # Check for new windows/tabs
                    new_windows = self.driver.window_handles
                    if len(new_windows) > len(original_windows):
                        # Switch to new window
                        new_window = [w for w in new_windows if w not in original_windows][0]
                        self.driver.switch_to.window(new_window)
                        
                        # Try to get PDF URL from new window
                        new_url = self.driver.current_url
                        if '.pdf' in new_url or 'download' in new_url:
                            # Download from new URL
                            result = self.download_direct_pdf(new_url, filepath)
                            
                            # Close new window and switch back
                            self.driver.close()
                            self.driver.switch_to.window(original_windows[0])
                            
                            return result
                        else:
                            # Close new window and switch back
                            self.driver.close()
                            self.driver.switch_to.window(original_windows[0])
                            logger.warning(f"   New window doesn't contain PDF: {new_url}")
                            return None
                    else:
                        logger.warning("   JavaScript link didn't open new window")
                        return None
                        
                except Exception as e:
                    logger.warning(f"   JavaScript link handling failed: {e}")
                    return None
            
            else:
                # Direct URL download
                return self.download_direct_pdf(url, filepath)
                
        except Exception as e:
            logger.error(f"PDF download error: {e}")
            return None
    
    def download_direct_pdf(self, url: str, filepath: Path) -> Optional[str]:
        """Download PDF from direct URL"""
        try:
            # Get cookies from selenium session
            selenium_cookies = self.driver.get_cookies()
            
            # Convert to requests format
            cookies = {}
            for cookie in selenium_cookies:
                cookies[cookie['name']] = cookie['value']
            
            # Set headers to mimic browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # Make request
            logger.info(f"   Downloading from: {url}")
            response = requests.get(url, cookies=cookies, headers=headers, timeout=30, stream=True)
            
            if response.status_code == 200:
                # Check if it's actually a PDF or if it's a download URL
                content_type = response.headers.get('content-type', '').lower()
                is_download_url = 'DOWNLOAD=TRUE' in url
                
                if 'pdf' in content_type or 'application/pdf' in content_type or is_download_url:
                    # Save file
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    file_size = filepath.stat().st_size
                    
                    # Check if the downloaded file is actually a PDF by reading first few bytes
                    with open(filepath, 'rb') as f:
                        header = f.read(4)
                        if header.startswith(b'%PDF'):
                            logger.info(f"   ✅ PDF downloaded: {filepath.name} ({file_size} bytes)")
                            return str(filepath)
                        else:
                            logger.warning(f"   ⚠️  Downloaded file is not a PDF (header: {header})")
                            filepath.unlink()  # Delete the non-PDF file
                            return None
                else:
                    logger.warning(f"   ⚠️  URL doesn't return PDF content: {content_type}")
                    return None
            else:
                logger.warning(f"   ⚠️  HTTP {response.status_code}: {url}")
                return None
                
        except Exception as e:
            logger.error(f"   ❌ Direct download failed: {e}")
            return None
    
    def extract_complete_manuscript_data(self, manuscript_id: str) -> Dict[str, Any]:
        """Extract complete manuscript data including referee details and PDFs"""
        logger.info(f"📊 Extracting complete data for {manuscript_id}...")
        
        manuscript_data = {
            'manuscript_id': manuscript_id,
            'title': '',
            'submitted_date': '',
            'due_date': '',
            'status': '',
            'authors': '',
            'abstract': '',
            'keywords': '',
            'referees': [],
            'completed_referees': [],
            'pdf_info': {},
            'extraction_status': 'pending'
        }
        
        try:
            # Wait for page to load
            time.sleep(3)
            
            # Get page source and parse with BeautifulSoup
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract basic manuscript info (exact same patterns as stable system)
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', page_source, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
                if 'manuscript' not in title.lower() and len(title) > 10:
                    manuscript_data['title'] = title
                    logger.info(f"📄 Title: {title[:50]}...")
            
            # Extract dates
            submitted_match = re.search(r'Date Submitted[:\s]*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', page_source)
            if submitted_match:
                manuscript_data['submitted_date'] = submitted_match.group(1)
                logger.info(f"📅 Submitted: {manuscript_data['submitted_date']}")
            
            due_match = re.search(r'Due Date[:\s]*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', page_source)
            if due_match:
                manuscript_data['due_date'] = due_match.group(1)
                logger.info(f"⏰ Due: {manuscript_data['due_date']}")
            
            # Extract status
            status_match = re.search(r'Status[:\s]*([^<\n]+)', page_source)
            if status_match:
                manuscript_data['status'] = status_match.group(1).strip()
                logger.info(f"📊 Status: {manuscript_data['status']}")
            
            # Extract referee data (using proven stable approach)
            reviewer_list_header = soup.find(string=re.compile('Reviewer List', re.IGNORECASE))
            if reviewer_list_header:
                logger.info("✅ Found Reviewer List section")
                
                # Use exact same referee extraction as stable system
                reviewer_section = reviewer_list_header.find_parent()
                while reviewer_section and reviewer_section.name != 'table':
                    reviewer_section = reviewer_section.find_next('table')
                
                if reviewer_section:
                    rows = reviewer_section.find_all('tr')
                    logger.info(f"Found {len(rows)} rows in reviewer table")
                    
                    for i, row in enumerate(rows[1:], 1):  # Skip header row
                        cells = row.find_all('td')
                        
                        if len(cells) >= 4:
                            # Extract name
                            name = ''
                            name_cell_full_text = ''
                            for cell_idx, cell in enumerate(cells[:5]):
                                cell_text = cell.get_text(strip=True)
                                
                                # Skip obvious non-name cells
                                if any(skip in cell_text.lower() for skip in ['security reasons', 'time out', 'session', 'revision', 'rescind']):
                                    continue
                                
                                # Look for pattern: "LastName, FirstName" and extract properly
                                # Try different regex patterns to capture names properly
                                name_patterns = [
                                    # Pattern 1: LastName, FirstName at start of string followed by institution
                                    r'^([A-Za-z]+,\s*[A-Za-z]+?)(?=[A-Z][a-z]|University|College|Institute|School)',
                                    # Pattern 2: LastName, FirstName followed by (R0) marker
                                    r'([A-Za-z]+,\s*[A-Za-z]+)(?:\(R0\))',
                                    # Pattern 3: LastName, FirstName at start followed by uppercase sequences
                                    r'^([A-Za-z]+,\s*[A-Za-z]+?)(?=[A-Z]{2,})',
                                    # Pattern 4: Basic LastName, FirstName at start
                                    r'^([A-Za-z]+,\s*[A-Za-z]+)',
                                    # Pattern 5: Fallback - any LastName, FirstName
                                    r'([A-Za-z]+,\s*[A-Za-z]+)'
                                ]
                                
                                name_found = False
                                for pattern in name_patterns:
                                    name_match = re.search(pattern, cell_text)
                                    if name_match:
                                        potential_name = name_match.group(1).strip()
                                        
                                        # Clean name - remove any non-letter/comma/space characters
                                        cleaned_name = re.sub(r'[^a-zA-Z,\s]', '', potential_name).strip()
                                        
                                        # Validate it's a proper name format
                                        if len(cleaned_name) > 3 and ',' in cleaned_name and cleaned_name.count(',') == 1:
                                            # Additional check: name shouldn't contain obvious institution words
                                            name_lower = cleaned_name.lower()
                                            if not any(inst_word in name_lower for inst_word in ['university', 'college', 'school', 'institute']):
                                                name = cleaned_name
                                                name_cell_full_text = cell_text
                                                name_found = True
                                                break
                                
                                if name_found:
                                    break
                            
                            if name:
                                # Create referee object
                                referee = {
                                    'name': name,
                                    'institution': '',
                                    'email': '',
                                    'status': '',
                                    'dates': {'invited': '', 'agreed': '', 'due': ''},
                                    'time_in_review': '',
                                    'report_submitted': False,
                                    'submission_date': '',
                                    'review_decision': '',
                                    'report_url': '',
                                    'acceptance_date': ''
                                }
                                
                                # Extract status and dates (exact same logic)
                                status_found = False
                                for cell in cells:
                                    cell_text = cell.get_text(strip=True).lower()
                                    
                                    # Check for status
                                    if 'agreed' in cell_text or 'accepted' in cell_text:
                                        referee['status'] = 'Agreed'
                                        status_found = True
                                        break
                                    elif 'declined' in cell_text:
                                        referee['status'] = 'Declined'
                                        status_found = True
                                        break
                                
                                # Extract dates
                                for cell in cells:
                                    cell_text = cell.get_text(strip=True)
                                    
                                    invited_match = re.search(r'Invited:\s*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', cell_text)
                                    if invited_match:
                                        referee['dates']['invited'] = invited_match.group(1)
                                    
                                    agreed_match = re.search(r'Agreed:\s*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', cell_text)
                                    if agreed_match:
                                        referee['dates']['agreed'] = agreed_match.group(1)
                                    
                                    due_match = re.search(r'Due Date:\s*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', cell_text)
                                    if due_match:
                                        referee['dates']['due'] = due_match.group(1)
                                    
                                    time_match = re.search(r'Time in Review:\s*([0-9]+\s*Days?)', cell_text)
                                    if time_match:
                                        referee['time_in_review'] = time_match.group(1)
                                
                                # Extract institution from name cell and other cells
                                institution_found = False
                                
                                # First try to extract from the name cell itself
                                if name in name_cell_full_text and len(name_cell_full_text) > len(name) + 3:
                                    # Split on the name and take what comes after
                                    after_name = name_cell_full_text[name_cell_full_text.find(name) + len(name):]
                                    
                                    # Clean up institution - remove common patterns
                                    potential_institution = after_name.strip(' ,()')
                                    
                                    # Remove R0 marker if present
                                    potential_institution = re.sub(r'\(R0\)', '', potential_institution).strip()
                                    
                                    # Clean up common institution patterns
                                    if potential_institution:
                                        # Handle patterns like "UC Berkeley" from "ThibautUC Berkeley"
                                        potential_institution = re.sub(r'^[A-Za-z]{2,3}(?=[A-Z])', lambda m: m.group(0) + ' ', potential_institution)
                                        # Handle patterns like "University" from "GechunUniversity"
                                        potential_institution = re.sub(r'^[A-Za-z]+(?=University)', lambda m: m.group(0) + ' ', potential_institution)
                                        # Handle patterns like "Warwick" from "MorisWarwick"
                                        potential_institution = re.sub(r'^[A-Za-z]+(?=[A-Z][a-z])', lambda m: m.group(0) + ' ', potential_institution)
                                        
                                        # Remove URLs and ORCID links
                                        potential_institution = re.sub(r'https?://[^\s]+', '', potential_institution).strip()
                                        
                                        if potential_institution and len(potential_institution) > 2 and not potential_institution.isdigit():
                                            referee['institution'] = potential_institution.strip()
                                            institution_found = True
                                
                                # If no institution found in name cell, look in other cells
                                if not institution_found:
                                    for cell in cells:
                                        cell_text_clean = cell.get_text(strip=True)
                                        
                                        # Look for institution patterns in other cells
                                        if ('university' in cell_text_clean.lower() or 
                                            'college' in cell_text_clean.lower() or
                                            'institute' in cell_text_clean.lower() or
                                            'school' in cell_text_clean.lower()) and len(cell_text_clean) > 10:
                                            
                                            # Clean institution text
                                            clean_institution = re.sub(r'https?://[^\s]+', '', cell_text_clean).strip()
                                            if clean_institution and clean_institution != referee['institution']:
                                                referee['institution'] = clean_institution
                                                break
                                
                                # Skip unavailable/declined referees
                                skip_keywords = ['unavailable', 'declined', 'rescind', 'withdraw']
                                should_skip = False
                                for keyword in skip_keywords:
                                    if any(keyword in cell.get_text(strip=True).lower() for cell in cells):
                                        should_skip = True
                                        break
                                
                                if not should_skip:
                                    manuscript_data['referees'].append(referee)
                                    logger.info(f"   ✅ {name} ({referee['status']})")
            
            # Download PDFs
            pdf_info = self.find_and_download_pdfs(manuscript_id)
            manuscript_data['pdf_info'] = pdf_info
            
            manuscript_data['extraction_status'] = 'success'
            logger.info(f"✅ Successfully extracted complete data for {manuscript_id}")
            logger.info(f"   Referees: {len(manuscript_data['referees'])}")
            logger.info(f"   PDFs: Manuscript={bool(pdf_info.get('manuscript_pdf_file'))}, Reports={len(pdf_info.get('referee_reports', []))}")
            
            return manuscript_data
            
        except Exception as e:
            logger.error(f"❌ Complete extraction failed for {manuscript_id}: {e}")
            manuscript_data['extraction_status'] = 'failed'
            manuscript_data['error'] = str(e)
            return manuscript_data
    
    def extract_all_mf_complete_data(self, headless=False):
        """Extract complete MF data with PDFs"""
        logger.info("🚀 Starting complete stable MF extraction with PDFs")
        
        all_results = {
            'journal': 'MF',
            'extraction_date': datetime.now().isoformat(),
            'extraction_method': 'complete_stable_with_pdfs',
            'manuscripts': []
        }
        
        try:
            # Create driver and login (proven working approach)
            if not self.create_driver(headless=headless):
                raise Exception("Driver creation failed")
            
            if not self.login_mf():
                raise Exception("Login failed")
            
            # Navigate to AE Center
            ae_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            time.sleep(3)
            logger.info("✅ Navigated to Associate Editor Center")
            
            # Navigate to category
            category = "Awaiting Reviewer Scores"
            category_link = self.driver.find_element(By.LINK_TEXT, category)
            category_link.click()
            time.sleep(3)
            logger.info(f"✅ Navigated to {category}")
            
            # Process each manuscript (using proven checkbox finding)
            for manuscript_id, manuscript_info in self.expected_manuscripts.items():
                logger.info(f"\n{'='*60}")
                logger.info(f"📄 Processing: {manuscript_id}")
                logger.info(f"Expected: {manuscript_info['title'][:50]}...")
                logger.info(f"{'='*60}")
                
                # Find and click checkbox (proven working approach)
                checkboxes = self.driver.find_elements(By.XPATH, "//img[contains(@src, 'check_off.gif')]")
                rows = self.driver.find_elements(By.TAG_NAME, "tr")
                found_checkbox = False
                
                for i, row in enumerate(rows):
                    try:
                        row_text = row.text.strip()
                        if row_text.startswith(manuscript_id):
                            row_checkboxes = row.find_elements(By.XPATH, ".//img[contains(@src, 'check_off.gif')]")
                            if len(row_checkboxes) == 1:
                                logger.info(f"✅ Found {manuscript_id} in row {i}")
                                
                                # Click checkbox
                                checkbox = row_checkboxes[0]
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                                time.sleep(0.5)
                                checkbox.click()
                                time.sleep(3)
                                
                                found_checkbox = True
                                break
                    except:
                        continue
                
                if found_checkbox:
                    # Extract complete manuscript data including PDFs
                    manuscript_data = self.extract_complete_manuscript_data(manuscript_id)
                    all_results['manuscripts'].append(manuscript_data)
                    
                    # Navigate back
                    ae_link = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
                    )
                    ae_link.click()
                    time.sleep(2)
                    
                    category_link = self.driver.find_element(By.LINK_TEXT, category)
                    category_link.click()
                    time.sleep(3)
                else:
                    # Add failed record
                    all_results['manuscripts'].append({
                        'manuscript_id': manuscript_id,
                        'extraction_status': 'failed',
                        'error': 'Checkbox not found'
                    })
            
            # Save results
            results_file = self.results_dir / "mf_complete_stable_results.json"
            with open(results_file, 'w') as f:
                json.dump(all_results, f, indent=2)
            
            # Generate report
            self.generate_complete_report(all_results)
            
            logger.info(f"🎉 Complete stable MF extraction finished!")
            logger.info(f"   Results: {results_file}")
            
            return all_results
            
        except Exception as e:
            logger.error(f"❌ Complete extraction failed: {e}")
            return all_results
            
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    logger.info("🔄 Driver closed")
                except:
                    pass
    
    def generate_complete_report(self, results: Dict[str, Any]):
        """Generate comprehensive report including PDF info"""
        report_lines = []
        report_lines.append("COMPLETE STABLE MF EXTRACTION WITH PDFS")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("Method: complete_stable_with_pdfs")
        report_lines.append("="*80)
        report_lines.append("")
        
        for manuscript in results['manuscripts']:
            if manuscript.get('extraction_status') == 'success':
                report_lines.append(f"Manuscript: {manuscript['manuscript_id']}")
                report_lines.append(f"Title: {manuscript.get('title', 'N/A')}")
                report_lines.append(f"Status: {manuscript.get('status', 'N/A')}")
                report_lines.append(f"Submitted: {manuscript.get('submitted_date', 'N/A')}")
                report_lines.append(f"Due: {manuscript.get('due_date', 'N/A')}")
                
                # Referee info
                referees = manuscript.get('referees', [])
                report_lines.append(f"Referees: {len(referees)}")
                for ref in referees:
                    report_lines.append(f"  • {ref['name']} ({ref['status']})")
                    report_lines.append(f"    Invited: {ref['dates'].get('invited', 'N/A')}")
                    report_lines.append(f"    Due: {ref['dates'].get('due', 'N/A')}")
                    report_lines.append(f"    Time in Review: {ref.get('time_in_review', 'N/A')}")
                
                # PDF info
                pdf_info = manuscript.get('pdf_info', {})
                report_lines.append(f"PDFs:")
                if pdf_info.get('manuscript_pdf_file'):
                    report_lines.append(f"  • Manuscript PDF: {Path(pdf_info['manuscript_pdf_file']).name}")
                
                referee_reports = pdf_info.get('referee_reports', [])
                if referee_reports:
                    report_lines.append(f"  • Referee Reports: {len(referee_reports)}")
                    for report in referee_reports:
                        report_lines.append(f"    - {Path(report['downloaded_file']).name}")
                
                additional_files = pdf_info.get('additional_files', [])
                if additional_files:
                    report_lines.append(f"  • Additional Files: {len(additional_files)}")
                
                report_lines.append("")
                report_lines.append("-" * 60)
                report_lines.append("")
        
        # Summary
        total = len(results['manuscripts'])
        successful = len([m for m in results['manuscripts'] if m.get('extraction_status') == 'success'])
        total_referees = sum(len(m.get('referees', [])) for m in results['manuscripts'])
        total_pdfs = sum(
            1 + len(m.get('pdf_info', {}).get('referee_reports', [])) + len(m.get('pdf_info', {}).get('additional_files', []))
            for m in results['manuscripts'] 
            if m.get('pdf_info', {}).get('manuscript_pdf_file')
        )
        
        report_lines.append("SUMMARY:")
        report_lines.append(f"Total Manuscripts: {total}")
        report_lines.append(f"Successful Extractions: {successful}")
        report_lines.append(f"Total Referees: {total_referees}")
        report_lines.append(f"Total PDFs Downloaded: {total_pdfs}")
        report_lines.append(f"Success Rate: {(successful/total*100):.1f}%" if total > 0 else "0%")
        
        # Save report
        report_file = self.results_dir / "mf_complete_stable_report.txt"
        with open(report_file, 'w') as f:
            f.write('\n'.join(report_lines))
        
        logger.info(f"📄 Complete report saved: {report_file}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    args = parser.parse_args()
    
    extractor = CompleteStableMFExtractor()
    results = extractor.extract_all_mf_complete_data(headless=args.headless)
    
    if results and results.get('manuscripts'):
        successful = len([m for m in results['manuscripts'] if m.get('extraction_status') == 'success'])
        total = len(results['manuscripts'])
        print(f"✅ Complete extraction: {successful}/{total} manuscripts with PDFs")
    else:
        print("❌ Complete extraction failed!")
        sys.exit(1)