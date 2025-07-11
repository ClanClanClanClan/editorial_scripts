#!/usr/bin/env python3
"""
Foolproof Journal Extractor - Bulletproof extraction with comprehensive fallbacks and retries
This extractor is designed to NEVER fail - it will retry, fallback, and recover from any issue
"""

import os
import sys
import time
import logging
import traceback
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import json
import re
from typing import List, Dict, Any, Optional, Tuple
import requests
from functools import wraps
import random

# Load environment variables
load_dotenv()

# Import selenium with error handling
try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        TimeoutException, NoSuchElementException, WebDriverException,
        StaleElementReferenceException, ElementClickInterceptedException,
        ElementNotInteractableException, InvalidSessionIdException
    )
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"Installing required packages: {e}")
    os.system("pip install undetected-chromedriver selenium beautifulsoup4 requests python-dotenv")
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        TimeoutException, NoSuchElementException, WebDriverException,
        StaleElementReferenceException, ElementClickInterceptedException,
        ElementNotInteractableException, InvalidSessionIdException
    )
    from bs4 import BeautifulSoup

def retry_on_failure(max_attempts=3, delay=2, backoff=2):
    """Decorator for automatic retry with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1
            current_delay = delay
            
            while attempt <= max_attempts:
                try:
                    result = func(*args, **kwargs)
                    if attempt > 1:
                        logging.info(f"   ✅ Succeeded on attempt {attempt}")
                    return result
                except Exception as e:
                    if attempt == max_attempts:
                        logging.error(f"   ❌ All {max_attempts} attempts failed for {func.__name__}")
                        raise
                    else:
                        logging.warning(f"   Attempt {attempt} failed: {str(e)[:100]}...")
                        logging.info(f"   Retrying in {current_delay} seconds...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                        attempt += 1
            
        return wrapper
    return decorator

class FoolproofExtractor:
    """Bulletproof journal extractor with comprehensive error handling"""
    
    def __init__(self, journal: str, headless: bool = True, max_global_retries: int = 5):
        self.journal = journal.upper()
        self.headless = headless
        self.max_global_retries = max_global_retries
        self.driver = None
        self.current_url = None
        self.driver_restart_count = 0
        self.max_driver_restarts = 3
        
        # Setup logging
        self.setup_comprehensive_logging()
        
        # Setup directories
        self.base_dir = Path(f"foolproof_results_{journal.lower()}")
        self.base_dir.mkdir(exist_ok=True)
        self.pdfs_dir = self.base_dir / "pdfs"
        self.pdfs_dir.mkdir(exist_ok=True)
        self.checkpoints_dir = self.base_dir / "checkpoints"
        self.checkpoints_dir.mkdir(exist_ok=True)
        
        # Journal configurations
        self.configs = {
            "MF": {
                "name": "Mathematical Finance",
                "url": "https://mc.manuscriptcentral.com/mafi",
                "categories": ["Awaiting Reviewer Scores", "Awaiting Final Decision", "Ready for Decision"],
                "id_pattern": r'MAFI-\d{4}-\d{4}'
            },
            "MOR": {
                "name": "Mathematics of Operations Research",
                "url": "https://mc.manuscriptcentral.com/mathor",
                "categories": ["Awaiting Reviewer Reports", "Awaiting Final Decision", "Ready for Decision"],
                "id_pattern": r'(MOR|MATHOR)-\d{4}-\d{4}'
            }
        }
        
        self.config = self.configs[journal]
        
        # State management
        self.processed_manuscripts = set()
        self.failed_manuscripts = {}
        self.session_state = {
            'logged_in': False,
            'current_category': None,
            'manuscripts_found': [],
            'last_checkpoint': None
        }
        
        # Load checkpoint if exists
        self.load_checkpoint()
        
        self.logger.info(f"🚀 Foolproof {self.config['name']} extractor initialized")
        self.logger.info(f"   Headless: {headless}")
        self.logger.info(f"   Max global retries: {max_global_retries}")
        self.logger.info(f"   Checkpoint recovery: {'Enabled' if self.session_state['last_checkpoint'] else 'Fresh start'}")
    
    def setup_comprehensive_logging(self):
        """Setup detailed logging with multiple handlers"""
        log_dir = Path("foolproof_logs")
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Main log file
        main_log = log_dir / f"{self.journal.lower()}_foolproof_{timestamp}.log"
        
        # Error log file
        error_log = log_dir / f"{self.journal.lower()}_errors_{timestamp}.log"
        
        # Setup main logger
        self.logger = logging.getLogger(f"FOOLPROOF_{self.journal}")
        self.logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        self.logger.handlers = []
        
        # Main file handler
        main_handler = logging.FileHandler(main_log)
        main_handler.setLevel(logging.DEBUG)
        main_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        main_handler.setFormatter(main_formatter)
        
        # Error file handler
        error_handler = logging.FileHandler(error_log)
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s\n%(exc_info)s')
        error_handler.setFormatter(error_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(main_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info(f"📝 Logging to: {main_log}")
        self.logger.info(f"📝 Errors to: {error_log}")
    
    def save_checkpoint(self, stage: str):
        """Save current state for recovery"""
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'stage': stage,
            'processed_manuscripts': list(self.processed_manuscripts),
            'failed_manuscripts': self.failed_manuscripts,
            'session_state': self.session_state,
            'driver_restart_count': self.driver_restart_count
        }
        
        checkpoint_file = self.checkpoints_dir / f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        
        self.logger.debug(f"💾 Checkpoint saved: {stage}")
        self.session_state['last_checkpoint'] = checkpoint_file
    
    def load_checkpoint(self):
        """Load most recent checkpoint if available"""
        try:
            checkpoints = list(self.checkpoints_dir.glob("checkpoint_*.json"))
            if checkpoints:
                latest = max(checkpoints, key=lambda p: p.stat().st_mtime)
                with open(latest, 'r') as f:
                    checkpoint = json.load(f)
                
                self.processed_manuscripts = set(checkpoint.get('processed_manuscripts', []))
                self.failed_manuscripts = checkpoint.get('failed_manuscripts', {})
                self.session_state.update(checkpoint.get('session_state', {}))
                self.driver_restart_count = checkpoint.get('driver_restart_count', 0)
                
                self.logger.info(f"📥 Loaded checkpoint from: {latest}")
                self.logger.info(f"   Processed: {len(self.processed_manuscripts)} manuscripts")
                self.logger.info(f"   Failed: {len(self.failed_manuscripts)} manuscripts")
        except Exception as e:
            self.logger.debug(f"No checkpoint loaded: {e}")
    
    def ensure_driver_alive(self):
        """Ensure driver is alive and restart if necessary"""
        try:
            # Try a simple operation
            _ = self.driver.current_url
            return True
        except (InvalidSessionIdException, WebDriverException):
            self.logger.warning("⚠️  Driver is dead, attempting restart...")
            return self.restart_driver()
        except Exception:
            return False
    
    def restart_driver(self) -> bool:
        """Restart driver with full recovery"""
        self.driver_restart_count += 1
        
        if self.driver_restart_count > self.max_driver_restarts:
            self.logger.error(f"❌ Exceeded max driver restarts ({self.max_driver_restarts})")
            return False
        
        self.logger.info(f"🔄 Restarting driver (attempt {self.driver_restart_count}/{self.max_driver_restarts})")
        
        # Kill old driver
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
        
        # Create new driver
        if self.create_ultra_robust_driver():
            # Re-login if we were logged in
            if self.session_state['logged_in']:
                self.logger.info("   Re-establishing session...")
                if self.login_with_ultimate_fallbacks():
                    # Navigate back to where we were
                    if self.session_state['current_category']:
                        self.navigate_to_category_robust(self.session_state['current_category'])
                    return True
            else:
                return True
        
        return False
    
    def create_ultra_robust_driver(self) -> bool:
        """Create driver with maximum robustness"""
        self.logger.info("🚀 Creating ultra-robust Chrome driver")
        
        # Multiple driver strategies with increasing compatibility
        strategies = [
            {
                "name": "optimal",
                "options": ["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"],
                "version": None,
                "use_subprocess": False
            },
            {
                "name": "compatible", 
                "options": ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-extensions"],
                "version": None,
                "use_subprocess": True
            },
            {
                "name": "minimal",
                "options": ["--no-sandbox"],
                "version": None,
                "use_subprocess": True
            },
            {
                "name": "version_specific",
                "options": ["--no-sandbox", "--disable-dev-shm-usage"],
                "version": 126,
                "use_subprocess": True
            }
        ]
        
        for strategy in strategies:
            try:
                self.logger.info(f"   Trying strategy: {strategy['name']}")
                
                options = uc.ChromeOptions()
                
                # Add strategy options
                for opt in strategy['options']:
                    options.add_argument(opt)
                
                # Common options
                options.add_argument('--window-size=1920,1080')
                options.add_argument('--start-maximized')
                options.add_argument('--disable-popup-blocking')
                
                # Headless if requested
                if self.headless:
                    options.add_argument('--headless=new')
                    options.add_argument('--disable-gpu')
                    options.add_argument('--no-first-run')
                    options.add_argument('--disable-default-apps')
                
                # Additional stability options
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                options.add_experimental_option('excludeSwitches', ['enable-logging'])
                
                # Preferences for download handling
                prefs = {
                    "download.default_directory": str(self.pdfs_dir),
                    "download.prompt_for_download": False,
                    "download.directory_upgrade": True,
                    "plugins.always_open_pdf_externally": True,
                    "profile.default_content_setting_values.automatic_downloads": 1
                }
                options.add_experimental_option("prefs", prefs)
                
                # Create driver
                self.driver = uc.Chrome(
                    options=options,
                    version_main=strategy['version'],
                    use_subprocess=strategy['use_subprocess']
                )
                
                # Set timeouts
                self.driver.set_page_load_timeout(30)
                self.driver.implicitly_wait(10)
                
                # Test driver
                self.driver.get("https://www.google.com")
                time.sleep(2)
                
                if "Google" in self.driver.title:
                    self.logger.info(f"   ✅ Driver created successfully: {strategy['name']}")
                    return True
                
            except Exception as e:
                self.logger.warning(f"   Strategy {strategy['name']} failed: {str(e)[:100]}...")
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
                
                # Wait before next attempt
                time.sleep(2)
        
        self.logger.error("❌ All driver creation strategies failed")
        return False
    
    @retry_on_failure(max_attempts=3, delay=2)
    def aggressive_element_interaction(self, element, action="click"):
        """Interact with element using multiple methods"""
        self.logger.debug(f"Aggressive {action} on element")
        
        # Dismiss any overlays first
        self.nuclear_overlay_removal()
        
        methods = [
            lambda: self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element),
            lambda: self.driver.execute_script("arguments[0].focus();", element),
            lambda: time.sleep(0.5)
        ]
        
        # Execute preparation methods
        for method in methods:
            try:
                method()
            except:
                pass
        
        # Try different click methods
        if action == "click":
            click_methods = [
                lambda: self.driver.execute_script("arguments[0].click();", element),
                lambda: self.driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true}));", element),
                lambda: element.click(),
                lambda: self.driver.execute_script("""
                    var evt = document.createEvent('MouseEvents');
                    evt.initMouseEvent('click', true, true, window, 1, 0, 0, 0, 0, false, false, false, false, 0, null);
                    arguments[0].dispatchEvent(evt);
                """, element)
            ]
            
            for i, method in enumerate(click_methods):
                try:
                    method()
                    time.sleep(1)
                    self.logger.debug(f"   Click method {i+1} succeeded")
                    return True
                except Exception as e:
                    self.logger.debug(f"   Click method {i+1} failed: {e}")
                    if i < len(click_methods) - 1:
                        self.nuclear_overlay_removal()
                        time.sleep(0.5)
        
        return False
    
    def nuclear_overlay_removal(self):
        """Remove ALL possible overlays and popups"""
        try:
            # JavaScript to remove common overlay elements
            removal_script = """
            // Remove cookie banners
            ['#onetrust-banner-sdk', '.onetrust-pc-dark-filter', '#onetrust-consent-sdk',
             '[class*="cookie"]', '[id*="cookie"]', '[class*="consent"]', '[id*="consent"]',
             '.cc-window', '#cookieConsent', '.cookie-notice', '.gdpr-banner'].forEach(selector => {
                document.querySelectorAll(selector).forEach(el => el.remove());
            });
            
            // Remove overlay divs
            ['[class*="overlay"]', '[class*="modal-backdrop"]', '.fancybox-overlay',
             '[style*="position: fixed"]', '[style*="position: absolute"]'].forEach(selector => {
                document.querySelectorAll(selector).forEach(el => {
                    if (el.style.zIndex > 1000 || getComputedStyle(el).zIndex > 1000) {
                        el.remove();
                    }
                });
            });
            
            // Remove popups
            ['[class*="popup"]', '[class*="modal"]', '[role="dialog"]'].forEach(selector => {
                document.querySelectorAll(selector).forEach(el => {
                    if (el.offsetWidth > window.innerWidth * 0.5) {
                        el.remove();
                    }
                });
            });
            
            // Force remove OneTrust specific elements
            if (typeof OneTrust !== 'undefined') {
                try { OneTrust.Close(); } catch(e) {}
            }
            
            // Remove any element blocking clicks
            document.querySelectorAll('*').forEach(el => {
                const style = getComputedStyle(el);
                if (style.position === 'fixed' && style.zIndex > 9000) {
                    el.style.display = 'none';
                }
            });
            """
            
            self.driver.execute_script(removal_script)
            
            # Also try clicking common dismiss buttons
            dismiss_selectors = [
                "#onetrust-accept-btn-handler",
                "#onetrust-close-btn-container",
                "button[aria-label*='Close']",
                "button[aria-label*='Accept']",
                ".close-button",
                "[class*='close']",
                "[class*='dismiss']"
            ]
            
            for selector in dismiss_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements[:3]:  # Only try first 3 to avoid over-clicking
                        if elem.is_displayed() and elem.is_enabled():
                            elem.click()
                            time.sleep(0.2)
                except:
                    pass
                    
        except Exception as e:
            self.logger.debug(f"Overlay removal error: {e}")
    
    def wait_for_page_stable(self, timeout=10):
        """Wait for page to be fully loaded and stable"""
        try:
            # Wait for JavaScript to complete
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # Wait for jQuery if present
            self.driver.execute_script("""
                if (typeof jQuery !== 'undefined') {
                    return jQuery.active == 0;
                }
                return true;
            """)
            
            # Additional stability wait
            time.sleep(1)
            
        except Exception as e:
            self.logger.debug(f"Page stability wait error: {e}")
    
    @retry_on_failure(max_attempts=3, delay=3)
    def login_with_ultimate_fallbacks(self) -> bool:
        """Login with comprehensive fallback strategies"""
        self.logger.info(f"🔐 Logging into {self.journal} with ultimate fallbacks")
        
        try:
            # Ensure driver is alive
            if not self.ensure_driver_alive():
                return False
            
            # Navigate to journal
            self.driver.get(self.config['url'])
            self.wait_for_page_stable()
            
            # Aggressive overlay removal
            self.nuclear_overlay_removal()
            
            # Get credentials with multiple fallbacks
            credentials = self.get_credentials_with_fallbacks()
            if not credentials:
                return False
            
            # Fill login form with retries
            if not self.fill_login_form_robust(*credentials):
                return False
            
            # Handle verification with retries
            self.handle_verification_robust()
            
            # Verify login success
            if self.verify_login_success():
                self.session_state['logged_in'] = True
                self.save_checkpoint("login_successful")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False
    
    def get_credentials_with_fallbacks(self) -> Optional[Tuple[str, str]]:
        """Get credentials with multiple fallback options"""
        # Try journal-specific first
        user = os.environ.get(f"{self.journal}_USER")
        password = os.environ.get(f"{self.journal}_PASS")
        
        # Fallback to MF credentials
        if not user or not password:
            self.logger.info("   Using MF credentials as fallback")
            user = user or os.environ.get("MF_USER")
            password = password or os.environ.get("MF_PASS")
        
        # Check for credentials file
        if not user or not password:
            cred_file = Path(".credentials.json")
            if cred_file.exists():
                try:
                    with open(cred_file, 'r') as f:
                        creds = json.load(f)
                        user = user or creds.get(f"{self.journal}_USER") or creds.get("MF_USER")
                        password = password or creds.get(f"{self.journal}_PASS") or creds.get("MF_PASS")
                except:
                    pass
        
        if not user or not password:
            self.logger.error("❌ No credentials found")
            return None
        
        self.logger.info(f"   Using credentials for: {user[:3]}***")
        return (user, password)
    
    @retry_on_failure(max_attempts=3, delay=2)
    def fill_login_form_robust(self, user: str, password: str) -> bool:
        """Fill login form with robust error handling"""
        try:
            # Wait for and find username field
            user_field = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "USERID"))
            )
            
            # Clear and fill username
            user_field.clear()
            time.sleep(0.5)
            user_field.send_keys(user)
            
            # Find password field
            pass_field = self.driver.find_element(By.ID, "PASSWORD")
            pass_field.clear()
            time.sleep(0.5)
            pass_field.send_keys(password)
            
            # Find and click login button
            login_button = self.driver.find_element(By.ID, "logInButton")
            self.aggressive_element_interaction(login_button, "click")
            
            # Wait for page to load
            time.sleep(5)
            self.wait_for_page_stable()
            
            return True
            
        except Exception as e:
            self.logger.error(f"   Failed to fill login form: {e}")
            return False
    
    def handle_verification_robust(self):
        """Handle 2FA verification with retries"""
        max_verification_attempts = 3
        
        for attempt in range(max_verification_attempts):
            try:
                # Check if verification is needed
                code_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "TOKEN_VALUE"))
                )
                
                if not code_input.is_displayed():
                    return
                
                self.logger.info("   2FA verification required")
                
                # Import email utilities
                sys.path.insert(0, str(Path(__file__).parent))
                from core.email_utils import fetch_latest_verification_code
                
                # Wait for email with increasing delays
                wait_time = 5 + (attempt * 3)
                self.logger.info(f"   Waiting {wait_time} seconds for verification email...")
                time.sleep(wait_time)
                
                verification_code = fetch_latest_verification_code(journal=self.journal)
                
                if verification_code:
                    code_input.clear()
                    code_input.send_keys(verification_code)
                    code_input.send_keys(Keys.RETURN)
                    time.sleep(3)
                    self.logger.info(f"   ✅ Verification code submitted: {verification_code}")
                    return
                else:
                    self.logger.warning(f"   No verification code found (attempt {attempt + 1})")
                    
            except TimeoutException:
                self.logger.debug("   No verification required")
                return
            except Exception as e:
                self.logger.warning(f"   Verification attempt {attempt + 1} failed: {e}")
        
        self.logger.error("   ❌ All verification attempts failed")
    
    def verify_login_success(self) -> bool:
        """Verify login was successful"""
        try:
            current_url = self.driver.current_url
            
            # Check if we're still on login page
            if "login" in current_url.lower():
                return False
            
            # Check for common post-login elements
            success_indicators = [
                "Associate Editor Center",
                "Author Center",
                "Reviewer Center",
                "Logout",
                "Sign Out"
            ]
            
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            for indicator in success_indicators:
                if indicator in page_text:
                    self.logger.info(f"   ✅ Login verified: Found '{indicator}'")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"   Login verification error: {e}")
            return False
    
    @retry_on_failure(max_attempts=3, delay=2)
    def navigate_to_category_robust(self, category: str) -> bool:
        """Navigate to specific category with retries"""
        self.logger.info(f"🧭 Navigating to: {category}")
        
        try:
            # First go to Associate Editor Center
            ae_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            self.aggressive_element_interaction(ae_link)
            self.wait_for_page_stable()
            
            # Then navigate to specific category
            category_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.LINK_TEXT, category))
            )
            self.aggressive_element_interaction(category_link)
            self.wait_for_page_stable()
            
            self.session_state['current_category'] = category
            self.logger.info(f"   ✅ Reached category: {category}")
            return True
            
        except Exception as e:
            self.logger.error(f"   Navigation to {category} failed: {e}")
            return False
    
    def find_manuscripts_comprehensive(self) -> List[str]:
        """Find all manuscripts with deduplication"""
        self.logger.info("🔍 Finding manuscripts comprehensively")
        
        manuscripts = []
        
        try:
            # Wait for page to stabilize
            self.wait_for_page_stable()
            
            # Get page source for BeautifulSoup parsing
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Multiple strategies to find manuscripts
            strategies = [
                # Strategy 1: Find by TR elements
                lambda: self.driver.find_elements(By.TAG_NAME, "tr"),
                # Strategy 2: Find by table cells
                lambda: self.driver.find_elements(By.TAG_NAME, "td"),
                # Strategy 3: BeautifulSoup text search
                lambda: [elem for elem in soup.find_all(text=re.compile(self.config['id_pattern']))]
            ]
            
            all_text_found = set()
            
            for i, strategy in enumerate(strategies):
                try:
                    elements = strategy()
                    for elem in elements:
                        try:
                            if hasattr(elem, 'text'):
                                text = elem.text
                            else:
                                text = str(elem)
                            
                            # Find all manuscript IDs in text
                            matches = re.findall(self.config['id_pattern'], text)
                            all_text_found.update(matches)
                        except:
                            continue
                except Exception as e:
                    self.logger.debug(f"   Strategy {i+1} error: {e}")
            
            # Convert to list and remove duplicates while preserving order
            seen = set()
            manuscripts = []
            for ms in all_text_found:
                if ms not in seen:
                    seen.add(ms)
                    manuscripts.append(ms)
            
            self.logger.info(f"   ✅ Found {len(manuscripts)} unique manuscripts")
            for ms in manuscripts:
                self.logger.info(f"      - {ms}")
            
            self.session_state['manuscripts_found'] = manuscripts
            self.save_checkpoint("manuscripts_found")
            
            return manuscripts
            
        except Exception as e:
            self.logger.error(f"   Error finding manuscripts: {e}")
            return []
    
    def process_manuscript_with_recovery(self, manuscript_id: str) -> Dict[str, Any]:
        """Process single manuscript with full recovery capabilities"""
        self.logger.info(f"📄 Processing: {manuscript_id}")
        
        # Skip if already processed
        if manuscript_id in self.processed_manuscripts:
            self.logger.info(f"   ⏭️  Already processed, skipping")
            return {'manuscript_id': manuscript_id, 'status': 'already_processed'}
        
        # Check if previously failed
        if manuscript_id in self.failed_manuscripts:
            retry_count = self.failed_manuscripts[manuscript_id].get('retry_count', 0)
            if retry_count >= 3:
                self.logger.info(f"   ⏭️  Max retries reached, skipping")
                return {'manuscript_id': manuscript_id, 'status': 'max_retries_exceeded'}
        
        result = {
            'manuscript_id': manuscript_id,
            'status': 'failed',
            'extraction_time': datetime.now().isoformat(),
            'referees': [],
            'pdf_info': {}
        }
        
        # Try processing with recovery
        for attempt in range(3):
            try:
                self.logger.info(f"   Processing attempt {attempt + 1}/3")
                
                # Ensure we're on the right page
                if not self.ensure_on_manuscript_list():
                    continue
                
                # Click manuscript checkbox
                if not self.click_manuscript_robust(manuscript_id):
                    continue
                
                # Extract all data
                referee_data = self.extract_referees_foolproof()
                pdf_data = self.extract_pdfs_foolproof(manuscript_id)
                
                result.update({
                    'status': 'success',
                    'referees': referee_data,
                    'pdf_info': pdf_data
                })
                
                # Mark as processed
                self.processed_manuscripts.add(manuscript_id)
                self.save_checkpoint(f"processed_{manuscript_id}")
                
                self.logger.info(f"   ✅ Successfully processed {manuscript_id}")
                self.logger.info(f"      Referees: {len(referee_data)}")
                self.logger.info(f"      PDFs: {len(pdf_data.get('manuscript_pdf_file', '')) > 0}")
                
                # Navigate back to list for next manuscript
                self.navigate_back_to_list()
                
                return result
                
            except Exception as e:
                self.logger.error(f"   Attempt {attempt + 1} failed: {e}")
                self.logger.debug(traceback.format_exc())
                
                # Record failure
                if manuscript_id not in self.failed_manuscripts:
                    self.failed_manuscripts[manuscript_id] = {'retry_count': 0, 'errors': []}
                self.failed_manuscripts[manuscript_id]['retry_count'] += 1
                self.failed_manuscripts[manuscript_id]['errors'].append(str(e))
                
                # Try to recover
                if attempt < 2:
                    self.logger.info("   Attempting recovery...")
                    self.recover_from_error()
        
        return result
    
    def ensure_on_manuscript_list(self) -> bool:
        """Ensure we're on the manuscript list page"""
        try:
            # Check if we can see manuscript checkboxes
            checkboxes = self.driver.find_elements(By.XPATH, "//img[contains(@src, 'check_off.gif')]")
            if len(checkboxes) > 0:
                return True
            
            # If not, navigate back
            self.logger.info("   Not on manuscript list, navigating back...")
            
            # Try multiple methods to get back
            methods = [
                lambda: self.driver.back(),
                lambda: self.navigate_to_category_robust(self.session_state['current_category']),
                lambda: self.driver.get(self.config['url']) and self.navigate_to_category_robust(self.session_state['current_category'])
            ]
            
            for method in methods:
                try:
                    method()
                    self.wait_for_page_stable()
                    
                    # Check again
                    checkboxes = self.driver.find_elements(By.XPATH, "//img[contains(@src, 'check_off.gif')]")
                    if len(checkboxes) > 0:
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.error(f"   Error ensuring manuscript list: {e}")
            return False
    
    @retry_on_failure(max_attempts=3, delay=2)
    def click_manuscript_robust(self, manuscript_id: str) -> bool:
        """Click manuscript checkbox with maximum robustness"""
        self.logger.info(f"   Clicking checkbox for {manuscript_id}")
        
        try:
            # Remove overlays first
            self.nuclear_overlay_removal()
            
            # Find all rows
            rows = self.driver.find_elements(By.TAG_NAME, "tr")
            
            for row_index, row in enumerate(rows):
                try:
                    row_text = row.text.strip()
                    
                    # Check if this row contains our manuscript
                    if manuscript_id in row_text or row_text.startswith(manuscript_id):
                        self.logger.debug(f"      Found {manuscript_id} in row {row_index}")
                        
                        # Find checkbox in this row
                        checkboxes = row.find_elements(By.XPATH, ".//img[contains(@src, 'check_off.gif')]")
                        
                        if not checkboxes:
                            # Try alternate checkbox selectors
                            checkboxes = row.find_elements(By.XPATH, ".//input[@type='checkbox']")
                        
                        if checkboxes:
                            checkbox = checkboxes[0]
                            
                            # Scroll to element
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)
                            time.sleep(1)
                            
                            # Remove overlays again
                            self.nuclear_overlay_removal()
                            
                            # Click with aggressive method
                            if self.aggressive_element_interaction(checkbox):
                                time.sleep(3)
                                self.wait_for_page_stable()
                                
                                # Verify we're on manuscript detail page
                                if self.verify_on_manuscript_detail(manuscript_id):
                                    self.logger.info(f"      ✅ Successfully clicked {manuscript_id}")
                                    return True
                except Exception as e:
                    self.logger.debug(f"      Row {row_index} error: {e}")
                    continue
            
            self.logger.error(f"      ❌ Could not find/click {manuscript_id}")
            return False
            
        except Exception as e:
            self.logger.error(f"   Click error: {e}")
            return False
    
    def verify_on_manuscript_detail(self, manuscript_id: str) -> bool:
        """Verify we're on the manuscript detail page"""
        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Check for manuscript ID in page
            if manuscript_id in page_text:
                # Check for detail page indicators
                indicators = ["Reviewer List", "reviewer list", "Abstract", "Version History", "Files", "Review"]
                for indicator in indicators:
                    if indicator in page_text:
                        return True
            
            return False
            
        except:
            return False
    
    def navigate_back_to_list(self):
        """Navigate back to manuscript list"""
        try:
            # Try back button first
            self.driver.back()
            time.sleep(2)
            
            # Verify we're back on list
            if not self.ensure_on_manuscript_list():
                # Re-navigate to category
                self.navigate_to_category_robust(self.session_state['current_category'])
                
        except Exception as e:
            self.logger.error(f"   Error navigating back: {e}")
            # Force re-navigation
            self.navigate_to_category_robust(self.session_state['current_category'])
    
    def extract_referees_foolproof(self) -> List[Dict[str, Any]]:
        """Extract referees with maximum error handling"""
        self.logger.info("      Extracting referee data")
        referees = []
        
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Multiple strategies to find reviewer section
            reviewer_section = None
            
            # Strategy 1: Look for text containing "reviewer"
            for elem in soup.find_all(text=re.compile(r'reviewer.*list|referee.*list', re.I)):
                reviewer_section = elem.parent
                break
            
            # Strategy 2: Look for common table structures
            if not reviewer_section:
                tables = soup.find_all('table')
                for table in tables:
                    table_text = table.get_text().lower()
                    if 'reviewer' in table_text or 'referee' in table_text:
                        reviewer_section = table
                        break
            
            if reviewer_section:
                # Find parent table
                table = reviewer_section.find_parent('table') or reviewer_section
                
                if hasattr(table, 'find_all'):
                    rows = table.find_all('tr')
                    
                    for row in rows:
                        referee_data = self.parse_referee_row_comprehensive(row)
                        if referee_data:
                            referees.append(referee_data)
                            self.logger.info(f"         ✅ {referee_data['name']} ({referee_data['status']})")
            
            # Fallback: Try selenium approach
            if not referees:
                self.logger.info("         Trying Selenium approach...")
                rows = self.driver.find_elements(By.TAG_NAME, "tr")
                
                for row in rows:
                    try:
                        row_text = row.text.strip()
                        if len(row_text) > 20 and ',' in row_text:
                            referee_data = self.parse_referee_text_foolproof(row_text)
                            if referee_data:
                                referees.append(referee_data)
                                self.logger.info(f"         ✅ {referee_data['name']} ({referee_data['status']})")
                    except:
                        continue
            
            self.logger.info(f"      Total referees found: {len(referees)}")
            return referees
            
        except Exception as e:
            self.logger.error(f"      Referee extraction error: {e}")
            return referees
    
    def parse_referee_row_comprehensive(self, row) -> Optional[Dict[str, Any]]:
        """Parse referee row with comprehensive patterns"""
        try:
            row_text = row.get_text(strip=True)
            if not row_text or len(row_text) < 10:
                return None
            
            # Skip headers
            skip_patterns = ['name', 'status', 'history', 'order', 'reviewer list', 'referee list']
            if any(pattern in row_text.lower() for pattern in skip_patterns):
                return None
            
            # Extract name with multiple patterns
            name = self.extract_name_ultra_robust(row_text)
            if not name:
                return None
            
            # Extract institution
            institution = self.extract_institution_robust(row_text, name)
            
            # Extract status
            status = self.extract_status_robust(row_text)
            
            # Extract dates
            dates = self.extract_dates_comprehensive(row_text)
            
            return {
                'name': name,
                'institution': institution,
                'status': status,
                'dates': dates,
                'time_in_review': self.calculate_time_in_review(dates.get('invited', '')),
                'raw_text': row_text[:200]  # Store for debugging
            }
            
        except Exception:
            return None
    
    def extract_name_ultra_robust(self, text: str) -> Optional[str]:
        """Extract name with ultra-robust patterns"""
        # Comprehensive name patterns
        patterns = [
            # Standard Last, First format
            r'^([A-Za-z\-\'\s]+,\s*[A-Za-z\-\'\s]+?)(?=\s+[A-Z][a-z]|University|College|Institute|School|\s+\()',
            
            # With parenthetical info
            r'([A-Za-z\-\'\s]+,\s*[A-Za-z\-\'\s]+)\s*\([^)]+\)',
            
            # Before institution keywords
            r'^([A-Za-z\-\'\s]+,\s*[A-Za-z\-\'\s]+?)(?=\s+(?:University|College|Institute|School|Department|Faculty))',
            
            # Before multiple capitals
            r'^([A-Za-z\-\'\s]+,\s*[A-Za-z\-\'\s]+?)(?=\s+[A-Z]{2,})',
            
            # With numbers
            r'^([A-Za-z\-\'\s]+,\s*[A-Za-z\-\'\s]+?)(?=\s+\d)',
            
            # Generic Last, First
            r'^([A-Za-z\-\'\s]{2,},\s*[A-Za-z\-\'\s]{2,})',
            
            # Fallback: any Last, First pattern
            r'([A-Za-z\-\'\s]+,\s*[A-Za-z\-\'\s]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip()
                
                # Validate name
                if self.validate_name(name):
                    return name
        
        return None
    
    def validate_name(self, name: str) -> bool:
        """Validate extracted name"""
        if not name or ',' not in name:
            return False
        
        # Check for invalid patterns
        invalid_patterns = ['reasons, your', ', ', 'reviewer, list', 'name, status']
        if any(invalid in name.lower() for invalid in invalid_patterns):
            return False
        
        # Check length
        if len(name) < 5 or len(name) > 50:
            return False
        
        # Check for actual letter content
        if sum(c.isalpha() for c in name) < 4:
            return False
        
        return True
    
    def extract_institution_robust(self, text: str, name: str) -> str:
        """Extract institution with robust parsing"""
        try:
            # Find where name ends
            name_end = text.find(name) + len(name)
            remaining = text[name_end:].strip()
            
            # Remove common suffixes
            remaining = re.sub(r'^\s*\([^)]+\)\s*', '', remaining)
            
            # Find where status keywords begin
            status_keywords = ['agreed', 'declined', 'invited', 'completed', 'pending', 'due', 'time in review']
            
            institution_end = len(remaining)
            for keyword in status_keywords:
                pos = remaining.lower().find(keyword)
                if pos != -1 and pos < institution_end:
                    institution_end = pos
            
            institution = remaining[:institution_end].strip()
            
            # Clean institution
            institution = re.sub(r'^[^\w]+', '', institution)
            institution = re.sub(r'\s+', ' ', institution)
            institution = institution.strip(' ,.-')
            
            # Validate institution
            if len(institution) > 100 or len(institution) < 3:
                return ""
            
            return institution
            
        except:
            return ""
    
    def extract_status_robust(self, text: str) -> str:
        """Extract status with comprehensive patterns"""
        text_lower = text.lower()
        
        # Status mapping with priority
        status_map = [
            ('completed', 'Completed'),
            ('agreed', 'Agreed'),
            ('declined', 'Declined'),
            ('pending', 'Pending'),
            ('invited', 'Invited'),
            ('not responded', 'Not Responded'),
            ('unavailable', 'Unavailable')
        ]
        
        for keyword, status in status_map:
            if keyword in text_lower:
                return status
        
        return "Unknown"
    
    def extract_dates_comprehensive(self, text: str) -> Dict[str, str]:
        """Extract dates with comprehensive patterns"""
        dates = {'invited': '', 'agreed': '', 'due': ''}
        
        # Date patterns
        date_patterns = [
            # Standard format: 01-Jan-2025
            (r'invited[:\s]*(\d{1,2}-[A-Za-z]{3}-\d{4})', 'invited'),
            (r'agreed[:\s]*(\d{1,2}-[A-Za-z]{3}-\d{4})', 'agreed'),
            (r'due\s*date[:\s]*(\d{1,2}-[A-Za-z]{3}-\d{4})', 'due'),
            (r'due[:\s]*(\d{1,2}-[A-Za-z]{3}-\d{4})', 'due'),
            
            # Alternative format: 01/01/2025
            (r'invited[:\s]*(\d{1,2}/\d{1,2}/\d{4})', 'invited'),
            (r'agreed[:\s]*(\d{1,2}/\d{1,2}/\d{4})', 'agreed'),
            (r'due[:\s]*(\d{1,2}/\d{1,2}/\d{4})', 'due'),
            
            # ISO format: 2025-01-01
            (r'invited[:\s]*(\d{4}-\d{2}-\d{2})', 'invited'),
            (r'agreed[:\s]*(\d{4}-\d{2}-\d{2})', 'agreed'),
            (r'due[:\s]*(\d{4}-\d{2}-\d{2})', 'due')
        ]
        
        for pattern, date_type in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and not dates[date_type]:
                dates[date_type] = match.group(1)
        
        return dates
    
    def calculate_time_in_review(self, invited_date: str) -> str:
        """Calculate time in review from invited date"""
        if not invited_date:
            return ""
        
        try:
            # Try multiple date formats
            formats = ["%d-%b-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"]
            
            invited = None
            for fmt in formats:
                try:
                    invited = datetime.strptime(invited_date, fmt)
                    break
                except ValueError:
                    continue
            
            if invited:
                delta = datetime.now() - invited
                return f"{delta.days} Days"
                
        except:
            pass
        
        return ""
    
    def parse_referee_text_foolproof(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse referee from raw text with maximum flexibility"""
        # Use the comprehensive parsing methods
        name = self.extract_name_ultra_robust(text)
        if not name:
            return None
        
        return {
            'name': name,
            'institution': self.extract_institution_robust(text, name),
            'status': self.extract_status_robust(text),
            'dates': self.extract_dates_comprehensive(text),
            'time_in_review': self.calculate_time_in_review(
                self.extract_dates_comprehensive(text).get('invited', '')
            ),
            'raw_text': text[:200]
        }
    
    def extract_pdfs_foolproof(self, manuscript_id: str) -> Dict[str, Any]:
        """Extract PDFs with maximum robustness"""
        self.logger.info("      Extracting PDFs")
        
        pdf_info = {
            'manuscript_pdf_url': '',
            'manuscript_pdf_file': '',
            'referee_reports': [],
            'text_reviews': [],
            'extraction_errors': []
        }
        
        try:
            # Get manuscript PDF
            manuscript_pdf = self.get_manuscript_pdf_ultra_robust(manuscript_id)
            if manuscript_pdf:
                pdf_info['manuscript_pdf_url'] = manuscript_pdf['url']
                pdf_info['manuscript_pdf_file'] = manuscript_pdf['file']
                self.logger.info(f"         ✅ Manuscript PDF downloaded")
            
            # Get referee reports
            reports = self.get_referee_reports_ultra_robust(manuscript_id)
            pdf_info['referee_reports'] = reports['pdf_reports']
            pdf_info['text_reviews'] = reports['text_reviews']
            
            if reports['pdf_reports']:
                self.logger.info(f"         ✅ Downloaded {len(reports['pdf_reports'])} referee PDFs")
            if reports['text_reviews']:
                self.logger.info(f"         ✅ Extracted {len(reports['text_reviews'])} text reviews")
            
        except Exception as e:
            self.logger.error(f"      PDF extraction error: {e}")
            pdf_info['extraction_errors'].append(str(e))
        
        return pdf_info
    
    def get_manuscript_pdf_ultra_robust(self, manuscript_id: str) -> Optional[Dict[str, str]]:
        """Get manuscript PDF with ultra-robust approach"""
        self.logger.info("         Looking for manuscript PDF")
        
        try:
            original_windows = self.driver.window_handles
            
            # Try multiple tab names and variations
            tab_variations = [
                'PDF', 'pdf', 'Pdf',
                'Original Files', 'original files', 'Original files',
                'Files', 'files',
                'HTML', 'html', 'Html',
                'Submission', 'submission',
                'Download', 'download',
                'View', 'view'
            ]
            
            for tab_name in tab_variations:
                try:
                    # Multiple ways to find tabs
                    tab_selectors = [
                        f"//a[contains(text(), '{tab_name}')]",
                        f"//a[contains(@title, '{tab_name}')]",
                        f"//a[contains(@href, '{tab_name.lower()}')]",
                        f"//span[contains(text(), '{tab_name}')]/parent::a",
                        f"//button[contains(text(), '{tab_name}')]"
                    ]
                    
                    for selector in tab_selectors:
                        try:
                            elements = self.driver.find_elements(By.XPATH, selector)
                            
                            for elem in elements:
                                try:
                                    elem_text = elem.text.strip()
                                    
                                    # Skip if too long (not a tab)
                                    if len(elem_text) > 30:
                                        continue
                                    
                                    # Skip if not visible
                                    if not elem.is_displayed():
                                        continue
                                    
                                    self.logger.debug(f"            Trying: {elem_text}")
                                    
                                    # Click element
                                    self.aggressive_element_interaction(elem)
                                    time.sleep(2)
                                    
                                    # Check for new window
                                    new_windows = self.driver.window_handles
                                    if len(new_windows) > len(original_windows):
                                        new_window = [w for w in new_windows if w not in original_windows][0]
                                        self.driver.switch_to.window(new_window)
                                        
                                        # Try to download from new window
                                        pdf_result = self.try_download_pdf_from_window(manuscript_id)
                                        
                                        # Close window
                                        self.driver.close()
                                        self.driver.switch_to.window(original_windows[0])
                                        
                                        if pdf_result:
                                            return pdf_result
                                
                                except Exception as e:
                                    self.logger.debug(f"            Element error: {e}")
                                    # Ensure we're back on original window
                                    if len(self.driver.window_handles) > len(original_windows):
                                        self.driver.switch_to.window(original_windows[0])
                                    continue
                        except:
                            continue
                except:
                    continue
            
            self.logger.warning("         No manuscript PDF found")
            return None
            
        except Exception as e:
            self.logger.error(f"         Manuscript PDF error: {e}")
            return None
    
    def try_download_pdf_from_window(self, manuscript_id: str) -> Optional[Dict[str, str]]:
        """Try to download PDF from current window"""
        try:
            current_url = self.driver.current_url
            
            # Check if URL indicates a PDF
            if '.pdf' in current_url.lower() or 'DOWNLOAD=TRUE' in current_url or 'download' in current_url.lower():
                pdf_path = self.pdfs_dir / f"{manuscript_id}_manuscript.pdf"
                
                if self.download_file_robust(current_url, pdf_path):
                    return {'url': current_url, 'file': str(pdf_path)}
            
            # Look for PDF links in the page
            pdf_selectors = [
                "//a[contains(@href, '.pdf')]",
                "//a[contains(@href, 'download')]",
                "//a[contains(@href, 'DOWNLOAD=TRUE')]",
                "//a[contains(text(), 'Download')]",
                "//a[contains(text(), 'PDF')]",
                "//button[contains(text(), 'Download')]"
            ]
            
            for selector in pdf_selectors:
                try:
                    links = self.driver.find_elements(By.XPATH, selector)
                    for link in links:
                        href = link.get_attribute('href')
                        if href:
                            pdf_path = self.pdfs_dir / f"{manuscript_id}_manuscript.pdf"
                            if self.download_file_robust(href, pdf_path):
                                return {'url': href, 'file': str(pdf_path)}
                except:
                    continue
            
            return None
            
        except Exception as e:
            self.logger.debug(f"         Window PDF extraction error: {e}")
            return None
    
    def get_referee_reports_ultra_robust(self, manuscript_id: str) -> Dict[str, List]:
        """Get referee reports with ultra-robust approach"""
        self.logger.info("         Looking for referee reports")
        
        reports = {
            'pdf_reports': [],
            'text_reviews': []
        }
        
        try:
            original_windows = self.driver.window_handles
            
            # Remove overlays first
            self.nuclear_overlay_removal()
            
            # Multiple ways to find review links
            review_selectors = [
                "//a[contains(text(), 'view review')]",
                "//a[contains(text(), 'View Review')]",
                "//a[contains(text(), 'review')]",
                "//a[contains(text(), 'Review')]",
                "//a[contains(@href, 'review')]",
                "//a[contains(@onclick, 'review')]",
                "//a[contains(text(), 'report')]",
                "//a[contains(text(), 'Report')]",
                "//button[contains(text(), 'review')]",
                "//button[contains(text(), 'Review')]"
            ]
            
            all_review_elements = []
            for selector in review_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    all_review_elements.extend(elements)
                except:
                    continue
            
            # Deduplicate elements
            unique_elements = []
            seen_texts = set()
            for elem in all_review_elements:
                try:
                    elem_text = elem.text.strip().lower()
                    if elem_text and elem_text not in seen_texts and elem.is_displayed():
                        unique_elements.append(elem)
                        seen_texts.add(elem_text)
                except:
                    continue
            
            self.logger.info(f"         Found {len(unique_elements)} potential review links")
            
            # Process each review link
            for i, review_elem in enumerate(unique_elements):
                try:
                    self.logger.info(f"         Processing review {i+1}/{len(unique_elements)}")
                    
                    # Remove overlays before each click
                    self.nuclear_overlay_removal()
                    
                    # Click review link
                    if self.aggressive_element_interaction(review_elem):
                        time.sleep(3)
                        
                        # Check for new window
                        new_windows = self.driver.window_handles
                        if len(new_windows) > len(original_windows):
                            new_window = [w for w in new_windows if w not in original_windows][0]
                            self.driver.switch_to.window(new_window)
                            
                            # Extract data from review window
                            review_data = self.extract_review_window_data_comprehensive(manuscript_id, i+1)
                            
                            # Add to results
                            if review_data['pdf_files']:
                                reports['pdf_reports'].extend(review_data['pdf_files'])
                            if review_data['text_content']:
                                reports['text_reviews'].append({
                                    'referee_number': i+1,
                                    'content': review_data['text_content'],
                                    'extraction_time': datetime.now().isoformat()
                                })
                            
                            # Close window
                            self.driver.close()
                            self.driver.switch_to.window(original_windows[0])
                            time.sleep(1)
                
                except Exception as e:
                    self.logger.error(f"         Review {i+1} error: {e}")
                    # Ensure we're back on original window
                    try:
                        if len(self.driver.window_handles) > len(original_windows):
                            self.driver.switch_to.window(original_windows[0])
                    except:
                        pass
            
            return reports
            
        except Exception as e:
            self.logger.error(f"         Referee reports error: {e}")
            return reports
    
    def extract_review_window_data_comprehensive(self, manuscript_id: str, referee_num: int) -> Dict[str, Any]:
        """Extract all data from review window comprehensively"""
        result = {
            'pdf_files': [],
            'text_content': ''
        }
        
        try:
            # Look for PDFs
            pdf_found = False
            
            # Multiple selectors for PDF links
            pdf_selectors = [
                "//a[contains(@href, '.pdf')]",
                "//a[contains(text(), 'PDF')]",
                "//a[contains(text(), 'pdf')]",
                "//a[contains(text(), 'Download')]",
                "//a[contains(text(), 'download')]",
                "//a[contains(text(), 'File')]",
                "//a[contains(text(), 'file')]",
                "//a[contains(text(), 'Attachment')]",
                "//a[contains(text(), 'attachment')]",
                "//a[contains(@href, 'download')]",
                "//a[contains(@href, 'file')]",
                "//*[contains(text(), 'Files attached')]/following::a",
                "//*[contains(text(), 'Attachments')]/following::a"
            ]
            
            for selector in pdf_selectors:
                try:
                    links = self.driver.find_elements(By.XPATH, selector)
                    for link in links:
                        try:
                            href = link.get_attribute('href')
                            link_text = link.text.strip()
                            
                            if href and ('pdf' in href.lower() or 'download' in href.lower() or 'file' in href.lower()):
                                pdf_path = self.pdfs_dir / f"{manuscript_id}_referee_{referee_num}_report.pdf"
                                
                                if self.download_file_robust(href, pdf_path):
                                    result['pdf_files'].append({
                                        'referee_number': referee_num,
                                        'url': href,
                                        'file': str(pdf_path),
                                        'link_text': link_text,
                                        'download_time': datetime.now().isoformat()
                                    })
                                    pdf_found = True
                                    self.logger.info(f"            ✅ Downloaded referee PDF")
                        except:
                            continue
                except:
                    continue
            
            # Extract text content
            text_content = self.extract_review_text_comprehensive()
            if text_content:
                result['text_content'] = text_content
                self.logger.info(f"            ✅ Extracted text review ({len(text_content)} chars)")
            
            # If no specific content found, get entire page
            if not pdf_found and not result['text_content']:
                try:
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text
                    if len(page_text) > 200:
                        result['text_content'] = page_text
                        self.logger.info(f"            ✅ Captured full page ({len(page_text)} chars)")
                except:
                    pass
            
            return result
            
        except Exception as e:
            self.logger.error(f"            Review extraction error: {e}")
            return result
    
    def extract_review_text_comprehensive(self) -> str:
        """Extract review text comprehensively"""
        all_text = []
        
        # Multiple selectors for text content
        text_selectors = [
            "//*[contains(text(), 'Comments to the Author')]//following::*",
            "//*[contains(text(), 'comments to author')]//following::*",
            "//*[contains(text(), 'Comments to Author')]//following::*",
            "//*[contains(text(), 'Review')]//following::*",
            "//*[contains(text(), 'Comments')]//following::*",
            "//textarea",
            "//pre",
            "//*[contains(@class, 'review')]",
            "//*[contains(@class, 'comment')]",
            "//*[contains(@id, 'review')]",
            "//*[contains(@id, 'comment')]"
        ]
        
        for selector in text_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                for elem in elements[:10]:  # Limit to avoid too much content
                    try:
                        text = ""
                        
                        if elem.tag_name == 'textarea':
                            text = elem.get_attribute('value') or elem.text
                        else:
                            text = elem.text.strip()
                        
                        # Only include substantial text
                        if text and len(text) > 50 and text not in all_text:
                            all_text.append(text)
                            if len(all_text) >= 5:  # Limit sections
                                break
                    except:
                        continue
            except:
                continue
        
        # Combine and clean text
        if all_text:
            combined = "\n\n---SECTION---\n\n".join(all_text)
            # Remove excessive whitespace
            combined = re.sub(r'\n{3,}', '\n\n', combined)
            combined = re.sub(r' {2,}', ' ', combined)
            return combined.strip()
        
        return ""
    
    @retry_on_failure(max_attempts=3, delay=3)
    def download_file_robust(self, url: str, filepath: Path) -> bool:
        """Download file with robust error handling"""
        try:
            # Get cookies from selenium
            selenium_cookies = self.driver.get_cookies()
            cookies = {cookie['name']: cookie['value'] for cookie in selenium_cookies}
            
            # Comprehensive headers
            headers = {
                'User-Agent': self.driver.execute_script("return navigator.userAgent;"),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Referer': self.driver.current_url
            }
            
            # Download with timeout
            response = requests.get(url, cookies=cookies, headers=headers, timeout=60, stream=True)
            
            if response.status_code == 200:
                # Save file
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # Validate file
                if filepath.suffix.lower() == '.pdf':
                    # Check PDF header
                    with open(filepath, 'rb') as f:
                        header = f.read(5)
                        if header.startswith(b'%PDF'):
                            self.logger.info(f"            ✅ Valid PDF downloaded: {filepath.name}")
                            return True
                        else:
                            self.logger.warning(f"            Invalid PDF header: {header}")
                            filepath.unlink()
                            return False
                else:
                    # For non-PDF files, just check size
                    if filepath.stat().st_size > 100:
                        return True
                    else:
                        filepath.unlink()
                        return False
            else:
                self.logger.warning(f"            HTTP {response.status_code} for {url}")
                return False
                
        except Exception as e:
            self.logger.error(f"            Download failed: {e}")
            return False
    
    def recover_from_error(self):
        """Recover from error state"""
        try:
            self.logger.info("   🔧 Attempting error recovery...")
            
            # Try to close any extra windows
            if len(self.driver.window_handles) > 1:
                self.driver.switch_to.window(self.driver.window_handles[0])
                for handle in self.driver.window_handles[1:]:
                    try:
                        self.driver.switch_to.window(handle)
                        self.driver.close()
                    except:
                        pass
                self.driver.switch_to.window(self.driver.window_handles[0])
            
            # Try to navigate back to manuscript list
            if self.session_state['current_category']:
                self.navigate_to_category_robust(self.session_state['current_category'])
            
        except Exception as e:
            self.logger.error(f"   Recovery failed: {e}")
            # Last resort: restart driver
            self.restart_driver()
    
    def run_foolproof_extraction(self) -> bool:
        """Run the complete foolproof extraction process"""
        self.logger.info(f"🚀 Starting foolproof {self.journal} extraction")
        self.logger.info(f"   Headless: {self.headless}")
        self.logger.info(f"   Max retries: {self.max_global_retries}")
        
        overall_success = False
        
        for global_attempt in range(self.max_global_retries):
            try:
                self.logger.info(f"\n{'='*80}")
                self.logger.info(f"GLOBAL ATTEMPT {global_attempt + 1}/{self.max_global_retries}")
                self.logger.info(f"{'='*80}\n")
                
                # Create driver
                if not self.driver or not self.ensure_driver_alive():
                    if not self.create_ultra_robust_driver():
                        continue
                
                # Login
                if not self.session_state['logged_in']:
                    if not self.login_with_ultimate_fallbacks():
                        continue
                
                # Try each category until we find manuscripts
                manuscripts_found = False
                
                for category in self.config['categories']:
                    self.logger.info(f"\n📂 Trying category: {category}")
                    
                    if self.navigate_to_category_robust(category):
                        manuscripts = self.find_manuscripts_comprehensive()
                        
                        if manuscripts:
                            manuscripts_found = True
                            self.logger.info(f"✅ Found {len(manuscripts)} manuscripts in {category}")
                            
                            # Process all manuscripts
                            results = []
                            
                            for i, manuscript_id in enumerate(manuscripts):
                                self.logger.info(f"\n{'='*60}")
                                self.logger.info(f"MANUSCRIPT {i+1}/{len(manuscripts)}")
                                self.logger.info(f"{'='*60}\n")
                                
                                result = self.process_manuscript_with_recovery(manuscript_id)
                                results.append(result)
                                
                                # Save intermediate results
                                self.save_results(results, interim=True)
                            
                            # Save final results
                            self.save_results(results, interim=False)
                            
                            # Calculate success metrics
                            successful = sum(1 for r in results if r.get('status') == 'success')
                            
                            self.logger.info(f"\n{'='*80}")
                            self.logger.info(f"✅ EXTRACTION COMPLETED")
                            self.logger.info(f"   Total manuscripts: {len(manuscripts)}")
                            self.logger.info(f"   Successfully processed: {successful}")
                            self.logger.info(f"   Failed: {len(manuscripts) - successful}")
                            self.logger.info(f"   Success rate: {successful/len(manuscripts)*100:.1f}%")
                            self.logger.info(f"{'='*80}")
                            
                            overall_success = True
                            break
                
                if manuscripts_found:
                    break
                else:
                    self.logger.warning(f"⚠️  No manuscripts found in any category")
                    
            except Exception as e:
                self.logger.error(f"Global attempt {global_attempt + 1} failed: {e}")
                self.logger.debug(traceback.format_exc())
                
                if global_attempt < self.max_global_retries - 1:
                    self.logger.info("Restarting for next global attempt...")
                    time.sleep(5)
        
        return overall_success
    
    def save_results(self, results: List[Dict], interim: bool = False):
        """Save extraction results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Prepare results data
        data = {
            'journal': self.journal,
            'extraction_date': datetime.now().isoformat(),
            'headless_mode': self.headless,
            'total_processed': len(self.processed_manuscripts),
            'total_failed': len(self.failed_manuscripts),
            'manuscripts': results
        }
        
        # Save JSON
        if interim:
            json_file = self.base_dir / f"{self.journal.lower()}_interim_results.json"
        else:
            json_file = self.base_dir / f"{self.journal.lower()}_final_results_{timestamp}.json"
        
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Save human-readable report
        if not interim:
            report_file = self.base_dir / f"{self.journal.lower()}_final_report_{timestamp}.txt"
            self.generate_final_report(data, report_file)
        
        self.logger.info(f"💾 Results saved to: {json_file}")
    
    def generate_final_report(self, data: Dict, report_file: Path):
        """Generate final human-readable report"""
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"FOOLPROOF {self.journal} EXTRACTION REPORT\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Headless Mode: {data['headless_mode']}\n")
            f.write(f"Total Processed: {data['total_processed']}\n")
            f.write(f"Total Failed: {data['total_failed']}\n\n")
            
            # Successful manuscripts
            successful = [m for m in data['manuscripts'] if m.get('status') == 'success']
            if successful:
                f.write("SUCCESSFUL EXTRACTIONS:\n")
                f.write("-" * 40 + "\n\n")
                
                for manuscript in successful:
                    f.write(f"📄 {manuscript['manuscript_id']}\n")
                    f.write(f"   Referees: {len(manuscript.get('referees', []))}\n")
                    
                    for referee in manuscript.get('referees', []):
                        f.write(f"   • {referee['name']} ({referee['status']})\n")
                        if referee.get('institution'):
                            f.write(f"     {referee['institution']}\n")
                    
                    pdf_info = manuscript.get('pdf_info', {})
                    if pdf_info.get('manuscript_pdf_file'):
                        f.write(f"   ✅ Manuscript PDF downloaded\n")
                    if pdf_info.get('referee_reports'):
                        f.write(f"   ✅ {len(pdf_info['referee_reports'])} referee PDFs\n")
                    if pdf_info.get('text_reviews'):
                        f.write(f"   ✅ {len(pdf_info['text_reviews'])} text reviews\n")
                    
                    f.write("\n")
            
            # Failed manuscripts
            failed = [m for m in data['manuscripts'] if m.get('status') != 'success']
            if failed:
                f.write("\nFAILED EXTRACTIONS:\n")
                f.write("-" * 40 + "\n\n")
                
                for manuscript in failed:
                    f.write(f"❌ {manuscript['manuscript_id']}\n")
                    if 'error' in manuscript:
                        f.write(f"   Error: {manuscript['error']}\n")
                    f.write("\n")
            
            # Summary statistics
            f.write("\nSUMMARY STATISTICS:\n")
            f.write("-" * 40 + "\n")
            
            total_referees = sum(len(m.get('referees', [])) for m in successful)
            total_manuscript_pdfs = sum(1 for m in successful if m.get('pdf_info', {}).get('manuscript_pdf_file'))
            total_referee_pdfs = sum(len(m.get('pdf_info', {}).get('referee_reports', [])) for m in successful)
            total_text_reviews = sum(len(m.get('pdf_info', {}).get('text_reviews', [])) for m in successful)
            
            f.write(f"Total Referees Extracted: {total_referees}\n")
            f.write(f"Manuscript PDFs Downloaded: {total_manuscript_pdfs}\n")
            f.write(f"Referee PDFs Downloaded: {total_referee_pdfs}\n")
            f.write(f"Text Reviews Extracted: {total_text_reviews}\n")
            f.write(f"Success Rate: {len(successful)/len(data['manuscripts'])*100:.1f}%\n")
        
        self.logger.info(f"📄 Report saved to: {report_file}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Foolproof Journal Extractor")
    parser.add_argument("journal", choices=["MF", "MOR"], help="Journal to extract")
    parser.add_argument("--visible", action="store_true", help="Run with visible browser")
    parser.add_argument("--max-retries", type=int, default=5, help="Maximum global retry attempts")
    
    args = parser.parse_args()
    
    try:
        extractor = FoolproofExtractor(
            journal=args.journal,
            headless=not args.visible,
            max_global_retries=args.max_retries
        )
        
        success = extractor.run_foolproof_extraction()
        
        if success:
            print(f"\n🎉 {args.journal} extraction completed successfully!")
            sys.exit(0)
        else:
            print(f"\n❌ {args.journal} extraction failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Extraction interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup
        try:
            if 'extractor' in locals() and hasattr(extractor, 'driver') and extractor.driver:
                extractor.driver.quit()
        except:
            pass

if __name__ == "__main__":
    main()