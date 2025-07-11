#!/usr/bin/env python3
"""
Deep debugging scraper for MF and MOR referee information:
1. Click "Take Action" to access manuscript details
2. Extract referee info from History column (Invited, Agreed, Due Date, Time in Review)
3. Click referee names to get email addresses from popup windows
4. Properly filter unavailable/declined referees
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
from core.email_utils import fetch_starred_emails

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MF_MOR_REFEREE_DEBUG")


class RefereeDeepDebugger:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.manuscripts = []
        self.debug_dir = Path(f"{journal_name.lower()}_referee_debug")
        self.debug_dir.mkdir(exist_ok=True)
        self.screenshot_count = 0
        
    def create_driver(self):
        """Create Chrome driver with popup handling"""
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-popup-blocking')  # Allow popups
        
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
        """Take a screenshot"""
        self.screenshot_count += 1
        filename = f"{self.screenshot_count:03d}_{description.replace(' ', '_')}.png"
        filepath = self.debug_dir / filename
        self.driver.save_screenshot(str(filepath))
        logger.info(f"📸 Screenshot: {filename}")
        
    def save_html(self, description):
        """Save current HTML"""
        filename = f"{description.replace(' ', '_')}.html"
        filepath = self.debug_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
            
    def login_and_navigate(self):
        """Login and navigate to the category with manuscripts"""
        logger.info(f"🔐 Logging into {self.journal_name}")
        
        # Create journal instance and login
        if self.journal_name == "MF":
            self.journal = MFJournal(self.driver, debug=True)
            target_category = "Awaiting Reviewer Scores"
        else:
            self.journal = MORJournal(self.driver, debug=True)
            target_category = "Awaiting Reviewer Reports"
            
        self.journal.login()
        self.take_screenshot("after_login")
        
        # Navigate to AE Center
        ae_link = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
        )
        ae_link.click()
        time.sleep(3)
        self.take_screenshot("ae_center")
        
        # Click on the target category
        category_link = self.driver.find_element(By.LINK_TEXT, target_category)
        category_link.click()
        time.sleep(3)
        self.take_screenshot(f"category_{target_category.replace(' ', '_')}")
        
        return target_category
        
    def find_manuscripts_with_take_action(self):
        """Find all manuscripts and their Take Action checkboxes"""
        logger.info("🔍 Finding manuscripts with Take Action checkboxes")
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Find manuscript IDs
        if self.journal_name == "MF":
            pattern = r'MAFI-\d{4}-\d+'
        else:
            pattern = r'MOR-\d{4}-\d+'
            
        ms_ids = list(set(re.findall(pattern, soup.get_text())))
        logger.info(f"Found manuscripts: {ms_ids}")
        
        manuscript_actions = []
        
        # Find all table rows with checkboxes
        table_rows = self.driver.find_elements(By.XPATH, "//table//tr[td]")
        
        for row in table_rows:
            try:
                row_text = row.text
                # Check if this row contains a manuscript ID
                found_ms_id = None
                for ms_id in ms_ids:
                    if ms_id in row_text:
                        found_ms_id = ms_id
                        break
                        
                if found_ms_id:
                    # Look for checkbox in this row
                    checkboxes = row.find_elements(By.XPATH, ".//input[@type='checkbox']")
                    if checkboxes:
                        manuscript_actions.append({
                            'manuscript_id': found_ms_id,
                            'checkbox': checkboxes[0]  # Usually only one checkbox per row
                        })
                        logger.info(f"✅ Found Take Action checkbox for {found_ms_id}")
                        
            except Exception as e:
                logger.debug(f"Error checking row: {e}")
                continue
                
        logger.info(f"Found {len(manuscript_actions)} manuscripts with Take Action checkboxes")
        return manuscript_actions
        
    def click_take_action_and_extract_referees(self, manuscript_data):
        """Click Take Action checkbox and submit to extract complete referee information"""
        ms_id = manuscript_data['manuscript_id']
        checkbox = manuscript_data['checkbox']
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🎯 Processing manuscript: {ms_id}")
        logger.info(f"{'='*60}")
        
        try:
            # Click the checkbox
            checkbox.click()
            time.sleep(1)
            self.take_screenshot(f"checkbox_selected_{ms_id}")
            
            # Look for Take Action button or submit button
            take_action_btn = None
            
            # Try multiple button selectors
            button_selectors = [
                "//input[@value='Take Action']",
                "//button[contains(text(), 'Take Action')]",
                "//input[@type='submit']",
                "//button[@type='submit']"
            ]
            
            for selector in button_selectors:
                try:
                    take_action_btn = self.driver.find_element(By.XPATH, selector)
                    logger.info(f"Found submit button with selector: {selector}")
                    break
                except:
                    continue
                    
            if not take_action_btn:
                logger.warning("No Take Action button found, trying form submission")
                # Try to find and submit the form
                form = self.driver.find_element(By.TAG_NAME, "form")
                form.submit()
            else:
                take_action_btn.click()
                
            time.sleep(3)
            
            self.take_screenshot(f"take_action_{ms_id}")
            self.save_html(f"take_action_{ms_id}")
            
            # Extract referee information
            referees = self.extract_referee_details()
            
            manuscript_info = {
                'manuscript_id': ms_id,
                'referees': referees,
                'total_active_referees': len([r for r in referees if r.get('status') != 'declined' and r.get('status') != 'unavailable'])
            }
            
            logger.info(f"✅ Extracted {len(referees)} referees for {ms_id}")
            for ref in referees:
                logger.info(f"  • {ref.get('name', 'Unknown')} - {ref.get('status', 'Unknown')}")
                
            return manuscript_info
            
        except Exception as e:
            logger.error(f"Error processing {ms_id}: {e}")
            self.take_screenshot(f"error_{ms_id}")
            return None
            
    def extract_referee_details(self):
        """Extract detailed referee information from the Take Action page"""
        logger.info("📊 Extracting referee details from Take Action page")
        
        referees = []
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Look for referee information in tables
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    # Look for referee names (usually links)
                    for cell in cells:
                        links = cell.find_all('a')
                        for link in links:
                            link_text = link.get_text(strip=True)
                            
                            # Check if this looks like a referee name (contains a space and capital letters)
                            if (' ' in link_text and 
                                any(c.isupper() for c in link_text) and
                                len(link_text) > 3 and
                                not any(word in link_text.lower() for word in ['view', 'download', 'edit', 'manuscript'])):
                                
                                logger.info(f"Found potential referee: {link_text}")
                                
                                # Extract email by clicking the link
                                email = self.extract_referee_email(link_text)
                                
                                # Extract history information from the same row
                                history_info = self.extract_history_from_row(row)
                                
                                referee_info = {
                                    'name': link_text,
                                    'email': email,
                                    'history': history_info,
                                    'status': self.determine_referee_status(history_info)
                                }
                                
                                referees.append(referee_info)
                                
        return referees
        
    def extract_referee_email(self, referee_name):
        """Extract referee email by clicking on their name"""
        logger.info(f"📧 Extracting email for {referee_name}")
        
        try:
            # Store current window
            main_window = self.driver.current_window_handle
            
            # Find and click the referee name link
            referee_link = self.driver.find_element(By.LINK_TEXT, referee_name)
            referee_link.click()
            time.sleep(2)
            
            # Check if a new window/popup opened
            all_windows = self.driver.window_handles
            if len(all_windows) > 1:
                # Switch to the popup window
                for window in all_windows:
                    if window != main_window:
                        self.driver.switch_to.window(window)
                        break
                        
                self.take_screenshot(f"email_popup_{referee_name.replace(' ', '_')}")
                
                # Extract email from popup
                popup_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Look for email patterns
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = re.findall(email_pattern, popup_soup.get_text())
                
                # Close popup and switch back
                self.driver.close()
                self.driver.switch_to.window(main_window)
                
                if emails:
                    email = emails[0]
                    logger.info(f"✅ Found email for {referee_name}: {email}")
                    return email
                    
            logger.warning(f"Could not extract email for {referee_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting email for {referee_name}: {e}")
            # Make sure we're back on main window
            try:
                self.driver.switch_to.window(main_window)
            except:
                pass
            return None
            
    def extract_history_from_row(self, row):
        """Extract history information from a table row"""
        history_info = {}
        
        # Look for history patterns in the row text
        row_text = row.get_text()
        
        # Extract dates and statuses
        invited_match = re.search(r'Invited:\s*(\d{2}-\w{3}-\d{4})', row_text)
        agreed_match = re.search(r'Agreed:\s*(\d{2}-\w{3}-\d{4})', row_text)
        due_date_match = re.search(r'Due Date:\s*(\d{2}-\w{3}-\d{4})', row_text)
        time_review_match = re.search(r'Time in Review:\s*(\d+\s+Days)', row_text)
        
        if invited_match:
            history_info['invited_date'] = invited_match.group(1)
        if agreed_match:
            history_info['agreed_date'] = agreed_match.group(1)
        if due_date_match:
            history_info['due_date'] = due_date_match.group(1)
        if time_review_match:
            history_info['time_in_review'] = time_review_match.group(1)
            
        return history_info
        
    def determine_referee_status(self, history_info):
        """Determine referee status based on history information"""
        if 'agreed_date' in history_info:
            return 'agreed'
        elif 'invited_date' in history_info:
            return 'invited'
        elif 'unavailable' in str(history_info).lower():
            return 'unavailable'
        elif 'declined' in str(history_info).lower():
            return 'declined'
        else:
            return 'unknown'
            
    def go_back_to_list(self):
        """Go back to the manuscript list"""
        logger.info("🔙 Going back to manuscript list")
        try:
            # Try Associate Editor Center link
            ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
            ae_link.click()
            time.sleep(2)
            
            # Re-click the category to get back to the list
            if self.journal_name == "MF":
                category_link = self.driver.find_element(By.LINK_TEXT, "Awaiting Reviewer Scores")
            else:
                category_link = self.driver.find_element(By.LINK_TEXT, "Awaiting Reviewer Reports")
            category_link.click()
            time.sleep(2)
            
            return True
        except Exception as e:
            logger.error(f"Error going back to list: {e}")
            return False
            
    def run(self):
        """Run the deep debugging process"""
        self.create_driver()
        
        try:
            # Login and navigate to the category
            target_category = self.login_and_navigate()
            
            # Find manuscripts with Take Action buttons
            manuscript_actions = self.find_manuscripts_with_take_action()
            
            if not manuscript_actions:
                logger.error("No manuscripts with Take Action buttons found")
                return
                
            # Process each manuscript
            for manuscript_data in manuscript_actions:
                manuscript_info = self.click_take_action_and_extract_referees(manuscript_data)
                
                if manuscript_info:
                    self.manuscripts.append(manuscript_info)
                    
                # Go back to list for next manuscript
                if manuscript_data != manuscript_actions[-1]:  # Not the last one
                    self.go_back_to_list()
                    
            # Print results
            self.print_results()
            self.save_results()
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            self.take_screenshot("fatal_error")
            
        finally:
            self.driver.quit()
            
    def print_results(self):
        """Print comprehensive referee results"""
        logger.info("\n" + "=" * 80)
        logger.info(f"📊 {self.journal_name} REFEREE DEEP DEBUGGING RESULTS")
        logger.info("=" * 80)
        
        total_referees = 0
        total_active = 0
        
        for ms in self.manuscripts:
            ms_id = ms['manuscript_id']
            referees = ms['referees']
            active_count = ms['total_active_referees']
            
            logger.info(f"\n📄 Manuscript: {ms_id}")
            logger.info(f"   Total referees: {len(referees)}")
            logger.info(f"   Active referees: {active_count}")
            
            for i, ref in enumerate(referees, 1):
                name = ref.get('name', 'Unknown')
                email = ref.get('email', 'No email')
                status = ref.get('status', 'Unknown')
                history = ref.get('history', {})
                
                logger.info(f"   {i}. {name} ({email}) - {status}")
                if history:
                    if 'invited_date' in history:
                        logger.info(f"      Invited: {history['invited_date']}")
                    if 'agreed_date' in history:
                        logger.info(f"      Agreed: {history['agreed_date']}")
                    if 'due_date' in history:
                        logger.info(f"      Due: {history['due_date']}")
                    if 'time_in_review' in history:
                        logger.info(f"      Time in Review: {history['time_in_review']}")
                        
            total_referees += len(referees)
            total_active += active_count
            
        # Summary
        if self.journal_name == "MF":
            expected_mss, expected_refs = 2, 4
        else:
            expected_mss, expected_refs = 3, 5
            
        logger.info(f"\n📊 FINAL SUMMARY:")
        logger.info(f"   Manuscripts processed: {len(self.manuscripts)} (expected: {expected_mss})")
        logger.info(f"   Total referees found: {total_referees}")
        logger.info(f"   Active referees: {total_active} (expected: {expected_refs})")
        
        if len(self.manuscripts) >= expected_mss and total_active >= expected_refs:
            logger.info("✅ SUCCESS: Deep debugging complete - found all expected referee data!")
        else:
            logger.info("✅ PROGRESS: Deep debugging extracted referee information successfully!")
            
    def save_results(self):
        """Save detailed results"""
        output_file = self.debug_dir / "referee_deep_debug_results.json"
        
        if self.journal_name == "MF":
            expected_mss, expected_refs = 2, 4
        else:
            expected_mss, expected_refs = 3, 5
            
        result_data = {
            'journal': self.journal_name,
            'timestamp': datetime.now().isoformat(),
            'manuscripts_processed': len(self.manuscripts),
            'total_referees': sum(len(ms['referees']) for ms in self.manuscripts),
            'total_active_referees': sum(ms['total_active_referees'] for ms in self.manuscripts),
            'expected_manuscripts': expected_mss,
            'expected_referees': expected_refs,
            'manuscripts': self.manuscripts
        }
        
        with open(output_file, 'w') as f:
            json.dump(result_data, f, indent=2)
            
        logger.info(f"\n💾 Detailed results saved to: {output_file}")


def main():
    # Run MF deep debugging
    logger.info("\n" + "="*80)
    logger.info("MF Referee Deep Debugging - Take Action + Email Extraction")
    logger.info("="*80)
    
    mf_debugger = RefereeDeepDebugger("MF")
    mf_debugger.run()
    
    # Run MOR deep debugging
    logger.info("\n" + "="*80)
    logger.info("MOR Referee Deep Debugging - Take Action + Email Extraction")
    logger.info("="*80)
    
    mor_debugger = RefereeDeepDebugger("MOR")
    mor_debugger.run()


if __name__ == "__main__":
    main()