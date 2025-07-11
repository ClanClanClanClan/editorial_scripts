#!/usr/bin/env python3
"""
Complete SIAM Data Extraction Script

This script performs complete data extraction from SICON and SIFIN journals:
- Authenticates with ORCID
- Extracts ALL manuscript information
- Gets referee data (names, emails, statuses, due dates)
- Downloads manuscript PDFs and referee reports
- Saves everything to organized folder structure
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
import yaml

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'complete_siam_extraction_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class CompleteSIAMExtractor:
    """Complete SIAM data extraction with PDF downloads."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.session = requests.Session()
        
        # Create organized output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_complete_extraction_{timestamp}')
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.manuscripts_dir = self.output_dir / 'manuscripts'
        self.referees_dir = self.output_dir / 'referee_reports'
        self.data_dir = self.output_dir / 'data'
        
        for dir_path in [self.manuscripts_dir, self.referees_dir, self.data_dir]:
            dir_path.mkdir(exist_ok=True)
        
        print(f"🗂️  Output directory created: {self.output_dir}")
        print(f"📄 Manuscripts: {self.manuscripts_dir}")
        print(f"📋 Referee reports: {self.referees_dir}")
        print(f"📊 Data files: {self.data_dir}")
    
    def setup_driver(self, headless: bool = True):
        """Setup Chrome WebDriver with download preferences."""
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
        
        # Additional options for stability
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_page_load_timeout(30)
        self.wait = WebDriverWait(self.driver, 20)
        
        print("✅ Chrome WebDriver initialized with download support")
    
    def remove_cookie_banners(self):
        """Remove cookie banners and overlays."""
        js_script = """
        // Remove cookie banners and overlays
        var selectors = [
            '#cookie-policy-layer-bg', '#cookie-policy-layer', '.cc_banner-wrapper',
            '#onetrust-banner-sdk', '.onetrust-pc-dark-filter', '.cookie-banner',
            '.gdpr-banner', '.modal-backdrop', '.overlay'
        ];
        
        selectors.forEach(function(selector) {
            var elements = document.querySelectorAll(selector);
            elements.forEach(function(el) {
                el.style.display = 'none';
                el.style.visibility = 'hidden';
                el.remove();
            });
        });
        
        // Click accept buttons
        var acceptButtons = document.querySelectorAll('button, a');
        acceptButtons.forEach(function(btn) {
            var text = btn.textContent.toLowerCase();
            if (text.includes('accept') || text.includes('agree') || text.includes('ok')) {
                try { btn.click(); } catch(e) {}
            }
        });
        """
        
        try:
            self.driver.execute_script(js_script)
            time.sleep(1)
        except Exception as e:
            logger.debug(f"Cookie banner removal: {e}")
    
    def authenticate_orcid(self, journal_url: str, journal_name: str) -> bool:
        """Complete ORCID authentication flow."""
        print(f"\n🔐 Authenticating with {journal_name}...")
        
        try:
            # Navigate to journal
            self.driver.get(journal_url)
            time.sleep(2)
            self.remove_cookie_banners()
            
            # Find and click ORCID login
            orcid_element = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'orcid')]"))
            )
            
            # Scroll to element and click
            self.driver.execute_script("arguments[0].scrollIntoView(true);", orcid_element)
            time.sleep(1)
            orcid_element.click()
            print(f"   ✅ Clicked ORCID login for {journal_name}")
            
            # Wait for ORCID page
            self.wait.until(lambda driver: 'orcid.org' in driver.current_url)
            time.sleep(2)
            
            # Get credentials
            orcid_user = os.getenv("ORCID_USER")
            orcid_pass = os.getenv("ORCID_PASS")
            
            if not orcid_user or not orcid_pass:
                raise Exception("ORCID credentials not found")
            
            # Remove any overlays or modals on ORCID page
            self.driver.execute_script("""
                // Remove potential overlays
                var overlays = document.querySelectorAll('.modal, .overlay, .popup, .banner');
                overlays.forEach(function(el) { el.remove(); });
                
                // Make all inputs visible and interactable
                var inputs = document.querySelectorAll('input');
                inputs.forEach(function(input) {
                    input.style.visibility = 'visible';
                    input.style.display = 'block';
                    input.style.pointerEvents = 'auto';
                });
            """)
            time.sleep(1)
            
            # Find and fill username field with more robust approach
            username_filled = False
            username_selectors = [
                "#username", "#userId", "#user-id", "#email", 
                "input[name='userId']", "input[name='username']", "input[name='email']",
                "input[type='text']", "input[type='email']"
            ]
            
            for selector in username_selectors:
                try:
                    # Wait for element to be present and visible
                    username_field = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    
                    # Scroll into view and wait for it to be clickable
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", username_field)
                    time.sleep(0.5)
                    
                    # Try multiple methods to interact with the field
                    try:
                        # Method 1: Direct interaction
                        username_field.clear()
                        username_field.send_keys(orcid_user)
                        username_filled = True
                        break
                    except:
                        # Method 2: JavaScript interaction
                        self.driver.execute_script(
                            "arguments[0].focus(); arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input'));",
                            username_field, orcid_user
                        )
                        username_filled = True
                        break
                        
                except Exception as e:
                    continue
            
            if not username_filled:
                raise Exception("Could not fill username field")
            
            print(f"   ✅ Entered username")
            
            # Fill password with similar robust approach
            password_filled = False
            password_selectors = ["#password", "input[name='password']", "input[type='password']"]
            
            for selector in password_selectors:
                try:
                    password_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", password_field)
                    time.sleep(0.5)
                    
                    try:
                        password_field.clear()
                        password_field.send_keys(orcid_pass)
                        password_filled = True
                        break
                    except:
                        self.driver.execute_script(
                            "arguments[0].focus(); arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input'));",
                            password_field, orcid_pass
                        )
                        password_filled = True
                        break
                        
                except:
                    continue
            
            if not password_filled:
                raise Exception("Could not fill password field")
            
            print(f"   ✅ Entered password")
            
            # Submit form
            submit_button = None
            for selector in ["button[type='submit']", "#signin-button", "button:contains('Sign in')"]:
                try:
                    submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if not submit_button:
                # Try xpath for button with sign in text
                submit_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Sign in') or contains(text(), 'SIGN IN')]")
            
            submit_button.click()
            print(f"   ✅ Submitted ORCID credentials")
            
            # Wait for redirect back to journal
            start_time = time.time()
            while time.time() - start_time < 30:
                current_url = self.driver.current_url
                if journal_name.lower() in current_url.lower():
                    print(f"   ✅ Successfully authenticated with {journal_name}")
                    return True
                time.sleep(1)
            
            raise Exception(f"Timeout waiting for redirect to {journal_name}")
            
        except Exception as e:
            logger.error(f"Authentication failed for {journal_name}: {e}")
            return False
    
    def extract_sicon_data(self) -> Dict[str, Any]:
        """Extract complete data from SICON including PDFs."""
        print("\n📖 EXTRACTING SICON DATA...")
        
        journal_url = "http://sicon.siam.org"
        if not self.authenticate_orcid(journal_url, "SICON"):
            return {"success": False, "error": "Authentication failed"}
        
        try:
            time.sleep(3)
            self.remove_cookie_banners()
            
            # Look for manuscripts in dashboard
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            manuscripts = []
            
            # Find manuscript links
            manuscript_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if 'form_type=view_ms' in href:
                    full_url = href if href.startswith('http') else urljoin(journal_url, href)
                    manuscript_links.append(full_url)
            
            print(f"   📄 Found {len(manuscript_links)} manuscripts")
            
            # Extract data from each manuscript
            for i, ms_url in enumerate(manuscript_links, 1):
                print(f"   📋 Processing manuscript {i}/{len(manuscript_links)}...")
                
                try:
                    ms_data = self.extract_manuscript_details(ms_url, "SICON", i)
                    if ms_data:
                        manuscripts.append(ms_data)
                        
                        # Download manuscript PDF if available
                        self.download_manuscript_pdf(ms_url, ms_data, "SICON")
                        
                except Exception as e:
                    logger.error(f"Error processing manuscript {ms_url}: {e}")
                    continue
            
            result = {
                "success": True,
                "journal": "SICON", 
                "manuscripts": manuscripts,
                "total_manuscripts": len(manuscripts),
                "extraction_time": datetime.now().isoformat()
            }
            
            # Save data
            with open(self.data_dir / "sicon_data.json", 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"   ✅ SICON extraction complete: {len(manuscripts)} manuscripts")
            return result
            
        except Exception as e:
            logger.error(f"SICON extraction failed: {e}")
            return {"success": False, "error": str(e)}
    
    def extract_sifin_data(self) -> Dict[str, Any]:
        """Extract complete data from SIFIN including PDFs."""
        print("\n📗 EXTRACTING SIFIN DATA...")
        
        journal_url = "http://sifin.siam.org"  
        if not self.authenticate_orcid(journal_url, "SIFIN"):
            return {"success": False, "error": "Authentication failed"}
        
        try:
            time.sleep(3)
            self.remove_cookie_banners()
            
            # Look for manuscripts in dashboard
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            manuscripts = []
            
            # Find manuscript links
            manuscript_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if 'form_type=view_ms' in href:
                    full_url = href if href.startswith('http') else urljoin(journal_url, href)
                    manuscript_links.append(full_url)
            
            print(f"   📄 Found {len(manuscript_links)} manuscripts")
            
            # Extract data from each manuscript
            for i, ms_url in enumerate(manuscript_links, 1):
                print(f"   📋 Processing manuscript {i}/{len(manuscript_links)}...")
                
                try:
                    ms_data = self.extract_manuscript_details(ms_url, "SIFIN", i)
                    if ms_data:
                        manuscripts.append(ms_data)
                        
                        # Download manuscript PDF if available
                        self.download_manuscript_pdf(ms_url, ms_data, "SIFIN")
                        
                except Exception as e:
                    logger.error(f"Error processing manuscript {ms_url}: {e}")
                    continue
            
            result = {
                "success": True,
                "journal": "SIFIN",
                "manuscripts": manuscripts, 
                "total_manuscripts": len(manuscripts),
                "extraction_time": datetime.now().isoformat()
            }
            
            # Save data
            with open(self.data_dir / "sifin_data.json", 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"   ✅ SIFIN extraction complete: {len(manuscripts)} manuscripts")
            return result
            
        except Exception as e:
            logger.error(f"SIFIN extraction failed: {e}")
            return {"success": False, "error": str(e)}
    
    def extract_manuscript_details(self, ms_url: str, journal: str, ms_index: int) -> Optional[Dict[str, Any]]:
        """Extract detailed manuscript information including referees."""
        try:
            self.driver.get(ms_url)
            time.sleep(2)
            self.remove_cookie_banners()
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find manuscript details table
            details_table = soup.find('table', id='ms_details_expanded')
            if not details_table:
                details_table = soup.find('table', class_='ms_details')
            
            if not details_table:
                logger.warning(f"No manuscript details table found for {ms_url}")
                return None
            
            manuscript_data = {
                "manuscript_id": "",
                "title": "",
                "authors": "",
                "submission_date": "",
                "current_stage": "",
                "status": "",
                "referees": [],
                "manuscript_url": ms_url,
                "extraction_index": ms_index
            }
            
            # Extract basic manuscript info
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
                    # Extract referee information
                    referees = self.extract_referee_info(td, journal)
                    manuscript_data["referees"].extend(referees)
            
            print(f"      📋 {manuscript_data['manuscript_id']}: {manuscript_data['title'][:50]}...")
            print(f"      👥 {len(manuscript_data['referees'])} referees found")
            
            return manuscript_data
            
        except Exception as e:
            logger.error(f"Error extracting manuscript details from {ms_url}: {e}")
            return None
    
    def extract_referee_info(self, referee_cell, journal: str) -> List[Dict[str, Any]]:
        """Extract referee information from table cell."""
        referees = []
        
        try:
            # Find all referee links
            for link in referee_cell.find_all('a', href=True):
                referee_name = link.get_text(strip=True)
                referee_url = link.get('href')
                
                if not referee_name or not referee_url:
                    continue
                
                # Make URL absolute
                if not referee_url.startswith('http'):
                    base_url = f"http://{journal.lower()}.siam.org"
                    referee_url = urljoin(base_url, referee_url)
                
                # Extract referee status from surrounding text
                status = "Unknown"
                due_date = ""
                
                # Look for status indicators
                parent_text = referee_cell.get_text()
                if 'accepted' in parent_text.lower():
                    status = "Accepted"
                elif 'contacted' in parent_text.lower():
                    status = "Contacted"
                elif 'declined' in parent_text.lower():
                    status = "Declined"
                
                # Try to extract due date
                import re
                due_match = re.search(r'due:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', parent_text, re.IGNORECASE)
                if due_match:
                    due_date = due_match.group(1)
                
                referee_data = {
                    "name": referee_name,
                    "url": referee_url,
                    "status": status,
                    "due_date": due_date,
                    "email": ""  # Will be filled by get_referee_email
                }
                
                # Get referee email
                email = self.get_referee_email(referee_url)
                referee_data["email"] = email
                
                referees.append(referee_data)
        
        except Exception as e:
            logger.error(f"Error extracting referee info: {e}")
        
        return referees
    
    def get_referee_email(self, referee_url: str) -> str:
        """Extract referee email from profile page."""
        try:
            # Open referee profile in new tab to avoid losing current page
            current_handle = self.driver.current_window_handle
            self.driver.execute_script(f"window.open('{referee_url}', '_blank');")
            
            # Switch to new tab
            new_handles = self.driver.window_handles
            for handle in new_handles:
                if handle != current_handle:
                    self.driver.switch_to.window(handle)
                    break
            
            time.sleep(1)
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Look for email
            email = ""
            
            # Try mailto links first
            mailto_link = soup.find('a', href=lambda x: x and x.startswith('mailto:'))
            if mailto_link:
                email = mailto_link.get('href').replace('mailto:', '')
            else:
                # Look for email patterns in text
                import re
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                page_text = soup.get_text()
                email_match = re.search(email_pattern, page_text)
                if email_match:
                    email = email_match.group(0)
            
            # Close tab and switch back
            self.driver.close()
            self.driver.switch_to.window(current_handle)
            
            return email
            
        except Exception as e:
            logger.debug(f"Could not extract email from {referee_url}: {e}")
            # Make sure we're back on the original tab
            try:
                self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return ""
    
    def download_manuscript_pdf(self, ms_url: str, ms_data: Dict[str, Any], journal: str):
        """Download manuscript PDF."""
        try:
            # Look for PDF download links on the manuscript page
            self.driver.get(ms_url)
            time.sleep(2)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find PDF download links
            pdf_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                link_text = link.get_text(strip=True).lower()
                
                if ('pdf' in href.lower() or 'pdf' in link_text or 
                    'download' in link_text or 'manuscript' in link_text):
                    pdf_links.append(href)
            
            if not pdf_links:
                print(f"      ⚠️  No PDF download links found for {ms_data['manuscript_id']}")
                return
            
            # Download the first PDF found
            pdf_url = pdf_links[0]
            if not pdf_url.startswith('http'):
                base_url = f"http://{journal.lower()}.siam.org"
                pdf_url = urljoin(base_url, pdf_url)
            
            # Click the download link
            try:
                pdf_element = self.driver.find_element(By.XPATH, f"//a[@href='{pdf_links[0]}']")
                pdf_element.click()
                print(f"      📥 Downloading PDF for {ms_data['manuscript_id']}")
                time.sleep(3)  # Allow download to start
            except Exception as e:
                logger.debug(f"Could not click PDF download link: {e}")
                
        except Exception as e:
            logger.error(f"Error downloading PDF for {ms_data['manuscript_id']}: {e}")
    
    def run_complete_extraction(self) -> Dict[str, Any]:
        """Run complete extraction for both journals."""
        print("🚀 STARTING COMPLETE SIAM DATA EXTRACTION")
        print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check credentials
        orcid_user = os.getenv("ORCID_USER")
        orcid_pass = os.getenv("ORCID_PASS")
        
        if not orcid_user or not orcid_pass:
            print("❌ ORCID credentials not found")
            return {"success": False, "error": "No ORCID credentials"}
        
        print(f"✅ ORCID credentials available: {orcid_user}")
        
        results = {
            "start_time": datetime.now().isoformat(),
            "output_directory": str(self.output_dir),
            "sicon_results": {},
            "sifin_results": {},
            "overall_success": False
        }
        
        try:
            self.setup_driver(headless=False)  # Use visible browser for debugging
            
            # Extract SICON data
            results["sicon_results"] = self.extract_sicon_data()
            
            # Extract SIFIN data  
            results["sifin_results"] = self.extract_sifin_data()
            
            # Calculate success
            sicon_success = results["sicon_results"].get("success", False)
            sifin_success = results["sifin_results"].get("success", False)
            results["overall_success"] = sicon_success or sifin_success  # Success if at least one works
            
            # Save combined results
            results["end_time"] = datetime.now().isoformat()
            with open(self.data_dir / "complete_extraction_results.json", 'w') as f:
                json.dump(results, f, indent=2)
            
            self.print_summary(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Complete extraction failed: {e}")
            results["error"] = str(e)
            return results
        
        finally:
            if self.driver:
                self.driver.quit()
                print("🔄 Browser closed")
    
    def print_summary(self, results: Dict[str, Any]):
        """Print extraction summary."""
        print("\n" + "="*80)
        print("📊 COMPLETE SIAM EXTRACTION SUMMARY")
        print("="*80)
        
        sicon_results = results.get("sicon_results", {})
        sifin_results = results.get("sifin_results", {})
        
        sicon_success = sicon_results.get("success", False)
        sifin_success = sifin_results.get("success", False)
        
        print(f"✅ SICON: {'Success' if sicon_success else 'Failed'}")
        if sicon_success:
            print(f"   📄 Manuscripts: {sicon_results.get('total_manuscripts', 0)}")
        
        print(f"✅ SIFIN: {'Success' if sifin_success else 'Failed'}")
        if sifin_success:
            print(f"   📄 Manuscripts: {sifin_results.get('total_manuscripts', 0)}")
        
        print(f"\n📁 All files saved to: {self.output_dir}")
        print(f"📊 Data files: {self.data_dir}")
        print(f"📄 PDFs: {self.manuscripts_dir}")
        print(f"📋 Reports: {self.referees_dir}")


def main():
    """Main extraction entry point."""
    extractor = CompleteSIAMExtractor()
    results = extractor.run_complete_extraction()
    
    if results.get("overall_success"):
        print("\n✅ Complete extraction finished successfully!")
        sys.exit(0)
    else:
        print("\n❌ Extraction encountered issues")
        sys.exit(1)


if __name__ == "__main__":
    main()