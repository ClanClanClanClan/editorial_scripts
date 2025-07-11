#!/usr/bin/env python3
"""
Complete SIAM extraction v2 - handles privacy popup and gets full referee data
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
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup


class CompleteSIAMExtractorV2:
    """Complete SIAM extractor with full referee data extraction."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.main_window = None
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_complete_final_v2_{timestamp}')
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
    
    def setup_driver(self, headless=False):
        """Setup Chrome WebDriver."""
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument('--headless')
        
        # Download configuration
        prefs = {
            "download.default_directory": str(self.download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Additional options
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(options=chrome_options)
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
        self.save_screenshot("01_sicon_home")
        
        # Check if already authenticated
        if "logout" in self.driver.page_source.lower():
            print("✅ Already authenticated!")
            return True
        
        # Find and click ORCID link
        try:
            orcid_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'orcid') or contains(@href, 'sso_site_redirect')]")
            
            if not orcid_links:
                # Try clicking the ORCID icon
                orcid_imgs = self.driver.find_elements(By.XPATH, "//img[@title='ORCID']")
                if orcid_imgs:
                    orcid_parent = orcid_imgs[0].find_element(By.XPATH, "..")
                    if orcid_parent.tag_name == 'a':
                        orcid_links = [orcid_parent]
            
            if orcid_links:
                self.driver.execute_script("arguments[0].click();", orcid_links[0])
                time.sleep(3)
                
                # Wait for ORCID page
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
                    
                    # Wait for redirect
                    timeout = time.time() + 30
                    while time.time() < timeout:
                        if 'sicon.siam.org' in self.driver.current_url and 'orcid.org' not in self.driver.current_url:
                            print("   ✅ Authentication successful!")
                            time.sleep(3)
                            return True
                        time.sleep(1)
                    
                    print("❌ Authentication timeout")
                    return False
                else:
                    print("❌ Failed to navigate to ORCID")
                    return False
            else:
                print("❌ No ORCID link found")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def navigate_to_all_pending(self):
        """Navigate to All Pending Manuscripts view."""
        print("\n📋 Navigating to All Pending Manuscripts...")
        
        # Go to home page first
        self.driver.get("http://sicon.siam.org/cgi-bin/main.plex?form_type=home")
        time.sleep(3)
        self.handle_popups()
        
        # Look for Under Review folder first
        try:
            under_review_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'folder_id=1400')]")
            if under_review_links:
                print("   Found Under Review folder")
                under_review_links[0].click()
                time.sleep(3)
                self.handle_popups()
        except Exception as e:
            print(f"   Could not find Under Review folder: {e}")
        
        # Now look for All Pending Manuscripts
        try:
            all_pending_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'folder_id=1800') or contains(text(), 'All Pending')]")
            if all_pending_links:
                print("   ✅ Found All Pending Manuscripts")
                all_pending_links[0].click()
                time.sleep(3)
                self.handle_popups()
                self.save_screenshot("02_all_pending")
                return True
        except Exception as e:
            print(f"   Error clicking All Pending: {e}")
        
        print("❌ Could not navigate to All Pending Manuscripts")
        return False
    
    def extract_manuscripts_from_table(self):
        """Extract manuscripts from the All Pending Manuscripts table."""
        print("\n📊 Extracting manuscripts from table...")
        
        manuscripts = []
        
        # Parse the page
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Find the main table with manuscript data
        for table in soup.find_all('table'):
            # Look for a table that contains manuscript IDs
            table_text = table.get_text()
            if not any(ms_id in table_text for ms_id in ['M172', 'M173', 'M176']):
                continue
            
            print("   ✅ Found manuscripts table")
            
            # Get table headers
            headers = []
            header_row = table.find('tr')
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
            
            print(f"   Table headers: {headers[:5]}...")  # Show first 5 headers
            
            # Process data rows
            rows = table.find_all('tr')[1:]  # Skip header row
            
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
                
                # Extract data from all cells
                cell_data = [cell.get_text(strip=True) for cell in cells]
                
                # Create manuscript data structure
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
                
                # Parse referee information from table columns
                if len(cell_data) > 10:
                    # Invitees column (usually column 6)
                    invitees_text = cell_data[6] if len(cell_data) > 6 else ''
                    status_text = cell_data[7] if len(cell_data) > 7 else ''
                    due_dates_text = cell_data[9] if len(cell_data) > 9 else ''
                    received_dates_text = cell_data[10] if len(cell_data) > 10 else ''
                    
                    # Split by lines to get individual referees
                    invitees = [i.strip() for i in invitees_text.split('\n') if i.strip()]
                    statuses = [s.strip() for s in status_text.split('\n') if s.strip()]
                    due_dates = [d.strip() for d in due_dates_text.split('\n') if d.strip()]
                    received_dates = [r.strip() for r in received_dates_text.split('\n') if r.strip()]
                    
                    # Create referee entries for accepted referees
                    referee_index = 0
                    for i, (invitee, status) in enumerate(zip(invitees, statuses)):
                        if status.lower() == 'accepted':
                            ref_data = {
                                'name': invitee,
                                'full_name': invitee,
                                'email': None,
                                'status': 'Active',
                                'due_date': due_dates[referee_index] if referee_index < len(due_dates) else '',
                                'received_date': received_dates[referee_index] if referee_index < len(received_dates) else '',
                                'has_report': bool(received_dates[referee_index].strip()) if referee_index < len(received_dates) else False
                            }
                            
                            # Calculate days late/early if we have both dates
                            if ref_data['due_date'] and ref_data['received_date']:
                                try:
                                    from datetime import datetime
                                    due_date = datetime.strptime(ref_data['due_date'], '%Y-%m-%d')
                                    received_date = datetime.strptime(ref_data['received_date'], '%Y-%m-%d')
                                    days_diff = (received_date - due_date).days
                                    ref_data['days_late'] = days_diff
                                    if days_diff > 0:
                                        print(f"      {invitee}: {days_diff} days late")
                                    else:
                                        print(f"      {invitee}: {abs(days_diff)} days early")
                                except:
                                    pass
                            
                            ms_data['referees'].append(ref_data)
                            referee_index += 1
                
                print(f"      Found {len(ms_data['referees'])} referees")
                manuscripts.append(ms_data)
        
        print(f"\n   ✅ Extracted {len(manuscripts)} manuscripts")
        return manuscripts
    
    def extract_referee_details(self, manuscript):
        """Extract detailed referee information by clicking on referee names."""
        ms_id = manuscript['manuscript_id']
        print(f"\n   🔍 Getting referee details for {ms_id}...")
        
        # Navigate to manuscript page
        if manuscript['url']:
            full_url = manuscript['url']
            if not full_url.startswith('http'):
                full_url = f"http://sicon.siam.org/{full_url}"
            
            self.driver.get(full_url)
            time.sleep(3)
            self.handle_popups()
        
        # Find referee links on the page
        referee_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'dump_person_record') or contains(@href, 'person_id')]")
        
        for i, ref_data in enumerate(manuscript['referees']):
            referee_name = ref_data['name']
            
            # Try to find the corresponding link
            for link in referee_links:
                if referee_name.lower() in link.text.lower():
                    try:
                        href = link.get_attribute('href')
                        
                        # Open in new tab
                        self.driver.execute_script("window.open('');")
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                        self.driver.get(href)
                        time.sleep(2)
                        
                        # Extract email
                        email_links = self.driver.find_elements(By.XPATH, "//a[starts-with(@href, 'mailto:')]")
                        if email_links:
                            ref_data['email'] = email_links[0].get_attribute('href').replace('mailto:', '')
                            print(f"         📧 {referee_name}: {ref_data['email']}")
                        
                        # Extract full name from page title
                        page_title = self.driver.title
                        if referee_name.split()[0].lower() in page_title.lower():
                            name_part = page_title.split('-')[0].strip()
                            if len(name_part) > len(referee_name):
                                ref_data['full_name'] = name_part
                                print(f"         👤 Full name: {name_part}")
                        
                        # Close tab
                        self.driver.close()
                        self.driver.switch_to.window(self.main_window)
                        break
                        
                    except Exception as e:
                        print(f"         ❌ Error getting details for {referee_name}: {e}")
                        # Make sure we're back on main window
                        if len(self.driver.window_handles) > 1:
                            self.driver.close()
                        self.driver.switch_to.window(self.main_window)
        
        return manuscript
    
    def create_summary_report(self, manuscripts):
        """Create comprehensive summary report."""
        print("\n📊 Creating summary report...")
        
        # Create markdown report
        report_path = self.dirs['data'] / "extraction_report.md"
        
        with open(report_path, 'w') as f:
            f.write("# SIAM Complete Extraction Report\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Total Manuscripts**: {len(manuscripts)}\n\n")
            
            # Statistics
            total_referees = sum(len(ms.get('referees', [])) for ms in manuscripts)
            refs_with_reports = sum(1 for ms in manuscripts for ref in ms.get('referees', []) if ref.get('has_report'))
            refs_with_emails = sum(1 for ms in manuscripts for ref in ms.get('referees', []) if ref.get('email'))
            
            f.write(f"**Total Referees**: {total_referees}\n")
            f.write(f"**Reports Received**: {refs_with_reports}\n")
            f.write(f"**Emails Found**: {refs_with_emails}\n\n")
            
            f.write("## Manuscripts\n\n")
            
            for ms in manuscripts:
                f.write(f"### {ms['manuscript_id']}\n")
                f.write(f"**Title**: {ms.get('title', 'N/A')}\n")
                f.write(f"**Corresponding Editor**: {ms.get('corresponding_editor', 'N/A')}\n")
                f.write(f"**Associate Editor**: {ms.get('associate_editor', 'N/A')}\n")
                f.write(f"**Submitted**: {ms.get('submission_date', 'N/A')}\n")
                f.write(f"**Days in System**: {ms.get('days_in_system', 'N/A')}\n")
                f.write(f"**Stage**: {ms.get('current_stage', 'N/A')}\n\n")
                
                f.write("**Referees**:\n")
                for ref in ms.get('referees', []):
                    status = "✅" if ref.get('has_report') else "⏳"
                    f.write(f"- {status} {ref['full_name']}")
                    if ref.get('email'):
                        f.write(f" ({ref['email']})")
                    f.write("\n")
                    
                    if ref.get('due_date'):
                        f.write(f"  - Due: {ref['due_date']}")
                        if ref.get('received_date'):
                            f.write(f", Received: {ref['received_date']}")
                            if ref.get('days_late'):
                                days = ref['days_late']
                                if days > 0:
                                    f.write(f" ({days} days late)")
                                else:
                                    f.write(f" ({abs(days)} days early)")
                        f.write("\n")
                
                f.write("\n---\n\n")
        
        print(f"   ✅ Report saved to: {report_path}")
    
    def run(self):
        """Run the complete extraction."""
        print("\n🚀 STARTING COMPLETE SIAM EXTRACTION V2")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Setup
            self.setup_driver(headless=False)
            
            # Authenticate
            if not self.authenticate_sicon():
                print("❌ Authentication failed")
                return
            
            # Navigate to All Pending Manuscripts
            if not self.navigate_to_all_pending():
                print("❌ Could not navigate to All Pending Manuscripts")
                return
            
            # Extract manuscripts
            manuscripts = self.extract_manuscripts_from_table()
            
            if not manuscripts:
                print("❌ No manuscripts found")
                return
            
            # Extract detailed referee information
            print("\n🔍 Extracting detailed referee information...")
            for ms in manuscripts:
                try:
                    self.extract_referee_details(ms)
                except Exception as e:
                    print(f"   ❌ Error extracting referee details for {ms['manuscript_id']}: {e}")
            
            # Save results
            results = {
                'extraction_time': datetime.now().isoformat(),
                'total_manuscripts': len(manuscripts),
                'manuscripts': manuscripts
            }
            
            with open(self.dirs['data'] / 'manuscripts_complete.json', 'w') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            # Create summary report
            self.create_summary_report(manuscripts)
            
            print(f"\n✅ Extraction complete!")
            print(f"📁 Found {len(manuscripts)} manuscripts")
            print(f"📊 Total referees: {sum(len(ms.get('referees', [])) for ms in manuscripts)}")
            print(f"📄 Data saved to: {self.dirs['data']}")
            
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
    extractor = CompleteSIAMExtractorV2()
    extractor.run()


if __name__ == "__main__":
    main()
