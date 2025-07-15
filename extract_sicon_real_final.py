#!/usr/bin/env python3
"""
SICON Real Final Extractor - Click on Live/Post Decision Manuscripts to get real data
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

class RealFinalSICONExtractor:
    def __init__(self):
        self.orcid_email = os.getenv("ORCID_EMAIL")
        self.orcid_password = os.getenv("ORCID_PASSWORD")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_dir = project_root / "output" / f"real_final_sicon_{timestamp}"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def extract_real_final_data(self):
        """Extract REAL manuscript and referee data from SICON."""
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
            
            print("\n📊 EXTRACTING REAL MANUSCRIPT DATA...")
            
            manuscripts = []
            referees = []
            documents = []
            
            # Look for manuscript folders
            manuscript_folders = [
                "Live Manuscripts",
                "Post Decision Manuscripts",
                "Awaiting Referee Assignment",
                "Under Review"
            ]
            
            for folder_name in manuscript_folders:
                try:
                    print(f"\n🔍 Looking for '{folder_name}' folder...")
                    
                    # Find the folder link
                    folder_links = driver.find_elements(By.XPATH, f"//a[contains(text(), '{folder_name}')]")
                    
                    if folder_links:
                        folder_link = folder_links[0]
                        folder_text = folder_link.text
                        print(f"✅ Found: {folder_text}")
                        
                        # Click the folder
                        driver.execute_script("arguments[0].click();", folder_link)
                        time.sleep(3)
                        
                        # Save the page
                        folder_file = self.output_dir / f"{folder_name.replace(' ', '_').lower()}.html"
                        with open(folder_file, 'w', encoding='utf-8') as f:
                            f.write(driver.page_source)
                        
                        # Extract data from the folder page
                        page_text = driver.page_source
                        
                        # Look for manuscript IDs (MS-XXXX-XXXX or SICON-XX-XXXX patterns)
                        ms_patterns = [
                            r'MS-\d{4}-\d{4}',
                            r'SICON-\d{2}-\d{4}',
                            r'SICON-\d{4}-\d{4}'
                        ]
                        
                        for pattern in ms_patterns:
                            ms_ids = re.findall(pattern, page_text)
                            for ms_id in ms_ids:
                                if not any(m['id'] == ms_id for m in manuscripts):
                                    print(f"  📄 Found manuscript: {ms_id}")
                                    
                                    # Try to find more details about this manuscript
                                    # Look for the manuscript in a table row or list item
                                    ms_context = ""
                                    ms_title = ""
                                    
                                    # Search for title near the ID
                                    title_patterns = [
                                        rf'{ms_id}[^<]*?<[^>]*?>([^<]+)',
                                        rf'([^<]+?)[^<]*?{ms_id}',
                                        rf'{ms_id}\s*-?\s*([^<\n]+)'
                                    ]
                                    
                                    for title_pattern in title_patterns:
                                        title_match = re.search(title_pattern, page_text)
                                        if title_match:
                                            ms_title = title_match.group(1).strip()
                                            if len(ms_title) > 10 and ms_title != ms_id:
                                                break
                                    
                                    manuscripts.append({
                                        'id': ms_id,
                                        'title': ms_title or 'Title not found',
                                        'folder': folder_name,
                                        'extraction_date': datetime.now().isoformat()
                                    })
                        
                        # Look for email addresses (referees)
                        email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
                        emails = re.findall(email_pattern, page_text)
                        
                        for email in emails:
                            if email not in ['sicon@siam.org', 'noreply@siam.org', 'support@orcid.org']:
                                if not any(r['email'] == email for r in referees):
                                    print(f"  👤 Found referee: {email}")
                                    
                                    # Try to find referee name near email
                                    name_patterns = [
                                        rf'([A-Z][a-z]+\s+[A-Z][a-z]+)[^<]*?{re.escape(email)}',
                                        rf'{re.escape(email)}[^<]*?([A-Z][a-z]+\s+[A-Z][a-z]+)',
                                        rf'([A-Z][a-z]+,?\s+[A-Z][a-z]+)[^<]*?{re.escape(email)}'
                                    ]
                                    
                                    referee_name = ""
                                    for name_pattern in name_patterns:
                                        name_match = re.search(name_pattern, page_text)
                                        if name_match:
                                            referee_name = name_match.group(1).strip()
                                            break
                                    
                                    referees.append({
                                        'email': email,
                                        'name': referee_name or 'Name not found',
                                        'folder': folder_name,
                                        'extraction_date': datetime.now().isoformat()
                                    })
                        
                        # Look for document links
                        pdf_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf')]")
                        for pdf_link in pdf_links:
                            try:
                                pdf_name = pdf_link.text.strip() or 'PDF Document'
                                pdf_url = pdf_link.get_attribute('href')
                                
                                documents.append({
                                    'name': pdf_name,
                                    'url': pdf_url,
                                    'folder': folder_name,
                                    'extraction_date': datetime.now().isoformat()
                                })
                                print(f"  📎 Found document: {pdf_name}")
                            except:
                                continue
                        
                        # Try to click on individual manuscripts to get more details
                        try:
                            ms_links = driver.find_elements(By.XPATH, f"//a[contains(text(), 'MS-') or contains(text(), 'SICON-')]")
                            
                            for i, ms_link in enumerate(ms_links[:2]):  # First 2 manuscripts only
                                try:
                                    ms_text = ms_link.text
                                    print(f"\n  📋 Clicking on manuscript: {ms_text}")
                                    
                                    driver.execute_script("arguments[0].click();", ms_link)
                                    time.sleep(3)
                                    
                                    # Extract referee details from manuscript page
                                    ms_page_text = driver.page_source
                                    
                                    # Look for referee status information
                                    referee_statuses = re.findall(r'(Accepted|Declined|Pending|Invited)[^<]*?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', ms_page_text)
                                    
                                    for status, ref_email in referee_statuses:
                                        # Update existing referee or add new one
                                        existing_ref = next((r for r in referees if r['email'] == ref_email), None)
                                        if existing_ref:
                                            existing_ref['status'] = status
                                        else:
                                            referees.append({
                                                'email': ref_email,
                                                'status': status,
                                                'manuscript': ms_text,
                                                'extraction_date': datetime.now().isoformat()
                                            })
                                            print(f"    ✅ Referee: {ref_email} - {status}")
                                    
                                    # Go back
                                    driver.back()
                                    time.sleep(2)
                                    
                                except Exception as e:
                                    print(f"    ❌ Error clicking manuscript: {e}")
                                    
                        except Exception as e:
                            print(f"  ❌ Error exploring manuscripts: {e}")
                        
                        # Go back to main page
                        driver.get("https://sicon.siam.org/cgi-bin/main.plex")
                        time.sleep(2)
                        
                        # Remove cookie banner again if needed
                        try:
                            cookie_bg = driver.find_element(By.ID, "cookie-policy-layer-bg")
                            driver.execute_script("arguments[0].remove();", cookie_bg)
                            time.sleep(1)
                        except:
                            pass
                            
                except Exception as e:
                    print(f"❌ Error with folder '{folder_name}': {e}")
            
            # Calculate baseline compliance
            baseline_compliance = {
                'manuscripts': {
                    'found': len(manuscripts),
                    'target': 4,
                    'compliance': len(manuscripts) >= 4
                },
                'referees': {
                    'found': len(referees),
                    'target': 13,
                    'compliance': len(referees) >= 13,
                    'with_status': len([r for r in referees if 'status' in r])
                },
                'documents': {
                    'found': len(documents),
                    'target': 11,
                    'compliance': len(documents) >= 11
                }
            }
            
            # Save results
            results = {
                'extraction_date': datetime.now().isoformat(),
                'authentication_success': True,
                'extraction_type': 'REAL_SICON_DATA',
                'baseline_compliance': baseline_compliance,
                'manuscripts': manuscripts,
                'referees': referees,
                'documents': documents
            }
            
            results_file = self.output_dir / "real_final_extraction_results.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            # Save summary
            summary_file = self.output_dir / "real_extraction_summary.txt"
            with open(summary_file, 'w') as f:
                f.write("SICON REAL DATA EXTRACTION SUMMARY\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Extraction Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Authentication: ✅ SUCCESS\n\n")
                
                f.write("REAL DATA EXTRACTED:\n")
                f.write(f"• Manuscripts: {len(manuscripts)} (Target: 4)\n")
                if manuscripts:
                    for ms in manuscripts[:5]:
                        f.write(f"  - {ms['id']}: {ms.get('title', 'No title')[:50]}...\n")
                
                f.write(f"\n• Referees: {len(referees)} (Target: 13)\n")
                if referees:
                    for ref in referees[:5]:
                        f.write(f"  - {ref['email']} ({ref.get('status', 'No status')})\n")
                    if len(referees) > 5:
                        f.write(f"  ... and {len(referees) - 5} more referees\n")
                
                f.write(f"\n• Documents: {len(documents)} (Target: 11)\n")
                if documents:
                    for doc in documents[:5]:
                        f.write(f"  - {doc['name']}\n")
            
            print(f"\n📊 REAL DATA EXTRACTION RESULTS:")
            print(f"✅ Authentication: SUCCESS")
            print(f"✅ Manuscripts found: {len(manuscripts)} {'✅' if len(manuscripts) >= 4 else '❌'}")
            if manuscripts:
                for ms in manuscripts[:3]:
                    print(f"  - {ms['id']}: {ms.get('title', 'No title')[:40]}...")
            print(f"✅ Referees found: {len(referees)} {'✅' if len(referees) >= 13 else '❌'}")
            if referees:
                for ref in referees[:3]:
                    print(f"  - {ref['email']} ({ref.get('status', 'No status')})")
            print(f"✅ Documents found: {len(documents)} {'✅' if len(documents) >= 11 else '❌'}")
            
            print(f"\n💾 Results saved to: {results_file}")
            print(f"💾 Summary saved to: {summary_file}")
            print(f"💾 HTML pages saved in: {self.output_dir}")
            
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
                    
                return True
            else:
                print("❌ Authentication failed")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False

if __name__ == "__main__":
    extractor = RealFinalSICONExtractor()
    success = extractor.extract_real_final_data()
    
    if success:
        print("\n🎉 REAL DATA EXTRACTION COMPLETE!")
        print("✅ Extracted actual SICON manuscript and referee data!")
    else:
        print("\n❌ Real data extraction failed")