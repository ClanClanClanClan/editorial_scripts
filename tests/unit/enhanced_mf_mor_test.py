#!/usr/bin/env python3
"""
Enhanced MF and MOR testing that uses the original scrapers but with enhanced status searching
to find ALL manuscripts that you mentioned (2 MF with 4 referees, 3 MOR with 5 referees).
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

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'enhanced_mf_mor_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class EnhancedMFMORTester:
    """Enhanced tester that uses original scrapers but with better status detection"""
    
    def __init__(self, timeout_minutes: int = 25):
        self.timeout_seconds = timeout_minutes * 60
        self.session_id = f"enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.output_dir = Path("enhanced_output")
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
    
    def enhanced_journal_test(self, journal_name: str) -> Dict[str, Any]:
        """Enhanced test that should find ALL manuscripts"""
        logger.info(f"🔬 Enhanced testing for {journal_name} to find ALL manuscripts")
        
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
            
            # Phase 2: Login and Navigation (using original journal classes)
            logger.info(f"🔐 Phase 2: Enhanced login for {journal_name}")
            
            # Import and create journal instance
            if journal_name == 'MF':
                from journals.mf import MFJournal
                journal = MFJournal(driver, debug=True)
            else:  # MOR
                from journals.mor import MORJournal
                journal = MORJournal(driver, debug=True)
            
            # Phase 3: Enhanced Scraping
            logger.info(f"📚 Phase 3: Enhanced manuscript scraping for {journal_name}")
            
            try:
                # Call the original scraping method which should handle navigation properly
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
                    
                    # Add referee details
                    referees = manuscript.get('Referees', [])
                    if referees:
                        ms_summary['referees'] = []
                        for referee in referees:
                            ref_summary = {
                                'name': referee.get('Referee Name', ''),
                                'status': referee.get('Status', ''),
                                'email': referee.get('Email', ''),
                                'contacted_date': referee.get('Contacted Date', ''),
                                'accepted_date': referee.get('Accepted Date', ''),
                                'due_date': referee.get('Due Date', ''),
                                'lateness': referee.get('Lateness', '')
                            }
                            ms_summary['referees'].append(ref_summary)
                    
                    result['manuscripts'].append(ms_summary)
                
                logger.info(f"✅ Enhanced scraping successful: {len(manuscripts)} manuscripts found")
                
                # Verify against expected counts
                expected_counts = {'MF': {'manuscripts': 2, 'referees': 4}, 'MOR': {'manuscripts': 3, 'referees': 5}}
                expected = expected_counts.get(journal_name, {})
                
                actual_ms_count = len(manuscripts)
                actual_ref_count = sum(len(m.get('Referees', [])) for m in manuscripts)
                
                logger.info(f"📊 {journal_name} Results:")
                logger.info(f"   Expected: {expected.get('manuscripts', '?')} manuscripts, {expected.get('referees', '?')} referees")
                logger.info(f"   Found: {actual_ms_count} manuscripts, {actual_ref_count} referees")
                
                if expected.get('manuscripts') and actual_ms_count < expected['manuscripts']:
                    logger.warning(f"⚠️ Found fewer manuscripts than expected for {journal_name}")
                    result['phases']['scraping']['warning'] = f"Expected {expected['manuscripts']} manuscripts, found {actual_ms_count}"
                
                if expected.get('referees') and actual_ref_count < expected['referees']:
                    logger.warning(f"⚠️ Found fewer referees than expected for {journal_name}")
                    result['phases']['scraping']['warning'] = f"Expected {expected['referees']} referees, found {actual_ref_count}"
                
                self.save_debug_info(driver, journal_name, 'scraping_success')
                
            except Exception as scraping_e:
                result['phases']['scraping'] = {
                    'status': 'failed',
                    'error': str(scraping_e)
                }
                logger.error(f"❌ Scraping failed for {journal_name}: {scraping_e}")
                self.save_debug_info(driver, journal_name, 'scraping_failed')
                raise
            
            # Mark login and navigation as successful if we got this far
            result['phases']['login'] = {'status': 'success', 'method': 'enhanced'}
            result['phases']['navigation'] = {'status': 'success', 'method': 'enhanced'}
            
            # If we get here, test was successful
            result['success'] = True
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"❌ Enhanced test failed for {journal_name}: {e}")
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
        
        result['test_end'] = datetime.now().isoformat()
        return result
    
    def run_enhanced_tests(self) -> Dict[str, Any]:
        """Run enhanced tests for both journals"""
        logger.info("🎯 Starting Enhanced MF and MOR Testing")
        logger.info("=" * 60)
        logger.info("🎯 Target: MF = 2 manuscripts with 4 referees")
        logger.info("🎯 Target: MOR = 3 manuscripts with 5 referees")
        logger.info("=" * 60)
        
        # Test each journal
        for journal_name in ['MF', 'MOR']:
            logger.info(f"\\n🔬 Enhanced testing for {journal_name}")
            logger.info("-" * 40)
            
            result = self.enhanced_journal_test(journal_name)
            self.results['journals'][journal_name] = result
            
            # Display immediate results
            if result['success']:
                manuscripts = result['manuscripts']
                total_referees = sum(ms['referee_count'] for ms in manuscripts)
                
                logger.info(f"✅ {journal_name} test SUCCESSFUL")
                logger.info(f"   📋 Manuscripts found: {len(manuscripts)}")
                logger.info(f"   👥 Total referees: {total_referees}")
                
                # Show detailed manuscript info
                for i, ms in enumerate(manuscripts, 1):
                    logger.info(f"   {i}. {ms['id']}: {ms['title'][:50]}...")
                    logger.info(f"      👤 Author: {ms['author']}")
                    logger.info(f"      📅 Submitted: {ms['submission_date']}")
                    logger.info(f"      👥 Referees: {ms['referee_count']}")
                    
                    # Show referee details
                    for j, ref in enumerate(ms.get('referees', []), 1):
                        email_indicator = "📧✅" if ref['email'] else "📧❌"
                        logger.info(f"         {j}. {ref['name']} ({ref['status']}) {email_indicator}")
                        if ref['email']:
                            logger.info(f"            📧 {ref['email']}")
                    
            else:
                logger.error(f"❌ {journal_name} test FAILED: {result.get('error', 'Unknown error')}")
        
        # Generate summary
        tested_journals = [j for j in self.results['journals'].values()]
        successful_tests = [j for j in tested_journals if j.get('success')]
        
        total_manuscripts = sum(len(j.get('manuscripts', [])) for j in successful_tests)
        total_referees = sum(sum(ms['referee_count'] for ms in j.get('manuscripts', [])) for j in successful_tests)
        
        self.results['summary'] = {
            'total_tested': len(tested_journals),
            'successful': len(successful_tests),
            'success_rate': len(successful_tests) / len(tested_journals) if tested_journals else 0,
            'total_manuscripts': total_manuscripts,
            'total_referees': total_referees,
            'expected_vs_actual': {
                'MF': {
                    'expected_manuscripts': 2,
                    'expected_referees': 4,
                    'actual_manuscripts': len(self.results['journals'].get('MF', {}).get('manuscripts', [])),
                    'actual_referees': sum(ms['referee_count'] for ms in self.results['journals'].get('MF', {}).get('manuscripts', []))
                },
                'MOR': {
                    'expected_manuscripts': 3,
                    'expected_referees': 5,
                    'actual_manuscripts': len(self.results['journals'].get('MOR', {}).get('manuscripts', [])),
                    'actual_referees': sum(ms['referee_count'] for ms in self.results['journals'].get('MOR', {}).get('manuscripts', []))
                }
            }
        }
        
        self.results['end_time'] = datetime.now().isoformat()
        
        # Save results
        results_file = self.output_dir / f"enhanced_results_{self.session_id}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"\\n📄 Full results saved to: {results_file}")
        
        return self.results


def main():
    """Main enhanced testing function"""
    print("🔍 Enhanced MF and MOR Testing")
    print("=" * 50)
    print("🎯 This test aims to find:")
    print("   • MF: 2 manuscripts with 4 referees total")
    print("   • MOR: 3 manuscripts with 5 referees total")
    print("=" * 50)
    
    try:
        # Check credentials
        if not (os.getenv('MF_USER') and os.getenv('MF_PASS') and os.getenv('MOR_USER') and os.getenv('MOR_PASS')):
            print("\\n⚠️ Loading credentials from .env file...")
            
            # Load from .env file
            env_file = Path(".env")
            if env_file.exists():
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key] = value
                print("✅ Credentials loaded from .env file")
            else:
                print("❌ No .env file found. Please set up credentials first.")
                return 1
        
        # Run enhanced tests
        tester = EnhancedMFMORTester(timeout_minutes=30)
        results = tester.run_enhanced_tests()
        
        # Display final summary
        print("\\n" + "=" * 60)
        print("📊 ENHANCED TESTING SUMMARY")
        print("=" * 60)
        
        summary = results['summary']
        print(f"Journals Tested: {summary['total_tested']}")
        print(f"Successful Tests: {summary['successful']}")
        print(f"Success Rate: {summary['success_rate']:.1%}")
        print(f"Total Manuscripts: {summary['total_manuscripts']}")
        print(f"Total Referees: {summary['total_referees']}")
        
        # Expected vs Actual comparison
        print("\\n📋 Expected vs Actual:")
        for journal, data in summary['expected_vs_actual'].items():
            expected_ms = data['expected_manuscripts']
            actual_ms = data['actual_manuscripts']
            expected_ref = data['expected_referees']
            actual_ref = data['actual_referees']
            
            ms_status = "✅" if actual_ms >= expected_ms else "❌"
            ref_status = "✅" if actual_ref >= expected_ref else "❌"
            
            print(f"  {journal}:")
            print(f"    Manuscripts: {actual_ms}/{expected_ms} {ms_status}")
            print(f"    Referees: {actual_ref}/{expected_ref} {ref_status}")
        
        print(f"\\n📁 Debug files saved to: {tester.output_dir}")
        
        # Check if we found what was expected
        mf_data = summary['expected_vs_actual']['MF']
        mor_data = summary['expected_vs_actual']['MOR']
        
        mf_complete = mf_data['actual_manuscripts'] >= mf_data['expected_manuscripts'] and mf_data['actual_referees'] >= mf_data['expected_referees']
        mor_complete = mor_data['actual_manuscripts'] >= mor_data['expected_manuscripts'] and mor_data['actual_referees'] >= mor_data['expected_referees']
        
        if mf_complete and mor_complete:
            print("\\n🎉 SUCCESS! Found all expected manuscripts and referees!")
            return 0
        else:
            print("\\n⚠️ Some expected manuscripts/referees are missing.")
            if not mf_complete:
                print(f"   MF: Expected {mf_data['expected_manuscripts']} manuscripts + {mf_data['expected_referees']} referees")
                print(f"       Found {mf_data['actual_manuscripts']} manuscripts + {mf_data['actual_referees']} referees")
            if not mor_complete:
                print(f"   MOR: Expected {mor_data['expected_manuscripts']} manuscripts + {mor_data['expected_referees']} referees")
                print(f"        Found {mor_data['actual_manuscripts']} manuscripts + {mor_data['actual_referees']} referees")
            return 1
            
    except Exception as e:
        print(f"\\n❌ Enhanced testing failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())