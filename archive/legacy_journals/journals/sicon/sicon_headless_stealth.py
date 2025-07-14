#!/usr/bin/env python3
"""
SICON Headless Stealth - Full extraction with anti-detection measures
"""

import os
import re
import time
import json
import shutil
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()


class SICONStealthExtractor:
    """SICON extractor with stealth mode for headless operation."""
    
    def __init__(self):
        self.output_dir = Path(f'./sicon_stealth_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.dirs = {
            'pdfs': self.output_dir / 'pdfs',
            'data': self.output_dir / 'data',
            'debug': self.output_dir / 'debug'
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(exist_ok=True)
        
        self.main_window = None
        self.manuscripts = []
        
        print(f"📁 Output directory: {self.output_dir}")
    
    def setup_driver(self):
        """Setup Chrome driver with stealth settings."""
        chrome_options = Options()
        
        # Stealth settings to avoid detection
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Headless mode
        chrome_options.add_argument('--headless=new')  # New headless mode
        chrome_options.add_argument('--window-size=1920,1080')
        
        # Other settings
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Configure downloads
        self.temp_download = self.output_dir / 'temp_downloads'
        self.temp_download.mkdir(exist_ok=True)
        
        prefs = {
            "download.default_directory": str(self.temp_download),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)
        
        # Execute stealth JavaScript
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Enable downloads in headless mode
        self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": str(self.temp_download)
        })
        
        print("✅ Chrome driver initialized (STEALTH HEADLESS MODE)")
    
    def wait_for_page_load(self, timeout=30):
        """Wait for page to fully load."""
        time.sleep(3)  # Initial wait
        try:
            # Wait for body to be present
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Additional wait for dynamic content
            time.sleep(2)
            
            # Check if we're on a Cloudflare challenge page
            if "Just a moment" in self.driver.title:
                print("⏳ Cloudflare challenge detected, waiting...")
                time.sleep(10)  # Give Cloudflare time to process
                
                # Check again
                if "Just a moment" not in self.driver.title:
                    print("✅ Passed Cloudflare challenge")
                else:
                    print("⚠️  Still on Cloudflare page")
                    
        except Exception as e:
            print(f"⚠️  Page load timeout: {e}")
    
    def authenticate(self) -> bool:
        """Authenticate using ORCID."""
        print("\n🔐 Authenticating...")
        
        try:
            # Navigate to SICON
            print("  📍 Loading SICON homepage...")
            self.driver.get("http://sicon.siam.org")
            self.wait_for_page_load()
            self.main_window = self.driver.current_window_handle
            
            # Save initial state
            self.driver.save_screenshot(str(self.dirs['debug'] / 'initial_page.png'))
            
            # Check if already authenticated
            if 'associate editor tasks' in self.driver.page_source.lower():
                print("✅ Already authenticated!")
                return True
            
            # Dismiss privacy notification
            try:
                privacy_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@value='Continue']"))
                )
                privacy_button.click()
                print("✅ Clicked privacy notification")
                time.sleep(3)
            except:
                print("  ℹ️  No privacy notification found")
            
            # Try multiple methods to find ORCID link
            orcid_selectors = [
                (By.XPATH, "//a[contains(@href, 'orcid')]"),
                (By.XPATH, "//a[contains(text(), 'ORCID')]"),
                (By.XPATH, "//a[contains(text(), 'Sign in')]"),
                (By.XPATH, "//img[contains(@src, 'orcid')]/parent::a"),
                (By.CSS_SELECTOR, "a[href*='orcid']")
            ]
            
            orcid_link = None
            for by, selector in orcid_selectors:
                try:
                    orcid_link = self.driver.find_element(by, selector)
                    print(f"✅ Found ORCID link with selector: {selector}")
                    break
                except:
                    continue
            
            if not orcid_link:
                print("❌ Could not find ORCID link")
                self.driver.save_screenshot(str(self.dirs['debug'] / 'no_orcid_link.png'))
                return False
            
            # Click ORCID link
            self.driver.execute_script("arguments[0].click();", orcid_link)
            print("✅ Clicked ORCID link")
            time.sleep(5)
            
            # Handle ORCID authentication
            if 'orcid.org' in self.driver.current_url:
                print("📝 On ORCID page")
                
                # Accept cookies
                try:
                    accept_cookies = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept All Cookies')]"))
                    )
                    accept_cookies.click()
                    print("✅ Accepted cookies")
                    time.sleep(3)
                except:
                    pass
                
                # Fill credentials
                username = os.getenv('ORCID_USER', '0000-0002-9364-0124')
                password = os.getenv('ORCID_PASS', 'Hioupy0042%')
                
                username_field = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Email or 16-digit ORCID iD']"))
                )
                password_field = self.driver.find_element(By.XPATH, "//input[@placeholder='Your ORCID password']")
                
                username_field.clear()
                username_field.send_keys(username)
                password_field.clear()
                password_field.send_keys(password)
                
                # Click sign in
                signin_button = self.driver.find_element(By.XPATH, "//button[contains(., 'Sign in to ORCID')]")
                signin_button.click()
                print("✅ Clicked sign in")
                
                time.sleep(10)
            
            # Handle post-auth privacy notification
            try:
                privacy_button = self.driver.find_element(By.XPATH, "//input[@value='Continue']")
                privacy_button.click()
                print("✅ Clicked post-auth privacy")
                time.sleep(3)
            except:
                pass
            
            # Verify authentication
            if 'associate editor tasks' in self.driver.page_source.lower():
                print("✅ Authentication successful!")
                return True
            else:
                print("❌ Authentication failed")
                self.driver.save_screenshot(str(self.dirs['debug'] / 'auth_failed.png'))
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            self.driver.save_screenshot(str(self.dirs['debug'] / 'auth_error.png'))
            return False
    
    def navigate_to_manuscripts(self) -> bool:
        """Navigate to All Pending Manuscripts."""
        print("\n📋 Navigating to manuscripts...")
        
        try:
            # Find the "4 AE" link with folder_id=1800
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
    
    def parse_status(self, status_text: str) -> str:
        """Parse referee status from text."""
        status_lower = status_text.lower().strip()
        
        if 'declined' in status_lower:
            return 'Declined'
        elif 'accepted' in status_lower:
            return 'Accepted'
        elif 'report' in status_lower and 'submitted' in status_lower:
            return 'Report Submitted'
        elif 'overdue' in status_lower:
            return 'Overdue'
        elif 'invited' in status_lower:
            return 'Invited'
        else:
            return 'Unknown'
    
    def parse_manuscripts_table(self):
        """Parse manuscripts table."""
        print("\n📊 Parsing manuscripts table...")
        
        # Save page source
        with open(self.dirs['debug'] / 'manuscripts_table.html', 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Find the main data table
        tables = soup.find_all('table')
        data_table = None
        
        for table in tables:
            if re.search(r'M\d{6}', str(table)):
                data_table = table
                break
        
        if not data_table:
            print("❌ Could not find manuscripts table")
            return
        
        print("✅ Found manuscripts table")
        
        # Parse table rows
        rows = data_table.find_all('tr')
        
        for row in rows:
            # Skip if no manuscript ID
            if not re.search(r'M\d{6}', str(row)):
                continue
            
            cells = row.find_all('td')
            if len(cells) < 8:
                continue
            
            # Extract manuscript ID
            ms_id_match = re.search(r'(M\d{6})', cells[0].get_text())
            if not ms_id_match:
                continue
            
            ms_id = ms_id_match.group(1)
            print(f"\n🔍 Processing manuscript {ms_id}")
            
            manuscript = {
                'manuscript_id': ms_id,
                'title': cells[1].get_text(strip=True),
                'corresponding_editor': cells[2].get_text(strip=True),
                'associate_editor': cells[3].get_text(strip=True),
                'submitted': cells[4].get_text(strip=True),
                'days_in_system': cells[5].get_text(strip=True),
                'referees': [],
                'pdf_downloaded': False
            }
            
            # Extract referee names from column 6
            referee_links = cells[6].find_all('a')
            referee_names = []
            
            # Skip the first link if it's the manuscript author
            start_idx = 1 if len(referee_links) > 1 and not cells[6].find('br') else 0
            
            for link in referee_links[start_idx:]:
                name = link.get_text(strip=True)
                if name and name not in ['s Assigned', 'All Referees']:
                    referee_names.append(name)
            
            # Extract statuses from column 7
            status_html = str(cells[7])
            status_texts = []
            
            # Split by <br> and clean
            for part in status_html.split('<br>'):
                clean_text = re.sub(r'<[^>]+>', '', part).strip()
                if clean_text and clean_text != '&nbsp;':
                    status_texts.append(clean_text)
            
            # Extract due dates from column 8
            due_dates = []
            if len(cells) > 8:
                due_html = str(cells[8])
                for part in due_html.split('<br>'):
                    clean_text = re.sub(r'<[^>]+>', '', part).strip()
                    if clean_text and clean_text != '&nbsp;':
                        due_dates.append(clean_text)
                    else:
                        due_dates.append(None)
            
            # Match referees with their statuses
            for i, name in enumerate(referee_names):
                status = self.parse_status(status_texts[i]) if i < len(status_texts) else 'Unknown'
                due_date = due_dates[i] if i < len(due_dates) else None
                
                referee = {
                    'name': name,
                    'email': None,
                    'status': status,
                    'due_date': due_date
                }
                
                print(f"  👤 {name}: {status}", end="")
                if due_date:
                    print(f" (due: {due_date})", end="")
                print()
                
                manuscript['referees'].append(referee)
            
            self.manuscripts.append(manuscript)
    
    def extract_referee_emails(self):
        """Extract referee emails."""
        print("\n📧 Extracting referee emails...")
        
        emails_found = 0
        for manuscript in self.manuscripts:
            for referee in manuscript['referees']:
                if referee['email']:
                    continue
                
                try:
                    # Find referee link
                    referee_links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{referee['name']}')]")
                    
                    if not referee_links:
                        continue
                    
                    # Click the first matching link
                    self.driver.execute_script("arguments[0].click();", referee_links[0])
                    time.sleep(3)
                    
                    # Check if new window opened
                    if len(self.driver.window_handles) > 1:
                        # Switch to new window
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                        time.sleep(2)
                        
                        # Extract email
                        profile_html = self.driver.page_source
                        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', profile_html)
                        if email_match:
                            referee['email'] = email_match.group()
                            emails_found += 1
                        
                        # Close window
                        self.driver.close()
                        self.driver.switch_to.window(self.main_window)
                        time.sleep(1)
                    
                except Exception as e:
                    # Make sure we're back in main window
                    if len(self.driver.window_handles) > 1:
                        self.driver.close()
                        self.driver.switch_to.window(self.main_window)
        
        print(f"  ✅ Found {emails_found} email addresses")
    
    def download_pdfs(self):
        """Download manuscript PDFs."""
        print("\n📥 Downloading PDFs...")
        
        pdfs_downloaded = 0
        for manuscript in self.manuscripts:
            ms_id = manuscript['manuscript_id']
            
            try:
                # Clear temp download folder
                for f in self.temp_download.glob('*'):
                    f.unlink()
                
                # Find and click manuscript link
                ms_link = self.driver.find_element(By.XPATH, f"//a[contains(text(), '{ms_id}')]")
                self.driver.execute_script("arguments[0].click();", ms_link)
                time.sleep(3)
                
                # Check if new window opened
                if len(self.driver.window_handles) > 1:
                    # Switch to manuscript view window
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    time.sleep(2)
                    
                    # Look for PDF links
                    pdf_patterns = [
                        "//a[contains(text(), 'PDF')]",
                        "//a[contains(text(), 'Download PDF')]",
                        "//a[contains(@href, '.pdf')]"
                    ]
                    
                    for pattern in pdf_patterns:
                        try:
                            pdf_links = self.driver.find_elements(By.XPATH, pattern)
                            if pdf_links:
                                # Get initial file count
                                initial_files = set(self.temp_download.glob('*'))
                                
                                # Click the first PDF link
                                self.driver.execute_script("arguments[0].click();", pdf_links[0])
                                time.sleep(5)
                                
                                # Check for new files
                                new_files = set(self.temp_download.glob('*')) - initial_files
                                
                                if new_files:
                                    for new_file in new_files:
                                        # Verify it's a PDF
                                        with open(new_file, 'rb') as f:
                                            header = f.read(4)
                                        
                                        if header == b'%PDF':
                                            dest = self.dirs['pdfs'] / f"{ms_id}.pdf"
                                            shutil.move(str(new_file), str(dest))
                                            manuscript['pdf_downloaded'] = True
                                            pdfs_downloaded += 1
                                            break
                                
                                if manuscript['pdf_downloaded']:
                                    break
                        except:
                            continue
                    
                    # Close window
                    self.driver.close()
                    self.driver.switch_to.window(self.main_window)
                    time.sleep(1)
                    
            except Exception as e:
                # Make sure we're back in main window
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.main_window)
        
        print(f"  ✅ Downloaded {pdfs_downloaded} PDFs")
    
    def save_results(self):
        """Save extraction results."""
        # Calculate statistics
        total_referees = sum(len(m['referees']) for m in self.manuscripts)
        status_counts = {}
        emails_found = 0
        
        for ms in self.manuscripts:
            for ref in ms['referees']:
                status = ref['status']
                status_counts[status] = status_counts.get(status, 0) + 1
                if ref['email']:
                    emails_found += 1
        
        results = {
            'extraction_time': datetime.now().isoformat(),
            'mode': 'STEALTH_HEADLESS',
            'total_manuscripts': len(self.manuscripts),
            'total_referees': total_referees,
            'referees_with_emails': emails_found,
            'referee_status_breakdown': status_counts,
            'pdfs_downloaded': sum(1 for m in self.manuscripts if m['pdf_downloaded']),
            'manuscripts': self.manuscripts
        }
        
        # Save JSON
        json_path = self.dirs['data'] / 'extraction_results.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Generate report
        report_path = self.dirs['data'] / 'extraction_report.txt'
        with open(report_path, 'w') as f:
            f.write("SICON Extraction Report (Stealth Headless)\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Extraction Time: {results['extraction_time']}\n")
            f.write(f"Total Manuscripts: {results['total_manuscripts']}\n")
            f.write(f"Total Referees: {total_referees}\n")
            f.write(f"Emails Found: {emails_found}/{total_referees} ({emails_found/total_referees*100:.1f}%)\n")
            f.write(f"PDFs Downloaded: {results['pdfs_downloaded']}/{results['total_manuscripts']}\n\n")
            
            if status_counts:
                f.write("Referee Status Breakdown:\n")
                for status, count in sorted(status_counts.items()):
                    percentage = (count / total_referees * 100) if total_referees > 0 else 0
                    f.write(f"  {status}: {count} ({percentage:.1f}%)\n")
                f.write("\n")
            
            f.write("=" * 60 + "\n\n")
            
            for ms in self.manuscripts:
                f.write(f"Manuscript {ms['manuscript_id']}\n")
                f.write(f"  Title: {ms['title']}\n")
                f.write(f"  PDF: {'✅' if ms['pdf_downloaded'] else '❌'}\n")
                f.write(f"  Referees: {len(ms['referees'])}\n")
                
                for ref in ms['referees']:
                    f.write(f"    - {ref['name']} ({ref['status']})")
                    if ref['email']:
                        f.write(f" - {ref['email']}")
                    if ref['due_date']:
                        f.write(f" - Due: {ref['due_date']}")
                    f.write("\n")
                f.write("\n")
        
        print(f"\n📊 Results saved to: {self.output_dir}")
    
    def run(self):
        """Run the extraction."""
        try:
            self.setup_driver()
            
            # Try multiple times if Cloudflare blocks
            max_attempts = 3
            for attempt in range(max_attempts):
                if self.authenticate():
                    break
                elif attempt < max_attempts - 1:
                    print(f"\n🔄 Retrying authentication (attempt {attempt + 2}/{max_attempts})...")
                    time.sleep(5)
                else:
                    raise Exception("Authentication failed after all attempts")
            
            if not self.navigate_to_manuscripts():
                raise Exception("Navigation failed")
            
            self.parse_manuscripts_table()
            self.extract_referee_emails()
            self.download_pdfs()
            self.save_results()
            
            print("\n🎉 Extraction complete!")
            
            # Print summary
            total_refs = sum(len(m['referees']) for m in self.manuscripts)
            emails_found = sum(1 for m in self.manuscripts for r in m['referees'] if r['email'])
            pdfs = sum(1 for m in self.manuscripts if m['pdf_downloaded'])
            
            print(f"\n📊 Summary:")
            print(f"  Manuscripts: {len(self.manuscripts)}")
            print(f"  Referees: {total_refs}")
            print(f"  Emails: {emails_found}/{total_refs}")
            print(f"  PDFs: {pdfs}/{len(self.manuscripts)}")
            
            return self.manuscripts
            
        except Exception as e:
            print(f"❌ Fatal error: {e}")
            raise
        finally:
            if hasattr(self, 'driver'):
                self.driver.quit()


def main():
    """Main execution."""
    print("🚀 Starting SICON Stealth Extraction (HEADLESS)")
    print("Using anti-detection measures\n")
    
    extractor = SICONStealthExtractor()
    try:
        results = extractor.run()
        return results
    except Exception as e:
        print(f"\n❌ Extraction failed: {e}")
        return None


if __name__ == "__main__":
    main()