#!/usr/bin/env python3
"""
Direct SIAM Data Extraction Script

This script uses direct SIAM credentials to extract data from SICON and SIFIN:
- Uses journal-specific usernames and passwords from .env
- Extracts ALL manuscript information
- Gets referee data (names, emails, statuses, due dates)
- Downloads manuscript PDFs and referee reports
"""

import os
import sys
import json
import time
import logging
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'direct_siam_extraction_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class DirectSIAMExtractor:
    """Direct SIAM data extraction using journal credentials."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        
        # Create organized output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_direct_extraction_{timestamp}')
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.manuscripts_dir = self.output_dir / 'manuscripts'
        self.referees_dir = self.output_dir / 'referee_reports'
        self.data_dir = self.output_dir / 'data'
        
        for dir_path in [self.manuscripts_dir, self.referees_dir, self.data_dir]:
            dir_path.mkdir(exist_ok=True)
        
        print(f"🗂️  Output directory created: {self.output_dir}")
    
    def setup_driver(self, headless: bool = False):
        """Setup Chrome WebDriver."""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        
        # Configure download directory
        prefs = {
            "download.default_directory": str(self.manuscripts_dir.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_page_load_timeout(30)
        self.wait = WebDriverWait(self.driver, 15)
        
        print("✅ Chrome WebDriver initialized")
    
    def remove_banners(self):
        """Remove cookie banners and overlays."""
        js_script = """
        var selectors = [
            '#cookie-policy-layer-bg', '#cookie-policy-layer', '.cc_banner-wrapper',
            '#onetrust-banner-sdk', '.modal-backdrop'
        ];
        selectors.forEach(function(sel) {
            var els = document.querySelectorAll(sel);
            els.forEach(function(el) { el.remove(); });
        });
        """
        try:
            self.driver.execute_script(js_script)
        except:
            pass
    
    def login_sicon(self) -> bool:
        """Login to SICON using direct credentials."""
        print("\n🔐 Logging into SICON...")
        
        # Get SICON credentials
        sicon_user = os.getenv("SICON_USERNAME")
        sicon_pass = os.getenv("SICON_PASSWORD")
        
        if not sicon_user or not sicon_pass:
            print("❌ SICON credentials not found")
            return False
        
        try:
            # Navigate to SICON
            self.driver.get("http://sicon.siam.org")
            time.sleep(3)
            self.remove_banners()
            
            # Look for login form
            login_form = None
            try:
                # Try to find username field first
                username_field = self.driver.find_element(By.NAME, "user_name")
                login_form = True
            except:
                # Try alternative selectors
                try:
                    username_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='text']")
                    login_form = True
                except:
                    print("   ⚠️ No direct login form found, checking for login link...")
                    
                    # Look for login link
                    try:
                        login_link = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Login') or contains(text(), 'Sign in')]")
                        login_link.click()
                        time.sleep(2)
                        username_field = self.driver.find_element(By.NAME, "user_name")
                        login_form = True
                    except:
                        pass
            
            if not login_form:
                print("   ❌ Could not find login form")
                return False
            
            # Fill username
            username_field.clear()
            username_field.send_keys(sicon_user)
            print(f"   ✅ Entered username: {sicon_user}")
            
            # Fill password
            password_field = self.driver.find_element(By.NAME, "password")
            password_field.clear()
            password_field.send_keys(sicon_pass)
            print("   ✅ Entered password")
            
            # Submit form
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit'], button[type='submit']")
            submit_button.click()
            print("   ✅ Submitted login form")
            
            time.sleep(3)
            
            # Check if login was successful
            if "logout" in self.driver.page_source.lower() or "associate editor" in self.driver.page_source.lower():
                print("   ✅ SICON login successful")
                return True
            else:
                print("   ❌ SICON login may have failed")
                return False
                
        except Exception as e:
            logger.error(f"SICON login failed: {e}")
            return False
    
    def login_sifin(self) -> bool:
        """Login to SIFIN using direct credentials."""
        print("\n🔐 Logging into SIFIN...")
        
        # Get SIFIN credentials
        sifin_user = os.getenv("SIFIN_USERNAME")
        sifin_pass = os.getenv("SIFIN_PASSWORD")
        
        if not sifin_user or not sifin_pass:
            print("❌ SIFIN credentials not found")
            return False
        
        try:
            # Navigate to SIFIN
            self.driver.get("http://sifin.siam.org")
            time.sleep(3)
            self.remove_banners()
            
            # Look for login form
            username_field = None
            try:
                username_field = self.driver.find_element(By.NAME, "user_name")
            except:
                try:
                    username_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='text']")
                except:
                    # Look for login link
                    try:
                        login_link = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Login') or contains(text(), 'Sign in')]")
                        login_link.click()
                        time.sleep(2)
                        username_field = self.driver.find_element(By.NAME, "user_name")
                    except:
                        pass
            
            if not username_field:
                print("   ❌ Could not find username field")
                return False
            
            # Fill username
            username_field.clear()
            username_field.send_keys(sifin_user)
            print(f"   ✅ Entered username: {sifin_user}")
            
            # Fill password
            password_field = self.driver.find_element(By.NAME, "password")
            password_field.clear()
            password_field.send_keys(sifin_pass)
            print("   ✅ Entered password")
            
            # Submit form
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit'], button[type='submit']")
            submit_button.click()
            print("   ✅ Submitted login form")
            
            time.sleep(3)
            
            # Check if login was successful
            if "logout" in self.driver.page_source.lower() or "associate editor" in self.driver.page_source.lower():
                print("   ✅ SIFIN login successful")
                return True
            else:
                print("   ❌ SIFIN login may have failed")
                return False
                
        except Exception as e:
            logger.error(f"SIFIN login failed: {e}")
            return False
    
    def extract_journal_data(self, journal_name: str, login_func) -> Dict[str, Any]:
        """Extract data from a journal."""
        print(f"\n📖 EXTRACTING {journal_name} DATA...")
        
        if not login_func():
            return {"success": False, "error": "Login failed"}
        
        try:
            time.sleep(2)
            self.remove_banners()
            
            # Parse the current page
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            manuscripts = []
            
            # Look for manuscript links
            manuscript_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                link_text = link.get_text(strip=True)
                
                # Look for manuscript view links
                if ('form_type=view_ms' in href or 
                    'manuscript' in href.lower() or 
                    link_text.startswith('#')):  # Manuscript numbers usually start with #
                    
                    base_url = f"http://{journal_name.lower()}.siam.org"
                    full_url = href if href.startswith('http') else urljoin(base_url, href)
                    manuscript_links.append((full_url, link_text))
            
            print(f"   📄 Found {len(manuscript_links)} potential manuscripts")
            
            # If no manuscript links found, look for them in associate editor sections
            if not manuscript_links:
                ae_sections = soup.find_all(['tbody', 'div'], attrs={'role': 'assoc_ed'})
                for section in ae_sections:
                    for link in section.find_all('a', href=True):
                        href = link.get('href', '')
                        if 'form_type=view_ms' in href:
                            base_url = f"http://{journal_name.lower()}.siam.org"
                            full_url = href if href.startswith('http') else urljoin(base_url, href)
                            manuscript_links.append((full_url, link.get_text(strip=True)))
            
            print(f"   📋 Processing {len(manuscript_links)} manuscripts...")
            
            # Extract data from each manuscript
            for i, (ms_url, ms_text) in enumerate(manuscript_links, 1):
                try:
                    print(f"   📄 Processing manuscript {i}: {ms_text}")
                    ms_data = self.extract_manuscript_details(ms_url, journal_name)
                    if ms_data:
                        manuscripts.append(ms_data)
                        
                        # Try to download PDF
                        self.download_manuscript_pdf(ms_url, ms_data, journal_name)
                        
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
            
            # Save data
            with open(self.data_dir / f"{journal_name.lower()}_data.json", 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"   ✅ {journal_name} extraction complete: {len(manuscripts)} manuscripts")
            return result
            
        except Exception as e:
            logger.error(f"{journal_name} extraction failed: {e}")
            return {"success": False, "error": str(e)}
    
    def extract_manuscript_details(self, ms_url: str, journal: str) -> Optional[Dict[str, Any]]:
        """Extract detailed manuscript information."""
        try:
            self.driver.get(ms_url)
            time.sleep(2)
            self.remove_banners()
            
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
            
            # Look for manuscript details in various table formats
            details_table = soup.find('table', id='ms_details_expanded')
            if not details_table:
                details_table = soup.find('table', class_='ms_details')
            if not details_table:
                # Look for any table with manuscript information
                for table in soup.find_all('table'):
                    if any(cell.get_text().lower().find('manuscript') >= 0 for cell in table.find_all(['th', 'td'])):
                        details_table = table
                        break
            
            if details_table:
                for row in details_table.find_all('tr'):
                    cells = row.find_all(['th', 'td'])
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)
                        
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
                            referees = self.extract_referee_info(cells[1], journal)
                            manuscript_data["referees"].extend(referees)
            
            # If we didn't find much data in tables, try to extract from page text
            if not manuscript_data["manuscript_id"]:
                page_text = soup.get_text()
                import re
                ms_id_match = re.search(r'manuscript\s*#?\s*([A-Z]+-\d{4}-\d+)', page_text, re.IGNORECASE)
                if ms_id_match:
                    manuscript_data["manuscript_id"] = ms_id_match.group(1)
            
            return manuscript_data if manuscript_data["manuscript_id"] else None
            
        except Exception as e:
            logger.error(f"Error extracting manuscript details: {e}")
            return None
    
    def extract_referee_info(self, referee_cell, journal: str) -> List[Dict[str, Any]]:
        """Extract referee information."""
        referees = []
        
        try:
            for link in referee_cell.find_all('a', href=True):
                referee_name = link.get_text(strip=True)
                referee_url = link.get('href')
                
                if referee_name and referee_url:
                    # Make URL absolute
                    if not referee_url.startswith('http'):
                        base_url = f"http://{journal.lower()}.siam.org"
                        referee_url = urljoin(base_url, referee_url)
                    
                    referees.append({
                        "name": referee_name,
                        "url": referee_url,
                        "email": self.get_referee_email(referee_url),
                        "status": "Unknown"
                    })
        except Exception as e:
            logger.error(f"Error extracting referee info: {e}")
        
        return referees
    
    def get_referee_email(self, referee_url: str) -> str:
        """Get referee email from profile page."""
        try:
            # Save current window
            current_window = self.driver.current_window_handle
            
            # Open in new tab
            self.driver.execute_script(f"window.open('{referee_url}', '_blank');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            time.sleep(1)
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Look for email
            email = ""
            mailto_link = soup.find('a', href=lambda x: x and x.startswith('mailto:'))
            if mailto_link:
                email = mailto_link.get('href').replace('mailto:', '')
            
            # Close tab and return to original
            self.driver.close()
            self.driver.switch_to.window(current_window)
            
            return email
        except:
            return ""
    
    def download_manuscript_pdf(self, ms_url: str, ms_data: Dict[str, Any], journal: str):
        """Download manuscript PDF."""
        try:
            # Look for PDF links on manuscript page
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                if 'pdf' in href.lower() or 'pdf' in text or 'download' in text:
                    try:
                        pdf_element = self.driver.find_element(By.XPATH, f"//a[@href='{href}']")
                        pdf_element.click()
                        print(f"      📥 Downloading PDF for {ms_data['manuscript_id']}")
                        time.sleep(2)
                        break
                    except:
                        continue
        except Exception as e:
            logger.debug(f"PDF download failed: {e}")
    
    def run_complete_extraction(self) -> Dict[str, Any]:
        """Run complete extraction."""
        print("🚀 STARTING DIRECT SIAM EXTRACTION")
        print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        results = {
            "start_time": datetime.now().isoformat(),
            "sicon_results": {},
            "sifin_results": {},
            "overall_success": False
        }
        
        try:
            self.setup_driver(headless=False)
            
            # Extract SICON data
            results["sicon_results"] = self.extract_journal_data("SICON", self.login_sicon)
            
            # Extract SIFIN data
            results["sifin_results"] = self.extract_journal_data("SIFIN", self.login_sifin)
            
            # Calculate success
            sicon_success = results["sicon_results"].get("success", False)
            sifin_success = results["sifin_results"].get("success", False)
            results["overall_success"] = sicon_success or sifin_success
            
            # Save results
            with open(self.data_dir / "complete_results.json", 'w') as f:
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
    
    def print_summary(self, results: Dict[str, Any]):
        """Print extraction summary."""
        print("\n" + "="*80)
        print("📊 DIRECT SIAM EXTRACTION SUMMARY")
        print("="*80)
        
        sicon_results = results.get("sicon_results", {})
        sifin_results = results.get("sifin_results", {})
        
        print(f"✅ SICON: {'Success' if sicon_results.get('success') else 'Failed'}")
        if sicon_results.get("success"):
            print(f"   📄 Manuscripts: {sicon_results.get('total_manuscripts', 0)}")
        
        print(f"✅ SIFIN: {'Success' if sifin_results.get('success') else 'Failed'}")
        if sifin_results.get("success"):
            print(f"   📄 Manuscripts: {sifin_results.get('total_manuscripts', 0)}")
        
        print(f"\n📁 Files saved to: {self.output_dir}")


def main():
    """Main entry point."""
    extractor = DirectSIAMExtractor()
    results = extractor.run_complete_extraction()
    
    if results.get("overall_success"):
        print("\n✅ Direct extraction completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Extraction had issues")
        sys.exit(1)


if __name__ == "__main__":
    main()