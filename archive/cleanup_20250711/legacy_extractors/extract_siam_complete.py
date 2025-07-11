#!/usr/bin/env python3
"""
Complete SIAM Data Extraction Script - Final Version

Extracts manuscripts from SICON and SIFIN based on the actual page structure:
- Manuscripts are under "Associate Editor Tasks" section
- Each manuscript link starts with # and contains manuscript ID
- Clicking on manuscript shows detailed table with all information
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup


class SIAMCompleteExtractor:
    """Extract complete SIAM data including manuscripts and referees."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_complete_{timestamp}')
        self.output_dir.mkdir(exist_ok=True)
        
        self.data_dir = self.output_dir / 'data'
        self.pdfs_dir = self.output_dir / 'pdfs'
        
        for dir_path in [self.data_dir, self.pdfs_dir]:
            dir_path.mkdir(exist_ok=True)
        
        print(f"📁 Output directory: {self.output_dir}")
    
    def setup_driver(self):
        """Setup Chrome WebDriver."""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Configure download directory
        prefs = {
            "download.default_directory": str(self.pdfs_dir.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)
        
        print("✅ Chrome WebDriver initialized")
    
    def remove_cookie_banners(self):
        """Remove cookie banners and popups."""
        try:
            # Generic cookie removal
            self.driver.execute_script("""
                var elements = ['#cookie-policy-layer-bg', '#cookie-policy-layer', '.cc_banner-wrapper', '.cookie-banner'];
                elements.forEach(function(sel) {
                    var els = document.querySelectorAll(sel);
                    els.forEach(function(el) { el.remove(); });
                });
                
                // Click any accept/continue buttons
                var buttons = document.querySelectorAll('button, input[type="button"]');
                buttons.forEach(function(btn) {
                    var text = btn.textContent.toLowerCase() + ' ' + (btn.value || '').toLowerCase();
                    if (text.includes('accept') || text.includes('continue') || text.includes('agree')) {
                        try { btn.click(); } catch(e) {}
                    }
                });
            """)
            time.sleep(0.5)
        except:
            pass
    
    def authenticate_with_orcid(self, journal_url: str, journal_name: str) -> bool:
        """Authenticate using ORCID."""
        print(f"\n🔐 Authenticating with {journal_name}...")
        
        try:
            # Navigate to journal
            self.driver.get(journal_url)
            time.sleep(3)
            self.remove_cookie_banners()
            
            # Find and click ORCID link
            orcid_link = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'orcid')]"))
            )
            self.driver.execute_script("arguments[0].click();", orcid_link)
            print("   ✅ Clicked ORCID link")
            
            # Wait for ORCID page
            self.wait.until(lambda driver: 'orcid.org' in driver.current_url)
            time.sleep(2)
            
            # Fill credentials
            orcid_user = os.getenv("ORCID_USER")
            orcid_pass = os.getenv("ORCID_PASS")
            
            username_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "username-input"))
            )
            username_field.clear()
            username_field.send_keys(orcid_user)
            
            password_field = self.driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(orcid_pass)
            password_field.send_keys(Keys.RETURN)
            
            print("   ⏳ Waiting for authentication...")
            
            # Wait for redirect back to journal
            start_time = time.time()
            while time.time() - start_time < 30:
                current_url = self.driver.current_url.lower()
                if journal_name.lower() in current_url:
                    print(f"   ✅ Successfully authenticated with {journal_name}")
                    time.sleep(3)
                    self.remove_cookie_banners()
                    return True
                
                # Check for authorization page
                if 'authorize' in current_url:
                    try:
                        auth_button = self.driver.find_element(By.ID, "authorize")
                        auth_button.click()
                    except:
                        pass
                
                time.sleep(2)
            
            return False
            
        except Exception as e:
            print(f"   ❌ Authentication failed: {e}")
            return False
    
    def extract_journal_manuscripts(self, journal_name: str, journal_url: str) -> Dict[str, Any]:
        """Extract manuscripts from a journal."""
        print(f"\n📚 Extracting {journal_name} manuscripts...")
        
        if not self.authenticate_with_orcid(journal_url, journal_name):
            return {"success": False, "error": "Authentication failed"}
        
        try:
            # Parse the dashboard
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find Associate Editor Tasks section
            ae_section = None
            for element in soup.find_all(['h3', 'h4', 'div', 'td']):
                if 'Associate Editor Tasks' in element.get_text():
                    ae_section = element.parent if element.name == 'h3' else element
                    break
            
            if not ae_section:
                print("   ❌ Could not find Associate Editor Tasks section")
                return {"success": False, "error": "No AE section found"}
            
            # Find manuscript links (they start with # and contain manuscript ID)
            manuscripts = []
            manuscript_links = []
            
            # Look for links within or after the AE section
            for link in soup.find_all('a'):
                text = link.get_text(strip=True)
                if text.startswith('#') and re.search(r'M\d+', text):
                    href = link.get('href', '')
                    if href:
                        full_url = href if href.startswith('http') else urljoin(journal_url, href)
                        manuscript_links.append((text, full_url))
                        print(f"   📄 Found manuscript: {text.split(' - ')[0]}")
            
            print(f"   📋 Found {len(manuscript_links)} manuscripts total")
            
            # Extract details for each manuscript
            for ms_text, ms_url in manuscript_links:
                try:
                    # Parse manuscript ID from text
                    ms_id_match = re.search(r'#\s*(M\d+)', ms_text)
                    ms_id = ms_id_match.group(1) if ms_id_match else ms_text.split()[0]
                    
                    # Extract basic info from link text
                    parts = ms_text.split(' - ')
                    status = parts[1] if len(parts) > 1 else "Unknown"
                    title_part = parts[2] if len(parts) > 2 else "Unknown"
                    
                    # Extract referee counts if present (e.g., "(1 received / 2 total)")
                    referee_info = re.search(r'\((\d+)\s*received\s*/\s*(\d+)\s*total\)', ms_text)
                    received_reports = int(referee_info.group(1)) if referee_info else 0
                    total_referees = int(referee_info.group(2)) if referee_info else 0
                    
                    print(f"\n   📋 Extracting details for {ms_id}...")
                    
                    # Navigate to manuscript page
                    self.driver.get(ms_url)
                    time.sleep(2)
                    self.remove_cookie_banners()
                    
                    # Extract detailed information
                    ms_data = self.extract_manuscript_details(ms_id)
                    
                    # Add the summary info we already have
                    ms_data.update({
                        "summary_status": status,
                        "summary_title": title_part,
                        "reports_received": received_reports,
                        "total_referees": total_referees
                    })
                    
                    manuscripts.append(ms_data)
                    
                    # Try to download PDF
                    self.download_manuscript_pdf(ms_id)
                    
                except Exception as e:
                    print(f"      ❌ Error extracting {ms_id}: {e}")
                    continue
            
            result = {
                "success": True,
                "journal": journal_name,
                "manuscripts": manuscripts,
                "total_manuscripts": len(manuscripts),
                "extraction_time": datetime.now().isoformat()
            }
            
            # Save results
            with open(self.data_dir / f"{journal_name}_manuscripts.json", 'w') as f:
                json.dump(result, f, indent=2, default=str)
            
            print(f"\n   ✅ Successfully extracted {len(manuscripts)} manuscripts from {journal_name}")
            return result
            
        except Exception as e:
            print(f"   ❌ Extraction failed: {e}")
            return {"success": False, "error": str(e)}
    
    def extract_manuscript_details(self, ms_id: str) -> Dict[str, Any]:
        """Extract detailed manuscript information from the manuscript page."""
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        ms_data = {
            "manuscript_id": ms_id,
            "title": "",
            "authors": "",
            "submission_date": "",
            "current_stage": "",
            "abstract": "",
            "keywords": "",
            "referees": [],
            "potential_referees": [],
            "associate_editor": "",
            "corresponding_author": ""
        }
        
        # Look for the main manuscript details table
        # Try different table identifiers
        details_table = None
        for table in soup.find_all('table'):
            # Check if table contains manuscript information
            table_text = table.get_text().lower()
            if 'manuscript #' in table_text or 'title' in table_text:
                details_table = table
                break
        
        if details_table:
            for row in details_table.find_all('tr'):
                cells = row.find_all(['th', 'td'])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value_cell = cells[1]
                    value = value_cell.get_text(strip=True)
                    
                    # Extract various fields
                    if 'manuscript #' in label:
                        ms_data["manuscript_id"] = value
                    elif label == 'title':
                        ms_data["title"] = value
                    elif 'corresponding author' in label:
                        ms_data["corresponding_author"] = value
                    elif 'contributing author' in label:
                        ms_data["authors"] = value
                    elif 'submission date' in label:
                        ms_data["submission_date"] = value
                    elif 'current stage' in label:
                        ms_data["current_stage"] = value
                    elif 'abstract' in label:
                        ms_data["abstract"] = value
                    elif 'keywords' in label:
                        ms_data["keywords"] = value
                    elif 'associate editor' in label:
                        ms_data["associate_editor"] = value
                    elif 'potential referees' in label:
                        # Extract potential referees
                        for ref_text in value_cell.get_text().split(','):
                            ref_text = ref_text.strip()
                            if ref_text:
                                # Parse referee info
                                status_match = re.search(r'\(Status:\s*([^)]+)\)', ref_text)
                                status = status_match.group(1) if status_match else "Unknown"
                                name = re.sub(r'\s*\([^)]*\)', '', ref_text).strip()
                                
                                ms_data["potential_referees"].append({
                                    "name": name,
                                    "status": status
                                })
                    elif label == 'referees':
                        # Extract active referees
                        referee_texts = value_cell.get_text().split(',')
                        for ref_text in referee_texts:
                            ref_text = ref_text.strip()
                            if ref_text:
                                # Parse referee info (e.g., "Nicolas Privault #1 (Due: 2025-05-14)")
                                name_match = re.match(r'^([^#(]+)', ref_text)
                                name = name_match.group(1).strip() if name_match else ref_text
                                
                                due_match = re.search(r'Due:\s*([^)]+)', ref_text)
                                due_date = due_match.group(1) if due_match else ""
                                
                                rcvd_match = re.search(r'Rcvd:\s*([^)]+)', ref_text)
                                received_date = rcvd_match.group(1) if rcvd_match else ""
                                
                                status = "Report Received" if received_date else "Awaiting Report"
                                
                                ms_data["referees"].append({
                                    "name": name,
                                    "due_date": due_date,
                                    "received_date": received_date,
                                    "status": status
                                })
        
        print(f"      ✅ Title: {ms_data['title'][:50]}...")
        print(f"      ✅ Referees: {len(ms_data['referees'])} active")
        print(f"      ✅ Status: {ms_data['current_stage']}")
        
        return ms_data
    
    def download_manuscript_pdf(self, ms_id: str):
        """Try to download manuscript PDF."""
        try:
            # Look for PDF download links
            pdf_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf') or contains(text(), 'PDF') or contains(text(), 'Download')]")
            
            if pdf_links:
                print(f"      📥 Downloading PDF for {ms_id}...")
                pdf_links[0].click()
                time.sleep(2)
        except:
            pass
    
    def run_complete_extraction(self) -> Dict[str, Any]:
        """Run extraction for both SICON and SIFIN."""
        print("\n🚀 STARTING COMPLETE SIAM DATA EXTRACTION")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check credentials
        orcid_user = os.getenv("ORCID_USER")
        orcid_pass = os.getenv("ORCID_PASS")
        
        if not orcid_user or not orcid_pass:
            print("❌ ORCID credentials not found")
            return {"success": False, "error": "No credentials"}
        
        print(f"✅ ORCID credentials available: {orcid_user}")
        
        results = {
            "start_time": datetime.now().isoformat(),
            "sicon_results": {},
            "sifin_results": {}
        }
        
        try:
            self.setup_driver()
            
            # Extract SICON
            results["sicon_results"] = self.extract_journal_manuscripts("SICON", "http://sicon.siam.org")
            
            # Extract SIFIN
            results["sifin_results"] = self.extract_journal_manuscripts("SIFIN", "http://sifin.siam.org")
            
            # Save combined results
            with open(self.data_dir / "complete_results.json", 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            # Print detailed summary
            self.print_detailed_summary(results)
            
            return results
            
        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            return {"success": False, "error": str(e)}
        
        finally:
            if self.driver:
                self.driver.quit()
                print("\n🔄 Browser closed")
    
    def print_detailed_summary(self, results: Dict[str, Any]):
        """Print detailed extraction summary."""
        print("\n" + "="*80)
        print("📊 COMPLETE SIAM EXTRACTION SUMMARY")
        print("="*80)
        
        # SICON Summary
        sicon_data = results.get("sicon_results", {})
        if sicon_data.get("success"):
            manuscripts = sicon_data.get("manuscripts", [])
            print(f"\n✅ SICON: {len(manuscripts)} manuscripts")
            
            total_referees = 0
            referees_with_reports = 0
            
            for ms in manuscripts:
                print(f"\n   📄 {ms['manuscript_id']} - {ms['title'][:50]}...")
                print(f"      Status: {ms['current_stage']}")
                print(f"      Referees: {len(ms['referees'])}")
                
                for ref in ms['referees']:
                    total_referees += 1
                    status_symbol = "✅" if ref['status'] == "Report Received" else "⏳"
                    print(f"         {status_symbol} {ref['name']} - {ref['status']}")
                    if ref['status'] == "Report Received":
                        referees_with_reports += 1
            
            print(f"\n   📊 SICON Total: {total_referees} referees, {referees_with_reports} reports received")
        else:
            print(f"\n❌ SICON: Failed - {sicon_data.get('error', 'Unknown error')}")
        
        # SIFIN Summary
        sifin_data = results.get("sifin_results", {})
        if sifin_data.get("success"):
            manuscripts = sifin_data.get("manuscripts", [])
            print(f"\n✅ SIFIN: {len(manuscripts)} manuscripts")
            
            total_referees = 0
            referees_with_reports = 0
            
            for ms in manuscripts:
                print(f"\n   📄 {ms['manuscript_id']} - {ms['title'][:50]}...")
                print(f"      Status: {ms['current_stage']}")
                print(f"      Referees: {len(ms['referees'])}")
                
                for ref in ms['referees']:
                    total_referees += 1
                    status_symbol = "✅" if ref['status'] == "Report Received" else "⏳"
                    print(f"         {status_symbol} {ref['name']} - {ref['status']}")
                    if ref['status'] == "Report Received":
                        referees_with_reports += 1
            
            print(f"\n   📊 SIFIN Total: {total_referees} referees, {referees_with_reports} reports received")
        else:
            print(f"\n❌ SIFIN: Failed - {sifin_data.get('error', 'Unknown error')}")
        
        print(f"\n📁 All data saved to: {self.output_dir}")


def main():
    """Main entry point."""
    extractor = SIAMCompleteExtractor()
    results = extractor.run_complete_extraction()
    
    # Verify results match expectations
    sicon_mss = len(results.get("sicon_results", {}).get("manuscripts", []))
    sifin_mss = len(results.get("sifin_results", {}).get("manuscripts", []))
    
    print("\n" + "="*80)
    print("🎯 VERIFICATION")
    print("="*80)
    
    print(f"\nExpected:")
    print(f"  SICON: 4 papers with 4 referees (1 report each)")
    print(f"  SIFIN: 4 papers with 6 referees (2 reports total)")
    
    print(f"\nActual:")
    print(f"  SICON: {sicon_mss} papers")
    print(f"  SIFIN: {sifin_mss} papers")
    
    if sicon_mss == 4 and sifin_mss == 4:
        print("\n✅ SUCCESS! Found the expected manuscripts!")
    else:
        print("\n⚠️  Results don't match expectations")


if __name__ == "__main__":
    main()