#!/usr/bin/env python3
"""
Simplified referee extractor that works with the actual page structure
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
logger = logging.getLogger("SIMPLE_REFEREE_EXTRACTOR")


class SimpleRefereeExtractor:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.output_dir = Path(f"{journal_name.lower()}_referee_details")
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
            
    def run_extraction(self):
        """Run the extraction process"""
        logger.info(f"🚀 Starting referee extraction for {self.journal_name}")
        
        self.create_driver(headless=False)
        results = []
        
        try:
            # Login
            if self.journal_name == "MF":
                self.journal = MFJournal(self.driver, debug=True)
                category = "Awaiting Reviewer Scores"
            else:
                self.journal = MORJournal(self.driver, debug=True)
                category = "Awaiting Reviewer Reports"
                
            self.journal.login()
            
            # Navigate to AE Center
            ae_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            time.sleep(3)
            
            # Navigate to category
            logger.info(f"📂 Navigating to {category}")
            category_link = self.driver.find_element(By.LINK_TEXT, category)
            category_link.click()
            time.sleep(3)
            
            # Extract manuscripts and process each one
            manuscript_ids = self.get_manuscript_ids()
            logger.info(f"📄 Found {len(manuscript_ids)} manuscripts")
            
            for i, ms_id in enumerate(manuscript_ids):
                logger.info(f"\n{'='*60}")
                logger.info(f"📄 Processing manuscript {i+1}/{len(manuscript_ids)}: {ms_id}")
                logger.info(f"{'='*60}")
                
                manuscript_data = self.process_single_manuscript(ms_id, category)
                results.append(manuscript_data)
                
                # Navigate back to category if needed
                if i < len(manuscript_ids) - 1:
                    self.navigate_back_to_category(category)
                    
            # Save results
            self.save_results(results)
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            
        finally:
            self.driver.quit()
            
    def get_manuscript_ids(self):
        """Get manuscript IDs from current page"""
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        if self.journal_name == "MF":
            pattern = r'MAFI-\d{4}-\d+'
        else:
            pattern = r'MOR-\d{4}-\d+'
            
        ms_ids = list(set(re.findall(pattern, soup.get_text())))
        return ms_ids
        
    def process_single_manuscript(self, manuscript_id, category):
        """Process a single manuscript by clicking on it directly"""
        manuscript_data = {
            'manuscript_id': manuscript_id,
            'category': category,
            'title': '',
            'referees': []
        }
        
        try:
            # Method 1: Try clicking the manuscript ID directly
            try:
                ms_link = self.driver.find_element(By.LINK_TEXT, manuscript_id)
                ms_link.click()
                time.sleep(3)
                logger.info("✅ Clicked manuscript ID link")
                
            except:
                # Method 2: Try finding the row and clicking Take Action checkbox
                logger.info("Trying checkbox method...")
                
                # Find the row containing this manuscript
                rows = self.driver.find_elements(By.TAG_NAME, "tr")
                target_row = None
                
                for row in rows:
                    if manuscript_id in row.text:
                        target_row = row
                        break
                        
                if target_row:
                    # Find the last cell (Take Action column)
                    cells = target_row.find_elements(By.TAG_NAME, "td")
                    if cells:
                        last_cell = cells[-1]
                        
                        # Try to click any element in the last cell
                        clickable = last_cell.find_element(By.XPATH, ".//*")
                        self.driver.execute_script("arguments[0].click();", clickable)
                        time.sleep(1)
                        
                        # Now find and click the Take Action button
                        take_action_btns = self.driver.find_elements(By.XPATH, "//input[@type='submit']")
                        for btn in take_action_btns:
                            if btn.is_displayed():
                                btn.click()
                                time.sleep(3)
                                logger.info("✅ Clicked Take Action")
                                break
                                
            # Extract manuscript details
            manuscript_data = self.extract_manuscript_details(manuscript_id, manuscript_data)
            
        except Exception as e:
            logger.error(f"Error processing {manuscript_id}: {e}")
            
        return manuscript_data
        
    def extract_manuscript_details(self, manuscript_id, manuscript_data):
        """Extract details from manuscript page"""
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        page_text = soup.get_text()
        
        # Extract title
        title_patterns = [
            rf'{manuscript_id}[^\n]*\n[^\n]*\n([^\n]+)',
            rf'{manuscript_id}.*?Title:\s*([^\n]+)',
            rf'Title[:\s]+([^\n]+)'
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, page_text, re.MULTILINE | re.DOTALL)
            if match:
                manuscript_data['title'] = match.group(1).strip()
                break
                
        logger.info(f"📄 Title: {manuscript_data['title'][:50]}...")
        
        # Extract referees
        referees = self.extract_referees_from_page(soup)
        manuscript_data['referees'] = referees
        
        logger.info(f"👥 Found {len(referees)} referees")
        
        return manuscript_data
        
    def extract_referees_from_page(self, soup):
        """Extract referee information from page"""
        referees = []
        
        # Look for patterns that indicate referee information
        # Common patterns: tables with referee names, status, dates
        
        # Method 1: Look for tables with referee information
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                row_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                
                # Check if this row contains referee info
                if any(keyword in row_text.lower() for keyword in ['referee', 'reviewer', 'invited', 'agreed']):
                    # Extract referee name (usually a link or bold text)
                    for cell in cells:
                        links = cell.find_all('a')
                        for link in links:
                            name = link.get_text(strip=True)
                            if self.is_likely_name(name):
                                referee = {
                                    'name': name,
                                    'email': '',
                                    'status': self.extract_status_from_row(row_text),
                                    'dates': self.extract_dates_from_row(row_text)
                                }
                                
                                # Try to get email
                                email = self.try_extract_email(name)
                                if email:
                                    referee['email'] = email
                                    
                                referees.append(referee)
                                logger.info(f"  👤 Found referee: {name} ({referee['status']})")
                                
        # Method 2: Look for referee names in specific patterns
        if not referees:
            # Look for patterns like "Referee: Name" or "Reviewer: Name"
            referee_patterns = [
                r'(?:Referee|Reviewer)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
                r'(?:Dr\.|Prof\.|Mr\.|Ms\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
            ]
            
            page_text = soup.get_text()
            for pattern in referee_patterns:
                matches = re.findall(pattern, page_text)
                for name in matches:
                    if self.is_likely_name(name) and not any(r['name'] == name for r in referees):
                        referee = {
                            'name': name,
                            'email': '',
                            'status': 'unknown',
                            'dates': {}
                        }
                        referees.append(referee)
                        
        return referees
        
    def is_likely_name(self, text):
        """Check if text is likely a person's name"""
        if not text or len(text) < 3:
            return False
            
        # Exclude common non-name patterns
        exclude = ['manuscript', 'submission', 'view', 'download', 'edit', 'select', 'action']
        if any(word in text.lower() for word in exclude):
            return False
            
        # Names typically have 2-4 parts
        parts = text.split()
        if len(parts) < 2 or len(parts) > 5:
            return False
            
        # At least one capital letter
        if not any(c.isupper() for c in text):
            return False
            
        return True
        
    def extract_status_from_row(self, text):
        """Extract referee status from text"""
        text_lower = text.lower()
        
        if 'agreed' in text_lower:
            return 'agreed'
        elif 'declined' in text_lower:
            return 'declined'
        elif 'invited' in text_lower:
            return 'invited'
        elif 'unavailable' in text_lower:
            return 'unavailable'
        else:
            return 'unknown'
            
    def extract_dates_from_row(self, text):
        """Extract dates from text"""
        dates = {}
        
        date_patterns = {
            'invited': r'(?:Invited|Invitation)[:\s]+(\d{1,2}-\w{3}-\d{4})',
            'agreed': r'(?:Agreed|Accepted)[:\s]+(\d{1,2}-\w{3}-\d{4})',
            'due': r'(?:Due|Deadline)[:\s]+(\d{1,2}-\w{3}-\d{4})'
        }
        
        for key, pattern in date_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                dates[key] = match.group(1)
                
        return dates
        
    def try_extract_email(self, referee_name):
        """Try to extract email by clicking referee name"""
        try:
            # Save current window
            main_window = self.driver.current_window_handle
            
            # Try clicking the name
            try:
                link = self.driver.find_element(By.LINK_TEXT, referee_name)
                link.click()
                time.sleep(1)
                
                # Check for popup
                windows = self.driver.window_handles
                if len(windows) > 1:
                    # Switch to popup
                    self.driver.switch_to.window(windows[-1])
                    
                    # Look for email
                    popup_text = self.driver.page_source
                    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', popup_text)
                    
                    # Close popup
                    self.driver.close()
                    self.driver.switch_to.window(main_window)
                    
                    if email_match:
                        return email_match.group(0)
                        
            except:
                pass
                
        except:
            pass
            
        return None
        
    def navigate_back_to_category(self, category):
        """Navigate back to category list"""
        try:
            # Try Associate Editor Center link
            ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
            ae_link.click()
            time.sleep(2)
            
            # Navigate to category again
            category_link = self.driver.find_element(By.LINK_TEXT, category)
            category_link.click()
            time.sleep(2)
            
        except:
            # Try browser back
            self.driver.back()
            time.sleep(2)
            
    def save_results(self, results):
        """Save extraction results"""
        output_data = {
            'journal': self.journal_name,
            'extraction_date': datetime.now().isoformat(),
            'manuscripts': results
        }
        
        # Save JSON
        json_file = self.output_dir / f"{self.journal_name.lower()}_referees.json"
        with open(json_file, 'w') as f:
            json.dump(output_data, f, indent=2)
            
        logger.info(f"\n💾 Results saved to: {json_file}")
        
        # Print summary
        total_referees = sum(len(ms['referees']) for ms in results)
        logger.info(f"\n📊 SUMMARY:")
        logger.info(f"  📄 Manuscripts: {len(results)}")
        logger.info(f"  👥 Total referees: {total_referees}")
        
        for ms in results:
            logger.info(f"\n  {ms['manuscript_id']}: {len(ms['referees'])} referees")
            for ref in ms['referees']:
                logger.info(f"    • {ref['name']} ({ref['status']})")


def main():
    """Run extraction for both journals"""
    
    # Extract MF
    logger.info("="*80)
    logger.info("EXTRACTING MF REFEREE DETAILS")
    logger.info("="*80)
    
    mf_extractor = SimpleRefereeExtractor("MF")
    mf_extractor.run_extraction()
    
    # Extract MOR
    logger.info("\n" + "="*80)
    logger.info("EXTRACTING MOR REFEREE DETAILS")
    logger.info("="*80)
    
    mor_extractor = SimpleRefereeExtractor("MOR")
    mor_extractor.run_extraction()


if __name__ == "__main__":
    main()