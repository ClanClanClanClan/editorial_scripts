#!/usr/bin/env python3
"""
Debug referee email extraction - see what's actually on the manuscript pages
"""

import os
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup


class RefereeEmailDebugger:
    def __init__(self):
        self.driver = None
        self.wait = None
        
        # Create output directory
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./debug_referee_emails_{timestamp}')
        self.output_dir.mkdir(exist_ok=True)
        
    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)
        print("✅ Chrome WebDriver initialized")
    
    def save_page_source(self, name):
        html_path = self.output_dir / f"{name}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
        print(f"📄 Saved: {html_path.name}")
    
    def authenticate_sicon(self):
        print("🔐 Authenticating...")
        
        self.driver.get("http://sicon.siam.org")
        time.sleep(3)
        
        # Handle popups
        try:
            continue_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Continue')]")
            if continue_buttons:
                continue_buttons[0].click()
                time.sleep(2)
        except:
            pass
        
        # Check if already authenticated
        if "logout" in self.driver.page_source.lower():
            print("✅ Already authenticated!")
            return True
        
        # Click ORCID
        orcid_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'orcid')]")
        if orcid_links:
            self.driver.execute_script("arguments[0].click();", orcid_links[0])
            time.sleep(3)
            
            if 'orcid.org' in self.driver.current_url:
                # Fill credentials
                username = self.wait.until(EC.presence_of_element_located((By.ID, "username-input")))
                username.send_keys("0000-0002-9364-0124")
                
                password = self.driver.find_element(By.ID, "password")
                password.send_keys("Hioupy0042%")
                password.send_keys(Keys.RETURN)
                
                # Wait for redirect
                timeout = time.time() + 30
                while time.time() < timeout:
                    if 'sicon.siam.org' in self.driver.current_url:
                        print("✅ Authentication successful!")
                        return True
                    time.sleep(1)
        
        return False
    
    def debug_manuscript_page(self, ms_url, ms_id):
        print(f"\n🔍 Debugging {ms_id}...")
        
        # Navigate to manuscript
        full_url = f"http://sicon.siam.org/{ms_url}" if not ms_url.startswith('http') else ms_url
        self.driver.get(full_url)
        time.sleep(3)
        
        # Save page source
        self.save_page_source(f"{ms_id}_manuscript_page")
        
        # Look for ALL links
        all_links = self.driver.find_elements(By.TAG_NAME, "a")
        print(f"   Found {len(all_links)} total links")
        
        # Check for person/referee links
        person_links = []
        for link in all_links:
            href = link.get_attribute('href') or ''
            text = link.text.strip()
            
            if ('person' in href.lower() or 'dump_person' in href.lower() or 
                any(name in text.lower() for name in ['ferrari', 'cohen', 'ekren', 'daudin', 'li', 'guo', 'ren', 'tangpi'])):
                person_links.append((text, href))
        
        print(f"   Found {len(person_links)} potential referee links:")
        for text, href in person_links:
            print(f"      '{text}' -> {href[:60]}...")
        
        # Look for tables with referee info
        tables = self.driver.find_elements(By.TAG_NAME, "table")
        print(f"   Found {len(tables)} tables")
        
        for i, table in enumerate(tables):
            table_text = table.text
            if any(name in table_text.lower() for name in ['ferrari', 'cohen', 'ekren', 'daudin']):
                print(f"      Table {i+1} contains referee names")
                print(f"      Text preview: {table_text[:100]}...")
        
        return person_links
    
    def test_referee_link(self, link_text, link_href):
        print(f"\n🔗 Testing link: '{link_text}' -> {link_href}")
        
        try:
            # Open in new tab
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.get(link_href)
            time.sleep(2)
            
            # Save page source
            safe_name = link_text.replace(' ', '_').replace('/', '_')[:20]
            self.save_page_source(f"referee_{safe_name}_profile")
            
            # Look for email
            email_links = self.driver.find_elements(By.XPATH, "//a[starts-with(@href, 'mailto:')]")
            if email_links:
                email = email_links[0].get_attribute('href').replace('mailto:', '')
                print(f"   ✅ Found email: {email}")
            else:
                print(f"   ❌ No email found")
                
                # Look for any email patterns in text
                page_text = self.driver.page_source
                import re
                emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', page_text)
                if emails:
                    print(f"   📧 Found email patterns: {emails[:3]}")
            
            # Get page title
            title = self.driver.title
            print(f"   📄 Page title: {title}")
            
            # Close tab
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            if len(self.driver.window_handles) > 1:
                self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
    
    def run(self):
        print("🚀 STARTING REFEREE EMAIL DEBUG")
        
        try:
            self.setup_driver()
            
            if not self.authenticate_sicon():
                print("❌ Authentication failed")
                return
            
            # Test with one manuscript
            test_manuscripts = [
                ("M172838", "cgi-bin/main.plex?form_type=view_ms&j_id=8&ms_id=145756&ms_rev_no=0&ms_id_key=ftdcly1bpP6HE2Kk1N12e8GZw")
            ]
            
            for ms_id, ms_url in test_manuscripts:
                person_links = self.debug_manuscript_page(ms_url, ms_id)
                
                # Test the first few referee links
                for i, (text, href) in enumerate(person_links[:3]):
                    if href:
                        self.test_referee_link(text, href)
            
            print(f"\n✅ Debug complete! Check files in: {self.output_dir}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            if self.driver:
                self.driver.quit()


if __name__ == "__main__":
    debugger = RefereeEmailDebugger()
    debugger.run()
