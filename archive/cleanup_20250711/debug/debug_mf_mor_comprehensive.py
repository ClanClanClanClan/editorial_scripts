#!/usr/bin/env python3
"""
Ultra-comprehensive debugging and testing for MF and MOR journals.
This script will perform deep testing and ensure both journals work perfectly.
"""

import os
import sys
import time
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import signal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import journal classes
from journals.mf import MFJournal
from journals.mor import MORJournal

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'mf_mor_debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class UltraDeepJournalDebugger:
    """Ultra-comprehensive debugging for MF and MOR journals"""
    
    def __init__(self, debug: bool = True):
        self.debug = debug
        self.session_id = f"debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.debug_output_dir = Path("debug_output")
        self.debug_output_dir.mkdir(exist_ok=True)
        
        self.results = {
            'session_id': self.session_id,
            'start_time': datetime.now().isoformat(),
            'journals': {},
            'errors': [],
            'summary': {}
        }
        
        # Test parameters
        self.max_test_time = 300  # 5 minutes max per journal
        self.screenshot_on_error = True
        self.save_html_on_error = True
        
    def create_robust_driver(self) -> uc.Chrome:
        """Create a robust Chrome driver for testing"""
        logger.info("🚗 Creating robust Chrome driver...")
        
        options = uc.ChromeOptions()
        
        # Basic options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Performance options
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        
        # Anti-detection
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Window size
        options.add_argument('--window-size=1920,1080')
        
        try:
            # Try undetected Chrome first
            driver = uc.Chrome(options=options, version_main=120)
            logger.info("✅ Undetected Chrome driver created successfully")
            return driver
        except Exception as e:
            logger.warning(f"⚠️ Undetected Chrome failed: {e}")
            
            # Fallback to standard Chrome
            from selenium import webdriver
            standard_options = Options()
            standard_options.add_argument('--no-sandbox')
            standard_options.add_argument('--disable-dev-shm-usage')
            standard_options.add_argument('--disable-blink-features=AutomationControlled')
            
            driver = webdriver.Chrome(options=standard_options)
            logger.info("✅ Standard Chrome driver created as fallback")
            return driver
    
    def save_debug_artifacts(self, driver: uc.Chrome, journal_name: str, error_type: str):
        """Save debugging artifacts (screenshots, HTML, logs)"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        try:
            # Save screenshot
            if self.screenshot_on_error:
                screenshot_path = self.debug_output_dir / f"{journal_name}_{error_type}_{timestamp}.png"
                driver.save_screenshot(str(screenshot_path))
                logger.info(f"📸 Screenshot saved: {screenshot_path}")
            
            # Save HTML
            if self.save_html_on_error:
                html_path = self.debug_output_dir / f"{journal_name}_{error_type}_{timestamp}.html"
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                logger.info(f"📄 HTML saved: {html_path}")
            
            # Save current URL
            url_info = {
                'current_url': driver.current_url,
                'title': driver.title,
                'timestamp': timestamp,
                'error_type': error_type
            }
            
            url_path = self.debug_output_dir / f"{journal_name}_{error_type}_{timestamp}_url.json"
            with open(url_path, 'w') as f:
                json.dump(url_info, f, indent=2)
            
        except Exception as e:
            logger.error(f"❌ Failed to save debug artifacts: {e}")
    
    def check_environment_variables(self, journal_name: str) -> Dict[str, Any]:
        """Check if required environment variables are set"""
        logger.info(f"🔍 Checking environment variables for {journal_name}...")
        
        required_vars = {
            'MF': ['MF_USER', 'MF_PASS'],
            'MOR': ['MOR_USER', 'MOR_PASS']
        }
        
        result = {
            'journal': journal_name,
            'variables_checked': required_vars.get(journal_name, []),
            'variables_set': [],
            'variables_missing': [],
            'status': 'unknown'
        }
        
        for var_name in required_vars.get(journal_name, []):
            if os.getenv(var_name):
                result['variables_set'].append(var_name)
                logger.info(f"✅ {var_name} is set")
            else:
                result['variables_missing'].append(var_name)
                logger.warning(f"⚠️ {var_name} is missing")
        
        if len(result['variables_missing']) == 0:
            result['status'] = 'all_set'
        elif len(result['variables_set']) > 0:
            result['status'] = 'partial'
        else:
            result['status'] = 'missing'
        
        return result
    
    def test_journal_connection(self, journal_name: str) -> Dict[str, Any]:
        """Test connection to journal website"""
        logger.info(f"🌐 Testing connection to {journal_name}...")
        
        urls = {
            'MF': 'https://mc.manuscriptcentral.com/mafi',
            'MOR': 'https://mc.manuscriptcentral.com/mathor'
        }
        
        result = {
            'journal': journal_name,
            'url': urls.get(journal_name, ''),
            'connection_status': 'unknown',
            'response_time': 0,
            'page_title': '',
            'page_loaded': False,
            'login_form_found': False,
            'error': None
        }
        
        driver = None
        try:
            driver = self.create_robust_driver()
            
            # Test connection
            start_time = time.time()
            driver.get(result['url'])
            
            # Wait for page to load
            WebDriverWait(driver, 30).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            result['response_time'] = time.time() - start_time
            result['page_title'] = driver.title
            result['page_loaded'] = True
            result['connection_status'] = 'success'
            
            # Check for login form
            try:
                userid_field = driver.find_element(By.ID, "USERID")
                password_field = driver.find_element(By.ID, "PASSWORD")
                login_button = driver.find_element(By.ID, "logInButton")
                
                if userid_field and password_field and login_button:
                    result['login_form_found'] = True
                    logger.info("✅ Login form found")
                
            except NoSuchElementException:
                logger.warning("⚠️ Login form not found")
                result['login_form_found'] = False
            
            logger.info(f"✅ Connection test passed for {journal_name}")
            logger.info(f"   Response time: {result['response_time']:.2f}s")
            logger.info(f"   Page title: {result['page_title']}")
            
        except Exception as e:
            result['connection_status'] = 'failed'
            result['error'] = str(e)
            logger.error(f"❌ Connection test failed for {journal_name}: {e}")
            
            if driver:
                self.save_debug_artifacts(driver, journal_name, 'connection_failed')
        
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
        
        return result
    
    def test_journal_login(self, journal_name: str) -> Dict[str, Any]:
        """Test login process for journal"""
        logger.info(f"🔐 Testing login for {journal_name}...")
        
        result = {
            'journal': journal_name,
            'login_attempted': False,
            'login_successful': False,
            'verification_required': False,
            'verification_handled': False,
            'post_login_navigation': False,
            'ae_center_found': False,
            'error': None,
            'steps_completed': [],
            'steps_failed': []
        }
        
        driver = None
        try:
            driver = self.create_robust_driver()
            
            # Create journal instance
            if journal_name == 'MF':
                journal = MFJournal(driver, debug=True)
            elif journal_name == 'MOR':
                journal = MORJournal(driver, debug=True)
            else:
                raise ValueError(f"Unknown journal: {journal_name}")
            
            # Set timeout for login test
            def timeout_handler(signum, frame):
                raise TimeoutError("Login test timeout")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.max_test_time)
            
            try:
                # Test login
                result['login_attempted'] = True
                result['steps_completed'].append('Login attempt started')
                
                journal.login()
                
                result['login_successful'] = True
                result['steps_completed'].append('Login completed')
                
                # Check if verification was required
                if hasattr(journal, 'activation_required') and journal.activation_required:
                    result['verification_required'] = True
                    result['verification_handled'] = True
                    result['steps_completed'].append('Verification code handled')
                
                # Test post-login navigation
                time.sleep(3)
                
                # Check if we can find Associate Editor Center
                try:
                    # Look for AE center links
                    ae_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Associate Editor')]")
                    if ae_links:
                        result['ae_center_found'] = True
                        result['steps_completed'].append('Associate Editor Center found')
                    else:
                        result['steps_failed'].append('Associate Editor Center not found')
                        
                        # Look for alternative editor links
                        editor_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Editor')]")
                        if editor_links:
                            result['steps_completed'].append('Editor links found (alternative)')
                        else:
                            result['steps_failed'].append('No editor links found')
                    
                    result['post_login_navigation'] = True
                    
                except Exception as nav_e:
                    result['steps_failed'].append(f'Navigation test failed: {nav_e}')
                
                signal.alarm(0)  # Cancel timeout
                
            except TimeoutError:
                result['error'] = 'Login test timed out'
                result['steps_failed'].append('Login timed out')
                
            except Exception as login_e:
                result['error'] = str(login_e)
                result['steps_failed'].append(f'Login failed: {login_e}')
                
            logger.info(f"✅ Login test completed for {journal_name}")
            logger.info(f"   Login successful: {result['login_successful']}")
            logger.info(f"   Verification required: {result['verification_required']}")
            logger.info(f"   AE center found: {result['ae_center_found']}")
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"❌ Login test failed for {journal_name}: {e}")
            
            if driver:
                self.save_debug_artifacts(driver, journal_name, 'login_failed')
        
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
        
        return result
    
    def test_manuscript_scraping(self, journal_name: str) -> Dict[str, Any]:
        """Test manuscript scraping functionality"""
        logger.info(f"📚 Testing manuscript scraping for {journal_name}...")
        
        result = {
            'journal': journal_name,
            'scraping_attempted': False,
            'scraping_successful': False,
            'manuscripts_found': 0,
            'manuscripts_data': [],
            'referee_data_found': False,
            'pdf_links_found': False,
            'error': None,
            'parsing_errors': [],
            'steps_completed': [],
            'steps_failed': []
        }
        
        driver = None
        try:
            driver = self.create_robust_driver()
            
            # Create journal instance
            if journal_name == 'MF':
                journal = MFJournal(driver, debug=True)
            elif journal_name == 'MOR':
                journal = MORJournal(driver, debug=True)
            else:
                raise ValueError(f"Unknown journal: {journal_name}")
            
            # Set timeout for scraping test
            def timeout_handler(signum, frame):
                raise TimeoutError("Scraping test timeout")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.max_test_time)
            
            try:
                result['scraping_attempted'] = True
                result['steps_completed'].append('Scraping attempt started')
                
                # Run the scraping
                manuscripts = journal.scrape_manuscripts_and_emails()
                
                result['scraping_successful'] = True
                result['manuscripts_found'] = len(manuscripts)
                result['steps_completed'].append(f'Scraping completed: {len(manuscripts)} manuscripts')
                
                # Analyze the scraped data
                for manuscript in manuscripts:
                    try:
                        # Basic manuscript info
                        ms_info = {
                            'manuscript_id': manuscript.get('Manuscript #', ''),
                            'title': manuscript.get('Title', '')[:100],  # Truncate for summary
                            'author': manuscript.get('Contact Author', ''),
                            'submission_date': manuscript.get('Submission Date', ''),
                            'referee_count': len(manuscript.get('Referees', [])),
                            'has_referee_data': bool(manuscript.get('Referees', []))
                        }
                        
                        # Check referee data quality
                        referees = manuscript.get('Referees', [])
                        if referees:
                            result['referee_data_found'] = True
                            referee_with_email = sum(1 for r in referees if r.get('Email'))
                            ms_info['referees_with_email'] = referee_with_email
                            
                            # Sample referee data (first referee)
                            if referees:
                                ms_info['sample_referee'] = {
                                    'name': referees[0].get('Referee Name', ''),
                                    'status': referees[0].get('Status', ''),
                                    'email': bool(referees[0].get('Email'))
                                }
                        
                        # Check for download data
                        if manuscript.get('downloads'):
                            downloads = manuscript['downloads']
                            if downloads.get('paper'):
                                result['pdf_links_found'] = True
                                ms_info['paper_downloaded'] = True
                            ms_info['reports_downloaded'] = len(downloads.get('reports', []))
                        
                        result['manuscripts_data'].append(ms_info)
                        
                    except Exception as parse_e:
                        result['parsing_errors'].append(f"Error parsing manuscript: {parse_e}")
                
                signal.alarm(0)  # Cancel timeout
                
                logger.info(f"✅ Manuscript scraping test completed for {journal_name}")
                logger.info(f"   Manuscripts found: {result['manuscripts_found']}")
                logger.info(f"   Referee data found: {result['referee_data_found']}")
                logger.info(f"   PDF links found: {result['pdf_links_found']}")
                
            except TimeoutError:
                result['error'] = 'Scraping test timed out'
                result['steps_failed'].append('Scraping timed out')
                
            except Exception as scraping_e:
                result['error'] = str(scraping_e)
                result['steps_failed'].append(f'Scraping failed: {scraping_e}')
                
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"❌ Manuscript scraping test failed for {journal_name}: {e}")
            
            if driver:
                self.save_debug_artifacts(driver, journal_name, 'scraping_failed')
        
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
        
        return result
    
    def run_comprehensive_test(self, journal_name: str) -> Dict[str, Any]:
        """Run comprehensive test for a journal"""
        logger.info(f"🚀 Starting comprehensive test for {journal_name}")
        logger.info("=" * 60)
        
        journal_results = {
            'journal': journal_name,
            'test_start_time': datetime.now().isoformat(),
            'environment_check': {},
            'connection_test': {},
            'login_test': {},
            'scraping_test': {},
            'overall_status': 'unknown',
            'success_rate': 0.0,
            'recommendations': []
        }
        
        try:
            # Phase 1: Environment check
            logger.info(f"🔍 Phase 1: Environment check for {journal_name}")
            journal_results['environment_check'] = self.check_environment_variables(journal_name)
            
            # Phase 2: Connection test
            logger.info(f"🌐 Phase 2: Connection test for {journal_name}")
            journal_results['connection_test'] = self.test_journal_connection(journal_name)
            
            # Phase 3: Login test (only if environment and connection are OK)
            if (journal_results['environment_check']['status'] == 'all_set' and 
                journal_results['connection_test']['connection_status'] == 'success'):
                
                logger.info(f"🔐 Phase 3: Login test for {journal_name}")
                journal_results['login_test'] = self.test_journal_login(journal_name)
                
                # Phase 4: Scraping test (only if login is OK)
                if journal_results['login_test']['login_successful']:
                    logger.info(f"📚 Phase 4: Scraping test for {journal_name}")
                    journal_results['scraping_test'] = self.test_manuscript_scraping(journal_name)
            
            # Calculate success rate
            tests_passed = 0
            total_tests = 0
            
            if journal_results['environment_check']['status'] == 'all_set':
                tests_passed += 1
            total_tests += 1
            
            if journal_results['connection_test']['connection_status'] == 'success':
                tests_passed += 1
            total_tests += 1
            
            if journal_results['login_test'].get('login_successful'):
                tests_passed += 1
            total_tests += 1
            
            if journal_results['scraping_test'].get('scraping_successful'):
                tests_passed += 1
            total_tests += 1
            
            journal_results['success_rate'] = tests_passed / total_tests if total_tests > 0 else 0
            
            # Determine overall status
            if journal_results['success_rate'] >= 0.75:
                journal_results['overall_status'] = 'excellent'
            elif journal_results['success_rate'] >= 0.5:
                journal_results['overall_status'] = 'good'
            elif journal_results['success_rate'] >= 0.25:
                journal_results['overall_status'] = 'fair'
            else:
                journal_results['overall_status'] = 'poor'
            
            # Generate recommendations
            recommendations = []
            
            if journal_results['environment_check']['status'] != 'all_set':
                missing_vars = journal_results['environment_check']['variables_missing']
                recommendations.append(f"Set missing environment variables: {', '.join(missing_vars)}")
            
            if journal_results['connection_test']['connection_status'] != 'success':
                recommendations.append("Check network connectivity and journal website availability")
            
            if not journal_results['login_test'].get('login_successful'):
                recommendations.append("Verify login credentials and handle any authentication issues")
            
            if not journal_results['scraping_test'].get('scraping_successful'):
                recommendations.append("Debug manuscript scraping logic and selectors")
            
            if journal_results['scraping_test'].get('manuscripts_found', 0) == 0:
                recommendations.append("Verify manuscript availability and parsing logic")
            
            journal_results['recommendations'] = recommendations
            
            journal_results['test_end_time'] = datetime.now().isoformat()
            
        except Exception as e:
            journal_results['overall_status'] = 'failed'
            journal_results['error'] = str(e)
            logger.error(f"❌ Comprehensive test failed for {journal_name}: {e}")
        
        return journal_results
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive tests for both MF and MOR"""
        logger.info("🎯 Starting Ultra-Deep Journal Debugging")
        logger.info("=" * 80)
        
        for journal_name in ['MF', 'MOR']:
            logger.info(f"\n🔬 Testing {journal_name}")
            logger.info("-" * 40)
            
            journal_results = self.run_comprehensive_test(journal_name)
            self.results['journals'][journal_name] = journal_results
            
            # Print immediate results
            logger.info(f"📊 {journal_name} Test Results:")
            logger.info(f"   Overall Status: {journal_results['overall_status'].upper()}")
            logger.info(f"   Success Rate: {journal_results['success_rate']:.1%}")
            
            if journal_results.get('scraping_test', {}).get('manuscripts_found', 0) > 0:
                logger.info(f"   Manuscripts Found: {journal_results['scraping_test']['manuscripts_found']}")
            
            if journal_results.get('recommendations'):
                logger.info(f"   Recommendations: {len(journal_results['recommendations'])}")
                for rec in journal_results['recommendations']:
                    logger.info(f"     • {rec}")
        
        # Generate summary
        self.results['end_time'] = datetime.now().isoformat()
        
        total_journals = len(self.results['journals'])
        excellent_journals = sum(1 for j in self.results['journals'].values() if j['overall_status'] == 'excellent')
        working_journals = sum(1 for j in self.results['journals'].values() if j['overall_status'] in ['excellent', 'good'])
        
        self.results['summary'] = {
            'total_journals_tested': total_journals,
            'excellent_journals': excellent_journals,
            'working_journals': working_journals,
            'overall_success_rate': working_journals / total_journals if total_journals > 0 else 0
        }
        
        # Save results
        results_file = self.debug_output_dir / f"comprehensive_test_results_{self.session_id}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info("\n" + "=" * 80)
        logger.info("🎯 ULTRA-DEEP DEBUGGING COMPLETE")
        logger.info("=" * 80)
        logger.info(f"📄 Full results saved to: {results_file}")
        
        return self.results


