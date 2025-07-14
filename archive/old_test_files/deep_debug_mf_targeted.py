#!/usr/bin/env python3
"""
Ultra-deep targeted debugging for MF journal to find the 2 manuscripts in "Awaiting Reviewer Scores".
This script specifically targets the known location of manuscripts.
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
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import json
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from journals.mf import MFJournal
from core.email_utils import fetch_starred_emails

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MF_DEEP_DEBUG")


class MFDeepDebugger:
    """Ultra-deep debugger for MF journal"""
    
    def __init__(self):
        self.driver = None
        self.output_dir = Path("mf_deep_debug_output")
        self.output_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
    def create_driver(self):
        """Create Chrome driver with debugging options"""
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        # Enable logging
        options.add_argument('--enable-logging')
        options.add_argument('--v=1')
        
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
            
        return self.driver
    
    def save_debug_artifacts(self, stage_name, additional_data=None):
        """Save screenshot, HTML, and additional debug data"""
        stage_dir = self.output_dir / self.timestamp / stage_name
        stage_dir.mkdir(parents=True, exist_ok=True)
        
        # Screenshot
        screenshot_path = stage_dir / "screenshot.png"
        self.driver.save_screenshot(str(screenshot_path))
        
        # HTML
        html_path = stage_dir / "page.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
        
        # Current URL and title
        info = {
            'url': self.driver.current_url,
            'title': self.driver.title,
            'timestamp': datetime.now().isoformat()
        }
        
        if additional_data:
            info.update(additional_data)
            
        info_path = stage_dir / "info.json"
        with open(info_path, 'w') as f:
            json.dump(info, f, indent=2)
            
        logger.info(f"📸 Saved debug artifacts to {stage_dir}")
        
    def wait_and_click(self, selector, by=By.XPATH, timeout=10):
        """Wait for element and click with retry logic"""
        wait = WebDriverWait(self.driver, timeout)
        try:
            element = wait.until(EC.element_to_be_clickable((by, selector)))
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)
            element.click()
            return True
        except Exception as e:
            logger.error(f"Failed to click {selector}: {e}")
            return False
    
    def find_awaiting_reviewer_scores(self):
        """Specifically target the 'Awaiting Reviewer Scores' category"""
        logger.info("🎯 Targeting 'Awaiting Reviewer Scores' category...")
        
        # Save current state
        self.save_debug_artifacts("before_category_search")
        
        # Get page HTML for analysis
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Method 1: Find by exact text match in table cells
        found = False
        all_tds = soup.find_all('td')
        
        for i, td in enumerate(all_tds):
            text = td.get_text(strip=True)
            if text == "Awaiting Reviewer Scores":
                logger.info(f"✅ Found 'Awaiting Reviewer Scores' at position {i}")
                
                # The count should be in the previous td
                if i > 0:
                    count_td = all_tds[i-1]
                    count_text = count_td.get_text(strip=True)
                    logger.info(f"📊 Count cell text: '{count_text}'")
                    
                    # Try to click the count
                    try:
                        # Find the count element in Selenium
                        count_xpath = f"//td[normalize-space()='{count_text}'][following-sibling::td[normalize-space()='Awaiting Reviewer Scores']]"
                        count_element = self.driver.find_element(By.XPATH, count_xpath)
                        
                        # Check if it's a link
                        link = count_element.find_element(By.TAG_NAME, 'a') if count_element.find_elements(By.TAG_NAME, 'a') else count_element
                        
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", link)
                        time.sleep(1)
                        
                        # Save pre-click state
                        self.save_debug_artifacts("before_clicking_count")
                        
                        # Click
                        link.click()
                        time.sleep(3)
                        
                        # Save post-click state
                        self.save_debug_artifacts("after_clicking_count")
                        
                        found = True
                        break
                        
                    except Exception as e:
                        logger.error(f"Failed to click count cell: {e}")
                        
                        # Try alternative: Click the status text itself
                        try:
                            status_xpath = "//td[normalize-space()='Awaiting Reviewer Scores']"
                            status_element = self.driver.find_element(By.XPATH, status_xpath)
                            status_element.click()
                            time.sleep(3)
                            self.save_debug_artifacts("after_clicking_status")
                            found = True
                            break
                        except Exception as e2:
                            logger.error(f"Failed to click status text: {e2}")
        
        # Method 2: Try to find via link analysis
        if not found:
            logger.info("🔍 Method 2: Searching for clickable links...")
            
            links = self.driver.find_elements(By.TAG_NAME, 'a')
            for link in links:
                try:
                    onclick = link.get_attribute('onclick') or ''
                    href = link.get_attribute('href') or ''
                    text = link.text.strip()
                    
                    # Log all links for analysis
                    if onclick or (href and href != '#'):
                        logger.debug(f"Link: text='{text}', onclick='{onclick[:100]}...', href='{href[:100]}...'")
                    
                    # Look for submission/manuscript related links
                    if any(pattern in onclick.lower() + href.lower() for pattern in ['submission', 'manuscript', 'awaiting', 'reviewer']):
                        logger.info(f"📎 Found potential link: {text}")
                        
                except Exception:
                    continue
        
        return found
    
    def analyze_manuscript_list(self):
        """Analyze the manuscript list page in detail"""
        logger.info("📋 Analyzing manuscript list page...")
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Find all tables
        tables = soup.find_all('table')
        logger.info(f"Found {len(tables)} tables on page")
        
        manuscripts = []
        
        for idx, table in enumerate(tables):
            table_text = table.get_text()
            
            # Look for MAFI pattern
            mafi_matches = re.findall(r'MAFI-\d{4}-\d+', table_text)
            if mafi_matches:
                logger.info(f"📄 Table {idx} contains manuscripts: {mafi_matches}")
                
                # Try to extract detailed info from table rows
                rows = table.find_all('tr')
                for row in rows:
                    row_text = row.get_text()
                    if re.search(r'MAFI-\d{4}-\d+', row_text):
                        # Extract manuscript details
                        cells = row.find_all(['td', 'th'])
                        
                        manuscript_info = {
                            'row_text': row_text.strip(),
                            'cells': [cell.get_text(strip=True) for cell in cells],
                            'links': []
                        }
                        
                        # Find links in this row
                        links = row.find_all('a')
                        for link in links:
                            manuscript_info['links'].append({
                                'text': link.get_text(strip=True),
                                'href': link.get('href', ''),
                                'onclick': link.get('onclick', '')
                            })
                        
                        manuscripts.append(manuscript_info)
                        
        # Save detailed analysis
        analysis_path = self.output_dir / self.timestamp / "manuscript_analysis.json"
        with open(analysis_path, 'w') as f:
            json.dump({
                'manuscripts_found': len(manuscripts),
                'details': manuscripts
            }, f, indent=2)
            
        return manuscripts
    
    def click_manuscript_details(self, manuscript_id):
        """Try to click into a specific manuscript's details"""
        logger.info(f"🔍 Attempting to access details for {manuscript_id}")
        
        # Method 1: Direct link click
        try:
            # Look for a link containing the manuscript ID
            xpath = f"//a[contains(text(), '{manuscript_id}')]"
            if self.wait_and_click(xpath):
                logger.info(f"✅ Clicked manuscript link for {manuscript_id}")
                time.sleep(3)
                self.save_debug_artifacts(f"manuscript_details_{manuscript_id}")
                return True
        except Exception as e:
            logger.debug(f"Direct link method failed: {e}")
        
        # Method 2: Click anywhere in the row containing manuscript ID
        try:
            row_xpath = f"//tr[contains(., '{manuscript_id}')]//a"
            links = self.driver.find_elements(By.XPATH, row_xpath)
            
            for link in links:
                try:
                    link_text = link.text.strip()
                    logger.info(f"Trying link in manuscript row: '{link_text}'")
                    link.click()
                    time.sleep(3)
                    
                    # Check if we navigated to details
                    if manuscript_id in self.driver.page_source:
                        self.save_debug_artifacts(f"manuscript_details_{manuscript_id}_method2")
                        return True
                except Exception:
                    continue
                    
        except Exception as e:
            logger.debug(f"Row click method failed: {e}")
            
        return False
    
    def run_deep_debug(self):
        """Run the complete deep debugging process"""
        logger.info("🚀 Starting MF Ultra-Deep Debug Session")
        logger.info("=" * 60)
        
        results = {
            'start_time': datetime.now().isoformat(),
            'manuscripts': [],
            'errors': []
        }
        
        try:
            # Create driver
            self.create_driver()
            
            # Load credentials
            env_file = Path(".env")
            if env_file.exists():
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key] = value
            
            # Create MF journal instance and login
            journal = MFJournal(self.driver, debug=True)
            
            logger.info("🔐 Logging in to MF...")
            journal.login()
            
            # Save post-login state
            self.save_debug_artifacts("after_login")
            
            # Navigate to Associate Editor Center
            logger.info("🏢 Navigating to Associate Editor Center...")
            
            # Try multiple methods to find AE center
            ae_found = False
            
            # Method 1: Look for exact text
            try:
                if self.wait_and_click("//a[contains(text(), 'Associate Editor Center')]"):
                    ae_found = True
                    logger.info("✅ Found AE Center via exact text match")
            except:
                pass
            
            # Method 2: Look for partial matches
            if not ae_found:
                for variation in ['Associate Editor', 'Editor Center', 'AE Center']:
                    try:
                        if self.wait_and_click(f"//a[contains(text(), '{variation}')]"):
                            ae_found = True
                            logger.info(f"✅ Found AE Center via '{variation}'")
                            break
                    except:
                        continue
            
            if ae_found:
                time.sleep(3)
                self.save_debug_artifacts("ae_center")
                
                # Now find and click "Awaiting Reviewer Scores"
                if self.find_awaiting_reviewer_scores():
                    # Analyze the manuscript list
                    manuscripts = self.analyze_manuscript_list()
                    results['manuscripts'] = manuscripts
                    
                    # Try to access each manuscript's details
                    for ms in manuscripts:
                        # Extract manuscript ID from the data
                        ms_text = ms.get('row_text', '')
                        ms_match = re.search(r'MAFI-\d{4}-\d+', ms_text)
                        if ms_match:
                            ms_id = ms_match.group()
                            if self.click_manuscript_details(ms_id):
                                # Analyze referee information
                                self.analyze_referee_details(ms_id)
                                
                                # Go back to list
                                self.driver.back()
                                time.sleep(2)
                else:
                    logger.error("❌ Could not find 'Awaiting Reviewer Scores' category")
                    results['errors'].append("Category not found")
            else:
                logger.error("❌ Could not navigate to Associate Editor Center")
                results['errors'].append("AE Center not accessible")
                
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}")
            results['errors'].append(str(e))
            
        finally:
            results['end_time'] = datetime.now().isoformat()
            
            # Save final results
            results_path = self.output_dir / self.timestamp / "debug_results.json"
            results_path.parent.mkdir(parents=True, exist_ok=True)
            with open(results_path, 'w') as f:
                json.dump(results, f, indent=2)
            
            if self.driver:
                self.driver.quit()
                
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 DEBUG SESSION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Manuscripts found: {len(results['manuscripts'])}")
        logger.info(f"Errors encountered: {len(results['errors'])}")
        logger.info(f"Debug artifacts saved to: {self.output_dir / self.timestamp}")
        
        return results
    
    def analyze_referee_details(self, manuscript_id):
        """Analyze referee information for a manuscript"""
        logger.info(f"👥 Analyzing referee details for {manuscript_id}")
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Look for reviewer/referee information
        referee_info = []
        
        # Common patterns for referee sections
        patterns = [
            "Reviewer List",
            "Referee List",
            "Reviewers",
            "Review Status"
        ]
        
        for pattern in patterns:
            elements = soup.find_all(text=re.compile(pattern, re.I))
            for elem in elements:
                # Find the containing table
                parent = elem.parent
                while parent and parent.name != 'table':
                    parent = parent.parent
                    
                if parent:
                    logger.info(f"Found referee section: {pattern}")
                    # Extract referee details from table
                    rows = parent.find_all('tr')
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) > 1:
                            row_data = [cell.get_text(strip=True) for cell in cells]
                            # Look for name patterns (Last, First)
                            for cell in row_data:
                                if ',' in cell and not any(x in cell.lower() for x in ['date', 'status', 'review']):
                                    referee_info.append({
                                        'name': cell,
                                        'row_data': row_data
                                    })
        
        # Save referee analysis
        referee_path = self.output_dir / self.timestamp / f"referees_{manuscript_id}.json"
        with open(referee_path, 'w') as f:
            json.dump({
                'manuscript_id': manuscript_id,
                'referee_count': len(referee_info),
                'referees': referee_info
            }, f, indent=2)
            
        logger.info(f"Found {len(referee_info)} referees for {manuscript_id}")
        
        return referee_info


def main():
    """Run the ultra-deep MF debugging"""
    debugger = MFDeepDebugger()
    results = debugger.run_deep_debug()
    
    # Return exit code based on success
    if results['manuscripts']:
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit(main())