#!/usr/bin/env python3
"""
Reliable SIAM extraction - extract all data step by step
"""

import os
import re
import time
import json
import urllib.request
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup


class ReliableSIAMExtractor:
    """Reliable extractor for SIAM data."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_reliable_{timestamp}')
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
        print("✅ Chrome WebDriver initialized")
    
    def authenticate_orcid(self, journal_url):
        """Authenticate using ORCID."""
        print(f"🔐 Authenticating...")
        
        # Navigate to journal
        self.driver.get(journal_url)
        time.sleep(3)
        
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
        if "dpossama" in self.driver.page_source.lower():
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
    
    def download_file_urllib(self, url, filepath, cookies_str=""):
        """Download file using urllib with cookies."""
        try:
            print(f"   📥 Downloading: {filepath.name}")
            
            # Create request with cookies
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
            
            if cookies_str:
                req.add_header('Cookie', cookies_str)
            
            # Download file
            with urllib.request.urlopen(req) as response:
                with open(filepath, 'wb') as f:
                    f.write(response.read())
            
            print(f"      ✅ Downloaded: {filepath.name}")
            return True
            
        except Exception as e:
            print(f"      ❌ Download failed: {e}")
            return False
    
    def get_cookies_string(self):
        """Get cookies as string for urllib."""
        cookies = self.driver.get_cookies()
        cookie_str = '; '.join([f"{c['name']}={c['value']}" for c in cookies])
        return cookie_str
    
    def extract_sicon_data(self):
        """Extract SICON data with All Pending Manuscripts view."""
        print("\n📘 Extracting SICON data...")
        
        if not self.authenticate_orcid("http://sicon.siam.org"):
            return []
        
        # Navigate to All Pending Manuscripts
        print("📋 Navigating to All Pending Manuscripts...")
        
        # Find the link
        try:
            # Try direct link first
            all_pending_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'is_open_1800=1')]")
        except:
            # Navigate through Under Review first
            under_review_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'is_open_1400=1')]")
            self.driver.get(under_review_link.get_attribute('href'))
            time.sleep(2)
            all_pending_link = self.driver.find_element(By.XPATH, "//a[contains(text(), 'All Pending')]")
        
        all_pending_url = all_pending_link.get_attribute('href')
        self.driver.get(all_pending_url)
        time.sleep(3)
        
        # Get cookies for downloads
        cookies_str = self.get_cookies_string()
        
        # Parse the table
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        manuscripts = []
        
        # Find the manuscripts table
        for table in soup.find_all('table'):
            headers = [th.get_text(strip=True) for th in table.find_all('th')]
            
            if 'Manuscript #' in headers:
                print("✅ Found manuscripts table")
                
                rows = table.find_all('tr')[1:]  # Skip header
                
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) < 10 or not cells[0].get_text(strip=True).startswith('M'):
                        continue
                    
                    ms_link = cells[0].find('a')
                    if not ms_link:
                        continue
                    
                    ms_id = cells[0].get_text(strip=True)
                    ms_url = ms_link.get('href', '')
                    if not ms_url.startswith('http'):
                        ms_url = f"http://sicon.siam.org/{ms_url}"
                    
                    print(f"\n📄 Processing {ms_id}...")
                    
                    # Basic data from table
                    ms_data = {
                        "manuscript_id": ms_id,
                        "url": ms_url,
                        "title": cells[1].get_text(strip=True),
                        "corresponding_author": cells[2].get_text(strip=True),
                        "associate_editor": cells[3].get_text(strip=True),
                        "submission_date": cells[4].get_text(strip=True),
                        "days_in_system": cells[5].get_text(strip=True),
                        "current_stage": cells[-1].get_text(strip=True) if len(cells) > 11 else "",
                        "referees": [],
                        "files": {
                            "manuscript": None,
                            "cover_letter": None,
                            "reports": []
                        }
                    }
                    
                    # Parse referee information from table
                    invitees = [i.strip() for i in cells[6].get_text(separator="\n").split('\n') if i.strip()]
                    statuses = [s.strip() for s in cells[7].get_text(separator="\n").split('\n') if s.strip()]
                    due_dates = [d.strip() for d in cells[9].get_text(separator="\n").split('\n') if d.strip()]
                    rcvd_dates = [r.strip() for r in cells[10].get_text(separator="\n").split('\n') if r.strip()]
                    
                    referee_index = 0
                    for i, (invitee, status) in enumerate(zip(invitees, statuses)):
                        if status.lower() == "accepted":
                            ref_data = {
                                "name": invitee,
                                "status": "Active",
                                "due_date": due_dates[referee_index] if referee_index < len(due_dates) else "",
                                "received_date": rcvd_dates[referee_index] if referee_index < len(rcvd_dates) else "",
                                "has_report": bool(rcvd_dates[referee_index]) if referee_index < len(rcvd_dates) else False,
                                "email": None
                            }
                            ms_data["referees"].append(ref_data)
                            referee_index += 1
                    
                    print(f"   Found {len(ms_data['referees'])} referees")
                    
                    # Navigate to manuscript page for PDFs and emails
                    self.driver.get(ms_url)
                    time.sleep(2)
                    
                    ms_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    
                    # Look for referee emails
                    for ref in ms_data["referees"]:
                        # Search for email near referee name
                        for link in ms_soup.find_all('a', href=re.compile(r'mailto:')):
                            if ref["name"].lower() in link.get_text().lower():
                                ref["email"] = link.get('href').replace('mailto:', '')
                                print(f"   📧 Found email for {ref['name']}: {ref['email']}")
                                break
                    
                    # Find PDF links
                    pdf_links = []
                    for link in ms_soup.find_all('a'):
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        
                        if '.pdf' in href:
                            pdf_links.append({
                                'url': href if href.startswith('http') else f"http://sicon.siam.org/{href}",
                                'text': text
                            })
                    
                    # Download PDFs
                    for pdf in pdf_links:
                        url = pdf['url']
                        text = pdf['text'].lower()
                        
                        # Determine file type
                        if any(word in text for word in ['manuscript', 'paper', 'article']):
                            filename = f"{ms_id}_manuscript.pdf"
                            filepath = self.dirs['sicon']['manuscripts'] / filename
                            if self.download_file_urllib(url, filepath, cookies_str):
                                ms_data["files"]["manuscript"] = filename
                        
                        elif 'cover' in text:
                            filename = f"{ms_id}_cover_letter.pdf"
                            filepath = self.dirs['sicon']['cover_letters'] / filename
                            if self.download_file_urllib(url, filepath, cookies_str):
                                ms_data["files"]["cover_letter"] = filename
                        
                        elif any(word in text for word in ['report', 'review', 'referee']):
                            # Try to match with referee
                            matched = False
                            for ref in ms_data["referees"]:
                                if ref["has_report"] and ref["name"].lower() in text:
                                    filename = f"{ms_id}_report_{ref['name'].replace(' ', '_')}.pdf"
                                    filepath = self.dirs['sicon']['reports'] / filename
                                    if self.download_file_urllib(url, filepath, cookies_str):
                                        ms_data["files"]["reports"].append(filename)
                                    matched = True
                                    break
                            
                            if not matched and any(ref["has_report"] for ref in ms_data["referees"]):
                                # Generic report
                                report_num = len(ms_data["files"]["reports"]) + 1
                                filename = f"{ms_id}_report_{report_num}.pdf"
                                filepath = self.dirs['sicon']['reports'] / filename
                                if self.download_file_urllib(url, filepath, cookies_str):
                                    ms_data["files"]["reports"].append(filename)
                    
                    manuscripts.append(ms_data)
                    
                    # Return to All Pending page
                    self.driver.get(all_pending_url)
                    time.sleep(1)
                
                break
        
        # Save data
        with open(self.dirs['sicon']['data'] / 'manuscripts.json', 'w') as f:
            json.dump(manuscripts, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Extracted {len(manuscripts)} SICON manuscripts")
        return manuscripts
    
    def extract_sifin_data(self):
        """Extract SIFIN data."""
        print("\n📗 Extracting SIFIN data...")
        
        if not self.authenticate_orcid("http://sifin.siam.org"):
            return []
        
        # Get cookies for downloads
        cookies_str = self.get_cookies_string()
        
        # Find manuscripts
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        manuscript_links = []
        for link in soup.find_all('a'):
            text = link.get_text(strip=True)
            if text.startswith('#') and re.search(r'M\d+', text):
                href = link.get('href', '')
                manuscript_links.append({
                    'text': text,
                    'url': href if href.startswith('http') else f"http://sifin.siam.org/{href}"
                })
        
        print(f"📋 Found {len(manuscript_links)} manuscripts")
        
        manuscripts = []
        
        for ms_link in manuscript_links:
            try:
                ms_id_match = re.search(r'M\d+', ms_link['text'])
                if not ms_id_match:
                    continue
                
                ms_id = ms_id_match.group()
                print(f"\n📄 Processing {ms_id}...")
                
                # Navigate to manuscript
                self.driver.get(ms_link['url'])
                time.sleep(2)
                
                ms_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                ms_data = {
                    "manuscript_id": ms_id,
                    "url": ms_link['url'],
                    "title": "",
                    "corresponding_author": "",
                    "referees": [],
                    "files": {
                        "manuscript": None,
                        "cover_letter": None,
                        "reports": []
                    }
                }
                
                # Extract basic info from tables
                for table in ms_soup.find_all('table'):
                    for row in table.find_all('tr'):
                        cells = row.find_all(['th', 'td'])
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True).lower()
                            value = cells[1].get_text(strip=True)
                            
                            if 'title' in label and 'subtitle' not in label:
                                ms_data["title"] = value
                                print(f"   Title: {value[:50]}...")
                            elif 'corresponding author' in label:
                                ms_data["corresponding_author"] = value
                            elif 'referee' in label and 'potential' not in label:
                                # Extract referees
                                referee_cell = cells[1]
                                
                                # Parse referees - look for patterns like "Name #1"
                                cell_text = referee_cell.get_text()
                                referee_matches = re.findall(r'([^#,\n]+)\s*#(\d+)', cell_text)
                                
                                for name, number in referee_matches:
                                    ref_data = {
                                        "name": name.strip(),
                                        "number": number,
                                        "has_report": False,
                                        "email": None
                                    }
                                    
                                    # Check if report received
                                    if 'rcvd' in cell_text.lower():
                                        # Look for received date near this referee
                                        rcvd_match = re.search(rf'{name}.*?Rcvd[:\s]*([\d-]+)', cell_text, re.IGNORECASE)
                                        if rcvd_match:
                                            ref_data["has_report"] = True
                                            ref_data["received_date"] = rcvd_match.group(1)
                                    
                                    ms_data["referees"].append(ref_data)
                
                print(f"   Found {len(ms_data['referees'])} referees")
                
                # Look for emails
                for ref in ms_data["referees"]:
                    for link in ms_soup.find_all('a', href=re.compile(r'mailto:')):
                        if ref["name"].lower() in link.get_text().lower():
                            ref["email"] = link.get('href').replace('mailto:', '')
                            print(f"   📧 Found email for {ref['name']}: {ref['email']}")
                            break
                
                # Find and download PDFs
                pdf_count = 0
                for link in ms_soup.find_all('a'):
                    href = link.get('href', '')
                    text = link.get_text(strip=True).lower()
                    
                    if '.pdf' in href or any(word in text for word in ['download', 'view', 'file']):
                        url = href if href.startswith('http') else f"http://sifin.siam.org/{href}"
                        
                        # Determine file type
                        if 'manuscript' in text:
                            filename = f"{ms_id}_manuscript.pdf"
                            filepath = self.dirs['sifin']['manuscripts'] / filename
                            if self.download_file_urllib(url, filepath, cookies_str):
                                ms_data["files"]["manuscript"] = filename
                                pdf_count += 1
                        
                        elif 'cover' in text:
                            filename = f"{ms_id}_cover_letter.pdf"
                            filepath = self.dirs['sifin']['cover_letters'] / filename
                            if self.download_file_urllib(url, filepath, cookies_str):
                                ms_data["files"]["cover_letter"] = filename
                                pdf_count += 1
                        
                        elif 'report' in text or 'review' in text:
                            # Match with referee if possible
                            matched = False
                            for ref in ms_data["referees"]:
                                if ref["name"].lower() in text:
                                    filename = f"{ms_id}_report_{ref['name'].replace(' ', '_')}.pdf"
                                    filepath = self.dirs['sifin']['reports'] / filename
                                    if self.download_file_urllib(url, filepath, cookies_str):
                                        ms_data["files"]["reports"].append(filename)
                                        ref["has_report"] = True
                                        pdf_count += 1
                                    matched = True
                                    break
                            
                            if not matched:
                                # Generic report
                                report_num = len(ms_data["files"]["reports"]) + 1
                                filename = f"{ms_id}_report_{report_num}.pdf"
                                filepath = self.dirs['sifin']['reports'] / filename
                                if self.download_file_urllib(url, filepath, cookies_str):
                                    ms_data["files"]["reports"].append(filename)
                                    pdf_count += 1
                
                print(f"   Downloaded {pdf_count} PDFs")
                
                manuscripts.append(ms_data)
                
                # Return to main page
                self.driver.get("http://sifin.siam.org")
                time.sleep(1)
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                continue
        
        # Save data
        with open(self.dirs['sifin']['data'] / 'manuscripts.json', 'w') as f:
            json.dump(manuscripts, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Extracted {len(manuscripts)} SIFIN manuscripts")
        return manuscripts
    
    def create_summary(self, sicon_data, sifin_data):
        """Create extraction summary."""
        summary_path = self.output_dir / "extraction_summary.txt"
        
        with open(summary_path, 'w') as f:
            f.write("="*80 + "\n")
            f.write("SIAM COMPLETE EXTRACTION SUMMARY\n")
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
                f.write(f"  Corresponding Author: {ms['corresponding_author']}\n")
                f.write(f"  Files: MS={ms['files']['manuscript'] is not None}, ")
                f.write(f"CL={ms['files']['cover_letter'] is not None}, ")
                f.write(f"Reports={len(ms['files']['reports'])}\n")
                
                for ref in ms["referees"]:
                    status = "✓" if ref["has_report"] else "⏳"
                    email = ref.get("email", "No email")
                    f.write(f"  {status} {ref['name']} ({email})\n")
            
            # SIFIN Summary
            f.write("\n\nSIFIN (SIAM Journal on Financial Mathematics)\n")
            f.write("-"*50 + "\n")
            f.write(f"Manuscripts: {len(sifin_data)}\n")
            
            total_refs = sum(len(ms["referees"]) for ms in sifin_data)
            refs_with_reports = sum(1 for ms in sifin_data for ref in ms["referees"] if ref["has_report"])
            refs_with_emails = sum(1 for ms in sifin_data for ref in ms["referees"] if ref.get("email"))
            
            f.write(f"Total referees: {total_refs}\n")
            f.write(f"Reports received: {refs_with_reports}\n")
            f.write(f"Emails found: {refs_with_emails}\n\n")
            
            for ms in sifin_data:
                f.write(f"\n{ms['manuscript_id']} - {ms['title'][:60]}...\n")
                f.write(f"  Corresponding Author: {ms['corresponding_author']}\n")
                f.write(f"  Files: MS={ms['files']['manuscript'] is not None}, ")
                f.write(f"CL={ms['files']['cover_letter'] is not None}, ")
                f.write(f"Reports={len(ms['files']['reports'])}\n")
                
                for ref in ms["referees"]:
                    status = "✓" if ref["has_report"] else "⏳"
                    email = ref.get("email", "No email")
                    f.write(f"  {status} {ref['name']} ({email})\n")
            
            f.write(f"\n\nAll files saved to: {self.output_dir}\n")
        
        print(f"\n📊 Summary saved to: {summary_path}")
    
    def run(self):
        """Run the complete extraction."""
        print("\n🚀 STARTING RELIABLE SIAM EXTRACTION")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            self.setup_driver()
            
            # Extract SICON
            sicon_data = self.extract_sicon_data()
            
            # Extract SIFIN
            sifin_data = self.extract_sifin_data()
            
            # Create summary
            self.create_summary(sicon_data, sifin_data)
            
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
    extractor = ReliableSIAMExtractor()
    extractor.run()


if __name__ == "__main__":
    main()