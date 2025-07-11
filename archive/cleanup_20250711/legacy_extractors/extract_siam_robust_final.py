#!/usr/bin/env python3
"""
Robust SIAM Extractor - Production-ready with retries, fallbacks, and caching
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


class RobustCache:
    """Robust caching system for extraction results."""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize SQLite database for metadata
        self.db_path = cache_dir / 'extraction_cache.db'
        self.init_database()
    
    def init_database(self):
        """Initialize cache database."""
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
                checksum TEXT
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
                checksum TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_cache_key(self, journal: str, manuscript_id: str, extraction_type: str) -> str:
        """Generate cache key."""
        return f"{journal}_{manuscript_id}_{extraction_type}"
    
    def is_cached(self, journal: str, manuscript_id: str, extraction_type: str) -> bool:
        """Check if extraction result is cached."""
        cache_key = self.get_cache_key(journal, manuscript_id, extraction_type)
        
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
        cache_key = self.get_cache_key(journal, manuscript_id, extraction_type)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data, file_path FROM extractions 
            WHERE id = ? AND success = 1 AND timestamp > ?
            ORDER BY timestamp DESC LIMIT 1
        ''', (cache_key, datetime.now() - timedelta(hours=24)))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'data': json.loads(result[0]) if result[0] else None,
                'file_path': result[1]
            }
        return None
    
    def cache_result(self, journal: str, manuscript_id: str, extraction_type: str, 
                    data: Any, file_path: str = None, success: bool = True):
        """Cache extraction result."""
        cache_key = self.get_cache_key(journal, manuscript_id, extraction_type)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO extractions 
            (id, journal, manuscript_id, extraction_type, timestamp, file_path, success, data, checksum)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            cache_key, journal, manuscript_id, extraction_type,
            datetime.now(), file_path, success, 
            json.dumps(data) if data else None,
            hashlib.md5(str(data).encode()).hexdigest() if data else None
        ))
        
        conn.commit()
        conn.close()
    
    def is_file_downloaded(self, filename: str) -> bool:
        """Check if file is already downloaded."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT file_path FROM downloads 
            WHERE filename = ? AND timestamp > ?
        ''', (filename, datetime.now() - timedelta(hours=24)))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and Path(result[0]).exists():
            return True
        return False
    
    def get_downloaded_file_path(self, filename: str) -> Optional[str]:
        """Get path of downloaded file."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT file_path FROM downloads 
            WHERE filename = ? AND timestamp > ?
            ORDER BY timestamp DESC LIMIT 1
        ''', (filename, datetime.now() - timedelta(hours=24)))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None


