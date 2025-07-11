#!/usr/bin/env python3
"""
SICON Final Parser - Correctly matches referee names with their statuses
"""

import os
import re
import time
import json
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()


class SICONFinalParser:
    """SICON parser with correct referee-status matching."""
    
    def __init__(self):
        self.output_dir = Path(f'./sicon_parsed_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        self.output_dir.mkdir(exist_ok=True)
        self.manuscripts = []
        print(f"📁 Output directory: {self.output_dir}")
    
    def setup_driver(self):
        """Setup Chrome driver."""
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)
        print("✅ Chrome driver initialized")
    
    def authenticate(self) -> bool:
        """Authenticate using ORCID."""
        print("\n🔐 Authenticating...")
        
        try:
            # Navigate to SICON
            self.driver.get("http://sicon.siam.org")
            time.sleep(5)
            
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
    
    def parse_status_text(self, text: str) -> tuple:
        """Parse status text like 'Accepted', 'Declined', or dates."""
        text = text.strip()
        
        if not text or text == '&nbsp;' or text == ' ':
            return ('Invited', None)
        
        text_lower = text.lower()
        
        if 'declined' in text_lower:
            return ('Declined', text)
        elif 'accepted' in text_lower:
            return ('Accepted', text)
        elif 'submitted' in text_lower or 'report' in text_lower:
            return ('Report Submitted', text)
        elif 'overdue' in text_lower:
            return ('Overdue', text)
        elif re.match(r'\d{4}-\d{2}-\d{2}', text):  # Date pattern
            return ('Has Due Date', text)
        else:
            return ('Invited', text)
    
    def parse_manuscripts_table(self):
        """Parse manuscripts table with correct referee-status matching."""
        print("\n📊 Parsing manuscripts table...")
        
        # Save page source
        debug_file = self.output_dir / 'manuscripts_table.html'
        with open(debug_file, 'w', encoding='utf-8') as f:
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
            if len(cells) < 8:  # Need at least 8 cells
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
                'referees': []
            }
            
            # Column 6 has referee names (with <a> tags)
            # Column 7 has statuses (text)
            # Column 8 has due dates
            
            # Extract referee names from links
            referee_links = cells[6].find_all('a')
            referee_names = []
            for link in referee_links:
                name = link.get_text(strip=True)
                # Skip the first author link (manuscript author)
                if name and len(referee_names) > 0 or cells[6].find_all('br'):
                    referee_names.append(name)
            
            # Get status texts (split by <br>)
            status_html = str(cells[7])
            status_parts = status_html.split('<br>')
            statuses = []
            for part in status_parts:
                # Clean HTML tags
                clean_text = re.sub(r'<[^>]+>', '', part).strip()
                if clean_text:
                    status, detail = self.parse_status_text(clean_text)
                    statuses.append({'status': status, 'detail': detail})
            
            # Get due dates if available
            due_dates = []
            if len(cells) > 8:
                due_html = str(cells[8])
                due_parts = due_html.split('<br>')
                for part in due_parts:
                    clean_text = re.sub(r'<[^>]+>', '', part).strip()
                    if clean_text and clean_text != '&nbsp;':
                        due_dates.append(clean_text)
            
            # Match referees with statuses
            for i, name in enumerate(referee_names):
                referee = {
                    'name': name,
                    'status': statuses[i]['status'] if i < len(statuses) else 'Unknown',
                    'status_detail': statuses[i]['detail'] if i < len(statuses) else None,
                    'due_date': due_dates[i] if i < len(due_dates) else None
                }
                
                print(f"  👤 {referee['name']}: {referee['status']}", end="")
                if referee['due_date']:
                    print(f" (due: {referee['due_date']})", end="")
                print()
                
                manuscript['referees'].append(referee)
            
            self.manuscripts.append(manuscript)
    
    def save_results(self):
        """Save extraction results with detailed status breakdown."""
        # Calculate statistics
        status_counts = {
            'Declined': 0,
            'Accepted': 0,
            'Report Submitted': 0,
            'Overdue': 0,
            'Invited': 0,
            'Has Due Date': 0,
            'Unknown': 0
        }
        
        for ms in self.manuscripts:
            for ref in ms['referees']:
                status = ref['status']
                if status in status_counts:
                    status_counts[status] += 1
                else:
                    status_counts['Unknown'] += 1
        
        total_referees = sum(len(m['referees']) for m in self.manuscripts)
        
        results = {
            'extraction_time': datetime.now().isoformat(),
            'total_manuscripts': len(self.manuscripts),
            'total_referees': total_referees,
            'referee_status_breakdown': status_counts,
            'manuscripts': self.manuscripts
        }
        
        # Save JSON results
        json_path = self.output_dir / 'parsed_results.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Generate detailed report
        report_path = self.output_dir / 'parsing_report.txt'
        with open(report_path, 'w') as f:
            f.write("SICON Referee Status Report\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Extraction Time: {results['extraction_time']}\n")
            f.write(f"Total Manuscripts: {results['total_manuscripts']}\n")
            f.write(f"Total Referees: {total_referees}\n\n")
            
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
                
                f.write(f"\n  Referees ({len(ms['referees'])}):\n")
                
                # Group by status
                by_status = {}
                for ref in ms['referees']:
                    status = ref['status']
                    if status not in by_status:
                        by_status[status] = []
                    by_status[status].append(ref)
                
                # Print grouped by status
                for status in ['Declined', 'Accepted', 'Has Due Date', 'Report Submitted', 'Overdue', 'Invited']:
                    if status in by_status:
                        f.write(f"\n    {status}:\n")
                        for ref in by_status[status]:
                            f.write(f"      - {ref['name']}")
                            if ref['due_date']:
                                f.write(f" (due: {ref['due_date']})")
                            if ref['status_detail'] and ref['status_detail'] != status:
                                f.write(f" [{ref['status_detail']}]")
                            f.write("\n")
                
                f.write("\n" + "-" * 40 + "\n\n")
        
        print(f"\n📊 Results saved to: {self.output_dir}")
        print(f"📄 JSON: {json_path.name}")
        print(f"📄 Report: {report_path.name}")
    
    def run(self):
        """Run the parser."""
        try:
            self.setup_driver()
            
            # Step 1: Authenticate
            if not self.authenticate():
                raise Exception("Authentication failed")
            
            # Step 2: Navigate to manuscripts
            if not self.navigate_to_manuscripts():
                raise Exception("Navigation failed")
            
            # Step 3: Parse manuscripts table
            self.parse_manuscripts_table()
            
            # Step 4: Save results
            self.save_results()
            
            print("\n🎉 Parsing complete!")
            
            # Print summary
            total_refs = sum(len(m['referees']) for m in self.manuscripts)
            print(f"\n📊 Summary:")
            print(f"  Manuscripts: {len(self.manuscripts)}")
            print(f"  Total Referees: {total_refs}")
            
            if total_refs > 0:
                print("\n  Status Breakdown:")
                status_counts = {}
                for ms in self.manuscripts:
                    for ref in ms['referees']:
                        status = ref['status']
                        status_counts[status] = status_counts.get(status, 0) + 1
                
                for status, count in sorted(status_counts.items()):
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
    print("🚀 Starting SICON Final Parser")
    print("Correctly matches referee names with their statuses\n")
    
    parser = SICONFinalParser()
    try:
        results = parser.run()
        return results
    except Exception as e:
        print(f"\n❌ Parsing failed: {e}")
        return None


if __name__ == "__main__":
    main()