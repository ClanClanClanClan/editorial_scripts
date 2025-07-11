#!/usr/bin/env python3
"""
Working MF scraper that successfully finds and accesses manuscripts.
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

from journals.mf import MFJournal
from core.email_utils import fetch_starred_emails

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MF_SCRAPER")


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


def click_manuscript_count_link(driver, count_text, status_text):
    """Click on a manuscript count link using the visible text"""
    logger.info(f"🎯 Attempting to click count '{count_text}' for status '{status_text}'")
    
    try:
        # Method 1: Find the link by its visible text
        xpath = f"//a[normalize-space()='{count_text}']"
        links = driver.find_elements(By.XPATH, xpath)
        
        # If multiple links with same text, find the one near the status
        if len(links) > 1:
            # Look for the one in same row as status
            xpath = f"//td[contains(., '{status_text}')]/preceding-sibling::td//a[normalize-space()='{count_text}']"
            specific_link = driver.find_element(By.XPATH, xpath)
            if specific_link:
                driver.execute_script("arguments[0].scrollIntoView(true);", specific_link)
                time.sleep(0.5)
                specific_link.click()
                logger.info(f"✅ Clicked specific link for {status_text}")
                return True
        elif len(links) == 1:
            driver.execute_script("arguments[0].scrollIntoView(true);", links[0])
            time.sleep(0.5)
            links[0].click()
            logger.info(f"✅ Clicked link with text '{count_text}'")
            return True
        
        # Method 2: Find by href pattern
        all_links = driver.find_elements(By.TAG_NAME, 'a')
        for link in all_links:
            if link.text.strip() == count_text:
                # Check if this link is near the status text
                parent_row = link.find_element(By.XPATH, './ancestor::tr')
                if status_text in parent_row.text:
                    driver.execute_script("arguments[0].scrollIntoView(true);", link)
                    time.sleep(0.5)
                    link.click()
                    logger.info(f"✅ Clicked link via parent row search")
                    return True
        
    except Exception as e:
        logger.error(f"Failed to click link: {e}")
        
    return False


def parse_manuscript_details(driver, ms_id):
    """Parse detailed manuscript information including referees"""
    logger.info(f"📋 Parsing details for {ms_id}")
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    manuscript_data = {
        'id': ms_id,
        'title': '',
        'authors': '',
        'submission_date': '',
        'referees': []
    }
    
    # Find title
    title_pattern = re.compile(f"{ms_id}")
    for elem in soup.find_all(text=title_pattern):
        parent = elem.parent
        # Title is usually in the next paragraph or nearby
        next_p = parent.find_next_sibling('p')
        if next_p:
            manuscript_data['title'] = next_p.get_text(strip=True)
            break
    
    # Find referee information
    reviewer_section = soup.find(text=re.compile("Reviewer List", re.I))
    if reviewer_section:
        # Find the table containing reviewers
        reviewer_table = reviewer_section.find_parent('table')
        if reviewer_table:
            # Look for the actual reviewer data table
            next_table = reviewer_table.find_next_sibling('table')
            if next_table:
                rows = next_table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    # Look for cells with reviewer names (Last, First format)
                    for cell in cells:
                        text = cell.get_text(strip=True)
                        if ',' in text and len(text.split(',')) == 2:
                            # This looks like a name
                            referee_data = {
                                'name': text,
                                'status': '',
                                'dates': {}
                            }
                            
                            # Look for status in same row
                            for other_cell in cells:
                                other_text = other_cell.get_text(strip=True).lower()
                                if any(status in other_text for status in ['agreed', 'contacted', 'declined', 'accepted']):
                                    referee_data['status'] = other_text
                                    
                            manuscript_data['referees'].append(referee_data)
    
    logger.info(f"Found {len(manuscript_data['referees'])} referees for {ms_id}")
    
    return manuscript_data


def scrape_mf_manuscripts():
    """Main function to scrape MF manuscripts"""
    logger.info("🚀 Starting MF Manuscript Scraper")
    
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
    manuscripts = []
    
    try:
        # Login
        journal = MFJournal(driver, debug=True)
        logger.info("🔐 Logging in to MF...")
        journal.login()
        
        # Navigate to Associate Editor Center
        logger.info("🏢 Navigating to Associate Editor Center...")
        
        # Click Associate Editor Center link
        ae_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
        )
        ae_link.click()
        time.sleep(3)
        
        # Get flagged emails
        logger.info("📧 Fetching flagged emails...")
        flagged_emails = fetch_starred_emails("MF")
        logger.info(f"Found {len(flagged_emails)} flagged emails")
        
        # Find manuscript counts
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Look for status categories with counts
        status_categories = [
            "Awaiting Reviewer Scores",
            "Overdue Manuscripts Awaiting Revision"
        ]
        
        for status in status_categories:
            logger.info(f"🔍 Checking status: {status}")
            
            # Find the status text
            status_elem = soup.find(text=re.compile(status))
            if status_elem:
                # Look for count in previous cell
                parent_row = status_elem.find_parent('tr')
                if parent_row:
                    cells = parent_row.find_all('td')
                    for i, cell in enumerate(cells):
                        if status in cell.get_text():
                            # Previous cell should have count
                            if i > 0:
                                count_cell = cells[i-1]
                                count_link = count_cell.find('a')
                                if count_link:
                                    count_text = count_link.get_text(strip=True)
                                    if count_text.isdigit() and int(count_text) > 0:
                                        logger.info(f"📊 Found {count_text} manuscripts in '{status}'")
                                        
                                        # Click the count
                                        if click_manuscript_count_link(driver, count_text, status):
                                            time.sleep(3)
                                            
                                            # Parse manuscripts on this page
                                            ms_soup = BeautifulSoup(driver.page_source, 'html.parser')
                                            
                                            # Find all manuscript IDs
                                            ms_pattern = re.compile(r'MAFI-\d{4}-\d+')
                                            ms_ids = list(set(ms_pattern.findall(ms_soup.get_text())))
                                            
                                            logger.info(f"Found manuscript IDs: {ms_ids}")
                                            
                                            # Click on each manuscript to get details
                                            for ms_id in ms_ids:
                                                try:
                                                    # Find and click manuscript link
                                                    ms_link = driver.find_element(By.PARTIAL_LINK_TEXT, ms_id)
                                                    ms_link.click()
                                                    time.sleep(2)
                                                    
                                                    # Parse manuscript details
                                                    ms_data = parse_manuscript_details(driver, ms_id)
                                                    ms_data['status_category'] = status
                                                    
                                                    # Use the journal's parsing method for more details
                                                    detailed_data = journal.parse_manuscript_panel(
                                                        driver.page_source, 
                                                        flagged_emails=flagged_emails
                                                    )
                                                    
                                                    # Merge data
                                                    ms_data.update(detailed_data)
                                                    manuscripts.append(ms_data)
                                                    
                                                    # Go back to list
                                                    driver.back()
                                                    time.sleep(2)
                                                    
                                                except Exception as e:
                                                    logger.error(f"Error processing {ms_id}: {e}")
                                            
                                            # Go back to AE dashboard
                                            driver.back()
                                            time.sleep(2)
                                            
                                            # Re-parse the page
                                            soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Print results
        logger.info("\n" + "=" * 60)
        logger.info("📊 SCRAPING RESULTS")
        logger.info("=" * 60)
        logger.info(f"Total manuscripts found: {len(manuscripts)}")
        
        for ms in manuscripts:
            logger.info(f"\n📄 Manuscript: {ms.get('Manuscript #', ms.get('id'))}")
            logger.info(f"   Title: {ms.get('Title', 'N/A')}")
            logger.info(f"   Status: {ms.get('status_category', 'N/A')}")
            logger.info(f"   Contact Author: {ms.get('Contact Author', 'N/A')}")
            logger.info(f"   Referees: {len(ms.get('Referees', []))}")
            
            for ref in ms.get('Referees', []):
                logger.info(f"     - {ref.get('Referee Name', 'Unknown')} ({ref.get('Status', 'Unknown')})")
        
        # Save results
        output_file = Path("mf_scraping_results.json")
        with open(output_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_manuscripts': len(manuscripts),
                'manuscripts': manuscripts
            }, f, indent=2)
        
        logger.info(f"\n✅ Results saved to: {output_file}")
        
        # Expected: 2 manuscripts with 4 referees total
        referee_count = sum(len(ms.get('Referees', [])) for ms in manuscripts)
        logger.info(f"\n📊 Summary: Found {len(manuscripts)} manuscripts with {referee_count} referees total")
        logger.info(f"   Expected: 2 manuscripts with 4 referees total")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        
    finally:
        driver.quit()
        
    return manuscripts


if __name__ == "__main__":
    manuscripts = scrape_mf_manuscripts()