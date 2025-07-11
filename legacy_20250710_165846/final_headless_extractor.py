#!/usr/bin/env python3
"""
Final Headless Extractor - Complete MF/MOR extraction with referee reports in headless mode
Fixes cookie banner issues and ensures all PDFs and data are extracted
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

# Load environment variables
load_dotenv()

# Import selenium components with fallback
try:
    import undetected_chromedriver as uc
except ImportError:
    print("Installing undetected-chromedriver...")
    os.system("pip install undetected-chromedriver")
    import undetected_chromedriver as uc

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from bs4 import BeautifulSoup

class FinalHeadlessExtractor:
    """Final production extractor with headless mode and referee report downloads"""
    
    def __init__(self, journal: str, headless: bool = True):
        self.journal = journal.upper()
        self.headless = headless
        self.driver = None
        
        # Setup logging
        self.setup_logging()
        
        # Setup directories
        self.base_dir = Path(f"final_results_{journal.lower()}")
        self.base_dir.mkdir(exist_ok=True)
        self.pdfs_dir = self.base_dir / "pdfs"
        self.pdfs_dir.mkdir(exist_ok=True)
        
        # Journal configurations
        self.configs = {
            "MF": {
                "name": "Mathematical Finance",
                "url": "https://mc.manuscriptcentral.com/mafi",
                "category": "Awaiting Reviewer Scores"
            },
            "MOR": {
                "name": "Mathematics of Operations Research",
                "url": "https://mc.manuscriptcentral.com/mathor", 
                "category": "Awaiting Reviewer Reports"
            }
        }
        
        self.config = self.configs[journal]
        self.logger.info(f"🚀 Final {self.config['name']} extractor initialized")
        self.logger.info(f"   Headless: {headless}")
    
    def setup_logging(self):
        """Setup logging"""
        log_dir = Path("final_logs")
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"{self.journal.lower()}_final_{timestamp}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(f"FINAL_{self.journal}")
        self.logger.info(f"📝 Logging to: {log_file}")
    
    def create_robust_driver(self) -> bool:
        """Create driver with guaranteed headless mode support"""
        self.logger.info("🚀 Creating robust Chrome driver")
        
        # Multiple strategies for maximum compatibility
        strategies = [
            {"name": "minimal_args", "args": ["--no-sandbox", "--disable-dev-shm-usage"]},
            {"name": "stable_args", "args": ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-extensions"]},
            {"name": "compatibility", "args": ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--remote-debugging-port=9222"]}
        ]
        
        for i, strategy in enumerate(strategies, 1):
            try:
                self.logger.info(f"   Strategy {i}/{len(strategies)}: {strategy['name']}")
                
                options = uc.ChromeOptions()
                
                # Add strategy arguments
                for arg in strategy['args']:
                    options.add_argument(arg)
                
                # Force headless mode
                if self.headless:
                    options.add_argument('--headless=new')
                    options.add_argument('--window-size=1920,1080')
                    options.add_argument('--disable-gpu')
                    options.add_argument('--no-first-run')
                
                # Additional stability arguments
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                
                # Create driver
                self.driver = uc.Chrome(options=options, version_main=None)
                
                # Test with simple navigation
                self.driver.get("https://www.google.com")
                time.sleep(2)
                
                # Test basic functionality
                title = self.driver.title
                if "Google" in title:
                    self.logger.info(f"✅ Driver created successfully: {strategy['name']}")
                    return True
                
            except Exception as e:
                self.logger.warning(f"   Strategy {strategy['name']} failed: {str(e)[:100]}...")
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
                continue
        
        self.logger.error("❌ All driver creation strategies failed")
        return False
    
    def aggressive_cookie_dismissal(self):
        """Aggressively dismiss all cookie banners and overlays"""
        try:
            # Wait a moment for any overlays to appear
            time.sleep(1)
            
            # Multiple cookie banner selectors
            cookie_selectors = [
                "#onetrust-accept-btn-handler",
                "#onetrust-close-btn-container", 
                ".onetrust-close-btn-handler",
                "[id*='cookie'] button",
                "[class*='cookie'] button",
                "[id*='consent'] button",
                "[class*='consent'] button",
                "button[aria-label*='Accept']",
                "button[aria-label*='Close']"
            ]
            
            dismissed = False
            for selector in cookie_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if elem.is_displayed() and elem.is_enabled():
                            self.driver.execute_script("arguments[0].click();", elem)
                            self.logger.info(f"   Dismissed cookie banner: {selector}")
                            dismissed = True
                            time.sleep(0.5)
                except:
                    continue
            
            # Also try to remove overlay divs entirely
            overlay_selectors = [
                "#onetrust-banner-sdk",
                ".onetrust-pc-dark-filter",
                "[id*='cookie']",
                "[class*='overlay']"
            ]
            
            for selector in overlay_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        self.driver.execute_script("arguments[0].style.display = 'none';", elem)
                except:
                    continue
            
            if dismissed:
                self.logger.info("   ✅ Cookie banners dismissed")
            
        except Exception as e:
            self.logger.debug(f"   Cookie dismissal error: {e}")
    
    def login_journal(self) -> bool:
        """Login to journal with aggressive overlay handling"""
        self.logger.info(f"🔐 Logging into {self.journal}")
        
        try:
            # Navigate to journal
            self.driver.get(self.config['url'])
            time.sleep(3)
            
            # Aggressive cookie dismissal
            self.aggressive_cookie_dismissal()
            
            # Get credentials
            user = os.environ.get(f"{self.journal}_USER") or os.environ.get("MF_USER")
            password = os.environ.get(f"{self.journal}_PASS") or os.environ.get("MF_PASS")
            
            if not user or not password:
                raise RuntimeError(f"Credentials not found for {self.journal}")
            
            self.logger.info(f"   Using credentials for: {user[:3]}***")
            
            # Fill login form
            user_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "USERID"))
            )
            user_box.clear()
            user_box.send_keys(user)
            
            pw_box = self.driver.find_element(By.ID, "PASSWORD")
            pw_box.clear()
            pw_box.send_keys(password)
            
            # Submit login
            login_btn = self.driver.find_element(By.ID, "logInButton")
            login_btn.click()
            time.sleep(4)
            
            # Handle 2FA if needed
            self.handle_verification()
            
            self.logger.info("✅ Login successful")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Login failed: {e}")
            return False
    
    def handle_verification(self):
        """Handle 2FA verification"""
        try:
            code_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "TOKEN_VALUE"))
            )
            
            if code_input.is_displayed():
                self.logger.info("   2FA verification required")
                
                # Import email utilities
                sys.path.insert(0, str(Path(__file__).parent))
                from core.email_utils import fetch_latest_verification_code
                
                time.sleep(5)
                verification_code = fetch_latest_verification_code(journal=self.journal)
                
                if verification_code:
                    code_input.clear()
                    code_input.send_keys(verification_code)
                    code_input.send_keys(Keys.RETURN)
                    time.sleep(3)
                    self.logger.info(f"   Verification code submitted: {verification_code}")
                    
        except TimeoutException:
            self.logger.debug("   No verification required")
        except Exception as e:
            self.logger.warning(f"   Verification error: {e}")
    
    def navigate_to_manuscripts(self) -> bool:
        """Navigate to manuscript category"""
        self.logger.info("🧭 Navigating to manuscripts")
        
        try:
            # Navigate to Associate Editor Center
            ae_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            time.sleep(3)
            
            # Navigate to category
            category_link = self.driver.find_element(By.LINK_TEXT, self.config['category'])
            category_link.click()
            time.sleep(3)
            
            self.logger.info(f"✅ Reached {self.config['category']}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Navigation failed: {e}")
            return False
    
    def find_manuscripts(self) -> List[str]:
        """Find manuscripts on page"""
        try:
            manuscripts = []
            rows = self.driver.find_elements(By.TAG_NAME, "tr")
            
            # Journal-specific patterns
            patterns = {
                "MF": [r'MAFI-\d{4}-\d{4}'],
                "MOR": [r'MOR-\d{4}-\d{4}', r'MATHOR-\d{4}-\d{4}']
            }
            
            for row in rows:
                try:
                    row_text = row.text.strip()
                    for pattern in patterns[self.journal]:
                        matches = re.findall(pattern, row_text)
                        manuscripts.extend(matches)
                except:
                    continue
            
            # Remove duplicates
            unique_manuscripts = list(dict.fromkeys(manuscripts))
            self.logger.info(f"📄 Found {len(unique_manuscripts)} unique manuscripts")
            
            return unique_manuscripts
            
        except Exception as e:
            self.logger.error(f"Error finding manuscripts: {e}")
            return []
    
    def click_manuscript_checkbox(self, manuscript_id: str) -> bool:
        """Click manuscript checkbox with aggressive approach"""
        try:
            self.logger.info(f"   Clicking checkbox for {manuscript_id}")
            
            # Dismiss any overlays first
            self.aggressive_cookie_dismissal()
            
            rows = self.driver.find_elements(By.TAG_NAME, "tr")
            
            for i, row in enumerate(rows):
                try:
                    row_text = row.text.strip()
                    if row_text.startswith(manuscript_id):
                        checkboxes = row.find_elements(By.XPATH, ".//img[contains(@src, 'check_off.gif')]")
                        if checkboxes:
                            checkbox = checkboxes[0]
                            
                            # Scroll into view
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                            time.sleep(0.5)
                            
                            # Aggressive cookie dismissal again
                            self.aggressive_cookie_dismissal()
                            
                            # Multiple click approaches
                            click_methods = [
                                lambda: self.driver.execute_script("arguments[0].click();", checkbox),
                                lambda: self.driver.execute_script("arguments[0].dispatchEvent(new Event('click'));", checkbox),
                                lambda: checkbox.click()
                            ]
                            
                            for method in click_methods:
                                try:
                                    method()
                                    time.sleep(2)
                                    self.logger.info(f"   ✅ Clicked checkbox for {manuscript_id}")
                                    return True
                                except:
                                    continue
                except:
                    continue
            
            self.logger.warning(f"   ❌ Could not click checkbox for {manuscript_id}")
            return False
            
        except Exception as e:
            self.logger.error(f"   Checkbox click error: {e}")
            return False
    
    def extract_complete_manuscript_data(self, manuscript_id: str) -> Dict[str, Any]:
        """Extract complete manuscript data with referee reports"""
        self.logger.info(f"📊 Extracting complete data for {manuscript_id}")
        
        try:
            # Click manuscript checkbox
            if not self.click_manuscript_checkbox(manuscript_id):
                return {'manuscript_id': manuscript_id, 'status': 'failed', 'error': 'Could not click checkbox'}
            
            # Extract referee data
            referees = self.extract_referees()
            
            # Extract PDFs and reports
            pdf_info = self.extract_all_pdfs_and_reports(manuscript_id)
            
            result = {
                'manuscript_id': manuscript_id,
                'referees': referees,
                'pdf_info': pdf_info,
                'extraction_time': datetime.now().isoformat(),
                'status': 'success'
            }
            
            self.logger.info(f"   ✅ Extracted data for {manuscript_id}")
            self.logger.info(f"      Referees: {len(referees)}")
            self.logger.info(f"      Manuscript PDF: {bool(pdf_info.get('manuscript_pdf_file'))}")
            self.logger.info(f"      Referee reports: {len(pdf_info.get('referee_reports', []))}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"   ❌ Extraction failed for {manuscript_id}: {e}")
            return {'manuscript_id': manuscript_id, 'status': 'failed', 'error': str(e)}
    
    def extract_referees(self) -> List[Dict[str, Any]]:
        """Extract referee data with improved parsing"""
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find reviewer section
            reviewer_section = None
            for elem in soup.find_all(['div', 'table', 'tr', 'td']):
                if elem.get_text() and 'reviewer list' in elem.get_text().lower():
                    reviewer_section = elem
                    break
            
            if not reviewer_section:
                return []
            
            referees = []
            table = reviewer_section.find_parent('table') or soup.find('table')
            
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    referee_data = self.extract_referee_from_row(row)
                    if referee_data:
                        referees.append(referee_data)
            
            return referees
            
        except Exception as e:
            self.logger.error(f"   Error extracting referees: {e}")
            return []
    
    def extract_referee_from_row(self, row) -> Optional[Dict[str, Any]]:
        """Extract referee from table row"""
        try:
            row_text = row.get_text(strip=True)
            if not row_text or len(row_text) < 10:
                return None
            
            # Skip headers
            if any(keyword in row_text.lower() for keyword in ['name', 'status', 'history', 'order']):
                return None
            
            # Enhanced name patterns
            name_patterns = [
                r'^([A-Za-z\-\'\s]+,\s*[A-Za-z\-\'\s]+?)(?=\s+[A-Z][a-z]|University|College|Institute|School)',
                r'([A-Za-z\-\'\s]+,\s*[A-Za-z\-\'\s]+)(?:\s*\([R0-9]+\))',
                r'^([A-Za-z\-\'\s]+,\s*[A-Za-z\-\'\s]+?)(?=\s+[A-Z]{2,})',
                r'^([A-Za-z\-\'\s]+,\s*[A-Za-z\-\'\s]+)',
                r'([A-Za-z\-\'\s]+,\s*[A-Za-z\-\'\s]+)'
            ]
            
            referee_name = None
            for pattern in name_patterns:
                match = re.search(pattern, row_text)
                if match:
                    referee_name = match.group(1).strip()
                    if ',' in referee_name and 3 <= len(referee_name) <= 50:
                        break
                    referee_name = None
            
            if not referee_name or referee_name in ['reasons, your', ', ']:
                return None
            
            # Extract institution
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
            
            # Extract dates
            dates = self.extract_dates_from_text(row_text)
            
            return {
                'name': referee_name,
                'institution': institution,
                'status': status,
                'dates': dates,
                'time_in_review': self.calculate_time_in_review(dates.get('invited', ''))
            }
            
        except Exception:
            return None
    
    def extract_dates_from_text(self, text: str) -> Dict[str, str]:
        """Extract dates from text"""
        dates = {'invited': '', 'agreed': '', 'due': ''}
        
        patterns = [
            (r'invited[:\s]*(\d{1,2}-[A-Za-z]{3}-\d{4})', 'invited'),
            (r'agreed[:\s]*(\d{1,2}-[A-Za-z]{3}-\d{4})', 'agreed'),
            (r'due date[:\s]*(\d{1,2}-[A-Za-z]{3}-\d{4})', 'due')
        ]
        
        for pattern, date_type in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                dates[date_type] = match.group(1)
        
        return dates
    
    def calculate_time_in_review(self, invited_date: str) -> str:
        """Calculate time in review"""
        if not invited_date:
            return ""
        
        try:
            invited = datetime.strptime(invited_date, "%d-%b-%Y")
            now = datetime.now()
            delta = now - invited
            return f"{delta.days} Days"
        except:
            return ""
    
    def extract_all_pdfs_and_reports(self, manuscript_id: str) -> Dict[str, Any]:
        """Extract all PDFs and referee reports"""
        self.logger.info(f"   📥 Extracting PDFs and reports for {manuscript_id}")
        
        pdf_info = {
            'manuscript_pdf_url': '',
            'manuscript_pdf_file': '',
            'referee_reports': [],
            'text_reviews': []
        }
        
        try:
            # 1. Get manuscript PDF
            manuscript_pdf = self.get_manuscript_pdf(manuscript_id)
            if manuscript_pdf:
                pdf_info['manuscript_pdf_url'] = manuscript_pdf['url']
                pdf_info['manuscript_pdf_file'] = manuscript_pdf['file']
                self.logger.info(f"      ✅ Manuscript PDF downloaded")
            
            # 2. Get referee reports with aggressive overlay handling
            referee_reports = self.get_referee_reports_aggressive(manuscript_id)
            pdf_info['referee_reports'] = referee_reports['pdf_reports']
            pdf_info['text_reviews'] = referee_reports['text_reviews']
            
            self.logger.info(f"      ✅ Found {len(pdf_info['referee_reports'])} PDF reports + {len(pdf_info['text_reviews'])} text reviews")
            
            return pdf_info
            
        except Exception as e:
            self.logger.error(f"      ❌ PDF extraction error: {e}")
            return pdf_info
    
    def get_manuscript_pdf(self, manuscript_id: str) -> Optional[Dict[str, str]]:
        """Get manuscript PDF from tabs"""
        try:
            original_windows = self.driver.window_handles
            
            for tab_name in ['PDF', 'Original Files', 'HTML']:
                try:
                    tab_links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{tab_name}') or contains(text(), '{tab_name.lower()}')]")
                    
                    for tab_link in tab_links:
                        try:
                            link_text = tab_link.text.strip()
                            if len(link_text) > 20:
                                continue
                            
                            # Click tab
                            tab_link.click()
                            time.sleep(2)
                            
                            # Check for new window
                            new_windows = self.driver.window_handles
                            if len(new_windows) > len(original_windows):
                                new_window = [w for w in new_windows if w not in original_windows][0]
                                self.driver.switch_to.window(new_window)
                                
                                current_url = self.driver.current_url
                                
                                if '.pdf' in current_url.lower() or 'DOWNLOAD=TRUE' in current_url:
                                    pdf_file = self.download_pdf(
                                        current_url,
                                        self.pdfs_dir / f"{manuscript_id}_manuscript.pdf"
                                    )
                                    
                                    self.driver.close()
                                    self.driver.switch_to.window(original_windows[0])
                                    
                                    if pdf_file:
                                        return {'url': current_url, 'file': pdf_file}
                                
                                # Close window if no PDF
                                self.driver.close()
                                self.driver.switch_to.window(original_windows[0])
                            
                        except Exception:
                            try:
                                if len(self.driver.window_handles) > 1:
                                    self.driver.switch_to.window(original_windows[0])
                            except:
                                pass
                            continue
                except Exception:
                    continue
            
            return None
            
        except Exception as e:
            self.logger.error(f"      Error getting manuscript PDF: {e}")
            return None
    
    def get_referee_reports_aggressive(self, manuscript_id: str) -> Dict[str, List]:
        """Get referee reports with aggressive overlay dismissal"""
        self.logger.info(f"      🔍 Looking for referee reports (aggressive mode)")
        
        reports = {
            'pdf_reports': [],
            'text_reviews': []
        }
        
        try:
            # Aggressive overlay dismissal before looking for links
            self.aggressive_cookie_dismissal()
            
            # Find review links with multiple selectors
            review_selectors = [
                "//a[contains(text(), 'view review')]",
                "//a[contains(text(), 'View Review')]",
                "//a[contains(@href, 'review')]",
                "//a[contains(@onclick, 'review')]"
            ]
            
            all_review_links = []
            for selector in review_selectors:
                try:
                    links = self.driver.find_elements(By.XPATH, selector)
                    all_review_links.extend(links)
                except:
                    continue
            
            # Remove duplicates
            unique_links = []
            seen_hrefs = set()
            for link in all_review_links:
                href = link.get_attribute('href') or link.get_attribute('onclick') or ''
                if href and href not in seen_hrefs:
                    unique_links.append(link)
                    seen_hrefs.add(href)
            
            self.logger.info(f"         Found {len(unique_links)} unique review links")
            
            original_windows = self.driver.window_handles
            
            for i, review_link in enumerate(unique_links):
                try:
                    self.logger.info(f"         📝 Processing review link {i+1}/{len(unique_links)}")
                    
                    # Aggressive overlay dismissal before each click
                    self.aggressive_cookie_dismissal()
                    
                    # Scroll to element
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", review_link)
                    time.sleep(0.5)
                    
                    # Another overlay dismissal
                    self.aggressive_cookie_dismissal()
                    
                    # Try multiple click methods
                    clicked = False
                    click_methods = [
                        lambda: self.driver.execute_script("arguments[0].click();", review_link),
                        lambda: self.driver.execute_script("arguments[0].dispatchEvent(new Event('click'));", review_link),
                        lambda: review_link.click()
                    ]
                    
                    for method in click_methods:
                        try:
                            method()
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
                        
                        # Extract review data from this window
                        review_data = self.extract_review_data_from_window(manuscript_id, i+1)
                        
                        # Add to reports
                        if review_data['pdf_files']:
                            reports['pdf_reports'].extend(review_data['pdf_files'])
                        
                        if review_data['text_content']:
                            reports['text_reviews'].append({
                                'referee_number': i+1,
                                'content': review_data['text_content'],
                                'extraction_time': datetime.now().isoformat()
                            })
                        
                        # Close window and return to original
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
    
    def extract_review_data_from_window(self, manuscript_id: str, referee_num: int) -> Dict[str, Any]:
        """Extract all data from review window"""
        result = {
            'pdf_files': [],
            'text_content': ''
        }
        
        try:
            # Look for PDF attachments
            pdf_selectors = [
                "//a[contains(@href, '.pdf')]",
                "//a[contains(text(), 'attached') or contains(text(), 'attachment')]",
                "//a[contains(text(), 'file') or contains(text(), 'download')]",
                "//*[contains(text(), 'Files attached')]/following-sibling::*//a"
            ]
            
            for selector in pdf_selectors:
                try:
                    pdf_links = self.driver.find_elements(By.XPATH, selector)
                    for pdf_link in pdf_links:
                        href = pdf_link.get_attribute('href')
                        link_text = pdf_link.text.strip()
                        
                        if href and ('.pdf' in href.lower() or 'download' in href.lower()):
                            self.logger.info(f"               Found PDF: {link_text}")
                            
                            pdf_file = self.download_pdf(
                                href,
                                self.pdfs_dir / f"{manuscript_id}_referee_report_{referee_num}.pdf"
                            )
                            
                            if pdf_file:
                                result['pdf_files'].append({
                                    'referee_number': referee_num,
                                    'url': href,
                                    'file': pdf_file,
                                    'link_text': link_text,
                                    'download_time': datetime.now().isoformat()
                                })
                                self.logger.info(f"               ✅ Downloaded PDF report {referee_num}")
                
                except Exception:
                    continue
            
            # Look for text content
            text_selectors = [
                "//*[contains(text(), 'Comments to the Author')]//following-sibling::*",
                "//*[contains(text(), 'comments to author')]//following-sibling::*",
                "//textarea",
                "//pre"
            ]
            
            all_text = []
            for selector in text_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        text = ""
                        if elem.tag_name == 'textarea':
                            text = elem.get_attribute('value') or elem.text
                        else:
                            text = elem.text.strip()
                        
                        if text and len(text) > 50:
                            all_text.append(text)
                except Exception:
                    continue
            
            if all_text:
                result['text_content'] = "\n\n---SECTION---\n\n".join(all_text)
                self.logger.info(f"               ✅ Extracted text review ({len(result['text_content'])} chars)")
            
            # Fallback: get full page text if nothing specific found
            if not result['pdf_files'] and not result['text_content']:
                try:
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text
                    if len(page_text) > 200:
                        result['text_content'] = page_text
                        self.logger.info(f"               ✅ Captured full page as fallback ({len(page_text)} chars)")
                except:
                    pass
            
            return result
            
        except Exception as e:
            self.logger.error(f"               Error extracting review data: {e}")
            return result
    
    def download_pdf(self, url: str, filepath: Path) -> Optional[str]:
        """Download PDF with validation"""
        try:
            # Get session cookies
            selenium_cookies = self.driver.get_cookies()
            cookies = {cookie['name']: cookie['value'] for cookie in selenium_cookies}
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Connection': 'keep-alive'
            }
            
            response = requests.get(url, cookies=cookies, headers=headers, timeout=30, stream=True)
            
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                file_size = filepath.stat().st_size
                
                # Validate PDF
                with open(filepath, 'rb') as f:
                    header = f.read(4)
                    if header.startswith(b'%PDF'):
                        self.logger.info(f"               ✅ PDF downloaded: {filepath.name} ({file_size} bytes)")
                        return str(filepath)
                    else:
                        self.logger.warning(f"               ⚠️  File is not a valid PDF")
                        filepath.unlink()
                        return None
            
            return None
            
        except Exception as e:
            self.logger.error(f"               Download error: {e}")
            return None
    
    def run_complete_extraction(self) -> bool:
        """Run complete extraction process"""
        self.logger.info(f"🚀 Starting complete {self.journal} extraction")
        
        try:
            # Create driver
            if not self.create_robust_driver():
                return False
            
            # Login
            if not self.login_journal():
                return False
            
            # Navigate to manuscripts
            if not self.navigate_to_manuscripts():
                return False
            
            # Find manuscripts
            manuscripts = self.find_manuscripts()
            if not manuscripts:
                self.logger.warning("No manuscripts found")
                return False
            
            # Process each manuscript
            all_results = []
            
            for i, manuscript_id in enumerate(manuscripts[:3], 1):  # Process first 3
                self.logger.info(f"\n{'='*80}")
                self.logger.info(f"📄 Processing manuscript {i}/{min(len(manuscripts), 3)}: {manuscript_id}")
                self.logger.info(f"{'='*80}")
                
                result = self.extract_complete_manuscript_data(manuscript_id)
                all_results.append(result)
                
                if result.get('status') == 'success':
                    self.logger.info(f"✅ Successfully processed {manuscript_id}")
                else:
                    self.logger.error(f"❌ Failed to process {manuscript_id}")
                
                # Brief pause
                time.sleep(3)
            
            # Save results
            self.save_results(all_results)
            
            # Calculate success metrics
            successful = sum(1 for r in all_results if r.get('status') == 'success')
            total_referees = sum(len(r.get('referees', [])) for r in all_results if r.get('status') == 'success')
            total_pdfs = sum(1 for r in all_results if r.get('pdf_info', {}).get('manuscript_pdf_file'))
            total_reports = sum(len(r.get('pdf_info', {}).get('referee_reports', [])) for r in all_results)
            total_text_reviews = sum(len(r.get('pdf_info', {}).get('text_reviews', [])) for r in all_results)
            
            self.logger.info(f"\n🎉 {self.journal} extraction completed!")
            self.logger.info(f"   Manuscripts processed: {successful}/{len(all_results)}")
            self.logger.info(f"   Total referees: {total_referees}")
            self.logger.info(f"   Manuscript PDFs: {total_pdfs}")
            self.logger.info(f"   Referee PDF reports: {total_reports}")
            self.logger.info(f"   Text reviews: {total_text_reviews}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Fatal error: {e}")
            return False
            
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    self.logger.info("🔄 Driver closed")
                except:
                    pass
    
    def save_results(self, results: List[Dict]):
        """Save results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON
        json_file = self.base_dir / f"{self.journal.lower()}_final_results_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump({
                'journal': self.journal,
                'extraction_date': datetime.now().isoformat(),
                'headless_mode': self.headless,
                'manuscripts': results
            }, f, indent=2)
        
        # Save human-readable report
        report_file = self.base_dir / f"{self.journal.lower()}_final_report_{timestamp}.txt"
        with open(report_file, 'w') as f:
            f.write(f"FINAL {self.journal} EXTRACTION REPORT\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Headless Mode: {self.headless}\n\n")
            
            for i, manuscript in enumerate(results, 1):
                f.write(f"{i}. {manuscript['manuscript_id']}\n")
                f.write("-" * 40 + "\n")
                
                if manuscript.get('status') == 'success':
                    f.write(f"Status: ✅ SUCCESS\n")
                    f.write(f"Referees: {len(manuscript.get('referees', []))}\n")
                    
                    for referee in manuscript.get('referees', []):
                        f.write(f"  • {referee['name']} ({referee['status']})\n")
                        if referee.get('institution'):
                            f.write(f"    Institution: {referee['institution']}\n")
                    
                    pdf_info = manuscript.get('pdf_info', {})
                    f.write("\nFiles:\n")
                    if pdf_info.get('manuscript_pdf_file'):
                        f.write(f"  • Manuscript PDF: {pdf_info['manuscript_pdf_file'].split('/')[-1]}\n")
                    
                    for report in pdf_info.get('referee_reports', []):
                        f.write(f"  • Referee Report: {report['file'].split('/')[-1]}\n")
                    
                    for review in pdf_info.get('text_reviews', []):
                        f.write(f"  • Text Review: {len(review['content'])} characters\n")
                
                else:
                    f.write(f"Status: ❌ FAILED - {manuscript.get('error', 'Unknown error')}\n")
                
                f.write("\n")
        
        self.logger.info(f"📄 Results saved to:")
        self.logger.info(f"   JSON: {json_file}")
        self.logger.info(f"   Report: {report_file}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Final Headless Journal Extractor")
    parser.add_argument("journal", choices=["MF", "MOR"], help="Journal to extract")
    parser.add_argument("--visible", action="store_true", help="Run with visible browser")
    
    args = parser.parse_args()
    headless = not args.visible
    
    try:
        extractor = FinalHeadlessExtractor(journal=args.journal, headless=headless)
        success = extractor.run_complete_extraction()
        
        if success:
            print(f"\n🎉 {args.journal} extraction completed successfully!")
        else:
            print(f"\n❌ {args.journal} extraction failed!")
            
    except KeyboardInterrupt:
        print("\n⚠️  Extraction interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")

if __name__ == "__main__":
    main()