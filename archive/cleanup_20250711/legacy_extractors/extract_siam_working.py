#!/usr/bin/env python3
"""
SIAM Working Extractor - Using successful authentication to get referee data
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
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup


class WorkingSIAMExtractor:
    """Working SIAM extractor using successful authentication."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.main_window = None
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_working_{timestamp}')
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.download_dir = self.output_dir / 'downloads'
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
    
    def setup_driver(self):
        """Setup Chrome WebDriver with download capabilities."""
        chrome_options = Options()
        
        # Download configuration
        prefs = {
            "download.default_directory": str(self.download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Enable downloads
        self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": str(self.download_dir)
        })
        
        self.wait = WebDriverWait(self.driver, 20)
        print("✅ Chrome WebDriver initialized")
    
    def save_screenshot(self, name):
        """Save screenshot."""
        try:
            path = self.dirs['screenshots'] / f"{name}.png"
            self.driver.save_screenshot(str(path))
            print(f"📸 Screenshot: {name}.png")
        except:
            pass
    
    def handle_popups(self):
        """Handle popups including Privacy Notification."""
        try:
            # Privacy Notification Continue button
            privacy_continue = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Continue')]")
            if privacy_continue:
                print("   Dismissing Privacy Notification...")
                privacy_continue[0].click()
                time.sleep(2)
            
            # Generic Continue buttons
            continue_btns = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Continue')]")
            if continue_btns:
                continue_btns[0].click()
                time.sleep(2)
            
            # Remove overlays with JavaScript
            self.driver.execute_script("""
                var overlays = document.querySelectorAll('[style*="position: fixed"]');
                overlays.forEach(function(el) {
                    if (el.style.zIndex > 100) {
                        el.remove();
                    }
                });
                
                // Remove Privacy Notification specifically
                var privacyNotif = document.querySelector('[style*="Privacy Notification"]');
                if (privacyNotif) {
                    privacyNotif.remove();
                }
            """)
        except:
            pass
    
    def authenticate(self):
        """Authenticate with ORCID - using working method."""
        print("\n🔐 Authenticating with ORCID...")
        
        # Navigate to SICON
        self.driver.get("http://sicon.siam.org")
        time.sleep(3)
        self.main_window = self.driver.current_window_handle
        self.handle_popups()
        self.save_screenshot("01_sicon_initial")
        
        # Check if already authenticated
        page_text = self.driver.page_source.lower()
        if 'associate editor tasks' in page_text:
            print("✅ Already authenticated!")
            return True
        
        # Find and click ORCID link
        orcid_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'orcid')]")
        if not orcid_links:
            print("❌ No ORCID links found")
            return False
        
        # Click ORCID
        self.driver.execute_script("arguments[0].click();", orcid_links[0])
        time.sleep(5)
        
        # Verify on ORCID
        if 'orcid.org' not in self.driver.current_url:
            print("❌ Did not reach ORCID")
            return False
        
        self.save_screenshot("02_orcid_page")
        
        # Fill credentials
        try:
            username = self.wait.until(EC.presence_of_element_located((By.ID, "username-input")))
            username.clear()
            username.send_keys("0000-0002-9364-0124")
            
            password = self.driver.find_element(By.ID, "password")
            password.clear()
            password.send_keys("Hioupy0042%")
            password.send_keys(Keys.RETURN)
            
            print("   Credentials submitted")
        except Exception as e:
            print(f"❌ Error filling credentials: {e}")
            return False
        
        # Wait for redirect
        timeout = time.time() + 25
        while time.time() < timeout:
            current_url = self.driver.current_url
            
            if 'sicon.siam.org' in current_url and 'orcid.org' not in current_url:
                time.sleep(3)
                self.handle_popups()
                
                # Check authentication
                page_text = self.driver.page_source.lower()
                self.save_screenshot("03_after_auth")
                
                if 'associate editor tasks' in page_text:
                    print("✅ Authentication successful!")
                    return True
                else:
                    print("❌ Still on login page after redirect")
                    return False
            
            time.sleep(1)
        
        print("❌ Authentication timeout")
        return False
    
    def navigate_to_all_pending(self):
        """Navigate to All Pending Manuscripts using working method."""
        print("\n📋 Navigating to All Pending Manuscripts...")
        
        # Go to home page
        self.driver.get("http://sicon.siam.org/cgi-bin/main.plex?form_type=home")
        time.sleep(3)
        self.handle_popups()
        self.save_screenshot("04_home_page_before_popup")
        
        # Handle Privacy Notification more aggressively
        time.sleep(2)
        
        # Specifically target the Privacy Notification Continue button
        try:
            # Find the Continue button in the Privacy Notification
            continue_button = self.driver.find_element(By.XPATH, "//button[text()='Continue']")
            print("   Found Privacy Notification Continue button")
            self.driver.execute_script("arguments[0].click();", continue_button)
            time.sleep(3)
            print("   Dismissed Privacy Notification")
        except Exception as e:
            print(f"   Could not dismiss Privacy Notification: {e}")
        
        self.save_screenshot("04_home_page_after_popup")
        
        # Look for all links on the page and print them for debugging
        all_links = self.driver.find_elements(By.TAG_NAME, "a")
        print(f"   Found {len(all_links)} total links on page")
        
        pending_links = []
        for i, link in enumerate(all_links):
            try:
                text = link.text.strip()
                href = link.get_attribute('href') or ''
                if text and ('pending' in text.lower() or 'manuscripts' in text.lower()):
                    pending_links.append((text, href, link))
                    print(f"   Link {i}: '{text}' -> {href}")
            except:
                continue
        
        # Also look for the specific "All Pending Manuscripts 4 AE" link
        try:
            all_pending_link = self.driver.find_element(By.XPATH, "//a[contains(text(), 'All Pending Manuscripts')]")
            print(f"   Found specific 'All Pending Manuscripts' link: '{all_pending_link.text}'")
            pending_links.append((all_pending_link.text, all_pending_link.get_attribute('href'), all_pending_link))
        except:
            print("   Could not find specific 'All Pending Manuscripts' link")
        
        # Try clicking the most promising links
        for text, href, link_element in pending_links:
            if any(phrase in text.lower() for phrase in ['all pending', 'pending manuscripts']):
                try:
                    print(f"   Attempting to click link: '{text}'")
                    
                    # Try multiple click strategies
                    clicked = False
                    
                    # Strategy 1: Direct click
                    try:
                        link_element.click()
                        clicked = True
                        print(f"   Successfully clicked '{text}' with direct click")
                    except Exception as e1:
                        print(f"   Direct click failed: {e1}")
                        # Strategy 2: JavaScript click
                        try:
                            self.driver.execute_script("arguments[0].click();", link_element)
                            clicked = True
                            print(f"   Successfully clicked '{text}' with JavaScript click")
                        except Exception as e2:
                            print(f"   JavaScript click failed: {e2}")
                            # Strategy 3: ActionChains
                            try:
                                ActionChains(self.driver).move_to_element(link_element).click().perform()
                                clicked = True
                                print(f"   Successfully clicked '{text}' with ActionChains")
                            except Exception as e3:
                                print(f"   ActionChains click failed: {e3}")
                    
                    if clicked:
                        time.sleep(5)
                        self.handle_popups()
                        
                        # Check if we have the table
                        page_text = self.driver.page_source
                        if any(ms_id in page_text for ms_id in ['M172838', 'M173704', 'M173889', 'M176733']):
                            print("   ✅ Successfully reached All Pending Manuscripts table!")
                            self.save_screenshot("05_all_pending_table")
                            return True
                        else:
                            print(f"   Clicked '{text}' but no manuscripts found")
                            # Navigate back to home page for next attempt
                            self.driver.get("http://sicon.siam.org/cgi-bin/main.plex?form_type=home")
                            time.sleep(3)
                            self.handle_popups()
                    else:
                        print(f"   Could not click '{text}' with any method")
                        
                except Exception as e:
                    print(f"   Error clicking '{text}': {e}")
        
        print("❌ Could not find All Pending Manuscripts table")
        return False
    
    def extract_referee_data(self):
        """Extract referee data by clicking on referee names."""
        print("\n👥 Extracting referee data...")
        
        manuscripts = []
        
        try:
            # Parse the table
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            tables = soup.find_all('table')
            
            for table in tables:
                table_text = table.get_text()
                
                # Check if this table contains manuscripts
                manuscript_count = sum(1 for ms_id in ['M172838', 'M173704', 'M173889', 'M176733'] if ms_id in table_text)
                
                if manuscript_count >= 2:
                    print(f"   ✅ Found manuscript table with {manuscript_count} manuscripts")
                    
                    # Find all rows with manuscript data
                    rows = table.find_all('tr')
                    
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) < 6:
                            continue
                        
                        # Check if first cell contains manuscript ID
                        first_cell = cells[0]
                        ms_match = re.search(r'(M\d{6})', first_cell.get_text())
                        if not ms_match:
                            continue
                        
                        ms_id = ms_match.group(1)
                        print(f"\n   📄 Processing manuscript: {ms_id}")
                        
                        # Extract basic manuscript data
                        ms_data = {
                            'manuscript_id': ms_id,
                            'title': cells[1].get_text(strip=True) if len(cells) > 1 else '',
                            'corresponding_editor': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                            'associate_editor': cells[3].get_text(strip=True) if len(cells) > 3 else '',
                            'submitted': cells[4].get_text(strip=True) if len(cells) > 4 else '',
                            'days_in_system': cells[5].get_text(strip=True) if len(cells) > 5 else '',
                            'referees': [],
                            'pdf_url': None
                        }
                        
                        # Find manuscript PDF link
                        ms_link = first_cell.find('a')
                        if ms_link:
                            ms_data['pdf_url'] = ms_link.get('href')
                        
                        # Look for referee names in the "Invitees" column and beyond
                        referee_names = ['Ferrari', 'LI', 'Cohen', 'Guo', 'Ekren', 'Ren', 'daudin', 'Tangpi']
                        
                        for i, cell in enumerate(cells[6:], 6):
                            cell_text = cell.get_text(strip=True)
                            
                            # Check if this cell contains referee names
                            for ref_name in referee_names:
                                if ref_name in cell_text:
                                    # Look for clickable referee link
                                    ref_link = cell.find('a')
                                    if ref_link:
                                        ref_data = {
                                            'name': ref_name,
                                            'full_name': ref_name,
                                            'email': None,
                                            'status': 'Found',
                                            'profile_url': ref_link.get('href')
                                        }
                                        
                                        # Try to click referee link to get email
                                        try:
                                            print(f"      Clicking referee: {ref_name}")
                                            
                                            # Find the actual link element on the page
                                            ref_link_elements = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{ref_name}')]")
                                            if ref_link_elements:
                                                # Open in new window
                                                self.driver.execute_script("arguments[0].click();", ref_link_elements[0])
                                                time.sleep(3)
                                                
                                                # Check if new window opened
                                                if len(self.driver.window_handles) > 1:
                                                    # Switch to new window
                                                    self.driver.switch_to.window(self.driver.window_handles[-1])
                                                    time.sleep(2)
                                                    
                                                    # Extract email and full name
                                                    profile_text = self.driver.page_source
                                                    
                                                    # Look for email pattern
                                                    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', profile_text)
                                                    if email_match:
                                                        ref_data['email'] = email_match.group()
                                                        print(f"         Found email: {ref_data['email']}")
                                                    
                                                    # Look for full name
                                                    name_patterns = [
                                                        r'<title>([^<]+)</title>',
                                                        r'Full Name[:\s]*([^<\n]+)',
                                                        r'Name[:\s]*([^<\n]+)'
                                                    ]
                                                    
                                                    for pattern in name_patterns:
                                                        name_match = re.search(pattern, profile_text, re.IGNORECASE)
                                                        if name_match:
                                                            full_name = name_match.group(1).strip()
                                                            if len(full_name) > len(ref_name):
                                                                ref_data['full_name'] = full_name
                                                                print(f"         Found full name: {ref_data['full_name']}")
                                                            break
                                                    
                                                    # Close window and return to main
                                                    self.driver.close()
                                                    self.driver.switch_to.window(self.main_window)
                                                    time.sleep(1)
                                                    
                                                else:
                                                    print(f"         No new window opened for {ref_name}")
                                                    
                                        except Exception as e:
                                            print(f"         Error clicking referee {ref_name}: {e}")
                                            # Make sure we're back on main window
                                            self.driver.switch_to.window(self.main_window)
                                        
                                        # Add referee to manuscript
                                        if not any(r['name'] == ref_name for r in ms_data['referees']):
                                            ms_data['referees'].append(ref_data)
                        
                        manuscripts.append(ms_data)
                        print(f"      Found {len(ms_data['referees'])} referees for {ms_id}")
                    
                    break
            
        except Exception as e:
            print(f"❌ Error extracting referee data: {e}")
            import traceback
            traceback.print_exc()
        
        return manuscripts
    
    def download_pdfs(self, manuscripts):
        """Download manuscript PDFs."""
        print("\n📥 Downloading PDFs...")
        
        for ms in manuscripts:
            if ms['pdf_url']:
                try:
                    print(f"   Downloading PDF for {ms['manuscript_id']}")
                    
                    # Find and click manuscript link
                    ms_links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{ms['manuscript_id']}')]")
                    if ms_links:
                        self.driver.execute_script("arguments[0].click();", ms_links[0])
                        time.sleep(5)
                        
                        # Check if download started
                        downloaded_files = list(self.download_dir.glob("*"))
                        if downloaded_files:
                            print(f"      ✅ Downloaded files: {[f.name for f in downloaded_files]}")
                        else:
                            print(f"      ⚠️  No files downloaded for {ms['manuscript_id']}")
                    
                except Exception as e:
                    print(f"   Error downloading PDF for {ms['manuscript_id']}: {e}")
    
    def create_results_report(self, manuscripts):
        """Create results report."""
        print("\n📊 Creating results report...")
        
        # Save JSON data
        results = {
            'extraction_time': datetime.now().isoformat(),
            'total_manuscripts': len(manuscripts),
            'total_referees': sum(len(ms['referees']) for ms in manuscripts),
            'referees_with_emails': sum(1 for ms in manuscripts for ref in ms['referees'] if ref['email']),
            'manuscripts': manuscripts
        }
        
        json_path = self.dirs['data'] / 'working_results.json'
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Create markdown report
        report_path = self.dirs['data'] / 'working_report.md'
        with open(report_path, 'w') as f:
            f.write("# SIAM Working Extraction Report\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Summary\n\n")
            f.write(f"- **Manuscripts**: {len(manuscripts)}\n")
            f.write(f"- **Total Referees**: {sum(len(ms['referees']) for ms in manuscripts)}\n")
            f.write(f"- **Referees with Emails**: {sum(1 for ms in manuscripts for ref in ms['referees'] if ref['email'])}\n\n")
            
            for ms in manuscripts:
                f.write(f"## {ms['manuscript_id']}\n\n")
                f.write(f"**Title**: {ms['title']}\n")
                f.write(f"**Submitted**: {ms['submitted']}\n")
                f.write(f"**Days in System**: {ms['days_in_system']}\n\n")
                
                f.write("### Referees\n\n")
                for ref in ms['referees']:
                    f.write(f"- **{ref['name']}**: {ref['full_name']} ({ref['email'] or 'No email'})\n")
                f.write("\n")
        
        print(f"   ✅ Results saved to: {json_path}")
        print(f"   ✅ Report saved to: {report_path}")
        
        return results
    
    def run(self):
        """Run the working extraction."""
        print("\n🚀 STARTING WORKING SIAM EXTRACTION")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        manuscripts = []
        
        try:
            # Setup
            self.setup_driver()
            
            # Authenticate
            if not self.authenticate():
                print("❌ Authentication failed")
                return
            
            # Navigate to table
            if not self.navigate_to_all_pending():
                print("❌ Could not reach All Pending Manuscripts table")
                return
            
            # Extract referee data
            manuscripts = self.extract_referee_data()
            
            # Download PDFs
            self.download_pdfs(manuscripts)
            
            # Create results report
            results = self.create_results_report(manuscripts)
            
            # Final summary
            print(f"\n📊 EXTRACTION COMPLETE:")
            print(f"✅ Manuscripts: {len(manuscripts)}")
            print(f"✅ Total Referees: {sum(len(ms['referees']) for ms in manuscripts)}")
            print(f"✅ Referees with Emails: {sum(1 for ms in manuscripts for ref in ms['referees'] if ref['email'])}")
            print(f"📁 Results saved to: {self.dirs['data']}")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            if self.driver:
                print("\n🔄 Closing browser...")
                try:
                    self.driver.quit()
                except:
                    pass


def main():
    extractor = WorkingSIAMExtractor()
    extractor.run()


if __name__ == "__main__":
    main()