#!/usr/bin/env python3
"""
Test script to find and click the count numbers on the MF dashboard.
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
logger = logging.getLogger("COUNT_TEST")

def test_count_clicking():
    """Test finding and clicking count numbers"""
    
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
        
        # Analyze the page structure
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Find all links with numbers
        logger.info("=== All links with numbers ===")
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True)
            if text.isdigit():
                logger.info(f"Found number link: '{text}' -> {link.get('href', '')[:50]}...")
                
        # Try to find the "2" link for Awaiting Reviewer Scores
        logger.info("\n=== Looking for '2' link ===")
        try:
            two_links = driver.find_elements(By.LINK_TEXT, "2")
            logger.info(f"Found {len(two_links)} links with text '2'")
            
            if two_links:
                # Click the first "2" link
                logger.info("Clicking first '2' link...")
                two_links[0].click()
                time.sleep(3)
                
                # Check what page we're on
                logger.info(f"After clicking '2': {driver.current_url}")
                
                # Check if we're on a manuscript detail page
                if "MAFI-" in driver.page_source:
                    logger.info("✅ Successfully navigated to manuscript page!")
                    
                    # Look for manuscript IDs
                    import re
                    ms_ids = re.findall(r'MAFI-\d{4}-\d+', driver.page_source)
                    logger.info(f"Found manuscript IDs: {set(ms_ids)}")
                    
                    # Look for Next button
                    try:
                        next_btn = driver.find_element(By.LINK_TEXT, "Next")
                        logger.info("Found 'Next' button!")
                    except:
                        logger.info("No 'Next' button found")
                else:
                    logger.warning("Did not find manuscript page")
                    
        except Exception as e:
            logger.error(f"Error finding '2' link: {e}")
            
        # Try to find the "1" link for Overdue Manuscripts
        logger.info("\n=== Looking for '1' link ===")
        try:
            # Go back to AE Center first
            ae_link = driver.find_element(By.LINK_TEXT, "Associate Editor Center")
            ae_link.click()
            time.sleep(2)
            
            one_links = driver.find_elements(By.LINK_TEXT, "1")
            logger.info(f"Found {len(one_links)} links with text '1'")
            
            if len(one_links) > 1:
                # Click the second "1" link (first is probably for something else)
                logger.info("Clicking second '1' link...")
                one_links[1].click()
                time.sleep(3)
                
                logger.info(f"After clicking '1': {driver.current_url}")
                
                # Check if we're on a manuscript detail page
                if "MAFI-" in driver.page_source:
                    logger.info("✅ Successfully navigated to manuscript page!")
                    
                    # Look for manuscript IDs
                    ms_ids = re.findall(r'MAFI-\d{4}-\d+', driver.page_source)
                    logger.info(f"Found manuscript IDs: {set(ms_ids)}")
                    
        except Exception as e:
            logger.error(f"Error finding '1' link: {e}")
            
    finally:
        driver.quit()

if __name__ == "__main__":
    test_count_clicking()