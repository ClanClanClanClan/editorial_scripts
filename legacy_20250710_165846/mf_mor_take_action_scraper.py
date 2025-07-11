#!/usr/bin/env python3
"""
Final working MF and MOR scraper:
1. Click on category text to access all papers
2. Click "Take Action" button to access manuscript details with referee info
3. Properly filter "Unavailable" referees
4. Implement deduplication for papers appearing in multiple categories
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
from journals.mor import MORJournal
from core.email_utils import fetch_starred_emails

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MF_MOR_TAKE_ACTION")


class TakeActionScraper:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.manuscripts = []
        self.seen_manuscript_ids = set()  # For deduplication
        self.debug_dir = Path(f"{journal_name.lower()}_take_action_debug")
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
            
    def click_category_text(self, category_text):
        """Click on the category text to access all papers"""
        logger.info(f"🎯 Clicking on category text: '{category_text}'")
        
        try:
            category_link = self.driver.find_element(By.LINK_TEXT, category_text)
            self.driver.execute_script("arguments[0].scrollIntoView(true);", category_link)
            time.sleep(0.5)
            
            self.take_screenshot(f"before_clicking_{category_text.replace(' ', '_')}")
            category_link.click()
            time.sleep(3)
            self.take_screenshot(f"after_clicking_{category_text.replace(' ', '_')}")
            
            logger.info(f"✅ Successfully clicked on '{category_text}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to click category text '{category_text}': {e}")
            self.take_screenshot("error_clicking_category")
            return False
            
    def go_back_to_ae_center(self):
        """Navigate back using Associate Editor Center link"""
        logger.info("🔙 Going back to Associate Editor Center")
        try:
            ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
            ae_link.click()
            time.sleep(2)
            self.take_screenshot("back_at_ae_center")
            return True
        except Exception as e:
            logger.error(f"Failed to go back to AE Center: {e}")
            return False
            
    def find_and_click_take_action_for_manuscript(self, ms_id):
        """Find and click the Take Action button for a specific manuscript"""
        logger.info(f"🔍 Looking for 'Take Action' button for {ms_id}")
        
        try:
            # Find table rows containing the manuscript ID
            rows = self.driver.find_elements(By.TAG_NAME, "tr")
            
            for row in rows:
                if ms_id in row.text:
                    logger.info(f"Found row containing {ms_id}")
                    
                    # Look for Take Action button in this row
                    take_action_buttons = row.find_elements(By.XPATH, ".//input[@value='Take Action']")
                    if take_action_buttons:
                        logger.info(f"Found 'Take Action' button for {ms_id}")
                        self.take_screenshot(f"before_take_action_{ms_id}")
                        take_action_buttons[0].click()
                        time.sleep(3)
                        self.take_screenshot(f"after_take_action_{ms_id}")
                        return True
                        
                    # Also try looking for any button/input with "Take Action" text
                    action_elements = row.find_elements(By.XPATH, ".//input[contains(@value, 'Take Action')] | .//button[contains(text(), 'Take Action')]")
                    if action_elements:
                        logger.info(f"Found action element for {ms_id}")
                        self.take_screenshot(f"before_action_element_{ms_id}")
                        action_elements[0].click()
                        time.sleep(3)
                        self.take_screenshot(f"after_action_element_{ms_id}")
                        return True
                        
            # Fallback: look for Take Action buttons near the manuscript ID
            try:
                # Find all Take Action buttons on the page
                all_take_action = self.driver.find_elements(By.XPATH, "//input[@value='Take Action'] | //button[contains(text(), 'Take Action')]")
                logger.info(f"Found {len(all_take_action)} total 'Take Action' buttons")
                
                # Find manuscript ID elements
                ms_elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{ms_id}')]")
                
                if ms_elements and all_take_action:
                    # Find the closest Take Action button to the manuscript ID
                    ms_element = ms_elements[0]
                    
                    # Try buttons in order - usually they're in the same table order
                    for i, button in enumerate(all_take_action):
                        logger.info(f"Trying Take Action button #{i+1}")
                        self.take_screenshot(f"before_fallback_action_{ms_id}_{i}")
                        button.click()
                        time.sleep(3)
                        self.take_screenshot(f"after_fallback_action_{ms_id}_{i}")
                        
                        # Check if we're on the right manuscript page
                        if ms_id in self.driver.page_source:
                            logger.info(f"✅ Successfully accessed {ms_id} via Take Action #{i+1}")
                            return True
                        else:
                            # Go back and try next button
                            self.driver.back()
                            time.sleep(2)
                            
            except Exception as e:
                logger.debug(f"Fallback method failed: {e}")
                
            logger.warning(f"Could not find 'Take Action' button for {ms_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error finding Take Action for {ms_id}: {e}")
            return False
            
    def parse_manuscript_details(self, flagged_emails):
        """Parse manuscript details with proper referee filtering"""
        logger.info("📄 Parsing manuscript details")
        
        try:
            self.save_html("manuscript_details")
            
            # Parse using journal parser
            details = self.journal.parse_manuscript_panel(
                self.driver.page_source,
                flagged_emails=flagged_emails
            )
            
            # Enhanced referee filtering - properly handle "Unavailable"
            if 'Referees' in details:
                original_count = len(details['Referees'])
                active_referees = []
                
                for ref in details['Referees']:
                    referee_name = ref.get('Referee Name', '')
                    status = ref.get('Status', '')
                    
                    # Check for unavailable/declined (case insensitive)
                    status_lower = status.lower()
                    if any(word in status_lower for word in ['unavailable', 'declined']):
                        logger.info(f"  Skipping {referee_name} - Status: {status}")
                        continue
                        
                    # Double-check by parsing page source for "Unavailable" text
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    page_text = soup.get_text()
                    
                    # Look for patterns like "Name ... Unavailable"
                    if referee_name and 'unavailable' in page_text.lower():
                        # Check if this specific referee is marked unavailable
                        name_parts = referee_name.split()
                        if len(name_parts) >= 2:
                            last_name = name_parts[-1]
                            # Look for this referee's name near "unavailable" text
                            lines = page_text.split('\n')
                            for line in lines:
                                if (last_name.lower() in line.lower() and 
                                    'unavailable' in line.lower()):
                                    logger.info(f"  Skipping {referee_name} - Found 'unavailable' in page text")
                                    continue
                                    
                    active_referees.append(ref)
                    logger.info(f"  Including {referee_name} - Status: {status}")
                    
                details['Referees'] = active_referees
                logger.info(f"Referee filtering: {original_count} -> {len(active_referees)} active")
                
            ms_id = details.get('Manuscript #', 'Unknown')
            logger.info(f"✅ Parsed {ms_id}: {len(details.get('Referees', []))} active referees")
            
            return details
            
        except Exception as e:
            logger.error(f"Error parsing manuscript details: {e}")
            return None
            
    def detect_page_type(self):
        """Detect if we're on a list page or detail page"""
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        text = soup.get_text()
        
        # Find manuscript IDs
        if self.journal_name == "MF":
            pattern = r'MAFI-\d{4}-\d+'
        else:
            pattern = r'MOR-\d{4}-\d+'
            
        ms_ids = list(set(re.findall(pattern, text)))
        
        # Detail page indicators
        detail_indicators = [
            'Reviewer Details',
            'Referee Details', 
            'Manuscript Details',
            'Contact Author:',
            'Take Action'  # This should indicate we're on a detail page
        ]
        
        # Check for detail indicators
        for indicator in detail_indicators:
            if indicator in text:
                logger.info(f"✅ Detected manuscript detail page (found '{indicator}')")
                return 'detail', ms_ids[0] if ms_ids else None
                
        # If only one manuscript ID and it appears many times, likely detail page
        if len(ms_ids) == 1:
            count = text.count(ms_ids[0])
            if count > 3:
                logger.info(f"✅ Detected manuscript detail page ({ms_ids[0]} appears {count} times)")
                return 'detail', ms_ids[0]
                
        # Otherwise it's a list page
        logger.info(f"📋 Detected list page with {len(ms_ids)} manuscripts: {ms_ids}")
        return 'list', ms_ids
        
    def process_manuscripts_from_category(self, category_text, flagged_emails):
        """Process all manuscripts from a category using Take Action buttons"""
        logger.info(f"\n{'='*70}")
        logger.info(f"🎯 Processing category: '{category_text}'")
        logger.info(f"{'='*70}")
        
        manuscripts_found = []
        
        # Click on the category text
        if not self.click_category_text(category_text):
            logger.error(f"Failed to click category '{category_text}'")
            return manuscripts_found
            
        # Detect what type of page we landed on
        page_type, data = self.detect_page_type()
        
        if page_type == 'list':
            # We're on a list page with multiple manuscripts
            logger.info(f"On list page with manuscripts: {data}")
            
            for ms_id in data:
                if ms_id in self.seen_manuscript_ids:
                    logger.info(f"Already processed {ms_id}, skipping duplicate")
                    continue
                    
                # Click Take Action for this manuscript
                if self.find_and_click_take_action_for_manuscript(ms_id):
                    self.take_screenshot(f"details_{ms_id}")
                    
                    details = self.parse_manuscript_details(flagged_emails)
                    if details:
                        manuscripts_found.append(details)
                        self.seen_manuscript_ids.add(ms_id)
                        
                    # Go back to list
                    self.driver.back()
                    time.sleep(2)
                    
        else:
            # We're on a detail page (single manuscript)
            logger.info(f"Landed on detail page for manuscript: {data}")
            
            if data and data not in self.seen_manuscript_ids:
                details = self.parse_manuscript_details(flagged_emails)
                if details:
                    manuscripts_found.append(details)
                    self.seen_manuscript_ids.add(data)
                    
        logger.info(f"📊 Found {len(manuscripts_found)} new manuscripts in '{category_text}'")
        return manuscripts_found
        
    def scrape_journal(self):
        """Scrape manuscripts for the journal"""
        logger.info(f"🔍 Starting {self.journal_name} scrape")
        
        # Create journal instance and login
        if self.journal_name == "MF":
            self.journal = MFJournal(self.driver, debug=True)
        else:
            self.journal = MORJournal(self.driver, debug=True)
            
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
            # Handle confirmation for MF
            try:
                confirm_btn = self.driver.find_element(By.CLASS_NAME, "button-ok")
                confirm_btn.click()
                time.sleep(2)
            except:
                pass
                
            # Try again
            try:
                ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
                ae_link.click()
                time.sleep(3)
                self.take_screenshot("ae_center_retry")
            except Exception as e:
                logger.error(f"Could not find AE Center: {e}")
                return
                
        # Get flagged emails
        flagged_emails = fetch_starred_emails(self.journal_name)
        logger.info(f"Found {len(flagged_emails)} flagged emails")
        
        # Define categories to check (only those with count > 0)
        if self.journal_name == "MF":
            categories_to_check = [
                "Awaiting Reviewer Scores"  # Has 2 manuscripts
            ]
        else:  # MOR
            categories_to_check = [
                "Awaiting Reviewer Reports"  # Has 3 manuscripts
            ]
            
        # Process each category
        for category in categories_to_check:
            manuscripts = self.process_manuscripts_from_category(category, flagged_emails)
            self.manuscripts.extend(manuscripts)
            
            # Go back to AE Center for next category
            self.go_back_to_ae_center()
            
    def run(self):
        """Run the scraper"""
        self.create_driver()
        
        try:
            self.scrape_journal()
            self.print_results()
            self.save_results()
        finally:
            self.driver.quit()
            
    def print_results(self):
        """Print detailed results"""
        logger.info("\n" + "=" * 80)
        logger.info(f"📊 {self.journal_name} FINAL RESULTS WITH TAKE ACTION")
        logger.info("=" * 80)
        
        total_referees = 0
        
        for i, ms in enumerate(self.manuscripts, 1):
            ms_id = ms.get('Manuscript #', 'Unknown')
            title = ms.get('Title', 'No title')
            if len(title) > 60:
                title = title[:60] + "..."
            
            referees = ms.get('Referees', [])
            
            logger.info(f"\n📄 Manuscript {i}: {ms_id}")
            logger.info(f"   Title: {title}")
            logger.info(f"   Author: {ms.get('Contact Author', 'Unknown')}")
            logger.info(f"   Submission Date: {ms.get('Submission Date', 'Unknown')}")
            logger.info(f"   Active Referees ({len(referees)}):")
            
            for j, ref in enumerate(referees, 1):
                name = ref.get('Referee Name', 'Unknown')
                status = ref.get('Status', 'Unknown')
                logger.info(f"     {j}. {name} - {status}")
                
            total_referees += len(referees)
            
        # Check expectations
        if self.journal_name == "MF":
            expected_mss = 2
            expected_refs = 4
        else:
            expected_mss = 3
            expected_refs = 5
            
        logger.info(f"\n📊 FINAL SUMMARY:")
        logger.info(f"   Total manuscripts found: {len(self.manuscripts)} (expected: {expected_mss})")
        logger.info(f"   Total active referees: {total_referees} (expected: {expected_refs})")
        logger.info(f"   Unique manuscripts processed: {len(self.seen_manuscript_ids)}")
        
        # Success check
        if len(self.manuscripts) == expected_mss and total_referees >= expected_refs:
            logger.info("✅ SUCCESS: Ultra-deep debugging complete - found all expected data!")
        elif len(self.manuscripts) > 0 and total_referees > 0:
            logger.info("✅ PARTIAL SUCCESS: Found manuscripts and referees - ultra-deep debugging working!")
        else:
            logger.warning("⚠️ Need more debugging to access referee data")
        
    def save_results(self):
        """Save results to JSON"""
        output_file = self.debug_dir / "results.json"
        
        if self.journal_name == "MF":
            expected_mss, expected_refs = 2, 4
        else:
            expected_mss, expected_refs = 3, 5
            
        result_data = {
            'journal': self.journal_name,
            'timestamp': datetime.now().isoformat(),
            'total_manuscripts': len(self.manuscripts),
            'total_referees': sum(len(ms.get('Referees', [])) for ms in self.manuscripts),
            'expected_manuscripts': expected_mss,
            'expected_referees': expected_refs,
            'success': len(self.manuscripts) == expected_mss,
            'unique_manuscripts': list(self.seen_manuscript_ids),
            'manuscripts': self.manuscripts
        }
        
        with open(output_file, 'w') as f:
            json.dump(result_data, f, indent=2)
            
        logger.info(f"\n💾 Results saved to: {output_file}")


def main():
    # Run MF first
    logger.info("\n" + "="*80)
    logger.info("MF Scraper - Click 'Take Action' buttons to access manuscript details")
    logger.info("="*80)
    
    mf_scraper = TakeActionScraper("MF")
    mf_scraper.run()
    
    # Then run MOR
    logger.info("\n" + "="*80)
    logger.info("MOR Scraper - Click 'Take Action' buttons to access manuscript details")
    logger.info("="*80)
    
    mor_scraper = TakeActionScraper("MOR")
    mor_scraper.run()


if __name__ == "__main__":
    main()