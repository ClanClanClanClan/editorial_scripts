#!/usr/bin/env python3
"""
Category Discovery Tool - Finds ALL available categories on AE Center pages
Instead of hardcoding category names, this discovers what actually exists
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
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from journals.mf import MFJournal
from journals.mor import MORJournal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CATEGORY_DISCOVERY")

class CategoryDiscovery:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.discovered_categories = []
        
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
            
    def login_and_navigate_to_ae_center(self):
        """Login and navigate to AE Center"""
        logger.info(f"🔐 Logging into {self.journal_name}")
        
        if self.journal_name == "MF":
            self.journal = MFJournal(self.driver, debug=True)
        else:
            self.journal = MORJournal(self.driver, debug=True)
            
        self.journal.login()
        
        # Navigate to AE Center
        ae_link = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
        )
        ae_link.click()
        time.sleep(3)
        
    def discover_all_categories(self):
        """Discover ALL available categories on the AE Center page"""
        logger.info("🔍 Discovering all available categories...")
        
        # Save HTML for analysis
        with open(f"{self.journal_name.lower()}_ae_center.html", "w", encoding='utf-8') as f:
            f.write(self.driver.page_source)
            
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Strategy 1: Look for links that might be categories
        logger.info("Strategy 1: Finding category links...")
        category_links = []
        
        # Look for all links on the page
        for link in soup.find_all('a'):
            link_text = link.get_text(strip=True)
            
            # Skip empty links or common navigation
            if not link_text or link_text in ['Home', 'Author', 'Review', 'Associate Editor Center', 'Search']:
                continue
                
            # Look for patterns that might be categories
            # Common patterns: "Awaiting...", "Overdue...", "Under..."
            if any(word in link_text.lower() for word in ['awaiting', 'overdue', 'under', 'reviewer', 'review', 'assignment', 'invitation', 'selection', 'score', 'report', 'recommendation']):
                category_links.append(link_text)
                
        logger.info(f"Found potential category links: {category_links}")
        
        # Strategy 2: Look for category counts (e.g., "Category Name (5)")
        logger.info("Strategy 2: Finding categories with counts...")
        page_text = soup.get_text()
        
        # Look for patterns like "Category Name (number)"
        count_patterns = re.findall(r'([^()]+)\s*\((\d+)\)', page_text)
        categories_with_counts = []
        
        for text, count in count_patterns:
            text = text.strip()
            count = int(count)
            
            # Filter for category-like text
            if any(word in text.lower() for word in ['awaiting', 'overdue', 'under', 'reviewer', 'review']):
                categories_with_counts.append({
                    'name': text,
                    'count': count,
                    'clickable': text in category_links
                })
                
        logger.info(f"Found categories with counts: {categories_with_counts}")
        
        # Strategy 3: Look for table headers or section headers
        logger.info("Strategy 3: Finding section headers...")
        headers = []
        
        for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'th', 'td']):
            header_text = tag.get_text(strip=True)
            if header_text and any(word in header_text.lower() for word in ['awaiting', 'overdue', 'under', 'reviewer']):
                headers.append(header_text)
                
        logger.info(f"Found relevant headers: {headers}")
        
        # Strategy 4: Look for any text containing manuscript patterns
        logger.info("Strategy 4: Finding manuscript ID patterns...")
        if self.journal_name == "MF":
            ms_pattern = r'MAFI-\d{4}-\d+'
        else:
            ms_pattern = r'MOR-\d{4}-\d+'
            
        manuscript_contexts = []
        for match in re.finditer(ms_pattern, page_text):
            # Get surrounding context
            start = max(0, match.start() - 100)
            end = min(len(page_text), match.end() + 100)
            context = page_text[start:end].strip()
            manuscript_contexts.append(context)
            
        logger.info(f"Found {len(manuscript_contexts)} manuscript contexts")
        
        # Combine all discoveries
        self.discovered_categories = {
            'category_links': category_links,
            'categories_with_counts': categories_with_counts,
            'headers': headers,
            'manuscript_contexts': manuscript_contexts[:3]  # Just show first 3
        }
        
        return self.discovered_categories
        
    def test_category_navigation(self):
        """Test navigation to each discovered category"""
        logger.info("🧪 Testing navigation to discovered categories...")
        
        navigation_results = {}
        
        # Test each category link
        for category_name in self.discovered_categories.get('category_links', []):
            logger.info(f"Testing navigation to: {category_name}")
            
            try:
                # Try to find and click the category
                category_link = self.driver.find_element(By.LINK_TEXT, category_name)
                
                # Check if it's visible and clickable
                is_visible = category_link.is_displayed()
                is_enabled = category_link.is_enabled()
                
                navigation_results[category_name] = {
                    'found': True,
                    'visible': is_visible,
                    'enabled': is_enabled,
                    'tested_click': False
                }
                
                # Actually test clicking (but navigate back)
                if is_visible and is_enabled:
                    try:
                        category_link.click()
                        time.sleep(2)
                        
                        # Check what page we got
                        current_url = self.driver.current_url
                        page_title = self.driver.title
                        has_manuscripts = bool(re.search(r'(MAFI|MOR)-\d{4}-\d+', self.driver.page_source))
                        
                        navigation_results[category_name].update({
                            'tested_click': True,
                            'result_url': current_url,
                            'result_title': page_title,
                            'has_manuscripts': has_manuscripts
                        })
                        
                        # Navigate back to AE Center
                        ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
                        ae_link.click()
                        time.sleep(2)
                        
                    except Exception as e:
                        navigation_results[category_name]['click_error'] = str(e)
                        
            except Exception as e:
                navigation_results[category_name] = {
                    'found': False,
                    'error': str(e)
                }
                
        return navigation_results
        
    def generate_test_report(self):
        """Generate comprehensive test report"""
        logger.info("📊 Generating test report...")
        
        # Test navigation
        navigation_results = self.test_category_navigation()
        
        # Create comprehensive report
        report = {
            'journal': self.journal_name,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'discovered_categories': self.discovered_categories,
            'navigation_tests': navigation_results,
            'recommendations': [],
            'potential_issues': []
        }
        
        # Analyze results and add recommendations
        working_categories = [name for name, result in navigation_results.items() 
                            if result.get('tested_click') and result.get('has_manuscripts')]
        
        failed_categories = [name for name, result in navigation_results.items() 
                           if not result.get('found') or result.get('click_error')]
        
        if working_categories:
            report['recommendations'].append(f"✅ Working categories: {working_categories}")
        
        if failed_categories:
            report['recommendations'].append(f"❌ Failed categories: {failed_categories}")
            report['potential_issues'].append("Some expected categories are not accessible")
            
        # Check for categories with counts but not working
        counted_categories = [cat['name'] for cat in self.discovered_categories.get('categories_with_counts', []) 
                            if cat['count'] > 0]
        missing_from_working = [cat for cat in counted_categories if cat not in working_categories]
        
        if missing_from_working:
            report['potential_issues'].append(f"Categories with manuscripts but not working: {missing_from_working}")
            
        # Save report
        report_file = f"{self.journal_name.lower()}_category_discovery_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"📄 Report saved to: {report_file}")
        return report
        
    def run(self):
        """Run complete category discovery and testing"""
        self.create_driver()
        
        try:
            self.login_and_navigate_to_ae_center()
            self.discover_all_categories()
            report = self.generate_test_report()
            
            # Print summary
            logger.info("\\n" + "="*80)
            logger.info(f"📊 CATEGORY DISCOVERY REPORT FOR {self.journal_name}")
            logger.info("="*80)
            
            logger.info(f"📋 Category Links Found: {len(self.discovered_categories.get('category_links', []))}")
            logger.info(f"📊 Categories with Counts: {len(self.discovered_categories.get('categories_with_counts', []))}")
            
            for rec in report['recommendations']:
                logger.info(f"✅ {rec}")
                
            for issue in report['potential_issues']:
                logger.info(f"⚠️ {issue}")
                
            return report
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            
        finally:
            self.driver.quit()

def main():
    # Test both journals
    for journal_name in ["MF", "MOR"]:
        logger.info(f"\\n{'='*60}")
        logger.info(f"DISCOVERING CATEGORIES FOR {journal_name}")
        logger.info(f"{'='*60}")
        
        discovery = CategoryDiscovery(journal_name)
        discovery.run()

if __name__ == "__main__":
    main()