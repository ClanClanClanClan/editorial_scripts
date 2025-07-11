#!/usr/bin/env python3
"""
Final Working SICON Extractor - Based on Successful Runs
Combines working authentication with PDF download debugging
"""

import os
import re
import time
import json
import shutil
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()


class FinalWorkingSICONExtractor:
    """Final working SICON extractor with all fixes."""
    
    def __init__(self):
        self.output_dir = Path(f'./sicon_final_working_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.dirs = {
            'pdfs': self.output_dir / 'pdfs',
            'data': self.output_dir / 'data',
            'screenshots': self.output_dir / 'screenshots',
            'debug': self.output_dir / 'debug'
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(exist_ok=True)
        
        self.session = requests.Session()
        self.main_window = None
        self.debug_log = []
        
        print(f"📁 Output directory: {self.output_dir}")
    
    def log(self, message: str, level: str = "INFO"):
        """Log with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        print(log_entry)
        self.debug_log.append(log_entry)
    
    def setup_driver(self):
        """Setup Chrome driver with download configuration."""
        chrome_options = Options()
        
        prefs = {
            "download.default_directory": str(self.dirs['pdfs']),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": False,
            "safebrowsing.disable_download_protection": True,
            "profile.default_content_setting_values.automatic_downloads": 1
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)
        
        # Enable downloads
        self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": str(self.dirs['pdfs'])
        })
        
        self.log("Chrome driver initialized", "SUCCESS")
    
    def save_screenshot(self, name: str):
        """Save screenshot."""
        path = self.dirs['screenshots'] / f"{name}_{datetime.now().strftime('%H%M%S')}.png"
        self.driver.save_screenshot(str(path))
        self.log(f"Screenshot saved: {path.name}", "DEBUG")
    
    def authenticate(self) -> bool:
        """Authenticate using the working method."""
        self.log("Starting authentication")
        
        try:
            # Navigate to SICON
            self.driver.get("http://sicon.siam.org")
            time.sleep(5)
            self.main_window = self.driver.current_window_handle
            self.save_screenshot("01_initial")
            
            # Check if already authenticated
            if 'associate editor tasks' in self.driver.page_source.lower():
                self.log("Already authenticated!", "SUCCESS")
                return True
            
            # Dismiss privacy notification using working strategy
            self.log("Handling privacy notification")
            try:
                # Strategy 2 from successful runs
                privacy_button = self.driver.find_element(By.XPATH, "//input[@value='Continue']")
                privacy_button.click()
                self.log("Clicked privacy notification", "SUCCESS")
                time.sleep(3)
                self.save_screenshot("02_after_privacy")
            except Exception as e:
                self.log(f"No privacy notification found: {e}", "INFO")
            
            # Click ORCID link
            self.log("Finding ORCID link")
            orcid_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'orcid')]")
            self.driver.execute_script("arguments[0].click();", orcid_link)
            self.log("Clicked ORCID link", "SUCCESS")
            time.sleep(5)
            
            # Handle ORCID authentication
            if 'orcid.org' in self.driver.current_url:
                self.log("On ORCID page", "SUCCESS")
                self.save_screenshot("03_orcid_page")
                
                # Accept cookies
                try:
                    accept_cookies = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept All Cookies')]"))
                    )
                    accept_cookies.click()
                    self.log("Accepted ORCID cookies", "SUCCESS")
                    time.sleep(3)
                except:
                    self.log("No cookie banner", "INFO")
                
                # Fill credentials
                username = os.getenv('ORCID_USER', '0000-0002-9364-0124')
                password = os.getenv('ORCID_PASS', 'Hioupy0042%')
                
                # Find and fill fields
                username_field = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Email or 16-digit ORCID iD']"))
                )
                password_field = self.driver.find_element(By.XPATH, "//input[@placeholder='Your ORCID password']")
                
                username_field.clear()
                username_field.send_keys(username)
                password_field.clear()
                password_field.send_keys(password)
                self.log("Filled credentials", "SUCCESS")
                
                # Click sign in - using the exact button from screenshot
                signin_button = self.driver.find_element(By.XPATH, "//button[contains(., 'Sign in to ORCID')]")
                signin_button.click()
                self.log("Clicked sign in", "SUCCESS")
                
                time.sleep(10)
                self.save_screenshot("04_after_signin")
            
            # Handle post-auth privacy notification
            try:
                privacy_button = self.driver.find_element(By.XPATH, "//input[@value='Continue']")
                privacy_button.click()
                self.log("Clicked post-auth privacy notification", "SUCCESS")
                time.sleep(3)
            except:
                pass
            
            # Verify authentication
            if 'associate editor tasks' in self.driver.page_source.lower():
                self.log("Authentication successful!", "SUCCESS")
                self.sync_cookies()
                return True
            else:
                self.log("Authentication failed", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Authentication error: {e}", "ERROR")
            self.save_screenshot("auth_error")
            return False
    
    def sync_cookies(self):
        """Sync cookies to requests session."""
        for cookie in self.driver.get_cookies():
            self.session.cookies.set(cookie['name'], cookie['value'], 
                                   domain=cookie.get('domain'),
                                   path=cookie.get('path'))
        self.log(f"Synced {len(self.driver.get_cookies())} cookies")
    
    def navigate_to_manuscripts(self) -> bool:
        """Navigate to All Pending Manuscripts using the working method."""
        self.log("Navigating to manuscripts")
        
        try:
            # Find the "4 AE" link with folder_id=1800
            ae_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'folder_id=1800')]")
            href = ae_link.get_attribute('href')
            text = ae_link.text
            self.log(f"Found AE link: '{text}' -> {href}")
            
            # Click it
            self.driver.execute_script("arguments[0].click();", ae_link)
            time.sleep(5)
            self.save_screenshot("05_manuscripts_table")
            
            # Verify we reached the table
            if 'All Pending Manuscripts' in self.driver.page_source:
                self.log("Successfully reached manuscripts table", "SUCCESS")
                return True
            else:
                self.log("Failed to reach manuscripts table", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Navigation error: {e}", "ERROR")
            return False
    
    def extract_referee_data(self, referee_name: str, manuscript_id: str) -> Dict:
        """Extract referee data with email."""
        self.log(f"Extracting referee data: {referee_name}")
        
        referee_data = {
            'name': referee_name,
            'full_name': referee_name,
            'email': None,
            'status': 'Unknown'
        }
        
        try:
            # Find and click referee link
            referee_link = self.driver.find_element(By.XPATH, f"//a[contains(text(), '{referee_name}')]")
            self.driver.execute_script("arguments[0].click();", referee_link)
            time.sleep(3)
            
            # Check if new window opened
            if len(self.driver.window_handles) > 1:
                # Switch to new window
                self.driver.switch_to.window(self.driver.window_handles[-1])
                time.sleep(2)
                
                # Extract email
                profile_text = self.driver.page_source
                email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', profile_text)
                if email_match:
                    referee_data['email'] = email_match.group()
                    self.log(f"Found email: {referee_data['email']}", "SUCCESS")
                
                # Extract full name from title
                soup = BeautifulSoup(profile_text, 'html.parser')
                title_tag = soup.find('title')
                if title_tag and title_tag.text:
                    referee_data['full_name'] = title_tag.text.strip()
                
                # Close window and return
                self.driver.close()
                self.driver.switch_to.window(self.main_window)
                
        except Exception as e:
            self.log(f"Error extracting referee data: {e}", "ERROR")
        
        return referee_data
    
    def download_manuscript_pdf(self, manuscript_id: str) -> Dict:
        """Download manuscript PDF with debugging."""
        self.log(f"Attempting PDF download for {manuscript_id}")
        
        result = {
            'manuscript_id': manuscript_id,
            'downloaded': False,
            'method': None,
            'file': None,
            'debug_info': {}
        }
        
        try:
            # Find manuscript link
            ms_link = self.driver.find_element(By.XPATH, f"//a[contains(text(), '{manuscript_id}')]")
            
            # Get link attributes for debugging
            href = ms_link.get_attribute('href')
            onclick = ms_link.get_attribute('onclick')
            result['debug_info']['href'] = href
            result['debug_info']['onclick'] = onclick
            
            self.log(f"Link attributes - href: {href}, onclick: {onclick}", "DEBUG")
            
            # Method 1: Click and check for new window
            initial_windows = len(self.driver.window_handles)
            initial_files = set(self.dirs['pdfs'].glob('*'))
            
            ms_link.click()
            time.sleep(5)
            
            # Check for new window (PDF viewer)
            if len(self.driver.window_handles) > initial_windows:
                self.log("New window opened", "INFO")
                self.driver.switch_to.window(self.driver.window_handles[-1])
                
                pdf_url = self.driver.current_url
                self.log(f"PDF URL: {pdf_url}", "DEBUG")
                result['debug_info']['pdf_url'] = pdf_url
                
                # Download with requests
                if self.download_pdf_with_requests(manuscript_id, pdf_url):
                    result['downloaded'] = True
                    result['method'] = 'requests_from_viewer'
                    result['file'] = f"{manuscript_id}.pdf"
                
                # Close PDF viewer
                self.driver.close()
                self.driver.switch_to.window(self.main_window)
            
            # Method 2: Check for direct download
            if not result['downloaded']:
                new_files = set(self.dirs['pdfs'].glob('*')) - initial_files
                if new_files:
                    for f in new_files:
                        if self.verify_pdf(f):
                            # Rename to manuscript ID
                            new_name = self.dirs['pdfs'] / f"{manuscript_id}.pdf"
                            f.rename(new_name)
                            result['downloaded'] = True
                            result['method'] = 'direct_download'
                            result['file'] = new_name.name
                            self.log(f"Direct download successful: {new_name.name}", "SUCCESS")
                            break
            
            # Method 3: Extract URL from onclick and download
            if not result['downloaded'] and onclick and 'window.open' in onclick:
                url_match = re.search(r"window\.open\('([^']+)'", onclick)
                if url_match:
                    pdf_url = url_match.group(1)
                    if not pdf_url.startswith('http'):
                        pdf_url = f"http://sicon.siam.org{pdf_url}"
                    
                    self.log(f"Extracted URL from onclick: {pdf_url}", "DEBUG")
                    
                    if self.download_pdf_with_requests(manuscript_id, pdf_url):
                        result['downloaded'] = True
                        result['method'] = 'requests_from_onclick'
                        result['file'] = f"{manuscript_id}.pdf"
            
        except Exception as e:
            self.log(f"Download error: {e}", "ERROR")
            result['debug_info']['error'] = str(e)
        
        return result
    
    def download_pdf_with_requests(self, manuscript_id: str, url: str) -> bool:
        """Download PDF using requests session."""
        try:
            self.log(f"Downloading PDF with requests: {url}", "DEBUG")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': 'http://sicon.siam.org'
            }
            
            response = self.session.get(url, headers=headers, stream=True, timeout=30)
            
            if response.status_code == 200:
                content = response.content
                
                # Verify it's a PDF
                if content[:4] == b'%PDF':
                    pdf_path = self.dirs['pdfs'] / f"{manuscript_id}.pdf"
                    with open(pdf_path, 'wb') as f:
                        f.write(content)
                    
                    self.log(f"PDF downloaded successfully: {pdf_path.name} ({len(content)} bytes)", "SUCCESS")
                    return True
                else:
                    # Save for debugging
                    debug_path = self.dirs['debug'] / f"{manuscript_id}_response.bin"
                    with open(debug_path, 'wb') as f:
                        f.write(content[:5000])
                    
                    self.log(f"Response is not a PDF. First bytes: {content[:10]}", "ERROR")
                    
                    # Check if HTML
                    if b'<html' in content[:1000].lower():
                        html_path = self.dirs['debug'] / f"{manuscript_id}_response.html"
                        with open(html_path, 'w') as f:
                            f.write(response.text)
                        self.log("Response is HTML - likely authentication issue", "ERROR")
            else:
                self.log(f"HTTP error: {response.status_code}", "ERROR")
                
        except Exception as e:
            self.log(f"Request error: {e}", "ERROR")
        
        return False
    
    def verify_pdf(self, file_path: Path) -> bool:
        """Verify if file is a valid PDF."""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
            return header == b'%PDF'
        except:
            return False
    
    def extract_manuscripts(self) -> List[Dict]:
        """Extract all manuscript data."""
        self.log("Extracting manuscripts")
        manuscripts = []
        
        # Parse table
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Find manuscript IDs
        ms_pattern = re.compile(r'M\d{6}')
        ms_ids = set(ms_pattern.findall(str(soup)))
        
        self.log(f"Found {len(ms_ids)} manuscripts: {ms_ids}")
        
        for ms_id in sorted(ms_ids):
            self.log(f"\n📄 Processing {ms_id}")
            
            manuscript = {
                'manuscript_id': ms_id,
                'referees': [],
                'pdf_download': None
            }
            
            # Find row containing this manuscript
            try:
                row = soup.find('tr', string=re.compile(ms_id))
                if row and row.parent:
                    row = row.parent  # Get the actual tr element
                    
                    # Extract basic info from cells
                    cells = row.find_all('td')
                    if len(cells) > 5:
                        manuscript['title'] = cells[1].get_text(strip=True)
                        manuscript['corresponding_editor'] = cells[2].get_text(strip=True)
                        manuscript['associate_editor'] = cells[3].get_text(strip=True)
                        manuscript['submitted'] = cells[4].get_text(strip=True)
                        manuscript['days_in_system'] = cells[5].get_text(strip=True)
                    
                    # Extract referees
                    referee_names = ['Ferrari', 'LI', 'Cohen', 'Guo', 'Ekren', 'Ren', 'daudin', 'Tangpi']
                    
                    for name in referee_names:
                        if name in str(row):
                            self.log(f"  Found referee: {name}")
                            referee_data = self.extract_referee_data(name, ms_id)
                            manuscript['referees'].append(referee_data)
            except Exception as e:
                self.log(f"Error extracting manuscript data: {e}", "ERROR")
            
            # Download PDF
            pdf_result = self.download_manuscript_pdf(ms_id)
            manuscript['pdf_download'] = pdf_result
            
            manuscripts.append(manuscript)
            
            # Save intermediate results
            self.save_results(manuscripts, intermediate=True)
        
        return manuscripts
    
    def save_results(self, manuscripts: List[Dict], intermediate: bool = False):
        """Save extraction results."""
        results = {
            'extraction_time': datetime.now().isoformat(),
            'total_manuscripts': len(manuscripts),
            'total_referees': sum(len(m['referees']) for m in manuscripts),
            'pdfs_downloaded': sum(1 for m in manuscripts if m.get('pdf_download', {}).get('downloaded')),
            'manuscripts': manuscripts,
            'debug_log': self.debug_log[-100:]  # Last 100 log entries
        }
        
        filename = 'intermediate_results.json' if intermediate else 'final_results.json'
        path = self.dirs['data'] / filename
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        if not intermediate:
            # Generate summary report
            report_path = self.dirs['data'] / 'extraction_report.txt'
            with open(report_path, 'w') as f:
                f.write("SICON Extraction Report\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Extraction Time: {results['extraction_time']}\n")
                f.write(f"Total Manuscripts: {results['total_manuscripts']}\n")
                f.write(f"Total Referees: {results['total_referees']}\n")
                f.write(f"PDFs Downloaded: {results['pdfs_downloaded']}\n\n")
                
                for ms in manuscripts:
                    f.write(f"\nManuscript {ms['manuscript_id']}\n")
                    f.write(f"  Title: {ms.get('title', 'N/A')}\n")
                    f.write(f"  Referees: {len(ms['referees'])}\n")
                    for ref in ms['referees']:
                        f.write(f"    - {ref['name']}: {ref.get('email', 'No email')}\n")
                    
                    pdf_info = ms.get('pdf_download', {})
                    if pdf_info.get('downloaded'):
                        f.write(f"  PDF: ✅ Downloaded ({pdf_info.get('method')})\n")
                    else:
                        f.write(f"  PDF: ❌ Failed\n")
                        if pdf_info.get('debug_info'):
                            f.write(f"    Debug: {pdf_info['debug_info']}\n")
            
            self.log(f"Report saved to: {report_path}")
    
    def run(self):
        """Run the complete extraction."""
        try:
            self.setup_driver()
            
            if not self.authenticate():
                raise Exception("Authentication failed")
            
            if not self.navigate_to_manuscripts():
                raise Exception("Navigation failed")
            
            manuscripts = self.extract_manuscripts()
            
            self.save_results(manuscripts)
            
            self.log(f"\n🎉 Extraction complete!", "SUCCESS")
            self.log(f"📊 Results saved to: {self.output_dir}")
            
            # Summary
            total_refs = sum(len(m['referees']) for m in manuscripts)
            pdfs = sum(1 for m in manuscripts if m.get('pdf_download', {}).get('downloaded'))
            
            print(f"\n📊 Summary:")
            print(f"  Manuscripts: {len(manuscripts)}")
            print(f"  Referees: {total_refs}")
            print(f"  PDFs: {pdfs}")
            
            return manuscripts
            
        except Exception as e:
            self.log(f"Fatal error: {e}", "ERROR")
            self.save_screenshot("fatal_error")
            raise
        finally:
            if hasattr(self, 'driver'):
                self.driver.quit()


def main():
    """Main execution."""
    print("🚀 Starting Final Working SICON Extraction")
    
    extractor = FinalWorkingSICONExtractor()
    try:
        results = extractor.run()
        print(f"✅ Successfully extracted {len(results)} manuscripts")
        return results
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return None


if __name__ == "__main__":
    main()