#!/usr/bin/env python3
"""
Comprehensive MF and MOR scraper that finds ALL manuscripts, not just those in specific status queues.
This version performs deep scanning of all manuscript data on the Associate Editor pages.
"""

import os
import sys
import time
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.email_utils import fetch_starred_emails, robust_match_email_for_referee_mf, robust_match_email_for_referee_mor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'comprehensive_scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ComprehensiveMFMORScraper:
    """Enhanced scraper that finds ALL manuscripts by deep scanning"""
    
    def __init__(self, timeout_minutes: int = 20):
        self.timeout_seconds = timeout_minutes * 60
        self.session_id = f"comprehensive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.output_dir = Path("comprehensive_output")
        self.output_dir.mkdir(exist_ok=True)
        
        self.results = {
            'session_id': self.session_id,
            'start_time': datetime.now().isoformat(),
            'journals': {},
            'summary': {}
        }
        
    def create_robust_driver(self) -> uc.Chrome:
        """Create a robust Chrome driver"""
        logger.info("🚗 Creating robust Chrome driver...")
        
        options = uc.ChromeOptions()
        
        # Anti-detection options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Performance options
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        
        # User agent
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Window size
        options.add_argument('--window-size=1920,1080')
        
        try:
            # Try with current Chrome version first
            driver = uc.Chrome(options=options)
            logger.info("✅ Chrome driver created successfully")
            return driver
        except Exception as e:
            logger.warning(f"⚠️ Undetected ChromeDriver failed: {e}")
            logger.info("🔄 Trying with standard ChromeDriver...")
            
            # Fallback to standard ChromeDriver
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                chrome_options = Options()
                
                # Copy options from undetected to standard
                for arg in options.arguments:
                    chrome_options.add_argument(arg)
                
                driver = webdriver.Chrome(options=chrome_options)
                logger.info("✅ Standard Chrome driver created successfully")
                return driver
            except Exception as e2:
                logger.error(f"❌ All driver creation methods failed: {e2}")
                raise
    
    def save_debug_info(self, driver: uc.Chrome, journal_name: str, stage: str):
        """Save debug information"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        try:
            # Save screenshot
            screenshot_path = self.output_dir / f"{journal_name}_{stage}_{timestamp}.png"
            driver.save_screenshot(str(screenshot_path))
            logger.info(f"📸 Screenshot: {screenshot_path}")
            
            # Save HTML
            html_path = self.output_dir / f"{journal_name}_{stage}_{timestamp}.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            logger.info(f"📄 HTML: {html_path}")
            
            # Save URL info
            url_info = {
                'url': driver.current_url,
                'title': driver.title,
                'timestamp': timestamp,
                'stage': stage
            }
            url_path = self.output_dir / f"{journal_name}_{stage}_{timestamp}_info.json"
            with open(url_path, 'w') as f:
                json.dump(url_info, f, indent=2)
            
        except Exception as e:
            logger.error(f"❌ Failed to save debug info: {e}")
    
    def comprehensive_manuscript_search(self, driver: uc.Chrome, journal_name: str) -> List[Dict[str, Any]]:
        """Perform comprehensive search for ALL manuscripts on the page"""
        logger.info(f"🔍 Starting comprehensive manuscript search for {journal_name}")
        
        manuscripts = []
        
        # Get page source
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Pattern for manuscript IDs
        if journal_name == 'MF':
            manuscript_pattern = r'(MAFI-\d{4}-\d+(?:\.\w+)?)'
            email_key = 'MF'
        else:  # MOR
            manuscript_pattern = r'(MOR-\d{4}-\d+(?:\.\w+)?)'
            email_key = 'MOR'
        
        # Find all manuscript IDs on the page
        manuscript_ids = set()
        
        # Search in all text content
        all_text = soup.get_text()
        for match in re.finditer(manuscript_pattern, all_text):
            manuscript_ids.add(match.group(1))
        
        # Search in all table cells and links
        for element in soup.find_all(['td', 'a', 'b', 'span', 'div']):
            text = element.get_text(strip=True)
            for match in re.finditer(manuscript_pattern, text):
                manuscript_ids.add(match.group(1))
        
        logger.info(f"📋 Found {len(manuscript_ids)} unique manuscript IDs: {list(manuscript_ids)}")
        
        # Get emails for cross-referencing
        try:
            logger.info(f"📧 Fetching emails for {journal_name}...")
            flagged_emails = fetch_starred_emails(email_key)
            logger.info(f"📧 Retrieved {len(flagged_emails)} flagged emails")
        except Exception as e:
            logger.warning(f"⚠️ Failed to fetch emails: {e}")
            flagged_emails = []
        
        # For each manuscript ID, try to extract detailed information
        for ms_id in manuscript_ids:
            try:
                logger.info(f"🔍 Extracting details for {ms_id}...")
                
                # Look for the manuscript in tables
                manuscript_data = self.extract_manuscript_details(soup, ms_id, journal_name, flagged_emails)
                
                if manuscript_data:
                    manuscripts.append(manuscript_data)
                    logger.info(f"✅ Successfully extracted data for {ms_id}")
                else:
                    logger.warning(f"⚠️ Could not extract full details for {ms_id}")
                    
            except Exception as e:
                logger.error(f"❌ Error extracting details for {ms_id}: {e}")
                continue
        
        # Try to find more manuscripts by clicking through different sections
        manuscripts.extend(self.explore_manuscript_sections(driver, journal_name, flagged_emails))
        
        # Remove duplicates
        unique_manuscripts = []
        seen_ids = set()
        for ms in manuscripts:
            ms_id = ms.get('Manuscript #', '')
            if ms_id and ms_id not in seen_ids:
                unique_manuscripts.append(ms)
                seen_ids.add(ms_id)
        
        logger.info(f"📚 Final count: {len(unique_manuscripts)} unique manuscripts found")
        return unique_manuscripts
    
    def extract_manuscript_details(self, soup: BeautifulSoup, ms_id: str, journal_name: str, flagged_emails: List) -> Optional[Dict[str, Any]]:
        """Extract detailed information for a specific manuscript"""
        
        # Look for tables containing this manuscript ID
        target_table = None
        for table in soup.find_all('table'):
            if ms_id in table.get_text():
                target_table = table
                break
        
        if not target_table:
            logger.debug(f"No table found for {ms_id}")
            return None
        
        # Extract basic manuscript info
        manuscript_data = {
            'Manuscript #': ms_id,
            'Title': '',
            'Contact Author': '',
            'Submission Date': '',
            'Referees': []
        }
        
        # Extract title (look for patterns after manuscript ID)
        text_content = target_table.get_text()
        lines = text_content.split('\n')
        
        for i, line in enumerate(lines):
            if ms_id in line:
                # Title is usually in the next few lines
                for j in range(i + 1, min(i + 5, len(lines))):
                    potential_title = lines[j].strip()
                    if potential_title and len(potential_title) > 10 and not re.match(r'^[A-Z][a-z]+,\s+[A-Z]', potential_title):
                        manuscript_data['Title'] = potential_title
                        break
                break
        
        # Extract author (look for "contact" pattern)
        for element in target_table.find_all(text=re.compile(r'\(contact\)')):
            author_text = element.strip()
            # Extract name before "(contact)"
            match = re.search(r'([A-Za-z\-\s,]+)\s*\(contact\)', author_text)
            if match:
                raw_name = match.group(1).strip()
                # Convert "Last, First" to "First Last"
                if ',' in raw_name:
                    parts = raw_name.split(',', 1)
                    if len(parts) == 2:
                        manuscript_data['Contact Author'] = f"{parts[1].strip()} {parts[0].strip()}"
                else:
                    manuscript_data['Contact Author'] = raw_name
                break
        
        # Extract submission date
        for element in target_table.find_all(text=re.compile(r'Submitted:')):
            date_text = element.strip()
            match = re.search(r'Submitted:\s*([\d\w\-]+)', date_text)
            if match:
                manuscript_data['Submission Date'] = match.group(1)
                break
        
        # Extract referee information
        referees = self.extract_referee_info(target_table, ms_id, journal_name, flagged_emails)
        manuscript_data['Referees'] = referees
        
        return manuscript_data
    
    def extract_referee_info(self, table_element, ms_id: str, journal_name: str, flagged_emails: List) -> List[Dict[str, Any]]:
        """Extract referee information from table element"""
        referees = []
        
        # Look for referee tables within the manuscript table
        referee_rows = table_element.find_all('tr')
        
        for row in referee_rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 3:  # Typical referee row has multiple cells
                
                # Check if this row contains referee information
                row_text = row.get_text().lower()
                if any(keyword in row_text for keyword in ['referee', 'reviewer', 'invited', 'agreed', 'declined']):
                    
                    # Extract referee data
                    referee_data = {
                        'Referee Name': '',
                        'Status': '',
                        'Contacted Date': '',
                        'Accepted Date': '',
                        'Due Date': '',
                        'Email': '',
                        'Lateness': ''
                    }
                    
                    # Try to extract name (usually in first cell)
                    if cells:
                        name_text = cells[0].get_text(strip=True)
                        if name_text and len(name_text) > 2:
                            referee_data['Referee Name'] = name_text
                    
                    # Try to extract status
                    status_indicators = ['agreed', 'accepted', 'declined', 'contacted', 'invited']
                    for indicator in status_indicators:
                        if indicator in row_text:
                            referee_data['Status'] = indicator.capitalize()
                            break
                    
                    # Try to match email
                    if flagged_emails and referee_data['Referee Name']:
                        try:
                            if journal_name == 'MF':
                                crossmatch_date, email_addr = robust_match_email_for_referee_mf(
                                    referee_data['Referee Name'], ms_id, referee_data['Status'], flagged_emails
                                )
                            else:  # MOR
                                crossmatch_date, email_addr = robust_match_email_for_referee_mor(
                                    referee_data['Referee Name'], ms_id, referee_data['Status'], flagged_emails
                                )
                            referee_data['Email'] = email_addr
                        except Exception as e:
                            logger.debug(f"Email matching failed for {referee_data['Referee Name']}: {e}")
                    
                    if referee_data['Referee Name']:
                        referees.append(referee_data)
        
        return referees
    
    def explore_manuscript_sections(self, driver: uc.Chrome, journal_name: str, flagged_emails: List) -> List[Dict[str, Any]]:
        """Explore different sections of the page to find more manuscripts"""
        logger.info(f"🔍 Exploring manuscript sections for {journal_name}...")
        
        manuscripts = []
        
        # Try to find and click on different status sections
        try:
            # Look for sections with manuscript counts
            sections_to_check = [
                "Awaiting Reviewer Assignment",
                "Awaiting Reviewer Scores", 
                "Overdue Reviewer Scores",
                "Awaiting Reviewer Selection",
                "Awaiting AE Decision",
                "Under Review",
                "New Submission",
                "Revised Manuscript Submitted"
            ]
            
            for section in sections_to_check:
                try:
                    # Look for this section on the page
                    section_elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{section}')]")
                    
                    for element in section_elements:
                        # Check if there's a number indicating manuscripts
                        parent = element.find_element(By.XPATH, "..")
                        section_text = parent.get_text()
                        
                        # Look for patterns like "2 active selections"
                        if re.search(r'\d+\s+active', section_text):
                            logger.info(f"📋 Found section with manuscripts: {section}")
                            
                            # Try to click on any links in this section
                            links = parent.find_elements(By.TAG_NAME, 'a')
                            for link in links:
                                try:
                                    link.click()
                                    time.sleep(2)
                                    
                                    # Extract manuscripts from the detail page
                                    detail_manuscripts = self.extract_manuscript_details_from_page(driver, journal_name, flagged_emails)
                                    manuscripts.extend(detail_manuscripts)
                                    
                                    # Go back
                                    driver.back()
                                    time.sleep(1)
                                    
                                except Exception as e:
                                    logger.debug(f"Could not click link in {section}: {e}")
                                    continue
                            
                except Exception as e:
                    logger.debug(f"Could not explore section {section}: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"Error exploring manuscript sections: {e}")
        
        return manuscripts
    
    def extract_manuscript_details_from_page(self, driver: uc.Chrome, journal_name: str, flagged_emails: List) -> List[Dict[str, Any]]:
        """Extract manuscript details from current page"""
        manuscripts = []
        
        try:
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for manuscript patterns
            if journal_name == 'MF':
                manuscript_pattern = r'(MAFI-\d{4}-\d+(?:\.\w+)?)'
            else:  # MOR
                manuscript_pattern = r'(MOR-\d{4}-\d+(?:\.\w+)?)'
            
            # Find manuscript IDs
            manuscript_ids = set()
            for match in re.finditer(manuscript_pattern, soup.get_text()):
                manuscript_ids.add(match.group(1))
            
            # Extract details for each manuscript
            for ms_id in manuscript_ids:
                manuscript_data = self.extract_manuscript_details(soup, ms_id, journal_name, flagged_emails)
                if manuscript_data:
                    manuscripts.append(manuscript_data)
            
        except Exception as e:
            logger.debug(f"Error extracting manuscript details from page: {e}")
        
        return manuscripts
    
    def scrape_journal_comprehensive(self, journal_name: str) -> Dict[str, Any]:
        """Comprehensively scrape a journal for ALL manuscripts"""
        logger.info(f"🔬 Starting comprehensive scraping for {journal_name}")
        
        result = {
            'journal': journal_name,
            'scraping_start': datetime.now().isoformat(),
            'manuscripts': [],
            'error': None,
            'success': False
        }
        
        driver = None
        try:
            # Create driver
            driver = self.create_robust_driver()
            
            # Login to journal
            if journal_name == 'MF':
                from journals.mf import MFJournal
                journal = MFJournal(driver, debug=True)
            else:  # MOR
                from journals.mor import MORJournal
                journal = MORJournal(driver, debug=True)
            
            # Login
            journal.login()
            time.sleep(3)
            
            # Save login state
            self.save_debug_info(driver, journal_name, 'after_login')
            
            # Find Associate Editor Center
            ae_found = False
            for attempt in range(10):
                try:
                    links = driver.find_elements(By.XPATH, "//a")
                    for link in links:
                        link_text = link.text.strip().lower()
                        if any(phrase in link_text for phrase in [
                            "associate editor center", 
                            "associate editor centre",
                            "editor center",
                            "assignment center"
                        ]):
                            driver.execute_script("arguments[0].scrollIntoView(true);", link)
                            link.click()
                            time.sleep(2)
                            ae_found = True
                            logger.info(f"✅ Found and clicked Associate Editor Center")
                            break
                    
                    if ae_found:
                        break
                        
                except Exception as e:
                    logger.debug(f"Attempt {attempt + 1} to find AE center failed: {e}")
                    time.sleep(1)
            
            if not ae_found:
                logger.warning("⚠️ Could not find Associate Editor Center, proceeding with current page")
            
            # Save AE center state
            self.save_debug_info(driver, journal_name, 'ae_center')
            
            # Comprehensive manuscript search
            manuscripts = self.comprehensive_manuscript_search(driver, journal_name)
            
            result['manuscripts'] = manuscripts
            result['success'] = True
            result['manuscripts_found'] = len(manuscripts)
            
            logger.info(f"✅ {journal_name} comprehensive scraping completed: {len(manuscripts)} manuscripts")
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"❌ {journal_name} comprehensive scraping failed: {e}")
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
        
        result['scraping_end'] = datetime.now().isoformat()
        return result
    
    def run_comprehensive_scraping(self) -> Dict[str, Any]:
        """Run comprehensive scraping for both journals"""
        logger.info("🎯 Starting Comprehensive MF and MOR Scraping")
        logger.info("=" * 60)
        
        # Scrape both journals
        for journal_name in ['MF', 'MOR']:
            logger.info(f"\\n🔬 Comprehensive scraping for {journal_name}")
            logger.info("-" * 40)
            
            result = self.scrape_journal_comprehensive(journal_name)
            self.results['journals'][journal_name] = result
            
            # Display results
            if result['success']:
                manuscripts = result['manuscripts']
                logger.info(f"✅ {journal_name} SUCCESS: {len(manuscripts)} manuscripts found")
                
                for i, ms in enumerate(manuscripts, 1):
                    logger.info(f"   {i}. {ms['Manuscript #']}: {ms['Title'][:50]}...")
                    logger.info(f"      Author: {ms['Contact Author']}")
                    logger.info(f"      Referees: {len(ms['Referees'])}")
                    
                    # Show referee details
                    for j, ref in enumerate(ms['Referees'], 1):
                        email_status = "✅" if ref['Email'] else "❌"
                        logger.info(f"        {j}. {ref['Referee Name']} ({ref['Status']}) {email_status}")
                        
            else:
                logger.error(f"❌ {journal_name} FAILED: {result.get('error', 'Unknown error')}")
        
        # Generate summary
        total_manuscripts = sum(len(j.get('manuscripts', [])) for j in self.results['journals'].values())
        successful_journals = sum(1 for j in self.results['journals'].values() if j.get('success'))
        
        self.results['summary'] = {
            'total_tested': len(self.results['journals']),
            'successful': successful_journals,
            'success_rate': successful_journals / len(self.results['journals']) if self.results['journals'] else 0,
            'total_manuscripts': total_manuscripts
        }
        
        self.results['end_time'] = datetime.now().isoformat()
        
        # Save results
        results_file = self.output_dir / f"comprehensive_results_{self.session_id}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"\\n📄 Results saved to: {results_file}")
        
        return self.results


def main():
    """Main comprehensive scraping function"""
    print("🔍 Comprehensive MF and MOR Manuscript Scraper")
    print("=" * 60)
    print("This script performs deep scanning to find ALL manuscripts,")
    print("not just those in specific status queues.")
    print("=" * 60)
    
    try:
        # Check credentials
        if not (os.getenv('MF_USER') and os.getenv('MF_PASS') and os.getenv('MOR_USER') and os.getenv('MOR_PASS')):
            print("\\n⚠️ Please ensure all credentials are set:")
            print("MF_USER, MF_PASS, MOR_USER, MOR_PASS")
            
            # Try to load from .env file
            env_file = Path(".env")
            if env_file.exists():
                print("📄 Loading from .env file...")
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key] = value
            else:
                print("❌ No .env file found. Please set up credentials first.")
                return 1
        
        # Run comprehensive scraping
        scraper = ComprehensiveMFMORScraper(timeout_minutes=30)
        results = scraper.run_comprehensive_scraping()
        
        # Display final summary
        print("\\n" + "=" * 60)
        print("📊 COMPREHENSIVE SCRAPING SUMMARY")
        print("=" * 60)
        
        summary = results['summary']
        print(f"Journals Tested: {summary['total_tested']}")
        print(f"Successful: {summary['successful']}")
        print(f"Success Rate: {summary['success_rate']:.1%}")
        print(f"Total Manuscripts Found: {summary['total_manuscripts']}")
        
        # Detailed breakdown
        for journal_name, journal_data in results['journals'].items():
            if journal_data.get('success'):
                manuscripts = journal_data.get('manuscripts', [])
                total_referees = sum(len(ms.get('Referees', [])) for ms in manuscripts)
                print(f"\\n📋 {journal_name} Details:")
                print(f"  Manuscripts: {len(manuscripts)}")
                print(f"  Total Referees: {total_referees}")
                
                for ms in manuscripts:
                    print(f"    • {ms['Manuscript #']}: {len(ms['Referees'])} referees")
        
        print(f"\\n📁 Debug files saved to: {scraper.output_dir}")
        
        if summary['total_manuscripts'] > 0:
            print("\\n✅ Comprehensive scraping completed successfully!")
            return 0
        else:
            print("\\n❌ No manuscripts found.")
            return 1
            
    except Exception as e:
        print(f"\\n❌ Comprehensive scraping failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())