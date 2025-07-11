#!/usr/bin/env python3
"""
MF and MOR scraper that handles popup windows correctly.
The View Submission links open in new windows/tabs.
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
logger = logging.getLogger("MF_MOR_POPUP")


class PopupScraper:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.manuscripts = []
        self.debug_dir = Path(f"{journal_name.lower()}_popup_debug")
        self.debug_dir.mkdir(exist_ok=True)
        self.screenshot_count = 0
        self.main_window = None
        
    def create_driver(self):
        """Create Chrome driver"""
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        # Allow popups
        prefs = {"profile.default_content_setting_values.notifications": 1}
        options.add_experimental_option("prefs", prefs)
        
        try:
            self.driver = uc.Chrome(options=options)
        except Exception as e:
            logger.warning(f"Undetected Chrome failed: {e}")
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            chrome_options = Options()
            for arg in options.arguments:
                chrome_options.add_argument(arg)
            chrome_options.add_experimental_option("prefs", prefs)
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
        
        # Make sure we're on the main window
        if self.main_window:
            self.driver.switch_to.window(self.main_window)
            
        try:
            ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
            ae_link.click()
            time.sleep(2)
            self.take_screenshot("back_at_ae_center")
            return True
        except:
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
                
    def handle_view_submission_popup(self, ms_id):
        """Handle View Submission that opens in a popup window"""
        logger.info(f"🔍 Handling View Submission popup for {ms_id}")
        
        # Store current window handle
        current_windows = set(self.driver.window_handles)
        
        try:
            # Find the View Submission link for this manuscript
            # Look in the table row containing the manuscript ID
            rows = self.driver.find_elements(By.TAG_NAME, "tr")
            
            for row in rows:
                if ms_id in row.text:
                    # Find View Submission link in this row
                    try:
                        view_link = row.find_element(By.LINK_TEXT, "View Submission")
                        logger.info(f"Found View Submission link for {ms_id}")
                        
                        # Click the link (will open new window)
                        view_link.click()
                        time.sleep(3)
                        
                        # Wait for new window
                        WebDriverWait(self.driver, 10).until(
                            lambda d: len(d.window_handles) > len(current_windows)
                        )
                        
                        # Get new window handle
                        new_windows = set(self.driver.window_handles) - current_windows
                        if new_windows:
                            new_window = new_windows.pop()
                            
                            # Switch to new window
                            self.driver.switch_to.window(new_window)
                            time.sleep(2)
                            
                            self.take_screenshot(f"popup_{ms_id}")
                            self.save_html(f"popup_{ms_id}")
                            
                            # Parse manuscript details
                            return True, new_window
                            
                    except Exception as e:
                        logger.debug(f"No View Submission in this row: {e}")
                        continue
                        
            logger.error(f"Could not find View Submission link for {ms_id}")
            return False, None
            
        except Exception as e:
            logger.error(f"Error handling popup for {ms_id}: {e}")
            return False, None
            
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
                logger.info(f"✅ Parsed {ms_ids[0]}: {len(details.get('Referees', []))} active referees")
                
            except Exception as e:
                logger.error(f"Error parsing detail page: {e}")
                
        else:
            # We're on a list page
            logger.info(f"On list page with manuscripts: {ms_ids}")
            
            for ms_id in ms_ids:
                # Handle popup window
                success, popup_window = self.handle_view_submission_popup(ms_id)
                
                if success:
                    try:
                        # Parse details from popup
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
                        logger.info(f"✅ Parsed {ms_id}: {len(details.get('Referees', []))} active referees")
                        
                        # Close popup and switch back
                        self.driver.close()
                        self.driver.switch_to.window(self.main_window)
                        time.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error parsing {ms_id}: {e}")
                        # Make sure we're back on main window
                        if len(self.driver.window_handles) > 1:
                            self.driver.close()
                        self.driver.switch_to.window(self.main_window)
                        
        return manuscripts_found
        
    def scrape_journal(self):
        """Scrape manuscripts for the journal"""
        logger.info(f"🔍 Scraping {self.journal_name}")
        
        # Store main window handle
        self.main_window = self.driver.current_window_handle
        
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
            # Handle confirmation
            self.take_screenshot("looking_for_ae")
            
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
        
        # Process statuses
        if self.journal_name == "MF":
            statuses = [
                "Awaiting Reviewer Scores",
                "Awaiting Reviewer Reports",
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
                found = self.parse_manuscript_list(status, flagged_emails)
                self.manuscripts.extend(found)
                
                # Go back to AE Center
                self.go_back_to_ae_center()
            else:
                logger.warning(f"Status '{status}' not found")
                
    def run(self):
        """Run the scraper"""
        self.create_driver()
        
        try:
            self.scrape_journal()
            self.print_results()
            self.save_results()
        finally:
            # Close all windows
            for handle in self.driver.window_handles:
                self.driver.switch_to.window(handle)
                self.driver.close()
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
            logger.info(f"   Expected: 2 manuscripts with 4 referees total")
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
    # Run MF
    logger.info("\n" + "="*70)
    logger.info("Starting MF Scraper")
    logger.info("="*70)
    
    mf_scraper = PopupScraper("MF")
    mf_scraper.run()
    
    # Run MOR
    logger.info("\n" + "="*70)
    logger.info("Starting MOR Scraper")
    logger.info("="*70)
    
    mor_scraper = PopupScraper("MOR")
    mor_scraper.run()


if __name__ == "__main__":
    main()