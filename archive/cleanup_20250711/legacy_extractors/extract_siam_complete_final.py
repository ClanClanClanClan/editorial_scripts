#!/usr/bin/env python3
"""
Complete SIAM extraction with all data:
- Referee emails
- Manuscript PDFs
- Cover letters
- Referee reports
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
import requests


class CompleteSIAMExtractor:
    """Extract all data from SIAM journals including PDFs and emails."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.session = requests.Session()
        
        # Create output directory structure
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_complete_final_{timestamp}')
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for different file types
        self.dirs = {
            'manuscripts': self.output_dir / 'manuscripts',
            'cover_letters': self.output_dir / 'cover_letters',
            'reports': self.output_dir / 'reports',
            'data': self.output_dir / 'data'
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(exist_ok=True)
        
        print(f"📁 Output directory: {self.output_dir}")
    
    def setup_driver(self):
        """Setup Chrome WebDriver with download preferences."""
        chrome_options = Options()
        
        # Configure download directory
        download_dir = str(self.output_dir / 'downloads')
        Path(download_dir).mkdir(exist_ok=True)
        
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Enable downloads in headless mode
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.command_executor._commands["send_command"] = ("POST", '/session/$sessionId/chromium/send_command')
        
        params = {'cmd': 'Page.setDownloadBehavior', 'params': {'behavior': 'allow', 'downloadPath': download_dir}}
        self.driver.execute("send_command", params)
        
        self.wait = WebDriverWait(self.driver, 30)
        self.download_dir = download_dir
        
        print("✅ Chrome WebDriver initialized with download support")
    
    def authenticate_orcid(self, journal_url):
        """Authenticate using ORCID."""
        print(f"🔐 Authenticating with {journal_url}...")
        
        # Navigate to journal
        self.driver.get(journal_url)
        time.sleep(3)
        
        # Remove cookie banners
        self.driver.execute_script("""
            var elements = ['#cookie-policy-layer-bg', '#cookie-policy-layer', '.cc_banner-wrapper'];
            elements.forEach(function(sel) {
                var els = document.querySelectorAll(sel);
                els.forEach(function(el) { el.remove(); });
            });
            
            var continueBtn = document.getElementById('continue-btn');
            if (continueBtn) continueBtn.click();
        """)
        
        # Click ORCID link
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
        
        # Copy cookies to requests session
        for cookie in self.driver.get_cookies():
            self.session.cookies.set(cookie['name'], cookie['value'])
    
    def extract_referee_email(self, referee_name, manuscript_soup):
        """Extract referee email from manuscript page."""
        # Look for email links near referee name
        email = None
        
        # Method 1: Look for mailto links
        for link in manuscript_soup.find_all('a', href=re.compile(r'mailto:')):
            link_text = link.get_text(strip=True)
            if referee_name.lower() in link_text.lower() or link_text in referee_name:
                email = link.get('href').replace('mailto:', '')
                break
        
        # Method 2: Look in tables for email patterns
        if not email:
            for table in manuscript_soup.find_all('table'):
                table_text = table.get_text()
                if referee_name in table_text:
                    # Look for email pattern
                    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', table_text)
                    if email_match:
                        # Check if email is near referee name
                        index = table_text.find(referee_name)
                        email_index = table_text.find(email_match.group())
                        if abs(index - email_index) < 100:  # Within ~100 chars
                            email = email_match.group()
        
        return email
    
    def download_pdf(self, url, filename, file_type="document"):
        """Download a PDF file."""
        try:
            print(f"   📥 Downloading {file_type}: {filename}")
            
            # Clear download directory first
            for file in Path(self.download_dir).glob("*"):
                if file.is_file():
                    file.unlink()
            
            # Navigate to URL
            self.driver.get(url)
            time.sleep(3)
            
            # Check if it's a direct PDF or needs another click
            if self.driver.current_url.endswith('.pdf'):
                # Direct PDF - browser should download it
                time.sleep(5)
            else:
                # Look for download/view PDF button
                try:
                    pdf_button = self.driver.find_element(By.XPATH, "//a[contains(text(), 'PDF') or contains(text(), 'Download') or contains(@href, '.pdf')]")
                    pdf_button.click()
                    time.sleep(5)
                except:
                    pass
            
            # Check if file was downloaded
            downloaded_files = list(Path(self.download_dir).glob("*"))
            if downloaded_files:
                # Move to appropriate directory
                source_file = downloaded_files[0]
                
                if file_type == "manuscript":
                    dest_dir = self.dirs['manuscripts']
                elif file_type == "cover_letter":
                    dest_dir = self.dirs['cover_letters']
                elif file_type == "report":
                    dest_dir = self.dirs['reports']
                else:
                    dest_dir = self.output_dir
                
                dest_file = dest_dir / filename
                shutil.move(str(source_file), str(dest_file))
                print(f"      ✅ Saved as: {dest_file.name}")
                return True
            else:
                print(f"      ❌ Download failed")
                return False
                
        except Exception as e:
            print(f"      ❌ Error downloading: {e}")
            return False
    
    def extract_sicon_complete(self):
        """Extract complete SICON data including emails and PDFs."""
        print("\n📘 Extracting complete SICON data...")
        
        self.authenticate_orcid("http://sicon.siam.org")
        
        # Navigate to All Pending Manuscripts
        print("📋 Navigating to All Pending Manuscripts...")
        
        try:
            all_pending_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'is_open_1800=1')]")
            all_pending_url = all_pending_link.get_attribute('href')
        except:
            # Try Under Review folder first
            under_review_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'is_open_1400=1')]")
            self.driver.get(under_review_link.get_attribute('href'))
            time.sleep(2)
            # Then find All Pending
            all_pending_link = self.driver.find_element(By.XPATH, "//a[contains(text(), 'All Pending')]")
            all_pending_url = all_pending_link.get_attribute('href')
        
        self.driver.get(all_pending_url)
        time.sleep(3)
        
        # Parse the manuscripts table
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        manuscripts = []
        
        # Find the main table
        tables = soup.find_all('table')
        
        for table in tables:
            headers = [th.get_text(strip=True) for th in table.find_all('th')]
            
            if 'Manuscript #' in headers:
                print("✅ Found manuscripts table")
                
                rows = table.find_all('tr')[1:]  # Skip header
                
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) < 10 or not cells[0].get_text(strip=True).startswith('M'):
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
                    
                    # Navigate to manuscript page
                    self.driver.get(ms_url)
                    time.sleep(2)
                    
                    ms_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    
                    # Extract manuscript data
                    ms_data = {
                        "manuscript_id": ms_id,
                        "url": ms_url,
                        "title": cells[1].get_text(strip=True) if len(cells) > 1 else "",
                        "corresponding_author": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                        "submission_date": cells[4].get_text(strip=True) if len(cells) > 4 else "",
                        "referees": [],
                        "pdf_links": [],
                        "emails": {}
                    }
                    
                    # Extract referee information from the All Pending table
                    invitees_text = cells[6].get_text(separator="\n") if len(cells) > 6 else ""
                    status_text = cells[7].get_text(separator="\n") if len(cells) > 7 else ""
                    due_dates_text = cells[9].get_text(separator="\n") if len(cells) > 9 else ""
                    rcvd_dates_text = cells[10].get_text(separator="\n") if len(cells) > 10 else ""
                    
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
                                "status": status,
                                "due_date": due_dates[referee_index] if referee_index < len(due_dates) else "",
                                "received_date": rcvd_dates[referee_index] if referee_index < len(rcvd_dates) else "",
                                "has_report": bool(rcvd_dates[referee_index]) if referee_index < len(rcvd_dates) else False,
                                "email": None
                            }
                            
                            # Try to find referee email
                            email = self.extract_referee_email(invitee, ms_soup)
                            if email:
                                ref_data["email"] = email
                                ms_data["emails"][invitee] = email
                                print(f"   📧 Found email for {invitee}: {email}")
                            
                            ms_data["referees"].append(ref_data)
                            referee_index += 1
                    
                    # Look for PDF links
                    for link in ms_soup.find_all('a'):
                        href = link.get('href', '')
                        text = link.get_text(strip=True).lower()
                        
                        if '.pdf' in href or 'download' in text or 'view' in text:
                            link_info = {
                                "text": link.get_text(strip=True),
                                "url": href if href.startswith('http') else f"http://sicon.siam.org/{href}",
                                "type": "unknown"
                            }
                            
                            # Categorize the link
                            if 'manuscript' in text or 'paper' in text:
                                link_info["type"] = "manuscript"
                            elif 'cover' in text or 'letter' in text:
                                link_info["type"] = "cover_letter"
                            elif 'report' in text or 'review' in text:
                                link_info["type"] = "report"
                            elif 'decision' in text:
                                link_info["type"] = "decision"
                            
                            ms_data["pdf_links"].append(link_info)
                    
                    # Download PDFs
                    for pdf_link in ms_data["pdf_links"]:
                        if pdf_link["type"] == "manuscript":
                            self.download_pdf(pdf_link["url"], f"{ms_id}_manuscript.pdf", "manuscript")
                        elif pdf_link["type"] == "cover_letter":
                            self.download_pdf(pdf_link["url"], f"{ms_id}_cover_letter.pdf", "cover_letter")
                        elif pdf_link["type"] == "report":
                            # Try to identify which referee
                            for ref in ms_data["referees"]:
                                if ref["has_report"] and ref["name"].lower() in pdf_link["text"].lower():
                                    filename = f"{ms_id}_report_{ref['name'].replace(' ', '_')}.pdf"
                                    self.download_pdf(pdf_link["url"], filename, "report")
                                    break
                            else:
                                # Generic report name
                                self.download_pdf(pdf_link["url"], f"{ms_id}_report.pdf", "report")
                    
                    manuscripts.append(ms_data)
                    
                    # Go back to All Pending page
                    self.driver.get(all_pending_url)
                    time.sleep(1)
                
                break
        
        return manuscripts
    
    def extract_sifin_complete(self):
        """Extract complete SIFIN data including emails and PDFs."""
        print("\n📗 Extracting complete SIFIN data...")
        
        self.authenticate_orcid("http://sifin.siam.org")
        
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
                    "pdf_links": [],
                    "emails": {}
                }
                
                # Extract basic info
                for table in ms_soup.find_all('table'):
                    for row in table.find_all('tr'):
                        cells = row.find_all(['th', 'td'])
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True).lower()
                            value = cells[1].get_text(strip=True)
                            
                            if 'manuscript #' in label:
                                ms_data["manuscript_id"] = value
                            elif 'title' in label and 'subtitle' not in label:
                                ms_data["title"] = value
                                print(f"   Title: {value[:50]}...")
                            elif 'corresponding author' in label:
                                ms_data["corresponding_author"] = value
                            elif 'referee' in label and 'potential' not in label:
                                # Process referees
                                referee_cell = cells[1]
                                
                                # Look for referee information
                                for element in referee_cell.find_all(['a', 'span']):
                                    ref_text = element.get_text(strip=True)
                                    if ref_text and ref_text.lower() != 'referees':
                                        ref_data = {
                                            "name": ref_text.split('#')[0].strip(),
                                            "has_report": False,
                                            "email": None
                                        }
                                        
                                        # Check for email
                                        email = self.extract_referee_email(ref_data["name"], ms_soup)
                                        if email:
                                            ref_data["email"] = email
                                            ms_data["emails"][ref_data["name"]] = email
                                            print(f"   📧 Found email for {ref_data['name']}: {email}")
                                        
                                        ms_data["referees"].append(ref_data)
                
                # Look for all PDF links in the page
                print("   🔍 Looking for PDFs...")
                
                # Find all links that might be PDFs
                all_links = ms_soup.find_all('a')
                
                for link in all_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # Check if it's a PDF-related link
                    if any(keyword in href.lower() or keyword in text.lower() 
                          for keyword in ['.pdf', 'download', 'view', 'file', 'document']):
                        
                        link_info = {
                            "text": text,
                            "url": href if href.startswith('http') else f"http://sifin.siam.org/{href}",
                            "type": "unknown"
                        }
                        
                        # Categorize based on text
                        text_lower = text.lower()
                        if 'manuscript' in text_lower or 'paper' in text_lower:
                            link_info["type"] = "manuscript"
                        elif 'cover' in text_lower:
                            link_info["type"] = "cover_letter"
                        elif 'report' in text_lower or 'review' in text_lower:
                            link_info["type"] = "report"
                            # Check if report is received
                            for ref in ms_data["referees"]:
                                if ref["name"].lower() in text_lower:
                                    ref["has_report"] = True
                                    break
                        
                        ms_data["pdf_links"].append(link_info)
                        print(f"      Found: {text}")
                
                # Download PDFs
                for pdf_link in ms_data["pdf_links"]:
                    if pdf_link["type"] == "manuscript":
                        self.download_pdf(pdf_link["url"], f"{ms_id}_manuscript.pdf", "manuscript")
                    elif pdf_link["type"] == "cover_letter":
                        self.download_pdf(pdf_link["url"], f"{ms_id}_cover_letter.pdf", "cover_letter")
                    elif pdf_link["type"] == "report":
                        # Try to match with referee
                        for ref in ms_data["referees"]:
                            if ref["name"].lower() in pdf_link["text"].lower():
                                filename = f"{ms_id}_report_{ref['name'].replace(' ', '_')}.pdf"
                                self.download_pdf(pdf_link["url"], filename, "report")
                                break
                        else:
                            self.download_pdf(pdf_link["url"], f"{ms_id}_report.pdf", "report")
                
                manuscripts.append(ms_data)
                
                # Go back to main page
                self.driver.get("http://sifin.siam.org")
                time.sleep(1)
                
            except Exception as e:
                print(f"   ❌ Error processing manuscript: {e}")
                continue
        
        return manuscripts
    
    def run_complete_extraction(self):
        """Run extraction for both journals."""
        print("\n🚀 STARTING COMPLETE SIAM DATA EXTRACTION")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        results = {
            "extraction_time": datetime.now().isoformat(),
            "sicon": {},
            "sifin": {}
        }
        
        try:
            self.setup_driver()
            
            # Extract SICON
            sicon_manuscripts = self.extract_sicon_complete()
            results["sicon"] = {
                "manuscripts": sicon_manuscripts,
                "total": len(sicon_manuscripts),
                "referees_total": sum(len(ms["referees"]) for ms in sicon_manuscripts),
                "reports_received": sum(1 for ms in sicon_manuscripts for ref in ms["referees"] if ref["has_report"]),
                "emails_found": sum(1 for ms in sicon_manuscripts for ref in ms["referees"] if ref.get("email"))
            }
            
            # Save SICON data
            with open(self.dirs['data'] / "sicon_complete.json", 'w') as f:
                json.dump(results["sicon"], f, indent=2, ensure_ascii=False)
            
            # Extract SIFIN
            sifin_manuscripts = self.extract_sifin_complete()
            results["sifin"] = {
                "manuscripts": sifin_manuscripts,
                "total": len(sifin_manuscripts),
                "referees_total": sum(len(ms["referees"]) for ms in sifin_manuscripts),
                "reports_received": sum(1 for ms in sifin_manuscripts for ref in ms["referees"] if ref["has_report"]),
                "emails_found": sum(1 for ms in sifin_manuscripts for ref in ms["referees"] if ref.get("email"))
            }
            
            # Save SIFIN data
            with open(self.dirs['data'] / "sifin_complete.json", 'w') as f:
                json.dump(results["sifin"], f, indent=2, ensure_ascii=False)
            
            # Save combined results
            with open(self.dirs['data'] / "complete_extraction.json", 'w') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            # Create summary report
            self.create_summary_report(results)
            
            return results
            
        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            if self.driver:
                self.driver.quit()
                print("\n🔄 Browser closed")
    
    def create_summary_report(self, results):
        """Create a detailed summary report."""
        report_path = self.output_dir / "extraction_summary.txt"
        
        with open(report_path, 'w') as f:
            f.write("="*80 + "\n")
            f.write("COMPLETE SIAM EXTRACTION SUMMARY\n")
            f.write("="*80 + "\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # SICON Summary
            f.write("SICON (SIAM Journal on Control and Optimization)\n")
            f.write("-"*50 + "\n")
            sicon = results.get("sicon", {})
            f.write(f"Manuscripts: {sicon.get('total', 0)}\n")
            f.write(f"Total referees: {sicon.get('referees_total', 0)}\n")
            f.write(f"Reports received: {sicon.get('reports_received', 0)}\n")
            f.write(f"Emails found: {sicon.get('emails_found', 0)}\n\n")
            
            for ms in sicon.get("manuscripts", []):
                f.write(f"\n{ms['manuscript_id']} - {ms['title'][:60]}...\n")
                f.write(f"  Author: {ms['corresponding_author']}\n")
                for ref in ms["referees"]:
                    status = "✓ Report" if ref["has_report"] else "⏳ Waiting"
                    email = ref.get("email", "No email")
                    f.write(f"  {status} {ref['name']} ({email})\n")
            
            f.write("\n\n")
            
            # SIFIN Summary
            f.write("SIFIN (SIAM Journal on Financial Mathematics)\n")
            f.write("-"*50 + "\n")
            sifin = results.get("sifin", {})
            f.write(f"Manuscripts: {sifin.get('total', 0)}\n")
            f.write(f"Total referees: {sifin.get('referees_total', 0)}\n")
            f.write(f"Reports received: {sifin.get('reports_received', 0)}\n")
            f.write(f"Emails found: {sifin.get('emails_found', 0)}\n\n")
            
            for ms in sifin.get("manuscripts", []):
                f.write(f"\n{ms['manuscript_id']} - {ms['title'][:60]}...\n")
                f.write(f"  Author: {ms['corresponding_author']}\n")
                for ref in ms["referees"]:
                    status = "✓ Report" if ref["has_report"] else "⏳ Waiting"
                    email = ref.get("email", "No email")
                    f.write(f"  {status} {ref['name']} ({email})\n")
            
            f.write("\n\nFiles Downloaded:\n")
            f.write("-"*30 + "\n")
            
            # Count files
            manuscript_count = len(list(self.dirs['manuscripts'].glob("*.pdf")))
            cover_count = len(list(self.dirs['cover_letters'].glob("*.pdf")))
            report_count = len(list(self.dirs['reports'].glob("*.pdf")))
            
            f.write(f"Manuscript PDFs: {manuscript_count}\n")
            f.write(f"Cover letters: {cover_count}\n")
            f.write(f"Referee reports: {report_count}\n")
            
            f.write(f"\nAll files saved to: {self.output_dir}\n")
        
        print(f"\n📊 Summary report saved to: {report_path}")


def main():
    """Main entry point."""
    extractor = CompleteSIAMExtractor()
    results = extractor.run_complete_extraction()


if __name__ == "__main__":
    main()