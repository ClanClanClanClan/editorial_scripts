#!/usr/bin/env python3
"""
ScholarOne Workflow Debug - Understanding the Take Action workflow
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
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
import json
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from journals.mf import MFJournal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("WORKFLOW_DEBUG")


class ScholarOneWorkflowDebugger:
    def __init__(self):
        self.driver = None
        self.journal = None
        self.debug_dir = Path("workflow_debug")
        self.debug_dir.mkdir(exist_ok=True)
        self.screenshot_count = 0
        
    def create_driver(self):
        """Create Chrome driver"""
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        try:
            self.driver = uc.Chrome(options=options)
        except:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            chrome_options = Options()
            for arg in options.arguments:
                chrome_options.add_argument(arg)
            self.driver = webdriver.Chrome(options=chrome_options)
            
    def take_screenshot(self, description):
        """Take screenshot with description"""
        self.screenshot_count += 1
        filename = f"{self.screenshot_count:03d}_{description.replace(' ', '_')}.png"
        filepath = self.debug_dir / filename
        self.driver.save_screenshot(str(filepath))
        logger.info(f"📸 Screenshot: {filename}")
        return filepath
        
    def debug_workflow(self):
        """Debug the ScholarOne workflow"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 DEBUGGING SCHOLARONE WORKFLOW")
        logger.info(f"{'='*80}")
        
        self.create_driver()
        
        try:
            # Login to MF
            self.journal = MFJournal(self.driver, debug=True)
            
            # Navigate to journal URL
            logger.info("Navigating to MF...")
            self.driver.get("https://mc.manuscriptcentral.com/mafi")
            time.sleep(3)
            
            # Handle cookie banner
            try:
                cookie_button = self.driver.find_element(By.ID, "onetrust-accept-btn-handler")
                if cookie_button.is_displayed():
                    logger.info("Accepting cookies...")
                    cookie_button.click()
                    time.sleep(1)
            except:
                pass
                
            self.journal.login()
            self.take_screenshot("01_after_login")
            
            # Navigate to AE Center
            ae_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            time.sleep(3)
            self.take_screenshot("02_ae_center")
            
            # Navigate to category
            category = "Awaiting Reviewer Scores"
            logger.info(f"\n📂 Navigating to: {category}")
            category_link = self.driver.find_element(By.LINK_TEXT, category)
            category_link.click()
            time.sleep(3)
            self.take_screenshot("03_category_list")
            
            # EXPERIMENT 1: Click directly on manuscript ID link
            logger.info("\n🧪 EXPERIMENT 1: Click manuscript ID directly")
            manuscript_ids = ['MAFI-2025-0166', 'MAFI-2024-0167']
            
            for ms_id in manuscript_ids[:1]:  # Try first one
                try:
                    logger.info(f"\nTrying to click on {ms_id}...")
                    ms_link = self.driver.find_element(By.LINK_TEXT, ms_id)
                    ms_link.click()
                    time.sleep(3)
                    
                    self.take_screenshot(f"04_clicked_{ms_id}")
                    
                    # Check what page we're on
                    current_url = self.driver.current_url
                    page_title = self.driver.title
                    logger.info(f"Current URL: {current_url}")
                    logger.info(f"Page title: {page_title}")
                    
                    # Look for referee information
                    page_source = self.driver.page_source
                    if "referee" in page_source.lower() or "reviewer" in page_source.lower():
                        logger.info("✅ Found referee/reviewer content!")
                        
                        # Extract what we can see
                        soup = BeautifulSoup(page_source, 'html.parser')
                        
                        # Look for tables with referee info
                        tables = soup.find_all('table')
                        logger.info(f"Found {len(tables)} tables on page")
                        
                        # Take detailed screenshot
                        self.take_screenshot("05_referee_detail_page")
                        
                    # Go back
                    self.driver.back()
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error clicking {ms_id}: {e}")
                    
            # EXPERIMENT 2: Look for action menu or dropdown
            logger.info("\n🧪 EXPERIMENT 2: Look for action dropdowns")
            
            # Find all select elements
            selects = self.driver.find_elements(By.TAG_NAME, "select")
            logger.info(f"Found {len(selects)} select dropdowns")
            
            for i, select in enumerate(selects):
                try:
                    name = select.get_attribute('name') or ''
                    options_count = len(select.find_elements(By.TAG_NAME, "option"))
                    logger.info(f"Select {i+1}: name='{name}', options={options_count}")
                    
                    if 'action' in name.lower():
                        self.take_screenshot(f"06_action_dropdown_{i+1}")
                except:
                    pass
                    
            # EXPERIMENT 3: Look for hidden forms
            logger.info("\n🧪 EXPERIMENT 3: Check for hidden forms")
            
            forms = self.driver.find_elements(By.TAG_NAME, "form")
            logger.info(f"Found {len(forms)} forms")
            
            for i, form in enumerate(forms):
                try:
                    action = form.get_attribute('action') or ''
                    method = form.get_attribute('method') or ''
                    name = form.get_attribute('name') or ''
                    
                    if action or name:
                        logger.info(f"Form {i+1}: action='{action}', method='{method}', name='{name}'")
                        
                        # Look for hidden inputs in form
                        hidden_inputs = form.find_elements(By.XPATH, ".//input[@type='hidden']")
                        if hidden_inputs:
                            logger.info(f"  Has {len(hidden_inputs)} hidden inputs")
                except:
                    pass
                    
            # EXPERIMENT 4: Check manuscript row structure in detail
            logger.info("\n🧪 EXPERIMENT 4: Detailed row analysis")
            
            # Find manuscript rows
            rows = self.driver.find_elements(By.XPATH, "//tr[contains(., 'MAFI-')]")
            logger.info(f"Found {len(rows)} manuscript rows")
            
            if rows:
                row = rows[0]  # First manuscript
                cells = row.find_elements(By.TAG_NAME, "td")
                
                logger.info(f"\nAnalyzing first row ({len(cells)} cells):")
                
                for i, cell in enumerate(cells):
                    try:
                        cell_text = cell.text.strip()[:50]  # First 50 chars
                        
                        # Find all clickable elements in cell
                        clickables = cell.find_elements(By.XPATH, ".//*[@onclick or @href]")
                        
                        logger.info(f"\nCell {i+1}: '{cell_text}...'")
                        
                        if clickables:
                            logger.info(f"  Has {len(clickables)} clickable elements:")
                            
                            for j, elem in enumerate(clickables[:3]):  # First 3
                                tag = elem.tag_name
                                onclick = elem.get_attribute('onclick') or ''
                                href = elem.get_attribute('href') or ''
                                text = elem.text or elem.get_attribute('value') or ''
                                
                                logger.info(f"    - {tag}: text='{text[:30]}', onclick='{onclick[:50]}', href='{href[:50]}'")
                    except:
                        pass
                        
            # EXPERIMENT 5: Try clicking View Submission link
            logger.info("\n🧪 EXPERIMENT 5: Try View Submission link")
            
            try:
                view_links = self.driver.find_elements(By.PARTIAL_LINK_TEXT, "View Submission")
                logger.info(f"Found {len(view_links)} View Submission links")
                
                if view_links:
                    view_links[0].click()
                    time.sleep(3)
                    self.take_screenshot("07_view_submission_page")
                    
                    # Check for referee info
                    page_source = self.driver.page_source
                    if "referee" in page_source.lower() or "reviewer" in page_source.lower():
                        logger.info("✅ Found referee/reviewer content on View Submission page!")
                    
                    self.driver.back()
                    time.sleep(2)
            except:
                pass
                
            logger.info("\n" + "="*80)
            logger.info("WORKFLOW ANALYSIS COMPLETE")
            logger.info("="*80)
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            self.take_screenshot("error")
            
        finally:
            time.sleep(2)
            self.driver.quit()


def main():
    debugger = ScholarOneWorkflowDebugger()
    debugger.debug_workflow()


if __name__ == "__main__":
    main()