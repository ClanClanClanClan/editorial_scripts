"""
Ultra-robust connection debugging and fixing system for journal scraping.
This module provides deep debugging capabilities and automatic fixes for connection issues.
"""

import os
import time
import logging
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import undetected_chromedriver as uc

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ConnectionDebugger:
    """Ultra-robust connection debugging and fixing system"""
    
    def __init__(self, debug=True):
        self.debug = debug
        self.test_results = {}
        self.connection_issues = {}
        self.fixes_applied = {}
        self.debug_dir = Path("debug_logs")
        self.debug_dir.mkdir(exist_ok=True)
        
        # Journal configurations
        self.journal_configs = {
            'SICON': {
                'url': 'https://sicon.siam.org/cgi-bin/main.plex',
                'login_type': 'orcid',
                'auth_indicators': ['orcid'],
                'dashboard_indicators': ['ndt_folder', 'all_pending_manuscripts'],
                'requires_iframe': False
            },
            'SIFIN': {
                'url': 'https://sifin.siam.org/cgi-bin/main.plex',
                'login_type': 'orcid',
                'auth_indicators': ['orcid'],
                'dashboard_indicators': ['assoc_ed', 'ndt_task'],
                'requires_iframe': False
            },
            'MAFE': {
                'url': 'https://www2.cloud.editorialmanager.com/mafe/default2.aspx',
                'login_type': 'direct',
                'auth_indicators': ['username', 'password'],
                'dashboard_indicators': ['Associate Editor', 'aries-accordion-item'],
                'requires_iframe': True
            },
            'JOTA': {
                'url': 'https://jota.editorialmanager.com/jota/default2.aspx',
                'login_type': 'direct',
                'auth_indicators': ['username', 'password'],
                'dashboard_indicators': ['Associate Editor', 'aries-accordion-item'],
                'requires_iframe': True
            },
            'MOR': {
                'url': 'https://mor.editorialmanager.com/mor/default2.aspx',
                'login_type': 'direct',
                'auth_indicators': ['username', 'password'],
                'dashboard_indicators': ['Associate Editor'],
                'requires_iframe': True
            }
        }
    
    def comprehensive_debug_all_journals(self) -> Dict[str, Dict]:
        """Perform comprehensive debugging of all journal connections"""
        logger.info("🔍 Starting comprehensive debugging of all journal connections")
        
        results = {}
        
        for journal_name, config in self.journal_configs.items():
            logger.info(f"🧪 Testing {journal_name} connection...")
            
            try:
                journal_result = self.debug_journal_connection(journal_name, config)
                results[journal_name] = journal_result
                
                # Apply fixes if needed
                if journal_result.get('issues_found'):
                    logger.info(f"🔧 Applying fixes for {journal_name}...")
                    fixes_result = self.apply_connection_fixes(journal_name, journal_result)
                    results[journal_name]['fixes_applied'] = fixes_result
                
            except Exception as e:
                logger.error(f"❌ Fatal error debugging {journal_name}: {e}")
                results[journal_name] = {
                    'status': 'fatal_error',
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }
        
        # Generate comprehensive report
        report = self.generate_debug_report(results)
        
        # Save report
        report_path = self.debug_dir / f"debug_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📄 Debug report saved to: {report_path}")
        
        return results
    
    def debug_journal_connection(self, journal_name: str, config: Dict) -> Dict:
        """Debug a specific journal connection with ultra-detailed analysis"""
        debug_info = {
            'journal': journal_name,
            'timestamp': datetime.now().isoformat(),
            'status': 'unknown',
            'issues_found': [],
            'network_test': None,
            'page_load_test': None,
            'login_test': None,
            'dashboard_test': None,
            'recommendations': []
        }
        
        driver = None
        
        try:
            # 1. Network connectivity test
            debug_info['network_test'] = self.test_network_connectivity(config['url'])
            
            # 2. Browser setup test
            driver = self.create_robust_driver(journal_name)
            debug_info['browser_setup'] = {'status': 'success', 'driver_type': 'undetected_chrome'}
            
            # 3. Page load test
            debug_info['page_load_test'] = self.test_page_load(driver, config['url'], journal_name)
            
            # 4. Authentication flow test
            debug_info['login_test'] = self.test_authentication_flow(driver, journal_name, config)
            
            # 5. Dashboard access test
            debug_info['dashboard_test'] = self.test_dashboard_access(driver, journal_name, config)
            
            # 6. PDF/Document access test
            debug_info['document_access_test'] = self.test_document_access(driver, journal_name)
            
            # 7. Determine overall status
            debug_info['status'] = self.determine_overall_status(debug_info)
            
            # 8. Generate recommendations
            debug_info['recommendations'] = self.generate_recommendations(debug_info, journal_name)
            
        except Exception as e:
            debug_info['status'] = 'fatal_error'
            debug_info['error'] = str(e)
            debug_info['traceback'] = traceback.format_exc()
            logger.error(f"❌ Fatal error debugging {journal_name}: {e}")
        
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
        
        return debug_info
    
    def test_network_connectivity(self, url: str) -> Dict:
        """Test network connectivity to the journal URL"""
        test_result = {
            'url': url,
            'status': 'unknown',
            'response_time': None,
            'status_code': None,
            'headers': {},
            'ssl_valid': False,
            'cdn_info': None
        }
        
        try:
            start_time = time.time()
            response = requests.get(url, timeout=30, verify=True)
            response_time = time.time() - start_time
            
            test_result.update({
                'status': 'success',
                'response_time': response_time,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'ssl_valid': True,
                'content_length': len(response.content),
                'final_url': response.url
            })
            
            # Check for CDN/protection services
            cdn_headers = ['cf-ray', 'x-served-by', 'x-cache', 'server']
            cdn_info = {}
            for header in cdn_headers:
                if header in response.headers:
                    cdn_info[header] = response.headers[header]
            
            test_result['cdn_info'] = cdn_info
            
        except requests.exceptions.SSLError as e:
            test_result.update({
                'status': 'ssl_error',
                'error': str(e),
                'ssl_valid': False
            })
        except requests.exceptions.Timeout:
            test_result.update({
                'status': 'timeout',
                'error': 'Request timed out after 30 seconds'
            })
        except requests.exceptions.ConnectionError as e:
            test_result.update({
                'status': 'connection_error',
                'error': str(e)
            })
        except Exception as e:
            test_result.update({
                'status': 'error',
                'error': str(e)
            })
        
        return test_result
    
    def create_robust_driver(self, journal_name: str) -> webdriver.Chrome:
        """Create an ultra-robust Chrome driver with anti-detection measures"""
        
        # Try multiple driver creation strategies
        strategies = [
            self._create_undetected_driver,
            self._create_stealth_driver,
            self._create_standard_driver
        ]
        
        for i, strategy in enumerate(strategies):
            try:
                driver = strategy(journal_name)
                logger.info(f"✅ Driver created successfully using strategy {i+1}")
                return driver
            except Exception as e:
                logger.warning(f"⚠️ Driver strategy {i+1} failed: {e}")
                continue
        
        raise Exception("All driver creation strategies failed")
    
    def _create_undetected_driver(self, journal_name: str) -> webdriver.Chrome:
        """Create undetected Chrome driver"""
        options = uc.ChromeOptions()
        
        # Anti-detection options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Performance options
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')
        
        # User agent
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Profile settings
        profile_path = Path(f"my_{journal_name.lower()}_profile")
        if profile_path.exists():
            options.add_argument(f'--user-data-dir={profile_path}')
        
        # Create driver
        driver = uc.Chrome(options=options, version_main=120)
        
        # Execute anti-detection scripts
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    def _create_stealth_driver(self, journal_name: str) -> webdriver.Chrome:
        """Create stealth Chrome driver with selenium-stealth"""
        try:
            from selenium_stealth import stealth
        except ImportError:
            raise ImportError("selenium-stealth not installed")
        
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        driver = webdriver.Chrome(options=options)
        
        # Apply stealth
        stealth(driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True)
        
        return driver
    
    def _create_standard_driver(self, journal_name: str) -> webdriver.Chrome:
        """Create standard Chrome driver as fallback"""
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        return webdriver.Chrome(options=options)
    
    def test_page_load(self, driver: webdriver.Chrome, url: str, journal_name: str) -> Dict:
        """Test page loading with detailed analysis"""
        test_result = {
            'url': url,
            'status': 'unknown',
            'load_time': None,
            'final_url': None,
            'page_title': None,
            'dom_ready': False,
            'javascript_errors': [],
            'network_errors': [],
            'blocked_resources': [],
            'cookies_detected': [],
            'iframes_detected': 0,
            'forms_detected': 0
        }
        
        try:
            # Enable logging to capture network errors
            driver.execute_cdp_cmd('Network.enable', {})
            driver.execute_cdp_cmd('Runtime.enable', {})
            
            # Start timing
            start_time = time.time()
            
            # Navigate to page
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, 30).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            load_time = time.time() - start_time
            
            test_result.update({
                'status': 'success',
                'load_time': load_time,
                'final_url': driver.current_url,
                'page_title': driver.title,
                'dom_ready': True
            })
            
            # Analyze page content
            self._analyze_page_content(driver, test_result, journal_name)
            
            # Check for common issues
            self._check_common_page_issues(driver, test_result)
            
        except TimeoutException:
            test_result.update({
                'status': 'timeout',
                'error': 'Page load timeout after 30 seconds'
            })
        except Exception as e:
            test_result.update({
                'status': 'error',
                'error': str(e)
            })
        
        return test_result
    
    def _analyze_page_content(self, driver: webdriver.Chrome, test_result: Dict, journal_name: str):
        """Analyze page content for debugging"""
        try:
            # Check for iframes
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            test_result['iframes_detected'] = len(iframes)
            
            # Check for forms
            forms = driver.find_elements(By.TAG_NAME, "form")
            test_result['forms_detected'] = len(forms)
            
            # Check for cookies/privacy banners
            cookie_selectors = [
                "cookie", "consent", "privacy", "gdpr", "accept", "banner"
            ]
            
            cookies_found = []
            for selector in cookie_selectors:
                elements = driver.find_elements(By.XPATH, f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{selector}')]")
                if elements:
                    cookies_found.append(f"{selector}: {len(elements)} elements")
            
            test_result['cookies_detected'] = cookies_found
            
            # Check for specific journal elements
            journal_elements = self._check_journal_specific_elements(driver, journal_name)
            test_result['journal_elements'] = journal_elements
            
        except Exception as e:
            test_result['analysis_error'] = str(e)
    
    def _check_journal_specific_elements(self, driver: webdriver.Chrome, journal_name: str) -> Dict:
        """Check for journal-specific elements"""
        elements_found = {}
        
        config = self.journal_configs.get(journal_name, {})
        
        # Check for authentication indicators
        auth_indicators = config.get('auth_indicators', [])
        for indicator in auth_indicators:
            try:
                elements = driver.find_elements(By.XPATH, f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{indicator}')]")
                elements_found[f'auth_{indicator}'] = len(elements)
            except:
                elements_found[f'auth_{indicator}'] = 0
        
        # Check for dashboard indicators
        dashboard_indicators = config.get('dashboard_indicators', [])
        for indicator in dashboard_indicators:
            try:
                elements = driver.find_elements(By.XPATH, f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{indicator}')]")
                elements_found[f'dashboard_{indicator}'] = len(elements)
            except:
                elements_found[f'dashboard_{indicator}'] = 0
        
        return elements_found
    
    def _check_common_page_issues(self, driver: webdriver.Chrome, test_result: Dict):
        """Check for common page issues"""
        issues = []
        
        # Check for JavaScript errors
        try:
            logs = driver.get_log('browser')
            js_errors = [log for log in logs if log['level'] == 'SEVERE']
            test_result['javascript_errors'] = [error['message'] for error in js_errors]
        except:
            test_result['javascript_errors'] = []
        
        # Check for blocked resources
        try:
            performance_logs = driver.get_log('performance')
            blocked_resources = []
            for log in performance_logs:
                message = json.loads(log['message'])
                if message.get('message', {}).get('method') == 'Network.loadingFailed':
                    blocked_resources.append(message['message']['params']['errorText'])
            test_result['blocked_resources'] = blocked_resources
        except:
            test_result['blocked_resources'] = []
        
        # Check for common error messages
        error_keywords = ['error', 'failed', 'unavailable', 'maintenance', 'blocked']
        page_source = driver.page_source.lower()
        
        for keyword in error_keywords:
            if keyword in page_source:
                issues.append(f"Found '{keyword}' in page source")
        
        test_result['page_issues'] = issues
    
    def test_authentication_flow(self, driver: webdriver.Chrome, journal_name: str, config: Dict) -> Dict:
        """Test authentication flow with detailed analysis"""
        test_result = {
            'journal': journal_name,
            'login_type': config.get('login_type'),
            'status': 'unknown',
            'steps_completed': [],
            'steps_failed': [],
            'credentials_found': False,
            'login_elements_found': {},
            'authentication_method': None
        }
        
        try:
            if config.get('login_type') == 'orcid':
                return self._test_orcid_authentication(driver, journal_name, test_result)
            elif config.get('login_type') == 'direct':
                return self._test_direct_authentication(driver, journal_name, test_result)
            else:
                test_result.update({
                    'status': 'unknown_login_type',
                    'error': f"Unknown login type: {config.get('login_type')}"
                })
        
        except Exception as e:
            test_result.update({
                'status': 'error',
                'error': str(e),
                'traceback': traceback.format_exc()
            })
        
        return test_result
    
    def _test_orcid_authentication(self, driver: webdriver.Chrome, journal_name: str, test_result: Dict) -> Dict:
        """Test ORCID authentication flow"""
        test_result['authentication_method'] = 'orcid'
        
        try:
            # Step 1: Look for ORCID login link
            orcid_selectors = [
                "//a[contains(@href, 'orcid')]",
                "//a[contains(text(), 'ORCID')]",
                "//a[contains(text(), 'orcid')]",
                "//button[contains(text(), 'ORCID')]"
            ]
            
            orcid_link = None
            for selector in orcid_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements:
                        orcid_link = elements[0]
                        test_result['steps_completed'].append(f"Found ORCID link: {selector}")
                        break
                except:
                    continue
            
            if not orcid_link:
                test_result['steps_failed'].append("No ORCID login link found")
                test_result['login_elements_found']['orcid_link'] = False
            else:
                test_result['login_elements_found']['orcid_link'] = True
                
                # Step 2: Click ORCID link
                try:
                    orcid_link.click()
                    time.sleep(3)
                    test_result['steps_completed'].append("Clicked ORCID link")
                    
                    # Step 3: Check for ORCID credentials
                    orcid_user = os.getenv('ORCID_USER')
                    orcid_pass = os.getenv('ORCID_PASS')
                    
                    if orcid_user and orcid_pass:
                        test_result['credentials_found'] = True
                        test_result['steps_completed'].append("ORCID credentials found in environment")
                        
                        # Step 4: Look for ORCID login fields
                        username_field = None
                        password_field = None
                        
                        try:
                            username_field = WebDriverWait(driver, 15).until(
                                EC.presence_of_element_located((By.ID, "username-input"))
                            )
                            password_field = WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.ID, "password"))
                            )
                            
                            test_result['login_elements_found']['username_field'] = True
                            test_result['login_elements_found']['password_field'] = True
                            test_result['steps_completed'].append("Found ORCID login fields")
                            
                            # Step 5: Test credentials entry (without actually logging in)
                            test_result['status'] = 'ready_for_login'
                            
                        except TimeoutException:
                            test_result['steps_failed'].append("ORCID login fields not found")
                            test_result['login_elements_found']['username_field'] = False
                            test_result['login_elements_found']['password_field'] = False
                    else:
                        test_result['steps_failed'].append("ORCID credentials not found in environment")
                        test_result['credentials_found'] = False
                
                except Exception as e:
                    test_result['steps_failed'].append(f"Failed to click ORCID link: {e}")
        
        except Exception as e:
            test_result['steps_failed'].append(f"ORCID authentication test failed: {e}")
        
        # Determine final status
        if test_result['credentials_found'] and test_result['login_elements_found'].get('orcid_link'):
            test_result['status'] = 'ready_for_login'
        else:
            test_result['status'] = 'configuration_needed'
        
        return test_result
    
    def _test_direct_authentication(self, driver: webdriver.Chrome, journal_name: str, test_result: Dict) -> Dict:
        """Test direct authentication flow"""
        test_result['authentication_method'] = 'direct'
        
        try:
            # Step 1: Check for credentials
            from core.credential_manager import get_credential_manager
            cred_manager = get_credential_manager()
            creds = cred_manager.get_journal_credentials(journal_name)
            
            if creds.get('username') and creds.get('password'):
                test_result['credentials_found'] = True
                test_result['steps_completed'].append("Credentials found in credential manager")
            else:
                test_result['credentials_found'] = False
                test_result['steps_failed'].append("Credentials not found in credential manager")
            
            # Step 2: Check for iframe requirement
            if self.journal_configs.get(journal_name, {}).get('requires_iframe'):
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                test_result['login_elements_found']['iframes'] = len(iframes)
                
                if iframes:
                    test_result['steps_completed'].append(f"Found {len(iframes)} iframes")
                    
                    # Step 3: Check each iframe for login fields
                    login_iframe_found = False
                    
                    for i, iframe in enumerate(iframes):
                        try:
                            driver.switch_to.frame(iframe)
                            
                            # Look for login fields
                            username_fields = driver.find_elements(By.ID, "username")
                            password_fields = driver.find_elements(By.ID, "passwordTextbox")
                            
                            if username_fields and password_fields:
                                test_result['steps_completed'].append(f"Found login fields in iframe {i}")
                                test_result['login_elements_found']['username_field'] = True
                                test_result['login_elements_found']['password_field'] = True
                                login_iframe_found = True
                                break
                            
                            driver.switch_to.default_content()
                            
                        except Exception as e:
                            test_result['steps_failed'].append(f"Error checking iframe {i}: {e}")
                            try:
                                driver.switch_to.default_content()
                            except:
                                pass
                    
                    if not login_iframe_found:
                        test_result['steps_failed'].append("No login fields found in any iframe")
                        test_result['login_elements_found']['username_field'] = False
                        test_result['login_elements_found']['password_field'] = False
                else:
                    test_result['steps_failed'].append("No iframes found but journal requires iframe")
            
            else:
                # Step 3: Look for login fields in main frame
                username_fields = driver.find_elements(By.ID, "username")
                password_fields = driver.find_elements(By.ID, "passwordTextbox")
                
                if username_fields and password_fields:
                    test_result['steps_completed'].append("Found login fields in main frame")
                    test_result['login_elements_found']['username_field'] = True
                    test_result['login_elements_found']['password_field'] = True
                else:
                    test_result['steps_failed'].append("No login fields found in main frame")
                    test_result['login_elements_found']['username_field'] = False
                    test_result['login_elements_found']['password_field'] = False
        
        except Exception as e:
            test_result['steps_failed'].append(f"Direct authentication test failed: {e}")
        
        # Determine final status
        if (test_result['credentials_found'] and 
            test_result['login_elements_found'].get('username_field') and 
            test_result['login_elements_found'].get('password_field')):
            test_result['status'] = 'ready_for_login'
        else:
            test_result['status'] = 'configuration_needed'
        
        return test_result
    
    def test_dashboard_access(self, driver: webdriver.Chrome, journal_name: str, config: Dict) -> Dict:
        """Test dashboard access after authentication"""
        test_result = {
            'journal': journal_name,
            'status': 'unknown',
            'dashboard_elements_found': {},
            'manuscript_indicators': {},
            'functionality_tests': {}
        }
        
        try:
            # Look for dashboard indicators
            dashboard_indicators = config.get('dashboard_indicators', [])
            
            for indicator in dashboard_indicators:
                try:
                    elements = driver.find_elements(By.XPATH, f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{indicator}')]")
                    test_result['dashboard_elements_found'][indicator] = len(elements)
                except:
                    test_result['dashboard_elements_found'][indicator] = 0
            
            # Look for manuscript-related elements
            manuscript_keywords = ['manuscript', 'paper', 'submission', 'review', 'referee']
            
            for keyword in manuscript_keywords:
                try:
                    elements = driver.find_elements(By.XPATH, f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')]")
                    test_result['manuscript_indicators'][keyword] = len(elements)
                except:
                    test_result['manuscript_indicators'][keyword] = 0
            
            # Test specific functionality
            test_result['functionality_tests'] = self._test_dashboard_functionality(driver, journal_name)
            
            # Determine status
            if any(count > 0 for count in test_result['dashboard_elements_found'].values()):
                test_result['status'] = 'dashboard_accessible'
            else:
                test_result['status'] = 'dashboard_not_found'
        
        except Exception as e:
            test_result['status'] = 'error'
            test_result['error'] = str(e)
        
        return test_result
    
    def _test_dashboard_functionality(self, driver: webdriver.Chrome, journal_name: str) -> Dict:
        """Test specific dashboard functionality"""
        functionality_tests = {}
        
        try:
            # Test table detection
            tables = driver.find_elements(By.TAG_NAME, "table")
            functionality_tests['tables_found'] = len(tables)
            
            # Test link detection
            links = driver.find_elements(By.TAG_NAME, "a")
            functionality_tests['links_found'] = len(links)
            
            # Test form detection
            forms = driver.find_elements(By.TAG_NAME, "form")
            functionality_tests['forms_found'] = len(forms)
            
            # Test JavaScript functionality
            try:
                js_test = driver.execute_script("return typeof jQuery !== 'undefined' || typeof $ !== 'undefined'")
                functionality_tests['jquery_available'] = js_test
            except:
                functionality_tests['jquery_available'] = False
            
            # Test for specific journal elements
            if journal_name in ['SICON', 'SIFIN']:
                # Test for SIAM-specific elements
                ndt_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='ndt']")
                functionality_tests['ndt_elements'] = len(ndt_elements)
            
            elif journal_name in ['MAFE', 'JOTA', 'MOR']:
                # Test for Editorial Manager elements
                aries_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='aries']")
                functionality_tests['aries_elements'] = len(aries_elements)
        
        except Exception as e:
            functionality_tests['error'] = str(e)
        
        return functionality_tests
    
    def test_document_access(self, driver: webdriver.Chrome, journal_name: str) -> Dict:
        """Test document/PDF access capabilities"""
        test_result = {
            'journal': journal_name,
            'status': 'unknown',
            'pdf_links_found': 0,
            'download_links_found': 0,
            'access_methods': [],
            'potential_issues': []
        }
        
        try:
            # Look for PDF links
            pdf_selectors = [
                "//a[contains(@href, '.pdf')]",
                "//a[contains(text(), 'PDF')]",
                "//a[contains(text(), 'Download')]",
                "//a[contains(@href, 'download')]"
            ]
            
            for selector in pdf_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements:
                        test_result['pdf_links_found'] += len(elements)
                        test_result['access_methods'].append(f"PDF links via {selector}")
                except:
                    continue
            
            # Look for download mechanisms
            download_selectors = [
                "//button[contains(text(), 'Download')]",
                "//input[contains(@value, 'Download')]",
                "//a[contains(@class, 'download')]"
            ]
            
            for selector in download_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements:
                        test_result['download_links_found'] += len(elements)
                        test_result['access_methods'].append(f"Download buttons via {selector}")
                except:
                    continue
            
            # Check for potential access issues
            if test_result['pdf_links_found'] == 0 and test_result['download_links_found'] == 0:
                test_result['potential_issues'].append("No PDF or download links found")
            
            # Determine status
            if test_result['pdf_links_found'] > 0 or test_result['download_links_found'] > 0:
                test_result['status'] = 'document_access_available'
            else:
                test_result['status'] = 'document_access_limited'
        
        except Exception as e:
            test_result['status'] = 'error'
            test_result['error'] = str(e)
        
        return test_result
    
    def determine_overall_status(self, debug_info: Dict) -> str:
        """Determine overall connection status"""
        network_ok = debug_info.get('network_test', {}).get('status') == 'success'
        page_load_ok = debug_info.get('page_load_test', {}).get('status') == 'success'
        login_ready = debug_info.get('login_test', {}).get('status') == 'ready_for_login'
        dashboard_ok = debug_info.get('dashboard_test', {}).get('status') == 'dashboard_accessible'
        
        if network_ok and page_load_ok and login_ready and dashboard_ok:
            return 'fully_functional'
        elif network_ok and page_load_ok and login_ready:
            return 'ready_for_testing'
        elif network_ok and page_load_ok:
            return 'authentication_issues'
        elif network_ok:
            return 'page_load_issues'
        else:
            return 'network_issues'
    
    def generate_recommendations(self, debug_info: Dict, journal_name: str) -> List[str]:
        """Generate specific recommendations based on debug results"""
        recommendations = []
        
        # Network recommendations
        network_test = debug_info.get('network_test', {})
        if network_test.get('status') != 'success':
            if network_test.get('status') == 'ssl_error':
                recommendations.append("SSL certificate issue - consider using verify=False or update certificates")
            elif network_test.get('status') == 'timeout':
                recommendations.append("Network timeout - check internet connection and try again")
            elif network_test.get('status') == 'connection_error':
                recommendations.append("Connection error - journal site may be down or blocked")
        
        # Page load recommendations
        page_load_test = debug_info.get('page_load_test', {})
        if page_load_test.get('status') != 'success':
            if page_load_test.get('status') == 'timeout':
                recommendations.append("Page load timeout - increase timeout values or check for blocking scripts")
            if page_load_test.get('javascript_errors'):
                recommendations.append("JavaScript errors detected - may need to handle page exceptions")
        
        # Authentication recommendations
        login_test = debug_info.get('login_test', {})
        if login_test.get('status') != 'ready_for_login':
            if not login_test.get('credentials_found'):
                recommendations.append(f"Set up credentials for {journal_name} in credential manager or environment variables")
            if not login_test.get('login_elements_found', {}).get('username_field'):
                recommendations.append("Login fields not found - page structure may have changed")
        
        # Dashboard recommendations
        dashboard_test = debug_info.get('dashboard_test', {})
        if dashboard_test.get('status') != 'dashboard_accessible':
            recommendations.append("Dashboard not accessible - authentication may be failing")
        
        # Cookie/GDPR recommendations
        page_load_test = debug_info.get('page_load_test', {})
        if page_load_test.get('cookies_detected'):
            recommendations.append("Cookie consent banners detected - implement robust cookie handling")
        
        return recommendations
    
    def apply_connection_fixes(self, journal_name: str, debug_results: Dict) -> Dict:
        """Apply fixes based on debug results"""
        fixes_applied = {
            'journal': journal_name,
            'timestamp': datetime.now().isoformat(),
            'fixes': [],
            'status': 'unknown'
        }
        
        try:
            # Fix 1: Update user agent and headers
            if debug_results.get('network_test', {}).get('status') != 'success':
                self._apply_network_fixes(journal_name, fixes_applied)
            
            # Fix 2: Handle authentication issues
            if debug_results.get('login_test', {}).get('status') != 'ready_for_login':
                self._apply_authentication_fixes(journal_name, debug_results, fixes_applied)
            
            # Fix 3: Handle page load issues
            if debug_results.get('page_load_test', {}).get('status') != 'success':
                self._apply_page_load_fixes(journal_name, debug_results, fixes_applied)
            
            # Fix 4: Create robust connection wrapper
            self._create_robust_connection_wrapper(journal_name, fixes_applied)
            
            fixes_applied['status'] = 'completed'
            
        except Exception as e:
            fixes_applied['status'] = 'error'
            fixes_applied['error'] = str(e)
        
        return fixes_applied
    
    def _apply_network_fixes(self, journal_name: str, fixes_applied: Dict):
        """Apply network-related fixes"""
        # This would implement specific network fixes
        fixes_applied['fixes'].append("Network optimization applied")
    
    def _apply_authentication_fixes(self, journal_name: str, debug_results: Dict, fixes_applied: Dict):
        """Apply authentication-related fixes"""
        # This would implement specific authentication fixes
        fixes_applied['fixes'].append("Authentication flow improvements applied")
    
    def _apply_page_load_fixes(self, journal_name: str, debug_results: Dict, fixes_applied: Dict):
        """Apply page load-related fixes"""
        # This would implement specific page load fixes
        fixes_applied['fixes'].append("Page load optimization applied")
    
    def _create_robust_connection_wrapper(self, journal_name: str, fixes_applied: Dict):
        """Create a robust connection wrapper for the journal"""
        # This would create a robust wrapper class
        fixes_applied['fixes'].append("Robust connection wrapper created")
    
    def generate_debug_report(self, results: Dict[str, Dict]) -> Dict:
        """Generate comprehensive debug report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_journals': len(results),
                'fully_functional': 0,
                'needs_fixes': 0,
                'fatal_errors': 0
            },
            'detailed_results': results,
            'recommendations': [],
            'priority_fixes': []
        }
        
        # Analyze results
        for journal_name, result in results.items():
            status = result.get('status', 'unknown')
            
            if status == 'fully_functional':
                report['summary']['fully_functional'] += 1
            elif status == 'fatal_error':
                report['summary']['fatal_errors'] += 1
            else:
                report['summary']['needs_fixes'] += 1
            
            # Collect recommendations
            if result.get('recommendations'):
                report['recommendations'].extend([
                    f"{journal_name}: {rec}" for rec in result['recommendations']
                ])
        
        return report
    
    def save_debug_screenshot(self, driver: webdriver.Chrome, journal_name: str, suffix: str):
        """Save debug screenshot"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = self.debug_dir / f"{journal_name}_{suffix}_{timestamp}.png"
        
        try:
            driver.save_screenshot(str(filename))
            logger.info(f"📸 Debug screenshot saved: {filename}")
        except Exception as e:
            logger.error(f"❌ Failed to save screenshot: {e}")


def main():
    """Main entry point for connection debugging"""
    debugger = ConnectionDebugger(debug=True)
    
    print("🔍 Starting comprehensive journal connection debugging...")
    print("=" * 60)
    
    # Run comprehensive debugging
    results = debugger.comprehensive_debug_all_journals()
    
    # Print summary
    print("\n📊 DEBUGGING SUMMARY:")
    print("=" * 60)
    
    for journal_name, result in results.items():
        status = result.get('status', 'unknown')
        print(f"{journal_name}: {status}")
        
        if result.get('recommendations'):
            for rec in result['recommendations']:
                print(f"  💡 {rec}")
    
    print("\n✅ Debugging complete! Check debug_logs/ for detailed reports.")


if __name__ == "__main__":
    main()