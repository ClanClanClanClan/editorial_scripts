#!/usr/bin/env python3
"""
Comprehensive MF and MOR scraper that:
1. Checks ALL allowed categories for both journals (not just those with count > 0)
2. Gets complete referee details including downloading reports when available
3. Properly filters unavailable/declined referees
4. Implements deduplication across categories
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
import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from journals.mf import MFJournal
from journals.mor import MORJournal
from core.email_utils import fetch_starred_emails

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MF_MOR_COMPREHENSIVE")


class ComprehensiveScraper:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.manuscripts = []
        self.seen_manuscript_ids = set()  # For deduplication
        self.debug_dir = Path(f"{journal_name.lower()}_comprehensive_debug")
        self.debug_dir.mkdir(exist_ok=True)
        self.reports_dir = self.debug_dir / "referee_reports"
        self.reports_dir.mkdir(exist_ok=True)
        self.screenshot_count = 0
        
        # Define ALL categories to check for each journal
        if journal_name == "MF":
            self.categories_to_check = [
                "Awaiting Reviewer Selection",
                "Awaiting Reviewer Invitation", 
                "Awaiting Reviewer Assignment",
                "Awaiting Reviewer Scores",
                "Overdue Reviewer Scores",
                "Awaiting AE Recommendation"
            ]
        else:  # MOR
            self.categories_to_check = [
                "Awaiting Reviewer Selection",
                "Awaiting Reviewer Invitation",
                "Overdue Reviewer Response",
                "Awaiting Reviewer Assignment",
                "Awaiting Reviewer Reports",
                "Overdue Reviewer Reports",
                "Awaiting AE Recommendation"
            ]
        
    def create_driver(self):
        """Create Chrome driver with download preferences"""
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        # Set download preferences
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
            
    def click_category_text(self, category_text):
        """Click on the category text to access all papers"""
        logger.info(f"🎯 Clicking on category: '{category_text}'")
        
        try:
            category_link = self.driver.find_element(By.LINK_TEXT, category_text)
            self.driver.execute_script("arguments[0].scrollIntoView(true);", category_link)
            time.sleep(0.5)
            
            self.take_screenshot(f"before_clicking_{category_text.replace(' ', '_')}")
            category_link.click()
            time.sleep(3)
            self.take_screenshot(f"after_clicking_{category_text.replace(' ', '_')}")
            
            logger.info(f"✅ Successfully clicked on '{category_text}'")
            return True
            
        except Exception as e:
            logger.warning(f"Category '{category_text}' not found or not clickable: {e}")
            return False
            
    def go_back_to_ae_center(self):
        """Navigate back using Associate Editor Center link"""
        logger.info("🔙 Going back to Associate Editor Center")
        try:
            ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
            ae_link.click()
            time.sleep(2)
            self.take_screenshot("back_at_ae_center")
            return True
        except Exception as e:
            logger.error(f"Failed to go back to AE Center: {e}")
            return False
            
    def find_and_click_take_action_checkbox(self, ms_id):
        """Find and click the Take Action checkbox for a specific manuscript"""
        logger.info(f"🔍 Looking for Take Action checkbox for {ms_id}")
        
        try:
            # Find table rows containing the manuscript ID
            rows = self.driver.find_elements(By.TAG_NAME, "tr")
            
            for row in rows:
                if ms_id in row.text:
                    logger.info(f"Found row containing {ms_id}")
                    
                    # Look for checkbox in the "Take Action" column
                    checkboxes = row.find_elements(By.XPATH, ".//input[@type='checkbox']")
                    if checkboxes:
                        logger.info(f"Found Take Action checkbox for {ms_id}")
                        self.take_screenshot(f"before_checkbox_{ms_id}")
                        checkboxes[0].click()
                        time.sleep(1)
                        
                        # Look for and click "Take Action" button
                        take_action_btns = self.driver.find_elements(By.XPATH, "//input[@value='Take Action']")
                        if take_action_btns:
                            take_action_btns[0].click()
                            time.sleep(3)
                            self.take_screenshot(f"after_take_action_{ms_id}")
                            return True
                            
            logger.warning(f"Could not find Take Action checkbox for {ms_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error finding Take Action for {ms_id}: {e}")
            return False
            
    def download_referee_report(self, report_link, referee_name, ms_id):
        """Download a referee report"""
        logger.info(f"📥 Downloading report from {referee_name} for {ms_id}")
        
        try:
            # Click the report link
            report_link.click()
            time.sleep(3)
            
            # Wait for download to complete
            time.sleep(5)
            
            # Check if file was downloaded
            downloaded_files = list(self.reports_dir.glob("*"))
            if downloaded_files:
                # Rename to include referee name and manuscript ID
                latest_file = max(downloaded_files, key=lambda f: f.stat().st_mtime)
                new_name = f"{ms_id}_{referee_name.replace(' ', '_')}_report{latest_file.suffix}"
                new_path = self.reports_dir / new_name
                latest_file.rename(new_path)
                logger.info(f"✅ Downloaded report: {new_name}")
                return str(new_path)
            else:
                logger.warning(f"No file downloaded for {referee_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading report from {referee_name}: {e}")
            return None
            
    def parse_manuscript_details_comprehensive(self, flagged_emails):
        """Parse manuscript details with comprehensive referee information and report downloading"""
        logger.info("📄 Parsing comprehensive manuscript details")
        
        try:
            self.save_html("manuscript_details_comprehensive")
            
            # Parse using journal parser
            details = self.journal.parse_manuscript_panel(
                self.driver.page_source,
                flagged_emails=flagged_emails
            )
            
            # Enhanced referee processing
            if 'Referees' in details:
                original_count = len(details['Referees'])
                active_referees = []
                
                for ref in details['Referees']:
                    referee_name = ref.get('Referee Name', '')
                    status = ref.get('Status', '')
                    
                    # Check for unavailable/declined (case insensitive)
                    status_lower = status.lower()
                    if any(word in status_lower for word in ['unavailable', 'declined']):
                        logger.info(f"  Skipping {referee_name} - Status: {status}")
                        continue
                        
                    # Look for downloadable reports
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    
                    # Find report links for this referee
                    report_links = []
                    for link in soup.find_all('a', href=True):
                        if (referee_name.lower() in link.get_text().lower() or 
                            'report' in link.get_text().lower()):
                            if 'download' in link.get('href', '').lower():
                                report_links.append(link)
                                
                    # Download reports if available
                    downloaded_reports = []
                    for report_link in report_links:
                        try:
                            selenium_link = self.driver.find_element(
                                By.XPATH, 
                                f"//a[@href='{report_link.get('href')}']"
                            )
                            report_path = self.download_referee_report(
                                selenium_link, 
                                referee_name, 
                                details.get('Manuscript #', 'Unknown')
                            )
                            if report_path:
                                downloaded_reports.append(report_path)
                        except:
                            continue
                            
                    # Add report information to referee data
                    ref['Downloaded_Reports'] = downloaded_reports
                    
                    active_referees.append(ref)
                    logger.info(f"  Including {referee_name} - Status: {status} - Reports: {len(downloaded_reports)}")
                    
                details['Referees'] = active_referees
                logger.info(f"Referee filtering: {original_count} -> {len(active_referees)} active")
                
            ms_id = details.get('Manuscript #', 'Unknown')
            total_reports = sum(len(ref.get('Downloaded_Reports', [])) for ref in details.get('Referees', []))
            logger.info(f"✅ Parsed {ms_id}: {len(details.get('Referees', []))} active referees, {total_reports} reports downloaded")
            
            return details
            
        except Exception as e:
            logger.error(f"Error parsing manuscript details: {e}")
            return None
            
    def detect_page_type(self):
        """Detect if we're on a list page or detail page"""
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        text = soup.get_text()
        
        # Find manuscript IDs
        if self.journal_name == "MF":
            pattern = r'MAFI-\d{4}-\d+'
        else:
            pattern = r'MOR-\d{4}-\d+'
            
        ms_ids = list(set(re.findall(pattern, text)))
        
        # List page indicators
        if 'Take Action' in text and 'Manuscripts 1-' in text:
            logger.info(f"📋 Detected list page with {len(ms_ids)} manuscripts: {ms_ids}")
            return 'list', ms_ids
            
        # Detail page indicators
        detail_indicators = [
            'Reviewer Details',
            'Referee Details', 
            'Manuscript Details',
            'Contact Author:'
        ]
        
        for indicator in detail_indicators:
            if indicator in text:
                logger.info(f"✅ Detected manuscript detail page (found '{indicator}')")
                return 'detail', ms_ids[0] if ms_ids else None
                
        # If no manuscripts found, it's likely an empty category
        if not ms_ids:
            logger.info("📝 Empty category - no manuscripts found")
            return 'empty', []
            
        logger.info(f"🤔 Unknown page type with {len(ms_ids)} manuscripts")
        return 'unknown', ms_ids
        
    def process_manuscripts_from_category(self, category_text, flagged_emails):
        """Process all manuscripts from a category"""
        logger.info(f"\n{'='*70}")
        logger.info(f"🎯 Processing category: '{category_text}'")
        logger.info(f"{'='*70}")
        
        manuscripts_found = []
        
        # Click on the category text
        if not self.click_category_text(category_text):
            logger.warning(f"Could not access category '{category_text}' - skipping")
            return manuscripts_found
            
        # Detect what type of page we landed on
        page_type, data = self.detect_page_type()
        
        if page_type == 'empty':
            logger.info(f"Category '{category_text}' is empty - no manuscripts")
            
        elif page_type == 'list':
            # We're on a list page with multiple manuscripts
            logger.info(f"Found {len(data)} manuscripts in '{category_text}': {data}")
            
            for ms_id in data:
                if ms_id in self.seen_manuscript_ids:
                    logger.info(f"Already processed {ms_id}, skipping duplicate")
                    continue
                    
                # Click Take Action checkbox for this manuscript
                if self.find_and_click_take_action_checkbox(ms_id):
                    self.take_screenshot(f"details_{ms_id}")
                    
                    details = self.parse_manuscript_details_comprehensive(flagged_emails)
                    if details:
                        manuscripts_found.append(details)
                        self.seen_manuscript_ids.add(ms_id)
                        
                    # Go back to list
                    self.driver.back()
                    time.sleep(2)
                    
        elif page_type == 'detail':
            # We're on a detail page (single manuscript)
            logger.info(f"Landed on detail page for manuscript: {data}")
            
            if data and data not in self.seen_manuscript_ids:
                details = self.parse_manuscript_details_comprehensive(flagged_emails)
                if details:
                    manuscripts_found.append(details)
                    self.seen_manuscript_ids.add(data)
                    
        else:
            logger.warning(f"Unknown page type for category '{category_text}'")
            
        logger.info(f"📊 Found {len(manuscripts_found)} new manuscripts in '{category_text}'")
        return manuscripts_found
        
    def scrape_journal(self):
        """Scrape manuscripts for all categories in the journal"""
        logger.info(f"🔍 Starting comprehensive {self.journal_name} scrape")
        logger.info(f"Will check {len(self.categories_to_check)} categories: {self.categories_to_check}")
        
        # Create journal instance and login
        if self.journal_name == "MF":
            self.journal = MFJournal(self.driver, debug=True)
        else:
            self.journal = MORJournal(self.driver, debug=True)
            
        self.journal.login()
        self.take_screenshot("after_login")
        
        # Navigate to AE Center
        try:
            ae_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            time.sleep(3)
            self.take_screenshot("ae_center")
        except:
            # Handle confirmation for MF
            try:
                confirm_btn = self.driver.find_element(By.CLASS_NAME, "button-ok")
                confirm_btn.click()
                time.sleep(2)
            except:
                pass
                
            # Try again
            try:
                ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
                ae_link.click()
                time.sleep(3)
                self.take_screenshot("ae_center_retry")
            except Exception as e:
                logger.error(f"Could not find AE Center: {e}")
                return
                
        # Get flagged emails
        flagged_emails = fetch_starred_emails(self.journal_name)
        logger.info(f"Found {len(flagged_emails)} flagged emails")
        
        # Process ALL categories
        for category in self.categories_to_check:
            manuscripts = self.process_manuscripts_from_category(category, flagged_emails)
            self.manuscripts.extend(manuscripts)
            
            # Go back to AE Center for next category
            self.go_back_to_ae_center()
            time.sleep(1)
            
    def run(self):
        """Run the scraper"""
        self.create_driver()
        
        try:
            self.scrape_journal()
            self.print_results()
            self.save_results()
        finally:
            self.driver.quit()
            
    def print_results(self):
        """Print comprehensive results"""
        logger.info("\n" + "=" * 80)
        logger.info(f"📊 {self.journal_name} COMPREHENSIVE RESULTS")
        logger.info("=" * 80)
        
        total_referees = 0
        total_reports = 0
        
        for i, ms in enumerate(self.manuscripts, 1):
            ms_id = ms.get('Manuscript #', 'Unknown')
            title = ms.get('Title', 'No title')
            if len(title) > 60:
                title = title[:60] + "..."
            
            referees = ms.get('Referees', [])
            
            logger.info(f"\n📄 Manuscript {i}: {ms_id}")
            logger.info(f"   Title: {title}")
            logger.info(f"   Author: {ms.get('Contact Author', 'Unknown')}")
            logger.info(f"   Submission Date: {ms.get('Submission Date', 'Unknown')}")
            logger.info(f"   Active Referees ({len(referees)}):")
            
            for j, ref in enumerate(referees, 1):
                name = ref.get('Referee Name', 'Unknown')
                status = ref.get('Status', 'Unknown')
                reports = ref.get('Downloaded_Reports', [])
                logger.info(f"     {j}. {name} - {status} - {len(reports)} report(s)")
                total_reports += len(reports)
                
            total_referees += len(referees)
            
        # Check expectations
        if self.journal_name == "MF":
            expected_mss = 2
            expected_refs = 4
        else:
            expected_mss = 3
            expected_refs = 5
            
        logger.info(f"\n📊 FINAL SUMMARY:")
        logger.info(f"   Categories checked: {len(self.categories_to_check)}")
        logger.info(f"   Total manuscripts found: {len(self.manuscripts)} (expected: {expected_mss})")
        logger.info(f"   Total active referees: {total_referees} (expected: {expected_refs})")
        logger.info(f"   Total reports downloaded: {total_reports}")
        logger.info(f"   Unique manuscripts processed: {len(self.seen_manuscript_ids)}")
        
        # Success check
        if len(self.manuscripts) >= expected_mss and total_referees >= expected_refs:
            logger.info("✅ SUCCESS: Comprehensive ultra-deep debugging complete!")
        elif len(self.manuscripts) > 0:
            logger.info("✅ PARTIAL SUCCESS: Found manuscripts - ultra-deep debugging working!")
        else:
            logger.warning("⚠️ Need more debugging")
        
    def save_results(self):
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
            'total_manuscripts': len(self.manuscripts),
            'total_referees': sum(len(ms.get('Referees', [])) for ms in self.manuscripts),
            'total_reports': sum(sum(len(ref.get('Downloaded_Reports', [])) for ref in ms.get('Referees', [])) for ms in self.manuscripts),
            'expected_manuscripts': expected_mss,
            'expected_referees': expected_refs,
            'success': len(self.manuscripts) >= expected_mss,
            'unique_manuscripts': list(self.seen_manuscript_ids),
            'manuscripts': self.manuscripts
        }
        
        with open(output_file, 'w') as f:
            json.dump(result_data, f, indent=2)
            
        logger.info(f"\n💾 Results saved to: {output_file}")
        logger.info(f"📁 Reports saved to: {self.reports_dir}")


def main():
    # Run MF first - check ALL categories
    logger.info("\n" + "="*80)
    logger.info("MF Comprehensive Scraper - All Categories + Report Downloads")
    logger.info("="*80)
    
    mf_scraper = ComprehensiveScraper("MF")
    mf_scraper.run()
    
    # Then run MOR - check ALL categories
    logger.info("\n" + "="*80)
    logger.info("MOR Comprehensive Scraper - All Categories + Report Downloads")
    logger.info("="*80)
    
    mor_scraper = ComprehensiveScraper("MOR")
    mor_scraper.run()


if __name__ == "__main__":
    main()