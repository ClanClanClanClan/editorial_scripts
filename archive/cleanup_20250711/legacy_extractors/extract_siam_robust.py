#!/usr/bin/env python3
"""
Robust SIAM Extractor - Multiple fallbacks and authentication strategies
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


class RobustSIAMExtractor:
    """Robust SIAM extractor with multiple fallback strategies."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.main_window = None
        self.authenticated = False
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_robust_{timestamp}')
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.download_dir = self.output_dir / 'downloads'
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
        
        # Additional robustness options
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Execute script to hide automation
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Enable downloads
        self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": str(self.download_dir)
        })
        
        self.wait = WebDriverWait(self.driver, 30)
        self.driver.implicitly_wait(10)
        
        print("✅ Chrome WebDriver initialized with robust settings")
    
    def save_screenshot(self, name):
        """Save screenshot for debugging."""
        try:
            path = self.dirs['screenshots'] / f"{name}.png"
            self.driver.save_screenshot(str(path))
            print(f"📸 Screenshot: {name}.png")
        except Exception as e:
            print(f"   Warning: Could not save screenshot {name}: {e}")
    
    def save_page_source(self, name):
        """Save page source for debugging."""
        try:
            path = self.dirs['screenshots'] / f"{name}.html"
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print(f"📄 Page source: {name}.html")
        except Exception as e:
            print(f"   Warning: Could not save page source {name}: {e}")
    
    def robust_click(self, element, description="element"):
        """Robust click with multiple fallback strategies."""
        try:
            # Strategy 1: Normal click
            element.click()
            return True
        except:
            try:
                # Strategy 2: JavaScript click
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except:
                try:
                    # Strategy 3: Action chains
                    ActionChains(self.driver).move_to_element(element).click().perform()
                    return True
                except Exception as e:
                    print(f"   ❌ All click strategies failed for {description}: {e}")
                    return False
    
    def handle_popups_comprehensive(self):
        """Comprehensive popup handling with multiple strategies."""
        try:
            # Strategy 1: Continue buttons
            continue_selectors = [
                "//button[contains(text(), 'Continue')]",
                "//button[@value='Continue']",
                "//input[@value='Continue']",
                "//a[contains(text(), 'Continue')]"
            ]
            
            for selector in continue_selectors:
                try:
                    buttons = self.driver.find_elements(By.XPATH, selector)
                    if buttons:
                        if self.robust_click(buttons[0], "Continue button"):
                            time.sleep(2)
                            print("   ✅ Dismissed popup with Continue button")
                            break
                except:
                    continue
            
            # Strategy 2: JavaScript removal of overlays
            self.driver.execute_script("""
                // Remove known popup elements
                var selectors = [
                    '#cookie-policy-layer-bg', '#cookie-policy-layer', 
                    '.cc-banner', '.cookie-banner', '.modal-overlay',
                    '[role="dialog"]', '.popup', '.notification'
                ];
                
                selectors.forEach(function(sel) {
                    var elements = document.querySelectorAll(sel);
                    elements.forEach(function(el) {
                        el.style.display = 'none';
                        el.remove();
                    });
                });
                
                // Remove fixed position overlays
                var allElements = document.querySelectorAll('*');
                allElements.forEach(function(el) {
                    var style = window.getComputedStyle(el);
                    if (style.position === 'fixed' && 
                        (parseInt(style.zIndex) > 100 || style.zIndex === 'auto')) {
                        if (el.offsetWidth > 200 && el.offsetHeight > 100) {
                            el.style.display = 'none';
                        }
                    }
                });
            """)
            
            # Strategy 3: Press Escape key
            try:
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            except:
                pass
                
        except Exception as e:
            print(f"   Warning: Error in popup handling: {e}")
    
    def check_authentication_status(self):
        """Robust authentication status check."""
        try:
            page_source = self.driver.page_source.lower()
            current_url = self.driver.current_url
            
            # Positive indicators of authentication
            auth_indicators = [
                'logout',
                'associate editor tasks',
                'author tasks',
                'reviewer tasks',
                'all pending manuscripts'
            ]
            
            # Negative indicators (still on login page)
            login_indicators = [
                'please log in',
                'login name',
                'password',
                'welcome to siam journal on control and optimization, please log in'
            ]
            
            auth_score = sum(1 for indicator in auth_indicators if indicator in page_source)
            login_score = sum(1 for indicator in login_indicators if indicator in page_source)
            
            print(f"   Auth indicators: {auth_score}, Login indicators: {login_score}")
            
            if auth_score >= 2 and login_score == 0:
                return True
            elif auth_score > login_score:
                return True
            else:
                return False
                
        except Exception as e:
            print(f"   Error checking auth status: {e}")
            return False
    
    def authenticate_with_fallbacks(self):
        """Authenticate with multiple fallback strategies."""
        print("\n🔐 Starting robust authentication...")
        
        # Strategy 1: Check if already authenticated
        self.driver.get("http://sicon.siam.org")
        time.sleep(3)
        self.main_window = self.driver.current_window_handle
        
        self.handle_popups_comprehensive()
        self.save_screenshot("01_initial_page")
        
        if self.check_authentication_status():
            print("✅ Already authenticated!")
            self.authenticated = True
            return True
        
        print("   Need to authenticate...")
        
        # Strategy 2: ORCID authentication with retries
        for attempt in range(3):
            print(f"   Authentication attempt {attempt + 1}/3")
            
            try:
                # Navigate to fresh login page
                self.driver.get("http://sicon.siam.org")
                time.sleep(3)
                self.handle_popups_comprehensive()
                
                # Find ORCID link with multiple strategies
                orcid_link = None
                
                # Try different ORCID link patterns
                orcid_selectors = [
                    "//a[contains(@href, 'orcid')]",
                    "//a[contains(@href, 'sso_site_redirect')]",
                    "//img[@title='ORCID']/parent::a",
                    "//a[contains(text(), 'ORCID')]"
                ]
                
                for selector in orcid_selectors:
                    try:
                        links = self.driver.find_elements(By.XPATH, selector)
                        if links:
                            orcid_link = links[0]
                            print(f"   Found ORCID link with selector: {selector}")
                            break
                    except:
                        continue
                
                if not orcid_link:
                    print(f"   ❌ No ORCID link found on attempt {attempt + 1}")
                    continue
                
                # Click ORCID link
                if not self.robust_click(orcid_link, "ORCID link"):
                    print(f"   ❌ Could not click ORCID link on attempt {attempt + 1}")
                    continue
                
                time.sleep(5)
                
                # Check if we're on ORCID
                if 'orcid.org' not in self.driver.current_url:
                    print(f"   ❌ Did not reach ORCID on attempt {attempt + 1}")
                    continue
                
                print("   ✅ Reached ORCID login page")
                self.save_screenshot(f"02_orcid_attempt_{attempt + 1}")
                
                # Fill ORCID credentials with retries
                credentials_filled = False
                for cred_attempt in range(2):
                    try:
                        # Wait for and fill username
                        username_field = self.wait.until(
                            EC.presence_of_element_located((By.ID, "username-input"))
                        )
                        username_field.clear()
                        username_field.send_keys("0000-0002-9364-0124")
                        
                        # Fill password
                        password_field = self.driver.find_element(By.ID, "password")
                        password_field.clear()
                        password_field.send_keys("Hioupy0042%")
                        
                        # Submit with multiple strategies
                        try:
                            password_field.send_keys(Keys.RETURN)
                        except:
                            try:
                                submit_btn = self.driver.find_element(By.XPATH, "//button[@type='submit'] | //input[@type='submit']")
                                self.robust_click(submit_btn, "Submit button")
                            except:
                                password_field.send_keys(Keys.RETURN)
                        
                        credentials_filled = True
                        break
                        
                    except Exception as e:
                        print(f"   Credential filling attempt {cred_attempt + 1} failed: {e}")
                        time.sleep(2)
                
                if not credentials_filled:
                    print(f"   ❌ Could not fill credentials on attempt {attempt + 1}")
                    continue
                
                print("   ⏳ Waiting for authentication redirect...")
                
                # Wait for redirect with robust checking
                redirect_timeout = time.time() + 30
                while time.time() < redirect_timeout:
                    current_url = self.driver.current_url
                    
                    # Check if we're back on SICON
                    if 'sicon.siam.org' in current_url and 'orcid.org' not in current_url:
                        time.sleep(3)
                        self.handle_popups_comprehensive()
                        
                        # Robust authentication check
                        if self.check_authentication_status():
                            print(f"   ✅ Authentication successful on attempt {attempt + 1}!")
                            self.authenticated = True
                            self.save_screenshot(f"03_authenticated_attempt_{attempt + 1}")
                            return True
                    
                    time.sleep(1)
                
                print(f"   ❌ Authentication timeout on attempt {attempt + 1}")
                
            except Exception as e:
                print(f"   ❌ Authentication attempt {attempt + 1} failed: {e}")
                
            # Wait before retry
            if attempt < 2:
                print("   Waiting before retry...")
                time.sleep(5)
        
        print("❌ All authentication attempts failed")
        self.save_screenshot("auth_failed_final")
        self.save_page_source("auth_failed_final")
        return False
    
    def navigate_to_table_with_fallbacks(self):
        """Navigate to All Pending Manuscripts table with multiple fallback strategies."""
        print("\n📋 Navigating to All Pending Manuscripts table...")
        
        if not self.authenticated:
            print("❌ Not authenticated, cannot navigate")
            return False
        
        # Strategy 1: Navigate to home and look for links
        for attempt in range(3):
            print(f"   Navigation attempt {attempt + 1}/3")
            
            try:
                # Go to home page
                self.driver.get("http://sicon.siam.org/cgi-bin/main.plex?form_type=home")
                time.sleep(3)
                self.handle_popups_comprehensive()
                self.save_screenshot(f"04_home_attempt_{attempt + 1}")
                
                # Look for "All Pending" links with various strategies
                pending_link_selectors = [
                    "//a[contains(text(), 'All Pending Manuscripts')]",
                    "//a[contains(text(), 'All Pending')]",
                    "//a[contains(text(), 'Pending Manuscripts')]",
                    "//a[contains(@href, 'folder_id=1800')]",
                    "//a[contains(@href, 'is_open_1800')]"
                ]
                
                link_found = False
                for selector in pending_link_selectors:
                    try:
                        links = self.driver.find_elements(By.XPATH, selector)
                        if links:
                            print(f"   Found link with selector: {selector}")
                            if self.robust_click(links[0], "All Pending link"):
                                time.sleep(5)
                                self.handle_popups_comprehensive()
                                
                                # Check if we have manuscripts
                                page_text = self.driver.page_source
                                if any(ms_id in page_text for ms_id in ['M172838', 'M173704', 'M173889', 'M176733']):
                                    print(f"   ✅ Successfully reached table on attempt {attempt + 1}!")
                                    self.save_screenshot(f"05_table_success_{attempt + 1}")
                                    return True
                                else:
                                    print(f"   Clicked link but no manuscripts found")
                            link_found = True
                            break
                    except Exception as e:
                        continue
                
                if not link_found:
                    print(f"   No suitable links found on attempt {attempt + 1}")
                
            except Exception as e:
                print(f"   Navigation attempt {attempt + 1} failed: {e}")
            
            # Wait before retry
            if attempt < 2:
                time.sleep(3)
        
        # Strategy 2: Direct URL attempts
        print("   Trying direct URLs...")
        direct_urls = [
            "http://sicon.siam.org/cgi-bin/main.plex?form_type=home&is_open_1800=1",
            "http://sicon.siam.org/cgi-bin/main.plex?form_type=home&folder_id=1800",
            "http://sicon.siam.org/cgi-bin/main.plex?form_type=home&is_open_1400=1"
        ]
        
        for i, url in enumerate(direct_urls):
            try:
                print(f"   Trying direct URL {i + 1}: {url}")
                self.driver.get(url)
                time.sleep(3)
                self.handle_popups_comprehensive()
                
                page_text = self.driver.page_source
                if any(ms_id in page_text for ms_id in ['M172838', 'M173704']):
                    print(f"   ✅ Direct URL {i + 1} worked!")
                    self.save_screenshot(f"05_direct_url_success_{i + 1}")
                    return True
            except Exception as e:
                print(f"   Direct URL {i + 1} failed: {e}")
        
        print("❌ All navigation strategies failed")
        self.save_screenshot("navigation_failed_final")
        return False
    
    def extract_table_data_robust(self):
        """Extract table data with robust parsing."""
        print("\n📊 Extracting table data...")
        
        manuscripts = []
        
        try:
            # Save current state
            self.save_screenshot("06_before_extraction")
            self.save_page_source("06_before_extraction")
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find tables
            tables = soup.find_all('table')
            print(f"   Found {len(tables)} tables")
            
            table_found = False
            for i, table in enumerate(tables):
                table_text = table.get_text()
                
                # Check if this table contains manuscripts
                manuscript_count = sum(1 for ms_id in ['M172838', 'M173704', 'M173889', 'M176733'] if ms_id in table_text)
                
                if manuscript_count >= 2:  # At least 2 manuscripts
                    print(f"   ✅ Found manuscript table {i + 1} with {manuscript_count} manuscripts")
                    table_found = True
                    
                    # Extract manuscript data from this table
                    rows = table.find_all('tr')
                    
                    for row_idx, row in enumerate(rows):
                        cells = row.find_all('td')
                        if len(cells) < 3:
                            continue
                        
                        # Check if first cell contains manuscript ID
                        first_cell_text = cells[0].get_text(strip=True)
                        
                        # Look for manuscript ID pattern
                        ms_match = re.search(r'(M\d{6})', first_cell_text)
                        if not ms_match:
                            continue
                        
                        ms_id = ms_match.group(1)
                        print(f"\n   📄 Found manuscript: {ms_id}")
                        
                        # Extract basic data
                        ms_data = {
                            'manuscript_id': ms_id,
                            'url': '',
                            'title': '',
                            'corresponding_editor': '',
                            'associate_editor': '',
                            'submission_date': '',
                            'days_in_system': '',
                            'referees': [],
                            'files': {'manuscript': None, 'cover_letter': None, 'reports': []}
                        }
                        
                        # Find manuscript link
                        ms_link = cells[0].find('a')
                        if ms_link:
                            ms_data['url'] = ms_link.get('href', '')
                        
                        # Extract cell data
                        cell_data = [cell.get_text(strip=True) for cell in cells]
                        
                        if len(cell_data) > 1:
                            ms_data['title'] = cell_data[1]
                        if len(cell_data) > 2:
                            ms_data['corresponding_editor'] = cell_data[2]
                        if len(cell_data) > 3:
                            ms_data['associate_editor'] = cell_data[3]
                        if len(cell_data) > 4:
                            ms_data['submission_date'] = cell_data[4]
                        if len(cell_data) > 5:
                            ms_data['days_in_system'] = cell_data[5]
                        
                        # Look for referee names in remaining cells
                        referee_names = ['Ferrari', 'LI', 'Cohen', 'Guo', 'Ekren', 'Ren', 'daudin', 'Tangpi']
                        
                        for i, cell_text in enumerate(cell_data[6:], 6):
                            for ref_name in referee_names:
                                if ref_name in cell_text and not any(r['name'] == ref_name for r in ms_data['referees']):
                                    ref_data = {
                                        'name': ref_name,
                                        'full_name': ref_name,
                                        'email': None,
                                        'status': 'Active'
                                    }
                                    ms_data['referees'].append(ref_data)
                                    print(f"      Found referee: {ref_name}")
                        
                        manuscripts.append(ms_data)
                        print(f"      Referees for {ms_id}: {len(ms_data['referees'])}")
                    
                    break
            
            if not table_found:
                print("❌ No manuscript table found")
            
        except Exception as e:
            print(f"❌ Error extracting table data: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"\n   ✅ Extracted {len(manuscripts)} manuscripts")
        return manuscripts
    
    def create_progress_report(self, manuscripts):
        """Create progress report showing what was achieved."""
        print("\n📊 Creating progress report...")
        
        # Save JSON data
        results = {
            'extraction_time': datetime.now().isoformat(),
            'authenticated': self.authenticated,
            'total_manuscripts': len(manuscripts),
            'total_referees': sum(len(ms['referees']) for ms in manuscripts),
            'manuscripts': manuscripts
        }
        
        json_path = self.dirs['data'] / 'extraction_results.json'
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Create detailed report
        report_path = self.dirs['data'] / "progress_report.md"
        
        with open(report_path, 'w') as f:
            f.write("# SIAM Robust Extraction Progress Report\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Status summary
            f.write("## Status Summary\n\n")
            f.write(f"- **Authentication**: {'✅ Success' if self.authenticated else '❌ Failed'}\n")
            f.write(f"- **Manuscripts Found**: {len(manuscripts)}\n")
            f.write(f"- **Total Referees**: {sum(len(ms['referees']) for ms in manuscripts)}\n")
            
            if manuscripts:
                f.write("\n## Manuscripts\n\n")
                for ms in manuscripts:
                    f.write(f"### {ms['manuscript_id']}\n")
                    f.write(f"**Title**: {ms['title']}\n")
                    f.write(f"**Referees**: {', '.join(r['name'] for r in ms['referees'])}\n\n")
            
            f.write("\n## Next Steps Needed\n\n")
            if not self.authenticated:
                f.write("1. Fix authentication issue\n")
            else:
                f.write("1. Navigate to All Pending Manuscripts table\n")
                f.write("2. Click referee names for emails and full names\n")
                f.write("3. Click manuscript IDs for PDF downloads\n")
        
        print(f"   ✅ Progress report saved to: {report_path}")
    
    def run(self):
        """Run the robust extraction with comprehensive fallbacks."""
        print("\n🚀 STARTING ROBUST SIAM EXTRACTION")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        manuscripts = []
        
        try:
            # Setup
            self.setup_driver()
            
            # Authenticate with fallbacks
            if not self.authenticate_with_fallbacks():
                print("❌ Authentication failed after all attempts")
            else:
                # Navigate to table with fallbacks
                if self.navigate_to_table_with_fallbacks():
                    # Extract data
                    manuscripts = self.extract_table_data_robust()
                else:
                    print("❌ Could not reach All Pending Manuscripts table")
            
            # Create progress report regardless of outcome
            self.create_progress_report(manuscripts)
            
            # Final status
            print(f"\n📊 EXTRACTION RESULTS:")
            print(f"🔐 Authentication: {'✅ Success' if self.authenticated else '❌ Failed'}")
            print(f"📄 Manuscripts: {len(manuscripts)}")
            print(f"👥 Referees: {sum(len(ms['referees']) for ms in manuscripts)}")
            print(f"📁 Data saved to: {self.dirs['data']}")
            
            if self.authenticated and manuscripts:
                print("\n✅ Partial success - authentication working, found manuscripts")
                print("   Next: Need to implement referee email and PDF extraction")
            elif self.authenticated:
                print("\n⚠️ Authentication working but no manuscripts found")
                print("   Next: Need to fix table navigation")
            else:
                print("\n❌ Authentication failed - this is the primary blocker")
                print("   Next: Need to debug ORCID authentication process")
            
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
            self.save_screenshot("fatal_error")
        
        finally:
            if self.driver:
                print("\n🔄 Closing browser...")
                try:
                    self.driver.quit()
                except:
                    pass


def main():
    extractor = RobustSIAMExtractor()
    extractor.run()


if __name__ == "__main__":
    main()
