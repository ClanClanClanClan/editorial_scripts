#!/usr/bin/env python3
"""
Deep debugging for MOR journal to find 3 manuscripts with 5 referees.
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

from journals.mor import MORJournal
from core.email_utils import fetch_starred_emails

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MOR_DEBUG")


class MORDebugger:
    def __init__(self):
        self.driver = None
        self.journal = None
        self.manuscripts = []
        self.debug_dir = Path("mor_debug_output")
        self.debug_dir.mkdir(exist_ok=True)
        
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
            
    def save_debug(self, name):
        """Save debug information"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save HTML
        html_path = self.debug_dir / f"{name}_{timestamp}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
            
        # Save screenshot
        screenshot_path = self.debug_dir / f"{name}_{timestamp}.png"
        self.driver.save_screenshot(str(screenshot_path))
        
        logger.info(f"📸 Saved debug: {name}")
        
        return html_path
        
    def find_and_click_ae_center(self):
        """Find and click Associate Editor Center with multiple strategies"""
        logger.info("🔍 Looking for Associate Editor Center...")
        
        # Strategy 1: Direct link text
        try:
            ae_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            logger.info("✅ Found AE Center via link text")
            return True
        except:
            pass
            
        # Strategy 2: Partial link text variations
        variations = [
            "Associate Editor",
            "Editor Center",
            "AE Center",
            "Assignment Center"
        ]
        
        for variation in variations:
            try:
                ae_link = self.driver.find_element(By.PARTIAL_LINK_TEXT, variation)
                ae_link.click()
                logger.info(f"✅ Found AE Center via '{variation}'")
                return True
            except:
                continue
                
        # Strategy 3: Search all links
        links = self.driver.find_elements(By.TAG_NAME, 'a')
        logger.info(f"Searching through {len(links)} links...")
        
        for link in links:
            try:
                text = link.text.strip().lower()
                if any(phrase in text for phrase in ['associate', 'editor', 'ae center']):
                    logger.info(f"Found potential link: '{link.text}'")
                    link.click()
                    time.sleep(2)
                    
                    # Check if we're in AE center
                    if "associate editor" in self.driver.page_source.lower():
                        logger.info("✅ Successfully navigated to AE Center")
                        return True
                    else:
                        # Go back if wrong page
                        self.driver.back()
            except:
                continue
                
        return False
        
    def find_manuscripts_in_status(self, status_text, expected_count):
        """Find manuscripts in a specific status category"""
        logger.info(f"📋 Looking for manuscripts in '{status_text}'")
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Find the status in the page
        for row in soup.find_all('tr'):
            if status_text in row.get_text():
                # Look for count in this row
                cells = row.find_all('td')
                for i, cell in enumerate(cells):
                    cell_text = cell.get_text(strip=True)
                    if cell_text.isdigit():
                        count = int(cell_text)
                        logger.info(f"Found {count} manuscripts (expected {expected_count})")
                        
                        # Try to click the count
                        try:
                            # Find in Selenium
                            count_elem = self.driver.find_element(By.XPATH, f"//td[text()='{count}']")
                            count_elem.click()
                            time.sleep(3)
                            
                            self.save_debug(f"{status_text.replace(' ', '_')}_clicked")
                            return True
                        except:
                            # Try clicking the cell with link
                            try:
                                link_elem = self.driver.find_element(
                                    By.XPATH, 
                                    f"//td[contains(text(), '{status_text}')]/preceding-sibling::td//a"
                                )
                                link_elem.click()
                                time.sleep(3)
                                
                                self.save_debug(f"{status_text.replace(' ', '_')}_link_clicked")
                                return True
                            except Exception as e:
                                logger.error(f"Failed to click count: {e}")
                                
        return False
        
    def parse_manuscripts_on_page(self, flagged_emails):
        """Parse manuscripts from current page"""
        logger.info("📄 Parsing manuscripts on current page...")
        
        manuscripts_found = []
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Look for MOR manuscript IDs
        mor_pattern = re.compile(r'MOR-\d{4}-\d+')
        
        # If we're on a list page, find all manuscript IDs
        ms_ids = list(set(mor_pattern.findall(soup.get_text())))
        
        if ms_ids:
            logger.info(f"Found manuscript IDs: {ms_ids}")
            
            # Check if we're on a detail page (only one ID repeated many times)
            if len(ms_ids) == 1:
                # We're on a detail page, parse it
                try:
                    details = self.journal.parse_manuscript_panel(
                        self.driver.page_source,
                        flagged_emails=flagged_emails
                    )
                    manuscripts_found.append(details)
                    logger.info(f"✅ Parsed details for {ms_ids[0]}")
                except Exception as e:
                    logger.error(f"Error parsing details: {e}")
                    
                # Try to find navigation to other manuscripts
                # Look for "Next" or manuscript navigation
                try:
                    next_link = self.driver.find_element(By.PARTIAL_LINK_TEXT, "Next")
                    next_link.click()
                    time.sleep(2)
                    
                    # Parse next manuscript
                    next_details = self.journal.parse_manuscript_panel(
                        self.driver.page_source,
                        flagged_emails=flagged_emails
                    )
                    manuscripts_found.append(next_details)
                except:
                    logger.info("No 'Next' link found")
                    
            else:
                # We're on a list page, click each manuscript
                for ms_id in ms_ids:
                    try:
                        # Click on manuscript
                        ms_link = self.driver.find_element(By.PARTIAL_LINK_TEXT, ms_id)
                        ms_link.click()
                        time.sleep(2)
                        
                        # Parse details
                        details = self.journal.parse_manuscript_panel(
                            self.driver.page_source,
                            flagged_emails=flagged_emails
                        )
                        manuscripts_found.append(details)
                        
                        # Go back
                        self.driver.back()
                        time.sleep(2)
                    except Exception as e:
                        logger.error(f"Error accessing {ms_id}: {e}")
                        
        return manuscripts_found
        
    def run(self):
        """Main debugging process"""
        logger.info("🚀 Starting MOR Deep Debug")
        
        # Load credentials
        env_file = Path(".env")
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
                        
        # Create driver and login
        self.create_driver()
        self.journal = MORJournal(self.driver, debug=True)
        
        try:
            # Login
            logger.info("🔐 Logging in to MOR...")
            self.journal.login()
            
            self.save_debug("after_login")
            
            # Navigate to AE Center
            if not self.find_and_click_ae_center():
                logger.error("❌ Could not find Associate Editor Center")
                self.save_debug("no_ae_center")
                
                # Try alternative: Look for manuscripts directly
                logger.info("🔍 Attempting direct manuscript search...")
                
                # Search for any MOR manuscript links
                mor_links = self.driver.find_elements(
                    By.XPATH, 
                    "//a[contains(text(), 'MOR-')]"
                )
                
                if mor_links:
                    logger.info(f"Found {len(mor_links)} manuscript links")
                    
                    # Get flagged emails
                    flagged_emails = fetch_starred_emails("MOR")
                    
                    for link in mor_links[:3]:  # Process first 3
                        try:
                            ms_id = link.text.strip()
                            link.click()
                            time.sleep(2)
                            
                            details = self.journal.parse_manuscript_panel(
                                self.driver.page_source,
                                flagged_emails=flagged_emails
                            )
                            self.manuscripts.append(details)
                            
                            self.driver.back()
                            time.sleep(2)
                        except:
                            continue
            else:
                # We're in AE Center
                self.save_debug("ae_center")
                
                # Get flagged emails
                logger.info("📧 Fetching flagged emails...")
                flagged_emails = fetch_starred_emails("MOR")
                
                # Look for different status categories
                status_categories = [
                    ("Awaiting Reviewer Scores", 2),
                    ("Awaiting Reviewer Reports", 1),
                    ("Under Review", 3),
                    ("Overdue Reviewer Response", 1)
                ]
                
                for status, expected in status_categories:
                    if self.find_manuscripts_in_status(status, expected):
                        # Parse manuscripts
                        found = self.parse_manuscripts_on_page(flagged_emails)
                        self.manuscripts.extend(found)
                        
                        # Go back to dashboard
                        self.driver.back()
                        time.sleep(2)
                        
            # Print results
            self.print_results()
            self.save_results()
            
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            self.save_debug("error_state")
            
        finally:
            self.driver.quit()
            
    def print_results(self):
        """Print debugging results"""
        logger.info("\n" + "=" * 70)
        logger.info("📊 MOR DEBUG RESULTS")
        logger.info("=" * 70)
        
        total_referees = 0
        
        for ms in self.manuscripts:
            ms_id = ms.get('Manuscript #', 'Unknown')
            title = ms.get('Title', 'No title')[:50] + "..." if len(ms.get('Title', '')) > 50 else ms.get('Title', 'No title')
            author = ms.get('Contact Author', 'Unknown')
            referees = ms.get('Referees', [])
            
            logger.info(f"\n📄 {ms_id}")
            logger.info(f"   Title: {title}")
            logger.info(f"   Author: {author}")
            logger.info(f"   Referees ({len(referees)}):")
            
            for ref in referees:
                logger.info(f"     • {ref.get('Referee Name', 'Unknown')} - {ref.get('Status', 'Unknown')}")
                
            total_referees += len(referees)
            
        logger.info(f"\n📊 SUMMARY:")
        logger.info(f"   Total manuscripts: {len(self.manuscripts)}")
        logger.info(f"   Total referees: {total_referees}")
        logger.info(f"   Expected: 3 manuscripts with 5 referees")
        
    def save_results(self):
        """Save results to JSON"""
        output_file = Path("mor_debug_results.json")
        
        with open(output_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_manuscripts': len(self.manuscripts),
                'total_referees': sum(len(ms.get('Referees', [])) for ms in self.manuscripts),
                'manuscripts': self.manuscripts
            }, f, indent=2)
            
        logger.info(f"\n💾 Results saved to: {output_file}")


if __name__ == "__main__":
    debugger = MORDebugger()
    debugger.run()