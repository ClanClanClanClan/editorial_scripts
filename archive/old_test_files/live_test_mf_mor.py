#!/usr/bin/env python3
"""
Live testing script for MF and MOR journals with real credentials.
This script provides comprehensive debugging and real data extraction.
"""

import os
import sys
import time
import logging
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import signal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'live_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class LiveJournalTester:
    """Live testing for MF and MOR journals with real credentials"""
    
    def __init__(self, timeout_minutes: int = 10):
        self.timeout_seconds = timeout_minutes * 60
        self.session_id = f"live_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.output_dir = Path("live_test_output")
        self.output_dir.mkdir(exist_ok=True)
        
        self.results = {
            'session_id': self.session_id,
            'start_time': datetime.now().isoformat(),
            'journals': {},
            'summary': {}
        }
        
    def check_credentials(self) -> Dict[str, Any]:
        """Check if credentials are available"""
        logger.info("🔍 Checking for credentials...")
        
        creds_status = {
            'MF': {
                'user': bool(os.getenv('MF_USER')),
                'pass': bool(os.getenv('MF_PASS')),
                'complete': bool(os.getenv('MF_USER') and os.getenv('MF_PASS'))
            },
            'MOR': {
                'user': bool(os.getenv('MOR_USER')),
                'pass': bool(os.getenv('MOR_PASS')),
                'complete': bool(os.getenv('MOR_USER') and os.getenv('MOR_PASS'))
            }
        }
        
        # Try to load from .env file if not in environment
        env_file = Path(".env")
        if env_file.exists():
            logger.info("📄 Loading credentials from .env file...")
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key] = value
                            
                            # Update status
                            if key in ['MF_USER', 'MF_PASS']:
                                creds_status['MF'][key.split('_')[1].lower()] = True
                            elif key in ['MOR_USER', 'MOR_PASS']:
                                creds_status['MOR'][key.split('_')[1].lower()] = True
                
                # Recalculate complete status
                creds_status['MF']['complete'] = creds_status['MF']['user'] and creds_status['MF']['pass']
                creds_status['MOR']['complete'] = creds_status['MOR']['user'] and creds_status['MOR']['pass']
                
            except Exception as e:
                logger.warning(f"⚠️ Error loading .env file: {e}")
        
        for journal, status in creds_status.items():
            if status['complete']:
                logger.info(f"✅ {journal} credentials complete")
            else:
                missing = [k for k, v in status.items() if k != 'complete' and not v]
                logger.warning(f"❌ {journal} missing: {missing}")
        
        return creds_status
    
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
    
    def test_journal_live(self, journal_name: str) -> Dict[str, Any]:
        """Test a journal with live credentials"""
        logger.info(f"🔬 Testing {journal_name} with live credentials")
        
        result = {
            'journal': journal_name,
            'test_start': datetime.now().isoformat(),
            'phases': {
                'connection': {'status': 'pending'},
                'login': {'status': 'pending'},
                'navigation': {'status': 'pending'},
                'scraping': {'status': 'pending'}
            },
            'manuscripts': [],
            'error': None,
            'success': False
        }
        
        driver = None
        try:
            # Set timeout
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Test timeout after {self.timeout_seconds} seconds")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.timeout_seconds)
            
            # Phase 1: Create driver and test connection
            logger.info(f"🌐 Phase 1: Testing connection to {journal_name}")
            driver = self.create_robust_driver()
            
            urls = {
                'MF': 'https://mc.manuscriptcentral.com/mafi',
                'MOR': 'https://mc.manuscriptcentral.com/mathor'
            }
            
            url = urls[journal_name]
            driver.get(url)
            
            # Wait for page load
            WebDriverWait(driver, 30).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            result['phases']['connection'] = {
                'status': 'success',
                'url': url,
                'title': driver.title,
                'load_time': '< 30s'
            }
            
            logger.info(f"✅ Connection successful: {driver.title}")
            self.save_debug_info(driver, journal_name, 'connection')
            
            # Phase 2: Login
            logger.info(f"🔐 Phase 2: Testing login for {journal_name}")
            
            # Import and create journal instance
            if journal_name == 'MF':
                from journals.mf import MFJournal
                journal = MFJournal(driver, debug=True)
            else:  # MOR
                from journals.mor import MORJournal
                journal = MORJournal(driver, debug=True)
            
            # Attempt login
            try:
                journal.login()
                
                result['phases']['login'] = {
                    'status': 'success',
                    'verification_required': getattr(journal, 'activation_required', False),
                    'method': 'standard'
                }
                
                logger.info(f"✅ Login successful for {journal_name}")
                if getattr(journal, 'activation_required', False):
                    logger.info("📧 Verification code was required and handled")
                
                self.save_debug_info(driver, journal_name, 'login_success')
                
            except Exception as login_e:
                result['phases']['login'] = {
                    'status': 'failed',
                    'error': str(login_e)
                }
                logger.error(f"❌ Login failed for {journal_name}: {login_e}")
                self.save_debug_info(driver, journal_name, 'login_failed')
                raise
            
            # Phase 3: Navigation
            logger.info(f"🧭 Phase 3: Testing navigation for {journal_name}")
            
            # Give a moment for post-login processing
            time.sleep(3)
            
            # Look for Associate Editor Center or similar
            ae_found = False
            try:
                # Check for various AE center indicators
                ae_indicators = [
                    "//a[contains(text(), 'Associate Editor Center')]",
                    "//a[contains(text(), 'Associate Editor Centre')]",
                    "//a[contains(text(), 'Editor Center')]",
                    "//a[contains(text(), 'Assignment Center')]"
                ]
                
                for indicator in ae_indicators:
                    elements = driver.find_elements(By.XPATH, indicator)
                    if elements:
                        ae_found = True
                        logger.info(f"✅ Found AE center: {elements[0].text}")
                        break
                
                if not ae_found:
                    # Look for any editor-related links
                    editor_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Editor')]")
                    if editor_links:
                        ae_found = True
                        logger.info(f"✅ Found editor link: {editor_links[0].text}")
                
                result['phases']['navigation'] = {
                    'status': 'success' if ae_found else 'partial',
                    'ae_center_found': ae_found,
                    'page_title': driver.title
                }
                
                self.save_debug_info(driver, journal_name, 'navigation')
                
            except Exception as nav_e:
                result['phases']['navigation'] = {
                    'status': 'failed',
                    'error': str(nav_e)
                }
                logger.warning(f"⚠️ Navigation issues for {journal_name}: {nav_e}")
            
            # Phase 4: Scraping
            logger.info(f"📚 Phase 4: Testing manuscript scraping for {journal_name}")
            
            try:
                # Run the actual scraping
                manuscripts = journal.scrape_manuscripts_and_emails()
                
                result['phases']['scraping'] = {
                    'status': 'success',
                    'manuscripts_found': len(manuscripts),
                    'has_referee_data': any(m.get('Referees') for m in manuscripts),
                    'has_download_data': any(m.get('downloads') for m in manuscripts)
                }
                
                # Process manuscript data for summary
                for manuscript in manuscripts:
                    ms_summary = {
                        'id': manuscript.get('Manuscript #', ''),
                        'title': manuscript.get('Title', '')[:100],
                        'author': manuscript.get('Contact Author', ''),
                        'submission_date': manuscript.get('Submission Date', ''),
                        'referee_count': len(manuscript.get('Referees', [])),
                        'has_emails': any(r.get('Email') for r in manuscript.get('Referees', [])),
                        'has_downloads': bool(manuscript.get('downloads'))
                    }
                    
                    # Add referee summary
                    referees = manuscript.get('Referees', [])
                    if referees:
                        ms_summary['referee_sample'] = {
                            'name': referees[0].get('Referee Name', ''),
                            'status': referees[0].get('Status', ''),
                            'has_email': bool(referees[0].get('Email'))
                        }
                    
                    result['manuscripts'].append(ms_summary)
                
                logger.info(f"✅ Scraping successful: {len(manuscripts)} manuscripts found")
                self.save_debug_info(driver, journal_name, 'scraping_success')
                
            except Exception as scraping_e:
                result['phases']['scraping'] = {
                    'status': 'failed',
                    'error': str(scraping_e)
                }
                logger.error(f"❌ Scraping failed for {journal_name}: {scraping_e}")
                self.save_debug_info(driver, journal_name, 'scraping_failed')
                raise
            
            # If we get here, test was successful
            result['success'] = True
            signal.alarm(0)  # Cancel timeout
            
        except TimeoutError:
            result['error'] = f"Test timed out after {self.timeout_seconds} seconds"
            logger.error(f"⏰ Test timeout for {journal_name}")
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"❌ Test failed for {journal_name}: {e}")
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
        
        result['test_end'] = datetime.now().isoformat()
        return result
    
    def run_live_tests(self) -> Dict[str, Any]:
        """Run live tests for both journals"""
        logger.info("🎯 Starting Live Testing for MF and MOR")
        logger.info("=" * 60)
        
        # Check credentials first
        creds_status = self.check_credentials()
        
        # Test each journal that has credentials
        for journal_name in ['MF', 'MOR']:
            if creds_status[journal_name]['complete']:
                logger.info(f"\n🔬 Testing {journal_name} with live credentials")
                logger.info("-" * 40)
                
                result = self.test_journal_live(journal_name)
                self.results['journals'][journal_name] = result
                
                # Display immediate results
                if result['success']:
                    logger.info(f"✅ {journal_name} test SUCCESSFUL")
                    logger.info(f"   Manuscripts found: {len(result['manuscripts'])}")
                    
                    # Show sample manuscripts
                    for i, ms in enumerate(result['manuscripts'][:2], 1):
                        logger.info(f"   {i}. {ms['id']}: {ms['title'][:50]}...")
                        logger.info(f"      Author: {ms['author']}")
                        logger.info(f"      Referees: {ms['referee_count']} ({'with emails' if ms['has_emails'] else 'no emails'})")
                else:
                    logger.error(f"❌ {journal_name} test FAILED: {result.get('error', 'Unknown error')}")
                    
            else:
                logger.warning(f"⚠️ Skipping {journal_name} - credentials not complete")
                self.results['journals'][journal_name] = {
                    'skipped': True,
                    'reason': 'Credentials not available'
                }
        
        # Generate summary
        tested_journals = [j for j in self.results['journals'].values() if not j.get('skipped')]
        successful_tests = [j for j in tested_journals if j.get('success')]
        
        self.results['summary'] = {
            'total_tested': len(tested_journals),
            'successful': len(successful_tests),
            'success_rate': len(successful_tests) / len(tested_journals) if tested_journals else 0,
            'total_manuscripts': sum(len(j.get('manuscripts', [])) for j in successful_tests)
        }
        
        self.results['end_time'] = datetime.now().isoformat()
        
        # Save results
        results_file = self.output_dir / f"live_test_results_{self.session_id}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"\n📄 Full results saved to: {results_file}")
        
        return self.results


