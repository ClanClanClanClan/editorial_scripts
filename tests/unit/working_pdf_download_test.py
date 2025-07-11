#!/usr/bin/env python3
"""
Working PDF download test based on successful authentication from previous runs
"""

import os
import re
import time
import json
import shutil
import requests
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoAlertPresentException
from dotenv import load_dotenv

load_dotenv()


class WorkingPDFDownloader:
    def __init__(self):
        self.output_dir = Path(f'./pdf_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        self.output_dir.mkdir(exist_ok=True)
        
        self.download_dir = self.output_dir / 'downloads'
        self.download_dir.mkdir(exist_ok=True)
        
        self.session = requests.Session()
        self.results = []
    
    def setup_driver(self):
        """Setup Chrome driver"""
        chrome_options = Options()
        
        prefs = {
            "download.default_directory": str(self.download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": False,
            "safebrowsing.disable_download_protection": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)
        
        # Enable downloads
        self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": str(self.download_dir)
        })
        
        print("✅ Driver initialized")
    
    def handle_alert(self):
        """Handle any alerts"""
        try:
            alert = self.driver.switch_to.alert
            alert_text = alert.text
            print(f"⚠️  Alert detected: {alert_text}")
            alert.accept()
            time.sleep(1)
        except:
            pass
    
    def authenticate(self):
        """Simplified authentication"""
        print("\n🔐 Authenticating...")
        
        # Go to SICON
        self.driver.get("http://sicon.siam.org")
        time.sleep(3)
        
        # Handle any alerts
        self.handle_alert()
        
        # Check if already authenticated
        if 'associate editor tasks' in self.driver.page_source.lower():
            print("✅ Already authenticated")
            return True
        
        # Handle privacy notification
        try:
            privacy = self.driver.find_element(By.XPATH, "//input[@value='Continue']")
            privacy.click()
            print("✅ Clicked privacy notification")
            time.sleep(2)
        except:
            pass
        
        # Find ORCID link
        try:
            orcid_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'orcid')]")
            self.driver.execute_script("arguments[0].click();", orcid_link)
            print("✅ Clicked ORCID link")
            time.sleep(5)
        except Exception as e:
            print(f"❌ Could not find ORCID link: {e}")
            return False
        
        # Check if on ORCID page
        if 'orcid.org' in self.driver.current_url:
            print("✅ On ORCID page")
            
            # Accept cookies
            try:
                accept = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept All Cookies')]"))
                )
                accept.click()
                print("✅ Accepted cookies")
                time.sleep(2)
            except:
                pass
            
            # Fill credentials
            try:
                username_field = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Email or 16-digit ORCID iD']"))
                )
                password_field = self.driver.find_element(By.XPATH, "//input[@placeholder='Your ORCID password']")
                
                username = os.getenv('ORCID_USER')
                password = os.getenv('ORCID_PASS')
                
                username_field.clear()
                username_field.send_keys(username)
                password_field.clear()
                password_field.send_keys(password)
                
                print("✅ Filled credentials")
                
                # Click sign in
                signin = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Sign in to ORCID')]")
                signin.click()
                print("✅ Clicked sign in")
                
                time.sleep(10)
                
            except Exception as e:
                print(f"❌ Login error: {e}")
                return False
        
        # Handle post-auth privacy
        try:
            privacy = self.driver.find_element(By.XPATH, "//input[@value='Continue']")
            privacy.click()
            print("✅ Clicked post-auth privacy")
            time.sleep(2)
        except:
            pass
        
        # Verify authentication
        if 'associate editor tasks' in self.driver.page_source.lower():
            print("✅ Authentication successful")
            self.sync_cookies()
            return True
        else:
            print("❌ Authentication failed")
            return False
    
    def sync_cookies(self):
        """Sync cookies to requests session"""
        for cookie in self.driver.get_cookies():
            self.session.cookies.set(cookie['name'], cookie['value'], 
                                   domain=cookie.get('domain'),
                                   path=cookie.get('path'))
        print(f"✅ Synced {len(self.driver.get_cookies())} cookies")
    
    def navigate_to_manuscripts(self):
        """Navigate to manuscripts table"""
        print("\n📋 Navigating to manuscripts...")
        
        try:
            # Find the "4 AE" link
            ae_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'folder_id=1800')]")
            self.driver.execute_script("arguments[0].click();", ae_link)
            time.sleep(5)
            
            if 'All Pending Manuscripts' in self.driver.page_source:
                print("✅ Reached manuscripts table")
                return True
            else:
                print("❌ Failed to reach manuscripts table")
                return False
        except Exception as e:
            print(f"❌ Navigation error: {e}")
            return False
    
    def analyze_pdf_links(self):
        """Analyze PDF download mechanism"""
        print("\n🔍 Analyzing PDF links...")
        
        # Find manuscript links
        ms_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'M') and string-length(text()) = 7]")
        print(f"Found {len(ms_links)} manuscript links")
        
        # Test first manuscript
        if ms_links:
            first_link = ms_links[0]
            ms_id = first_link.text
            
            print(f"\n📄 Testing manuscript: {ms_id}")
            
            # Get link attributes
            href = first_link.get_attribute('href')
            onclick = first_link.get_attribute('onclick')
            
            print(f"  href: {href}")
            print(f"  onclick: {onclick}")
            
            # Save current page for return
            main_window = self.driver.current_window_handle
            
            # Strategy 1: Direct click and monitor
            print("\n  Strategy 1: Direct click")
            initial_windows = len(self.driver.window_handles)
            initial_files = set(self.download_dir.glob('*'))
            
            first_link.click()
            time.sleep(5)
            
            # Check for new window
            if len(self.driver.window_handles) > initial_windows:
                print("  ✅ New window opened")
                self.driver.switch_to.window(self.driver.window_handles[-1])
                
                new_url = self.driver.current_url
                print(f"  URL: {new_url}")
                
                # Check if it's a PDF viewer
                page_source = self.driver.page_source
                if 'pdf' in new_url.lower() or 'type=application/pdf' in page_source:
                    print("  ✅ PDF viewer detected")
                    
                    # Try to extract PDF URL
                    if 'embed' in page_source or 'iframe' in page_source:
                        # Look for embedded PDF
                        try:
                            embed = self.driver.find_element(By.TAG_NAME, 'embed')
                            pdf_url = embed.get_attribute('src')
                            print(f"  PDF URL from embed: {pdf_url}")
                        except:
                            try:
                                iframe = self.driver.find_element(By.TAG_NAME, 'iframe')
                                pdf_url = iframe.get_attribute('src')
                                print(f"  PDF URL from iframe: {pdf_url}")
                            except:
                                pdf_url = new_url
                                print(f"  Using page URL as PDF URL")
                    else:
                        pdf_url = new_url
                    
                    # Download with requests
                    if pdf_url:
                        self.download_pdf_with_requests(ms_id, pdf_url)
                
                # Close window and return
                self.driver.close()
                self.driver.switch_to.window(main_window)
            
            # Check for direct download
            new_files = set(self.download_dir.glob('*')) - initial_files
            if new_files:
                for f in new_files:
                    print(f"  ✅ Downloaded: {f.name} ({f.stat().st_size} bytes)")
                    self.verify_pdf(f)
            
            # Strategy 2: Extract URL from onclick
            if onclick and 'window.open' in onclick:
                print("\n  Strategy 2: Extract URL from onclick")
                url_match = re.search(r"window\.open\('([^']+)'", onclick)
                if url_match:
                    pdf_url = url_match.group(1)
                    if not pdf_url.startswith('http'):
                        pdf_url = f"http://sicon.siam.org{pdf_url}"
                    
                    print(f"  Extracted URL: {pdf_url}")
                    self.download_pdf_with_requests(ms_id, pdf_url)
    
    def download_pdf_with_requests(self, ms_id: str, url: str):
        """Download PDF using requests"""
        print(f"\n  📥 Downloading with requests: {ms_id}")
        
        try:
            # Add headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': 'http://sicon.siam.org'
            }
            
            response = self.session.get(url, headers=headers, stream=True, timeout=30)
            print(f"  Status: {response.status_code}")
            print(f"  Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
            
            if response.status_code == 200:
                # Check if it's a PDF
                content_sample = response.content[:10]
                
                if content_sample.startswith(b'%PDF'):
                    # Save PDF
                    pdf_path = self.download_dir / f"{ms_id}_requests.pdf"
                    with open(pdf_path, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"  ✅ Saved PDF: {pdf_path.name} ({pdf_path.stat().st_size} bytes)")
                    
                    self.results.append({
                        'manuscript_id': ms_id,
                        'method': 'requests',
                        'success': True,
                        'file': str(pdf_path),
                        'size': pdf_path.stat().st_size
                    })
                else:
                    print(f"  ❌ Not a PDF. Content starts with: {content_sample}")
                    
                    # Save for analysis
                    debug_path = self.output_dir / f"{ms_id}_response.bin"
                    with open(debug_path, 'wb') as f:
                        f.write(response.content[:5000])
                    
                    # Check if HTML
                    if b'<html' in response.content[:1000].lower():
                        print("  Response is HTML - likely authentication required")
                        html_path = self.output_dir / f"{ms_id}_response.html"
                        with open(html_path, 'w') as f:
                            f.write(response.text)
                    
                    self.results.append({
                        'manuscript_id': ms_id,
                        'method': 'requests',
                        'success': False,
                        'error': 'Not a PDF'
                    })
            else:
                self.results.append({
                    'manuscript_id': ms_id,
                    'method': 'requests',
                    'success': False,
                    'error': f'HTTP {response.status_code}'
                })
                
        except Exception as e:
            print(f"  ❌ Download error: {e}")
            self.results.append({
                'manuscript_id': ms_id,
                'method': 'requests',
                'success': False,
                'error': str(e)
            })
    
    def verify_pdf(self, file_path: Path):
        """Verify if file is a valid PDF"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(10)
                
            if header.startswith(b'%PDF'):
                print(f"  ✅ Valid PDF: {file_path.name}")
                return True
            else:
                print(f"  ❌ Not a PDF. Header: {header}")
                return False
        except Exception as e:
            print(f"  ❌ Verification error: {e}")
            return False
    
    def run_test(self):
        """Run the full test"""
        print("🚀 Starting working PDF download test")
        
        try:
            self.setup_driver()
            
            if not self.authenticate():
                print("❌ Authentication failed")
                return
            
            if not self.navigate_to_manuscripts():
                print("❌ Navigation failed")
                return
            
            self.analyze_pdf_links()
            
            # Save results
            results_path = self.output_dir / 'results.json'
            with open(results_path, 'w') as f:
                json.dump(self.results, f, indent=2)
            
            print(f"\n✅ Test complete. Results saved to: {self.output_dir}")
            
            # Summary
            print("\n📊 Summary:")
            successful = [r for r in self.results if r.get('success')]
            print(f"  Successful downloads: {len(successful)}")
            print(f"  Failed downloads: {len(self.results) - len(successful)}")
            
        except Exception as e:
            print(f"❌ Fatal error: {e}")
        finally:
            self.driver.quit()


if __name__ == "__main__":
    downloader = WorkingPDFDownloader()
    downloader.run_test()