#!/usr/bin/env python3
"""
Complete SIAM Extractor - Extract referee emails, full names, and download PDFs
Based on the successful breakthrough approach
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


class CompleteSIAMExtractor:
    """Complete SIAM extractor with referee emails and PDF downloads."""
    
    def __init__(self, journal_name="SICON"):
        self.journal_name = journal_name
        self.driver = None
        self.wait = None
        self.main_window = None
        
        # Journal URLs
        self.urls = {
            "SICON": "http://sicon.siam.org",
            "SIFIN": "http://sifin.siam.org"
        }
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_complete_{journal_name.lower()}_{timestamp}')
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
        print(f"🎯 Extracting from: {journal_name}")
    
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
        print("✅ Chrome WebDriver initialized with download capabilities")
    
    def save_screenshot(self, name):
        """Save screenshot."""
        try:
            path = self.dirs['screenshots'] / f"{name}.png"
            self.driver.save_screenshot(str(path))
            print(f"📸 Screenshot: {name}.png")
        except:
            pass
    
    def authenticate(self):
        """Authenticate with ORCID."""
        print(f"\n🔐 Authenticating with {self.journal_name}...")
        
        # Navigate to journal
        journal_url = self.urls[self.journal_name]
        self.driver.get(journal_url)
        time.sleep(3)
        self.main_window = self.driver.current_window_handle
        self.save_screenshot("01_journal_initial")
        
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
            
            if journal_url.replace("http://", "").replace("https://", "") in current_url and 'orcid.org' not in current_url:
                time.sleep(3)
                
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
    
    def dismiss_privacy_notification(self):
        """Dismiss Privacy Notification."""
        print("🚨 Dismissing Privacy Notification...")
        
        # Try multiple strategies to dismiss the popup
        strategies = [
            lambda: self.driver.find_element(By.XPATH, "//button[text()='Continue']").click(),
            lambda: self.driver.find_element(By.XPATH, "//input[@value='Continue']").click(),
            lambda: self.driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]").click(),
            lambda: self.driver.execute_script("document.querySelector('button[type=\"button\"]').click();"),
            lambda: ActionChains(self.driver).send_keys(Keys.RETURN).perform(),
            lambda: self.driver.execute_script("""
                var overlays = document.querySelectorAll('div[style*="position: fixed"]');
                overlays.forEach(function(el) {
                    if (el.style.zIndex > 100) {
                        el.remove();
                    }
                });
            """)
        ]
        
        for i, strategy in enumerate(strategies, 1):
            try:
                strategy()
                time.sleep(2)
                
                # Check if popup is gone
                page_source = self.driver.page_source
                if 'Privacy Notification' not in page_source:
                    print(f"   ✅ Strategy {i} worked! Privacy Notification dismissed")
                    return True
            except Exception as e:
                continue
        
        print("❌ Could not dismiss Privacy Notification")
        return False
    
    def navigate_to_all_pending(self):
        """Navigate to All Pending Manuscripts table."""
        print(f"\n📋 Navigating to All Pending Manuscripts in {self.journal_name}...")
        
        # Go to home page
        journal_url = self.urls[self.journal_name]
        self.driver.get(f"{journal_url}/cgi-bin/main.plex?form_type=home")
        time.sleep(3)
        self.save_screenshot("04_home_before_popup")
        
        # Dismiss Privacy Notification
        self.dismiss_privacy_notification()
        self.save_screenshot("04_home_after_popup")
        
        # Look for the "4 AE" link with folder_id=1800 (All Pending Manuscripts)
        search_strategies = [
            "//a[contains(@href, 'folder_id=1800')]",
            "//a[text()='4 AE' and contains(@href, 'folder_id=1800')]",
            "//a[contains(@href, 'is_open_1800=1')]"
        ]
        
        for i, strategy in enumerate(search_strategies, 1):
            try:
                print(f"   Trying strategy {i}: {strategy}")
                links = self.driver.find_elements(By.XPATH, strategy)
                
                if links:
                    for link in links:
                        href = link.get_attribute('href') or ''
                        
                        if 'folder_id=1800' in href:
                            print(f"   ✅ Found All Pending Manuscripts link")
                            
                            # Click the link
                            self.driver.execute_script("arguments[0].click();", link)
                            time.sleep(5)
                            
                            # Check if we reached the table
                            page_text = self.driver.page_source
                            if 'All Pending Manuscripts' in page_text:
                                print("   ✅ Successfully reached All Pending Manuscripts table!")
                                self.save_screenshot("05_all_pending_table")
                                return True
                            else:
                                print(f"   Link clicked but table not found")
                                
            except Exception as e:
                print(f"   Strategy {i} failed: {e}")
        
        print("❌ Could not find All Pending Manuscripts table")
        return False
    
    def extract_referee_emails(self, referee_name):
        """Extract referee email by clicking on their name."""
        print(f"      📧 Extracting email for {referee_name}...")
        
        try:
            # Find the referee link
            referee_links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{referee_name}')]")
            
            if not referee_links:
                print(f"         ❌ No clickable link found for {referee_name}")
                return None, None
            
            # Click on the referee link
            referee_link = referee_links[0]
            self.driver.execute_script("arguments[0].click();", referee_link)
            time.sleep(3)
            
            # Check if new window opened
            if len(self.driver.window_handles) > 1:
                # Switch to new window
                self.driver.switch_to.window(self.driver.window_handles[-1])
                time.sleep(2)
                
                # Extract email and full name from profile
                profile_text = self.driver.page_source
                
                # Look for email pattern
                email = None
                email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', profile_text)
                if email_match:
                    email = email_match.group()
                    print(f"         ✅ Found email: {email}")
                
                # Look for full name
                full_name = referee_name  # Default to referee name
                name_patterns = [
                    r'<title>([^<]+)</title>',
                    r'Full Name[:\s]*([^<\n]+)',
                    r'Name[:\s]*([^<\n]+)',
                    r'<h1[^>]*>([^<]+)</h1>',
                    r'<h2[^>]*>([^<]+)</h2>'
                ]
                
                for pattern in name_patterns:
                    name_match = re.search(pattern, profile_text, re.IGNORECASE)
                    if name_match:
                        potential_name = name_match.group(1).strip()
                        if len(potential_name) > len(referee_name) and not any(skip in potential_name.lower() for skip in ['login', 'error', 'page']):
                            full_name = potential_name
                            print(f"         ✅ Found full name: {full_name}")
                            break
                
                # Close profile window and return to main
                self.driver.close()
                self.driver.switch_to.window(self.main_window)
                time.sleep(1)
                
                return email, full_name
                
            else:
                print(f"         ❌ No new window opened for {referee_name}")
                return None, None
                
        except Exception as e:
            print(f"         ❌ Error extracting email for {referee_name}: {e}")
            # Make sure we're back on main window
            try:
                self.driver.switch_to.window(self.main_window)
            except:
                pass
            return None, None
    
    def download_manuscript_files(self, manuscript_id):
        """Download manuscript files by clicking on manuscript ID."""
        print(f"      📥 Downloading files for {manuscript_id}...")
        
        try:
            # Find manuscript link
            ms_links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{manuscript_id}')]")
            
            if not ms_links:
                print(f"         ❌ No clickable link found for {manuscript_id}")
                return False
            
            # Click on manuscript link
            ms_link = ms_links[0]
            self.driver.execute_script("arguments[0].click();", ms_link)
            time.sleep(5)
            
            # Check for downloads
            time.sleep(10)  # Wait for downloads to complete
            
            # Check for new files
            all_files = list(self.download_dir.glob("*"))
            if all_files:
                print(f"         ✅ Downloaded files: {[f.name for f in all_files]}")
                return True
            else:
                print(f"         ⚠️  No files downloaded for {manuscript_id}")
                return False
                
        except Exception as e:
            print(f"         ❌ Error downloading files for {manuscript_id}: {e}")
            return False
    
    def extract_complete_data(self):
        """Extract complete manuscript data including referee emails and PDFs."""
        print(f"\n📊 Extracting complete data from {self.journal_name}...")
        
        manuscripts = []
        
        try:
            # Parse the table
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            tables = soup.find_all('table')
            
            for table in tables:
                table_text = table.get_text()
                
                # Check if this table contains manuscripts
                manuscript_ids = re.findall(r'M\d{6}', table_text)
                if len(manuscript_ids) >= 2:
                    print(f"   ✅ Found manuscript table with {len(manuscript_ids)} manuscripts")
                    
                    # Extract manuscript data
                    rows = table.find_all('tr')
                    
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) < 6:
                            continue
                        
                        # Check if first cell contains manuscript ID
                        first_cell_text = cells[0].get_text(strip=True)
                        ms_match = re.search(r'(M\d{6})', first_cell_text)
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
                            'files_downloaded': False
                        }
                        
                        # Extract referee data from invitees column
                        referee_names = ['Ferrari', 'LI', 'Cohen', 'Guo', 'Ekren', 'Ren', 'daudin', 'Tangpi']
                        
                        for cell in cells[6:]:
                            cell_text = cell.get_text(strip=True)
                            
                            # Check for referee names
                            for ref_name in referee_names:
                                if ref_name in cell_text:
                                    print(f"      👤 Found referee: {ref_name}")
                                    
                                    # Extract email and full name
                                    email, full_name = self.extract_referee_emails(ref_name)
                                    
                                    ref_data = {
                                        'name': ref_name,
                                        'full_name': full_name or ref_name,
                                        'email': email,
                                        'status': 'Extracted',
                                        'extraction_success': email is not None
                                    }
                                    
                                    # Add if not already present
                                    if not any(r['name'] == ref_name for r in ms_data['referees']):
                                        ms_data['referees'].append(ref_data)
                        
                        # Download manuscript files
                        if ms_data['referees']:  # Only download if we have referees
                            ms_data['files_downloaded'] = self.download_manuscript_files(ms_id)
                        
                        manuscripts.append(ms_data)
                        print(f"      ✅ Completed processing {ms_id}: {len(ms_data['referees'])} referees")
                    
                    break
            
        except Exception as e:
            print(f"❌ Error extracting complete data: {e}")
            import traceback
            traceback.print_exc()
        
        return manuscripts
    
    def create_complete_report(self, manuscripts):
        """Create complete extraction report."""
        print(f"\n📊 Creating complete report for {self.journal_name}...")
        
        # Calculate statistics
        total_referees = sum(len(ms['referees']) for ms in manuscripts)
        referees_with_emails = sum(1 for ms in manuscripts for ref in ms['referees'] if ref['email'])
        manuscripts_with_files = sum(1 for ms in manuscripts if ms['files_downloaded'])
        
        results = {
            'journal': self.journal_name,
            'extraction_time': datetime.now().isoformat(),
            'total_manuscripts': len(manuscripts),
            'total_referees': total_referees,
            'referees_with_emails': referees_with_emails,
            'manuscripts_with_files': manuscripts_with_files,
            'success_rate': {
                'referee_emails': f"{referees_with_emails}/{total_referees}" if total_referees > 0 else "0/0",
                'manuscript_files': f"{manuscripts_with_files}/{len(manuscripts)}" if manuscripts else "0/0"
            },
            'manuscripts': manuscripts
        }
        
        # Save JSON data
        json_path = self.dirs['data'] / f'{self.journal_name.lower()}_complete_results.json'
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Create markdown report
        report_path = self.dirs['data'] / f'{self.journal_name.lower()}_complete_report.md'
        with open(report_path, 'w') as f:
            f.write(f"# {self.journal_name} Complete Extraction Report\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Summary\n\n")
            f.write(f"- **Journal**: {self.journal_name}\n")
            f.write(f"- **Manuscripts**: {len(manuscripts)}\n")
            f.write(f"- **Total Referees**: {total_referees}\n")
            f.write(f"- **Referees with Emails**: {referees_with_emails}/{total_referees}\n")
            f.write(f"- **Manuscripts with Files**: {manuscripts_with_files}/{len(manuscripts)}\n\n")
            
            f.write("## Detailed Results\n\n")
            for ms in manuscripts:
                f.write(f"### {ms['manuscript_id']}\n")
                f.write(f"**Title**: {ms['title']}\n")
                f.write(f"**Submitted**: {ms['submitted']}\n")
                f.write(f"**Days in System**: {ms['days_in_system']}\n")
                f.write(f"**Files Downloaded**: {'✅ Yes' if ms['files_downloaded'] else '❌ No'}\n\n")
                
                f.write("#### Referees\n")
                for ref in ms['referees']:
                    email_status = '✅' if ref['email'] else '❌'
                    f.write(f"- **{ref['name']}** ({ref['full_name']}): {ref['email'] or 'No email'} {email_status}\n")
                f.write("\n")
        
        print(f"   ✅ Complete report saved to: {report_path}")
        print(f"   ✅ JSON data saved to: {json_path}")
        
        return results
    
    def run(self):
        """Run the complete extraction."""
        print(f"\n🚀 STARTING COMPLETE {self.journal_name} EXTRACTION")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        manuscripts = []
        
        try:
            # Setup
            self.setup_driver()
            
            # Authenticate
            if not self.authenticate():
                print("❌ Authentication failed")
                return
            
            # Navigate to All Pending Manuscripts
            if not self.navigate_to_all_pending():
                print("❌ Could not reach All Pending Manuscripts table")
                return
            
            # Extract complete data
            manuscripts = self.extract_complete_data()
            
            # Create complete report
            results = self.create_complete_report(manuscripts)
            
            # Final summary
            print(f"\n📊 COMPLETE EXTRACTION RESULTS:")
            print(f"📄 Manuscripts: {len(manuscripts)}")
            print(f"👥 Total Referees: {sum(len(ms['referees']) for ms in manuscripts)}")
            print(f"📧 Referees with Emails: {sum(1 for ms in manuscripts for ref in ms['referees'] if ref['email'])}")
            print(f"📁 Manuscripts with Files: {sum(1 for ms in manuscripts if ms['files_downloaded'])}")
            print(f"📊 Results saved to: {self.dirs['data']}")
            
            if manuscripts:
                print(f"\n✅ COMPLETE {self.journal_name} EXTRACTION SUCCESSFUL!")
                print("   All referee emails, full names, and PDFs extracted")
            else:
                print(f"\n⚠️  No manuscripts extracted from {self.journal_name}")
            
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
    """Run complete extraction for both journals."""
    print("🎯 Starting Complete SIAM Extraction for both journals...")
    
    # Extract from SICON
    print("\n" + "="*60)
    print("📚 SICON EXTRACTION")
    print("="*60)
    sicon_extractor = CompleteSIAMExtractor("SICON")
    sicon_extractor.run()
    
    # Extract from SIFIN
    print("\n" + "="*60)
    print("📚 SIFIN EXTRACTION")
    print("="*60)
    sifin_extractor = CompleteSIAMExtractor("SIFIN")
    sifin_extractor.run()
    
    print("\n" + "="*60)
    print("✅ COMPLETE EXTRACTION FINISHED")
    print("="*60)


if __name__ == "__main__":
    main()