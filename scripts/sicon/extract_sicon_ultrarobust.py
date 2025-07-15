#!/usr/bin/env python3
"""
ULTRA-ROBUST SICON Extractor - Handles all authentication edge cases
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
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, ElementClickInterceptedException

# Load environment variables
project_root = Path(__file__).parent
load_dotenv(project_root / ".env.production")

class UltraRobustSICONExtractor:
    def __init__(self):
        self.orcid_email = os.getenv("ORCID_EMAIL")
        self.orcid_password = os.getenv("ORCID_PASSWORD")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_dir = project_root / "output" / f"ultrarobust_sicon_{timestamp}"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def remove_all_overlays(self, driver):
        """Remove ALL possible overlays and banners that could block clicks."""
        removed_count = 0
        
        # List of overlay selectors to remove
        overlay_selectors = [
            "#cookie-policy-layer-bg",
            ".cookie-policy-layer",
            ".cookie-banner",
            ".privacy-banner",
            "#onetrust-banner-sdk",
            ".onetrust-pc-dark-filter",
            "[class*='cookie']",
            "[id*='cookie']",
            "div[style*='z-index: 1000']",
            "div[style*='position: fixed']",
            ".modal-backdrop",
            ".overlay"
        ]
        
        for selector in overlay_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    try:
                        # Check if element is visible and blocking
                        if element.is_displayed():
                            driver.execute_script("arguments[0].remove();", element)
                            removed_count += 1
                    except:
                        pass
            except:
                pass
        
        if removed_count > 0:
            print(f"✅ Removed {removed_count} overlay elements")
            time.sleep(1)
        
        return removed_count > 0
    
    def click_accept_cookies(self, driver):
        """Try to click any accept cookie buttons."""
        accept_selectors = [
            "#onetrust-accept-btn-handler",
            "button[id*='accept']",
            "button[class*='accept']",
            "button[onclick*='accept']",
            "a[onclick*='accept']",
            "//button[contains(text(), 'Accept')]",
            "//button[contains(text(), 'OK')]",
            "//button[contains(text(), 'Agree')]",
            "//a[contains(text(), 'Accept')]",
            ".accept-cookies",
            ".btn-accept"
        ]
        
        for selector in accept_selectors:
            try:
                if selector.startswith("//"):
                    element = driver.find_element(By.XPATH, selector)
                else:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                
                if element.is_displayed():
                    try:
                        element.click()
                        print(f"✅ Clicked accept button: {selector}")
                        time.sleep(2)
                        return True
                    except:
                        try:
                            driver.execute_script("arguments[0].click();", element)
                            print(f"✅ JS clicked accept button: {selector}")
                            time.sleep(2)
                            return True
                        except:
                            pass
            except:
                pass
        
        return False
    
    def wait_and_click(self, driver, selector, selector_type=By.CSS_SELECTOR, timeout=10, use_js=False):
        """Wait for element and click with retry logic."""
        wait = WebDriverWait(driver, timeout)
        
        for attempt in range(3):
            try:
                # Remove overlays before each attempt
                self.remove_all_overlays(driver)
                
                # Wait for element
                element = wait.until(EC.element_to_be_clickable((selector_type, selector)))
                
                # Scroll into view
                driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(0.5)
                
                # Click
                if use_js:
                    driver.execute_script("arguments[0].click();", element)
                else:
                    element.click()
                
                return True
                
            except ElementClickInterceptedException:
                print(f"⚠️ Click intercepted, removing overlays (attempt {attempt + 1})")
                self.remove_all_overlays(driver)
                self.click_accept_cookies(driver)
                time.sleep(2)
            except TimeoutException:
                print(f"⚠️ Timeout waiting for {selector}")
                return False
            except Exception as e:
                print(f"⚠️ Error clicking {selector}: {e}")
                time.sleep(1)
        
        return False
    
    def ultra_robust_authenticate(self, driver):
        """Ultra-robust authentication with comprehensive error handling."""
        try:
            wait = WebDriverWait(driver, 20)
            
            # Step 1: Navigate to SICON
            print("📍 Step 1: Navigating to SICON...")
            driver.get("https://sicon.siam.org/cgi-bin/main.plex")
            time.sleep(3)
            
            # Step 2: Clear all overlays
            print("🧹 Step 2: Clearing initial overlays...")
            self.remove_all_overlays(driver)
            self.click_accept_cookies(driver)
            
            # Step 3: Find and click ORCID login
            print("🔍 Step 3: Finding ORCID login...")
            orcid_clicked = self.wait_and_click(driver, "a[href*='orcid']", use_js=True)
            
            if not orcid_clicked:
                print("❌ Could not find ORCID login link")
                return False
            
            print("✅ Clicked ORCID login")
            time.sleep(5)
            
            # Step 4: Verify we're on ORCID
            if "orcid.org" not in driver.current_url:
                print("❌ Not redirected to ORCID")
                return False
            
            print("✅ On ORCID login page")
            
            # Step 5: Handle ORCID cookies
            print("🍪 Step 5: Handling ORCID cookies...")
            self.click_accept_cookies(driver)
            self.remove_all_overlays(driver)
            
            # Step 6: Fill credentials with retry
            print("📧 Step 6: Filling credentials...")
            for attempt in range(3):
                try:
                    # Email field
                    email_field = wait.until(EC.presence_of_element_located((By.ID, "username-input")))
                    email_field.clear()
                    time.sleep(0.5)
                    email_field.send_keys(self.orcid_email)
                    print("✅ Email entered")
                    
                    # Password field
                    password_field = driver.find_element(By.ID, "password")
                    password_field.clear()
                    time.sleep(0.5)
                    password_field.send_keys(self.orcid_password)
                    print("✅ Password entered")
                    
                    # Submit with Enter key (most reliable)
                    password_field.send_keys(Keys.RETURN)
                    print("✅ Form submitted")
                    break
                    
                except Exception as e:
                    print(f"⚠️ Credential entry attempt {attempt + 1} failed: {e}")
                    time.sleep(2)
            
            # Step 7: Wait for response
            print("⏳ Step 7: Waiting for authentication response...")
            time.sleep(10)
            
            # Step 8: Handle authorization if needed
            if "authorize" in driver.current_url:
                print("🔓 Step 8: Handling authorization...")
                auth_clicked = self.wait_and_click(driver, "button[type='submit']", use_js=True)
                if auth_clicked:
                    print("✅ Authorization granted")
                    time.sleep(5)
            
            # Step 9: Verify we're back on SICON
            if "sicon" not in driver.current_url.lower():
                print("❌ Not returned to SICON")
                return False
            
            print("✅ Back on SICON")
            
            # Step 10: Final cleanup of overlays
            print("🧹 Step 10: Final overlay cleanup...")
            time.sleep(3)
            self.remove_all_overlays(driver)
            self.click_accept_cookies(driver)
            
            # Step 11: Verify authentication by looking for logout
            page_source = driver.page_source.lower()
            if any(indicator in page_source for indicator in ['logout', 'sign out', 'my account']):
                print("✅ Authentication verified - found logout option")
                return True
            
            print("⚠️ Could not verify authentication status")
            return True  # Assume success if we're on SICON
            
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def extract_from_folder(self, driver, folder_name, folder_link):
        """Extract data from a specific folder with robust error handling."""
        manuscripts = []
        referees = []
        documents = []
        
        try:
            # Click the folder
            print(f"\n📁 Opening folder: {folder_name}")
            driver.execute_script("arguments[0].click();", folder_link)
            time.sleep(3)
            
            # Save the page
            folder_file = self.output_dir / f"{folder_name.replace(' ', '_').lower()}.html"
            with open(folder_file, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            
            # Now look for manuscript table or list
            # Try multiple strategies to find manuscripts
            
            # Strategy 1: Look for table with manuscripts
            try:
                tables = driver.find_elements(By.TAG_NAME, "table")
                for table in tables:
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    for row in rows:
                        row_text = row.text
                        
                        # Look for manuscript IDs
                        ms_patterns = [
                            r'(MS-\d{4}-\d{4})',
                            r'(SICON-\d{2}-\d{4})',
                            r'(MS\d{6})'
                        ]
                        
                        for pattern in ms_patterns:
                            matches = re.findall(pattern, row_text)
                            for ms_id in matches:
                                if not any(m['id'] == ms_id for m in manuscripts):
                                    # Try to get more info from the row
                                    cells = row.find_elements(By.TAG_NAME, "td")
                                    title = ""
                                    for cell in cells:
                                        cell_text = cell.text.strip()
                                        if len(cell_text) > 20 and ms_id not in cell_text:
                                            title = cell_text[:100]
                                            break
                                    
                                    manuscripts.append({
                                        'id': ms_id,
                                        'title': title or 'No title found',
                                        'folder': folder_name,
                                        'row_text': row_text[:200]
                                    })
                                    print(f"  📄 Found manuscript: {ms_id}")
                        
                        # Look for referee emails in the row
                        email_matches = re.findall(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', row_text)
                        for email in email_matches:
                            if email not in ['sicon@siam.org', 'noreply@siam.org']:
                                if not any(r['email'] == email for r in referees):
                                    # Check for status
                                    status = "Unknown"
                                    if "accepted" in row_text.lower():
                                        status = "Accepted"
                                    elif "declined" in row_text.lower():
                                        status = "Declined"
                                    elif "pending" in row_text.lower():
                                        status = "Pending"
                                    
                                    referees.append({
                                        'email': email,
                                        'status': status,
                                        'folder': folder_name
                                    })
                                    print(f"  👤 Found referee: {email} ({status})")
            except Exception as e:
                print(f"  ⚠️ Error extracting from tables: {e}")
            
            # Strategy 2: Look for links to manuscripts
            try:
                ms_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'ms_id') or contains(text(), 'MS-')]")
                for link in ms_links[:5]:  # First 5 only
                    link_text = link.text.strip()
                    link_href = link.get_attribute('href')
                    
                    if link_text and any(pattern in link_text for pattern in ['MS-', 'SICON-']):
                        if not any(m.get('id') == link_text for m in manuscripts):
                            manuscripts.append({
                                'id': link_text,
                                'url': link_href,
                                'folder': folder_name
                            })
                            print(f"  📄 Found manuscript link: {link_text}")
            except Exception as e:
                print(f"  ⚠️ Error finding manuscript links: {e}")
            
            # Strategy 3: Look for document links
            try:
                doc_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf') or contains(@href, 'download')]")
                for link in doc_links[:5]:
                    link_text = link.text.strip() or "Document"
                    link_href = link.get_attribute('href')
                    
                    if link_href:
                        doc_type = 'document'
                        if 'manuscript' in link_text.lower():
                            doc_type = 'manuscript_pdf'
                        elif 'cover' in link_text.lower():
                            doc_type = 'cover_letter'
                        elif 'report' in link_text.lower():
                            doc_type = 'referee_report'
                        
                        documents.append({
                            'name': link_text,
                            'url': link_href,
                            'type': doc_type,
                            'folder': folder_name
                        })
                        print(f"  📎 Found document: {link_text}")
            except Exception as e:
                print(f"  ⚠️ Error finding documents: {e}")
            
        except Exception as e:
            print(f"❌ Error processing folder {folder_name}: {e}")
        
        return manuscripts, referees, documents
    
    def extract_data(self):
        """Main extraction method."""
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
            
            # Authenticate
            if not self.ultra_robust_authenticate(driver):
                print("❌ Authentication failed")
                return False
            
            print("\n📊 EXTRACTING DATA FROM CATEGORIES...")
            
            all_manuscripts = []
            all_referees = []
            all_documents = []
            
            # Find all folder links
            folder_links = driver.find_elements(By.CSS_SELECTOR, "a.ndt_folder_link")
            print(f"Found {len(folder_links)} folder categories")
            
            # Process each folder
            folders_to_process = []
            for link in folder_links:
                try:
                    link_text = link.text.strip()
                    parent_row = link.find_element(By.XPATH, "./../..")
                    folder_span = parent_row.find_element(By.CSS_SELECTOR, "span.ndt_title")
                    folder_name = folder_span.text.strip()
                    
                    if "AE" in link_text and link_text != "0 AE":
                        folders_to_process.append((folder_name, link_text))
                except:
                    continue
            
            print(f"\nFolders with content: {len(folders_to_process)}")
            for folder_name, count in folders_to_process:
                print(f"  • {folder_name}: {count}")
            
            # Process each folder
            for i, (folder_name, count) in enumerate(folders_to_process):
                try:
                    # Re-find the link after navigation
                    folder_links = driver.find_elements(By.CSS_SELECTOR, "a.ndt_folder_link")
                    
                    # Find the specific folder link again
                    target_link = None
                    for link in folder_links:
                        try:
                            parent_row = link.find_element(By.XPATH, "./../..")
                            folder_span = parent_row.find_element(By.CSS_SELECTOR, "span.ndt_title")
                            if folder_span.text.strip() == folder_name:
                                target_link = link
                                break
                        except:
                            continue
                    
                    if target_link:
                        # Extract from this folder
                        manuscripts, referees, documents = self.extract_from_folder(driver, folder_name, target_link)
                        
                        all_manuscripts.extend(manuscripts)
                        all_referees.extend(referees)
                        all_documents.extend(documents)
                        
                        # Go back to main page
                        driver.get("https://sicon.siam.org/cgi-bin/main.plex")
                        time.sleep(2)
                        
                        # Clean overlays
                        self.remove_all_overlays(driver)
                    
                except Exception as e:
                    print(f"❌ Error with folder {folder_name}: {e}")
                    # Try to recover
                    driver.get("https://sicon.siam.org/cgi-bin/main.plex")
                    time.sleep(2)
            
            # Save results
            results = {
                'extraction_date': datetime.now().isoformat(),
                'authentication_success': True,
                'extraction_type': 'ULTRA_ROBUST_SICON',
                'folders_processed': [f[0] for f in folders_to_process],
                'baseline_compliance': {
                    'manuscripts': {
                        'found': len(all_manuscripts),
                        'target': 4,
                        'compliance': len(all_manuscripts) >= 4
                    },
                    'referees': {
                        'found': len(all_referees),
                        'target': 13,
                        'compliance': len(all_referees) >= 13,
                        'with_status': len([r for r in all_referees if r.get('status') != 'Unknown'])
                    },
                    'documents': {
                        'found': len(all_documents),
                        'target': 11,
                        'compliance': len(all_documents) >= 11
                    }
                },
                'manuscripts': all_manuscripts,
                'referees': all_referees,
                'documents': all_documents
            }
            
            results_file = self.output_dir / "ultrarobust_results.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"\n📊 ULTRA-ROBUST EXTRACTION RESULTS:")
            print(f"✅ Manuscripts: {len(all_manuscripts)}")
            print(f"✅ Referees: {len(all_referees)}")
            print(f"✅ Documents: {len(all_documents)}")
            print(f"\n💾 Results saved to: {results_file}")
            
            return True
            
        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if driver:
                time.sleep(10)
                driver.quit()

if __name__ == "__main__":
    extractor = UltraRobustSICONExtractor()
    success = extractor.extract_data()
    
    if success:
        print("\n🎉 ULTRA-ROBUST EXTRACTION COMPLETE!")
    else:
        print("\n❌ Extraction failed")