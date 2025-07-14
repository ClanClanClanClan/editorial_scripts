#!/usr/bin/env python3
"""
Run the working SIAM extractor for referee analytics
"""

import os
import sys
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
import re

class WorkingSIAMExtractor:
    """Working SIAM extractor using Selenium with minimal stealth"""
    
    def __init__(self, journal_name="SIFIN"):
        self.journal_name = journal_name
        self.driver = None
        self.wait = None
        
        # Journal URLs
        self.urls = {
            "SICON": "http://sicon.siam.org",
            "SIFIN": "http://sifin.siam.org"
        }
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f'./working_siam_{journal_name.lower()}_{timestamp}')
        self.output_dir.mkdir(exist_ok=True)
        
        print(f"📁 Output directory: {self.output_dir}")
        print(f"🎯 Extracting from: {journal_name}")
    
    def setup_driver(self):
        """Setup Chrome WebDriver with minimal stealth (as per user's guidance)"""
        chrome_options = Options()
        
        # Minimal configuration to avoid too much stealth
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Use regular Chrome (not undetected-chromedriver)
        self.driver = webdriver.Chrome(options=chrome_options)
        
        self.wait = WebDriverWait(self.driver, 30)  # Extended timeout for Cloudflare
        print("✅ Chrome WebDriver initialized")
    
    def handle_cloudflare(self):
        """Handle Cloudflare challenge with 60-second wait (proven approach)"""
        try:
            # Check for Cloudflare
            page_source = self.driver.page_source.lower()
            if 'cloudflare' in page_source or 'verifying you are human' in page_source:
                print("🛡️ Cloudflare detected - waiting 60 seconds (proven approach)...")
                time.sleep(60)  # 60-second wait as mentioned by user
                print("✅ Cloudflare wait complete")
                return True
        except Exception as e:
            print(f"⚠️ Cloudflare check error: {e}")
        return False
    
    def authenticate(self):
        """Authenticate with ORCID using proven method"""
        print(f"\n🔐 Authenticating with {self.journal_name}...")
        
        try:
            # Navigate to journal
            url = self.urls[self.journal_name]
            print(f"🌐 Navigating to {url}")
            self.driver.get(f"{url}/cgi-bin/main.plex")
            
            # Handle Cloudflare if present
            self.handle_cloudflare()
            
            # Look for ORCID login
            print("🔍 Looking for ORCID login...")
            
            # Multiple selectors for ORCID button
            orcid_selectors = [
                'img[alt*="ORCID"]',
                'a[href*="orcid"]',
                'img[src*="orcid"]'
            ]
            
            orcid_element = None
            for selector in orcid_selectors:
                try:
                    orcid_element = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    if orcid_element:
                        print(f"✅ Found ORCID element with selector: {selector}")
                        break
                except:
                    continue
            
            if not orcid_element:
                print("❌ No ORCID login found")
                return False
            
            # Click ORCID login
            print("🔗 Clicking ORCID login...")
            self.driver.execute_script("arguments[0].click();", orcid_element)
            
            # Wait for ORCID page
            time.sleep(5)
            
            # Enter credentials
            print("🔐 Entering ORCID credentials...")
            
            # Get credentials from environment
            email = os.environ.get('ORCID_EMAIL')
            password = os.environ.get('ORCID_PASSWORD')
            
            if not email or not password:
                print("❌ ORCID credentials not found in environment")
                return False
            
            # Try multiple username selectors
            username_selectors = [
                'input[name="userId"]',
                'input[id="username"]',
                'input[placeholder*="email"]',
                'input[placeholder*="Email"]'
            ]
            
            username_field = None
            for selector in username_selectors:
                try:
                    username_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if username_field:
                        break
                except:
                    continue
            
            if username_field:
                username_field.clear()
                username_field.send_keys(email)
                print("✅ Username entered")
            
            # Try multiple password selectors  
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[placeholder*="password"]'
            ]
            
            password_field = None
            for selector in password_selectors:
                try:
                    password_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if password_field:
                        break
                except:
                    continue
            
            if password_field:
                password_field.clear()
                password_field.send_keys(password)
                print("✅ Password entered")
            
            # Submit form
            submit_selectors = [
                'input[type="submit"]',
                'button[type="submit"]',
                'button:contains("Sign in")',
                '#signin-button'
            ]
            
            for selector in submit_selectors:
                try:
                    submit_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if submit_btn:
                        submit_btn.click()
                        print("✅ Login form submitted")
                        break
                except:
                    continue
            
            # Wait for authentication to complete
            print("⏳ Waiting for authentication...")
            time.sleep(10)
            
            # Check if we're back at the journal
            current_url = self.driver.current_url
            if self.journal_name.lower() in current_url.lower():
                print("✅ Authentication successful!")
                return True
            else:
                print(f"❌ Still not at journal. Current URL: {current_url}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    def extract_manuscripts(self):
        """Extract manuscript data"""
        print("\n📄 Extracting manuscripts...")
        manuscripts = []
        
        try:
            # Look for manuscript listings
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find manuscript links/tables
            manuscript_elements = soup.find_all(['a', 'tr'], string=re.compile(r'M\d+'))
            
            print(f"Found {len(manuscript_elements)} potential manuscripts")
            
            for elem in manuscript_elements[:5]:  # First 5 for testing
                try:
                    # Extract manuscript ID
                    text = elem.get_text()
                    ms_id_match = re.search(r'(M\d+)', text)
                    if ms_id_match:
                        ms_id = ms_id_match.group(1)
                        manuscripts.append({
                            'id': ms_id,
                            'title': text.strip()[:100],  # First 100 chars
                            'status': 'extracted'
                        })
                        print(f"📄 Found manuscript: {ms_id}")
                except Exception as e:
                    print(f"⚠️ Error processing manuscript element: {e}")
            
            return manuscripts
            
        except Exception as e:
            print(f"❌ Error extracting manuscripts: {e}")
            return []
    
    def run_extraction(self):
        """Run the complete extraction"""
        print("🚀 Starting Working SIAM Extraction...")
        
        # Set credentials
        os.environ['ORCID_EMAIL'] = 'dylan.possamai@polytechnique.org'
        os.environ['ORCID_PASSWORD'] = 'Hioupy0042%'
        
        try:
            self.setup_driver()
            
            if self.authenticate():
                manuscripts = self.extract_manuscripts()
                
                # Save results
                results = {
                    'journal': self.journal_name,
                    'timestamp': datetime.now().isoformat(),
                    'manuscripts_found': len(manuscripts),
                    'manuscripts': manuscripts
                }
                
                results_file = self.output_dir / 'extraction_results.json'
                with open(results_file, 'w') as f:
                    json.dump(results, f, indent=2)
                
                print(f"\n✅ Extraction complete!")
                print(f"📊 Found {len(manuscripts)} manuscripts")
                print(f"💾 Results saved to: {results_file}")
                
                return results
            else:
                print("❌ Authentication failed - cannot proceed")
                return None
                
        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            if self.driver:
                self.driver.quit()
                print("🔚 Browser closed")

def main():
    """Main function"""
    extractor = WorkingSIAMExtractor('SIFIN')  # Test with SIFIN
    results = extractor.run_extraction()
    
    if results:
        print("\n🎉 SUCCESS: Working SIAM extractor is functional!")
    else:
        print("\n❌ FAILURE: Need to debug further")

if __name__ == "__main__":
    main()