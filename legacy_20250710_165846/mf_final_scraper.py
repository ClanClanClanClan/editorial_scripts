#!/usr/bin/env python3
"""
Final working MF scraper with robust manuscript access.
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
from selenium.common.exceptions import TimeoutException, ElementNotInteractableException
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
logger = logging.getLogger("MF_FINAL")


class MFManuscriptScraper:
    def __init__(self):
        self.driver = None
        self.journal = None
        self.manuscripts = []
        
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
            
    def save_debug_page(self, name):
        """Save current page for debugging"""
        debug_dir = Path("mf_final_debug")
        debug_dir.mkdir(exist_ok=True)
        
        # Save HTML
        with open(debug_dir / f"{name}.html", 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
            
        # Save screenshot
        self.driver.save_screenshot(str(debug_dir / f"{name}.png"))
        
        logger.info(f"📸 Saved debug info: {debug_dir}/{name}")
        
    def click_manuscript_row(self, ms_id):
        """Click on a manuscript row to view details"""
        logger.info(f"🖱️ Attempting to access manuscript {ms_id}")
        
        # Method 1: Try to find any clickable element in the row containing the manuscript ID
        try:
            # Find all elements containing the manuscript ID
            elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{ms_id}')]")
            
            for elem in elements:
                # Check if this element or its parent is clickable
                try:
                    # Try the element itself
                    if elem.is_displayed() and elem.is_enabled():
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                        time.sleep(0.5)
                        elem.click()
                        logger.info(f"✅ Clicked on element containing {ms_id}")
                        return True
                except:
                    pass
                    
                # Try parent elements
                parent = elem.find_element(By.XPATH, "..")
                if parent.tag_name == 'a':
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", parent)
                        time.sleep(0.5)
                        parent.click()
                        logger.info(f"✅ Clicked on parent link of {ms_id}")
                        return True
                    except:
                        pass
                        
            # Method 2: Look for onclick handlers in the row
            row_xpath = f"//tr[contains(., '{ms_id}')]"
            try:
                row = self.driver.find_element(By.XPATH, row_xpath)
                # Check for onclick attribute
                onclick = row.get_attribute('onclick')
                if onclick:
                    self.driver.execute_script(onclick)
                    logger.info(f"✅ Executed onclick for {ms_id} row")
                    return True
                    
                # Check cells in the row
                cells = row.find_elements(By.TAG_NAME, 'td')
                for cell in cells:
                    onclick = cell.get_attribute('onclick')
                    if onclick:
                        self.driver.execute_script(onclick)
                        logger.info(f"✅ Executed onclick for {ms_id} cell")
                        return True
            except:
                pass
                
            # Method 3: JavaScript click on the row
            try:
                row = self.driver.find_element(By.XPATH, row_xpath)
                self.driver.execute_script("arguments[0].click();", row)
                logger.info(f"✅ JavaScript clicked on {ms_id} row")
                return True
            except:
                pass
                
        except Exception as e:
            logger.error(f"Failed to click manuscript {ms_id}: {e}")
            
        return False
        
    def parse_manuscript_list_alternative(self):
        """Alternative parsing method when manuscripts are in a table"""
        logger.info("📋 Using alternative parsing method...")
        
        manuscripts_on_page = []
        
        # Look for manuscript details in the current page
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Find all tables
        tables = soup.find_all('table')
        
        for table in tables:
            # Look for manuscript pattern
            table_text = table.get_text()
            ms_matches = re.findall(r'MAFI-\d{4}-\d+', table_text)
            
            if ms_matches:
                # This table contains manuscripts
                rows = table.find_all('tr')
                
                for row in rows:
                    row_text = row.get_text()
                    ms_match = re.search(r'MAFI-\d{4}-\d+', row_text)
                    
                    if ms_match:
                        ms_id = ms_match.group()
                        
                        # Extract basic info from the row
                        cells = row.find_all('td')
                        
                        manuscript_info = {
                            'Manuscript #': ms_id,
                            'row_data': [cell.get_text(strip=True) for cell in cells],
                            'found_in_list': True
                        }
                        
                        # Try to identify title, authors, etc. from cell positions
                        if len(cells) > 1:
                            # Usually: MS ID | Title | Author | Date | Status
                            for i, cell in enumerate(cells):
                                cell_text = cell.get_text(strip=True)
                                
                                # Title is often the longest cell
                                if len(cell_text) > 50 and not re.match(r'MAFI-', cell_text):
                                    manuscript_info['Title'] = cell_text
                                    
                                # Look for author patterns
                                if ',' in cell_text and len(cell_text.split(',')) == 2:
                                    parts = cell_text.split(',')
                                    if all(part.strip().replace('-', '').isalpha() for part in parts):
                                        manuscript_info['Contact Author'] = cell_text
                                        
                                # Look for dates
                                if re.match(r'\d{1,2}-\w{3}-\d{4}', cell_text):
                                    manuscript_info['Submission Date'] = cell_text
                                    
                        manuscripts_on_page.append(manuscript_info)
                        
        return manuscripts_on_page
        
    def get_manuscript_details(self, ms_id, flagged_emails):
        """Get detailed information for a manuscript"""
        logger.info(f"📄 Getting details for {ms_id}")
        
        # First, try to access the manuscript
        if self.click_manuscript_row(ms_id):
            time.sleep(3)
            
            # Check if we navigated to details page
            if ms_id in self.driver.page_source:
                # Use the journal's parser
                try:
                    details = self.journal.parse_manuscript_panel(
                        self.driver.page_source,
                        flagged_emails=flagged_emails
                    )
                    
                    logger.info(f"✅ Parsed details for {ms_id}")
                    logger.info(f"   Title: {details.get('Title', 'N/A')}")
                    logger.info(f"   Author: {details.get('Contact Author', 'N/A')}")
                    logger.info(f"   Referees: {len(details.get('Referees', []))}")
                    
                    # Go back to list
                    self.driver.back()
                    time.sleep(2)
                    
                    return details
                    
                except Exception as e:
                    logger.error(f"Error parsing details: {e}")
                    self.driver.back()
                    time.sleep(2)
                    
        return None
        
    def run(self):
        """Main scraping process"""
        logger.info("🚀 Starting MF Final Scraper")
        
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
        self.journal = MFJournal(self.driver, debug=True)
        
        try:
            # Login
            logger.info("🔐 Logging in...")
            self.journal.login()
            
            # Navigate to AE Center
            logger.info("🏢 Navigating to Associate Editor Center...")
            ae_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            time.sleep(3)
            
            self.save_debug_page("ae_dashboard")
            
            # Get flagged emails
            logger.info("📧 Getting flagged emails...")
            flagged_emails = fetch_starred_emails("MF")
            
            # Process each status category
            status_categories = [
                ("Awaiting Reviewer Scores", "2"),
                ("Overdue Manuscripts Awaiting Revision", "1")
            ]
            
            for status, expected_count in status_categories:
                logger.info(f"\n🔍 Processing: {status}")
                
                # Find and click the count
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Find the row with this status
                status_found = False
                for row in soup.find_all('tr'):
                    if status in row.get_text():
                        # Find the count link in this row
                        count_link = row.find('a')
                        if count_link and count_link.get_text(strip=True).isdigit():
                            count = count_link.get_text(strip=True)
                            logger.info(f"📊 Found {count} manuscripts (expected {expected_count})")
                            
                            # Click using Selenium
                            try:
                                # Find by partial text to be more flexible
                                count_elem = self.driver.find_element(By.LINK_TEXT, count)
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", count_elem)
                                time.sleep(0.5)
                                count_elem.click()
                                time.sleep(3)
                                
                                self.save_debug_page(f"{status.replace(' ', '_')}_list")
                                
                                # Parse manuscripts on this page
                                manuscripts_found = self.parse_manuscript_list_alternative()
                                logger.info(f"Found {len(manuscripts_found)} manuscripts in list")
                                
                                # Get details for each manuscript
                                for ms_info in manuscripts_found:
                                    ms_id = ms_info['Manuscript #']
                                    
                                    # Get full details
                                    details = self.get_manuscript_details(ms_id, flagged_emails)
                                    
                                    if details:
                                        details['status_category'] = status
                                        self.manuscripts.append(details)
                                    else:
                                        # Use basic info if we couldn't get details
                                        ms_info['status_category'] = status
                                        ms_info['Referees'] = []
                                        self.manuscripts.append(ms_info)
                                        
                                # Go back to dashboard
                                self.driver.back()
                                time.sleep(2)
                                
                                status_found = True
                                break
                                
                            except Exception as e:
                                logger.error(f"Error clicking count: {e}")
                                
                if not status_found:
                    logger.warning(f"Could not find status: {status}")
                    
            # Final summary
            self.print_results()
            self.save_results()
            
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            
        finally:
            self.driver.quit()
            
    def print_results(self):
        """Print scraping results"""
        logger.info("\n" + "=" * 70)
        logger.info("📊 FINAL SCRAPING RESULTS")
        logger.info("=" * 70)
        
        total_referees = 0
        
        for ms in self.manuscripts:
            ms_id = ms.get('Manuscript #', 'Unknown')
            title = ms.get('Title', 'No title')[:60] + "..." if len(ms.get('Title', '')) > 60 else ms.get('Title', 'No title')
            author = ms.get('Contact Author', 'Unknown')
            status = ms.get('status_category', 'Unknown')
            referees = ms.get('Referees', [])
            
            logger.info(f"\n📄 {ms_id}")
            logger.info(f"   Title: {title}")
            logger.info(f"   Author: {author}")
            logger.info(f"   Status: {status}")
            logger.info(f"   Referees ({len(referees)}):")
            
            for ref in referees:
                logger.info(f"     • {ref.get('Referee Name', 'Unknown')} - {ref.get('Status', 'Unknown')}")
                
            total_referees += len(referees)
            
        logger.info(f"\n📊 SUMMARY:")
        logger.info(f"   Total manuscripts: {len(self.manuscripts)}")
        logger.info(f"   Total referees: {total_referees}")
        logger.info(f"   Expected: 2 manuscripts with 4 referees")
        
    def save_results(self):
        """Save results to JSON file"""
        output_file = Path("mf_final_results.json")
        
        with open(output_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_manuscripts': len(self.manuscripts),
                'total_referees': sum(len(ms.get('Referees', [])) for ms in self.manuscripts),
                'manuscripts': self.manuscripts
            }, f, indent=2)
            
        logger.info(f"\n💾 Results saved to: {output_file}")


if __name__ == "__main__":
    scraper = MFManuscriptScraper()
    scraper.run()