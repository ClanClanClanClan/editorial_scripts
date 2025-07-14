#!/usr/bin/env python3
"""
Quick script to explore MOR categories and find manuscripts with completed reviews
"""

import os
import sys
import time
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MOR_EXPLORER")

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

def login_mor(driver):
    """Login to MOR"""
    logger.info("🔐 Logging into MOR...")
    
    try:
        driver.get("https://mc.manuscriptcentral.com/mathor")
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
        user = os.environ.get("MOR_USER") or os.environ.get("MF_USER")
        pw = os.environ.get("MOR_PASS") or os.environ.get("MF_PASS")
        if not user or not pw:
            raise RuntimeError("MOR_USER/MOR_PASS or MF_USER/MF_PASS environment variables must be set.")
        
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
                logger.info("Verification needed - using MOR email verification...")
                sys.path.insert(0, str(Path(__file__).parent))
                from core.email_utils import fetch_latest_verification_code
                
                time.sleep(5)
                verification_code = fetch_latest_verification_code(journal="MOR")
                
                if verification_code:
                    code_input.clear()
                    code_input.send_keys(verification_code)
                    code_input.send_keys(Keys.RETURN)
                    time.sleep(3)
                    logger.info("Submitted verification code.")
        except TimeoutException:
            pass
        
        logger.info("✅ Login completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Login failed: {e}")
        return False

def explore_categories(driver):
    """Explore all available categories"""
    logger.info("🔍 Exploring MOR categories...")
    
    try:
        # Navigate to Associate Editor Center
        ae_link = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
        )
        ae_link.click()
        time.sleep(3)
        logger.info("✅ Navigated to Associate Editor Center")
        
        # Find all category links
        category_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'CENTER=A') or contains(text(), 'Awaiting')]")
        
        logger.info("📋 Available categories:")
        categories = []
        for link in category_links:
            try:
                text = link.text.strip()
                href = link.get_attribute('href')
                if text and len(text) > 5:  # Filter out short/empty text
                    categories.append((text, href))
                    logger.info(f"   • {text}")
            except:
                continue
        
        # Test each category to see manuscript counts
        for i, (category_name, category_href) in enumerate(categories):
            if i >= 5:  # Limit to first 5 categories
                break
                
            logger.info(f"\n🔍 Testing category: {category_name}")
            try:
                driver.get(category_href)
                time.sleep(3)
                
                # Count manuscripts
                rows = driver.find_elements(By.TAG_NAME, "tr")
                manuscript_count = 0
                view_review_count = 0
                
                for row in rows:
                    try:
                        row_text = row.text.strip()
                        if 'MOR-' in row_text or 'MATHOR-' in row_text:
                            manuscript_count += 1
                            # Check for view review links in this row
                            review_links = row.find_elements(By.XPATH, ".//a[contains(text(), 'view review')]")
                            view_review_count += len(review_links)
                    except:
                        continue
                
                logger.info(f"   📄 {manuscript_count} manuscripts, {view_review_count} 'view review' links")
                
                # If we found manuscripts with review links, this is promising
                if view_review_count > 0:
                    logger.info(f"   🎯 PROMISING CATEGORY: {category_name} has {view_review_count} review links!")
                    
                    # Show some sample manuscripts from this category
                    sample_manuscripts = []
                    for row in rows[:10]:  # Check first 10 rows
                        try:
                            row_text = row.text.strip()
                            if 'MOR-' in row_text or 'MATHOR-' in row_text:
                                # Extract manuscript ID
                                import re
                                id_match = re.search(r'(MOR-\d{4}-\d{4}|MATHOR-\d{4}-\d{4})', row_text)
                                if id_match:
                                    manuscript_id = id_match.group(1)
                                    review_links = row.find_elements(By.XPATH, ".//a[contains(text(), 'view review')]")
                                    if review_links:
                                        sample_manuscripts.append(f"{manuscript_id} (has review link)")
                                    else:
                                        sample_manuscripts.append(manuscript_id)
                        except:
                            continue
                    
                    if sample_manuscripts:
                        logger.info(f"   📋 Sample manuscripts:")
                        for ms in sample_manuscripts[:5]:
                            logger.info(f"      - {ms}")
                
            except Exception as e:
                logger.warning(f"   ❌ Error testing category {category_name}: {e}")
                continue
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error exploring categories: {e}")
        return False

def main():
    """Main exploration function"""
    driver = create_driver()
    if not driver:
        return
    
    try:
        if login_mor(driver):
            explore_categories(driver)
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()