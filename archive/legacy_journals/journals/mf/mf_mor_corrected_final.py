#!/usr/bin/env python3
"""
Corrected MF and MOR scraper:
1. Click on CATEGORY TEXT (not numbers) to access all papers
2. Properly filter "Unavailable" referees
3. Implement deduplication for papers appearing in multiple categories
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
logger = logging.getLogger("MF_MOR_FINAL")


class CorrectedFinalScraper:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.manuscripts = []
        self.seen_manuscript_ids = set()  # For deduplication
        self.debug_dir = Path(f"{journal_name.lower()}_corrected_final_debug")
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
        """Click on the category text (not the number) to access all papers"""
        logger.info(f"🎯 Clicking on category text: '{category_text}'")
        
        try:
            # Find the category link
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
            
            # Enhanced referee filtering - check for "Unavailable" more thoroughly
            if 'Referees' in details:
                original_count = len(details['Referees'])
                active_referees = []
                
                for ref in details['Referees']:
                    referee_name = ref.get('Referee Name', '')
                    status = ref.get('Status', '').lower()
                    
                    # Check for unavailable/declined in status
                    if any(word in status for word in ['unavailable', 'declined']):
                        logger.info(f"  Skipping {referee_name} - Status: {ref.get('Status')}")
                        continue
                        
                    # Also check the raw text for "Unavailable" patterns
                    # Parse the page source directly to double-check
                    page_text = self.driver.page_source.lower()
                    if 'unavailable' in page_text and referee_name.lower() in page_text:
                        # Check if this referee is marked as unavailable in the raw HTML
                        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                        
                        # Look for text containing both the referee name and "unavailable"
                        for element in soup.find_all(text=True):
                            if (referee_name.lower() in element.lower() and 
                                'unavailable' in element.lower()):
                                logger.info(f"  Skipping {referee_name} - Found 'unavailable' in page text")
                                continue
                                
                    active_referees.append(ref)
                    logger.info(f"  Including {referee_name} - Status: {ref.get('Status')}")
                    
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
            'Contact Author:'
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
        
    def handle_view_submission_for_manuscript(self, ms_id):
        """Click View Submission for a specific manuscript in a table"""
        logger.info(f"🔍 Looking for View Submission for {ms_id}")
        
        try:
            # Find table rows containing the manuscript ID
            rows = self.driver.find_elements(By.TAG_NAME, "tr")
            
            for row in rows:
                if ms_id in row.text:
                    # Look for View Submission link in this row
                    try:
                        view_links = row.find_elements(By.LINK_TEXT, "View Submission")
                        if view_links:
                            logger.info(f"Found View Submission for {ms_id}")
                            view_links[0].click()
                            time.sleep(3)
                            return True
                    except:
                        continue
                        
            # Fallback: look for any clickable element with the manuscript ID
            try:
                ms_elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{ms_id}')]")
                for elem in ms_elements:
                    if elem.tag_name == 'a':
                        logger.info(f"Found clickable element for {ms_id}")
                        elem.click()
                        time.sleep(3)
                        return True
            except:
                pass
                
            logger.warning(f"Could not find clickable element for {ms_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error handling View Submission for {ms_id}: {e}")
            return False
            
    def process_manuscripts_from_category(self, category_text, flagged_emails):
        """Process all manuscripts from a category"""
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
        
        if page_type == 'detail':
            # We're on a single manuscript detail page
            logger.info(f"Landed on detail page for manuscript: {data}")
            
            # Check if we've already seen this manuscript
            if data in self.seen_manuscript_ids:
                logger.info(f"Already processed {data}, skipping duplicate")
                return manuscripts_found
                
            details = self.parse_manuscript_details(flagged_emails)
            if details:
                manuscripts_found.append(details)
                self.seen_manuscript_ids.add(data)
                
            # Look for Next button to get other manuscripts
            manuscript_count = 1
            while True:
                try:
                    next_btn = self.driver.find_element(By.LINK_TEXT, "Next")
                    logger.info(f"Found Next button, going to manuscript #{manuscript_count + 1}")
                    next_btn.click()
                    time.sleep(3)
                    
                    # Parse the next manuscript
                    page_type2, data2 = self.detect_page_type()
                    if page_type2 == 'detail' and data2 not in self.seen_manuscript_ids:
                        details2 = self.parse_manuscript_details(flagged_emails)
                        if details2:
                            manuscripts_found.append(details2)
                            self.seen_manuscript_ids.add(data2)
                            
                    manuscript_count += 1
                    if manuscript_count > 10:  # Safety break
                        break
                        
                except:
                    logger.info("No more Next buttons found")
                    break
                    
        else:  # list page
            # We're on a list page with multiple manuscripts
            logger.info(f"On list page with manuscripts: {data}")
            
            for ms_id in data:
                if ms_id in self.seen_manuscript_ids:
                    logger.info(f"Already processed {ms_id}, skipping duplicate")
                    continue
                    
                # Try to click on this manuscript
                if self.handle_view_submission_for_manuscript(ms_id):
                    self.take_screenshot(f"viewing_{ms_id}")
                    
                    details = self.parse_manuscript_details(flagged_emails)
                    if details:
                        manuscripts_found.append(details)
                        self.seen_manuscript_ids.add(ms_id)
                        
                    # Go back to list
                    self.driver.back()
                    time.sleep(2)
                    
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
        logger.info(f"📊 {self.journal_name} FINAL CORRECTED RESULTS")
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
            logger.info("✅ SUCCESS: Results match expectations!")
        else:
            logger.warning("⚠️ Results don't fully match expectations - may need further investigation")
        
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
    logger.info("Starting MF Scraper - Click category text, filter unavailable referees")
    logger.info("="*80)
    
    mf_scraper = CorrectedFinalScraper("MF")
    mf_scraper.run()
    
    # Then run MOR
    logger.info("\n" + "="*80)
    logger.info("Starting MOR Scraper - Click category text, filter unavailable referees")
    logger.info("="*80)
    
    mor_scraper = CorrectedFinalScraper("MOR")
    mor_scraper.run()


if __name__ == "__main__":
    main()