def main():
    """Main live testing function"""
    print("🔬 Live Testing for MF and MOR Journals")
    print("=" * 50)
    print("This script tests MF and MOR journals with real credentials.")
    print("Make sure you have set up your credentials first.")
    print("=" * 50)
    
    # Check if credentials setup is needed
    if not (os.getenv('MF_USER') or os.getenv('MOR_USER')):
        print("\n⚠️  No credentials found in environment variables.")
        print("Please set up credentials first:")
        print("1. Run: python setup_mf_mor_credentials.py")
        print("2. Or set environment variables manually:")
        print("   export MF_USER='your_mf_username'")
        print("   export MF_PASS='your_mf_password'")
        print("   export MOR_USER='your_mor_username'")
        print("   export MOR_PASS='your_mor_password'")
        print("\nAlternatively, create a .env file with these variables.")
        
        response = input("\nContinue anyway? (y/N): ").lower()
        if response != 'y':
            print("Exiting. Set up credentials first.")
            return 1
    
    try:
        # Run live tests
        tester = LiveJournalTester(timeout_minutes=15)
        results = tester.run_live_tests()
        
        # Display final summary
        print("\n" + "=" * 60)
        print("📊 LIVE TESTING SUMMARY")
        print("=" * 60)
        
        summary = results['summary']
        print(f"Journals Tested: {summary['total_tested']}")
        print(f"Successful Tests: {summary['successful']}")
        print(f"Success Rate: {summary['success_rate']:.1%}")
        print(f"Total Manuscripts: {summary['total_manuscripts']}")
        
        # Show journal details
        print("\n📋 Journal Details:")
        for journal_name, journal_data in results['journals'].items():
            if journal_data.get('skipped'):
                print(f"  {journal_name}: SKIPPED ({journal_data['reason']})")
            elif journal_data.get('success'):
                manuscripts = len(journal_data.get('manuscripts', []))
                print(f"  {journal_name}: SUCCESS ({manuscripts} manuscripts)")
            else:
                error = journal_data.get('error', 'Unknown error')
                print(f"  {journal_name}: FAILED ({error})")
        
        print(f"\n📁 Debug files saved to: {tester.output_dir}")
        
        if summary['successful'] > 0:
            print("\n✅ Live testing completed with successful results!")
            return 0
        else:
            print("\n❌ Live testing failed for all journals.")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️ Testing interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Testing failed: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())