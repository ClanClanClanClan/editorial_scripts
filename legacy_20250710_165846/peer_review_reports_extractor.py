#!/usr/bin/env python3
"""
Peer Review Reports Extractor - Extract referee data from Peer Review Details Reports
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
logger = logging.getLogger("PEER_REVIEW_REPORTS")


class PeerReviewReportsExtractor:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.output_dir = Path(f"{journal_name.lower()}_peer_review_reports")
        self.output_dir.mkdir(exist_ok=True)
        self.screenshot_count = 0
        
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
            
    def take_screenshot(self, description):
        """Take screenshot"""
        self.screenshot_count += 1
        filename = f"{self.screenshot_count:03d}_{description.replace(' ', '_')}.png"
        filepath = self.output_dir / filename
        self.driver.save_screenshot(str(filepath))
        logger.info(f"📸 Screenshot: {filename}")
        
    def extract_via_peer_review_reports(self):
        """Extract referee data via Peer Review Details Reports"""
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 EXTRACTING VIA PEER REVIEW REPORTS - {self.journal_name}")
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
                expected_manuscripts = {
                    'MAFI-2024-0167': 2,
                    'MAFI-2025-0166': 2
                }
            else:
                self.journal = MORJournal(self.driver, debug=True)
                expected_manuscripts = {
                    'MOR-2025-1037': 2,
                    'MOR-2023-0376': 2,
                    'MOR-2024-0804': 2
                }
                
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
            self.take_screenshot("01_ae_center")
            
            # Look for Peer Review Details Reports
            logger.info("\n🔍 Looking for Peer Review Details Reports...")
            
            try:
                peer_review_link = self.driver.find_element(By.LINK_TEXT, "Peer Review Details Reports")
                logger.info("✅ Found Peer Review Details Reports link")
                peer_review_link.click()
                time.sleep(3)
                self.take_screenshot("02_peer_review_reports")
                
                # Analyze the page
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                # Look for manuscript information
                for ms_id, expected_refs in expected_manuscripts.items():
                    logger.info(f"\n📄 Looking for {ms_id}...")
                    
                    manuscript_data = {
                        'manuscript_id': ms_id,
                        'expected_referees': expected_refs,
                        'referees': [],
                        'extraction_status': 'not_found'
                    }
                    
                    # Check if manuscript is on this page
                    if ms_id in page_source:
                        logger.info(f"✅ Found {ms_id} on page")
                        
                        # Try to extract referee information
                        manuscript_data = self.extract_referee_info_from_report(ms_id, manuscript_data)
                        
                    all_results['manuscripts'].append(manuscript_data)
                    
            except Exception as e:
                logger.error(f"Could not access Peer Review Reports: {e}")
                
                # Alternative: Try each manuscript category
                categories = ["Awaiting Reviewer Scores", "Awaiting Reviewer Reports"]
                
                for category in categories:
                    try:
                        logger.info(f"\n📂 Trying category: {category}")
                        category_link = self.driver.find_element(By.LINK_TEXT, category)
                        category_link.click()
                        time.sleep(3)
                        
                        # Check if manuscripts are here
                        page_source = self.driver.page_source
                        
                        for ms_id, expected_refs in expected_manuscripts.items():
                            if ms_id in page_source:
                                logger.info(f"Found {ms_id} in {category}")
                                
                        # Go back to AE Center
                        ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
                        ae_link.click()
                        time.sleep(2)
                        
                    except:
                        pass
                        
            # Save results
            self.save_results(all_results)
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            self.take_screenshot("error")
            
        finally:
            self.driver.quit()
            
    def extract_referee_info_from_report(self, manuscript_id, manuscript_data):
        """Extract referee information from report page"""
        try:
            # Get current page source
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Look for referee information near manuscript ID
            # Find all text containing the manuscript ID
            elements_with_ms_id = soup.find_all(text=re.compile(manuscript_id))
            
            for element in elements_with_ms_id:
                # Get parent container
                parent = element.parent
                while parent and parent.name not in ['table', 'div', 'tr']:
                    parent = parent.parent
                    
                if parent:
                    container_text = parent.get_text()
                    
                    # Extract referee names
                    name_patterns = [
                        r'(?:Referee|Reviewer)\s*\d*[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
                        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*\([^)]*(?:Agreed|Declined|Invited)[^)]*\)',
                        r'Assigned to[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
                    ]
                    
                    for pattern in name_patterns:
                        matches = re.findall(pattern, container_text)
                        for name in matches:
                            if self.is_valid_referee_name(name):
                                referee_data = {
                                    'name': name.strip(),
                                    'status': 'unknown',
                                    'email': '',
                                    'dates': {}
                                }
                                
                                # Look for status
                                name_context = container_text[max(0, container_text.find(name)-50):container_text.find(name)+50]
                                if 'agreed' in name_context.lower():
                                    referee_data['status'] = 'Agreed'
                                elif 'declined' in name_context.lower():
                                    referee_data['status'] = 'Declined'
                                elif 'invited' in name_context.lower():
                                    referee_data['status'] = 'Invited'
                                    
                                manuscript_data['referees'].append(referee_data)
                                logger.info(f"  👤 Found referee: {name} ({referee_data['status']})")
                                
            if manuscript_data['referees']:
                manuscript_data['extraction_status'] = 'success'
            else:
                manuscript_data['extraction_status'] = 'no_referees_found'
                
        except Exception as e:
            logger.error(f"Error extracting referee info: {e}")
            
        return manuscript_data
        
    def is_valid_referee_name(self, name):
        """Check if a name is likely a referee name"""
        if not name or len(name) < 3:
            return False
            
        exclude_terms = [
            'manuscript', 'submission', 'associate', 'editor',
            'review', 'report', 'peer', 'details', 'center'
        ]
        
        name_lower = name.lower()
        if any(term in name_lower for term in exclude_terms):
            return False
            
        parts = name.split()
        if len(parts) < 2:
            return False
            
        return True
        
    def save_results(self, results):
        """Save extraction results"""
        # Save JSON
        json_file = self.output_dir / "referee_results.json"
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2)
            
        # Save report
        report_file = self.output_dir / "referee_report.txt"
        with open(report_file, 'w') as f:
            f.write(f"PEER REVIEW REPORTS EXTRACTION - {self.journal_name}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            
            total_found = 0
            total_expected = 0
            
            for ms in results['manuscripts']:
                ms_id = ms['manuscript_id']
                expected = ms['expected_referees']
                found = len(ms['referees'])
                status = ms['extraction_status']
                
                total_found += found
                total_expected += expected
                
                f.write(f"Manuscript: {ms_id}\n")
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
            f.write(f"Total Expected: {total_expected}\n")
            f.write(f"Total Found: {total_found}\n")
            f.write(f"Success Rate: {(total_found/total_expected*100 if total_expected > 0 else 0):.1f}%\n")
            
        logger.info(f"\n💾 Results saved to: {self.output_dir}")
        
        # Print summary
        logger.info(f"\n{'='*60}")
        logger.info(f"EXTRACTION SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total manuscripts: {len(results['manuscripts'])}")
        logger.info(f"Total referees found: {total_found}/{total_expected}")


def main():
    # Try MF first
    mf_extractor = PeerReviewReportsExtractor("MF")
    mf_extractor.extract_via_peer_review_reports()


if __name__ == "__main__":
    main()