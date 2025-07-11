#!/usr/bin/env python3
"""
Targeted MF manuscript finder - focuses on getting to the manuscripts.
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
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import json
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from journals.mf import MFJournal
from core.email_utils import fetch_starred_emails

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MF_FINDER")


def create_driver():
    """Create Chrome driver"""
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    try:
        return uc.Chrome(options=options)
    except Exception as e:
        logger.warning(f"Undetected Chrome failed: {e}")
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        chrome_options = Options()
        for arg in options.arguments:
            chrome_options.add_argument(arg)
        return webdriver.Chrome(options=chrome_options)


def save_page_state(driver, filename):
    """Save current page state for debugging"""
    output_dir = Path("mf_finder_debug")
    output_dir.mkdir(exist_ok=True)
    
    # Save HTML
    with open(output_dir / f"{filename}.html", 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    
    # Save screenshot
    driver.save_screenshot(str(output_dir / f"{filename}.png"))
    
    logger.info(f"📸 Saved page state to {output_dir}/{filename}")


def wait_for_page_load(driver, timeout=10):
    """Wait for page to finish loading"""
    try:
        # Wait for jQuery to be ready if it exists
        driver.execute_script("return jQuery.active == 0")
        return True
    except:
        # If jQuery doesn't exist, just wait a bit
        time.sleep(2)
        return True


def find_and_click_link(driver, text_patterns, max_attempts=3):
    """Find and click a link containing any of the given text patterns"""
    for attempt in range(max_attempts):
        try:
            # Get all links
            links = driver.find_elements(By.TAG_NAME, 'a')
            logger.info(f"Found {len(links)} links on page (attempt {attempt + 1})")
            
            for link in links:
                try:
                    link_text = link.text.strip()
                    if not link_text:
                        # Try to get text from innerHTML if text is empty
                        link_text = link.get_attribute('innerHTML').strip()
                    
                    # Check if any pattern matches
                    for pattern in text_patterns:
                        if pattern.lower() in link_text.lower():
                            logger.info(f"✅ Found link: '{link_text}' matching pattern '{pattern}'")
                            
                            # Scroll to element
                            driver.execute_script("arguments[0].scrollIntoView(true);", link)
                            time.sleep(0.5)
                            
                            # Try to click
                            try:
                                link.click()
                            except:
                                # If regular click fails, try JavaScript click
                                driver.execute_script("arguments[0].click();", link)
                            
                            time.sleep(3)
                            wait_for_page_load(driver)
                            return True
                            
                except Exception as e:
                    continue
            
            # If no link found, wait and try again
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error in attempt {attempt + 1}: {e}")
            
    return False


def navigate_to_manuscripts(driver):
    """Navigate from login to manuscripts"""
    logger.info("🧭 Navigating to manuscripts...")
    
    # Step 1: After login, we might be on a confirmation page
    # Look for any "Continue" or "OK" buttons first
    try:
        # Check for alert/confirmation buttons
        confirm_buttons = driver.find_elements(By.XPATH, "//button[contains(@class, 'button-ok') or contains(text(), 'OK') or contains(text(), 'Continue')]")
        if confirm_buttons:
            logger.info(f"Found {len(confirm_buttons)} confirmation buttons")
            confirm_buttons[0].click()
            time.sleep(2)
    except:
        pass
    
    save_page_state(driver, "after_login_confirmation")
    
    # Step 2: Look for role selection or main dashboard
    # Try multiple navigation paths
    navigation_paths = [
        # Direct AE Center links
        ["Associate Editor Center", "Associate Editor Centre", "AE Center"],
        # Role-based navigation
        ["Associate Editor", "AE Dashboard", "Editor Dashboard"],
        # General dashboard
        ["Dashboard", "Home", "Main Menu"],
        # Manuscript-specific
        ["Manuscripts", "Submissions", "Papers"]
    ]
    
    for path_group in navigation_paths:
        logger.info(f"🔍 Trying navigation path: {path_group}")
        if find_and_click_link(driver, path_group):
            save_page_state(driver, f"after_clicking_{path_group[0].replace(' ', '_')}")
            break
    
    # Step 3: Now look for manuscript status categories
    status_categories = [
        "Awaiting Reviewer Scores",
        "Awaiting Reviewer Reports", 
        "Under Review",
        "Awaiting AE Decision"
    ]
    
    # Check if we can see any manuscript counts
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    manuscripts_found = []
    
    for status in status_categories:
        logger.info(f"🔎 Looking for status: {status}")
        
        # Find the status in the page
        status_elements = soup.find_all(text=re.compile(status))
        
        for elem in status_elements:
            parent = elem.parent
            # Look for count in nearby cells
            row = parent.find_parent('tr')
            if row:
                cells = row.find_all('td')
                for i, cell in enumerate(cells):
                    if status in cell.get_text():
                        # Check previous cell for count
                        if i > 0:
                            count_cell = cells[i-1]
                            count_text = count_cell.get_text(strip=True)
                            if count_text.isdigit() and int(count_text) > 0:
                                logger.info(f"✅ Found {count_text} manuscripts in '{status}'")
                                
                                # Try to click the count
                                try:
                                    # Find the clickable element in Selenium
                                    count_xpath = f"//td[text()='{count_text}']"
                                    count_elem = driver.find_element(By.XPATH, count_xpath)
                                    count_elem.click()
                                    time.sleep(3)
                                    save_page_state(driver, f"manuscripts_in_{status.replace(' ', '_')}")
                                    
                                    # Parse manuscripts on this page
                                    manuscripts = parse_manuscript_list(driver)
                                    manuscripts_found.extend(manuscripts)
                                    
                                    # Go back to dashboard
                                    driver.back()
                                    time.sleep(2)
                                    
                                except Exception as e:
                                    logger.error(f"Failed to click count for {status}: {e}")
    
    return manuscripts_found


def parse_manuscript_list(driver):
    """Parse manuscripts from current page"""
    logger.info("📝 Parsing manuscript list...")
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    manuscripts = []
    
    # Look for MAFI manuscript IDs
    mafi_pattern = re.compile(r'MAFI-\d{4}-\d+')
    
    # Find all matches
    for match in soup.find_all(text=mafi_pattern):
        ms_id = mafi_pattern.search(match).group()
        logger.info(f"Found manuscript: {ms_id}")
        
        # Try to get more details
        parent_element = match.parent
        
        # Look for title, authors, etc. in nearby elements
        manuscript_data = {
            'id': ms_id,
            'found_in': parent_element.name,
            'context': parent_element.get_text()[:200]
        }
        
        manuscripts.append(manuscript_data)
    
    return manuscripts


def main():
    logger.info("🚀 Starting MF Manuscript Finder")
    
    # Load credentials
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    
    driver = create_driver()
    
    try:
        # Login using existing MFJournal class
        journal = MFJournal(driver, debug=True)
        logger.info("🔐 Logging in to MF...")
        journal.login()
        
        # Navigate to manuscripts
        manuscripts = navigate_to_manuscripts(driver)
        
        # Print results
        logger.info("\n" + "=" * 60)
        logger.info("📊 RESULTS")
        logger.info("=" * 60)
        logger.info(f"Total manuscripts found: {len(manuscripts)}")
        
        for ms in manuscripts:
            logger.info(f"  - {ms['id']}")
            
        # Save results
        output_dir = Path("mf_finder_debug")
        results_file = output_dir / "results.json"
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'manuscripts': manuscripts
            }, f, indent=2)
            
        logger.info(f"\nResults saved to: {results_file}")
        
    finally:
        driver.quit()


if __name__ == "__main__":
    main()