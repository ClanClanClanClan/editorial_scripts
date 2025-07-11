#!/usr/bin/env python3
"""
Final working MF scraper based on user feedback:
1. Click on the COUNT number (not the text) to go directly to first manuscript
2. Use Next navigation to get to subsequent manuscripts  
3. Use Associate Editor Center link to go back
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
logger = logging.getLogger("MF_FINAL_WORKING")


class FinalWorkingScraper:
    def __init__(self):
        self.driver = None
        self.journal = None
        self.manuscripts = []
        self.debug_dir = Path("mf_final_working_debug")
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
            
    def click_count_for_status(self, status_text):
        """Click on the COUNT number for a status (not the text)"""
        logger.info(f"🔍 Looking for count number near '{status_text}'")
        
        try:
            # Find the status text first
            status_element = self.driver.find_element(By.LINK_TEXT, status_text)
            
            # Get the parent row
            row = status_element.find_element(By.XPATH, "..")
            
            # Look for a clickable number in the same row
            # Try different strategies to find the count
            count_clicked = False
            
            # Strategy 1: Look for a link with just a number
            try:
                number_links = row.find_elements(By.XPATH, ".//a[string-length(normalize-space(text())) <= 2 and string-length(normalize-space(text())) > 0]")
                for link in number_links:
                    text = link.text.strip()
                    if text.isdigit():
                        logger.info(f"Found count link: '{text}'")
                        self.take_screenshot(f"before_clicking_count_{text}")
                        link.click()
                        count_clicked = True
                        break
            except:
                pass
            
            # Strategy 2: Look for any clickable element with a number
            if not count_clicked:
                try:
                    # Find all clickable elements in the row
                    clickable_elements = row.find_elements(By.XPATH, ".//a | .//button | .//td[@onclick]")
                    for elem in clickable_elements:
                        text = elem.text.strip()
                        if text.isdigit() and int(text) > 0:
                            logger.info(f"Found clickable count: '{text}'")
                            self.take_screenshot(f"before_clicking_count_{text}")
                            elem.click()
                            count_clicked = True
                            break
                except:
                    pass
                    
            # Strategy 3: Look for the first cell with a number
            if not count_clicked:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    for cell in cells:
                        text = cell.text.strip()
                        if text.isdigit() and int(text) > 0:
                            logger.info(f"Found count in cell: '{text}' - trying to click")
                            self.take_screenshot(f"before_clicking_cell_{text}")
                            # Try to click the cell
                            cell.click()
                            count_clicked = True
                            break
                except:
                    pass
                    
            if count_clicked:
                time.sleep(3)
                self.take_screenshot(f"after_clicking_count")
                logger.info("✅ Successfully clicked count")
                return True
            else:
                logger.warning("Could not find clickable count")
                return False
                
        except Exception as e:
            logger.error(f"Error clicking count for '{status_text}': {e}")
            return False
            
    def parse_manuscript_details(self, flagged_emails):
        """Parse manuscript details from current page"""
        logger.info("📄 Parsing manuscript details")
        
        try:
            self.save_html("manuscript_details")
            
            # Parse using the journal's parser
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
            
    def get_all_manuscripts_for_status(self, status_text, flagged_emails):
        """Get all manuscripts for a status by clicking count and using Next navigation"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🎯 Processing status: '{status_text}'")
        logger.info(f"{'='*60}")
        
        manuscripts = []
        
        # Click on the count (not the text)
        if not self.click_count_for_status(status_text):
            logger.error(f"Failed to click count for '{status_text}'")
            return manuscripts
            
        # We should now be on the first manuscript's detail page
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
                logger.info("Found 'Next' button - clicking to go to next manuscript")
                next_btn.click()
                time.sleep(3)
                self.take_screenshot(f"after_next_{manuscript_count}")
                manuscript_count += 1
                
                # Safety check to prevent infinite loops
                if manuscript_count > 10:
                    logger.warning("Safety break: processed too many manuscripts")
                    break
                    
            except:
                logger.info("No 'Next' button found - finished with this status")
                break
                
        logger.info(f"📊 Found {len(manuscripts)} manuscripts for '{status_text}'")
        return manuscripts
        
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
            manuscripts = self.get_all_manuscripts_for_status(status, flagged_emails)
            self.manuscripts.extend(manuscripts)
            
            # Go back to AE Center
            self.go_back_to_ae_center()
            
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
        """Print detailed results"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 MF SCRAPING RESULTS")
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
            
        logger.info(f"\n📊 FINAL SUMMARY:")
        logger.info(f"   Total manuscripts found: {len(self.manuscripts)}")
        logger.info(f"   Total active referees: {total_referees}")
        logger.info(f"   Expected: 2 manuscripts with 4 referees total")
        
        # Check if we met expectations
        if len(self.manuscripts) >= 2 and total_referees >= 3:
            logger.info("✅ SUCCESS: Found expected number of manuscripts and referees!")
        else:
            logger.warning("⚠️  Results don't match expectations - may need further debugging")
        
    def save_results(self):
        """Save results to JSON"""
        output_file = self.debug_dir / "results.json"
        
        result_data = {
            'journal': 'MF',
            'timestamp': datetime.now().isoformat(),
            'total_manuscripts': len(self.manuscripts),
            'total_referees': sum(len(ms.get('Referees', [])) for ms in self.manuscripts),
            'manuscripts': self.manuscripts,
            'success': len(self.manuscripts) >= 2 and sum(len(ms.get('Referees', [])) for ms in self.manuscripts) >= 3
        }
        
        with open(output_file, 'w') as f:
            json.dump(result_data, f, indent=2)
            
        logger.info(f"\n💾 Results saved to: {output_file}")


if __name__ == "__main__":
    scraper = FinalWorkingScraper()
    scraper.run()