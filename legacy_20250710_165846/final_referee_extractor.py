#!/usr/bin/env python3
"""
Final Referee Extractor - Clicks manuscript ID directly to access referee details
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

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from journals.mf import MFJournal
from journals.mor import MORJournal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FINAL_REFEREE_EXTRACTOR")


class FinalRefereeExtractor:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.output_dir = Path(f"{journal_name.lower()}_referee_final_results")
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
            
    def run_extraction(self):
        """Run the extraction process"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 FINAL REFEREE EXTRACTION FOR {self.journal_name}")
        logger.info(f"{'='*80}")
        
        self.create_driver(headless=False)
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
            time.sleep(3)
            
            # Navigate to category
            logger.info(f"\n📂 Navigating to: {category}")
            category_link = self.driver.find_element(By.LINK_TEXT, category)
            category_link.click()
            time.sleep(3)
            
            # Process each manuscript
            for ms_id, ms_info in expected_manuscripts.items():
                logger.info(f"\n{'='*60}")
                logger.info(f"📄 Processing: {ms_id}")
                logger.info(f"Expected: {ms_info['title'][:50]}...")
                logger.info(f"Expected referees: {ms_info['expected_referees']}")
                logger.info(f"{'='*60}")
                
                manuscript_data = self.process_manuscript_via_link(ms_id, category)
                manuscript_data['expected_title'] = ms_info['title']
                manuscript_data['expected_referees'] = ms_info['expected_referees']
                
                all_results['manuscripts'].append(manuscript_data)
                
            # Save results
            self.save_final_results(all_results)
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            
        finally:
            self.driver.quit()
            
    def process_manuscript_via_link(self, manuscript_id, category):
        """Process manuscript by clicking on manuscript ID link"""
        manuscript_data = {
            'manuscript_id': manuscript_id,
            'category': category,
            'title': '',
            'referees': [],
            'extraction_method': 'manuscript_id_link',
            'extraction_status': 'failed'
        }
        
        try:
            # Try to click the manuscript ID directly
            logger.info(f"🔍 Looking for manuscript ID link: {manuscript_id}")
            
            # Find all links on the page
            links = self.driver.find_elements(By.TAG_NAME, "a")
            manuscript_link = None
            
            for link in links:
                if link.text.strip() == manuscript_id:
                    manuscript_link = link
                    break
                    
            if manuscript_link:
                logger.info(f"✅ Found manuscript ID link")
                manuscript_link.click()
                time.sleep(3)
                
                # Check if we navigated to a detail page
                current_url = self.driver.current_url
                page_source = self.driver.page_source
                
                # Look for signs we're on a detail page
                if "View Submission" in page_source or "Referee" in page_source or "Download" in page_source:
                    logger.info("✅ Successfully navigated to manuscript details page")
                    
                    # Extract referee information
                    manuscript_data = self.extract_referee_information(manuscript_id, manuscript_data)
                    manuscript_data['extraction_status'] = 'success'
                    
                else:
                    logger.warning("⚠️ Did not reach detail page, trying alternative methods")
                    
                # Navigate back
                self.navigate_back_to_category(category)
                
            else:
                logger.error(f"❌ Could not find manuscript ID link for {manuscript_id}")
                
        except Exception as e:
            logger.error(f"Error processing {manuscript_id}: {e}")
            
        return manuscript_data
        
    def extract_referee_information(self, manuscript_id, manuscript_data):
        """Extract referee information from current page"""
        logger.info("📊 Extracting referee information...")
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        page_text = soup.get_text()
        
        # Extract title
        title_patterns = [
            rf'{manuscript_id}[^\n]*\n[^\n]*\n([^\n]+)',
            r'Title[:\s]+([^\n]+)',
            r'Manuscript Title[:\s]+([^\n]+)'
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, page_text, re.MULTILINE | re.DOTALL)
            if match:
                title = match.group(1).strip()
                # Clean up the title
                if not any(exclude in title.lower() for exclude in ['view', 'download', 'manuscript search']):
                    manuscript_data['title'] = title
                    logger.info(f"📄 Title: {title[:60]}...")
                    break
                    
        # Look for referee information in the page
        referees = []
        
        # Strategy 1: Look for "Referee" or "Reviewer" sections
        referee_sections = []
        
        # Find all text containing referee/reviewer
        lines = page_text.split('\n')
        for i, line in enumerate(lines):
            if any(keyword in line.lower() for keyword in ['referee', 'reviewer']):
                # Get context around this line
                start = max(0, i-5)
                end = min(len(lines), i+10)
                context = '\n'.join(lines[start:end])
                referee_sections.append(context)
                
        # Extract referee names from contexts
        potential_referees = set()
        
        for section in referee_sections:
            # Look for name patterns
            # Common patterns: "Referee: Name", "Reviewer 1: Name", etc.
            patterns = [
                r'(?:Referee|Reviewer)(?:\s+\d+)?[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)(?:\s+\((?:agreed|declined|invited)\))',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, section)
                for name in matches:
                    if self.is_valid_referee_name(name):
                        potential_referees.add(name)
                        
        # Strategy 2: Look for common academic titles followed by names
        title_patterns = [
            r'(?:Dr\.|Prof\.|Professor|Mr\.|Ms\.|Mrs\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        ]
        
        for pattern in title_patterns:
            matches = re.findall(pattern, page_text)
            for name in matches:
                if self.is_valid_referee_name(name):
                    potential_referees.add(name)
                    
        # Create referee entries
        for name in potential_referees:
            referee_data = {
                'name': name,
                'email': '',
                'status': 'unknown',
                'dates': {}
            }
            
            # Look for status near the name
            name_index = page_text.find(name)
            if name_index != -1:
                context = page_text[max(0, name_index-200):name_index+200]
                
                if 'agreed' in context.lower():
                    referee_data['status'] = 'agreed'
                elif 'declined' in context.lower():
                    referee_data['status'] = 'declined'
                elif 'invited' in context.lower():
                    referee_data['status'] = 'invited'
                    
                # Extract dates
                date_pattern = r'(\d{1,2}-\w{3}-\d{4})'
                dates_found = re.findall(date_pattern, context)
                if dates_found:
                    referee_data['dates']['found'] = dates_found
                    
            referees.append(referee_data)
            logger.info(f"  👤 Found referee: {name} ({referee_data['status']})")
            
        manuscript_data['referees'] = referees
        
        # If no referees found, log what we see on the page
        if not referees:
            logger.warning("⚠️ No referees found using standard extraction")
            
            # Log some page content for debugging
            logger.debug("Page snippet:")
            logger.debug(page_text[:500])
            
        return manuscript_data
        
    def is_valid_referee_name(self, name):
        """Check if a name is likely a referee name"""
        if not name or len(name) < 3:
            return False
            
        # Exclude common non-name terms
        exclude_terms = [
            'manuscript', 'submission', 'view', 'download', 'associate',
            'editor', 'system', 'review', 'report', 'action', 'select'
        ]
        
        name_lower = name.lower()
        if any(term in name_lower for term in exclude_terms):
            return False
            
        # Must have at least 2 parts
        parts = name.split()
        if len(parts) < 2:
            return False
            
        return True
        
    def navigate_back_to_category(self, category):
        """Navigate back to category list"""
        try:
            # Try browser back first
            self.driver.back()
            time.sleep(2)
            
            # If not on category page, navigate via AE Center
            if category not in self.driver.page_source:
                ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
                ae_link.click()
                time.sleep(2)
                
                category_link = self.driver.find_element(By.LINK_TEXT, category)
                category_link.click()
                time.sleep(2)
                
        except:
            pass
            
    def save_final_results(self, results):
        """Save final results with summary"""
        # Save JSON
        json_file = self.output_dir / f"{self.journal_name.lower()}_referee_results.json"
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2)
            
        logger.info(f"\n💾 Results saved to: {json_file}")
        
        # Generate summary report
        report_file = self.output_dir / f"{self.journal_name.lower()}_referee_summary.txt"
        with open(report_file, 'w') as f:
            f.write(f"REFEREE EXTRACTION SUMMARY FOR {self.journal_name}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            
            total_referees = 0
            successful_extractions = 0
            
            for ms in results['manuscripts']:
                ms_id = ms['manuscript_id']
                expected_title = ms.get('expected_title', 'Unknown')
                extracted_title = ms.get('title', 'Not extracted')
                expected_refs = ms.get('expected_referees', 0)
                found_refs = len(ms['referees'])
                status = ms['extraction_status']
                
                if status == 'success':
                    successful_extractions += 1
                    
                total_referees += found_refs
                
                f.write(f"Manuscript: {ms_id}\n")
                f.write(f"Expected Title: {expected_title}\n")
                f.write(f"Extracted Title: {extracted_title}\n")
                f.write(f"Expected Referees: {expected_refs}\n")
                f.write(f"Found Referees: {found_refs}\n")
                f.write(f"Status: {status}\n")
                
                if ms['referees']:
                    f.write("\nReferees:\n")
                    for ref in ms['referees']:
                        f.write(f"  • {ref['name']} ({ref['status']})\n")
                        if ref.get('dates'):
                            f.write(f"    Dates: {ref['dates']}\n")
                            
                f.write("\n" + "-"*80 + "\n\n")
                
            f.write(f"\nOVERALL SUMMARY:\n")
            f.write(f"Total Manuscripts: {len(results['manuscripts'])}\n")
            f.write(f"Successful Extractions: {successful_extractions}\n")
            f.write(f"Total Referees Found: {total_referees}\n")
            
            # Calculate expected totals
            total_expected_refs = sum(ms.get('expected_referees', 0) for ms in results['manuscripts'])
            f.write(f"Total Expected Referees: {total_expected_refs}\n")
            f.write(f"Extraction Rate: {(total_referees/total_expected_refs*100):.1f}%\n")
            
        logger.info(f"📄 Summary saved to: {report_file}")
        
        # Print summary
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 FINAL EXTRACTION SUMMARY")
        logger.info(f"{'='*80}")
        
        for ms in results['manuscripts']:
            ms_id = ms['manuscript_id']
            found_refs = len(ms['referees'])
            expected_refs = ms.get('expected_referees', 0)
            status = "✅" if ms['extraction_status'] == 'success' else "❌"
            
            logger.info(f"\n{status} {ms_id}: {found_refs}/{expected_refs} referees")
            
            if ms['title']:
                logger.info(f"   Title: {ms['title'][:60]}...")
                
            for ref in ms['referees']:
                logger.info(f"   • {ref['name']} ({ref['status']})")


def main():
    """Run extraction for both journals"""
    
    # Extract MF
    logger.info("="*80)
    logger.info("FINAL MF REFEREE EXTRACTION")
    logger.info("="*80)
    
    mf_extractor = FinalRefereeExtractor("MF")
    mf_extractor.run_extraction()
    
    # Extract MOR
    logger.info("\n\n" + "="*80)
    logger.info("FINAL MOR REFEREE EXTRACTION")
    logger.info("="*80)
    
    mor_extractor = FinalRefereeExtractor("MOR")
    mor_extractor.run_extraction()


if __name__ == "__main__":
    main()