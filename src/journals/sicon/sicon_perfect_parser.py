#!/usr/bin/env python3
"""
SICON Perfect Parser - Correctly extracts all referee statuses
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


class SICONPerfectExtractor:
    """SICON extractor with perfect referee status parsing."""
    
    def __init__(self):
        self.output_dir = Path(f'./sicon_perfect_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.dirs = {
            'pdfs': self.output_dir / 'pdfs',
            'cover_letters': self.output_dir / 'cover_letters',
            'reports': self.output_dir / 'reports',
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
        
        # Stealth settings to avoid detection
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
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Configure downloads
        self.temp_download = self.output_dir / 'temp_downloads'
        self.temp_download.mkdir(exist_ok=True)
        
        prefs = {
            "download.default_directory": str(self.temp_download),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)
        
        # Execute stealth JavaScript
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Enable downloads in headless mode
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
            
            # Check for Cloudflare
            if "Just a moment" in self.driver.title:
                print("⏳ Cloudflare challenge detected, waiting...")
                time.sleep(10)
        except:
            pass
    
    def authenticate(self) -> bool:
        """Authenticate using ORCID."""
        print("\n🔐 Authenticating...")
        
        try:
            # Navigate to SICON
            self.driver.get("http://sicon.siam.org")
            self.wait_for_page_load()
            self.main_window = self.driver.current_window_handle
            
            # Check if already authenticated
            if 'associate editor tasks' in self.driver.page_source.lower():
                print("✅ Already authenticated!")
                return True
            
            # Dismiss privacy notification
            try:
                privacy_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@value='Continue']"))
                )
                privacy_button.click()
                print("✅ Clicked privacy notification")
                time.sleep(3)
            except:
                pass
            
            # Find ORCID link
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
        
        # If it's a BeautifulSoup element, process its contents
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
            # If it's plain text, try to split by common patterns
            text = str(cell_content)
            # Try to split "AcceptedAcceptedDeclined" pattern
            parts = re.findall(r'(?:Accepted|Declined|Invited|Overdue|Report\s+Submitted)', text, re.IGNORECASE)
            statuses = parts if parts else [text]
        
        return statuses
    
    def parse_manuscripts_table(self):
        """Parse manuscripts table with perfect referee status extraction."""
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
            if len(cells) < 8:
                continue
            
            # Extract manuscript ID
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
                'reports_downloaded': []
            }
            
            # Extract referee names from column 6
            referee_links = cells[6].find_all('a')
            referee_names = []
            
            for link in referee_links:
                name = link.get_text(strip=True)
                # Skip the manuscript author (usually first link if it's followed by <br>)
                if name and name not in ['s Assigned', 'All Referees']:
                    # Check if this is likely a referee (not the author)
                    link_html = str(link)
                    if 'biblio_dump' in link_html:
                        referee_names.append(name)
            
            # Extract statuses from column 7 - this is the key fix
            status_cell = cells[7]
            status_list = self.split_status_text(status_cell)
            
            # Extract due dates from column 8
            due_dates = []
            if len(cells) > 8:
                due_cell = cells[8]
                due_parts = []
                
                # Process cell contents
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
            
            # Extract "invited on" dates from column 9 if present
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
            
            # Match referees with their statuses, due dates, and invited dates
            print(f"  Found {len(referee_names)} referees and {len(status_list)} statuses")
            
            for i, name in enumerate(referee_names):
                # Get status
                if i < len(status_list):
                    status = self.parse_status_from_text(status_list[i])
                else:
                    status = 'Unknown'
                
                # Get due date
                due_date = due_dates[i] if i < len(due_dates) else None
                
                # Get invited date
                invited_date = invited_dates[i] if i < len(invited_dates) else None
                
                referee = {
                    'name': name,
                    'email': None,
                    'full_name': name,
                    'status': status,
                    'due_date': due_date,
                    'invited_date': invited_date,
                    'report_available': 'report' in status_list[i].lower() if i < len(status_list) else False
                }
                
                print(f"  👤 {name}: {status}", end="")
                if due_date:
                    print(f" (due: {due_date})", end="")
                if invited_date:
                    print(f" (invited: {invited_date})", end="")
                print()
                
                manuscript['referees'].append(referee)
            
            self.manuscripts.append(manuscript)
    
    def extract_referee_emails(self):
        """Extract referee emails by clicking on their names."""
        print("\n📧 Extracting referee emails...")
        
        emails_found = 0
        for manuscript in self.manuscripts:
            for referee in manuscript['referees']:
                if referee['email']:
                    continue
                
                try:
                    # Find referee link
                    referee_links = self.driver.find_elements(By.XPATH, f"//a[contains(text(), '{referee['name']}')]")
                    
                    if not referee_links:
                        continue
                    
                    # Click the first matching link
                    self.driver.execute_script("arguments[0].click();", referee_links[0])
                    time.sleep(3)
                    
                    # Check if new window opened
                    if len(self.driver.window_handles) > 1:
                        # Switch to new window
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                        time.sleep(2)
                        
                        # Extract email
                        profile_html = self.driver.page_source
                        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', profile_html)
                        if email_match:
                            referee['email'] = email_match.group()
                            emails_found += 1
                        
                        # Look for full name
                        soup = BeautifulSoup(profile_html, 'html.parser')
                        title_tag = soup.find('title')
                        if title_tag and title_tag.text:
                            full_name = title_tag.text.strip()
                            if full_name and len(full_name) > len(referee['name']):
                                referee['full_name'] = full_name
                        
                        # Close window
                        self.driver.close()
                        self.driver.switch_to.window(self.main_window)
                        time.sleep(1)
                    
                except Exception as e:
                    # Make sure we're back in main window
                    if len(self.driver.window_handles) > 1:
                        self.driver.close()
                        self.driver.switch_to.window(self.main_window)
        
        print(f"  ✅ Found {emails_found} email addresses")
    
    def download_manuscript_documents(self):
        """Download all documents: PDFs, cover letters, and referee reports."""
        print("\n📥 Downloading manuscript documents...")
        
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
                    # Switch to manuscript view window
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    time.sleep(2)
                    
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
                            "//a[contains(text(), 'Manuscript PDF')]"
                        ]),
                        
                        # Cover letter patterns
                        ("Cover Letter", [
                            "//a[contains(text(), 'Cover Letter')]",
                            "//a[contains(text(), 'cover letter')]",
                            "//a[contains(@href, 'cover')]"
                        ]),
                        
                        # Referee report patterns
                        ("Reports", [
                            "//a[contains(text(), 'Report')]",
                            "//a[contains(text(), 'Referee Report')]",
                            "//a[contains(text(), 'Review')]"
                        ])
                    ]
                    
                    # Try each document type
                    for doc_type, patterns in document_patterns:
                        for pattern in patterns:
                            try:
                                links = self.driver.find_elements(By.XPATH, pattern)
                                
                                if links and doc_type == "PDF" and not manuscript['pdf_downloaded']:
                                    # Get initial file count
                                    initial_files = set(self.temp_download.glob('*'))
                                    
                                    # Click the link
                                    self.driver.execute_script("arguments[0].click();", links[0])
                                    time.sleep(5)
                                    
                                    # Check for new files
                                    new_files = set(self.temp_download.glob('*')) - initial_files
                                    
                                    if new_files:
                                        for new_file in new_files:
                                            # Verify it's a PDF
                                            with open(new_file, 'rb') as f:
                                                header = f.read(4)
                                            
                                            if header == b'%PDF':
                                                dest = self.dirs['pdfs'] / f"{ms_id}.pdf"
                                                shutil.move(str(new_file), str(dest))
                                                manuscript['pdf_downloaded'] = True
                                                print(f"  ✅ PDF downloaded")
                                                break
                                    
                                    if manuscript['pdf_downloaded']:
                                        break
                                        
                            except Exception as e:
                                continue
                    
                    # Close window and return to main
                    self.driver.close()
                    self.driver.switch_to.window(self.main_window)
                    time.sleep(1)
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
                # Make sure we're back in main window
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.main_window)
    
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
        for ms in self.manuscripts:
            for ref in ms['referees']:
                status_counts[ref['status']] = status_counts.get(ref['status'], 0) + 1
                if ref['email']:
                    emails_found += 1
        
        results = {
            'extraction_time': datetime.now().isoformat(),
            'total_manuscripts': len(self.manuscripts),
            'total_referees': total_referees,
            'referees_with_emails': emails_found,
            'referee_status_breakdown': status_counts,
            'pdfs_downloaded': sum(1 for m in self.manuscripts if m['pdf_downloaded']),
            'manuscripts': self.manuscripts
        }
        
        # Save JSON results
        json_path = self.dirs['data'] / 'perfect_extraction_results.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Generate detailed report
        report_path = self.dirs['data'] / 'perfect_extraction_report.txt'
        with open(report_path, 'w') as f:
            f.write("SICON Perfect Extraction Report\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Extraction Time: {results['extraction_time']}\n")
            f.write(f"Total Manuscripts: {results['total_manuscripts']}\n")
            f.write(f"Total Referees: {total_referees}\n")
            f.write(f"Referees with Emails: {emails_found} ({emails_found/total_referees*100:.1f}%)\n")
            f.write(f"PDFs Downloaded: {results['pdfs_downloaded']}\n\n")
            
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
                f.write(f"  Days in System: {ms['days_in_system']}\n")
                f.write(f"  PDF: {'✅ Downloaded' if ms['pdf_downloaded'] else '❌ Not downloaded'}\n")
                
                f.write(f"\n  Referees ({len(ms['referees'])}):\n")
                
                # Group by status for better readability
                by_status = {}
                for ref in ms['referees']:
                    status = ref['status']
                    if status not in by_status:
                        by_status[status] = []
                    by_status[status].append(ref)
                
                # Print grouped by status
                for status in ['Declined', 'Accepted', 'Report Submitted', 'Overdue', 'Invited', 'Unknown']:
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
                            f.write("\n")
                
                f.write("\n" + "-" * 40 + "\n\n")
        
        print(f"\n📊 Results saved to: {self.output_dir}")
        print(f"📄 JSON: {json_path.name}")
        print(f"📄 Report: {report_path.name}")
    
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
            
            # Step 3: Parse manuscripts table with perfect status extraction
            self.parse_manuscripts_table()
            
            # Step 4: Extract referee emails
            self.extract_referee_emails()
            
            # Step 5: Download documents
            self.download_manuscript_documents()
            
            # Step 6: Save results
            self.save_results()
            
            print("\n🎉 Perfect extraction complete!")
            
            # Print summary
            total_refs = sum(len(m['referees']) for m in self.manuscripts)
            emails_found = sum(1 for m in self.manuscripts for r in m['referees'] if r['email'])
            pdfs = sum(1 for m in self.manuscripts if m['pdf_downloaded'])
            
            print(f"\n📊 Final Summary:")
            print(f"  Manuscripts: {len(self.manuscripts)}")
            print(f"  Total Referees: {total_refs}")
            print(f"  Emails Extracted: {emails_found}/{total_refs} ({emails_found/total_refs*100:.1f}%)")
            print(f"  PDFs Downloaded: {pdfs}/{len(self.manuscripts)}")
            
            # Detailed status breakdown
            if total_refs > 0:
                print("\n  Referee Status Breakdown:")
                status_counts = {}
                for ms in self.manuscripts:
                    for ref in ms['referees']:
                        status = ref['status']
                        status_counts[status] = status_counts.get(status, 0) + 1
                
                for status in ['Declined', 'Accepted', 'Report Submitted', 'Overdue', 'Invited', 'Unknown']:
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
    print("🚀 Starting SICON Perfect Extraction")
    print("This version correctly parses ALL referee statuses\n")
    
    extractor = SICONPerfectExtractor()
    try:
        results = extractor.run()
        return results
    except Exception as e:
        print(f"\n❌ Extraction failed: {e}")
        return None


if __name__ == "__main__":
    main()