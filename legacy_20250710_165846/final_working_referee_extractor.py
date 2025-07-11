#!/usr/bin/env python3
"""
Final Working Referee Extractor - Extract referee data by clicking checkbox images
BREAKTHROUGH: Found that clicking the checkbox images navigates to referee details!
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
from core.email_utils import fetch_starred_emails, robust_match_email_for_referee_mf, robust_match_email_for_referee_mor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FINAL_WORKING_EXTRACTOR")


class FinalWorkingRefereeExtractor:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.output_dir = Path(f"{journal_name.lower()}_final_working_results")
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
            
    def extract_referee_data(self, headless=True):
        """Extract referee data using checkbox clicks"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 FINAL WORKING REFEREE EXTRACTION - {self.journal_name}")
        logger.info(f"{'='*80}")
        
        self.create_driver(headless=headless)
        all_results = {
            'journal': self.journal_name,
            'extraction_date': datetime.now().isoformat(),
            'extraction_method': 'checkbox_image_clicks',
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
                        'expected_referees': 1  # Should have Xing, Hao with completed report
                    },
                    'MOR-2024-0804': {
                        'title': 'Semi-static variance-optimal hedging with self-exciting jumps',
                        'expected_referees': 2
                    }
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
            
            # Navigate to category
            logger.info(f"\n📂 Navigating to: {category}")
            category_link = self.driver.find_element(By.LINK_TEXT, category)
            category_link.click()
            time.sleep(3)
            
            # Also check "Final Decisions" category for completed reports
            final_decisions_available = False
            try:
                final_decisions_link = self.driver.find_element(By.LINK_TEXT, "Final Decisions")
                final_decisions_available = True
                logger.info(f"✅ Found 'Final Decisions' category for completed reports")
            except:
                logger.info("ℹ️  No 'Final Decisions' category found")
            
            # Process each manuscript by finding and clicking checkbox images
            for ms_id, ms_info in expected_manuscripts.items():
                logger.info(f"\n{'='*60}")
                logger.info(f"📄 Processing: {ms_id}")
                logger.info(f"Expected: {ms_info['title'][:50]}...")
                logger.info(f"{'='*60}")
                
                manuscript_data = {
                    'manuscript_id': ms_id,
                    'expected_title': ms_info['title'],
                    'expected_referees': ms_info['expected_referees'],
                    'title': '',
                    'referees': [],
                    'extraction_status': 'failed'
                }
                
                try:
                    # Strategy: Find all rows with checkbox images, then match by manuscript content
                    # First, find all checkbox images
                    checkbox_images = self.driver.find_elements(By.XPATH, "//img[contains(@src, 'check_off.gif')]")
                    logger.info(f"Found {len(checkbox_images)} checkbox images")
                    
                    found_checkbox = None
                    
                    for checkbox in checkbox_images:
                        # Get the row containing this checkbox
                        checkbox_row = checkbox.find_element(By.XPATH, "./ancestor::tr")
                        
                        # Get all table rows and find our manuscript data row (not just mention)
                        all_rows = self.driver.find_elements(By.TAG_NAME, "tr")
                        
                        for i, row in enumerate(all_rows):
                            row_text = row.text
                            
                            # Look for the actual manuscript data row:
                            # - Must start with the manuscript ID (not just contain it)
                            # - Should have exactly 1 checkbox (data rows have 1, header rows have multiple)
                            if row_text.strip().startswith(ms_id):
                                # Check if this is the actual data row
                                row_checkboxes = row.find_elements(By.XPATH, ".//img[contains(@src, 'check_off.gif')]")
                                
                                # Data rows should have exactly 1 checkbox
                                if len(row_checkboxes) == 1:
                                    found_checkbox = row_checkboxes[0]
                                    logger.info(f"✅ Found manuscript data for {ms_id} in row {i}")
                                    logger.info(f"   Row preview: {row_text[:100]}...")
                                    break
                                else:
                                    logger.info(f"   Skipping row {i} (wrong checkbox count: {len(row_checkboxes)}): {row_text[:50]}...")
                            elif ms_id in row_text:
                                logger.info(f"   Skipping row {i} (contains but doesn't start with {ms_id}): {row_text[:50]}...")
                                    
                        if found_checkbox:
                            break
                            
                    if found_checkbox:
                        logger.info(f"✅ Clicking checkbox for {ms_id}")
                        
                        # Scroll checkbox into view
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", found_checkbox)
                        time.sleep(0.5)
                        
                        # Click the checkbox image
                        found_checkbox.click()
                        time.sleep(3)
                        
                        # We should now be on the referee details page
                        current_url = self.driver.current_url
                        logger.info(f"Navigated to: {current_url}")
                        
                        # Extract referee data from this page
                        manuscript_data = self.extract_referee_details(manuscript_data)
                        
                        # Try to download manuscript PDF if URL was found
                        if manuscript_data.get('manuscript_pdf_url'):
                            try:
                                pdf_file = self.download_manuscript_pdf(
                                    manuscript_data['manuscript_pdf_url'],
                                    manuscript_data['manuscript_id']
                                )
                                if pdf_file:
                                    manuscript_data['manuscript_pdf_file'] = pdf_file
                            except Exception as e:
                                logger.warning(f"   ⚠️  Failed to download manuscript PDF: {e}")
                        
                        # Navigate back to AE Center (don't use back button - it kills the session!)
                        logger.info("🔄 Navigating back to Associate Editor Center...")
                        try:
                            ae_link = WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
                            )
                            ae_link.click()
                            time.sleep(2)
                            
                            # Navigate back to the category
                            logger.info(f"🔄 Navigating back to: {category}")
                            category_link = WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.LINK_TEXT, category))
                            )
                            category_link.click()
                            time.sleep(3)
                        except Exception as e:
                            logger.warning(f"⚠️  Failed to navigate back: {e}")
                            # Try alternative navigation
                            try:
                                self.driver.get(f"https://mc.manuscriptcentral.com/{self.journal_name.lower()}")
                                time.sleep(2)
                                ae_link = WebDriverWait(self.driver, 10).until(
                                    EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
                                )
                                ae_link.click()
                                time.sleep(2)
                                category_link = WebDriverWait(self.driver, 10).until(
                                    EC.element_to_be_clickable((By.LINK_TEXT, category))
                                )
                                category_link.click()
                                time.sleep(3)
                            except Exception as e2:
                                logger.error(f"❌ Navigation failed completely: {e2}")
                        
                    else:
                        logger.warning(f"❌ No checkbox found for {ms_id}")
                        
                except Exception as e:
                    logger.error(f"Error processing {ms_id}: {e}")
                    
                all_results['manuscripts'].append(manuscript_data)
                
            # Save results
            self.save_results(all_results)
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            
        finally:
            self.driver.quit()
            
    def extract_referee_details(self, manuscript_data):
        """Extract referee details from the referee page"""
        logger.info("📊 Extracting referee details...")
        
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            page_text = soup.get_text()
            
            # Extract manuscript title from the page
            manuscript_data['title'] = self.extract_manuscript_title(soup, page_text)
            
            # Extract key paper statistics
            manuscript_data.update(self.extract_paper_statistics(soup, page_text))
            
            # Look for Reviewer List section specifically
            reviewer_list_header = soup.find(text=re.compile('Reviewer List', re.IGNORECASE))
            
            if reviewer_list_header:
                logger.info("✅ Found Reviewer List section")
                
                # Find the table containing reviewer information
                reviewer_section = reviewer_list_header.find_parent()
                while reviewer_section and reviewer_section.name != 'table':
                    reviewer_section = reviewer_section.find_next('table')
                
                if reviewer_section:
                    # Find all rows in the reviewer table
                    rows = reviewer_section.find_all('tr')
                    logger.info(f"Found {len(rows)} rows in reviewer table")
                    
                    referees = []
                    
                    for i, row in enumerate(rows[1:], 1):  # Skip header row
                        cells = row.find_all('td')
                        
                        if len(cells) >= 4:  # Minimum columns needed
                            # ROBUST TABLE PARSING - handle complex table structures
                            
                            # Extract name - simplified and direct approach
                            name_cell = None
                            name = ''
                            
                            # Look for name patterns in the first few cells
                            for cell_idx, cell in enumerate(cells[:5]):  # Check first 5 columns only
                                cell_text = cell.get_text(strip=True)
                                
                                logger.info(f"      🔍 Cell[{cell_idx}]: '{cell_text[:100]}'")
                                
                                # Skip obvious non-name cells
                                if any(skip in cell_text.lower() for skip in ['security reasons', 'time out', 'session', 'revision', 'rescind']):
                                    logger.info(f"      ❌ Skipping cell[{cell_idx}] - contains excluded keyword")
                                    continue
                                
                                # Look for pattern: "LastName, FirstName(R0)Institution"
                                name_match = re.search(r'([A-Za-z]+,\s*[A-Za-z]+)(?:\(R0\))?', cell_text)
                                if name_match:
                                    potential_name = name_match.group(1).strip()
                                    logger.info(f"      🎯 Found name pattern: '{potential_name}' in cell[{cell_idx}]")
                                    
                                    # Clean up the name - remove any trailing non-name text
                                    # Split by common non-name patterns and take the first part
                                    clean_name = potential_name
                                    for separator in ['recommended', 'University', 'College', 'Institute', 'Department', 'School']:
                                        if separator in clean_name:
                                            clean_name = clean_name.split(separator)[0].strip()
                                            break
                                    
                                    # Remove any trailing non-alpha characters except comma and space
                                    clean_name = re.sub(r'[^A-Za-z,\s]+$', '', clean_name).strip()
                                    
                                    logger.info(f"      🧹 Cleaned name: '{clean_name}'")
                                    
                                    # Verify it's not a status word
                                    if not any(status_word in clean_name.lower() for status_word in ['minor', 'major', 'revision', 'accept', 'reject', 'rescind']):
                                        name = clean_name
                                        name_cell = cell
                                        logger.info(f"      ✅ Extracted name: '{name}' from cell[{cell_idx}]")
                                        break
                                    else:
                                        logger.info(f"      ❌ Rejected name pattern - contains status keyword: '{clean_name}'")
                                        
                            # If no name found, log for debugging
                            if not name:
                                logger.warning(f"      ❌ No valid name found in row with {len(cells)} cells")
                            
                            if not name:
                                continue  # Skip rows without identifiable names
                            
                            # Find status - look for decision keywords in all cells
                            status = ''
                            status_cell = None
                            all_cell_contents = []  # For debugging
                            decision_statuses = ['minor revision', 'major revision', 'accept', 'reject', 'revision', 'agreed']
                            
                            # DEBUG: Log all cell contents for this referee
                            logger.info(f"      🔍 DEBUG: Analyzing {len(cells)} cells for referee '{name}'")
                            for idx, cell in enumerate(cells):
                                cell_text = cell.get_text(strip=True)
                                all_cell_contents.append(f"Cell[{idx}]: '{cell_text[:100]}'")
                                logger.info(f"         Cell[{idx}]: '{cell_text[:100]}'")
                            
                            for cell in cells:
                                cell_text = cell.get_text(strip=True).lower()
                                for decision in decision_statuses:
                                    if decision in cell_text:
                                        status = cell.get_text(strip=True)
                                        status_cell = cell
                                        logger.info(f"         ✅ FOUND STATUS: '{status}' (matched '{decision}')")
                                        break
                                if status:
                                    break
                                    
                            # If no decision found, look for other status indicators
                            if not status:
                                logger.info(f"         ⚠️  No decision keyword found, looking for other status indicators")
                                for cell in cells:
                                    cell_text = cell.get_text(strip=True)
                                    if cell_text and cell_text not in [name, ''] and len(cell_text) < 50:
                                        status = cell_text
                                        status_cell = cell
                                        logger.info(f"         📄 Using status: '{status}'")
                                        break
                            
                            # ROBUST STATUS DETECTION - Check if this referee has submitted their report
                            is_report_submitted = False
                            submitted_date = ''
                            review_decision = ''
                            
                            # Look for decision statuses (indicates completed review)
                            completion_keywords = ['minor revision', 'major revision', 'accept', 'reject']
                            status_lower = status.lower()
                            
                            for keyword in completion_keywords:
                                if keyword in status_lower:
                                    is_report_submitted = True
                                    review_decision = status
                                    logger.info(f"    🎯 FOUND COMPLETED REVIEW: {name} - Decision: {status}")
                                    break
                            
                            # ROBUST DATE EXTRACTION - Look for "Review Returned" date in ALL cells
                            # Strategy 1: Look for combined "Review Returned: DATE" pattern
                            for cell in cells:
                                cell_text = cell.get_text()
                                
                                # Look for "Review Returned" specifically - more flexible pattern
                                review_returned_patterns = [
                                    r'Review Returned[:\s]*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})',  # With colon/space
                                    r'Review Returned:([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})',       # Direct after colon
                                    r'(?:Review Returned.*?)([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})'  # Anywhere after "Review Returned"
                                ]
                                
                                for pattern in review_returned_patterns:
                                    review_returned_match = re.search(pattern, cell_text, re.IGNORECASE)
                                    if review_returned_match:
                                        is_report_submitted = True
                                        submitted_date = review_returned_match.group(1)
                                        logger.info(f"    📅 Review returned date found (combined): {submitted_date}")
                                        break
                                
                                if submitted_date:
                                    break
                                    
                            # Strategy 2: Look for "Review Returned:" in one cell and date in next cell
                            if not submitted_date:
                                for i, cell in enumerate(cells):
                                    cell_text = cell.get_text(strip=True)
                                    if 'review returned' in cell_text.lower():
                                        # Check the next cell for date
                                        if i + 1 < len(cells):
                                            next_cell = cells[i + 1]
                                            next_text = next_cell.get_text(strip=True)
                                            date_match = re.search(r'^([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})$', next_text)
                                            if date_match:
                                                is_report_submitted = True
                                                submitted_date = date_match.group(1)
                                                logger.info(f"    📅 Review returned date found (separate cells): {submitted_date}")
                                                break
                                
                                # Also check for other submission patterns
                                submission_patterns = [
                                    r'Report Submitted[:\s]+([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})',
                                    r'Submitted[:\s]+([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})',
                                    r'Completed[:\s]+([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})'
                                ]
                                
                                for pattern in submission_patterns:
                                    match = re.search(pattern, cell_text, re.IGNORECASE)
                                    if match:
                                        is_report_submitted = True
                                        submitted_date = match.group(1)
                                        logger.info(f"    📅 Submission date found: {submitted_date}")
                                        break
                                
                                if submitted_date:
                                    break
                            
                            # If we found completion indicators but no specific date, extract the most recent date
                            if is_report_submitted and not submitted_date:
                                for cell in cells:
                                    cell_text = cell.get_text()
                                    date_pattern = r'([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})'
                                    dates = re.findall(date_pattern, cell_text)
                                    if dates:
                                        submitted_date = dates[-1]  # Take the last (most recent) date
                                        logger.info(f"    📅 Using most recent date: {submitted_date}")
                                        break
                            
                            # Check for report download link if report is submitted
                            report_url = ''
                            if is_report_submitted:
                                # Look for view/download link in the row
                                try:
                                    # Find links in the row that might be report links
                                    row_element = cells[0].find_parent('tr')
                                    if row_element:
                                        links = row_element.find_all('a', href=True)
                                        for link in links:
                                            href = link.get('href', '')
                                            link_text = link.get_text(strip=True).lower()
                                            # Look for report-related links
                                            if any(keyword in link_text for keyword in ['view', 'report', 'review', 'decision']):
                                                if href.startswith('/'):
                                                    report_url = f"https://mc.manuscriptcentral.com{href}"
                                                else:
                                                    report_url = href
                                                logger.info(f"    📄 Found report link: {link_text} -> {report_url}")
                                                break
                                except Exception as e:
                                    logger.warning(f"    ⚠️  Error finding report link: {e}")
                            
                            # Also check for unavailable in the history/notes
                            row_text = row.get_text().lower()
                            
                            # Skip unavailable, declined, or unwanted referees
                            skip_statuses = ['unavailable', 'declined', 'invite again', 'security reasons', 'unavailable:', 'declined:']
                            should_skip = any(skip_status in status.lower() for skip_status in skip_statuses)
                            should_skip = should_skip or any(skip_status in row_text for skip_status in skip_statuses)
                            
                            # Specifically exclude Dos Reis as you mentioned he's unavailable
                            if 'dos reis' in name.lower():
                                should_skip = True
                                
                            if should_skip:
                                logger.info(f"  ❌ Skipping {name}: {status} (unavailable/declined)")
                                continue
                            
                            # Extract email if available
                            email = ''
                            email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
                            row_text = row.get_text()
                            email_match = re.search(email_pattern, row_text)
                            if email_match:
                                email = email_match.group(1)
                            
                            # Extract dates from history column or any cell
                            dates = {}
                            institution = ''
                            time_in_review = ''
                            
                            # Look through all cells for date information
                            for cell in cells:
                                cell_text = cell.get_text()
                                
                                # Extract specific dates with labels
                                if 'invited' in cell_text.lower():
                                    invited_match = re.search(r'Invited[:\s]+([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', cell_text, re.IGNORECASE)
                                    if invited_match:
                                        dates['invited'] = invited_match.group(1)
                                        logger.info(f"    📅 Invited date: {dates['invited']}")
                                
                                if 'agreed' in cell_text.lower():
                                    agreed_match = re.search(r'Agreed[:\s]+([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', cell_text, re.IGNORECASE)
                                    if agreed_match:
                                        dates['agreed'] = agreed_match.group(1)
                                        logger.info(f"    📅 Agreed date: {dates['agreed']}")
                                
                                if 'declined' in cell_text.lower():
                                    declined_match = re.search(r'Declined[:\s]+([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', cell_text, re.IGNORECASE)
                                    if declined_match:
                                        dates['declined'] = declined_match.group(1)
                                        logger.info(f"    📅 Declined date: {dates['declined']}")
                                
                                if 'due date' in cell_text.lower():
                                    due_match = re.search(r'Due Date[:\s]+([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})', cell_text, re.IGNORECASE)
                                    if due_match:
                                        dates['due'] = due_match.group(1)
                                        logger.info(f"    📅 Due date: {dates['due']}")
                                
                                # Extract time in review
                                if 'time in review' in cell_text.lower():
                                    time_match = re.search(r'Time in Review[:\s]+([0-9]+\s*Days?)', cell_text, re.IGNORECASE)
                                    if time_match:
                                        time_in_review = time_match.group(1)
                                        logger.info(f"    ⏱️  Time in review: {time_in_review}")
                            
                            # Extract institution from name cell or nearby cells
                            if name_cell:
                                cell_text = name_cell.get_text()
                                # Look for institution patterns
                                inst_patterns = ['University', 'College', 'Institute', 'School', 'Department', 'Center', 'Centre']
                                lines = cell_text.split('\n')
                                for line in lines:
                                    if any(inst in line for inst in inst_patterns):
                                        # Clean up institution name
                                        inst_line = line.strip()
                                        # Remove common prefixes
                                        inst_line = re.sub(r'^(Grant an Extension|recommended|agreed)', '', inst_line, flags=re.IGNORECASE).strip()
                                        if inst_line and len(inst_line) > 5:
                                            institution = inst_line
                                            logger.info(f"    🏛️  Institution: {institution}")
                                            break
                            
                            # Only add if we found a valid name and acceptable status
                            if name and len(name.split()) >= 2:
                                # For digest, we need name and key dates
                                referee_info = {
                                    'name': name,
                                    'institution': institution,
                                    'email': email,
                                    'status': status,
                                    'dates': dates,
                                    'time_in_review': time_in_review,
                                    'report_submitted': is_report_submitted,
                                    'submission_date': submitted_date,
                                    'review_decision': review_decision,
                                    'report_url': report_url
                                }
                                referees.append(referee_info)
                                
                                if is_report_submitted:
                                    logger.info(f"  ✅ {name} ({status}) - REPORT SUBMITTED: {submitted_date}")
                                else:
                                    logger.info(f"  ✅ {name} ({status})")
                    
                    # Enhance referee data with email dates
                    enhanced_referees = self.enhance_referees_with_email_dates(referees, manuscript_data['manuscript_id'])
                    
                    # Separate active referees from completed ones
                    active_referees = []
                    completed_referees = []
                    
                    for ref in enhanced_referees:
                        if ref.get('report_submitted', False):
                            completed_referees.append(ref)
                        else:
                            active_referees.append(ref)
                    
                    manuscript_data['referees'] = active_referees  # Only active referees for digest
                    manuscript_data['completed_referees'] = completed_referees  # Completed referees separately
                    manuscript_data['extraction_status'] = 'success' if (active_referees or completed_referees) else 'no_referees_found'
                    
                    logger.info(f"✅ Successfully extracted {len(enhanced_referees)} referees")
                    if active_referees:
                        logger.info(f"   📋 Active referees: {len(active_referees)}")
                    if completed_referees:
                        logger.info(f"   ✅ Completed referees: {len(completed_referees)}")
                        
                        # Try to download reports for completed referees
                        # TEMPORARILY DISABLED: Report download is causing session issues
                        logger.info("   ℹ️  Report download temporarily disabled to ensure stable extraction")
                        # for ref in completed_referees:
                        #     if ref.get('report_url'):
                        #         try:
                        #             report_file = self.download_referee_report(
                        #                 ref['report_url'], 
                        #                 ref['name'], 
                        #                 manuscript_data['manuscript_id']
                        #             )
                        #             if report_file:
                        #                 ref['report_file'] = report_file
                        #         except Exception as e:
                        #             logger.warning(f"   ⚠️  Failed to download report for {ref['name']}: {e}")
                        #             # Continue with extraction even if report download fails
                    
                else:
                    logger.warning("❌ Could not find reviewer table")
                    
            else:
                logger.warning("❌ Could not find Reviewer List section")
                
                # Fallback: Look for any referee names in the page
                logger.info("🔍 Trying fallback extraction...")
                
                # Look for common referee name patterns
                name_patterns = [
                    r'([A-Z][a-z]+,\s+[A-Z][a-z]+)',  # Last, First
                    r'([A-Z][a-z]+\s+[A-Z][a-z]+)',   # First Last
                ]
                
                potential_names = set()
                for pattern in name_patterns:
                    matches = re.findall(pattern, page_text)
                    for match in matches:
                        # Skip common false positives
                        if not any(skip in match.lower() for skip in ['security', 'session', 'please', 'work']):
                            potential_names.add(match)
                
                referees = []
                for name in list(potential_names)[:5]:  # Limit to 5
                    referee_data = {
                        'name': name,
                        'affiliation': '',
                        'email': '',
                        'status': 'Unknown',
                        'dates': {}
                    }
                    referees.append(referee_data)
                    logger.info(f"  👤 {name} (fallback extraction)")
                
                manuscript_data['referees'] = referees
                manuscript_data['extraction_status'] = 'partial' if referees else 'failed'
                
        except Exception as e:
            logger.error(f"Error extracting referee details: {e}")
            
        return manuscript_data
    
    def extract_manuscript_title(self, soup, page_text):
        """Extract manuscript title from the page"""
        # Look for title in various locations
        title_patterns = [
            r'Optimal investment and consumption under forward utilities with relative performance concerns',
            r'Competitive optimal portfolio selection in a non-Markovian financial market',
            r'The Value of Partial Information',
            r'Utility maximization under endogenous pricing',
            r'Semi-static variance-optimal hedging'
        ]
        
        for pattern in title_patterns:
            if pattern.lower() in page_text.lower():
                logger.info(f"📄 Title: {pattern[:60]}...")
                return pattern
                
        # Fallback: look for title in common locations
        title_element = soup.find('td', string=re.compile('Optimal|Competitive|Value|Utility|Semi-static', re.IGNORECASE))
        if title_element:
            title = title_element.get_text(strip=True)
            logger.info(f"📄 Title (extracted): {title[:60]}...")
            return title
            
        return ''
    
    def extract_paper_statistics(self, soup, page_text):
        """Extract key paper statistics for the digest"""
        stats = {
            'submitted_date': '',
            'due_date': '',
            'status': '',
            'reviewers_count': 0,
            'authors': '',
            'abstract': '',
            'keywords': '',
            'manuscript_pdf_url': '',
            'decision_letter': ''
        }
        
        # Extract submitted date
        submitted_patterns = [
            r'Submitted[:\s]+([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})',
            r'Date Submitted[:\s]+([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})',
            r'([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})[^\w]*Submitted'
        ]
        
        for pattern in submitted_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                stats['submitted_date'] = match.group(1)
                logger.info(f"📅 Submitted: {stats['submitted_date']}")
                break
        
        # Extract due date
        due_patterns = [
            r'Due[:\s]+([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})',
            r'Due Date[:\s]+([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})',
            r'Due[:\s]+([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4})'
        ]
        
        for pattern in due_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                stats['due_date'] = match.group(1)
                logger.info(f"⏰ Due: {stats['due_date']}")
                break
        
        # Extract current status
        status_patterns = [
            r'Awaiting Reviewer (Scores|Reports)',
            r'Under Review',
            r'Reviewer Assignment'
        ]
        
        for pattern in status_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                stats['status'] = match.group(0)
                logger.info(f"📊 Status: {stats['status']}")
                break
        
        # Extract authors
        author_patterns = [
            r'Author[s]*[:\s]+([^;\n]+)',
            r'By[:\s]+([^;\n]+)',
            r'Submitted by[:\s]+([^;\n]+)'
        ]
        
        for pattern in author_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                stats['authors'] = match.group(1).strip()
                logger.info(f"👥 Authors: {stats['authors']}")
                break
        
        # Look for manuscript PDF link
        pdf_links = soup.find_all('a', href=True)
        for link in pdf_links:
            href = link.get('href', '')
            link_text = link.get_text(strip=True).lower()
            if any(keyword in link_text for keyword in ['pdf', 'manuscript', 'download', 'view submission']):
                if 'pdf' in href.lower() or 'download' in href.lower():
                    if href.startswith('/'):
                        stats['manuscript_pdf_url'] = f"https://mc.manuscriptcentral.com{href}"
                    else:
                        stats['manuscript_pdf_url'] = href
                    logger.info(f"📄 Found manuscript PDF link: {stats['manuscript_pdf_url']}")
                    break
        
        # Extract abstract if visible
        abstract_elem = soup.find(text=re.compile('Abstract', re.IGNORECASE))
        if abstract_elem:
            abstract_container = abstract_elem.find_parent()
            if abstract_container:
                abstract_text = abstract_container.get_text(strip=True)
                # Remove the word "Abstract" and clean up
                abstract_text = re.sub(r'^Abstract[:\s]*', '', abstract_text, flags=re.IGNORECASE)
                if len(abstract_text) > 50:  # Likely to be actual abstract
                    stats['abstract'] = abstract_text[:500] + '...' if len(abstract_text) > 500 else abstract_text
                    logger.info(f"📝 Abstract: {stats['abstract'][:100]}...")
        
        # Extract keywords if visible
        keywords_elem = soup.find(text=re.compile('Keywords', re.IGNORECASE))
        if keywords_elem:
            keywords_container = keywords_elem.find_parent()
            if keywords_container:
                keywords_text = keywords_container.get_text(strip=True)
                keywords_text = re.sub(r'^Keywords[:\s]*', '', keywords_text, flags=re.IGNORECASE)
                stats['keywords'] = keywords_text
                logger.info(f"🏷️  Keywords: {stats['keywords']}")
                
        return stats
    
    def enhance_referees_with_email_dates(self, referees, manuscript_id):
        """Enhance referee data with acceptance and contact dates from starred emails"""
        logger.info(f"📧 Fetching email dates for {manuscript_id}...")
        
        try:
            # Fetch starred emails
            starred_emails = fetch_starred_emails(self.journal_name)
            logger.info(f"Found {len(starred_emails)} starred emails")
            
            enhanced_referees = []
            
            for referee in referees:
                referee_name = referee['name']
                enhanced_referee = referee.copy()
                
                # Use appropriate matching function based on journal
                if self.journal_name == "MF":
                    acceptance_date, acceptance_email = robust_match_email_for_referee_mf(referee_name, manuscript_id, "Accepted", starred_emails)
                    contact_date, contact_email = robust_match_email_for_referee_mf(referee_name, manuscript_id, "Contacted", starred_emails)
                else:
                    acceptance_date, acceptance_email = robust_match_email_for_referee_mor(referee_name, manuscript_id, "Accepted", starred_emails)
                    contact_date, contact_email = robust_match_email_for_referee_mor(referee_name, manuscript_id, "Contacted", starred_emails)
                
                # Add acceptance date (when they agreed to review)
                if acceptance_date:
                    enhanced_referee['acceptance_date'] = acceptance_date
                    logger.info(f"  📅 {referee_name} acceptance: {acceptance_date}")
                
                # Add contact date (when we reached out)
                if contact_date:
                    enhanced_referee['contact_date'] = contact_date
                    logger.info(f"  📤 {referee_name} contacted: {contact_date}")
                    
                # Add email details if available
                if acceptance_email:
                    enhanced_referee['email'] = acceptance_email
                elif contact_email:
                    enhanced_referee['email'] = contact_email
                    
                if not acceptance_date and not contact_date:
                    logger.warning(f"  ❌ No email match found for {referee_name}")
                
                enhanced_referees.append(enhanced_referee)
                
        except Exception as e:
            logger.error(f"Error fetching email dates: {e}")
            return referees  # Return original if email fetch fails
            
        return enhanced_referees
    
    def download_referee_report(self, report_url, referee_name, manuscript_id):
        """Download and save referee report"""
        if not report_url:
            return None
            
        try:
            logger.info(f"📥 Downloading report for {referee_name}")
            
            # Store current window handle
            original_window = self.driver.current_window_handle
            
            # Handle JavaScript popup URLs
            if report_url.startswith('javascript:'):
                # Extract the actual URL from the JavaScript
                import re
                url_match = re.search(r"popWindow\('([^']+)'", report_url)
                if url_match:
                    actual_path = url_match.group(1)
                    full_url = f"https://mc.manuscriptcentral.com/{actual_path}"
                    logger.info(f"   Extracted URL: {full_url}")
                    
                    # Open in new tab to avoid navigation issues
                    self.driver.execute_script(f"window.open('{full_url}', '_blank');")
                    time.sleep(1)
                    
                    # Switch to new tab
                    for window_handle in self.driver.window_handles:
                        if window_handle != original_window:
                            self.driver.switch_to.window(window_handle)
                            break
                else:
                    logger.warning(f"   ⚠️  Could not extract URL from JavaScript: {report_url}")
                    return None
            else:
                # Open regular URL in new tab
                self.driver.execute_script(f"window.open('{report_url}', '_blank');")
                time.sleep(1)
                
                # Switch to new tab
                for window_handle in self.driver.window_handles:
                    if window_handle != original_window:
                        self.driver.switch_to.window(window_handle)
                        break
            
            time.sleep(3)  # Give page more time to load
            
            # Get the report content
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Try to find the report text in common locations
            report_text = ""
            
            # Strategy 1: Look for specific report containers
            report_containers = soup.find_all(['div', 'td'], class_=re.compile('report|review|decision|comment', re.I))
            for container in report_containers:
                text = container.get_text(strip=True)
                if len(text) > 100:  # Likely to be actual report content
                    report_text = text
                    break
            
            # Strategy 2: Look for pre-formatted text
            if not report_text:
                pre_elements = soup.find_all('pre')
                for pre in pre_elements:
                    text = pre.get_text(strip=True)
                    if len(text) > 100:
                        report_text = text
                        break
            
            # Strategy 3: Get main content area
            if not report_text:
                main_content = soup.find('div', {'id': re.compile('main|content|body', re.I)})
                if main_content:
                    report_text = main_content.get_text(strip=True)
            
            if report_text:
                # Save report to file
                safe_name = referee_name.replace(' ', '_').replace(',', '')
                report_file = self.output_dir / f"{manuscript_id}_{safe_name}_report.txt"
                
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(f"Referee Report\n")
                    f.write(f"{'='*60}\n")
                    f.write(f"Manuscript: {manuscript_id}\n")
                    f.write(f"Referee: {referee_name}\n")
                    f.write(f"Downloaded: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"URL: {report_url}\n")
                    f.write(f"{'='*60}\n\n")
                    f.write(report_text)
                
                logger.info(f"✅ Report saved to: {report_file}")
                
                # Close the report tab and switch back
                self.driver.close()
                self.driver.switch_to.window(original_window)
                
                return str(report_file)
            else:
                logger.warning(f"⚠️  Could not extract report content from {report_url}")
                
                # Close the tab and switch back even if we couldn't extract content
                try:
                    self.driver.close()
                    self.driver.switch_to.window(original_window)
                except:
                    pass
                
        except Exception as e:
            logger.error(f"❌ Error downloading report: {e}")
            
            # Try to switch back to original window
            try:
                if 'original_window' in locals():
                    self.driver.switch_to.window(original_window)
            except:
                pass
            
        return None
    
    def download_manuscript_pdf(self, pdf_url, manuscript_id):
        """Download manuscript PDF"""
        if not pdf_url:
            return None
            
        try:
            logger.info(f"📥 Downloading manuscript PDF for {manuscript_id}")
            
            # Store current window handle
            original_window = self.driver.current_window_handle
            
            # Open PDF URL in new tab
            self.driver.execute_script(f"window.open('{pdf_url}', '_blank');")
            time.sleep(2)
            
            # Switch to new tab
            for window_handle in self.driver.window_handles:
                if window_handle != original_window:
                    self.driver.switch_to.window(window_handle)
                    break
            
            # Wait for PDF to load
            time.sleep(3)
            
            # Get the current URL (might be different after redirects)
            current_url = self.driver.current_url
            
            # Save PDF URL and close tab
            pdf_file_path = self.output_dir / f"{manuscript_id}_manuscript.pdf"
            
            # Note: Selenium can't directly download PDFs that open in browser
            # We'll save the URL for later download with requests or wget
            url_file = self.output_dir / f"{manuscript_id}_manuscript_url.txt"
            with open(url_file, 'w') as f:
                f.write(current_url)
            
            logger.info(f"✅ Manuscript PDF URL saved to: {url_file}")
            
            # Close the PDF tab and switch back
            self.driver.close()
            self.driver.switch_to.window(original_window)
            
            return str(url_file)
            
        except Exception as e:
            logger.error(f"❌ Error accessing manuscript PDF: {e}")
            
            # Try to switch back to original window
            try:
                if 'original_window' in locals():
                    self.driver.switch_to.window(original_window)
            except:
                pass
                
        return None
        
    def save_results(self, results):
        """Save extraction results"""
        # Save JSON
        json_file = self.output_dir / f"{self.journal_name.lower()}_referee_results.json"
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2)
            
        # Save detailed report
        report_file = self.output_dir / f"{self.journal_name.lower()}_referee_report.txt"
        with open(report_file, 'w') as f:
            f.write(f"FINAL WORKING REFEREE EXTRACTION - {self.journal_name}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Method: {results.get('extraction_method', 'unknown')}\n")
            f.write("="*80 + "\n\n")
            
            total_found = 0
            total_expected = 0
            successful_extractions = 0
            
            for ms in results['manuscripts']:
                ms_id = ms['manuscript_id']
                expected_title = ms.get('expected_title', 'Unknown')
                extracted_title = ms.get('title', 'Not extracted')
                expected_refs = ms.get('expected_referees', 0)
                found_refs = len(ms['referees'])
                completed_refs = len(ms.get('completed_referees', []))
                total_refs = found_refs + completed_refs
                status = ms['extraction_status']
                
                if status == 'success':
                    successful_extractions += 1
                    
                total_found += total_refs
                total_expected += expected_refs
                
                f.write(f"Manuscript: {ms_id}\n")
                f.write(f"Expected Title: {expected_title}\n")
                f.write(f"Extracted Title: {extracted_title}\n")
                f.write(f"Expected Referees: {expected_refs}\n")
                f.write(f"Found Referees: {total_refs} (Active: {found_refs}, Completed: {completed_refs})\n")
                f.write(f"Status: {status}\n")
                
                # Add paper statistics
                f.write(f"Submitted Date: {ms.get('submitted_date', 'Not found')}\n")
                f.write(f"Due Date: {ms.get('due_date', 'Not found')}\n")
                f.write(f"Current Status: {ms.get('status', 'Unknown')}\n")
                
                if ms['referees']:
                    f.write("\nActive Referees (excluding declined/unavailable):\n")
                    for ref in ms['referees']:
                        ref_name = ref['name'] if isinstance(ref, dict) else ref
                        f.write(f"  • {ref_name}\n")
                        
                        if isinstance(ref, dict):
                            # Add email dates if available
                            if ref.get('acceptance_date'):
                                f.write(f"    Acceptance Date: {ref['acceptance_date']}\n")
                            if ref.get('contact_date'):
                                f.write(f"    Contact Date: {ref['contact_date']}\n")
                            if ref.get('email'):
                                f.write(f"    Email: {ref['email']}\n")
                
                # Add completed referees section
                if ms.get('completed_referees'):
                    f.write("\nCompleted Referees (reports submitted):\n")
                    for ref in ms['completed_referees']:
                        ref_name = ref['name'] if isinstance(ref, dict) else ref
                        f.write(f"  • {ref_name}\n")
                        
                        if isinstance(ref, dict):
                            if ref.get('submission_date'):
                                f.write(f"    Report Submitted: {ref['submission_date']}\n")
                            if ref.get('review_decision'):
                                f.write(f"    Decision: {ref['review_decision']}\n")
                            if ref.get('acceptance_date'):
                                f.write(f"    Acceptance Date: {ref['acceptance_date']}\n")
                            if ref.get('email'):
                                f.write(f"    Email: {ref['email']}\n")
                            
                f.write("\n" + "-"*80 + "\n\n")
                
            # Summary
            extraction_rate = (total_found / total_expected * 100) if total_expected > 0 else 0
            f.write(f"SUMMARY:\n")
            f.write(f"Total Manuscripts: {len(results['manuscripts'])}\n")
            f.write(f"Successful Extractions: {successful_extractions}\n")
            f.write(f"Total Expected Referees: {total_expected}\n")
            f.write(f"Total Found Referees: {total_found}\n")
            f.write(f"Extraction Rate: {extraction_rate:.1f}%\n")
            
        logger.info(f"\n💾 Results saved to:")  
        logger.info(f"  - {json_file}")
        logger.info(f"  - {report_file}")
        
        # Print summary
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 FINAL EXTRACTION SUMMARY")
        logger.info(f"{'='*80}")
        
        for ms in results['manuscripts']:
            ms_id = ms['manuscript_id']
            found_refs = len(ms['referees'])
            completed_refs = len(ms.get('completed_referees', []))
            total_refs = found_refs + completed_refs
            expected_refs = ms.get('expected_referees', 0)
            status = "✅" if ms['extraction_status'] == 'success' else "❌"
            
            logger.info(f"\n{status} {ms_id}: {total_refs}/{expected_refs} referees")
            
            if ms.get('title'):
                logger.info(f"   Title: {ms['title'][:60]}...")
                
            for ref in ms['referees']:
                ref_name = ref['name'] if isinstance(ref, dict) else ref
                logger.info(f"   • {ref_name}")
                
                if isinstance(ref, dict):
                    if ref.get('acceptance_date'):
                        logger.info(f"     ✅ Accepted: {ref['acceptance_date']}")
                    if ref.get('contact_date'):
                        logger.info(f"     📤 Contacted: {ref['contact_date']}")
            
            # Log completed referees
            if ms.get('completed_referees'):
                logger.info(f"   📋 Completed Referees:")
                for ref in ms['completed_referees']:
                    ref_name = ref['name'] if isinstance(ref, dict) else ref
                    logger.info(f"   ✅ {ref_name}")
                    
                    if isinstance(ref, dict):
                        if ref.get('submission_date'):
                            logger.info(f"     📄 Report Submitted: {ref['submission_date']}")
                        if ref.get('review_decision'):
                            logger.info(f"     ⚖️  Decision: {ref['review_decision']}")
                        if ref.get('acceptance_date'):
                            logger.info(f"     ✅ Accepted: {ref['acceptance_date']}")
                
            # Log paper statistics
            if ms.get('submitted_date'):
                logger.info(f"   📅 Submitted: {ms['submitted_date']}")
            if ms.get('due_date'):
                logger.info(f"   ⏰ Due: {ms['due_date']}")
                    
        total_found = sum(len(ms['referees']) + len(ms.get('completed_referees', [])) for ms in results['manuscripts'])
        total_expected = sum(ms.get('expected_referees', 0) for ms in results['manuscripts'])
        extraction_rate = (total_found / total_expected * 100) if total_expected > 0 else 0
        
        logger.info(f"\n🎯 OVERALL: {total_found}/{total_expected} referees extracted ({extraction_rate:.1f}%)")


def main():
    """Run extraction for both journals"""
    
    # Extract MF
    logger.info("="*80)
    logger.info("EXTRACTING MF REFEREE DATA")
    logger.info("="*80)
    
    mf_extractor = FinalWorkingRefereeExtractor("MF")
    mf_extractor.extract_referee_data(headless=True)
    
    # Extract MOR
    logger.info("\n\n" + "="*80)
    logger.info("EXTRACTING MOR REFEREE DATA")
    logger.info("="*80)
    
    mor_extractor = FinalWorkingRefereeExtractor("MOR")
    mor_extractor.extract_referee_data(headless=True)


if __name__ == "__main__":
    main()