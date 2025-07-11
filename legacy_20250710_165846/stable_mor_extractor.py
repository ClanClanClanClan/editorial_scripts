#!/usr/bin/env python3
"""
Stable MOR Extractor - Using exact working MF approach for MOR
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

# Load environment variables
load_dotenv()

# Import exact same driver approach as working MF system
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
        logging.FileHandler('stable_mor_extraction.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("STABLE_MOR_EXTRACTOR")

class StableMORExtractor:
    """Stable MOR extractor using exact working MF approach"""
    
    def __init__(self):
        self.driver = None
        self.debug_dir = Path("stable_mor_debug")
        self.debug_dir.mkdir(exist_ok=True)
        self.results_dir = Path("stable_mor_results")
        self.results_dir.mkdir(exist_ok=True)
        
        # Expected manuscripts for MOR (from working system data)
        self.expected_manuscripts = {
            'MOR-2025-1037': {
                'title': 'Optimal portfolio selection under dynamic risk measure constraints',
                'expected_referees': 3
            },
            'MOR-2023-0376': {
                'title': 'Utility maximization under endogenous pricing',
                'expected_referees': 3
            }
        }
    
    def create_driver(self, headless=False):
        """Create driver with multiple fallback approaches (exact same as working MF)"""
        logger.info("🚀 Creating Chrome driver with fallback approaches")
        
        # Try approach 1: undetected chromedriver (like working system)
        try:
            logger.info("   Attempting undetected chromedriver...")
            options = uc.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            
            if headless:
                options.add_argument('--headless')
            
            # Try different version strategies
            for version_strategy in [None, 126, 125]:
                try:
                    logger.info(f"     Trying version_main={version_strategy}")
                    self.driver = uc.Chrome(options=options, version_main=version_strategy)
                    logger.info("✅ Undetected Chrome driver created successfully")
                    return True
                except Exception as e:
                    logger.debug(f"     Version {version_strategy} failed: {e}")
                    continue
                    
        except Exception as e:
            logger.warning(f"Undetected chromedriver failed: {e}")
        
        # Try approach 2: Regular Chrome driver (fallback)
        try:
            logger.info("   Attempting regular Chrome driver...")
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            
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
            
            logger.info("✅ Regular Chrome driver created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Regular Chrome driver failed: {e}")
        
        logger.error("❌ All driver creation methods failed")
        return False
    
    def login_mor(self):
        """Login to MOR using exact working MF approach"""
        logger.info("🔐 Logging into MOR (exact working system approach)")
        
        try:
            # Navigate to MOR (exact same approach as MF)
            mor_url = "https://mc.manuscriptcentral.com/mor"
            logger.info(f"Navigating to MOR dashboard: {mor_url}")
            self.driver.get(mor_url)
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
            
            # Get credentials (using MOR env vars)
            user = os.environ.get("MOR_USER")
            pw = os.environ.get("MOR_PASS")
            if not user or not pw:
                raise RuntimeError("MOR_USER and MOR_PASS environment variables must be set.")
            
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
                    
                    # Import exact same email function (but use MOR journal)
                    sys.path.insert(0, str(Path(__file__).parent))
                    from core.email_utils import fetch_latest_verification_code
                    
                    # Wait and fetch code (exact same timing)
                    logger.info("Waiting 5 seconds for verification email to arrive...")
                    time.sleep(5)
                    
                    verification_code = fetch_latest_verification_code(journal="MOR")
                    
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
            logger.error(f"❌ MOR login failed: {e}")
            return False
    
    def navigate_to_ae_center(self):
        """Navigate to Associate Editor Center (exact working system approach)"""
        logger.info("🔍 Navigating to Associate Editor Center...")
        
        try:
            # Navigate to AE Center (exact same approach)
            ae_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            time.sleep(3)
            
            logger.info("✅ Successfully navigated to Associate Editor Center")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to navigate to AE Center: {e}")
            return False
    
    def navigate_to_category(self, category="Awaiting Reviewer Reports"):
        """Navigate to specific category (MOR uses different default category)"""
        logger.info(f"📂 Navigating to: {category}")
        
        try:
            category_link = self.driver.find_element(By.LINK_TEXT, category)
            category_link.click()
            time.sleep(3)
            
            logger.info(f"✅ Successfully navigated to {category}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to navigate to category '{category}': {e}")
            return False
    
    def find_and_click_manuscript_checkbox(self, manuscript_id):
        """Find and click manuscript checkbox (exact working system approach)"""
        logger.info(f"🔍 Looking for manuscript checkbox: {manuscript_id}")
        
        try:
            # Look for checkbox images (exact same approach)
            checkboxes = self.driver.find_elements(By.XPATH, "//img[contains(@src, 'check_off.gif')]")
            logger.info(f"Found {len(checkboxes)} checkbox images")
            
            if not checkboxes:
                logger.error("No checkbox images found on page")
                return False
            
            # Get all table rows (exact same approach)
            rows = self.driver.find_elements(By.TAG_NAME, "tr")
            found_checkbox = False
            
            for i, row in enumerate(rows):
                try:
                    row_text = row.text.strip()
                    
                    # Check if row starts with manuscript ID (exact same logic)
                    if row_text.startswith(manuscript_id):
                        row_checkboxes = row.find_elements(By.XPATH, ".//img[contains(@src, 'check_off.gif')]")
                        
                        if len(row_checkboxes) == 1:
                            logger.info(f"✅ Found manuscript data for {manuscript_id} in row {i}")
                            logger.info(f"   Row preview: {row_text[:100]}...")
                            
                            found_checkbox = row_checkboxes[0]
                            break
                        else:
                            logger.info(f"   Skipping row {i} (wrong checkbox count: {len(row_checkboxes)}): {row_text[:50]}...")
                    elif manuscript_id in row_text:
                        logger.info(f"   Skipping row {i} (contains but doesn't start with {manuscript_id}): {row_text[:50]}...")
                        
                except Exception as e:
                    continue
            
            if found_checkbox:
                logger.info(f"✅ Clicking checkbox for {manuscript_id}")
                
                # Scroll checkbox into view (exact same approach)
                self.driver.execute_script("arguments[0].scrollIntoView(true);", found_checkbox)
                time.sleep(0.5)
                
                # Click the checkbox
                found_checkbox.click()
                time.sleep(3)
                
                # Log current URL
                current_url = self.driver.current_url
                logger.info(f"Navigated to: {current_url}")
                
                return True
            else:
                logger.error(f"❌ Could not find checkbox for {manuscript_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error finding checkbox for {manuscript_id}: {e}")
            return False
    
    def extract_referee_details(self, manuscript_id):
        """Extract referee details (exact working system approach)"""
        logger.info(f"📊 Extracting referee details for {manuscript_id}...")
        
        manuscript_data = {
            'manuscript_id': manuscript_id,
            'title': '',
            'submitted_date': '',
            'due_date': '',
            'status': '',
            'referees': [],
            'completed_referees': [],
            'extraction_status': 'pending'
        }
        
        try:
            # Get page source and parse (exact same approach)
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract title (exact same patterns)
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', page_source, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
                if 'manuscript' not in title.lower() and len(title) > 10:
                    manuscript_data['title'] = title
                    logger.info(f"📄 Title: {title[:50]}...")
            
            # Extract dates (exact same patterns)
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
            
            # Find reviewer list (EXACT same approach as working system)
            reviewer_list_header = soup.find(string=re.compile('Reviewer List', re.IGNORECASE))
            if reviewer_list_header:
                logger.info("✅ Found Reviewer List section")
                
                # Find the table containing reviewer information (EXACT same approach)
                reviewer_section = reviewer_list_header.find_parent()
                while reviewer_section and reviewer_section.name != 'table':
                    reviewer_section = reviewer_section.find_next('table')
                
                if reviewer_section:
                    # Find all rows in the reviewer table
                    rows = reviewer_section.find_all('tr')
                    logger.info(f"Found {len(rows)} rows in reviewer table")
                    
                    referees = []
                    
                    for i, row in enumerate(rows[1:], 1):  # Skip header row (EXACT same)
                        cells = row.find_all('td')
                        
                        if len(cells) >= 4:  # Minimum columns needed (EXACT same)
                            # Extract name - simplified and direct approach
                            name_cell = None
                            name = ''
                            name_cell_full_text = ''
                            
                            # Look for name patterns in the first few cells (EXACT same)
                            for cell_idx, cell in enumerate(cells[:5]):  # Check first 5 columns only
                                cell_text = cell.get_text(strip=True)
                                
                                logger.info(f"      🔍 Cell[{cell_idx}]: '{cell_text[:100]}'")
                                
                                # Skip obvious non-name cells (EXACT same)
                                if any(skip in cell_text.lower() for skip in ['security reasons', 'time out', 'session', 'revision', 'rescind']):
                                    logger.info(f"      ❌ Skipping cell[{cell_idx}] - contains excluded keyword")
                                    continue
                                
                                # Look for pattern: "LastName, FirstName" and extract properly
                                # Handle patterns like "Mastrolia, ThibautUC Berkeley" or "Liang, GechunUniversity of Warwick"
                                
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
                                                name_cell = cell_idx
                                                name_cell_full_text = cell_text
                                                name_found = True
                                                logger.info(f"      🎯 Found clean name: '{name}' using pattern {name_patterns.index(pattern)+1} in cell[{cell_idx}]")
                                                break
                                
                                if name_found:
                                    break
                            
                            if name:
                                # Create referee object (EXACT same structure)
                                referee = {
                                    'name': name,
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
                                
                                # Debug: Analyze all cells for this referee (EXACT same)
                                logger.info(f"      🔍 DEBUG: Analyzing {len(cells)} cells for referee '{name}'")
                                for debug_idx, debug_cell in enumerate(cells):
                                    debug_text = debug_cell.get_text(strip=True)
                                    logger.info(f"         Cell[{debug_idx}]: '{debug_text[:80]}'")
                                
                                # Extract status (EXACT same logic)
                                status_found = False
                                for cell in cells:
                                    cell_text = cell.get_text(strip=True).lower()
                                    
                                    # Check for decision keywords (EXACT same)
                                    decision_keywords = ['accept', 'reject', 'major revision', 'minor revision']
                                    for keyword in decision_keywords:
                                        if keyword in cell_text:
                                            referee['review_decision'] = keyword.title()
                                            referee['report_submitted'] = True
                                            logger.info(f"         📋 Decision: {referee['review_decision']}")
                                            status_found = True
                                            break
                                    
                                    if status_found:
                                        break
                                    
                                    # Check for status keywords (EXACT same)
                                    if 'agreed' in cell_text or 'accepted' in cell_text:
                                        referee['status'] = 'Agreed'
                                        logger.info(f"         ✅ FOUND STATUS: 'Agreed' (matched '{cell_text[:20]}')")
                                        status_found = True
                                        break
                                    elif 'declined' in cell_text:
                                        referee['status'] = 'Declined'
                                        logger.info(f"         ❌ FOUND STATUS: 'Declined'")
                                        status_found = True
                                        break
                                
                                if not status_found:
                                    # Look for other status indicators (EXACT same)
                                    for cell in cells:
                                        cell_text = cell.get_text(strip=True)
                                        if cell_text.isdigit() or any(char.isdigit() for char in cell_text[:5]):
                                            logger.info(f"         ⚠️  No decision keyword found, looking for other status indicators")
                                            logger.info(f"         📄 Using status: '{cell_text}'")
                                            referee['status'] = cell_text
                                            break
                                
                                # Extract dates (EXACT same patterns)
                                for cell in cells:
                                    cell_text = cell.get_text(strip=True)
                                    
                                    invited_match = re.search(r'Invited:\s*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', cell_text)
                                    if invited_match:
                                        referee['dates']['invited'] = invited_match.group(1)
                                        logger.info(f"     📅 Invited date: {referee['dates']['invited']}")
                                    
                                    agreed_match = re.search(r'Agreed:\s*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', cell_text)
                                    if agreed_match:
                                        referee['dates']['agreed'] = agreed_match.group(1)
                                        logger.info(f"     📅 Agreed date: {referee['dates']['agreed']}")
                                    
                                    due_match = re.search(r'Due Date:\s*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', cell_text)
                                    if due_match:
                                        referee['dates']['due'] = due_match.group(1)
                                        logger.info(f"     📅 Due date: {referee['dates']['due']}")
                                    
                                    time_match = re.search(r'Time in Review:\s*([0-9]+\s*Days?)', cell_text)
                                    if time_match:
                                        referee['time_in_review'] = time_match.group(1)
                                        logger.info(f"     ⏱️  Time in review: {referee['time_in_review']}")
                                    
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
                                                logger.info(f"     🏛️  Institution from name cell: {referee['institution']}")
                                    
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
                                                    logger.info(f"     🏛️  Institution from other cell: {referee['institution']}")
                                                    break
                                
                                # Skip unavailable/declined referees (EXACT same logic)
                                skip_keywords = ['unavailable', 'declined', 'rescind', 'withdraw']
                                should_skip = False
                                for keyword in skip_keywords:
                                    if any(keyword in cell.get_text(strip=True).lower() for cell in cells):
                                        logger.info(f"   ❌ Skipping {name}: {keyword} (unavailable/declined)")
                                        should_skip = True
                                        break
                                
                                if not should_skip:
                                    # Add to appropriate list based on report status (EXACT same)
                                    if referee['report_submitted']:
                                        manuscript_data['completed_referees'].append(referee)
                                        logger.info(f"   ✅ {name} (Completed)")
                                    else:
                                        manuscript_data['referees'].append(referee)
                                        logger.info(f"   ✅ {name} ({referee['status']})")
                
                else:
                    logger.warning("Could not find reviewer table")
            else:
                logger.warning("Could not find Reviewer List section")
            
            # Fetch email dates (exact same approach, but for MOR)
            try:
                sys.path.insert(0, str(Path(__file__).parent))
                from core.email_utils import fetch_starred_emails
                from core.generic_email_utils import robust_match_email_for_referee_generic
                
                logger.info(f"📧 Fetching email dates for {manuscript_id}...")
                starred_emails = fetch_starred_emails("MOR")  # MOR journal parameter
                flagged_emails = [email for email in starred_emails if email.get('subject', '').startswith('MOR')]
                
                for referee in manuscript_data['referees']:
                    try:
                        acceptance_date, contact_date = robust_match_email_for_referee_generic(
                            referee['name'], manuscript_id, 'MOR', 
                            referee['status'], flagged_emails, starred_emails
                        )
                        if acceptance_date:
                            referee['acceptance_date'] = acceptance_date
                            logger.info(f"   📅 {referee['name']} acceptance: {acceptance_date}")
                        else:
                            logger.info(f"   ❌ No email match found for {referee['name']}")
                    except Exception as e:
                        logger.warning(f"Email matching error for {referee['name']}: {e}")
                        
            except Exception as e:
                logger.warning(f"Email processing error: {e}")
            
            manuscript_data['extraction_status'] = 'success'
            logger.info(f"✅ Successfully extracted {len(manuscript_data['referees'])} active + {len(manuscript_data['completed_referees'])} completed referees")
            
            return manuscript_data
            
        except Exception as e:
            logger.error(f"❌ Referee extraction failed: {e}")
            manuscript_data['extraction_status'] = 'failed'
            return manuscript_data
    
    def navigate_back_to_ae_center(self):
        """Navigate back to AE Center (exact working system approach)"""
        logger.info("🔄 Navigating back to Associate Editor Center...")
        
        try:
            ae_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            time.sleep(2)
            
            logger.info("✅ Navigated back to Associate Editor Center")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to navigate back: {e}")
            return False
    
    def extract_all_mor_data(self, headless=False):
        """Extract all MOR data using exact working system approach"""
        logger.info("🚀 Starting stable MOR extraction (exact working system approach)")
        
        all_results = {
            'journal': 'MOR',
            'extraction_date': datetime.now().isoformat(),
            'extraction_method': 'stable_checkbox_clicks',
            'manuscripts': []
        }
        
        try:
            # Create driver
            if not self.create_driver(headless=headless):
                raise Exception("Driver creation failed")
            
            # Login
            if not self.login_mor():
                raise Exception("Login failed")
            
            # Navigate to AE Center
            if not self.navigate_to_ae_center():
                raise Exception("AE Center navigation failed")
            
            # Navigate to category (MOR uses different category)
            category = "Awaiting Reviewer Reports"
            if not self.navigate_to_category(category):
                raise Exception(f"Category '{category}' navigation failed")
            
            # Process each manuscript
            for manuscript_id, manuscript_info in self.expected_manuscripts.items():
                logger.info(f"\n{'='*60}")
                logger.info(f"📄 Processing: {manuscript_id}")
                logger.info(f"Expected: {manuscript_info['title'][:50]}...")
                logger.info(f"{'='*60}")
                
                # Find and click checkbox
                if self.find_and_click_manuscript_checkbox(manuscript_id):
                    # Extract referee details
                    manuscript_data = self.extract_referee_details(manuscript_id)
                    all_results['manuscripts'].append(manuscript_data)
                    
                    # Navigate back for next manuscript
                    if not self.navigate_back_to_ae_center():
                        logger.warning("Could not navigate back")
                        break
                    
                    if not self.navigate_to_category(category):
                        logger.warning("Could not navigate back to category")
                        break
                else:
                    # Add failed record
                    all_results['manuscripts'].append({
                        'manuscript_id': manuscript_id,
                        'extraction_status': 'failed',
                        'error': 'Checkbox not found'
                    })
            
            # Save results
            results_file = self.results_dir / "mor_stable_results.json"
            with open(results_file, 'w') as f:
                json.dump(all_results, f, indent=2)
            
            # Generate report
            self.generate_report(all_results)
            
            logger.info(f"🎉 Stable MOR extraction completed!")
            logger.info(f"   Results: {results_file}")
            
            return all_results
            
        except Exception as e:
            logger.error(f"❌ Stable extraction failed: {e}")
            return all_results
            
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    logger.info("🔄 Driver closed")
                except:
                    pass
    
    def generate_report(self, results):
        """Generate summary report"""
        report_lines = []
        report_lines.append("STABLE MOR REFEREE EXTRACTION")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("Method: stable_checkbox_clicks")
        report_lines.append("="*60)
        report_lines.append("")
        
        for manuscript in results['manuscripts']:
            if manuscript.get('extraction_status') == 'success':
                report_lines.append(f"Manuscript: {manuscript['manuscript_id']}")
                report_lines.append(f"Title: {manuscript.get('title', 'N/A')}")
                report_lines.append(f"Status: {manuscript.get('status', 'N/A')}")
                report_lines.append(f"Submitted: {manuscript.get('submitted_date', 'N/A')}")
                report_lines.append(f"Due: {manuscript.get('due_date', 'N/A')}")
                
                referees = manuscript.get('referees', [])
                completed_referees = manuscript.get('completed_referees', [])
                
                report_lines.append(f"Active Referees: {len(referees)}")
                for ref in referees:
                    report_lines.append(f"  • {ref['name']} ({ref['status']})")
                    report_lines.append(f"    Invited: {ref['dates'].get('invited', 'N/A')}")
                    report_lines.append(f"    Agreed: {ref['dates'].get('agreed', 'N/A')}")
                    report_lines.append(f"    Due: {ref['dates'].get('due', 'N/A')}")
                    if ref.get('acceptance_date'):
                        report_lines.append(f"    Email: {ref['acceptance_date']}")
                
                if completed_referees:
                    report_lines.append(f"Completed Referees: {len(completed_referees)}")
                    for ref in completed_referees:
                        report_lines.append(f"  • {ref['name']} ({ref.get('review_decision', 'Completed')})")
                        if ref.get('dates', {}).get('invited'):
                            report_lines.append(f"    Invited: {ref['dates']['invited']}")
                
                report_lines.append("")
                report_lines.append("-"*40)
                report_lines.append("")
        
        # Summary
        total = len(results['manuscripts'])
        successful = len([m for m in results['manuscripts'] if m.get('extraction_status') == 'success'])
        total_active_referees = sum(len(m.get('referees', [])) for m in results['manuscripts'])
        total_completed_referees = sum(len(m.get('completed_referees', [])) for m in results['manuscripts'])
        
        report_lines.append("SUMMARY:")
        report_lines.append(f"Total Manuscripts: {total}")
        report_lines.append(f"Successful: {successful}")
        report_lines.append(f"Total Active Referees: {total_active_referees}")
        report_lines.append(f"Total Completed Referees: {total_completed_referees}")
        report_lines.append(f"Success Rate: {(successful/total*100):.1f}%" if total > 0 else "0%")
        
        # Save report
        report_file = self.results_dir / "mor_stable_report.txt"
        with open(report_file, 'w') as f:
            f.write('\n'.join(report_lines))
        
        logger.info(f"📄 Report saved: {report_file}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    args = parser.parse_args()
    
    extractor = StableMORExtractor()
    results = extractor.extract_all_mor_data(headless=args.headless)
    
    if results and results.get('manuscripts'):
        successful = len([m for m in results['manuscripts'] if m.get('extraction_status') == 'success'])
        total = len(results['manuscripts'])
        total_active = sum(len(m.get('referees', [])) for m in results['manuscripts'])
        total_completed = sum(len(m.get('completed_referees', [])) for m in results['manuscripts'])
        print(f"✅ Stable MOR extraction: {successful}/{total} manuscripts, {total_active} active + {total_completed} completed referees")
    else:
        print("❌ Stable MOR extraction failed!")
        sys.exit(1)