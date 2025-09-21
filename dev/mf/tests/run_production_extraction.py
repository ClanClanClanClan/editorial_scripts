#!/usr/bin/env python3
"""Production extraction script to bypass test mode detection."""

# Temporarily disable cache system import to avoid test mode
import os
import sys
import time
import json
import re
import requests
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import traceback
from typing import Optional, Callable

# Enhanced credential loading
sys.path.append(str(Path(__file__).parent.parent))
try:
    from ensure_credentials import load_credentials
    load_credentials()
    print("✅ Credentials loaded from keychain")
except:
    print("⚠️ Secure credential system not available, using environment variables...")

# Simple extractor class without caching to avoid test mode
class SimpleComprehensiveMFExtractor:
    """Simplified MF extractor without caching system."""
    
    def __init__(self):
        self.manuscripts = []
        self.project_root = Path(__file__).parent.parent.parent.parent
        
        # Browser setup
        chrome_options = Options()
        if os.environ.get('EXTRACTOR_HEADLESS', 'true').lower() == 'true':
            chrome_options.add_argument('--headless')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1200,800')
        
        # Download settings
        download_dir = str(self.project_root / "downloads")
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        print(f"🚀 PRODUCTION MF EXTRACTION STARTING")
        
    def login(self):
        """Login to MF system."""
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                print(f"🔐 Login attempt {attempt}/{max_attempts}...")
                self.driver.get('https://mc.manuscriptcentral.com/mafi')
                time.sleep(5)  # Give more time for page to load
                
                # Save page for debugging
                with open(f'debug_login_page_{attempt}.html', 'w') as f:
                    f.write(self.driver.page_source)
                
                # Check for maintenance message
                if 'maintenance' in self.driver.page_source.lower():
                    print("⚠️ Site appears to be under maintenance")
                    return False
                
                # Try different selectors for login form
                username_field = None
                password_field = None
                
                # Try NAME selector first
                try:
                    username_field = self.driver.find_element(By.NAME, 'USER')
                    password_field = self.driver.find_element(By.NAME, 'PASSWORD')
                except:
                    # Try ID selector
                    try:
                        username_field = self.driver.find_element(By.ID, 'USERID')
                        password_field = self.driver.find_element(By.ID, 'PASSWORD')
                    except:
                        # Try class selector
                        username_field = self.driver.find_element(By.CSS_SELECTOR, 'input[type="text"]')
                        password_field = self.driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')
            
                username = os.environ.get('MF_EMAIL')
                password = os.environ.get('MF_PASSWORD') 
                
                if not username or not password:
                    print("❌ Credentials not found in environment")
                    return False
                    
                username_field.send_keys(username)
                password_field.send_keys(password)
                
                # Submit form - try different methods
                try:
                    submit_button = self.driver.find_element(By.XPATH, "//input[@type='submit']")
                    submit_button.click()
                except:
                    try:
                        submit_button = self.driver.find_element(By.NAME, "login")
                        submit_button.click()
                    except:
                        # Try pressing Enter in password field
                        password_field.send_keys(Keys.RETURN)
                
                time.sleep(5)
                
                # Check if login was successful
                if "Associate Editor Center" in self.driver.page_source:
                    print("✅ Login successful")
                    return True
                else:
                    print(f"❌ Login failed on attempt {attempt}")
                    if attempt < max_attempts:
                        time.sleep(3)
                        continue
                    
            except Exception as e:
                print(f"❌ Login error on attempt {attempt}: {e}")
                if attempt < max_attempts:
                    time.sleep(3)
                    continue
        
        return False
            
    def get_email_from_popup_safe(self, link):
        """Extract email from popup - working version."""
        try:
            original_window = self.driver.current_window_handle
            
            # Click the link to open popup
            self.driver.execute_script("arguments[0].click();", link)
            time.sleep(2)
            
            # Switch to popup window
            popup_window = None
            for window in self.driver.window_handles:
                if window != original_window:
                    popup_window = window
                    break
            
            if popup_window:
                self.driver.switch_to.window(popup_window)
                time.sleep(2)
                
                # Check frames for email content
                frames = self.driver.find_elements(By.TAG_NAME, 'frame')
                if not frames:
                    frames = self.driver.find_elements(By.TAG_NAME, 'iframe')
                
                email = ""
                for i, frame in enumerate(frames):
                    try:
                        self.driver.switch_to.frame(frame)
                        frame_source = self.driver.page_source
                        
                        # Look for email patterns in frame content
                        import re
                        email_pattern = r'\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b'
                        found_emails = re.findall(email_pattern, frame_source)
                        
                        if found_emails:
                            # Filter out editor emails
                            referee_emails = [e for e in found_emails if 'dylan.possamai' not in e and 'math.ethz.ch' not in e]
                            if referee_emails:
                                email = referee_emails[0]
                                break
                        
                        self.driver.switch_to.window(popup_window)
                    except:
                        continue
                
                # Close popup and return to main window
                self.driver.close()
                self.driver.switch_to.window(original_window)
                time.sleep(1)
                
                return email
            
        except Exception as e:
            try:
                self.driver.switch_to.window(original_window)
            except:
                pass
            
        return ""
    
    def extract_all(self):
        """Extract from all manuscripts."""
        if not self.login():
            return
        
        # Navigate to AE Center
        ae_link = self.driver.find_element(By.LINK_TEXT, 'Associate Editor Center')
        ae_link.click()
        time.sleep(3)
        
        # Get categories
        categories = self.get_manuscript_categories()
        
        for cat in categories:
            if cat['count'] > 0:
                print(f"\\n📂 Processing: {cat['name']} ({cat['count']} manuscripts)")
                self.process_category(cat)
        
        print(f"\\n📊 FINAL RESULTS: {len(self.manuscripts)} manuscripts extracted")
        
    def get_manuscript_categories(self):
        """Get manuscript categories."""
        categories = []
        
        try:
            # Find category links
            links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'AUTHOR_SUBMIT_CHECK')]")
            
            for link in links:
                text = link.text.strip()
                if '(' in text and ')' in text:
                    # Extract category name and count
                    name_part = text[:text.rfind('(')].strip()
                    count_part = text[text.rfind('(')+1:text.rfind(')')].strip()
                    
                    try:
                        count = int(count_part)
                        categories.append({'name': name_part, 'count': count, 'link': link})
                    except:
                        continue
                        
        except Exception as e:
            print(f"❌ Error getting categories: {e}")
            
        return categories
    
    def process_category(self, category):
        """Process manuscripts in a category."""
        try:
            # Click category
            category['link'].click()
            time.sleep(3)
            
            # Get manuscript links
            manuscript_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS')]")
            
            for i, ms_link in enumerate(manuscript_links):
                try:
                    print(f"   📄 Processing manuscript {i+1}/{len(manuscript_links)}...")
                    
                    # Click manuscript
                    ms_link.click()
                    time.sleep(5)
                    
                    # Extract manuscript data
                    manuscript = self.extract_manuscript_data()
                    if manuscript:
                        self.manuscripts.append(manuscript)
                    
                    # Go back to category
                    self.driver.back()
                    time.sleep(3)
                    
                except Exception as e:
                    print(f"   ❌ Error processing manuscript: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Error processing category: {e}")
    
    def extract_manuscript_data(self):
        """Extract data from manuscript page."""
        try:
            manuscript = {}
            
            # Get ID from URL
            url = self.driver.current_url
            if 'MANUSCRIPT_ID=' in url:
                manuscript['id'] = url.split('MANUSCRIPT_ID=')[1].split('&')[0]
            
            # Extract title
            try:
                title_elements = self.driver.find_elements(By.XPATH, "//td[contains(text(), 'Title:')]/following-sibling::td")
                if title_elements:
                    manuscript['title'] = title_elements[0].text.strip()
            except:
                pass
            
            # Extract referees
            manuscript['referees'] = self.extract_referees()
            manuscript['authors'] = self.extract_authors()
            
            return manuscript
            
        except Exception as e:
            print(f"❌ Error extracting manuscript data: {e}")
            return None
    
    def extract_referees(self):
        """Extract referee information."""
        referees = []
        
        try:
            # Find referee rows using ORDER selector
            referee_rows = self.driver.find_elements(By.XPATH, "//select[contains(@name, 'ORDER')]/ancestor::tr[1]")
            
            for row in referee_rows:
                try:
                    cells = row.find_elements(By.XPATH, ".//td[@class='tablelightcolor']")
                    if len(cells) > 1:
                        name_cell = cells[1]
                        name_links = name_cell.find_elements(By.XPATH, './/a')
                        
                        referee = {'name': '', 'email': ''}
                        
                        for link in name_links:
                            link_text = link.text.strip()
                            if link_text and ',' in link_text:
                                referee['name'] = link_text
                            
                            href = link.get_attribute('href') or ''
                            onclick = link.get_attribute('onclick') or ''
                            
                            # Check for email popup
                            if 'mailpopup' in href or 'mailpopup' in onclick:
                                email = self.get_email_from_popup_safe(link)
                                if email:
                                    referee['email'] = email
                                break
                        
                        if referee['name']:
                            referees.append(referee)
                            
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"❌ Error extracting referees: {e}")
            
        return referees
    
    def extract_authors(self):
        """Extract author information."""
        authors = []
        
        try:
            # Find author links
            author_links = self.driver.find_elements(By.XPATH, "//td[contains(text(), 'Author')]/following-sibling::td//a")
            
            for link in author_links:
                try:
                    name = link.text.strip()
                    if name and len(name) > 3:
                        author = {'name': name, 'email': ''}
                        
                        # Check for email popup
                        href = link.get_attribute('href') or ''
                        if 'mailpopup' in href:
                            email = self.get_email_from_popup_safe(link)
                            if email:
                                author['email'] = email
                        
                        authors.append(author)
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"❌ Error extracting authors: {e}")
            
        return authors
    
    def save_results(self):
        """Save extraction results."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'mf_production_extraction_{timestamp}.json'
        
        with open(filename, 'w') as f:
            json.dump(self.manuscripts, f, indent=2, default=str)
        
        print(f"💾 Results saved to: {filename}")
        
    def cleanup(self):
        """Clean up browser."""
        try:
            self.driver.quit()
        except:
            pass

# Run the extraction
print('🚀 COMPLETE MF EXTRACTION - PRODUCTION MODE')
print('=' * 70)

extractor = SimpleComprehensiveMFExtractor()

try:
    extractor.extract_all()
    
    if extractor.manuscripts:
        print(f'\\n📊 COMPLETE EXTRACTION RESULTS:')
        print('=' * 70)
        print(f'TOTAL MANUSCRIPTS EXTRACTED: {len(extractor.manuscripts)}')
        
        total_referees = sum(len(ms.get('referees', [])) for ms in extractor.manuscripts)
        total_referee_emails = sum(sum(1 for r in ms.get('referees', []) if r.get('email')) for ms in extractor.manuscripts)
        total_authors = sum(len(ms.get('authors', [])) for ms in extractor.manuscripts) 
        total_author_emails = sum(sum(1 for a in ms.get('authors', []) if a.get('email')) for ms in extractor.manuscripts)
        
        print(f'\\n📊 OVERALL SUMMARY:')
        print(f'🧑‍⚖️ Total referees: {total_referees}')
        print(f'📧 Referee emails extracted: {total_referee_emails}/{total_referees} ({100*total_referee_emails/total_referees if total_referees > 0 else 0:.1f}%)')
        print(f'✍️ Total authors: {total_authors}')
        print(f'📧 Author emails extracted: {total_author_emails}/{total_authors} ({100*total_author_emails/total_authors if total_authors > 0 else 0:.1f}%)')
        print(f'📧 TOTAL EMAILS EXTRACTED: {total_referee_emails + total_author_emails}')
        
        # Show detailed results for each manuscript
        for i, ms in enumerate(extractor.manuscripts):
            print(f'\\n📄 MANUSCRIPT {i+1}: {ms.get("id", "NO_ID")}')
            print(f'📝 Title: {ms.get("title", "N/A")}')
            
            referees = ms.get('referees', [])
            referee_emails = sum(1 for r in referees if r.get('email'))
            print(f'🧑‍⚖️ Referees: {len(referees)} total, {referee_emails} with emails')
            
            for j, r in enumerate(referees):
                name = r.get('name', 'Unknown')
                email = r.get('email', '')
                status = '✅' if email else '❌'
                print(f'  {j+1}. {status} {name}: {email or "NO EMAIL"}')
            
            authors = ms.get('authors', [])
            author_emails = sum(1 for a in authors if a.get('email'))
            print(f'✍️ Authors: {len(authors)} total, {author_emails} with emails')
            
            for j, a in enumerate(authors):
                name = a.get('name', 'Unknown')
                email = a.get('email', '')
                status = '✅' if email else '❌'
                print(f'  {j+1}. {status} {name}: {email or "NO EMAIL"}')
        
        extractor.save_results()
        
        if total_referee_emails > 0:
            print('\\n🎉 SUCCESS: REFEREE EMAIL EXTRACTION IS WORKING!')
        else:
            print('\\n❌ WARNING: NO REFEREE EMAILS EXTRACTED')
    else:
        print('❌ NO MANUSCRIPTS EXTRACTED')
        
except Exception as e:
    print(f'❌ ERROR: {e}')
    import traceback
    traceback.print_exc()
finally:
    extractor.cleanup()
    print(f'\\nExtraction completed at: {datetime.now().strftime("%H:%M:%S")}')