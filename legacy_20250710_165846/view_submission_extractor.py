#!/usr/bin/env python3
"""
View Submission Extractor - Extract referee data via View Submission links
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

from journals.mf import MFJournal
from journals.mor import MORJournal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("VIEW_SUBMISSION")


class ViewSubmissionExtractor:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.output_dir = Path(f"{journal_name.lower()}_view_submission_results")
        self.output_dir.mkdir(exist_ok=True)
        
    def create_driver(self):
        """Create Chrome driver"""
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        try:
            self.driver = uc.Chrome(options=options)
        except:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            chrome_options = Options()
            for arg in options.arguments:
                chrome_options.add_argument(arg)
            self.driver = webdriver.Chrome(options=chrome_options)
            
    def extract_referee_data(self):
        """Extract referee data using View Submission links"""
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 EXTRACTING REFEREE DATA FOR {self.journal_name}")
        logger.info(f"{'='*80}")
        
        self.create_driver()
        all_results = {
            'journal': self.journal_name,
            'extraction_date': datetime.now().isoformat(),
            'manuscripts': []
        }
        
        try:
            # Login
            if self.journal_name == "MF":
                self.journal = MFJournal(self.driver, debug=True)
                category = "Awaiting Reviewer Scores"
                expected_manuscripts = [
                    ('MAFI-2024-0167', 'Competitive optimal portfolio selection', 2),
                    ('MAFI-2025-0166', 'Optimal investment and consumption', 2)
                ]
            else:
                self.journal = MORJournal(self.driver, debug=True)
                category = "Awaiting Reviewer Reports"
                expected_manuscripts = [
                    ('MOR-2025-1037', 'The Value of Partial Information', 2),
                    ('MOR-2023-0376', 'Utility maximization under endogenous pricing', 2),
                    ('MOR-2024-0804', 'Semi-static variance-optimal hedging', 2)
                ]
                
            # Navigate to journal
            journal_url = f"https://mc.manuscriptcentral.com/{self.journal_name.lower()}"
            self.driver.get(journal_url)
            time.sleep(3)
            
            # Handle cookie banner
            try:
                cookie_button = self.driver.find_element(By.ID, "onetrust-accept-btn-handler")
                if cookie_button.is_displayed():
                    cookie_button.click()
                    time.sleep(1)
            except:
                pass
                
            self.journal.login()
            
            # Navigate to AE Center
            ae_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            time.sleep(3)
            
            # Navigate to category
            logger.info(f"\n📂 Navigating to: {category}")
            category_link = self.driver.find_element(By.LINK_TEXT, category)
            category_link.click()
            time.sleep(3)
            
            # Process each manuscript
            for ms_id, ms_title_partial, expected_refs in expected_manuscripts:
                logger.info(f"\n{'='*60}")
                logger.info(f"📄 Processing: {ms_id}")
                logger.info(f"{'='*60}")
                
                manuscript_data = {
                    'manuscript_id': ms_id,
                    'title': '',
                    'expected_referees': expected_refs,
                    'referees': [],
                    'extraction_status': 'failed'
                }
                
                try:
                    # Find the row containing this manuscript
                    row_xpath = f"//tr[contains(., '{ms_id}')]"
                    row = self.driver.find_element(By.XPATH, row_xpath)
                    
                    # Find View Submission link in this row
                    view_link = row.find_element(By.LINK_TEXT, "View Submission")
                    
                    logger.info("Clicking View Submission...")
                    view_link.click()
                    time.sleep(3)
                    
                    # Extract data from View Submission page
                    manuscript_data = self.extract_from_view_submission_page(manuscript_data)
                    
                    # Go back to list
                    self.driver.back()
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error processing {ms_id}: {e}")
                    
                all_results['manuscripts'].append(manuscript_data)
                
            # Save results
            self.save_results(all_results)
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            
        finally:
            self.driver.quit()
            
    def extract_from_view_submission_page(self, manuscript_data):
        """Extract referee information from View Submission page"""
        logger.info("📊 Extracting from View Submission page...")
        
        try:
            # Get page source
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            page_text = soup.get_text()
            
            # Extract title
            title_elem = soup.find('td', string=re.compile('Title:', re.IGNORECASE))
            if title_elem:
                title_text = title_elem.find_next_sibling('td')
                if title_text:
                    manuscript_data['title'] = title_text.get_text(strip=True)
                    logger.info(f"Title: {manuscript_data['title'][:60]}...")
                    
            # Look for referee/reviewer section
            referee_sections = []
            
            # Method 1: Find tables with referee headers
            tables = soup.find_all('table')
            for table in tables:
                table_text = table.get_text()
                if any(keyword in table_text.lower() for keyword in ['referee', 'reviewer', 'review']):
                    referee_sections.append(table)
                    
            logger.info(f"Found {len(referee_sections)} potential referee tables")
            
            # Method 2: Look for specific referee patterns
            referees = []
            
            # Pattern for referee entries (e.g., "Referee 1: Name")
            referee_patterns = [
                r'(?:Referee|Reviewer)\s*(\d+)[:\s]+([^,\n]+)',
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*\((?:Agreed|Declined|Invited)\)',
                r'Review\s+by[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
            ]
            
            for pattern in referee_patterns:
                matches = re.findall(pattern, page_text, re.MULTILINE)
                for match in matches:
                    if isinstance(match, tuple):
                        # Extract name from tuple
                        name = match[1] if len(match) > 1 else match[0]
                    else:
                        name = match
                        
                    # Clean name
                    name = name.strip()
                    if self.is_valid_referee_name(name):
                        referee_data = {
                            'name': name,
                            'status': 'unknown',
                            'email': '',
                            'dates': {}
                        }
                        
                        # Look for status near name
                        name_index = page_text.find(name)
                        if name_index != -1:
                            context = page_text[max(0, name_index-100):name_index+100]
                            
                            if 'agreed' in context.lower() or 'accepted' in context.lower():
                                referee_data['status'] = 'Agreed'
                            elif 'declined' in context.lower():
                                referee_data['status'] = 'Declined'
                            elif 'invited' in context.lower():
                                referee_data['status'] = 'Invited'
                                
                        referees.append(referee_data)
                        logger.info(f"  👤 Found referee: {name} ({referee_data['status']})")
                        
            # Method 3: Look for reviewer assignments in detail sections
            detail_sections = soup.find_all(['div', 'td'], string=re.compile('Reviewer|Referee', re.IGNORECASE))
            
            for section in detail_sections:
                parent = section.parent
                if parent:
                    section_text = parent.get_text()
                    
                    # Extract names from this section
                    name_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
                    potential_names = re.findall(name_pattern, section_text)
                    
                    for name in potential_names:
                        if self.is_valid_referee_name(name) and not any(r['name'] == name for r in referees):
                            referee_data = {
                                'name': name,
                                'status': 'unknown',
                                'email': '',
                                'dates': {}
                            }
                            referees.append(referee_data)
                            logger.info(f"  👤 Found additional referee: {name}")
                            
            manuscript_data['referees'] = referees
            manuscript_data['extraction_status'] = 'success' if referees else 'partial'
            
            logger.info(f"Total referees found: {len(referees)}")
            
        except Exception as e:
            logger.error(f"Error extracting data: {e}")
            
        return manuscript_data
        
    def is_valid_referee_name(self, name):
        """Check if a name is likely a referee name"""
        if not name or len(name) < 3:
            return False
            
        # Exclude common non-name terms
        exclude_terms = [
            'manuscript', 'submission', 'view', 'download', 'associate',
            'editor', 'system', 'review', 'report', 'action', 'select',
            'title', 'author', 'date', 'status', 'referee', 'reviewer'
        ]
        
        name_lower = name.lower()
        if any(term in name_lower for term in exclude_terms):
            return False
            
        # Must have at least first and last name
        parts = name.split()
        if len(parts) < 2:
            return False
            
        # Each part should start with capital
        if not all(part[0].isupper() for part in parts if part):
            return False
            
        return True
        
    def save_results(self, results):
        """Save extraction results"""
        # Save JSON
        json_file = self.output_dir / f"{self.journal_name.lower()}_referees.json"
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2)
            
        # Save report
        report_file = self.output_dir / f"{self.journal_name.lower()}_referee_report.txt"
        with open(report_file, 'w') as f:
            f.write(f"REFEREE EXTRACTION REPORT FOR {self.journal_name}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            
            total_found = 0
            total_expected = 0
            
            for ms in results['manuscripts']:
                ms_id = ms['manuscript_id']
                title = ms.get('title', 'Not extracted')
                expected = ms.get('expected_referees', 0)
                found = len(ms['referees'])
                status = ms['extraction_status']
                
                total_found += found
                total_expected += expected
                
                f.write(f"Manuscript: {ms_id}\n")
                f.write(f"Title: {title[:60]}...\n" if title != 'Not extracted' else "Title: Not extracted\n")
                f.write(f"Expected Referees: {expected}\n")
                f.write(f"Found Referees: {found}\n")
                f.write(f"Status: {status}\n")
                
                if ms['referees']:
                    f.write("\nReferees:\n")
                    for ref in ms['referees']:
                        f.write(f"  • {ref['name']} ({ref['status']})\n")
                        
                f.write("\n" + "-"*80 + "\n\n")
                
            # Summary
            f.write(f"SUMMARY:\n")
            f.write(f"Total Manuscripts: {len(results['manuscripts'])}\n")
            f.write(f"Total Expected Referees: {total_expected}\n")
            f.write(f"Total Found Referees: {total_found}\n")
            f.write(f"Success Rate: {(total_found/total_expected*100):.1f}%\n")
            
        logger.info(f"\n💾 Results saved to:")
        logger.info(f"  - {json_file}")
        logger.info(f"  - {report_file}")
        
        # Print summary
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 EXTRACTION SUMMARY")
        logger.info(f"{'='*80}")
        
        for ms in results['manuscripts']:
            ms_id = ms['manuscript_id']
            found = len(ms['referees'])
            expected = ms.get('expected_referees', 0)
            status = "✅" if ms['extraction_status'] == 'success' else "⚠️"
            
            logger.info(f"\n{status} {ms_id}: {found}/{expected} referees")
            
            if ms.get('title'):
                logger.info(f"   Title: {ms['title'][:60]}...")
                
            for ref in ms['referees']:
                logger.info(f"   • {ref['name']} ({ref['status']})")


def main():
    # Extract for both journals
    for journal in ["MF", "MOR"]:
        extractor = ViewSubmissionExtractor(journal)
        extractor.extract_referee_data()
        
        # Brief pause between journals
        time.sleep(5)


if __name__ == "__main__":
    main()