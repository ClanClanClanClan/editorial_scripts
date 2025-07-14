#!/usr/bin/env python3
"""
Custom Checkbox Handler - Handle ScholarOne's custom checkbox implementation
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
logger = logging.getLogger("CUSTOM_CHECKBOX")


class CustomCheckboxHandler:
    def __init__(self):
        self.driver = None
        self.journal = None
        self.output_dir = Path("custom_checkbox_results")
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
        
    def handle_custom_checkboxes(self):
        """Handle custom checkbox implementation"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🎯 CUSTOM CHECKBOX HANDLER")
        logger.info(f"{'='*80}")
        
        self.create_driver()
        
        try:
            # Login to MF
            self.journal = MFJournal(self.driver, debug=True)
            
            # Navigate to journal
            logger.info("Navigating to MF...")
            self.driver.get("https://mc.manuscriptcentral.com/mafi")
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
            category = "Awaiting Reviewer Scores"
            logger.info(f"\n📂 Navigating to: {category}")
            category_link = self.driver.find_element(By.LINK_TEXT, category)
            category_link.click()
            time.sleep(3)
            self.take_screenshot("01_manuscript_list")
            
            # Find checkboxes in the Take Action column
            logger.info("\n🔍 Finding checkbox elements in Take Action column...")
            
            # Method 1: Find by the last cell in each row
            rows = self.driver.find_elements(By.XPATH, "//tr[contains(., 'MAFI-')]")
            logger.info(f"Found {len(rows)} manuscript rows")
            
            checkbox_elements = []
            
            for i, row in enumerate(rows):
                cells = row.find_elements(By.TAG_NAME, "td")
                if cells:
                    # Last cell should be Take Action
                    take_action_cell = cells[-1]
                    
                    # Find clickable elements in this cell
                    # Could be input, img, or a wrapped in a link
                    clickables = take_action_cell.find_elements(By.XPATH, ".//*[@onclick or contains(@class, 'checkbox') or @type='checkbox']")
                    
                    if clickables:
                        logger.info(f"Row {i+1}: Found {len(clickables)} clickable elements in Take Action cell")
                        checkbox_elements.extend(clickables)
                    else:
                        # Try clicking the cell itself
                        logger.info(f"Row {i+1}: No explicit clickables, will try clicking the cell")
                        checkbox_elements.append(take_action_cell)
                        
            # Try clicking the checkbox elements
            if checkbox_elements:
                logger.info(f"\n✅ Attempting to click {len(checkbox_elements)} checkbox elements...")
                
                for i, elem in enumerate(checkbox_elements[:2]):  # Try first two
                    try:
                        logger.info(f"\nClicking element {i+1}...")
                        
                        # Scroll element into view
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                        time.sleep(0.5)
                        
                        # Try different click methods
                        try:
                            elem.click()
                            logger.info("  ✓ Regular click successful")
                        except:
                            # Try JavaScript click
                            self.driver.execute_script("arguments[0].click();", elem)
                            logger.info("  ✓ JavaScript click successful")
                            
                        time.sleep(1)
                        self.take_screenshot(f"02_after_click_{i+1}")
                        
                        # Look for changes
                        self.look_for_changes()
                        
                    except Exception as e:
                        logger.error(f"  ✗ Failed to click element {i+1}: {e}")
                        
            # Method 2: Look for image checkboxes
            logger.info("\n🔍 Looking for image-based checkboxes...")
            images = self.driver.find_elements(By.TAG_NAME, "img")
            checkbox_images = []
            
            for img in images:
                src = img.get_attribute('src') or ''
                alt = img.get_attribute('alt') or ''
                onclick = img.get_attribute('onclick') or ''
                
                if any(keyword in src.lower() + alt.lower() for keyword in ['check', 'box', 'select']):
                    checkbox_images.append(img)
                    logger.info(f"Found checkbox image: src='{src[-50:]}'")
                    
            if checkbox_images:
                logger.info(f"\n✅ Clicking checkbox images...")
                for i, img in enumerate(checkbox_images[:2]):
                    try:
                        img.click()
                        time.sleep(1)
                        self.take_screenshot(f"03_after_image_click_{i+1}")
                        self.look_for_changes()
                    except:
                        pass
                        
            # Method 3: Try form submission
            logger.info("\n📋 Looking for form submission options...")
            forms = self.driver.find_elements(By.TAG_NAME, "form")
            
            if forms:
                form = forms[0]
                
                # Look for action parameter in form
                action = form.get_attribute('action') or ''
                logger.info(f"Form action: {action}")
                
                # Try to submit the form
                try:
                    logger.info("Attempting form submission...")
                    form.submit()
                    time.sleep(3)
                    self.take_screenshot("04_after_form_submit")
                    
                    # Check if we navigated
                    current_url = self.driver.current_url
                    logger.info(f"Current URL: {current_url}")
                    
                except Exception as e:
                    logger.error(f"Form submission failed: {e}")
                    
            # Final attempt: Look for any action buttons/links after manipulating checkboxes
            logger.info("\n🔍 Final search for action elements...")
            self.comprehensive_action_search()
            
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
            
    def look_for_changes(self):
        """Look for any changes after clicking"""
        # Check for new buttons
        buttons = self.driver.find_elements(By.TAG_NAME, "button")
        visible_buttons = [b for b in buttons if b.is_displayed() and b.text.strip()]
        
        if visible_buttons:
            logger.info("  New visible buttons found:")
            for btn in visible_buttons:
                logger.info(f"    - '{btn.text}'")
                
        # Check for new submit inputs
        submits = self.driver.find_elements(By.XPATH, "//input[@type='submit' and @value]")
        visible_submits = [s for s in submits if s.is_displayed()]
        
        if visible_submits:
            logger.info("  New submit buttons found:")
            for submit in visible_submits:
                value = submit.get_attribute('value')
                logger.info(f"    - '{value}'")
                
                if 'action' in value.lower():
                    logger.info("    ✅ This looks like the Take Action button!")
                    submit.click()
                    time.sleep(2)
                    self.take_screenshot("found_take_action")
                    return True
                    
        return False
        
    def comprehensive_action_search(self):
        """Comprehensive search for action elements"""
        # Get all text on page
        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        
        # Look for action-related text
        action_keywords = ['take action', 'submit', 'go', 'continue', 'proceed']
        
        for keyword in action_keywords:
            if keyword in page_text.lower():
                logger.info(f"✅ Found '{keyword}' in page text")
                
                # Try to find the element containing this text
                elements = self.driver.find_elements(By.XPATH, f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')]")
                
                for elem in elements:
                    if elem.is_displayed() and elem.tag_name in ['button', 'input', 'a']:
                        logger.info(f"  Found actionable element: {elem.tag_name} - '{elem.text or elem.get_attribute('value')}'")
                        
                        try:
                            elem.click()
                            time.sleep(2)
                            self.take_screenshot("clicked_action_element")
                            return True
                        except:
                            pass
                            
        return False


def main():
    handler = CustomCheckboxHandler()
    handler.handle_custom_checkboxes()


if __name__ == "__main__":
    main()