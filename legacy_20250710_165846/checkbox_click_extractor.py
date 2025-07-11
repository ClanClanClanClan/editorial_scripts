#!/usr/bin/env python3
"""
Checkbox Click Extractor - Click checkboxes and find the action that becomes available
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
from journals.mor import MORJournal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CHECKBOX_CLICK")


class CheckboxClickExtractor:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.output_dir = Path(f"{journal_name.lower()}_checkbox_results")
        self.output_dir.mkdir(exist_ok=True)
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
        """Take screenshot"""
        self.screenshot_count += 1
        filename = f"{self.screenshot_count:03d}_{description.replace(' ', '_')}.png"
        filepath = self.output_dir / filename
        self.driver.save_screenshot(str(filepath))
        logger.info(f"📸 Screenshot: {filename}")
        
    def extract_with_checkbox_clicks(self):
        """Extract referee data by clicking checkboxes"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🎯 CHECKBOX CLICK EXTRACTION - {self.journal_name}")
        logger.info(f"{'='*80}")
        
        self.create_driver()
        all_results = {
            'journal': self.journal_name,
            'extraction_date': datetime.now().isoformat(),
            'manuscripts': []
        }
        
        try:
            # Login
            if self.journal_name == "MF":
                self.journal = MFJournal(self.driver, debug=True)
                category = "Awaiting Reviewer Scores"
            else:
                self.journal = MORJournal(self.driver, debug=True)
                category = "Awaiting Reviewer Reports"
                
            # Navigate to journal
            journal_url = f"https://mc.manuscriptcentral.com/{self.journal_name.lower()}"
            self.driver.get(journal_url)
            time.sleep(3)
            
            # Handle cookie banner
            try:
                cookie_button = self.driver.find_element(By.ID, "onetrust-accept-btn-handler")
                if cookie_button.is_displayed():
                    cookie_button.click()
                    time.sleep(1)
            except:
                pass
                
            self.journal.login()
            
            # Navigate to AE Center
            ae_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            time.sleep(3)
            
            # Navigate to category
            logger.info(f"\n📂 Navigating to: {category}")
            category_link = self.driver.find_element(By.LINK_TEXT, category)
            category_link.click()
            time.sleep(3)
            self.take_screenshot("01_manuscript_list")
            
            # Find all checkboxes
            logger.info("\n🔍 Finding checkboxes...")
            checkboxes = self.driver.find_elements(By.XPATH, "//input[@type='checkbox']")
            logger.info(f"Found {len(checkboxes)} checkboxes")
            
            # First, uncheck all checkboxes
            logger.info("\n📦 Unchecking all checkboxes first...")
            for i, checkbox in enumerate(checkboxes):
                if checkbox.is_selected():
                    checkbox.click()
                    time.sleep(0.2)
                    
            self.take_screenshot("02_all_unchecked")
            
            # Now click first checkbox
            logger.info("\n✅ Clicking first checkbox...")
            if checkboxes:
                checkboxes[0].click()
                time.sleep(1)
                self.take_screenshot("03_first_checkbox_clicked")
                
                # Look for any changes on the page
                self.look_for_action_elements("after clicking first checkbox")
                
                # Try clicking a second checkbox
                if len(checkboxes) > 1:
                    logger.info("\n✅ Clicking second checkbox...")
                    checkboxes[1].click()
                    time.sleep(1)
                    self.take_screenshot("04_two_checkboxes_clicked")
                    
                    # Look for changes again
                    self.look_for_action_elements("after clicking two checkboxes")
                    
                # Try different combinations
                logger.info("\n🔄 Trying to find action by scrolling...")
                
                # Scroll to top
                self.driver.execute_script("window.scrollTo(0, 0)")
                time.sleep(1)
                self.take_screenshot("05_scrolled_top_with_checkboxes")
                self.look_for_action_elements("at top of page")
                
                # Scroll to bottom
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)
                self.take_screenshot("06_scrolled_bottom_with_checkboxes")
                self.look_for_action_elements("at bottom of page")
                
                # Try pressing Enter
                logger.info("\n⌨️ Trying keyboard shortcuts...")
                body = self.driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.ENTER)
                time.sleep(1)
                self.take_screenshot("07_after_enter_key")
                
                # Try Tab navigation to find hidden elements
                logger.info("\n🔄 Tab navigation to find action elements...")
                for i in range(20):
                    body.send_keys(Keys.TAB)
                    time.sleep(0.1)
                    
                    # Check active element
                    active_element = self.driver.switch_to.active_element
                    try:
                        tag = active_element.tag_name
                        text = active_element.text or active_element.get_attribute('value') or ''
                        
                        if text and any(keyword in text.lower() for keyword in ['action', 'submit', 'go', 'referee']):
                            logger.info(f"✅ Found via Tab: {tag} - '{text}'")
                            self.take_screenshot(f"08_found_element_{i}")
                            
                            # Try clicking it
                            active_element.click()
                            time.sleep(2)
                            self.take_screenshot("09_after_clicking_action")
                            
                            # Check if we navigated somewhere
                            current_url = self.driver.current_url
                            logger.info(f"Current URL: {current_url}")
                            
                            break
                    except:
                        pass
                        
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            self.take_screenshot("error")
            
        finally:
            self.driver.quit()
            
    def look_for_action_elements(self, context):
        """Look for action elements that might have appeared"""
        logger.info(f"\n🔍 Looking for action elements {context}...")
        
        # Look for buttons
        buttons = self.driver.find_elements(By.TAG_NAME, "button")
        visible_buttons = [btn for btn in buttons if btn.is_displayed()]
        
        if visible_buttons:
            logger.info(f"Found {len(visible_buttons)} visible buttons:")
            for btn in visible_buttons[:5]:  # First 5
                text = btn.text.strip()
                if text:
                    logger.info(f"  - Button: '{text}'")
                    
        # Look for submit inputs
        submits = self.driver.find_elements(By.XPATH, "//input[@type='submit' or @type='button']")
        visible_submits = [s for s in submits if s.is_displayed()]
        
        if visible_submits:
            logger.info(f"Found {len(visible_submits)} visible submit/button inputs:")
            for submit in visible_submits[:5]:
                value = submit.get_attribute('value') or ''
                if value:
                    logger.info(f"  - Input: '{value}'")
                    
                    # If it looks like an action button, click it
                    if any(keyword in value.lower() for keyword in ['action', 'submit', 'go', 'continue']):
                        logger.info(f"  ✅ This looks like an action button! Clicking...")
                        submit.click()
                        time.sleep(2)
                        self.take_screenshot("after_clicking_action_button")
                        return True
                        
        # Look for links that might be actions
        links = self.driver.find_elements(By.TAG_NAME, "a")
        action_links = []
        
        for link in links:
            text = link.text.strip()
            if text and any(keyword in text.lower() for keyword in ['action', 'submit', 'referee', 'review details']):
                if link.is_displayed():
                    action_links.append((text, link))
                    
        if action_links:
            logger.info(f"Found {len(action_links)} potential action links:")
            for text, link in action_links[:5]:
                logger.info(f"  - Link: '{text}'")
                
        # Check for any new elements that appeared
        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        if "take action" in page_text.lower():
            logger.info("✅ 'Take Action' text found on page!")
            
        return False


def main():
    # Extract for both journals
    for journal in ["MF", "MOR"]:
        extractor = CheckboxClickExtractor(journal)
        extractor.extract_with_checkbox_clicks()
        time.sleep(5)


if __name__ == "__main__":
    main()