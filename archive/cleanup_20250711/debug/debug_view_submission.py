#!/usr/bin/env python3
"""
Debug View Submission - Find where View Submission links are
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

from journals.mor import MORJournal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DEBUG_VIEW_SUBMISSION")


def debug_view_submission():
    """Debug where View Submission links are"""
    logger.info("🔍 DEBUGGING VIEW SUBMISSION LINKS")
    
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    driver = uc.Chrome(options=options)
    journal = MORJournal(driver, debug=True)
    
    try:
        # Login
        journal.login()
        
        # Navigate to AE Center
        ae_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
        )
        ae_link.click()
        time.sleep(2)
        
        # Navigate to category
        category_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Awaiting Reviewer Reports"))
        )
        category_link.click()
        time.sleep(3)
        
        # Take screenshot
        driver.save_screenshot("awaiting_reviewer_reports.png")
        logger.info("📸 Screenshot saved: awaiting_reviewer_reports.png")
        
        # Look for all links on the page
        logger.info("\n🔍 All links on the page:")
        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            text = link.text.strip()
            href = link.get_attribute("href") or ""
            if text and len(text) > 2:
                logger.info(f"   Link: '{text}' -> {href[:50]}...")
                
        # Look for View Submission specifically
        logger.info("\n🔍 Looking for View Submission links:")
        view_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "View")
        for link in view_links:
            logger.info(f"   Found: '{link.text}'")
            
        # Click on first manuscript checkbox to see what's there
        logger.info("\n🔍 Clicking first manuscript checkbox...")
        checkbox = driver.find_element(By.XPATH, "//img[contains(@src, 'check_off.gif')]")
        checkbox.click()
        time.sleep(3)
        
        # Take screenshot of referee page
        driver.save_screenshot("referee_page.png")
        logger.info("📸 Screenshot saved: referee_page.png")
        
        # Look for View Submission on this page
        logger.info("\n🔍 Links on referee page:")
        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            text = link.text.strip()
            if text and "view" in text.lower():
                logger.info(f"   View-related link: '{text}'")
                
        # Check page source for manuscript details
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Look for manuscript link patterns
        logger.info("\n🔍 Looking for manuscript detail links in HTML:")
        manuscript_links = soup.find_all('a', href=re.compile(r'(viewSubmission|viewManuscript|manuscriptDetail)', re.I))
        for link in manuscript_links:
            logger.info(f"   Found: {link.get('href', 'No href')}")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        
    finally:
        input("\n⏸️  Press Enter to close browser...")
        driver.quit()


if __name__ == '__main__':
    debug_view_submission()