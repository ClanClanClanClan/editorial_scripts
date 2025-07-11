#!/usr/bin/env python3
"""
SICON Perfect Email Search - Finds only emails related to specific manuscripts
"""

import os
import re
import time
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup, NavigableString
from dotenv import load_dotenv

# Import existing email infrastructure
from core.email_utils import (
    get_gmail_service, 
    fetch_latest_verification_code,
    robust_match_email_for_referee_mf,
    fetch_starred_emails
)

load_dotenv()


class SICONPerfectEmailExtractor:
    """SICON extractor with precise manuscript-specific email search."""
    
    def __init__(self):
        self.output_dir = Path(f'./sicon_perfect_email_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.dirs = {
            'pdfs': self.output_dir / 'pdfs',
            'data': self.output_dir / 'data',
            'debug': self.output_dir / 'debug'
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(exist_ok=True)
        
        self.main_window = None
        self.manuscripts = []
        
        # Initialize Gmail service using existing infrastructure
        try:
            self.gmail_service = get_gmail_service()
            print("✅ Gmail API service initialized")
        except Exception as e:
            print(f"⚠️  Gmail API not available: {e}")
            self.gmail_service = None
        
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
    
    def parse_date_string(self, date_str: str) -> datetime:
        """Parse various date formats into datetime object."""
        if not date_str:
            return None
        
        # Common date formats
        formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%Y/%m/%d',
            '%b %d, %Y',
            '%d %b %Y',
            '%B %d, %Y',
            '%d %B %Y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except:
                continue
        
        # Try parsing Gmail date format
        try:
            # Remove timezone info and day name
            clean_date = re.sub(r'^[A-Za-z]+,\s*', '', date_str)
            clean_date = re.sub(r'\s*\([^)]+\)$', '', clean_date)
            clean_date = re.sub(r'\s*[+-]\d{4}$', '', clean_date)
            
            return datetime.strptime(clean_date.strip(), '%d %b %Y %H:%M:%S')
        except:
            pass
        
        return None
    
    def search_referee_emails_precise(self, referee_name: str, referee_email: str, manuscript_id: str, 
                                    submission_date: str, title: str) -> dict:
        """Search for emails specifically related to this manuscript and referee."""
        if not self.gmail_service:
            return {'found': False, 'emails': [], 'invitation_date': None, 'email_count': 0}
        
        try:
            # Parse submission date to create time window
            submission_dt = self.parse_date_string(submission_date)
            if submission_dt:
                # Search window: 1 month before submission to now
                start_date = submission_dt - timedelta(days=30)
                after_date = start_date.strftime('%Y/%m/%d')
            else:
                after_date = None
            
            # Build precise search queries that must include manuscript ID
            search_queries = []
            
            # Primary queries with manuscript ID
            if referee_email:
                search_queries.extend([
                    f'to:{referee_email} "{manuscript_id}"',
                    f'from:{referee_email} "{manuscript_id}"',
                    f'to:{referee_email} subject:"{manuscript_id}"',
                ])
            
            # Name-based queries with manuscript ID
            search_queries.extend([
                f'"{referee_name}" "{manuscript_id}"',
                f'subject:"{manuscript_id}" "{referee_name}"',
                f'subject:"review" "{manuscript_id}" "{referee_name}"',
                f'subject:"referee" "{manuscript_id}" "{referee_name}"',
            ])
            
            # Title-based queries (first few words of title)
            title_words = title.split()[:5]
            title_snippet = ' '.join(title_words)
            if len(title_snippet) > 10:
                search_queries.append(f'"{referee_name}" "{title_snippet}"')
            
            # Add date filter to all queries
            if after_date:
                search_queries = [f'{q} after:{after_date}' for q in search_queries]
            
            all_emails = []
            invitation_date = None
            email_details = []
            
            print(f"    🔍 Searching with manuscript ID {manuscript_id}...")
            
            for query in search_queries:
                try:
                    # Use Gmail API to search
                    results = self.gmail_service.users().messages().list(
                        userId='me',
                        q=query,
                        maxResults=20  # Reasonable limit per query
                    ).execute()
                    
                    messages = results.get('messages', [])
                    
                    for message in messages:
                        try:
                            # Get message details
                            msg = self.gmail_service.users().messages().get(
                                userId='me',
                                id=message['id'],
                                format='full'
                            ).execute()
                            
                            headers = msg['payload'].get('headers', [])
                            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                            from_header = next((h['value'] for h in headers if h['name'] == 'From'), '')
                            to_header = next((h['value'] for h in headers if h['name'] == 'To'), '')
                            
                            # Verify this email is actually about this manuscript
                            if manuscript_id not in subject and manuscript_id not in str(msg.get('snippet', '')):
                                continue
                            
                            email_data = {
                                'id': message['id'],
                                'subject': subject,
                                'date': date,
                                'from': from_header,
                                'to': to_header,
                                'snippet': msg.get('snippet', '')[:200]
                            }
                            
                            all_emails.append(email_data)
                            
                            # Identify invitation emails
                            subject_lower = subject.lower()
                            if not invitation_date and any(word in subject_lower for word in ['invitation', 'invite', 'review request']):
                                invitation_date = date
                                email_data['type'] = 'invitation'
                            elif 'accept' in subject_lower:
                                email_data['type'] = 'acceptance'
                            elif 'decline' in subject_lower or 'unable' in subject_lower:
                                email_data['type'] = 'decline'
                            elif 'report' in subject_lower or 'review' in subject_lower:
                                email_data['type'] = 'report'
                            else:
                                email_data['type'] = 'other'
                            
                            email_details.append(email_data)
                                
                        except Exception as e:
                            continue
                            
                except Exception as e:
                    continue
            
            # Remove duplicates
            unique_emails = []
            seen_ids = set()
            for email in all_emails:
                email_id = email.get('id', '')
                if email_id and email_id not in seen_ids:
                    unique_emails.append(email)
                    seen_ids.add(email_id)
            
            # Sort by date
            unique_emails.sort(key=lambda x: self.parse_date_string(x.get('date', '')) or datetime.min)
            
            return {
                'found': len(unique_emails) > 0,
                'emails': unique_emails,
                'email_details': email_details,
                'invitation_date': invitation_date,
                'email_count': len(unique_emails),
                'search_manuscript_id': manuscript_id
            }
            
        except Exception as e:
            print(f"    ⚠️  Error searching emails: {e}")
            return {'found': False, 'emails': [], 'invitation_date': None, 'email_count': 0}
    
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
        """Parse manuscripts table with precise email verification."""
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
                'email_verification': {
                    'total_emails_found': 0,
                    'referees_with_any_emails': 0,
                    'referees_with_manuscript_emails': 0,
                    'invitation_emails_found': 0
                }
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
            
            # Extract invited dates from SICON
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
            
            # Process each referee
            print(f"  📧 Searching for manuscript-specific emails...")
            
            for i, name in enumerate(referee_names):
                status = self.parse_status_from_text(status_list[i]) if i < len(status_list) else 'Unknown'
                due_date = due_dates[i] if i < len(due_dates) else None
                sicon_invited_date = invited_dates[i] if i < len(invited_dates) else None
                
                referee = {
                    'name': name,
                    'email': None,
                    'full_name': name,
                    'status': status,
                    'due_date': due_date,
                    'sicon_invited_date': sicon_invited_date,
                    'email_verification': {
                        'emails_found': 0,
                        'email_types': {},
                        'email_invitation_date': None,
                        'verification_status': 'not_found',
                        'email_subjects': []
                    },
                    'report_available': False
                }
                
                manuscript['referees'].append(referee)
            
            self.manuscripts.append(manuscript)
    
    def extract_referee_emails_and_verify(self):
        """Extract referee emails from SICON and search for manuscript-specific emails."""
        print("\n📧 Extracting referee emails and verifying with Gmail...")
        
        for manuscript in self.manuscripts:
            ms_id = manuscript['manuscript_id']
            print(f"\n📄 Processing {ms_id}: {manuscript['title'][:50]}...")
            
            for referee in manuscript['referees']:
                print(f"\n  👤 {referee['name']} ({referee['status']})")
                
                # First, try to get email from SICON profile
                try:
                    referee_links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{referee['name']}')]")
                    
                    if referee_links:
                        self.driver.execute_script("arguments[0].click();", referee_links[0])
                        time.sleep(3)
                        
                        if len(self.driver.window_handles) > 1:
                            self.driver.switch_to.window(self.driver.window_handles[-1])
                            time.sleep(2)
                            
                            profile_html = self.driver.page_source
                            email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', profile_html)
                            if email_match:
                                referee['email'] = email_match.group()
                                print(f"    ✅ Found email: {referee['email']}")
                            
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
                
                # Now search for manuscript-specific emails
                email_search = self.search_referee_emails_precise(
                    referee_name=referee['name'],
                    referee_email=referee.get('email'),
                    manuscript_id=ms_id,
                    submission_date=manuscript['submitted'],
                    title=manuscript['title']
                )
                
                if email_search['found']:
                    referee['email_verification']['emails_found'] = email_search['email_count']
                    referee['email_verification']['verification_status'] = 'verified'
                    referee['email_verification']['email_invitation_date'] = email_search['invitation_date']
                    
                    # Count email types
                    email_types = {}
                    for email in email_search.get('email_details', []):
                        email_type = email.get('type', 'other')
                        email_types[email_type] = email_types.get(email_type, 0) + 1
                        
                        # Store subject for reference
                        referee['email_verification']['email_subjects'].append({
                            'subject': email.get('subject', '')[:100],
                            'date': email.get('date', '')[:25],
                            'type': email_type
                        })
                    
                    referee['email_verification']['email_types'] = email_types
                    
                    # Update manuscript stats
                    manuscript['email_verification']['total_emails_found'] += email_search['email_count']
                    manuscript['email_verification']['referees_with_manuscript_emails'] += 1
                    
                    if email_search['invitation_date']:
                        manuscript['email_verification']['invitation_emails_found'] += 1
                    
                    print(f"    📧 Found {email_search['email_count']} emails for manuscript {ms_id}:")
                    for email_type, count in email_types.items():
                        print(f"       - {email_type}: {count}")
                    
                    if len(referee['email_verification']['email_subjects']) > 0:
                        print(f"    📋 Sample email: \"{referee['email_verification']['email_subjects'][0]['subject']}\"")
                else:
                    print(f"    ❌ No emails found for manuscript {ms_id}")
    
    def download_manuscript_pdfs(self):
        """Download manuscript PDFs."""
        print("\n📥 Downloading manuscript PDFs...")
        
        for manuscript in self.manuscripts:
            ms_id = manuscript['manuscript_id']
            
            try:
                # Clear temp download folder
                for f in self.temp_download.glob('*'):
                    f.unlink()
                
                # Find and click manuscript link
                ms_link = self.driver.find_element(By.XPATH, f"//a[contains(text(), '{ms_id}')]")
                self.driver.execute_script("arguments[0].click();", ms_link)
                time.sleep(3)
                
                if len(self.driver.window_handles) > 1:
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    time.sleep(2)
                    
                    # Look for PDF links
                    pdf_patterns = [
                        "//a[contains(text(), 'PDF')]",
                        "//a[contains(text(), 'Download PDF')]",
                        "//a[contains(@href, '.pdf')]"
                    ]
                    
                    for pattern in pdf_patterns:
                        try:
                            pdf_links = self.driver.find_elements(By.XPATH, pattern)
                            if pdf_links:
                                initial_files = set(self.temp_download.glob('*'))
                                self.driver.execute_script("arguments[0].click();", pdf_links[0])
                                time.sleep(5)
                                
                                new_files = set(self.temp_download.glob('*')) - initial_files
                                
                                if new_files:
                                    for new_file in new_files:
                                        with open(new_file, 'rb') as f:
                                            header = f.read(4)
                                        
                                        if header == b'%PDF':
                                            dest = self.dirs['pdfs'] / f"{ms_id}.pdf"
                                            shutil.move(str(new_file), str(dest))
                                            manuscript['pdf_downloaded'] = True
                                            print(f"  ✅ PDF downloaded for {ms_id}")
                                            break
                                
                                if manuscript['pdf_downloaded']:
                                    break
                        except:
                            continue
                    
                    self.driver.close()
                    self.driver.switch_to.window(self.main_window)
                    time.sleep(1)
                    
            except Exception as e:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.main_window)
    
    def save_results(self):
        """Save comprehensive extraction results with precise email verification."""
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
        total_manuscript_emails = 0
        referees_with_emails = 0
        invitation_emails = 0
        
        for ms in self.manuscripts:
            for ref in ms['referees']:
                status_counts[ref['status']] = status_counts.get(ref['status'], 0) + 1
                if ref['email']:
                    emails_found += 1
                
                if ref['email_verification']['emails_found'] > 0:
                    referees_with_emails += 1
                    total_manuscript_emails += ref['email_verification']['emails_found']
                    
                if ref['email_verification']['email_invitation_date']:
                    invitation_emails += 1
        
        results = {
            'extraction_time': datetime.now().isoformat(),
            'total_manuscripts': len(self.manuscripts),
            'total_referees': total_referees,
            'referees_with_sicon_emails': emails_found,
            'referee_status_breakdown': status_counts,
            'email_verification_summary': {
                'total_manuscript_specific_emails': total_manuscript_emails,
                'referees_with_manuscript_emails': referees_with_emails,
                'average_emails_per_referee': round(total_manuscript_emails / total_referees, 1) if total_referees > 0 else 0,
                'invitation_emails_found': invitation_emails,
                'verification_rate': f"{referees_with_emails/total_referees*100:.1f}%" if total_referees > 0 else "0%"
            },
            'pdfs_downloaded': sum(1 for m in self.manuscripts if m['pdf_downloaded']),
            'manuscripts': self.manuscripts
        }
        
        # Save JSON results
        json_path = self.dirs['data'] / 'perfect_email_extraction_results.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Generate detailed report
        report_path = self.dirs['data'] / 'perfect_email_extraction_report.txt'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("SICON Perfect Email Extraction Report\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Extraction Time: {results['extraction_time']}\n")
            f.write(f"Total Manuscripts: {results['total_manuscripts']}\n")
            f.write(f"Total Referees: {total_referees}\n")
            f.write(f"Referees with SICON Emails: {emails_found} ({emails_found/total_referees*100:.1f}%)\n")
            f.write(f"PDFs Downloaded: {results['pdfs_downloaded']}\n\n")
            
            f.write("MANUSCRIPT-SPECIFIC EMAIL VERIFICATION:\n")
            f.write(f"  Total Manuscript-Specific Emails: {total_manuscript_emails}\n")
            f.write(f"  Average Emails per Referee: {results['email_verification_summary']['average_emails_per_referee']}\n")
            f.write(f"  Referees with Manuscript Emails: {referees_with_emails} ({referees_with_emails/total_referees*100:.1f}%)\n")
            f.write(f"  Invitation Emails Found: {invitation_emails}\n\n")
            
            f.write("REFEREE STATUS BREAKDOWN:\n")
            for status, count in sorted(status_counts.items()):
                if count > 0:
                    percentage = (count / total_referees * 100) if total_referees > 0 else 0
                    f.write(f"  {status}: {count} ({percentage:.1f}%)\n")
            
            f.write("\n" + "=" * 80 + "\n\n")
            f.write("DETAILED MANUSCRIPT INFORMATION:\n\n")
            
            for ms in self.manuscripts:
                f.write(f"Manuscript {ms['manuscript_id']}: {ms['title'][:60]}...\n")
                f.write(f"  Corresponding Editor: {ms['corresponding_editor']}\n")
                f.write(f"  Associate Editor: {ms['associate_editor']}\n")
                f.write(f"  Submitted: {ms['submitted']}\n")
                f.write(f"  Days in System: {ms['days_in_system']}\n")
                f.write(f"  PDF: {'✅ Downloaded' if ms['pdf_downloaded'] else '❌ Not downloaded'}\n\n")
                
                f.write("  Email Verification Summary:\n")
                ev = ms['email_verification']
                f.write(f"    Total Emails for This Manuscript: {ev['total_emails_found']}\n")
                f.write(f"    Referees with Emails: {ev['referees_with_manuscript_emails']}/{len(ms['referees'])}\n")
                f.write(f"    Invitation Emails: {ev['invitation_emails_found']}\n\n")
                
                f.write(f"  Referees ({len(ms['referees'])}):\n")
                
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
                            if ref['email']:
                                f.write(f" <{ref['email']}>")
                            f.write("\n")
                            
                            # SICON dates
                            if ref['sicon_invited_date'] or ref['due_date']:
                                f.write(f"        SICON: ")
                                if ref['sicon_invited_date']:
                                    f.write(f"Invited {ref['sicon_invited_date']}")
                                if ref['due_date']:
                                    f.write(f", Due {ref['due_date']}")
                                f.write("\n")
                            
                            # Email verification
                            ev = ref['email_verification']
                            if ev['emails_found'] > 0:
                                f.write(f"        Emails: {ev['emails_found']} found for {ms['manuscript_id']}")
                                
                                # Show email types
                                if ev['email_types']:
                                    types_str = ', '.join([f"{t}: {c}" for t, c in ev['email_types'].items()])
                                    f.write(f" ({types_str})")
                                f.write("\n")
                                
                                # Show sample emails
                                if ev['email_subjects']:
                                    f.write("        Email Examples:\n")
                                    for i, email in enumerate(ev['email_subjects'][:2]):  # Show first 2
                                        f.write(f"          • \"{email['subject']}\" ({email['date'][:10]})\n")
                            else:
                                f.write(f"        Emails: None found for {ms['manuscript_id']}\n")
                
                f.write("\n" + "-" * 60 + "\n\n")
        
        print(f"\n📊 Results saved to: {self.output_dir}")
        print(f"📄 JSON: {json_path.name}")
        print(f"📄 Report: {report_path.name}")
    
    def run(self):
        """Run the perfect email extraction."""
        try:
            self.setup_driver()
            
            if not self.authenticate():
                raise Exception("Authentication failed")
            
            if not self.navigate_to_manuscripts():
                raise Exception("Navigation failed")
            
            self.parse_manuscripts_table()
            self.extract_referee_emails_and_verify()
            self.download_manuscript_pdfs()
            self.save_results()
            
            print("\n🎉 Perfect email extraction complete!")
            
            # Print summary
            total_refs = sum(len(m['referees']) for m in self.manuscripts)
            emails_found = sum(1 for m in self.manuscripts for r in m['referees'] if r['email'])
            pdfs = sum(1 for m in self.manuscripts if m['pdf_downloaded'])
            
            # Email verification stats
            total_manuscript_emails = sum(r['email_verification']['emails_found'] for m in self.manuscripts for r in m['referees'])
            verified_referees = sum(1 for m in self.manuscripts for r in m['referees'] if r['email_verification']['emails_found'] > 0)
            avg_emails = total_manuscript_emails / total_refs if total_refs > 0 else 0
            
            print(f"\n📊 Final Summary:")
            print(f"  Manuscripts: {len(self.manuscripts)}")
            print(f"  Total Referees: {total_refs}")
            print(f"  SICON Emails: {emails_found}/{total_refs} ({emails_found/total_refs*100:.1f}%)")
            print(f"  PDFs Downloaded: {pdfs}/{len(self.manuscripts)}")
            print(f"\n📧 Manuscript-Specific Email Verification:")
            print(f"  Total Emails Found: {total_manuscript_emails} (avg {avg_emails:.1f} per referee)")
            print(f"  Referees with Emails: {verified_referees}/{total_refs} ({verified_referees/total_refs*100:.1f}%)")
            
            # Show email breakdown by type
            all_email_types = {}
            for ms in self.manuscripts:
                for ref in ms['referees']:
                    for email_type, count in ref['email_verification'].get('email_types', {}).items():
                        all_email_types[email_type] = all_email_types.get(email_type, 0) + count
            
            if all_email_types:
                print(f"\n  Email Types Found:")
                for email_type, count in sorted(all_email_types.items()):
                    print(f"    - {email_type}: {count}")
            
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
    print("🚀 Starting SICON Perfect Email Extraction")
    print("Searches ONLY for emails related to specific manuscripts\n")
    
    extractor = SICONPerfectEmailExtractor()
    try:
        results = extractor.run()
        return results
    except Exception as e:
        print(f"\n❌ Extraction failed: {e}")
        return None


if __name__ == "__main__":
    main()