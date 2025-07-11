#!/usr/bin/env python3
"""
Deep debugging version - captures all page details to understand the checkbox structure
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
logger = logging.getLogger("DEEP_DEBUG_EXTRACTOR")


class DeepDebugRefereeExtractor:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.debug_dir = Path(f"{journal_name.lower()}_deep_debug")
        self.debug_dir.mkdir(exist_ok=True)
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
        filepath = self.debug_dir / filename
        self.driver.save_screenshot(str(filepath))
        logger.info(f"📸 Screenshot: {filename}")
        
    def save_page_source(self, description):
        """Save page source HTML"""
        filename = f"{description.replace(' ', '_')}.html"
        filepath = self.debug_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
        logger.info(f"💾 Saved HTML: {filename}")
        
    def debug_page_elements(self):
        """Debug all interactive elements on the page"""
        logger.info("\n🔍 DEBUGGING PAGE ELEMENTS")
        logger.info("="*60)
        
        # Find all input elements
        inputs = self.driver.find_elements(By.TAG_NAME, "input")
        logger.info(f"\n📌 Found {len(inputs)} input elements:")
        
        for i, inp in enumerate(inputs):
            try:
                inp_type = inp.get_attribute('type')
                inp_name = inp.get_attribute('name')
                inp_value = inp.get_attribute('value')
                inp_id = inp.get_attribute('id')
                inp_class = inp.get_attribute('class')
                is_visible = inp.is_displayed()
                
                logger.info(f"\n  Input #{i+1}:")
                logger.info(f"    Type: {inp_type}")
                logger.info(f"    Name: {inp_name}")
                logger.info(f"    Value: {inp_value}")
                logger.info(f"    ID: {inp_id}")
                logger.info(f"    Class: {inp_class}")
                logger.info(f"    Visible: {is_visible}")
                
                # Check if it's in a table row with manuscript ID
                parent = inp.find_element(By.XPATH, "./ancestor::tr")
                if parent:
                    row_text = parent.text[:100]
                    logger.info(f"    Row text: {row_text}...")
                    
            except Exception as e:
                logger.debug(f"Error processing input {i+1}: {e}")
                
        # Find all clickable images
        images = self.driver.find_elements(By.TAG_NAME, "img")
        clickable_images = []
        
        for img in images:
            try:
                onclick = img.get_attribute('onclick')
                src = img.get_attribute('src')
                alt = img.get_attribute('alt')
                
                if onclick or 'checkbox' in str(src) or 'check' in str(alt):
                    clickable_images.append({
                        'src': src,
                        'alt': alt,
                        'onclick': onclick
                    })
            except:
                pass
                
        if clickable_images:
            logger.info(f"\n📌 Found {len(clickable_images)} potentially clickable images:")
            for img in clickable_images:
                logger.info(f"  Image: {img}")
                
        # Find all links
        links = self.driver.find_elements(By.TAG_NAME, "a")
        manuscript_links = []
        
        for link in links:
            try:
                href = link.get_attribute('href')
                text = link.text
                
                if self.journal_name == "MF":
                    if 'MAFI-' in text:
                        manuscript_links.append({'text': text, 'href': href})
                else:
                    if 'MOR-' in text:
                        manuscript_links.append({'text': text, 'href': href})
            except:
                pass
                
        if manuscript_links:
            logger.info(f"\n📌 Found {len(manuscript_links)} manuscript links:")
            for link in manuscript_links[:5]:  # Show first 5
                logger.info(f"  Link: {link['text']} -> {link['href']}")
                
    def find_and_analyze_checkboxes(self):
        """Deep analysis of checkbox elements"""
        logger.info("\n🔍 ANALYZING CHECKBOX STRUCTURE")
        logger.info("="*60)
        
        # Get manuscript IDs from page
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        if self.journal_name == "MF":
            pattern = r'MAFI-\d{4}-\d+'
        else:
            pattern = r'MOR-\d{4}-\d+'
            
        manuscript_ids = list(set(re.findall(pattern, soup.get_text())))
        logger.info(f"\n📄 Manuscripts on page: {manuscript_ids}")
        
        # For each manuscript, find its row and analyze
        for ms_id in manuscript_ids:
            logger.info(f"\n🔍 Analyzing row for {ms_id}:")
            
            # Find the row containing this manuscript
            rows = self.driver.find_elements(By.TAG_NAME, "tr")
            
            for row in rows:
                try:
                    row_text = row.text
                    if ms_id in row_text:
                        # Found the row
                        logger.info(f"  ✅ Found row containing {ms_id}")
                        
                        # Get all cells in this row
                        cells = row.find_elements(By.TAG_NAME, "td")
                        logger.info(f"  📊 Row has {len(cells)} cells")
                        
                        # Analyze last cell (typically Take Action column)
                        if cells:
                            last_cell = cells[-1]
                            logger.info(f"  🎯 Last cell text: '{last_cell.text}'")
                            
                            # Find all elements in last cell
                            all_elements = last_cell.find_elements(By.XPATH, ".//*")
                            logger.info(f"  📦 Last cell contains {len(all_elements)} elements")
                            
                            for elem in all_elements:
                                tag = elem.tag_name
                                elem_type = elem.get_attribute('type')
                                elem_class = elem.get_attribute('class')
                                elem_onclick = elem.get_attribute('onclick')
                                
                                if tag or elem_type or elem_onclick:
                                    logger.info(f"    Element: <{tag}> type='{elem_type}' class='{elem_class}' onclick='{elem_onclick}'")
                                    
                        break
                        
                except Exception as e:
                    logger.debug(f"Error analyzing row: {e}")
                    
    def try_different_click_methods(self, manuscript_id):
        """Try different methods to select a manuscript"""
        logger.info(f"\n🎯 TRYING DIFFERENT CLICK METHODS FOR {manuscript_id}")
        logger.info("="*60)
        
        success = False
        
        # Method 1: Direct manuscript ID link
        try:
            logger.info("\n📍 Method 1: Clicking manuscript ID directly...")
            ms_link = self.driver.find_element(By.LINK_TEXT, manuscript_id)
            ms_link.click()
            time.sleep(2)
            
            # Check if we navigated
            if "View Submission" in self.driver.page_source or "Referee" in self.driver.page_source:
                logger.info("  ✅ SUCCESS! Navigated to manuscript details")
                success = True
                self.extract_referee_details_from_current_page(manuscript_id)
                return True
        except Exception as e:
            logger.info(f"  ❌ Method 1 failed: {e}")
            
        # Method 2: JavaScript click on table row
        if not success:
            try:
                logger.info("\n📍 Method 2: JavaScript click on table row...")
                rows = self.driver.find_elements(By.TAG_NAME, "tr")
                
                for row in rows:
                    if manuscript_id in row.text:
                        self.driver.execute_script("arguments[0].click();", row)
                        time.sleep(2)
                        
                        if "View Submission" in self.driver.page_source:
                            logger.info("  ✅ SUCCESS! Row click worked")
                            success = True
                            self.extract_referee_details_from_current_page(manuscript_id)
                            return True
                        break
            except Exception as e:
                logger.info(f"  ❌ Method 2 failed: {e}")
                
        # Method 3: Find any clickable element in the row
        if not success:
            try:
                logger.info("\n📍 Method 3: Finding clickable elements in row...")
                rows = self.driver.find_elements(By.TAG_NAME, "tr")
                
                for row in rows:
                    if manuscript_id in row.text:
                        # Try all links in the row
                        links = row.find_elements(By.TAG_NAME, "a")
                        for link in links:
                            href = link.get_attribute('href')
                            if href and '#' not in href and 'javascript' not in href:
                                logger.info(f"  🔗 Clicking link: {link.text}")
                                link.click()
                                time.sleep(2)
                                
                                if "View Submission" in self.driver.page_source:
                                    logger.info("  ✅ SUCCESS! Link click worked")
                                    success = True
                                    self.extract_referee_details_from_current_page(manuscript_id)
                                    return True
                        break
            except Exception as e:
                logger.info(f"  ❌ Method 3 failed: {e}")
                
        return success
        
    def extract_referee_details_from_current_page(self, manuscript_id):
        """Extract referee details from the current page"""
        logger.info(f"\n📊 EXTRACTING REFEREE DETAILS FOR {manuscript_id}")
        logger.info("="*60)
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        page_text = soup.get_text()
        
        # Save the page for analysis
        self.save_page_source(f"manuscript_{manuscript_id}_details")
        self.take_screenshot(f"manuscript_{manuscript_id}_details")
        
        # Extract title
        title = "Unknown"
        title_patterns = [
            r'Title[:\s]+([^\n]+)',
            r'Manuscript Title[:\s]+([^\n]+)',
            rf'{manuscript_id}[^\n]*\n[^\n]*\n([^\n]+)'
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, page_text, re.MULTILINE)
            if match:
                title = match.group(1).strip()
                break
                
        logger.info(f"\n📄 Title: {title}")
        
        # Look for referee information
        referees = []
        
        # Method 1: Look for referee names in links
        all_links = soup.find_all('a')
        potential_referees = []
        
        for link in all_links:
            link_text = link.get_text(strip=True)
            
            # Check if this looks like a person's name
            if self.is_referee_name(link_text):
                href = link.get('href', '')
                onclick = link.get('onclick', '')
                
                potential_referees.append({
                    'name': link_text,
                    'href': href,
                    'onclick': onclick,
                    'element': link
                })
                
        logger.info(f"\n👥 Found {len(potential_referees)} potential referee names:")
        
        for ref in potential_referees:
            logger.info(f"  • {ref['name']}")
            
            # Try to extract more details about this referee
            referee_data = {
                'name': ref['name'],
                'email': '',
                'status': 'unknown',
                'dates': {}
            }
            
            # Look for status and dates near the name
            name_index = page_text.find(ref['name'])
            if name_index != -1:
                context = page_text[max(0, name_index-500):name_index+500]
                
                # Extract status
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
                    referee_data['dates'] = dates_found
                    
            referees.append(referee_data)
            
        # Try to extract emails by clicking on names
        for i, ref in enumerate(referees):
            try:
                logger.info(f"\n🔍 Trying to extract email for {ref['name']}...")
                
                # Save current window
                main_window = self.driver.current_window_handle
                
                # Click the referee name
                referee_link = self.driver.find_element(By.LINK_TEXT, ref['name'])
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
                    
                    if email_match:
                        referees[i]['email'] = email_match.group(0)
                        logger.info(f"  ✅ Found email: {referees[i]['email']}")
                        
                    # Close popup
                    self.driver.close()
                    self.driver.switch_to.window(main_window)
                    
            except Exception as e:
                logger.debug(f"Could not extract email: {e}")
                
        # Save results
        results = {
            'manuscript_id': manuscript_id,
            'title': title,
            'referees': referees,
            'extraction_time': datetime.now().isoformat()
        }
        
        results_file = self.debug_dir / f"{manuscript_id}_referees.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
            
        logger.info(f"\n💾 Saved results to: {results_file}")
        
        return results
        
    def is_referee_name(self, text):
        """Check if text is likely a referee name"""
        if not text or len(text) < 3:
            return False
            
        # Exclude common UI elements
        exclude_words = [
            'view', 'download', 'edit', 'manuscript', 'submission',
            'center', 'logout', 'home', 'help', 'associate', 'editor',
            'action', 'select', 'pdf', 'report', 'email', 'send'
        ]
        
        text_lower = text.lower()
        if any(word in text_lower for word in exclude_words):
            return False
            
        # Must have at least one space (first and last name)
        if ' ' not in text:
            return False
            
        # Check for name patterns
        parts = text.split()
        if len(parts) >= 2 and len(parts) <= 5:
            # Check if starts with capital letter
            if parts[0][0].isupper():
                return True
                
        return False
        
    def run_deep_debug(self):
        """Run deep debugging extraction"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 DEEP DEBUG EXTRACTION FOR {self.journal_name}")
        logger.info(f"{'='*80}")
        
        self.create_driver()
        
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
            self.save_page_source("category_list")
            
            # Debug page elements
            self.debug_page_elements()
            
            # Analyze checkbox structure
            self.find_and_analyze_checkboxes()
            
            # Get manuscript IDs
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            if self.journal_name == "MF":
                pattern = r'MAFI-\d{4}-\d+'
            else:
                pattern = r'MOR-\d{4}-\d+'
                
            manuscript_ids = list(set(re.findall(pattern, soup.get_text())))
            
            # Try to process first manuscript
            if manuscript_ids:
                ms_id = manuscript_ids[0]
                logger.info(f"\n🎯 Attempting to process: {ms_id}")
                
                success = self.try_different_click_methods(ms_id)
                
                if success:
                    logger.info("\n✅ Successfully extracted referee details!")
                else:
                    logger.info("\n❌ Could not navigate to manuscript details")
                    
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            self.take_screenshot("error")
            
        finally:
            input("\n⏸️  Press Enter to close browser...")
            self.driver.quit()


def main():
    """Run deep debug for MF only first"""
    
    # Debug MF
    logger.info("="*80)
    logger.info("DEEP DEBUG: MF JOURNAL")
    logger.info("="*80)
    
    mf_extractor = DeepDebugRefereeExtractor("MF")
    mf_extractor.run_deep_debug()


if __name__ == "__main__":
    main()