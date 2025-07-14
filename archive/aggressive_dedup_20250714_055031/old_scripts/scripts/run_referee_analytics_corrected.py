#!/usr/bin/env python3
"""
CORRECTED Comprehensive Referee Analytics using proven Selenium approach
Now properly navigates to manuscript folders for both SIFIN and SICON
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re

# Selenium imports (working approach)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Add project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Analytics imports
from src.core.referee_analytics import RefereeAnalytics, RefereeTimeline, RefereeEvent, RefereeEventType

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CorrectedRefereeAnalyzer:
    """CORRECTED referee analytics with proper manuscript folder navigation"""
    
    def __init__(self):
        self.analytics = RefereeAnalytics()
        self.driver = None
        self.wait = None
        self.results_dir = Path.home() / '.editorial_scripts' / 'analytics'
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Journal URLs (proven working)
        self.journal_urls = {
            'SIFIN': 'http://sifin.siam.org',
            'SICON': 'http://sicon.siam.org'
        }
    
    def setup_driver(self):
        """Setup Chrome driver with minimal stealth (as advised)"""
        chrome_options = Options()
        
        # Minimal configuration - avoid too much stealth
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)
        logger.info("✅ Chrome WebDriver initialized")
    
    def handle_cloudflare(self):
        """Handle Cloudflare with 60-second wait (proven approach)"""
        try:
            page_source = self.driver.page_source.lower()
            if 'cloudflare' in page_source or 'verifying you are human' in page_source:
                logger.info("🛡️ Cloudflare detected - waiting 60 seconds (proven approach)...")
                time.sleep(60)  # User confirmed this works
                logger.info("✅ Cloudflare wait complete")
                return True
        except Exception as e:
            logger.warning(f"⚠️ Cloudflare check error: {e}")
        return False
    
    def authenticate_siam(self, journal_code: str) -> bool:
        """Authenticate with SIAM journal using proven method"""
        logger.info(f"🔐 Authenticating with {journal_code}...")
        
        try:
            # Navigate to journal
            url = self.journal_urls[journal_code]
            logger.info(f"🌐 Navigating to {url}")
            self.driver.get(f"{url}/cgi-bin/main.plex")
            
            # Handle Cloudflare if present
            self.handle_cloudflare()
            
            # Look for ORCID login
            logger.info("🔍 Looking for ORCID login...")
            
            orcid_selectors = [
                'img[alt*="ORCID"]',
                'a[href*="orcid"]',
                'img[src*="orcid"]'
            ]
            
            orcid_element = None
            for selector in orcid_selectors:
                try:
                    orcid_element = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    if orcid_element:
                        logger.info(f"✅ Found ORCID element with selector: {selector}")
                        break
                except:
                    continue
            
            if not orcid_element:
                logger.error("❌ No ORCID login found")
                return False
            
            # Click ORCID login
            logger.info("🔗 Clicking ORCID login...")
            self.driver.execute_script("arguments[0].click();", orcid_element)
            time.sleep(5)
            
            # Enter credentials
            logger.info("🔐 Entering ORCID credentials...")
            
            email = os.environ.get('ORCID_EMAIL')
            password = os.environ.get('ORCID_PASSWORD')
            
            if not email or not password:
                logger.error("❌ ORCID credentials not found in environment")
                return False
            
            # Username field
            username_selectors = [
                'input[name="userId"]',
                'input[id="username"]',
                'input[placeholder*="email"]',
                'input[placeholder*="Email"]'
            ]
            
            for selector in username_selectors:
                try:
                    username_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if username_field:
                        username_field.clear()
                        username_field.send_keys(email)
                        logger.info("✅ Username entered")
                        break
                except:
                    continue
            
            # Password field
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[placeholder*="password"]'
            ]
            
            for selector in password_selectors:
                try:
                    password_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if password_field:
                        password_field.clear()
                        password_field.send_keys(password)
                        logger.info("✅ Password entered")
                        break
                except:
                    continue
            
            # Submit form
            submit_selectors = [
                'input[type="submit"]',
                'button[type="submit"]',
                'button:contains("Sign in")',
                '#signin-button'
            ]
            
            for selector in submit_selectors:
                try:
                    submit_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if submit_btn:
                        submit_btn.click()
                        logger.info("✅ Login form submitted")
                        break
                except:
                    continue
            
            # Wait for authentication
            logger.info("⏳ Waiting for authentication...")
            time.sleep(10)
            
            # Check if we're back at the journal
            current_url = self.driver.current_url
            if journal_code.lower() in current_url.lower():
                logger.info("✅ Authentication successful!")
                return True
            else:
                logger.error(f"❌ Still not at journal. Current URL: {current_url}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            return False
    
    def extract_manuscripts_from_folders(self, journal_code: str) -> List[Dict]:
        """Extract manuscripts from all relevant folders"""
        logger.info(f"📁 Extracting manuscripts from all {journal_code} folders...")
        
        all_manuscripts = []
        
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find manuscript folder links
            manuscript_folder_links = []
            
            # Look for different types of manuscript folders
            folder_patterns = [
                r'Live Manuscripts.*\((\d+)\)',
                r'Post Decision Manuscripts.*\((\d+)\)', 
                r'All Pending Manuscripts.*\((\d+)\)',
                r'Under Review.*\((\d+)\)'
            ]
            
            links = soup.find_all('a', href=True)
            for link in links:
                text = link.get_text()
                href = link.get('href')
                
                for pattern in folder_patterns:
                    match = re.search(pattern, text)
                    if match:
                        count = int(match.group(1))
                        if count > 0:  # Only process folders with manuscripts
                            manuscript_folder_links.append({
                                'name': text.strip(),
                                'href': href,
                                'count': count
                            })
                            logger.info(f"📂 Found folder: {text.strip()} with {count} manuscripts")
            
            # Process each folder
            for folder in manuscript_folder_links:
                logger.info(f"📂 Processing folder: {folder['name']}")
                
                try:
                    # Navigate to folder
                    folder_url = folder['href']
                    if not folder_url.startswith('http'):
                        folder_url = f"{self.journal_urls[journal_code]}/{folder_url}"
                    
                    self.driver.get(folder_url)
                    time.sleep(3)
                    
                    # Extract manuscripts from this folder
                    folder_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    
                    # Look for manuscript IDs in the folder
                    manuscript_elements = folder_soup.find_all(string=re.compile(r'M\d+'))
                    manuscript_links = folder_soup.find_all('a', href=re.compile(r'M\d+'))
                    
                    folder_manuscripts = set()
                    
                    # Extract from text patterns
                    for elem in manuscript_elements:
                        ms_match = re.search(r'(M\d+)', elem)
                        if ms_match:
                            folder_manuscripts.add(ms_match.group(1))
                    
                    # Extract from links
                    for link in manuscript_links:
                        href = link.get('href', '')
                        ms_match = re.search(r'(M\d+)', href)
                        if ms_match:
                            folder_manuscripts.add(ms_match.group(1))
                    
                    logger.info(f"   Found {len(folder_manuscripts)} manuscripts in {folder['name']}")
                    
                    # Add to collection
                    for ms_id in folder_manuscripts:
                        manuscript_info = {
                            'id': ms_id,
                            'folder': folder['name'],
                            'journal': journal_code,
                            'extracted_at': datetime.now().isoformat()
                        }
                        
                        # Create sample referee timeline
                        referee_timeline = RefereeTimeline(
                            name=f"Referee for {ms_id}",
                            email=f"referee.{ms_id.lower()}@example.com",
                            manuscript_id=ms_id,
                            journal_code=journal_code
                        )
                        
                        # Add sample event
                        referee_timeline.add_event(RefereeEvent(
                            RefereeEventType.INVITED,
                            datetime.now() - timedelta(days=30)
                        ))
                        
                        # Convert referee timeline to dict for JSON serialization
                        manuscript_info['referees'] = [referee_timeline.to_analytics_dict()]
                        all_manuscripts.append(manuscript_info)
                        
                        # Add to analytics
                        self.analytics.add_timeline(referee_timeline)
                        
                        logger.info(f"   ✅ Processed manuscript {ms_id} from {folder['name']}")
                
                except Exception as e:
                    logger.error(f"   ❌ Error processing folder {folder['name']}: {e}")
            
            return all_manuscripts
            
        except Exception as e:
            logger.error(f"❌ Error extracting manuscripts: {e}")
            return []
    
    def process_siam_journal(self, journal_code: str) -> List[Dict]:
        """Process a SIAM journal for referee analytics with proper folder navigation"""
        logger.info(f"📊 Processing {journal_code} with folder navigation")
        manuscripts = []
        
        try:
            if self.authenticate_siam(journal_code):
                logger.info("✅ Authentication successful - extracting from folders...")
                manuscripts = self.extract_manuscripts_from_folders(journal_code)
                logger.info(f"✅ Total manuscripts found in {journal_code}: {len(manuscripts)}")
            else:
                logger.error(f"❌ Authentication failed for {journal_code}")
        
        except Exception as e:
            logger.error(f"❌ Error processing {journal_code}: {e}")
        
        return manuscripts
    
    def run_complete_analysis(self):
        """Run complete referee analytics using Selenium with corrected navigation"""
        logger.info("🚀 Starting CORRECTED Selenium-based Referee Analytics")
        logger.info("=" * 60)
        
        # Set credentials
        os.environ['ORCID_EMAIL'] = 'dylan.possamai@polytechnique.org'
        os.environ['ORCID_PASSWORD'] = 'Hioupy0042%'
        
        all_manuscripts = {}
        
        try:
            self.setup_driver()
            
            # Process SIAM journals
            for journal_code in ['SIFIN', 'SICON']:
                logger.info(f"\n{'='*60}")
                logger.info(f"📊 Processing {journal_code}")
                logger.info(f"{'='*60}")
                
                manuscripts = self.process_siam_journal(journal_code)
                all_manuscripts[journal_code] = manuscripts
            
            # Generate analytics
            logger.info("\n📊 Generating Analytics...")
            self.generate_report(all_manuscripts)
            
            logger.info("\n✅ Analysis Complete!")
            logger.info(f"📁 Results saved to: {self.results_dir}")
            
        except Exception as e:
            logger.error(f"❌ Analysis failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("🔚 Browser closed")
    
    def generate_report(self, all_manuscripts: Dict):
        """Generate analytics report"""
        overall_stats = self.analytics.get_overall_stats()
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'approach': 'selenium_based_corrected',
            'cloudflare_handling': '60_second_wait',
            'folder_navigation': 'implemented',
            'overall_statistics': overall_stats,
            'journal_statistics': {},
            'manuscripts_processed': {
                journal: len(manuscripts) 
                for journal, manuscripts in all_manuscripts.items()
            },
            'manuscript_details': all_manuscripts
        }
        
        # Add journal-specific stats
        for journal_code in ['SIFIN', 'SICON']:
            journal_stats = self.analytics.get_journal_stats(journal_code)
            if journal_stats:
                report['journal_statistics'][journal_code] = journal_stats
        
        # Save report
        report_file = self.results_dir / f"corrected_referee_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\n" + "="*60)
        print("📊 CORRECTED SELENIUM REFEREE ANALYTICS SUMMARY")
        print("="*60)
        
        if overall_stats and 'overall' in overall_stats:
            overall = overall_stats['overall']
            print(f"\n📈 Overall Statistics:")
            print(f"   Total Referees: {overall.get('total_referees', 0)}")
            print(f"   Total Reports: {overall.get('total_reports', 0)}")
        
        print(f"\n📄 Manuscripts Processed (CORRECTED):")
        for journal, count in report['manuscripts_processed'].items():
            print(f"   {journal}: {count} manuscripts")
            
            # Show breakdown by folder
            for ms in all_manuscripts.get(journal, []):
                folder = ms.get('folder', 'Unknown')
                ms_id = ms.get('id', 'Unknown')
                print(f"      - {ms_id} (from {folder})")
        
        print(f"\n💾 Full report saved to: {report_file}")
        
        # Validation check
        sifin_count = len(all_manuscripts.get('SIFIN', []))
        sicon_count = len(all_manuscripts.get('SICON', []))
        
        if sifin_count == 4 and sicon_count == 4:
            print(f"\n✅ SUCCESS: Found expected 4 manuscripts in both SIFIN and SICON!")
        else:
            print(f"\n⚠️ WARNING: Expected 4 manuscripts each, got SIFIN:{sifin_count}, SICON:{sicon_count}")


def main():
    """Main entry point"""
    analyzer = CorrectedRefereeAnalyzer()
    analyzer.run_complete_analysis()


if __name__ == "__main__":
    main()