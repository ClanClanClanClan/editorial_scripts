#!/usr/bin/env python3
"""
Enhanced SIAM extraction - gets all referee details and PDFs
"""

import os
import re
import time
import json
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup


class EnhancedSIAMExtractor:
    """Extract all SIAM data including referee details and PDFs."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_enhanced_{timestamp}')
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.dirs = {
            'sicon': {
                'manuscripts': self.output_dir / 'sicon' / 'manuscripts',
                'cover_letters': self.output_dir / 'sicon' / 'cover_letters',
                'reports': self.output_dir / 'sicon' / 'reports',
                'data': self.output_dir / 'sicon' / 'data'
            },
            'sifin': {
                'manuscripts': self.output_dir / 'sifin' / 'manuscripts',
                'cover_letters': self.output_dir / 'sifin' / 'cover_letters',
                'reports': self.output_dir / 'sifin' / 'reports',
                'data': self.output_dir / 'sifin' / 'data'
            }
        }
        
        for journal_dirs in self.dirs.values():
            for dir_path in journal_dirs.values():
                dir_path.mkdir(exist_ok=True, parents=True)
        
        print(f"📁 Output directory: {self.output_dir}")
    
    def setup_driver(self):
        """Setup Chrome WebDriver."""
        chrome_options = Options()
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)
        self.main_window = None
        print("✅ Chrome WebDriver initialized")
    
    def authenticate_orcid(self, journal_url):
        """Authenticate using ORCID."""
        print(f"🔐 Authenticating...")
        
        # Navigate to journal
        self.driver.get(journal_url)
        time.sleep(3)
        self.main_window = self.driver.current_window_handle
        
        # Remove cookie banners
        self.driver.execute_script("""
            var elements = ['#cookie-policy-layer-bg', '#cookie-policy-layer'];
            elements.forEach(function(sel) {
                var els = document.querySelectorAll(sel);
                els.forEach(function(el) { el.remove(); });
            });
            
            var continueBtn = document.getElementById('continue-btn');
            if (continueBtn) continueBtn.click();
        """)
        
        # Check if already authenticated
        if "dpossama" in self.driver.page_source.lower() or "possamaï" in self.driver.page_source.lower():
            print("✅ Already authenticated!")
            return True
        
        # Click ORCID link
        try:
            orcid_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'orcid')]")
            self.driver.execute_script("arguments[0].click();", orcid_link)
            
            # Wait for ORCID page
            self.wait.until(lambda driver: 'orcid.org' in driver.current_url)
            time.sleep(2)
            
            # Fill credentials
            orcid_user = os.getenv("ORCID_USER", "0000-0002-9364-0124")
            orcid_pass = os.getenv("ORCID_PASS", "Hioupy0042%")
            
            username_field = self.driver.find_element(By.ID, "username-input")
            username_field.clear()
            username_field.send_keys(orcid_user)
            
            password_field = self.driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(orcid_pass)
            password_field.send_keys(Keys.RETURN)
            
            print("⏳ Waiting for authentication...")
            
            # Wait for redirect back
            self.wait.until(lambda driver: 'siam.org' in driver.current_url and 'orcid.org' not in driver.current_url)
            time.sleep(3)
            
            print("✅ Successfully authenticated!")
            return True
            
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    def get_referee_details(self, referee_name):
        """Click on referee name to get full details including email."""
        try:
            # Store current URL to return to
            current_url = self.driver.current_url
            
            # Find and click referee link
            referee_links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{referee_name}')]")
            
            for link in referee_links:
                # Check if it's likely a referee link (not a menu item)
                href = link.get_attribute('href')
                if href and 'person' in href:
                    print(f"      🔍 Getting details for {referee_name}...")
                    
                    # Click the link
                    link.click()
                    time.sleep(2)
                    
                    # Switch to new window if opened
                    windows = self.driver.window_handles
                    if len(windows) > 1:
                        self.driver.switch_to.window(windows[-1])
                    
                    # Parse referee details
                    referee_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    
                    # Extract full name
                    full_name = referee_name
                    name_elements = referee_soup.find_all(['h1', 'h2', 'h3'])
                    for elem in name_elements:
                        text = elem.get_text(strip=True)
                        if referee_name.lower() in text.lower() and len(text) > len(referee_name):
                            full_name = text
                            break
                    
                    # Extract email
                    email = None
                    email_links = referee_soup.find_all('a', href=re.compile(r'mailto:'))
                    if email_links:
                        email = email_links[0].get('href').replace('mailto:', '')
                    else:
                        # Look for email pattern in text
                        email_pattern = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
                        for text in referee_soup.stripped_strings:
                            match = email_pattern.search(text)
                            if match:
                                email = match.group()
                                break
                    
                    # Close window if new one was opened
                    if len(windows) > 1:
                        self.driver.close()
                        self.driver.switch_to.window(self.main_window)
                    else:
                        # Navigate back
                        self.driver.get(current_url)
                        time.sleep(1)
                    
                    print(f"         ✅ Full name: {full_name}")
                    if email:
                        print(f"         📧 Email: {email}")
                    
                    return {
                        "full_name": full_name,
                        "email": email
                    }
            
            return {"full_name": referee_name, "email": None}
            
        except Exception as e:
            print(f"         ❌ Error getting referee details: {e}")
            # Make sure we're back on the main window
            self.driver.switch_to.window(self.main_window)
            return {"full_name": referee_name, "email": None}
    
    def download_file_selenium(self, link_element, filename, file_type):
        """Download file by clicking the link."""
        try:
            print(f"      📥 Downloading {file_type}: {filename}")
            
            # Store current URL
            current_url = self.driver.current_url
            
            # Click the download link
            link_element.click()
            time.sleep(3)
            
            # Check if we're on a PDF page
            if self.driver.current_url.endswith('.pdf'):
                # Get the PDF URL
                pdf_url = self.driver.current_url
                
                # Navigate back
                self.driver.back()
                time.sleep(1)
                
                # Download using urllib
                return self.download_file_urllib(pdf_url, filename, file_type)
            else:
                # Look for additional download link
                try:
                    download_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'Download') or contains(text(), 'Save')]")
                    if download_links:
                        download_links[0].click()
                        time.sleep(3)
                except:
                    pass
                
                # Navigate back if needed
                if self.driver.current_url != current_url:
                    self.driver.get(current_url)
                    time.sleep(1)
            
            return True
            
        except Exception as e:
            print(f"         ❌ Download failed: {e}")
            return False
    
    def download_file_urllib(self, url, filename, file_type):
        """Download file using urllib."""
        try:
            # Determine destination directory
            if file_type == "manuscript":
                dest_dir = self.dirs['sicon']['manuscripts']
            elif file_type == "cover_letter":
                dest_dir = self.dirs['sicon']['cover_letters']
            elif file_type == "report":
                dest_dir = self.dirs['sicon']['reports']
            else:
                dest_dir = self.output_dir
            
            filepath = dest_dir / filename
            
            # Get cookies
            cookies = self.driver.get_cookies()
            cookie_str = '; '.join([f"{c['name']}={c['value']}" for c in cookies])
            
            # Create request
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
            req.add_header('Cookie', cookie_str)
            
            # Download
            with urllib.request.urlopen(req) as response:
                with open(filepath, 'wb') as f:
                    f.write(response.read())
            
            print(f"         ✅ Saved: {filepath.name}")
            return True
            
        except Exception as e:
            print(f"         ❌ Error: {e}")
            return False
    
    def extract_manuscript_files(self, ms_id, ms_url):
        """Extract all files for a manuscript by clicking on manuscript ID."""
        try:
            print(f"   📎 Extracting files for {ms_id}...")
            
            # Navigate to manuscript URL
            self.driver.get(ms_url)
            time.sleep(2)
            
            # Click on manuscript ID link to get to files page
            ms_id_links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{ms_id}')]")
            
            for link in ms_id_links:
                # Check if it's the right link (not a navigation link)
                href = link.get_attribute('href')
                if href and 'view_ms' in href:
                    link.click()
                    time.sleep(2)
                    break
            
            # Look for Manuscript Items section
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            files_downloaded = {
                "manuscript": None,
                "cover_letter": None,
                "reports": []
            }
            
            # Find all PDF links
            pdf_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf') or contains(text(), 'PDF')]")
            
            for link in pdf_links:
                try:
                    link_text = link.text.strip().lower()
                    parent_text = link.find_element(By.XPATH, "..").text.lower()
                    
                    # Determine file type based on context
                    if 'cover letter' in parent_text:
                        filename = f"{ms_id}_cover_letter.pdf"
                        if self.download_file_selenium(link, filename, "cover_letter"):
                            files_downloaded["cover_letter"] = filename
                    
                    elif 'article file' in parent_text or 'manuscript' in parent_text:
                        filename = f"{ms_id}_manuscript.pdf"
                        if self.download_file_selenium(link, filename, "manuscript"):
                            files_downloaded["manuscript"] = filename
                    
                    elif 'referee' in parent_text and 'review' in parent_text:
                        # Extract referee number
                        ref_num_match = re.search(r'referee #(\d+)', parent_text)
                        if ref_num_match:
                            ref_num = ref_num_match.group(1)
                            filename = f"{ms_id}_referee_{ref_num}_report.pdf"
                            if self.download_file_selenium(link, filename, "report"):
                                files_downloaded["reports"].append(filename)
                
                except Exception as e:
                    print(f"         ❌ Error processing link: {e}")
                    continue
            
            return files_downloaded
            
        except Exception as e:
            print(f"      ❌ Error extracting files: {e}")
            return {"manuscript": None, "cover_letter": None, "reports": []}
    
    def extract_sicon_complete(self):
        """Extract complete SICON data."""
        print("\n📘 Extracting complete SICON data...")
        
        if not self.authenticate_orcid("http://sicon.siam.org"):
            return []
        
        # Navigate to All Pending Manuscripts
        print("📋 Navigating to All Pending Manuscripts...")
        
        try:
            all_pending_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'is_open_1800=1')]")
            all_pending_url = all_pending_link.get_attribute('href')
        except:
            # Navigate through folders
            under_review_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'is_open_1400=1')]")
            self.driver.get(under_review_link.get_attribute('href'))
            time.sleep(2)
            all_pending_link = self.driver.find_element(By.XPATH, "//a[contains(text(), 'All Pending')]")
            all_pending_url = all_pending_link.get_attribute('href')
        
        self.driver.get(all_pending_url)
        time.sleep(3)
        
        # Parse the manuscripts table
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        manuscripts = []
        
        for table in soup.find_all('table'):
            headers = [th.get_text(strip=True) for th in table.find_all('th')]
            
            if 'Manuscript #' in headers:
                print("✅ Found manuscripts table")
                
                # Get column indices - handle variations in header text
                def find_header_index(headers, patterns):
                    """Find header index with multiple pattern options."""
                    for pattern in patterns:
                        for i, header in enumerate(headers):
                            if pattern.lower() in header.lower():
                                return i
                    return -1
                
                col_indices = {
                    'manuscript': find_header_index(headers, ['Manuscript #', 'Manuscript']),
                    'title': find_header_index(headers, ['Title']),
                    'corresponding_editor': find_header_index(headers, ['Corresponding Editor']),
                    'associate_editor': find_header_index(headers, ['Associate Editor']),
                    'submitted': find_header_index(headers, ['Submitted']),
                    'days': find_header_index(headers, ['Days In System', 'Days In']),
                    'invitees': find_header_index(headers, ['Invitees']),
                    'status': find_header_index(headers, ['Invitee Status', 'Status']),
                    'due_date': find_header_index(headers, ['Review Due Date', 'Due Date']),
                    'receive_date': find_header_index(headers, ['Review Receive Date', 'Receive Date']),
                    'stage': find_header_index(headers, ['Current Stage', 'Stage'])
                }
                
                rows = table.find_all('tr')[1:]  # Skip header
                
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) < 10 or not cells[0].get_text(strip=True).startswith('M'):
                        continue
                    
                    ms_link = cells[0].find('a')
                    if not ms_link:
                        continue
                    
                    ms_id = cells[col_indices['manuscript']].get_text(strip=True)
                    ms_url = ms_link.get('href', '')
                    if not ms_url.startswith('http'):
                        ms_url = f"http://sicon.siam.org/{ms_url}"
                    
                    print(f"\n📄 Processing {ms_id}...")
                    
                    # Extract basic data from table
                    ms_data = {
                        "manuscript_id": ms_id,
                        "url": ms_url,
                        "title": cells[col_indices['title']].get_text(strip=True),
                        "corresponding_editor": cells[col_indices['corresponding_editor']].get_text(strip=True),
                        "associate_editor": cells[col_indices['associate_editor']].get_text(strip=True),
                        "submission_date": cells[col_indices['submitted']].get_text(strip=True),
                        "days_in_system": cells[col_indices['days']].get_text(strip=True),
                        "current_stage": cells[col_indices['stage']].get_text(strip=True),
                        "referees": [],
                        "files": {"manuscript": None, "cover_letter": None, "reports": []}
                    }
                    
                    # Parse referees with their due and received dates
                    invitees = [i.strip() for i in cells[col_indices['invitees']].get_text(separator="\n").split('\n') if i.strip()]
                    statuses = [s.strip() for s in cells[col_indices['status']].get_text(separator="\n").split('\n') if s.strip()]
                    due_dates = [d.strip() for d in cells[col_indices['due_date']].get_text(separator="\n").split('\n') if d.strip()]
                    rcvd_dates = [r.strip() for r in cells[col_indices['receive_date']].get_text(separator="\n").split('\n') if r.strip()]
                    
                    # Process only accepted referees
                    referee_index = 0
                    for i, (invitee, status) in enumerate(zip(invitees, statuses)):
                        if status.lower() == "accepted":
                            ref_data = {
                                "name": invitee,
                                "full_name": invitee,
                                "email": None,
                                "status": "Active",
                                "due_date": due_dates[referee_index] if referee_index < len(due_dates) else "",
                                "received_date": rcvd_dates[referee_index] if referee_index < len(rcvd_dates) else "",
                                "has_report": bool(rcvd_dates[referee_index]) if referee_index < len(rcvd_dates) else False,
                                "days_taken": None
                            }
                            
                            # Calculate days taken if report received
                            if ref_data["has_report"] and ref_data["due_date"] and ref_data["received_date"]:
                                try:
                                    due = datetime.strptime(ref_data["due_date"], "%Y-%m-%d")
                                    received = datetime.strptime(ref_data["received_date"], "%Y-%m-%d")
                                    ref_data["days_taken"] = (received - due).days
                                except:
                                    pass
                            
                            ms_data["referees"].append(ref_data)
                            referee_index += 1
                    
                    print(f"   Found {len(ms_data['referees'])} referees")
                    
                    # Navigate to manuscript page to get referee details and files
                    self.driver.get(ms_url)
                    time.sleep(2)
                    
                    # Get referee full details
                    for ref in ms_data["referees"]:
                        details = self.get_referee_details(ref["name"])
                        ref["full_name"] = details["full_name"]
                        ref["email"] = details["email"]
                    
                    # Extract all files
                    files = self.extract_manuscript_files(ms_id, ms_url)
                    ms_data["files"] = files
                    
                    manuscripts.append(ms_data)
                    
                    # Return to All Pending page
                    self.driver.get(all_pending_url)
                    time.sleep(1)
                
                break
        
        # Save data
        with open(self.dirs['sicon']['data'] / 'manuscripts_complete.json', 'w') as f:
            json.dump(manuscripts, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Extracted {len(manuscripts)} SICON manuscripts with complete details")
        return manuscripts
    
    def create_summary(self, sicon_data):
        """Create detailed extraction summary."""
        summary_path = self.output_dir / "extraction_summary.txt"
        
        with open(summary_path, 'w') as f:
            f.write("="*80 + "\n")
            f.write("SIAM ENHANCED EXTRACTION SUMMARY\n")
            f.write("="*80 + "\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # SICON Summary
            f.write("SICON (SIAM Journal on Control and Optimization)\n")
            f.write("-"*50 + "\n")
            f.write(f"Manuscripts: {len(sicon_data)}\n")
            
            total_refs = sum(len(ms["referees"]) for ms in sicon_data)
            refs_with_reports = sum(1 for ms in sicon_data for ref in ms["referees"] if ref["has_report"])
            refs_with_emails = sum(1 for ms in sicon_data for ref in ms["referees"] if ref.get("email"))
            
            f.write(f"Total referees: {total_refs}\n")
            f.write(f"Reports received: {refs_with_reports}\n")
            f.write(f"Emails found: {refs_with_emails}\n\n")
            
            for ms in sicon_data:
                f.write(f"\n{ms['manuscript_id']} - {ms['title'][:60]}...\n")
                f.write(f"  Corresponding Editor: {ms['corresponding_editor']}\n")
                f.write(f"  Associate Editor: {ms['associate_editor']}\n")
                f.write(f"  Submitted: {ms['submission_date']} ({ms['days_in_system']} days)\n")
                f.write(f"  Stage: {ms['current_stage']}\n")
                f.write(f"  Files: MS={ms['files']['manuscript'] is not None}, ")
                f.write(f"CL={ms['files']['cover_letter'] is not None}, ")
                f.write(f"Reports={len(ms['files']['reports'])}\n")
                f.write("  Referees:\n")
                
                for ref in ms["referees"]:
                    status = "✓" if ref["has_report"] else "⏳"
                    email = ref.get("email", "No email")
                    f.write(f"    {status} {ref['full_name']} ({email})\n")
                    f.write(f"       Due: {ref['due_date']}")
                    if ref["has_report"]:
                        f.write(f", Received: {ref['received_date']}")
                        if ref.get("days_taken") is not None:
                            f.write(f" ({ref['days_taken']} days {'late' if ref['days_taken'] > 0 else 'early'})")
                    f.write("\n")
            
            # File counts
            f.write("\n\nFiles Downloaded:\n")
            f.write("-"*30 + "\n")
            
            manuscript_count = sum(1 for ms in sicon_data if ms['files']['manuscript'])
            cover_count = sum(1 for ms in sicon_data if ms['files']['cover_letter'])
            report_count = sum(len(ms['files']['reports']) for ms in sicon_data)
            
            f.write(f"Manuscript PDFs: {manuscript_count}\n")
            f.write(f"Cover letters: {cover_count}\n")
            f.write(f"Referee reports: {report_count}\n")
            
            f.write(f"\n\nAll files saved to: {self.output_dir}\n")
        
        print(f"\n📊 Summary saved to: {summary_path}")
    
    def run(self):
        """Run the enhanced extraction."""
        print("\n🚀 STARTING ENHANCED SIAM EXTRACTION")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            self.setup_driver()
            
            # Extract SICON with all details
            sicon_data = self.extract_sicon_complete()
            
            # Create detailed summary
            self.create_summary(sicon_data)
            
            print("\n✅ Extraction complete!")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            if self.driver:
                self.driver.quit()
                print("🔄 Browser closed")


def main():
    extractor = EnhancedSIAMExtractor()
    extractor.run()


if __name__ == "__main__":
    main()