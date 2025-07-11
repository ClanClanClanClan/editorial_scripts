#!/usr/bin/env python3
"""
Debug script to specifically check Xing, Hao's status detection
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
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from journals.mor import MORJournal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DEBUG_XING_HAO")

def debug_xing_hao():
    """Debug Xing, Hao's status detection for MOR-2023-0376.R1"""
    logger.info("🔍 DEBUGGING XING, HAO STATUS DETECTION")
    
    # Create driver
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    
    driver = uc.Chrome(options=options)
    
    try:
        # Navigate and login
        journal = MORJournal(driver, debug=True)
        journal_url = "https://mc.manuscriptcentral.com/mor"
        driver.get(journal_url)
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
        
        # Navigate to Awaiting Reviewer Reports
        category_link = driver.find_element(By.LINK_TEXT, "Awaiting Reviewer Reports")
        category_link.click()
        time.sleep(3)
        
        # Find MOR-2023-0376.R1 specifically
        ms_id = "MOR-2023-0376.R1"
        logger.info(f"🎯 Looking for {ms_id}")
        
        # Find all rows and look for the specific manuscript
        all_rows = driver.find_elements(By.TAG_NAME, "tr")
        
        found_checkbox = None
        for i, row in enumerate(all_rows):
            row_text = row.text
            
            if row_text.strip().startswith(ms_id):
                row_checkboxes = row.find_elements(By.XPATH, ".//img[contains(@src, 'check_off.gif')]")
                
                if len(row_checkboxes) == 1:
                    found_checkbox = row_checkboxes[0]
                    logger.info(f"✅ Found {ms_id} in row {i}")
                    logger.info(f"   Row text: {row_text}")
                    break
        
        if found_checkbox:
            logger.info(f"✅ Clicking checkbox for {ms_id}")
            
            # Scroll and click
            driver.execute_script("arguments[0].scrollIntoView(true);", found_checkbox)
            time.sleep(0.5)
            found_checkbox.click()
            time.sleep(3)
            
            # Extract page content
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Look for Reviewer List section
            reviewer_list_header = soup.find(text=re.compile('Reviewer List', re.IGNORECASE))
            
            if reviewer_list_header:
                logger.info("✅ Found Reviewer List section")
                
                # Find the table
                reviewer_section = reviewer_list_header.find_parent()
                while reviewer_section and reviewer_section.name != 'table':
                    reviewer_section = reviewer_section.find_next('table')
                
                if reviewer_section:
                    rows = reviewer_section.find_all('tr')
                    logger.info(f"📊 Found {len(rows)} rows in reviewer table")
                    
                    for i, row in enumerate(rows[1:], 1):  # Skip header
                        cells = row.find_all('td')
                        logger.info(f"\n🔍 ROW {i}: {len(cells)} cells")
                        
                        # Print all cell contents
                        for j, cell in enumerate(cells):
                            cell_text = cell.get_text(strip=True)
                            logger.info(f"   Cell[{j}]: '{cell_text[:200]}'")
                        
                        # Look for Xing, Hao specifically
                        row_text = row.get_text().lower()
                        if 'xing' in row_text and 'hao' in row_text:
                            logger.info(f"🎯 FOUND XING, HAO IN ROW {i}")
                            
                            # Analyze each cell for status patterns
                            for j, cell in enumerate(cells):
                                cell_text = cell.get_text(strip=True)
                                logger.info(f"   🔍 Cell[{j}] full text: '{cell_text}'")
                                
                                # Check for decision keywords
                                decision_keywords = ['minor revision', 'major revision', 'accept', 'reject', 'revision']
                                for keyword in decision_keywords:
                                    if keyword in cell_text.lower():
                                        logger.info(f"   ✅ FOUND DECISION KEYWORD: '{keyword}' in Cell[{j}]")
                                
                                # Check for review returned date
                                if 'review returned' in cell_text.lower():
                                    logger.info(f"   📅 FOUND REVIEW RETURNED in Cell[{j}]: '{cell_text}'")
                                
                                # Check for specific date pattern
                                date_pattern = r'([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})'
                                dates = re.findall(date_pattern, cell_text)
                                if dates:
                                    logger.info(f"   📅 FOUND DATES in Cell[{j}]: {dates}")
                            
                            break
                    
                else:
                    logger.error("❌ Could not find reviewer table")
            else:
                logger.error("❌ Could not find Reviewer List section")
        else:
            logger.error(f"❌ Could not find checkbox for {ms_id}")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    debug_xing_hao()