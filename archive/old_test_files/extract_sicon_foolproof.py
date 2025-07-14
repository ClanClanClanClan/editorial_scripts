#!/usr/bin/env python3
"""
Foolproof SICON Extractor - Complete implementation with working PDF downloads and referee status tracking
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
import requests


@dataclass
class RefereeInfo:
    """Complete referee information with status tracking."""
    name: str
    full_name: str = None
    email: str = None
    status: str = "Unknown"  # Accepted, Declined, Pending, Submitted
    invited_date: str = None
    response_date: str = None
    due_date: str = None
    days_to_respond: int = None
    report_submitted: bool = False
    extraction_success: bool = False


class FoolproofSICONExtractor:
    """Foolproof SICON extractor with complete PDF download and referee tracking."""
    
    def __init__(self):
        self.journal_name = "SICON"
        self.driver = None
        self.wait = None
        self.main_window = None
        self.session = requests.Session()  # For PDF downloads
        
        # Journal URL
        self.base_url = "http://sicon.siam.org"
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./sicon_foolproof_{timestamp}')
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.dirs = {
            'manuscripts': self.output_dir / 'manuscripts',
            'cover_letters': self.output_dir / 'cover_letters',
            'reports': self.output_dir / 'reports',
            'data': self.output_dir / 'data',
            'screenshots': self.output_dir / 'screenshots',
            'debug': self.output_dir / 'debug',
            'temp': self.output_dir / 'temp'
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(exist_ok=True)
        
        # State tracking
        self.authenticated = False
        self.cookies = {}
        self.current_session = {
            'start_time': datetime.now(),
            'manuscripts_processed': 0,
            'referees_extracted': 0,
            'pdfs_downloaded': 0,
            'errors': []
        }
        
        print(f"📁 Output directory: {self.output_dir}")
        print(f"🎯 Foolproof extraction for: {self.journal_name}")
    
    def setup_driver(self):
        """Setup Chrome WebDriver with optimized download configuration."""
        chrome_options = Options()
        
        # Download configuration - use temp directory first
        prefs = {
            "download.default_directory": str(self.dirs['temp']),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": False,
            "safebrowsing.disable_download_protection": True,
            "profile.default_content_setting_values.automatic_downloads": 1
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Browser settings
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Hide automation indicators
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Enable downloads in temp directory
        self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": str(self.dirs['temp'])
        })
        
        # Configure timeouts
        self.driver.set_page_load_timeout(60)
        self.driver.implicitly_wait(10)
        self.wait = WebDriverWait(self.driver, 30)
        
        print("✅ Chrome WebDriver initialized")
    
    def save_screenshot(self, name: str, description: str = ""):
        """Save screenshot for debugging."""
        try:
            timestamp = datetime.now().strftime("%H%M%S")
            path = self.dirs['screenshots'] / f"{name}_{timestamp}.png"
            self.driver.save_screenshot(str(path))
            print(f"📸 Screenshot: {name} - {description}")
        except Exception as e:
            print(f"⚠️  Could not save screenshot {name}: {e}")
    
    def authenticate(self) -> bool:
        """Authenticate with SICON."""
        print(f"\n🔐 Authenticating with {self.journal_name}...")
        
        try:
            # Navigate to journal
            self.driver.get(self.base_url)
            time.sleep(5)
            self.main_window = self.driver.current_window_handle
            self.save_screenshot("01_initial", "Initial page")
            
            # Check if already authenticated
            page_text = self.driver.page_source.lower()
            if 'associate editor tasks' in page_text:
                print("✅ Already authenticated!")
                self.authenticated = True
                self.sync_cookies()
                return True
            
            # Handle privacy notification first
            try:
                privacy_button = self.driver.find_element(By.XPATH, "//input[@value='Continue']")
                privacy_button.click()
                print("✅ Clicked privacy notification")
                time.sleep(3)
            except:
                print("ℹ️  No privacy notification found")
            
            # Click ORCID link
            orcid_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'orcid')]")
            self.driver.execute_script("arguments[0].click();", orcid_link)
            time.sleep(5)
            
            # Handle ORCID authentication
            current_url = self.driver.current_url
            if 'orcid.org' in current_url:
                print("📝 On ORCID login page")
                
                # Handle cookie consent
                try:
                    accept_cookies = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Accept All Cookies')]")
                    accept_cookies.click()
                    print("✅ Accepted ORCID cookies")
                    time.sleep(2)
                except:
                    pass
                
                # Fill credentials
                username = os.getenv('ORCID_USER')
                password = os.getenv('ORCID_PASS')
                
                if not username or not password:
                    raise Exception("ORCID credentials not found")
                
                # Enter credentials - wait for fields to be visible
                try:
                    # Wait for the email field to be present
                    username_field = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Email or 16-digit ORCID iD']"))
                    )
                    print("✅ Found ORCID username field")
                    
                    password_field = self.driver.find_element(By.XPATH, "//input[@placeholder='Your ORCID password']")
                    print("✅ Found ORCID password field")
                    
                    # Clear and fill fields
                    username_field.clear()
                    username_field.send_keys(username)
                    password_field.clear()
                    password_field.send_keys(password)
                    
                    # Click sign in button - try multiple strategies
                    signin_strategies = [
                        lambda: self.driver.find_element(By.XPATH, "//button[text()='Sign in to ORCID']"),
                        lambda: self.driver.find_element(By.CSS_SELECTOR, "button.btn-sign-in"),
                        lambda: self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']"),
                        lambda: self.driver.find_element(By.XPATH, "//button[contains(@class, 'primary')]")
                    ]
                    
                    for strategy in signin_strategies:
                        try:
                            signin_button = strategy()
                            signin_button.click()
                            print("✅ Clicked sign in button")
                            break
                        except:
                            continue
                    
                    time.sleep(8)
                    
                except Exception as e:
                    print(f"❌ Error with ORCID login: {e}")
                    self.save_screenshot("orcid_error", "ORCID login error")
                    raise
            
            # Handle privacy notification after ORCID
            try:
                privacy_button = self.driver.find_element(By.XPATH, "//input[@value='Continue']")
                privacy_button.click()
                print("✅ Clicked post-auth privacy notification")
                time.sleep(3)
            except:
                pass
            
            # Verify authentication
            page_text = self.driver.page_source.lower()
            if 'associate editor tasks' in page_text:
                print("✅ Authentication successful!")
                self.authenticated = True
                self.sync_cookies()
                return True
            else:
                raise Exception("Authentication verification failed")
                
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            self.save_screenshot("auth_error", f"Authentication error: {e}")
            return False
    
    def sync_cookies(self):
        """Sync cookies between Selenium and requests session."""
        selenium_cookies = self.driver.get_cookies()
        for cookie in selenium_cookies:
            self.session.cookies.set(cookie['name'], cookie['value'])
        self.cookies = {c['name']: c['value'] for c in selenium_cookies}
        print("🔄 Cookies synced between Selenium and requests")
    
    def navigate_to_manuscripts(self) -> bool:
        """Navigate to All Pending Manuscripts table."""
        print("\n📋 Navigating to manuscripts...")
        
        try:
            # Look for "4 AE" link (folder_id=1800)
            link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'folder_id=1800')]")
            self.driver.execute_script("arguments[0].click();", link)
            time.sleep(5)
            
            page_text = self.driver.page_source
            if 'All Pending Manuscripts' in page_text:
                print("✅ Successfully reached manuscripts table!")
                self.save_screenshot("manuscripts_table", "All Pending Manuscripts")
                return True
            else:
                raise Exception("Could not verify manuscripts table")
                
        except Exception as e:
            print(f"❌ Navigation failed: {e}")
            return False
    
    def extract_referee_details(self, referee_name: str, manuscript_id: str) -> RefereeInfo:
        """Extract complete referee details including status."""
        print(f"      📧 Extracting details for {referee_name}")
        
        referee = RefereeInfo(name=referee_name)
        
        try:
            # Find and click referee link
            referee_link = self.driver.find_element(By.XPATH, f"//a[contains(text(), '{referee_name}')]")
            self.driver.execute_script("arguments[0].click();", referee_link)
            time.sleep(3)
            
            # Switch to new window if opened
            if len(self.driver.window_handles) > 1:
                self.driver.switch_to.window(self.driver.window_handles[-1])
                time.sleep(2)
                
                # Extract information from profile page
                profile_html = self.driver.page_source
                soup = BeautifulSoup(profile_html, 'html.parser')
                
                # Extract email
                email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', profile_html)
                if email_match:
                    referee.email = email_match.group()
                
                # Extract full name from title or headers
                title_tag = soup.find('title')
                if title_tag:
                    referee.full_name = title_tag.text.strip()
                
                # Look for status indicators
                profile_text = profile_html.lower()
                if 'declined' in profile_text:
                    referee.status = "Declined"
                elif 'accepted' in profile_text:
                    referee.status = "Accepted"
                elif 'pending' in profile_text:
                    referee.status = "Pending"
                elif 'submitted' in profile_text or 'report' in profile_text:
                    referee.status = "Submitted"
                    referee.report_submitted = True
                
                # Close window and return
                self.driver.close()
                self.driver.switch_to.window(self.main_window)
                time.sleep(1)
                
                referee.extraction_success = True
                
            else:
                # Try to extract from main page context
                row_html = self.driver.execute_script(
                    f"return document.querySelector('tr:has(a:contains(\"{referee_name}\"))').innerHTML;"
                )
                if row_html:
                    # Look for status in the same row
                    if 'declined' in row_html.lower():
                        referee.status = "Declined"
                    elif 'accepted' in row_html.lower():
                        referee.status = "Accepted"
                    elif 'report' in row_html.lower():
                        referee.status = "Submitted"
                        referee.report_submitted = True
                
        except Exception as e:
            print(f"         ⚠️  Error extracting referee details: {e}")
            referee.extraction_success = False
        
        return referee
    
    def download_pdf_robust(self, manuscript_id: str, link_element) -> Dict[str, Any]:
        """Robust PDF download using multiple strategies."""
        print(f"      📥 Downloading PDF for {manuscript_id}")
        
        result = {
            'success': False,
            'files': [],
            'method': None,
            'error': None
        }
        
        try:
            # Strategy 1: Get direct PDF URL and download with requests
            pdf_url = link_element.get_attribute('href')
            if not pdf_url:
                # Try JavaScript click to get URL
                self.driver.execute_script("arguments[0].click();", link_element)
                time.sleep(2)
                pdf_url = self.driver.current_url
                
            if pdf_url and pdf_url != self.driver.current_url:
                print(f"         🔗 PDF URL: {pdf_url}")
                
                # Make URL absolute if needed
                if not pdf_url.startswith('http'):
                    pdf_url = f"{self.base_url}{pdf_url}"
                
                # Download with requests
                response = self.session.get(pdf_url, stream=True, timeout=30)
                
                if response.status_code == 200:
                    # Check content type
                    content_type = response.headers.get('Content-Type', '').lower()
                    
                    if 'pdf' in content_type or response.content[:4] == b'%PDF':
                        # Valid PDF
                        filename = f"{manuscript_id}.pdf"
                        filepath = self.dirs['manuscripts'] / filename
                        
                        with open(filepath, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        
                        # Verify PDF
                        if self.verify_pdf(filepath):
                            print(f"         ✅ Downloaded valid PDF: {filename}")
                            result['success'] = True
                            result['files'].append(str(filepath))
                            result['method'] = 'requests'
                            self.current_session['pdfs_downloaded'] += 1
                            return result
                        else:
                            filepath.unlink()
                            print(f"         ❌ Invalid PDF file")
            
            # Strategy 2: Traditional Selenium download
            print(f"         🔄 Trying Selenium download...")
            
            # Clear temp directory
            for f in self.dirs['temp'].glob('*'):
                f.unlink()
            
            # Click link
            link_element.click()
            
            # Wait for download
            downloaded = self.wait_for_download(self.dirs['temp'], timeout=30)
            
            if downloaded:
                for file in downloaded:
                    if self.verify_pdf(file):
                        # Move to manuscripts folder
                        dest = self.dirs['manuscripts'] / f"{manuscript_id}.pdf"
                        shutil.move(str(file), str(dest))
                        result['success'] = True
                        result['files'].append(str(dest))
                        result['method'] = 'selenium'
                        self.current_session['pdfs_downloaded'] += 1
                        print(f"         ✅ Downloaded via Selenium: {dest.name}")
                    else:
                        # Save invalid file to debug
                        debug_path = self.dirs['debug'] / f"{manuscript_id}_{file.name}"
                        shutil.move(str(file), str(debug_path))
                        print(f"         ⚠️  Invalid file saved to debug: {debug_path.name}")
            
            # Strategy 3: Check for iframe or embedded viewer
            if not result['success']:
                print(f"         🔄 Checking for embedded PDF...")
                
                # Look for PDF viewer
                try:
                    # Switch to potential iframe
                    iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                    for iframe in iframes:
                        self.driver.switch_to.frame(iframe)
                        if 'pdf' in self.driver.current_url.lower():
                            pdf_url = self.driver.current_url
                            self.driver.switch_to.default_content()
                            
                            # Download the PDF
                            response = self.session.get(pdf_url, stream=True)
                            if response.status_code == 200:
                                filename = f"{manuscript_id}.pdf"
                                filepath = self.dirs['manuscripts'] / filename
                                
                                with open(filepath, 'wb') as f:
                                    f.write(response.content)
                                
                                if self.verify_pdf(filepath):
                                    result['success'] = True
                                    result['files'].append(str(filepath))
                                    result['method'] = 'iframe'
                                    self.current_session['pdfs_downloaded'] += 1
                                    print(f"         ✅ Downloaded from iframe: {filename}")
                                else:
                                    filepath.unlink()
                        self.driver.switch_to.default_content()
                except:
                    self.driver.switch_to.default_content()
                
        except Exception as e:
            result['error'] = str(e)
            print(f"         ❌ Download error: {e}")
        
        return result
    
    def verify_pdf(self, filepath: Path) -> bool:
        """Verify if a file is a valid PDF."""
        if not filepath.exists():
            return False
        
        try:
            # Check file size
            if filepath.stat().st_size < 1024:  # Less than 1KB
                return False
            
            # Check PDF header
            with open(filepath, 'rb') as f:
                header = f.read(4)
                if header != b'%PDF':
                    return False
            
            # Check for HTML content
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(1000).lower()
                if any(tag in content for tag in ['<html', '<head', '<body', '<!doctype']):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def wait_for_download(self, directory: Path, timeout: int = 30) -> List[Path]:
        """Wait for downloads to complete."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Get all files in directory
            files = list(directory.glob('*'))
            
            # Filter out partial downloads
            complete_files = []
            for f in files:
                if not f.name.endswith(('.crdownload', '.tmp', '.part')):
                    complete_files.append(f)
            
            if complete_files:
                # Wait a bit more to ensure download is complete
                time.sleep(2)
                return complete_files
            
            time.sleep(1)
        
        return []
    
    def extract_manuscripts(self) -> List[Dict]:
        """Extract all manuscript data with referee status tracking."""
        manuscripts = []
        
        # Parse table
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Find the main table
        table = soup.find('table', {'class': 'datatable'}) or soup.find('table')
        
        if not table:
            print("❌ Could not find manuscripts table")
            return manuscripts
        
        rows = table.find_all('tr')[1:]  # Skip header
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 6:
                continue
            
            # Extract manuscript ID
            ms_id_match = re.search(r'(M\d{6})', cells[0].get_text())
            if not ms_id_match:
                continue
            
            ms_id = ms_id_match.group(1)
            print(f"\n   📄 Processing manuscript: {ms_id}")
            
            # Extract basic info
            ms_data = {
                'manuscript_id': ms_id,
                'title': cells[1].get_text(strip=True) if len(cells) > 1 else '',
                'corresponding_editor': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                'associate_editor': cells[3].get_text(strip=True) if len(cells) > 3 else '',
                'submitted': cells[4].get_text(strip=True) if len(cells) > 4 else '',
                'days_in_system': cells[5].get_text(strip=True) if len(cells) > 5 else '',
                'referees': [],
                'pdfs': [],
                'statistics': {
                    'total_invited': 0,
                    'accepted': 0,
                    'declined': 0,
                    'pending': 0,
                    'reports_submitted': 0
                }
            }
            
            # Extract referees from the row
            row_text = row.get_text()
            
            # Common referee names to look for
            referee_names = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', row_text)
            
            # Get unique names that look like referee names
            seen_names = set()
            for name in referee_names:
                if (len(name) > 2 and 
                    name not in ['Editor', 'Associate', 'Submitted', 'Days', 'System'] and
                    name not in seen_names):
                    seen_names.add(name)
                    
                    # Extract referee details
                    referee = self.extract_referee_details(name, ms_id)
                    ms_data['referees'].append(referee.__dict__)
                    
                    # Update statistics
                    ms_data['statistics']['total_invited'] += 1
                    if referee.status == "Accepted":
                        ms_data['statistics']['accepted'] += 1
                    elif referee.status == "Declined":
                        ms_data['statistics']['declined'] += 1
                    elif referee.status == "Pending":
                        ms_data['statistics']['pending'] += 1
                    
                    if referee.report_submitted:
                        ms_data['statistics']['reports_submitted'] += 1
            
            # Download manuscript PDF
            try:
                # Find manuscript link
                ms_link = self.driver.find_element(By.XPATH, f"//a[contains(text(), '{ms_id}')]")
                download_result = self.download_pdf_robust(ms_id, ms_link)
                
                if download_result['success']:
                    ms_data['pdfs'] = download_result['files']
                    ms_data['pdf_download_method'] = download_result['method']
                else:
                    ms_data['pdf_error'] = download_result.get('error', 'Unknown error')
                    
            except Exception as e:
                print(f"      ❌ Could not download PDF: {e}")
                ms_data['pdf_error'] = str(e)
            
            manuscripts.append(ms_data)
            self.current_session['manuscripts_processed'] += 1
            self.current_session['referees_extracted'] += len(ms_data['referees'])
            
            # Save intermediate results
            self.save_results(manuscripts, intermediate=True)
        
        return manuscripts
    
    def save_results(self, manuscripts: List[Dict], intermediate: bool = False):
        """Save extraction results."""
        results = {
            'journal': self.journal_name,
            'extraction_time': datetime.now().isoformat(),
            'session_info': {
                'start_time': self.current_session['start_time'].isoformat(),
                'manuscripts_processed': self.current_session['manuscripts_processed'],
                'referees_extracted': self.current_session['referees_extracted'],
                'pdfs_downloaded': self.current_session['pdfs_downloaded'],
                'errors': self.current_session['errors']
            },
            'summary': {
                'total_manuscripts': len(manuscripts),
                'total_referees': sum(len(m['referees']) for m in manuscripts),
                'referees_accepted': sum(m['statistics']['accepted'] for m in manuscripts),
                'referees_declined': sum(m['statistics']['declined'] for m in manuscripts),
                'referees_pending': sum(m['statistics']['pending'] for m in manuscripts),
                'reports_submitted': sum(m['statistics']['reports_submitted'] for m in manuscripts),
                'pdfs_downloaded': self.current_session['pdfs_downloaded']
            },
            'manuscripts': manuscripts
        }
        
        # Save JSON
        filename = 'intermediate_results.json' if intermediate else 'final_results.json'
        json_path = self.dirs['data'] / filename
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        if not intermediate:
            # Generate summary report
            report_path = self.dirs['data'] / 'extraction_report.txt'
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(f"SICON Extraction Report\n")
                f.write(f"=" * 50 + "\n\n")
                f.write(f"Extraction Time: {results['extraction_time']}\n")
                f.write(f"Total Manuscripts: {results['summary']['total_manuscripts']}\n")
                f.write(f"Total Referees: {results['summary']['total_referees']}\n")
                f.write(f"  - Accepted: {results['summary']['referees_accepted']}\n")
                f.write(f"  - Declined: {results['summary']['referees_declined']}\n")
                f.write(f"  - Pending: {results['summary']['referees_pending']}\n")
                f.write(f"  - Reports Submitted: {results['summary']['reports_submitted']}\n")
                f.write(f"PDFs Downloaded: {results['summary']['pdfs_downloaded']}\n\n")
                
                for ms in manuscripts:
                    f.write(f"\nManuscript {ms['manuscript_id']}\n")
                    f.write(f"  Title: {ms['title']}\n")
                    f.write(f"  Referees: {len(ms['referees'])}\n")
                    for ref in ms['referees']:
                        f.write(f"    - {ref['name']} ({ref['status']})")
                        if ref['email']:
                            f.write(f" - {ref['email']}")
                        f.write("\n")
                    if ms.get('pdfs'):
                        f.write(f"  PDFs: {', '.join([Path(p).name for p in ms['pdfs']])}\n")
                    else:
                        f.write(f"  PDF Error: {ms.get('pdf_error', 'No PDF downloaded')}\n")
            
            print(f"\n📊 Report saved to: {report_path}")
    
    def run_extraction(self):
        """Run the complete extraction process."""
        try:
            # Load environment variables
            from dotenv import load_dotenv
            load_dotenv()
            
            # Setup driver
            self.setup_driver()
            
            # Authenticate
            if not self.authenticate():
                raise Exception("Authentication failed")
            
            # Navigate to manuscripts
            if not self.navigate_to_manuscripts():
                raise Exception("Could not navigate to manuscripts")
            
            # Extract data
            manuscripts = self.extract_manuscripts()
            
            # Save final results
            self.save_results(manuscripts)
            
            print(f"\n🎉 Extraction complete!")
            print(f"📊 Results saved to: {self.output_dir}")
            
            return manuscripts
            
        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            self.current_session['errors'].append(str(e))
            self.save_screenshot("error", f"Error: {e}")
            raise
        finally:
            if self.driver:
                self.driver.quit()


def main():
    """Main execution function."""
    print("🚀 Starting foolproof SICON extraction")
    
    extractor = FoolproofSICONExtractor()
    try:
        results = extractor.run_extraction()
        print(f"✅ Successfully extracted {len(results)} manuscripts")
        return results
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return None


if __name__ == "__main__":
    main()