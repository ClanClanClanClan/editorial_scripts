#!/usr/bin/env python3
"""
Complete SICON Extractor - Final Version
Extracts ALL data including referee status, cover letters, and reports
"""

import os
import re
import time
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()


class CompleteSICONExtractor:
    """Complete SICON extractor with referee status and all documents."""
    
    def __init__(self):
        self.output_dir = Path(f'./sicon_complete_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.dirs = {
            'pdfs': self.output_dir / 'pdfs',
            'cover_letters': self.output_dir / 'cover_letters',
            'reports': self.output_dir / 'reports',
            'data': self.output_dir / 'data',
            'screenshots': self.output_dir / 'screenshots',
            'debug': self.output_dir / 'debug'
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(exist_ok=True)
        
        self.main_window = None
        self.manuscripts = []
        
        print(f"📁 Output directory: {self.output_dir}")
    
    def setup_driver(self):
        """Setup Chrome driver with download configuration."""
        chrome_options = Options()
        
        # Configure downloads to go to temp folder first
        self.temp_download = self.output_dir / 'temp_downloads'
        self.temp_download.mkdir(exist_ok=True)
        
        prefs = {
            "download.default_directory": str(self.temp_download),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": False,
            "safebrowsing.disable_download_protection": True,
            "profile.default_content_setting_values.automatic_downloads": 1
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)
        
        # Enable downloads
        self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": str(self.temp_download)
        })
        
        print("✅ Chrome driver initialized")
    
    def save_screenshot(self, name: str):
        """Save screenshot."""
        path = self.dirs['screenshots'] / f"{name}_{datetime.now().strftime('%H%M%S')}.png"
        self.driver.save_screenshot(str(path))
    
    def authenticate(self) -> bool:
        """Authenticate using ORCID."""
        print("\n🔐 Authenticating...")
        
        try:
            # Navigate to SICON
            self.driver.get("http://sicon.siam.org")
            time.sleep(5)
            self.main_window = self.driver.current_window_handle
            
            # Check if already authenticated
            if 'associate editor tasks' in self.driver.page_source.lower():
                print("✅ Already authenticated!")
                return True
            
            # Dismiss privacy notification
            try:
                privacy_button = self.driver.find_element(By.XPATH, "//input[@value='Continue']")
                privacy_button.click()
                print("✅ Clicked privacy notification")
                time.sleep(3)
            except:
                pass
            
            # Click ORCID link
            orcid_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'orcid')]")
            self.driver.execute_script("arguments[0].click();", orcid_link)
            print("✅ Clicked ORCID link")
            time.sleep(5)
            
            # Handle ORCID authentication
            if 'orcid.org' in self.driver.current_url:
                print("📝 On ORCID page")
                
                # Accept cookies
                try:
                    accept_cookies = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept All Cookies')]"))
                    )
                    accept_cookies.click()
                    print("✅ Accepted cookies")
                    time.sleep(3)
                except:
                    pass
                
                # Fill credentials
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
                
                # Click sign in
                signin_button = self.driver.find_element(By.XPATH, "//button[contains(., 'Sign in to ORCID')]")
                signin_button.click()
                print("✅ Clicked sign in")
                
                time.sleep(10)
            
            # Handle post-auth privacy notification
            try:
                privacy_button = self.driver.find_element(By.XPATH, "//input[@value='Continue']")
                privacy_button.click()
                print("✅ Clicked post-auth privacy")
                time.sleep(3)
            except:
                pass
            
            # Verify authentication
            if 'associate editor tasks' in self.driver.page_source.lower():
                print("✅ Authentication successful!")
                return True
            else:
                print("❌ Authentication failed")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            self.save_screenshot("auth_error")
            return False
    
    def navigate_to_manuscripts(self) -> bool:
        """Navigate to All Pending Manuscripts."""
        print("\n📋 Navigating to manuscripts...")
        
        try:
            # Find the "4 AE" link with folder_id=1800
            ae_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'folder_id=1800')]")
            self.driver.execute_script("arguments[0].click();", ae_link)
            time.sleep(5)
            
            if 'All Pending Manuscripts' in self.driver.page_source:
                print("✅ Reached manuscripts table")
                self.save_screenshot("manuscripts_table")
                return True
            else:
                print("❌ Failed to reach manuscripts table")
                return False
                
        except Exception as e:
            print(f"❌ Navigation error: {e}")
            return False
    
    def parse_referee_status(self, cell_text: str, row_html: str) -> str:
        """Parse referee status from table cell."""
        cell_lower = cell_text.lower()
        row_lower = row_html.lower()
        
        # Check for various status indicators
        if 'declined' in cell_lower or 'declined' in row_lower:
            return 'Declined'
        elif 'report' in cell_lower or 'submitted' in cell_lower:
            return 'Report Submitted'
        elif 'accepted' in cell_lower or 'agreed' in cell_lower:
            return 'Accepted'
        elif 'invited' in cell_lower or 'pending' in cell_lower:
            return 'Invited'
        elif 'overdue' in cell_lower:
            return 'Overdue'
        else:
            # Default based on context
            if 'due' in cell_lower:
                return 'Accepted'  # Has a due date
            else:
                return 'Invited'
    
    def parse_manuscripts_table(self):
        """Parse manuscripts table with proper referee status."""
        print("\n📊 Parsing manuscripts table...")
        
        # Save page source
        with open(self.dirs['debug'] / 'manuscripts_table.html', 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Find the main data table
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
        
        # Parse table rows
        rows = data_table.find_all('tr')
        
        for row in rows:
            # Skip if no manuscript ID
            if not re.search(r'M\d{6}', str(row)):
                continue
            
            cells = row.find_all('td')
            if len(cells) < 6:
                continue
            
            # Extract manuscript ID
            ms_id_match = re.search(r'(M\d{6})', cells[0].get_text())
            if not ms_id_match:
                continue
            
            ms_id = ms_id_match.group(1)
            print(f"\n🔍 Processing manuscript {ms_id}")
            
            manuscript = {
                'manuscript_id': ms_id,
                'title': cells[1].get_text(strip=True) if len(cells) > 1 else '',
                'corresponding_editor': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                'associate_editor': cells[3].get_text(strip=True) if len(cells) > 3 else '',
                'submitted': cells[4].get_text(strip=True) if len(cells) > 4 else '',
                'days_in_system': cells[5].get_text(strip=True) if len(cells) > 5 else '',
                'referees': [],
                'pdf_downloaded': False,
                'cover_letter_downloaded': False,
                'reports_downloaded': []
            }
            
            # Parse invitees/referees column (usually column 6 or 7)
            referee_cells = cells[6:] if len(cells) > 6 else []
            row_html = str(row)
            
            # Look for referee patterns in the entire row
            # Pattern 1: Name followed by parentheses with status/date
            referee_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*\([^)]+\)'
            matches = re.findall(referee_pattern, row.get_text())
            
            for match in matches:
                name = match.strip()
                # Skip false positives
                if name in ['Days', 'System', 'Editor', 'Title', 'Status', 'Assigned']:
                    continue
                
                # Find the context around this name to determine status
                name_index = row_html.find(name)
                if name_index > 0:
                    context = row_html[max(0, name_index-50):name_index+200]
                    status = self.parse_referee_status(context, row_html)
                else:
                    status = 'Invited'
                
                print(f"  👤 Found referee: {name} ({status})")
                
                manuscript['referees'].append({
                    'name': name,
                    'email': None,
                    'full_name': name,
                    'status': status,
                    'report_available': 'report' in context.lower() if name_index > 0 else False
                })
            
            # Also check for known referee names
            known_referees = ['Ferrari', 'LI', 'Cohen', 'Guo', 'Ekren', 'Ren', 'daudin', 'Tangpi']
            for name in known_referees:
                if name in row_html and not any(r['name'] == name for r in manuscript['referees']):
                    # Find context
                    name_index = row_html.find(name)
                    context = row_html[max(0, name_index-50):name_index+200]
                    status = self.parse_referee_status(context, row_html)
                    
                    print(f"  👤 Found known referee: {name} ({status})")
                    
                    manuscript['referees'].append({
                        'name': name,
                        'email': None,
                        'full_name': name,
                        'status': status,
                        'report_available': 'report' in context.lower()
                    })
            
            self.manuscripts.append(manuscript)
            
            # Save intermediate results
            self.save_results(intermediate=True)
    
    def extract_referee_emails(self):
        """Extract referee emails by clicking on their names."""
        print("\n📧 Extracting referee emails...")
        
        for manuscript in self.manuscripts:
            print(f"\n📄 Processing referees for {manuscript['manuscript_id']}")
            
            for referee in manuscript['referees']:
                if referee['email']:  # Skip if already have email
                    continue
                
                print(f"  📧 Extracting email for {referee['name']} ({referee['status']})...")
                
                try:
                    # Find referee link
                    referee_links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{referee['name']}')]")
                    
                    if not referee_links:
                        print(f"    ❌ No link found")
                        continue
                    
                    # Click the first matching link
                    referee_link = referee_links[0]
                    self.driver.execute_script("arguments[0].click();", referee_link)
                    time.sleep(3)
                    
                    # Check if new window opened
                    if len(self.driver.window_handles) > 1:
                        # Switch to new window
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                        time.sleep(2)
                        
                        # Extract email from profile
                        profile_html = self.driver.page_source
                        
                        # Look for email
                        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', profile_html)
                        if email_match:
                            referee['email'] = email_match.group()
                            print(f"    ✅ Found email: {referee['email']}")
                        
                        # Look for full name
                        soup = BeautifulSoup(profile_html, 'html.parser')
                        title_tag = soup.find('title')
                        if title_tag and title_tag.text:
                            full_name = title_tag.text.strip()
                            if full_name and len(full_name) > len(referee['name']):
                                referee['full_name'] = full_name
                                print(f"    ✅ Found full name: {full_name}")
                        
                        # Close window
                        self.driver.close()
                        self.driver.switch_to.window(self.main_window)
                        time.sleep(1)
                    
                except Exception as e:
                    print(f"    ❌ Error: {e}")
                    # Make sure we're back in main window
                    if len(self.driver.window_handles) > 1:
                        self.driver.close()
                        self.driver.switch_to.window(self.main_window)
    
    def download_manuscript_documents(self):
        """Download all documents: PDFs, cover letters, and referee reports."""
        print("\n📥 Downloading all manuscript documents...")
        
        for manuscript in self.manuscripts:
            ms_id = manuscript['manuscript_id']
            print(f"\n📄 Processing documents for {ms_id}")
            
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
                    # Switch to manuscript view window
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    time.sleep(2)
                    
                    print("  🔍 Looking for documents on manuscript page...")
                    
                    # Save page for debugging
                    debug_file = self.dirs['debug'] / f"{ms_id}_view_page.html"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    
                    # Look for various document links
                    document_patterns = [
                        # PDF patterns
                        ("PDF", [
                            "//a[contains(text(), 'PDF')]",
                            "//a[contains(text(), 'Download PDF')]",
                            "//a[contains(@href, '.pdf')]",
                            "//a[contains(text(), 'Manuscript PDF')]",
                            "//a[contains(text(), 'View PDF')]"
                        ]),
                        
                        # Cover letter patterns
                        ("Cover Letter", [
                            "//a[contains(text(), 'Cover Letter')]",
                            "//a[contains(text(), 'cover letter')]",
                            "//a[contains(text(), 'Cover')]",
                            "//a[contains(@href, 'cover')]"
                        ]),
                        
                        # Referee report patterns
                        ("Reports", [
                            "//a[contains(text(), 'Report')]",
                            "//a[contains(text(), 'Referee Report')]",
                            "//a[contains(text(), 'Review')]",
                            "//a[contains(text(), 'Reviewer Report')]",
                            "//a[contains(@href, 'report')]"
                        ])
                    ]
                    
                    # Try each document type
                    for doc_type, patterns in document_patterns:
                        print(f"\n  📎 Looking for {doc_type}...")
                        
                        for pattern in patterns:
                            try:
                                links = self.driver.find_elements(By.XPATH, pattern)
                                
                                if links:
                                    print(f"    ✅ Found {len(links)} {doc_type} link(s)")
                                    
                                    for i, link in enumerate(links):
                                        link_text = link.text.strip()
                                        print(f"    📥 Downloading: {link_text}")
                                        
                                        # Get initial file count
                                        initial_files = set(self.temp_download.glob('*'))
                                        
                                        # Click the link
                                        self.driver.execute_script("arguments[0].click();", link)
                                        time.sleep(5)
                                        
                                        # Check for new files
                                        new_files = set(self.temp_download.glob('*')) - initial_files
                                        
                                        if new_files:
                                            for new_file in new_files:
                                                # Determine destination based on file type
                                                if doc_type == "PDF" and not manuscript['pdf_downloaded']:
                                                    dest = self.dirs['pdfs'] / f"{ms_id}.pdf"
                                                    shutil.move(str(new_file), str(dest))
                                                    manuscript['pdf_downloaded'] = True
                                                    manuscript['pdf_path'] = str(dest)
                                                    print(f"      ✅ PDF saved: {dest.name}")
                                                
                                                elif doc_type == "Cover Letter" and not manuscript['cover_letter_downloaded']:
                                                    dest = self.dirs['cover_letters'] / f"{ms_id}_cover_letter.pdf"
                                                    shutil.move(str(new_file), str(dest))
                                                    manuscript['cover_letter_downloaded'] = True
                                                    manuscript['cover_letter_path'] = str(dest)
                                                    print(f"      ✅ Cover letter saved: {dest.name}")
                                                
                                                elif doc_type == "Reports":
                                                    # Name report with index
                                                    report_name = f"{ms_id}_report_{len(manuscript['reports_downloaded'])+1}.pdf"
                                                    dest = self.dirs['reports'] / report_name
                                                    shutil.move(str(new_file), str(dest))
                                                    manuscript['reports_downloaded'].append({
                                                        'path': str(dest),
                                                        'name': report_name,
                                                        'referee': link_text if 'referee' in link_text.lower() else 'Unknown'
                                                    })
                                                    print(f"      ✅ Report saved: {dest.name}")
                                        
                                        # Return to manuscript page if needed
                                        if len(self.driver.window_handles) > 2:
                                            self.driver.close()
                                            self.driver.switch_to.window(self.driver.window_handles[-1])
                                    
                                    # Break if we found this document type
                                    if (doc_type == "PDF" and manuscript['pdf_downloaded']) or \
                                       (doc_type == "Cover Letter" and manuscript['cover_letter_downloaded']):
                                        break
                                        
                            except Exception as e:
                                print(f"    ⚠️  Error with pattern {pattern}: {e}")
                                continue
                    
                    # List all links for debugging if we missed something
                    if not manuscript['pdf_downloaded']:
                        print("\n  📋 All links on page (for debugging):")
                        all_links = self.driver.find_elements(By.TAG_NAME, 'a')
                        for i, link in enumerate(all_links[:20]):  # First 20 links
                            text = link.text.strip()
                            href = link.get_attribute('href') or ''
                            if text:
                                print(f"    Link {i}: '{text}'")
                    
                    # Close window and return to main
                    self.driver.close()
                    self.driver.switch_to.window(self.main_window)
                    time.sleep(1)
                    
            except Exception as e:
                print(f"  ❌ Error processing documents: {e}")
                # Make sure we're back in main window
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.main_window)
    
    def save_results(self, intermediate: bool = False):
        """Save extraction results."""
        # Calculate statistics
        total_referees = sum(len(m['referees']) for m in self.manuscripts)
        referees_declined = sum(1 for m in self.manuscripts for r in m['referees'] if r['status'] == 'Declined')
        referees_accepted = sum(1 for m in self.manuscripts for r in m['referees'] if r['status'] == 'Accepted')
        referees_submitted = sum(1 for m in self.manuscripts for r in m['referees'] if r['status'] == 'Report Submitted')
        
        results = {
            'extraction_time': datetime.now().isoformat(),
            'total_manuscripts': len(self.manuscripts),
            'total_referees': total_referees,
            'referee_statistics': {
                'declined': referees_declined,
                'accepted': referees_accepted,
                'reports_submitted': referees_submitted,
                'pending': total_referees - referees_declined - referees_accepted - referees_submitted
            },
            'documents_downloaded': {
                'pdfs': sum(1 for m in self.manuscripts if m['pdf_downloaded']),
                'cover_letters': sum(1 for m in self.manuscripts if m['cover_letter_downloaded']),
                'reports': sum(len(m['reports_downloaded']) for m in self.manuscripts)
            },
            'manuscripts': self.manuscripts
        }
        
        filename = 'intermediate_results.json' if intermediate else 'final_results.json'
        path = self.dirs['data'] / filename
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        if not intermediate:
            # Generate detailed report
            report_path = self.dirs['data'] / 'complete_extraction_report.txt'
            with open(report_path, 'w') as f:
                f.write("SICON Complete Extraction Report\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"Extraction Time: {results['extraction_time']}\n")
                f.write(f"Total Manuscripts: {results['total_manuscripts']}\n\n")
                
                f.write("REFEREE STATISTICS:\n")
                f.write(f"  Total Referees: {total_referees}\n")
                f.write(f"  Declined: {referees_declined}\n")
                f.write(f"  Accepted: {referees_accepted}\n")
                f.write(f"  Reports Submitted: {referees_submitted}\n")
                f.write(f"  Pending/Invited: {results['referee_statistics']['pending']}\n\n")
                
                f.write("DOCUMENTS DOWNLOADED:\n")
                f.write(f"  PDFs: {results['documents_downloaded']['pdfs']}\n")
                f.write(f"  Cover Letters: {results['documents_downloaded']['cover_letters']}\n")
                f.write(f"  Referee Reports: {results['documents_downloaded']['reports']}\n")
                f.write("\n" + "=" * 60 + "\n\n")
                
                for ms in self.manuscripts:
                    f.write(f"Manuscript {ms['manuscript_id']}\n")
                    f.write(f"  Title: {ms['title']}\n")
                    f.write(f"  Corresponding Editor: {ms['corresponding_editor']}\n")
                    f.write(f"  Associate Editor: {ms['associate_editor']}\n")
                    f.write(f"  Submitted: {ms['submitted']}\n")
                    f.write(f"  Days in System: {ms['days_in_system']}\n")
                    
                    f.write(f"\n  Referees ({len(ms['referees'])}):\n")
                    for ref in ms['referees']:
                        email = ref.get('email', 'No email')
                        f.write(f"    - {ref['name']} ({ref['full_name']})\n")
                        f.write(f"      Status: {ref['status']}\n")
                        f.write(f"      Email: {email}\n")
                        if ref.get('report_available'):
                            f.write(f"      Report: Available\n")
                    
                    f.write(f"\n  Documents:\n")
                    if ms['pdf_downloaded']:
                        f.write(f"    PDF: ✅ Downloaded\n")
                    else:
                        f.write(f"    PDF: ❌ Not found\n")
                    
                    if ms['cover_letter_downloaded']:
                        f.write(f"    Cover Letter: ✅ Downloaded\n")
                    else:
                        f.write(f"    Cover Letter: ❌ Not found\n")
                    
                    if ms['reports_downloaded']:
                        f.write(f"    Referee Reports: ✅ {len(ms['reports_downloaded'])} downloaded\n")
                        for report in ms['reports_downloaded']:
                            f.write(f"      - {report['name']}\n")
                    else:
                        f.write(f"    Referee Reports: ❌ None found\n")
                    
                    f.write("\n" + "-" * 40 + "\n\n")
            
            print(f"\n📊 Report saved to: {report_path}")
    
    def run(self):
        """Run the complete extraction."""
        try:
            self.setup_driver()
            
            # Step 1: Authenticate
            if not self.authenticate():
                raise Exception("Authentication failed")
            
            # Step 2: Navigate to manuscripts
            if not self.navigate_to_manuscripts():
                raise Exception("Navigation failed")
            
            # Step 3: Parse manuscripts table with status
            self.parse_manuscripts_table()
            
            # Step 4: Extract referee emails
            self.extract_referee_emails()
            
            # Step 5: Download all documents
            self.download_manuscript_documents()
            
            # Step 6: Save final results
            self.save_results()
            
            print("\n🎉 Complete extraction finished!")
            print(f"📊 Results saved to: {self.output_dir}")
            
            # Print summary
            total_refs = sum(len(m['referees']) for m in self.manuscripts)
            refs_declined = sum(1 for m in self.manuscripts for r in m['referees'] if r['status'] == 'Declined')
            refs_accepted = sum(1 for m in self.manuscripts for r in m['referees'] if r['status'] == 'Accepted')
            refs_submitted = sum(1 for m in self.manuscripts for r in m['referees'] if r['status'] == 'Report Submitted')
            
            pdfs = sum(1 for m in self.manuscripts if m['pdf_downloaded'])
            covers = sum(1 for m in self.manuscripts if m['cover_letter_downloaded'])
            reports = sum(len(m['reports_downloaded']) for m in self.manuscripts)
            
            print(f"\n📊 Summary:")
            print(f"  Manuscripts: {len(self.manuscripts)}")
            print(f"\n  Referees: {total_refs}")
            print(f"    - Declined: {refs_declined}")
            print(f"    - Accepted: {refs_accepted}")
            print(f"    - Reports Submitted: {refs_submitted}")
            print(f"    - Pending/Invited: {total_refs - refs_declined - refs_accepted - refs_submitted}")
            print(f"\n  Documents:")
            print(f"    - PDFs: {pdfs}")
            print(f"    - Cover Letters: {covers}")
            print(f"    - Referee Reports: {reports}")
            
            return self.manuscripts
            
        except Exception as e:
            print(f"❌ Fatal error: {e}")
            self.save_screenshot("fatal_error")
            raise
        finally:
            if hasattr(self, 'driver'):
                self.driver.quit()


def main():
    """Main execution."""
    print("🚀 Starting Complete SICON Extraction")
    print("This version extracts referee status and ALL documents\n")
    
    extractor = CompleteSICONExtractor()
    try:
        results = extractor.run()
        print(f"\n✅ Successfully extracted {len(results)} manuscripts")
        return results
    except Exception as e:
        print(f"\n❌ Extraction failed: {e}")
        return None


if __name__ == "__main__":
    main()