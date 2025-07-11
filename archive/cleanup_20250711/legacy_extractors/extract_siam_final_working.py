#!/usr/bin/env python3
"""
Final working SIAM extraction - handles authentication and gets all data
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


class FinalSIAMExtractor:
    """Final working extractor for all SIAM data."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.main_window = None
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_final_{timestamp}')
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.download_dir = self.output_dir / 'temp_downloads'
        self.download_dir.mkdir(exist_ok=True)
        
        self.dirs = {
            'manuscripts': self.output_dir / 'manuscripts',
            'cover_letters': self.output_dir / 'cover_letters',
            'reports': self.output_dir / 'reports',
            'data': self.output_dir / 'data',
            'screenshots': self.output_dir / 'screenshots'
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(exist_ok=True)
        
        print(f"📁 Output directory: {self.output_dir}")
    
    def setup_driver(self, headless=False):
        """Setup Chrome WebDriver with proper configuration."""
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument('--headless')
        
        # Download configuration
        prefs = {
            "download.default_directory": str(self.download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": True,
            "safebrowsing_for_trusted_sources_enabled": False
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Additional options for stability
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Enable downloads in headless mode
        if headless:
            self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
                "behavior": "allow",
                "downloadPath": str(self.download_dir)
            })
        
        self.wait = WebDriverWait(self.driver, 30)
        self.driver.implicitly_wait(10)
        
        print("✅ Chrome WebDriver initialized")
    
    def save_screenshot(self, name):
        """Save screenshot for debugging."""
        try:
            path = self.dirs['screenshots'] / f"{name}.png"
            self.driver.save_screenshot(str(path))
            print(f"📸 Screenshot: {name}.png")
        except:
            pass
    
    def remove_popups(self):
        """Remove cookie banners and popups."""
        try:
            self.driver.execute_script("""
                // Remove cookie layers
                ['#cookie-policy-layer-bg', '#cookie-policy-layer', '.cc-banner', '.cookie-banner'].forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => el.remove());
                });
                
                // Click continue buttons
                ['#continue-btn', '.accept-cookies', '.agree-button'].forEach(sel => {
                    var btn = document.querySelector(sel);
                    if (btn) btn.click();
                });
                
                // Remove overlays
                document.querySelectorAll('[style*="z-index: 100"]').forEach(el => {
                    if (el.style.position === 'fixed') el.remove();
                });
            """)
        except:
            pass
    
    def authenticate_sicon(self):
        """Authenticate with SICON using ORCID."""
        print("\n🔐 Authenticating with SICON...")
        
        self.driver.get("http://sicon.siam.org")
        time.sleep(3)
        self.main_window = self.driver.current_window_handle
        
        self.remove_popups()
        self.save_screenshot("01_sicon_home")
        
        # Check if already authenticated
        page_source = self.driver.page_source.lower()
        if any(term in page_source for term in ['logout', 'dpossama', 'possamaï', 'my account']):
            print("✅ Already authenticated!")
            return True
        
        try:
            # Find and click ORCID link
            orcid_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'orcid') or contains(text(), 'ORCID')]")
            if not orcid_links:
                print("❌ No ORCID login link found")
                return False
            
            # Try clicking with JavaScript
            self.driver.execute_script("arguments[0].click();", orcid_links[0])
            
            # Wait for ORCID page
            time.sleep(3)
            if 'orcid.org' not in self.driver.current_url:
                print("❌ Did not navigate to ORCID")
                return False
            
            self.save_screenshot("02_orcid_login")
            
            # Fill ORCID credentials
            username = self.wait.until(EC.presence_of_element_located((By.ID, "username-input")))
            username.clear()
            username.send_keys("0000-0002-9364-0124")
            
            password = self.driver.find_element(By.ID, "password")
            password.clear()
            password.send_keys("Hioupy0042%")
            
            # Submit
            password.send_keys(Keys.RETURN)
            
            print("⏳ Waiting for authentication...")
            
            # Wait for redirect back to SICON
            timeout = time.time() + 30
            while time.time() < timeout:
                if 'sicon.siam.org' in self.driver.current_url:
                    print("✅ Successfully authenticated!")
                    time.sleep(3)
                    self.save_screenshot("03_authenticated")
                    return True
                time.sleep(1)
            
            print("❌ Authentication timeout")
            return False
            
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            self.save_screenshot("auth_error")
            return False
    
    def navigate_to_all_pending(self):
        """Navigate to All Pending Manuscripts."""
        print("\n📋 Navigating to All Pending Manuscripts...")
        
        # First, make sure we're on the home page
        if 'home' not in self.driver.current_url:
            self.driver.get("http://sicon.siam.org/cgi-bin/main.plex?form_type=home")
            time.sleep(2)
        
        self.remove_popups()
        
        # Look for folder structure
        # Try to find and expand the Associate Editor Tasks section
        try:
            # Look for the Under Review folder first
            under_review_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'folder_id=1400')]")
            if under_review_links:
                print("   Found Under Review folder")
                under_review_links[0].click()
                time.sleep(2)
                self.save_screenshot("04_under_review")
                return True
        except:
            pass
        
        # Try All Pending Manuscripts directly
        try:
            all_pending_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'folder_id=1800')]")
            if all_pending_links:
                print("   Found All Pending Manuscripts")
                all_pending_links[0].click()
                time.sleep(2)
                self.save_screenshot("05_all_pending")
                return True
        except:
            pass
        
        # If not found, look for any manuscript links
        ms_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'M17')]")
        if ms_links:
            print(f"   Found {len(ms_links)} manuscript links directly")
            return True
        
        print("❌ Could not find manuscript folders")
        self.save_screenshot("navigation_failed")
        return False
    
    def extract_manuscripts_from_page(self):
        """Extract manuscripts from the current page."""
        print("\n📊 Extracting manuscripts...")
        
        manuscripts = []
        
        # Method 1: Look for manuscript links in list view
        ms_pattern = re.compile(r'(M\d+)')
        
        # Find all links that contain manuscript IDs
        all_links = self.driver.find_elements(By.TAG_NAME, "a")
        
        for link in all_links:
            try:
                link_text = link.text
                href = link.get_attribute('href')
                
                if not link_text or not href:
                    continue
                
                # Check if this is a manuscript link
                ms_match = ms_pattern.search(link_text)
                if ms_match and 'view_ms' in href:
                    ms_id = ms_match.group(1)
                    
                    # Skip if we already have this manuscript
                    if any(m['manuscript_id'] == ms_id for m in manuscripts):
                        continue
                    
                    print(f"   Found manuscript: {ms_id}")
                    
                    # Extract basic info from link text
                    ms_data = {
                        'manuscript_id': ms_id,
                        'url': href,
                        'link_text': link_text
                    }
                    
                    # Try to parse additional info from link text
                    # Format: "Submit Review # M172838 (Yu) 141 days (for LI due on 2025-04-17)"
                    author_match = re.search(r'\(([^)]+)\)', link_text)
                    if author_match:
                        ms_data['author'] = author_match.group(1)
                    
                    referee_match = re.search(r'for\s+(\w+)\s+due', link_text)
                    if referee_match:
                        ms_data['awaiting_referee'] = referee_match.group(1)
                    
                    manuscripts.append(ms_data)
                    
            except Exception as e:
                continue
        
        # Method 2: If no manuscripts found, try table view
        if not manuscripts:
            print("   Trying table extraction...")
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            
            for table in tables:
                rows = table.find_elements(By.TAG_NAME, "tr")
                
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if cells:
                        first_cell = cells[0].text.strip()
                        
                        # Check if this is a manuscript row
                        if ms_pattern.match(first_cell):
                            ms_id = first_cell
                            
                            # Find link in this row
                            links = cells[0].find_elements(By.TAG_NAME, "a")
                            if links:
                                ms_data = {
                                    'manuscript_id': ms_id,
                                    'url': links[0].get_attribute('href'),
                                    'title': cells[1].text if len(cells) > 1 else ""
                                }
                                manuscripts.append(ms_data)
                                print(f"   Found manuscript in table: {ms_id}")
        
        print(f"   Total manuscripts found: {len(manuscripts)}")
        return manuscripts
    
    def extract_manuscript_details(self, manuscript):
        """Extract detailed information for a manuscript."""
        ms_id = manuscript['manuscript_id']
        print(f"\n{'='*60}")
        print(f"📄 Processing {ms_id}")
        print('='*60)
        
        # Navigate to manuscript
        self.driver.get(manuscript['url'])
        time.sleep(2)
        self.remove_popups()
        
        # Initialize detailed data
        detailed_data = manuscript.copy()
        detailed_data.update({
            'title': '',
            'authors': '',
            'corresponding_editor': '',
            'associate_editor': '',
            'submission_date': '',
            'current_stage': '',
            'referees': [],
            'files': {
                'manuscript': None,
                'cover_letter': None,
                'reports': []
            }
        })
        
        # Extract from main manuscript page
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Find main details table
        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                cells = row.find_all(['th', 'td'])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    
                    if 'title' in label:
                        detailed_data['title'] = value
                        print(f"   Title: {value[:50]}...")
                    elif 'author' in label and 'corresponding' not in label:
                        detailed_data['authors'] = value
                    elif 'corresponding editor' in label:
                        detailed_data['corresponding_editor'] = value
                    elif 'associate editor' in label:
                        detailed_data['associate_editor'] = value
                    elif 'submission date' in label or 'submitted' in label:
                        detailed_data['submission_date'] = value
                    elif 'current stage' in label or 'status' in label:
                        detailed_data['current_stage'] = value
        
        # Extract referees
        detailed_data['referees'] = self.extract_referees(ms_id)
        
        # Download files
        detailed_data['files'] = self.download_manuscript_files(ms_id)
        
        return detailed_data
    
    def extract_referees(self, manuscript_id):
        """Extract referee information including emails."""
        print("   🔍 Extracting referee information...")
        
        referees = []
        
        # Find referee links
        referee_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'dump_person_record') or contains(@href, 'person_id')]")
        
        for link in referee_links:
            try:
                referee_name = link.text.strip()
                if not referee_name or len(referee_name) < 2:
                    continue
                
                # Skip if this is not a referee (e.g., editor)
                parent_text = link.find_element(By.XPATH, "..").text.lower()
                if 'editor' in parent_text and 'referee' not in parent_text:
                    continue
                
                print(f"      Found referee: {referee_name}")
                
                # Get referee details by clicking link
                href = link.get_attribute('href')
                
                # Open in new tab
                self.driver.execute_script("window.open('');")
                self.driver.switch_to.window(self.driver.window_handles[-1])
                self.driver.get(href)
                time.sleep(2)
                
                # Extract details from referee page
                referee_data = {
                    'name': referee_name,
                    'full_name': referee_name,
                    'email': None
                }
                
                # Look for email
                email_links = self.driver.find_elements(By.XPATH, "//a[starts-with(@href, 'mailto:')]")
                if email_links:
                    referee_data['email'] = email_links[0].get_attribute('href').replace('mailto:', '')
                    print(f"         Email: {referee_data['email']}")
                
                # Look for full name in page title or headers
                page_title = self.driver.title
                if referee_name.split()[0].lower() in page_title.lower():
                    # Extract name from title
                    name_part = page_title.split('-')[0].strip()
                    if len(name_part) > len(referee_name):
                        referee_data['full_name'] = name_part
                        print(f"         Full name: {name_part}")
                
                referees.append(referee_data)
                
                # Close tab and switch back
                self.driver.close()
                self.driver.switch_to.window(self.main_window)
                
            except Exception as e:
                print(f"         ❌ Error getting referee details: {e}")
                # Make sure we're back on main window
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                self.driver.switch_to.window(self.main_window)
        
        return referees
    
    def download_manuscript_files(self, manuscript_id):
        """Download all files for a manuscript."""
        print("   📥 Downloading files...")
        
        files = {
            'manuscript': None,
            'cover_letter': None,
            'reports': []
        }
        
        try:
            # Click on manuscript ID to get to files page
            ms_links = self.driver.find_elements(By.XPATH, f"//a[text()='{manuscript_id}']")
            
            for link in ms_links:
                href = link.get_attribute('href')
                if href and ('view_ms' in href or 'display_submission' in href):
                    link.click()
                    time.sleep(3)
                    break
            
            # Find all PDF links
            pdf_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf') or contains(text(), 'PDF') or contains(text(), 'Save File As')]")
            
            for i, link in enumerate(pdf_links):
                try:
                    # Get context
                    parent = link.find_element(By.XPATH, "../..")
                    context = parent.text.lower()
                    
                    # Clear download directory
                    for file in self.download_dir.glob("*.pdf"):
                        file.unlink()
                    
                    # Click download
                    link.click()
                    
                    # Wait for download
                    download_complete = False
                    for _ in range(10):
                        time.sleep(1)
                        pdf_files = list(self.download_dir.glob("*.pdf"))
                        if pdf_files:
                            download_complete = True
                            break
                    
                    if download_complete:
                        source_file = pdf_files[0]
                        
                        # Determine file type and destination
                        if 'cover letter' in context:
                            dest_name = f"{manuscript_id}_cover_letter.pdf"
                            dest_path = self.dirs['cover_letters'] / dest_name
                            files['cover_letter'] = dest_name
                        elif 'manuscript' in context or 'article file' in context:
                            dest_name = f"{manuscript_id}_manuscript.pdf"
                            dest_path = self.dirs['manuscripts'] / dest_name
                            files['manuscript'] = dest_name
                        elif 'referee' in context and 'review' in context:
                            ref_num = len(files['reports']) + 1
                            dest_name = f"{manuscript_id}_referee_{ref_num}_report.pdf"
                            dest_path = self.dirs['reports'] / dest_name
                            files['reports'].append(dest_name)
                        else:
                            dest_name = f"{manuscript_id}_document_{i}.pdf"
                            dest_path = self.output_dir / dest_name
                        
                        # Move file
                        shutil.move(str(source_file), str(dest_path))
                        print(f"      ✅ Downloaded: {dest_name}")
                    
                except Exception as e:
                    print(f"      ❌ Error downloading file: {e}")
        
        except Exception as e:
            print(f"      ❌ Error accessing files: {e}")
        
        return files
    
    def create_summary_report(self, manuscripts):
        """Create comprehensive summary report."""
        report_path = self.output_dir / "extraction_report.md"
        
        with open(report_path, 'w') as f:
            f.write("# SIAM Extraction Report\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Total Manuscripts**: {len(manuscripts)}\n\n")
            
            # Statistics
            total_referees = sum(len(ms.get('referees', [])) for ms in manuscripts)
            referees_with_email = sum(1 for ms in manuscripts for ref in ms.get('referees', []) if ref.get('email'))
            files_downloaded = sum(
                (1 if ms.get('files', {}).get('manuscript') else 0) +
                (1 if ms.get('files', {}).get('cover_letter') else 0) +
                len(ms.get('files', {}).get('reports', []))
                for ms in manuscripts
            )
            
            f.write(f"**Total Referees**: {total_referees}\n")
            f.write(f"**Referees with Email**: {referees_with_email}\n")
            f.write(f"**Files Downloaded**: {files_downloaded}\n\n")
            
            f.write("## Manuscripts\n\n")
            
            for ms in manuscripts:
                f.write(f"### {ms['manuscript_id']}\n")
                f.write(f"**Title**: {ms.get('title', 'N/A')}\n")
                f.write(f"**Authors**: {ms.get('authors', 'N/A')}\n")
                f.write(f"**Corresponding Editor**: {ms.get('corresponding_editor', 'N/A')}\n")
                f.write(f"**Associate Editor**: {ms.get('associate_editor', 'N/A')}\n")
                f.write(f"**Submitted**: {ms.get('submission_date', 'N/A')}\n")
                f.write(f"**Stage**: {ms.get('current_stage', 'N/A')}\n\n")
                
                f.write("**Referees**:\n")
                for ref in ms.get('referees', []):
                    f.write(f"- {ref['full_name']}")
                    if ref.get('email'):
                        f.write(f" ({ref['email']})")
                    f.write("\n")
                
                f.write("\n**Files**:\n")
                files = ms.get('files', {})
                if files.get('manuscript'):
                    f.write(f"- Manuscript: ✅ {files['manuscript']}\n")
                if files.get('cover_letter'):
                    f.write(f"- Cover Letter: ✅ {files['cover_letter']}\n")
                for report in files.get('reports', []):
                    f.write(f"- Report: ✅ {report}\n")
                
                f.write("\n---\n\n")
        
        print(f"\n📊 Report saved to: {report_path}")
    
    def run(self):
        """Run the complete extraction."""
        print("\n🚀 STARTING FINAL SIAM EXTRACTION")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        all_manuscripts = []
        
        try:
            # Setup driver
            self.setup_driver(headless=False)  # Use visible browser for better compatibility
            
            # Authenticate with SICON
            if not self.authenticate_sicon():
                print("❌ Authentication failed")
                return
            
            # Navigate to manuscripts
            if not self.navigate_to_all_pending():
                print("⚠️  Could not navigate to All Pending, trying direct extraction...")
            
            # Extract manuscripts from current page
            manuscripts = self.extract_manuscripts_from_page()
            
            if not manuscripts:
                print("❌ No manuscripts found")
                return
            
            # Process each manuscript
            for ms in manuscripts:
                try:
                    detailed_ms = self.extract_manuscript_details(ms)
                    all_manuscripts.append(detailed_ms)
                except Exception as e:
                    print(f"❌ Error processing {ms['manuscript_id']}: {e}")
                    all_manuscripts.append(ms)  # Keep basic data
            
            # Save all data
            with open(self.dirs['data'] / 'manuscripts_complete.json', 'w') as f:
                json.dump(all_manuscripts, f, indent=2, ensure_ascii=False)
            
            # Create summary report
            self.create_summary_report(all_manuscripts)
            
            print(f"\n✅ Extraction complete!")
            print(f"📁 All files saved to: {self.output_dir}")
            
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
            self.save_screenshot("fatal_error")
        
        finally:
            if self.driver:
                print("\n🔄 Closing browser...")
                self.driver.quit()


def main():
    extractor = FinalSIAMExtractor()
    extractor.run()


if __name__ == "__main__":
    main()