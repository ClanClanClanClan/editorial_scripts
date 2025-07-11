#!/usr/bin/env python3
"""
Fixed SIAM extraction - properly handles authentication and navigation
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
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup


class FixedSIAMExtractor:
    """Fixed SIAM extractor with proper authentication and navigation."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.main_window = None
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_fixed_{timestamp}')
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.download_dir = self.output_dir / 'temp_downloads'
        self.download_dir.mkdir(exist_ok=True)
        
        self.dirs = {
            'manuscripts': self.output_dir / 'manuscripts',
            'cover_letters': self.output_dir / 'cover_letters',
            'reports': self.output_dir / 'reports',
            'data': self.output_dir / 'data',
            'screenshots': self.output_dir / 'screenshots'
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(exist_ok=True)
        
        print(f"📁 Output directory: {self.output_dir}")
    
    def setup_driver(self, headless=False):
        """Setup Chrome WebDriver with proper configuration."""
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument('--headless')
        
        # Download configuration
        prefs = {
            "download.default_directory": str(self.download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": True,
            "safebrowsing_for_trusted_sources_enabled": False
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Additional options for stability
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Enable downloads in headless mode
        if headless:
            self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
                "behavior": "allow",
                "downloadPath": str(self.download_dir)
            })
        
        self.wait = WebDriverWait(self.driver, 30)
        self.driver.implicitly_wait(10)
        
        print("✅ Chrome WebDriver initialized")
    
    def save_screenshot(self, name):
        """Save screenshot for debugging."""
        try:
            path = self.dirs['screenshots'] / f"{name}.png"
            self.driver.save_screenshot(str(path))
            print(f"📸 Screenshot: {name}.png")
        except:
            pass
    
    def remove_popups(self):
        """Remove cookie banners and popups."""
        try:
            self.driver.execute_script("""
                // Remove cookie layers
                ['#cookie-policy-layer-bg', '#cookie-policy-layer', '.cc-banner', '.cookie-banner'].forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => el.remove());
                });
                
                // Click continue buttons
                ['#continue-btn', '.accept-cookies', '.agree-button'].forEach(sel => {
                    var btn = document.querySelector(sel);
                    if (btn) btn.click();
                });
                
                // Remove overlays
                document.querySelectorAll('[style*="z-index: 100"]').forEach(el => {
                    if (el.style.position === 'fixed') el.remove();
                });
            """)
        except:
            pass
    
    def authenticate_sicon(self):
        """Authenticate with SICON using ORCID."""
        print("\n🔐 Authenticating with SICON...")
        
        self.driver.get("http://sicon.siam.org")
        time.sleep(3)
        self.main_window = self.driver.current_window_handle
        
        self.remove_popups()
        self.save_screenshot("01_sicon_home")
        
        # Check if we're on the login page or already authenticated
        page_source = self.driver.page_source.lower()
        
        # If we see a logout link, we're authenticated
        if "logout" in page_source and "login" not in page_source:
            print("✅ Already authenticated!")
            return True
        
        # If we see "Welcome to SIAM Journal" with login form, we need to authenticate
        if "welcome to siam journal" in page_source and "please log in" in page_source:
            print("   Need to authenticate via ORCID")
            
            try:
                # Find and click ORCID link
                orcid_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'orcid') or contains(@href, 'sso_site_redirect')]")
                
                if not orcid_links:
                    # Try clicking the ORCID icon
                    orcid_imgs = self.driver.find_elements(By.XPATH, "//img[@title='ORCID']")
                    if orcid_imgs:
                        orcid_parent = orcid_imgs[0].find_element(By.XPATH, "..")
                        if orcid_parent.tag_name == 'a':
                            orcid_links = [orcid_parent]
                
                if not orcid_links:
                    print("❌ No ORCID login link found")
                    return False
                
                print("   Found ORCID link, clicking...")
                # Try clicking with JavaScript
                self.driver.execute_script("arguments[0].click();", orcid_links[0])
                
                # Wait for ORCID page
                time.sleep(5)
                
                # Check if we're on ORCID
                if 'orcid.org' not in self.driver.current_url:
                    print(f"❌ Did not navigate to ORCID. Current URL: {self.driver.current_url}")
                    return False
                
                print("   ✅ Navigated to ORCID")
                self.save_screenshot("02_orcid_login")
                
                # Fill ORCID credentials
                try:
                    username = self.wait.until(EC.presence_of_element_located((By.ID, "username-input")))
                    username.clear()
                    username.send_keys("0000-0002-9364-0124")
                    
                    password = self.driver.find_element(By.ID, "password")
                    password.clear()
                    password.send_keys("Hioupy0042%")
                    
                    # Submit
                    password.send_keys(Keys.RETURN)
                    
                    print("   ⏳ Waiting for authentication...")
                    
                    # Wait for redirect back to SICON
                    timeout = time.time() + 30
                    while time.time() < timeout:
                        current_url = self.driver.current_url
                        if 'sicon.siam.org' in current_url and 'orcid.org' not in current_url:
                            print("   ✅ Successfully authenticated and redirected!")
                            time.sleep(3)
                            self.save_screenshot("03_authenticated")
                            return True
                        time.sleep(1)
                    
                    print("❌ Authentication timeout")
                    return False
                    
                except Exception as e:
                    print(f"❌ Error during ORCID login: {e}")
                    return False
                
            except Exception as e:
                print(f"❌ Error clicking ORCID link: {e}")
                return False
        
        # If we get here, we might be on a different page
        print(f"❌ Unexpected page state. Current URL: {self.driver.current_url}")
        return False
    
    def navigate_to_manuscripts(self):
        """Navigate to manuscript listings."""
        print("\n📋 Navigating to manuscripts...")
        
        # First, try to navigate to the home page to see folders
        current_url = self.driver.current_url
        if 'home' not in current_url:
            home_url = "http://sicon.siam.org/cgi-bin/main.plex?form_type=home"
            print(f"   Going to home page: {home_url}")
            self.driver.get(home_url)
            time.sleep(3)
        
        self.remove_popups()
        self.save_screenshot("04_home_page")
        
        # Look for manuscript folders in the page
        page_source = self.driver.page_source
        
        # Strategy 1: Look for "Under Review" or "All Pending" folders
        folder_patterns = [
            ("Under Review", r"folder_id=1400"),
            ("All Pending Manuscripts", r"folder_id=1800"),
            ("Awaiting Associate Editor Recommendation", r"folder_id=1500")
        ]
        
        for folder_name, pattern in folder_patterns:
            print(f"   Looking for {folder_name}...")
            
            # Try to find links with the folder pattern
            folder_links = self.driver.find_elements(By.XPATH, f"//a[contains(@href, '{pattern}')]")
            
            if folder_links:
                print(f"   ✅ Found {folder_name} folder")
                try:
                    folder_links[0].click()
                    time.sleep(3)
                    self.save_screenshot(f"05_{folder_name.replace(' ', '_').lower()}")
                    return True
                except Exception as e:
                    print(f"   ❌ Error clicking {folder_name}: {e}")
                    continue
        
        # Strategy 2: Look for manuscript links directly
        print("   Looking for manuscript links directly...")
        
        # Look for links that contain manuscript IDs (M followed by numbers)
        manuscript_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'M') and string-length(text()) > 3]")
        
        if manuscript_links:
            print(f"   ✅ Found {len(manuscript_links)} manuscript links directly")
            return True
        
        print("❌ Could not find manuscript folders or links")
        return False
    
    def extract_manuscripts(self):
        """Extract manuscript data from current page."""
        print("\n📊 Extracting manuscripts...")
        
        manuscripts = []
        
        # Get page source for parsing
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Method 1: Look for manuscript links that match the pattern
        ms_pattern = re.compile(r'M\d{6}')
        
        # Find all links
        all_links = self.driver.find_elements(By.TAG_NAME, "a")
        
        for link in all_links:
            try:
                link_text = link.text.strip()
                href = link.get_attribute('href')
                
                if not link_text or not href:
                    continue
                
                # Check if this looks like a manuscript link
                ms_match = ms_pattern.search(link_text)
                if ms_match:
                    ms_id = ms_match.group()
                    
                    # Skip if we already have this manuscript
                    if any(m['manuscript_id'] == ms_id for m in manuscripts):
                        continue
                    
                    print(f"   📄 Found manuscript: {ms_id}")
                    
                    # Extract info from the link and surrounding context
                    ms_data = {
                        'manuscript_id': ms_id,
                        'url': href,
                        'link_text': link_text,
                        'title': '',
                        'authors': '',
                        'referees': [],
                        'files': {'manuscript': None, 'cover_letter': None, 'reports': []}
                    }
                    
                    # Try to extract additional info from the link context
                    parent = link.find_element(By.XPATH, "..")
                    parent_text = parent.text
                    
                    # Look for author names in parentheses
                    author_match = re.search(r'\(([^)]+)\)', parent_text)
                    if author_match:
                        ms_data['authors'] = author_match.group(1)
                    
                    manuscripts.append(ms_data)
                    
            except Exception as e:
                continue
        
        # Method 2: If no manuscripts found, try table parsing
        if not manuscripts:
            print("   Trying table extraction...")
            
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            
            for table in tables:
                table_html = table.get_attribute('innerHTML')
                if not any(ms_id in table_html for ms_id in ['M172', 'M173', 'M176']):
                    continue
                
                print("   ✅ Found manuscript table")
                
                # Parse table rows
                rows = table.find_elements(By.TAG_NAME, "tr")
                
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if not cells:
                        continue
                    
                    first_cell_text = cells[0].text.strip()
                    
                    # Check if this is a manuscript row
                    if ms_pattern.match(first_cell_text):
                        ms_id = first_cell_text
                        
                        # Find the link
                        links = cells[0].find_elements(By.TAG_NAME, "a")
                        if links:
                            ms_data = {
                                'manuscript_id': ms_id,
                                'url': links[0].get_attribute('href'),
                                'title': cells[1].text.strip() if len(cells) > 1 else '',
                                'authors': cells[2].text.strip() if len(cells) > 2 else '',
                                'referees': [],
                                'files': {'manuscript': None, 'cover_letter': None, 'reports': []}
                            }
                            
                            manuscripts.append(ms_data)
                            print(f"   📄 Found manuscript in table: {ms_id}")
        
        print(f"   ✅ Total manuscripts found: {len(manuscripts)}")
        return manuscripts
    
    def extract_detailed_manuscript_info(self, manuscript):
        """Extract detailed information for a specific manuscript."""
        ms_id = manuscript['manuscript_id']
        print(f"\n📋 Processing {ms_id} in detail...")
        
        # Navigate to manuscript
        self.driver.get(manuscript['url'])
        time.sleep(3)
        self.remove_popups()
        
        # Parse the manuscript page
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Extract title and other details from tables
        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                cells = row.find_all(['th', 'td'])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    
                    if 'title' in label:
                        manuscript['title'] = value
                        print(f"   Title: {value[:50]}...")
                    elif 'author' in label and 'corresponding' not in label:
                        manuscript['authors'] = value
                    elif 'corresponding editor' in label:
                        manuscript['corresponding_editor'] = value
                    elif 'associate editor' in label:
                        manuscript['associate_editor'] = value
                    elif 'submission date' in label or 'submitted' in label:
                        manuscript['submission_date'] = value
                    elif 'current stage' in label or 'status' in label:
                        manuscript['current_stage'] = value
        
        # Extract referees
        referees = []
        referee_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'dump_person_record') or contains(@href, 'person_id')]")
        
        for link in referee_links:
            try:
                referee_name = link.text.strip()
                if not referee_name or len(referee_name) < 2:
                    continue
                
                # Skip if this is an editor, not a referee
                parent_text = link.find_element(By.XPATH, "..").text.lower()
                if 'editor' in parent_text and 'referee' not in parent_text:
                    continue
                
                print(f"   👤 Found referee: {referee_name}")
                
                referee_data = {
                    'name': referee_name,
                    'full_name': referee_name,
                    'email': None
                }
                
                # Try to get detailed info by clicking the link
                try:
                    href = link.get_attribute('href')
                    
                    # Open in new tab
                    self.driver.execute_script("window.open('');")
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    self.driver.get(href)
                    time.sleep(2)
                    
                    # Look for email
                    email_links = self.driver.find_elements(By.XPATH, "//a[starts-with(@href, 'mailto:')]")
                    if email_links:
                        referee_data['email'] = email_links[0].get_attribute('href').replace('mailto:', '')
                        print(f"      📧 Email: {referee_data['email']}")
                    
                    # Look for full name
                    page_title = self.driver.title
                    if referee_name.split()[0].lower() in page_title.lower():
                        name_part = page_title.split('-')[0].strip()
                        if len(name_part) > len(referee_name):
                            referee_data['full_name'] = name_part
                            print(f"      👤 Full name: {name_part}")
                    
                    # Close tab
                    self.driver.close()
                    self.driver.switch_to.window(self.main_window)
                    
                except Exception as e:
                    print(f"      ❌ Error getting referee details: {e}")
                    # Make sure we're back on main window
                    if len(self.driver.window_handles) > 1:
                        self.driver.close()
                    self.driver.switch_to.window(self.main_window)
                
                referees.append(referee_data)
                
            except Exception as e:
                continue
        
        manuscript['referees'] = referees
        print(f"   ✅ Found {len(referees)} referees")
        
        return manuscript
    
    def run(self):
        """Run the complete extraction."""
        print("\n🚀 STARTING FIXED SIAM EXTRACTION")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        all_manuscripts = []
        
        try:
            # Setup driver
            self.setup_driver(headless=False)
            
            # Authenticate
            if not self.authenticate_sicon():
                print("❌ Authentication failed")
                return
            
            # Navigate to manuscripts
            if not self.navigate_to_manuscripts():
                print("⚠️  Navigation to manuscripts failed, trying direct extraction...")
            
            # Extract manuscripts
            manuscripts = self.extract_manuscripts()
            
            if not manuscripts:
                print("❌ No manuscripts found")
                return
            
            # Process each manuscript in detail
            for ms in manuscripts:
                try:
                    detailed_ms = self.extract_detailed_manuscript_info(ms)
                    all_manuscripts.append(detailed_ms)
                except Exception as e:
                    print(f"❌ Error processing {ms['manuscript_id']}: {e}")
                    all_manuscripts.append(ms)  # Keep basic data
            
            # Save results
            results = {
                'extraction_time': datetime.now().isoformat(),
                'total_manuscripts': len(all_manuscripts),
                'manuscripts': all_manuscripts
            }
            
            with open(self.dirs['data'] / 'extraction_results.json', 'w') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            # Create summary
            summary_path = self.dirs['data'] / 'extraction_summary.txt'
            with open(summary_path, 'w') as f:
                f.write(f"SIAM Extraction Summary\n")
                f.write(f"======================\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Manuscripts: {len(all_manuscripts)}\n\n")
                
                for ms in all_manuscripts:
                    f.write(f"\n{ms['manuscript_id']}\n")
                    f.write(f"  Title: {ms.get('title', 'N/A')}\n")
                    f.write(f"  Authors: {ms.get('authors', 'N/A')}\n")
                    f.write(f"  Referees: {len(ms.get('referees', []))}\n")
                    for ref in ms.get('referees', []):
                        f.write(f"    - {ref['full_name']}")
                        if ref.get('email'):
                            f.write(f" ({ref['email']})")
                        f.write("\n")
            
            print(f"\n✅ Extraction complete!")
            print(f"📁 Found {len(all_manuscripts)} manuscripts")
            print(f"📄 Results saved to: {self.dirs['data']}")
            
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
            self.save_screenshot("fatal_error")
        
        finally:
            if self.driver:
                print("\n🔄 Closing browser...")
                self.driver.quit()


def main():
    extractor = FixedSIAMExtractor()
    extractor.run()


if __name__ == "__main__":
    main()
