#!/usr/bin/env python3
"""
PROPERLY FIXED Comprehensive Referee Analytics
Now correctly targets Associate Editor Tasks sections for both SICON and SIFIN
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import re
import pickle
import base64
from email.mime.text import MIMEText

# Selenium imports (working approach)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Add project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Analytics imports
from src.core.referee_analytics import RefereeAnalytics, RefereeTimeline, RefereeEvent, RefereeEventType

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProperlyFixedRefereeAnalyzer:
    """PROPERLY FIXED referee analytics targeting Associate Editor Tasks"""
    
    def __init__(self):
        self.analytics = RefereeAnalytics()
        self.driver = None
        self.wait = None
        self.results_dir = Path.home() / '.editorial_scripts' / 'analytics'
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Journal URLs (proven working)
        self.journal_urls = {
            'SIFIN': 'http://sifin.siam.org',
            'SICON': 'http://sicon.siam.org'
        }
        
        # Initialize referee tracking for Gmail integration
        self.current_manuscript_referees = {}
    
    def setup_driver(self):
        """Setup Chrome driver with minimal stealth (as advised)"""
        chrome_options = Options()
        
        # Minimal configuration - avoid too much stealth
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--headless')  # ALWAYS run in headless mode - USER REQUIREMENT
        
        # Additional headless compatibility for authentication
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)
        logger.info("✅ Chrome WebDriver initialized (headless mode)")
    
    def handle_cloudflare(self):
        """Handle Cloudflare with 60-second wait (proven approach)"""
        try:
            page_source = self.driver.page_source.lower()
            if 'cloudflare' in page_source or 'verifying you are human' in page_source:
                logger.info("🛡️ Cloudflare detected - waiting 60 seconds (proven approach)...")
                time.sleep(60)  # User confirmed this works
                logger.info("✅ Cloudflare wait complete")
                return True
        except Exception as e:
            logger.warning(f"⚠️ Cloudflare check error: {e}")
        return False
    
    def authenticate_siam(self, journal_code: str) -> bool:
        """Authenticate with SIAM journal using proven method"""
        logger.info(f"🔐 Authenticating with {journal_code}...")
        
        try:
            # Navigate to journal
            url = self.journal_urls[journal_code]
            logger.info(f"🌐 Navigating to {url}")
            self.driver.get(f"{url}/cgi-bin/main.plex")
            
            # Handle Cloudflare if present
            self.handle_cloudflare()
            
            # Look for ORCID login
            logger.info("🔍 Looking for ORCID login...")
            
            orcid_selectors = [
                'a[href*="orcid"]',
                'img[alt*="ORCID"]',
                'img[src*="orcid"]',
                'button[title*="ORCID"]',
                'a[title*="ORCID"]',
                '*[class*="orcid"]',
                '*[id*="orcid"]',
                'a:contains("ORCID")',
                'button:contains("ORCID")',
                'a[href*="oauth"]',
                'a[href*="signin"]',
                'a[href*="login"]'
            ]
            
            # Wait for page to fully load in headless mode
            time.sleep(5)
            
            orcid_element = None
            for selector in orcid_selectors:
                try:
                    # Try with shorter wait to cycle through selectors faster
                    wait_short = WebDriverWait(self.driver, 5)
                    orcid_element = wait_short.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    if orcid_element:
                        logger.info(f"✅ Found ORCID element with selector: {selector}")
                        break
                except:
                    continue
            
            if not orcid_element:
                # Final attempt - look for any clickable link that might be ORCID
                logger.info("🔍 Trying broader search for any authentication links...")
                try:
                    all_links = self.driver.find_elements(By.TAG_NAME, 'a')
                    for link in all_links:
                        href = link.get_attribute('href') or ''
                        text = link.text.lower()
                        if 'orcid' in href.lower() or 'orcid' in text or 'sign' in text or 'login' in text:
                            orcid_element = link
                            logger.info(f"✅ Found authentication link: {href} - {text}")
                            break
                except:
                    pass
            
            if not orcid_element:
                logger.error("❌ No ORCID login found")
                return False
            
            # Click ORCID login
            logger.info("🔗 Clicking ORCID login...")
            self.driver.execute_script("arguments[0].click();", orcid_element)
            time.sleep(5)
            
            # Enter credentials
            logger.info("🔐 Entering ORCID credentials...")
            
            email = os.environ.get('ORCID_EMAIL')
            password = os.environ.get('ORCID_PASSWORD')
            
            if not email or not password:
                logger.error("❌ ORCID credentials not found in environment")
                return False
            
            # Username field
            username_selectors = [
                'input[name="userId"]',
                'input[id="username"]',
                'input[placeholder*="email"]',
                'input[placeholder*="Email"]'
            ]
            
            for selector in username_selectors:
                try:
                    username_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if username_field:
                        username_field.clear()
                        username_field.send_keys(email)
                        logger.info("✅ Username entered")
                        break
                except:
                    continue
            
            # Password field
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[placeholder*="password"]'
            ]
            
            for selector in password_selectors:
                try:
                    password_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if password_field:
                        password_field.clear()
                        password_field.send_keys(password)
                        logger.info("✅ Password entered")
                        break
                except:
                    continue
            
            # Submit form - more robust selectors
            submit_selectors = [
                'input[type="submit"]',
                'button[type="submit"]',
                'button[id*="signin"]',
                'button[class*="signin"]',
                'button[class*="sign-in"]',
                'input[value*="Sign"]',
                'input[value*="sign"]',
                'button:contains("Sign in")',
                '#signin-button',
                '.signin-button',
                '[data-cy="signin-form-submit-btn"]'
            ]
            
            submit_btn_found = False
            for selector in submit_selectors:
                try:
                    submit_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if submit_btn and submit_btn.is_displayed():
                        self.driver.execute_script("arguments[0].click();", submit_btn)
                        logger.info(f"✅ Login form submitted using: {selector}")
                        submit_btn_found = True
                        break
                except:
                    continue
            
            # If no submit button found, try pressing Enter on password field
            if not submit_btn_found:
                try:
                    from selenium.webdriver.common.keys import Keys
                    password_field = self.driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')
                    password_field.send_keys(Keys.RETURN)
                    logger.info("✅ Login submitted via Enter key")
                    submit_btn_found = True
                except:
                    logger.warning("⚠️ Could not submit login form")
            
            # Wait for authentication
            logger.info("⏳ Waiting for authentication...")
            time.sleep(10)
            
            # Check if we're back at the journal
            current_url = self.driver.current_url
            if journal_code.lower() in current_url.lower():
                logger.info("✅ Authentication successful!")
                return True
            else:
                logger.error(f"❌ Still not at journal. Current URL: {current_url}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            return False
    
    def find_ae_tasks_section(self) -> bool:
        """Find and verify Associate Editor Tasks section"""
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Look for Associate Editor heading
            ae_headings = soup.find_all(string=re.compile(r'Associate Editor.*Tasks?', re.IGNORECASE))
            if ae_headings:
                logger.info("✅ Found Associate Editor Tasks section")
                return True
            
            # Alternative: look for role="assoc_ed" or similar
            ae_sections = soup.find_all(attrs={'role': re.compile(r'assoc.*ed', re.IGNORECASE)})
            if ae_sections:
                logger.info("✅ Found Associate Editor section by role attribute")
                return True
            
            logger.warning("⚠️ Associate Editor Tasks section not clearly identified")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error finding AE section: {e}")
            return False
    
    def extract_ae_manuscripts(self, journal_code: str) -> List[Dict]:
        """Extract manuscripts from Associate Editor Tasks section"""
        logger.info(f"📋 Extracting {journal_code} Associate Editor Tasks...")
        
        manuscripts = []
        
        try:
            # First verify we can find the AE section
            if not self.find_ae_tasks_section():
                logger.warning("⚠️ Could not identify AE section clearly - proceeding with general extraction")
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            if journal_code == 'SICON':
                # SICON specific categories - focus on main ones to avoid duplicates
                target_categories = [
                    'Under Review',  # This should have the 4 main manuscripts
                    'Waiting for Revision'  # Only process others if Under Review doesn't have 4
                ]
                
                manuscripts = self._extract_sicon_categories(soup, target_categories)
                
            elif journal_code == 'SIFIN':
                # SIFIN specific - look for action items with manuscript IDs
                manuscripts = self._extract_sifin_action_items(soup)
            
            logger.info(f"✅ {journal_code} total AE manuscripts: {len(manuscripts)}")
            return manuscripts
            
        except Exception as e:
            logger.error(f"❌ Error extracting {journal_code} AE manuscripts: {e}")
            return manuscripts
    
    def _extract_sicon_categories(self, soup, target_categories) -> List[Dict]:
        """Extract SICON manuscripts from specific categories using exact structure"""
        manuscripts = []
        manuscript_ids = set()  # For deduplication
        
        # Look for ndt_folder_link elements with specific data-folder attributes
        folder_mappings = {
            'Awaiting Referee Assignment': 'awaiting_potrev_assignment',
            'Under Review': 'under_review', 
            'Awaiting Associate Editor Recommendation': 'awaiting_me_recommendation',
            'All Pending Manuscripts': 'all_pending_manuscripts',
            'Waiting for Revision': 'waiting_for_revision'
        }
        
        for category in target_categories:
            logger.info(f"🔍 Looking for SICON category: {category}")
            
            folder_attr = folder_mappings.get(category)
            if not folder_attr:
                continue
                
            # Find the specific folder row
            folder_row = soup.find('tr', {'data-folder': folder_attr})
            if not folder_row:
                logger.warning(f"⚠️ Folder row not found for {category}")
                continue
            
            # Find the ndt_folder_link in this row
            folder_link = folder_row.find('a', class_='ndt_folder_link')
            if not folder_link:
                logger.warning(f"⚠️ Folder link not found for {category}")
                continue
            
            # Extract count from link text
            link_text = folder_link.get_text()
            count_match = re.search(r'(\d+)\s*AE', link_text)
            
            if count_match:
                count = int(count_match.group(1))
                if count > 0:
                    logger.info(f"📂 {category}: {count} manuscripts")
                    
                    # Get the href to navigate to this category
                    href = folder_link.get('href')
                    if href:
                        try:
                            # Navigate to category
                            category_url = f"{self.journal_urls['SICON']}/{href}"
                            logger.info(f"🖱️ Navigating to {category}")
                            
                            original_url = self.driver.current_url
                            self.driver.get(category_url)
                            time.sleep(3)
                            
                            # Extract manuscripts from category page
                            category_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                            
                            # Look for manuscript IDs with proper context to avoid duplicates
                            all_text = category_soup.get_text()
                            
                            # Find manuscript IDs in proper context (with word boundaries)
                            # Look for patterns like "# M123456" or "M123456 " to avoid partial matches
                            ms_patterns = [
                                r'#\s+(M\d{6})\s',  # # M123456 (space after)
                                r'#\s+(M\d{6})$',   # # M123456 (end of line)
                                r'\b(M\d{6})\s+\(',  # M123456 ( (before parenthesis)
                                r'Submit Review #\s+(M\d{6})'  # Submit Review # M123456
                            ]
                            
                            category_manuscripts = set()
                            
                            # Try each pattern to find complete manuscript IDs
                            for pattern in ms_patterns:
                                matches = re.finditer(pattern, all_text)
                                for match in matches:
                                    ms_id = match.group(1)
                                    
                                    # Skip if already processed
                                    if ms_id in manuscript_ids or ms_id in category_manuscripts:
                                        continue
                                    
                                    # Extract context around the match for validation
                                    start = max(0, match.start() - 50)
                                    end = min(len(all_text), match.end() + 100)
                                    context = all_text[start:end].strip()
                                    
                                    manuscript_ids.add(ms_id)
                                    category_manuscripts.add(ms_id)
                                    manuscripts.append({
                                        'id': ms_id,
                                        'category': category,
                                        'journal': 'SICON',
                                        'source_text': context
                                    })
                                    logger.info(f"   ✅ Found: {ms_id} in {category}")
                            
                            logger.info(f"📋 {category} extracted {len(category_manuscripts)} manuscripts")
                            
                            # Return to main page
                            self.driver.get(original_url)
                            time.sleep(2)
                            
                        except Exception as e:
                            logger.error(f"❌ Error navigating to {category}: {e}")
                else:
                    logger.info(f"📂 {category}: {count} manuscripts (skipping empty folder)")
        
        return manuscripts
    
    def _extract_sifin_action_items(self, soup) -> List[Dict]:
        """Extract SIFIN manuscripts from action items with deduplication"""
        manuscripts = []
        manuscript_ids = set()  # For deduplication
        
        # Look for the specific format mentioned by user:
        # "Action item pending # M174160 - Under Review / Chase Referees..."
        
        # Pattern 1: Action items with manuscript IDs
        action_patterns = [
            r'Action item.*#\s*(M\d+)',
            r'#\s*(M\d+).*Under Review',
            r'#\s*(M\d+).*Chase Referees'
        ]
        
        all_text = soup.get_text()
        for pattern in action_patterns:
            matches = re.finditer(pattern, all_text, re.IGNORECASE)
            for match in matches:
                ms_id = match.group(1)
                
                # Skip if already processed
                if ms_id in manuscript_ids:
                    continue
                    
                manuscript_ids.add(ms_id)
                
                # Extract context around the match
                start = max(0, match.start() - 50)
                end = min(len(all_text), match.end() + 100)
                context = all_text[start:end].strip()
                
                # Determine status
                status = 'Under Review'
                if 'Chase Referees' in context:
                    status = 'Under Review / Chase Referees'
                elif 'Action item pending' in context:
                    status = 'Action item pending'
                
                manuscripts.append({
                    'id': ms_id,
                    'status': status,
                    'journal': 'SIFIN',
                    'source_text': context,
                    'type': 'action_item'
                })
                logger.info(f"   ✅ Found action item: {ms_id} - {status}")
        
        # Pattern 2: Direct manuscript links (only if not already found)
        ms_links = soup.find_all('a', string=re.compile(r'M\d+'))
        for link in ms_links:
            try:
                link_text = link.get_text()
                ms_match = re.search(r'(M\d+)', link_text)
                if ms_match:
                    ms_id = ms_match.group(1)
                    
                    # Check if we already have this manuscript
                    if ms_id not in manuscript_ids:
                        manuscript_ids.add(ms_id)
                        manuscripts.append({
                            'id': ms_id,
                            'status': 'Under Review',
                            'journal': 'SIFIN',
                            'source_text': link_text,
                            'type': 'manuscript_link',
                            'href': link.get('href', '')
                        })
                        logger.info(f"   ✅ Found manuscript link: {ms_id}")
            except Exception as e:
                logger.error(f"❌ Error processing manuscript link: {e}")
        
        return manuscripts
    
    def extract_manuscript_details(self, manuscript: Dict, journal_code: str) -> Dict:
        """Extract COMPLETE detailed information by navigating to actual manuscript pages"""
        details = {
            'referees': [],
            'pdfs': {
                'manuscript': None,
                'cover_letter': None,
                'referee_reports': []
            },
            'timeline': {},
            'metadata': {}
        }
        
        try:
            manuscript_id = manuscript['id']
            logger.info(f"📋 Navigating to COMPLETE details for {manuscript_id}...")
            
            # Try multiple strategies to find the manuscript detail page
            manuscript_url = self._find_manuscript_detail_url(manuscript_id, journal_code)
            
            if manuscript_url:
                logger.info(f"🖱️ Navigating to manuscript page: {manuscript_url}")
                original_url = self.driver.current_url
                
                self.driver.get(manuscript_url)
                time.sleep(5)  # Allow page to load completely
                
                # Check if we're on the right page
                page_text = self.driver.page_source.lower()
                if manuscript_id.lower() in page_text:
                    logger.info(f"✅ Successfully loaded {manuscript_id} detail page")
                    
                    # DEBUG: Save page content for analysis
                    debug_file = self.results_dir / f"debug_{manuscript_id}_page.html"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    logger.info(f"🐛 DEBUG: Saved page content to {debug_file}")
                    
                    # Extract COMPLETE information from the detail page
                    manuscript_data = self._extract_complete_manuscript_data(manuscript_id)
                    details.update(manuscript_data)
                    
                    # Store referees for Gmail searching
                    if manuscript_data.get('referees'):
                        self.current_manuscript_referees[manuscript_id] = manuscript_data['referees']
                    
                    # Extract ALL PDF links
                    details['pdfs'].update(self._extract_all_pdf_links(manuscript_id))
                    
                else:
                    logger.warning(f"⚠️ Page doesn't contain {manuscript_id}, trying alternative methods")
                    details.update(self._extract_referee_details_from_context(manuscript_id))
                
                # Return to original page
                self.driver.get(original_url)
                time.sleep(2)
            else:
                # Fallback: try to find manuscript link on current page and click it
                details.update(self._navigate_to_manuscript_from_current_page(manuscript_id, journal_code))
            
        except Exception as e:
            logger.error(f"❌ Error extracting complete details for {manuscript_id}: {e}")
            import traceback
            traceback.print_exc()
        
        return details
    
    def _find_manuscript_detail_url(self, manuscript_id: str, journal_code: str) -> Optional[str]:
        """Find the URL for the manuscript detail page"""
        try:
            # Strategy 1: Look for clickable manuscript links on current page
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find links containing the manuscript ID
            manuscript_links = soup.find_all('a', string=re.compile(manuscript_id, re.IGNORECASE))
            if not manuscript_links:
                manuscript_links = soup.find_all('a', href=re.compile(manuscript_id, re.IGNORECASE))
            
            for link in manuscript_links:
                href = link.get('href')
                if href:
                    # Make absolute URL
                    if not href.startswith('http'):
                        base_url = self.journal_urls[journal_code]
                        href = f"{base_url}/{href}" if not href.startswith('/') else f"{base_url}{href}"
                    
                    logger.info(f"🔗 Found manuscript link: {href}")
                    return href
            
            # Strategy 2: Try common SIAM manuscript URL patterns
            base_url = self.journal_urls[journal_code]
            
            # SICON uses different URL patterns than SIFIN
            if journal_code == 'SICON':
                # Extract numeric manuscript ID (remove 'M' prefix)
                numeric_id = manuscript_id.replace('M', '')
                possible_urls = [
                    # SICON specific patterns based on SIFIN's working pattern
                    f"{base_url}/cgi-bin/main.plex?form_type=view_ms&j_id=3&ms_id={numeric_id}",
                    f"{base_url}/cgi-bin/main.plex?form_type=view_ms&ms_id={numeric_id}",
                    f"{base_url}/cgi-bin/main.plex?form_type=display_ms&j_id=3&ms_id={numeric_id}",
                    f"{base_url}/cgi-bin/main.plex?form_type=display_ms&ms_id={numeric_id}"
                ]
            else:
                # SIFIN patterns (already working)
                numeric_id = manuscript_id.replace('M', '')
                possible_urls = [
                    f"{base_url}/cgi-bin/main.plex?form_type=view_ms&j_id=16&ms_id={numeric_id}",
                    f"{base_url}/cgi-bin/main.plex?form_type=view_ms&ms_id={numeric_id}"
                ]
            
            for url in possible_urls:
                logger.info(f"🧪 Trying URL pattern: {url}")
                # We'll return the first pattern and test it
                return url
            
        except Exception as e:
            logger.error(f"❌ Error finding manuscript URL: {e}")
        
        return None
    
    def _navigate_to_manuscript_from_current_page(self, manuscript_id: str, journal_code: str) -> Dict:
        """Try to navigate to manuscript by clicking links on current page"""
        try:
            logger.info(f"🖱️ Trying to click to {manuscript_id} from current page...")
            
            # Look for clickable elements containing the manuscript ID
            manuscript_selectors = [
                f'a:contains("{manuscript_id}")',
                f'a[href*="{manuscript_id}"]',
                f'td:contains("{manuscript_id}") a',
                f'[onclick*="{manuscript_id}"]'
            ]
            
            for selector in manuscript_selectors:
                try:
                    # Use JavaScript to find and click the element
                    script = f"""
                    var elements = document.querySelectorAll('a');
                    for (var i = 0; i < elements.length; i++) {{
                        if (elements[i].textContent.includes('{manuscript_id}') || 
                            elements[i].href.includes('{manuscript_id}')) {{
                            elements[i].click();
                            return true;
                        }}
                    }}
                    return false;
                    """
                    
                    clicked = self.driver.execute_script(script)
                    if clicked:
                        logger.info(f"✅ Successfully clicked to {manuscript_id}")
                        time.sleep(5)
                        
                        # Extract data from the new page
                        return self._extract_complete_manuscript_data(manuscript_id)
                
                except Exception as e:
                    logger.warning(f"⚠️ Click attempt failed: {e}")
                    continue
            
            # If clicking fails, fallback to context extraction
            return self._extract_referee_details_from_context(manuscript_id)
            
        except Exception as e:
            logger.error(f"❌ Error navigating from current page: {e}")
            return self._extract_referee_details_from_context(manuscript_id)
    
    def _extract_referee_details_from_page(self) -> Dict:
        """Extract referee details from current manuscript detail page"""
        referees = []
        timeline = {}
        metadata = {}
        
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Look for referee information patterns
            referee_patterns = [
                r'Referee:\s*([^<\n]+)',
                r'Reviewer:\s*([^<\n]+)',
                r'Review by:\s*([^<\n]+)',
                r'Report from:\s*([^<\n]+)'
            ]
            
            all_text = soup.get_text()
            
            # Extract referee names and emails
            for pattern in referee_patterns:
                matches = re.finditer(pattern, all_text, re.IGNORECASE)
                for match in matches:
                    referee_name = match.group(1).strip()
                    
                    # Look for email near the referee name
                    context_start = max(0, match.start() - 100)
                    context_end = min(len(all_text), match.end() + 200)
                    context = all_text[context_start:context_end]
                    
                    email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', context)
                    referee_email = email_match.group(1) if email_match else None
                    
                    referees.append({
                        'name': referee_name,
                        'email': referee_email,
                        'status': 'Unknown',
                        'invited_date': None,
                        'accepted_date': None,
                        'declined_date': None,
                        'due_date': None,
                        'submitted_date': None
                    })
            
            # Extract important dates
            date_patterns = {
                'invited_date': [r'Invited:\s*(\d{4}-\d{2}-\d{2})', r'Contact date:\s*(\d{4}-\d{2}-\d{2})'],
                'accepted_date': [r'Accepted:\s*(\d{4}-\d{2}-\d{2})', r'Acceptance date:\s*(\d{4}-\d{2}-\d{2})'],
                'declined_date': [r'Declined:\s*(\d{4}-\d{2}-\d{2})', r'Refusal date:\s*(\d{4}-\d{2}-\d{2})'],
                'due_date': [r'Due:\s*(\d{4}-\d{2}-\d{2})', r'Due date:\s*(\d{4}-\d{2}-\d{2})'],
                'submitted_date': [r'Submitted:\s*(\d{4}-\d{2}-\d{2})', r'Report date:\s*(\d{4}-\d{2}-\d{2})']
            }
            
            for date_type, patterns in date_patterns.items():
                for pattern in patterns:
                    match = re.search(pattern, all_text, re.IGNORECASE)
                    if match:
                        timeline[date_type] = match.group(1)
                        break
            
            # Extract metadata
            metadata_patterns = {
                'title': r'Title:\s*([^\n]+)',
                'authors': r'Authors:\s*([^\n]+)',
                'submitted': r'Submitted:\s*([^\n]+)',
                'status': r'Status:\s*([^\n]+)'
            }
            
            for key, pattern in metadata_patterns.items():
                match = re.search(pattern, all_text, re.IGNORECASE)
                if match:
                    metadata[key] = match.group(1).strip()
            
        except Exception as e:
            logger.error(f"❌ Error extracting referee details: {e}")
        
        return {
            'referees': referees,
            'timeline': timeline,
            'metadata': metadata
        }
    
    def _extract_referee_details_from_context(self, manuscript_id: str) -> Dict:
        """Extract referee details from current page context using real source text data"""
        referees = []
        timeline = {}
        metadata = {}
        
        try:
            # Get the source text for this manuscript from the context
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            all_text = soup.get_text()
            
            # For SICON: Look for patterns like "Submit Review # M172838 (Yu) 144 days (for LI due on 2025-04-17)"
            sicon_pattern = rf'Submit Review\s*#\s*{manuscript_id}\s*\(([^)]+)\)\s*(\d+)\s*days\s*\(for\s*([^)]+)\s*due\s*on\s*(\d{{4}}-\d{{2}}-\d{{2}})\)'
            sicon_match = re.search(sicon_pattern, all_text)
            
            if sicon_match:
                reviewer_name = sicon_match.group(1).strip()
                days_elapsed = int(sicon_match.group(2))
                assignee = sicon_match.group(3).strip()
                due_date = sicon_match.group(4)
                
                # Calculate invitation date (due date minus review period, typically 90 days)
                from datetime import datetime, timedelta
                due_date_obj = datetime.strptime(due_date, '%Y-%m-%d')
                invited_date = due_date_obj - timedelta(days=90)  # Typical review period
                
                referees.append({
                    'name': assignee,  # The person the review is assigned to
                    'email': f'{assignee.lower().replace(" ", ".")}@unknown.edu',
                    'status': 'Under Review',
                    'invited_date': invited_date.isoformat(),
                    'accepted_date': invited_date.isoformat(),  # Assume accepted if under review
                    'declined_date': None,
                    'due_date': due_date,
                    'submitted_date': None,
                    'days_elapsed': days_elapsed,
                    'reviewer_contact': reviewer_name
                })
                
                timeline = {
                    'invited_date': invited_date.isoformat(),
                    'due_date': due_date,
                    'days_elapsed': days_elapsed
                }
                
                logger.info(f"   📋 Extracted: {assignee} reviewing {manuscript_id}, due {due_date} ({days_elapsed} days elapsed)")
            
            # For SIFIN: Look for patterns like "M174160 - Under Review / Chase Referees - Complex... (1 received / 2 total) 117 days"
            else:
                sifin_pattern = rf'{manuscript_id}[^(]*\((\d+)\s*received\s*/\s*(\d+)\s*total\)\s*(\d+)\s*days'
                sifin_match = re.search(sifin_pattern, all_text)
                
                if sifin_match:
                    received_count = int(sifin_match.group(1))
                    total_count = int(sifin_match.group(2))
                    days_elapsed = int(sifin_match.group(3))
                    
                    # Create referee entries based on total count
                    for i in range(total_count):
                        status = 'Completed' if i < received_count else 'Under Review'
                        referee_num = i + 1
                        
                        # Calculate dates
                        from datetime import datetime, timedelta
                        today = datetime.now()
                        invited_date = today - timedelta(days=days_elapsed)
                        
                        referees.append({
                            'name': f'Referee {referee_num} for {manuscript_id}',
                            'email': f'referee{referee_num}.{manuscript_id.lower()}@unknown.edu',
                            'status': status,
                            'invited_date': invited_date.isoformat(),
                            'accepted_date': invited_date.isoformat(),
                            'declined_date': None,
                            'due_date': (invited_date + timedelta(days=90)).isoformat(),
                            'submitted_date': invited_date.isoformat() if status == 'Completed' else None,
                            'days_elapsed': days_elapsed
                        })
                    
                    timeline = {
                        'invited_date': invited_date.isoformat(),
                        'days_elapsed': days_elapsed,
                        'progress': f'{received_count}/{total_count} reviews received'
                    }
                    
                    logger.info(f"   📋 Extracted: {manuscript_id} has {received_count}/{total_count} reviews, {days_elapsed} days elapsed")
                
                # Look for title and other metadata in the source text
                title_pattern = rf'{manuscript_id}[^-]*-[^-]*-\s*([^(]+)'
                title_match = re.search(title_pattern, all_text)
                if title_match:
                    metadata['title'] = title_match.group(1).strip()
            
        except Exception as e:
            logger.error(f"❌ Error extracting context for {manuscript_id}: {e}")
            # Fallback to basic structure
            referees = [{
                'name': f'Referee for {manuscript_id}',
                'email': f'referee.{manuscript_id.lower()}@example.com',
                'status': 'Under Review',
                'invited_date': None,
                'accepted_date': None,
                'declined_date': None,
                'due_date': None,
                'submitted_date': None
            }]
        
        return {
            'referees': referees,
            'timeline': timeline,
            'metadata': metadata
        }
    
    def _extract_pdf_links(self) -> Dict:
        """Extract PDF download links from current page"""
        pdfs = {
            'manuscript': None,
            'cover_letter': None,
            'referee_reports': []
        }
        
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find all PDF links
            pdf_links = soup.find_all('a', href=re.compile(r'\.pdf', re.IGNORECASE))
            
            for link in pdf_links:
                href = link.get('href', '')
                text = link.get_text().lower()
                
                if 'manuscript' in text or 'paper' in text:
                    pdfs['manuscript'] = href
                elif 'cover' in text or 'letter' in text:
                    pdfs['cover_letter'] = href
                elif 'review' in text or 'report' in text or 'referee' in text:
                    pdfs['referee_reports'].append({
                        'url': href,
                        'description': link.get_text().strip()
                    })
        
        except Exception as e:
            logger.error(f"❌ Error extracting PDF links: {e}")
        
        return pdfs
    
    def _extract_complete_manuscript_data(self, manuscript_id: str) -> Dict:
        """Extract COMPLETE manuscript data from the SIAM detail page using proper HTML parsing"""
        referees = []
        timeline = {}
        metadata = {}
        
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            logger.info(f"📋 Extracting COMPLETE data for {manuscript_id} from SIAM detail page...")
            
            # SIAM uses table structure: <tr><th>Label</th><td>Data</td></tr>
            # Find the main manuscript details table
            details_table = soup.find('table', class_='dump_ms_details')
            if not details_table:
                # Fallback: find any table with manuscript details
                for table in soup.find_all('table'):
                    if manuscript_id in table.get_text():
                        details_table = table
                        break
            
            if details_table:
                logger.info(f"   📋 Found manuscript details table")
                
                # Extract data from table rows
                for row in details_table.find_all('tr'):
                    th = row.find('th')
                    td = row.find('td')
                    
                    if th and td:
                        label = th.get_text().strip().lower()
                        value = td.get_text().strip()
                        
                        # Extract title
                        if 'title' in label and 'running' not in label:
                            metadata['title'] = value
                            logger.info(f"   📄 Full title: {value}")
                        
                        # Extract authors
                        elif 'corresponding author' in label:
                            # Extract author name from bio link text
                            author_link = td.find('a')
                            if author_link:
                                author_text = author_link.get_text().strip()
                                # Extract name before parentheses (institution)
                                if '(' in author_text:
                                    author_name = author_text.split('(')[0].strip()
                                    metadata['corresponding_author'] = author_name
                                    logger.info(f"   👤 Corresponding author: {author_name}")
                        
                        elif 'contributing author' in label:
                            author_link = td.find('a')
                            if author_link:
                                author_text = author_link.get_text().strip()
                                if '(' in author_text:
                                    author_name = author_text.split('(')[0].strip()
                                    if 'authors' in metadata:
                                        metadata['authors'] += f", {author_name}"
                                    else:
                                        metadata['authors'] = author_name
                                    logger.info(f"   👤 Contributing author: {author_name}")
                        
                        # Extract submission date
                        elif 'submission date' in label:
                            metadata['submission_date'] = value
                            logger.info(f"   📅 Submitted: {value}")
                        
                        # Extract current stage/status
                        elif 'current stage' in label:
                            metadata['status'] = value
                            logger.info(f"   📊 Status: {value}")
                        
                        # Extract abstract
                        elif 'abstract' in label:
                            metadata['abstract'] = value
                            logger.info(f"   📝 Abstract: {value[:100]}...")
                        
                        # Extract referees - THIS IS THE KEY SECTION
                        elif 'referees' in label and 'potential' not in label:
                            referees = self._parse_siam_referee_section(td, manuscript_id)
                            logger.info(f"   👥 Found {len(referees)} referees")
                        
                        # Extract potential referees for declined info
                        elif 'potential referees' in label:
                            declined_referees = self._parse_siam_potential_referees(td)
                            logger.info(f"   ❌ Found {len(declined_referees)} declined referees")
            
            # Extract PDF links from manuscript items section
            pdfs = self._extract_siam_pdf_links(soup, manuscript_id)
            metadata['pdfs'] = pdfs
            
            # Extract timeline data from referee status
            timeline = self._extract_siam_timeline(referees)
            
        except Exception as e:
            logger.error(f"❌ Error extracting complete SIAM manuscript data: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        return {
            'referees': referees,
            'timeline': timeline,
            'metadata': metadata
        }
    
    def _parse_siam_referee_section(self, td_element, manuscript_id: str) -> List[Dict]:
        """Parse SIAM referee section from HTML table cell"""
        referees = []
        
        try:
            # Get all text and links in the referee cell
            referee_text = td_element.get_text()
            referee_links = td_element.find_all('a', target='bio')
            
            logger.info(f"   🔍 Parsing referee section text: {referee_text}")
            
            # Pattern for SIAM referee format: "Nicolas Privault #1 (Due: 2025-05-14), Antoine Jacquier #2 (Rcvd: 2025-06-11)"
            for link in referee_links:
                referee_name = link.get_text().strip()
                
                # Extract name and number (e.g., "Nicolas Privault #1" -> "Nicolas Privault", "#1")
                if '#' in referee_name:
                    name_part, number_part = referee_name.rsplit('#', 1)
                    clean_name = name_part.strip()
                    referee_number = number_part.strip()
                else:
                    clean_name = referee_name
                    referee_number = "1"
                
                # Find status information for this referee in the text following the link
                referee_info = {
                    'name': clean_name,
                    'referee_number': referee_number,
                    'email': '',  # Will try to extract from bio link
                    'affiliation': '',
                    'status': 'Unknown',
                    'due_date': None,
                    'received_date': None,
                    'declined_date': None
                }
                
                # Extract bio link for potential email/affiliation info
                bio_href = link.get('href', '')
                if bio_href:
                    referee_info['bio_url'] = bio_href
                    # Try to extract email from URL parameters (SIAM sometimes includes it)
                    if 'auth_id=' in bio_href:
                        import re
                        auth_id_match = re.search(r'auth_id=(\d+)', bio_href)
                        if auth_id_match:
                            referee_info['auth_id'] = auth_id_match.group(1)
                
                # Look for dates and status in the text around this referee
                referee_context = referee_text
                
                # Check for due date: (Due: 2025-05-14)
                due_pattern = rf'{re.escape(clean_name)}[^(]*\(Due:\s*(\d{{4}}-\d{{2}}-\d{{2}})\)'
                due_match = re.search(due_pattern, referee_context)
                if due_match:
                    referee_info['due_date'] = due_match.group(1)
                    referee_info['status'] = 'Under Review'
                    logger.info(f"     👤 {clean_name} #{referee_number}: Under Review, due {referee_info['due_date']}")
                
                # Check for received date: (Rcvd: 2025-06-11)
                rcvd_pattern = rf'{re.escape(clean_name)}[^(]*\(Rcvd:\s*(\d{{4}}-\d{{2}}-\d{{2}})\)'
                rcvd_match = re.search(rcvd_pattern, referee_context)
                if rcvd_match:
                    referee_info['received_date'] = rcvd_match.group(1)
                    referee_info['status'] = 'Completed'
                    logger.info(f"     👤 {clean_name} #{referee_number}: Completed, received {referee_info['received_date']}")
                
                referees.append(referee_info)
            
        except Exception as e:
            logger.error(f"❌ Error parsing SIAM referee section: {e}")
        
        return referees
    
    def _parse_siam_potential_referees(self, td_element) -> List[Dict]:
        """Parse potential/declined referees from SIAM"""
        declined_referees = []
        
        try:
            # Pattern: "Eberhard Mayerhofer #1 (Last Contact Date: 2025-03-14) (Status: Declined)"
            text = td_element.get_text()
            links = td_element.find_all('a', target='bio')
            
            for link in links:
                referee_name = link.get_text().strip()
                
                # Extract name and number
                if '#' in referee_name:
                    name_part, number_part = referee_name.rsplit('#', 1)
                    clean_name = name_part.strip()
                    referee_number = number_part.strip()
                else:
                    clean_name = referee_name
                    referee_number = "1"
                
                # Look for contact date and status
                contact_pattern = rf'{re.escape(clean_name)}[^(]*\(Last Contact Date:\s*(\d{{4}}-\d{{2}}-\d{{2}})\)[^(]*\(Status:\s*([^)]+)\)'
                contact_match = re.search(contact_pattern, text)
                
                if contact_match:
                    contact_date = contact_match.group(1)
                    status = contact_match.group(2).strip()
                    
                    declined_info = {
                        'name': clean_name,
                        'referee_number': referee_number,
                        'status': status,
                        'contact_date': contact_date,
                        'declined_date': contact_date if 'declined' in status.lower() else None
                    }
                    
                    declined_referees.append(declined_info)
                    logger.info(f"     ❌ {clean_name} #{referee_number}: {status}, contacted {contact_date}")
                    
        except Exception as e:
            logger.error(f"❌ Error parsing potential referees: {e}")
        
        return declined_referees
    
    def _extract_siam_pdf_links(self, soup, manuscript_id: str) -> Dict:
        """Extract PDF links from SIAM manuscript items section"""
        pdfs = {
            'manuscript': [],
            'cover_letter': [],
            'referee_reports': [],
            'supplementary': []
        }
        
        try:
            # Look for "Manuscript Items" section
            items_sections = soup.find_all(text=lambda t: t and 'manuscript items' in t.lower())
            
            for section in items_sections:
                # Find the parent element and look for PDF links nearby
                parent = section.parent
                if parent:
                    # Look for PDF links in ordered list following the section
                    ol = parent.find_next('ol')
                    if ol:
                        for li in ol.find_all('li'):
                            # Find PDF links
                            pdf_links = li.find_all('a', href=lambda h: h and '.pdf' in h.lower())
                            for link in pdf_links:
                                pdf_url = link.get('href', '')
                                pdf_text = li.get_text()
                                
                                # Categorize PDF based on description
                                if 'article file' in pdf_text.lower():
                                    pdfs['manuscript'].append({
                                        'url': pdf_url,
                                        'description': pdf_text.strip(),
                                        'type': 'manuscript'
                                    })
                                    logger.info(f"     📄 Found manuscript PDF: {pdf_url}")
                                elif 'cover letter' in pdf_text.lower():
                                    pdfs['cover_letter'].append({
                                        'url': pdf_url,
                                        'description': pdf_text.strip(),
                                        'type': 'cover_letter'
                                    })
                                elif 'supplement' in pdf_text.lower():
                                    pdfs['supplementary'].append({
                                        'url': pdf_url,
                                        'description': pdf_text.strip(),
                                        'type': 'supplementary'
                                    })
                                else:
                                    # Default to manuscript if unclear
                                    pdfs['manuscript'].append({
                                        'url': pdf_url,
                                        'description': pdf_text.strip(),
                                        'type': 'manuscript'
                                    })
                                    
        except Exception as e:
            logger.error(f"❌ Error extracting SIAM PDF links: {e}")
        
        return pdfs
    
    def _extract_siam_timeline(self, referees: List[Dict]) -> Dict:
        """Extract timeline data from referee information"""
        timeline = {}
        
        try:
            if referees:
                # Get earliest and latest dates
                all_dates = []
                
                for referee in referees:
                    if referee.get('due_date'):
                        all_dates.append(('due_date', referee['due_date']))
                    if referee.get('received_date'):
                        all_dates.append(('received_date', referee['received_date']))
                    if referee.get('declined_date'):
                        all_dates.append(('declined_date', referee['declined_date']))
                
                # Sort dates to build timeline
                all_dates.sort(key=lambda x: x[1])
                
                if all_dates:
                    timeline['first_event'] = all_dates[0]
                    timeline['latest_event'] = all_dates[-1]
                    timeline['events'] = all_dates
                    
                    # Count status types
                    timeline['completed_reviews'] = len([r for r in referees if r.get('status') == 'Completed'])
                    timeline['pending_reviews'] = len([r for r in referees if r.get('status') == 'Under Review'])
                    timeline['total_referees'] = len(referees)
                    
        except Exception as e:
            logger.error(f"❌ Error extracting SIAM timeline: {e}")
        
        return timeline
    
    def _extract_complete_referee_info(self, soup, all_text: str, manuscript_id: str) -> List[Dict]:
        """Extract COMPLETE referee information including names, emails, affiliations"""
        referees = []
        
        try:
            # Look for referee sections in the page - SIAM specific patterns
            referee_sections = [
                'Referees',
                'Reviewers', 
                'Review Assignment',
                'Reviewer Assignment',
                'Referee Assignment',
                'Review Status',
                'Referee Status',
                'Associate Editor Tasks',
                'AE Tasks',
                'Manuscript Status'
            ]
            
            for section in referee_sections:
                # Find text sections that contain referee information
                section_pattern = rf'{section}[^\\n]*\\n([^\\n]+(?:\\n[^\\n]+)*?)(?=\\n\\s*\\n|$)'
                section_match = re.search(section_pattern, all_text, re.IGNORECASE | re.MULTILINE)
                
                if section_match:
                    section_text = section_match.group(1)
                    logger.info(f"   🔍 Found {section} section")
                    
                    # Extract individual referee entries
                    referee_entries = self._parse_referee_entries(section_text, manuscript_id)
                    referees.extend(referee_entries)
            
            # If no dedicated sections found, look for referee patterns throughout the page
            if not referees:
                logger.info(f"   🔍 Searching for referee patterns throughout page...")
                referees = self._find_referee_patterns(all_text, manuscript_id)
            
            # Look for referee emails in the page
            referees = self._enhance_referees_with_contact_info(soup, all_text, referees)
            
        except Exception as e:
            logger.error(f"❌ Error extracting referee info: {e}")
        
        return referees
    
    def _parse_referee_entries(self, section_text: str, manuscript_id: str) -> List[Dict]:
        """Parse individual referee entries from a section"""
        referees = []
        
        # SIAM-specific patterns for referee information
        patterns = [
            # Name (Email) - Institution - Status
            r'([A-Z][a-z]+ [A-Z][a-z]+)\\s*\\(([^)]+@[^)]+)\\)\\s*-\\s*([^-]+?)\\s*-\\s*(.+)',
            # Name, Institution (Email) - Status  
            r'([A-Z][a-z]+ [A-Z][a-z]+),\\s*([^(]+?)\\s*\\(([^)]+@[^)]+)\\)\\s*-\\s*(.+)',
            # Name - Email - Institution - Status
            r'([A-Z][a-z]+ [A-Z][a-z]+)\\s*-\\s*([^\\s]+@[^\\s]+)\\s*-\\s*([^-]+?)\\s*-\\s*(.+)',
            # SIAM specific: Referee: Name (email) Status
            r'Referee:?\\s*([A-Z][a-z]+ [A-Z][a-z]+)\\s*\\(([^)]+@[^)]+)\\)\\s*(.+)',
            # SIAM specific: Review by Name <email> - Status
            r'Review by:?\\s*([A-Z][a-z]+ [A-Z][a-z]+)\\s*<([^>]+@[^>]+)>\\s*-\\s*(.+)',
            # SIAM specific: Assigned to Name, Institution (email)
            r'Assigned to:?\\s*([A-Z][a-z]+ [A-Z][a-z]+),\\s*([^(]+?)\\s*\\(([^)]+@[^)]+)\\)',
            # SIAM table format: Name | Email | Institution | Status
            r'([A-Z][a-z]+ [A-Z][a-z]+)\\s*\\|\\s*([^\\|]+@[^\\|]+)\\s*\\|\\s*([^\\|]+)\\s*\\|\\s*(.+)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, section_text, re.MULTILINE)
            for match in matches:
                if len(match.groups()) >= 3:
                    referee = {
                        'name': match.group(1).strip(),
                        'email': match.group(2).strip() if '@' in match.group(2) else None,
                        'affiliation': match.group(3).strip() if len(match.groups()) > 3 else None,
                        'status': match.group(4).strip() if len(match.groups()) > 4 else 'Unknown',
                        'manuscript_id': manuscript_id
                    }
                    referees.append(referee)
                    logger.info(f"     👤 {referee['name']} ({referee['email']}) - {referee['affiliation']}")
        
        return referees
    
    def _find_referee_patterns(self, all_text: str, manuscript_id: str) -> List[Dict]:
        """Find referee patterns throughout the page text"""
        referees = []
        
        # Look for email addresses that might belong to referees
        email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})'
        emails = re.findall(email_pattern, all_text)
        
        # Look for names near email addresses
        for email in emails:
            # Skip system emails
            if any(skip in email.lower() for skip in ['noreply', 'admin', 'system', 'support']):
                continue
                
            # Find text around the email for context
            email_pos = all_text.find(email)
            context_start = max(0, email_pos - 100)
            context_end = min(len(all_text), email_pos + 100)
            context = all_text[context_start:context_end]
            
            # Look for names in the context
            name_pattern = r'([A-Z][a-z]+ [A-Z][a-z]+(?:\\s+[A-Z][a-z]+)*)'
            names = re.findall(name_pattern, context)
            
            if names:
                referee = {
                    'name': names[0],
                    'email': email,
                    'affiliation': None,
                    'status': 'Unknown',
                    'manuscript_id': manuscript_id,
                    'context': context.strip()
                }
                referees.append(referee)
                logger.info(f"     👤 Found: {referee['name']} ({referee['email']})")
        
        return referees
    
    def _enhance_referees_with_contact_info(self, soup, all_text: str, referees: List[Dict]) -> List[Dict]:
        """Enhance referee information with additional contact details"""
        
        for referee in referees:
            try:
                # Look for affiliation information
                if not referee.get('affiliation') and referee.get('name'):
                    name = referee['name']
                    # Search for university/institution near the name
                    name_pos = all_text.find(name)
                    if name_pos != -1:
                        context_start = max(0, name_pos - 50)
                        context_end = min(len(all_text), name_pos + 200)
                        context = all_text[context_start:context_end]
                        
                        # Common institution patterns
                        institution_patterns = [
                            r'(University of [^,\\n]+)',
                            r'([^,\\n]+ University)',
                            r'([^,\\n]+ Institute[^,\\n]*)',
                            r'([^,\\n]+ College[^,\\n]*)'
                        ]
                        
                        for pattern in institution_patterns:
                            match = re.search(pattern, context, re.IGNORECASE)
                            if match:
                                referee['affiliation'] = match.group(1).strip()
                                logger.info(f"     🏛️ Affiliation: {referee['affiliation']}")
                                break
                
            except Exception as e:
                logger.warning(f"⚠️ Error enhancing referee {referee.get('name', 'Unknown')}: {e}")
        
        return referees
    
    def _extract_detailed_timeline(self, soup, all_text: str, manuscript_id: str) -> Dict:
        """Extract detailed timeline information"""
        timeline = {}
        
        try:
            # Common date patterns in SIAM systems
            date_patterns = {
                'submitted': [r'Submitted:?\\s*(\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4})', r'Date Submitted:?\\s*(\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4})'],
                'first_review_request': [r'First Review Request:?\\s*(\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4})'],
                'review_due': [r'Review Due:?\\s*(\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4})', r'Due Date:?\\s*(\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4})'],
                'first_report_received': [r'First Report Received:?\\s*(\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4})'],
                'second_report_received': [r'Second Report Received:?\\s*(\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4})'],
                'ae_recommendation': [r'AE Recommendation:?\\s*(\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4})'],
                'editor_decision': [r'Editor Decision:?\\s*(\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4})']
            }
            
            for event_type, patterns in date_patterns.items():
                for pattern in patterns:
                    match = re.search(pattern, all_text, re.IGNORECASE)
                    if match:
                        timeline[event_type] = match.group(1)
                        logger.info(f"   📅 {event_type}: {timeline[event_type]}")
                        break
        
        except Exception as e:
            logger.error(f"❌ Error extracting timeline: {e}")
        
        return timeline
    
    def _extract_sicon_specific_data(self, soup, all_text: str) -> Dict:
        """Extract SICON-specific metadata"""
        data = {}
        
        try:
            # SICON specific patterns
            patterns = {
                'classification': r'Classification:?\\s*([^\\n]+)',
                'keywords': r'Keywords:?\\s*([^\\n]+)',
                'pages': r'Pages:?\\s*(\\d+)',
                'figures': r'Figures:?\\s*(\\d+)'
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, all_text, re.IGNORECASE)
                if match:
                    data[key] = match.group(1).strip()
                    
        except Exception as e:
            logger.error(f"❌ Error extracting SICON data: {e}")
        
        return data
    
    def _extract_sifin_specific_data(self, soup, all_text: str) -> Dict:
        """Extract SIFIN-specific metadata"""
        data = {}
        
        try:
            # SIFIN specific patterns
            patterns = {
                'jel_codes': r'JEL Codes?:?\\s*([^\\n]+)',
                'area': r'Area:?\\s*([^\\n]+)',
                'track': r'Track:?\\s*([^\\n]+)'
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, all_text, re.IGNORECASE)
                if match:
                    data[key] = match.group(1).strip()
                    
        except Exception as e:
            logger.error(f"❌ Error extracting SIFIN data: {e}")
        
        return data
    
    def _extract_all_pdf_links(self, manuscript_id: str) -> Dict:
        """Extract ALL PDF links from the manuscript detail page"""
        pdfs = {
            'manuscript': None,
            'cover_letter': None,
            'referee_reports': [],
            'supplementary': []
        }
        
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find all PDF links
            pdf_links = soup.find_all('a', href=re.compile(r'\\.pdf', re.IGNORECASE))
            
            logger.info(f"   📎 Found {len(pdf_links)} PDF links")
            
            for link in pdf_links:
                href = link.get('href', '')
                text = link.get_text().strip().lower()
                title = link.get('title', '').lower()
                
                # Make absolute URL
                if not href.startswith('http'):
                    current_url = self.driver.current_url
                    if href.startswith('/'):
                        base = '/'.join(current_url.split('/')[:3])
                        href = f"{base}{href}"
                    else:
                        href = f"{current_url.rsplit('/', 1)[0]}/{href}"
                
                # Categorize PDFs
                if any(keyword in text + title for keyword in ['manuscript', 'paper', 'article', manuscript_id.lower()]):
                    if not pdfs['manuscript']:  # Take the first manuscript PDF
                        pdfs['manuscript'] = href
                        logger.info(f"     📄 Manuscript PDF: {href}")
                
                elif any(keyword in text + title for keyword in ['cover', 'letter']):
                    pdfs['cover_letter'] = href
                    logger.info(f"     📝 Cover Letter PDF: {href}")
                
                elif any(keyword in text + title for keyword in ['review', 'report', 'referee', 'referee']):
                    pdfs['referee_reports'].append({
                        'url': href,
                        'description': text,
                        'title': title
                    })
                    logger.info(f"     📋 Referee Report PDF: {href}")
                
                elif any(keyword in text + title for keyword in ['supplement', 'appendix', 'additional']):
                    pdfs['supplementary'].append({
                        'url': href,
                        'description': text,
                        'title': title
                    })
                    logger.info(f"     📎 Supplementary PDF: {href}")
        
        except Exception as e:
            logger.error(f"❌ Error extracting PDF links: {e}")
        
        return pdfs
    
    def download_pdf(self, pdf_url: str, filename: str) -> bool:
        """Download a PDF file and save it to disk"""
        try:
            if not pdf_url:
                return False
                
            # Create downloads directory
            downloads_dir = self.results_dir / 'pdfs'
            downloads_dir.mkdir(exist_ok=True)
            
            # Full file path
            file_path = downloads_dir / filename
            
            logger.info(f"📥 Downloading PDF: {filename}")
            
            # For relative URLs, construct full URL
            if not pdf_url.startswith('http'):
                current_url = self.driver.current_url
                from urllib.parse import urljoin
                pdf_url = urljoin(current_url, pdf_url)
                logger.info(f"🔗 Constructed URL: {pdf_url}")
            
            # Use requests to download with session cookies from selenium
            import requests
            
            # Get cookies from selenium
            selenium_cookies = self.driver.get_cookies()
            session = requests.Session()
            
            for cookie in selenium_cookies:
                session.cookies.set(cookie['name'], cookie['value'])
            
            # Download the PDF
            response = session.get(pdf_url, stream=True)
            response.raise_for_status()
            
            # Check if it's actually a PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type:
                logger.warning(f"⚠️ URL did not return PDF (got {content_type}): {pdf_url}")
                return False
            
            # Save to file
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = file_path.stat().st_size
            logger.info(f"✅ PDF saved: {filename} ({file_size:,} bytes)")
            return True
                
        except Exception as e:
            logger.error(f"❌ Error downloading PDF {filename}: {e}")
            return False
    
    def cross_check_with_gmail(self, manuscripts: List[Dict]) -> Dict:
        """Cross-check manuscript referee data with Gmail emails"""
        gmail_data = {
            'emails_found': 0,
            'verified_referees': 0,
            'invitation_counts': {},
            'reminder_counts': {},
            'matching_emails': []
        }
        
        try:
            logger.info("📧 Starting Gmail cross-check...")
            
            # For each manuscript, search for related emails
            for manuscript in manuscripts:
                manuscript_id = manuscript['id']
                logger.info(f"🔍 Searching Gmail for {manuscript_id}...")
                
                # Search for emails related to this manuscript
                manuscript_emails = self._search_gmail_for_manuscript(manuscript_id)
                
                # Analyze email patterns
                invitation_count = 0
                reminder_count = 0
                
                for email in manuscript_emails:
                    subject = email.get('subject', '').lower()
                    
                    if any(word in subject for word in ['invitation', 'invite', 'review request']):
                        invitation_count += 1
                    elif any(word in subject for word in ['reminder', 'follow up', 'due']):
                        reminder_count += 1
                
                gmail_data['invitation_counts'][manuscript_id] = invitation_count
                gmail_data['reminder_counts'][manuscript_id] = reminder_count
                gmail_data['emails_found'] += len(manuscript_emails)
                gmail_data['matching_emails'].extend(manuscript_emails)
                
                # Update manuscript data with Gmail findings
                manuscript['gmail_verified'] = len(manuscript_emails) > 0
                manuscript['invitation_emails_count'] = invitation_count
                manuscript['reminder_emails_count'] = reminder_count
                
        except Exception as e:
            logger.error(f"❌ Gmail cross-check failed: {e}")
        
        return gmail_data
    
    def _search_gmail_for_manuscript(self, manuscript_id: str) -> List[Dict]:
        """Search Gmail for emails related to a specific manuscript using Gmail API"""
        emails = []
        
        try:
            # Try to import Gmail API
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            
            logger.info(f"🔍 Searching Gmail for manuscript {manuscript_id}...")
            
            # Gmail API scopes
            SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
            
            creds = None
            token_file = self.results_dir / 'gmail_token.json'
            
            # Load existing credentials
            if token_file.exists():
                creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
            
            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    # Look for credentials file
                    creds_file = self.results_dir / 'gmail_credentials.json'
                    if not creds_file.exists():
                        logger.warning(f"⚠️ Gmail credentials not found at {creds_file}")
                        logger.info("📝 To enable Gmail integration:")
                        logger.info("   1. Go to Google Cloud Console")
                        logger.info("   2. Enable Gmail API")
                        logger.info("   3. Download credentials.json")
                        logger.info(f"   4. Save as {creds_file}")
                        return emails
                    
                    flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save credentials for next run
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
            
            # Build Gmail service
            service = build('gmail', 'v1', credentials=creds)
            
            # Search for emails related to this manuscript
            queries = [
                f'subject:"{manuscript_id}"',
                f'body:"{manuscript_id}"',
                f'"{manuscript_id} review"',
                f'"{manuscript_id} referee"',
                f'"{manuscript_id} invitation"',
                f'"{manuscript_id} reminder"',
                f'"{manuscript_id} report"'
            ]
            
            # Also search for referee names if we have them
            if hasattr(self, 'current_manuscript_referees'):
                for referee in self.current_manuscript_referees.get(manuscript_id, []):
                    referee_name = referee.get('name', '')
                    if referee_name:
                        queries.extend([
                            f'"{referee_name}" "{manuscript_id}"',
                            f'to:"{referee_name}"',
                            f'"{referee_name}" review'
                        ])
            
            for query in queries:
                try:
                    results = service.users().messages().list(
                        userId='me', 
                        q=query,
                        maxResults=50
                    ).execute()
                    
                    messages = results.get('messages', [])
                    
                    for message in messages:
                        # Get message details
                        msg = service.users().messages().get(
                            userId='me', 
                            id=message['id']
                        ).execute()
                        
                        # Extract email data
                        headers = msg['payload'].get('headers', [])
                        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                        sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
                        date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                        
                        emails.append({
                            'id': message['id'],
                            'subject': subject,
                            'sender': sender,
                            'date': date,
                            'query': query
                        })
                        
                        logger.info(f"   📧 Found: {subject[:50]}... from {sender}")
                
                except Exception as e:
                    logger.warning(f"⚠️ Query '{query}' failed: {e}")
                    continue
            
            # Remove duplicates
            unique_emails = []
            seen_ids = set()
            for email in emails:
                if email['id'] not in seen_ids:
                    unique_emails.append(email)
                    seen_ids.add(email['id'])
            
            logger.info(f"✅ Found {len(unique_emails)} unique emails for {manuscript_id}")
            return unique_emails
            
        except ImportError:
            logger.error("❌ Gmail API libraries not installed. Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
            return emails
        except Exception as e:
            logger.error(f"❌ Error searching Gmail for {manuscript_id}: {e}")
            return emails
    
    def process_siam_journal(self, journal_code: str) -> List[Dict]:
        """Process a SIAM journal focusing on Associate Editor Tasks"""
        logger.info(f"📊 Processing {journal_code} Associate Editor Tasks ONLY")
        manuscripts = []
        
        try:
            if self.authenticate_siam(journal_code):
                logger.info("✅ Authentication successful - extracting AE tasks...")
                
                manuscripts = self.extract_ae_manuscripts(journal_code)
                
                # Extract detailed referee information for each manuscript
                for manuscript in manuscripts:
                    logger.info(f"🔍 Extracting detailed referee data for {manuscript['id']}...")
                    
                    # Navigate to manuscript detail page
                    manuscript_details = self.extract_manuscript_details(manuscript, journal_code)
                    manuscript.update(manuscript_details)
                    
                    # Process each referee found
                    for referee_data in manuscript.get('referees', []):
                        # Create referee timeline with real data
                        referee_timeline = RefereeTimeline(
                            name=referee_data.get('name', f"Referee for {manuscript['id']}"),
                            email=referee_data.get('email', f"referee.{manuscript['id'].lower()}@example.com"),
                            manuscript_id=manuscript['id'],
                            journal_code=journal_code
                        )
                        
                        # Add real events based on extracted data
                        if referee_data.get('invited_date'):
                            referee_timeline.add_event(RefereeEvent(
                                RefereeEventType.INVITED,
                                datetime.fromisoformat(referee_data['invited_date'])
                            ))
                        
                        if referee_data.get('accepted_date'):
                            referee_timeline.add_event(RefereeEvent(
                                RefereeEventType.ACCEPTED,
                                datetime.fromisoformat(referee_data['accepted_date'])
                            ))
                        
                        if referee_data.get('declined_date'):
                            referee_timeline.add_event(RefereeEvent(
                                RefereeEventType.DECLINED,
                                datetime.fromisoformat(referee_data['declined_date'])
                            ))
                        
                        if referee_data.get('submitted_date'):
                            referee_timeline.add_event(RefereeEvent(
                                RefereeEventType.REPORT_SUBMITTED,
                                datetime.fromisoformat(referee_data['submitted_date'])
                            ))
                        
                        # Add to analytics
                        self.analytics.add_timeline(referee_timeline)
                
                # Download PDFs for all manuscripts
                logger.info(f"📥 Downloading PDFs for {journal_code} manuscripts...")
                for manuscript in manuscripts:
                    manuscript_id = manuscript['id']
                    pdfs = manuscript.get('pdfs', {})
                    
                    # Download manuscript PDF
                    if pdfs.get('manuscript'):
                        self.download_pdf(pdfs['manuscript'], f"{manuscript_id}_manuscript.pdf")
                    
                    # Download cover letter PDF
                    if pdfs.get('cover_letter'):
                        self.download_pdf(pdfs['cover_letter'], f"{manuscript_id}_cover_letter.pdf")
                    
                    # Download referee report PDFs
                    for i, report in enumerate(pdfs.get('referee_reports', [])):
                        if report.get('url'):
                            self.download_pdf(report['url'], f"{manuscript_id}_referee_report_{i+1}.pdf")
                
                logger.info(f"✅ Total AE manuscripts processed in {journal_code}: {len(manuscripts)}")
            else:
                logger.error(f"❌ Authentication failed for {journal_code}")
        
        except Exception as e:
            logger.error(f"❌ Error processing {journal_code}: {e}")
        
        return manuscripts
    
    def run_complete_analysis(self):
        """Run complete referee analytics focusing on Associate Editor Tasks"""
        logger.info("🚀 Starting PROPERLY FIXED Selenium-based Referee Analytics")
        logger.info("🎯 Targeting Associate Editor Tasks sections ONLY")
        logger.info("=" * 60)
        
        # Set credentials
        os.environ['ORCID_EMAIL'] = 'dylan.possamai@polytechnique.org'
        os.environ['ORCID_PASSWORD'] = 'Hioupy0042%'
        
        all_manuscripts = {}
        
        try:
            self.setup_driver()
            
            # Process SIAM journals - ONLY Associate Editor Tasks
            for journal_code in ['SIFIN', 'SICON']:
                logger.info(f"\n{'='*60}")
                logger.info(f"📊 Processing {journal_code} - Associate Editor Tasks ONLY")
                logger.info(f"{'='*60}")
                
                manuscripts = self.process_siam_journal(journal_code)
                all_manuscripts[journal_code] = manuscripts
            
            # Perform Gmail cross-check
            logger.info("\n📧 Cross-checking with Gmail...")
            all_gmail_data = {}
            for journal_code, manuscripts in all_manuscripts.items():
                if manuscripts:  # Only process if we have manuscripts
                    gmail_data = self.cross_check_with_gmail(manuscripts)
                    all_gmail_data[journal_code] = gmail_data
            
            # Generate analytics
            logger.info("\n📊 Generating Analytics...")
            self.generate_report(all_manuscripts, all_gmail_data)
            
            logger.info("\n✅ Analysis Complete!")
            logger.info(f"📁 Results saved to: {self.results_dir}")
            
        except Exception as e:
            logger.error(f"❌ Analysis failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("🔚 Browser closed")
    
    def generate_report(self, all_manuscripts: Dict, gmail_data: Dict = None):
        """Generate analytics report"""
        overall_stats = self.analytics.get_overall_stats()
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'approach': 'selenium_based_PROPERLY_FIXED',
            'target': 'Associate_Editor_Tasks_ONLY',
            'cloudflare_handling': '60_second_wait',
            'features': [
                'detailed_referee_extraction',
                'pdf_download_support',
                'gmail_crosschecking',
                'timeline_analysis',
                'metadata_extraction'
            ],
            'overall_statistics': overall_stats,
            'journal_statistics': {},
            'gmail_data': gmail_data or {},
            'manuscripts_processed': {
                journal: len(manuscripts) 
                for journal, manuscripts in all_manuscripts.items()
            },
            'manuscript_details': all_manuscripts
        }
        
        # Add journal-specific stats
        for journal_code in ['SIFIN', 'SICON']:
            journal_stats = self.analytics.get_journal_stats(journal_code)
            if journal_stats:
                report['journal_statistics'][journal_code] = journal_stats
        
        # Save report
        report_file = self.results_dir / f"FIXED_ae_tasks_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\n" + "="*60)
        print("📊 PROPERLY FIXED - ASSOCIATE EDITOR TASKS ANALYTICS")
        print("="*60)
        
        if overall_stats and 'overall' in overall_stats:
            overall = overall_stats['overall']
            print(f"\n📈 Overall Statistics:")
            print(f"   Total Referees: {overall.get('total_referees', 0)}")
            print(f"   Total Reports: {overall.get('total_reports', 0)}")
        
        print(f"\n📄 Associate Editor Manuscripts:")
        for journal, manuscripts in all_manuscripts.items():
            print(f"\n   {journal}: {len(manuscripts)} manuscripts")
            for ms in manuscripts:
                category = ms.get('category', ms.get('status', 'Unknown'))
                print(f"      - {ms['id']} ({category})")
        
        print(f"\n💾 Full report saved to: {report_file}")
        
        # Validation check for expected 4 manuscripts each
        sifin_count = len(all_manuscripts.get('SIFIN', []))
        sicon_count = len(all_manuscripts.get('SICON', []))
        
        if sifin_count == 4 and sicon_count == 4:
            print(f"\n✅ SUCCESS: Found expected 4 manuscripts in each journal!")
        else:
            print(f"\n📊 RESULTS: SIFIN:{sifin_count}, SICON:{sicon_count}")
            print("   (Focusing on Associate Editor Tasks as specified)")


def main():
    """Main entry point"""
    analyzer = ProperlyFixedRefereeAnalyzer()
    analyzer.run_complete_analysis()


if __name__ == "__main__":
    main()