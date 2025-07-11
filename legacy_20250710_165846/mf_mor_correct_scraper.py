#!/usr/bin/env python3
"""
Corrected MF and MOR scraper following the proper navigation:
- Click on status text, not numbers
- Use Associate Editor Center link to navigate back
- Ignore unavailable/declined referees
- Take screenshots for debugging
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


class CorrectScraper:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.manuscripts = []
        self.debug_dir = Path(f"{journal_name.lower()}_correct_debug")
        self.debug_dir.mkdir(exist_ok=True)
        self.screenshot_count = 0
        self.current_status = None
        
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
            status_link = self.driver.find_element(
                By.LINK_TEXT, 
                status_text
            )
            
            self.driver.execute_script("arguments[0].scrollIntoView(true);", status_link)
            time.sleep(0.5)
            
            self.take_screenshot(f"before_clicking_{status_text}")
            status_link.click()
            time.sleep(3)
            self.take_screenshot(f"after_clicking_{status_text}")
            
            self.current_status = status_text  # Track current status
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
                
    def parse_manuscript_list(self, flagged_emails):
        """Parse manuscripts from list page"""
        logger.info("📋 Parsing manuscript list")
        
        manuscripts_on_page = []
        
        # Save HTML for debugging
        self.save_html("manuscript_list")
        
        # Wait for table to load
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
        except:
            logger.warning("No table found, checking page structure")
            
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Check if we're already on a manuscript detail page
        if self.journal_name == "MF":
            pattern = re.compile(r'MAFI-\d{4}-\d+')
        else:
            pattern = re.compile(r'MOR-\d{4}-\d+')
            
        ms_ids = list(set(pattern.findall(soup.get_text())))
        
        # If only one manuscript ID appears many times, we're on detail page
        if len(ms_ids) == 1 and soup.get_text().count(ms_ids[0]) > 5:
            logger.info(f"Already on manuscript detail page for {ms_ids[0]}")
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
                    
                manuscripts_on_page.append(details)
                logger.info(f"✅ Parsed {ms_ids[0]}: {len(details.get('Referees', []))} active referees")
                
                # Look for other manuscripts navigation
                # Try "Next" button
                try:
                    next_btn = self.driver.find_element(By.LINK_TEXT, "Next")
                    next_btn.click()
                    time.sleep(3)
                    self.take_screenshot("after_next")
                    
                    # Recursively parse the next manuscript
                    more_manuscripts = self.parse_manuscript_list(flagged_emails)
                    manuscripts_on_page.extend(more_manuscripts)
                except:
                    logger.info("No more manuscripts to navigate to")
                    
            except Exception as e:
                logger.error(f"Error parsing manuscript detail: {e}")
                
        else:
            # We're on a list page
            logger.info(f"Found manuscript IDs on list page: {ms_ids}")
            
            # Try different strategies to find manuscript links
            for ms_id in ms_ids:
                clicked = False
                
                # Strategy 1: Direct link with manuscript ID
                try:
                    ms_links = self.driver.find_elements(By.PARTIAL_LINK_TEXT, ms_id)
                    if ms_links:
                        logger.info(f"Found {len(ms_links)} links for {ms_id}")
                        self.take_screenshot(f"before_clicking_{ms_id}")
                        ms_links[0].click()
                        clicked = True
                except:
                    pass
                    
                # Strategy 2: Find in table rows
                if not clicked:
                    try:
                        # Find all links containing the manuscript ID
                        links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{ms_id}')]")
                        if links:
                            logger.info(f"Found {len(links)} XPath links for {ms_id}")
                            links[0].click()
                            clicked = True
                    except:
                        pass
                        
                # Strategy 3: JavaScript click
                if not clicked:
                    try:
                        link = self.driver.find_element(By.XPATH, f"//*[contains(text(), '{ms_id}')]")
                        self.driver.execute_script("arguments[0].click();", link)
                        clicked = True
                    except:
                        pass
                        
                if clicked:
                    time.sleep(3)
                    self.take_screenshot(f"viewing_{ms_id}")
                    
                    # Parse details
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
                        
                    manuscripts_on_page.append(details)
                    logger.info(f"✅ Parsed {ms_id}: {len(details.get('Referees', []))} active referees")
                    
                    # Go back to list
                    self.go_back_to_ae_center()
                    
                    # Click back on the status to return to list
                    time.sleep(1)
                    
                    # Re-click the status text to get back to the list
                    status_text = self.current_status  # We'll need to track this
                    if status_text:
                        self.click_status_text(status_text)
                else:
                    logger.error(f"Could not click on {ms_id}")
                    self.take_screenshot(f"error_{ms_id}")
                    
        return manuscripts_on_page
        
    def scrape_mf(self):
        """Scrape MF manuscripts"""
        logger.info("🔍 Scraping MF")
        
        # Login
        self.journal = MFJournal(self.driver, debug=True)
        logger.info("Logging in to MF...")
        self.journal.login()
        self.take_screenshot("mf_after_login")
        
        # Navigate to AE Center
        try:
            ae_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            time.sleep(3)
            self.take_screenshot("mf_ae_center")
        except:
            # Maybe we need to handle a confirmation page first
            self.take_screenshot("mf_looking_for_ae")
            
            # Check for any confirmation buttons
            try:
                confirm_btn = self.driver.find_element(By.CLASS_NAME, "button-ok")
                confirm_btn.click()
                time.sleep(2)
                self.take_screenshot("mf_after_confirm")
            except:
                pass
                
            # Try again
            try:
                ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
                ae_link.click()
                time.sleep(3)
                self.take_screenshot("mf_ae_center_retry")
            except Exception as e:
                logger.error(f"Could not find AE Center: {e}")
                self.take_screenshot("mf_no_ae_center")
                return
        
        # Get emails
        flagged_emails = fetch_starred_emails("MF")
        
        # Process status categories
        statuses = [
            "Awaiting Reviewer Scores",
            "Overdue Manuscripts Awaiting Revision"
        ]
        
        for status in statuses:
            if self.click_status_text(status):
                # Parse manuscripts
                found = self.parse_manuscript_list(flagged_emails)
                self.manuscripts.extend(found)
                
                # Return to AE Center for next status
                self.go_back_to_ae_center()
                
    def scrape_mor(self):
        """Scrape MOR manuscripts with extensive debugging"""
        logger.info("🔍 Scraping MOR")
        
        # Login
        self.journal = MORJournal(self.driver, debug=True)
        logger.info("Logging in to MOR...")
        self.journal.login()
        self.take_screenshot("mor_after_login")
        self.save_html("mor_after_login")
        
        # Try to find AE Center
        logger.info("Looking for Associate Editor Center...")
        
        # Strategy 1: Direct link
        try:
            ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
            self.take_screenshot("mor_found_ae_link")
            ae_link.click()
            time.sleep(3)
            self.take_screenshot("mor_ae_center")
            ae_found = True
        except:
            ae_found = False
            logger.warning("No direct AE Center link found")
            
        # Strategy 2: Look through all links
        if not ae_found:
            self.take_screenshot("mor_no_ae_searching_links")
            links = self.driver.find_elements(By.TAG_NAME, 'a')
            logger.info(f"Found {len(links)} total links")
            
            for i, link in enumerate(links):
                try:
                    text = link.text.strip()
                    href = link.get_attribute('href') or ''
                    
                    if text:
                        logger.debug(f"Link {i}: '{text}'")
                        
                    if any(phrase in text.lower() for phrase in ['editor', 'associate', 'ae']):
                        logger.info(f"Potential link: '{text}'")
                        self.take_screenshot(f"mor_potential_link_{i}")
                        link.click()
                        time.sleep(3)
                        self.take_screenshot(f"mor_after_click_{i}")
                        
                        # Check if we're in AE area
                        if "associate editor" in self.driver.page_source.lower():
                            ae_found = True
                            break
                        else:
                            self.driver.back()
                            time.sleep(1)
                except:
                    continue
                    
        if ae_found:
            # Get emails
            flagged_emails = fetch_starred_emails("MOR")
            
            # Look for status categories
            statuses = [
                "Awaiting Reviewer Scores",
                "Awaiting Reviewer Reports",
                "Under Review"
            ]
            
            for status in statuses:
                if self.click_status_text(status):
                    found = self.parse_manuscript_list(flagged_emails)
                    self.manuscripts.extend(found)
                    self.go_back_to_ae_center()
        else:
            logger.error("Could not access MOR Associate Editor Center")
            self.take_screenshot("mor_final_no_ae")
            
    def run(self):
        """Run the scraper"""
        self.create_driver()
        
        try:
            if self.journal_name == "MF":
                self.scrape_mf()
            else:
                self.scrape_mor()
                
            # Print results
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
            logger.info(f"   Expected: 2 manuscripts with 3 active referees (excluding unavailable)")
        else:
            logger.info(f"   Expected: 3 manuscripts with 5 referees")
            
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
    # First run MF
    logger.info("\n" + "="*70)
    logger.info("Starting MF Scraper")
    logger.info("="*70)
    
    mf_scraper = CorrectScraper("MF")
    mf_scraper.run()
    
    # Then run MOR
    logger.info("\n" + "="*70)
    logger.info("Starting MOR Scraper")
    logger.info("="*70)
    
    mor_scraper = CorrectScraper("MOR")
    mor_scraper.run()


if __name__ == "__main__":
    main()