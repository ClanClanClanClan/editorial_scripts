#!/usr/bin/env python3
"""
SIAM Extractor - Following the correct navigation pattern shown by user
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


class CorrectSIAMExtractor:
    """SIAM extractor following the correct navigation pattern."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.main_window = None
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_correct_{timestamp}')
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
        """Setup Chrome WebDriver with download configuration."""
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
        print("✅ Chrome WebDriver initialized with downloads")
    
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
            # Handle privacy notification
            continue_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Continue')]")
            if continue_buttons:
                continue_buttons[0].click()
                time.sleep(2)
                print("   ✅ Dismissed privacy notification")
            
            # Handle cookie banners
            self.driver.execute_script("""
                var elements = ['#cookie-policy-layer-bg', '#cookie-policy-layer', '.cc-banner', '.cookie-banner'];
                elements.forEach(function(sel) {
                    var els = document.querySelectorAll(sel);
                    els.forEach(function(el) { 
                        el.style.display = 'none';
                        el.remove(); 
                    });
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
        
        self.handle_popups()
        self.save_screenshot("01_sicon_home")
        
        # Check if already authenticated
        page_source = self.driver.page_source
        if "logout" in page_source.lower() and "login name" not in page_source.lower():
            print("✅ Already authenticated!")
            return True
        
        # Find and click ORCID link
        try:
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
                    
                    print("   ⏳ Waiting for authentication...")
                    
                    # Wait for redirect
                    timeout = time.time() + 30
                    while time.time() < timeout:
                        current_url = self.driver.current_url
                        if 'sicon.siam.org' in current_url and 'orcid.org' not in current_url:
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
        """Navigate to All Pending Manuscripts table."""
        print("\n📋 Navigating to All Pending Manuscripts...")
        
        # Go to home first
        self.driver.get("http://sicon.siam.org/cgi-bin/main.plex?form_type=home")
        time.sleep(3)
        self.handle_popups()
        
        # Navigate to Under Review folder
        try:
            under_review_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'folder_id=1400')]")
            if under_review_links:
                print("   Found Under Review folder")
                under_review_links[0].click()
                time.sleep(3)
                self.handle_popups()
        except:
            pass
        
        # Navigate to All Pending Manuscripts
        try:
            all_pending_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'folder_id=1800') or contains(text(), 'All Pending')]")
            if all_pending_links:
                print("   ✅ Found All Pending Manuscripts")
                all_pending_links[0].click()
                time.sleep(3)
                self.handle_popups()
                self.save_screenshot("02_all_pending_table")
                return True
        except Exception as e:
            print(f"   Error: {e}")
        
        print("❌ Could not navigate to All Pending Manuscripts")
        return False
    
    def extract_manuscripts_and_referees(self):
        """Extract manuscripts and get referee details by clicking on referee names in the table."""
        print("\n📊 Extracting manuscripts and referee details...")
        
        manuscripts = []
        
        # Parse the current page (All Pending Manuscripts table)
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Find the table with manuscript data
        for table in soup.find_all('table'):
            table_text = table.get_text()
            if not any(ms_id in table_text for ms_id in ['M172', 'M173', 'M176']):
                continue
            
            print("   ✅ Found manuscripts table")
            
            # Process data rows (skip header)
            rows = table.find_all('tr')[1:]
            
            for row in rows:
                cells = row.find_all('td')
                if not cells:
                    continue
                
                # Get manuscript ID from first cell
                first_cell = cells[0]
                ms_link = first_cell.find('a')
                
                if not ms_link:
                    continue
                
                ms_id = first_cell.get_text(strip=True)
                if not ms_id.startswith('M'):
                    continue
                
                print(f"\n   📄 Processing {ms_id}")
                
                # Extract data from cells
                cell_data = [cell.get_text(strip=True) for cell in cells]
                
                ms_data = {
                    'manuscript_id': ms_id,
                    'url': ms_link.get('href', ''),
                    'title': cell_data[1] if len(cell_data) > 1 else '',
                    'corresponding_editor': cell_data[2] if len(cell_data) > 2 else '',
                    'associate_editor': cell_data[3] if len(cell_data) > 3 else '',
                    'submission_date': cell_data[4] if len(cell_data) > 4 else '',
                    'days_in_system': cell_data[5] if len(cell_data) > 5 else '',
                    'current_stage': cell_data[-1] if len(cell_data) > 10 else '',
                    'referees': [],
                    'files': {'manuscript': None, 'cover_letter': None, 'reports': []}
                }
                
                # Extract referee info from columns 6-10
                if len(cell_data) > 10:
                    invitees_text = cell_data[6] if len(cell_data) > 6 else ''
                    status_text = cell_data[7] if len(cell_data) > 7 else ''
                    due_dates_text = cell_data[9] if len(cell_data) > 9 else ''
                    received_dates_text = cell_data[10] if len(cell_data) > 10 else ''
                    
                    # Split by lines
                    invitees = [i.strip() for i in invitees_text.split('\n') if i.strip()]
                    statuses = [s.strip() for s in status_text.split('\n') if s.strip()]
                    due_dates = [d.strip() for d in due_dates_text.split('\n') if d.strip()]
                    received_dates = [r.strip() for r in received_dates_text.split('\n') if r.strip()]
                    
                    # Process accepted referees
                    referee_idx = 0
                    for i, (invitee, status) in enumerate(zip(invitees, statuses)):
                        if status.lower() == 'accepted':
                            ref_data = {
                                'name': invitee,
                                'full_name': invitee,
                                'email': None,
                                'status': 'Active',
                                'due_date': due_dates[referee_idx] if referee_idx < len(due_dates) else '',
                                'received_date': received_dates[referee_idx] if referee_idx < len(received_dates) else '',
                                'has_report': bool(received_dates[referee_idx].strip()) if referee_idx < len(received_dates) else False
                            }
                            
                            ms_data['referees'].append(ref_data)
                            referee_idx += 1
                
                manuscripts.append(ms_data)
                print(f"      Found {len(ms_data['referees'])} accepted referees")
            
            break
        
        print(f"\n   ✅ Found {len(manuscripts)} manuscripts")
        
        # Now click on referee names in the table to get full details
        print("\n🔍 Clicking on referee names to get full details...")
        
        for ms in manuscripts:
            for ref in ms['referees']:
                referee_name = ref['name']
                print(f"\n      👤 Getting details for {referee_name}...")
                
                # Find referee name link in the table
                referee_links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{referee_name}')]")
                
                # Try partial matches if exact match not found
                if not referee_links and len(referee_name) > 2:
                    referee_links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{referee_name[:3]}')]")
                
                if referee_links:
                    try:
                        # Click the first matching link
                        self.driver.execute_script("arguments[0].click();", referee_links[0])
                        time.sleep(3)
                        
                        # Switch to new window
                        if len(self.driver.window_handles) > 1:
                            self.driver.switch_to.window(self.driver.window_handles[-1])
                            
                            # Extract full name from page title
                            page_title = self.driver.title
                            if page_title and len(page_title) > len(referee_name):
                                # Clean up title
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
                        
                    except Exception as e:
                        print(f"         ❌ Error getting details for {referee_name}: {e}")
                        # Make sure we're back on main window
                        if len(self.driver.window_handles) > 1:
                            self.driver.close()
                        self.driver.switch_to.window(self.main_window)
                else:
                    print(f"         ⚠️ No clickable link found for {referee_name}")
        
        return manuscripts
    
    def download_manuscript_files(self, manuscripts):
        """Download PDFs by clicking on manuscript IDs to get to the files page."""
        print("\n📎 Downloading manuscript files...")
        
        for ms in manuscripts:
            ms_id = ms['manuscript_id']
            print(f"\n   📄 Downloading files for {ms_id}...")
            
            # Navigate back to All Pending table
            if not self.navigate_to_all_pending():
                print(f"      ❌ Could not navigate back to table for {ms_id}")
                continue
            
            # Find and click the manuscript ID link
            ms_links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{ms_id}')]")
            
            if ms_links:
                try:
                    print(f"      Clicking on {ms_id} to access files...")
                    self.driver.execute_script("arguments[0].click();", ms_links[0])
                    time.sleep(5)
                    
                    # Switch to new window if opened
                    if len(self.driver.window_handles) > 1:
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                    
                    self.save_screenshot(f"manuscript_{ms_id}_files")
                    
                    # Look for file download links
                    page_text = self.driver.page_source
                    
                    # Find PDF download links with "Save File As" text
                    pdf_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'Save File As')]")
                    
                    print(f"      Found {len(pdf_links)} download links")
                    
                    files_downloaded = []
                    
                    for i, link in enumerate(pdf_links):
                        try:
                            # Get context to determine file type
                            parent = link.find_element(By.XPATH, "../..")
                            context = parent.text.lower()
                            
                            print(f"         Downloading file {i+1}: {context[:50]}...")
                            
                            # Clear download directory
                            for file in self.download_dir.glob("*.pdf"):
                                file.unlink()
                            
                            # Click download
                            link.click()
                            
                            # Wait for download
                            download_complete = False
                            for _ in range(10):
                                time.sleep(1)
                                pdf_files = list(self.download_dir.glob("*.pdf"))
                                if pdf_files:
                                    download_complete = True
                                    break
                            
                            if download_complete:
                                source_file = pdf_files[0]
                                
                                # Determine file type and destination
                                if 'article file' in context or 'manuscript' in context:
                                    dest_name = f"{ms_id}_manuscript.pdf"
                                    dest_path = self.dirs['manuscripts'] / dest_name
                                    ms['files']['manuscript'] = dest_name
                                elif 'cover letter' in context:
                                    dest_name = f"{ms_id}_cover_letter.pdf"
                                    dest_path = self.dirs['cover_letters'] / dest_name  
                                    ms['files']['cover_letter'] = dest_name
                                elif 'referee' in context and 'review' in context:
                                    ref_num = len(ms['files']['reports']) + 1
                                    dest_name = f"{ms_id}_referee_{ref_num}_report.pdf"
                                    dest_path = self.dirs['reports'] / dest_name
                                    ms['files']['reports'].append(dest_name)
                                else:
                                    dest_name = f"{ms_id}_file_{i+1}.pdf"
                                    dest_path = self.output_dir / dest_name
                                
                                # Move file
                                shutil.move(str(source_file), str(dest_path))
                                files_downloaded.append(dest_name)
                                print(f"            ✅ Downloaded: {dest_name}")
                            else:
                                print(f"            ❌ Download failed for file {i+1}")
                                
                        except Exception as e:
                            print(f"            ❌ Error downloading file {i+1}: {e}")
                    
                    # Close manuscript window and return to main
                    if len(self.driver.window_handles) > 1:
                        self.driver.close()
                        self.driver.switch_to.window(self.main_window)
                    
                    print(f"      ✅ Downloaded {len(files_downloaded)} files for {ms_id}")
                    
                except Exception as e:
                    print(f"      ❌ Error accessing files for {ms_id}: {e}")
                    # Make sure we're back on main window
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
        report_path = self.dirs['data'] / "siam_complete_report.md"
        
        with open(report_path, 'w') as f:
            f.write("# SIAM Complete Extraction Report\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Statistics
            total_referees = sum(len(ms['referees']) for ms in manuscripts)
            refs_with_emails = sum(1 for ms in manuscripts for ref in ms['referees'] if ref.get('email'))
            total_files = sum(
                (1 if ms['files']['manuscript'] else 0) +
                (1 if ms['files']['cover_letter'] else 0) +
                len(ms['files']['reports'])
                for ms in manuscripts
            )
            
            f.write(f"**Total Manuscripts**: {len(manuscripts)}\n")
            f.write(f"**Total Referees**: {total_referees}\n")
            f.write(f"**Referee Emails Found**: {refs_with_emails}\n")
            f.write(f"**Files Downloaded**: {total_files}\n\n")
            
            f.write("## Manuscripts\n\n")
            
            for ms in manuscripts:
                f.write(f"### {ms['manuscript_id']}\n")
                f.write(f"**Title**: {ms['title']}\n")
                f.write(f"**Corresponding Editor**: {ms['corresponding_editor']}\n")
                f.write(f"**Associate Editor**: {ms['associate_editor']}\n")
                f.write(f"**Submitted**: {ms['submission_date']}\n")
                f.write(f"**Days in System**: {ms['days_in_system']}\n\n")
                
                f.write("**Referees**:\n")
                for ref in ms['referees']:
                    status = "✅" if ref.get('has_report') else "⏳"
                    f.write(f"- {status} **{ref['full_name']}**")
                    if ref.get('email'):
                        f.write(f" ({ref['email']})")
                    else:
                        f.write(" (no email)")
                    f.write("\n")
                    
                    if ref.get('due_date'):
                        f.write(f"  - Due: {ref['due_date']}")
                        if ref.get('received_date'):
                            f.write(f", Received: {ref['received_date']}")
                        f.write("\n")
                
                f.write("\n**Files**:\n")
                files = ms['files']
                if files['manuscript']:
                    f.write(f"- ✅ Manuscript: {files['manuscript']}\n")
                else:
                    f.write(f"- ❌ Manuscript: Not downloaded\n")
                    
                if files['cover_letter']:
                    f.write(f"- ✅ Cover Letter: {files['cover_letter']}\n")
                else:
                    f.write(f"- ❌ Cover Letter: Not downloaded\n")
                    
                if files['reports']:
                    for report in files['reports']:
                        f.write(f"- ✅ Report: {report}\n")
                else:
                    f.write(f"- ❌ Reports: None downloaded\n")
                
                f.write("\n---\n\n")
        
        print(f"   ✅ JSON saved to: {json_path}")
        print(f"   ✅ Report saved to: {report_path}")
    
    def run(self):
        """Run the complete SIAM extraction following the correct pattern."""
        print("\n🚀 STARTING CORRECT SIAM EXTRACTION")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Setup
            self.setup_driver()
            
            # Authenticate
            if not self.authenticate_sicon():
                print("❌ Authentication failed")
                return
            
            # Navigate to All Pending Manuscripts table
            if not self.navigate_to_all_pending():
                print("❌ Could not navigate to All Pending Manuscripts")
                return
            
            # Extract manuscripts and get referee details by clicking referee names
            manuscripts = self.extract_manuscripts_and_referees()
            
            if not manuscripts:
                print("❌ No manuscripts found")
                return
            
            # Download files by clicking manuscript IDs
            manuscripts = self.download_manuscript_files(manuscripts)
            
            # Create final report
            self.create_final_report(manuscripts)
            
            print(f"\n✅ Complete extraction finished!")
            print(f"📊 Manuscripts: {len(manuscripts)}")
            print(f"👥 Referees: {sum(len(ms['referees']) for ms in manuscripts)}")
            print(f"📧 Emails: {sum(1 for ms in manuscripts for ref in ms['referees'] if ref.get('email'))}")
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
    extractor = CorrectSIAMExtractor()
    extractor.run()


if __name__ == "__main__":
    main()
