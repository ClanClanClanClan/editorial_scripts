#!/usr/bin/env python3
"""
Step-by-step SIAM extraction - focused on getting referee details and PDFs
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
from bs4 import BeautifulSoup


class StepByStepSIAMExtractor:
    """Extract SIAM data step by step with debugging."""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./siam_step_by_step_{timestamp}')
        self.output_dir.mkdir(exist_ok=True)
        
        # Download directory
        self.download_dir = self.output_dir / 'downloads'
        self.download_dir.mkdir(exist_ok=True)
        
        print(f"📁 Output directory: {self.output_dir}")
    
    def setup_driver(self):
        """Setup Chrome WebDriver."""
        chrome_options = Options()
        
        # Configure downloads
        prefs = {
            "download.default_directory": str(self.download_dir),
            "download.prompt_for_download": False,
            "plugins.always_open_pdf_externally": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)
        print("✅ Chrome WebDriver initialized")
    
    def save_screenshot(self, name):
        """Save screenshot for debugging."""
        screenshot_path = self.output_dir / f"{name}.png"
        self.driver.save_screenshot(str(screenshot_path))
        print(f"📸 Screenshot saved: {screenshot_path.name}")
    
    def save_page_source(self, name):
        """Save page source for debugging."""
        html_path = self.output_dir / f"{name}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
        print(f"📄 HTML saved: {html_path.name}")
    
    def authenticate(self):
        """Authenticate with SICON."""
        print("\n🔐 Authenticating with SICON...")
        
        self.driver.get("http://sicon.siam.org")
        time.sleep(3)
        
        # Remove cookie banners
        self.driver.execute_script("""
            ['#cookie-policy-layer-bg', '#cookie-policy-layer', '#continue-btn'].forEach(id => {
                var el = document.querySelector(id);
                if (el) {
                    if (id === '#continue-btn') el.click();
                    else el.remove();
                }
            });
        """)
        
        self.save_screenshot("01_sicon_home")
        
        # Check if already logged in
        if "logout" in self.driver.page_source.lower():
            print("✅ Already authenticated!")
            return True
        
        # Click ORCID
        orcid_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'orcid')]")
        orcid_link.click()
        
        self.wait.until(lambda d: 'orcid.org' in d.current_url)
        time.sleep(2)
        
        # Login
        username = self.driver.find_element(By.ID, "username-input")
        username.send_keys(os.getenv("ORCID_USER", "0000-0002-9364-0124"))
        
        password = self.driver.find_element(By.ID, "password")
        password.send_keys(os.getenv("ORCID_PASS", "Hioupy0042%"))
        password.send_keys(Keys.RETURN)
        
        print("⏳ Waiting for authentication...")
        self.wait.until(lambda d: 'sicon.siam.org' in d.current_url)
        time.sleep(3)
        
        self.save_screenshot("02_authenticated")
        print("✅ Authenticated!")
        return True
    
    def navigate_to_manuscripts(self):
        """Navigate to manuscript list."""
        print("\n📋 Navigating to manuscripts...")
        
        # Look for different folder options
        folders_to_try = [
            ("Under Review", "is_open_1400=1"),
            ("All Pending Manuscripts", "is_open_1800=1"),
            ("Awaiting Associate Editor Recommendation", "is_open_1500=1")
        ]
        
        for folder_name, url_pattern in folders_to_try:
            try:
                print(f"   Looking for {folder_name}...")
                
                # Try by URL pattern first
                links = self.driver.find_elements(By.XPATH, f"//a[contains(@href, '{url_pattern}')]")
                if links:
                    print(f"   ✅ Found {folder_name} link")
                    links[0].click()
                    time.sleep(3)
                    self.save_screenshot(f"03_{folder_name.replace(' ', '_').lower()}")
                    return True
                
                # Try by text
                links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{folder_name}')]")
                if links:
                    print(f"   ✅ Found {folder_name} link by text")
                    links[0].click()
                    time.sleep(3)
                    return True
                    
            except Exception as e:
                print(f"   ❌ {folder_name} not found: {e}")
                continue
        
        # If no folders found, save current state
        self.save_page_source("navigation_failed")
        return False
    
    def extract_manuscript_table(self):
        """Extract manuscripts from table view."""
        print("\n📊 Extracting manuscript table...")
        
        # Look for manuscript links (they start with M and are followed by numbers)
        manuscript_links = self.driver.find_elements(By.XPATH, "//a[starts-with(text(), 'M') and string-length(text()) > 3]")
        
        if not manuscript_links:
            print("   ❌ No manuscript links found in table view")
            # Try the individual manuscript view
            return self.extract_individual_manuscripts()
        
        print(f"   ✅ Found {len(manuscript_links)} manuscript links")
        
        manuscripts = []
        
        # Get the table containing manuscripts
        tables = self.driver.find_elements(By.TAG_NAME, "table")
        
        for table in tables:
            # Check if this table has manuscript data
            if not any(link in table.get_attribute('innerHTML') for link in ['M172838', 'M173704', 'M173889', 'M176733']):
                continue
            
            print("   ✅ Found manuscripts table")
            
            # Process the table
            soup = BeautifulSoup(table.get_attribute('innerHTML'), 'html.parser')
            rows = soup.find_all('tr')
            
            for row in rows:
                cells = row.find_all('td')
                if not cells:
                    continue
                
                # Check if first cell contains manuscript ID
                first_cell = cells[0].get_text(strip=True)
                if not first_cell.startswith('M') or not first_cell[1:].replace('Yu', '').replace('Zhang', '').replace('Wan', '').replace('Luo', '').isdigit():
                    continue
                
                ms_id = first_cell
                print(f"\n   📄 Found manuscript: {ms_id}")
                
                ms_data = {
                    "manuscript_id": ms_id,
                    "cells": [cell.get_text(strip=True) for cell in cells]
                }
                
                manuscripts.append(ms_data)
        
        return manuscripts
    
    def extract_individual_manuscripts(self):
        """Extract manuscripts from individual links view."""
        print("\n📊 Extracting individual manuscript links...")
        
        # Pattern to match manuscript descriptions
        # e.g., "Submit Review # M172838 (Yu) 141 days"
        manuscript_pattern = re.compile(r'M\d+')
        
        links = self.driver.find_elements(By.TAG_NAME, "a")
        manuscripts = []
        
        for link in links:
            text = link.text
            match = manuscript_pattern.search(text)
            
            if match:
                ms_id = match.group()
                href = link.get_attribute('href')
                
                if href and 'view_ms' in href:
                    print(f"   📄 Found manuscript: {ms_id} - {text}")
                    
                    manuscripts.append({
                        "manuscript_id": ms_id,
                        "url": href,
                        "link_text": text
                    })
        
        return manuscripts
    
    def get_referee_details(self, manuscript_url):
        """Get referee details from manuscript page."""
        print("\n   🔍 Getting referee details...")
        
        # Navigate to manuscript
        self.driver.get(manuscript_url)
        time.sleep(2)
        
        # Look for referee information
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        referees = []
        
        # Find referee links
        referee_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'dump_person_record')]")
        
        for link in referee_links:
            referee_name = link.text.strip()
            if not referee_name or len(referee_name) < 2:
                continue
            
            print(f"      Found referee: {referee_name}")
            
            # Click to get details
            try:
                href = link.get_attribute('href')
                
                # Open in new tab
                self.driver.execute_script("window.open(arguments[0], '_blank');", href)
                time.sleep(1)
                
                # Switch to new tab
                self.driver.switch_to.window(self.driver.window_handles[-1])
                
                # Extract email
                email = None
                email_links = self.driver.find_elements(By.XPATH, "//a[starts-with(@href, 'mailto:')]")
                if email_links:
                    email = email_links[0].get_attribute('href').replace('mailto:', '')
                
                # Get full name from page
                page_text = self.driver.page_source
                full_name = referee_name
                
                # Look for name in title or headers
                title_match = re.search(r'<title>([^<]+)</title>', page_text)
                if title_match:
                    title_text = title_match.group(1)
                    if referee_name.split()[0] in title_text:
                        full_name = title_text.split('-')[0].strip()
                
                referees.append({
                    "name": referee_name,
                    "full_name": full_name,
                    "email": email
                })
                
                print(f"         Full name: {full_name}")
                if email:
                    print(f"         Email: {email}")
                
                # Close tab
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
                
            except Exception as e:
                print(f"         ❌ Error getting details: {e}")
                # Make sure we're back on main window
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
        
        return referees
    
    def download_pdfs(self, manuscript_id, manuscript_url):
        """Download PDFs for a manuscript."""
        print("\n   📥 Downloading PDFs...")
        
        # Navigate to manuscript
        self.driver.get(manuscript_url)
        time.sleep(2)
        
        # Click on manuscript ID to get to files page
        ms_id_links = self.driver.find_elements(By.XPATH, f"//a[text()='{manuscript_id}']")
        
        clicked = False
        for link in ms_id_links:
            href = link.get_attribute('href')
            if href and 'view_ms' in href:
                link.click()
                time.sleep(3)
                clicked = True
                break
        
        if not clicked:
            print("      ❌ Could not navigate to files page")
            return []
        
        # Look for PDF links
        pdf_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf') or contains(text(), 'PDF')]")
        
        downloaded_files = []
        
        for i, link in enumerate(pdf_links):
            try:
                link_text = link.text
                parent_text = link.find_element(By.XPATH, "..").text
                
                print(f"      Found PDF: {link_text} in context: {parent_text[:50]}...")
                
                # Clear download directory
                for file in self.download_dir.glob("*.pdf"):
                    file.unlink()
                
                # Click download
                link.click()
                
                # Wait for download
                time.sleep(5)
                
                # Check if downloaded
                downloaded = list(self.download_dir.glob("*.pdf"))
                if downloaded:
                    # Rename based on context
                    if 'cover letter' in parent_text.lower():
                        new_name = f"{manuscript_id}_cover_letter.pdf"
                    elif 'manuscript' in parent_text.lower() or 'article' in parent_text.lower():
                        new_name = f"{manuscript_id}_manuscript.pdf"
                    elif 'referee' in parent_text.lower():
                        ref_num = re.search(r'#(\d+)', parent_text)
                        num = ref_num.group(1) if ref_num else str(i)
                        new_name = f"{manuscript_id}_referee_{num}_report.pdf"
                    else:
                        new_name = f"{manuscript_id}_file_{i}.pdf"
                    
                    new_path = self.output_dir / new_name
                    shutil.move(str(downloaded[0]), str(new_path))
                    
                    downloaded_files.append(new_name)
                    print(f"         ✅ Downloaded: {new_name}")
                
            except Exception as e:
                print(f"         ❌ Error downloading: {e}")
        
        return downloaded_files
    
    def run(self):
        """Run the extraction."""
        print("\n🚀 STARTING STEP-BY-STEP SIAM EXTRACTION")
        
        results = {
            "extraction_time": datetime.now().isoformat(),
            "manuscripts": []
        }
        
        try:
            self.setup_driver()
            
            # Step 1: Authenticate
            if not self.authenticate():
                return
            
            # Step 2: Navigate to manuscripts
            if not self.navigate_to_manuscripts():
                print("❌ Could not navigate to manuscripts")
                return
            
            # Step 3: Extract manuscript list
            manuscripts = self.extract_manuscript_table()
            
            if not manuscripts:
                print("❌ No manuscripts found")
                return
            
            print(f"\n✅ Found {len(manuscripts)} manuscripts")
            
            # Step 4: Process each manuscript
            for ms in manuscripts:
                ms_id = ms["manuscript_id"]
                print(f"\n{'='*60}")
                print(f"Processing {ms_id}")
                print('='*60)
                
                # Get manuscript URL
                if "url" in ms:
                    ms_url = ms["url"]
                else:
                    # Find the URL
                    links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{ms_id}')]")
                    ms_url = None
                    for link in links:
                        href = link.get_attribute('href')
                        if href and 'view_ms' in href:
                            ms_url = href
                            break
                
                if not ms_url:
                    print(f"   ❌ No URL found for {ms_id}")
                    continue
                
                # Get referee details
                referees = self.get_referee_details(ms_url)
                
                # Download PDFs
                pdfs = self.download_pdfs(ms_id, ms_url)
                
                # Store results
                ms_result = {
                    "manuscript_id": ms_id,
                    "url": ms_url,
                    "referees": referees,
                    "pdfs": pdfs
                }
                
                results["manuscripts"].append(ms_result)
            
            # Save results
            with open(self.output_dir / "extraction_results.json", 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"\n✅ Extraction complete!")
            print(f"📁 Results saved to: {self.output_dir}")
            
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
            
            # Save debug info
            self.save_screenshot("error_screenshot")
            self.save_page_source("error_page")
        
        finally:
            if self.driver:
                input("\n⏸️  Press Enter to close browser...")
                self.driver.quit()


def main():
    extractor = StepByStepSIAMExtractor()
    extractor.run()


if __name__ == "__main__":
    main()