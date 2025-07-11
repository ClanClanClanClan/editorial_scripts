#!/usr/bin/env python3
"""
Complete SIAM extraction v3 - with referee details and PDF downloads
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


class CompleteSIAMExtractorV3:
    """Extract all SIAM data including referee details and PDFs."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.main_window = None
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_complete_v3_{timestamp}')
        self.output_dir.mkdir(exist_ok=True)
        
        # Create download directory
        self.download_dir = self.output_dir / 'downloads'
        self.download_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.dirs = {
            'sicon': {
                'manuscripts': self.output_dir / 'sicon' / 'manuscripts',
                'cover_letters': self.output_dir / 'sicon' / 'cover_letters',
                'reports': self.output_dir / 'sicon' / 'reports',
                'data': self.output_dir / 'sicon' / 'data'
            }
        }
        
        for journal_dirs in self.dirs.values():
            for dir_path in journal_dirs.values():
                dir_path.mkdir(exist_ok=True, parents=True)
        
        print(f"📁 Output directory: {self.output_dir}")
    
    def setup_driver(self):
        """Setup Chrome WebDriver with download configuration."""
        chrome_options = Options()
        
        # Configure download settings
        prefs = {
            "download.default_directory": str(self.download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Create driver
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": str(self.download_dir)
        })
        
        self.wait = WebDriverWait(self.driver, 30)
        print("✅ Chrome WebDriver initialized with download support")
    
    def authenticate_orcid(self, journal_url):
        """Authenticate using ORCID."""
        print(f"🔐 Authenticating...")
        
        # Navigate to journal
        self.driver.get(journal_url)
        time.sleep(3)
        self.main_window = self.driver.current_window_handle
        
        # Remove cookie banners
        self.remove_cookie_banners()
        
        # Check if already authenticated
        page_text = self.driver.page_source.lower()
        if "dpossama" in page_text or "possamaï" in page_text or "logout" in page_text:
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
    
    def remove_cookie_banners(self):
        """Remove cookie banners and popups."""
        self.driver.execute_script("""
            var elements = ['#cookie-policy-layer-bg', '#cookie-policy-layer', '.cc-banner'];
            elements.forEach(function(sel) {
                var els = document.querySelectorAll(sel);
                els.forEach(function(el) { 
                    el.style.display = 'none';
                    el.remove(); 
                });
            });
            
            var continueBtn = document.getElementById('continue-btn');
            if (continueBtn) continueBtn.click();
        """)
    
    def extract_referee_details(self, referee_name, manuscript_id):
        """Click on referee name to get full details including email."""
        print(f"      🔍 Getting details for {referee_name}...")
        
        try:
            # Store current URL
            current_url = self.driver.current_url
            
            # Find referee link - try multiple strategies
            referee_link = None
            
            # Strategy 1: Direct text match
            try:
                referee_link = self.driver.find_element(
                    By.XPATH, 
                    f"//a[contains(text(), '{referee_name}') and contains(@href, 'person')]"
                )
            except:
                # Strategy 2: Partial text match
                try:
                    referee_link = self.driver.find_element(
                        By.XPATH, 
                        f"//a[contains(text(), '{referee_name.split()[0]}') and contains(@href, 'person')]"
                    )
                except:
                    pass
            
            if not referee_link:
                # Strategy 3: Find in table cells
                cells = self.driver.find_elements(By.XPATH, "//td")
                for cell in cells:
                    if referee_name in cell.text:
                        links = cell.find_elements(By.TAG_NAME, "a")
                        for link in links:
                            if 'person' in link.get_attribute('href'):
                                referee_link = link
                                break
                        if referee_link:
                            break
            
            if referee_link:
                # Click the link
                href = referee_link.get_attribute('href')
                self.driver.execute_script("window.open(arguments[0], '_blank');", href)
                time.sleep(2)
                
                # Switch to new window
                windows = self.driver.window_handles
                self.driver.switch_to.window(windows[-1])
                
                # Parse referee details
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Extract full name from page title or headers
                full_name = referee_name
                for tag in ['title', 'h1', 'h2', 'h3']:
                    elements = soup.find_all(tag)
                    for elem in elements:
                        text = elem.get_text(strip=True)
                        if referee_name.split()[0].lower() in text.lower():
                            # Found a more complete name
                            if len(text) > len(referee_name) and len(text) < 100:
                                full_name = text
                                # Clean up common suffixes
                                full_name = re.sub(r'\s*-\s*Person.*', '', full_name)
                                full_name = re.sub(r'\s*\|.*', '', full_name)
                                break
                
                # Extract email
                email = None
                
                # Look for mailto links
                email_links = soup.find_all('a', href=re.compile(r'mailto:'))
                if email_links:
                    email = email_links[0].get('href').replace('mailto:', '')
                else:
                    # Look for email pattern in text
                    email_pattern = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
                    text_content = soup.get_text()
                    matches = email_pattern.findall(text_content)
                    if matches:
                        # Filter out common non-personal emails
                        for match in matches:
                            if not any(skip in match.lower() for skip in ['noreply', 'donotreply', 'example']):
                                email = match
                                break
                
                # Close the new window
                self.driver.close()
                self.driver.switch_to.window(self.main_window)
                
                print(f"         ✅ Full name: {full_name}")
                if email:
                    print(f"         📧 Email: {email}")
                
                return {"full_name": full_name, "email": email}
            
            else:
                print(f"         ⚠️  Could not find clickable link for {referee_name}")
                return {"full_name": referee_name, "email": None}
                
        except Exception as e:
            print(f"         ❌ Error: {e}")
            # Make sure we're back on main window
            if len(self.driver.window_handles) > 1:
                self.driver.close()
            self.driver.switch_to.window(self.main_window)
            return {"full_name": referee_name, "email": None}
    
    def wait_for_download(self, timeout=10):
        """Wait for download to complete."""
        end_time = time.time() + timeout
        while time.time() < end_time:
            if any(self.download_dir.glob("*.pdf")):
                # Wait a bit more for download to finish
                time.sleep(1)
                return True
            time.sleep(0.5)
        return False
    
    def download_manuscript_files(self, manuscript_id, manuscript_url):
        """Download all files for a manuscript."""
        print(f"   📎 Downloading files for {manuscript_id}...")
        
        files_downloaded = {
            "manuscript": None,
            "cover_letter": None,
            "reports": []
        }
        
        try:
            # Navigate to manuscript page
            self.driver.get(manuscript_url)
            time.sleep(2)
            self.remove_cookie_banners()
            
            # Click on manuscript ID to get to detailed view
            ms_id_links = self.driver.find_elements(By.XPATH, f"//a[text()='{manuscript_id}']")
            
            for link in ms_id_links:
                # Check if it's the right type of link
                href = link.get_attribute('href')
                if href and ('view_ms' in href or 'display_ms' in href):
                    link.click()
                    time.sleep(3)
                    break
            
            # Now look for file links
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find all rows that might contain files
            file_rows = []
            for row in soup.find_all('tr'):
                row_text = row.get_text().lower()
                if any(keyword in row_text for keyword in ['manuscript', 'article', 'cover letter', 'referee', 'review']):
                    file_rows.append(row)
            
            # Process each file row
            for row in file_rows:
                row_text = row.get_text().lower()
                
                # Find PDF links in this row
                pdf_links = row.find_all('a', href=re.compile(r'\.pdf', re.I))
                
                for link in pdf_links:
                    href = link.get('href')
                    if not href:
                        continue
                    
                    # Make URL absolute
                    if not href.startswith('http'):
                        href = f"https://sicon.siam.org/{href}"
                    
                    # Clear download directory
                    for file in self.download_dir.glob("*.pdf"):
                        file.unlink()
                    
                    # Determine file type and download
                    if 'cover letter' in row_text:
                        print(f"      📥 Downloading cover letter...")
                        # Click the link
                        selenium_link = self.driver.find_element(By.XPATH, f"//a[@href='{link.get('href')}']")
                        selenium_link.click()
                        
                        if self.wait_for_download():
                            # Move file
                            downloaded_files = list(self.download_dir.glob("*.pdf"))
                            if downloaded_files:
                                dest_path = self.dirs['sicon']['cover_letters'] / f"{manuscript_id}_cover_letter.pdf"
                                shutil.move(str(downloaded_files[0]), str(dest_path))
                                files_downloaded["cover_letter"] = dest_path.name
                                print(f"         ✅ Saved: {dest_path.name}")
                    
                    elif any(word in row_text for word in ['manuscript', 'article file']):
                        print(f"      📥 Downloading manuscript...")
                        selenium_link = self.driver.find_element(By.XPATH, f"//a[@href='{link.get('href')}']")
                        selenium_link.click()
                        
                        if self.wait_for_download():
                            downloaded_files = list(self.download_dir.glob("*.pdf"))
                            if downloaded_files:
                                dest_path = self.dirs['sicon']['manuscripts'] / f"{manuscript_id}_manuscript.pdf"
                                shutil.move(str(downloaded_files[0]), str(dest_path))
                                files_downloaded["manuscript"] = dest_path.name
                                print(f"         ✅ Saved: {dest_path.name}")
                    
                    elif 'referee' in row_text and 'review' in row_text:
                        # Extract referee number
                        ref_num_match = re.search(r'referee\s*#?\s*(\d+)', row_text)
                        ref_num = ref_num_match.group(1) if ref_num_match else str(len(files_downloaded["reports"]) + 1)
                        
                        print(f"      📥 Downloading referee {ref_num} report...")
                        selenium_link = self.driver.find_element(By.XPATH, f"//a[@href='{link.get('href')}']")
                        selenium_link.click()
                        
                        if self.wait_for_download():
                            downloaded_files = list(self.download_dir.glob("*.pdf"))
                            if downloaded_files:
                                dest_path = self.dirs['sicon']['reports'] / f"{manuscript_id}_referee_{ref_num}_report.pdf"
                                shutil.move(str(downloaded_files[0]), str(dest_path))
                                files_downloaded["reports"].append(dest_path.name)
                                print(f"         ✅ Saved: {dest_path.name}")
            
        except Exception as e:
            print(f"      ❌ Error downloading files: {e}")
        
        return files_downloaded
    
    def extract_sicon_complete(self):
        """Extract complete SICON data."""
        print("\n📘 Extracting complete SICON data...")
        
        if not self.authenticate_orcid("http://sicon.siam.org"):
            return []
        
        # Navigate to All Pending Manuscripts
        print("📋 Navigating to All Pending Manuscripts...")
        
        # Find the link
        try:
            all_pending_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'is_open_1800=1')]")
            all_pending_url = all_pending_link.get_attribute('href')
        except:
            # Try through Under Review folder
            try:
                under_review = self.driver.find_element(By.XPATH, "//a[contains(@href, 'is_open_1400=1')]")
                self.driver.get(under_review.get_attribute('href'))
                time.sleep(2)
            except:
                pass
            
            # Now find All Pending
            all_pending_link = self.driver.find_element(By.XPATH, "//a[contains(., 'All Pending')]")
            all_pending_url = all_pending_link.get_attribute('href')
        
        self.driver.get(all_pending_url)
        time.sleep(3)
        
        # Parse table
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        manuscripts = []
        
        # Find the manuscripts table
        for table in soup.find_all('table'):
            # Check if this is the right table
            if not any('Manuscript' in str(th) for th in table.find_all('th')):
                continue
            
            print("✅ Found manuscripts table")
            
            # Get headers
            headers = [th.get_text(strip=True) for th in table.find_all('th')]
            
            # Process rows
            rows = table.find_all('tr')[1:]  # Skip header
            
            for row in rows:
                cells = row.find_all('td')
                if not cells or not cells[0].get_text(strip=True).startswith('M'):
                    continue
                
                # Get manuscript link
                ms_link = cells[0].find('a')
                if not ms_link:
                    continue
                
                ms_id = cells[0].get_text(strip=True)
                ms_url = ms_link.get('href', '')
                if not ms_url.startswith('http'):
                    ms_url = f"http://sicon.siam.org/{ms_url}"
                
                print(f"\n📄 Processing {ms_id}...")
                
                # Extract data from table row
                ms_data = {
                    "manuscript_id": ms_id,
                    "url": ms_url,
                    "title": cells[1].get_text(strip=True) if len(cells) > 1 else "",
                    "corresponding_editor": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                    "associate_editor": cells[3].get_text(strip=True) if len(cells) > 3 else "",
                    "submission_date": cells[4].get_text(strip=True) if len(cells) > 4 else "",
                    "days_in_system": cells[5].get_text(strip=True) if len(cells) > 5 else "",
                    "current_stage": cells[-1].get_text(strip=True) if len(cells) > 10 else "",
                    "referees": [],
                    "files": {"manuscript": None, "cover_letter": None, "reports": []}
                }
                
                # Parse referee information
                if len(cells) > 10:
                    invitees_text = cells[6].get_text(separator="\n")
                    status_text = cells[7].get_text(separator="\n")
                    due_dates_text = cells[9].get_text(separator="\n")
                    rcvd_dates_text = cells[10].get_text(separator="\n")
                    
                    invitees = [i.strip() for i in invitees_text.split('\n') if i.strip()]
                    statuses = [s.strip() for s in status_text.split('\n') if s.strip()]
                    due_dates = [d.strip() for d in due_dates_text.split('\n') if d.strip()]
                    rcvd_dates = [r.strip() for r in rcvd_dates_text.split('\n') if r.strip()]
                    
                    # Process accepted referees
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
                                "has_report": bool(rcvd_dates[referee_index]) if referee_index < len(rcvd_dates) else False
                            }
                            ms_data["referees"].append(ref_data)
                            referee_index += 1
                
                print(f"   Found {len(ms_data['referees'])} referees")
                
                # Navigate to manuscript page for detailed extraction
                self.driver.get(ms_url)
                time.sleep(2)
                
                # Extract referee details
                for ref in ms_data["referees"]:
                    details = self.extract_referee_details(ref["name"], ms_id)
                    ref["full_name"] = details["full_name"]
                    ref["email"] = details["email"]
                
                # Download files
                files = self.download_manuscript_files(ms_id, ms_url)
                ms_data["files"] = files
                
                manuscripts.append(ms_data)
                
                # Return to All Pending page
                self.driver.get(all_pending_url)
                time.sleep(1)
            
            break
        
        # Save results
        with open(self.dirs['sicon']['data'] / 'manuscripts_complete.json', 'w') as f:
            json.dump(manuscripts, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Extracted {len(manuscripts)} manuscripts")
        return manuscripts
    
    def create_summary(self, manuscripts):
        """Create detailed summary."""
        summary_path = self.output_dir / "extraction_summary.txt"
        
        with open(summary_path, 'w') as f:
            f.write("="*80 + "\n")
            f.write("SIAM COMPLETE EXTRACTION SUMMARY V3\n")
            f.write("="*80 + "\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(f"Total Manuscripts: {len(manuscripts)}\n")
            
            total_refs = sum(len(ms["referees"]) for ms in manuscripts)
            refs_with_reports = sum(1 for ms in manuscripts for ref in ms["referees"] if ref["has_report"])
            refs_with_emails = sum(1 for ms in manuscripts for ref in ms["referees"] if ref.get("email"))
            
            f.write(f"Total Referees: {total_refs}\n")
            f.write(f"Reports Received: {refs_with_reports}\n")
            f.write(f"Emails Found: {refs_with_emails}\n\n")
            
            # File statistics
            ms_pdfs = sum(1 for ms in manuscripts if ms["files"]["manuscript"])
            cover_letters = sum(1 for ms in manuscripts if ms["files"]["cover_letter"])
            report_pdfs = sum(len(ms["files"]["reports"]) for ms in manuscripts)
            
            f.write(f"Files Downloaded:\n")
            f.write(f"  Manuscript PDFs: {ms_pdfs}\n")
            f.write(f"  Cover Letters: {cover_letters}\n")
            f.write(f"  Referee Reports: {report_pdfs}\n\n")
            
            f.write("-"*80 + "\n\n")
            
            for ms in manuscripts:
                f.write(f"{ms['manuscript_id']} - {ms['title'][:60]}...\n")
                f.write(f"  Corresponding Editor: {ms['corresponding_editor']}\n")
                f.write(f"  Associate Editor: {ms['associate_editor']}\n")
                f.write(f"  Submitted: {ms['submission_date']} ({ms['days_in_system']} days)\n")
                f.write(f"  Stage: {ms['current_stage']}\n")
                f.write(f"  Files: ")
                if ms['files']['manuscript']:
                    f.write("📄 Manuscript ")
                if ms['files']['cover_letter']:
                    f.write("📋 Cover Letter ")
                if ms['files']['reports']:
                    f.write(f"📝 {len(ms['files']['reports'])} Reports")
                f.write("\n")
                
                f.write("  Referees:\n")
                for ref in ms["referees"]:
                    status = "✅" if ref["has_report"] else "⏳"
                    f.write(f"    {status} {ref['full_name']}")
                    if ref.get("email"):
                        f.write(f" ({ref['email']})")
                    else:
                        f.write(" (no email)")
                    f.write("\n")
                    if ref["due_date"]:
                        f.write(f"       Due: {ref['due_date']}")
                        if ref["has_report"]:
                            f.write(f", Received: {ref['received_date']}")
                        f.write("\n")
                f.write("\n")
        
        print(f"\n📊 Summary saved to: {summary_path}")
    
    def run(self):
        """Run the complete extraction."""
        print("\n🚀 STARTING SIAM COMPLETE EXTRACTION V3")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            self.setup_driver()
            
            # Extract SICON data
            manuscripts = self.extract_sicon_complete()
            
            # Create summary
            self.create_summary(manuscripts)
            
            print("\n✅ Extraction complete!")
            print(f"📁 All files saved to: {self.output_dir}")
            
        except Exception as e:
            print(f"❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            if self.driver:
                self.driver.quit()
                print("🔄 Browser closed")


def main():
    extractor = CompleteSIAMExtractorV3()
    extractor.run()


if __name__ == "__main__":
    main()