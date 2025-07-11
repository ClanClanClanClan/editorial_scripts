#!/usr/bin/env python3
"""
Final Debug - Explore all possible paths to find referee details
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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from journals.mf import MFJournal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FINAL_DEBUG")


class FinalDebugger:
    def __init__(self):
        self.driver = None
        self.journal = None
        self.debug_dir = Path("final_debug_results")
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
        """Take screenshot with description"""
        self.screenshot_count += 1
        filename = f"{self.screenshot_count:03d}_{description.replace(' ', '_')}.png"
        filepath = self.debug_dir / filename
        self.driver.save_screenshot(str(filepath))
        logger.info(f"📸 Screenshot: {filename}")
        return filepath
        
    def debug_all_paths(self):
        """Debug all possible navigation paths"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 FINAL DEBUG - EXPLORING ALL PATHS")
        logger.info(f"{'='*80}")
        
        self.create_driver()
        
        try:
            # Login to MF
            self.journal = MFJournal(self.driver, debug=True)
            
            # Navigate to journal URL
            logger.info("Navigating to MF...")
            self.driver.get("https://mc.manuscriptcentral.com/mafi")
            time.sleep(3)
            
            # Handle cookie banner
            try:
                cookie_button = self.driver.find_element(By.ID, "onetrust-accept-btn-handler")
                if cookie_button.is_displayed():
                    logger.info("Accepting cookies...")
                    cookie_button.click()
                    time.sleep(1)
            except:
                pass
                
            self.journal.login()
            self.take_screenshot("01_after_login")
            
            # Navigate to AE Center
            ae_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            time.sleep(3)
            self.take_screenshot("02_ae_center")
            
            # Check what categories are available
            logger.info("\n📂 Available categories:")
            links = self.driver.find_elements(By.TAG_NAME, "a")
            category_links = []
            
            for link in links:
                text = link.text.strip()
                if text and any(keyword in text.lower() for keyword in ['awaiting', 'review', 'referee']):
                    logger.info(f"  - {text}")
                    category_links.append((text, link))
                    
            # Navigate to Awaiting Reviewer Scores
            category = "Awaiting Reviewer Scores"
            logger.info(f"\n📂 Navigating to: {category}")
            category_link = self.driver.find_element(By.LINK_TEXT, category)
            category_link.click()
            time.sleep(3)
            self.take_screenshot("03_manuscript_list")
            
            # PATH 1: Try form submission with selected checkboxes
            logger.info("\n🧪 PATH 1: Form submission with checkboxes")
            
            # Find the form
            forms = self.driver.find_elements(By.TAG_NAME, "form")
            logger.info(f"Found {len(forms)} forms")
            
            if forms:
                form = forms[0]
                
                # Look for submit buttons in the form
                submit_buttons = form.find_elements(By.XPATH, ".//input[@type='submit']")
                logger.info(f"Found {len(submit_buttons)} submit buttons in form")
                
                for i, btn in enumerate(submit_buttons):
                    try:
                        value = btn.get_attribute('value') or ''
                        name = btn.get_attribute('name') or ''
                        is_displayed = btn.is_displayed()
                        
                        logger.info(f"  Submit {i+1}: value='{value}', name='{name}', displayed={is_displayed}")
                        
                        if is_displayed and value:
                            self.take_screenshot(f"04_submit_button_{i+1}")
                    except:
                        pass
                        
            # PATH 2: Check for action links in referee count cells
            logger.info("\n🧪 PATH 2: Check referee count cells for links")
            
            # Find cells with referee counts
            cells = self.driver.find_elements(By.XPATH, "//td[contains(., 'active selections')]")
            logger.info(f"Found {len(cells)} cells with referee counts")
            
            for i, cell in enumerate(cells[:1]):  # Check first one
                cell_text = cell.text
                logger.info(f"\nCell text: {cell_text}")
                
                # Check for links in this cell
                links_in_cell = cell.find_elements(By.TAG_NAME, "a")
                if links_in_cell:
                    logger.info(f"  Found {len(links_in_cell)} links in cell")
                    for link in links_in_cell:
                        logger.info(f"    - Link text: '{link.text}'")
                        
            # PATH 3: Double-click on manuscript rows
            logger.info("\n🧪 PATH 3: Double-click on manuscript row")
            
            try:
                # Find first manuscript row
                row = self.driver.find_element(By.XPATH, "//tr[contains(., 'MAFI-2024-0167')]")
                
                # Double-click the row
                actions = ActionChains(self.driver)
                actions.double_click(row).perform()
                time.sleep(3)
                
                self.take_screenshot("05_after_double_click")
                
                # Check if we navigated somewhere
                current_url = self.driver.current_url
                logger.info(f"Current URL after double-click: {current_url}")
                
                # Go back if needed
                if "manuscriptdetail" in current_url.lower():
                    self.driver.back()
                    time.sleep(2)
                    
            except Exception as e:
                logger.error(f"Double-click failed: {e}")
                
            # PATH 4: Right-click context menu
            logger.info("\n🧪 PATH 4: Right-click for context menu")
            
            try:
                row = self.driver.find_element(By.XPATH, "//tr[contains(., 'MAFI-2024-0167')]")
                
                # Right-click
                actions = ActionChains(self.driver)
                actions.context_click(row).perform()
                time.sleep(1)
                
                self.take_screenshot("06_right_click_menu")
                
                # Press Escape to close context menu
                body = self.driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.ESCAPE)
                
            except Exception as e:
                logger.error(f"Right-click failed: {e}")
                
            # PATH 5: Look for hidden action buttons that appear on hover
            logger.info("\n🧪 PATH 5: Hover over elements to reveal hidden buttons")
            
            try:
                # Hover over manuscript row
                row = self.driver.find_element(By.XPATH, "//tr[contains(., 'MAFI-2024-0167')]")
                actions = ActionChains(self.driver)
                actions.move_to_element(row).perform()
                time.sleep(1)
                
                self.take_screenshot("07_hover_on_row")
                
                # Hover over Take Action cell
                take_action_cell = row.find_elements(By.TAG_NAME, "td")[-1]
                actions.move_to_element(take_action_cell).perform()
                time.sleep(1)
                
                self.take_screenshot("08_hover_on_take_action_cell")
                
            except Exception as e:
                logger.error(f"Hover failed: {e}")
                
            # PATH 6: Check page source for hidden forms or JavaScript functions
            logger.info("\n🧪 PATH 6: Analyze page source for hidden elements")
            
            page_source = self.driver.page_source
            
            # Look for JavaScript functions related to actions
            if "takeAction" in page_source:
                logger.info("✅ Found 'takeAction' in JavaScript")
            if "submitAction" in page_source:
                logger.info("✅ Found 'submitAction' in JavaScript")
            if "viewReferees" in page_source:
                logger.info("✅ Found 'viewReferees' in JavaScript")
                
            # PATH 7: Check if there's a specific referee management section
            logger.info("\n🧪 PATH 7: Look for referee management links")
            
            # Go back to AE Center
            ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
            ae_link.click()
            time.sleep(2)
            
            # Look for referee-related links
            links = self.driver.find_elements(By.TAG_NAME, "a")
            referee_links = []
            
            for link in links:
                text = link.text.strip().lower()
                if text and any(keyword in text for keyword in ['referee', 'reviewer', 'review']):
                    referee_links.append(link.text.strip())
                    
            if referee_links:
                logger.info("Found referee-related links:")
                for link_text in referee_links:
                    logger.info(f"  - {link_text}")
                    
            self.take_screenshot("09_ae_center_all_links")
            
            logger.info("\n" + "="*80)
            logger.info("DEBUG COMPLETE - Check screenshots for visual inspection")
            logger.info("="*80)
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            self.take_screenshot("error")
            
        finally:
            logger.info("\nPress Enter to close browser...")
            try:
                input()
            except:
                pass
            self.driver.quit()


def main():
    debugger = FinalDebugger()
    debugger.debug_all_paths()


if __name__ == "__main__":
    main()