#!/usr/bin/env python3
"""
Enhanced PDF Extractor - Extracts all manuscript data including PDFs
Navigates to View Submission page to get authors, abstract, keywords, and PDFs
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
from selenium.webdriver.common.action_chains import ActionChains
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
logger = logging.getLogger("ENHANCED_PDF_EXTRACTOR")


class EnhancedPDFExtractor:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.output_dir = Path(f"{journal_name.lower()}_enhanced_results")
        self.output_dir.mkdir(exist_ok=True)
        self.pdf_dir = self.output_dir / "pdfs"
        self.pdf_dir.mkdir(exist_ok=True)
        
    def create_driver(self, headless=False):
        """Create Chrome driver with download configuration"""
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        # Configure Chrome to download PDFs instead of displaying them
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
            
    def navigate_to_view_submission(self, manuscript_id):
        """Navigate to View Submission page for a manuscript"""
        try:
            logger.info(f"🔍 Navigating to View Submission for {manuscript_id}")
            
            # Look for View Submission link
            view_links = self.driver.find_elements(By.PARTIAL_LINK_TEXT, "View Submission")
            
            if not view_links:
                logger.warning(f"   ⚠️  No View Submission link found")
                return False
                
            # Click the appropriate View Submission link
            for link in view_links:
                # Check if this link is associated with our manuscript
                parent_element = link.find_element(By.XPATH, "./ancestor::tr")
                if parent_element and manuscript_id in parent_element.text:
                    logger.info(f"   ✅ Found View Submission link for {manuscript_id}")
                    link.click()
                    time.sleep(3)
                    return True
                    
            # If no specific link found, click the first one
            view_links[0].click()
            time.sleep(3)
            return True
            
        except Exception as e:
            logger.error(f"❌ Error navigating to View Submission: {e}")
            return False
            
    def extract_submission_details(self):
        """Extract full submission details from View Submission page"""
        details = {
            'authors': [],
            'abstract': '',
            'keywords': [],
            'manuscript_pdf_url': ''
        }
        
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract authors
            author_section = soup.find(text=re.compile('Author.?s', re.IGNORECASE))
            if author_section:
                author_table = author_section.find_parent().find_next('table')
                if author_table:
                    author_rows = author_table.find_all('tr')[1:]  # Skip header
                    for row in author_rows:
                        cells = row.find_all('td')
                        if len(cells) >= 2:
                            author_name = cells[0].get_text(strip=True)
                            author_email = cells[1].get_text(strip=True) if len(cells) > 1 else ''
                            if author_name and not any(skip in author_name.lower() for skip in ['select', 'all', 'none']):
                                details['authors'].append({
                                    'name': author_name,
                                    'email': author_email
                                })
                                logger.info(f"   👤 Author: {author_name}")
            
            # Extract abstract
            abstract_section = soup.find(text=re.compile('Abstract', re.IGNORECASE))
            if abstract_section:
                abstract_container = abstract_section.find_parent().find_next(['div', 'td', 'p'])
                if abstract_container:
                    details['abstract'] = abstract_container.get_text(strip=True)
                    logger.info(f"   📝 Abstract: {details['abstract'][:100]}...")
            
            # Extract keywords
            keywords_section = soup.find(text=re.compile('Keywords', re.IGNORECASE))
            if keywords_section:
                keywords_container = keywords_section.find_parent().find_next(['div', 'td', 'p'])
                if keywords_container:
                    keywords_text = keywords_container.get_text(strip=True)
                    # Split by common delimiters
                    keywords = re.split(r'[;,\n]', keywords_text)
                    details['keywords'] = [k.strip() for k in keywords if k.strip() and len(k.strip()) > 2]
                    logger.info(f"   🏷️  Keywords: {', '.join(details['keywords'])}")
            
            # Find manuscript PDF link
            pdf_links = soup.find_all('a', href=re.compile(r'\.pdf|downloadFile|viewFile', re.IGNORECASE))
            for link in pdf_links:
                link_text = link.get_text(strip=True).lower()
                if any(term in link_text for term in ['manuscript', 'paper', 'download', 'pdf']):
                    href = link.get('href', '')
                    if href:
                        if href.startswith('/'):
                            details['manuscript_pdf_url'] = f"https://mc.manuscriptcentral.com{href}"
                        elif href.startswith('http'):
                            details['manuscript_pdf_url'] = href
                        else:
                            details['manuscript_pdf_url'] = f"https://mc.manuscriptcentral.com/{self.journal_name.lower()}/{href}"
                        logger.info(f"   📄 Found manuscript PDF URL")
                        break
                        
        except Exception as e:
            logger.error(f"❌ Error extracting submission details: {e}")
            
        return details
        
    def download_pdf_with_session(self, pdf_url, filename):
        """Download PDF using current session cookies"""
        try:
            # Get cookies from Selenium
            cookies = self.driver.get_cookies()
            
            # Create requests session with cookies
            session = requests.Session()
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'])
                
            # Add headers to mimic browser
            headers = {
                'User-Agent': self.driver.execute_script("return navigator.userAgent;"),
                'Accept': 'application/pdf,*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': self.driver.current_url
            }
            
            # Download PDF
            response = session.get(pdf_url, headers=headers, stream=True)
            response.raise_for_status()
            
            # Save PDF
            pdf_path = self.pdf_dir / filename
            with open(pdf_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
                
            logger.info(f"   ✅ PDF saved to: {pdf_path}")
            return str(pdf_path)
            
        except Exception as e:
            logger.error(f"   ❌ Error downloading PDF: {e}")
            return None
            
    def extract_with_pdfs(self, headless=True):
        """Extract all data including PDFs"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 ENHANCED PDF EXTRACTION - {self.journal_name}")
        logger.info(f"{'='*80}")
        
        self.create_driver(headless=headless)
        all_results = {
            'journal': self.journal_name,
            'extraction_date': datetime.now().isoformat(),
            'extraction_method': 'enhanced_with_pdfs',
            'manuscripts': []
        }
        
        try:
            # Login
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
                logger.info(f"📄 Processing manuscript: {ms_id}")
                logger.info(f"Expected title: {ms_info['title']}")
                
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
                    'extraction_status': 'pending',
                    'manuscript_pdf_path': '',
                    'referee_reports': []
                }
                
                try:
                    # First, click checkbox to get referee data
                    found_checkbox = None
                    table = self.driver.find_element(By.TAG_NAME, "table")
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    
                    for i, row in enumerate(rows):
                        row_text = row.text.strip()
                        if row_text.startswith(ms_id):
                            row_checkboxes = row.find_elements(By.XPATH, ".//img[contains(@src, 'check_off.gif')]")
                            if len(row_checkboxes) == 1:
                                found_checkbox = row_checkboxes[0]
                                logger.info(f"✅ Found checkbox for {ms_id}")
                                break
                                
                    if found_checkbox:
                        # Click checkbox to get referee details
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", found_checkbox)
                        time.sleep(0.5)
                        found_checkbox.click()
                        time.sleep(3)
                        
                        # Extract referee data inline
                        manuscript_data = self.extract_referee_details_inline(manuscript_data)
                        
                        # Navigate back to manuscript list
                        logger.info("🔄 Navigating back to manuscript list...")
                        ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
                        ae_link.click()
                        time.sleep(2)
                        category_link = self.driver.find_element(By.LINK_TEXT, category)
                        category_link.click()
                        time.sleep(3)
                        
                        # Now navigate to View Submission for full details
                        if self.navigate_to_view_submission(ms_id):
                            submission_details = self.extract_submission_details()
                            manuscript_data.update(submission_details)
                            
                            # Download manuscript PDF if URL found
                            if manuscript_data.get('manuscript_pdf_url'):
                                pdf_path = self.download_pdf_with_session(
                                    manuscript_data['manuscript_pdf_url'],
                                    f"{ms_id}_manuscript.pdf"
                                )
                                if pdf_path:
                                    manuscript_data['manuscript_pdf_path'] = pdf_path
                                    
                            # Navigate back
                            logger.info("🔄 Navigating back from View Submission...")
                            self.driver.back()
                            time.sleep(2)
                            
                        # Download referee reports for completed referees
                        for ref in manuscript_data.get('completed_referees', []):
                            if ref.get('report_url'):
                                report_path = self.download_referee_report_safe(
                                    ref['report_url'],
                                    ref['name'],
                                    ms_id
                                )
                                if report_path:
                                    manuscript_data['referee_reports'].append({
                                        'referee': ref['name'],
                                        'report_path': report_path
                                    })
                                    
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
            
    def extract_referee_details_inline(self, manuscript_data):
        """Extract referee details from the referee page"""
        logger.info("📊 Extracting referee details...")
        
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            page_text = soup.get_text()
            
            # Extract manuscript title
            title_match = re.search(r'Title:\s*([^\n]+)', page_text)
            if title_match:
                manuscript_data['title'] = title_match.group(1).strip()
                
            # Extract dates
            submitted_match = re.search(r'Date Submitted:\s*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', page_text)
            if submitted_match:
                manuscript_data['submitted_date'] = submitted_match.group(1)
                
            due_match = re.search(r'Date Due:\s*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', page_text)
            if due_match:
                manuscript_data['due_date'] = due_match.group(1)
                
            # Extract status
            status_match = re.search(r'Status:\s*([^\n]+)', page_text)
            if status_match:
                manuscript_data['status'] = status_match.group(1).strip()
                
            # Look for reviewer table
            reviewer_list_header = soup.find(text=re.compile('Reviewer List', re.IGNORECASE))
            
            if reviewer_list_header:
                logger.info("✅ Found Reviewer List section")
                
                # Find the table containing reviewer information
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
                            # Extract referee info
                            name = ''
                            status = ''
                            
                            # Look for name in first few cells
                            for cell in cells[:5]:
                                cell_text = cell.get_text(strip=True)
                                name_match = re.search(r'([A-Za-z]+,\s*[A-Za-z]+)', cell_text)
                                if name_match:
                                    name = name_match.group(1).strip()
                                    break
                                    
                            # Look for status
                            for cell in cells:
                                cell_text = cell.get_text(strip=True).lower()
                                if any(keyword in cell_text for keyword in ['minor revision', 'major revision', 'accept', 'reject', 'agreed']):
                                    status = cell.get_text(strip=True)
                                    break
                                    
                            if name:
                                referee_info = {
                                    'name': name,
                                    'status': status
                                }
                                
                                # Check if report submitted
                                if any(keyword in status.lower() for keyword in ['minor revision', 'major revision', 'accept', 'reject']):
                                    referee_info['report_submitted'] = True
                                    completed_referees.append(referee_info)
                                else:
                                    referees.append(referee_info)
                                    
                    # Enhance with email dates
                    manuscript_data['referees'] = self.enhance_referees_with_email_dates(referees, manuscript_data['manuscript_id'])
                    manuscript_data['completed_referees'] = completed_referees
                    manuscript_data['extraction_status'] = 'success'
                    
        except Exception as e:
            logger.error(f"Error extracting referee details: {e}")
            manuscript_data['extraction_status'] = 'error'
            
        return manuscript_data
        
    def enhance_referees_with_email_dates(self, referees, manuscript_id):
        """Enhance referee data with acceptance/contact dates from emails"""
        try:
            logger.info("📧 Fetching starred emails...")
            flagged_emails, starred_emails = fetch_starred_emails()
            
            for referee in referees:
                name = referee['name']
                email_match_fn = robust_match_email_for_referee_mf if self.journal_name == "MF" else robust_match_email_for_referee_mor
                
                # Get acceptance and contact emails
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
                    logger.info(f"   ✔️  Found acceptance email for {name}")
                    
                if contact_email:
                    referee['contact_date'] = contact_email['date']
                    if not referee.get('email'):
                        referee['email'] = contact_email['to']
                    logger.info(f"   ✔️  Found contact email for {name}")
                    
        except Exception as e:
            logger.warning(f"⚠️  Could not fetch emails: {e}")
            
        return referees
            
    def download_referee_report_safe(self, report_url, referee_name, manuscript_id):
        """Download referee report using session cookies"""
        if not report_url:
            return None
            
        try:
            logger.info(f"📥 Downloading report for {referee_name}")
            
            # Extract actual URL from JavaScript if needed
            if report_url.startswith('javascript:'):
                url_match = re.search(r"popWindow\('([^']+)'", report_url)
                if url_match:
                    actual_path = url_match.group(1)
                    full_url = f"https://mc.manuscriptcentral.com/{actual_path}"
                else:
                    logger.warning(f"   ⚠️  Could not extract URL from JavaScript")
                    return None
            else:
                full_url = report_url
                
            # Download using session cookies
            safe_name = referee_name.replace(' ', '_').replace(',', '')
            filename = f"{manuscript_id}_{safe_name}_report.pdf"
            
            return self.download_pdf_with_session(full_url, filename)
            
        except Exception as e:
            logger.error(f"❌ Error downloading report: {e}")
            return None
            
    def save_results(self, results):
        """Save extraction results"""
        # Save JSON
        json_file = self.output_dir / f"{self.journal_name.lower()}_enhanced_results.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"\n✅ Results saved to: {json_file}")
        
        # Generate summary report
        report_file = self.output_dir / f"{self.journal_name.lower()}_enhanced_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"ENHANCED PDF EXTRACTION - {self.journal_name}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*80}\n\n")
            
            for ms in results['manuscripts']:
                f.write(f"Manuscript: {ms['manuscript_id']}\n")
                f.write(f"Title: {ms.get('title', 'N/A')}\n")
                f.write(f"Authors: {', '.join([a['name'] for a in ms.get('authors', [])])}\n")
                f.write(f"Abstract: {ms.get('abstract', '')[:200]}...\n" if ms.get('abstract') else "Abstract: N/A\n")
                f.write(f"Keywords: {', '.join(ms.get('keywords', []))}\n")
                f.write(f"Manuscript PDF: {'✅ Downloaded' if ms.get('manuscript_pdf_path') else '❌ Not downloaded'}\n")
                f.write(f"Referee Reports: {len(ms.get('referee_reports', []))} downloaded\n")
                f.write(f"\nActive Referees:\n")
                for ref in ms.get('referees', []):
                    f.write(f"  • {ref['name']} ({ref.get('email', 'No email')})\n")
                f.write(f"\nCompleted Referees:\n")
                for ref in ms.get('completed_referees', []):
                    f.write(f"  • {ref['name']} - {ref.get('review_decision', 'N/A')}\n")
                f.write(f"\n{'-'*80}\n\n")
                
        logger.info(f"✅ Report saved to: {report_file}")


def main():
    """Main function"""
    import argparse
    parser = argparse.ArgumentParser(description='Enhanced PDF Extractor')
    parser.add_argument('journal', choices=['MF', 'MOR'], help='Journal to extract')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    
    args = parser.parse_args()
    
    extractor = EnhancedPDFExtractor(args.journal)
    extractor.extract_with_pdfs(headless=args.headless)


if __name__ == '__main__':
    main()