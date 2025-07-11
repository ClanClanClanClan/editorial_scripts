#!/usr/bin/env python3
"""
Detailed inspection of checkbox structure
"""

import os
import sys
import time
import logging
from pathlib import Path
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from journals.mf import MFJournal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CHECKBOX_STRUCTURE_INSPECT")

def inspect_checkbox_structure():
    """Inspect the detailed structure of checkboxes"""
    
    # Create driver
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    try:
        driver = uc.Chrome(options=options)
    except:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        chrome_options = Options()
        for arg in options.arguments:
            chrome_options.add_argument(arg)
        driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Login to MF
        journal = MFJournal(driver, debug=True)
        journal.login()
        
        # Navigate to AE Center
        ae_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
        )
        ae_link.click()
        time.sleep(3)
        
        # Click on Awaiting Reviewer Scores
        category_link = driver.find_element(By.LINK_TEXT, "Awaiting Reviewer Scores")
        category_link.click()
        time.sleep(3)
        
        # Save HTML for inspection
        with open("checkbox_page.html", "w", encoding='utf-8') as f:
            f.write(driver.page_source)
        
        # Find all checkboxes on the page
        all_checkboxes = driver.find_elements(By.XPATH, "//input[@type='checkbox']")
        logger.info(f"Found {len(all_checkboxes)} total checkboxes on page")
        
        # Inspect each checkbox
        for i, checkbox in enumerate(all_checkboxes):
            try:
                # Get checkbox attributes
                checkbox_id = checkbox.get_attribute('id')
                checkbox_name = checkbox.get_attribute('name')
                checkbox_value = checkbox.get_attribute('value')
                is_checked = checkbox.is_selected()
                
                logger.info(f"Checkbox {i}:")
                logger.info(f"  ID: {checkbox_id}")
                logger.info(f"  Name: {checkbox_name}")
                logger.info(f"  Value: {checkbox_value}")
                logger.info(f"  Checked: {is_checked}")
                
                # Get parent context
                parent = checkbox.find_element(By.XPATH, "..")
                parent_text = parent.text.strip()
                if parent_text:
                    logger.info(f"  Parent text: {parent_text[:100]}...")
                
                # Get row context if in a table
                try:
                    row = checkbox.find_element(By.XPATH, "ancestor::tr[1]")
                    row_text = row.text.strip()
                    if 'MAFI-' in row_text:
                        logger.info(f"  ✅ In manuscript row: {row_text[:200]}...")
                        
                        # Check if this is a Take Action checkbox
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if cells:
                            logger.info(f"  Row has {len(cells)} cells")
                            for j, cell in enumerate(cells):
                                cell_text = cell.text.strip()
                                if 'Take Action' in cell_text or checkbox in cell.find_elements(By.XPATH, ".//input[@type='checkbox']"):
                                    logger.info(f"    Cell {j}: {cell_text} (contains checkbox: {checkbox in cell.find_elements(By.XPATH, './/input[@type=\"checkbox\"]')})")
                                    
                except:
                    pass
                
                logger.info("")
                
            except Exception as e:
                logger.error(f"Error inspecting checkbox {i}: {e}")
                
    finally:
        driver.quit()

if __name__ == "__main__":
    inspect_checkbox_structure()