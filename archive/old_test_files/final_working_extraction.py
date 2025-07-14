#!/usr/bin/env python3
"""
Final Working SIAM Extraction Script

This version properly handles ORCID authentication and waits for successful redirect.
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, quote
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinalSIAMExtractor:
    """Final working SIAM extraction."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_final_extraction_{timestamp}')
        self.output_dir.mkdir(exist_ok=True)
        
        self.data_dir = self.output_dir / 'data'
        self.data_dir.mkdir(exist_ok=True)
        
        print(f"📁 Output directory: {self.output_dir}")
    
    def setup_driver(self):
        """Setup Chrome WebDriver."""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 30)
        
        print("✅ Chrome WebDriver initialized")
    
    def remove_cookie_banners(self):
        """Remove cookie banners."""
        try:
            self.driver.execute_script("""
                var elements = ['#cookie-policy-layer-bg', '#cookie-policy-layer', '.cc_banner-wrapper'];
                elements.forEach(function(sel) {
                    var els = document.querySelectorAll(sel);
                    els.forEach(function(el) { el.remove(); });
                });
            """)
        except:
            pass
    
    def authenticate_journal(self, journal_url: str, journal_name: str) -> bool:
        """Authenticate with journal using ORCID."""
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
            time.sleep(3)
            
            # Get credentials
            orcid_user = os.getenv("ORCID_USER")
            orcid_pass = os.getenv("ORCID_PASS")
            
            # Fill username
            username_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "username-input"))
            )
            username_field.clear()
            username_field.send_keys(orcid_user)
            print("   ✅ Entered username")
            
            # Fill password
            password_field = self.driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(orcid_pass)
            print("   ✅ Entered password")
            
            # Submit form
            password_field.send_keys(Keys.RETURN)
            print("   ⏳ Submitted credentials")
            
            # Wait for either redirect or authorization page
            print("   ⏳ Waiting for authentication...")
            start_time = time.time()
            while time.time() - start_time < 30:
                current_url = self.driver.current_url.lower()
                
                # Check if we're back on the journal
                if journal_name.lower() in current_url:
                    print(f"   ✅ Successfully authenticated with {journal_name}")
                    return True
                
                # Check if we're on an authorization page
                if 'authorize' in current_url:
                    print("   📋 Authorization page detected")
                    try:
                        # Look for authorize button
                        auth_button = self.driver.find_element(By.ID, "authorize")
                        if not auth_button:
                            auth_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Authorize')]")
                        auth_button.click()
                        print("   ✅ Clicked authorize button")
                    except:
                        pass
                
                time.sleep(2)
            
            # Check final URL
            if journal_name.lower() in self.driver.current_url.lower():
                print(f"   ✅ Successfully authenticated with {journal_name}")
                return True
            else:
                print(f"   ❌ Authentication failed - current URL: {self.driver.current_url}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication failed for {journal_name}: {e}")
            return False
    
    def extract_journal_data(self, journal_name: str, journal_url: str) -> Dict[str, Any]:
        """Extract manuscripts from journal."""
        print(f"\n📚 Extracting {journal_name} manuscripts...")
        
        if not self.authenticate_journal(journal_url, journal_name):
            return {"success": False, "error": "Authentication failed"}
        
        try:
            time.sleep(3)
            self.remove_cookie_banners()
            
            # Get page source
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Save page for debugging
            with open(self.data_dir / f"{journal_name}_dashboard.html", 'w') as f:
                f.write(self.driver.page_source)
            
            manuscripts = []
            
            # Method 1: Look for manuscript links in task rows
            print("   🔍 Looking for manuscripts...")
            task_rows = soup.find_all('tr', class_='ndt_task')
            print(f"   Found {len(task_rows)} task rows")
            
            for row in task_rows:
                link = row.find('a', class_='ndt_task_link')
                if link and link.get_text(strip=True).startswith('#'):
                    ms_id = link.get_text(strip=True)
                    ms_url = link.get('href', '')
                    if not ms_url.startswith('http'):
                        ms_url = urljoin(journal_url, ms_url)
                    
                    print(f"   📄 Found manuscript: {ms_id}")
                    
                    # Extract manuscript details
                    ms_data = self.extract_manuscript_details(ms_url, ms_id, journal_name)
                    if ms_data:
                        manuscripts.append(ms_data)
            
            # Method 2: Look for any links with manuscript patterns
            if not manuscripts:
                print("   🔍 Looking for manuscript links (method 2)...")
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    if 'form_type=view_ms' in href or (text.startswith('#') and len(text) > 1):
                        ms_url = href if href.startswith('http') else urljoin(journal_url, href)
                        print(f"   📄 Found manuscript link: {text}")
                        
                        ms_data = self.extract_manuscript_details(ms_url, text, journal_name)
                        if ms_data:
                            manuscripts.append(ms_data)
            
            result = {
                "success": True,
                "journal": journal_name,
                "manuscripts": manuscripts,
                "total_manuscripts": len(manuscripts),
                "extraction_time": datetime.now().isoformat()
            }
            
            # Save results
            with open(self.data_dir / f"{journal_name}_results.json", 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"   ✅ Extracted {len(manuscripts)} manuscripts from {journal_name}")
            return result
            
        except Exception as e:
            logger.error(f"Extraction failed for {journal_name}: {e}")
            return {"success": False, "error": str(e)}
    
    def extract_manuscript_details(self, ms_url: str, ms_id: str, journal: str) -> Optional[Dict[str, Any]]:
        """Extract detailed manuscript information."""
        try:
            print(f"      📋 Extracting details for {ms_id}...")
            self.driver.get(ms_url)
            time.sleep(2)
            self.remove_cookie_banners()
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            manuscript_data = {
                "manuscript_id": ms_id,
                "title": "",
                "authors": "",
                "submission_date": "",
                "current_stage": "",
                "referees": [],
                "url": ms_url
            }
            
            # Find manuscript details table
            details_table = soup.find('table', id='ms_details_expanded')
            if not details_table:
                details_table = soup.find('table', class_='ms_details')
            
            if details_table:
                for row in details_table.find_all('tr'):
                    cells = row.find_all(['th', 'td'])
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True).lower()
                        value_cell = cells[1]
                        value = value_cell.get_text(strip=True)
                        
                        if 'title' in label:
                            manuscript_data["title"] = value
                        elif 'author' in label:
                            manuscript_data["authors"] = value
                        elif 'submission' in label or 'submitted' in label:
                            manuscript_data["submission_date"] = value
                        elif 'stage' in label or 'status' in label:
                            manuscript_data["current_stage"] = value
                        elif 'referee' in label:
                            # Extract referee information
                            referee_links = value_cell.find_all('a', href=True)
                            for ref_link in referee_links:
                                ref_name = ref_link.get_text(strip=True)
                                ref_url = ref_link.get('href')
                                if not ref_url.startswith('http'):
                                    ref_url = urljoin(f"http://{journal.lower()}.siam.org", ref_url)
                                
                                # Check for status in surrounding text
                                parent_text = value_cell.get_text()
                                status = "Unknown"
                                if "accepted" in parent_text.lower():
                                    status = "Accepted"
                                elif "declined" in parent_text.lower():
                                    status = "Declined"
                                elif "contacted" in parent_text.lower():
                                    status = "Contacted"
                                
                                # Check if report is available
                                if "report" in parent_text.lower() or "review" in parent_text.lower():
                                    status += " (Report Available)"
                                
                                manuscript_data["referees"].append({
                                    "name": ref_name,
                                    "url": ref_url,
                                    "status": status
                                })
            
            print(f"      ✅ Title: {manuscript_data['title'][:50]}...")
            print(f"      ✅ Referees: {len(manuscript_data['referees'])}")
            
            return manuscript_data
            
        except Exception as e:
            logger.error(f"Error extracting details for {ms_id}: {e}")
            return None
    
    def run_extraction(self) -> Dict[str, Any]:
        """Run complete extraction."""
        print("\n🚀 STARTING FINAL SIAM EXTRACTION")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check credentials
        orcid_user = os.getenv("ORCID_USER")
        orcid_pass = os.getenv("ORCID_PASS")
        
        if not orcid_user or not orcid_pass:
            print("❌ ORCID credentials not found")
            return {"success": False, "error": "No credentials"}
        
        print(f"✅ ORCID user: {orcid_user}")
        
        results = {
            "start_time": datetime.now().isoformat(),
            "sicon_results": {},
            "sifin_results": {}
        }
        
        try:
            self.setup_driver()
            
            # Extract SICON
            results["sicon_results"] = self.extract_journal_data("SICON", "http://sicon.siam.org")
            
            # Extract SIFIN
            results["sifin_results"] = self.extract_journal_data("SIFIN", "http://sifin.siam.org")
            
            # Save combined results
            with open(self.data_dir / "combined_results.json", 'w') as f:
                json.dump(results, f, indent=2)
            
            # Print summary
            print("\n" + "="*80)
            print("📊 EXTRACTION SUMMARY")
            print("="*80)
            
            total_manuscripts = 0
            total_referees = 0
            
            for journal in ["sicon_results", "sifin_results"]:
                journal_data = results.get(journal, {})
                journal_name = journal.replace("_results", "").upper()
                
                if journal_data.get("success"):
                    manuscripts = journal_data.get("manuscripts", [])
                    num_manuscripts = len(manuscripts)
                    num_referees = sum(len(ms.get("referees", [])) for ms in manuscripts)
                    
                    total_manuscripts += num_manuscripts
                    total_referees += num_referees
                    
                    print(f"\n✅ {journal_name}:")
                    print(f"   📄 Manuscripts: {num_manuscripts}")
                    print(f"   👥 Total referees: {num_referees}")
                    
                    # Show manuscript details
                    for ms in manuscripts:
                        print(f"\n   📋 {ms['manuscript_id']}")
                        print(f"      Title: {ms['title'][:60]}...")
                        print(f"      Referees: {len(ms['referees'])}")
                        for ref in ms['referees']:
                            print(f"         • {ref['name']} - {ref['status']}")
                else:
                    print(f"\n❌ {journal_name}: Failed")
            
            print(f"\n📊 TOTAL: {total_manuscripts} manuscripts, {total_referees} referees")
            print(f"📁 Data saved to: {self.output_dir}")
            
            return results
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return {"success": False, "error": str(e)}
        
        finally:
            if self.driver:
                self.driver.quit()


def main():
    """Main entry point."""
    extractor = FinalSIAMExtractor()
    results = extractor.run_extraction()
    
    # Check if we found the expected data
    sicon_manuscripts = len(results.get("sicon_results", {}).get("manuscripts", []))
    sifin_manuscripts = len(results.get("sifin_results", {}).get("manuscripts", []))
    
    if sicon_manuscripts == 4 and sifin_manuscripts == 4:
        print("\n✅ SUCCESS! Found expected manuscripts:")
        print("   SICON: 4 papers ✓")
        print("   SIFIN: 4 papers ✓")
    else:
        print(f"\n⚠️  Found {sicon_manuscripts} SICON and {sifin_manuscripts} SIFIN manuscripts")
        print("   Expected: 4 SICON and 4 SIFIN manuscripts")


if __name__ == "__main__":
    main()