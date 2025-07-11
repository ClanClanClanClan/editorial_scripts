#!/usr/bin/env python3
"""
Quick test to verify MF checkbox detection
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
logger = logging.getLogger("MF_CHECKBOX_TEST")

def test_mf_checkboxes():
    """Test finding MF checkboxes"""
    
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
        
        # Find manuscripts
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        ms_ids = list(set(re.findall(r'MAFI-\d{4}-\d+', soup.get_text())))
        logger.info(f"Found manuscripts: {ms_ids}")
        
        # Test checkbox detection
        manuscript_actions = []
        
        # Find all table rows with checkboxes
        table_rows = driver.find_elements(By.XPATH, "//table//tr[td]")
        logger.info(f"Found {len(table_rows)} table rows")
        
        for i, row in enumerate(table_rows):
            try:
                row_text = row.text
                # Check if this row contains a manuscript ID
                found_ms_id = None
                for ms_id in ms_ids:
                    if ms_id in row_text:
                        found_ms_id = ms_id
                        break
                        
                if found_ms_id:
                    logger.info(f"Row {i} contains manuscript {found_ms_id}")
                    # Look for checkbox in this row
                    checkboxes = row.find_elements(By.XPATH, ".//input[@type='checkbox']")
                    logger.info(f"  Found {len(checkboxes)} checkboxes in this row")
                    
                    if checkboxes:
                        manuscript_actions.append({
                            'manuscript_id': found_ms_id,
                            'checkbox': checkboxes[0]
                        })
                        logger.info(f"  ✅ Found Take Action checkbox for {found_ms_id}")
                        
            except Exception as e:
                logger.debug(f"Error checking row {i}: {e}")
                continue
                
        logger.info(f"\\nFINAL RESULT: Found {len(manuscript_actions)} manuscripts with checkboxes")
        for action in manuscript_actions:
            logger.info(f"  • {action['manuscript_id']}: checkbox ready")
            
    finally:
        driver.quit()

if __name__ == "__main__":
    test_mf_checkboxes()