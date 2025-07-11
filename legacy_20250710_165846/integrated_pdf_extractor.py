#!/usr/bin/env python3
"""
Integrated PDF Extractor - Combines referee extraction with PDF downloads
Uses the working checkbox approach and adds PDF download capability
"""

import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json
import re
import requests
import shutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from journals.mf import MFJournal
from journals.mor import MORJournal
from core.email_utils import fetch_starred_emails, robust_match_email_for_referee_mf, robust_match_email_for_referee_mor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("INTEGRATED_PDF_EXTRACTOR")


class IntegratedPDFExtractor:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.output_dir = Path(f"{journal_name.lower()}_integrated_results")
        self.output_dir.mkdir(exist_ok=True)
        self.pdf_dir = self.output_dir / "pdfs"
        self.pdf_dir.mkdir(exist_ok=True)
        
    def create_driver(self, headless=False):
        """Create Chrome driver with download configuration"""
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        # Configure Chrome to download PDFs
        prefs = {
            "download.default_directory": str(self.pdf_dir.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        
        if headless:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
        
        try:
            self.driver = uc.Chrome(options=options)
        except:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            chrome_options = Options()
            for arg in options.arguments:
                chrome_options.add_argument(arg)
            chrome_options.add_experimental_option("prefs", prefs)
            self.driver = webdriver.Chrome(options=chrome_options)
            
    def download_pdf_with_session(self, pdf_url, filename):
        """Download PDF using current session cookies"""
        try:
            logger.info(f"   📥 Downloading: {filename}")
            
            # Get cookies from Selenium
            cookies = self.driver.get_cookies()
            
            # Create requests session with cookies
            session = requests.Session()
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'])
                
            # Add headers
            headers = {
                'User-Agent': self.driver.execute_script("return navigator.userAgent;"),
                'Accept': 'application/pdf,*/*',
                'Referer': self.driver.current_url
            }
            
            # Download PDF
            response = session.get(pdf_url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Check if response is actually a PDF
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' not in content_type.lower() and response.content[:4] != b'%PDF':
                logger.warning(f"   ⚠️  Response is not a PDF (Content-Type: {content_type})")
                return None
                
            # Save PDF
            pdf_path = self.pdf_dir / filename
            with open(pdf_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
                
            file_size = pdf_path.stat().st_size
            logger.info(f"   ✅ PDF saved: {pdf_path} ({file_size:,} bytes)")
            return str(pdf_path)
            
        except Exception as e:
            logger.error(f"   ❌ Download failed: {e}")
            return None
            
    def extract_with_pdfs(self, headless=True):
        """Extract referee data and PDFs using the working checkbox method"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 INTEGRATED PDF EXTRACTION - {self.journal_name}")
        logger.info(f"{'='*80}")
        
        self.create_driver(headless=headless)
        all_results = {
            'journal': self.journal_name,
            'extraction_date': datetime.now().isoformat(),
            'extraction_method': 'integrated_with_pdfs',
            'manuscripts': []
        }
        
        try:
            # Setup journal and manuscripts
            if self.journal_name == "MF":
                self.journal = MFJournal(self.driver, debug=True)
                category = "Awaiting Reviewer Scores"
                expected_manuscripts = {
                    'MAFI-2024-0167': {
                        'title': 'Competitive optimal portfolio selection in a non-Markovian financial market',
                        'expected_referees': 2
                    },
                    'MAFI-2025-0166': {
                        'title': 'Optimal investment and consumption under forward utilities with relative performance concerns',
                        'expected_referees': 2
                    }
                }
            else:
                self.journal = MORJournal(self.driver, debug=True)
                category = "Awaiting Reviewer Reports"
                expected_manuscripts = {
                    'MOR-2025-1037': {
                        'title': 'The Value of Partial Information',
                        'expected_referees': 2
                    },
                    'MOR-2023-0376': {
                        'title': 'Utility maximization under endogenous pricing',
                        'expected_referees': 2
                    },
                    'MOR-2023-0376.R1': {
                        'title': 'Utility maximization under endogenous pricing',
                        'expected_referees': 1
                    },
                    'MOR-2024-0804': {
                        'title': 'Semi-static variance-optimal hedging with self-exciting jumps',
                        'expected_referees': 2
                    }
                }
                
            # Login
            self.journal.login()
            
            # Navigate to AE Center
            ae_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            time.sleep(2)
            
            # Navigate to category
            category_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, category))
            )
            category_link.click()
            time.sleep(3)
            
            # Process each manuscript
            for ms_id, ms_info in expected_manuscripts.items():
                logger.info(f"\n{'='*60}")
                logger.info(f"📄 Processing: {ms_id}")
                
                manuscript_data = {
                    'manuscript_id': ms_id,
                    'expected_title': ms_info['title'],
                    'expected_referees': ms_info['expected_referees'],
                    'title': '',
                    'authors': [],
                    'abstract': '',
                    'keywords': [],
                    'referees': [],
                    'completed_referees': [],
                    'manuscript_pdf_path': ''
                }
                
                try:
                    # STEP 1: Click checkbox to get referee data (using working method)
                    found_checkbox = None
                    table = self.driver.find_element(By.TAG_NAME, "table")
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    
                    for row in rows:
                        row_text = row.text.strip()
                        if row_text.startswith(ms_id):
                            row_checkboxes = row.find_elements(By.XPATH, ".//img[contains(@src, 'check_off.gif')]")
                            if len(row_checkboxes) == 1:
                                found_checkbox = row_checkboxes[0]
                                logger.info(f"✅ Found checkbox for {ms_id}")
                                break
                                
                    if found_checkbox:
                        # Click checkbox
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", found_checkbox)
                        time.sleep(0.5)
                        found_checkbox.click()
                        time.sleep(3)
                        
                        # Extract referee data (reuse working logic)
                        manuscript_data = self.extract_referee_details(manuscript_data)
                        
                        # STEP 2: Look for PDF on this page
                        logger.info("🔍 Looking for PDF on referee page...")
                        
                        # Try clicking PDF tab
                        try:
                            pdf_tab = self.driver.find_element(By.LINK_TEXT, "PDF")
                            logger.info("📄 Found PDF tab, clicking...")
                            pdf_tab.click()
                            time.sleep(2)
                            
                            # Look for download link
                            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                            pdf_frame = soup.find('iframe', src=re.compile(r'\.pdf|downloadFile', re.I))
                            if pdf_frame:
                                pdf_url = pdf_frame.get('src', '')
                                if pdf_url:
                                    if pdf_url.startswith('/'):
                                        pdf_url = f"https://mc.manuscriptcentral.com{pdf_url}"
                                    elif not pdf_url.startswith('http'):
                                        pdf_url = f"https://mc.manuscriptcentral.com/{self.journal_name.lower()}/{pdf_url}"
                                        
                                    # Download PDF
                                    pdf_path = self.download_pdf_with_session(pdf_url, f"{ms_id}_manuscript.pdf")
                                    if pdf_path:
                                        manuscript_data['manuscript_pdf_path'] = pdf_path
                                        
                        except Exception as e:
                            logger.info(f"   ℹ️  PDF tab not available: {e}")
                            
                        # Try Abstract tab for better data
                        try:
                            abstract_tab = self.driver.find_element(By.LINK_TEXT, "Abstract")
                            logger.info("📝 Found Abstract tab, clicking...")
                            abstract_tab.click()
                            time.sleep(1)
                            
                            # Extract better abstract
                            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                            # Look for abstract in various containers
                            for container in soup.find_all(['div', 'td', 'p']):
                                text = container.get_text(strip=True)
                                if len(text) > 100 and 'abstract' not in text.lower()[:20]:
                                    manuscript_data['abstract'] = text
                                    logger.info(f"   📝 Abstract: {text[:100]}...")
                                    break
                                    
                        except:
                            pass
                            
                        # Navigate back to manuscript list
                        logger.info("🔄 Navigating back to Associate Editor Center...")
                        ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
                        ae_link.click()
                        time.sleep(2)
                        category_link = self.driver.find_element(By.LINK_TEXT, category)
                        category_link.click()
                        time.sleep(3)
                        
                except Exception as e:
                    logger.error(f"Error processing {ms_id}: {e}")
                    manuscript_data['extraction_status'] = 'error'
                    manuscript_data['error'] = str(e)
                    
                all_results['manuscripts'].append(manuscript_data)
                
            # Save results
            self.save_results(all_results)
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            
        finally:
            self.driver.quit()
            
    def extract_referee_details(self, manuscript_data):
        """Extract referee details from the referee page (reuse working logic)"""
        logger.info("📊 Extracting referee details...")
        
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            page_text = soup.get_text()
            
            # Extract title
            title_match = re.search(r'([^:]+)$', manuscript_data['manuscript_id'])
            if title_match:
                # Look for actual title in page
                lines = page_text.split('\n')
                for i, line in enumerate(lines):
                    if manuscript_data['manuscript_id'] in line:
                        # Title might be on next line
                        if i + 1 < len(lines):
                            potential_title = lines[i + 1].strip()
                            if len(potential_title) > 10 and not any(skip in potential_title.lower() for skip in ['submitted', 'status', 'date']):
                                manuscript_data['title'] = potential_title
                                break
                                
            # Extract dates and status
            submitted_match = re.search(r'Date Submitted:\s*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', page_text)
            if submitted_match:
                manuscript_data['submitted_date'] = submitted_match.group(1)
                
            due_match = re.search(r'Date Due:\s*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', page_text)
            if due_match:
                manuscript_data['due_date'] = due_match.group(1)
                
            status_match = re.search(r'Status:\s*([^\n]+)', page_text)
            if status_match:
                manuscript_data['status'] = status_match.group(1).strip()
                
            # Extract referees
            reviewer_list_header = soup.find(text=re.compile('Reviewer List', re.IGNORECASE))
            
            if reviewer_list_header:
                reviewer_section = reviewer_list_header.find_parent()
                while reviewer_section and reviewer_section.name != 'table':
                    reviewer_section = reviewer_section.find_next('table')
                    
                if reviewer_section:
                    rows = reviewer_section.find_all('tr')
                    referees = []
                    completed_referees = []
                    
                    for row in rows[1:]:  # Skip header
                        cells = row.find_all('td')
                        if len(cells) >= 4:
                            # Extract name
                            name = ''
                            for cell in cells[:5]:
                                cell_text = cell.get_text(strip=True)
                                name_match = re.search(r'([A-Za-z]+,\s*[A-Za-z]+)', cell_text)
                                if name_match:
                                    name = name_match.group(1).strip()
                                    break
                                    
                            if name:
                                # Extract status and other info
                                referee_info = {'name': name}
                                
                                # Look for status keywords
                                row_text = row.get_text().lower()
                                if any(keyword in row_text for keyword in ['minor revision', 'major revision', 'accept', 'reject']):
                                    referee_info['report_submitted'] = True
                                    completed_referees.append(referee_info)
                                elif 'agreed' in row_text:
                                    referees.append(referee_info)
                                    
                    # Enhance with email dates
                    referees = self.enhance_referees_with_email_dates(referees, manuscript_data['manuscript_id'])
                    
                    manuscript_data['referees'] = referees
                    manuscript_data['completed_referees'] = completed_referees
                    manuscript_data['extraction_status'] = 'success'
                    
        except Exception as e:
            logger.error(f"Error extracting details: {e}")
            manuscript_data['extraction_status'] = 'error'
            
        return manuscript_data
        
    def enhance_referees_with_email_dates(self, referees, manuscript_id):
        """Add email dates to referees"""
        try:
            logger.info("📧 Fetching email dates...")
            flagged_emails, starred_emails = fetch_starred_emails()
            
            for referee in referees:
                name = referee['name']
                email_match_fn = robust_match_email_for_referee_mf if self.journal_name == "MF" else robust_match_email_for_referee_mor
                
                acceptance_email, contact_email = email_match_fn(
                    name,
                    manuscript_id,
                    "agreed",
                    flagged_emails,
                    starred_emails
                )
                
                if acceptance_email:
                    referee['acceptance_date'] = acceptance_email['date']
                    referee['email'] = acceptance_email['to']
                    
                if contact_email:
                    referee['contact_date'] = contact_email['date']
                    if not referee.get('email'):
                        referee['email'] = contact_email['to']
                        
        except Exception as e:
            logger.warning(f"⚠️  Could not fetch emails: {e}")
            
        return referees
        
    def save_results(self, results):
        """Save extraction results"""
        # Save JSON
        json_file = self.output_dir / f"{self.journal_name.lower()}_integrated_results.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"\n✅ Results saved to: {json_file}")
        
        # Generate report
        report_file = self.output_dir / f"{self.journal_name.lower()}_integrated_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"INTEGRATED PDF EXTRACTION - {self.journal_name}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*80}\n\n")
            
            for ms in results['manuscripts']:
                f.write(f"Manuscript: {ms['manuscript_id']}\n")
                f.write(f"Title: {ms.get('title', 'N/A')}\n")
                f.write(f"Abstract: {ms.get('abstract', '')[:200]}...\n" if ms.get('abstract') else "Abstract: N/A\n")
                f.write(f"PDF Downloaded: {'✅' if ms.get('manuscript_pdf_path') else '❌'}\n")
                f.write(f"\nActive Referees:\n")
                for ref in ms.get('referees', []):
                    f.write(f"  • {ref['name']}")
                    if ref.get('email'):
                        f.write(f" ({ref['email']})")
                    if ref.get('acceptance_date'):
                        f.write(f" - Accepted: {ref['acceptance_date']}")
                    f.write("\n")
                f.write(f"\nCompleted Referees:\n")
                for ref in ms.get('completed_referees', []):
                    f.write(f"  • {ref['name']} - Report submitted\n")
                f.write(f"\n{'-'*80}\n\n")
                
        logger.info(f"✅ Report saved to: {report_file}")


def main():
    """Main function"""
    import argparse
    parser = argparse.ArgumentParser(description='Integrated PDF Extractor')
    parser.add_argument('journal', choices=['MF', 'MOR'], help='Journal to extract')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    
    args = parser.parse_args()
    
    extractor = IntegratedPDFExtractor(args.journal)
    extractor.extract_with_pdfs(headless=args.headless)


if __name__ == '__main__':
    main()