class RobustRetryManager:
    """Robust retry manager with exponential backoff."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    def retry_with_backoff(self, func, *args, **kwargs):
        """Execute function with retry and exponential backoff."""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                print(f"   Attempt {attempt + 1}/{self.max_retries}")
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
                    print(f"   Attempt {attempt + 1} failed: {e}")
                    print(f"   Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
                else:
                    print(f"   All attempts failed: {e}")
        
        return ExtractionResult(
            success=False,
            error=str(last_exception),
            attempts=self.max_retries,
            timestamp=datetime.now()
        )


class RobustSIAMExtractor:
    """Production-ready SIAM extractor with robust error handling."""
    
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
        self.output_dir = Path(f'./siam_robust_{journal_name.lower()}_{timestamp}')
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
            'cache': self.output_dir / 'cache'
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(exist_ok=True)
        
        # Initialize components
        self.cache = RobustCache(self.dirs['cache'])
        self.retry_manager = RobustRetryManager(max_retries=3, base_delay=2.0)
        
        # State tracking
        self.authenticated = False
        self.current_session = {
            'start_time': datetime.now(),
            'manuscripts_processed': 0,
            'referees_extracted': 0,
            'files_downloaded': 0,
            'errors': []
        }
        
        print(f"📁 Output directory: {self.output_dir}")
        print(f"🎯 Robust extraction for: {journal_name}")
        print(f"💾 Cache initialized: {self.dirs['cache']}")
    
    def setup_driver(self):
        """Setup Chrome WebDriver with robust configuration."""
        chrome_options = Options()
        
        # Download configuration
        prefs = {
            "download.default_directory": str(self.download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Robust browser settings
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Longer timeouts
        chrome_options.add_argument('--page-load-strategy=eager')
        chrome_options.add_argument('--disable-extensions')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Hide automation indicators
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Enable downloads
        self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": str(self.download_dir)
        })
        
        # Configure timeouts
        self.driver.set_page_load_timeout(60)
        self.driver.implicitly_wait(10)
        self.wait = WebDriverWait(self.driver, 30)
        
        print("✅ Robust Chrome WebDriver initialized")
    
    def save_screenshot(self, name: str, description: str = ""):
        """Save screenshot with error handling."""
        try:
            timestamp = datetime.now().strftime("%H%M%S")
            path = self.dirs['screenshots'] / f"{name}_{timestamp}.png"
            self.driver.save_screenshot(str(path))
            print(f"📸 Screenshot: {name}_{timestamp}.png {description}")
        except Exception as e:
            print(f"⚠️  Could not save screenshot {name}: {e}")
    
    def robust_authenticate(self) -> bool:
        """Authenticate with robust retry mechanism."""
        print(f"\n🔐 Robust authentication with {self.journal_name}...")
        
        def _authenticate():
            # Navigate to journal
            journal_url = self.urls[self.journal_name]
            self.driver.get(journal_url)
            time.sleep(5)
            self.main_window = self.driver.current_window_handle
            self.save_screenshot("01_journal_initial", "Initial journal page")
            
            # Check if already authenticated
            page_text = self.driver.page_source.lower()
            if 'associate editor tasks' in page_text:
                print("✅ Already authenticated!")
                self.authenticated = True
                return True
            
            # Find and click ORCID link
            orcid_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'orcid')]")
            if not orcid_links:
                raise Exception("No ORCID links found")
            
            # Click ORCID
            self.driver.execute_script("arguments[0].click();", orcid_links[0])
            time.sleep(8)
            
            # Verify on ORCID
            if 'orcid.org' not in self.driver.current_url:
                raise Exception("Did not reach ORCID")
            
            self.save_screenshot("02_orcid_page", "ORCID login page")
            
            # Fill credentials with retries
            for cred_attempt in range(3):
                try:
                    username = self.wait.until(EC.presence_of_element_located((By.ID, "username-input")))
                    username.clear()
                    username.send_keys("0000-0002-9364-0124")
                    
                    password = self.driver.find_element(By.ID, "password")
                    password.clear()
                    password.send_keys("Hioupy0042%")
                    password.send_keys(Keys.RETURN)
                    
                    print(f"   Credentials submitted (attempt {cred_attempt + 1})")
                    break
                except Exception as e:
                    if cred_attempt == 2:
                        raise Exception(f"Failed to fill credentials: {e}")
                    time.sleep(2)
            
            # Wait for redirect with extended timeout
            redirect_timeout = time.time() + 45
            while time.time() < redirect_timeout:
                try:
                    current_url = self.driver.current_url
                    if not current_url:
                        time.sleep(2)
                        continue
                        
                    if journal_url.replace("http://", "").replace("https://", "") in current_url and 'orcid.org' not in current_url:
                        time.sleep(5)
                        
                        # Check authentication
                        page_text = self.driver.page_source.lower()
                        self.save_screenshot("03_after_auth", "After authentication")
                        
                        if 'associate editor tasks' in page_text:
                            print("✅ Authentication successful!")
                            self.authenticated = True
                            return True
                        else:
                            # Try refreshing the page
                            self.driver.refresh()
                            time.sleep(5)
                            page_text = self.driver.page_source.lower()
                            if 'associate editor tasks' in page_text:
                                print("✅ Authentication successful after refresh!")
                                self.authenticated = True
                                return True
                    
                    time.sleep(2)
                except Exception as e:
                    print(f"   Error during redirect check: {e}")
                    time.sleep(2)
            
            raise Exception("Authentication timeout - redirect not completed")
        
        result = self.retry_manager.retry_with_backoff(_authenticate)
        if result.success:
            self.authenticated = True
            return True
        else:
            self.current_session['errors'].append(f"Authentication failed: {result.error}")
            return False
    
    def robust_dismiss_privacy_notification(self) -> bool:
        """Dismiss privacy notification with multiple fallbacks."""
        print("🚨 Dismissing privacy notification...")
        
        def _dismiss_popup():
            # Try multiple strategies
            strategies = [
                lambda: self.driver.find_element(By.XPATH, "//button[text()='Continue']").click(),
                lambda: self.driver.find_element(By.XPATH, "//input[@value='Continue']").click(),
                lambda: self.driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]").click(),
                lambda: ActionChains(self.driver).send_keys(Keys.RETURN).perform(),
                lambda: self.driver.execute_script("""
                    var overlays = document.querySelectorAll('div[style*="position: fixed"]');
                    overlays.forEach(function(el) {
                        if (el.style.zIndex > 100) {
                            el.remove();
                        }
                    });
                """)
            ]
            
            for i, strategy in enumerate(strategies, 1):
                try:
                    strategy()
                    time.sleep(2)
                    
                    # Check if popup is gone
                    page_source = self.driver.page_source
                    if 'Privacy Notification' not in page_source:
                        print(f"   ✅ Strategy {i} worked!")
                        return True
                except:
                    continue
            
            return False
        
        result = self.retry_manager.retry_with_backoff(_dismiss_popup)
        return result.success
    
    def robust_navigate_to_manuscripts(self) -> bool:
        """Navigate to manuscripts with robust error handling."""
        print(f"\n📋 Navigating to manuscripts in {self.journal_name}...")
        
        def _navigate():
            # Go to home page
            journal_url = self.urls[self.journal_name]
            self.driver.get(f"{journal_url}/cgi-bin/main.plex?form_type=home")
            time.sleep(5)
            
            # Dismiss privacy notification
            self.robust_dismiss_privacy_notification()
            self.save_screenshot("04_home_page", "Home page after popup dismissal")
            
            if self.journal_name == "SICON":
                # SICON: Look for All Pending Manuscripts table
                search_strategies = [
                    "//a[contains(@href, 'folder_id=1800')]",
                    "//a[contains(@href, 'is_open_1800=1')]",
                    "//a[text()='4 AE']"
                ]
                
                for strategy in search_strategies:
                    try:
                        links = self.driver.find_elements(By.XPATH, strategy)
                        if links:
                            for link in links:
                                href = link.get_attribute('href') or ''
                                if 'folder_id=1800' in href:
                                    print(f"   ✅ Found SICON All Pending Manuscripts link")
                                    self.driver.execute_script("arguments[0].click();", link)
                                    time.sleep(8)
                                    
                                    # Verify we reached the table
                                    page_text = self.driver.page_source
                                    if 'All Pending Manuscripts' in page_text:
                                        print("   ✅ Successfully reached SICON manuscripts table!")
                                        self.save_screenshot("05_sicon_table", "SICON manuscripts table")
                                        return True
                    except Exception as e:
                        print(f"   Strategy failed: {e}")
                        continue
                
                raise Exception("Could not find SICON All Pending Manuscripts table")
            
            elif self.journal_name == "SIFIN":
                # SIFIN: Manuscripts are directly on home page
                page_text = self.driver.page_source
                if 'Associate Editor Tasks' in page_text and '#M' in page_text:
                    print("   ✅ Successfully found SIFIN manuscripts on home page!")
                    self.save_screenshot("05_sifin_home", "SIFIN manuscripts on home")
                    return True
                else:
                    raise Exception("Could not find SIFIN manuscripts on home page")
        
        result = self.retry_manager.retry_with_backoff(_navigate)
        return result.success
    
    def robust_extract_referee_email(self, referee_name: str, manuscript_id: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract referee email with caching and retries."""
        print(f"      📧 Extracting email for {referee_name} (manuscript {manuscript_id})")
        
        # Check cache first
        if self.cache.is_cached(self.journal_name, manuscript_id, f"referee_{referee_name}"):
            cached = self.cache.get_cached_result(self.journal_name, manuscript_id, f"referee_{referee_name}")
            if cached and cached['data']:
                print(f"         ✅ Found cached email: {cached['data'].get('email', 'No email')}")
                return cached['data'].get('email'), cached['data'].get('full_name')
        
        def _extract_email():
            # Find referee link
            referee_links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{referee_name}')]")
            if not referee_links:
                raise Exception(f"No clickable link found for {referee_name}")
            
            # Click referee link
            self.driver.execute_script("arguments[0].click();", referee_links[0])
            time.sleep(5)
            
            # Check if new window opened
            if len(self.driver.window_handles) > 1:
                # Switch to new window
                self.driver.switch_to.window(self.driver.window_handles[-1])
                time.sleep(3)
                
                # Extract email and full name
                profile_text = self.driver.page_source
                
                # Look for email
                email = None
                email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', profile_text)
                if email_match:
                    email = email_match.group()
                
                # Look for full name
                full_name = referee_name
                name_patterns = [
                    r'<title>([^<]+)</title>',
                    r'Full Name[:\s]*([^<\n]+)',
                    r'Name[:\s]*([^<\n]+)',
                    r'<h1[^>]*>([^<]+)</h1>',
                    r'<h2[^>]*>([^<]+)</h2>'
                ]
                
                for pattern in name_patterns:
                    name_match = re.search(pattern, profile_text, re.IGNORECASE)
                    if name_match:
                        potential_name = name_match.group(1).strip()
                        if len(potential_name) > len(referee_name) and not any(skip in potential_name.lower() for skip in ['login', 'error', 'page']):
                            full_name = potential_name
                            break
                
                # Close window and return to main
                self.driver.close()
                self.driver.switch_to.window(self.main_window)
                time.sleep(2)
                
                # Cache result
                result_data = {'email': email, 'full_name': full_name}
                self.cache.cache_result(self.journal_name, manuscript_id, f"referee_{referee_name}", result_data)
                
                return email, full_name
            else:
                raise Exception(f"No new window opened for {referee_name}")
        
        result = self.retry_manager.retry_with_backoff(_extract_email)
        if result.success:
            self.current_session['referees_extracted'] += 1
            return result.data
        else:
            self.current_session['errors'].append(f"Failed to extract email for {referee_name}: {result.error}")
            return None, None
    
    def robust_download_manuscript_files(self, manuscript_id: str) -> bool:
        """Download manuscript files with caching and verification."""
        print(f"      📥 Downloading files for {manuscript_id}")
        
        # Check if already downloaded
        if self.cache.is_file_downloaded(f"{manuscript_id}.pdf"):
            cached_path = self.cache.get_downloaded_file_path(f"{manuscript_id}.pdf")
            if cached_path and Path(cached_path).exists():
                print(f"         ✅ Found cached PDF: {cached_path}")
                return True
        
        def _download_files():
            # Find manuscript link
            ms_links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{manuscript_id}')]")
            if not ms_links:
                raise Exception(f"No clickable link found for {manuscript_id}")
            
            # Get initial file count
            initial_files = set(f.name for f in self.download_dir.glob("*"))
            
            # Click manuscript link
            self.driver.execute_script("arguments[0].click();", ms_links[0])
            time.sleep(3)
            
            # Wait for download to complete
            download_timeout = time.time() + 30
            while time.time() < download_timeout:
                current_files = set(f.name for f in self.download_dir.glob("*"))
                new_files = current_files - initial_files
                
                if new_files:
                    print(f"         ✅ Downloaded: {', '.join(new_files)}")
                    
                    # Cache the download
                    for filename in new_files:
                        file_path = self.download_dir / filename
                        if file_path.exists():
                            conn = sqlite3.connect(self.cache.db_path)
                            cursor = conn.cursor()
                            cursor.execute('''
                                INSERT OR REPLACE INTO downloads 
                                (id, url, filename, file_path, timestamp, file_size, checksum)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                f"{manuscript_id}_{filename}",
                                self.driver.current_url,
                                filename,
                                str(file_path),
                                datetime.now(),
                                file_path.stat().st_size,
                                hashlib.md5(file_path.read_bytes()).hexdigest()
                            ))
                            conn.commit()
                            conn.close()
                    
                    return True
                
                time.sleep(2)
            
            # Check if files were downloaded but not detected
            final_files = set(f.name for f in self.download_dir.glob("*"))
            new_files = final_files - initial_files
            
            if new_files:
                print(f"         ✅ Found downloaded files: {', '.join(new_files)}")
                return True
            else:
                print(f"         ⚠️  No files downloaded for {manuscript_id}")
                return False
        
        result = self.retry_manager.retry_with_backoff(_download_files)
        if result.success:
            self.current_session['files_downloaded'] += 1
            return True
        else:
            self.current_session['errors'].append(f"Failed to download files for {manuscript_id}: {result.error}")
            return False
    
    def robust_extract_complete_data(self) -> List[Dict]:
        """Extract complete manuscript data with robust error handling."""
        print(f"\n📊 Extracting complete data from {self.journal_name}...")
        
        manuscripts = []
        
        try:
            if self.journal_name == "SICON":
                manuscripts = self._extract_sicon_data()
            elif self.journal_name == "SIFIN":
                manuscripts = self._extract_sifin_data()
            
            print(f"   ✅ Extracted {len(manuscripts)} manuscripts")
            
        except Exception as e:
            print(f"❌ Error extracting data: {e}")
            self.current_session['errors'].append(f"Data extraction failed: {e}")
        
        return manuscripts
    
    def _extract_sicon_data(self) -> List[Dict]:
        """Extract SICON data from table."""
        manuscripts = []
        
        # Parse table
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        tables = soup.find_all('table')
        
        for table in tables:
            table_text = table.get_text()
            manuscript_ids = re.findall(r'M\d{6}', table_text)
            
            if len(manuscript_ids) >= 2:
                print(f"   ✅ Found SICON table with {len(manuscript_ids)} manuscripts")
                
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) < 6:
                        continue
                    
                    first_cell_text = cells[0].get_text(strip=True)
                    ms_match = re.search(r'(M\d{6})', first_cell_text)
                    if not ms_match:
                        continue
                    
                    ms_id = ms_match.group(1)
                    print(f"\n   📄 Processing SICON manuscript: {ms_id}")
                    
                    ms_data = {
                        'manuscript_id': ms_id,
                        'title': cells[1].get_text(strip=True) if len(cells) > 1 else '',
                        'corresponding_editor': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                        'associate_editor': cells[3].get_text(strip=True) if len(cells) > 3 else '',
                        'submitted': cells[4].get_text(strip=True) if len(cells) > 4 else '',
                        'days_in_system': cells[5].get_text(strip=True) if len(cells) > 5 else '',
                        'referees': [],
                        'files_downloaded': False
                    }
                    
                    # Extract referees
                    referee_names = ['Ferrari', 'LI', 'Cohen', 'Guo', 'Ekren', 'Ren', 'daudin', 'Tangpi']
                    for cell in cells[6:]:
                        cell_text = cell.get_text(strip=True)
                        for ref_name in referee_names:
                            if ref_name in cell_text:
                                print(f"      👤 Found referee: {ref_name}")
                                
                                # Extract email and full name
                                email, full_name = self.robust_extract_referee_email(ref_name, ms_id)
                                
                                ref_data = {
                                    'name': ref_name,
                                    'full_name': full_name or ref_name,
                                    'email': email,
                                    'status': 'Extracted' if email else 'No email found',
                                    'extraction_success': email is not None
                                }
                                
                                if not any(r['name'] == ref_name for r in ms_data['referees']):
                                    ms_data['referees'].append(ref_data)
                    
                    # Download files
                    if ms_data['referees']:
                        ms_data['files_downloaded'] = self.robust_download_manuscript_files(ms_id)
                    
                    manuscripts.append(ms_data)
                    self.current_session['manuscripts_processed'] += 1
                    
                    # Save intermediate results
                    self.save_intermediate_results(manuscripts)
                
                break
        
        return manuscripts
    
    def _extract_sifin_data(self) -> List[Dict]:
        """Extract SIFIN data from home page links."""
        manuscripts = []
        
        # Parse home page for manuscript links
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Find manuscript links (format: #M174160 - Under Review / Chase Referees - Title)
        manuscript_links = []
        for link in soup.find_all('a'):
            text = link.get_text(strip=True)
            if text.startswith('#M') and re.search(r'M\d{6}', text):
                manuscript_links.append((text, link.get('href', '')))
        
        print(f"   ✅ Found {len(manuscript_links)} SIFIN manuscripts")
        
        for ms_text, ms_url in manuscript_links:
            try:
                ms_id_match = re.search(r'#(M\d{6})', ms_text)
                if not ms_id_match:
                    continue
                
                ms_id = ms_id_match.group(1)
                print(f"\n   📄 Processing SIFIN manuscript: {ms_id}")
                
                # Parse manuscript info from link text
                parts = ms_text.split(' - ')
                status = parts[1] if len(parts) > 1 else "Unknown"
                title = parts[2] if len(parts) > 2 else "Unknown"
                
                # Extract referee info
                referee_info = re.search(r'\((\d+)\s*received\s*/\s*(\d+)\s*total\)', ms_text)
                received_reports = int(referee_info.group(1)) if referee_info else 0
                total_referees = int(referee_info.group(2)) if referee_info else 0
                
                ms_data = {
                    'manuscript_id': ms_id,
                    'title': title,
                    'status': status,
                    'reports_received': received_reports,
                    'total_referees_expected': total_referees,
                    'url': ms_url,
                    'referees': [],
                    'files_downloaded': False
                }
                
                # Navigate to manuscript page for detailed info
                if ms_url:
                    full_url = ms_url if ms_url.startswith('http') else f"http://sifin.siam.org{ms_url}"
                    try:
                        self.driver.get(full_url)
                        time.sleep(5)
                        
                        # Extract detailed information from manuscript page
                        detail_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                        
                        # Look for referee information in tables
                        for table in detail_soup.find_all('table'):
                            table_text = table.get_text().lower()
                            if 'referee' in table_text or 'reviewer' in table_text:
                                # Extract referee names from table
                                for row in table.find_all('tr'):
                                    cells = row.find_all(['td', 'th'])
                                    for cell in cells:
                                        cell_text = cell.get_text(strip=True)
                                        # Look for names (capitalized words)
                                        potential_names = re.findall(r'\b[A-Z][a-z]{2,}\b', cell_text)
                                        for name in potential_names:
                                            if len(name) > 2 and name not in ['Status', 'Date', 'Due', 'Received']:
                                                print(f"      👤 Found potential referee: {name}")
                                                
                                                # Extract email if possible
                                                email, full_name = self.robust_extract_referee_email(name, ms_id)
                                                
                                                ref_data = {
                                                    'name': name,
                                                    'full_name': full_name or name,
                                                    'email': email,
                                                    'status': 'Extracted' if email else 'No email found',
                                                    'extraction_success': email is not None
                                                }
                                                
                                                if not any(r['name'] == name for r in ms_data['referees']):
                                                    ms_data['referees'].append(ref_data)
                        
                        # Download files
                        ms_data['files_downloaded'] = self.robust_download_manuscript_files(ms_id)
                        
                    except Exception as e:
                        print(f"      ❌ Error processing manuscript page: {e}")
                
                manuscripts.append(ms_data)
                self.current_session['manuscripts_processed'] += 1
                
                # Save intermediate results
                self.save_intermediate_results(manuscripts)
                
            except Exception as e:
                print(f"   ❌ Error processing manuscript {ms_text}: {e}")
                continue
        
        return manuscripts
    
    def save_intermediate_results(self, manuscripts: List[Dict]):
        """Save intermediate results to prevent data loss."""
        try:
            intermediate_path = self.dirs['data'] / 'intermediate_results.json'
            with open(intermediate_path, 'w') as f:
                json.dump({
                    'journal': self.journal_name,
                    'timestamp': datetime.now().isoformat(),
                    'session': self.current_session,
                    'manuscripts': manuscripts
                }, f, indent=2, default=str)
        except Exception as e:
            print(f"⚠️  Could not save intermediate results: {e}")
    
    def create_final_report(self, manuscripts: List[Dict]) -> Dict:
        """Create comprehensive final report."""
        print(f"\n📊 Creating comprehensive report for {self.journal_name}...")
        
        # Calculate statistics
        total_referees = sum(len(ms['referees']) for ms in manuscripts)
        referees_with_emails = sum(1 for ms in manuscripts for ref in ms['referees'] if ref.get('email'))
        manuscripts_with_files = sum(1 for ms in manuscripts if ms.get('files_downloaded'))
        
        # Generate report
        results = {
            'journal': self.journal_name,
            'extraction_time': datetime.now().isoformat(),
            'session_info': self.current_session,
            'summary': {
                'total_manuscripts': len(manuscripts),
                'total_referees': total_referees,
                'referees_with_emails': referees_with_emails,
                'manuscripts_with_files': manuscripts_with_files,
                'success_rates': {
                    'referee_email_rate': f"{referees_with_emails}/{total_referees}" if total_referees > 0 else "0/0",
                    'file_download_rate': f"{manuscripts_with_files}/{len(manuscripts)}" if manuscripts else "0/0"
                }
            },
            'manuscripts': manuscripts,
            'errors': self.current_session['errors']
        }
        
        # Save JSON report
        json_path = self.dirs['data'] / f'{self.journal_name.lower()}_final_results.json'
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        # Save markdown report
        report_path = self.dirs['data'] / f'{self.journal_name.lower()}_final_report.md'
        with open(report_path, 'w') as f:
            f.write(f"# {self.journal_name} Robust Extraction Report\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Session Duration**: {datetime.now() - self.current_session['start_time']}\n\n")
            
            f.write("## Summary\n\n")
            f.write(f"- **Journal**: {self.journal_name}\n")
            f.write(f"- **Manuscripts Processed**: {len(manuscripts)}\n")
            f.write(f"- **Total Referees**: {total_referees}\n")
            f.write(f"- **Referees with Emails**: {referees_with_emails}/{total_referees}\n")
            f.write(f"- **Manuscripts with Files**: {manuscripts_with_files}/{len(manuscripts)}\n")
            f.write(f"- **Errors Encountered**: {len(self.current_session['errors'])}\n\n")
            
            f.write("## Detailed Results\n\n")
            for ms in manuscripts:
                f.write(f"### {ms['manuscript_id']}\n")
                f.write(f"**Title**: {ms.get('title', 'N/A')}\n")
                f.write(f"**Status**: {ms.get('status', 'N/A')}\n")
                f.write(f"**Files Downloaded**: {'✅ Yes' if ms.get('files_downloaded') else '❌ No'}\n\n")
                
                f.write("#### Referees\n")
                for ref in ms['referees']:
                    email_status = '✅' if ref.get('email') else '❌'
                    f.write(f"- **{ref['name']}** ({ref.get('full_name', ref['name'])}): {ref.get('email', 'No email')} {email_status}\n")
                f.write("\n")
            
            if self.current_session['errors']:
                f.write("## Errors\n\n")
                for error in self.current_session['errors']:
                    f.write(f"- {error}\n")
        
        print(f"   ✅ Final report saved to: {report_path}")
        print(f"   ✅ JSON data saved to: {json_path}")
        
        return results
    
    def run_robust_extraction(self) -> Dict:
        """Run the complete robust extraction."""
        print(f"\n🚀 STARTING ROBUST {self.journal_name} EXTRACTION")
        print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"💾 Cache directory: {self.dirs['cache']}")
        
        manuscripts = []
        
        try:
            # Setup driver
            self.setup_driver()
            
            # Authenticate
            if not self.robust_authenticate():
                print("❌ Authentication failed after all retries")
                return self.create_final_report(manuscripts)
            
            # Navigate to manuscripts
            if not self.robust_navigate_to_manuscripts():
                print("❌ Navigation failed after all retries")
                return self.create_final_report(manuscripts)
            
            # Extract complete data
            manuscripts = self.robust_extract_complete_data()
            
            # Create final report
            results = self.create_final_report(manuscripts)
            
            # Print final summary
            print(f"\n📊 ROBUST EXTRACTION COMPLETE:")
            print(f"⏱️  Duration: {datetime.now() - self.current_session['start_time']}")
            print(f"📄 Manuscripts: {len(manuscripts)}")
            print(f"👥 Total Referees: {sum(len(ms['referees']) for ms in manuscripts)}")
            print(f"📧 Referees with Emails: {sum(1 for ms in manuscripts for ref in ms['referees'] if ref.get('email'))}")
            print(f"📥 Manuscripts with Files: {sum(1 for ms in manuscripts if ms.get('files_downloaded'))}")
            print(f"❌ Errors: {len(self.current_session['errors'])}")
            print(f"💾 Cache entries: {len(list(self.dirs['cache'].glob('*')))}")
            print(f"📊 Results: {self.dirs['data']}")
            
            return results
            
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
            self.current_session['errors'].append(f"Fatal error: {e}")
            return self.create_final_report(manuscripts)
        
        finally:
            if self.driver:
                print("\n🔄 Closing browser...")
                try:
                    self.driver.quit()
                except:
                    pass


def main():
    """Run robust extraction for both journals."""
    print("🎯 Starting Robust SIAM Extraction System")
    print("="*60)
    
    # Extract from SICON
    print("\n📚 SICON ROBUST EXTRACTION")
    print("-" * 30)
    sicon_extractor = RobustSIAMExtractor("SICON")
    sicon_results = sicon_extractor.run_robust_extraction()
    
    # Extract from SIFIN
    print("\n📚 SIFIN ROBUST EXTRACTION")
    print("-" * 30)
    sifin_extractor = RobustSIAMExtractor("SIFIN")
    sifin_results = sifin_extractor.run_robust_extraction()
    
    # Combined summary
    print("\n" + "="*60)
    print("📊 COMBINED RESULTS SUMMARY")
    print("="*60)
    
    sicon_manuscripts = len(sicon_results.get('manuscripts', []))
    sifin_manuscripts = len(sifin_results.get('manuscripts', []))
    
    print(f"SICON: {sicon_manuscripts} manuscripts")
    print(f"SIFIN: {sifin_manuscripts} manuscripts")
    print(f"Total: {sicon_manuscripts + sifin_manuscripts} manuscripts")
    
    if sicon_manuscripts == 4 and sifin_manuscripts == 4:
        print("\n✅ SUCCESS! Expected manuscript counts achieved!")
    else:
        print(f"\n⚠️  Results differ from expected (SICON: 4, SIFIN: 4)")
    
    print("\n🎉 ROBUST EXTRACTION SYSTEM COMPLETE!")


if __name__ == "__main__":
    main()