def main():
    """Main entry point for ultra-deep debugging"""
    print("🔬 Ultra-Deep Journal Debugging for MF and MOR")
    print("=" * 60)
    print("This will perform comprehensive testing of both journals")
    print("=" * 60)
    
    try:
        debugger = UltraDeepJournalDebugger(debug=True)
        results = debugger.run_all_tests()
        
        # Display final summary
        print("\n" + "=" * 60)
        print("📊 FINAL SUMMARY")
        print("=" * 60)
        
        summary = results['summary']
        print(f"Total Journals Tested: {summary['total_journals_tested']}")
        print(f"Excellent Status: {summary['excellent_journals']}")
        print(f"Working Journals: {summary['working_journals']}")
        print(f"Overall Success Rate: {summary['overall_success_rate']:.1%}")
        
        print("\n📋 Journal Details:")
        for journal_name, journal_data in results['journals'].items():
            status = journal_data['overall_status'].upper()
            success_rate = journal_data['success_rate']
            manuscripts = journal_data.get('scraping_test', {}).get('manuscripts_found', 0)
            
            print(f"  {journal_name}: {status} ({success_rate:.1%} success, {manuscripts} manuscripts)")
        
        print(f"\n📁 Debug files saved to: debug_output/")
        print("✅ Ultra-deep debugging completed!")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️ Debugging interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Debugging failed: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())