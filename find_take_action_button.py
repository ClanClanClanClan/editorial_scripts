#!/usr/bin/env python3
"""
Find Take Action Button - Focused script to locate the Take Action button
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
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from journals.mf import MFJournal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FIND_TAKE_ACTION")


class TakeActionFinder:
    def __init__(self):
        self.driver = None
        self.journal = None
        self.debug_dir = Path("take_action_debug")
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
        
    def find_take_action(self):
        """Find the Take Action button"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 FINDING TAKE ACTION BUTTON")
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
            
            # Navigate to category
            category = "Awaiting Reviewer Scores"
            logger.info(f"\n📂 Navigating to: {category}")
            category_link = self.driver.find_element(By.LINK_TEXT, category)
            category_link.click()
            time.sleep(3)
            self.take_screenshot("03_category_list")
            
            # Find checkboxes and ensure they're checked
            logger.info("\n🔍 Looking for checkboxes...")
            checkboxes = self.driver.find_elements(By.XPATH, "//input[@type='checkbox']")
            logger.info(f"Found {len(checkboxes)} checkboxes")
            
            # Check first two checkboxes if not already checked
            checked_count = 0
            for i, checkbox in enumerate(checkboxes[:2]):
                if not checkbox.is_selected():
                    logger.info(f"Clicking checkbox {i+1}")
                    checkbox.click()
                    checked_count += 1
                    time.sleep(0.5)
                else:
                    logger.info(f"Checkbox {i+1} already selected")
                    
            self.take_screenshot("04_checkboxes_selected")
            
            # Now systematically look for Take Action button
            logger.info("\n🔍 SEARCHING FOR TAKE ACTION BUTTON...")
            
            # Method 1: Look for any element containing "Take Action" text
            logger.info("\n1. Searching by text content...")
            take_action_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Take Action')]")
            logger.info(f"   Found {len(take_action_elements)} elements with 'Take Action' text")
            
            for elem in take_action_elements:
                try:
                    tag = elem.tag_name
                    text = elem.text.strip()
                    is_displayed = elem.is_displayed()
                    parent_tag = elem.find_element(By.XPATH, "..").tag_name if elem != self.driver.find_element(By.TAG_NAME, "body") else "none"
                    
                    logger.info(f"   - {tag}: '{text}' (displayed={is_displayed}, parent={parent_tag})")
                    
                    if is_displayed and tag in ['button', 'input', 'a', 'span']:
                        self.highlight_element(elem)
                        self.take_screenshot(f"05_potential_take_action_{tag}")
                except:
                    pass
                    
            # Method 2: Look for buttons with Take Action in value attribute
            logger.info("\n2. Searching input buttons by value...")
            input_buttons = self.driver.find_elements(By.XPATH, "//input[@type='button' or @type='submit']")
            logger.info(f"   Found {len(input_buttons)} input buttons")
            
            for btn in input_buttons:
                try:
                    value = btn.get_attribute('value') or ''
                    name = btn.get_attribute('name') or ''
                    is_displayed = btn.is_displayed()
                    
                    if value:
                        logger.info(f"   - Input: value='{value}', name='{name}', displayed={is_displayed}")
                        
                        if 'take action' in value.lower() and is_displayed:
                            self.highlight_element(btn)
                            self.take_screenshot("06_found_take_action_input")
                            
                            logger.info("   ✅ FOUND IT! This is the Take Action button!")
                            
                            # Try clicking it
                            logger.info("   Clicking Take Action button...")
                            btn.click()
                            time.sleep(3)
                            self.take_screenshot("07_after_clicking_take_action")
                            
                            # Check if we navigated somewhere
                            current_url = self.driver.current_url
                            logger.info(f"   Current URL: {current_url}")
                            
                            return True
                except:
                    pass
                    
            # Method 3: Look for actual button elements
            logger.info("\n3. Searching button elements...")
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            logger.info(f"   Found {len(buttons)} button elements")
            
            for btn in buttons:
                try:
                    text = btn.text.strip()
                    is_displayed = btn.is_displayed()
                    
                    if text:
                        logger.info(f"   - Button: '{text}', displayed={is_displayed}")
                        
                        if 'take action' in text.lower() and is_displayed:
                            self.highlight_element(btn)
                            self.take_screenshot("08_found_take_action_button")
                            
                            logger.info("   ✅ FOUND IT! This is the Take Action button!")
                            return True
                except:
                    pass
                    
            # Method 4: Check if button appears after scrolling
            logger.info("\n4. Checking after scroll...")
            
            # Scroll to top
            self.driver.execute_script("window.scrollTo(0, 0)")
            time.sleep(1)
            self.take_screenshot("09_scrolled_to_top")
            
            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)
            self.take_screenshot("10_scrolled_to_bottom")
            
            # Method 5: Check all visible elements on page
            logger.info("\n5. Dumping all visible text on page...")
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Look for Take Action references
            lines_with_take_action = [line for line in page_text.split('\n') if 'take action' in line.lower()]
            
            logger.info(f"   Lines containing 'take action':")
            for line in lines_with_take_action:
                logger.info(f"   - {line.strip()}")
                
            # Method 6: Try keyboard navigation
            logger.info("\n6. Trying Tab key navigation...")
            body = self.driver.find_element(By.TAG_NAME, "body")
            
            # Press Tab multiple times to see if we can reach the button
            for i in range(50):
                body.send_keys(Keys.TAB)
                time.sleep(0.1)
                
                # Check if current active element is Take Action
                try:
                    active = self.driver.switch_to.active_element
                    active_text = active.get_attribute('value') or active.text or ''
                    
                    if 'take action' in active_text.lower():
                        logger.info(f"   ✅ Found Take Action via Tab navigation!")
                        self.highlight_element(active)
                        self.take_screenshot("11_take_action_via_tab")
                        return True
                except:
                    pass
                    
            logger.error("\n❌ Could not find Take Action button!")
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            self.take_screenshot("error")
            
        finally:
            logger.info("\nPress Enter to close browser...")
            input()
            self.driver.quit()


def main():
    finder = TakeActionFinder()
    finder.find_take_action()


if __name__ == "__main__":
    main()