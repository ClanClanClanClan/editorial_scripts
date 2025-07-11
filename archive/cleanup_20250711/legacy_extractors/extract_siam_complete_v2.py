#!/usr/bin/env python3
"""
Complete SIAM extraction with proper parsing of referee reports and PDFs
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
import requests


class SIAMExtractorV2:
    """Enhanced SIAM extractor with complete data parsing."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.session = requests.Session()
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_complete_v2_{timestamp}')
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.pdfs_dir = self.output_dir / 'pdfs'
        self.reports_dir = self.output_dir / 'reports'
        self.pdfs_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)
        
        print(f"📁 Output directory: {self.output_dir}")
    
    def setup_driver(self):
        """Setup Chrome WebDriver with download preferences."""
        chrome_options = Options()
        
        # Configure download directory
        prefs = {
            "download.default_directory": str(self.pdfs_dir.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
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
    
    def extract_sicon_complete(self):
        """Extract SICON manuscripts from All Pending Manuscripts view."""
        print("\n📘 Extracting SICON manuscripts...")
        
        self.authenticate_orcid("http://sicon.siam.org")
        
        # Find and click "All Pending Manuscripts" link
        print("📋 Looking for All Pending Manuscripts...")
        
        # Wait a bit for page to fully load
        time.sleep(2)
        
        # Find the link - it might be in a folder structure
        try:
            # First try direct link
            all_pending_link = self.driver.find_element(
                By.XPATH, 
                "//a[contains(text(), 'All Pending Manuscripts')]"
            )
            all_pending_url = all_pending_link.get_attribute('href')
        except:
            # Try finding it in the folder structure with partial text match
            all_pending_link = self.driver.find_element(
                By.XPATH, 
                "//a[contains(@href, 'is_open_1800=1')]"
            )
            all_pending_url = all_pending_link.get_attribute('href')
        
        # Navigate to All Pending Manuscripts
        self.driver.get(all_pending_url)
        time.sleep(3)
        
        # Parse the table
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Save the page for reference
        with open(self.output_dir / "sicon_all_pending.html", 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
        
        manuscripts = []
        
        # Find the main manuscripts table
        tables = soup.find_all('table')
        
        for table in tables:
            # Look for table with manuscript data
            headers = [th.get_text(strip=True) for th in table.find_all('th')]
            
            if 'Manuscript #' in headers:
                print("✅ Found manuscripts table")
                
                # Process each row
                rows = table.find_all('tr')[1:]  # Skip header row
                
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) < 10:
                        continue
                    
                    # Extract manuscript data based on column positions
                    ms_data = {
                        "manuscript_id": cells[0].get_text(strip=True),
                        "title": cells[1].get_text(strip=True),
                        "corresponding_editor": cells[2].get_text(strip=True),
                        "associate_editor": cells[3].get_text(strip=True),
                        "submitted": cells[4].get_text(strip=True),
                        "days_in_system": cells[5].get_text(strip=True),
                        "invitees": [],
                        "current_stage": cells[-1].get_text(strip=True) if len(cells) > 11 else "",
                        "referees": []
                    }
                    
                    # Extract invitees and their status
                    invitees_text = cells[6].get_text(separator="\n") if len(cells) > 6 else ""
                    status_text = cells[7].get_text(separator="\n") if len(cells) > 7 else ""
                    
                    invitees = [i.strip() for i in invitees_text.split('\n') if i.strip()]
                    statuses = [s.strip() for s in status_text.split('\n') if s.strip()]
                    
                    # Parse review dates
                    due_dates_text = cells[9].get_text(separator="\n") if len(cells) > 9 else ""
                    rcvd_dates_text = cells[10].get_text(separator="\n") if len(cells) > 10 else ""
                    
                    due_dates = [d.strip() for d in due_dates_text.split('\n') if d.strip()]
                    rcvd_dates = [r.strip() for r in rcvd_dates_text.split('\n') if r.strip()]
                    
                    # Match invitees with their status and dates
                    for i, invitee in enumerate(invitees):
                        status = statuses[i] if i < len(statuses) else ""
                        
                        invitee_data = {
                            "name": invitee,
                            "status": status,
                            "due_date": "",
                            "received_date": ""
                        }
                        
                        # If accepted, they are a referee
                        if status.lower() == "accepted":
                            # Find corresponding dates
                            referee_index = len(ms_data["referees"])
                            if referee_index < len(due_dates):
                                invitee_data["due_date"] = due_dates[referee_index]
                            if referee_index < len(rcvd_dates):
                                invitee_data["received_date"] = rcvd_dates[referee_index]
                                invitee_data["report_status"] = "Received" if rcvd_dates[referee_index] else "Awaiting"
                            else:
                                invitee_data["report_status"] = "Awaiting"
                            
                            ms_data["referees"].append(invitee_data)
                        
                        ms_data["invitees"].append(invitee_data)
                    
                    # Get manuscript link
                    ms_link = cells[0].find('a')
                    if ms_link:
                        ms_data["url"] = ms_link.get('href', '')
                        if not ms_data["url"].startswith('http'):
                            ms_data["url"] = f"http://sicon.siam.org/{ms_data['url']}"
                    
                    manuscripts.append(ms_data)
                    
                    print(f"\n📄 {ms_data['manuscript_id']} - {ms_data['title'][:50]}...")
                    print(f"   Referees: {len(ms_data['referees'])}")
                    for ref in ms_data["referees"]:
                        status_symbol = "✅" if ref.get("report_status") == "Received" else "⏳"
                        print(f"   {status_symbol} {ref['name']} - {ref.get('report_status', 'Unknown')}")
                
                break
        
        return manuscripts
    
    def extract_sifin_with_reports(self):
        """Extract SIFIN manuscripts with proper parsing of reports and PDFs."""
        print("\n📗 Extracting SIFIN manuscripts with reports...")
        
        self.authenticate_orcid("http://sifin.siam.org")
        
        # Find manuscripts in Associate Editor Tasks
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Look for manuscript links
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
        
        for i, ms_link in enumerate(manuscript_links, 1):
            try:
                # Extract manuscript ID
                ms_id_match = re.search(r'M\d+', ms_link['text'])
                if not ms_id_match:
                    continue
                
                ms_id = ms_id_match.group()
                print(f"\n📄 Manuscript {i}: {ms_id}")
                
                # Navigate to manuscript details
                self.driver.get(ms_link['url'])
                time.sleep(2)
                
                # Parse manuscript page
                ms_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                ms_data = {
                    "manuscript_id": ms_id,
                    "url": ms_link['url'],
                    "title": "",
                    "corresponding_author": "",
                    "referees": [],
                    "pdf_links": [],
                    "report_links": []
                }
                
                # Extract basic info from table
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
                
                # Look for PDF and report links
                # These are typically in the lower part of the page
                all_links = ms_soup.find_all('a')
                
                for link in all_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True).lower()
                    
                    # PDF links (manuscript, cover letter)
                    if '.pdf' in href or 'download' in text or 'view pdf' in text:
                        link_data = {
                            "text": link.get_text(strip=True),
                            "url": href if href.startswith('http') else f"http://sifin.siam.org/{href}",
                            "type": "manuscript" if 'manuscript' in text else "other"
                        }
                        
                        if 'cover' in text:
                            link_data["type"] = "cover_letter"
                        
                        ms_data["pdf_links"].append(link_data)
                        print(f"   📎 Found PDF: {link_data['text']}")
                    
                    # Referee report links
                    if 'report' in text or 'review' in text:
                        if 'referee' in text or 'reviewer' in text:
                            report_data = {
                                "text": link.get_text(strip=True),
                                "url": href if href.startswith('http') else f"http://sifin.siam.org/{href}"
                            }
                            ms_data["report_links"].append(report_data)
                            print(f"   📝 Found report: {report_data['text']}")
                
                # Extract referee information with report status
                for table in ms_soup.find_all('table'):
                    for row in table.find_all('tr'):
                        cells = row.find_all(['th', 'td'])
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True).lower()
                            
                            if 'referee' in label and 'potential' not in label:
                                referee_cell = cells[1]
                                
                                # Look for referee links and text
                                for ref_element in referee_cell.find_all(['a', 'span']):
                                    ref_text = ref_element.get_text(strip=True)
                                    if ref_text and not ref_text.lower() == 'referees':
                                        # Parse referee info
                                        ref_data = {
                                            "name": "",
                                            "has_report": False,
                                            "report_date": ""
                                        }
                                        
                                        # Check if this referee has a report link
                                        if ref_element.name == 'a':
                                            ref_href = ref_element.get('href', '')
                                            if 'report' in ref_href or 'review' in ref_href:
                                                ref_data["has_report"] = True
                                                ref_data["report_url"] = ref_href if ref_href.startswith('http') else f"http://sifin.siam.org/{ref_href}"
                                        
                                        # Extract name
                                        name_match = re.match(r'^([^#(]+)', ref_text)
                                        if name_match:
                                            ref_data["name"] = name_match.group(1).strip()
                                        
                                        # Check for dates
                                        if 'rcvd' in referee_cell.get_text().lower():
                                            date_match = re.search(r'rcvd[:\s]*([\d-]+)', referee_cell.get_text(), re.IGNORECASE)
                                            if date_match:
                                                ref_data["report_date"] = date_match.group(1)
                                                ref_data["has_report"] = True
                                        
                                        if ref_data["name"]:
                                            ms_data["referees"].append(ref_data)
                
                # Count reports
                reports_count = sum(1 for ref in ms_data["referees"] if ref["has_report"])
                print(f"   Referees: {len(ms_data['referees'])} ({reports_count} reports)")
                
                manuscripts.append(ms_data)
                
                # Try to download PDFs and reports
                if ms_data["pdf_links"]:
                    self.download_files(ms_data["pdf_links"], ms_id, "pdf")
                if ms_data["report_links"]:
                    self.download_files(ms_data["report_links"], ms_id, "report")
                
                # Go back to main page
                self.driver.get("http://sifin.siam.org")
                time.sleep(1)
                
            except Exception as e:
                print(f"   ❌ Error processing manuscript: {e}")
                continue
        
        return manuscripts
    
    def download_files(self, links, ms_id, file_type):
        """Download PDF or report files."""
        for link in links:
            try:
                print(f"   📥 Downloading {file_type}: {link['text']}")
                
                # Navigate to download link
                self.driver.get(link['url'])
                time.sleep(2)
                
                # Check if it's a direct download or needs another click
                if file_type == "pdf":
                    filename = f"{ms_id}_{link.get('type', 'document')}.pdf"
                else:
                    filename = f"{ms_id}_report_{len(links)}.pdf"
                
                # Wait for download
                time.sleep(3)
                
            except Exception as e:
                print(f"      ❌ Download failed: {e}")
    
    def run_complete_extraction(self):
        """Run extraction for both SICON and SIFIN."""
        print("\n🚀 STARTING COMPLETE SIAM DATA EXTRACTION V2")
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
                "reports_received": sum(1 for ms in sicon_manuscripts for ref in ms["referees"] if ref.get("report_status") == "Received")
            }
            
            # Extract SIFIN
            sifin_manuscripts = self.extract_sifin_with_reports()
            results["sifin"] = {
                "manuscripts": sifin_manuscripts,
                "total": len(sifin_manuscripts),
                "referees_total": sum(len(ms["referees"]) for ms in sifin_manuscripts),
                "reports_received": sum(1 for ms in sifin_manuscripts for ref in ms["referees"] if ref["has_report"])
            }
            
            # Save results
            with open(self.output_dir / "complete_extraction.json", 'w') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            # Print summary
            self.print_summary(results)
            
            return results
            
        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            if self.driver:
                self.driver.quit()
                print("\n🔄 Browser closed")
    
    def print_summary(self, results):
        """Print extraction summary."""
        print("\n" + "="*80)
        print("📊 COMPLETE SIAM EXTRACTION SUMMARY V2")
        print("="*80)
        
        # SICON Summary
        sicon = results.get("sicon", {})
        print(f"\n📘 SICON: {sicon.get('total', 0)} manuscripts")
        print(f"   Total referees: {sicon.get('referees_total', 0)}")
        print(f"   Reports received: {sicon.get('reports_received', 0)}")
        
        # SIFIN Summary
        sifin = results.get("sifin", {})
        print(f"\n📗 SIFIN: {sifin.get('total', 0)} manuscripts")
        print(f"   Total referees: {sifin.get('referees_total', 0)}")
        print(f"   Reports received: {sifin.get('reports_received', 0)}")
        
        print(f"\n📁 All data saved to: {self.output_dir}")


def main():
    """Main entry point."""
    extractor = SIAMExtractorV2()
    results = extractor.run_complete_extraction()


if __name__ == "__main__":
    main()