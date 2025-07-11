#!/usr/bin/env python3
"""
MF and MOR scraper targeting only the correct categories as specified:

MF - Only "Awaiting Reviewer Scores" (2 manuscripts)
MOR - Only "Awaiting Reviewer Reports" (3 manuscripts)
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
logger = logging.getLogger("MF_MOR_CORRECT")


class CorrectCategoriesScraper:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.manuscripts = []
        self.debug_dir = Path(f"{journal_name.lower()}_correct_categories_debug")
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
            
    def click_count_for_status(self, status_text, expected_count):
        """Click on the count number for a specific status"""
        logger.info(f"🎯 Looking for count '{expected_count}' for '{status_text}'")
        
        try:
            # Find all links with the expected count
            count_links = self.driver.find_elements(By.LINK_TEXT, str(expected_count))
            logger.info(f"Found {len(count_links)} links with text '{expected_count}'")
            
            if not count_links:
                logger.error(f"No links found with count '{expected_count}'")
                return False
                
            # Find the status text element to locate the correct count link
            try:
                status_element = self.driver.find_element(By.LINK_TEXT, status_text)
                status_row = status_element.find_element(By.XPATH, "..")
                
                # Look for the count link in the same row
                count_in_row = None
                for link in count_links:
                    try:
                        link_row = link.find_element(By.XPATH, "..")
                        if status_row == link_row or status_text in link_row.text:
                            count_in_row = link
                            break
                    except:
                        continue
                        
                if count_in_row:
                    logger.info(f"Found correct count link for '{status_text}'")
                    self.take_screenshot(f"before_clicking_count_{expected_count}")
                    count_in_row.click()
                    time.sleep(3)
                    self.take_screenshot(f"after_clicking_count_{expected_count}")
                    logger.info(f"✅ Successfully clicked count '{expected_count}' for '{status_text}'")
                    return True
                else:
                    # Fallback: click the first count link
                    logger.warning(f"Could not find count in same row, trying first '{expected_count}' link")
                    self.take_screenshot(f"before_clicking_fallback_{expected_count}")
                    count_links[0].click()
                    time.sleep(3)
                    self.take_screenshot(f"after_clicking_fallback_{expected_count}")
                    return True
                    
            except:
                # If we can't find the status text, just click the first count link
                logger.warning(f"Could not find status text, clicking first '{expected_count}' link")
                self.take_screenshot(f"before_clicking_first_{expected_count}")
                count_links[0].click()
                time.sleep(3)
                self.take_screenshot(f"after_clicking_first_{expected_count}")
                return True
                
        except Exception as e:
            logger.error(f"Error clicking count for '{status_text}': {e}")
            self.take_screenshot("error_clicking_count")
            return False
            
    def parse_manuscript_details(self, flagged_emails):
        """Parse manuscript details from current page"""
        logger.info("📄 Parsing manuscript details")
        
        try:
            self.save_html("manuscript_details")
            
            details = self.journal.parse_manuscript_panel(
                self.driver.page_source,
                flagged_emails=flagged_emails
            )
            
            # Filter out unavailable/declined referees
            if 'Referees' in details:
                original_count = len(details['Referees'])
                active_referees = []
                for ref in details['Referees']:
                    status = ref.get('Status', '').lower()
                    if 'unavailable' in status or 'declined' in status:
                        logger.info(f"  Skipping {ref.get('Referee Name')} - {ref.get('Status')}")
                        continue
                    active_referees.append(ref)
                details['Referees'] = active_referees
                
                logger.info(f"Filtered referees: {original_count} -> {len(active_referees)}")
                
            ms_id = details.get('Manuscript #', 'Unknown')
            logger.info(f"✅ Parsed {ms_id}: {len(details.get('Referees', []))} active referees")
            
            return details
            
        except Exception as e:
            logger.error(f"Error parsing manuscript details: {e}")
            return None
            
    def get_all_manuscripts_for_category(self, status_text, expected_count, flagged_emails):
        """Get all manuscripts for a category by clicking count and using Next navigation"""
        logger.info(f"\n{'='*70}")
        logger.info(f"🎯 Processing: '{status_text}' (expecting {expected_count} manuscripts)")
        logger.info(f"{'='*70}")
        
        manuscripts = []
        
        # Click on the count
        if not self.click_count_for_status(status_text, expected_count):
            logger.error(f"Failed to click count for '{status_text}'")
            return manuscripts
            
        # Process manuscripts
        manuscript_count = 1
        
        while True:
            logger.info(f"📄 Processing manuscript #{manuscript_count}")
            
            # Parse current manuscript
            details = self.parse_manuscript_details(flagged_emails)
            if details:
                manuscripts.append(details)
            
            # Look for Next button
            try:
                next_btn = self.driver.find_element(By.LINK_TEXT, "Next")
                logger.info("Found 'Next' button - going to next manuscript")
                next_btn.click()
                time.sleep(3)
                self.take_screenshot(f"after_next_{manuscript_count}")
                manuscript_count += 1
                
                # Safety check
                if manuscript_count > expected_count + 2:
                    logger.warning("Safety break: too many manuscripts")
                    break
                    
            except:
                logger.info("No 'Next' button found - finished with this category")
                break
                
        logger.info(f"📊 Found {len(manuscripts)} manuscripts for '{status_text}' (expected {expected_count})")
        
        if len(manuscripts) != expected_count:
            logger.warning(f"⚠️ Count mismatch! Found {len(manuscripts)}, expected {expected_count}")
        else:
            logger.info(f"✅ Count matches expectation!")
            
        return manuscripts
        
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
        
        # Process the correct category for each journal
        if self.journal_name == "MF":
            # Only "Awaiting Reviewer Scores" with 2 manuscripts
            manuscripts = self.get_all_manuscripts_for_category(
                "Awaiting Reviewer Scores", 2, flagged_emails
            )
            self.manuscripts.extend(manuscripts)
            
        else:  # MOR
            # Only "Awaiting Reviewer Reports" with 3 manuscripts
            manuscripts = self.get_all_manuscripts_for_category(
                "Awaiting Reviewer Reports", 3, flagged_emails
            )
            self.manuscripts.extend(manuscripts)
            
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
        logger.info(f"📊 {self.journal_name} FINAL RESULTS")
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
        
        # Success check
        if len(self.manuscripts) == expected_mss and total_referees >= expected_refs:
            logger.info("✅ SUCCESS: Results match expectations!")
        else:
            logger.warning("⚠️ Results don't fully match expectations")
        
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
            'manuscripts': self.manuscripts
        }
        
        with open(output_file, 'w') as f:
            json.dump(result_data, f, indent=2)
            
        logger.info(f"\n💾 Results saved to: {output_file}")


def main():
    # Run MF first
    logger.info("\n" + "="*80)
    logger.info("Starting MF Scraper - Only 'Awaiting Reviewer Scores' (2 manuscripts)")
    logger.info("="*80)
    
    mf_scraper = CorrectCategoriesScraper("MF")
    mf_scraper.run()
    
    # Then run MOR
    logger.info("\n" + "="*80)
    logger.info("Starting MOR Scraper - Only 'Awaiting Reviewer Reports' (3 manuscripts)")
    logger.info("="*80)
    
    mor_scraper = CorrectCategoriesScraper("MOR")
    mor_scraper.run()


if __name__ == "__main__":
    main()