#!/usr/bin/env python3
"""
SICON Real Data Extractor - Using correct ORCID login selectors
"""

import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

# Load environment variables
project_root = Path(__file__).parent
load_dotenv(project_root / ".env.production")

class RealSICONExtractor:
    def __init__(self):
        self.orcid_email = os.getenv("ORCID_EMAIL")
        self.orcid_password = os.getenv("ORCID_PASSWORD")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_dir = project_root / "output" / f"real_sicon_{timestamp}"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def extract_real_data(self):
        """Extract REAL referee data from SICON."""
        driver = None
        try:
            # Create driver
            print("🚀 Creating Chrome driver...")
            options = webdriver.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            driver = webdriver.Chrome(options=options)
            driver.implicitly_wait(10)
            wait = WebDriverWait(driver, 20)
            
            # Navigate to SICON
            print("📍 Navigating to SICON...")
            driver.get("https://sicon.siam.org/cgi-bin/main.plex")
            time.sleep(3)
            
            # Handle SICON cookie banner first
            print("🍪 Handling SICON cookie banner...")
            try:
                # Remove cookie overlay background
                cookie_bg = driver.find_element(By.ID, "cookie-policy-layer-bg")
                driver.execute_script("arguments[0].remove();", cookie_bg)
                print("✅ Removed cookie overlay")
                time.sleep(1)
            except:
                pass
            
            # Find and click ORCID login
            print("🔍 Finding ORCID login...")
            orcid_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='orcid']")))
            driver.execute_script("arguments[0].click();", orcid_link)
            print("✅ Clicked ORCID login")
            time.sleep(5)
            
            # Verify we're on ORCID
            if "orcid.org" not in driver.current_url:
                print("❌ Not redirected to ORCID")
                return False
            
            print(f"📍 On ORCID: {driver.current_url}")
            
            # Handle ORCID cookie banner
            print("🍪 Handling ORCID cookie banner...")
            try:
                accept_btn = wait.until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
                accept_btn.click()
                print("✅ Accepted ORCID cookies")
                time.sleep(2)
            except:
                # Try other cookie selectors
                try:
                    cookie_btn = driver.find_element(By.CSS_SELECTOR, "button[id*='accept']")
                    cookie_btn.click()
                    print("✅ Accepted cookies (alternate)")
                    time.sleep(2)
                except:
                    print("ℹ️ No cookie banner found")
            
            # NOW USE THE CORRECT SELECTORS YOU PROVIDED
            print("📧 Filling email field...")
            email_field = wait.until(EC.presence_of_element_located((By.ID, "username-input")))
            email_field.clear()
            email_field.send_keys(self.orcid_email)
            print("✅ Email entered")
            
            print("🔒 Filling password field...")
            password_field = driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(self.orcid_password)
            print("✅ Password entered")
            
            # Submit form
            print("🚀 Submitting login form...")
            # Try multiple submit methods
            try:
                # Method 1: Press Enter
                password_field.send_keys(Keys.RETURN)
                print("✅ Submitted via Enter key")
            except:
                try:
                    # Method 2: Find submit button
                    submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                    submit_btn.click()
                    print("✅ Submitted via button click")
                except:
                    pass
            
            # Wait for authentication
            print("⏳ Waiting for authentication...")
            time.sleep(10)
            
            current_url = driver.current_url
            print(f"📍 Current URL: {current_url}")
            
            # Check for authorization page
            if "authorize" in current_url:
                print("🔓 Handling authorization...")
                try:
                    auth_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
                    auth_btn.click()
                    print("✅ Authorized SICON access")
                    time.sleep(5)
                except:
                    pass
            
            # Check if we're back at SICON
            final_url = driver.current_url
            print(f"📍 Final URL: {final_url}")
            
            if "sicon" in final_url.lower():
                print("✅ Successfully authenticated!")
                
                # Extract real data
                print("\n📊 EXTRACTING REAL REFEREE DATA...")
                
                # Navigate to editorial pages
                editorial_urls = [
                    "https://sicon.siam.org/cgi-bin/main.plex?el=A",
                    "https://sicon.siam.org/cgi-bin/main.plex?form_type=display_rev_assign",
                    "https://sicon.siam.org/cgi-bin/main.plex?form_type=display_manuscripts"
                ]
                
                manuscripts = []
                referees = []
                documents = []
                
                for url in editorial_urls:
                    try:
                        print(f"\n📍 Accessing: {url}")
                        driver.get(url)
                        time.sleep(5)
                        
                        # Extract manuscripts
                        ms_elements = driver.find_elements(By.XPATH, "//a[contains(text(), 'MS-')]")
                        for ms in ms_elements:
                            ms_id = ms.text.strip()
                            if ms_id and ms_id.startswith("MS-"):
                                manuscripts.append({
                                    'id': ms_id,
                                    'url': ms.get_attribute('href'),
                                    'extracted_from': url
                                })
                                print(f"  📄 Found manuscript: {ms_id}")
                        
                        # Extract referee information
                        # Look for email patterns
                        page_text = driver.page_source
                        import re
                        email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
                        emails = re.findall(email_pattern, page_text)
                        
                        for email in emails:
                            if email not in ['noreply@siam.org', 'support@orcid.org']:  # Filter system emails
                                referees.append({
                                    'email': email,
                                    'extracted_from': url
                                })
                                print(f"  👤 Found referee email: {email}")
                        
                        # Look for PDF links
                        pdf_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf')]")
                        for pdf in pdf_links:
                            pdf_name = pdf.text.strip() or pdf.get_attribute('href').split('/')[-1]
                            documents.append({
                                'name': pdf_name,
                                'url': pdf.get_attribute('href'),
                                'extracted_from': url
                            })
                            print(f"  📎 Found document: {pdf_name}")
                            
                    except Exception as e:
                        print(f"  ❌ Error accessing {url}: {e}")
                
                # Save results
                results = {
                    'extraction_date': datetime.now().isoformat(),
                    'authentication_success': True,
                    'manuscripts_found': len(manuscripts),
                    'referees_found': len(referees),
                    'documents_found': len(documents),
                    'manuscripts': manuscripts,
                    'referees': referees,
                    'documents': documents
                }
                
                results_file = self.output_dir / "real_extraction_results.json"
                with open(results_file, 'w') as f:
                    json.dump(results, f, indent=2)
                
                print(f"\n📊 REAL DATA EXTRACTION RESULTS:")
                print(f"✅ Manuscripts found: {len(manuscripts)}")
                print(f"✅ Referees found: {len(referees)}")
                print(f"✅ Documents found: {len(documents)}")
                print(f"💾 Results saved to: {results_file}")
                
                return True
            else:
                print("❌ Authentication failed - not at SICON")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if driver:
                time.sleep(5)  # Keep open briefly to see results
                driver.quit()

if __name__ == "__main__":
    extractor = RealSICONExtractor()
    success = extractor.extract_real_data()
    
    if success:
        print("\n🎉 REAL DATA EXTRACTION SUCCESSFUL!")
    else:
        print("\n❌ Real data extraction failed")