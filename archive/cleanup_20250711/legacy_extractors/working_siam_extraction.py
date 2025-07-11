#!/usr/bin/env python3
"""
Working SIAM Data Extraction Script

This script successfully connects to SICON and SIFIN journals and extracts:
- All manuscript information
- Referee data (names, emails, statuses)
- Downloads manuscript PDFs
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'working_siam_extraction_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class WorkingSIAMExtractor:
    """Working SIAM data extraction with proper authentication."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_working_extraction_{timestamp}')
        self.output_dir.mkdir(exist_ok=True)
        
        self.manuscripts_dir = self.output_dir / 'manuscripts'
        self.data_dir = self.output_dir / 'data'
        
        for dir_path in [self.manuscripts_dir, self.data_dir]:
            dir_path.mkdir(exist_ok=True)
        
        print(f"🗂️  Output directory: {self.output_dir}")
    
    def setup_driver(self, headless: bool = False):
        """Setup Chrome WebDriver."""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        
        # Configure downloads
        prefs = {
            "download.default_directory": str(self.manuscripts_dir.absolute()),
            "download.prompt_for_download": False,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_page_load_timeout(30)
        self.wait = WebDriverWait(self.driver, 20)
        
        print("✅ Chrome WebDriver initialized")
    
    def remove_cookie_banners(self):
        """Remove cookie banners that block interactions."""
        js_script = """
        // Remove cookie policy layers
        var cookieElements = document.querySelectorAll('#cookie-policy-layer-bg, #cookie-policy-layer, .cc_banner-wrapper');
        cookieElements.forEach(function(el) { 
            el.style.display = 'none'; 
            el.remove(); 
        });
        
        // Click any accept buttons
        var acceptButtons = document.querySelectorAll('button, a');
        acceptButtons.forEach(function(btn) {
            var text = btn.textContent.toLowerCase();
            if (text.includes('accept') || text.includes('agree')) {
                try { btn.click(); } catch(e) {}
            }
        });
        """
        
        try:
            self.driver.execute_script(js_script)
            time.sleep(1)
            print("   🍪 Cookie banners removed")
        except Exception as e:
            logger.debug(f"Cookie removal: {e}")
    
    def authenticate_journal(self, journal_url: str, journal_name: str) -> bool:
        """Authenticate with journal using ORCID."""
        print(f"\n🔐 Authenticating with {journal_name}...")
        
        try:
            # Navigate to journal
            self.driver.get(journal_url)
            time.sleep(3)
            
            # Remove cookie banners FIRST
            self.remove_cookie_banners()
            time.sleep(1)
            
            # Find ORCID login link
            orcid_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'orcid')]")
            print(f"   📍 Found ORCID link: {orcid_link.get_attribute('href')}")
            
            # Use JavaScript to click to avoid interception
            self.driver.execute_script("arguments[0].click();", orcid_link)
            print("   ✅ Clicked ORCID link")
            time.sleep(3)
            
            # Wait for ORCID page
            self.wait.until(lambda driver: 'orcid.org' in driver.current_url)
            print(f"   📍 Redirected to ORCID: {self.driver.current_url}")
            
            # Get credentials
            orcid_user = os.getenv("ORCID_USER")
            orcid_pass = os.getenv("ORCID_PASS")
            
            if not orcid_user or not orcid_pass:
                raise Exception("ORCID credentials not found")
            
            # Fill username with robust method
            print("   📝 Filling username...")
            username_field = None
            # Use the correct ID we discovered
            for selector in ["#username-input", "#username", "#userId", "input[placeholder*='Email' i]", "input[type='text']"]:
                try:
                    username_field = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    break
                except:
                    continue
            
            if not username_field:
                raise Exception("Cannot find username field")
            
            # Use JavaScript to set value to avoid interaction issues
            self.driver.execute_script(
                "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input'));",
                username_field, orcid_user
            )
            
            # Fill password
            print("   🔒 Filling password...")
            password_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            self.driver.execute_script(
                "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input'));",
                password_field, orcid_pass
            )
            
            # Submit form
            print("   ⏳ Submitting credentials...")
            submit_button = None
            for selector in ["#signin-button", "button[type='submit']"]:
                try:
                    submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if not submit_button:
                submit_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Sign in')]")
            
            self.driver.execute_script("arguments[0].click();", submit_button)
            time.sleep(5)
            
            # Wait for redirect back to journal
            print("   ⏳ Waiting for redirect...")
            start_time = time.time()
            while time.time() - start_time < 30:
                current_url = self.driver.current_url.lower()
                if journal_name.lower() in current_url:
                    print(f"   ✅ Successfully authenticated with {journal_name}")
                    return True
                time.sleep(2)
            
            raise Exception(f"Timeout waiting for redirect to {journal_name}")
            
        except Exception as e:
            logger.error(f"{journal_name} authentication failed: {e}")
            return False
    
    def extract_journal_manuscripts(self, journal_name: str, journal_url: str) -> Dict[str, Any]:
        """Extract manuscripts from authenticated journal."""
        print(f"\n📚 Extracting manuscripts from {journal_name}...")
        
        if not self.authenticate_journal(journal_url, journal_name):
            return {"success": False, "error": "Authentication failed"}
        
        try:
            time.sleep(3)
            self.remove_cookie_banners()
            
            # Parse current page for manuscripts
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            manuscripts = []
            
            # Look for manuscript links
            manuscript_links = []
            
            # Method 1: Look for associate editor sections
            ae_sections = soup.find_all('tbody', attrs={'role': 'assoc_ed'})
            for section in ae_sections:
                for link in section.find_all('a', class_='ndt_task_link'):
                    href = link.get('href', '')
                    if 'form_type=view_ms' in href:
                        full_url = href if href.startswith('http') else urljoin(journal_url, href)
                        manuscript_links.append((full_url, link.get_text(strip=True)))
            
            # Method 2: General manuscript link search
            if not manuscript_links:
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    if ('form_type=view_ms' in href or 
                        (text.startswith('#') and 'manuscript' in href.lower())):
                        full_url = href if href.startswith('http') else urljoin(journal_url, href)
                        manuscript_links.append((full_url, text))
            
            print(f"   📄 Found {len(manuscript_links)} manuscripts")
            
            # Extract data from each manuscript
            for i, (ms_url, ms_text) in enumerate(manuscript_links, 1):
                try:
                    print(f"   📋 Processing manuscript {i}: {ms_text}")
                    ms_data = self.extract_manuscript_details(ms_url, journal_name)
                    if ms_data:
                        manuscripts.append(ms_data)
                        
                        # Try to download PDF
                        self.download_manuscript_pdf(ms_url, ms_data)
                        
                except Exception as e:
                    logger.error(f"Error processing manuscript {ms_url}: {e}")
                    continue
            
            result = {
                "success": True,
                "journal": journal_name,
                "manuscripts": manuscripts,
                "total_manuscripts": len(manuscripts),
                "extraction_time": datetime.now().isoformat()
            }
            
            # Save individual journal data
            with open(self.data_dir / f"{journal_name.lower()}_manuscripts.json", 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"   ✅ {journal_name} extraction complete: {len(manuscripts)} manuscripts")
            return result
            
        except Exception as e:
            logger.error(f"{journal_name} extraction failed: {e}")
            return {"success": False, "error": str(e)}
    
    def extract_manuscript_details(self, ms_url: str, journal: str) -> Optional[Dict[str, Any]]:
        """Extract detailed manuscript information including referees."""
        try:
            self.driver.get(ms_url)
            time.sleep(2)
            self.remove_cookie_banners()
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            manuscript_data = {
                "manuscript_id": "",
                "title": "",
                "authors": "",
                "submission_date": "",
                "current_stage": "",
                "referees": [],
                "manuscript_url": ms_url
            }
            
            # Find manuscript details table
            details_table = soup.find('table', id='ms_details_expanded')
            if not details_table:
                details_table = soup.find('table', class_='ms_details')
            if not details_table:
                # Look for any table with manuscript info
                for table in soup.find_all('table'):
                    if any('manuscript' in cell.get_text().lower() for cell in table.find_all(['th', 'td'])):
                        details_table = table
                        break
            
            if details_table:
                for row in details_table.find_all('tr'):
                    th = row.find('th')
                    td = row.find('td')
                    
                    if not th or not td:
                        continue
                    
                    label = th.get_text(strip=True).lower()
                    value = td.get_text(strip=True)
                    
                    if 'manuscript' in label and '#' in label:
                        manuscript_data["manuscript_id"] = value
                    elif 'title' in label:
                        manuscript_data["title"] = value
                    elif 'author' in label:
                        manuscript_data["authors"] = value
                    elif 'submission' in label or 'submitted' in label:
                        manuscript_data["submission_date"] = value
                    elif 'stage' in label or 'status' in label:
                        manuscript_data["current_stage"] = value
                    elif 'referee' in label:
                        referees = self.extract_referee_info(td, journal)
                        manuscript_data["referees"].extend(referees)
            
            # Extract manuscript ID from URL if not found in table
            if not manuscript_data["manuscript_id"]:
                import re
                url_match = re.search(r'ms_id=([^&]+)', ms_url)
                if url_match:
                    manuscript_data["manuscript_id"] = url_match.group(1)
            
            return manuscript_data if manuscript_data["manuscript_id"] or manuscript_data["title"] else None
            
        except Exception as e:
            logger.error(f"Error extracting manuscript details: {e}")
            return None
    
    def extract_referee_info(self, referee_cell, journal: str) -> List[Dict[str, Any]]:
        """Extract referee information from table cell."""
        referees = []
        
        try:
            # Find referee links
            for link in referee_cell.find_all('a', href=True):
                referee_name = link.get_text(strip=True)
                referee_url = link.get('href')
                
                if not referee_name or not referee_url:
                    continue
                
                # Make URL absolute
                if not referee_url.startswith('http'):
                    base_url = f"http://{journal.lower()}.siam.org"
                    referee_url = urljoin(base_url, referee_url)
                
                # Extract status from surrounding text
                cell_text = referee_cell.get_text().lower()
                status = "Unknown"
                if 'accepted' in cell_text:
                    status = "Accepted"
                elif 'contacted' in cell_text:
                    status = "Contacted"
                elif 'declined' in cell_text:
                    status = "Declined"
                
                referee_data = {
                    "name": referee_name,
                    "url": referee_url,
                    "status": status,
                    "email": self.get_referee_email(referee_url)
                }
                
                referees.append(referee_data)
                
        except Exception as e:
            logger.error(f"Error extracting referee info: {e}")
        
        return referees
    
    def get_referee_email(self, referee_url: str) -> str:
        """Get referee email from profile page."""
        try:
            # Save current window
            current_window = self.driver.current_window_handle
            
            # Open referee page in new tab
            self.driver.execute_script(f"window.open('{referee_url}', '_blank');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            time.sleep(1)
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Look for email
            email = ""
            mailto_link = soup.find('a', href=lambda x: x and x.startswith('mailto:'))
            if mailto_link:
                email = mailto_link.get('href').replace('mailto:', '')
            else:
                # Look for email patterns in text
                import re
                email_pattern = r'\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b'
                page_text = soup.get_text()
                email_match = re.search(email_pattern, page_text)
                if email_match:
                    email = email_match.group(0)
            
            # Close tab and return to original
            self.driver.close()
            self.driver.switch_to.window(current_window)
            
            return email
            
        except Exception as e:
            logger.debug(f"Could not get email from {referee_url}: {e}")
            try:
                self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return ""
    
    def download_manuscript_pdf(self, ms_url: str, ms_data: Dict[str, Any]):
        """Download manuscript PDF if available."""
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Look for PDF download links
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                if ('pdf' in href.lower() or 'pdf' in text or 
                    'download' in text or 'manuscript' in text):
                    try:
                        pdf_element = self.driver.find_element(By.XPATH, f"//a[@href='{href}']")
                        self.driver.execute_script("arguments[0].click();", pdf_element)
                        print(f"      📥 Downloading PDF for {ms_data.get('manuscript_id', 'manuscript')}")
                        time.sleep(2)
                        break
                    except:
                        continue
                        
        except Exception as e:
            logger.debug(f"PDF download failed: {e}")
    
    def run_complete_extraction(self) -> Dict[str, Any]:
        """Run complete extraction for both journals."""
        print("🚀 STARTING WORKING SIAM EXTRACTION")
        print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check credentials
        orcid_user = os.getenv("ORCID_USER")
        orcid_pass = os.getenv("ORCID_PASS")
        
        if not orcid_user or not orcid_pass:
            print("❌ ORCID credentials not found")
            return {"success": False, "error": "No ORCID credentials"}
        
        print(f"✅ ORCID credentials: {orcid_user}")
        
        results = {
            "start_time": datetime.now().isoformat(),
            "sicon_results": {},
            "sifin_results": {},
            "overall_success": False
        }
        
        try:
            self.setup_driver(headless=False)  # Use visible browser
            
            # Extract SICON data
            results["sicon_results"] = self.extract_journal_manuscripts("SICON", "http://sicon.siam.org")
            
            # Extract SIFIN data
            results["sifin_results"] = self.extract_journal_manuscripts("SIFIN", "http://sifin.siam.org")
            
            # Calculate success
            sicon_success = results["sicon_results"].get("success", False)
            sifin_success = results["sifin_results"].get("success", False)
            results["overall_success"] = sicon_success or sifin_success
            
            # Save combined results
            results["end_time"] = datetime.now().isoformat()
            with open(self.data_dir / "complete_extraction.json", 'w') as f:
                json.dump(results, f, indent=2)
            
            self.print_summary(results)
            return results
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            results["error"] = str(e)
            return results
        
        finally:
            if self.driver:
                self.driver.quit()
                print("🔄 Browser closed")
    
    def print_summary(self, results: Dict[str, Any]):
        """Print extraction summary."""
        print("\\n" + "="*80)
        print("📊 WORKING SIAM EXTRACTION SUMMARY")
        print("="*80)
        
        sicon_results = results.get("sicon_results", {})
        sifin_results = results.get("sifin_results", {})
        
        sicon_success = sicon_results.get("success", False)
        sifin_success = sifin_results.get("success", False)
        
        print(f"{'✅' if sicon_success else '❌'} SICON: {'Success' if sicon_success else 'Failed'}")
        if sicon_success:
            sicon_manuscripts = sicon_results.get("total_manuscripts", 0)
            print(f"   📄 Manuscripts: {sicon_manuscripts}")
            if sicon_manuscripts > 0:
                for ms in sicon_results.get("manuscripts", [])[:3]:  # Show first 3
                    print(f"      • {ms.get('manuscript_id', 'N/A')}: {ms.get('title', 'No title')[:40]}...")
                    print(f"        👥 {len(ms.get('referees', []))} referees")
        
        print(f"{'✅' if sifin_success else '❌'} SIFIN: {'Success' if sifin_success else 'Failed'}")
        if sifin_success:
            sifin_manuscripts = sifin_results.get("total_manuscripts", 0)
            print(f"   📄 Manuscripts: {sifin_manuscripts}")
            if sifin_manuscripts > 0:
                for ms in sifin_results.get("manuscripts", [])[:3]:  # Show first 3
                    print(f"      • {ms.get('manuscript_id', 'N/A')}: {ms.get('title', 'No title')[:40]}...")
                    print(f"        👥 {len(ms.get('referees', []))} referees")
        
        total_manuscripts = (sicon_results.get("total_manuscripts", 0) + 
                           sifin_results.get("total_manuscripts", 0))
        
        print(f"\\n📊 Total manuscripts extracted: {total_manuscripts}")
        print(f"📁 All data saved to: {self.output_dir}")
        print(f"📄 Individual journal files: {self.data_dir}")
        print(f"📥 PDFs downloaded to: {self.manuscripts_dir}")


def main():
    """Main entry point."""
    extractor = WorkingSIAMExtractor()
    results = extractor.run_complete_extraction()
    
    if results.get("overall_success"):
        print("\\n🎉 EXTRACTION COMPLETED SUCCESSFULLY!")
        print("\\n📋 Summary of extracted data:")
        
        total_manuscripts = 0
        total_referees = 0
        
        for journal in ["sicon_results", "sifin_results"]:
            journal_data = results.get(journal, {})
            if journal_data.get("success"):
                manuscripts = journal_data.get("manuscripts", [])
                total_manuscripts += len(manuscripts)
                
                for ms in manuscripts:
                    total_referees += len(ms.get("referees", []))
        
        print(f"   📚 Total manuscripts: {total_manuscripts}")
        print(f"   👥 Total referees: {total_referees}")
        print(f"   📁 Data location: {extractor.output_dir}")
        
        sys.exit(0)
    else:
        print("\\n❌ Extraction had issues - check logs for details")
        sys.exit(1)


if __name__ == "__main__":
    main()