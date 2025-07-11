#!/usr/bin/env python3
"""
Debug script to understand the Take Action structure on MF/MOR pages
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

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from journals.mf import MFJournal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TAKE_ACTION_DEBUG")

def debug_take_action_structure():
    """Debug the Take Action page structure"""
    
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
        
        # Analyze the page structure
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        logger.info("=== PAGE STRUCTURE ANALYSIS ===")
        
        # Look for all checkboxes
        checkboxes = driver.find_elements(By.XPATH, "//input[@type='checkbox']")
        logger.info(f"Found {len(checkboxes)} checkboxes")
        
        # Look for Take Action buttons
        take_action_buttons = driver.find_elements(By.XPATH, "//input[@value='Take Action']")
        logger.info(f"Found {len(take_action_buttons)} 'Take Action' buttons")
        
        # Look for forms
        forms = driver.find_elements(By.TAG_NAME, "form")
        logger.info(f"Found {len(forms)} forms")
        
        # Analyze table structure
        tables = soup.find_all('table')
        logger.info(f"Found {len(tables)} tables")
        
        for i, table in enumerate(tables):
            rows = table.find_all('tr')
            logger.info(f"Table {i}: {len(rows)} rows")
            
            # Look for headers
            headers = table.find_all('th')
            if headers:
                header_texts = [h.get_text(strip=True) for h in headers]
                logger.info(f"  Headers: {header_texts}")
                
        # Look for manuscript IDs and their context
        import re
        ms_ids = re.findall(r'MAFI-\d{4}-\d+', driver.page_source)
        logger.info(f"Manuscript IDs found: {set(ms_ids)}")
        
        # Look for the specific structure around manuscripts
        for ms_id in set(ms_ids):
            logger.info(f"\n=== ANALYZING {ms_id} ===")
            
            # Find elements containing this manuscript ID
            elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{ms_id}')]")
            logger.info(f"Found {len(elements)} elements containing {ms_id}")
            
            for j, elem in enumerate(elements):
                try:
                    # Get the parent row
                    parent_row = elem.find_element(By.XPATH, "ancestor::tr[1]")
                    
                    # Look for checkboxes in this row
                    row_checkboxes = parent_row.find_elements(By.XPATH, ".//input[@type='checkbox']")
                    logger.info(f"  Row {j}: {len(row_checkboxes)} checkboxes")
                    
                    # Look for buttons in this row
                    row_buttons = parent_row.find_elements(By.XPATH, ".//input[@type='button'] | .//input[@type='submit'] | .//button")
                    logger.info(f"  Row {j}: {len(row_buttons)} buttons")
                    
                    # Get all cells in this row
                    cells = parent_row.find_elements(By.TAG_NAME, "td")
                    logger.info(f"  Row {j}: {len(cells)} cells")
                    
                    # Check the last cell (likely where Take Action checkbox is)
                    if cells:
                        last_cell = cells[-1]
                        last_cell_checkboxes = last_cell.find_elements(By.XPATH, ".//input[@type='checkbox']")
                        logger.info(f"  Last cell: {len(last_cell_checkboxes)} checkboxes")
                        
                        if last_cell_checkboxes:
                            logger.info(f"  ✅ Found checkbox in last cell for {ms_id}")
                            
                            # Try to click it
                            try:
                                last_cell_checkboxes[0].click()
                                logger.info(f"  ✅ Successfully clicked checkbox for {ms_id}")
                                
                                # Look for Take Action button
                                take_action_btns = driver.find_elements(By.XPATH, "//input[@value='Take Action']")
                                if take_action_btns:
                                    logger.info(f"  ✅ Found Take Action button, clicking...")
                                    take_action_btns[0].click()
                                    time.sleep(3)
                                    
                                    # Check what page we're on
                                    if ms_id in driver.page_source:
                                        logger.info(f"  ✅ Successfully navigated to {ms_id} details page")
                                        
                                        # Look for referee information
                                        soup2 = BeautifulSoup(driver.page_source, 'html.parser')
                                        
                                        # Look for referee names (clickable links)
                                        referee_links = []
                                        for link in soup2.find_all('a'):
                                            link_text = link.get_text(strip=True)
                                            if (' ' in link_text and 
                                                any(c.isupper() for c in link_text) and
                                                len(link_text) > 3 and
                                                not any(word in link_text.lower() for word in ['view', 'download', 'edit', 'manuscript', 'center'])):
                                                referee_links.append(link_text)
                                                
                                        logger.info(f"  Potential referee names: {referee_links}")
                                        
                                        # Look for history information
                                        history_patterns = ['Invited:', 'Agreed:', 'Due Date:', 'Time in Review:']
                                        for pattern in history_patterns:
                                            if pattern in driver.page_source:
                                                logger.info(f"  Found history pattern: {pattern}")
                                                
                                    else:
                                        logger.warning(f"  Did not find {ms_id} on details page")
                                        
                                    return  # Exit after first successful test
                                    
                            except Exception as e:
                                logger.error(f"  Error clicking checkbox: {e}")
                                
                except Exception as e:
                    logger.debug(f"  Error analyzing element {j}: {e}")
                    
    finally:
        driver.quit()

if __name__ == "__main__":
    debug_take_action_structure()