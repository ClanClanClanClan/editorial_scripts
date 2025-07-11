#!/usr/bin/env python3
"""
SIAM Extractor - Final attempt with focused debugging and robustness
"""

import os
import re
import time
import json
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup


class FinalSIAMExtractor:
    """Final SIAM extractor with focused approach."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.main_window = None
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_final_attempt_{timestamp}')
        self.output_dir.mkdir(exist_ok=True)
        
        self.dirs = {
            'data': self.output_dir / 'data',
            'screenshots': self.output_dir / 'screenshots'
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(exist_ok=True)
        
        print(f"📁 Output directory: {self.output_dir}")
    
    def setup_driver(self):
        """Setup Chrome WebDriver."""
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)
        
        print("✅ Chrome WebDriver initialized")
    
    def save_screenshot(self, name):
        """Save screenshot."""
        try:
            path = self.dirs['screenshots'] / f"{name}.png"
            self.driver.save_screenshot(str(path))
            print(f"📸 Screenshot: {name}.png")
        except:
            pass
    
    def handle_popups(self):
        """Handle popups."""
        try:
            # Continue button
            continue_btns = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Continue')]")
            if continue_btns:
                continue_btns[0].click()
                time.sleep(2)
            
            # Remove overlays with JavaScript
            self.driver.execute_script("""
                var overlays = document.querySelectorAll('[style*="position: fixed"]');
                overlays.forEach(function(el) {
                    if (el.style.zIndex > 100) {
                        el.remove();
                    }
                });
            """)
        except:
            pass
    
    def authenticate_step_by_step(self):
        """Authenticate with detailed step-by-step debugging."""
        print("\n🔐 Step-by-step authentication...")
        
        # Step 1: Navigate to SICON
        print("   Step 1: Navigate to SICON")
        self.driver.get("http://sicon.siam.org")
        time.sleep(3)
        self.main_window = self.driver.current_window_handle
        self.handle_popups()
        self.save_screenshot("01_sicon_initial")
        
        # Step 2: Check current state
        print("   Step 2: Check current state")
        page_text = self.driver.page_source.lower()
        print(f"   Page contains 'logout': {'logout' in page_text}")
        print(f"   Page contains 'login': {'login' in page_text}")
        print(f"   Page contains 'associate editor': {'associate editor' in page_text}")
        print(f"   Current URL: {self.driver.current_url}")
        
        # If we see Associate Editor tasks, we're authenticated
        if 'associate editor tasks' in page_text:
            print("✅ Already authenticated (found Associate Editor Tasks)!")
            return True
        
        # Step 3: Find ORCID link
        print("   Step 3: Look for ORCID link")
        orcid_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'orcid')]")
        print(f"   Found {len(orcid_links)} ORCID links")
        
        if not orcid_links:
            print("❌ No ORCID links found")
            return False
        
        # Step 4: Click ORCID
        print("   Step 4: Click ORCID link")
        try:
            self.driver.execute_script("arguments[0].click();", orcid_links[0])
            time.sleep(5)
        except Exception as e:
            print(f"❌ Error clicking ORCID: {e}")
            return False
        
        # Step 5: Check if on ORCID
        print("   Step 5: Verify ORCID page")
        print(f"   Current URL: {self.driver.current_url}")
        if 'orcid.org' not in self.driver.current_url:
            print("❌ Did not reach ORCID")
            return False
        
        self.save_screenshot("02_orcid_page")
        
        # Step 6: Fill credentials
        print("   Step 6: Fill ORCID credentials")
        try:
            username = self.wait.until(EC.presence_of_element_located((By.ID, "username-input")))
            username.clear()
            username.send_keys("0000-0002-9364-0124")
            
            password = self.driver.find_element(By.ID, "password")
            password.clear()
            password.send_keys("Hioupy0042%")
            password.send_keys(Keys.RETURN)
            
            print("   Credentials submitted")
        except Exception as e:
            print(f"❌ Error filling credentials: {e}")
            return False
        
        # Step 7: Wait for redirect
        print("   Step 7: Wait for redirect to SICON")
        timeout = time.time() + 25
        while time.time() < timeout:
            current_url = self.driver.current_url
            print(f"   Current URL: {current_url}")
            
            if 'sicon.siam.org' in current_url and 'orcid.org' not in current_url:
                print("   ✅ Redirected back to SICON")
                time.sleep(3)
                self.handle_popups()
                
                # Step 8: Final authentication check
                print("   Step 8: Final authentication check")
                page_text = self.driver.page_source.lower()
                self.save_screenshot("03_after_auth")
                
                print(f"   Page contains 'associate editor tasks': {'associate editor tasks' in page_text}")
                print(f"   Page contains 'author tasks': {'author tasks' in page_text}")
                print(f"   Page contains 'logout': {'logout' in page_text}")
                print(f"   Page contains 'please log in': {'please log in' in page_text}")
                
                # Success if we see authenticated content
                if any(indicator in page_text for indicator in ['associate editor tasks', 'author tasks']) and 'please log in' not in page_text:
                    print("✅ Authentication successful!")
                    return True
                else:
                    print("❌ Still on login page after redirect")
                    return False
            
            time.sleep(1)
        
        print("❌ Authentication timeout")
        return False
    
    def find_table_with_debugging(self):
        """Find the All Pending Manuscripts table with detailed debugging."""
        print("\n📋 Finding All Pending Manuscripts table...")
        
        # Navigate to home page
        print("   Navigating to home page")
        self.driver.get("http://sicon.siam.org/cgi-bin/main.plex?form_type=home")
        time.sleep(3)
        self.handle_popups()
        self.save_screenshot("04_home_page")
        
        # List all links on the page
        print("   Analyzing page links...")
        all_links = self.driver.find_elements(By.TAG_NAME, "a")
        print(f"   Found {len(all_links)} total links")
        
        pending_links = []
        for i, link in enumerate(all_links):
            text = link.text.strip()
            href = link.get_attribute('href') or ''
            
            if 'pending' in text.lower() or 'manuscripts' in text.lower():
                pending_links.append((text, href))
                print(f"   Link {i}: '{text}' -> {href}")
        
        print(f"   Found {len(pending_links)} potential manuscript links")
        
        # Try clicking promising links
        for text, href in pending_links:
            if 'all pending' in text.lower() or 'manuscripts' in text.lower():
                print(f"   Trying to click: '{text}'")
                try:
                    # Find the link again and click it
                    link_element = self.driver.find_element(By.XPATH, f"//a[text()='{text}']")
                    self.driver.execute_script("arguments[0].click();", link_element)
                    time.sleep(3)
                    
                    # Check if we got manuscripts
                    page_text = self.driver.page_source
                    if any(ms_id in page_text for ms_id in ['M172838', 'M173704', 'M173889', 'M176733']):
                        print(f"   ✅ Success! Found manuscripts with link: '{text}'")
                        self.save_screenshot("05_table_found")
                        return True
                    else:
                        print(f"   Link clicked but no manuscripts found")
                        
                except Exception as e:
                    print(f"   Error clicking '{text}': {e}")
        
        # Try direct URLs as fallback
        print("   Trying direct URLs...")
        direct_urls = [
            "http://sicon.siam.org/cgi-bin/main.plex?form_type=home&is_open_1800=1",
            "http://sicon.siam.org/cgi-bin/main.plex?form_type=home&folder_id=1800"
        ]
        
        for i, url in enumerate(direct_urls):
            print(f"   Trying direct URL {i+1}: {url}")
            try:
                self.driver.get(url)
                time.sleep(3)
                
                page_text = self.driver.page_source
                if any(ms_id in page_text for ms_id in ['M172838', 'M173704']):
                    print(f"   ✅ Direct URL {i+1} worked!")
                    self.save_screenshot(f"05_direct_url_{i+1}")
                    return True
            except Exception as e:
                print(f"   Direct URL {i+1} failed: {e}")
        
        print("❌ Could not find All Pending Manuscripts table")
        return False
    
    def extract_basic_data(self):
        """Extract whatever data we can find."""
        print("\n📊 Extracting available data...")
        
        manuscripts = []
        
        try:
            page_text = self.driver.page_source
            
            # Look for manuscript IDs in the page
            manuscript_ids = re.findall(r'M\d{6}', page_text)
            manuscript_ids = list(set(manuscript_ids))  # Remove duplicates
            
            print(f"   Found manuscript IDs: {manuscript_ids}")
            
            for ms_id in manuscript_ids:
                ms_data = {
                    'manuscript_id': ms_id,
                    'url': '',
                    'title': 'Not extracted',
                    'referees': [],
                    'extraction_status': 'Basic ID only'
                }
                manuscripts.append(ms_data)
            
            # Look for referee names
            referee_names = ['Ferrari', 'LI', 'Cohen', 'Guo', 'Ekren', 'Ren', 'daudin', 'Tangpi']
            found_referees = []
            
            for ref_name in referee_names:
                if ref_name in page_text:
                    found_referees.append(ref_name)
            
            print(f"   Found referee names: {found_referees}")
            
        except Exception as e:
            print(f"   Error extracting data: {e}")
        
        return manuscripts
    
    def create_diagnostic_report(self, authenticated, table_found, manuscripts):
        """Create diagnostic report."""
        print("\n📊 Creating diagnostic report...")
        
        results = {
            'extraction_time': datetime.now().isoformat(),
            'authentication_success': authenticated,
            'table_access_success': table_found,
            'manuscripts_found': len(manuscripts),
            'manuscripts': manuscripts,
            'status': 'diagnostic_run'
        }
        
        json_path = self.dirs['data'] / 'diagnostic_results.json'
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        report_path = self.dirs['data'] / 'diagnostic_report.md'
        with open(report_path, 'w') as f:
            f.write("# SIAM Diagnostic Report\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Status\n\n")
            f.write(f"- Authentication: {'✅ Success' if authenticated else '❌ Failed'}\n")
            f.write(f"- Table Access: {'✅ Success' if table_found else '❌ Failed'}\n")
            f.write(f"- Manuscripts Found: {len(manuscripts)}\n\n")
            
            if manuscripts:
                f.write("## Manuscripts\n\n")
                for ms in manuscripts:
                    f.write(f"- {ms['manuscript_id']}: {ms['extraction_status']}\n")
            
            f.write("\n## Next Steps\n\n")
            if not authenticated:
                f.write("1. **Fix authentication** - Primary blocker\n")
                f.write("   - Debug ORCID login process\n")
                f.write("   - Check credentials and session handling\n")
            elif not table_found:
                f.write("1. **Fix table navigation** - Secondary blocker\n")
                f.write("   - Find correct link to All Pending Manuscripts\n")
                f.write("   - Try different URL patterns\n")
            else:
                f.write("1. **Extract referee details** - Click referee names for emails\n")
                f.write("2. **Download PDFs** - Click manuscript IDs for files\n")
        
        print(f"   ✅ Diagnostic report saved to: {report_path}")
    
    def run(self):
        """Run focused diagnostic extraction."""
        print("\n🚀 STARTING FOCUSED SIAM DIAGNOSTIC")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        authenticated = False
        table_found = False
        manuscripts = []
        
        try:
            # Setup
            self.setup_driver()
            
            # Test authentication
            authenticated = self.authenticate_step_by_step()
            
            if authenticated:
                # Test table access
                table_found = self.find_table_with_debugging()
                
                if table_found:
                    # Extract data
                    manuscripts = self.extract_basic_data()
            
            # Create diagnostic report
            self.create_diagnostic_report(authenticated, table_found, manuscripts)
            
            # Summary
            print(f"\n📊 DIAGNOSTIC RESULTS:")
            print(f"Authentication: {'✅' if authenticated else '❌'}")
            print(f"Table Access: {'✅' if table_found else '❌'}")
            print(f"Manuscripts: {len(manuscripts)}")
            
            if authenticated and table_found and manuscripts:
                print("\n✅ BREAKTHROUGH: All core components working!")
                print("   Ready to implement referee email and PDF extraction")
            elif authenticated and table_found:
                print("\n⚠️  Core access working, data extraction needs refinement")
            elif authenticated:
                print("\n⚠️  Authentication working, need to fix table navigation")
            else:
                print("\n❌ Authentication is the primary blocker")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            if self.driver:
                print("\n🔄 Closing browser...")
                try:
                    self.driver.quit()
                except:
                    pass


def main():
    extractor = FinalSIAMExtractor()
    extractor.run()


if __name__ == "__main__":
    main()
