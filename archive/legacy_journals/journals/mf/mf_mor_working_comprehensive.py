#!/usr/bin/env python3
"""
Working comprehensive MF and MOR scraper based on successful previous runs.
Starting with what we know works, then expanding to all categories.
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
from journals.mor import MORJournal
from core.email_utils import fetch_starred_emails

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MF_MOR_WORKING_COMPREHENSIVE")


class WorkingComprehensiveScraper:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.manuscripts = []
        self.seen_manuscript_ids = set()
        self.debug_dir = Path(f"{journal_name.lower()}_working_comprehensive_debug")
        self.debug_dir.mkdir(exist_ok=True)
        self.reports_dir = self.debug_dir / "referee_reports"
        self.reports_dir.mkdir(exist_ok=True)
        self.screenshot_count = 0
        
        # ALL categories to check for each journal
        if journal_name == "MF":
            self.categories_to_check = [
                "Awaiting Reviewer Selection",
                "Awaiting Reviewer Invitation", 
                "Awaiting Reviewer Assignment",
                "Awaiting Reviewer Scores",      # Known to have 2 manuscripts
                "Overdue Reviewer Scores",
                "Awaiting AE Recommendation"
            ]
        else:  # MOR
            self.categories_to_check = [
                "Awaiting Reviewer Selection",
                "Awaiting Reviewer Invitation",
                "Overdue Reviewer Response",
                "Awaiting Reviewer Assignment",
                "Awaiting Reviewer Reports",     # Known to have 3 manuscripts
                "Overdue Reviewer Reports",
                "Awaiting AE Recommendation"
            ]
        
    def create_driver(self, headless=True):
        """Create Chrome driver with download capabilities"""
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        if headless:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
        
        # Download settings
        prefs = {
            "download.default_directory": str(self.reports_dir.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        
        try:
            self.driver = uc.Chrome(options=options)
        except:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            chrome_options = Options()
            for arg in options.arguments:
                chrome_options.add_argument(arg)
            chrome_options.add_experimental_option("prefs", prefs)
            self.driver = webdriver.Chrome(options=chrome_options)
            
    def take_screenshot(self, description):
        """Take a screenshot"""
        self.screenshot_count += 1
        filename = f"{self.screenshot_count:03d}_{description.replace(' ', '_')}.png"
        filepath = self.debug_dir / filename
        self.driver.save_screenshot(str(filepath))
        logger.info(f"📸 Screenshot: {filename}")
        
    def save_html(self, description):
        """Save current HTML"""
        filename = f"{description.replace(' ', '_')}.html"
        filepath = self.debug_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
            
    def login_and_navigate_to_ae_center(self):
        """Login and navigate to AE Center with robust error handling"""
        logger.info(f"🔐 Logging into {self.journal_name}")
        
        # Create journal instance and login
        if self.journal_name == "MF":
            self.journal = MFJournal(self.driver, debug=True)
        else:
            self.journal = MORJournal(self.driver, debug=True)
            
        self.journal.login()
        self.take_screenshot("after_login")
        
        # Navigate to AE Center with multiple strategies
        success = False
        
        # Strategy 1: Direct wait for AE Center link
        try:
            ae_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            time.sleep(3)
            self.take_screenshot("ae_center_direct")
            success = True
            logger.info("✅ Accessed AE Center directly")
        except:
            logger.info("Strategy 1 failed - trying confirmation handling")
            
        # Strategy 2: Handle confirmation for MF
        if not success and self.journal_name == "MF":
            try:
                confirm_btn = self.driver.find_element(By.CLASS_NAME, "button-ok")
                confirm_btn.click()
                time.sleep(2)
                self.take_screenshot("after_confirm")
                
                # Try AE Center again
                ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
                ae_link.click()
                time.sleep(3)
                self.take_screenshot("ae_center_after_confirm")
                success = True
                logger.info("✅ Accessed AE Center after confirmation")
            except:
                logger.info("Strategy 2 failed - trying alternative navigation")
                
        # Strategy 3: Look for alternative navigation
        if not success:
            try:
                # Look for any link containing "Associate Editor"
                ae_links = self.driver.find_elements(By.PARTIAL_LINK_TEXT, "Associate Editor")
                if ae_links:
                    ae_links[0].click()
                    time.sleep(3)
                    self.take_screenshot("ae_center_partial")
                    success = True
                    logger.info("✅ Accessed AE Center via partial link")
            except:
                logger.info("Strategy 3 failed")
                
        if not success:
            logger.error("❌ Could not access Associate Editor Center")
            raise Exception("Failed to access Associate Editor Center")
            
        return success
        
    def click_category_and_detect_result(self, category_text):
        """Click category and detect what type of page we get"""
        logger.info(f"🎯 Clicking category: '{category_text}'")
        
        try:
            # Find the category link
            category_link = self.driver.find_element(By.LINK_TEXT, category_text)
            self.driver.execute_script("arguments[0].scrollIntoView(true);", category_link)
            time.sleep(0.5)
            
            self.take_screenshot(f"before_{category_text.replace(' ', '_')}")
            category_link.click()
            time.sleep(3)
            self.take_screenshot(f"after_{category_text.replace(' ', '_')}")
            
            # Analyze what we got
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            page_text = soup.get_text()
            
            # Find manuscript IDs
            if self.journal_name == "MF":
                pattern = r'MAFI-\d{4}-\d+'
            else:
                pattern = r'MOR-\d{4}-\d+'
                
            ms_ids = list(set(re.findall(pattern, page_text)))
            
            # Determine page type
            if not ms_ids:
                logger.info(f"📝 Category '{category_text}' is empty")
                return 'empty', []
            elif 'Take Action' in page_text and 'Manuscripts 1-' in page_text:
                logger.info(f"📋 Category '{category_text}' has list page with {len(ms_ids)} manuscripts")
                return 'list', ms_ids
            else:
                logger.info(f"📄 Category '{category_text}' has detail page or unknown format")
                return 'detail', ms_ids
                
        except Exception as e:
            logger.warning(f"Could not access category '{category_text}': {e}")
            return 'error', []
            
    def extract_referee_info_from_list_page(self):
        """Extract referee information directly from the list page"""
        logger.info("📊 Extracting referee info from list page")
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        referee_info = {}
        
        # Look for referee status patterns like "2 active selections; 2 invited; 2 agreed; 2 declined"
        # Search in the full page text
        page_text = soup.get_text()
        
        # Find manuscript IDs
        if self.journal_name == "MF":
            ms_pattern = r'MAFI-\d{4}-\d+'
        else:
            ms_pattern = r'MOR-\d{4}-\d+'
            
        ms_ids = list(set(re.findall(ms_pattern, page_text)))
        logger.info(f"Found manuscript IDs: {ms_ids}")
        
        # For each manuscript, find the referee status information
        for ms_id in ms_ids:
            logger.info(f"Looking for referee info for {ms_id}")
            
            # Find the table row containing this manuscript
            try:
                # Look for elements containing the manuscript ID
                for element in soup.find_all(text=re.compile(ms_id)):
                    parent_row = element.parent
                    
                    # Traverse up to find the table row
                    while parent_row and parent_row.name != 'tr':
                        parent_row = parent_row.parent
                        
                    if parent_row:
                        row_text = parent_row.get_text()
                        
                        # Look for referee information patterns in this row
                        if ('active selections' in row_text or 'invited' in row_text or 
                            'agreed' in row_text or 'declined' in row_text):
                            
                            logger.info(f"Found referee info in row: {row_text[:200]}...")
                            
                            # Extract referee counts
                            active_match = re.search(r'(\d+)\s+active\s+selections', row_text)
                            invited_match = re.search(r'(\d+)\s+invited', row_text)
                            agreed_match = re.search(r'(\d+)\s+agreed', row_text)
                            declined_match = re.search(r'(\d+)\s+declined', row_text)
                            returned_match = re.search(r'(\d+)\s+returned', row_text)
                            
                            active_count = int(active_match.group(1)) if active_match else 0
                            invited_count = int(invited_match.group(1)) if invited_match else 0
                            agreed_count = int(agreed_match.group(1)) if agreed_match else 0
                            declined_count = int(declined_match.group(1)) if declined_match else 0
                            returned_count = int(returned_match.group(1)) if returned_match else 0
                            
                            referee_info[ms_id] = {
                                'active_selections': active_count,
                                'invited': invited_count,
                                'agreed': agreed_count,
                                'declined': declined_count,
                                'returned': returned_count,
                                'active': agreed_count,  # Active referees are those who agreed
                                'raw_text': row_text.strip()
                            }
                            
                            logger.info(f"  ✅ {ms_id}: {active_count} active selections, {invited_count} invited, {agreed_count} agreed, {declined_count} declined, {returned_count} returned")
                            break
                            
            except Exception as e:
                logger.warning(f"Error processing {ms_id}: {e}")
                
        return referee_info
        
    def process_all_categories(self):
        """Process all categories for the journal"""
        logger.info(f"🔍 Processing all {len(self.categories_to_check)} categories")
        
        flagged_emails = fetch_starred_emails(self.journal_name)
        logger.info(f"Found {len(flagged_emails)} flagged emails")
        
        category_results = {}
        total_manuscripts = 0
        total_referees = 0
        
        for category in self.categories_to_check:
            logger.info(f"\n{'='*50}")
            logger.info(f"Processing: {category}")
            logger.info(f"{'='*50}")
            
            # Click category and see what we get
            page_type, ms_ids = self.click_category_and_detect_result(category)
            
            if page_type == 'empty':
                category_results[category] = {
                    'manuscripts': [],
                    'referee_count': 0,
                    'status': 'empty'
                }
                
            elif page_type == 'list':
                # Extract referee info from list page
                referee_info = self.extract_referee_info_from_list_page()
                
                manuscripts = []
                category_referees = 0
                
                for ms_id in ms_ids:
                    if ms_id in self.seen_manuscript_ids:
                        logger.info(f"Already processed {ms_id}, skipping")
                        continue
                        
                    self.seen_manuscript_ids.add(ms_id)
                    
                    # Create manuscript entry
                    ms_data = {
                        'Manuscript #': ms_id,
                        'Category': category,
                        'Referee_Info': referee_info.get(ms_id, {}),
                        'Active_Referees': referee_info.get(ms_id, {}).get('active', 0)
                    }
                    
                    manuscripts.append(ms_data)
                    category_referees += ms_data['Active_Referees']
                    
                category_results[category] = {
                    'manuscripts': manuscripts,
                    'referee_count': category_referees,
                    'status': 'success'
                }
                
                total_manuscripts += len(manuscripts)
                total_referees += category_referees
                
            else:
                category_results[category] = {
                    'manuscripts': [],
                    'referee_count': 0,
                    'status': 'unknown_format'
                }
                
            # Go back to AE Center
            try:
                ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
                ae_link.click()
                time.sleep(2)
            except:
                logger.warning("Could not go back to AE Center")
                
        return category_results, total_manuscripts, total_referees
        
    def run(self, headless=True):
        """Run the comprehensive scraper"""
        self.create_driver(headless=headless)
        
        try:
            # Login and navigate to AE Center
            self.login_and_navigate_to_ae_center()
            
            # Process all categories
            category_results, total_manuscripts, total_referees = self.process_all_categories()
            
            # Print results
            self.print_results(category_results, total_manuscripts, total_referees)
            
            # Save results
            self.save_results(category_results, total_manuscripts, total_referees)
            
            return category_results, total_manuscripts, total_referees
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            if not headless:
                self.take_screenshot("fatal_error")
            
        finally:
            self.driver.quit()
            
    def print_results(self, category_results, total_manuscripts, total_referees):
        """Print comprehensive results"""
        logger.info("\n" + "=" * 80)
        logger.info(f"📊 {self.journal_name} COMPREHENSIVE RESULTS")
        logger.info("=" * 80)
        
        for category, results in category_results.items():
            status = results['status']
            ms_count = len(results['manuscripts'])
            ref_count = results['referee_count']
            
            logger.info(f"\n📂 {category}: {status}")
            logger.info(f"   Manuscripts: {ms_count}")
            logger.info(f"   Active Referees: {ref_count}")
            
            if ms_count > 0:
                for ms in results['manuscripts']:
                    ms_id = ms['Manuscript #']
                    active_refs = ms['Active_Referees']
                    logger.info(f"   📄 {ms_id}: {active_refs} active referees")
                    
        # Summary
        if self.journal_name == "MF":
            expected_mss, expected_refs = 2, 4
        else:
            expected_mss, expected_refs = 3, 5
            
        logger.info(f"\n📊 OVERALL SUMMARY:")
        logger.info(f"   Categories checked: {len(self.categories_to_check)}")
        logger.info(f"   Total manuscripts: {total_manuscripts} (expected: {expected_mss})")
        logger.info(f"   Total active referees: {total_referees} (expected: {expected_refs})")
        
        if total_manuscripts >= expected_mss and total_referees >= expected_refs:
            logger.info("✅ SUCCESS: Found all expected manuscripts and referees!")
        elif total_manuscripts > 0:
            logger.info("✅ PARTIAL SUCCESS: Found manuscripts - ultra-deep debugging working!")
        else:
            logger.warning("⚠️ Need more investigation")
            
    def save_results(self, category_results, total_manuscripts, total_referees):
        """Save comprehensive results"""
        output_file = self.debug_dir / "comprehensive_results.json"
        
        if self.journal_name == "MF":
            expected_mss, expected_refs = 2, 4
        else:
            expected_mss, expected_refs = 3, 5
            
        result_data = {
            'journal': self.journal_name,
            'timestamp': datetime.now().isoformat(),
            'categories_checked': self.categories_to_check,
            'category_results': category_results,
            'total_manuscripts': total_manuscripts,
            'total_referees': total_referees,
            'expected_manuscripts': expected_mss,
            'expected_referees': expected_refs,
            'success': total_manuscripts >= expected_mss and total_referees >= expected_refs,
            'unique_manuscripts': list(self.seen_manuscript_ids)
        }
        
        with open(output_file, 'w') as f:
            json.dump(result_data, f, indent=2)
            
        logger.info(f"\n💾 Results saved to: {output_file}")


def main():
    # Run MF first
    logger.info("\n" + "="*80)
    logger.info("MF Working Comprehensive Scraper - All Categories")
    logger.info("="*80)
    
    mf_scraper = WorkingComprehensiveScraper("MF")
    mf_scraper.run()
    
    # Then run MOR
    logger.info("\n" + "="*80)
    logger.info("MOR Working Comprehensive Scraper - All Categories")
    logger.info("="*80)
    
    mor_scraper = WorkingComprehensiveScraper("MOR")
    mor_scraper.run()


if __name__ == "__main__":
    main()