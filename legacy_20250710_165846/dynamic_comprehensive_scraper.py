#!/usr/bin/env python3
"""
Dynamic Comprehensive Scraper - Discovers categories automatically
Instead of hardcoding, this finds categories with manuscripts and processes them
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
logger = logging.getLogger("DYNAMIC_COMPREHENSIVE_SCRAPER")

class DynamicComprehensiveScraper:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.discovered_categories = []
        self.processed_manuscripts = []
        self.debug_dir = Path(f"{journal_name.lower()}_dynamic_debug")
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
        """Take a screenshot"""
        self.screenshot_count += 1
        filename = f"{self.screenshot_count:03d}_{description.replace(' ', '_')}.png"
        filepath = self.debug_dir / filename
        self.driver.save_screenshot(str(filepath))
        logger.info(f"📸 Screenshot: {filename}")
        
    def login_and_navigate_to_ae_center(self):
        """Login and navigate to AE Center"""
        logger.info(f"🔐 Logging into {self.journal_name}")
        
        if self.journal_name == "MF":
            self.journal = MFJournal(self.driver, debug=True)
        else:
            self.journal = MORJournal(self.driver, debug=True)
            
        self.journal.login()
        self.take_screenshot("after_login")
        
        # Navigate to AE Center
        ae_link = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
        )
        ae_link.click()
        time.sleep(3)
        self.take_screenshot("ae_center")
        
    def discover_categories_with_manuscripts(self):
        """Dynamically discover all categories that have manuscripts"""
        logger.info("🔍 Dynamically discovering categories with manuscripts...")
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        page_text = soup.get_text()
        
        # Save HTML for debugging
        with open(self.debug_dir / "ae_center_page.html", "w", encoding='utf-8') as f:
            f.write(self.driver.page_source)
            
        # Strategy: Parse the manuscript count structure
        # Look for patterns like "2Awaiting Reviewer Scores" or "3Awaiting Reviewer Reports"
        
        categories_with_counts = []
        
        # Pattern 1: Look for number followed by category name
        category_patterns = [
            r'(\d+)\s*([A-Z][A-Za-z\s]+(?:Reviewer|Review|Awaiting|Overdue)[A-Za-z\s]*)',
            r'(\d+)\s*(Awaiting[A-Za-z\s]+)',
            r'(\d+)\s*(Overdue[A-Za-z\s]+)'
        ]
        
        for pattern in category_patterns:
            matches = re.findall(pattern, page_text)
            for count, category_name in matches:
                count = int(count)
                category_name = category_name.strip()
                
                # Filter for realistic category names
                if (count > 0 and 
                    len(category_name) > 5 and 
                    any(word in category_name.lower() for word in ['awaiting', 'overdue', 'reviewer', 'review'])):
                    
                    categories_with_counts.append({
                        'name': category_name,
                        'count': count
                    })
                    
        # Remove duplicates and sort by count
        seen = set()
        unique_categories = []
        for cat in categories_with_counts:
            key = cat['name'].lower().strip()
            if key not in seen:
                seen.add(key)
                unique_categories.append(cat)
                
        unique_categories.sort(key=lambda x: x['count'], reverse=True)
        
        logger.info(f"📊 Discovered categories with manuscripts:")
        for cat in unique_categories:
            logger.info(f"  • {cat['name']}: {cat['count']} manuscripts")
            
        self.discovered_categories = unique_categories
        return unique_categories
        
    def process_category(self, category_name, expected_count):
        """Process a specific category"""
        logger.info(f"\\n{'='*60}")
        logger.info(f"🎯 Processing: {category_name} (expecting {expected_count} manuscripts)")
        logger.info(f"{'='*60}")
        
        try:
            # Try to find and click the category link
            category_link = self.driver.find_element(By.LINK_TEXT, category_name)
            self.take_screenshot(f"before_{category_name.replace(' ', '_')}")
            
            category_link.click()
            time.sleep(3)
            self.take_screenshot(f"after_{category_name.replace(' ', '_')}")
            
            # Extract manuscripts and referee information
            manuscripts = self.extract_manuscripts_and_referees(category_name)
            
            logger.info(f"✅ Successfully processed {category_name}: found {len(manuscripts)} manuscripts")
            
            # Navigate back to AE Center
            ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
            ae_link.click()
            time.sleep(2)
            
            return manuscripts
            
        except Exception as e:
            logger.error(f"❌ Failed to process {category_name}: {e}")
            return []
            
    def extract_manuscripts_and_referees(self, category_name):
        """Extract manuscripts and referee information from current page"""
        logger.info("📊 Extracting manuscripts and referee information...")
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        page_text = soup.get_text()
        
        # Find manuscript IDs
        if self.journal_name == "MF":
            ms_pattern = r'MAFI-\d{4}-\d+'
        else:
            ms_pattern = r'MOR-\d{4}-\d+'
            
        ms_ids = list(set(re.findall(ms_pattern, page_text)))
        logger.info(f"Found manuscript IDs: {ms_ids}")
        
        manuscripts = []
        
        # For each manuscript, extract referee information
        for ms_id in ms_ids:
            logger.info(f"Processing referee info for {ms_id}")
            
            try:
                # Find the table row containing this manuscript
                for element in soup.find_all(string=re.compile(ms_id)):
                    parent_row = element.parent
                    
                    # Traverse up to find the table row
                    while parent_row and parent_row.name != 'tr':
                        parent_row = parent_row.parent
                        
                    if parent_row:
                        row_text = parent_row.get_text()
                        
                        # Look for referee information patterns
                        if ('active selections' in row_text or 'invited' in row_text or 
                            'agreed' in row_text or 'declined' in row_text):
                            
                            logger.info(f"Found referee info for {ms_id}")
                            
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
                            
                            manuscript_data = {
                                'manuscript_id': ms_id,
                                'category': category_name,
                                'referee_info': {
                                    'active_selections': active_count,
                                    'invited': invited_count,
                                    'agreed': agreed_count,
                                    'declined': declined_count,
                                    'returned': returned_count,
                                    'active_referees': agreed_count  # Active = agreed
                                },
                                'raw_text': row_text.strip()
                            }
                            
                            manuscripts.append(manuscript_data)
                            logger.info(f"  ✅ {ms_id}: {active_count} active, {invited_count} invited, {agreed_count} agreed, {declined_count} declined")
                            break
                            
            except Exception as e:
                logger.warning(f"Error processing {ms_id}: {e}")
                
        return manuscripts
        
    def run_comprehensive_test(self):
        """Run comprehensive dynamic scraping test"""
        logger.info("🚀 Starting Dynamic Comprehensive Scraper...")
        
        self.create_driver()
        
        try:
            # Login and navigate
            self.login_and_navigate_to_ae_center()
            
            # Discover categories dynamically
            categories = self.discover_categories_with_manuscripts()
            
            if not categories:
                logger.warning("⚠️ No categories with manuscripts found!")
                return
                
            # Process each category that has manuscripts
            all_manuscripts = []
            total_referees = 0
            
            for category in categories:
                manuscripts = self.process_category(category['name'], category['count'])
                all_manuscripts.extend(manuscripts)
                
            # Calculate totals
            for ms in all_manuscripts:
                total_referees += ms['referee_info']['active_referees']
                
            # Generate results
            self.generate_comprehensive_report(categories, all_manuscripts, total_referees)
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            self.take_screenshot("fatal_error")
            
        finally:
            self.driver.quit()
            
    def generate_comprehensive_report(self, categories, manuscripts, total_referees):
        """Generate comprehensive test report"""
        logger.info("\\n" + "="*80)
        logger.info(f"📊 DYNAMIC COMPREHENSIVE RESULTS FOR {self.journal_name}")
        logger.info("="*80)
        
        # Expected values (from user requirements)
        if self.journal_name == "MF":
            expected_mss, expected_refs = 2, 4
        else:
            expected_mss, expected_refs = 3, 5
            
        logger.info(f"📋 Categories discovered: {len(categories)}")
        for cat in categories:
            logger.info(f"  • {cat['name']}: {cat['count']} manuscripts")
            
        logger.info(f"\\n📄 Manuscripts processed: {len(manuscripts)} (expected: {expected_mss})")
        logger.info(f"🧑‍💼 Total active referees: {total_referees} (expected: {expected_refs})")
        
        # Detailed breakdown
        logger.info(f"\\n📊 DETAILED BREAKDOWN:")
        for ms in manuscripts:
            ms_id = ms['manuscript_id']
            category = ms['category']
            ref_info = ms['referee_info']
            active = ref_info['active_referees']
            
            logger.info(f"  📄 {ms_id} ({category}): {active} active referees")
            
        # Success evaluation
        if len(manuscripts) >= expected_mss and total_referees >= expected_refs:
            logger.info(f"\\n✅ SUCCESS: Dynamic scraper found all expected data!")
            success = True
        else:
            logger.info(f"\\n⚠️ PARTIAL: Found {len(manuscripts)}/{expected_mss} manuscripts, {total_referees}/{expected_refs} referees")
            success = False
            
        # Save detailed report
        report = {
            'journal': self.journal_name,
            'timestamp': datetime.now().isoformat(),
            'discovered_categories': categories,
            'processed_manuscripts': manuscripts,
            'total_manuscripts': len(manuscripts),
            'total_active_referees': total_referees,
            'expected_manuscripts': expected_mss,
            'expected_referees': expected_refs,
            'success': success,
            'test_type': 'dynamic_comprehensive'
        }
        
        report_file = self.debug_dir / "dynamic_comprehensive_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"\\n💾 Detailed report saved to: {report_file}")
        return report

def main():
    """Test both journals with dynamic discovery"""
    
    # Test MF
    logger.info("\\n" + "="*80)
    logger.info("TESTING MF WITH DYNAMIC DISCOVERY")
    logger.info("="*80)
    
    mf_scraper = DynamicComprehensiveScraper("MF")
    mf_scraper.run_comprehensive_test()
    
    # Test MOR  
    logger.info("\\n" + "="*80)
    logger.info("TESTING MOR WITH DYNAMIC DISCOVERY")
    logger.info("="*80)
    
    mor_scraper = DynamicComprehensiveScraper("MOR")
    mor_scraper.run_comprehensive_test()

if __name__ == "__main__":
    main()