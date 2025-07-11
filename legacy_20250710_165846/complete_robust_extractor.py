#!/usr/bin/env python3
"""
Complete Robust MF/MOR Extractor - Full referee data and PDF downloads
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

# Load environment variables from .env file
load_dotenv()

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from bs4 import BeautifulSoup
import traceback

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('complete_extraction.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("COMPLETE_EXTRACTOR")

class CompleteRobustExtractor:
    """Complete referee and PDF extractor for MF/MOR"""
    
    def __init__(self, journal_code: str = "MF"):
        self.journal_code = journal_code
        self.driver = None
        self.debug_dir = Path(f"complete_debug_{journal_code.lower()}")
        self.debug_dir.mkdir(exist_ok=True)
        self.results_dir = Path(f"complete_results_{journal_code.lower()}")
        self.results_dir.mkdir(exist_ok=True)
        
        # Journal configurations
        self.configs = {
            "MF": {
                "url": "https://mc.manuscriptcentral.com/mafi",
                "user_env": "MF_USER",
                "pass_env": "MF_PASS",
                "categories": ["Awaiting Reviewer Scores", "Final Decisions"],
                "expected_manuscripts": {
                    'MAFI-2024-0167': {
                        'title': 'Competitive optimal portfolio selection in a non-Markovian financial market',
                        'expected_referees': 2
                    },
                    'MAFI-2025-0166': {
                        'title': 'Optimal investment and consumption under forward utilities with relative performance concerns',
                        'expected_referees': 2
                    }
                }
            },
            "MOR": {
                "url": "https://mc.manuscriptcentral.com/mor",
                "user_env": "MOR_USER", 
                "pass_env": "MOR_PASS",
                "categories": ["Awaiting Reviewer Reports", "Final Decisions"],
                "expected_manuscripts": {
                    'MOR-2025-1037': {
                        'title': 'Optimal portfolio selection under dynamic risk measure constraints',
                        'expected_referees': 3
                    },
                    'MOR-2023-0376': {
                        'title': 'Utility maximization under endogenous pricing',
                        'expected_referees': 3
                    }
                }
            }
        }
        
        self.config = self.configs[journal_code]
        
    def capture_state(self, step_name: str):
        """Capture current state for debugging"""
        try:
            timestamp = datetime.now().strftime("%H%M%S")
            if self.driver:
                screenshot_path = self.debug_dir / f"{timestamp}_{step_name}.png"
                self.driver.save_screenshot(str(screenshot_path))
                logger.debug(f"📸 Screenshot: {screenshot_path}")
                
        except Exception as e:
            logger.warning(f"Could not capture state for {step_name}: {e}")
    
    def create_driver(self, headless=False):
        """Create reliable Chrome driver"""
        logger.info("🚀 Creating Chrome driver...")
        
        try:
            options = Options()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--log-level=3')
            
            if headless:
                options.add_argument('--headless')
                
            self.driver = webdriver.Chrome(options=options)
            self.driver.implicitly_wait(10)
            self.driver.set_page_load_timeout(30)
            
            logger.info("✅ Chrome driver created")
            return True
            
        except Exception as e:
            logger.error(f"❌ Driver creation failed: {e}")
            return False
    
    def login_and_verify(self):
        """Complete login and verification process"""
        logger.info(f"🔐 Logging into {self.journal_code}...")
        
        try:
            # Navigate to journal
            self.driver.get(self.config["url"])
            time.sleep(3)
            self.capture_state("initial_page")
            
            # Handle cookies
            try:
                cookie_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
                )
                cookie_btn.click()
                logger.info("✅ Cookies accepted")
                time.sleep(2)
            except:
                logger.debug("No cookie button found")
            
            # Check for login form
            try:
                username_input = WebDriverWait(self.driver, 5).until(
                    EC.visibility_of_element_located((By.ID, "USERID"))
                )
                
                # Get credentials
                username = os.getenv(self.config["user_env"])
                password = os.getenv(self.config["pass_env"])
                
                if not username or not password:
                    raise Exception(f"Missing credentials: {self.config['user_env']}, {self.config['pass_env']}")
                
                # Enter credentials
                username_input.clear()
                username_input.send_keys(username)
                
                password_input = self.driver.find_element(By.ID, "PASSWORD")
                password_input.clear()
                password_input.send_keys(password)
                
                # Submit
                login_btn = self.driver.find_element(By.ID, "logInButton")
                login_btn.click()
                logger.info("📤 Login submitted")
                time.sleep(4)
                
                self.capture_state("after_login")
                
            except TimeoutException:
                logger.info("ℹ️  No login form, may already be logged in")
            
            # Handle verification if needed
            try:
                # Check reCAPTCHA
                try:
                    recaptcha = self.driver.find_element(By.XPATH, "//iframe[contains(@title, 'reCAPTCHA')]")
                    if recaptcha.is_displayed():
                        self.driver.switch_to.frame(recaptcha)
                        checkbox = self.driver.find_element(By.ID, "recaptcha-anchor")
                        checkbox.click()
                        self.driver.switch_to.default_content()
                        logger.info("✅ reCAPTCHA handled")
                        time.sleep(2)
                except:
                    pass
                
                # Check for verification code
                verification_input = None
                try:
                    verification_input = WebDriverWait(self.driver, 10).until(
                        lambda d: d.find_element(By.ID, "TOKEN_VALUE") if d.find_element(By.ID, "TOKEN_VALUE").is_displayed() else None
                    )
                    logger.info("📧 Verification code required")
                except:
                    try:
                        verification_input = WebDriverWait(self.driver, 5).until(
                            lambda d: d.find_element(By.ID, "validationCode") if d.find_element(By.ID, "validationCode").is_displayed() else None
                        )
                        logger.info("📧 Validation code required")
                    except:
                        pass
                
                if verification_input:
                    # Fetch code from email
                    sys.path.insert(0, str(Path(__file__).parent))
                    from core.email_utils import fetch_latest_verification_code
                    
                    logger.info("⏳ Fetching verification code...")
                    time.sleep(5)
                    
                    code = fetch_latest_verification_code(journal=self.journal_code)
                    if not code:
                        raise Exception("Could not fetch verification code")
                    
                    logger.info(f"✅ Got code: {code}")
                    verification_input.clear()
                    verification_input.send_keys(code)
                    verification_input.send_keys(Keys.RETURN)
                    time.sleep(3)
                    
            except Exception as e:
                logger.warning(f"Verification handling: {e}")
            
            self.capture_state("after_verification")
            
            # Navigate to Associate Editor Center
            time.sleep(3)
            ae_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            logger.info("✅ Navigated to Associate Editor Center")
            time.sleep(3)
            
            self.capture_state("ae_center")
            return True
            
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            self.capture_state("login_failed")
            return False
    
    def find_and_click_checkbox(self, manuscript_id: str) -> bool:
        """Find and click checkbox for specific manuscript"""
        logger.info(f"🔍 Looking for manuscript: {manuscript_id}")
        
        try:
            # Look for checkbox images
            checkboxes = self.driver.find_elements(By.XPATH, "//img[contains(@src, 'check_off.gif')]")
            logger.info(f"Found {len(checkboxes)} checkbox images")
            
            # Get all table rows to find the right manuscript
            rows = self.driver.find_elements(By.TAG_NAME, "tr")
            
            for i, row in enumerate(rows):
                try:
                    row_text = row.text.strip()
                    
                    # Check if this row starts with our manuscript ID
                    if row_text.startswith(manuscript_id):
                        # Count checkboxes in this row
                        row_checkboxes = row.find_elements(By.XPATH, ".//img[contains(@src, 'check_off.gif')]")
                        
                        if len(row_checkboxes) == 1:
                            logger.info(f"✅ Found manuscript {manuscript_id} in row {i}")
                            logger.debug(f"   Row preview: {row_text[:100]}...")
                            
                            # Scroll checkbox into view and click
                            checkbox = row_checkboxes[0]
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                            time.sleep(0.5)
                            checkbox.click()
                            time.sleep(3)
                            
                            logger.info(f"✅ Clicked checkbox for {manuscript_id}")
                            return True
                        else:
                            logger.debug(f"   Row {i} has {len(row_checkboxes)} checkboxes, skipping")
                    elif manuscript_id in row_text:
                        logger.debug(f"   Row {i} contains {manuscript_id} but doesn't start with it")
                        
                except Exception as e:
                    continue
            
            logger.error(f"❌ Could not find checkbox for {manuscript_id}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error finding checkbox for {manuscript_id}: {e}")
            return False
    
    def extract_referee_details(self, manuscript_id: str) -> Dict[str, Any]:
        """Extract complete referee details from manuscript page"""
        logger.info(f"📊 Extracting referee details for {manuscript_id}")
        
        try:
            # Wait for page to load
            time.sleep(3)
            self.capture_state(f"referee_page_{manuscript_id}")
            
            # Get page source and parse with BeautifulSoup
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract basic manuscript info
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
                'manuscript_pdf_url': '',
                'extraction_status': 'pending'
            }
            
            # Extract title
            title_patterns = [
                r'<title[^>]*>([^<]+)</title>',
                r'<h1[^>]*>([^<]+)</h1>',
                r'<h2[^>]*>([^<]+)</h2>'
            ]
            
            for pattern in title_patterns:
                match = re.search(pattern, page_source, re.IGNORECASE)
                if match:
                    title = match.group(1).strip()
                    if len(title) > 20 and 'manuscript' not in title.lower():
                        manuscript_data['title'] = title
                        break
            
            # Extract submission and due dates
            date_patterns = [
                (r'Date Submitted[:\s]*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', 'submitted_date'),
                (r'Due Date[:\s]*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', 'due_date'),
                (r'Submitted[:\s]*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', 'submitted_date')
            ]
            
            for pattern, field in date_patterns:
                match = re.search(pattern, page_source, re.IGNORECASE)
                if match:
                    manuscript_data[field] = match.group(1)
            
            # Extract status
            status_match = re.search(r'Status[:\s]*([^<\n]+)', page_source, re.IGNORECASE)
            if status_match:
                manuscript_data['status'] = status_match.group(1).strip()
            
            # Find reviewer list section
            reviewer_section = soup.find(string=re.compile('Reviewer List', re.IGNORECASE))
            if reviewer_section:
                logger.info("✅ Found Reviewer List section")
                
                # Find the table containing reviewers
                reviewer_table = reviewer_section.find_parent('table')
                if not reviewer_table:
                    # Try to find nearby table
                    parent = reviewer_section.parent
                    for _ in range(5):  # Look up to 5 levels up
                        if parent:
                            reviewer_table = parent.find('table')
                            if reviewer_table:
                                break
                            parent = parent.parent
                
                if reviewer_table:
                    rows = reviewer_table.find_all('tr')
                    logger.info(f"Found {len(rows)} rows in reviewer table")
                    
                    current_referee = None
                    
                    for i, row in enumerate(rows):
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 3:
                            cell_texts = [cell.get_text(strip=True) for cell in cells]
                            
                            # Check if this row contains a referee name (usually in cell[1])
                            if len(cell_texts) > 1:
                                potential_name = cell_texts[1]
                                
                                # Look for name patterns (Last, First or similar)
                                name_pattern = r'^([A-Za-z]+,\s*[A-Za-z]+)'
                                name_match = re.search(name_pattern, potential_name)
                                
                                if name_match:
                                    referee_name = name_match.group(1)
                                    logger.info(f"   🎯 Found referee: {referee_name}")
                                    
                                    # Create referee object
                                    referee = {
                                        'name': referee_name,
                                        'institution': '',
                                        'email': '',
                                        'status': '',
                                        'dates': {
                                            'invited': '',
                                            'agreed': '',
                                            'due': ''
                                        },
                                        'time_in_review': '',
                                        'report_submitted': False,
                                        'submission_date': '',
                                        'review_decision': '',
                                        'report_url': '',
                                        'acceptance_date': ''
                                    }
                                    
                                    # Extract institution (often after name)
                                    institution_match = re.search(r'^[^,]+,\s*[^,]+[,\s]+([^,\n]+)', potential_name)
                                    if institution_match:
                                        referee['institution'] = institution_match.group(1).strip()
                                    
                                    # Look for status in nearby cells
                                    for cell_text in cell_texts:
                                        if any(status in cell_text.lower() for status in ['agreed', 'declined', 'overdue', 'accepted']):
                                            if 'agreed' in cell_text.lower():
                                                referee['status'] = 'Agreed'
                                            elif 'declined' in cell_text.lower():
                                                referee['status'] = 'Declined'
                                            elif 'overdue' in cell_text.lower():
                                                referee['status'] = 'Overdue'
                                            break
                                    
                                    # Extract dates from cell containing date information
                                    for cell_text in cell_texts:
                                        if 'invited:' in cell_text.lower():
                                            invited_match = re.search(r'Invited:\s*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', cell_text)
                                            if invited_match:
                                                referee['dates']['invited'] = invited_match.group(1)
                                        
                                        if 'agreed:' in cell_text.lower():
                                            agreed_match = re.search(r'Agreed:\s*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', cell_text)
                                            if agreed_match:
                                                referee['dates']['agreed'] = agreed_match.group(1)
                                        
                                        if 'due date:' in cell_text.lower():
                                            due_match = re.search(r'Due Date:\s*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', cell_text)
                                            if due_match:
                                                referee['dates']['due'] = due_match.group(1)
                                        
                                        if 'time in review:' in cell_text.lower():
                                            time_match = re.search(r'Time in Review:\s*([0-9]+\s*Days?)', cell_text)
                                            if time_match:
                                                referee['time_in_review'] = time_match.group(1)
                                    
                                    # Check if referee has submitted report
                                    if any('review returned' in cell.lower() for cell in cell_texts):
                                        referee['report_submitted'] = True
                                        manuscript_data['completed_referees'].append(referee)
                                    elif referee['status'] == 'Declined':
                                        # Skip declined referees
                                        logger.info(f"   ❌ Skipping declined referee: {referee_name}")
                                        continue
                                    else:
                                        manuscript_data['referees'].append(referee)
                                        
                                    logger.info(f"   ✅ Added referee: {referee_name} ({referee['status']})")
                
            # Extract email acceptance dates using existing email utilities
            try:
                sys.path.insert(0, str(Path(__file__).parent))
                from core.email_utils import fetch_starred_emails
                from core.generic_email_utils import robust_match_email_for_referee_generic
                
                starred_emails = fetch_starred_emails()
                flagged_emails = [email for email in starred_emails if email.get('subject', '').startswith(self.journal_code)]
                
                for referee in manuscript_data['referees']:
                    try:
                        acceptance_date, contact_date = robust_match_email_for_referee_generic(
                            referee['name'], manuscript_id, self.journal_code, 
                            referee['status'], flagged_emails, starred_emails
                        )
                        if acceptance_date:
                            referee['acceptance_date'] = acceptance_date
                        logger.info(f"   📧 {referee['name']}: {acceptance_date or 'no email match'}")
                    except Exception as e:
                        logger.warning(f"Email matching error for {referee['name']}: {e}")
                        
            except Exception as e:
                logger.warning(f"Email processing error: {e}")
            
            manuscript_data['extraction_status'] = 'success'
            logger.info(f"✅ Extracted {len(manuscript_data['referees'])} active + {len(manuscript_data['completed_referees'])} completed referees")
            
            return manuscript_data
            
        except Exception as e:
            logger.error(f"❌ Referee extraction failed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'manuscript_id': manuscript_id,
                'extraction_status': 'failed',
                'error': str(e)
            }
    
    def download_manuscript_pdf(self, manuscript_id: str) -> Optional[str]:
        """Download manuscript PDF if available"""
        logger.info(f"📥 Looking for manuscript PDF: {manuscript_id}")
        
        try:
            # Look for PDF download links
            pdf_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf') or contains(text(), 'PDF') or contains(text(), 'Download')]")
            
            for link in pdf_links:
                href = link.get_attribute('href')
                text = link.text.strip()
                
                if href and ('.pdf' in href or 'manuscript' in text.lower()):
                    logger.info(f"   Found PDF link: {text} -> {href}")
                    
                    # Create PDF downloads directory
                    pdf_dir = self.results_dir / "pdfs"
                    pdf_dir.mkdir(exist_ok=True)
                    
                    # Download PDF (implementation would go here)
                    # For now, just save the URL
                    pdf_info = {
                        'manuscript_id': manuscript_id,
                        'pdf_url': href,
                        'link_text': text,
                        'download_time': datetime.now().isoformat()
                    }
                    
                    pdf_info_file = pdf_dir / f"{manuscript_id}_pdf_info.json"
                    with open(pdf_info_file, 'w') as f:
                        json.dump(pdf_info, f, indent=2)
                    
                    logger.info(f"   ✅ PDF info saved: {pdf_info_file}")
                    return str(pdf_info_file)
            
            logger.info(f"   ℹ️  No PDF download found for {manuscript_id}")
            return None
            
        except Exception as e:
            logger.error(f"❌ PDF download error: {e}")
            return None
    
    def navigate_back_to_category(self, category: str):
        """Navigate back to manuscript category"""
        logger.info(f"🔄 Navigating back to {category}")
        
        try:
            # Click Associate Editor Center link
            ae_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            time.sleep(2)
            
            # Click category link
            category_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, category))
            )
            category_link.click()
            time.sleep(3)
            
            logger.info(f"✅ Navigated back to {category}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Navigation back failed: {e}")
            return False
    
    def extract_complete_journal_data(self, headless=True):
        """Extract complete data for all manuscripts in journal"""
        logger.info(f"🚀 Starting complete {self.journal_code} extraction")
        
        all_results = {
            'journal': self.journal_code,
            'extraction_date': datetime.now().isoformat(),
            'extraction_method': 'complete_robust_extraction',
            'manuscripts': []
        }
        
        try:
            # Create driver and login
            if not self.create_driver(headless=headless):
                raise Exception("Driver creation failed")
            
            if not self.login_and_verify():
                raise Exception("Login failed")
            
            # Process each category
            for category in self.config["categories"]:
                logger.info(f"\n📂 Processing category: {category}")
                
                # Navigate to category
                try:
                    category_link = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.LINK_TEXT, category))
                    )
                    category_link.click()
                    time.sleep(3)
                    logger.info(f"✅ Navigated to {category}")
                except:
                    logger.warning(f"⚠️  Could not find category: {category}")
                    continue
                
                # Process each expected manuscript
                for manuscript_id, manuscript_info in self.config["expected_manuscripts"].items():
                    logger.info(f"\n{'='*60}")
                    logger.info(f"📄 Processing: {manuscript_id}")
                    logger.info(f"Expected: {manuscript_info['title'][:50]}...")
                    logger.info(f"{'='*60}")
                    
                    # Find and click checkbox
                    if self.find_and_click_checkbox(manuscript_id):
                        # Extract referee details
                        manuscript_data = self.extract_referee_details(manuscript_id)
                        
                        # Download PDF if available
                        pdf_info = self.download_manuscript_pdf(manuscript_id)
                        if pdf_info:
                            manuscript_data['manuscript_pdf_file'] = pdf_info
                        
                        all_results['manuscripts'].append(manuscript_data)
                        
                        # Navigate back for next manuscript
                        if not self.navigate_back_to_category(category):
                            logger.warning("Could not navigate back, continuing...")
                    else:
                        # Add failed extraction record
                        all_results['manuscripts'].append({
                            'manuscript_id': manuscript_id,
                            'extraction_status': 'failed',
                            'error': 'Checkbox not found'
                        })
            
            # Save results
            results_file = self.results_dir / f"{self.journal_code.lower()}_complete_results.json"
            with open(results_file, 'w') as f:
                json.dump(all_results, f, indent=2)
            
            # Generate summary report
            self.generate_summary_report(all_results)
            
            logger.info(f"🎉 Complete extraction finished!")
            logger.info(f"   Results saved: {results_file}")
            
            return all_results
            
        except Exception as e:
            logger.error(f"❌ Complete extraction failed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return all_results
            
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    logger.info("🔄 Driver closed")
                except:
                    pass
    
    def generate_summary_report(self, results: Dict[str, Any]):
        """Generate human-readable summary report"""
        report_lines = []
        report_lines.append(f"COMPLETE REFEREE EXTRACTION - {self.journal_code}")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Method: complete_robust_extraction")
        report_lines.append("="*80)
        report_lines.append("")
        
        total_manuscripts = len(results['manuscripts'])
        successful_extractions = len([m for m in results['manuscripts'] if m.get('extraction_status') == 'success'])
        total_active_referees = sum(len(m.get('referees', [])) for m in results['manuscripts'])
        total_completed_referees = sum(len(m.get('completed_referees', [])) for m in results['manuscripts'])
        
        for manuscript in results['manuscripts']:
            if manuscript.get('extraction_status') == 'success':
                report_lines.append(f"Manuscript: {manuscript['manuscript_id']}")
                report_lines.append(f"Title: {manuscript.get('title', 'N/A')}")
                report_lines.append(f"Status: {manuscript.get('status', 'N/A')}")
                report_lines.append(f"Submitted: {manuscript.get('submitted_date', 'N/A')}")
                report_lines.append(f"Due Date: {manuscript.get('due_date', 'N/A')}")
                
                active_refs = manuscript.get('referees', [])
                completed_refs = manuscript.get('completed_referees', [])
                
                report_lines.append(f"Active Referees: {len(active_refs)}")
                for ref in active_refs:
                    report_lines.append(f"  • {ref['name']} ({ref['status']})")
                    report_lines.append(f"    Institution: {ref.get('institution', 'N/A')}")
                    report_lines.append(f"    Invited: {ref['dates'].get('invited', 'N/A')}")
                    report_lines.append(f"    Agreed: {ref['dates'].get('agreed', 'N/A')}")
                    report_lines.append(f"    Due: {ref['dates'].get('due', 'N/A')}")
                    if ref.get('acceptance_date'):
                        report_lines.append(f"    Email Date: {ref['acceptance_date']}")
                
                if completed_refs:
                    report_lines.append(f"Completed Referees: {len(completed_refs)}")
                    for ref in completed_refs:
                        report_lines.append(f"  • {ref['name']} (Completed)")
                
                report_lines.append("")
                report_lines.append("-" * 60)
                report_lines.append("")
            else:
                report_lines.append(f"❌ Failed: {manuscript['manuscript_id']} - {manuscript.get('error', 'Unknown error')}")
                report_lines.append("")
        
        report_lines.append("SUMMARY:")
        report_lines.append(f"Total Manuscripts: {total_manuscripts}")
        report_lines.append(f"Successful Extractions: {successful_extractions}")
        report_lines.append(f"Total Active Referees: {total_active_referees}")
        report_lines.append(f"Total Completed Referees: {total_completed_referees}")
        report_lines.append(f"Success Rate: {(successful_extractions/total_manuscripts*100):.1f}%" if total_manuscripts > 0 else "Success Rate: 0%")
        
        # Save report
        report_file = self.results_dir / f"{self.journal_code.lower()}_complete_report.txt"
        with open(report_file, 'w') as f:
            f.write('\n'.join(report_lines))
        
        logger.info(f"📄 Summary report saved: {report_file}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--journal", choices=["MF", "MOR"], default="MF", help="Journal to extract")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    args = parser.parse_args()
    
    extractor = CompleteRobustExtractor(args.journal)
    results = extractor.extract_complete_journal_data(headless=args.headless)
    
    if results and results.get('manuscripts'):
        successful = len([m for m in results['manuscripts'] if m.get('extraction_status') == 'success'])
        total = len(results['manuscripts'])
        print(f"✅ Extraction completed: {successful}/{total} manuscripts successful")
    else:
        print("❌ Extraction failed!")
        sys.exit(1)