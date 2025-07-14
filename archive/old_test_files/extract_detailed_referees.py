#!/usr/bin/env python3
"""
Extract detailed referee information including names and emails
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DETAILED_REFEREE_EXTRACTOR")


class DetailedRefereeExtractor:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.output_dir = Path(f"{journal_name.lower()}_detailed_referees")
        self.output_dir.mkdir(exist_ok=True)
        
    def create_driver(self, headless=False):
        """Create Chrome driver"""
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
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
            
    def login_and_navigate(self):
        """Login and navigate to AE Center"""
        logger.info(f"🔐 Logging into {self.journal_name}")
        
        if self.journal_name == "MF":
            self.journal = MFJournal(self.driver, debug=True)
        else:
            self.journal = MORJournal(self.driver, debug=True)
            
        self.journal.login()
        
        # Navigate to AE Center
        ae_link = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
        )
        ae_link.click()
        time.sleep(3)
        
    def navigate_to_category(self, category_name):
        """Navigate to specific category"""
        try:
            category_link = self.driver.find_element(By.LINK_TEXT, category_name)
            category_link.click()
            time.sleep(3)
            return True
        except Exception as e:
            logger.error(f"Could not navigate to {category_name}: {e}")
            return False
            
    def extract_detailed_referee_info(self, manuscript_id):
        """Extract detailed referee information for a manuscript"""
        logger.info(f"🔍 Extracting detailed referee info for {manuscript_id}")
        
        try:
            # Find checkbox for this manuscript
            checkbox = None
            rows = self.driver.find_elements(By.TAG_NAME, "tr")
            
            for row in rows:
                if manuscript_id in row.text:
                    checkboxes = row.find_elements(By.XPATH, ".//input[@type='checkbox']")
                    if checkboxes:
                        checkbox = checkboxes[0]
                        break
                        
            if not checkbox:
                logger.warning(f"No checkbox found for {manuscript_id}")
                return None
                
            # Click checkbox
            checkbox.click()
            time.sleep(1)
            
            # Click Take Action
            take_action_button = self.driver.find_element(By.XPATH, "//input[@value='Take Action' or @type='submit']")
            take_action_button.click()
            time.sleep(3)
            
            # Now extract referee details from the detail page
            referee_details = self.extract_referees_from_detail_page(manuscript_id)
            
            # Navigate back to AE Center
            ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
            ae_link.click()
            time.sleep(2)
            
            return referee_details
            
        except Exception as e:
            logger.error(f"Error extracting referee info for {manuscript_id}: {e}")
            return None
            
    def extract_referees_from_detail_page(self, manuscript_id):
        """Extract referee details from manuscript detail page"""
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        referees = []
        
        # Look for referee names (they're usually links)
        referee_links = []
        for link in soup.find_all('a'):
            link_text = link.get_text(strip=True)
            # Check if this looks like a referee name
            if (' ' in link_text and 
                any(c.isupper() for c in link_text) and
                len(link_text) > 3 and
                not any(word in link_text.lower() for word in ['view', 'download', 'edit', 'manuscript', 'submission'])):
                
                # This might be a referee name
                referee_links.append(link_text)
                
        # Extract email by clicking on referee names
        for referee_name in referee_links:
            referee_info = {
                'name': referee_name,
                'email': '',
                'status': 'unknown',
                'invited_date': '',
                'agreed_date': '',
                'due_date': '',
                'time_in_review': ''
            }
            
            # Try to extract email by clicking the name
            try:
                email = self.extract_referee_email(referee_name)
                if email:
                    referee_info['email'] = email
            except:
                pass
                
            # Extract status and dates from page
            page_text = soup.get_text()
            
            # Look for status patterns near the referee name
            name_index = page_text.find(referee_name)
            if name_index != -1:
                # Check surrounding text for status
                surrounding_text = page_text[max(0, name_index-200):name_index+500]
                
                if 'agreed' in surrounding_text.lower():
                    referee_info['status'] = 'agreed'
                elif 'declined' in surrounding_text.lower():
                    referee_info['status'] = 'declined'
                elif 'invited' in surrounding_text.lower():
                    referee_info['status'] = 'invited'
                    
                # Extract dates
                date_patterns = {
                    'invited_date': r'Invited:\s*(\d{2}-\w{3}-\d{4})',
                    'agreed_date': r'Agreed:\s*(\d{2}-\w{3}-\d{4})',
                    'due_date': r'Due Date:\s*(\d{2}-\w{3}-\d{4})',
                    'time_in_review': r'Time in Review:\s*(\d+\s+Days)'
                }
                
                for field, pattern in date_patterns.items():
                    match = re.search(pattern, surrounding_text)
                    if match:
                        referee_info[field] = match.group(1)
                        
            referees.append(referee_info)
            logger.info(f"  Found referee: {referee_name} ({referee_info['status']})")
            
        return referees
        
    def extract_referee_email(self, referee_name):
        """Extract email by clicking referee name"""
        try:
            # Save current window
            main_window = self.driver.current_window_handle
            
            # Click referee name
            referee_link = self.driver.find_element(By.LINK_TEXT, referee_name)
            referee_link.click()
            time.sleep(2)
            
            # Check if popup opened
            all_windows = self.driver.window_handles
            if len(all_windows) > 1:
                # Switch to popup
                for window in all_windows:
                    if window != main_window:
                        self.driver.switch_to.window(window)
                        break
                        
                # Extract email from popup
                popup_html = self.driver.page_source
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = re.findall(email_pattern, popup_html)
                
                # Close popup
                self.driver.close()
                self.driver.switch_to.window(main_window)
                
                return emails[0] if emails else None
            else:
                # No popup, check current page
                return None
                
        except Exception as e:
            logger.warning(f"Could not extract email for {referee_name}: {e}")
            # Make sure we're back to main window
            try:
                self.driver.switch_to.window(main_window)
            except:
                pass
            return None
            
    def run_extraction(self):
        """Run the complete extraction process"""
        self.create_driver(headless=False)  # Use non-headless for debugging
        results = {
            'journal': self.journal_name,
            'extraction_date': datetime.now().isoformat(),
            'manuscripts': []
        }
        
        try:
            # Login and navigate
            self.login_and_navigate()
            
            # Define categories to check
            if self.journal_name == "MF":
                categories = ["Awaiting Reviewer Scores"]
                expected_manuscripts = ["MAFI-2024-0167", "MAFI-2025-0166"]
            else:
                categories = ["Awaiting Reviewer Reports"]
                expected_manuscripts = ["MOR-2025-1037", "MOR-2023-0376", "MOR-2024-0804"]
                
            # Process each category
            for category in categories:
                logger.info(f"\n📂 Processing category: {category}")
                
                if self.navigate_to_category(category):
                    # Extract referee info for each expected manuscript
                    for manuscript_id in expected_manuscripts:
                        referee_details = self.extract_detailed_referee_info(manuscript_id)
                        
                        if referee_details:
                            results['manuscripts'].append({
                                'manuscript_id': manuscript_id,
                                'category': category,
                                'referees': referee_details
                            })
                            
                        # Navigate back to category
                        self.navigate_to_category(category)
                        
            # Save results
            output_file = self.output_dir / f"{self.journal_name.lower()}_detailed_referees.json"
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
                
            logger.info(f"\n💾 Results saved to: {output_file}")
            
            # Print summary
            self.print_summary(results)
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            
        finally:
            self.driver.quit()
            
    def print_summary(self, results):
        """Print summary of extracted referee details"""
        logger.info("\n" + "="*80)
        logger.info(f"📊 DETAILED REFEREE EXTRACTION RESULTS FOR {self.journal_name}")
        logger.info("="*80)
        
        total_referees = 0
        
        for manuscript in results['manuscripts']:
            ms_id = manuscript['manuscript_id']
            referees = manuscript['referees']
            
            logger.info(f"\n📄 {ms_id}: {len(referees)} referees")
            
            for ref in referees:
                total_referees += 1
                logger.info(f"  • {ref['name']}")
                logger.info(f"    Email: {ref['email'] or 'Not found'}")
                logger.info(f"    Status: {ref['status']}")
                if ref['due_date']:
                    logger.info(f"    Due: {ref['due_date']}")
                    
        logger.info(f"\n📊 Total referees with details: {total_referees}")


def main():
    """Extract detailed referee info for both journals"""
    
    # Test with MF first
    logger.info("\n" + "="*80)
    logger.info("EXTRACTING DETAILED REFEREE INFO FOR MF")
    logger.info("="*80)
    
    mf_extractor = DetailedRefereeExtractor("MF")
    mf_extractor.run_extraction()
    
    # Then MOR
    logger.info("\n" + "="*80)
    logger.info("EXTRACTING DETAILED REFEREE INFO FOR MOR")
    logger.info("="*80)
    
    mor_extractor = DetailedRefereeExtractor("MOR")
    mor_extractor.run_extraction()


if __name__ == "__main__":
    main()