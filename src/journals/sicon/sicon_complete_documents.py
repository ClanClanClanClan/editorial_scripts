#!/usr/bin/env python3
"""
SICON Complete Document Extractor - Downloads ALL documents including reports and cover letters
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
from bs4 import BeautifulSoup, NavigableString
from dotenv import load_dotenv

load_dotenv()


class SICONCompleteDocumentExtractor:
    """SICON extractor that downloads ALL available documents."""
    
    def __init__(self):
        self.output_dir = Path(f'./sicon_complete_docs_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.dirs = {
            'pdfs': self.output_dir / 'pdfs',
            'cover_letters': self.output_dir / 'cover_letters',
            'reports': self.output_dir / 'reports',
            'attachments': self.output_dir / 'attachments',
            'data': self.output_dir / 'data',
            'debug': self.output_dir / 'debug'
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(exist_ok=True)
        
        self.main_window = None
        self.manuscripts = []
        
        print(f"📁 Output directory: {self.output_dir}")
    
    def setup_driver(self):
        """Setup Chrome driver with stealth settings for headless mode."""
        chrome_options = Options()
        
        # Stealth settings
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Headless mode
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # Other settings
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Configure downloads
        self.temp_download = self.output_dir / 'temp_downloads'
        self.temp_download.mkdir(exist_ok=True)
        
        prefs = {
            "download.default_directory": str(self.temp_download),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": False
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)
        
        # Execute stealth JavaScript
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Enable downloads
        self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": str(self.temp_download)
        })
        
        print("✅ Chrome driver initialized (HEADLESS MODE)")
    
    def wait_for_page_load(self):
        """Wait for page to fully load."""
        time.sleep(3)
        try:
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(2)
            
            if "Just a moment" in self.driver.title:
                print("⏳ Cloudflare challenge detected, waiting...")
                time.sleep(10)
        except:
            pass
    
    def authenticate(self) -> bool:
        """Authenticate using ORCID."""
        print("\n🔐 Authenticating...")
        
        try:
            self.driver.get("http://sicon.siam.org")
            self.wait_for_page_load()
            self.main_window = self.driver.current_window_handle
            
            if 'associate editor tasks' in self.driver.page_source.lower():
                print("✅ Already authenticated!")
                return True
            
            # Privacy notification
            try:
                privacy_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@value='Continue']"))
                )
                privacy_button.click()
                print("✅ Clicked privacy notification")
                time.sleep(3)
            except:
                pass
            
            # ORCID link
            orcid_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'orcid')]")
            self.driver.execute_script("arguments[0].click();", orcid_link)
            print("✅ Clicked ORCID link")
            time.sleep(5)
            
            # ORCID authentication
            if 'orcid.org' in self.driver.current_url:
                print("📝 On ORCID page")
                
                try:
                    accept_cookies = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept All Cookies')]"))
                    )
                    accept_cookies.click()
                    print("✅ Accepted cookies")
                    time.sleep(3)
                except:
                    pass
                
                username = os.getenv('ORCID_USER', '0000-0002-9364-0124')
                password = os.getenv('ORCID_PASS', 'Hioupy0042%')
                
                username_field = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Email or 16-digit ORCID iD']"))
                )
                password_field = self.driver.find_element(By.XPATH, "//input[@placeholder='Your ORCID password']")
                
                username_field.clear()
                username_field.send_keys(username)
                password_field.clear()
                password_field.send_keys(password)
                
                signin_button = self.driver.find_element(By.XPATH, "//button[contains(., 'Sign in to ORCID')]")
                signin_button.click()
                print("✅ Clicked sign in")
                
                time.sleep(10)
            
            # Post-auth privacy
            try:
                privacy_button = self.driver.find_element(By.XPATH, "//input[@value='Continue']")
                privacy_button.click()
                print("✅ Clicked post-auth privacy")
                time.sleep(3)
            except:
                pass
            
            if 'associate editor tasks' in self.driver.page_source.lower():
                print("✅ Authentication successful!")
                return True
            else:
                print("❌ Authentication failed")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def navigate_to_manuscripts(self) -> bool:
        """Navigate to All Pending Manuscripts."""
        print("\n📋 Navigating to manuscripts...")
        
        try:
            ae_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'folder_id=1800')]")
            self.driver.execute_script("arguments[0].click();", ae_link)
            time.sleep(5)
            
            if 'All Pending Manuscripts' in self.driver.page_source:
                print("✅ Reached manuscripts table")
                return True
            else:
                print("❌ Failed to reach manuscripts table")
                return False
                
        except Exception as e:
            print(f"❌ Navigation error: {e}")
            return False
    
    def parse_status_from_text(self, text: str) -> str:
        """Parse a single status from text."""
        text_lower = text.lower().strip()
        
        if 'declined' in text_lower:
            return 'Declined'
        elif 'accepted' in text_lower:
            return 'Accepted'
        elif 'report' in text_lower and 'submitted' in text_lower:
            return 'Report Submitted'
        elif 'overdue' in text_lower:
            return 'Overdue'
        elif 'invited' in text_lower or 'pending' in text_lower:
            return 'Invited'
        else:
            return 'Unknown'
    
    def split_status_text(self, cell_content):
        """Split the status cell content into individual statuses."""
        statuses = []
        
        if hasattr(cell_content, 'contents'):
            current_text = ""
            for element in cell_content.contents:
                if isinstance(element, NavigableString):
                    current_text += str(element).strip()
                elif element.name == 'br':
                    if current_text:
                        statuses.append(current_text)
                        current_text = ""
            if current_text:
                statuses.append(current_text)
        else:
            text = str(cell_content)
            parts = re.findall(r'(?:Accepted|Declined|Invited|Overdue|Report\s+Submitted)', text, re.IGNORECASE)
            statuses = parts if parts else [text]
        
        return statuses
    
    def parse_manuscripts_table(self):
        """Parse manuscripts table."""
        print("\n📊 Parsing manuscripts table...")
        
        with open(self.dirs['debug'] / 'manuscripts_table.html', 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        tables = soup.find_all('table')
        data_table = None
        
        for table in tables:
            if re.search(r'M\d{6}', str(table)):
                data_table = table
                break
        
        if not data_table:
            print("❌ Could not find manuscripts table")
            return
        
        print("✅ Found manuscripts table")
        
        rows = data_table.find_all('tr')
        
        for row in rows:
            if not re.search(r'M\d{6}', str(row)):
                continue
            
            cells = row.find_all('td')
            if len(cells) < 8:
                continue
            
            ms_id_match = re.search(r'(M\d{6})', cells[0].get_text())
            if not ms_id_match:
                continue
            
            ms_id = ms_id_match.group(1)
            print(f"\n🔍 Processing manuscript {ms_id}")
            
            manuscript = {
                'manuscript_id': ms_id,
                'title': cells[1].get_text(strip=True),
                'corresponding_editor': cells[2].get_text(strip=True),
                'associate_editor': cells[3].get_text(strip=True),
                'submitted': cells[4].get_text(strip=True),
                'days_in_system': cells[5].get_text(strip=True),
                'referees': [],
                'pdf_downloaded': False,
                'cover_letter_downloaded': False,
                'reports_downloaded': [],
                'attachments_downloaded': []
            }
            
            # Extract referee names
            referee_links = cells[6].find_all('a')
            referee_names = []
            
            for link in referee_links:
                name = link.get_text(strip=True)
                if name and name not in ['s Assigned', 'All Referees']:
                    link_html = str(link)
                    if 'biblio_dump' in link_html:
                        referee_names.append(name)
            
            # Extract statuses
            status_cell = cells[7]
            status_list = self.split_status_text(status_cell)
            
            # Extract due dates
            due_dates = []
            if len(cells) > 8:
                due_cell = cells[8]
                due_parts = []
                
                if hasattr(due_cell, 'contents'):
                    current_text = ""
                    for element in due_cell.contents:
                        if isinstance(element, NavigableString):
                            text = str(element).strip()
                            if text and text != '&nbsp;':
                                current_text = text
                        elif element.name == 'br':
                            due_parts.append(current_text if current_text else None)
                            current_text = ""
                    if len(due_parts) < len(referee_names):
                        due_parts.append(current_text if current_text else None)
                
                due_dates = due_parts
            
            # Extract invited dates
            invited_dates = []
            if len(cells) > 9:
                invited_cell = cells[9]
                invited_parts = []
                
                if hasattr(invited_cell, 'contents'):
                    current_text = ""
                    for element in invited_cell.contents:
                        if isinstance(element, NavigableString):
                            text = str(element).strip()
                            if text and text != '&nbsp;':
                                current_text = text
                        elif element.name == 'br':
                            invited_parts.append(current_text if current_text else None)
                            current_text = ""
                    if len(invited_parts) < len(referee_names):
                        invited_parts.append(current_text if current_text else None)
                
                invited_dates = invited_parts
            
            # Match referees with data
            for i, name in enumerate(referee_names):
                status = self.parse_status_from_text(status_list[i]) if i < len(status_list) else 'Unknown'
                due_date = due_dates[i] if i < len(due_dates) else None
                invited_date = invited_dates[i] if i < len(invited_dates) else None
                
                # Check for report submitted
                report_available = False
                if status == 'Accepted' and due_date:
                    # Check if report was submitted (look for "Rcvd" in the row)
                    if 'Rcvd' in str(row) and name in str(row):
                        report_available = True
                        status = 'Report Submitted'
                
                referee = {
                    'name': name,
                    'email': None,
                    'full_name': name,
                    'status': status,
                    'due_date': due_date,
                    'invited_date': invited_date,
                    'report_available': report_available
                }
                
                print(f"  👤 {name}: {status}", end="")
                if due_date:
                    print(f" (due: {due_date})", end="")
                if invited_date:
                    print(f" (invited: {invited_date})", end="")
                if report_available:
                    print(" [Report Available]", end="")
                print()
                
                manuscript['referees'].append(referee)
            
            self.manuscripts.append(manuscript)
    
    def extract_referee_emails(self):
        """Extract referee emails."""
        print("\n📧 Extracting referee emails...")
        
        emails_found = 0
        for manuscript in self.manuscripts:
            for referee in manuscript['referees']:
                if referee['email']:
                    continue
                
                try:
                    referee_links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{referee['name']}')]")
                    
                    if not referee_links:
                        continue
                    
                    self.driver.execute_script("arguments[0].click();", referee_links[0])
                    time.sleep(3)
                    
                    if len(self.driver.window_handles) > 1:
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                        time.sleep(2)
                        
                        profile_html = self.driver.page_source
                        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', profile_html)
                        if email_match:
                            referee['email'] = email_match.group()
                            emails_found += 1
                        
                        soup = BeautifulSoup(profile_html, 'html.parser')
                        title_tag = soup.find('title')
                        if title_tag and title_tag.text:
                            full_name = title_tag.text.strip()
                            if full_name and len(full_name) > len(referee['name']):
                                referee['full_name'] = full_name
                        
                        self.driver.close()
                        self.driver.switch_to.window(self.main_window)
                        time.sleep(1)
                    
                except Exception as e:
                    if len(self.driver.window_handles) > 1:
                        self.driver.close()
                        self.driver.switch_to.window(self.main_window)
        
        print(f"  ✅ Found {emails_found} email addresses")
    
    def wait_for_download(self, timeout=30):
        """Wait for a download to complete."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if any partial downloads exist
            partial_files = list(self.temp_download.glob('*.crdownload')) + \
                           list(self.temp_download.glob('*.part')) + \
                           list(self.temp_download.glob('*.download'))
            
            if not partial_files:
                # No partial files, download might be complete
                time.sleep(1)
                return True
            
            time.sleep(0.5)
        
        return False
    
    def download_all_documents(self):
        """Download ALL documents: PDFs, cover letters, referee reports, and attachments."""
        print("\n📥 Downloading ALL documents...")
        
        for manuscript in self.manuscripts:
            ms_id = manuscript['manuscript_id']
            print(f"\n📄 Downloading documents for {ms_id}...")
            
            try:
                # Clear temp download folder
                for f in self.temp_download.glob('*'):
                    f.unlink()
                
                # Find and click manuscript link
                ms_link = self.driver.find_element(By.XPATH, f"//a[contains(text(), '{ms_id}')]")
                self.driver.execute_script("arguments[0].click();", ms_link)
                time.sleep(3)
                
                # Check if new window opened
                if len(self.driver.window_handles) > 1:
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    time.sleep(2)
                    
                    # Save page for debugging
                    debug_file = self.dirs['debug'] / f"{ms_id}_view_page.html"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    
                    # Parse page with BeautifulSoup
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    
                    # 1. Download main manuscript PDF
                    pdf_patterns = [
                        "//a[contains(text(), 'PDF')]",
                        "//a[contains(text(), 'Download PDF')]",
                        "//a[contains(@href, '.pdf') and contains(@href, 'ms_id')]",
                        "//a[contains(@href, 'view_ms_obj') and contains(@href, 'pdf')]"
                    ]
                    
                    for pattern in pdf_patterns:
                        if manuscript['pdf_downloaded']:
                            break
                        try:
                            pdf_links = self.driver.find_elements(By.XPATH, pattern)
                            for link in pdf_links:
                                link_text = link.text.lower()
                                # Skip referee reports in this section
                                if 'referee' in link_text or 'review' in link_text:
                                    continue
                                
                                initial_files = set(self.temp_download.glob('*'))
                                self.driver.execute_script("arguments[0].click();", link)
                                
                                if self.wait_for_download():
                                    new_files = set(self.temp_download.glob('*')) - initial_files
                                    if new_files:
                                        for new_file in new_files:
                                            with open(new_file, 'rb') as f:
                                                header = f.read(4)
                                            
                                            if header == b'%PDF':
                                                dest = self.dirs['pdfs'] / f"{ms_id}.pdf"
                                                shutil.move(str(new_file), str(dest))
                                                manuscript['pdf_downloaded'] = True
                                                print(f"  ✅ Main PDF downloaded")
                                                break
                                
                                if manuscript['pdf_downloaded']:
                                    break
                        except:
                            continue
                    
                    # 2. Look for cover letter
                    cover_patterns = [
                        "cover letter",
                        "author.*letter",
                        "submission.*letter",
                        "accompanying.*letter"
                    ]
                    
                    for pattern in cover_patterns:
                        if manuscript['cover_letter_downloaded']:
                            break
                        
                        # Search in page text
                        links = soup.find_all('a', text=re.compile(pattern, re.I))
                        for link in links:
                            href = link.get('href', '')
                            if 'pdf' in href or 'download' in href:
                                try:
                                    selenium_link = self.driver.find_element(By.XPATH, f"//a[@href='{href}']")
                                    initial_files = set(self.temp_download.glob('*'))
                                    self.driver.execute_script("arguments[0].click();", selenium_link)
                                    
                                    if self.wait_for_download():
                                        new_files = set(self.temp_download.glob('*')) - initial_files
                                        if new_files:
                                            for new_file in new_files:
                                                dest = self.dirs['cover_letters'] / f"{ms_id}_cover_letter{new_file.suffix}"
                                                shutil.move(str(new_file), str(dest))
                                                manuscript['cover_letter_downloaded'] = True
                                                print(f"  ✅ Cover letter downloaded")
                                                break
                                except:
                                    continue
                    
                    # 3. Look for referee reports
                    report_count = 0
                    
                    # First, check for "display_all_reviews" link
                    review_link = soup.find('a', href=re.compile('display_all_reviews'))
                    if review_link:
                        try:
                            href = review_link.get('href')
                            self.driver.get(f"http://sicon.siam.org/{href}")
                            time.sleep(3)
                            
                            # Parse the reviews page
                            reviews_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                            
                            # Look for review attachments
                            review_links = reviews_soup.find_all('a', text=re.compile('Review Attachment|Referee.*Report|reviewer_attachment', re.I))
                            
                            for r_link in review_links:
                                r_href = r_link.get('href', '')
                                if '.pdf' in r_href:
                                    try:
                                        initial_files = set(self.temp_download.glob('*'))
                                        self.driver.get(f"http://sicon.siam.org/{r_href}")
                                        
                                        if self.wait_for_download():
                                            new_files = set(self.temp_download.glob('*')) - initial_files
                                            if new_files:
                                                for new_file in new_files:
                                                    report_count += 1
                                                    dest = self.dirs['reports'] / f"{ms_id}_referee_report_{report_count}{new_file.suffix}"
                                                    shutil.move(str(new_file), str(dest))
                                                    manuscript['reports_downloaded'].append({
                                                        'filename': dest.name,
                                                        'referee': 'Unknown'
                                                    })
                                                    print(f"  ✅ Referee report {report_count} downloaded")
                                    except:
                                        continue
                            
                            # Go back to manuscript page
                            self.driver.back()
                            time.sleep(2)
                            
                        except Exception as e:
                            print(f"    ⚠️ Error accessing reviews: {e}")
                    
                    # Also look for individual report links on main page
                    report_patterns = [
                        "Referee.*Review.*Attachment",
                        "Review.*Attachment",
                        "reviewer_attachment",
                        "Referee.*Report"
                    ]
                    
                    for pattern in report_patterns:
                        report_links = soup.find_all('a', text=re.compile(pattern, re.I))
                        for link in report_links:
                            href = link.get('href', '')
                            if 'pdf' in href:
                                try:
                                    selenium_link = self.driver.find_element(By.XPATH, f"//a[@href='{href}']")
                                    initial_files = set(self.temp_download.glob('*'))
                                    self.driver.execute_script("arguments[0].click();", selenium_link)
                                    
                                    if self.wait_for_download():
                                        new_files = set(self.temp_download.glob('*')) - initial_files
                                        if new_files:
                                            for new_file in new_files:
                                                report_count += 1
                                                
                                                # Try to identify which referee
                                                link_text = link.get_text()
                                                referee_name = "Unknown"
                                                for ref in manuscript['referees']:
                                                    if ref['name'] in link_text:
                                                        referee_name = ref['name']
                                                        break
                                                
                                                dest = self.dirs['reports'] / f"{ms_id}_referee_report_{report_count}_{referee_name}{new_file.suffix}"
                                                shutil.move(str(new_file), str(dest))
                                                manuscript['reports_downloaded'].append({
                                                    'filename': dest.name,
                                                    'referee': referee_name
                                                })
                                                print(f"  ✅ Referee report from {referee_name} downloaded")
                                except:
                                    continue
                    
                    # 4. Look for other attachments
                    attachment_patterns = [
                        "Supplementary",
                        "Supporting.*Material",
                        "Additional.*File",
                        "Attachment"
                    ]
                    
                    attachment_count = 0
                    for pattern in attachment_patterns:
                        att_links = soup.find_all('a', text=re.compile(pattern, re.I))
                        for link in att_links:
                            href = link.get('href', '')
                            if 'pdf' in href or 'download' in href:
                                try:
                                    selenium_link = self.driver.find_element(By.XPATH, f"//a[@href='{href}']")
                                    initial_files = set(self.temp_download.glob('*'))
                                    self.driver.execute_script("arguments[0].click();", selenium_link)
                                    
                                    if self.wait_for_download():
                                        new_files = set(self.temp_download.glob('*')) - initial_files
                                        if new_files:
                                            for new_file in new_files:
                                                attachment_count += 1
                                                dest = self.dirs['attachments'] / f"{ms_id}_attachment_{attachment_count}{new_file.suffix}"
                                                shutil.move(str(new_file), str(dest))
                                                manuscript['attachments_downloaded'].append({
                                                    'filename': dest.name,
                                                    'type': link.get_text()
                                                })
                                                print(f"  ✅ Attachment downloaded: {link.get_text()}")
                                except:
                                    continue
                    
                    # Close window and return to main
                    self.driver.close()
                    self.driver.switch_to.window(self.main_window)
                    time.sleep(1)
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.main_window)
            
            # Summary for this manuscript
            print(f"  📊 Summary for {ms_id}:")
            print(f"     - Main PDF: {'✅' if manuscript['pdf_downloaded'] else '❌'}")
            print(f"     - Cover Letter: {'✅' if manuscript['cover_letter_downloaded'] else '❌'}")
            print(f"     - Referee Reports: {len(manuscript['reports_downloaded'])}")
            print(f"     - Other Attachments: {len(manuscript['attachments_downloaded'])}")
    
    def save_results(self):
        """Save comprehensive extraction results."""
        # Calculate statistics
        total_referees = sum(len(m['referees']) for m in self.manuscripts)
        status_counts = {
            'Declined': 0,
            'Accepted': 0,
            'Report Submitted': 0,
            'Overdue': 0,
            'Invited': 0,
            'Unknown': 0
        }
        
        emails_found = 0
        total_reports = 0
        total_cover_letters = 0
        total_attachments = 0
        
        for ms in self.manuscripts:
            for ref in ms['referees']:
                status_counts[ref['status']] = status_counts.get(ref['status'], 0) + 1
                if ref['email']:
                    emails_found += 1
            
            total_reports += len(ms['reports_downloaded'])
            if ms['cover_letter_downloaded']:
                total_cover_letters += 1
            total_attachments += len(ms['attachments_downloaded'])
        
        results = {
            'extraction_time': datetime.now().isoformat(),
            'total_manuscripts': len(self.manuscripts),
            'total_referees': total_referees,
            'referees_with_emails': emails_found,
            'referee_status_breakdown': status_counts,
            'documents_downloaded': {
                'pdfs': sum(1 for m in self.manuscripts if m['pdf_downloaded']),
                'cover_letters': total_cover_letters,
                'referee_reports': total_reports,
                'other_attachments': total_attachments
            },
            'manuscripts': self.manuscripts
        }
        
        # Save JSON results
        json_path = self.dirs['data'] / 'complete_extraction_results.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Generate detailed report
        report_path = self.dirs['data'] / 'complete_extraction_report.txt'
        with open(report_path, 'w') as f:
            f.write("SICON Complete Document Extraction Report\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Extraction Time: {results['extraction_time']}\n")
            f.write(f"Total Manuscripts: {results['total_manuscripts']}\n")
            f.write(f"Total Referees: {total_referees}\n")
            f.write(f"Referees with Emails: {emails_found} ({emails_found/total_referees*100:.1f}%)\n\n")
            
            f.write("DOCUMENTS DOWNLOADED:\n")
            f.write(f"  Main PDFs: {results['documents_downloaded']['pdfs']}\n")
            f.write(f"  Cover Letters: {results['documents_downloaded']['cover_letters']}\n")
            f.write(f"  Referee Reports: {results['documents_downloaded']['referee_reports']}\n")
            f.write(f"  Other Attachments: {results['documents_downloaded']['other_attachments']}\n\n")
            
            f.write("REFEREE STATUS BREAKDOWN:\n")
            for status, count in sorted(status_counts.items()):
                if count > 0:
                    percentage = (count / total_referees * 100) if total_referees > 0 else 0
                    f.write(f"  {status}: {count} ({percentage:.1f}%)\n")
            
            f.write("\n" + "=" * 60 + "\n\n")
            f.write("DETAILED MANUSCRIPT INFORMATION:\n\n")
            
            for ms in self.manuscripts:
                f.write(f"Manuscript {ms['manuscript_id']}\n")
                f.write(f"  Title: {ms['title']}\n")
                f.write(f"  Corresponding Editor: {ms['corresponding_editor']}\n")
                f.write(f"  Associate Editor: {ms['associate_editor']}\n")
                f.write(f"  Submitted: {ms['submitted']}\n")
                f.write(f"  Days in System: {ms['days_in_system']}\n\n")
                
                f.write("  Documents:\n")
                f.write(f"    Main PDF: {'✅ Downloaded' if ms['pdf_downloaded'] else '❌ Not found'}\n")
                f.write(f"    Cover Letter: {'✅ Downloaded' if ms['cover_letter_downloaded'] else '❌ Not found'}\n")
                
                if ms['reports_downloaded']:
                    f.write(f"    Referee Reports ({len(ms['reports_downloaded'])}):\n")
                    for report in ms['reports_downloaded']:
                        f.write(f"      - {report['filename']} (from {report['referee']})\n")
                else:
                    f.write("    Referee Reports: None found\n")
                
                if ms['attachments_downloaded']:
                    f.write(f"    Other Attachments ({len(ms['attachments_downloaded'])}):\n")
                    for att in ms['attachments_downloaded']:
                        f.write(f"      - {att['filename']} ({att['type']})\n")
                
                f.write(f"\n  Referees ({len(ms['referees'])}):\n")
                
                # Group by status
                by_status = {}
                for ref in ms['referees']:
                    status = ref['status']
                    if status not in by_status:
                        by_status[status] = []
                    by_status[status].append(ref)
                
                for status in ['Report Submitted', 'Declined', 'Accepted', 'Overdue', 'Invited', 'Unknown']:
                    if status in by_status:
                        f.write(f"\n    {status} ({len(by_status[status])}):\n")
                        for ref in by_status[status]:
                            f.write(f"      - {ref['name']}")
                            if ref['full_name'] != ref['name']:
                                f.write(f" ({ref['full_name']})")
                            if ref['email']:
                                f.write(f" <{ref['email']}>")
                            if ref['due_date']:
                                f.write(f" - Due: {ref['due_date']}")
                            if ref['invited_date']:
                                f.write(f" - Invited: {ref['invited_date']}")
                            if ref['report_available']:
                                f.write(" [Report Available]")
                            f.write("\n")
                
                f.write("\n" + "-" * 40 + "\n\n")
        
        print(f"\n📊 Results saved to: {self.output_dir}")
        print(f"📄 JSON: {json_path.name}")
        print(f"📄 Report: {report_path.name}")
    
    def run(self):
        """Run the complete extraction."""
        try:
            self.setup_driver()
            
            if not self.authenticate():
                raise Exception("Authentication failed")
            
            if not self.navigate_to_manuscripts():
                raise Exception("Navigation failed")
            
            self.parse_manuscripts_table()
            self.extract_referee_emails()
            self.download_all_documents()
            self.save_results()
            
            print("\n🎉 Complete document extraction finished!")
            
            # Print summary
            total_refs = sum(len(m['referees']) for m in self.manuscripts)
            emails_found = sum(1 for m in self.manuscripts for r in m['referees'] if r['email'])
            pdfs = sum(1 for m in self.manuscripts if m['pdf_downloaded'])
            covers = sum(1 for m in self.manuscripts if m['cover_letter_downloaded'])
            reports = sum(len(m['reports_downloaded']) for m in self.manuscripts)
            attachments = sum(len(m['attachments_downloaded']) for m in self.manuscripts)
            
            print(f"\n📊 Final Summary:")
            print(f"  Manuscripts: {len(self.manuscripts)}")
            print(f"  Total Referees: {total_refs}")
            print(f"  Emails Extracted: {emails_found}/{total_refs} ({emails_found/total_refs*100:.1f}%)")
            print(f"\n  Documents Downloaded:")
            print(f"    Main PDFs: {pdfs}/{len(self.manuscripts)}")
            print(f"    Cover Letters: {covers}")
            print(f"    Referee Reports: {reports}")
            print(f"    Other Attachments: {attachments}")
            
            # Status breakdown
            if total_refs > 0:
                print("\n  Referee Status Breakdown:")
                status_counts = {}
                for ms in self.manuscripts:
                    for ref in ms['referees']:
                        status = ref['status']
                        status_counts[status] = status_counts.get(status, 0) + 1
                
                for status in ['Report Submitted', 'Declined', 'Accepted', 'Overdue', 'Invited', 'Unknown']:
                    if status in status_counts:
                        count = status_counts[status]
                        percentage = (count / total_refs * 100)
                        print(f"    {status}: {count} ({percentage:.1f}%)")
            
            return self.manuscripts
            
        except Exception as e:
            print(f"❌ Fatal error: {e}")
            raise
        finally:
            if hasattr(self, 'driver'):
                self.driver.quit()


def main():
    """Main execution."""
    print("🚀 Starting SICON Complete Document Extraction")
    print("This version downloads ALL available documents\n")
    
    extractor = SICONCompleteDocumentExtractor()
    try:
        results = extractor.run()
        return results
    except Exception as e:
        print(f"\n❌ Extraction failed: {e}")
        return None


if __name__ == "__main__":
    main()