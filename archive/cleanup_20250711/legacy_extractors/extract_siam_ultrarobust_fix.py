#!/usr/bin/env python3
"""
Ultra-Robust SIAM Extractor - Fixed version addressing all critical issues
"""

import os
import re
import time
import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import sqlite3
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup


@dataclass
class ExtractionResult:
    """Result of an extraction operation."""
    success: bool
    data: Any = None
    error: str = None
    attempts: int = 0
    timestamp: datetime = None


class UltraRobustCache:
    """Ultra-robust caching system with enhanced file verification."""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize SQLite database for metadata
        self.db_path = cache_dir / 'extraction_cache.db'
        self.init_database()
    
    def init_database(self):
        """Initialize cache database with enhanced schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS extractions (
                id TEXT PRIMARY KEY,
                journal TEXT,
                manuscript_id TEXT,
                extraction_type TEXT,
                timestamp TIMESTAMP,
                file_path TEXT,
                success BOOLEAN,
                data TEXT,
                checksum TEXT,
                file_type TEXT,
                file_size INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id TEXT PRIMARY KEY,
                url TEXT,
                filename TEXT,
                file_path TEXT,
                timestamp TIMESTAMP,
                file_size INTEGER,
                checksum TEXT,
                file_type TEXT,
                is_valid_pdf BOOLEAN
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def verify_pdf_file(self, file_path: Path) -> bool:
        """Verify if a file is a valid PDF."""
        if not file_path.exists():
            return False
        
        try:
            # Check file size
            if file_path.stat().st_size < 1024:  # Less than 1KB is suspicious
                return False
            
            # Check PDF header
            with open(file_path, 'rb') as f:
                header = f.read(4)
                if header != b'%PDF':
                    return False
            
            # Check if it's an HTML file disguised as PDF
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(1000)
                if any(tag in content.lower() for tag in ['<html>', '<head>', '<body>', '<!doctype']):
                    return False
            
            return True
            
        except Exception as e:
            print(f"⚠️  Error verifying PDF {file_path}: {e}")
            return False
    
    def get_file_type(self, file_path: Path) -> str:
        """Determine the actual file type."""
        if not file_path.exists():
            return "missing"
        
        try:
            with open(file_path, 'rb') as f:
                header = f.read(8)
                
            if header.startswith(b'%PDF'):
                return "pdf"
            elif header.startswith(b'<html') or header.startswith(b'<!DOC'):
                return "html"
            elif header.startswith(b'PK'):
                return "zip"
            else:
                return "unknown"
                
        except Exception:
            return "error"
    
    def cache_result(self, journal: str, manuscript_id: str, extraction_type: str, data: Any, file_path: str = None):
        """Cache extraction result with enhanced metadata."""
        cache_key = f"{journal}_{manuscript_id}_{extraction_type}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        file_type = None
        file_size = None
        
        if file_path and Path(file_path).exists():
            file_type = self.get_file_type(Path(file_path))
            file_size = Path(file_path).stat().st_size
        
        cursor.execute('''
            INSERT OR REPLACE INTO extractions 
            (id, journal, manuscript_id, extraction_type, timestamp, file_path, success, data, checksum, file_type, file_size)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            cache_key,
            journal,
            manuscript_id,
            extraction_type,
            datetime.now(),
            file_path,
            True,
            json.dumps(data),
            hashlib.md5(json.dumps(data).encode()).hexdigest(),
            file_type,
            file_size
        ))
        
        conn.commit()
        conn.close()
    
    def is_cached(self, journal: str, manuscript_id: str, extraction_type: str) -> bool:
        """Check if extraction result is cached."""
        cache_key = f"{journal}_{manuscript_id}_{extraction_type}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM extractions 
            WHERE id = ? AND success = 1 AND timestamp > ?
        ''', (cache_key, datetime.now() - timedelta(hours=24)))
        
        result = cursor.fetchone()[0] > 0
        conn.close()
        return result
    
    def get_cached_result(self, journal: str, manuscript_id: str, extraction_type: str) -> Optional[Dict]:
        """Get cached extraction result."""
        cache_key = f"{journal}_{manuscript_id}_{extraction_type}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data, timestamp FROM extractions 
            WHERE id = ? AND success = 1 
            ORDER BY timestamp DESC LIMIT 1
        ''', (cache_key,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'data': json.loads(result[0]),
                'timestamp': result[1]
            }
        return None


class UltraRobustRetryManager:
    """Ultra-robust retry manager with exponential backoff."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    def retry_with_backoff(self, func, *args, **kwargs) -> ExtractionResult:
        """Execute function with exponential backoff retry."""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                print(f"   🔄 Attempt {attempt + 1}/{self.max_retries}")
                result = func(*args, **kwargs)
                return ExtractionResult(
                    success=True,
                    data=result,
                    attempts=attempt + 1,
                    timestamp=datetime.now()
                )
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    print(f"   ❌ Attempt {attempt + 1} failed: {e}")
                    print(f"   ⏱️  Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
                else:
                    print(f"   💥 All attempts failed: {e}")
        
        return ExtractionResult(
            success=False,
            error=str(last_exception),
            attempts=self.max_retries,
            timestamp=datetime.now()
        )


class UltraRobustSIAMExtractor:
    """Ultra-robust SIAM extractor with comprehensive fixes."""
    
    def __init__(self, journal_name: str = "SICON"):
        self.journal_name = journal_name
        self.driver = None
        self.wait = None
        self.main_window = None
        
        # Journal URLs
        self.urls = {
            "SICON": "http://sicon.siam.org",
            "SIFIN": "http://sifin.siam.org"
        }
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_ultrarobust_{journal_name.lower()}_{timestamp}')
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.download_dir = self.output_dir / 'downloads'
        self.download_dir.mkdir(exist_ok=True)
        
        self.dirs = {
            'manuscripts': self.output_dir / 'manuscripts',
            'cover_letters': self.output_dir / 'cover_letters',
            'reports': self.output_dir / 'reports',
            'data': self.output_dir / 'data',
            'screenshots': self.output_dir / 'screenshots',
            'cache': self.output_dir / 'cache',
            'debug': self.output_dir / 'debug'
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(exist_ok=True)
        
        # Initialize components
        self.cache = UltraRobustCache(self.dirs['cache'])
        self.retry_manager = UltraRobustRetryManager(max_retries=5, base_delay=3.0)
        
        # State tracking
        self.authenticated = False
        self.debug_info = []
        self.current_session = {
            'start_time': datetime.now(),
            'manuscripts_processed': 0,
            'referees_extracted': 0,
            'files_downloaded': 0,
            'errors': []
        }
        
        print(f"📁 Ultra-robust output directory: {self.output_dir}")
        print(f"🎯 Fixed extraction for: {journal_name}")
        print(f"💾 Enhanced cache initialized: {self.dirs['cache']}")
    
    def debug_log(self, message: str, level: str = "INFO"):
        """Enhanced debugging with file logging."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {level}: {message}"
        
        print(formatted_msg)
        self.debug_info.append(formatted_msg)
        
        # Write to debug file
        debug_file = self.dirs['debug'] / f"debug_{self.journal_name.lower()}.log"
        with open(debug_file, 'a', encoding='utf-8') as f:
            f.write(formatted_msg + '\n')
    
    def setup_driver(self):
        """Setup Chrome WebDriver with ultra-robust configuration."""
        chrome_options = Options()
        
        # Enhanced download configuration
        prefs = {
            "download.default_directory": str(self.download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": False,
            "safebrowsing.disable_download_protection": True,
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Ultra-robust browser settings
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Extended timeouts
        chrome_options.add_argument('--page-load-strategy=eager')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Enhanced automation hiding
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
        
        # Enhanced download behavior
        self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": str(self.download_dir)
        })
        
        # Extended timeouts
        self.driver.set_page_load_timeout(90)
        self.driver.implicitly_wait(15)
        self.wait = WebDriverWait(self.driver, 45)
        
        self.debug_log("Ultra-robust Chrome WebDriver initialized", "SUCCESS")
    
    def save_screenshot(self, name: str, description: str = ""):
        """Save screenshot with enhanced error handling."""
        try:
            timestamp = datetime.now().strftime("%H%M%S")
            path = self.dirs['screenshots'] / f"{name}_{timestamp}.png"
            self.driver.save_screenshot(str(path))
            self.debug_log(f"Screenshot saved: {name}_{timestamp}.png {description}", "DEBUG")
        except Exception as e:
            self.debug_log(f"Could not save screenshot {name}: {e}", "ERROR")
    
    def robust_navigate_to_manuscripts(self) -> bool:
        """Navigate to manuscripts with ultra-robust detection."""
        self.debug_log(f"Navigating to {self.journal_name} manuscripts")
        
        def _navigate():
            if self.journal_name == "SICON":
                # SICON: Look for "4 AE" link with folder_id=1800
                self.debug_log("Looking for SICON 'All Pending Manuscripts' link")
                
                # Multiple strategies to find the link
                strategies = [
                    lambda: self.driver.find_element(By.XPATH, "//a[contains(@href, 'folder_id=1800')]"),
                    lambda: self.driver.find_element(By.XPATH, "//a[contains(text(), '4 AE')]"),
                    lambda: self.driver.find_element(By.XPATH, "//a[contains(text(), 'All Pending Manuscripts')]/following-sibling::a[1]"),
                    lambda: self.driver.find_element(By.XPATH, "//td[contains(text(), 'All Pending Manuscripts')]/following-sibling::td//a")
                ]
                
                for i, strategy in enumerate(strategies):
                    try:
                        self.debug_log(f"Trying SICON strategy {i+1}")
                        link = strategy()
                        self.driver.execute_script("arguments[0].click();", link)
                        time.sleep(5)
                        
                        page_text = self.driver.page_source
                        if 'All Pending Manuscripts' in page_text:
                            self.debug_log("Successfully reached SICON manuscripts table!", "SUCCESS")
                            self.save_screenshot("05_sicon_table", "SICON manuscripts table")
                            return True
                    except Exception as e:
                        self.debug_log(f"SICON strategy {i+1} failed: {e}", "WARNING")
                        continue
                
                raise Exception("Could not find SICON All Pending Manuscripts table")
            
            elif self.journal_name == "SIFIN":
                # SIFIN: Enhanced detection - manuscripts are directly on home page
                self.debug_log("Checking SIFIN home page for manuscripts")
                
                page_text = self.driver.page_source
                
                # FIXED: More flexible detection - just look for manuscript IDs
                manuscript_count = len(re.findall(r'#M\d{6}', page_text))
                
                if manuscript_count > 0:
                    self.debug_log(f"Successfully found {manuscript_count} SIFIN manuscripts on home page!", "SUCCESS")
                    self.save_screenshot("05_sifin_home", "SIFIN manuscripts on home")
                    return True
                else:
                    # Debug: Save page source for analysis
                    debug_file = self.dirs['debug'] / f"sifin_page_source_{datetime.now().strftime('%H%M%S')}.html"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(page_text)
                    self.debug_log(f"SIFIN page source saved to {debug_file}", "DEBUG")
                    
                    raise Exception("Could not find SIFIN manuscripts on home page")
        
        result = self.retry_manager.retry_with_backoff(_navigate)
        return result.success
    
    def ultra_robust_download_files(self, manuscript_id: str) -> bool:
        """Ultra-robust file download with comprehensive verification."""
        self.debug_log(f"Downloading files for {manuscript_id}")
        
        # Check cache first
        if self.cache.is_cached(self.journal_name, manuscript_id, "files"):
            cached = self.cache.get_cached_result(self.journal_name, manuscript_id, "files")
            if cached:
                self.debug_log(f"Found cached files for {manuscript_id}", "CACHE")
                return True
        
        def _download_files():
            # Multiple strategies to find manuscript links
            strategies = [
                lambda: self.driver.find_element(By.XPATH, f"//a[contains(text(), '{manuscript_id}')]"),
                lambda: self.driver.find_element(By.XPATH, f"//a[contains(@href, '{manuscript_id}')]"),
                lambda: self.driver.find_element(By.XPATH, f"//td[contains(text(), '{manuscript_id}')]//a"),
                lambda: self.driver.find_element(By.XPATH, f"//tr[contains(., '{manuscript_id}')]//a[1]")
            ]
            
            # Get initial file list
            initial_files = set(f.name for f in self.download_dir.glob("*"))
            self.debug_log(f"Initial files: {len(initial_files)}")
            
            # Try each strategy
            for i, strategy in enumerate(strategies):
                try:
                    self.debug_log(f"Trying download strategy {i+1} for {manuscript_id}")
                    link = strategy()
                    
                    # Enhanced click with multiple methods
                    try:
                        link.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", link)
                    
                    time.sleep(5)
                    
                    # Check for new files
                    current_files = set(f.name for f in self.download_dir.glob("*"))
                    new_files = current_files - initial_files
                    
                    if new_files:
                        self.debug_log(f"Downloaded: {', '.join(new_files)}")
                        
                        # Verify file types
                        valid_pdfs = []
                        invalid_files = []
                        
                        for filename in new_files:
                            file_path = self.download_dir / filename
                            
                            # Enhanced file verification
                            if self.cache.verify_pdf_file(file_path):
                                valid_pdfs.append(filename)
                                self.debug_log(f"Valid PDF: {filename}", "SUCCESS")
                            else:
                                invalid_files.append(filename)
                                file_type = self.cache.get_file_type(file_path)
                                self.debug_log(f"Invalid file: {filename} (type: {file_type})", "WARNING")
                                
                                # Move invalid files to debug directory
                                debug_path = self.dirs['debug'] / f"invalid_{filename}"
                                shutil.move(str(file_path), str(debug_path))
                                self.debug_log(f"Moved invalid file to: {debug_path}", "DEBUG")
                        
                        if valid_pdfs:
                            # Cache successful download
                            self.cache.cache_result(self.journal_name, manuscript_id, "files", {
                                'valid_pdfs': valid_pdfs,
                                'invalid_files': invalid_files,
                                'strategy_used': i+1
                            })
                            return True
                        else:
                            self.debug_log(f"No valid PDFs found for {manuscript_id}", "WARNING")
                    
                    # Wait longer for potential delayed downloads
                    time.sleep(10)
                    
                    # Check again
                    current_files = set(f.name for f in self.download_dir.glob("*"))
                    new_files = current_files - initial_files
                    
                    if new_files:
                        self.debug_log(f"Late download detected: {', '.join(new_files)}")
                        # Repeat verification process
                        for filename in new_files:
                            file_path = self.download_dir / filename
                            if self.cache.verify_pdf_file(file_path):
                                self.cache.cache_result(self.journal_name, manuscript_id, "files", {
                                    'valid_pdfs': [filename],
                                    'strategy_used': i+1
                                })
                                return True
                    
                except Exception as e:
                    self.debug_log(f"Download strategy {i+1} failed: {e}", "ERROR")
                    continue
            
            raise Exception(f"All download strategies failed for {manuscript_id}")
        
        result = self.retry_manager.retry_with_backoff(_download_files)
        if result.success:
            self.current_session['files_downloaded'] += 1
        return result.success
    
    def _extract_sifin_data(self) -> List[Dict]:
        """Extract SIFIN data with ultra-robust parsing."""
        manuscripts = []
        
        # Parse home page for manuscript links
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Enhanced manuscript detection
        manuscript_links = []
        
        # Look for manuscript patterns in various formats
        patterns = [
            r'#(M\d{6})\s*-\s*([^-]+)\s*-\s*([^(]+)(?:\s*\(([^)]+)\))?',
            r'#(M\d{6})[^-]*-[^-]*-([^(]+)(?:\s*\(([^)]+)\))?'
        ]
        
        page_text = self.driver.page_source
        
        for pattern in patterns:
            matches = re.findall(pattern, page_text)
            for match in matches:
                ms_id = match[0]
                if ms_id not in [m['manuscript_id'] for m in manuscripts]:
                    manuscripts.append({
                        'manuscript_id': ms_id,
                        'title': match[2].strip() if len(match) > 2 else "Unknown",
                        'status': match[1].strip() if len(match) > 1 else "Unknown",
                        'referees': [],
                        'files_downloaded': False
                    })
        
        self.debug_log(f"Found {len(manuscripts)} SIFIN manuscripts", "SUCCESS")
        
        # Process each manuscript
        for ms_data in manuscripts:
            ms_id = ms_data['manuscript_id']
            self.debug_log(f"Processing SIFIN manuscript: {ms_id}")
            
            # Try to download files
            ms_data['files_downloaded'] = self.ultra_robust_download_files(ms_id)
            
            self.current_session['manuscripts_processed'] += 1
        
        return manuscripts
    
    def run_extraction(self):
        """Run complete extraction with ultra-robust error handling."""
        try:
            self.setup_driver()
            
            # Load credentials
            from dotenv import load_dotenv
            load_dotenv()
            
            # Authenticate
            if not self.robust_authenticate():
                raise Exception("Authentication failed")
            
            # Navigate to manuscripts
            if not self.robust_navigate_to_manuscripts():
                raise Exception("Could not navigate to manuscripts")
            
            # Extract data
            if self.journal_name == "SIFIN":
                manuscripts = self._extract_sifin_data()
            else:
                manuscripts = self._extract_sicon_data()
            
            # Save results
            self.save_final_results(manuscripts)
            
            return manuscripts
            
        except Exception as e:
            self.debug_log(f"Extraction failed: {e}", "ERROR")
            raise
        finally:
            if self.driver:
                self.driver.quit()
    
    def robust_authenticate(self) -> bool:
        """Authenticate with ultra-robust error handling."""
        self.debug_log(f"Ultra-robust authentication with {self.journal_name}")
        
        def _authenticate():
            # Navigate to journal
            journal_url = self.urls[self.journal_name]
            self.driver.get(journal_url)
            time.sleep(8)
            self.main_window = self.driver.current_window_handle
            self.save_screenshot("01_journal_initial", "Initial journal page")
            
            # Enhanced authentication detection
            page_text = self.driver.page_source.lower()
            
            # Multiple authentication indicators
            auth_indicators = [
                'associate editor tasks',
                'all pending manuscripts',
                'editor dashboard',
                'manuscript management'
            ]
            
            is_authenticated = any(indicator in page_text for indicator in auth_indicators)
            
            if is_authenticated:
                self.debug_log("Already authenticated!", "SUCCESS")
                self.authenticated = True
                return True
            
            # Handle privacy notification first (if present)
            try:
                privacy_button = self.driver.find_element(By.XPATH, "//input[@value='Continue']")
                privacy_button.click()
                self.debug_log("Clicked privacy notification Continue button")
                time.sleep(3)
                self.save_screenshot("01b_after_privacy", "After privacy notification")
            except:
                self.debug_log("No privacy notification found (already handled)", "INFO")
            
            # Find and click ORCID link with enhanced strategies
            orcid_strategies = [
                lambda: self.driver.find_element(By.XPATH, "//a[contains(@href, 'orcid')]"),
                lambda: self.driver.find_element(By.XPATH, "//a[contains(text(), 'ORCID')]"),
                lambda: self.driver.find_element(By.XPATH, "//a[contains(@href, 'sso_site_redirect')]")
            ]
            
            orcid_link = None
            for i, strategy in enumerate(orcid_strategies):
                try:
                    orcid_link = strategy()
                    self.debug_log(f"Found ORCID link using strategy {i+1}")
                    break
                except:
                    continue
            
            if not orcid_link:
                raise Exception("No ORCID link found")
            
            # Enhanced click strategies for ORCID link
            self.debug_log("Clicking ORCID link with enhanced strategies")
            
            click_strategies = [
                lambda: orcid_link.click(),
                lambda: self.driver.execute_script("arguments[0].click();", orcid_link),
                lambda: self.driver.execute_script("arguments[0].scrollIntoView(); arguments[0].click();", orcid_link),
                lambda: ActionChains(self.driver).move_to_element(orcid_link).click().perform()
            ]
            
            for i, click_strategy in enumerate(click_strategies):
                try:
                    self.debug_log(f"Trying ORCID click strategy {i+1}")
                    click_strategy()
                    time.sleep(5)
                    break
                except Exception as e:
                    self.debug_log(f"ORCID click strategy {i+1} failed: {e}", "WARNING")
                    if i == len(click_strategies) - 1:
                        raise Exception("All ORCID click strategies failed")
            
            # Handle ORCID authentication
            current_url = self.driver.current_url
            if 'orcid.org' in current_url:
                self.debug_log("On ORCID login page")
                self.save_screenshot("02_orcid_login", "ORCID login page")
                
                # Handle ORCID cookie consent first
                try:
                    cookie_consent_strategies = [
                        lambda: self.driver.find_element(By.XPATH, "//button[contains(text(), 'Accept All Cookies')]").click(),
                        lambda: self.driver.find_element(By.XPATH, "//button[contains(text(), 'Accept all cookies')]").click(),
                        lambda: self.driver.find_element(By.XPATH, "//button[contains(@class, 'accept')]").click(),
                        lambda: self.driver.find_element(By.XPATH, "//div[contains(text(), 'Accept All Cookies')]").click(),
                        lambda: self.driver.find_element(By.XPATH, "//input[@value='Accept All Cookies']").click()
                    ]
                    
                    for i, strategy in enumerate(cookie_consent_strategies):
                        try:
                            self.debug_log(f"Trying ORCID cookie consent strategy {i+1}")
                            strategy()
                            self.debug_log("Successfully accepted ORCID cookies")
                            time.sleep(3)
                            self.save_screenshot("02b_after_orcid_cookies", "After ORCID cookie consent")
                            break
                        except Exception as e:
                            self.debug_log(f"ORCID cookie consent strategy {i+1} failed: {e}", "WARNING")
                            continue
                    
                except Exception as e:
                    self.debug_log(f"No ORCID cookie consent found or already handled: {e}", "INFO")
                
                # Fill credentials
                username = os.getenv('ORCID_USER')
                password = os.getenv('ORCID_PASS')
                
                if not username or not password:
                    raise Exception("ORCID credentials not found in environment")
                
                # Wait for login form to be available
                self.debug_log("Waiting for ORCID login form")
                
                # Enhanced login field detection
                username_field = None
                password_field = None
                
                username_strategies = [
                    lambda: self.driver.find_element(By.ID, "username"),
                    lambda: self.driver.find_element(By.ID, "userId"),
                    lambda: self.driver.find_element(By.NAME, "username"),
                    lambda: self.driver.find_element(By.NAME, "userId"),
                    lambda: self.driver.find_element(By.XPATH, "//input[@type='text']"),
                    lambda: self.driver.find_element(By.XPATH, "//input[@placeholder='Email or 16-digit ORCID iD']")
                ]
                
                for i, strategy in enumerate(username_strategies):
                    try:
                        self.debug_log(f"Trying username field strategy {i+1}")
                        username_field = strategy()
                        self.debug_log("Found username field")
                        break
                    except Exception as e:
                        self.debug_log(f"Username field strategy {i+1} failed: {e}", "WARNING")
                        continue
                
                if not username_field:
                    raise Exception("Could not find username field")
                
                password_strategies = [
                    lambda: self.driver.find_element(By.ID, "password"),
                    lambda: self.driver.find_element(By.NAME, "password"),
                    lambda: self.driver.find_element(By.XPATH, "//input[@type='password']")
                ]
                
                for i, strategy in enumerate(password_strategies):
                    try:
                        self.debug_log(f"Trying password field strategy {i+1}")
                        password_field = strategy()
                        self.debug_log("Found password field")
                        break
                    except Exception as e:
                        self.debug_log(f"Password field strategy {i+1} failed: {e}", "WARNING")
                        continue
                
                if not password_field:
                    raise Exception("Could not find password field")
                
                # Clear fields and enter credentials
                username_field.clear()
                password_field.clear()
                username_field.send_keys(username)
                password_field.send_keys(password)
                
                self.debug_log("Filled ORCID credentials")
                
                # Click sign in
                signin_strategies = [
                    lambda: self.driver.find_element(By.ID, "signin-button").click(),
                    lambda: self.driver.find_element(By.XPATH, "//button[contains(text(), 'Sign in')]").click(),
                    lambda: self.driver.find_element(By.XPATH, "//button[contains(text(), 'SIGN IN')]").click(),
                    lambda: self.driver.find_element(By.XPATH, "//input[@type='submit']").click(),
                    lambda: self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
                ]
                
                for i, strategy in enumerate(signin_strategies):
                    try:
                        self.debug_log(f"Trying signin strategy {i+1}")
                        strategy()
                        self.debug_log("Clicked signin button")
                        break
                    except Exception as e:
                        self.debug_log(f"Signin strategy {i+1} failed: {e}", "WARNING")
                        continue
                
                time.sleep(8)
                self.save_screenshot("03_after_orcid_login", "After ORCID login")
            
            # Handle privacy notification with multiple strategies
            self.debug_log("Handling privacy notification")
            
            privacy_strategies = [
                lambda: self.driver.find_element(By.XPATH, "//input[@value='Continue']").click(),
                lambda: self.driver.find_element(By.XPATH, "//button[text()='Continue']").click(),
                lambda: self.driver.find_element(By.XPATH, "//input[@type='submit'][@value='Continue']").click(),
                lambda: self.driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]").click()
            ]
            
            for i, strategy in enumerate(privacy_strategies):
                try:
                    self.debug_log(f"Trying privacy strategy {i+1}")
                    strategy()
                    time.sleep(5)
                    self.save_screenshot("04_after_privacy", "After privacy notification")
                    break
                except Exception as e:
                    self.debug_log(f"Privacy strategy {i+1} failed: {e}", "WARNING")
                    continue
            
            # Verify authentication
            time.sleep(5)
            page_text = self.driver.page_source.lower()
            is_authenticated = any(indicator in page_text for indicator in auth_indicators)
            
            if is_authenticated:
                self.debug_log("Authentication successful!", "SUCCESS")
                self.authenticated = True
                return True
            else:
                raise Exception("Authentication verification failed")
        
        result = self.retry_manager.retry_with_backoff(_authenticate)
        return result.success
    
    def save_final_results(self, manuscripts: List[Dict]):
        """Save final results with comprehensive metadata."""
        results = {
            'journal': self.journal_name,
            'extraction_time': datetime.now().isoformat(),
            'session_info': {
                'start_time': self.current_session['start_time'].isoformat(),
                'manuscripts_processed': self.current_session['manuscripts_processed'],
                'referees_extracted': self.current_session['referees_extracted'],
                'files_downloaded': self.current_session['files_downloaded'],
                'errors': self.current_session['errors']
            },
            'summary': {
                'total_manuscripts': len(manuscripts),
                'manuscripts_with_files': sum(1 for m in manuscripts if m.get('files_downloaded', False)),
                'valid_pdfs_downloaded': len([f for f in self.download_dir.glob("*.pdf") if self.cache.verify_pdf_file(f)]),
                'invalid_files_found': len(list(self.dirs['debug'].glob("invalid_*"))),
                'debug_info_entries': len(self.debug_info)
            },
            'manuscripts': manuscripts,
            'debug_info': self.debug_info[-50:]  # Last 50 debug entries
        }
        
        # Save JSON results
        json_path = self.dirs['data'] / f"{self.journal_name.lower()}_ultrarobust_results.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        self.debug_log(f"Final results saved to {json_path}", "SUCCESS")
        print(f"\n🎉 Ultra-robust extraction complete!")
        print(f"📊 Results: {len(manuscripts)} manuscripts processed")
        print(f"📁 Output directory: {self.output_dir}")


def main():
    """Main execution function."""
    import sys
    
    journal = sys.argv[1] if len(sys.argv) > 1 else "SIFIN"
    
    print(f"🚀 Starting ultra-robust extraction for {journal}")
    
    extractor = UltraRobustSIAMExtractor(journal)
    try:
        results = extractor.run_extraction()
        print(f"✅ Extraction completed successfully!")
        return results
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return None


if __name__ == "__main__":
    main()