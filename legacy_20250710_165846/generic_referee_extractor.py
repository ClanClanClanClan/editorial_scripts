#!/usr/bin/env python3
"""
Generic Referee Extractor - Works with any ScholarOne journal
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

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from journals.base_journal import BaseJournal
from core.email_utils import fetch_starred_emails
from core.generic_email_utils import robust_match_email_for_referee_generic

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GENERIC_REFEREE_EXTRACTOR")


class GenericRefereeExtractor:
    """Generic referee extractor that works with any configured journal"""
    
    def __init__(self, journal_code: str):
        self.journal_code = journal_code
        self.driver = None
        self.journal = None
        self.output_dir = Path(f"{journal_code.lower()}_results")
        self.output_dir.mkdir(exist_ok=True)
        
    def create_driver(self, headless=False):
        """Create Chrome driver"""
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
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
            self.driver = webdriver.Chrome(options=chrome_options)
            
    def extract_referee_data(self, manuscript_ids: list = None, headless=True):
        """Extract referee data for specified manuscripts or all manuscripts"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 GENERIC REFEREE EXTRACTION - {self.journal_code}")
        logger.info(f"{'='*80}")
        
        self.create_driver(headless=headless)
        all_results = {
            'journal': self.journal_code,
            'extraction_date': datetime.now().isoformat(),
            'extraction_method': 'generic_checkbox_clicks',
            'manuscripts': []
        }
        
        try:
            # Initialize journal handler
            self.journal = BaseJournal(self.journal_code, self.driver, debug=True)
            
            # Login
            if not self.journal.login():
                raise Exception("Login failed")
                
            # Navigate to AE Center
            if not self.journal.navigate_to_ae_center():
                raise Exception("Failed to navigate to AE Center")
                
            # Navigate to manuscript category
            if not self.journal.navigate_to_category():
                raise Exception("Failed to navigate to manuscript category")
                
            # Get all manuscripts if none specified
            if manuscript_ids is None:
                manuscript_ids = self.get_all_manuscript_ids()
                
            # Process each manuscript
            for ms_id in manuscript_ids:
                logger.info(f"\n{'='*60}")
                logger.info(f"📄 Processing: {ms_id}")
                
                manuscript_data = {
                    'manuscript_id': ms_id,
                    'title': '',
                    'referees': [],
                    'completed_referees': [],
                    'extraction_status': 'pending'
                }
                
                try:
                    # Click checkbox to get referee data
                    if self.journal.click_manuscript_checkbox(ms_id):
                        # Extract referee details
                        manuscript_data = self.extract_referee_details(manuscript_data)
                        
                        # Navigate back
                        self.journal.navigate_back_to_ae_center()
                        self.journal.navigate_to_category()
                    else:
                        logger.warning(f"Could not find checkbox for {ms_id}")
                        manuscript_data['extraction_status'] = 'checkbox_not_found'
                        
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
            if self.driver:
                self.driver.quit()
                
        return all_results
        
    def get_all_manuscript_ids(self) -> list:
        """Extract all manuscript IDs from the current page"""
        manuscript_ids = []
        
        try:
            table = self.journal.get_manuscript_table()
            if table:
                rows = table.find_elements(By.TAG_NAME, "tr")
                
                for row in rows:
                    row_text = row.text.strip()
                    # Look for manuscript ID pattern (e.g., MOR-2023-1234)
                    match = re.match(r'^([A-Z]+-\d{4}-\d+(?:\.[A-Z]\d+)?)', row_text)
                    if match:
                        ms_id = match.group(1)
                        manuscript_ids.append(ms_id)
                        logger.info(f"Found manuscript: {ms_id}")
                        
        except Exception as e:
            logger.error(f"Error getting manuscript IDs: {e}")
            
        return manuscript_ids
        
    def extract_referee_details(self, manuscript_data):
        """Extract referee details from the referee page"""
        logger.info("📊 Extracting referee details...")
        
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            page_text = soup.get_text()
            
            # Extract manuscript title
            manuscript_data['title'] = self.extract_manuscript_title(soup, page_text)
            
            # Extract key paper statistics
            manuscript_data.update(self.extract_paper_statistics(soup, page_text))
            
            # Extract referees
            referees, completed_referees = self.extract_referees(soup)
            
            # Enhance with email dates
            referees = self.enhance_referees_with_email_dates(referees, manuscript_data['manuscript_id'])
            
            manuscript_data['referees'] = referees
            manuscript_data['completed_referees'] = completed_referees
            manuscript_data['extraction_status'] = 'success'
            
            logger.info(f"✅ Successfully extracted {len(referees)} active and {len(completed_referees)} completed referees")
            
        except Exception as e:
            logger.error(f"Error extracting referee details: {e}")
            manuscript_data['extraction_status'] = 'extraction_error'
            
        return manuscript_data
        
    def extract_manuscript_title(self, soup, page_text):
        """Extract manuscript title"""
        # Try various patterns
        title_match = re.search(r'Title:\s*([^\n]+)', page_text)
        if title_match:
            return title_match.group(1).strip()
            
        # Try finding in specific elements
        title_element = soup.find(text=re.compile('Title:', re.I))
        if title_element:
            next_text = title_element.find_next().get_text(strip=True)
            if len(next_text) > 10:
                return next_text
                
        return ""
        
    def extract_paper_statistics(self, soup, page_text):
        """Extract paper statistics"""
        stats = {}
        
        # Date patterns
        patterns = {
            'submitted_date': r'Date Submitted:\s*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})',
            'due_date': r'Date Due:\s*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})',
            'status': r'Status:\s*([^\n]+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, page_text)
            if match:
                stats[key] = match.group(1).strip()
                
        return stats
        
    def extract_referees(self, soup):
        """Extract referee information from the page"""
        referees = []
        completed_referees = []
        
        # Look for Reviewer List section
        reviewer_list_header = soup.find(text=re.compile('Reviewer List', re.IGNORECASE))
        
        if not reviewer_list_header:
            logger.warning("No Reviewer List section found")
            return referees, completed_referees
            
        # Find the reviewer table
        reviewer_section = reviewer_list_header.find_parent()
        while reviewer_section and reviewer_section.name != 'table':
            reviewer_section = reviewer_section.find_next('table')
            
        if not reviewer_section:
            logger.warning("No reviewer table found")
            return referees, completed_referees
            
        rows = reviewer_section.find_all('tr')
        logger.info(f"Found {len(rows)} rows in reviewer table")
        
        for row in rows[1:]:  # Skip header
            referee_info = self.parse_referee_row(row)
            if referee_info:
                if referee_info.get('report_submitted'):
                    completed_referees.append(referee_info)
                else:
                    referees.append(referee_info)
                    
        return referees, completed_referees
        
    def parse_referee_row(self, row):
        """Parse a single referee row"""
        cells = row.find_all('td')
        if len(cells) < 4:
            return None
            
        # Extract name
        name = self.extract_referee_name(cells)
        if not name:
            return None
            
        # Extract other information
        referee_info = {
            'name': name,
            'institution': self.extract_institution(cells),
            'email': '',
            'status': self.extract_status(cells),
            'dates': self.extract_dates(row),
            'time_in_review': self.extract_time_in_review(row),
            'report_submitted': False,
            'submission_date': '',
            'review_decision': '',
            'report_url': ''
        }
        
        # Check if report is submitted
        status_lower = referee_info['status'].lower()
        if any(keyword in status_lower for keyword in ['minor revision', 'major revision', 'accept', 'reject']):
            referee_info['report_submitted'] = True
            referee_info['review_decision'] = referee_info['status']
            
            # Look for submission date
            submission_date = self.extract_submission_date(row)
            if submission_date:
                referee_info['submission_date'] = submission_date
                
            # Look for report URL
            report_url = self.extract_report_url(row)
            if report_url:
                referee_info['report_url'] = report_url
                
        return referee_info
        
    def extract_referee_name(self, cells):
        """Extract referee name from cells"""
        for cell in cells[:5]:
            cell_text = cell.get_text(strip=True)
            # Look for name pattern
            name_match = re.search(r'([A-Za-z]+,\s*[A-Za-z]+)', cell_text)
            if name_match:
                return name_match.group(1).strip()
        return None
        
    def extract_institution(self, cells):
        """Extract institution from cells"""
        for cell in cells:
            cell_text = cell.get_text()
            inst_keywords = ['University', 'College', 'Institute', 'School', 'Department']
            for keyword in inst_keywords:
                if keyword in cell_text:
                    # Extract the institution part
                    lines = cell_text.split('\n')
                    for line in lines:
                        if keyword in line:
                            return line.strip()
        return ''
        
    def extract_status(self, cells):
        """Extract referee status"""
        status_keywords = ['agreed', 'declined', 'invited', 'minor revision', 'major revision', 'accept', 'reject']
        
        for cell in cells:
            cell_text = cell.get_text(strip=True).lower()
            for keyword in status_keywords:
                if keyword in cell_text:
                    return cell.get_text(strip=True)
        return ''
        
    def extract_dates(self, row):
        """Extract all dates from row"""
        dates = {}
        row_text = row.get_text()
        
        # Date patterns
        date_patterns = {
            'invited': r'Invited[:\s]+([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})',
            'agreed': r'Agreed[:\s]+([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})',
            'due': r'Due Date[:\s]+([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})'
        }
        
        for key, pattern in date_patterns.items():
            match = re.search(pattern, row_text, re.IGNORECASE)
            if match:
                dates[key] = match.group(1)
                
        return dates
        
    def extract_time_in_review(self, row):
        """Extract time in review"""
        row_text = row.get_text()
        time_match = re.search(r'Time in Review[:\s]+([0-9]+\s*Days?)', row_text, re.IGNORECASE)
        if time_match:
            return time_match.group(1)
        return ''
        
    def extract_submission_date(self, row):
        """Extract report submission date"""
        row_text = row.get_text()
        date_match = re.search(r'Review Returned[:\s]+([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', row_text, re.IGNORECASE)
        if date_match:
            return date_match.group(1)
        return ''
        
    def extract_report_url(self, row):
        """Extract referee report URL"""
        # Look for JavaScript popup links
        links = row.find_all('a', href=re.compile(r'javascript:', re.I))
        for link in links:
            href = link.get('href', '')
            if 'popWindow' in href:
                return href
        return ''
        
    def enhance_referees_with_email_dates(self, referees, manuscript_id):
        """Enhance referee data with email dates"""
        try:
            logger.info(f"📧 Fetching email dates for {manuscript_id}...")
            flagged_emails, starred_emails = fetch_starred_emails()
            
            for referee in referees:
                # Use generic email matching function
                acceptance_email, contact_email = robust_match_email_for_referee_generic(
                    referee['name'],
                    manuscript_id,
                    self.journal_code,
                    "agreed",
                    flagged_emails,
                    starred_emails
                )
                
                if acceptance_email:
                    referee['acceptance_date'] = acceptance_email['date']
                    referee['email'] = acceptance_email['to']
                    logger.info(f"   📅 {referee['name']} acceptance: {acceptance_email['date']}")
                    
                if contact_email:
                    referee['contact_date'] = contact_email['date']
                    if not referee.get('email'):
                        referee['email'] = contact_email['to']
                        
        except Exception as e:
            logger.warning(f"Could not fetch emails: {e}")
            
        return referees
        
    def save_results(self, results):
        """Save extraction results"""
        # Save JSON
        json_file = self.output_dir / f"{self.journal_code.lower()}_referee_results.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"\n💾 Results saved to: {json_file}")
        
        # Generate report
        report_file = self.output_dir / f"{self.journal_code.lower()}_referee_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"GENERIC REFEREE EXTRACTION - {self.journal_code}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*80}\n\n")
            
            for ms in results['manuscripts']:
                f.write(f"Manuscript: {ms['manuscript_id']}\n")
                f.write(f"Title: {ms.get('title', 'N/A')}\n")
                f.write(f"Status: {ms.get('extraction_status', 'N/A')}\n")
                f.write(f"Submitted: {ms.get('submitted_date', 'N/A')}\n")
                f.write(f"Due: {ms.get('due_date', 'N/A')}\n")
                f.write(f"\nActive Referees:\n")
                
                for ref in ms.get('referees', []):
                    f.write(f"  • {ref['name']}")
                    if ref.get('email'):
                        f.write(f" ({ref['email']})")
                    if ref.get('acceptance_date'):
                        f.write(f"\n    Accepted: {ref['acceptance_date']}")
                    f.write("\n")
                    
                if ms.get('completed_referees'):
                    f.write(f"\nCompleted Referees:\n")
                    for ref in ms['completed_referees']:
                        f.write(f"  • {ref['name']}")
                        if ref.get('submission_date'):
                            f.write(f" - Submitted: {ref['submission_date']}")
                        if ref.get('review_decision'):
                            f.write(f" ({ref['review_decision']})")
                        f.write("\n")
                        
                f.write(f"\n{'-'*80}\n\n")
                
        logger.info(f"💾 Report saved to: {report_file}")


def main():
    """Test the generic extractor"""
    import argparse
    parser = argparse.ArgumentParser(description='Generic Referee Extractor')
    parser.add_argument('journal', help='Journal code (e.g., MF, MOR, JFE, etc.)')
    parser.add_argument('--manuscripts', nargs='+', help='Specific manuscript IDs to process')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    
    args = parser.parse_args()
    
    extractor = GenericRefereeExtractor(args.journal)
    extractor.extract_referee_data(manuscript_ids=args.manuscripts, headless=args.headless)


if __name__ == '__main__':
    main()