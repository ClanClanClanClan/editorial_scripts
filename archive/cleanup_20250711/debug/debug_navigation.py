#!/usr/bin/env python3
"""
Debug script to understand ScholarOne navigation structure
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

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from journals.mf import MFJournal
from core.email_utils import fetch_starred_emails

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("NAV_DEBUG")


class NavigationDebugger:
    def __init__(self):
        self.driver = None
        self.journal = None
        self.debug_dir = Path("nav_debug_output")
        self.debug_dir.mkdir(exist_ok=True)
        self.step_count = 0
        
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
            
    def save_step(self, description):
        """Save screenshot and HTML for a step"""
        self.step_count += 1
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Screenshot
        screenshot_path = self.debug_dir / f"step_{self.step_count:03d}_{description}_{timestamp}.png"
        self.driver.save_screenshot(str(screenshot_path))
        
        # HTML
        html_path = self.debug_dir / f"step_{self.step_count:03d}_{description}_{timestamp}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
            
        # Extract info
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Find all links
        links = []
        for link in soup.find_all('a', href=True):
            link_text = link.get_text(strip=True)
            if link_text and len(link_text) < 100:  # Skip very long texts
                links.append({
                    'text': link_text,
                    'href': link.get('href', '')
                })
                
        # Find manuscript IDs
        import re
        mafi_pattern = re.compile(r'MAFI-\d{4}-\d+')
        manuscript_ids = list(set(mafi_pattern.findall(soup.get_text())))
        
        # Log info
        logger.info(f"\n{'='*60}")
        logger.info(f"Step {self.step_count}: {description}")
        logger.info(f"URL: {self.driver.current_url}")
        logger.info(f"Title: {self.driver.title}")
        logger.info(f"Manuscript IDs found: {manuscript_ids}")
        logger.info(f"Links found: {len(links)}")
        
        # Log important links
        for link in links:
            if any(term in link['text'].lower() for term in ['mafi-', 'manuscript', 'next', 'previous', 'associate editor']):
                logger.info(f"  - '{link['text']}' -> {link['href'][:50]}...")
                
        return {
            'step': self.step_count,
            'description': description,
            'url': self.driver.current_url,
            'manuscript_ids': manuscript_ids,
            'links': links
        }
        
    def debug_mf_navigation(self):
        """Debug MF navigation"""
        logger.info("Starting MF navigation debug")
        
        # Login
        self.journal = MFJournal(self.driver, debug=True)
        self.journal.login()
        
        self.save_step("after_login")
        
        # Go to AE Center
        try:
            ae_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            time.sleep(3)
        except:
            # Handle confirmation if needed
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
            
        self.save_step("ae_center")
        
        # Click on "Awaiting Reviewer Scores"
        status_text = "Awaiting Reviewer Scores"
        try:
            status_link = self.driver.find_element(By.LINK_TEXT, status_text)
            status_link.click()
            time.sleep(3)
            
            step_info = self.save_step("after_clicking_status")
            
            # Analyze what happened
            if len(step_info['manuscript_ids']) == 1:
                logger.info("✅ Navigated directly to manuscript detail page")
                ms_id = step_info['manuscript_ids'][0]
                
                # Look for navigation to other manuscripts
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Check for Next/Previous links
                nav_links = []
                for link in soup.find_all('a'):
                    text = link.get_text(strip=True).lower()
                    if any(nav in text for nav in ['next', 'previous', 'list']):
                        nav_links.append(link.get_text(strip=True))
                        
                logger.info(f"Navigation links found: {nav_links}")
                
            elif len(step_info['manuscript_ids']) > 1:
                logger.info("✅ Navigated to manuscript list page")
                
                # Try to find how to click on manuscripts
                for ms_id in step_info['manuscript_ids'][:1]:  # Test with first manuscript
                    logger.info(f"Looking for ways to click on {ms_id}")
                    
                    # Find all elements containing the manuscript ID
                    elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{ms_id}')]")
                    logger.info(f"Found {len(elements)} elements containing {ms_id}")
                    
                    for i, elem in enumerate(elements):
                        try:
                            tag_name = elem.tag_name
                            parent_tag = elem.find_element(By.XPATH, "..").tag_name if elem.find_element(By.XPATH, "..") else "none"
                            logger.info(f"  Element {i}: <{tag_name}> (parent: <{parent_tag}>)")
                            
                            # Check if it's clickable
                            if tag_name == 'a' or (tag_name == 'td' and 'onclick' in elem.get_attribute('outerHTML')):
                                logger.info(f"    -> Appears clickable!")
                        except:
                            pass
                            
        except Exception as e:
            logger.error(f"Error clicking status: {e}")
            self.save_step("error_clicking_status")
            
        # Save final analysis
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'steps': self.step_count,
            'findings': "See logs for detailed analysis"
        }
        
        with open(self.debug_dir / "analysis.json", 'w') as f:
            json.dump(analysis, f, indent=2)
            
    def run(self):
        """Run the debugger"""
        self.create_driver()
        
        try:
            self.debug_mf_navigation()
        finally:
            logger.info("\nDebug session complete. Check nav_debug_output/ for screenshots and HTML files.")
            self.driver.quit()


if __name__ == "__main__":
    debugger = NavigationDebugger()
    debugger.run()