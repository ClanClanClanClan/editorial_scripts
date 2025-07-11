#!/usr/bin/env python3
"""
Test Complete Extraction - Focused test for referee and PDF extraction
"""

import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TEST_EXTRACTION")

def test_mf_complete_extraction():
    """Test complete MF extraction focused on working functionality"""
    logger.info("🧪 Testing complete MF referee extraction")
    
    # Create simple driver
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(5)
        driver.set_page_load_timeout(30)
        
        # Step 1: Navigate and login
        logger.info("🌐 Navigating to MF...")
        driver.get("https://mc.manuscriptcentral.com/mafi")
        time.sleep(3)
        
        # Handle cookies
        try:
            cookie_btn = driver.find_element(By.ID, "onetrust-accept-btn-handler")
            cookie_btn.click()
            logger.info("✅ Cookies accepted")
            time.sleep(2)
        except:
            pass
        
        # Login if needed
        try:
            username_input = driver.find_element(By.ID, "USERID")
            password_input = driver.find_element(By.ID, "PASSWORD")
            
            username = os.getenv('MF_USER')
            password = os.getenv('MF_PASS')
            
            username_input.send_keys(username)
            password_input.send_keys(password)
            
            login_btn = driver.find_element(By.ID, "logInButton")
            login_btn.click()
            logger.info("📤 Login submitted")
            time.sleep(4)
            
            # Handle verification if needed
            try:
                verification_input = WebDriverWait(driver, 10).until(
                    lambda d: d.find_element(By.ID, "TOKEN_VALUE") if d.find_element(By.ID, "TOKEN_VALUE").is_displayed() else None
                )
                
                if verification_input:
                    # Get verification code
                    sys.path.insert(0, str(Path(__file__).parent))
                    from core.email_utils import fetch_latest_verification_code
                    
                    time.sleep(5)
                    code = fetch_latest_verification_code(journal="MF")
                    
                    if code:
                        verification_input.send_keys(code)
                        verification_input.send_keys(Keys.RETURN)
                        logger.info(f"✅ Verification code submitted: {code}")
                        time.sleep(3)
            except:
                logger.info("ℹ️  No verification needed")
                
        except:
            logger.info("ℹ️  No login form or already logged in")
        
        # Step 2: Navigate to Associate Editor Center
        logger.info("🔍 Looking for Associate Editor Center...")
        ae_link = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
        )
        ae_link.click()
        logger.info("✅ Clicked Associate Editor Center")
        time.sleep(3)
        
        # Step 3: Navigate to category
        logger.info("🔍 Looking for Awaiting Reviewer Scores...")
        category_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Awaiting Reviewer Scores"))
        )
        category_link.click()
        logger.info("✅ Navigated to Awaiting Reviewer Scores")
        time.sleep(3)
        
        # Step 4: Find manuscript checkbox
        target_manuscript = "MAFI-2024-0167"
        logger.info(f"🔍 Looking for manuscript: {target_manuscript}")
        
        # Take screenshot for debugging
        driver.save_screenshot("test_category_page.png")
        logger.info("📸 Screenshot saved: test_category_page.png")
        
        # Look for checkboxes
        checkboxes = driver.find_elements(By.XPATH, "//img[contains(@src, 'check_off.gif')]")
        logger.info(f"Found {len(checkboxes)} checkbox images")
        
        # Get all table rows
        rows = driver.find_elements(By.TAG_NAME, "tr")
        logger.info(f"Found {len(rows)} table rows")
        
        found_manuscript = False
        for i, row in enumerate(rows[:50]):  # Check first 50 rows
            try:
                row_text = row.text.strip()
                if target_manuscript in row_text:
                    logger.info(f"Row {i}: {row_text[:100]}...")
                    
                    if row_text.startswith(target_manuscript):
                        row_checkboxes = row.find_elements(By.XPATH, ".//img[contains(@src, 'check_off.gif')]")
                        if len(row_checkboxes) == 1:
                            logger.info(f"✅ Found {target_manuscript} with 1 checkbox in row {i}")
                            
                            # Click the checkbox
                            checkbox = row_checkboxes[0]
                            driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                            time.sleep(0.5)
                            checkbox.click()
                            time.sleep(3)
                            
                            logger.info(f"✅ Clicked checkbox for {target_manuscript}")
                            found_manuscript = True
                            break
                        else:
                            logger.info(f"   Row has {len(row_checkboxes)} checkboxes, skipping")
            except:
                continue
        
        if not found_manuscript:
            logger.error(f"❌ Could not find manuscript {target_manuscript}")
            return False
        
        # Step 5: Extract referee data from manuscript page
        logger.info("📊 Extracting referee data...")
        driver.save_screenshot("test_manuscript_page.png")
        logger.info("📸 Screenshot saved: test_manuscript_page.png")
        
        # Get page source and look for referee information
        page_source = driver.page_source
        
        # Save page source for analysis
        with open("test_manuscript_source.html", "w", encoding="utf-8") as f:
            f.write(page_source)
        logger.info("📄 Page source saved: test_manuscript_source.html")
        
        # Look for basic patterns
        title_found = "competitive optimal portfolio" in page_source.lower()
        reviewer_list_found = "reviewer list" in page_source.lower()
        referees_found = "mastrolia" in page_source.lower() or "hamadene" in page_source.lower()
        
        logger.info(f"✅ Title pattern found: {title_found}")
        logger.info(f"✅ Reviewer list found: {reviewer_list_found}")
        logger.info(f"✅ Expected referees found: {referees_found}")
        
        # Look for PDF download links
        pdf_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf') or contains(text(), 'PDF') or contains(text(), 'Download')]")
        logger.info(f"Found {len(pdf_links)} potential PDF download links")
        
        for i, link in enumerate(pdf_links[:5]):  # Check first 5 links
            try:
                href = link.get_attribute('href')
                text = link.text.strip()
                logger.info(f"   PDF Link {i+1}: '{text}' -> {href}")
            except:
                continue
        
        # Test results
        extraction_success = title_found and reviewer_list_found and referees_found
        
        logger.info(f"🎯 Extraction test result: {'SUCCESS' if extraction_success else 'PARTIAL'}")
        
        return extraction_success
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False
        
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("🔄 Driver closed")
            except:
                pass

if __name__ == "__main__":
    success = test_mf_complete_extraction()
    if success:
        print("✅ Complete extraction test PASSED!")
        sys.exit(0)
    else:
        print("❌ Complete extraction test FAILED!")
        sys.exit(1)