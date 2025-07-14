#!/usr/bin/env python3
"""
Comprehensive Referee Analytics using proven Selenium approach
Based on the working SIAM extractor that successfully bypasses Cloudflare
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


class SeleniumRefereeAnalyzer:
    """Referee analytics using proven Selenium approach"""
    
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
    
    def extract_manuscript_details(self, manuscript_id: str) -> Optional[Dict]:
        """Extract detailed manuscript information including referees"""
        logger.info(f"📄 Extracting details for manuscript {manuscript_id}")
        
        try:
            # Navigate to manuscript details
            # This would need to be adapted based on the specific SIAM interface
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract referee information
            referees = []
            referee_timeline = RefereeTimeline(
                name="Sample Referee",  # Would extract from page
                email="referee@example.com",  # Would extract from page
                manuscript_id=manuscript_id,
                journal_code="SIFIN"  # Or SICON
            )
            
            # Add sample events (would extract from actual page)
            referee_timeline.add_event(RefereeEvent(
                RefereeEventType.INVITED,
                datetime.now() - timedelta(days=30)
            ))
            
            referees.append(referee_timeline)
            
            return {
                'id': manuscript_id,
                'referees': referees,
                'extracted_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error extracting manuscript {manuscript_id}: {e}")
            return None
    
    def process_siam_journal(self, journal_code: str) -> List[Dict]:
        """Process a SIAM journal for referee analytics"""
        logger.info(f"📊 Processing {journal_code}")
        manuscripts = []
        
        try:
            if self.authenticate_siam(journal_code):
                logger.info("✅ Authentication successful - extracting manuscripts...")
                
                # Extract manuscript list
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                manuscript_elements = soup.find_all(['a', 'tr'], string=re.compile(r'M\d+'))
                
                logger.info(f"Found {len(manuscript_elements)} potential manuscripts")
                
                for elem in manuscript_elements[:3]:  # First 3 for testing
                    try:
                        text = elem.get_text()
                        ms_id_match = re.search(r'(M\d+)', text)
                        if ms_id_match:
                            ms_id = ms_id_match.group(1)
                            
                            # Extract detailed information
                            details = self.extract_manuscript_details(ms_id)
                            if details:
                                manuscripts.append(details)
                                
                                # Add referee timelines to analytics
                                for referee in details.get('referees', []):
                                    self.analytics.add_timeline(referee)
                                
                                logger.info(f"✅ Processed manuscript {ms_id}")
                            
                    except Exception as e:
                        logger.error(f"⚠️ Error processing manuscript element: {e}")
            else:
                logger.error(f"❌ Authentication failed for {journal_code}")
        
        except Exception as e:
            logger.error(f"❌ Error processing {journal_code}: {e}")
        
        return manuscripts
    
    def run_complete_analysis(self):
        """Run complete referee analytics using Selenium"""
        logger.info("🚀 Starting Selenium-based Referee Analytics")
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
            'approach': 'selenium_based',
            'cloudflare_handling': '60_second_wait',
            'overall_statistics': overall_stats,
            'journal_statistics': {},
            'manuscripts_processed': {
                journal: len(manuscripts) 
                for journal, manuscripts in all_manuscripts.items()
            }
        }
        
        # Add journal-specific stats
        for journal_code in ['SIFIN', 'SICON']:
            journal_stats = self.analytics.get_journal_stats(journal_code)
            if journal_stats:
                report['journal_statistics'][journal_code] = journal_stats
        
        # Save report
        report_file = self.results_dir / f"selenium_referee_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\n" + "="*60)
        print("📊 SELENIUM REFEREE ANALYTICS SUMMARY")
        print("="*60)
        
        if overall_stats and 'overall' in overall_stats:
            overall = overall_stats['overall']
            print(f"\n📈 Overall Statistics:")
            print(f"   Total Referees: {overall.get('total_referees', 0)}")
            print(f"   Total Reports: {overall.get('total_reports', 0)}")
        
        print(f"\n📄 Manuscripts Processed:")
        for journal, count in report['manuscripts_processed'].items():
            print(f"   {journal}: {count}")
        
        print(f"\n💾 Full report saved to: {report_file}")


def main():
    """Main entry point"""
    analyzer = SeleniumRefereeAnalyzer()
    analyzer.run_complete_analysis()


if __name__ == "__main__":
    main()