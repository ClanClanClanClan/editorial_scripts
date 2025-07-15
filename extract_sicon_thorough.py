#!/usr/bin/env python3
"""
SICON Thorough Data Extractor - Find and extract all manuscript and referee data
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

class ThoroughSICONExtractor:
    def __init__(self):
        self.orcid_email = os.getenv("ORCID_EMAIL")
        self.orcid_password = os.getenv("ORCID_PASSWORD")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_dir = project_root / "output" / f"thorough_sicon_{timestamp}"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def extract_thorough_data(self):
        """Extract all available data from SICON."""
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
            
            # Authenticate (same as before)
            if not self._authenticate(driver, wait):
                return False
            
            print("\n📊 EXPLORING SICON INTERFACE...")
            
            # Save page HTML for analysis
            main_page_html = self.output_dir / "main_page.html"
            with open(main_page_html, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print(f"💾 Saved main page HTML to: {main_page_html}")
            
            # Find all links on the main page
            all_links = driver.find_elements(By.TAG_NAME, "a")
            print(f"\n🔍 Found {len(all_links)} links on main page")
            
            # Categorize links
            editorial_links = []
            manuscript_links = []
            other_links = []
            
            for link in all_links:
                try:
                    href = link.get_attribute('href')
                    text = link.text.strip()
                    
                    if href and 'sicon.siam.org' in href:
                        link_info = {
                            'text': text,
                            'href': href
                        }
                        
                        if any(keyword in text.lower() for keyword in ['manuscript', 'paper', 'submission', 'ms-']):
                            manuscript_links.append(link_info)
                            print(f"  📄 Manuscript link: {text[:50]}")
                        elif any(keyword in text.lower() for keyword in ['editor', 'referee', 'review', 'assign']):
                            editorial_links.append(link_info)
                            print(f"  👤 Editorial link: {text[:50]}")
                        else:
                            other_links.append(link_info)
                except:
                    continue
            
            # Extract data from each category
            manuscripts = []
            referees = []
            documents = []
            
            # Process manuscript links
            print(f"\n📄 Processing {len(manuscript_links)} manuscript links...")
            for i, link in enumerate(manuscript_links[:10]):  # Limit to first 10
                try:
                    print(f"  Visiting: {link['text']}")
                    driver.get(link['href'])
                    time.sleep(2)
                    
                    # Extract manuscript data from page
                    page_text = driver.page_source
                    
                    # Look for manuscript IDs
                    ms_ids = re.findall(r'MS-\d{4}-\d{4}', page_text)
                    for ms_id in ms_ids:
                        if not any(m['id'] == ms_id for m in manuscripts):
                            manuscripts.append({
                                'id': ms_id,
                                'found_on': link['href'],
                                'page_title': driver.title
                            })
                            print(f"    ✅ Found manuscript: {ms_id}")
                    
                    # Look for email addresses (potential referees)
                    emails = re.findall(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', page_text)
                    for email in emails:
                        if email not in ['noreply@siam.org', 'support@orcid.org'] and not any(r['email'] == email for r in referees):
                            referees.append({
                                'email': email,
                                'found_on': link['href']
                            })
                            print(f"    ✅ Found referee email: {email}")
                    
                except Exception as e:
                    print(f"    ❌ Error processing link: {e}")
            
            # Look for specific SICON pages
            print("\n🔍 Checking specific SICON pages...")
            specific_pages = [
                ("Author Main", "https://sicon.siam.org/cgi-bin/main.plex?el=A"),
                ("Editor Main", "https://sicon.siam.org/cgi-bin/main.plex?el=E"),
                ("Reviewer Main", "https://sicon.siam.org/cgi-bin/main.plex?el=R"),
                ("Manuscripts List", "https://sicon.siam.org/cgi-bin/main.plex?form_type=display_manuscripts"),
                ("Under Review", "https://sicon.siam.org/cgi-bin/main.plex?form_type=status_under_review"),
                ("Pending", "https://sicon.siam.org/cgi-bin/main.plex?form_type=status_pending"),
                ("Assigned", "https://sicon.siam.org/cgi-bin/main.plex?form_type=display_rev_assign"),
                ("All Submissions", "https://sicon.siam.org/cgi-bin/main.plex?form_type=all_submissions")
            ]
            
            for page_name, url in specific_pages:
                try:
                    print(f"\n📍 Checking {page_name}: {url}")
                    driver.get(url)
                    time.sleep(3)
                    
                    # Save page for analysis
                    page_file = self.output_dir / f"{page_name.replace(' ', '_').lower()}.html"
                    with open(page_file, 'w', encoding='utf-8') as f:
                        f.write(driver.page_source)
                    
                    # Look for data
                    page_text = driver.page_source
                    
                    # Extract manuscript IDs
                    ms_ids = re.findall(r'MS-\d{4}-\d{4}', page_text)
                    for ms_id in ms_ids:
                        if not any(m['id'] == ms_id for m in manuscripts):
                            manuscripts.append({
                                'id': ms_id,
                                'found_on': url,
                                'page': page_name
                            })
                            print(f"  ✅ Found manuscript: {ms_id}")
                    
                    # Extract SICON submission IDs
                    sicon_ids = re.findall(r'SICON-\d+-\d+', page_text)
                    for sicon_id in sicon_ids:
                        if not any(m['id'] == sicon_id for m in manuscripts):
                            manuscripts.append({
                                'id': sicon_id,
                                'found_on': url,
                                'page': page_name
                            })
                            print(f"  ✅ Found SICON ID: {sicon_id}")
                    
                    # Look for referee information in tables
                    tables = driver.find_elements(By.TAG_NAME, "table")
                    print(f"  Found {len(tables)} tables")
                    
                    for table in tables:
                        try:
                            rows = table.find_elements(By.TAG_NAME, "tr")
                            for row in rows:
                                cells = row.find_elements(By.TAG_NAME, "td")
                                for cell in cells:
                                    cell_text = cell.text.strip()
                                    # Look for email patterns
                                    if '@' in cell_text:
                                        email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', cell_text)
                                        if email_match:
                                            email = email_match.group(1)
                                            if email not in ['noreply@siam.org', 'support@orcid.org']:
                                                referees.append({
                                                    'email': email,
                                                    'found_on': url,
                                                    'page': page_name,
                                                    'context': cell_text[:100]
                                                })
                                                print(f"  ✅ Found referee: {email}")
                        except:
                            continue
                    
                    # Look for document links
                    doc_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf') or contains(@href, 'download')]")
                    for doc_link in doc_links:
                        try:
                            doc_text = doc_link.text.strip()
                            doc_href = doc_link.get_attribute('href')
                            if doc_text or doc_href:
                                documents.append({
                                    'name': doc_text or 'Unnamed',
                                    'url': doc_href,
                                    'found_on': url,
                                    'page': page_name
                                })
                                print(f"  ✅ Found document: {doc_text or 'PDF'}")
                        except:
                            continue
                            
                except Exception as e:
                    print(f"  ❌ Error accessing {page_name}: {e}")
            
            # Save all results
            results = {
                'extraction_date': datetime.now().isoformat(),
                'authentication_success': True,
                'pages_checked': len(specific_pages),
                'manuscripts_found': len(manuscripts),
                'referees_found': len(referees),
                'documents_found': len(documents),
                'manuscripts': manuscripts,
                'referees': referees,
                'documents': documents,
                'editorial_links_found': len(editorial_links),
                'manuscript_links_found': len(manuscript_links)
            }
            
            results_file = self.output_dir / "thorough_extraction_results.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            # Save link analysis
            links_file = self.output_dir / "link_analysis.json"
            with open(links_file, 'w') as f:
                json.dump({
                    'editorial_links': editorial_links[:20],
                    'manuscript_links': manuscript_links[:20],
                    'other_links': other_links[:20]
                }, f, indent=2)
            
            print(f"\n📊 THOROUGH EXTRACTION RESULTS:")
            print(f"✅ Authentication: SUCCESS")
            print(f"✅ Pages checked: {len(specific_pages)}")
            print(f"✅ Manuscripts found: {len(manuscripts)}")
            print(f"✅ Referees found: {len(referees)}")
            print(f"✅ Documents found: {len(documents)}")
            print(f"✅ Editorial links: {len(editorial_links)}")
            print(f"✅ Manuscript links: {len(manuscript_links)}")
            print(f"\n💾 Results saved to: {results_file}")
            print(f"💾 Link analysis saved to: {links_file}")
            print(f"💾 HTML pages saved in: {self.output_dir}")
            
            return True
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if driver:
                time.sleep(5)
                driver.quit()
    
    def _authenticate(self, driver, wait):
        """Authenticate with ORCID (same as before)."""
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
            
            # Fill credentials
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
                return True
            else:
                print("❌ Authentication failed")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False

if __name__ == "__main__":
    extractor = ThoroughSICONExtractor()
    success = extractor.extract_thorough_data()
    
    if success:
        print("\n🎉 THOROUGH DATA EXTRACTION COMPLETE!")
    else:
        print("\n❌ Thorough extraction failed")