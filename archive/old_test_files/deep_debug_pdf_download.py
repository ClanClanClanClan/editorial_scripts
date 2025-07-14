#!/usr/bin/env python3
"""
Deep debugging script to understand PDF download flow in SICON
"""

import os
import re
import time
import json
import hashlib
import requests
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()


class PDFDownloadDebugger:
    def __init__(self):
        self.output_dir = Path(f'./pdf_debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        self.output_dir.mkdir(exist_ok=True)
        
        self.debug_log = []
        self.session = requests.Session()
        
        # Create subdirectories
        self.dirs = {
            'screenshots': self.output_dir / 'screenshots',
            'html': self.output_dir / 'html',
            'downloads': self.output_dir / 'downloads',
            'analysis': self.output_dir / 'analysis'
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(exist_ok=True)
    
    def log(self, message: str, level: str = "INFO"):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] {level}: {message}"
        print(log_entry)
        self.debug_log.append(log_entry)
    
    def setup_driver(self):
        """Setup Chrome with download directory"""
        chrome_options = Options()
        
        # Configure downloads
        prefs = {
            "download.default_directory": str(self.dirs['downloads']),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": False,
            "safebrowsing.disable_download_protection": True,
            "profile.default_content_setting_values.automatic_downloads": 1
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Add debugging options
        chrome_options.add_argument('--enable-logging')
        chrome_options.add_argument('--v=1')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)
        
        # Enable download behavior
        self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": str(self.dirs['downloads'])
        })
        
        # Enable network logging
        self.driver.execute_cdp_cmd("Network.enable", {})
        
        self.log("Driver setup complete")
    
    def save_state(self, name: str):
        """Save current page state for analysis"""
        timestamp = datetime.now().strftime("%H%M%S")
        
        # Screenshot
        screenshot_path = self.dirs['screenshots'] / f"{name}_{timestamp}.png"
        self.driver.save_screenshot(str(screenshot_path))
        
        # HTML
        html_path = self.dirs['html'] / f"{name}_{timestamp}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
        
        # Current URL
        self.log(f"Current URL: {self.driver.current_url}")
        
        # Cookies
        cookies = self.driver.get_cookies()
        self.log(f"Cookies: {len(cookies)} cookies present")
    
    def authenticate(self) -> bool:
        """Authenticate with SICON"""
        self.log("Starting authentication")
        
        try:
            # Navigate to SICON
            self.driver.get("http://sicon.siam.org")
            time.sleep(5)
            self.save_state("01_initial")
            
            # Check if already authenticated
            if 'associate editor tasks' in self.driver.page_source.lower():
                self.log("Already authenticated!", "SUCCESS")
                return True
            
            # Handle privacy notification
            try:
                privacy_button = self.driver.find_element(By.XPATH, "//input[@value='Continue']")
                privacy_button.click()
                self.log("Clicked privacy notification")
                time.sleep(3)
                self.save_state("02_after_privacy")
            except:
                self.log("No privacy notification found")
            
            # Find and click ORCID link
            orcid_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'orcid')]")
            href = orcid_link.get_attribute('href')
            self.log(f"ORCID link href: {href}")
            
            # Try JavaScript click
            self.driver.execute_script("arguments[0].click();", orcid_link)
            time.sleep(5)
            self.save_state("03_after_orcid_click")
            
            # Check if on ORCID page
            if 'orcid.org' in self.driver.current_url:
                self.log("On ORCID page")
                
                # Handle cookie consent
                try:
                    accept_button = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept All Cookies')]"))
                    )
                    accept_button.click()
                    self.log("Accepted ORCID cookies")
                    time.sleep(3)
                    self.save_state("04_after_cookies")
                except:
                    self.log("No cookie banner or already accepted")
                
                # Fill credentials
                username = os.getenv('ORCID_USER')
                password = os.getenv('ORCID_PASS')
                
                # Find fields
                username_field = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Email or 16-digit ORCID iD']"))
                )
                password_field = self.driver.find_element(By.XPATH, "//input[@placeholder='Your ORCID password']")
                
                username_field.clear()
                username_field.send_keys(username)
                password_field.clear()
                password_field.send_keys(password)
                
                self.log("Filled credentials")
                self.save_state("05_credentials_filled")
                
                # Find and click sign in button
                signin_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Sign in to ORCID')]"))
                )
                signin_button.click()
                
                self.log("Clicked sign in")
                time.sleep(10)
                self.save_state("06_after_signin")
            
            # Handle post-auth privacy notification
            try:
                privacy_button = self.driver.find_element(By.XPATH, "//input[@value='Continue']")
                privacy_button.click()
                self.log("Clicked post-auth privacy notification")
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
            self.save_state("auth_error")
            return False
    
    def sync_cookies(self):
        """Sync cookies to requests session"""
        for cookie in self.driver.get_cookies():
            self.session.cookies.set(cookie['name'], cookie['value'])
        self.log(f"Synced {len(self.driver.get_cookies())} cookies to requests session")
    
    def navigate_to_manuscripts(self) -> bool:
        """Navigate to manuscripts table"""
        self.log("Navigating to manuscripts")
        
        try:
            # Find the "4 AE" link
            ae_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'folder_id=1800')]")
            href = ae_link.get_attribute('href')
            self.log(f"Found AE link: {href}")
            
            # Click it
            self.driver.execute_script("arguments[0].click();", ae_link)
            time.sleep(5)
            self.save_state("07_manuscripts_table")
            
            if 'All Pending Manuscripts' in self.driver.page_source:
                self.log("Successfully reached manuscripts table", "SUCCESS")
                return True
            else:
                self.log("Failed to reach manuscripts table", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Navigation error: {e}", "ERROR")
            return False
    
    def analyze_manuscript_links(self):
        """Deep analysis of manuscript links"""
        self.log("Analyzing manuscript links")
        
        # Find all manuscript links
        ms_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'M') and contains(@href, 'javascript')]")
        
        self.log(f"Found {len(ms_links)} manuscript links")
        
        analysis = []
        
        for i, link in enumerate(ms_links[:2]):  # Analyze first 2
            try:
                text = link.text
                href = link.get_attribute('href')
                onclick = link.get_attribute('onclick')
                
                link_info = {
                    'text': text,
                    'href': href,
                    'onclick': onclick,
                    'tag_name': link.tag_name,
                    'classes': link.get_attribute('class')
                }
                
                self.log(f"\nLink {i+1}: {text}")
                self.log(f"  href: {href}")
                self.log(f"  onclick: {onclick}")
                
                # Try different interaction methods
                self.log(f"Testing interaction methods for {text}")
                
                # Method 1: Get URL from onclick
                if onclick:
                    # Extract URL from JavaScript
                    url_match = re.search(r"window\.open\('([^']+)'", onclick)
                    if url_match:
                        pdf_url = url_match.group(1)
                        if not pdf_url.startswith('http'):
                            pdf_url = f"http://sicon.siam.org{pdf_url}"
                        link_info['extracted_url'] = pdf_url
                        self.log(f"  Extracted URL: {pdf_url}")
                
                # Method 2: Hover and check for tooltips
                ActionChains(self.driver).move_to_element(link).perform()
                time.sleep(0.5)
                
                # Method 3: Right-click to see context menu
                ActionChains(self.driver).context_click(link).perform()
                time.sleep(0.5)
                self.save_state(f"08_context_menu_{text}")
                
                # Press ESC to close context menu
                link.send_keys(Keys.ESCAPE)
                
                analysis.append(link_info)
                
            except Exception as e:
                self.log(f"Error analyzing link {i+1}: {e}", "ERROR")
        
        # Save analysis
        analysis_path = self.dirs['analysis'] / 'link_analysis.json'
        with open(analysis_path, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        self.log(f"Saved link analysis to {analysis_path}")
        
        return analysis
    
    def test_pdf_download(self, manuscript_id: str, link_element):
        """Test PDF download with multiple strategies"""
        self.log(f"\nTesting PDF download for {manuscript_id}")
        
        results = {
            'manuscript_id': manuscript_id,
            'strategies': {}
        }
        
        # Strategy 1: Direct click
        self.log("Strategy 1: Direct click")
        try:
            initial_files = set(self.dirs['downloads'].glob('*'))
            
            link_element.click()
            time.sleep(5)
            
            new_files = set(self.dirs['downloads'].glob('*')) - initial_files
            
            if new_files:
                for f in new_files:
                    self.log(f"  Downloaded: {f.name} ({f.stat().st_size} bytes)")
                    
                    # Check file type
                    with open(f, 'rb') as file:
                        header = file.read(10)
                        if header.startswith(b'%PDF'):
                            self.log(f"  ✅ Valid PDF header detected")
                            results['strategies']['direct_click'] = {
                                'success': True,
                                'file': str(f),
                                'size': f.stat().st_size
                            }
                        else:
                            self.log(f"  ❌ Not a PDF. Header: {header}")
                            # Save first 1000 bytes for analysis
                            with open(self.dirs['analysis'] / f"{manuscript_id}_download_sample.bin", 'wb') as out:
                                file.seek(0)
                                out.write(file.read(1000))
            else:
                self.log("  No files downloaded")
                results['strategies']['direct_click'] = {'success': False, 'error': 'No files downloaded'}
                
            # Check if new window/tab opened
            if len(self.driver.window_handles) > 1:
                self.log("  New window opened")
                self.driver.switch_to.window(self.driver.window_handles[-1])
                current_url = self.driver.current_url
                self.log(f"  New window URL: {current_url}")
                self.save_state(f"09_new_window_{manuscript_id}")
                
                # Check if it's a PDF viewer
                if 'pdf' in current_url.lower() or 'type=application/pdf' in self.driver.page_source:
                    self.log("  PDF viewer detected")
                    results['strategies']['direct_click']['pdf_viewer'] = True
                
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
                
        except Exception as e:
            self.log(f"  Error: {e}", "ERROR")
            results['strategies']['direct_click'] = {'success': False, 'error': str(e)}
        
        # Strategy 2: Extract URL and download with requests
        self.log("\nStrategy 2: Extract URL and use requests")
        try:
            onclick = link_element.get_attribute('onclick')
            if onclick:
                url_match = re.search(r"window\.open\('([^']+)'", onclick)
                if url_match:
                    pdf_url = url_match.group(1)
                    if not pdf_url.startswith('http'):
                        pdf_url = f"http://sicon.siam.org{pdf_url}"
                    
                    self.log(f"  Extracted URL: {pdf_url}")
                    
                    # Download with requests
                    response = self.session.get(pdf_url, stream=True, timeout=30)
                    self.log(f"  Response status: {response.status_code}")
                    self.log(f"  Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
                    
                    if response.status_code == 200:
                        # Check content
                        content_sample = response.content[:10]
                        if content_sample.startswith(b'%PDF'):
                            # Save PDF
                            pdf_path = self.dirs['downloads'] / f"{manuscript_id}_requests.pdf"
                            with open(pdf_path, 'wb') as f:
                                f.write(response.content)
                            
                            self.log(f"  ✅ Downloaded valid PDF: {pdf_path.name}")
                            results['strategies']['requests'] = {
                                'success': True,
                                'file': str(pdf_path),
                                'size': pdf_path.stat().st_size,
                                'content_type': response.headers.get('Content-Type')
                            }
                        else:
                            self.log(f"  ❌ Not a PDF. Content starts with: {content_sample}")
                            # Save for analysis
                            debug_path = self.dirs['analysis'] / f"{manuscript_id}_requests_response.bin"
                            with open(debug_path, 'wb') as f:
                                f.write(response.content[:5000])
                            
                            # Check if it's HTML
                            if b'<html' in response.content[:1000].lower():
                                self.log("  Response is HTML - likely a login page or error")
                                html_path = self.dirs['analysis'] / f"{manuscript_id}_response.html"
                                with open(html_path, 'w') as f:
                                    f.write(response.text)
                                    
                            results['strategies']['requests'] = {
                                'success': False,
                                'error': 'Not a PDF',
                                'content_type': response.headers.get('Content-Type')
                            }
                    else:
                        results['strategies']['requests'] = {
                            'success': False,
                            'error': f'HTTP {response.status_code}'
                        }
                        
        except Exception as e:
            self.log(f"  Error: {e}", "ERROR")
            results['strategies']['requests'] = {'success': False, 'error': str(e)}
        
        # Strategy 3: JavaScript execution
        self.log("\nStrategy 3: Execute JavaScript directly")
        try:
            # Get the onclick content
            onclick = link_element.get_attribute('onclick')
            if onclick:
                self.log(f"  Executing: {onclick}")
                self.driver.execute_script(onclick)
                time.sleep(5)
                
                # Check for new downloads
                new_files = set(self.dirs['downloads'].glob('*')) - initial_files
                if new_files:
                    for f in new_files:
                        self.log(f"  Downloaded via JS: {f.name}")
                        results['strategies']['javascript'] = {
                            'success': True,
                            'file': str(f)
                        }
                else:
                    results['strategies']['javascript'] = {
                        'success': False,
                        'error': 'No files downloaded'
                    }
                    
        except Exception as e:
            self.log(f"  Error: {e}", "ERROR")
            results['strategies']['javascript'] = {'success': False, 'error': str(e)}
        
        return results
    
    def run_full_debug(self):
        """Run complete debugging session"""
        self.log("Starting full PDF download debug session")
        
        try:
            # Setup
            self.setup_driver()
            
            # Authenticate
            if not self.authenticate():
                self.log("Authentication failed - cannot continue", "ERROR")
                return
            
            # Navigate to manuscripts
            if not self.navigate_to_manuscripts():
                self.log("Navigation failed - cannot continue", "ERROR")
                return
            
            # Analyze links
            link_analysis = self.analyze_manuscript_links()
            
            # Test PDF downloads
            ms_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'M') and contains(@href, 'javascript')]")
            
            download_results = []
            
            for link in ms_links[:2]:  # Test first 2
                ms_id = link.text.strip()
                if re.match(r'M\d{6}', ms_id):
                    result = self.test_pdf_download(ms_id, link)
                    download_results.append(result)
                    
                    # Return to main page if needed
                    if len(self.driver.window_handles) > 1:
                        self.driver.switch_to.window(self.driver.window_handles[0])
            
            # Save all results
            final_report = {
                'session_time': datetime.now().isoformat(),
                'authentication': 'Success',
                'link_analysis': link_analysis,
                'download_results': download_results,
                'debug_log': self.debug_log
            }
            
            report_path = self.output_dir / 'debug_report.json'
            with open(report_path, 'w') as f:
                json.dump(final_report, f, indent=2)
            
            self.log(f"\n{'='*60}")
            self.log(f"Debug session complete. Results saved to:")
            self.log(f"  {self.output_dir}")
            self.log(f"  Report: {report_path}")
            
            # Print summary
            self.log(f"\nSummary:")
            for result in download_results:
                self.log(f"\n{result['manuscript_id']}:")
                for strategy, outcome in result['strategies'].items():
                    status = "✅" if outcome.get('success') else "❌"
                    self.log(f"  {strategy}: {status}")
                    
        except Exception as e:
            self.log(f"Fatal error: {e}", "ERROR")
            self.save_state("fatal_error")
        finally:
            self.driver.quit()
            
            # Save final log
            log_path = self.output_dir / 'debug_log.txt'
            with open(log_path, 'w') as f:
                f.write('\n'.join(self.debug_log))


if __name__ == "__main__":
    debugger = PDFDownloadDebugger()
    debugger.run_full_debug()