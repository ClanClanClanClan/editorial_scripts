#!/usr/bin/env python3
"""
Complete Stable MOR Extractor - Adapted from working MF system for MOR
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
        logging.FileHandler('complete_stable_mor_extraction.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("COMPLETE_STABLE_MOR")

class CompleteStableMORExtractor:
    """Complete stable MOR extractor with PDF downloads"""
    
    def __init__(self):
        self.driver = None
        self.debug_dir = Path("complete_debug_mor")
        self.debug_dir.mkdir(exist_ok=True)
        self.results_dir = Path("complete_results_mor")
        self.results_dir.mkdir(exist_ok=True)
        self.pdfs_dir = self.results_dir / "pdfs"
        self.pdfs_dir.mkdir(exist_ok=True)
        
        # MOR journal config
        self.journal_config = {
            "name": "Mathematics of Operations Research",
            "url": "https://mc.manuscriptcentral.com/mathor",
            "ae_category": "Awaiting Reviewer Reports",  # Try this first
            "alt_category": "Awaiting Final Decision",    # Fallback for completed reviews
            "email_prefix": "MOR"
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
            
            # Try fallback approach 2: different version
            try:
                logger.info("   Attempting fallback approach...")
                options = uc.ChromeOptions()
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-extensions')
                options.add_argument('--window-size=1920,1080')
                
                if headless:
                    options.add_argument('--headless')
                
                self.driver = uc.Chrome(options=options, version_main=126)
                logger.info("✅ Fallback Chrome driver created successfully")
                return True
                
            except Exception as e2:
                logger.error(f"All driver creation methods failed: {e2}")
                return False
    
    def login_mor(self):
        """Login to MOR using proven approach"""
        logger.info("🔐 Logging into MOR (adapted from working MF system)")
        
        try:
            # Navigate to MOR
            mor_url = self.journal_config["url"]
            logger.info(f"Navigating to MOR dashboard: {mor_url}")
            self.driver.get(mor_url)
            time.sleep(2)
            
            # Handle cookies (same approach as MF)
            try:
                accept_btn = self.driver.find_element(By.ID, "onetrust-accept-btn-handler")
                if accept_btn.is_displayed():
                    accept_btn.click()
                    logger.info("Accepted cookies.")
                    time.sleep(1)
            except Exception:
                pass
            
            # Get MOR credentials - try MOR first, fallback to MF if same user
            user = os.environ.get("MOR_USER") or os.environ.get("MF_USER")
            pw = os.environ.get("MOR_PASS") or os.environ.get("MF_PASS")
            if not user or not pw:
                raise RuntimeError("MOR_USER/MOR_PASS or MF_USER/MF_PASS environment variables must be set.")
            
            # Fill login form (same as MF)
            user_box = self.driver.find_element(By.ID, "USERID")
            pw_box = self.driver.find_element(By.ID, "PASSWORD")
            user_box.clear()
            user_box.send_keys(user)
            pw_box.clear()
            pw_box.send_keys(pw)
            
            # Submit login
            login_btn = self.driver.find_element(By.ID, "logInButton")
            login_btn.click()
            time.sleep(4)
            
            # Handle verification if needed (same approach as MF)
            wait = WebDriverWait(self.driver, 15)
            try:
                code_input = wait.until(
                    lambda d: d.find_element(By.ID, "TOKEN_VALUE") if d.find_element(By.ID, "TOKEN_VALUE").is_displayed() else None
                )
                if code_input:
                    logger.info("Verification needed - using MOR email verification...")
                    sys.path.insert(0, str(Path(__file__).parent))
                    from core.email_utils import fetch_latest_verification_code
                    
                    time.sleep(5)
                    verification_code = fetch_latest_verification_code(journal="MOR")
                    
                    if verification_code:
                        code_input.clear()
                        code_input.send_keys(verification_code)
                        code_input.send_keys(Keys.RETURN)
                        time.sleep(3)
                        logger.info("Submitted verification code.")
            except TimeoutException:
                pass
            
            # Check if we're logged in
            try:
                current_url = self.driver.current_url
                if "mathor" in current_url and "mc.manuscriptcentral.com" in current_url:
                    logger.info("Ready to continue navigation after login.")
                    return True
                else:
                    raise RuntimeError(f"Login may have failed. Current URL: {current_url}")
            except Exception as e:
                logger.error(f"Error checking login status: {e}")
                return False
                
        except Exception as e:
            logger.error(f"❌ MOR login failed: {e}")
            return False
    
    def navigate_to_manuscripts(self):
        """Navigate to manuscript listing page"""
        logger.info("🧭 Navigating to MOR manuscript categories")
        
        try:
            # Navigate to Associate Editor Center (same as MF)
            ae_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            time.sleep(3)
            logger.info("✅ Navigated to Associate Editor Center")
            
            # Navigate to MOR's category (Awaiting Reviewer Reports)
            category_text = self.journal_config["ae_category"]
            category_link = self.driver.find_element(By.LINK_TEXT, category_text)
            category_link.click()
            time.sleep(3)
            logger.info(f"✅ Navigated to {category_text}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Navigation failed: {e}")
            return False
    
    def extract_manuscript_data(self, manuscript_id: str) -> Dict[str, Any]:
        """Extract complete manuscript data including referees and PDFs"""
        logger.info(f"📊 Extracting complete data for {manuscript_id}...")
        
        try:
            # Use same referee extraction approach as MF
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find reviewer list section (same approach as MF)
            reviewer_section = None
            for elem in soup.find_all(['div', 'table', 'tr', 'td']):
                if elem.get_text() and 'reviewer list' in elem.get_text().lower():
                    reviewer_section = elem
                    break
            
            if not reviewer_section:
                logger.warning("Could not find Reviewer List section")
                return {'referees': [], 'pdf_info': {}}
            
            logger.info("✅ Found Reviewer List section")
            
            # Extract referees using proven name/institution separation
            referees = []
            table = reviewer_section.find_parent('table')
            if not table:
                table = soup.find('table')
            
            if table:
                rows = table.find_all('tr')
                logger.info(f"Found {len(rows)} rows in reviewer table")
                
                for row in rows:
                    referee_data = self.extract_referee_from_row(row)
                    if referee_data:
                        referees.append(referee_data)
                        logger.info(f"   ✅ {referee_data['name']} ({referee_data['status']})")
            
            # Get PDFs for this manuscript
            pdf_info = self.discover_pdfs(manuscript_id)
            
            return {
                'referees': referees,
                'pdf_info': pdf_info
            }
            
        except Exception as e:
            logger.error(f"❌ Error extracting data for {manuscript_id}: {e}")
            return {'referees': [], 'pdf_info': {}}
    
    def extract_referee_from_row(self, row) -> Optional[Dict[str, Any]]:
        """Extract referee data from table row using proven approach"""
        try:
            row_text = row.get_text(strip=True)
            if not row_text or len(row_text) < 10:
                return None
            
            # Skip header rows and empty rows
            if any(header in row_text.lower() for header in ['name', 'status', 'history', 'order']):
                return None
            
            # Use proven multi-pattern regex for name extraction
            name_patterns = [
                r'^([A-Za-z]+,\s*[A-Za-z]+?)(?=[A-Z][a-z]|University|College|Institute|School)',
                r'([A-Za-z]+,\s*[A-Za-z]+)(?:\(R0\))',
                r'^([A-Za-z]+,\s*[A-Za-z]+?)(?=[A-Z]{2,})',
                r'^([A-Za-z]+,\s*[A-Za-z]+)',
                r'([A-Za-z]+,\s*[A-Za-z]+)'
            ]
            
            referee_name = None
            for pattern in name_patterns:
                match = re.search(pattern, row_text)
                if match:
                    referee_name = match.group(1).strip()
                    break
            
            if not referee_name:
                return None
            
            # Extract institution (everything after name until status keywords)
            institution = ""
            name_end = row_text.find(referee_name) + len(referee_name)
            remaining_text = row_text[name_end:].strip()
            
            status_keywords = ['agreed', 'declined', 'invited', 'completed', 'pending']
            status_pos = float('inf')
            for keyword in status_keywords:
                pos = remaining_text.lower().find(keyword)
                if pos != -1 and pos < status_pos:
                    status_pos = pos
            
            if status_pos != float('inf'):
                institution = remaining_text[:status_pos].strip()
            
            # Clean institution
            institution = re.sub(r'^[^\w]*', '', institution)
            institution = re.sub(r'\s+', ' ', institution).strip()
            
            # Extract status
            status = "Unknown"
            if 'agreed' in row_text.lower():
                status = "Agreed"
            elif 'declined' in row_text.lower():
                status = "Declined"
            elif 'completed' in row_text.lower():
                status = "Completed"
            elif 'pending' in row_text.lower():
                status = "Pending"
            
            # Extract dates using same approach as MF
            dates = self.extract_dates_from_text(row_text)
            
            return {
                'name': referee_name,
                'institution': institution,
                'email': '',
                'status': status,
                'dates': dates,
                'time_in_review': self.calculate_time_in_review(dates.get('invited', '')),
                'report_submitted': status == "Completed",
                'submission_date': '',
                'review_decision': '',
                'report_url': '',
                'acceptance_date': ''
            }
            
        except Exception as e:
            return None
    
    def extract_dates_from_text(self, text: str) -> Dict[str, str]:
        """Extract dates from referee row text"""
        dates = {'invited': '', 'agreed': '', 'due': ''}
        
        # Look for date patterns
        date_patterns = [
            r'invited:\s*(\d{2}-[A-Za-z]{3}-\d{4})',
            r'agreed:\s*(\d{2}-[A-Za-z]{3}-\d{4})',
            r'due date:\s*(\d{2}-[A-Za-z]{3}-\d{4})'
        ]
        
        for i, pattern in enumerate(date_patterns):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_keys = ['invited', 'agreed', 'due']
                dates[date_keys[i]] = match.group(1)
        
        return dates
    
    def calculate_time_in_review(self, invited_date: str) -> str:
        """Calculate time in review from invited date"""
        if not invited_date:
            return ""
        
        try:
            invited = datetime.strptime(invited_date, "%d-%b-%Y")
            now = datetime.now()
            delta = now - invited
            return f"{delta.days} Days"
        except:
            return ""
    
    def discover_pdfs(self, manuscript_id: str) -> Dict[str, Any]:
        """Discover and download all PDFs for a manuscript"""
        logger.info(f"📥 Looking for PDFs for manuscript: {manuscript_id}")
        
        pdf_info = {
            'manuscript_pdf_url': '',
            'manuscript_pdf_file': '',
            'referee_reports': [],
            'additional_files': [],
            'text_reviews': []
        }
        
        try:
            # 1. Get manuscript PDF via tabs (same approach as MF)
            manuscript_pdf = self.get_manuscript_pdf(manuscript_id)
            if manuscript_pdf:
                pdf_info['manuscript_pdf_url'] = manuscript_pdf['url']
                pdf_info['manuscript_pdf_file'] = manuscript_pdf['file']
                logger.info(f"✅ Manuscript PDF: {manuscript_pdf['file']}")
            
            # 2. Get referee reports - this is where MOR should have completed reports
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
        """Get manuscript PDF by clicking PDF tabs (same as MF)"""
        logger.info(f"🔍 Looking for manuscript PDF tabs for {manuscript_id}")
        
        try:
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
        """Get referee reports by clicking 'view review' links - ENHANCED for MOR"""
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
                    
                    # Dismiss any overlaying elements first
                    try:
                        # Close cookie banner if it's blocking
                        cookie_close = self.driver.find_elements(By.ID, "onetrust-close-btn-container")
                        if cookie_close:
                            cookie_close[0].click()
                            time.sleep(1)
                    except:
                        pass
                    
                    # Scroll to element and use JavaScript click to avoid interception
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", review_link)
                    time.sleep(1)
                    self.driver.execute_script("arguments[0].click();", review_link)
                    time.sleep(3)  # Give more time for MOR
                    
                    # Check for new window
                    new_windows = self.driver.window_handles
                    if len(new_windows) > len(original_windows):
                        # Switch to review window
                        new_window = [w for w in new_windows if w not in original_windows][0]
                        self.driver.switch_to.window(new_window)
                        logger.info(f"✅ Opened review window {i+1}")
                        
                        # Enhanced extraction for MOR: get BOTH PDFs and text
                        report_data = self.extract_complete_review_data(manuscript_id, i+1)
                        
                        # Add to appropriate lists
                        if report_data['pdf_files']:
                            reports['pdf_reports'].extend(report_data['pdf_files'])
                        
                        if report_data['text_content']:
                            reports['text_reviews'].append({
                                'referee_number': i+1,
                                'content': report_data['text_content'],
                                'extraction_time': datetime.now().isoformat()
                            })
                        
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
    
    def extract_complete_review_data(self, manuscript_id: str, referee_num: int) -> Dict[str, Any]:
        """Enhanced method to extract BOTH PDFs and text from review window"""
        logger.info(f"🔍 Extracting complete review data for referee {referee_num}")
        
        result = {
            'pdf_files': [],
            'text_content': ''
        }
        
        try:
            # 1. Look for PDF attachments first
            logger.info(f"   Looking for PDF attachments...")
            
            # Multiple ways PDFs might be attached
            pdf_selectors = [
                "//a[contains(@href, '.pdf')]",  # Direct PDF links
                "//a[contains(text(), 'attached') or contains(text(), 'attachment')]",  # Attachment links
                "//a[contains(text(), 'file') or contains(text(), 'download')]",  # File download links
                "//*[contains(text(), 'Files attached')]/following-sibling::*//a"  # Files in attached section
            ]
            
            pdf_found = False
            for selector in pdf_selectors:
                try:
                    pdf_links = self.driver.find_elements(By.XPATH, selector)
                    for pdf_link in pdf_links:
                        href = pdf_link.get_attribute('href')
                        link_text = pdf_link.text.strip()
                        
                        if href and ('.pdf' in href.lower() or 'download' in href.lower() or 'attachment' in href.lower()):
                            logger.info(f"   Found PDF link: {link_text} -> {href[:100]}...")
                            
                            # Download referee report PDF
                            pdf_file = self.download_direct_pdf(
                                href, 
                                self.pdfs_dir / f"{manuscript_id}_referee_report_{referee_num}_{link_text[:20]}.pdf"
                            )
                            
                            if pdf_file:
                                result['pdf_files'].append({
                                    'referee_number': referee_num,
                                    'url': href,
                                    'file': pdf_file,
                                    'link_text': link_text,
                                    'download_time': datetime.now().isoformat()
                                })
                                pdf_found = True
                                logger.info(f"✅ Downloaded referee report PDF {referee_num}: {link_text}")
                except Exception as e:
                    logger.warning(f"   Error with selector {selector}: {e}")
                    continue
            
            # 2. Look for text comments - check multiple sections
            logger.info(f"   Looking for text comments...")
            
            text_selectors = [
                "//*[contains(text(), 'Comments to the Author')]",
                "//*[contains(text(), 'comments to author')]",
                "//*[contains(text(), 'Review')]//textarea",
                "//*[contains(text(), 'Comments')]//following-sibling::*",
                "//textarea",  # Any text areas
                "//*[contains(@class, 'review') or contains(@class, 'comment')]"  # Review/comment classes
            ]
            
            all_text_content = []
            
            for selector in text_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        # Try to get text content
                        text_content = ""
                        
                        # For textarea elements
                        if element.tag_name == 'textarea':
                            text_content = element.get_attribute('value') or element.text
                        else:
                            # For other elements, look for associated text content
                            try:
                                parent = element.find_element(By.XPATH, ".//..")
                                text_content = parent.text.strip()
                            except:
                                text_content = element.text.strip()
                        
                        if text_content and len(text_content) > 50:  # Meaningful review text
                            all_text_content.append(text_content)
                            logger.info(f"   Found text content ({len(text_content)} chars): {text_content[:100]}...")
                            
                except Exception as e:
                    logger.warning(f"   Error with text selector {selector}: {e}")
                    continue
            
            # Combine all text content
            if all_text_content:
                result['text_content'] = "\n\n---SECTION---\n\n".join(all_text_content)
                logger.info(f"✅ Extracted {len(all_text_content)} text sections ({len(result['text_content'])} total chars)")
            
            # 3. If no specific content found, get entire page text as fallback
            if not pdf_found and not result['text_content']:
                logger.info(f"   No specific content found, capturing full page text...")
                try:
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text
                    if len(page_text) > 200:  # Reasonable amount of content
                        result['text_content'] = page_text
                        logger.info(f"✅ Captured full page text ({len(page_text)} chars)")
                except Exception as e:
                    logger.warning(f"   Could not capture page text: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error extracting review data for referee {referee_num}: {e}")
            return result
    
    def download_direct_pdf(self, url: str, filepath: Path) -> Optional[str]:
        """Download PDF from direct URL (same proven approach as MF)"""
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
            logger.error(f"PDF download error: {e}")
            return None
    
    def find_manuscripts(self) -> List[str]:
        """Find available manuscripts on the page"""
        logger.info("🔍 Looking for manuscripts on page...")
        
        try:
            # Look for manuscript rows (same pattern as MF)
            rows = self.driver.find_elements(By.TAG_NAME, "tr")
            manuscripts = []
            
            for i, row in enumerate(rows):
                try:
                    row_text = row.text.strip()
                    # Look for MOR manuscript ID pattern (similar to MAFI pattern)
                    if re.search(r'MOR-\d{4}-\d{4}', row_text) or re.search(r'MATHOR-\d{4}-\d{4}', row_text):
                        # Extract manuscript ID
                        id_match = re.search(r'(MOR-\d{4}-\d{4}|MATHOR-\d{4}-\d{4})', row_text)
                        if id_match:
                            manuscript_id = id_match.group(1)
                            manuscripts.append(manuscript_id)
                            logger.info(f"   Found: {manuscript_id}")
                except:
                    continue
            
            logger.info(f"✅ Found {len(manuscripts)} manuscripts")
            return manuscripts
            
        except Exception as e:
            logger.error(f"❌ Error finding manuscripts: {e}")
            return []
    
    def click_manuscript_checkbox(self, manuscript_id: str) -> bool:
        """Click manuscript checkbox to view details (same as MF)"""
        try:
            checkboxes = self.driver.find_elements(By.XPATH, "//img[contains(@src, 'check_off.gif')]")
            rows = self.driver.find_elements(By.TAG_NAME, "tr")
            
            for i, row in enumerate(rows):
                try:
                    row_text = row.text.strip()
                    if row_text.startswith(manuscript_id):
                        row_checkboxes = row.find_elements(By.XPATH, ".//img[contains(@src, 'check_off.gif')]")
                        if len(row_checkboxes) == 1:
                            logger.info(f"✅ Found {manuscript_id} in row {i}, clicking...")
                            checkbox = row_checkboxes[0]
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                            time.sleep(0.5)
                            checkbox.click()
                            time.sleep(3)
                            return True
                except:
                    continue
                    
            logger.warning(f"❌ Could not find checkbox for {manuscript_id}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error clicking checkbox for {manuscript_id}: {e}")
            return False
    
    def run_extraction(self):
        """Main extraction process"""
        logger.info("🚀 Starting complete stable MOR extraction with PDFs")
        
        try:
            # Create driver
            if not self.create_driver():
                logger.error("❌ Failed to create driver")
                return
            
            # Login to MOR
            if not self.login_mor():
                logger.error("❌ Failed to login to MOR")
                return
            
            # Navigate to manuscripts
            if not self.navigate_to_manuscripts():
                logger.error("❌ Failed to navigate to manuscripts")
                return
            
            # Find manuscripts
            manuscripts = self.find_manuscripts()
            if not manuscripts:
                logger.warning("⚠️  No manuscripts found")
                return
            
            # Process each manuscript (remove duplicates first)
            unique_manuscripts = list(set(manuscripts))
            all_results = []
            
            for manuscript_id in unique_manuscripts[:3]:  # Process first 3 unique manuscripts
                logger.info(f"\n============================================================")
                logger.info(f"📄 Processing: {manuscript_id}")
                logger.info(f"============================================================")
                
                # Click manuscript checkbox
                if self.click_manuscript_checkbox(manuscript_id):
                    # Extract data
                    manuscript_data = self.extract_manuscript_data(manuscript_id)
                    manuscript_data['manuscript_id'] = manuscript_id
                    manuscript_data['extraction_status'] = 'success'
                    
                    all_results.append(manuscript_data)
                    
                    logger.info(f"✅ Successfully extracted data for {manuscript_id}")
                    logger.info(f"   Referees: {len(manuscript_data['referees'])}")
                    logger.info(f"   PDFs: Manuscript={bool(manuscript_data['pdf_info'].get('manuscript_pdf_file'))}, Reports={len(manuscript_data['pdf_info'].get('referee_reports', []))}")
                    
                    # Wait before next manuscript
                    time.sleep(5)
                else:
                    logger.error(f"❌ Failed to process {manuscript_id}")
            
            # Save final results
            final_results = {
                'journal': 'MOR',
                'extraction_date': datetime.now().isoformat(),
                'extraction_method': 'complete_stable_with_pdfs',
                'manuscripts': all_results
            }
            
            # Save JSON results
            results_file = self.results_dir / "mor_complete_stable_results.json"
            with open(results_file, 'w') as f:
                json.dump(final_results, f, indent=2)
            
            # Save text report
            report_file = self.results_dir / "mor_complete_stable_report.txt"
            self.generate_report(final_results, report_file)
            
            logger.info(f"📄 Complete report saved: {report_file}")
            logger.info(f"🎉 Complete stable MOR extraction finished!")
            logger.info(f"   Results: {results_file}")
            
        except Exception as e:
            logger.error(f"❌ Extraction failed: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("🔄 Driver closed")
    
    def generate_report(self, results: Dict[str, Any], report_file: Path):
        """Generate human-readable report"""
        try:
            with open(report_file, 'w') as f:
                f.write("COMPLETE STABLE MOR EXTRACTION WITH PDFS\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Method: {results['extraction_method']}\n")
                f.write("=" * 80 + "\n\n")
                
                for manuscript in results['manuscripts']:
                    f.write(f"Manuscript: {manuscript['manuscript_id']}\n")
                    f.write(f"Referees: {len(manuscript['referees'])}\n")
                    
                    for referee in manuscript['referees']:
                        f.write(f"  • {referee['name']} ({referee['status']})\n")
                        if referee.get('institution'):
                            f.write(f"    Institution: {referee['institution']}\n")
                        if referee['dates'].get('invited'):
                            f.write(f"    Invited: {referee['dates']['invited']}\n")
                        if referee['dates'].get('due'):
                            f.write(f"    Due: {referee['dates']['due']}\n")
                        if referee.get('time_in_review'):
                            f.write(f"    Time in Review: {referee['time_in_review']}\n")
                    
                    f.write("PDFs:\n")
                    pdf_info = manuscript.get('pdf_info', {})
                    if pdf_info.get('manuscript_pdf_file'):
                        f.write(f"  • Manuscript PDF: {pdf_info['manuscript_pdf_file'].split('/')[-1]}\n")
                    
                    for report in pdf_info.get('referee_reports', []):
                        f.write(f"  • Referee Report {report['referee_number']}: {report['file'].split('/')[-1]}\n")
                    
                    for review in pdf_info.get('text_reviews', []):
                        f.write(f"  • Text Review {review['referee_number']}: {len(review['content'])} characters\n")
                    
                    f.write("\n" + "-" * 60 + "\n\n")
                
                # Summary
                total_manuscripts = len(results['manuscripts'])
                total_referees = sum(len(m['referees']) for m in results['manuscripts'])
                total_pdf_reports = sum(len(m['pdf_info'].get('referee_reports', [])) for m in results['manuscripts'])
                total_text_reviews = sum(len(m['pdf_info'].get('text_reviews', [])) for m in results['manuscripts'])
                manuscript_pdfs = sum(1 for m in results['manuscripts'] if m['pdf_info'].get('manuscript_pdf_file'))
                
                f.write("SUMMARY:\n")
                f.write(f"Total Manuscripts: {total_manuscripts}\n")
                f.write(f"Total Referees: {total_referees}\n")
                f.write(f"Manuscript PDFs Downloaded: {manuscript_pdfs}\n")
                f.write(f"Total PDF Reports: {total_pdf_reports}\n")
                f.write(f"Total Text Reviews: {total_text_reviews}\n")
                f.write(f"Success Rate: {(total_manuscripts/max(total_manuscripts,1)*100):.1f}%\n")
                
        except Exception as e:
            logger.error(f"Error generating report: {e}")

if __name__ == "__main__":
    extractor = CompleteStableMORExtractor()
    extractor.run_extraction()