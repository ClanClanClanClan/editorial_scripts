#!/usr/bin/env python3
"""
Debug script to find all links on manuscript detail page
"""

import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import exact same driver approach
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DEBUG_PDF_LINKS")

def create_driver():
    """Create Chrome driver"""
    try:
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        driver = uc.Chrome(options=options, version_main=None)
        return driver
    except Exception as e:
        logger.error(f"Driver creation failed: {e}")
        return None

def login_mf(driver):
    """Login to MF"""
    logger.info("🔐 Logging into MF...")
    
    try:
        driver.get("https://mc.manuscriptcentral.com/mafi")
        time.sleep(2)
        
        # Handle cookies
        try:
            accept_btn = driver.find_element(By.ID, "onetrust-accept-btn-handler")
            if accept_btn.is_displayed():
                accept_btn.click()
                logger.info("Accepted cookies.")
                time.sleep(1)
        except Exception:
            pass
        
        # Get credentials
        user = os.environ.get("MF_USER")
        pw = os.environ.get("MF_PASS")
        if not user or not pw:
            raise RuntimeError("MF_USER and MF_PASS environment variables must be set.")
        
        # Fill login form
        user_box = driver.find_element(By.ID, "USERID")
        pw_box = driver.find_element(By.ID, "PASSWORD")
        user_box.clear()
        user_box.send_keys(user)
        pw_box.clear()
        pw_box.send_keys(pw)
        
        # Submit login
        login_btn = driver.find_element(By.ID, "logInButton")
        login_btn.click()
        time.sleep(4)
        
        # Handle verification if needed
        wait = WebDriverWait(driver, 15)
        try:
            code_input = wait.until(
                lambda d: d.find_element(By.ID, "TOKEN_VALUE") if d.find_element(By.ID, "TOKEN_VALUE").is_displayed() else None
            )
            if code_input:
                logger.info("Verification needed - waiting...")
                sys.path.insert(0, str(Path(__file__).parent))
                from core.email_utils import fetch_latest_verification_code
                
                time.sleep(5)
                verification_code = fetch_latest_verification_code(journal="MF")
                
                if verification_code:
                    code_input.clear()
                    code_input.send_keys(verification_code)
                    code_input.send_keys(Keys.RETURN)
                    time.sleep(3)
        except TimeoutException:
            pass
        
        logger.info("✅ Login completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Login failed: {e}")
        return False

def debug_manuscript_page(driver, manuscript_id="MAFI-2024-0167"):
    """Debug what links are available on manuscript page"""
    logger.info(f"🔍 Debugging links for {manuscript_id}")
    
    try:
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
        
        # Find and click manuscript checkbox
        checkboxes = driver.find_elements(By.XPATH, "//img[contains(@src, 'check_off.gif')]")
        rows = driver.find_elements(By.TAG_NAME, "tr")
        
        for i, row in enumerate(rows):
            try:
                row_text = row.text.strip()
                if row_text.startswith(manuscript_id):
                    row_checkboxes = row.find_elements(By.XPATH, ".//img[contains(@src, 'check_off.gif')]")
                    if len(row_checkboxes) == 1:
                        logger.info(f"✅ Found {manuscript_id}, clicking...")
                        checkbox = row_checkboxes[0]
                        driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                        time.sleep(0.5)
                        checkbox.click()
                        time.sleep(3)
                        break
            except:
                continue
        
        # Now we're on the manuscript detail page - let's find ALL links
        logger.info("🔍 ANALYZING ALL LINKS ON MANUSCRIPT DETAIL PAGE:")
        
        all_links = driver.find_elements(By.TAG_NAME, "a")
        logger.info(f"Found {len(all_links)} total links")
        
        # Categorize links
        submission_related = []
        review_related = []
        pdf_related = []
        other_links = []
        
        for i, link in enumerate(all_links):
            try:
                href = link.get_attribute('href') or ''
                text = link.text.strip().lower()
                title = link.get_attribute('title') or ''
                
                # Skip empty links
                if not text and not title:
                    continue
                
                # Categorize
                if any(word in text for word in ['submission', 'submit', 'manuscript']):
                    submission_related.append((text, href, title))
                elif any(word in text for word in ['review', 'report', 'referee']):
                    review_related.append((text, href, title))
                elif any(word in text for word in ['pdf', 'download', 'file', 'attachment']):
                    pdf_related.append((text, href, title))
                elif text:  # Only include links with text
                    other_links.append((text, href, title))
                    
            except Exception as e:
                continue
        
        # Print categorized results
        logger.info("📄 SUBMISSION-RELATED LINKS:")
        for text, href, title in submission_related[:10]:  # Show first 10
            logger.info(f"   '{text}' -> {href} (title: {title})")
        
        logger.info("📝 REVIEW-RELATED LINKS:")
        for text, href, title in review_related[:10]:
            logger.info(f"   '{text}' -> {href} (title: {title})")
        
        logger.info("📥 PDF-RELATED LINKS:")
        for text, href, title in pdf_related[:10]:
            logger.info(f"   '{text}' -> {href} (title: {title})")
        
        logger.info("🔗 OTHER INTERESTING LINKS:")
        for text, href, title in other_links[:20]:  # Show first 20
            if len(text) > 2:  # Skip very short text
                logger.info(f"   '{text}' -> {href} (title: {title})")
        
        # Also look for any clickable elements in table cells
        logger.info("🔍 LOOKING FOR CLICKABLE ELEMENTS IN TABLE CELLS:")
        
        # Find all clickable elements
        clickable_elements = driver.find_elements(By.XPATH, "//td//a | //td//button | //td//input[@type='button']")
        
        for elem in clickable_elements[:20]:  # Show first 20
            try:
                text = elem.text.strip()
                href = elem.get_attribute('href') or elem.get_attribute('onclick') or ''
                tag = elem.tag_name
                if text:
                    logger.info(f"   {tag}: '{text}' -> {href}")
            except:
                continue
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error debugging manuscript page: {e}")
        return False

def main():
    """Main debugging function"""
    driver = create_driver()
    if not driver:
        return
    
    try:
        if login_mf(driver):
            debug_manuscript_page(driver)
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()