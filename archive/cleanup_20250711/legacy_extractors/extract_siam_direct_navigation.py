#!/usr/bin/env python3
"""
SIAM Extractor - Direct navigation to All Pending Manuscripts
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


class DirectNavigationSIAMExtractor:
    """SIAM extractor with direct navigation to All Pending Manuscripts."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.main_window = None
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_direct_{timestamp}')
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
        self.save_screenshot("01_sicon_initial")
        
        # More accurate authentication check
        page_source = self.driver.page_source
        # Check for actual authenticated elements
        if "logout" in page_source.lower() and "welcome to siam journal" not in page_source.lower():
            print("✅ Already authenticated!")
            return True
        
        print("   Need to authenticate via ORCID")
        
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
                    self.save_screenshot("02_orcid_page")
                    
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
                        
                        # Check if we're back on SICON and authenticated
                        if ('sicon.siam.org' in current_url and 
                            'orcid.org' not in current_url and
                            'welcome to siam journal' not in page_content.lower()):
                            print("   ✅ Authentication successful!")
                            time.sleep(3)
                            self.handle_popups()
                            self.save_screenshot("03_authenticated_home")
                            return True
                        time.sleep(1)
                    
                    print("❌ Authentication timeout - still on login page")
                    self.save_screenshot("auth_timeout")
                    return False
            else:
                print("❌ No ORCID link found")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            self.save_screenshot("auth_error")
            return False
    
    def navigate_directly_to_all_pending(self):
        """Navigate directly to All Pending Manuscripts link (not through Under Review)."""
        print("\n📋 Looking for direct All Pending Manuscripts link...")
        
        # First ensure we're on the authenticated home page
        self.driver.get("http://sicon.siam.org/cgi-bin/main.plex?form_type=home")
        time.sleep(3)
        self.handle_popups()
        self.save_screenshot("04_home_page")
        
        # Look for ALL links on the page
        all_links = self.driver.find_elements(By.TAG_NAME, "a")
        print(f"   Found {len(all_links)} total links on page")
        
        # Check each link for "All Pending" text
        pending_links = []
        for link in all_links:
            link_text = link.text.strip()
            href = link.get_attribute('href') or ''
            
            if 'all pending' in link_text.lower():
                pending_links.append((link_text, href, link))
                print(f"      Found: '{link_text}' -> {href}")
        
        if pending_links:
            # Click the first "All Pending Manuscripts" link
            link_text, href, link_element = pending_links[0]
            print(f"   ✅ Clicking on: '{link_text}'")
            
            try:
                link_element.click()
                time.sleep(5)
                self.handle_popups()
                self.save_screenshot("05_all_pending_table")
                
                # Verify we're on the right page by checking for manuscript IDs
                page_text = self.driver.page_source
                if any(ms_id in page_text for ms_id in ['M172838', 'M173704', 'M173889', 'M176733']):
                    print("   ✅ Successfully reached All Pending Manuscripts table!")
                    return True
                else:
                    print("   ⚠️ Reached page but no manuscripts found")
                    return False
                    
            except Exception as e:
                print(f"   ❌ Error clicking link: {e}")
                return False
        else:
            print("   ❌ No 'All Pending Manuscripts' link found")
            
            # Try alternative approaches
            print("   Trying alternative link patterns...")
            
            # Look for folder_id=1800 pattern
            folder_links = [link for link in all_links if 'folder_id=1800' in (link.get_attribute('href') or '')]
            if folder_links:
                print(f"   Found folder_id=1800 link")
                try:
                    folder_links[0].click()
                    time.sleep(3)
                    self.save_screenshot("05_folder_1800")
                    return True
                except:
                    pass
            
            # Direct URL approach
            print("   Trying direct URL...")
            direct_url = "http://sicon.siam.org/cgi-bin/main.plex?form_type=home&is_open_1800=1"
            self.driver.get(direct_url)
            time.sleep(3)
            self.save_screenshot("05_direct_url")
            
            # Check if we got the table
            page_text = self.driver.page_source
            if any(ms_id in page_text for ms_id in ['M172838', 'M173704']):
                print("   ✅ Direct URL worked!")
                return True
            
            return False
    
    def extract_and_click_referees(self):
        """Extract manuscripts and click on referee names to get emails and full names."""
        print("\n📊 Extracting manuscripts and clicking referee names...")
        
        manuscripts = []
        
        # Parse the All Pending Manuscripts table
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
                
                # Extract referee info from columns
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
                print(f"      Found {len(ms_data['referees'])} accepted referees: {[r['name'] for r in ms_data['referees']]}")
            
            break
        
        print(f"\n   ✅ Found {len(manuscripts)} manuscripts with {sum(len(ms['referees']) for ms in manuscripts)} total referees")
        
        # Now click on each referee name to get full details
        print("\n🔍 Clicking on referee names to get emails and full names...")
        
        for ms in manuscripts:
            for ref in ms['referees']:
                referee_name = ref['name']
                print(f"\n      👤 Getting details for '{referee_name}'...")
                
                # Find referee name link in the current page
                referee_links = self.driver.find_elements(By.XPATH, f"//a[text()='{referee_name}']")
                
                # Try partial matches if exact not found
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
                                print(f"         ⚠️ No email found")
                                
                                # Try to find email in text
                                page_text = self.driver.page_source
                                email_pattern = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
                                emails = email_pattern.findall(page_text)
                                if emails:
                                    # Filter out common system emails
                                    personal_emails = [e for e in emails if not any(skip in e.lower() for skip in ['noreply', 'donotreply', 'siam.org', 'example'])]
                                    if personal_emails:
                                        ref['email'] = personal_emails[0]
                                        print(f"         ✅ Found email in text: {personal_emails[0]}")
                            
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
    
    def download_pdfs_by_clicking_manuscript_ids(self, manuscripts):
        """Download PDFs by clicking on manuscript IDs to access file pages."""
        print("\n📎 Downloading PDFs by clicking manuscript IDs...")
        
        for ms in manuscripts:
            ms_id = ms['manuscript_id']
            print(f"\n   📄 Downloading files for {ms_id}...")
            
            # Navigate back to All Pending table if needed
            if not any(ms_id in self.driver.page_source for ms_id in ['M172838', 'M173704']):
                if not self.navigate_directly_to_all_pending():
                    print(f"      ❌ Could not navigate back to table")
                    continue
            
            # Find and click the manuscript ID link
            ms_id_links = self.driver.find_elements(By.XPATH, f"//a[text()='{ms_id}']")
            
            # Try partial match if exact not found
            if not ms_id_links:
                ms_id_links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{ms_id}')]")
            
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
                    
                    # Look for "Save File As" links (as shown in user's example)
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
                            for _ in range(15):  # Wait up to 15 seconds
                                time.sleep(1)
                                downloaded_files = list(self.download_dir.glob("*"))
                                downloaded_files = [f for f in downloaded_files if f.is_file()]
                                if downloaded_files:
                                    download_complete = True
                                    break
                            
                            if download_complete:
                                source_file = downloaded_files[0]
                                
                                # Determine file type and destination based on context
                                if 'article file' in context:
                                    dest_name = f"{ms_id}_manuscript.pdf"
                                    dest_path = self.dirs['manuscripts'] / dest_name
                                    ms['files']['manuscript'] = dest_name
                                elif 'cover letter' in context:
                                    dest_name = f"{ms_id}_cover_letter.pdf"
                                    dest_path = self.dirs['cover_letters'] / dest_name
                                    ms['files']['cover_letter'] = dest_name
                                elif 'referee' in context and 'review' in context:
                                    # Extract referee number if possible
                                    ref_match = re.search(r'referee\s*#?(\d+)', context)
                                    ref_num = ref_match.group(1) if ref_match else str(len(ms['files']['reports']) + 1)
                                    dest_name = f"{ms_id}_referee_{ref_num}_report.pdf"
                                    dest_path = self.dirs['reports'] / dest_name
                                    ms['files']['reports'].append(dest_name)
                                else:
                                    # Default naming
                                    dest_name = f"{ms_id}_file_{i+1}.pdf"
                                    dest_path = self.output_dir / dest_name
                                
                                # Move file to correct location
                                shutil.move(str(source_file), str(dest_path))
                                files_downloaded += 1
                                print(f"            ✅ Downloaded: {dest_name}")
                            else:
                                print(f"            ❌ Download timeout for file {i+1}")
                                
                        except Exception as e:
                            print(f"            ❌ Error downloading file {i+1}: {e}")
                    
                    # Close manuscript window and return to main
                    if len(self.driver.window_handles) > 1:
                        self.driver.close()
                        self.driver.switch_to.window(self.main_window)
                    
                    print(f"      ✅ Downloaded {files_downloaded} files for {ms_id}")
                    
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
            
            f.write("## Detailed Results\n\n")
            
            for ms in manuscripts:
                f.write(f"### {ms['manuscript_id']}\n")
                f.write(f"**Title**: {ms['title']}\n")
                f.write(f"**Corresponding Editor**: {ms['corresponding_editor']}\n")
                f.write(f"**Associate Editor**: {ms['associate_editor']}\n")
                f.write(f"**Submitted**: {ms['submission_date']} ({ms['days_in_system']} days)\n\n")
                
                f.write("**Referees**:\n")
                for ref in ms['referees']:
                    status = "✅" if ref.get('has_report') else "⏳"
                    f.write(f"- {status} **{ref['full_name']}**")
                    if ref.get('email'):
                        f.write(f" ({ref['email']})")
                    else:
                        f.write(" (no email found)")
                    f.write("\n")
                    
                    if ref.get('due_date'):
                        f.write(f"  - Due: {ref['due_date']}")
                        if ref.get('received_date'):
                            f.write(f", Received: {ref['received_date']}")
                        f.write("\n")
                
                f.write("\n**Files Downloaded**:\n")
                files = ms['files']
                if files['manuscript']:
                    f.write(f"- ✅ Manuscript: {files['manuscript']}\n")
                else:
                    f.write(f"- ❌ Manuscript: Not found/downloaded\n")
                    
                if files['cover_letter']:
                    f.write(f"- ✅ Cover Letter: {files['cover_letter']}\n")
                else:
                    f.write(f"- ❌ Cover Letter: Not found/downloaded\n")
                    
                if files['reports']:
                    for report in files['reports']:
                        f.write(f"- ✅ Report: {report}\n")
                else:
                    f.write(f"- ❌ Reports: None found/downloaded\n")
                
                f.write("\n---\n\n")
        
        print(f"   ✅ JSON saved to: {json_path}")
        print(f"   ✅ Report saved to: {report_path}")
    
    def run(self):
        """Run the complete SIAM extraction with direct navigation."""
        print("\n🚀 STARTING SIAM EXTRACTION WITH DIRECT NAVIGATION")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Setup
            self.setup_driver()
            
            # Authenticate
            if not self.authenticate_sicon():
                print("❌ Authentication failed")
                return
            
            # Navigate directly to All Pending Manuscripts
            if not self.navigate_directly_to_all_pending():
                print("❌ Could not navigate to All Pending Manuscripts")
                return
            
            # Extract manuscripts and click referee names for emails/full names
            manuscripts = self.extract_and_click_referees()
            
            if not manuscripts:
                print("❌ No manuscripts found")
                return
            
            # Download PDFs by clicking manuscript IDs
            manuscripts = self.download_pdfs_by_clicking_manuscript_ids(manuscripts)
            
            # Create final report
            self.create_final_report(manuscripts)
            
            print(f"\n✅ EXTRACTION COMPLETE!")
            print(f"📊 Manuscripts: {len(manuscripts)}")
            print(f"👥 Referees: {sum(len(ms['referees']) for ms in manuscripts)}")
            print(f"📧 Emails found: {sum(1 for ms in manuscripts for ref in ms['referees'] if ref.get('email'))}")
            print(f"📁 Full names: {sum(1 for ms in manuscripts for ref in ms['referees'] if ref.get('full_name') != ref.get('name'))}")
            print(f"📎 Files downloaded: {sum((1 if ms['files']['manuscript'] else 0) + (1 if ms['files']['cover_letter'] else 0) + len(ms['files']['reports']) for ms in manuscripts)}")
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
    extractor = DirectNavigationSIAMExtractor()
    extractor.run()


if __name__ == "__main__":
    main()
