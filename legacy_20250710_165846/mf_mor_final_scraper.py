#!/usr/bin/env python3
"""
Final MF and MOR scraper with correct navigation logic.
Handles ScholarOne's table structure where manuscript IDs are not direct links.
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


class FinalScraper:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.manuscripts = []
        self.debug_dir = Path(f"{journal_name.lower()}_final_debug")
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
        except Exception as e:
            logger.warning(f"Undetected Chrome failed: {e}")
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            chrome_options = Options()
            for arg in options.arguments:
                chrome_options.add_argument(arg)
            self.driver = webdriver.Chrome(options=chrome_options)
            
    def take_screenshot(self, description):
        """Take a screenshot with description"""
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
            
    def click_status_text(self, status_text):
        """Click on the status text link (not the number)"""
        logger.info(f"🎯 Looking for status text: '{status_text}'")
        
        try:
            # Find the link with the exact status text
            status_link = self.driver.find_element(By.LINK_TEXT, status_text)
            
            self.driver.execute_script("arguments[0].scrollIntoView(true);", status_link)
            time.sleep(0.5)
            
            self.take_screenshot(f"before_clicking_{status_text}")
            status_link.click()
            time.sleep(3)
            self.take_screenshot(f"after_clicking_{status_text}")
            
            logger.info(f"✅ Clicked on '{status_text}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to click status text: {e}")
            self.take_screenshot("error_clicking_status")
            return False
            
    def go_back_to_ae_center(self):
        """Navigate back using Associate Editor Center link"""
        logger.info("🔙 Navigating back to Associate Editor Center")
        
        try:
            # Try exact text first
            ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
            ae_link.click()
            time.sleep(2)
            self.take_screenshot("back_at_ae_center")
            return True
        except:
            # Try partial text
            try:
                ae_link = self.driver.find_element(By.PARTIAL_LINK_TEXT, "Associate Editor")
                ae_link.click()
                time.sleep(2)
                self.take_screenshot("back_at_ae_center_partial")
                return True
            except Exception as e:
                logger.error(f"Failed to go back to AE Center: {e}")
                self.take_screenshot("error_going_back")
                return False
                
    def click_view_submission_for_manuscript(self, ms_id):
        """Click the View Submission link for a specific manuscript"""
        logger.info(f"🔍 Looking for View Submission link for {ms_id}")
        
        try:
            # Find the table row containing the manuscript ID
            # First find all cells containing the manuscript ID
            cells = self.driver.find_elements(By.XPATH, f"//td[contains(., '{ms_id}')]")
            
            for cell in cells:
                # Check if this is the right cell (should contain just the ID)
                if ms_id in cell.text:
                    # Find the parent row
                    row = cell.find_element(By.XPATH, "..")
                    
                    # Find the View Submission link in the same row
                    view_links = row.find_elements(By.LINK_TEXT, "View Submission")
                    if view_links:
                        logger.info(f"Found View Submission link for {ms_id}")
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", view_links[0])
                        time.sleep(0.5)
                        view_links[0].click()
                        time.sleep(3)
                        return True
                        
            logger.error(f"Could not find View Submission link for {ms_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error clicking View Submission for {ms_id}: {e}")
            return False
            
    def parse_manuscript_list(self, status_text, flagged_emails):
        """Parse manuscripts from list page after clicking status"""
        logger.info(f"📋 Parsing manuscripts for status: {status_text}")
        
        self.save_html(f"{status_text.replace(' ', '_')}_list")
        
        manuscripts_found = []
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Find manuscript IDs
        if self.journal_name == "MF":
            pattern = re.compile(r'MAFI-\d{4}-\d+')
        else:
            pattern = re.compile(r'MOR-\d{4}-\d+')
            
        ms_ids = list(set(pattern.findall(soup.get_text())))
        
        # Check if we're on a detail page (single manuscript)
        if len(ms_ids) == 1 and soup.get_text().count(ms_ids[0]) > 5:
            logger.info(f"Already on manuscript detail page for {ms_ids[0]}")
            
            # Parse this manuscript
            try:
                details = self.journal.parse_manuscript_panel(
                    self.driver.page_source,
                    flagged_emails=flagged_emails
                )
                
                # Filter out unavailable/declined referees
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
                logger.info(f"✅ Parsed {ms_ids[0]}: {len(details.get('Referees', []))} active referees")
                
                # Check for more manuscripts (Next button)
                try:
                    next_btn = self.driver.find_element(By.LINK_TEXT, "Next")
                    logger.info("Found Next button, clicking to see more manuscripts")
                    next_btn.click()
                    time.sleep(3)
                    
                    # Recursively parse
                    more = self.parse_manuscript_list(status_text, flagged_emails)
                    manuscripts_found.extend(more)
                except:
                    logger.info("No Next button found")
                    
            except Exception as e:
                logger.error(f"Error parsing detail page: {e}")
                
        else:
            # We're on a list page
            logger.info(f"On list page with manuscripts: {ms_ids}")
            
            for ms_id in ms_ids:
                # Click View Submission for this manuscript
                if self.click_view_submission_for_manuscript(ms_id):
                    self.take_screenshot(f"viewing_{ms_id}")
                    
                    # Parse details
                    try:
                        details = self.journal.parse_manuscript_panel(
                            self.driver.page_source,
                            flagged_emails=flagged_emails
                        )
                        
                        # Filter out unavailable/declined referees
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
                        logger.info(f"✅ Parsed {ms_id}: {len(details.get('Referees', []))} active referees")
                        
                        # Go back to list
                        self.driver.back()
                        time.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"Error parsing {ms_id}: {e}")
                        self.driver.back()
                        time.sleep(2)
                        
        return manuscripts_found
        
    def scrape_journal(self):
        """Scrape manuscripts for the journal"""
        logger.info(f"🔍 Scraping {self.journal_name}")
        
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
            # Handle confirmation page
            self.take_screenshot("looking_for_ae")
            
            try:
                confirm_btn = self.driver.find_element(By.CLASS_NAME, "button-ok")
                confirm_btn.click()
                time.sleep(2)
                self.take_screenshot("after_confirm")
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
                self.take_screenshot("no_ae_center")
                return
                
        # Get flagged emails
        flagged_emails = fetch_starred_emails(self.journal_name)
        logger.info(f"Found {len(flagged_emails)} flagged emails")
        
        # Process different status categories
        if self.journal_name == "MF":
            statuses = [
                "Awaiting Reviewer Scores",
                "Awaiting Reviewer Reports",  # Try this too
                "Overdue Manuscripts Awaiting Revision"
            ]
        else:
            statuses = [
                "Awaiting Reviewer Reports",
                "Awaiting Reviewer Scores",
                "Under Review"
            ]
            
        for status in statuses:
            if self.click_status_text(status):
                # Parse manuscripts in this status
                found = self.parse_manuscript_list(status, flagged_emails)
                self.manuscripts.extend(found)
                
                # Go back to AE Center for next status
                self.go_back_to_ae_center()
            else:
                logger.warning(f"Status '{status}' not found, skipping")
                
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
        """Print results"""
        logger.info("\n" + "=" * 70)
        logger.info(f"📊 {self.journal_name} RESULTS")
        logger.info("=" * 70)
        
        total_referees = 0
        
        for ms in self.manuscripts:
            ms_id = ms.get('Manuscript #', 'Unknown')
            title = ms.get('Title', 'No title')[:50] + "..." if len(ms.get('Title', '')) > 50 else ms.get('Title', 'No title')
            referees = ms.get('Referees', [])
            
            logger.info(f"\n📄 {ms_id}")
            logger.info(f"   Title: {title}")
            logger.info(f"   Author: {ms.get('Contact Author', 'Unknown')}")
            logger.info(f"   Active Referees ({len(referees)}):")
            
            for ref in referees:
                logger.info(f"     • {ref.get('Referee Name')} - {ref.get('Status')}")
                
            total_referees += len(referees)
            
        logger.info(f"\n📊 SUMMARY:")
        logger.info(f"   Total manuscripts: {len(self.manuscripts)}")
        logger.info(f"   Total active referees: {total_referees}")
        
        if self.journal_name == "MF":
            logger.info(f"   Expected: 2 manuscripts with 4 referees total (excluding unavailable)")
        else:
            logger.info(f"   Expected: 3 manuscripts with 5 referees total")
            
    def save_results(self):
        """Save results"""
        output_file = self.debug_dir / "results.json"
        
        with open(output_file, 'w') as f:
            json.dump({
                'journal': self.journal_name,
                'timestamp': datetime.now().isoformat(),
                'total_manuscripts': len(self.manuscripts),
                'total_referees': sum(len(ms.get('Referees', [])) for ms in self.manuscripts),
                'manuscripts': self.manuscripts
            }, f, indent=2)
            
        logger.info(f"\n💾 Results saved to: {output_file}")


def main():
    # Run MF first
    logger.info("\n" + "="*70)
    logger.info("Starting MF Scraper")
    logger.info("="*70)
    
    mf_scraper = FinalScraper("MF")
    mf_scraper.run()
    
    # Then run MOR
    logger.info("\n" + "="*70)
    logger.info("Starting MOR Scraper")
    logger.info("="*70)
    
    mor_scraper = FinalScraper("MOR")
    mor_scraper.run()


if __name__ == "__main__":
    main()