#!/usr/bin/env python3
"""
Complete Referee Extractor - Extracts full referee details including names, emails, and dates
Based on the working comprehensive scraper but with full Take Action implementation
"""

import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
import json
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from journals.mf import MFJournal
from journals.mor import MORJournal
from core.email_utils import fetch_starred_emails

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("COMPLETE_REFEREE_EXTRACTOR")


class CompleteRefereeExtractor:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.manuscripts_data = []
        self.output_dir = Path(f"{journal_name.lower()}_complete_referee_data")
        self.output_dir.mkdir(exist_ok=True)
        self.screenshot_count = 0
        
        # Define categories based on journal
        if journal_name == "MF":
            self.target_category = "Awaiting Reviewer Scores"
        else:
            self.target_category = "Awaiting Reviewer Reports"
            
    def create_driver(self, headless=False):
        """Create Chrome driver"""
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-popup-blocking')
        
        if headless:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
        
        try:
            self.driver = uc.Chrome(options=options)
        except:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            chrome_options = Options()
            for arg in options.arguments:
                chrome_options.add_argument(arg)
            self.driver = webdriver.Chrome(options=chrome_options)
            
    def take_screenshot(self, description):
        """Take screenshot for debugging"""
        self.screenshot_count += 1
        filename = f"{self.screenshot_count:03d}_{description.replace(' ', '_')}.png"
        filepath = self.output_dir / filename
        self.driver.save_screenshot(str(filepath))
        logger.info(f"📸 Screenshot: {filename}")
        
    def login_and_navigate_to_ae_center(self):
        """Login and navigate to AE Center"""
        logger.info(f"🔐 Logging into {self.journal_name}")
        
        if self.journal_name == "MF":
            self.journal = MFJournal(self.driver, debug=True)
        else:
            self.journal = MORJournal(self.driver, debug=True)
            
        self.journal.login()
        self.take_screenshot("after_login")
        
        # Navigate to AE Center
        ae_link = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
        )
        ae_link.click()
        time.sleep(3)
        self.take_screenshot("ae_center")
        logger.info("✅ At Associate Editor Center")
        
    def navigate_to_category(self):
        """Navigate to the target category"""
        logger.info(f"📂 Navigating to: {self.target_category}")
        
        try:
            category_link = self.driver.find_element(By.LINK_TEXT, self.target_category)
            category_link.click()
            time.sleep(3)
            self.take_screenshot(f"in_{self.target_category.replace(' ', '_')}")
            logger.info(f"✅ Successfully navigated to {self.target_category}")
            return True
        except Exception as e:
            logger.error(f"❌ Could not navigate to {self.target_category}: {e}")
            return False
            
    def get_manuscript_list(self):
        """Get list of manuscripts in current category"""
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Find manuscript IDs
        if self.journal_name == "MF":
            ms_pattern = r'MAFI-\d{4}-\d+'
        else:
            ms_pattern = r'MOR-\d{4}-\d+'
            
        ms_ids = list(set(re.findall(ms_pattern, soup.get_text())))
        logger.info(f"📄 Found {len(ms_ids)} manuscripts: {ms_ids}")
        return ms_ids
        
    def process_manuscript_with_take_action(self, manuscript_id):
        """Process a single manuscript using Take Action to get detailed referee info"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🔍 Processing manuscript: {manuscript_id}")
        logger.info(f"{'='*60}")
        
        manuscript_data = {
            'manuscript_id': manuscript_id,
            'title': '',
            'referees': [],
            'category': self.target_category,
            'extraction_time': datetime.now().isoformat()
        }
        
        try:
            # Find and click checkbox for this manuscript
            checkbox = self.find_manuscript_checkbox(manuscript_id)
            if not checkbox:
                logger.warning(f"❌ No checkbox found for {manuscript_id}")
                return manuscript_data
                
            # Click the checkbox
            self.driver.execute_script("arguments[0].click();", checkbox)
            time.sleep(1)
            logger.info("✅ Checkbox clicked")
            
            # Find and click Take Action button
            take_action_btn = self.find_take_action_button()
            if not take_action_btn:
                logger.warning("❌ No Take Action button found")
                return manuscript_data
                
            self.take_screenshot(f"before_take_action_{manuscript_id}")
            take_action_btn.click()
            time.sleep(3)
            self.take_screenshot(f"after_take_action_{manuscript_id}")
            logger.info("✅ Clicked Take Action")
            
            # Extract detailed information from the manuscript page
            manuscript_data = self.extract_detailed_manuscript_info(manuscript_id, manuscript_data)
            
            # Navigate back to category list
            self.navigate_back_to_list()
            
        except Exception as e:
            logger.error(f"❌ Error processing {manuscript_id}: {e}")
            self.take_screenshot(f"error_{manuscript_id}")
            
        return manuscript_data
        
    def find_manuscript_checkbox(self, manuscript_id):
        """Find checkbox for specific manuscript"""
        try:
            # Strategy 1: Find all table rows and look for manuscript ID
            rows = self.driver.find_elements(By.TAG_NAME, "tr")
            
            for row in rows:
                row_text = row.text
                if manuscript_id in row_text:
                    # Look for ANY clickable element in this row (checkbox, image, etc)
                    # Try checkbox first
                    checkboxes = row.find_elements(By.XPATH, ".//input[@type='checkbox']")
                    if checkboxes:
                        logger.info(f"✅ Found checkbox for {manuscript_id}")
                        return checkboxes[0]
                    
                    # Try image/icon that might act as checkbox
                    images = row.find_elements(By.XPATH, ".//img[@onclick or @src]")
                    for img in images:
                        src = img.get_attribute('src') or ''
                        onclick = img.get_attribute('onclick') or ''
                        if 'checkbox' in src.lower() or onclick:
                            logger.info(f"✅ Found clickable image for {manuscript_id}")
                            return img
                            
                    # Try any element in the Take Action column
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if cells:
                        # Last cell is typically Take Action column
                        last_cell = cells[-1]
                        clickables = last_cell.find_elements(By.XPATH, ".//*[@onclick or @href='#']")
                        if clickables:
                            logger.info(f"✅ Found clickable element in Take Action column for {manuscript_id}")
                            return clickables[0]
                        
            # Strategy 2: Find by partial match in onclick or other attributes
            all_clickables = self.driver.find_elements(By.XPATH, "//*[@onclick or @type='checkbox' or @href='#']")
            for element in all_clickables:
                onclick = element.get_attribute('onclick') or ''
                if manuscript_id in onclick:
                    logger.info(f"✅ Found element with onclick containing {manuscript_id}")
                    return element
                    
        except Exception as e:
            logger.error(f"Error finding checkbox: {e}")
            
        # Debug: print page source around manuscript ID
        try:
            page_source = self.driver.page_source
            ms_index = page_source.find(manuscript_id)
            if ms_index != -1:
                logger.debug(f"Context around {manuscript_id}:")
                logger.debug(page_source[max(0, ms_index-200):ms_index+200])
        except:
            pass
            
        return None
        
    def find_take_action_button(self):
        """Find Take Action button"""
        try:
            # Try multiple strategies
            strategies = [
                (By.XPATH, "//input[@value='Take Action']"),
                (By.XPATH, "//button[@value='Take Action']"),
                (By.XPATH, "//input[@type='submit' and contains(@value, 'Take')]"),
                (By.XPATH, "//button[contains(text(), 'Take Action')]"),
                (By.XPATH, "//input[@type='submit']"),
                (By.XPATH, "//button[@type='submit']"),
                (By.NAME, "submit"),
                (By.XPATH, "//a[contains(text(), 'Take Action')]")
            ]
            
            for by, value in strategies:
                try:
                    elements = self.driver.find_elements(by, value)
                    for elem in elements:
                        if elem.is_displayed():
                            elem_text = elem.get_attribute('value') or elem.text
                            logger.info(f"Found potential button: {elem_text}")
                            if 'take' in elem_text.lower() or 'submit' in elem_text.lower():
                                return elem
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"Error finding Take Action button: {e}")
            
        return None
        
    def extract_detailed_manuscript_info(self, manuscript_id, manuscript_data):
        """Extract all detailed information from manuscript detail page"""
        logger.info("📊 Extracting detailed manuscript information...")
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        page_text = soup.get_text()
        
        # Extract manuscript title
        title_match = re.search(f'{manuscript_id}[^\\n]*\\n[^\\n]*\\n([^\\n]+)', page_text)
        if title_match:
            manuscript_data['title'] = title_match.group(1).strip()
            logger.info(f"📄 Title: {manuscript_data['title']}")
            
        # Extract referee information
        referee_data = self.extract_referee_details()
        manuscript_data['referees'] = referee_data
        
        return manuscript_data
        
    def extract_referee_details(self):
        """Extract detailed referee information from current page"""
        logger.info("👥 Extracting referee details...")
        
        referees = []
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Find all potential referee links
        referee_candidates = []
        
        # Strategy 1: Look for links that appear to be names
        for link in soup.find_all('a'):
            link_text = link.get_text(strip=True)
            
            # Check if this looks like a person's name
            if self.is_likely_referee_name(link_text):
                referee_candidates.append({
                    'element': link,
                    'name': link_text
                })
                
        # Strategy 2: Look for referee information in tables
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                row_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                
                # Look for patterns indicating referee info
                if any(keyword in row_text.lower() for keyword in ['referee', 'reviewer', 'invited', 'agreed']):
                    # Extract names from this row
                    for cell in cells:
                        cell_text = cell.get_text(strip=True)
                        if self.is_likely_referee_name(cell_text):
                            referee_candidates.append({
                                'element': cell,
                                'name': cell_text
                            })
                            
        # Process each referee candidate
        seen_names = set()
        for candidate in referee_candidates:
            name = candidate['name']
            
            if name in seen_names:
                continue
                
            seen_names.add(name)
            logger.info(f"  👤 Processing referee: {name}")
            
            referee_info = {
                'name': name,
                'email': '',
                'status': 'unknown',
                'invited_date': '',
                'agreed_date': '',
                'declined_date': '',
                'due_date': '',
                'time_in_review': '',
                'report_submitted': False
            }
            
            # Try to extract email by clicking the name
            email = self.extract_referee_email_by_clicking(name)
            if email:
                referee_info['email'] = email
                logger.info(f"    📧 Email: {email}")
                
            # Extract status and dates from surrounding text
            referee_info = self.extract_referee_timeline(name, referee_info)
            
            referees.append(referee_info)
            
        logger.info(f"✅ Found {len(referees)} referees with details")
        return referees
        
    def is_likely_referee_name(self, text):
        """Check if text is likely a referee name"""
        if not text or len(text) < 3:
            return False
            
        # Exclude common UI elements
        exclude_patterns = [
            'view', 'download', 'edit', 'manuscript', 'submission',
            'center', 'logout', 'home', 'help', 'associate editor',
            'take action', 'select', 'all', 'none', 'pdf', 'report'
        ]
        
        text_lower = text.lower()
        if any(pattern in text_lower for pattern in exclude_patterns):
            return False
            
        # Check for name-like patterns
        # Names typically have spaces and capital letters
        if ' ' not in text:
            return False
            
        # Check for at least one capital letter
        if not any(c.isupper() for c in text):
            return False
            
        # Check for reasonable length
        if len(text) > 50:
            return False
            
        # Check if it contains common name patterns
        name_parts = text.split()
        if len(name_parts) >= 2 and len(name_parts) <= 5:
            # Likely a name
            return True
            
        return False
        
    def extract_referee_email_by_clicking(self, referee_name):
        """Extract referee email by clicking on their name"""
        try:
            # Save current window handle
            main_window = self.driver.current_window_handle
            
            # Try to find and click the referee name link
            try:
                referee_link = self.driver.find_element(By.LINK_TEXT, referee_name)
                referee_link.click()
                time.sleep(2)
            except:
                # Try partial link text
                try:
                    referee_link = self.driver.find_element(By.PARTIAL_LINK_TEXT, referee_name.split()[-1])
                    referee_link.click()
                    time.sleep(2)
                except:
                    return None
                    
            # Check if a new window/popup opened
            all_windows = self.driver.window_handles
            
            if len(all_windows) > 1:
                # Switch to the popup
                for window in all_windows:
                    if window != main_window:
                        self.driver.switch_to.window(window)
                        break
                        
                # Extract email from popup
                popup_html = self.driver.page_source
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = re.findall(email_pattern, popup_html)
                
                # Close popup and switch back
                self.driver.close()
                self.driver.switch_to.window(main_window)
                
                if emails:
                    # Return the first valid email found
                    for email in emails:
                        if not email.startswith('noreply') and '@' in email:
                            return email
                            
            else:
                # No popup, check if email is visible on current page
                current_html = self.driver.page_source
                
                # Look for email near the referee name
                name_index = current_html.find(referee_name)
                if name_index != -1:
                    # Check surrounding text for email
                    surrounding = current_html[max(0, name_index-500):name_index+500]
                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                    emails = re.findall(email_pattern, surrounding)
                    
                    if emails:
                        return emails[0]
                        
        except Exception as e:
            logger.debug(f"Could not extract email for {referee_name}: {e}")
            # Make sure we're back in main window
            try:
                self.driver.switch_to.window(main_window)
            except:
                pass
                
        return None
        
    def extract_referee_timeline(self, referee_name, referee_info):
        """Extract referee timeline information from page"""
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        page_text = soup.get_text()
        
        # Find text around referee name
        name_index = page_text.find(referee_name)
        if name_index == -1:
            return referee_info
            
        # Get surrounding context
        start = max(0, name_index - 1000)
        end = min(len(page_text), name_index + 1000)
        context = page_text[start:end]
        
        # Extract status
        if 'agreed' in context.lower():
            referee_info['status'] = 'agreed'
        elif 'declined' in context.lower():
            referee_info['status'] = 'declined'
        elif 'unavailable' in context.lower():
            referee_info['status'] = 'unavailable'
        elif 'invited' in context.lower():
            referee_info['status'] = 'invited'
            
        # Extract dates using patterns
        date_patterns = {
            'invited_date': [
                r'Invited[:\s]+(\d{1,2}-\w{3}-\d{4})',
                r'Invitation sent[:\s]+(\d{1,2}-\w{3}-\d{4})'
            ],
            'agreed_date': [
                r'Agreed[:\s]+(\d{1,2}-\w{3}-\d{4})',
                r'Accepted[:\s]+(\d{1,2}-\w{3}-\d{4})'
            ],
            'declined_date': [
                r'Declined[:\s]+(\d{1,2}-\w{3}-\d{4})',
                r'Unavailable[:\s]+(\d{1,2}-\w{3}-\d{4})'
            ],
            'due_date': [
                r'Due Date[:\s]+(\d{1,2}-\w{3}-\d{4})',
                r'Due[:\s]+(\d{1,2}-\w{3}-\d{4})'
            ]
        }
        
        for field, patterns in date_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, context, re.IGNORECASE)
                if match:
                    referee_info[field] = match.group(1)
                    break
                    
        # Extract time in review
        time_pattern = r'Time in Review[:\s]+(\d+\s+Days?)'
        time_match = re.search(time_pattern, context, re.IGNORECASE)
        if time_match:
            referee_info['time_in_review'] = time_match.group(1)
            
        # Check if report submitted
        if 'returned' in context.lower() or 'submitted' in context.lower():
            referee_info['report_submitted'] = True
            
        return referee_info
        
    def navigate_back_to_list(self):
        """Navigate back to manuscript list"""
        try:
            # Try multiple methods to go back
            strategies = [
                lambda: self.driver.find_element(By.LINK_TEXT, "Associate Editor Center").click(),
                lambda: self.driver.find_element(By.PARTIAL_LINK_TEXT, "Back to").click(),
                lambda: self.driver.back()
            ]
            
            for strategy in strategies:
                try:
                    strategy()
                    time.sleep(2)
                    
                    # Check if we need to navigate to category again
                    if self.target_category not in self.driver.page_source:
                        self.navigate_to_category()
                        
                    return True
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"Error navigating back: {e}")
            
        return False
        
    def run_extraction(self, headless=False):
        """Run the complete extraction process"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 Starting Complete Referee Extraction for {self.journal_name}")
        logger.info(f"{'='*80}")
        
        self.create_driver(headless=headless)
        
        try:
            # Login and navigate
            self.login_and_navigate_to_ae_center()
            
            # Navigate to target category
            if not self.navigate_to_category():
                logger.error("Failed to navigate to target category")
                return
                
            # Get list of manuscripts
            manuscript_ids = self.get_manuscript_list()
            
            # Process each manuscript
            for ms_id in manuscript_ids:
                manuscript_data = self.process_manuscript_with_take_action(ms_id)
                self.manuscripts_data.append(manuscript_data)
                
            # Save results
            self.save_results()
            
            # Print summary
            self.print_summary()
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            self.take_screenshot("fatal_error")
            
        finally:
            self.driver.quit()
            
    def save_results(self):
        """Save extraction results"""
        results = {
            'journal': self.journal_name,
            'extraction_date': datetime.now().isoformat(),
            'target_category': self.target_category,
            'total_manuscripts': len(self.manuscripts_data),
            'manuscripts': self.manuscripts_data
        }
        
        # Save as JSON
        output_file = self.output_dir / f"{self.journal_name.lower()}_complete_referee_data.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
            
        logger.info(f"\n💾 Results saved to: {output_file}")
        
        # Also save as formatted text report
        report_file = self.output_dir / f"{self.journal_name.lower()}_referee_report.txt"
        with open(report_file, 'w') as f:
            f.write(f"Complete Referee Report for {self.journal_name}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            
            for ms in self.manuscripts_data:
                f.write(f"Manuscript: {ms['manuscript_id']}\n")
                f.write(f"Title: {ms['title']}\n")
                f.write(f"Category: {ms['category']}\n")
                f.write(f"Referees ({len(ms['referees'])}):\n")
                
                for i, ref in enumerate(ms['referees'], 1):
                    f.write(f"\n  Referee {i}:\n")
                    f.write(f"    Name: {ref['name']}\n")
                    f.write(f"    Email: {ref['email'] or 'Not found'}\n")
                    f.write(f"    Status: {ref['status']}\n")
                    if ref['invited_date']:
                        f.write(f"    Invited: {ref['invited_date']}\n")
                    if ref['agreed_date']:
                        f.write(f"    Agreed: {ref['agreed_date']}\n")
                    if ref['due_date']:
                        f.write(f"    Due: {ref['due_date']}\n")
                    if ref['time_in_review']:
                        f.write(f"    Time in Review: {ref['time_in_review']}\n")
                    if ref['report_submitted']:
                        f.write(f"    Report: Submitted\n")
                        
                f.write("\n" + "-"*80 + "\n\n")
                
        logger.info(f"📄 Report saved to: {report_file}")
        
    def print_summary(self):
        """Print extraction summary"""
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 EXTRACTION SUMMARY FOR {self.journal_name}")
        logger.info(f"{'='*80}")
        
        total_referees = sum(len(ms['referees']) for ms in self.manuscripts_data)
        referees_with_emails = sum(1 for ms in self.manuscripts_data 
                                  for ref in ms['referees'] if ref['email'])
        
        logger.info(f"📄 Total manuscripts processed: {len(self.manuscripts_data)}")
        logger.info(f"👥 Total referees found: {total_referees}")
        logger.info(f"📧 Referees with emails: {referees_with_emails}")
        
        for ms in self.manuscripts_data:
            logger.info(f"\n📄 {ms['manuscript_id']}: {ms['title'][:50]}...")
            logger.info(f"   Referees: {len(ms['referees'])}")
            
            for ref in ms['referees']:
                status_emoji = {
                    'agreed': '✅',
                    'declined': '❌',
                    'invited': '📨',
                    'unavailable': '🚫',
                    'unknown': '❓'
                }.get(ref['status'], '❓')
                
                email_status = '📧' if ref['email'] else '❌'
                logger.info(f"   {status_emoji} {ref['name']} {email_status}")


def main():
    """Run complete extraction for both journals"""
    
    # Extract for MF
    logger.info("\n" + "="*80)
    logger.info("EXTRACTING COMPLETE REFEREE DATA FOR MF")
    logger.info("="*80)
    
    mf_extractor = CompleteRefereeExtractor("MF")
    mf_extractor.run_extraction(headless=False)
    
    # Extract for MOR
    logger.info("\n\n" + "="*80)
    logger.info("EXTRACTING COMPLETE REFEREE DATA FOR MOR")
    logger.info("="*80)
    
    mor_extractor = CompleteRefereeExtractor("MOR")
    mor_extractor.run_extraction(headless=False)


if __name__ == "__main__":
    main()