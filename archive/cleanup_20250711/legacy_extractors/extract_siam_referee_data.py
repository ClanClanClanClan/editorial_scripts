#!/usr/bin/env python3
"""
SIAM Referee Data Extractor - focuses on getting complete referee information
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


class SIAMRefereeExtractor:
    """Extract complete referee data from SIAM All Pending Manuscripts view."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.main_window = None
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_referee_data_{timestamp}')
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
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
        
        # Check if already authenticated by looking for logout link
        page_source = self.driver.page_source
        if "logout" in page_source.lower() and "login name" not in page_source.lower():
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
                print("   Clicking ORCID link...")
                self.driver.execute_script("arguments[0].click();", orcid_links[0])
                time.sleep(5)
                
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
                    
                    print("   ⏳ Waiting for authentication...")
                    
                    # Wait for redirect
                    timeout = time.time() + 30
                    while time.time() < timeout:
                        current_url = self.driver.current_url
                        if 'sicon.siam.org' in current_url and 'orcid.org' not in current_url:
                            print("   ✅ Authentication successful!")
                            time.sleep(3)
                            self.handle_popups()
                            self.save_screenshot("02_authenticated")
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
    
    def navigate_to_all_pending_direct(self):
        """Navigate directly to All Pending Manuscripts using known URL pattern."""
        print("\n📋 Navigating to All Pending Manuscripts...")
        
        # Based on successful extractions, try the direct URL pattern
        # First go to home to establish session
        home_url = "http://sicon.siam.org/cgi-bin/main.plex?form_type=home"
        self.driver.get(home_url)
        time.sleep(3)
        self.handle_popups()
        
        # Now try the folder navigation
        try:
            # Try Under Review folder first
            under_review_url = "http://sicon.siam.org/cgi-bin/main.plex?form_type=home&is_open_1400=1"
            print(f"   Trying Under Review: {under_review_url}")
            self.driver.get(under_review_url)
            time.sleep(3)
            self.handle_popups()
            
            # Look for All Pending Manuscripts link
            all_pending_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'folder_id=1800') or contains(text(), 'All Pending')]")
            
            if all_pending_links:
                print("   ✅ Found All Pending Manuscripts link")
                all_pending_links[0].click()
                time.sleep(3)
                self.handle_popups()
                self.save_screenshot("03_all_pending")
                return True
            else:
                # Try direct All Pending URL
                all_pending_url = "http://sicon.siam.org/cgi-bin/main.plex?form_type=home&is_open_1800=1"
                print(f"   Trying direct All Pending: {all_pending_url}")
                self.driver.get(all_pending_url)
                time.sleep(3)
                self.handle_popups()
                self.save_screenshot("03_all_pending_direct")
                return True
                
        except Exception as e:
            print(f"   Error navigating: {e}")
            return False
    
    def extract_referee_table_data(self):
        """Extract referee data from the All Pending Manuscripts table."""
        print("\n📊 Extracting referee data from table...")
        
        manuscripts = []
        
        # Parse the page
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Look for tables that contain manuscript data
        tables = soup.find_all('table')
        print(f"   Found {len(tables)} tables on page")
        
        for i, table in enumerate(tables):
            table_text = table.get_text()
            
            # Check if this table contains manuscript IDs
            if not any(ms_id in table_text for ms_id in ['M172', 'M173', 'M176']):
                continue
            
            print(f"   ✅ Found manuscripts table (table {i+1})")
            
            # Get headers
            header_row = table.find('tr')
            headers = []
            if header_row:
                for th in header_row.find_all(['th', 'td']):
                    headers.append(th.get_text(strip=True))
            
            print(f"   Headers ({len(headers)}): {headers[:8]}...")  # Show first 8 headers
            
            # Process data rows
            rows = table.find_all('tr')[1:]  # Skip header
            
            for row_idx, row in enumerate(rows):
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
                
                print(f"\n   📄 Processing {ms_id} (row {row_idx+1})")
                
                # Extract all cell data
                cell_data = []
                for cell in cells:
                    cell_text = cell.get_text(separator='\n', strip=True)
                    cell_data.append(cell_text)
                
                print(f"      Cell count: {len(cell_data)}")
                
                # Create manuscript data
                ms_data = {
                    'manuscript_id': ms_id,
                    'url': ms_link.get('href', ''),
                    'raw_cell_data': cell_data,
                    'parsed_data': {},
                    'referees': []
                }
                
                # Parse standard fields
                if len(cell_data) > 1:
                    ms_data['parsed_data']['title'] = cell_data[1]
                if len(cell_data) > 2:
                    ms_data['parsed_data']['corresponding_editor'] = cell_data[2]
                if len(cell_data) > 3:
                    ms_data['parsed_data']['associate_editor'] = cell_data[3]
                if len(cell_data) > 4:
                    ms_data['parsed_data']['submission_date'] = cell_data[4]
                if len(cell_data) > 5:
                    ms_data['parsed_data']['days_in_system'] = cell_data[5]
                
                # Parse referee information (typically in columns 6-11)
                if len(cell_data) > 10:
                    # Extract referee data from columns
                    invitees_col = cell_data[6] if len(cell_data) > 6 else ''
                    status_col = cell_data[7] if len(cell_data) > 7 else ''
                    # Skip column 8 (usually "Rec'd" header)
                    due_dates_col = cell_data[9] if len(cell_data) > 9 else ''
                    received_dates_col = cell_data[10] if len(cell_data) > 10 else ''
                    
                    print(f"      Invitees: {invitees_col[:50]}...")
                    print(f"      Status: {status_col[:50]}...")
                    print(f"      Due dates: {due_dates_col[:50]}...")
                    print(f"      Received: {received_dates_col[:50]}...")
                    
                    # Parse referee lines
                    invitees = [i.strip() for i in invitees_col.split('\n') if i.strip()]
                    statuses = [s.strip() for s in status_col.split('\n') if s.strip()]
                    due_dates = [d.strip() for d in due_dates_col.split('\n') if d.strip()]
                    received_dates = [r.strip() for r in received_dates_col.split('\n') if r.strip()]
                    
                    # Create referee entries for accepted referees
                    referee_idx = 0
                    for i, (invitee, status) in enumerate(zip(invitees, statuses)):
                        if status.lower() == 'accepted':
                            ref_data = {
                                'name': invitee,
                                'full_name': invitee,
                                'email': None,
                                'status': 'Active',
                                'invitation_status': status,
                                'due_date': due_dates[referee_idx] if referee_idx < len(due_dates) else '',
                                'received_date': received_dates[referee_idx] if referee_idx < len(received_dates) else '',
                                'has_report': bool(received_dates[referee_idx].strip()) if referee_idx < len(received_dates) else False
                            }
                            
                            # Calculate timing if we have both dates
                            if ref_data['due_date'] and ref_data['received_date']:
                                try:
                                    due = datetime.strptime(ref_data['due_date'], '%Y-%m-%d')
                                    received = datetime.strptime(ref_data['received_date'], '%Y-%m-%d')
                                    days_diff = (received - due).days
                                    ref_data['days_late'] = days_diff
                                    
                                    if days_diff > 0:
                                        print(f"         📊 {invitee}: {days_diff} days late")
                                    else:
                                        print(f"         📊 {invitee}: {abs(days_diff)} days early")
                                except Exception as e:
                                    print(f"         ⚠️ Date parsing error: {e}")
                            
                            ms_data['referees'].append(ref_data)
                            referee_idx += 1
                            print(f"         ✅ Added referee: {invitee}")
                
                manuscripts.append(ms_data)
                print(f"      📊 Total referees for {ms_id}: {len(ms_data['referees'])}")
            
            # Found the manuscripts table, no need to check others
            break
        
        print(f"\n   ✅ Extracted {len(manuscripts)} manuscripts")
        total_referees = sum(len(ms['referees']) for ms in manuscripts)
        print(f"   📊 Total referees found: {total_referees}")
        
        return manuscripts
    
    def extract_referee_emails(self, manuscripts):
        """Extract referee emails by clicking on referee profile links."""
        print("\n🔍 Extracting referee email addresses...")
        
        for ms in manuscripts:
            ms_id = ms['manuscript_id']
            print(f"\n   📄 Processing {ms_id} for referee emails...")
            
            if not ms['url']:
                print(f"      ⚠️ No URL for {ms_id}")
                continue
            
            # Navigate to manuscript page
            full_url = ms['url']
            if not full_url.startswith('http'):
                full_url = f"http://sicon.siam.org/{full_url}"
            
            try:
                self.driver.get(full_url)
                time.sleep(3)
                self.handle_popups()
                
                # Find referee profile links
                referee_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'dump_person_record') or contains(@href, 'person_id')]")
                
                for ref_data in ms['referees']:
                    referee_name = ref_data['name']
                    
                    # Find matching link
                    for link in referee_links:
                        link_text = link.text.strip()
                        if referee_name.lower() in link_text.lower() or link_text.lower() in referee_name.lower():
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
                                    email = email_links[0].get_attribute('href').replace('mailto:', '')
                                    ref_data['email'] = email
                                    print(f"         📧 {referee_name}: {email}")
                                else:
                                    print(f"         ⚠️ {referee_name}: No email found")
                                
                                # Get full name from page title
                                page_title = self.driver.title
                                if referee_name.split()[0].lower() in page_title.lower():
                                    name_part = page_title.split('-')[0].strip()
                                    if len(name_part) > len(referee_name) and len(name_part) < 100:
                                        ref_data['full_name'] = name_part
                                        print(f"         👤 Full name: {name_part}")
                                
                                # Close tab
                                self.driver.close()
                                self.driver.switch_to.window(self.main_window)
                                break
                                
                            except Exception as e:
                                print(f"         ❌ Error getting {referee_name} details: {e}")
                                # Make sure we're back on main window
                                if len(self.driver.window_handles) > 1:
                                    self.driver.close()
                                self.driver.switch_to.window(self.main_window)
                
            except Exception as e:
                print(f"      ❌ Error processing {ms_id}: {e}")
        
        return manuscripts
    
    def create_summary_report(self, manuscripts):
        """Create comprehensive summary report."""
        print("\n📊 Creating summary report...")
        
        # Save JSON data
        results = {
            'extraction_time': datetime.now().isoformat(),
            'total_manuscripts': len(manuscripts),
            'total_referees': sum(len(ms['referees']) for ms in manuscripts),
            'manuscripts': manuscripts
        }
        
        json_path = self.dirs['data'] / 'referee_extraction_complete.json'
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Create markdown report
        report_path = self.dirs['data'] / "referee_extraction_report.md"
        
        with open(report_path, 'w') as f:
            f.write("# SIAM Referee Data Extraction Report\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Total Manuscripts**: {len(manuscripts)}\n")
            
            total_referees = sum(len(ms.get('referees', [])) for ms in manuscripts)
            refs_with_reports = sum(1 for ms in manuscripts for ref in ms.get('referees', []) if ref.get('has_report'))
            refs_with_emails = sum(1 for ms in manuscripts for ref in ms.get('referees', []) if ref.get('email'))
            
            f.write(f"**Total Referees**: {total_referees}\n")
            f.write(f"**Reports Received**: {refs_with_reports}\n")
            f.write(f"**Emails Found**: {refs_with_emails}\n\n")
            
            f.write("## Summary Statistics\n\n")
            
            # Calculate timing statistics
            late_count = 0
            early_count = 0
            for ms in manuscripts:
                for ref in ms.get('referees', []):
                    if ref.get('days_late') is not None:
                        if ref['days_late'] > 0:
                            late_count += 1
                        else:
                            early_count += 1
            
            f.write(f"- Reports received late: {late_count}\n")
            f.write(f"- Reports received early: {early_count}\n")
            f.write(f"- All manuscripts handled by: Associate Editor Dylan Possamaï\n\n")
            
            f.write("## Manuscripts\n\n")
            
            for ms in manuscripts:
                f.write(f"### {ms['manuscript_id']}\n")
                
                parsed = ms.get('parsed_data', {})
                f.write(f"**Title**: {parsed.get('title', 'N/A')}\n")
                f.write(f"**Corresponding Editor**: {parsed.get('corresponding_editor', 'N/A')}\n")
                f.write(f"**Associate Editor**: {parsed.get('associate_editor', 'N/A')}\n")
                f.write(f"**Submitted**: {parsed.get('submission_date', 'N/A')}\n")
                f.write(f"**Days in System**: {parsed.get('days_in_system', 'N/A')}\n\n")
                
                f.write("**Referees**:\n")
                for ref in ms.get('referees', []):
                    status = "✅" if ref.get('has_report') else "⏳"
                    f.write(f"- {status} **{ref['full_name']}**")
                    if ref.get('email'):
                        f.write(f" ({ref['email']})")
                    f.write("\n")
                    
                    if ref.get('due_date'):
                        f.write(f"  - Due: {ref['due_date']}")
                        if ref.get('received_date'):
                            f.write(f", Received: {ref['received_date']}")
                            if ref.get('days_late') is not None:
                                days = ref['days_late']
                                if days > 0:
                                    f.write(f" (**{days} days late**)")
                                else:
                                    f.write(f" (**{abs(days)} days early**)")
                        f.write("\n")
                
                f.write("\n---\n\n")
        
        print(f"   ✅ JSON saved to: {json_path}")
        print(f"   ✅ Report saved to: {report_path}")
    
    def run(self):
        """Run the complete referee data extraction."""
        print("\n🚀 STARTING SIAM REFEREE DATA EXTRACTION")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Setup
            self.setup_driver()
            
            # Authenticate
            if not self.authenticate_sicon():
                print("❌ Authentication failed")
                return
            
            # Navigate to All Pending Manuscripts
            if not self.navigate_to_all_pending_direct():
                print("❌ Could not navigate to All Pending Manuscripts")
                return
            
            # Extract referee data from table
            manuscripts = self.extract_referee_table_data()
            
            if not manuscripts:
                print("❌ No manuscripts found")
                return
            
            # Extract referee emails
            manuscripts = self.extract_referee_emails(manuscripts)
            
            # Create summary report
            self.create_summary_report(manuscripts)
            
            print(f"\n✅ Referee data extraction complete!")
            print(f"📊 Found {len(manuscripts)} manuscripts")
            print(f"👥 Total referees: {sum(len(ms.get('referees', [])) for ms in manuscripts)}")
            print(f"📧 Emails found: {sum(1 for ms in manuscripts for ref in ms.get('referees', []) if ref.get('email'))}")
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
    extractor = SIAMRefereeExtractor()
    extractor.run()


if __name__ == "__main__":
    main()
