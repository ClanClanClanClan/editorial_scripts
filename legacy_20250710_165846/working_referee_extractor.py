#!/usr/bin/env python3
"""
Working Referee Extractor - Based on deep debugging insights
This version properly clicks checkboxes and extracts referee details
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
logger = logging.getLogger("WORKING_REFEREE_EXTRACTOR")


class WorkingRefereeExtractor:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.output_dir = Path(f"{journal_name.lower()}_referee_details_final")
        self.output_dir.mkdir(exist_ok=True)
        self.screenshot_count = 0
        
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
            
    def take_screenshot(self, description):
        """Take screenshot"""
        self.screenshot_count += 1
        filename = f"{self.screenshot_count:03d}_{description.replace(' ', '_')}.png"
        filepath = self.output_dir / filename
        self.driver.save_screenshot(str(filepath))
        logger.info(f"📸 Screenshot: {filename}")
        
    def run_extraction(self):
        """Run the extraction process"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 EXTRACTING REFEREE DETAILS FOR {self.journal_name}")
        logger.info(f"{'='*80}")
        
        self.create_driver(headless=False)
        all_results = []
        
        try:
            # Login
            if self.journal_name == "MF":
                self.journal = MFJournal(self.driver, debug=True)
                category = "Awaiting Reviewer Scores"
            else:
                self.journal = MORJournal(self.driver, debug=True)
                category = "Awaiting Reviewer Reports"
                
            self.journal.login()
            self.take_screenshot("after_login")
            
            # Navigate to AE Center
            ae_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            time.sleep(3)
            self.take_screenshot("ae_center")
            
            # Navigate to category
            logger.info(f"\n📂 Navigating to: {category}")
            category_link = self.driver.find_element(By.LINK_TEXT, category)
            category_link.click()
            time.sleep(3)
            self.take_screenshot("category_list")
            
            # Get manuscript IDs
            manuscript_ids = self.get_manuscript_ids()
            logger.info(f"📄 Found {len(manuscript_ids)} manuscripts: {manuscript_ids}")
            
            # Process each manuscript using checkbox method
            for ms_id in manuscript_ids:
                logger.info(f"\n{'='*60}")
                logger.info(f"📄 Processing: {ms_id}")
                logger.info(f"{'='*60}")
                
                manuscript_data = self.process_manuscript_with_checkbox(ms_id, category)
                all_results.append(manuscript_data)
                
                # Go back to category list for next manuscript
                self.navigate_back_to_category(category)
                
            # Save all results
            self.save_final_results(all_results)
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            self.take_screenshot("error")
            
        finally:
            self.driver.quit()
            
    def get_manuscript_ids(self):
        """Get manuscript IDs from current page"""
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        if self.journal_name == "MF":
            pattern = r'MAFI-\d{4}-\d+'
        else:
            pattern = r'MOR-\d{4}-\d+'
            
        ms_ids = list(set(re.findall(pattern, soup.get_text())))
        return ms_ids
        
    def process_manuscript_with_checkbox(self, manuscript_id, category):
        """Process manuscript by selecting checkbox and clicking Take Action"""
        manuscript_data = {
            'manuscript_id': manuscript_id,
            'category': category,
            'title': '',
            'referees': [],
            'extraction_status': 'failed'
        }
        
        try:
            # Find the row containing this manuscript
            rows = self.driver.find_elements(By.TAG_NAME, "tr")
            target_row = None
            
            for row in rows:
                if manuscript_id in row.text:
                    target_row = row
                    logger.info(f"✅ Found row for {manuscript_id}")
                    break
                    
            if not target_row:
                logger.error(f"❌ Could not find row for {manuscript_id}")
                return manuscript_data
                
            # Find the checkbox in the Take Action column (last cell)
            cells = target_row.find_elements(By.TAG_NAME, "td")
            if cells:
                last_cell = cells[-1]
                
                # Try to find and click the checkbox
                # Based on the screenshot, it's an image that looks like a checkbox
                clickable_found = False
                
                # Try to find any clickable element in the last cell
                clickable_elements = last_cell.find_elements(By.XPATH, ".//*")
                
                for element in clickable_elements:
                    try:
                        # Try to click it
                        self.driver.execute_script("arguments[0].click();", element)
                        time.sleep(0.5)
                        logger.info(f"✅ Clicked element in Take Action column")
                        clickable_found = True
                        break
                    except:
                        continue
                        
                if not clickable_found:
                    logger.warning("⚠️ Could not find clickable element, trying alternative methods")
                    
                    # Alternative: Click the entire cell
                    try:
                        self.driver.execute_script("arguments[0].click();", last_cell)
                        time.sleep(0.5)
                        logger.info("✅ Clicked Take Action cell")
                    except:
                        pass
                        
            # Now find and click the Take Action button
            self.take_screenshot(f"after_checkbox_{manuscript_id}")
            
            # Find Take Action button - it should be visible after checkbox selection
            take_action_clicked = False
            
            # Try various methods to find the button
            button_strategies = [
                ("XPATH", "//input[@value='Take Action']"),
                ("XPATH", "//button[contains(text(), 'Take Action')]"),
                ("XPATH", "//input[@type='submit']"),
                ("XPATH", "//button[@type='submit']"),
                ("XPATH", "//input[contains(@value, 'Take')]"),
                ("XPATH", "//input[contains(@name, 'submit')]")
            ]
            
            for method, selector in button_strategies:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        if elem.is_displayed():
                            elem_text = elem.get_attribute('value') or elem.text
                            logger.info(f"Found button: {elem_text}")
                            
                            elem.click()
                            time.sleep(3)
                            logger.info("✅ Clicked Take Action button")
                            take_action_clicked = True
                            break
                            
                    if take_action_clicked:
                        break
                        
                except Exception as e:
                    continue
                    
            if take_action_clicked:
                # We should now be on the detailed manuscript page
                self.take_screenshot(f"manuscript_{manuscript_id}_details")
                
                # Extract referee details
                manuscript_data = self.extract_referee_details(manuscript_id, manuscript_data)
                manuscript_data['extraction_status'] = 'success'
                
            else:
                logger.error("❌ Could not click Take Action button")
                
        except Exception as e:
            logger.error(f"Error processing {manuscript_id}: {e}")
            
        return manuscript_data
        
    def extract_referee_details(self, manuscript_id, manuscript_data):
        """Extract referee details from manuscript detail page"""
        logger.info("📊 Extracting referee information...")
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        page_text = soup.get_text()
        
        # Extract title
        # Look for title patterns
        title_match = re.search(rf'{manuscript_id}[^\n]*\n[^\n]*\n([^\n]+)', page_text)
        if not title_match:
            # Alternative pattern
            title_match = re.search(r'Title[:\s]+([^\n]+)', page_text)
            
        if title_match:
            manuscript_data['title'] = title_match.group(1).strip()
            logger.info(f"📄 Title: {manuscript_data['title']}")
            
        # Look for referee information
        # Based on the page structure, we need to find referee names and their details
        
        # Strategy: Look for tables containing referee information
        tables = soup.find_all('table')
        
        for table in tables:
            # Check if this table contains referee info
            table_text = table.get_text()
            
            if any(keyword in table_text.lower() for keyword in ['referee', 'reviewer', 'invited', 'agreed']):
                logger.info("📋 Found referee table")
                
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    
                    # Look for referee names in links
                    for cell in cells:
                        links = cell.find_all('a')
                        for link in links:
                            name = link.get_text(strip=True)
                            
                            if self.is_referee_name(name):
                                referee_data = {
                                    'name': name,
                                    'email': '',
                                    'status': 'unknown',
                                    'dates': {}
                                }
                                
                                # Extract email by clicking the name
                                email = self.try_extract_email(name)
                                if email:
                                    referee_data['email'] = email
                                    
                                # Extract status and dates from row
                                row_text = row.get_text()
                                referee_data = self.extract_referee_metadata(row_text, referee_data)
                                
                                manuscript_data['referees'].append(referee_data)
                                logger.info(f"  👤 Found referee: {name} ({referee_data['status']})")
                                
        # If no referees found in tables, try alternative extraction
        if not manuscript_data['referees']:
            logger.info("⚠️ No referees found in tables, trying alternative extraction...")
            
            # Look for common referee name patterns in the page
            # This would include looking for "Dr.", "Prof.", etc. followed by names
            
            name_patterns = [
                r'(?:Dr\.|Prof\.|Mr\.|Ms\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
                r'Referee[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
                r'Reviewer[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
            ]
            
            for pattern in name_patterns:
                matches = re.findall(pattern, page_text)
                for name in matches:
                    if self.is_referee_name(name) and not any(r['name'] == name for r in manuscript_data['referees']):
                        referee_data = {
                            'name': name,
                            'email': '',
                            'status': 'unknown',
                            'dates': {}
                        }
                        manuscript_data['referees'].append(referee_data)
                        logger.info(f"  👤 Found referee (pattern): {name}")
                        
        logger.info(f"✅ Total referees found: {len(manuscript_data['referees'])}")
        return manuscript_data
        
    def is_referee_name(self, text):
        """Check if text is likely a referee name"""
        if not text or len(text) < 3:
            return False
            
        # Exclude navigation and UI elements
        exclude_terms = [
            'mathematical finance', 'associate editor', 'view', 'download',
            'manuscript', 'submission', 'edit', 'select', 'action', 'log',
            'home', 'author', 'review', 'email', 'password', 'user id',
            'instructions', 'forms', 'date submitted', 'submitting author',
            'system requirements', 'privacy', 'terms', 'cookies', 'read more'
        ]
        
        text_lower = text.lower()
        if any(term in text_lower for term in exclude_terms):
            return False
            
        # Must have space (first and last name)
        if ' ' not in text and ',' not in text:
            return False
            
        # Check name structure
        parts = text.replace(',', ' ').split()
        if len(parts) < 2 or len(parts) > 5:
            return False
            
        # At least one part should start with capital
        if not any(part[0].isupper() for part in parts if part):
            return False
            
        return True
        
    def extract_referee_metadata(self, text, referee_data):
        """Extract status and dates from text"""
        text_lower = text.lower()
        
        # Extract status
        if 'agreed' in text_lower:
            referee_data['status'] = 'agreed'
        elif 'declined' in text_lower:
            referee_data['status'] = 'declined'
        elif 'invited' in text_lower:
            referee_data['status'] = 'invited'
        elif 'unavailable' in text_lower:
            referee_data['status'] = 'unavailable'
            
        # Extract dates
        date_patterns = {
            'invited': r'(?:Invited|Invitation)[:\s]+(\d{1,2}-\w{3}-\d{4})',
            'agreed': r'(?:Agreed|Accepted)[:\s]+(\d{1,2}-\w{3}-\d{4})',
            'declined': r'(?:Declined)[:\s]+(\d{1,2}-\w{3}-\d{4})',
            'due': r'(?:Due|Deadline)[:\s]+(\d{1,2}-\w{3}-\d{4})'
        }
        
        for key, pattern in date_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                referee_data['dates'][key] = match.group(1)
                
        return referee_data
        
    def try_extract_email(self, referee_name):
        """Try to extract email by clicking referee name"""
        try:
            main_window = self.driver.current_window_handle
            
            # Click the referee name
            referee_link = self.driver.find_element(By.LINK_TEXT, referee_name)
            referee_link.click()
            time.sleep(1)
            
            # Check for popup
            windows = self.driver.window_handles
            if len(windows) > 1:
                # Switch to popup
                self.driver.switch_to.window(windows[-1])
                
                # Extract email
                popup_source = self.driver.page_source
                email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', popup_source)
                
                # Close popup
                self.driver.close()
                self.driver.switch_to.window(main_window)
                
                if email_match:
                    logger.info(f"    📧 Found email: {email_match.group(0)}")
                    return email_match.group(0)
                    
        except:
            pass
            
        return None
        
    def navigate_back_to_category(self, category):
        """Navigate back to category list"""
        try:
            # Click Associate Editor Center
            ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
            ae_link.click()
            time.sleep(2)
            
            # Click category again
            category_link = self.driver.find_element(By.LINK_TEXT, category)
            category_link.click()
            time.sleep(2)
            
            logger.info("✅ Navigated back to category list")
            
        except Exception as e:
            logger.error(f"Error navigating back: {e}")
            
    def save_final_results(self, all_results):
        """Save final extraction results"""
        output_data = {
            'journal': self.journal_name,
            'extraction_date': datetime.now().isoformat(),
            'total_manuscripts': len(all_results),
            'successful_extractions': sum(1 for r in all_results if r['extraction_status'] == 'success'),
            'manuscripts': all_results
        }
        
        # Save JSON
        json_file = self.output_dir / f"{self.journal_name.lower()}_referee_details.json"
        with open(json_file, 'w') as f:
            json.dump(output_data, f, indent=2)
            
        logger.info(f"\n💾 Results saved to: {json_file}")
        
        # Generate summary report
        report_file = self.output_dir / f"{self.journal_name.lower()}_referee_report.txt"
        with open(report_file, 'w') as f:
            f.write(f"REFEREE EXTRACTION REPORT FOR {self.journal_name}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            
            total_referees = 0
            
            for ms in all_results:
                f.write(f"Manuscript: {ms['manuscript_id']}\n")
                f.write(f"Title: {ms['title'] or 'Not extracted'}\n")
                f.write(f"Category: {ms['category']}\n")
                f.write(f"Extraction Status: {ms['extraction_status']}\n")
                f.write(f"Referees ({len(ms['referees'])}):\n")
                
                for ref in ms['referees']:
                    total_referees += 1
                    f.write(f"\n  Name: {ref['name']}\n")
                    f.write(f"  Email: {ref['email'] or 'Not found'}\n")
                    f.write(f"  Status: {ref['status']}\n")
                    
                    if ref['dates']:
                        f.write("  Dates:\n")
                        for date_type, date_val in ref['dates'].items():
                            f.write(f"    {date_type.capitalize()}: {date_val}\n")
                            
                f.write("\n" + "-"*80 + "\n\n")
                
            f.write(f"\nSUMMARY:\n")
            f.write(f"Total Manuscripts: {len(all_results)}\n")
            f.write(f"Successfully Processed: {sum(1 for r in all_results if r['extraction_status'] == 'success')}\n")
            f.write(f"Total Referees Found: {total_referees}\n")
            
        logger.info(f"📄 Report saved to: {report_file}")
        
        # Print summary
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 EXTRACTION SUMMARY")
        logger.info(f"{'='*80}")
        logger.info(f"Total manuscripts: {len(all_results)}")
        logger.info(f"Successfully processed: {sum(1 for r in all_results if r['extraction_status'] == 'success')}")
        logger.info(f"Total referees found: {total_referees}")
        
        for ms in all_results:
            logger.info(f"\n{ms['manuscript_id']}: {len(ms['referees'])} referees")
            for ref in ms['referees']:
                status = f"({ref['status']})" if ref['status'] != 'unknown' else ""
                email = "📧" if ref['email'] else "❌"
                logger.info(f"  • {ref['name']} {status} {email}")


def main():
    """Run extraction for both journals"""
    
    # Extract MF
    logger.info("="*80)
    logger.info("EXTRACTING MF REFEREE DETAILS")
    logger.info("="*80)
    
    mf_extractor = WorkingRefereeExtractor("MF")
    mf_extractor.run_extraction()
    
    # Extract MOR
    logger.info("\n\n" + "="*80)
    logger.info("EXTRACTING MOR REFEREE DETAILS")
    logger.info("="*80)
    
    mor_extractor = WorkingRefereeExtractor("MOR")
    mor_extractor.run_extraction()


if __name__ == "__main__":
    main()