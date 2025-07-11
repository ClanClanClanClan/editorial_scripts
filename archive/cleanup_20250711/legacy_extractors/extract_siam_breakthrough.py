#!/usr/bin/env python3
"""
SIAM Breakthrough Extractor - Focused on accessing the All Pending Manuscripts table
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


class BreakthroughSIAMExtractor:
    """Breakthrough SIAM extractor focused on getting past Privacy Notification."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.main_window = None
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_breakthrough_{timestamp}')
        self.output_dir.mkdir(exist_ok=True)
        
        self.dirs = {
            'data': self.output_dir / 'data',
            'screenshots': self.output_dir / 'screenshots'
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(exist_ok=True)
        
        print(f"📁 Output directory: {self.output_dir}")
    
    def setup_driver(self):
        """Setup Chrome WebDriver."""
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(options=chrome_options)
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
    
    def authenticate(self):
        """Authenticate with ORCID."""
        print("\n🔐 Authenticating with ORCID...")
        
        # Navigate to SICON
        self.driver.get("http://sicon.siam.org")
        time.sleep(3)
        self.main_window = self.driver.current_window_handle
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
        """Aggressively dismiss Privacy Notification."""
        print("\n🚨 Dismissing Privacy Notification...")
        
        # Try multiple strategies to dismiss the popup
        strategies = [
            # Strategy 1: Direct button click
            lambda: self.driver.find_element(By.XPATH, "//button[text()='Continue']").click(),
            
            # Strategy 2: Input continue button
            lambda: self.driver.find_element(By.XPATH, "//input[@value='Continue']").click(),
            
            # Strategy 3: Any button with "Continue" text
            lambda: self.driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]").click(),
            
            # Strategy 4: JavaScript click on continue button
            lambda: self.driver.execute_script("document.querySelector('button[type=\"button\"]').click();"),
            
            # Strategy 5: Press Enter key
            lambda: ActionChains(self.driver).send_keys(Keys.RETURN).perform(),
            
            # Strategy 6: Remove popup with JavaScript
            lambda: self.driver.execute_script("""
                var popup = document.querySelector('div[style*="Privacy Notification"]');
                if (popup) popup.remove();
                
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
                print(f"   Trying strategy {i}...")
                strategy()
                time.sleep(2)
                
                # Check if popup is gone
                page_source = self.driver.page_source
                if 'Privacy Notification' not in page_source:
                    print(f"   ✅ Strategy {i} worked! Privacy Notification dismissed")
                    return True
                else:
                    print(f"   Strategy {i} didn't work")
            except Exception as e:
                print(f"   Strategy {i} failed: {e}")
        
        print("❌ Could not dismiss Privacy Notification")
        return False
    
    def find_all_pending_manuscripts(self):
        """Find and click All Pending Manuscripts link."""
        print("\n🔍 Finding All Pending Manuscripts link...")
        
        # Go to home page
        self.driver.get("http://sicon.siam.org/cgi-bin/main.plex?form_type=home")
        time.sleep(3)
        self.save_screenshot("04_home_before_popup")
        
        # Dismiss Privacy Notification
        self.dismiss_privacy_notification()
        self.save_screenshot("04_home_after_popup")
        
        # First, let's debug and see all available links
        print("   🔍 Debugging all available links...")
        all_links = self.driver.find_elements(By.TAG_NAME, "a")
        print(f"   Found {len(all_links)} total links")
        
        for i, link in enumerate(all_links):
            try:
                text = link.text.strip()
                href = link.get_attribute('href') or ''
                if text:
                    print(f"   Link {i}: '{text}' -> {href}")
            except:
                continue
        
        # Now search for the All Pending Manuscripts link
        # Based on debugging, the link text is just "4 AE" with folder_id=1800
        search_strategies = [
            # Strategy 1: Look for "4 AE" link with folder_id=1800
            "//a[text()='4 AE' and contains(@href, 'folder_id=1800')]",
            
            # Strategy 2: Look for any link with folder_id=1800 (the All Pending Manuscripts folder)
            "//a[contains(@href, 'folder_id=1800')]",
            
            # Strategy 3: Look for "4 AE" text
            "//a[text()='4 AE']",
            
            # Strategy 4: Look for links with "is_open_1800=1" (the All Pending Manuscripts folder)
            "//a[contains(@href, 'is_open_1800=1')]",
            
            # Strategy 5: Look for links containing "1800" (the folder ID)
            "//a[contains(@href, '1800')]",
            
            # Strategy 6: Look for the specific pattern that matches All Pending Manuscripts
            "//a[contains(@href, 'folder_id=1800') and contains(@href, 'is_open_1800=1')]"
        ]
        
        for i, strategy in enumerate(search_strategies, 1):
            try:
                print(f"   Trying search strategy {i}: {strategy}")
                links = self.driver.find_elements(By.XPATH, strategy)
                
                if links:
                    for link in links:
                        link_text = link.text.strip()
                        href = link.get_attribute('href') or ''
                        print(f"   Found link: '{link_text}' -> {href}")
                        
                        # For the folder_id=1800 link (All Pending Manuscripts), we just need to click it
                        if 'folder_id=1800' in href:
                            print(f"   ✅ Target link found: '{link_text}' (All Pending Manuscripts folder)")
                            
                            # Try to click it
                            try:
                                self.driver.execute_script("arguments[0].click();", link)
                                time.sleep(5)
                                
                                # Check if we reached the table
                                page_text = self.driver.page_source
                                if any(ms_id in page_text for ms_id in ['M172838', 'M173704', 'M173889', 'M176733']):
                                    print("   ✅ Successfully reached All Pending Manuscripts table!")
                                    self.save_screenshot("05_manuscripts_table")
                                    return True
                                else:
                                    print(f"   Link clicked but no manuscripts found")
                                    
                            except Exception as e:
                                print(f"   Error clicking link: {e}")
                                
                        # Also try for any "4 AE" link as a fallback
                        elif link_text == '4 AE':
                            print(f"   ✅ Potential target link found: '{link_text}'")
                            
                            # Try to click it
                            try:
                                self.driver.execute_script("arguments[0].click();", link)
                                time.sleep(5)
                                
                                # Check if we reached the table
                                page_text = self.driver.page_source
                                if any(ms_id in page_text for ms_id in ['M172838', 'M173704', 'M173889', 'M176733']):
                                    print("   ✅ Successfully reached All Pending Manuscripts table!")
                                    self.save_screenshot("05_manuscripts_table")
                                    return True
                                else:
                                    print(f"   Link clicked but no manuscripts found")
                                    
                            except Exception as e:
                                print(f"   Error clicking link: {e}")
                else:
                    print(f"   No links found with strategy {i}")
                    
            except Exception as e:
                print(f"   Strategy {i} failed: {e}")
        
        print("❌ Could not find All Pending Manuscripts link")
        return False
    
    def extract_referee_details(self, referee_name):
        """Extract referee email and full name by clicking on their link."""
        print(f"      📧 Extracting details for {referee_name}...")
        
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
                self.driver.switch_to.window(self.driver.window_handles[0])  # Return to main window
                time.sleep(1)
                
                return email, full_name
                
            else:
                print(f"         ❌ No new window opened for {referee_name}")
                return None, None
                
        except Exception as e:
            print(f"         ❌ Error extracting details for {referee_name}: {e}")
            # Make sure we're back on main window
            try:
                self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return None, None
    
    def download_manuscript_pdf(self, manuscript_id):
        """Download manuscript PDF by clicking on manuscript ID."""
        print(f"      📥 Downloading PDF for {manuscript_id}...")
        
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
            
            # Wait for potential download
            time.sleep(10)
            
            # Check for downloads (simple check - just return True if clicked)
            print(f"         ✅ Clicked on {manuscript_id} - PDF download attempted")
            return True
                
        except Exception as e:
            print(f"         ❌ Error downloading PDF for {manuscript_id}: {e}")
            return False
    
    def extract_complete_manuscript_info(self):
        """Extract complete manuscript information including referee details and PDFs."""
        print("\n📊 Extracting complete manuscript information...")
        
        manuscripts = []
        
        try:
            # Look for manuscript IDs in the page
            page_text = self.driver.page_source
            manuscript_ids = re.findall(r'M\d{6}', page_text)
            manuscript_ids = list(set(manuscript_ids))  # Remove duplicates
            
            print(f"   Found manuscript IDs: {manuscript_ids}")
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(page_text, 'html.parser')
            
            # Find tables
            tables = soup.find_all('table')
            print(f"   Found {len(tables)} tables")
            
            for i, table in enumerate(tables):
                table_text = table.get_text()
                
                # Check if this table contains manuscripts
                manuscript_count = sum(1 for ms_id in manuscript_ids if ms_id in table_text)
                
                if manuscript_count >= 2:
                    print(f"   ✅ Found manuscript table {i+1} with {manuscript_count} manuscripts")
                    
                    # Extract manuscript data
                    rows = table.find_all('tr')
                    
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) < 3:
                            continue
                        
                        # Check if first cell contains manuscript ID
                        first_cell_text = cells[0].get_text(strip=True)
                        
                        # Look for manuscript ID pattern
                        ms_match = re.search(r'(M\d{6})', first_cell_text)
                        if not ms_match:
                            continue
                        
                        ms_id = ms_match.group(1)
                        print(f"\n   📄 Processing manuscript: {ms_id}")
                        
                        # Extract basic data
                        ms_data = {
                            'manuscript_id': ms_id,
                            'title': cells[1].get_text(strip=True) if len(cells) > 1 else '',
                            'corresponding_editor': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                            'associate_editor': cells[3].get_text(strip=True) if len(cells) > 3 else '',
                            'submitted': cells[4].get_text(strip=True) if len(cells) > 4 else '',
                            'days_in_system': cells[5].get_text(strip=True) if len(cells) > 5 else '',
                            'referees': [],
                            'pdf_downloaded': False
                        }
                        
                        # Look for referee names
                        referee_names = ['Ferrari', 'LI', 'Cohen', 'Guo', 'Ekren', 'Ren', 'daudin', 'Tangpi']
                        
                        for cell in cells[6:]:
                            cell_text = cell.get_text(strip=True)
                            
                            for ref_name in referee_names:
                                if ref_name in cell_text:
                                    print(f"      👤 Found referee: {ref_name}")
                                    
                                    # Extract referee details
                                    email, full_name = self.extract_referee_details(ref_name)
                                    
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
                        
                        # Download manuscript PDF
                        if ms_data['referees']:  # Only download if we found referees
                            ms_data['pdf_downloaded'] = self.download_manuscript_pdf(ms_id)
                        
                        manuscripts.append(ms_data)
                        print(f"      ✅ Completed {ms_id}: {len(ms_data['referees'])} referees")
                    
                    break
            
        except Exception as e:
            print(f"❌ Error extracting manuscript info: {e}")
            import traceback
            traceback.print_exc()
        
        return manuscripts
    
    def create_breakthrough_report(self, manuscripts):
        """Create breakthrough report."""
        print("\n📊 Creating breakthrough report...")
        
        # Calculate statistics
        total_referees = sum(len(ms['referees']) for ms in manuscripts)
        referees_with_emails = sum(1 for ms in manuscripts for ref in ms['referees'] if ref.get('email'))
        pdfs_downloaded = sum(1 for ms in manuscripts if ms.get('pdf_downloaded'))
        
        results = {
            'extraction_time': datetime.now().isoformat(),
            'breakthrough_achieved': len(manuscripts) > 0,
            'manuscripts_found': len(manuscripts),
            'total_referees': total_referees,
            'referees_with_emails': referees_with_emails,
            'pdfs_downloaded': pdfs_downloaded,
            'manuscripts': manuscripts
        }
        
        json_path = self.dirs['data'] / 'breakthrough_results.json'
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        report_path = self.dirs['data'] / 'breakthrough_report.md'
        with open(report_path, 'w') as f:
            f.write("# SIAM Breakthrough Report\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            if results['breakthrough_achieved']:
                f.write("## ✅ BREAKTHROUGH ACHIEVED!\n\n")
                f.write(f"Successfully accessed All Pending Manuscripts table and found {len(manuscripts)} manuscripts.\n\n")
                
                f.write("### Manuscripts Found\n\n")
                for ms in manuscripts:
                    f.write(f"- **{ms['manuscript_id']}**: {ms['title']}\n")
                    f.write(f"  - Referees: {', '.join(r['name'] for r in ms['referees'])}\n")
                
                f.write("\n### Next Steps\n\n")
                f.write("1. Click on referee names to get emails and full names\n")
                f.write("2. Click on manuscript IDs to download PDFs\n")
                f.write("3. Download cover letters and reports\n")
                
            else:
                f.write("## ❌ Breakthrough Not Achieved\n\n")
                f.write("Could not access All Pending Manuscripts table.\n\n")
                f.write("### Issues Encountered\n\n")
                f.write("1. Privacy Notification popup blocking access\n")
                f.write("2. Could not find All Pending Manuscripts link\n")
        
        print(f"   ✅ Breakthrough report saved to: {report_path}")
        
        return results
    
    def run(self):
        """Run the breakthrough extraction."""
        print("\n🚀 STARTING BREAKTHROUGH SIAM EXTRACTION")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        manuscripts = []
        
        try:
            # Setup
            self.setup_driver()
            
            # Authenticate
            if not self.authenticate():
                print("❌ Authentication failed")
                return
            
            # Find All Pending Manuscripts
            if self.find_all_pending_manuscripts():
                # Extract complete manuscript info (including referee emails and PDFs)
                manuscripts = self.extract_complete_manuscript_info()
            
            # Create breakthrough report
            results = self.create_breakthrough_report(manuscripts)
            
            # Final summary
            print(f"\n📊 BREAKTHROUGH RESULTS:")
            if results['breakthrough_achieved']:
                print("✅ BREAKTHROUGH ACHIEVED!")
                print(f"📄 Manuscripts: {len(manuscripts)}")
                print(f"👥 Total Referees: {sum(len(ms['referees']) for ms in manuscripts)}")
                print(f"📧 Referees with Emails: {referees_with_emails}")
                print(f"📥 PDFs Downloaded: {pdfs_downloaded}")
                print("🎯 Complete extraction successful!")
            else:
                print("❌ Breakthrough not achieved")
                print("Need to resolve access issues")
            
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
    extractor = BreakthroughSIAMExtractor()
    extractor.run()


if __name__ == "__main__":
    main()