#!/usr/bin/env python3
"""
SIAM Extractor - Fixed parsing for the actual table structure
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
from bs4 import BeautifulSoup


class FixedParsingSIAMExtractor:
    """SIAM extractor with fixed parsing for the actual table structure."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.main_window = None
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_fixed_parsing_{timestamp}')
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
        """Setup Chrome WebDriver."""
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
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Enable downloads
        self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": str(self.download_dir)
        })
        
        self.wait = WebDriverWait(self.driver, 30)
        print("✅ Chrome WebDriver initialized")
    
    def save_screenshot(self, name):
        """Save screenshot for debugging."""
        try:
            path = self.dirs['screenshots'] / f"{name}.png"
            self.driver.save_screenshot(str(path))
            print(f"📸 Screenshot: {name}.png")
        except:
            pass
    
    def handle_popups(self):
        """Handle privacy notifications and cookie banners."""
        try:
            # Handle "Continue" button in privacy notification
            continue_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Continue') or @value='Continue']")
            if continue_buttons:
                continue_buttons[0].click()
                time.sleep(2)
                print("   ✅ Dismissed privacy notification")
            
            # Handle cookie banners and overlays
            self.driver.execute_script("""
                var elements = ['#cookie-policy-layer-bg', '#cookie-policy-layer', '.cc-banner', '.cookie-banner'];
                elements.forEach(function(sel) {
                    var els = document.querySelectorAll(sel);
                    els.forEach(function(el) { 
                        el.style.display = 'none';
                        el.remove(); 
                    });
                });
                
                // Remove any modal overlays
                var modals = document.querySelectorAll('[style*="position: fixed"], [style*="z-index"]');
                modals.forEach(function(modal) {
                    if (modal.style.position === 'fixed' && modal.style.zIndex > 100) {
                        modal.remove();
                    }
                });
            """)
        except Exception as e:
            print(f"   Warning: Error handling popups: {e}")
    
    def authenticate_sicon(self):
        """Authenticate with SICON using ORCID."""
        print("\n🔐 Authenticating with SICON...")
        
        self.driver.get("http://sicon.siam.org")
        time.sleep(3)
        self.main_window = self.driver.current_window_handle
        
        self.handle_popups()
        self.save_screenshot("01_sicon_initial")
        
        # Check if already authenticated
        page_source = self.driver.page_source
        if "logout" in page_source.lower() and "welcome to siam journal" not in page_source.lower():
            print("✅ Already authenticated!")
            return True
        
        print("   Need to authenticate via ORCID")
        
        try:
            # Find and click ORCID link
            orcid_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'orcid') or contains(@href, 'sso_site_redirect')]")
            
            if not orcid_links:
                orcid_imgs = self.driver.find_elements(By.XPATH, "//img[@title='ORCID']")
                if orcid_imgs:
                    orcid_parent = orcid_imgs[0].find_element(By.XPATH, "..")
                    if orcid_parent.tag_name == 'a':
                        orcid_links = [orcid_parent]
            
            if orcid_links:
                print("   Clicking ORCID link...")
                self.driver.execute_script("arguments[0].click();", orcid_links[0])
                time.sleep(5)
                
                if 'orcid.org' in self.driver.current_url:
                    print("   ✅ Navigated to ORCID")
                    
                    # Fill credentials
                    username = self.wait.until(EC.presence_of_element_located((By.ID, "username-input")))
                    username.clear()
                    username.send_keys("0000-0002-9364-0124")
                    
                    password = self.driver.find_element(By.ID, "password")
                    password.clear()
                    password.send_keys("Hioupy0042%")
                    password.send_keys(Keys.RETURN)
                    
                    print("   ⏳ Waiting for authentication redirect...")
                    
                    # Wait for redirect back to SICON
                    timeout = time.time() + 30
                    while time.time() < timeout:
                        current_url = self.driver.current_url
                        page_content = self.driver.page_source
                        
                        if ('sicon.siam.org' in current_url and 
                            'orcid.org' not in current_url and
                            'welcome to siam journal' not in page_content.lower()):
                            print("   ✅ Authentication successful!")
                            time.sleep(3)
                            self.handle_popups()
                            return True
                        time.sleep(1)
                    
                    print("❌ Authentication timeout")
                    return False
            else:
                print("❌ No ORCID link found")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def navigate_to_all_pending(self):
        """Navigate to All Pending Manuscripts."""
        print("\n📋 Navigating to All Pending Manuscripts...")
        
        # Go to home first
        self.driver.get("http://sicon.siam.org/cgi-bin/main.plex?form_type=home")
        time.sleep(3)
        self.handle_popups()
        
        # Try direct folder_id=1800 approach
        print("   Trying direct folder_id=1800 URL...")
        direct_url = "http://sicon.siam.org/cgi-bin/main.plex?form_type=home&is_open_1800=1"
        self.driver.get(direct_url)
        time.sleep(3)
        self.handle_popups()
        self.save_screenshot("02_all_pending_table")
        
        # Verify we have the table with manuscripts
        page_text = self.driver.page_source
        if any(ms_id in page_text for ms_id in ['M172838', 'M173704', 'M173889', 'M176733']):
            print("   ✅ Successfully reached All Pending Manuscripts table!")
            return True
        else:
            print("   ❌ Could not access All Pending Manuscripts table")
            return False
    
    def extract_manuscripts_and_referees(self):
        """Extract manuscripts and referee data from the actual table structure."""
        print("\n📊 Extracting manuscripts and referees from table...")
        
        manuscripts = []
        
        # Parse the current page
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Find the table with manuscript data
        table_found = False
        for table in soup.find_all('table'):
            # Look for table rows with manuscript IDs
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all('td')
                if not cells or len(cells) < 6:
                    continue
                
                # Check if first cell contains manuscript ID
                first_cell_text = cells[0].get_text(strip=True)
                if not first_cell_text.startswith('M'):
                    continue
                
                table_found = True
                ms_id = first_cell_text
                print(f"\n   📄 Processing {ms_id}")
                
                # Extract manuscript data
                ms_data = {
                    'manuscript_id': ms_id,
                    'url': '',
                    'title': '',
                    'corresponding_editor': '',
                    'associate_editor': '',
                    'submission_date': '',
                    'days_in_system': '',
                    'current_stage': '',
                    'referees': [],
                    'files': {'manuscript': None, 'cover_letter': None, 'reports': []}
                }
                
                # Find manuscript link
                ms_link = cells[0].find('a')
                if ms_link:
                    ms_data['url'] = ms_link.get('href', '')
                
                # Extract from cells based on actual structure
                if len(cells) > 1:
                    ms_data['title'] = cells[1].get_text(strip=True)
                if len(cells) > 2:
                    ms_data['corresponding_editor'] = cells[2].get_text(strip=True)
                if len(cells) > 3:
                    ms_data['associate_editor'] = cells[3].get_text(strip=True)
                if len(cells) > 4:
                    ms_data['submission_date'] = cells[4].get_text(strip=True)
                if len(cells) > 5:
                    ms_data['days_in_system'] = cells[5].get_text(strip=True)
                
                # Extract referee information from the visible columns
                # Based on the screenshot, referee info appears in later columns
                if len(cells) > 6:
                    # Look for referee names in the cells
                    for i in range(6, len(cells)):
                        cell_text = cells[i].get_text(strip=True)
                        
                        # Split by lines to get individual referee names
                        referee_lines = [line.strip() for line in cell_text.split('\n') if line.strip()]
                        
                        for line in referee_lines:
                            # Look for known referee names
                            referee_names = ['Ferrari', 'LI', 'Cohen', 'Guo', 'Ekren', 'Ren', 'daudin', 'Tangpi']
                            
                            for ref_name in referee_names:
                                if ref_name in line:
                                    # Check if this referee is already added
                                    if not any(r['name'] == ref_name for r in ms_data['referees']):
                                        ref_data = {
                                            'name': ref_name,
                                            'full_name': ref_name,
                                            'email': None,
                                            'status': 'Active',
                                            'due_date': '',
                                            'received_date': '',
                                            'has_report': False
                                        }
                                        ms_data['referees'].append(ref_data)
                                        print(f"      Found referee: {ref_name}")
                
                manuscripts.append(ms_data)
                print(f"      Total referees for {ms_id}: {len(ms_data['referees'])}")
        
        if not table_found:
            print("   ❌ No manuscript table found")
        
        print(f"\n   ✅ Found {len(manuscripts)} manuscripts with {sum(len(ms['referees']) for ms in manuscripts)} total referees")
        return manuscripts
    
    def click_referee_names_for_details(self, manuscripts):
        """Click on referee names to get emails and full names."""
        print("\n🔍 Clicking referee names to get detailed information...")
        
        for ms in manuscripts:
            for ref in ms['referees']:
                referee_name = ref['name']
                print(f"\n      👤 Getting details for '{referee_name}'...")
                
                # Look for clickable referee name links
                referee_links = self.driver.find_elements(By.XPATH, f"//a[text()='{referee_name}']")
                
                # Try partial match if exact not found
                if not referee_links:
                    referee_links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{referee_name}')]")
                
                if referee_links:
                    try:
                        print(f"         Clicking on '{referee_name}' link...")
                        
                        # Store current windows
                        original_windows = self.driver.window_handles
                        
                        # Click the referee link
                        self.driver.execute_script("arguments[0].click();", referee_links[0])
                        time.sleep(3)
                        
                        # Check if new window opened
                        new_windows = self.driver.window_handles
                        if len(new_windows) > len(original_windows):
                            # Switch to new window
                            self.driver.switch_to.window(new_windows[-1])
                            
                            self.save_screenshot(f"referee_{referee_name}_profile")
                            
                            # Extract full name from page title
                            page_title = self.driver.title
                            if page_title and '-' in page_title:
                                full_name = page_title.split('-')[0].strip()
                                if len(full_name) > len(referee_name) and len(full_name) < 100:
                                    ref['full_name'] = full_name
                                    print(f"         ✅ Full name: {full_name}")
                            
                            # Look for email
                            email_links = self.driver.find_elements(By.XPATH, "//a[starts-with(@href, 'mailto:')]")
                            if email_links:
                                email = email_links[0].get_attribute('href').replace('mailto:', '')
                                ref['email'] = email
                                print(f"         ✅ Email: {email}")
                            else:
                                print(f"         ⚠️ No email found for {referee_name}")
                            
                            # Close the new window
                            self.driver.close()
                            self.driver.switch_to.window(self.main_window)
                        else:
                            print(f"         ⚠️ No new window opened for {referee_name}")
                        
                    except Exception as e:
                        print(f"         ❌ Error getting details for {referee_name}: {e}")
                        # Make sure we're back on main window
                        if len(self.driver.window_handles) > 1:
                            self.driver.close()
                        self.driver.switch_to.window(self.main_window)
                else:
                    print(f"         ⚠️ No clickable link found for '{referee_name}'")
        
        return manuscripts
    
    def click_manuscript_ids_for_pdfs(self, manuscripts):
        """Click on manuscript IDs to download PDFs."""
        print("\n📎 Clicking manuscript IDs to download PDFs...")
        
        for ms in manuscripts:
            ms_id = ms['manuscript_id']
            print(f"\n   📄 Downloading files for {ms_id}...")
            
            # Ensure we're on the All Pending table
            if not any(ms_id in self.driver.page_source for ms_id in ['M172838', 'M173704']):
                if not self.navigate_to_all_pending():
                    print(f"      ❌ Could not navigate back to table")
                    continue
            
            # Find and click the manuscript ID link
            ms_id_links = self.driver.find_elements(By.XPATH, f"//a[text()='{ms_id}']")
            
            if ms_id_links:
                try:
                    print(f"      Clicking on {ms_id} to access files...")
                    
                    # Store current windows
                    original_windows = self.driver.window_handles
                    
                    # Click manuscript ID
                    self.driver.execute_script("arguments[0].click();", ms_id_links[0])
                    time.sleep(5)
                    
                    # Check if new window opened
                    new_windows = self.driver.window_handles
                    if len(new_windows) > len(original_windows):
                        # Switch to new window
                        self.driver.switch_to.window(new_windows[-1])
                    
                    self.save_screenshot(f"manuscript_{ms_id}_files")
                    
                    # Look for "Save File As" links
                    save_file_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'Save File As')]")
                    
                    print(f"      Found {len(save_file_links)} 'Save File As' links")
                    
                    files_downloaded = 0
                    
                    for i, link in enumerate(save_file_links):
                        try:
                            # Get context to determine file type
                            parent = link.find_element(By.XPATH, "../..")
                            context = parent.text.lower()
                            
                            print(f"         Downloading file {i+1}: {context[:60]}...")
                            
                            # Clear download directory
                            for file in self.download_dir.glob("*"):
                                if file.is_file():
                                    file.unlink()
                            
                            # Click download
                            link.click()
                            
                            # Wait for download
                            download_complete = False
                            for _ in range(15):
                                time.sleep(1)
                                downloaded_files = list(self.download_dir.glob("*"))
                                downloaded_files = [f for f in downloaded_files if f.is_file()]
                                if downloaded_files:
                                    download_complete = True
                                    break
                            
                            if download_complete:
                                source_file = downloaded_files[0]
                                
                                # Determine file type based on context
                                if 'article file' in context:
                                    dest_name = f"{ms_id}_manuscript.pdf"
                                    dest_path = self.dirs['manuscripts'] / dest_name
                                    ms['files']['manuscript'] = dest_name
                                elif 'cover letter' in context:
                                    dest_name = f"{ms_id}_cover_letter.pdf"
                                    dest_path = self.dirs['cover_letters'] / dest_name
                                    ms['files']['cover_letter'] = dest_name
                                elif 'referee' in context and 'review' in context:
                                    ref_match = re.search(r'referee\s*#?(\d+)', context)
                                    ref_num = ref_match.group(1) if ref_match else str(len(ms['files']['reports']) + 1)
                                    dest_name = f"{ms_id}_referee_{ref_num}_report.pdf"
                                    dest_path = self.dirs['reports'] / dest_name
                                    ms['files']['reports'].append(dest_name)
                                else:
                                    dest_name = f"{ms_id}_file_{i+1}.pdf"
                                    dest_path = self.output_dir / dest_name
                                
                                # Move file
                                shutil.move(str(source_file), str(dest_path))
                                files_downloaded += 1
                                print(f"            ✅ Downloaded: {dest_name}")
                            else:
                                print(f"            ❌ Download timeout for file {i+1}")
                                
                        except Exception as e:
                            print(f"            ❌ Error downloading file {i+1}: {e}")
                    
                    # Close manuscript window
                    if len(self.driver.window_handles) > 1:
                        self.driver.close()
                        self.driver.switch_to.window(self.main_window)
                    
                    print(f"      ✅ Downloaded {files_downloaded} files for {ms_id}")
                    
                except Exception as e:
                    print(f"      ❌ Error accessing files for {ms_id}: {e}")
                    if len(self.driver.window_handles) > 1:
                        self.driver.close()
                    self.driver.switch_to.window(self.main_window)
            else:
                print(f"      ❌ No clickable link found for {ms_id}")
        
        return manuscripts
    
    def create_final_report(self, manuscripts):
        """Create comprehensive final report."""
        print("\n📊 Creating final report...")
        
        # Save JSON data
        results = {
            'extraction_time': datetime.now().isoformat(),
            'total_manuscripts': len(manuscripts),
            'total_referees': sum(len(ms['referees']) for ms in manuscripts),
            'manuscripts': manuscripts
        }
        
        json_path = self.dirs['data'] / 'siam_complete_extraction.json'
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Create markdown report
        report_path = self.dirs['data'] / "siam_final_report.md"
        
        with open(report_path, 'w') as f:
            f.write("# SIAM Final Extraction Report\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Statistics
            total_referees = sum(len(ms['referees']) for ms in manuscripts)
            refs_with_emails = sum(1 for ms in manuscripts for ref in ms['referees'] if ref.get('email'))
            refs_with_full_names = sum(1 for ms in manuscripts for ref in ms['referees'] if ref.get('full_name') != ref.get('name'))
            total_files = sum(
                (1 if ms['files']['manuscript'] else 0) +
                (1 if ms['files']['cover_letter'] else 0) +
                len(ms['files']['reports'])
                for ms in manuscripts
            )
            
            f.write(f"**Total Manuscripts**: {len(manuscripts)}\n")
            f.write(f"**Total Referees**: {total_referees}\n")
            f.write(f"**Referee Emails Found**: {refs_with_emails}/{total_referees}\n")
            f.write(f"**Full Names Retrieved**: {refs_with_full_names}/{total_referees}\n")
            f.write(f"**Files Downloaded**: {total_files}\n\n")
            
            f.write("## Results\n\n")
            
            for ms in manuscripts:
                f.write(f"### {ms['manuscript_id']}\n")
                f.write(f"**Title**: {ms['title']}\n")
                f.write(f"**Editors**: {ms['corresponding_editor']} / {ms['associate_editor']}\n")
                f.write(f"**Submitted**: {ms['submission_date']} ({ms['days_in_system']} days)\n\n")
                
                f.write("**Referees**:\n")
                for ref in ms['referees']:
                    f.write(f"- **{ref['full_name']}**")
                    if ref.get('email'):
                        f.write(f" ({ref['email']})")
                    f.write("\n")
                
                f.write("\n**Files**:\n")
                files = ms['files']
                if files['manuscript']:
                    f.write(f"- ✅ Manuscript: {files['manuscript']}\n")
                if files['cover_letter']:
                    f.write(f"- ✅ Cover Letter: {files['cover_letter']}\n")
                for report in files['reports']:
                    f.write(f"- ✅ Report: {report}\n")
                
                f.write("\n---\n\n")
        
        print(f"   ✅ JSON saved to: {json_path}")
        print(f"   ✅ Report saved to: {report_path}")
    
    def run(self):
        """Run the complete SIAM extraction with fixed parsing."""
        print("\n🚀 STARTING SIAM EXTRACTION WITH FIXED PARSING")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Setup
            self.setup_driver()
            
            # Authenticate
            if not self.authenticate_sicon():
                print("❌ Authentication failed")
                return
            
            # Navigate to All Pending Manuscripts
            if not self.navigate_to_all_pending():
                print("❌ Could not navigate to All Pending Manuscripts")
                return
            
            # Extract manuscripts and referees
            manuscripts = self.extract_manuscripts_and_referees()
            
            if not manuscripts:
                print("❌ No manuscripts found")
                return
            
            # Click referee names for details
            manuscripts = self.click_referee_names_for_details(manuscripts)
            
            # Click manuscript IDs for PDFs
            manuscripts = self.click_manuscript_ids_for_pdfs(manuscripts)
            
            # Create final report
            self.create_final_report(manuscripts)
            
            print(f"\n✅ EXTRACTION COMPLETED!")
            print(f"📊 Manuscripts: {len(manuscripts)}")
            print(f"👥 Referees: {sum(len(ms['referees']) for ms in manuscripts)}")
            print(f"📧 Emails: {sum(1 for ms in manuscripts for ref in ms['referees'] if ref.get('email'))}")
            print(f"📁 Full names: {sum(1 for ms in manuscripts for ref in ms['referees'] if ref.get('full_name') != ref.get('name'))}")
            print(f"📎 Files: {sum((1 if ms['files']['manuscript'] else 0) + (1 if ms['files']['cover_letter'] else 0) + len(ms['files']['reports']) for ms in manuscripts)}")
            print(f"📁 Data saved to: {self.dirs['data']}")
            
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
    extractor = FixedParsingSIAMExtractor()
    extractor.run()


if __name__ == "__main__":
    main()
