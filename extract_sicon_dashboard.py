#!/usr/bin/env python3
"""
SICON Dashboard Extractor - Navigate to author/editor dashboard and extract data
"""

import sys
import os
import time
import json
import re
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

class DashboardSICONExtractor:
    def __init__(self):
        self.orcid_email = os.getenv("ORCID_EMAIL")
        self.orcid_password = os.getenv("ORCID_PASSWORD")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_dir = project_root / "output" / f"dashboard_sicon_{timestamp}"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def extract_dashboard_data(self):
        """Extract data from SICON dashboards."""
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
            
            # Authenticate
            if not self._authenticate(driver, wait):
                return False
            
            print("\n📊 NAVIGATING TO DASHBOARDS...")
            
            manuscripts = []
            referees = []
            documents = []
            
            # Look for dashboard sections on main page
            print("\n🔍 Looking for dashboard sections...")
            
            # Check for author submissions
            try:
                # Look for "Author Tasks" or similar sections
                author_sections = driver.find_elements(By.XPATH, "//td[contains(text(), 'Author') or contains(text(), 'Submission')]")
                print(f"Found {len(author_sections)} author sections")
                
                # Look for manuscript links
                ms_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'ms_id_key')]")
                print(f"Found {len(ms_links)} manuscript links")
                
                for link in ms_links[:5]:  # Process first 5
                    try:
                        link_text = link.text.strip()
                        link_href = link.get_attribute('href')
                        
                        if link_text:
                            print(f"\n📄 Found manuscript link: {link_text}")
                            
                            # Extract manuscript ID from link
                            ms_id_match = re.search(r'ms_id_key=([^&]+)', link_href)
                            if ms_id_match:
                                ms_id = ms_id_match.group(1)
                                
                                # Click and extract details
                                link.click()
                                time.sleep(3)
                                
                                # Get page title
                                page_title = driver.title
                                
                                # Look for manuscript details
                                page_text = driver.page_source
                                
                                # Extract title
                                title_match = re.search(r'Title:?\s*([^<\n]+)', page_text)
                                title = title_match.group(1).strip() if title_match else link_text
                                
                                # Extract author info
                                author_emails = re.findall(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', page_text)
                                
                                manuscripts.append({
                                    'id': ms_id,
                                    'title': title,
                                    'link_text': link_text,
                                    'page_title': page_title,
                                    'authors': author_emails[:3],  # First 3 emails
                                    'url': link_href
                                })
                                
                                print(f"  ✅ Extracted manuscript: {title[:50]}...")
                                
                                # Look for referee info on this page
                                referee_sections = driver.find_elements(By.XPATH, "//*[contains(text(), 'Referee') or contains(text(), 'Reviewer')]")
                                for section in referee_sections:
                                    section_text = section.text
                                    ref_emails = re.findall(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', section_text)
                                    for email in ref_emails:
                                        if email not in ['noreply@siam.org', 'support@orcid.org']:
                                            referees.append({
                                                'email': email,
                                                'manuscript_id': ms_id,
                                                'found_in': 'manuscript_page'
                                            })
                                            print(f"  ✅ Found referee: {email}")
                                
                                # Go back
                                driver.back()
                                time.sleep(2)
                                
                    except Exception as e:
                        print(f"  ❌ Error processing link: {e}")
                        try:
                            driver.get("https://sicon.siam.org/cgi-bin/main.plex")
                            time.sleep(2)
                        except:
                            pass
                            
            except Exception as e:
                print(f"❌ Error finding manuscripts: {e}")
            
            # Look for reviewer/editor sections
            print("\n🔍 Looking for reviewer/editor sections...")
            try:
                # Click on folders to expand them
                folder_icons = driver.find_elements(By.CSS_SELECTOR, "img.ndt_folder_icon")
                print(f"Found {len(folder_icons)} folders")
                
                for i, folder in enumerate(folder_icons[:5]):  # First 5 folders
                    try:
                        print(f"\n📁 Clicking folder {i+1}")
                        driver.execute_script("arguments[0].click();", folder)
                        time.sleep(2)
                        
                        # Look for data in expanded content
                        page_text = driver.page_source
                        
                        # Extract manuscript IDs
                        ms_matches = re.findall(r'(MS-\d{4}-\d{4}|SICON-\d+-\d+)', page_text)
                        for ms_id in ms_matches:
                            if not any(m['id'] == ms_id for m in manuscripts):
                                manuscripts.append({
                                    'id': ms_id,
                                    'found_in': f'folder_{i+1}'
                                })
                                print(f"  ✅ Found manuscript: {ms_id}")
                        
                        # Extract emails
                        emails = re.findall(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', page_text)
                        for email in emails:
                            if email not in ['noreply@siam.org', 'support@orcid.org'] and not any(r['email'] == email for r in referees):
                                referees.append({
                                    'email': email,
                                    'found_in': f'folder_{i+1}'
                                })
                                print(f"  ✅ Found referee: {email}")
                                
                    except Exception as e:
                        print(f"  ❌ Error with folder {i+1}: {e}")
                        
            except Exception as e:
                print(f"❌ Error exploring folders: {e}")
            
            # Save current page HTML
            main_html = self.output_dir / "dashboard_main.html"
            with open(main_html, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            
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
            
            results_file = self.output_dir / "dashboard_extraction_results.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"\n📊 DASHBOARD EXTRACTION RESULTS:")
            print(f"✅ Manuscripts found: {len(manuscripts)}")
            if manuscripts:
                for ms in manuscripts[:3]:
                    print(f"  - {ms.get('id', 'Unknown')}: {ms.get('title', ms.get('link_text', 'No title'))[:50]}...")
            print(f"✅ Referees found: {len(referees)}")
            if referees:
                for ref in referees[:3]:
                    print(f"  - {ref['email']}")
            print(f"✅ Documents found: {len(documents)}")
            print(f"\n💾 Results saved to: {results_file}")
            print(f"💾 HTML saved to: {main_html}")
            
            return True
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if driver:
                print("\n🔧 Keeping browser open for 10 seconds...")
                time.sleep(10)
                driver.quit()
    
    def _authenticate(self, driver, wait):
        """Authenticate with ORCID."""
        try:
            # Navigate to SICON
            print("📍 Navigating to SICON...")
            driver.get("https://sicon.siam.org/cgi-bin/main.plex")
            time.sleep(3)
            
            # Handle SICON cookie banner
            try:
                cookie_bg = driver.find_element(By.ID, "cookie-policy-layer-bg")
                driver.execute_script("arguments[0].remove();", cookie_bg)
                print("✅ Removed cookie overlay")
                time.sleep(1)
            except:
                pass
            
            # Click ORCID login
            orcid_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='orcid']")))
            driver.execute_script("arguments[0].click();", orcid_link)
            print("✅ Clicked ORCID login")
            time.sleep(5)
            
            # Handle ORCID cookie banner
            try:
                accept_btn = wait.until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
                accept_btn.click()
                print("✅ Accepted ORCID cookies")
                time.sleep(2)
            except:
                pass
            
            # Fill credentials with correct selectors
            email_field = wait.until(EC.presence_of_element_located((By.ID, "username-input")))
            email_field.clear()
            email_field.send_keys(self.orcid_email)
            print("✅ Email entered")
            
            password_field = driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(self.orcid_password)
            print("✅ Password entered")
            
            # Submit
            password_field.send_keys(Keys.RETURN)
            print("✅ Login submitted")
            time.sleep(10)
            
            # Check for authorization
            if "authorize" in driver.current_url:
                try:
                    auth_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
                    auth_btn.click()
                    print("✅ Authorized SICON")
                    time.sleep(5)
                except:
                    pass
            
            if "sicon" in driver.current_url.lower():
                print("✅ Authentication successful!")
                
                # Handle cookie banner AGAIN after returning from ORCID
                time.sleep(3)
                try:
                    cookie_bg = driver.find_element(By.ID, "cookie-policy-layer-bg")
                    driver.execute_script("arguments[0].remove();", cookie_bg)
                    print("✅ Removed post-login cookie overlay")
                    time.sleep(1)
                except:
                    pass
                
                # Also try to click any accept buttons
                try:
                    accept_btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'OK')]")
                    for btn in accept_btns:
                        try:
                            driver.execute_script("arguments[0].click();", btn)
                            print("✅ Clicked accept button")
                            break
                        except:
                            continue
                except:
                    pass
                    
                return True
            else:
                print("❌ Authentication failed")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False

if __name__ == "__main__":
    extractor = DashboardSICONExtractor()
    success = extractor.extract_dashboard_data()
    
    if success:
        print("\n🎉 DASHBOARD DATA EXTRACTION COMPLETE!")
    else:
        print("\n❌ Dashboard extraction failed")