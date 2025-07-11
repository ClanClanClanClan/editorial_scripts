#!/usr/bin/env python3
"""
Debug Checkbox Search - Debug why checkboxes aren't being found
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

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from journals.mf import MFJournal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DEBUG_CHECKBOX")


def debug_checkbox_search():
    """Debug checkbox search"""
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
        driver = webdriver.Chrome(options=chrome_options)
        
    try:
        # Login to MF
        journal = MFJournal(driver, debug=True)
        
        # Navigate to journal
        driver.get("https://mc.manuscriptcentral.com/mafi")
        time.sleep(3)
        
        # Handle cookie banner
        try:
            cookie_button = driver.find_element(By.ID, "onetrust-accept-btn-handler")
            if cookie_button.is_displayed():
                cookie_button.click()
                time.sleep(1)
        except:
            pass
            
        journal.login()
        
        # Navigate to AE Center
        ae_link = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
        )
        ae_link.click()
        time.sleep(3)
        
        # Navigate to category
        category_link = driver.find_element(By.LINK_TEXT, "Awaiting Reviewer Scores")
        category_link.click()
        time.sleep(3)
        
        # Debug: Check for checkbox images
        logger.info("\n🔍 Looking for all images on page...")
        images = driver.find_elements(By.TAG_NAME, "img")
        logger.info(f"Found {len(images)} images total")
        
        checkbox_related = []
        for i, img in enumerate(images):
            src = img.get_attribute('src') or ''
            alt = img.get_attribute('alt') or ''
            
            if any(keyword in src.lower() for keyword in ['check', 'box', 'select']):
                checkbox_related.append((i, src, alt))
                logger.info(f"Image {i}: src='{src}', alt='{alt}'")
                
        logger.info(f"Found {len(checkbox_related)} checkbox-related images")
        
        # Debug: Check manuscript rows
        logger.info("\n🔍 Checking manuscript rows...")
        rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MAFI-')]")
        logger.info(f"Found {len(rows)} manuscript rows")
        
        for i, row in enumerate(rows):
            cells = row.find_elements(By.TAG_NAME, "td")
            logger.info(f"\nRow {i+1}: {len(cells)} cells")
            
            if cells:
                # Check last cell (Take Action)
                last_cell = cells[-1]
                cell_text = last_cell.text.strip()[:50]
                logger.info(f"  Last cell text: '{cell_text}...'")
                
                # Find all images in this cell
                cell_images = last_cell.find_elements(By.TAG_NAME, "img")
                logger.info(f"  Images in cell: {len(cell_images)}")
                
                for j, img in enumerate(cell_images):
                    src = img.get_attribute('src') or ''
                    alt = img.get_attribute('alt') or ''
                    logger.info(f"    Image {j+1}: src='{src}', alt='{alt}'")
                    
                # Find ALL elements in this cell
                all_elements = last_cell.find_elements(By.XPATH, ".//*")
                logger.info(f"  All elements in cell: {len(all_elements)}")
                
                for j, elem in enumerate(all_elements[:5]):  # First 5
                    tag = elem.tag_name
                    text = elem.text.strip()[:30] if elem.text else ''
                    onclick = elem.get_attribute('onclick') or ''
                    logger.info(f"    Element {j+1}: {tag} - '{text}' - onclick: '{onclick[:50]}'")
                    
        logger.info("\nPress Enter to close...")
        input()
        
    finally:
        driver.quit()


if __name__ == "__main__":
    debug_checkbox_search()