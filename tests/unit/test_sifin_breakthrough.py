#!/usr/bin/env python3
"""
Test SIFIN breakthrough - Apply the same successful approach to SIFIN
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


class SIFINBreakthroughExtractor:
    """SIFIN breakthrough extractor using successful SICON approach."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.main_window = None
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./sifin_breakthrough_{timestamp}')
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
        print("\n🔐 Authenticating with SIFIN...")
        
        # Navigate to SIFIN
        self.driver.get("http://sifin.siam.org")
        time.sleep(3)
        self.main_window = self.driver.current_window_handle
        self.save_screenshot("01_sifin_initial")
        
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
            
            if 'sifin.siam.org' in current_url and 'orcid.org' not in current_url:
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
    
    def find_all_pending_manuscripts(self):
        """Find and click All Pending Manuscripts link."""
        print("\n🔍 Finding All Pending Manuscripts link...")
        
        # Go to home page
        self.driver.get("http://sifin.siam.org/cgi-bin/main.plex?form_type=home")
        time.sleep(3)
        self.save_screenshot("04_home_before_popup")
        
        # Dismiss Privacy Notification
        self.dismiss_privacy_notification()
        self.save_screenshot("04_home_after_popup")
        
        # Debug all available links
        print("   🔍 Debugging all available links...")
        all_links = self.driver.find_elements(By.TAG_NAME, "a")
        print(f"   Found {len(all_links)} total links")
        
        for i, link in enumerate(all_links):
            try:
                text = link.text.strip()
                href = link.get_attribute('href') or ''
                if text and ('pending' in text.lower() or 'manuscripts' in text.lower() or 'AE' in text):
                    print(f"   Link {i}: '{text}' -> {href}")
            except:
                continue
        
        # Search for All Pending Manuscripts link
        # For SIFIN, might be different folder ID than SICON
        search_strategies = [
            "//a[contains(@href, 'folder_id=1800')]",  # Same as SICON
            "//a[contains(@href, 'folder_id=1400')]",  # Alternative folder
            "//a[contains(@href, 'folder_id=1500')]",  # Alternative folder
            "//a[contains(@href, 'folder_id=1600')]",  # Alternative folder
            "//a[contains(@href, 'folder_id=1700')]",  # Alternative folder
            "//a[contains(@href, 'is_open_1800=1')]",
            "//a[contains(@href, 'is_open_1400=1')]",
            "//a[contains(@href, 'is_open_1500=1')]",
            "//a[text()='4 AE']",
            "//a[text()='6 AE']",  # User said 6 referees for SIFIN
            "//a[contains(text(), 'AE')]"
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
                        
                        # Try clicking promising links
                        if 'folder_id' in href or 'AE' in link_text:
                            print(f"   ✅ Trying to click: '{link_text}'")
                            
                            try:
                                self.driver.execute_script("arguments[0].click();", link)
                                time.sleep(5)
                                
                                # Check if we reached a manuscripts page
                                page_text = self.driver.page_source
                                if 'Manuscripts' in page_text and ('M1' in page_text or 'Pending' in page_text):
                                    print("   ✅ Successfully reached manuscripts page!")
                                    self.save_screenshot("05_manuscripts_page")
                                    return True
                                else:
                                    print(f"   Link clicked but no manuscripts found")
                                    # Navigate back to home page for next attempt
                                    self.driver.get("http://sifin.siam.org/cgi-bin/main.plex?form_type=home")
                                    time.sleep(3)
                                    self.dismiss_privacy_notification()
                                    
                            except Exception as e:
                                print(f"   Error clicking '{link_text}': {e}")
                else:
                    print(f"   No links found with strategy {i}")
                    
            except Exception as e:
                print(f"   Strategy {i} failed: {e}")
        
        print("❌ Could not find All Pending Manuscripts link")
        return False
    
    def extract_basic_manuscript_info(self):
        """Extract basic manuscript information."""
        print("\n📊 Extracting manuscript information...")
        
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
                
                if manuscript_count >= 1:
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
                        print(f"   📄 Processing manuscript: {ms_id}")
                        
                        # Extract basic data
                        ms_data = {
                            'manuscript_id': ms_id,
                            'title': cells[1].get_text(strip=True) if len(cells) > 1 else '',
                            'corresponding_editor': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                            'associate_editor': cells[3].get_text(strip=True) if len(cells) > 3 else '',
                            'submitted': cells[4].get_text(strip=True) if len(cells) > 4 else '',
                            'days_in_system': cells[5].get_text(strip=True) if len(cells) > 5 else '',
                            'referees': []
                        }
                        
                        # Look for referee names (look for any names in the cells)
                        for cell in cells[6:]:
                            cell_text = cell.get_text(strip=True)
                            
                            # Look for names (capitalized words)
                            potential_names = re.findall(r'\\b[A-Z][a-z]+\\b', cell_text)
                            for name in potential_names:
                                if len(name) > 2:  # Skip short words
                                    ms_data['referees'].append({
                                        'name': name,
                                        'status': 'Found in table'
                                    })
                                    print(f"      Found potential referee: {name}")
                        
                        manuscripts.append(ms_data)
                    
                    break
            
        except Exception as e:
            print(f"❌ Error extracting manuscript info: {e}")
            import traceback
            traceback.print_exc()
        
        return manuscripts
    
    def create_sifin_report(self, manuscripts):
        """Create SIFIN report."""
        print("\n📊 Creating SIFIN report...")
        
        results = {
            'extraction_time': datetime.now().isoformat(),
            'breakthrough_achieved': len(manuscripts) > 0,
            'manuscripts_found': len(manuscripts),
            'total_referees': sum(len(ms['referees']) for ms in manuscripts),
            'manuscripts': manuscripts
        }
        
        json_path = self.dirs['data'] / 'sifin_results.json'
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        report_path = self.dirs['data'] / 'sifin_report.md'
        with open(report_path, 'w') as f:
            f.write("# SIFIN Breakthrough Report\\n\\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n\\n")
            
            if results['breakthrough_achieved']:
                f.write("## ✅ BREAKTHROUGH ACHIEVED!\\n\\n")
                f.write(f"Successfully accessed manuscripts table and found {len(manuscripts)} manuscripts.\\n\\n")
                
                f.write("### Manuscripts Found\\n\\n")
                for ms in manuscripts:
                    f.write(f"- **{ms['manuscript_id']}**: {ms['title']}\\n")
                    f.write(f"  - Referees: {', '.join(r['name'] for r in ms['referees'])}\\n")
                
                f.write("\\n### Next Steps\\n\\n")
                f.write("1. Click on referee names to get emails and full names\\n")
                f.write("2. Click on manuscript IDs to download PDFs\\n")
                f.write("3. Compare with SICON results\\n")
                
            else:
                f.write("## ❌ Breakthrough Not Achieved\\n\\n")
                f.write("Could not access manuscripts table.\\n\\n")
        
        print(f"   ✅ SIFIN report saved to: {report_path}")
        
        return results
    
    def run(self):
        """Run the SIFIN breakthrough test."""
        print("\\n🚀 STARTING SIFIN BREAKTHROUGH TEST")
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
                # Extract manuscript info
                manuscripts = self.extract_basic_manuscript_info()
            
            # Create report
            results = self.create_sifin_report(manuscripts)
            
            # Final summary
            print(f"\\n📊 SIFIN BREAKTHROUGH RESULTS:")
            if results['breakthrough_achieved']:
                print("✅ BREAKTHROUGH ACHIEVED!")
                print(f"📄 Manuscripts: {len(manuscripts)}")
                print(f"👥 Referees: {sum(len(ms['referees']) for ms in manuscripts)}")
                print("🎯 Ready to extract referee emails and PDFs!")
            else:
                print("❌ Breakthrough not achieved")
                print("Need to resolve access issues")
            
        except Exception as e:
            print(f"\\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            if self.driver:
                print("\\n🔄 Closing browser...")
                try:
                    self.driver.quit()
                except:
                    pass


def main():
    extractor = SIFINBreakthroughExtractor()
    extractor.run()


if __name__ == "__main__":
    main()