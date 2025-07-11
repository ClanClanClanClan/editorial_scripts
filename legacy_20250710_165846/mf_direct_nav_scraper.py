#!/usr/bin/env python3
"""
MF scraper that handles direct navigation to manuscript details.
When clicking status text with count 2, it goes to first manuscript directly.
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
from bs4 import BeautifulSoup
import json
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from journals.mf import MFJournal
from core.email_utils import fetch_starred_emails

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MF_DIRECT")


class DirectNavScraper:
    def __init__(self):
        self.driver = None
        self.journal = None
        self.manuscripts = []
        self.debug_dir = Path("mf_direct_debug")
        self.debug_dir.mkdir(exist_ok=True)
        self.screenshot_count = 0
        
    def create_driver(self):
        """Create Chrome driver"""
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
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
        """Take a screenshot"""
        self.screenshot_count += 1
        filename = f"{self.screenshot_count:03d}_{description.replace(' ', '_')}.png"
        filepath = self.debug_dir / filename
        self.driver.save_screenshot(str(filepath))
        logger.info(f"📸 Screenshot: {filename}")
        
    def save_html(self, description):
        """Save current HTML"""
        filename = f"{description.replace(' ', '_')}.html"
        filepath = self.debug_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
            
    def detect_page_type(self):
        """Detect if we're on a list page or detail page"""
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        text = soup.get_text()
        
        # Count manuscript IDs
        ms_ids = list(set(re.findall(r'MAFI-\d{4}-\d+', text)))
        
        # Detail page indicators
        detail_indicators = [
            'Reviewer Details',
            'Referee Details', 
            'Manuscript Details',
            'Submission Date:',
            'Contact Author:'
        ]
        
        # Check for detail indicators
        for indicator in detail_indicators:
            if indicator in text:
                logger.info(f"✅ Detected manuscript detail page (found '{indicator}')")
                return 'detail', ms_ids[0] if ms_ids else None
                
        # If only one manuscript ID appears many times, likely detail page
        if len(ms_ids) == 1:
            count = text.count(ms_ids[0])
            if count > 3:
                logger.info(f"✅ Detected manuscript detail page ({ms_ids[0]} appears {count} times)")
                return 'detail', ms_ids[0]
                
        # Otherwise it's a list page
        logger.info(f"📋 Detected list page with {len(ms_ids)} manuscripts")
        return 'list', ms_ids
        
    def click_status_and_handle_navigation(self, status_text, flagged_emails):
        """Click status and handle whatever page we land on"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🎯 Processing status: '{status_text}'")
        logger.info(f"{'='*60}")
        
        manuscripts_found = []
        
        try:
            # Find and click the status link
            status_link = self.driver.find_element(By.LINK_TEXT, status_text)
            self.driver.execute_script("arguments[0].scrollIntoView(true);", status_link)
            time.sleep(0.5)
            
            # Get the count if visible
            row = status_link.find_element(By.XPATH, "..")
            count_text = row.text
            match = re.search(r'\b(\d+)\b', count_text)
            expected_count = int(match.group(1)) if match else 0
            logger.info(f"Expected manuscripts: {expected_count}")
            
            self.take_screenshot(f"before_clicking_{status_text}")
            status_link.click()
            time.sleep(3)
            self.take_screenshot(f"after_clicking_{status_text}")
            
            # Detect what type of page we landed on
            page_type, data = self.detect_page_type()
            
            if page_type == 'detail':
                # We're on a manuscript detail page
                logger.info(f"Landed directly on manuscript detail page")
                self.save_html(f"direct_detail_{data}")
                
                # Parse this manuscript
                details = self.journal.parse_manuscript_panel(
                    self.driver.page_source,
                    flagged_emails=flagged_emails
                )
                
                # Filter referees
                if 'Referees' in details:
                    active_referees = []
                    for ref in details['Referees']:
                        status = ref.get('Status', '').lower()
                        if 'unavailable' in status or 'declined' in status:
                            logger.info(f"  Skipping {ref.get('Referee Name')} - {ref.get('Status')}")
                            continue
                        active_referees.append(ref)
                    details['Referees'] = active_referees
                    
                manuscripts_found.append(details)
                logger.info(f"✅ Parsed {data}: {len(details.get('Referees', []))} active referees")
                
                # If we expect more manuscripts, look for navigation
                if expected_count > 1:
                    logger.info(f"Looking for other {expected_count - 1} manuscripts...")
                    
                    # Try "Next" button
                    try:
                        next_btn = self.driver.find_element(By.LINK_TEXT, "Next")
                        logger.info("Found 'Next' button")
                        next_btn.click()
                        time.sleep(3)
                        
                        # Parse the next manuscript
                        page_type2, data2 = self.detect_page_type()
                        if page_type2 == 'detail':
                            details2 = self.journal.parse_manuscript_panel(
                                self.driver.page_source,
                                flagged_emails=flagged_emails
                            )
                            
                            # Filter referees
                            if 'Referees' in details2:
                                active_referees = []
                                for ref in details2['Referees']:
                                    status = ref.get('Status', '').lower()
                                    if 'unavailable' in status or 'declined' in status:
                                        continue
                                    active_referees.append(ref)
                                details2['Referees'] = active_referees
                                
                            manuscripts_found.append(details2)
                            logger.info(f"✅ Parsed second manuscript: {len(details2.get('Referees', []))} active referees")
                    except:
                        logger.info("No 'Next' button found")
                        
            else:  # list page
                # We're on a list page with multiple manuscripts
                logger.info(f"On list page with manuscripts: {data}")
                self.save_html(f"{status_text.replace(' ', '_')}_list")
                
                # For list pages, we need to click on each manuscript
                # But ScholarOne doesn't have direct links - this is the issue
                logger.warning("List page navigation not fully implemented - ScholarOne uses complex JavaScript")
                
        except Exception as e:
            logger.error(f"Error processing status '{status_text}': {e}")
            self.take_screenshot("error_status")
            
        return manuscripts_found
        
    def scrape_mf(self):
        """Scrape MF manuscripts"""
        logger.info("🔍 Starting MF scrape")
        
        # Login
        self.journal = MFJournal(self.driver, debug=True)
        self.journal.login()
        self.take_screenshot("after_login")
        
        # Navigate to AE Center
        try:
            ae_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            time.sleep(3)
            self.take_screenshot("ae_center")
        except:
            # Handle confirmation
            try:
                confirm_btn = self.driver.find_element(By.CLASS_NAME, "button-ok")
                confirm_btn.click()
                time.sleep(2)
            except:
                pass
                
            # Try again
            ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
            ae_link.click()
            time.sleep(3)
            self.take_screenshot("ae_center_retry")
            
        # Get flagged emails
        flagged_emails = fetch_starred_emails("MF")
        logger.info(f"Found {len(flagged_emails)} flagged emails")
        
        # Process each status
        statuses = [
            "Awaiting Reviewer Scores",
            "Overdue Manuscripts Awaiting Revision"
        ]
        
        for status in statuses:
            found = self.click_status_and_handle_navigation(status, flagged_emails)
            self.manuscripts.extend(found)
            
            # Go back to AE Center
            logger.info("🔙 Going back to AE Center")
            try:
                ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
                ae_link.click()
                time.sleep(2)
            except:
                logger.error("Could not go back to AE Center")
                
    def run(self):
        """Run the scraper"""
        self.create_driver()
        
        try:
            self.scrape_mf()
            self.print_results()
            self.save_results()
        finally:
            self.driver.quit()
            
    def print_results(self):
        """Print results"""
        logger.info("\n" + "=" * 70)
        logger.info("📊 MF RESULTS")
        logger.info("=" * 70)
        
        total_referees = 0
        
        for i, ms in enumerate(self.manuscripts, 1):
            ms_id = ms.get('Manuscript #', 'Unknown')
            title = ms.get('Title', 'No title')[:60] + "..." if len(ms.get('Title', '')) > 60 else ms.get('Title', 'No title')
            referees = ms.get('Referees', [])
            
            logger.info(f"\n📄 Manuscript {i}: {ms_id}")
            logger.info(f"   Title: {title}")
            logger.info(f"   Author: {ms.get('Contact Author', 'Unknown')}")
            logger.info(f"   Submission Date: {ms.get('Submission Date', 'Unknown')}")
            logger.info(f"   Active Referees ({len(referees)}):")
            
            for ref in referees:
                logger.info(f"     • {ref.get('Referee Name')} - {ref.get('Status')}")
                
            total_referees += len(referees)
            
        logger.info(f"\n📊 SUMMARY:")
        logger.info(f"   Total manuscripts found: {len(self.manuscripts)}")
        logger.info(f"   Total active referees: {total_referees}")
        logger.info(f"   Expected: 2 manuscripts with 4 referees total (excluding unavailable)")
        
    def save_results(self):
        """Save results"""
        output_file = self.debug_dir / "results.json"
        
        with open(output_file, 'w') as f:
            json.dump({
                'journal': 'MF',
                'timestamp': datetime.now().isoformat(),
                'total_manuscripts': len(self.manuscripts),
                'total_referees': sum(len(ms.get('Referees', [])) for ms in self.manuscripts),
                'manuscripts': self.manuscripts
            }, f, indent=2)
            
        logger.info(f"\n💾 Results saved to: {output_file}")


if __name__ == "__main__":
    scraper = DirectNavScraper()
    scraper.run()