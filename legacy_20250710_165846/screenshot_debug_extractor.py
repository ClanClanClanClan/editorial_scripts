#!/usr/bin/env python3
"""
Screenshot Debug Extractor - Takes screenshots at every step to see what's happening
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
from bs4 import BeautifulSoup
import json
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from journals.mf import MFJournal
from journals.mor import MORJournal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SCREENSHOT_DEBUG")


class ScreenshotDebugExtractor:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.debug_dir = Path(f"{journal_name.lower()}_screenshot_debug")
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
        
    def highlight_element(self, element):
        """Highlight an element with red border"""
        self.driver.execute_script("""
            arguments[0].style.border = '3px solid red';
            arguments[0].style.backgroundColor = 'yellow';
        """, element)
        
    def run_debug(self):
        """Run debug extraction with detailed screenshots"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 SCREENSHOT DEBUG FOR {self.journal_name}")
        logger.info(f"{'='*80}")
        
        self.create_driver()
        
        try:
            # Login
            if self.journal_name == "MF":
                self.journal = MFJournal(self.driver, debug=True)
                category = "Awaiting Reviewer Scores"
            else:
                self.journal = MORJournal(self.driver, debug=True)
                category = "Awaiting Reviewer Reports"
            
            # Navigate to journal URL first
            if self.journal_name == "MF":
                journal_url = "https://mc.manuscriptcentral.com/mafi"
            else:
                journal_url = "https://mc.manuscriptcentral.com/mor"
                
            logger.info(f"Navigating to: {journal_url}")
            self.driver.get(journal_url)
            time.sleep(3)
            
            # Handle cookie banner if present
            try:
                logger.info("Looking for cookie banner...")
                cookie_button = self.driver.find_element(By.ID, "onetrust-accept-btn-handler")
                if cookie_button.is_displayed():
                    logger.info("Found cookie banner, accepting...")
                    cookie_button.click()
                    time.sleep(1)
            except:
                logger.info("No cookie banner found")
                
            self.journal.login()
            self.take_screenshot("01_after_login")
            
            # Navigate to AE Center
            try:
                ae_link = WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
                )
                ae_link.click()
                time.sleep(3)
                self.take_screenshot("02_ae_center")
            except Exception as e:
                logger.error(f"Could not find AE Center link: {e}")
                # Take screenshot to see what's on the page
                self.take_screenshot("02_ae_center_error")
                raise
            
            # Navigate to category
            logger.info(f"\n📂 Navigating to: {category}")
            category_link = self.driver.find_element(By.LINK_TEXT, category)
            category_link.click()
            time.sleep(3)
            self.take_screenshot("03_category_list")
            
            # Get manuscript IDs
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            if self.journal_name == "MF":
                pattern = r'MAFI-\d{4}-\d+'
            else:
                pattern = r'MOR-\d{4}-\d+'
                
            manuscript_ids = list(set(re.findall(pattern, soup.get_text())))
            logger.info(f"📄 Found manuscripts: {manuscript_ids}")
            
            if manuscript_ids:
                # Process first manuscript
                ms_id = manuscript_ids[0]
                logger.info(f"\n🎯 Processing: {ms_id}")
                
                # Find the row
                rows = self.driver.find_elements(By.TAG_NAME, "tr")
                target_row = None
                
                for row in rows:
                    if ms_id in row.text:
                        target_row = row
                        self.highlight_element(row)
                        self.take_screenshot(f"04_highlighted_row_{ms_id}")
                        logger.info(f"✅ Found and highlighted row for {ms_id}")
                        break
                        
                if target_row:
                    # Find all cells in the row
                    cells = target_row.find_elements(By.TAG_NAME, "td")
                    logger.info(f"📊 Row has {len(cells)} cells")
                    
                    # Highlight last cell (Take Action column)
                    if cells:
                        last_cell = cells[-1]
                        self.highlight_element(last_cell)
                        self.take_screenshot("05_highlighted_take_action_cell")
                        
                        # Find all elements in the last cell
                        all_elements = last_cell.find_elements(By.XPATH, ".//*")
                        logger.info(f"📦 Last cell contains {len(all_elements)} elements")
                        
                        # Try to find clickable elements
                        for i, elem in enumerate(all_elements):
                            try:
                                tag = elem.tag_name
                                elem_type = elem.get_attribute('type')
                                elem_name = elem.get_attribute('name')
                                elem_value = elem.get_attribute('value')
                                elem_onclick = elem.get_attribute('onclick')
                                is_displayed = elem.is_displayed()
                                
                                logger.info(f"\nElement {i+1}:")
                                logger.info(f"  Tag: {tag}")
                                logger.info(f"  Type: {elem_type}")
                                logger.info(f"  Name: {elem_name}")
                                logger.info(f"  Value: {elem_value}")
                                logger.info(f"  Onclick: {elem_onclick}")
                                logger.info(f"  Displayed: {is_displayed}")
                                
                                # If it looks like a checkbox, try to click it
                                if tag == 'input' and elem_type == 'checkbox':
                                    logger.info("  🎯 This is a checkbox! Clicking it...")
                                    elem.click()
                                    time.sleep(1)
                                    self.take_screenshot("06_after_checkbox_click")
                                    break
                                    
                            except Exception as e:
                                logger.debug(f"Error with element {i+1}: {e}")
                                
                    # Since checkbox is already selected, look for Take Action button
                    logger.info("\n🔍 Looking for Take Action button (checkboxes already selected)...")
                    
                    # Scroll to see full page
                    self.driver.execute_script("window.scrollTo(0, 0)")
                    time.sleep(1)
                    self.take_screenshot("06a_page_top")
                    
                    # Find all buttons and submit inputs ON THE ENTIRE PAGE
                    buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    inputs = self.driver.find_elements(By.XPATH, "//input[@type='submit' or @type='button']")
                    links = self.driver.find_elements(By.TAG_NAME, "a")
                    
                    logger.info(f"Found {len(buttons)} buttons, {len(inputs)} input buttons, and {len(links)} links")
                    
                    # Look specifically for Take Action text anywhere
                    take_action_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Take Action')]")
                    logger.info(f"Found {len(take_action_elements)} elements containing 'Take Action' text")
                    
                    for elem in take_action_elements:
                        try:
                            tag = elem.tag_name
                            text = elem.text
                            is_displayed = elem.is_displayed()
                            logger.info(f"\nTake Action element: {tag} - '{text}' - Displayed: {is_displayed}")
                            
                            if is_displayed and tag in ['button', 'input', 'a']:
                                self.highlight_element(elem)
                                self.take_screenshot("07_found_take_action_button")
                                logger.info("  ✅ Found Take Action button!")
                                
                                # Try to click it
                                elem.click()
                                time.sleep(3)
                                self.take_screenshot("08_after_take_action_click")
                                break
                        except:
                            pass
                    
                    # Also check all visible buttons/inputs
                    all_buttons = buttons + inputs
                    for i, btn in enumerate(all_buttons):
                        try:
                            btn_text = btn.get_attribute('value') or btn.text
                            is_displayed = btn.is_displayed()
                            
                            if is_displayed and btn_text:
                                logger.info(f"\nVisible Button {i+1}: '{btn_text}'")
                                
                                # Highlight potential Take Action buttons
                                if 'take' in btn_text.lower() and 'action' in btn_text.lower():
                                    self.highlight_element(btn)
                                    self.take_screenshot(f"07_highlighted_take_action_button_{i+1}")
                                    logger.info("  ✅ This is the Take Action button!")
                                    
                                    # Click it
                                    logger.info("  🎯 Clicking Take Action...")
                                    btn.click()
                                    time.sleep(3)
                                    self.take_screenshot("08_after_take_action_click")
                                    
                                    # Check where we are now
                                    current_url = self.driver.current_url
                                    logger.info(f"  📍 Current URL: {current_url}")
                                    
                                    # Look for referee information
                                    page_text = self.driver.page_source
                                    if "referee" in page_text.lower() or "reviewer" in page_text.lower():
                                        logger.info("  ✅ Found referee/reviewer text on page!")
                                        self.take_screenshot("09_referee_page")
                                        
                                    break
                                    
                        except Exception as e:
                            logger.debug(f"Error with button {i+1}: {e}")
                    
                    # Scroll down to check bottom of page
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(1)
                    self.take_screenshot("06b_page_bottom")
                            
            # Take final screenshot
            self.take_screenshot("10_final_state")
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            self.take_screenshot("error")
            
        finally:
            # Don't use input() in automated mode
            time.sleep(2)
            self.driver.quit()


def main():
    # Debug MF only
    logger.info("="*80)
    logger.info("SCREENSHOT DEBUG: MF")
    logger.info("="*80)
    
    mf_debug = ScreenshotDebugExtractor("MF")
    mf_debug.run_debug()


if __name__ == "__main__":
    main()