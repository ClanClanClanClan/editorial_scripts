#!/usr/bin/env python3
"""
Base extractor for SIAM journals (SICON/SIFIN)
Implements all production features using enhanced base class
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import time
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup, NavigableString

from core.enhanced_base import EnhancedBaseJournal
from core.email_utils import fetch_latest_verification_code


class SIAMJournalExtractor(EnhancedBaseJournal):
    """Base extractor for SIAM journals with all production features"""
    
    def __init__(self, journal_code: str):
        """Initialize with journal-specific configuration"""
        config = {
            'journal_name': journal_code,
            'journal_code': journal_code,
            'base_url': f'http://{journal_code.lower()}.siam.org',
            'download_types': ['pdf', 'referee_report', 'cover_letter']
        }
        
        # Journal-specific folder IDs
        self.folder_mapping = {
            'SICON': '1800',
            'SIFIN': '1802'  # To be verified
        }
        
        super().__init__(config)
        self.folder_id = self.folder_mapping.get(journal_code, '1800')
        self.manuscripts_data = []
    
    def authenticate(self) -> bool:
        """ORCID authentication for SIAM journals"""
        try:
            self.logger.info(f"Starting ORCID authentication for {self.journal_name}")
            
            # Navigate to login page
            login_url = f"{self.config['base_url']}/cgi-bin/main.plex"
            self.driver.get(login_url)
            time.sleep(3)
            
            # Handle privacy notification modal for SIFIN
            if self.journal_code == 'SIFIN':
                try:
                    continue_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]"))
                    )
                    continue_button.click()
                    time.sleep(2)
                    self.logger.info("Clicked privacy notification Continue button")
                except TimeoutException:
                    self.logger.info("No privacy notification modal found")
                except Exception as e:
                    self.logger.warning(f"Privacy notification handling failed: {e}")
            
            # Check if we're already on a login page (SIFIN) or need to click login (SICON)
            if self.journal_code == 'SICON':
                # SICON already shows login page directly - no need to click additional login link
                self.logger.info("SICON - already on login page")
            else:
                # SIFIN - already on login page
                self.logger.info("SIFIN - already on login page")
            
            # Click Sign in with ORCID - try multiple selectors
            orcid_element = None
            
            # Try to find ORCID element - both SICON and SIFIN use links with orcid in href
            try:
                orcid_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'orcid')]")
                if orcid_links:
                    orcid_element = orcid_links[0]
                    self.logger.info(f"Found ORCID link: {orcid_element.get_attribute('href')}")
            except:
                pass
            
            # If not found, try other selectors
            if not orcid_element:
                try:
                    # Try exact text button
                    orcid_element = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Sign in to ORCID')]"))
                    )
                except:
                    try:
                        # Try with just ORCID
                        orcid_element = self.driver.find_element(By.XPATH, "//button[contains(., 'ORCID')]")
                    except:
                        try:
                            # Try input button
                            orcid_element = self.driver.find_element(By.XPATH, "//input[@type='button' and contains(@value, 'ORCID')]")
                        except:
                            try:
                                # Try link with text
                                orcid_element = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Sign in with ORCID')]")
                            except:
                                try:
                                    # Try image link (SICON uses an image)
                                    orcid_element = self.driver.find_element(By.XPATH, "//a[contains(@href, 'orcid')]")
                                except:
                                    pass
            
            if not orcid_element:
                raise Exception("Could not find ORCID sign-in element")
            
            # Click using JavaScript to avoid interception
            self.driver.execute_script("arguments[0].click();", orcid_element)
            self.logger.info("Clicked ORCID sign-in")
            
            # Get ORCID credentials from 1Password
            orcid_username = self.cred_manager.get('ORCID', 'email')  # ORCID uses email
            orcid_password = self.cred_manager.get('ORCID', 'password')
            
            # Fallback to environment variables if 1Password doesn't have them
            if not orcid_username:
                import os
                orcid_username = os.getenv('ORCID_USER') or os.getenv('ORCID_USERNAME')
            if not orcid_password:
                import os
                orcid_password = os.getenv('ORCID_PASS') or os.getenv('ORCID_PASSWORD')
            
            if not orcid_username or not orcid_password:
                raise Exception("ORCID credentials not found in 1Password or environment")
            
            # Wait for ORCID page to load
            time.sleep(2)
            
            # Enter ORCID credentials - try multiple selectors
            username_field = None
            try:
                username_field = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "username"))
                )
            except:
                try:
                    username_field = self.driver.find_element(By.ID, "username-input")
                except:
                    username_field = self.driver.find_element(By.NAME, "userId")
            
            if not username_field:
                raise Exception("Could not find username field")
                
            username_field.clear()
            username_field.send_keys(orcid_username)
            
            password_field = self.driver.find_element(By.ID, "password")
            password_field.send_keys(orcid_password)
            
            # Submit login
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            # Handle 2FA if needed
            if self._check_2fa_required():
                self._handle_2fa()
            
            # Verify login success
            time.sleep(3)
            if "main.plex" in self.driver.current_url:
                self.logger.info("ORCID authentication successful")
                return True
            else:
                self.logger.error("Authentication may have failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            # Save screenshot for debugging
            try:
                screenshot_path = f"sifin_auth_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                self.driver.save_screenshot(screenshot_path)
                self.logger.error(f"Screenshot saved to {screenshot_path}")
            except:
                pass
            return False
    
    def _check_2fa_required(self) -> bool:
        """Check if 2FA is required"""
        try:
            WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.NAME, "recoveryCode")))
            return True
        except TimeoutException:
            return False
    
    def _handle_2fa(self):
        """Handle 2FA with Gmail verification"""
        self.logger.info("2FA required, fetching code from email")
        
        # Fetch code from Gmail
        if self.gmail_service:
            verification_code = fetch_latest_verification_code(self.gmail_service)
            if verification_code:
                code_field = self.driver.find_element(By.NAME, "recoveryCode")
                code_field.send_keys(verification_code)
                
                submit_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
                submit_button.click()
                self.logger.info("2FA code submitted")
            else:
                raise Exception("Could not fetch verification code from email")
        else:
            raise Exception("Gmail service not available for 2FA")
    
    def extract_manuscripts(self) -> List[dict]:
        """Extract all manuscripts with referee data"""
        try:
            self.logger.info(f"Starting manuscript extraction for {self.journal_name}")
            
            # Navigate to manuscripts under review
            self._navigate_to_manuscripts()
            
            # Extract manuscript data
            manuscripts = self._parse_manuscripts_table()
            
            # Extract detailed referee information for each manuscript
            for manuscript in manuscripts:
                self._extract_referee_details(manuscript)
                
                # Download documents
                self._download_manuscript_documents(manuscript)
                
                # Verify with email
                for referee in manuscript.get('referees', []):
                    self.verify_referee_with_email(referee, manuscript)
            
            self.manuscripts_data = manuscripts
            self.logger.info(f"Extracted {len(manuscripts)} manuscripts")
            
            return manuscripts
            
        except Exception as e:
            self.logger.error(f"Manuscript extraction failed: {e}")
            raise
    
    def _navigate_to_manuscripts(self):
        """Navigate to manuscripts page with timeout protection"""
        if self.journal_code == 'SICON':
            # Set page load timeout for SICON
            self.driver.set_page_load_timeout(30)
            
            # Add memory cleanup
            self.driver.execute_script("window.stop();")
            self.driver.execute_script("if (window.gc) window.gc();")
        
        self._do_navigate_to_manuscripts()
    
    def _do_navigate_to_manuscripts(self):
        """Navigate to manuscripts under review"""
        if self.journal_code == 'SICON':
            # Handle potential cookie policy popup
            try:
                cookie_close = self.driver.find_element(By.ID, "cookie-policy-layer-bg")
                if cookie_close.is_displayed():
                    self.driver.execute_script("arguments[0].style.display = 'none';", cookie_close)
                    self.logger.info("Dismissed cookie policy popup")
            except:
                pass
            
            # SICON uses folder navigation - find the manuscripts folder
            # Try multiple approaches to find the manuscripts
            navigation_success = False
            
            # Approach 1: Try to find "All Pending Manuscripts" link
            try:
                short_wait = WebDriverWait(self.driver, 10)
                folder_link = short_wait.until(
                    EC.element_to_be_clickable((By.XPATH, f"//a[contains(@href, 'folder_id={self.folder_id}') and contains(text(), 'All Pending')]"))
                )
                self.driver.execute_script("arguments[0].click();", folder_link)
                time.sleep(3)
                self.logger.info("Navigated to All Pending Manuscripts")
                navigation_success = True
            except:
                self.logger.debug("Could not find All Pending Manuscripts link")
            
            # Approach 2: Try to find "Under Review" link
            if not navigation_success:
                try:
                    short_wait = WebDriverWait(self.driver, 10)
                    folder_link = short_wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Under Review') and contains(text(), 'AE')]"))
                    )
                    self.driver.execute_script("arguments[0].click();", folder_link)
                    time.sleep(3)
                    self.logger.info("Navigated to Under Review manuscripts")
                    navigation_success = True
                except:
                    self.logger.debug("Could not find Under Review link")
            
            # Approach 3: Try any AE folder link
            if not navigation_success:
                try:
                    short_wait = WebDriverWait(self.driver, 10)
                    folder_link = short_wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'AE') and contains(@href, 'ndt_folder')]"))
                    )
                    self.driver.execute_script("arguments[0].click();", folder_link)
                    time.sleep(3)
                    self.logger.info("Navigated to AE manuscripts folder")
                    navigation_success = True
                except:
                    self.logger.debug("Could not find AE folder link")
            
            # Approach 4: Try to find any link with the folder_id
            if not navigation_success:
                try:
                    short_wait = WebDriverWait(self.driver, 10)
                    folder_link = short_wait.until(
                        EC.element_to_be_clickable((By.XPATH, f"//a[contains(@href, 'folder_id={self.folder_id}')]"))
                    )
                    self.driver.execute_script("arguments[0].click();", folder_link)
                    time.sleep(3)
                    self.logger.info(f"Navigated to folder with ID {self.folder_id}")
                    navigation_success = True
                except:
                    self.logger.debug(f"Could not find folder link with ID {self.folder_id}")
            
            # Approach 5: Try to find manuscripts directly on the current page
            if not navigation_success:
                self.logger.warning("Could not navigate to manuscripts folder, checking current page for manuscripts")
                # Check if manuscripts are already visible on current page
                try:
                    manuscripts_table = self.driver.find_element(By.XPATH, "//table[@border='1']")
                    if manuscripts_table:
                        self.logger.info("Found manuscripts table on current page")
                        navigation_success = True
                except:
                    self.logger.error("Could not find manuscripts table anywhere")
            
            if not navigation_success:
                raise Exception("Could not navigate to manuscripts - all approaches failed")
        else:
            # SIFIN lists manuscripts directly in dashboard
            self.logger.info("SIFIN manuscripts are listed directly in dashboard")
    
    def _parse_manuscripts_table(self) -> List[dict]:
        """Parse manuscripts table with perfect status parsing"""
        manuscripts = []
        
        if self.journal_code == 'SICON':
            # SICON uses a table format
            # Check for "No Manuscripts" first
            try:
                no_manuscripts = self.driver.find_element(By.XPATH, "//i[contains(text(), 'No Manuscripts')]")
                if no_manuscripts:
                    self.logger.info("No manuscripts found in SICON folder")
                    return manuscripts
            except:
                pass
            
            # Get table HTML
            try:
                table = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//table[@border='1']"))
                )
            except TimeoutException:
                self.logger.warning("No manuscripts table found, checking for alternative table structures")
                # Try alternative table patterns
                try:
                    table = self.driver.find_element(By.XPATH, "//table[contains(@id, 'manuscript') or contains(@class, 'manuscript')]")
                except:
                    self.logger.info("No manuscripts table found - may be empty folder")
                    return manuscripts
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            table = soup.find('table', {'border': '1'})
            
            if not table:
                self.logger.warning("No manuscripts table found")
                return manuscripts
            
            # Process each row
            rows = table.find_all('tr')[1:]  # Skip header
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 5:
                    continue
                
                # Extract manuscript data
                ms_link = cells[0].find('a')
                if not ms_link:
                    continue
                
                manuscript = {
                    'id': ms_link.text.strip(),
                    'title': cells[1].text.strip(),
                    'corresponding_editor': cells[2].text.strip(),
                    'associate_editor': cells[3].text.strip(),
                    'submitted': cells[4].text.strip(),
                    'submission_date': self._parse_date(cells[4].text.strip()),
                    'referees': [],
                    'documents': {
                        'pdf': None,
                        'referee_reports': [],
                        'cover_letter': None
                    }
                }
                
                manuscripts.append(manuscript)
                self.logger.info(f"Found manuscript: {manuscript['id']}")
        
        else:
            # SIFIN lists manuscripts directly in dashboard
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find associate editor section
            assoc_ed_section = soup.find('tbody', {'role': 'assoc_ed'})
            if not assoc_ed_section:
                self.logger.warning("No associate editor section found")
                return manuscripts
            
            # Find all manuscript links
            ms_links = assoc_ed_section.find_all('a', {'class': 'ndt_task_link'})
            
            for link in ms_links:
                # Extract manuscript ID from link text
                link_text = link.text.strip()
                if not link_text.startswith('#'):
                    continue
                
                # Parse manuscript info from link text
                # Format: "# M174160 - Under Review / Chase Referees - Complex Discontinuities..."
                parts = link_text.split(' - ', 2)
                if len(parts) < 3:
                    continue
                
                ms_id = parts[0].replace('#', '').strip()
                status = parts[1].strip()
                title = parts[2].split('(')[0].strip()
                
                # Get the URL for detailed extraction
                href = link.get('href', '')
                
                manuscript = {
                    'id': ms_id,
                    'title': title,
                    'status': status,
                    'url': href,
                    'corresponding_editor': 'N/A',  # Will be extracted from detail page
                    'associate_editor': 'Possamaï',  # You are the AE
                    'submitted': 'N/A',  # Will be extracted from detail page
                    'submission_date': None,
                    'referees': [],
                    'documents': {
                        'pdf': None,
                        'referee_reports': [],
                        'cover_letter': None
                    }
                }
                
                manuscripts.append(manuscript)
                self.logger.info(f"Found manuscript: {manuscript['id']} - {title[:50]}...")
        
        return manuscripts
    
    def _extract_referee_details(self, manuscript: dict):
        """Extract detailed referee information with perfect status parsing"""
        try:
            if self.journal_code == 'SICON':
                # Navigate to manuscript details
                ms_link = self.driver.find_element(
                    By.XPATH, f"//a[contains(text(), '{manuscript['id']}')]"
                )
                self.driver.execute_script("arguments[0].click();", ms_link)
                time.sleep(2)
            else:
                # SIFIN - navigate directly to manuscript URL
                if manuscript.get('url'):
                    full_url = self.config['base_url'] + '/' + manuscript['url']
                    self.driver.get(full_url)
                    time.sleep(2)
                    
                    # Extract additional details from SIFIN detail page
                    self._extract_sifin_manuscript_details(manuscript)
            
            # Click on referee list (SICON) or parse existing page (SIFIN)
            if self.journal_code == 'SICON':
                ref_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@value='Referee List']"))
                )
                ref_button.click()
                time.sleep(2)
            
            # Parse referee table
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            if self.journal_code == 'SICON':
                ref_table = soup.find('table', {'border': '1'})
                
                if ref_table:
                    # Extract referee names and emails
                    referee_names = self._extract_referee_names(ref_table)
                    
                    # Use the same advanced email extraction as SIFIN
                    referee_emails_data = self._extract_referee_emails_sicon()
                    
                    # Extract statuses with perfect parsing
                    referee_statuses = self._extract_referee_statuses_perfect(ref_table)
                    
                    # Create email mapping based on referee names
                    email_map = {}
                    if referee_emails_data:
                        # Match emails with referee names in order
                        for i, name in enumerate(referee_names):
                            if i < len(referee_emails_data):
                                email_map[name] = referee_emails_data[i]
                            else:
                                email_map[name] = ""
                    
                    # Combine all data for SICON
                    for i, name in enumerate(referee_names):
                        # Try to find email for this referee
                        email = email_map.get(name, "")
                        
                        status_info = referee_statuses.get(name, {
                            'status': 'Unknown',
                            'invited_date': None,
                            'due_date': None
                        })
                        
                        referee = {
                            'name': name,
                            'email': email,
                            'status': status_info['status'],
                            'invited_date': status_info.get('invited_date'),
                            'due_date': status_info.get('due_date'),
                            'report_available': self._check_report_available(name, status_info['status'])
                        }
                        
                        manuscript['referees'].append(referee)
                        self.logger.info(
                            f"Referee {name}: {status_info['status']} "
                            f"(invited: {status_info.get('invited_date')}) "
                            f"email: {email if email else 'NOT FOUND'}"
                        )
            else:
                # SIFIN - extract referees from manuscript detail table
                referee_names = []
                referee_emails = []
                referee_statuses = {}
                
                self._extract_sifin_referees(soup, referee_names, referee_emails, referee_statuses)
                
                # Extract emails for SIFIN referees
                if referee_names:
                    referee_emails_data = self._extract_referee_emails_sifin()
                    
                    # Create email mapping based on referee names
                    # All referees now have clickable links, so we can match them directly
                    email_map = {}
                    
                    # The email extraction returns emails in the same order as the clickable links
                    # We need to match these with our referee names in order
                    import re
                    if referee_emails_data:
                        # Match emails with referee names in order
                        for i, name in enumerate(referee_names):
                            clean_name = re.sub(r' #\d+$', '', name)
                            if i < len(referee_emails_data):
                                email_map[clean_name] = referee_emails_data[i]
                            else:
                                email_map[clean_name] = ""
                
                # Combine all data
                for i, name in enumerate(referee_names):
                    # Try to find email for this referee
                    clean_name = re.sub(r' #\d+$', '', name)
                    email = email_map.get(clean_name, "")
                    
                    status_info = referee_statuses.get(name, {
                        'status': 'Unknown',
                        'invited_date': None,
                        'due_date': None
                    })
                    
                    referee = {
                        'name': name,
                        'email': email,
                        'status': status_info['status'],
                        'invited_date': status_info.get('invited_date'),
                        'due_date': status_info.get('due_date'),
                        'report_available': self._check_report_available(name, status_info['status'])
                    }
                    
                    manuscript['referees'].append(referee)
                    self.logger.info(
                        f"Referee {name}: {status_info['status']} "
                        f"(invited: {status_info.get('invited_date')}) "
                        f"email: {email if email else 'NOT FOUND'}"
                    )
            
            # Go back to manuscript list
            if self.journal_code == 'SICON':
                self.driver.back()
                time.sleep(1)
            # For SIFIN, we'll navigate back to dashboard after all manuscripts are processed
            
        except Exception as e:
            self.logger.error(f"Error extracting referee details for {manuscript['id']}: {e}")
    
    def _extract_referee_names(self, table) -> List[str]:
        """Extract referee names from table"""
        names = []
        rows = table.find_all('tr')
        
        for row in rows[1:]:  # Skip header
            cells = row.find_all('td')
            if len(cells) >= 2:
                name_cell = cells[0]
                if name_cell.find('a'):
                    name = name_cell.get_text(strip=True)
                    names.append(name)
        
        return names
    
    def _extract_referee_emails(self, table) -> List[str]:
        """Extract referee emails from table"""
        emails = []
        
        # Store current window
        main_window = self.driver.current_window_handle
        
        # Find all referee profile links based on journal
        if self.journal_code == 'SICON':
            profile_links = self.driver.find_elements(
                By.XPATH, "//a[contains(@href, 'au_show_info')]"
            )
        else:
            # SIFIN - find profile links in manuscript detail page
            profile_links = self.driver.find_elements(
                By.XPATH, "//table[@id='ms_details_expanded']//a[contains(@href, 'au_show_info')]"
            )
        
        for link in profile_links:
            try:
                # Open in new tab
                self.driver.execute_script("arguments[0].click();", link)
                time.sleep(1)
                
                # Switch to new window
                for window in self.driver.window_handles:
                    if window != main_window:
                        self.driver.switch_to.window(window)
                        break
                
                # Extract email
                email_element = self.driver.find_element(
                    By.XPATH, "//td[contains(text(), 'E-mail')]/following-sibling::td"
                )
                email = email_element.text.strip()
                emails.append(email)
                
                # Close tab and switch back
                self.driver.close()
                self.driver.switch_to.window(main_window)
                
            except Exception as e:
                self.logger.warning(f"Could not extract email: {e}")
                emails.append("")
        
        return emails
    
    def _extract_referee_statuses_perfect(self, table) -> Dict[str, dict]:
        """Extract referee statuses with perfect parsing"""
        statuses = {}
        
        # Find the two columns we need
        header_row = table.find('tr')
        headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        
        name_col_idx = None
        status_col_idx = None
        
        for idx, header in enumerate(headers):
            if 'Name' in header:
                name_col_idx = idx
            elif 'Ref Status' in header or 'Status' in header:
                status_col_idx = idx
        
        if name_col_idx is None or status_col_idx is None:
            return statuses
        
        # Process data rows
        rows = table.find_all('tr')[1:]  # Skip header
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) > max(name_col_idx, status_col_idx):
                # Extract names
                names = self._split_cell_content(cells[name_col_idx])
                
                # Extract statuses
                status_entries = self._split_status_cell_perfect(cells[status_col_idx])
                
                # Match names with statuses
                for i, name in enumerate(names):
                    if i < len(status_entries):
                        status_text = status_entries[i]
                        status_info = self._parse_status_text(status_text)
                        statuses[name] = status_info
        
        return statuses
    
    def _split_cell_content(self, cell) -> List[str]:
        """Split cell content by <br> tags"""
        entries = []
        if hasattr(cell, 'contents'):
            current_text = ""
            for element in cell.contents:
                if isinstance(element, NavigableString):
                    text = str(element).strip()
                    if text:
                        current_text += text
                elif element.name == 'br':
                    if current_text:
                        entries.append(current_text.strip())
                        current_text = ""
                elif element.name == 'a':
                    current_text += element.get_text(strip=True)
            
            if current_text:
                entries.append(current_text.strip())
        
        return entries
    
    def _split_status_cell_perfect(self, cell) -> List[str]:
        """Split status cell content with perfect parsing"""
        statuses = []
        if hasattr(cell, 'contents'):
            current_text = ""
            for element in cell.contents:
                if isinstance(element, NavigableString):
                    current_text += str(element).strip() + " "
                elif element.name == 'br':
                    if current_text.strip():
                        statuses.append(current_text.strip())
                        current_text = ""
                else:
                    current_text += element.get_text(strip=True) + " "
            
            if current_text.strip():
                statuses.append(current_text.strip())
        
        return statuses
    
    def _parse_status_text(self, status_text: str) -> dict:
        """Parse status text to extract status, dates, etc."""
        info = {
            'status': 'Unknown',
            'invited_date': None,
            'due_date': None
        }
        
        # Determine status
        if 'Accepted' in status_text:
            info['status'] = 'Accepted'
        elif 'Declined' in status_text:
            info['status'] = 'Declined'
        elif 'Report Submitted' in status_text:
            info['status'] = 'Report Submitted'
        elif 'Invited' in status_text:
            info['status'] = 'Invited'
        
        # Extract dates
        import re
        
        # Invited date
        invited_match = re.search(r'Invited[:\s]+(\d{4}-\d{2}-\d{2})', status_text)
        if invited_match:
            info['invited_date'] = invited_match.group(1)
        
        # Due date
        due_match = re.search(r'Due[:\s]+(\d{4}-\d{2}-\d{2})', status_text)
        if due_match:
            info['due_date'] = due_match.group(1)
        
        return info
    
    def _check_report_available(self, referee_name: str, status: str) -> bool:
        """Check if referee report is available"""
        return status in ['Report Submitted', 'Accepted']
    
    def _download_manuscript_documents(self, manuscript: dict):
        """Download all available documents for a manuscript"""
        try:
            if self.journal_code == 'SICON':
                # SICON: Navigate to manuscript view page
                ms_link = self.driver.find_element(
                    By.XPATH, f"//a[contains(text(), '{manuscript['id']}')]"
                )
                self.driver.execute_script("arguments[0].click();", ms_link)
                time.sleep(2)
                
                # Click View Manuscript
                view_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@value='View Manuscript']"))
                )
                view_button.click()
                time.sleep(2)
                
                # Download documents using new comprehensive method
                self._download_sicon_documents(manuscript)
                
                # Go back to manuscript list
                self.driver.back()
                self.driver.back()
                time.sleep(1)
                
            else:
                # SIFIN: Already on manuscript detail page, look for PDF links directly
                self._download_sifin_documents(manuscript)
            
        except Exception as e:
            self.logger.error(f"Error downloading documents for {manuscript['id']}: {e}")
    
    def _download_pdf(self, manuscript: dict):
        """Download manuscript PDF"""
        try:
            pdf_link = self.driver.find_element(
                By.XPATH, "//a[contains(@href, '.pdf')]"
            )
            pdf_url = pdf_link.get_attribute('href')
            
            # Save PDF path
            pdf_filename = f"{manuscript['id']}_manuscript.pdf"
            pdf_path = self.output_dir / 'pdfs' / pdf_filename
            pdf_path.parent.mkdir(exist_ok=True)
            
            # Download using driver
            self.driver.get(pdf_url)
            time.sleep(3)
            
            manuscript['documents']['pdf'] = str(pdf_path)
            self.logger.info(f"Downloaded PDF for {manuscript['id']}")
            
            # Navigate back
            self.driver.back()
            
        except Exception as e:
            self.logger.warning(f"Could not download PDF for {manuscript['id']}: {e}")
    
    def _download_referee_reports(self, manuscript: dict):
        """Download available referee reports"""
        try:
            # Look for referee report links
            report_links = self.driver.find_elements(
                By.XPATH, "//a[contains(text(), 'Referee Report')]"
            )
            
            for i, link in enumerate(report_links):
                report_url = link.get_attribute('href')
                referee_name = self._extract_referee_name_from_report(link)
                
                report_filename = f"{manuscript['id']}_report_{i+1}_{referee_name}.pdf"
                report_path = self.output_dir / 'reports' / report_filename
                report_path.parent.mkdir(exist_ok=True)
                
                # Download report
                self.driver.get(report_url)
                time.sleep(2)
                
                manuscript['documents']['referee_reports'].append({
                    'referee': referee_name,
                    'path': str(report_path),
                    'download_date': datetime.now().isoformat()
                })
                
                self.logger.info(f"Downloaded report from {referee_name} for {manuscript['id']}")
                
                # Navigate back
                self.driver.back()
                
        except Exception as e:
            self.logger.warning(f"Could not download reports for {manuscript['id']}: {e}")
    
    def _download_cover_letter(self, manuscript: dict):
        """Download cover letter if available"""
        try:
            cover_link = self.driver.find_element(
                By.XPATH, "//a[contains(text(), 'Cover Letter')]"
            )
            cover_url = cover_link.get_attribute('href')
            
            cover_filename = f"{manuscript['id']}_cover_letter.pdf"
            cover_path = self.output_dir / 'cover_letters' / cover_filename
            cover_path.parent.mkdir(exist_ok=True)
            
            # Download cover letter
            self.driver.get(cover_url)
            time.sleep(2)
            
            manuscript['documents']['cover_letter'] = str(cover_path)
            self.logger.info(f"Downloaded cover letter for {manuscript['id']}")
            
            # Navigate back
            self.driver.back()
            
        except Exception as e:
            self.logger.info(f"No cover letter available for {manuscript['id']}")
    
    def _extract_referee_name_from_report(self, link_element) -> str:
        """Extract referee name from report link context"""
        try:
            # Look for referee name in surrounding text
            parent = link_element.find_element(By.XPATH, "./..")
            text = parent.text
            # Extract name from context
            return "Unknown"
        except:
            return "Unknown"
    
    def search_referee_emails(self, referee_name: str, referee_email: str,
                             manuscript_id: str, submission_date: str,
                             title: str) -> dict:
        """Search for manuscript-specific referee emails"""
        if not self.gmail_service:
            return {'found': False, 'emails': [], 'email_count': 0}
        
        try:
            # Build precise search queries
            search_queries = [
                f'to:{referee_email} "{manuscript_id}"',
                f'from:{referee_email} "{manuscript_id}"',
                f'subject:"{manuscript_id}" "{referee_name}"',
                f'"{manuscript_id}" "{referee_name}" "{self.journal_name}"'
            ]
            
            all_emails = []
            email_types = {
                'invitation': 0,
                'acceptance': 0,
                'decline': 0,
                'report': 0,
                'other': 0
            }
            
            for query in search_queries:
                try:
                    results = self.gmail_service.users().messages().list(
                        userId='me',
                        q=query,
                        maxResults=50
                    ).execute()
                    
                    messages = results.get('messages', [])
                    
                    for msg in messages:
                        msg_data = self.gmail_service.users().messages().get(
                            userId='me',
                            id=msg['id']
                        ).execute()
                        
                        # Categorize email
                        headers = msg_data['payload'].get('headers', [])
                        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                        
                        if 'request to referee' in subject.lower():
                            email_types['invitation'] += 1
                        elif 'accepted' in subject.lower():
                            email_types['acceptance'] += 1
                        elif 'declined' in subject.lower() or 'sv:' in subject.lower():
                            email_types['decline'] += 1
                        elif 'report' in subject.lower() or 'review' in subject.lower():
                            email_types['report'] += 1
                        else:
                            email_types['other'] += 1
                        
                        all_emails.append({
                            'id': msg['id'],
                            'subject': subject,
                            'date': next((h['value'] for h in headers if h['name'] == 'Date'), '')
                        })
                    
                except Exception as e:
                    self.logger.debug(f"Email search error for query '{query}': {e}")
            
            # Deduplicate emails by ID
            unique_emails = {email['id']: email for email in all_emails}.values()
            
            return {
                'found': len(unique_emails) > 0,
                'emails': list(unique_emails),
                'email_count': len(unique_emails),
                'email_types': email_types,
                'invitation_date': self._extract_invitation_date(unique_emails)
            }
            
        except Exception as e:
            self.logger.error(f"Email search failed: {e}")
            return {'found': False, 'emails': [], 'email_count': 0}
    
    def _extract_invitation_date(self, emails: list) -> Optional[str]:
        """Extract invitation date from emails"""
        for email in emails:
            if 'request to referee' in email.get('subject', '').lower():
                return email.get('date')
        return None
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to ISO format"""
        try:
            # Handle various date formats
            from dateutil import parser
            parsed = parser.parse(date_str)
            return parsed.strftime('%Y-%m-%d')
        except:
            return date_str
    
    def _extract_sifin_manuscript_details(self, manuscript: dict):
        """Extract additional details from SIFIN manuscript detail page"""
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find the manuscript details table
            details_table = soup.find('table', {'id': 'ms_details_expanded'})
            if details_table:
                for row in details_table.find_all('tr'):
                    th = row.find('th')
                    td = row.find('td')
                    if th and td:
                        label = th.get_text(strip=True)
                        value = td.get_text(strip=True)
                        
                        if label == "Submission Date":
                            manuscript['submitted'] = value
                            manuscript['submission_date'] = self._parse_date(value)
                        elif label == "Title":
                            manuscript['title'] = value  # Update with full title
                        elif label == "Corresponding Editor":
                            manuscript['corresponding_editor'] = value
            
            self.logger.info(f"Extracted SIFIN details for {manuscript['id']}")
            
        except Exception as e:
            self.logger.warning(f"Could not extract SIFIN manuscript details: {e}")
    
    def _extract_sifin_referees(self, soup, referee_names: List[str], referee_emails: List[str], referee_statuses: Dict[str, dict]):
        """Extract referees from SIFIN manuscript detail page"""
        try:
            # Find the manuscript details table
            details_table = soup.find('table', {'id': 'ms_details_expanded'})
            if not details_table:
                return
            
            for row in details_table.find_all('tr'):
                th = row.find('th')
                td = row.find('td')
                if not th or not td:
                    continue
                
                label = th.get_text(strip=True)
                
                # Look for referee rows
                if label == "Referees":
                    # Extract accepted referees
                    for ref_link in td.find_all('a'):
                        name = ref_link.get_text(strip=True)
                        href = ref_link.get('href', '')
                        
                        referee_names.append(name)
                        # Don't add empty email - will be extracted later
                        
                        # Look for due date in surrounding text
                        due_date = None
                        next_sibling = ref_link.next_sibling
                        if next_sibling and 'Due:' in str(next_sibling):
                            import re
                            due_match = re.search(r'Due:\s*([\d\-]+)', str(next_sibling))
                            if due_match:
                                due_date = due_match.group(1)
                        
                        referee_statuses[name] = {
                            'status': 'Accepted',
                            'invited_date': None,
                            'due_date': due_date
                        }
                
                elif "Potential Referees" in label:
                    # Extract ALL potential referees (contacted and declined)
                    for ref_link in td.find_all('a'):
                        name = ref_link.get_text(strip=True)
                        
                        # Check status in surrounding text
                        next_text = ''
                        node = ref_link.next_sibling
                        while node and len(next_text) < 200:
                            if hasattr(node, 'name') and node.name == 'a':
                                break
                            next_text += str(node)
                            node = node.next_sibling if hasattr(node, 'next_sibling') else None
                        
                        # Determine status from surrounding text
                        if 'declined' in next_text.lower():
                            status = 'Declined'
                        elif 'contacted' in next_text.lower():
                            status = 'Contacted'
                        else:
                            status = 'Contacted'  # Default for potential referees
                        
                        referee_names.append(name)
                        # Don't add empty email - will be extracted later
                        referee_statuses[name] = {
                            'status': status,
                            'invited_date': None,
                            'due_date': None
                        }
            
            self.logger.info(f"Extracted {len(referee_names)} referees from SIFIN page")
            
        except Exception as e:
            self.logger.warning(f"Error extracting SIFIN referees: {e}")
    
    def _extract_referee_emails_sifin(self) -> List[str]:
        """Extract referee emails from SIFIN - ALL referees have clickable profile links"""
        emails = []
        
        # Store current window
        main_window = self.driver.current_window_handle
        
        try:
            # Find ALL referee name links in the manuscript detail page
            # Both "Referees" and "Potential Referees" sections have clickable links
            referee_links = []
            
            # Get both "Referees" and "Potential Referees" sections
            # Note: "Referees" header is actually a clickable link, so we need to check the link text
            referee_xpath_patterns = [
                "//table[@id='ms_details_expanded']//th[contains(.,'Referees')]/../td//a[contains(@href, 'biblio_dump')]",
                "//table[@id='ms_details_expanded']//th[contains(text(), 'Potential Referees')]/../td//a[contains(@href, 'biblio_dump')]"
            ]
            
            all_referee_links = []
            for pattern in referee_xpath_patterns:
                try:
                    links = self.driver.find_elements(By.XPATH, pattern)
                    all_referee_links.extend(links)
                except:
                    continue
            
            # Filter to only include actual referee names (not other bio links)
            for link in all_referee_links:
                link_text = link.text.strip()
                # Skip non-referee links and duplicates
                if (link_text and 
                    '#' in link_text and  # Referee names have #1, #2, etc.
                    not any(skip in link_text.lower() for skip in ['current', 'stage', 'due', 'invited']) and
                    link not in referee_links):
                    referee_links.append(link)
            
            self.logger.info(f"Found {len(referee_links)} referee profile links (ALL referees)")
            
            # Extract emails from clickable links
            clickable_emails = []
            for i, link in enumerate(referee_links):
                try:
                    # Get the referee name
                    referee_name = link.text.strip()
                    self.logger.info(f"Extracting email for referee {i+1}: {referee_name}")
                    
                    # Click the referee name to open profile window
                    self.driver.execute_script("arguments[0].click();", link)
                    time.sleep(2)
                    
                    # Handle potential popup or new window
                    if len(self.driver.window_handles) > 1:
                        # New window opened
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                    
                    # Wait for page to load
                    time.sleep(2)
                    
                    # Extract email from profile page - try multiple selectors
                    email = ""
                    email_selectors = [
                        "//td[contains(text(), 'E-mail')]/following-sibling::td",
                        "//td[contains(text(), 'Email')]/following-sibling::td",
                        "//td[text()='E-mail']/following-sibling::td",
                        "//td[text()='Email']/following-sibling::td",
                        "//th[text()='E-mail']/following-sibling::td",
                        "//th[text()='Email']/following-sibling::td",
                        "//tr[contains(.,'E-mail')]//td[2]",
                        "//tr[contains(.,'Email')]//td[2]",
                        "//tr[contains(.,'e-mail')]//td[2]",
                        "//tr[contains(.,'email')]//td[2]",
                        "//td[contains(text(), '@')]",
                        "//span[contains(text(), '@')]"
                    ]
                    
                    for selector in email_selectors:
                        try:
                            email_element = self.driver.find_element(By.XPATH, selector)
                            email_text = email_element.text.strip()
                            if '@' in email_text:
                                # Extract just the email address using regex
                                import re
                                email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', email_text)
                                if email_match:
                                    email = email_match.group(0)
                                    self.logger.info(f"Extracted email for {referee_name}: {email}")
                                    break
                        except:
                            continue
                    
                    if not email:
                        # Try regex search in page source
                        import re
                        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                        emails_in_page = re.findall(email_pattern, self.driver.page_source)
                        if emails_in_page:
                            # Filter out common non-personal emails
                            filtered_emails = [e for e in emails_in_page if not any(skip in e.lower() for skip in ['noreply', 'no-reply', 'admin', 'system', 'test'])]
                            if filtered_emails:
                                email = filtered_emails[0]
                                self.logger.info(f"Found email in page source for {referee_name}: {email}")
                    
                    if not email:
                        self.logger.warning(f"Could not extract email for {referee_name}")
                    
                    clickable_emails.append((referee_name, email))
                    
                    # Close popup/window and switch back
                    if len(self.driver.window_handles) > 1:
                        self.driver.close()
                        self.driver.switch_to.window(main_window)
                    else:
                        # If it was a popup, try to dismiss it
                        try:
                            self.driver.execute_script("window.history.back();")
                            time.sleep(1)
                        except:
                            pass
                    
                except Exception as e:
                    self.logger.warning(f"Error extracting email for referee {i+1}: {e}")
                    clickable_emails.append((referee_name, ""))
                    # Make sure we're back on main window
                    try:
                        if len(self.driver.window_handles) > 1:
                            self.driver.switch_to.window(main_window)
                    except:
                        pass
            
            # Create a mapping of referee names to emails
            email_map = {}
            for ref_name, email in clickable_emails:
                # Remove the numbering from the name for matching
                clean_name = re.sub(r' #\d+$', '', ref_name)
                email_map[clean_name] = email
            
            # Log the available emails
            self.logger.info(f"Extracted emails mapping: {email_map}")
            
            # Return the clickable emails for now - the calling code will handle the mapping
            return [email for _, email in clickable_emails]
            
        except Exception as e:
            self.logger.error(f"Error extracting SIFIN referee emails: {e}")
            return []
    
    def _download_sifin_documents(self, manuscript: dict):
        """Download documents for SIFIN manuscripts"""
        try:
            # Parse the page to find manuscript items section
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find the manuscript details table
            details_table = soup.find('table', {'id': 'ms_details_expanded'})
            if not details_table:
                self.logger.warning(f"No manuscript details table found for {manuscript['id']}")
                return
            
            manuscript_pdf_found = False
            cover_letter_found = False
            
            # Look for Manuscript Items section (not in the table, but in the page)
            # First check if there's a Manuscript Items section in the page
            manuscript_items_section = soup.find('font', string=lambda text: text and 'manuscript items' in text.lower())
            if manuscript_items_section:
                self.logger.info(f"Found Manuscript Items section for {manuscript['id']}")
                
                # Find the ordered list that follows the Manuscript Items header
                ol_section = manuscript_items_section.find_next('ol')
                if ol_section:
                    # Extract all PDF links from this section
                    pdf_links = ol_section.find_all('a', href=lambda x: x and '.pdf' in x.lower())
                    
                    for link in pdf_links:
                        try:
                            link_text = link.get_text(strip=True)
                            href = link.get('href')
                            
                            # Make URL absolute
                            if href.startswith('/') or href.startswith('sifin_files/'):
                                href = f"https://sifin.siam.org/{href.lstrip('/')}"
                            elif not href.startswith('http'):
                                href = f"https://sifin.siam.org/{href}"
                            
                            # Check if this is a cover letter
                            if 'cover' in link_text.lower() and 'letter' in link_text.lower():
                                cover_letter_filename = f"{manuscript['id']}_cover_letter.pdf"
                                cover_letter_path = self.output_dir / 'cover_letters' / cover_letter_filename
                                cover_letter_path.parent.mkdir(exist_ok=True)
                                
                                manuscript['documents']['cover_letter'] = str(cover_letter_path)
                                manuscript['cover_letter_url'] = href
                                
                                self.logger.info(f"Found cover letter for {manuscript['id']}: {href}")
                                cover_letter_found = True
                                
                            # Check if this is the main manuscript/article file
                            elif (('article' in link_text.lower() or 'manuscript' in link_text.lower()) and 
                                  not manuscript_pdf_found):
                                pdf_filename = f"{manuscript['id']}_manuscript.pdf"
                                pdf_path = self.output_dir / 'pdfs' / pdf_filename
                                pdf_path.parent.mkdir(exist_ok=True)
                                
                                manuscript['documents']['pdf'] = str(pdf_path)
                                manuscript['pdf_url'] = href
                                
                                self.logger.info(f"Found manuscript PDF for {manuscript['id']}: {href}")
                                manuscript_pdf_found = True
                                
                        except Exception as e:
                            self.logger.warning(f"Error processing manuscript item link: {e}")
                            continue
            
            # If no PDF found in Manuscript Items, look for any PDF in the page
            if not manuscript_pdf_found:
                pdf_links = self.driver.find_elements(
                    By.XPATH, "//a[contains(@href, '.pdf') or contains(text(), 'PDF') or contains(text(), 'pdf')]"
                )
                
                if pdf_links:
                    try:
                        first_pdf = pdf_links[0]
                        href = first_pdf.get_attribute('href')
                        
                        # Check if this PDF is actually a cover letter based on the URL
                        if 'cover_letter' in href.lower():
                            # This is a cover letter, not a manuscript
                            cover_letter_filename = f"{manuscript['id']}_cover_letter.pdf"
                            cover_letter_path = self.output_dir / 'cover_letters' / cover_letter_filename
                            cover_letter_path.parent.mkdir(exist_ok=True)
                            
                            manuscript['documents']['cover_letter'] = str(cover_letter_path)
                            manuscript['cover_letter_url'] = href
                            
                            self.logger.info(f"Found cover letter (from URL pattern) for {manuscript['id']}: {href}")
                            cover_letter_found = True
                            
                            # Look for additional PDFs that might be the actual manuscript
                            for pdf_link in pdf_links[1:]:
                                additional_href = pdf_link.get_attribute('href')
                                if 'art_file' in additional_href.lower() or 'article' in additional_href.lower():
                                    pdf_filename = f"{manuscript['id']}_manuscript.pdf"
                                    pdf_path = self.output_dir / 'pdfs' / pdf_filename
                                    pdf_path.parent.mkdir(exist_ok=True)
                                    
                                    manuscript['documents']['pdf'] = str(pdf_path)
                                    manuscript['pdf_url'] = additional_href
                                    
                                    self.logger.info(f"Found manuscript PDF for {manuscript['id']}: {additional_href}")
                                    manuscript_pdf_found = True
                                    break
                        else:
                            # Regular PDF
                            pdf_filename = f"{manuscript['id']}_manuscript.pdf"
                            pdf_path = self.output_dir / 'pdfs' / pdf_filename
                            pdf_path.parent.mkdir(exist_ok=True)
                            
                            manuscript['documents']['pdf'] = str(pdf_path)
                            manuscript['pdf_url'] = href
                            
                            self.logger.info(f"Found PDF (first available) for {manuscript['id']}: {href}")
                            manuscript_pdf_found = True
                        
                    except Exception as e:
                        self.logger.warning(f"Error processing first PDF: {e}")
            
            # Look for referee reports in workflow tasks (temporarily disabled due to timeout issues)
            # TODO: Re-enable once we fix the window handling issues
            # reports_found = self._extract_referee_reports_sifin(manuscript)
            # 
            # if reports_found:
            #     self.logger.info(f"✅ Found {reports_found} referee reports for manuscript {manuscript['id']}")
            # else:
            #     self.logger.info(f"ℹ️  No referee reports found for manuscript {manuscript['id']}")
            
            self.logger.info(f"ℹ️  Referee report extraction temporarily disabled for {manuscript['id']}")
            
            # Log results
            if manuscript_pdf_found:
                self.logger.info(f"✅ Found PDF for manuscript {manuscript['id']}")
            else:
                self.logger.warning(f"❌ No PDF found for manuscript {manuscript['id']}")
                
            if cover_letter_found:
                self.logger.info(f"✅ Found cover letter for manuscript {manuscript['id']}")
            else:
                self.logger.info(f"ℹ️  No cover letter found for manuscript {manuscript['id']}")
                
        except Exception as e:
            self.logger.error(f"Error downloading SIFIN documents for {manuscript['id']}: {e}")
    
    def _extract_referee_reports_sifin(self, manuscript: dict) -> int:
        """Extract referee reports from SIFIN Associate Editor Recommendation workflow"""
        reports_found = 0
        main_window = self.driver.current_window_handle
        
        try:
            # Look for Associate Editor Recommendation link
            workflow_links = self.driver.find_elements(
                By.XPATH, "//a[contains(text(), 'Associate Editor Recommendation')]"
            )
            
            if workflow_links:
                self.logger.info(f"Found Associate Editor Recommendation link for {manuscript['id']}")
                
                # Click the Associate Editor Recommendation link
                workflow_link = workflow_links[0]
                self.driver.execute_script("arguments[0].click();", workflow_link)
                
                # Wait for new window to open with timeout
                wait_time = 0
                while len(self.driver.window_handles) == 1 and wait_time < 10:
                    time.sleep(0.5)
                    wait_time += 0.5
                
                # Handle new window/tab
                if len(self.driver.window_handles) > 1:
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    time.sleep(2)
                    
                    # Look for PDF links in the reports window with timeout
                    try:
                        from selenium.webdriver.support.ui import WebDriverWait
                        from selenium.webdriver.support import expected_conditions as EC
                        
                        # Wait for page to load
                        wait = WebDriverWait(self.driver, 10)
                        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                        
                        # Look for PDF links in the reports window
                        pdf_links = self.driver.find_elements(
                            By.XPATH, "//a[contains(@href, '.pdf')]"
                        )
                        
                        for i, pdf_link in enumerate(pdf_links):
                            try:
                                href = pdf_link.get_attribute('href')
                                link_text = pdf_link.text.strip()
                                
                                # Check if this looks like a referee report
                                if any(keyword in link_text.lower() for keyword in ['report', 'review', 'referee']):
                                    report_filename = f"{manuscript['id']}_referee_report_{i+1}.pdf"
                                    report_path = self.output_dir / 'referee_reports' / report_filename
                                    report_path.parent.mkdir(exist_ok=True)
                                    
                                    manuscript['documents']['referee_reports'].append({
                                        'path': str(report_path),
                                        'url': href,
                                        'download_date': datetime.now().isoformat(),
                                        'type': 'referee_report',
                                        'source': 'Associate Editor Recommendation'
                                    })
                                    
                                    self.logger.info(f"Found referee report for {manuscript['id']}: {link_text} -> {href}")
                                    reports_found += 1
                                    
                            except Exception as e:
                                self.logger.warning(f"Error processing report PDF link: {e}")
                                continue
                    
                    except Exception as e:
                        self.logger.warning(f"Timeout or error loading reports window: {e}")
                    
                    # Close the report window and switch back
                    try:
                        self.driver.close()
                        self.driver.switch_to.window(main_window)
                        time.sleep(1)
                    except:
                        pass
                else:
                    self.logger.warning(f"No new window opened for Associate Editor Recommendation")
            
            # Also try the "Referees" link that opens all reviews
            if reports_found == 0:  # Only if we didn't find reports from first method
                referees_links = self.driver.find_elements(
                    By.XPATH, "//a[contains(@href, 'display_all_reviews')]"
                )
                
                if referees_links:
                    self.logger.info(f"Found display_all_reviews link for {manuscript['id']}")
                    
                    # Click the display_all_reviews link
                    referees_link = referees_links[0]
                    self.driver.execute_script("arguments[0].click();", referees_link)
                    
                    # Wait for new window to open with timeout
                    wait_time = 0
                    while len(self.driver.window_handles) == 1 and wait_time < 10:
                        time.sleep(0.5)
                        wait_time += 0.5
                    
                    # Handle new window/tab
                    if len(self.driver.window_handles) > 1:
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                        time.sleep(2)
                        
                        # Look for PDF links in the reviews window
                        try:
                            from selenium.webdriver.support.ui import WebDriverWait
                            from selenium.webdriver.support import expected_conditions as EC
                            
                            # Wait for page to load
                            wait = WebDriverWait(self.driver, 10)
                            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                            
                            pdf_links = self.driver.find_elements(
                                By.XPATH, "//a[contains(@href, '.pdf')]"
                            )
                            
                            for i, pdf_link in enumerate(pdf_links):
                                try:
                                    href = pdf_link.get_attribute('href')
                                    link_text = pdf_link.text.strip()
                                    
                                    # Check if this looks like a referee report
                                    if any(keyword in link_text.lower() for keyword in ['report', 'review', 'referee']):
                                        report_filename = f"{manuscript['id']}_all_reviews_report_{i+1}.pdf"
                                        report_path = self.output_dir / 'referee_reports' / report_filename
                                        report_path.parent.mkdir(exist_ok=True)
                                        
                                        manuscript['documents']['referee_reports'].append({
                                            'path': str(report_path),
                                            'url': href,
                                            'download_date': datetime.now().isoformat(),
                                            'type': 'referee_report',
                                            'source': 'All Reviews'
                                        })
                                        
                                        self.logger.info(f"Found referee report for {manuscript['id']}: {link_text} -> {href}")
                                        reports_found += 1
                                        
                                except Exception as e:
                                    self.logger.warning(f"Error processing report PDF link: {e}")
                                    continue
                        
                        except Exception as e:
                            self.logger.warning(f"Timeout or error loading reviews window: {e}")
                        
                        # Close the reviews window and switch back
                        try:
                            self.driver.close()
                            self.driver.switch_to.window(main_window)
                            time.sleep(1)
                        except:
                            pass
                    else:
                        self.logger.warning(f"No new window opened for display_all_reviews")
            
            return reports_found
            
        except Exception as e:
            self.logger.error(f"Error extracting referee reports for {manuscript['id']}: {e}")
            # Make sure we're back on the main window
            try:
                if len(self.driver.window_handles) > 1:
                    # Close any extra windows
                    for handle in self.driver.window_handles[1:]:
                        self.driver.switch_to.window(handle)
                        self.driver.close()
                    self.driver.switch_to.window(main_window)
            except:
                pass
            return 0
    
    def _extract_referee_emails_sicon(self) -> List[str]:
        """Extract referee emails from SICON - using same enhanced approach as SIFIN"""
        emails = []
        
        # Store current window
        main_window = self.driver.current_window_handle
        
        try:
            # Use the same XPath patterns that work for SIFIN but adapted for SICON
            referee_xpath_patterns = [
                "//table[@id='ms_details_expanded']//th[contains(.,'Referees')]/../td//a[contains(@href, 'au_show_info')]",
                "//table[@id='ms_details_expanded']//th[contains(text(), 'Potential Referees')]/../td//a[contains(@href, 'au_show_info')]"
            ]
            
            referee_links = []
            for pattern in referee_xpath_patterns:
                try:
                    links = self.driver.find_elements(By.XPATH, pattern)
                    referee_links.extend(links)
                    self.logger.info(f"Found {len(links)} referee links with pattern: {pattern}")
                except Exception as e:
                    self.logger.debug(f"XPath pattern failed: {pattern} - {e}")
                    continue
            
            # Remove duplicates
            unique_links = []
            seen_hrefs = set()
            for link in referee_links:
                href = link.get_attribute('href')
                if href not in seen_hrefs:
                    unique_links.append(link)
                    seen_hrefs.add(href)
            
            self.logger.info(f"Found {len(unique_links)} unique referee profile links (ALL referees)")
            
            # Extract emails from clickable links
            for i, link in enumerate(unique_links):
                try:
                    # Get the referee name
                    referee_name = link.text.strip()
                    self.logger.info(f"Extracting email for referee {i+1}: {referee_name}")
                    
                    # Click the referee name to open profile window
                    self.driver.execute_script("arguments[0].click();", link)
                    time.sleep(2)
                    
                    # Handle potential popup or new window
                    if len(self.driver.window_handles) > 1:
                        # New window opened
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                    
                    # Wait for page to load
                    time.sleep(2)
                    
                    # Extract email from profile page - try multiple selectors
                    email = ""
                    email_selectors = [
                        "//td[contains(text(), 'E-mail')]/following-sibling::td",
                        "//td[contains(text(), 'Email')]/following-sibling::td",
                        "//td[text()='E-mail']/following-sibling::td",
                        "//td[text()='Email']/following-sibling::td",
                        "//th[text()='E-mail']/following-sibling::td",
                        "//th[text()='Email']/following-sibling::td",
                        "//tr[contains(.,'E-mail')]//td[2]",
                        "//tr[contains(.,'Email')]//td[2]",
                        "//tr[contains(.,'e-mail')]//td[2]",
                        "//tr[contains(.,'email')]//td[2]",
                        "//td[contains(text(), '@')]",
                        "//span[contains(text(), '@')]"
                    ]
                    
                    for selector in email_selectors:
                        try:
                            email_element = self.driver.find_element(By.XPATH, selector)
                            email_text = email_element.text.strip()
                            if '@' in email_text:
                                # Extract just the email address using regex
                                import re
                                email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', email_text)
                                if email_match:
                                    email = email_match.group(0)
                                    self.logger.info(f"Extracted email for {referee_name}: {email}")
                                    break
                        except:
                            continue
                    
                    if not email:
                        # Try regex search in page source
                        import re
                        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                        emails_in_page = re.findall(email_pattern, self.driver.page_source)
                        if emails_in_page:
                            # Filter out common non-personal emails
                            filtered_emails = [e for e in emails_in_page if not any(skip in e.lower() for skip in ['noreply', 'no-reply', 'admin', 'system', 'test'])]
                            if filtered_emails:
                                email = filtered_emails[0]
                                self.logger.info(f"Found email in page source for {referee_name}: {email}")
                    
                    if not email:
                        self.logger.warning(f"Could not extract email for {referee_name}")
                    
                    emails.append(email)
                    
                    # Close popup/window and switch back
                    if len(self.driver.window_handles) > 1:
                        self.driver.close()
                        self.driver.switch_to.window(main_window)
                    else:
                        # If it was a popup, try to dismiss it
                        try:
                            self.driver.execute_script("window.history.back();")
                            time.sleep(1)
                        except:
                            pass
                    
                except Exception as e:
                    self.logger.warning(f"Error extracting email for referee {i+1}: {e}")
                    emails.append("")
                    # Make sure we're back on main window
                    try:
                        if len(self.driver.window_handles) > 1:
                            self.driver.switch_to.window(main_window)
                    except:
                        pass
            
            return emails
            
        except Exception as e:
            self.logger.error(f"Error extracting SICON referee emails: {e}")
            return []
    
    def _download_sicon_documents(self, manuscript: dict):
        """Download documents for SICON manuscripts"""
        try:
            # Parse the page to find manuscript items section
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find the manuscript details table
            details_table = soup.find('table', {'id': 'ms_details_expanded'})
            if not details_table:
                self.logger.warning(f"No manuscript details table found for {manuscript['id']}")
                return
            
            manuscript_pdf_found = False
            cover_letter_found = False
            
            # Look for Manuscript Items section (similar to SIFIN)
            manuscript_items_section = soup.find('font', string=lambda text: text and 'manuscript items' in text.lower())
            if manuscript_items_section:
                self.logger.info(f"Found Manuscript Items section for {manuscript['id']}")
                
                # Find the ordered list that follows the Manuscript Items header
                ol_section = manuscript_items_section.find_next('ol')
                if ol_section:
                    # Extract all PDF links from this section
                    pdf_links = ol_section.find_all('a', href=lambda x: x and '.pdf' in x.lower())
                    
                    for link in pdf_links:
                        try:
                            link_text = link.get_text(strip=True)
                            href = link.get('href')
                            
                            # Make URL absolute (SICON uses sicon instead of sifin)
                            if href.startswith('/') or href.startswith('sicon_files/'):
                                href = f"https://sicon.siam.org/{href.lstrip('/')}"
                            elif not href.startswith('http'):
                                href = f"https://sicon.siam.org/{href}"
                            
                            # Check if this is a cover letter
                            if 'cover' in link_text.lower() and 'letter' in link_text.lower():
                                cover_letter_filename = f"{manuscript['id']}_cover_letter.pdf"
                                cover_letter_path = self.output_dir / 'cover_letters' / cover_letter_filename
                                cover_letter_path.parent.mkdir(exist_ok=True)
                                
                                manuscript['documents']['cover_letter'] = str(cover_letter_path)
                                manuscript['cover_letter_url'] = href
                                
                                self.logger.info(f"Found cover letter for {manuscript['id']}: {href}")
                                cover_letter_found = True
                                
                            # Check if this is the main manuscript/article file
                            elif (('article' in link_text.lower() or 'manuscript' in link_text.lower()) and 
                                  not manuscript_pdf_found):
                                pdf_filename = f"{manuscript['id']}_manuscript.pdf"
                                pdf_path = self.output_dir / 'pdfs' / pdf_filename
                                pdf_path.parent.mkdir(exist_ok=True)
                                
                                manuscript['documents']['pdf'] = str(pdf_path)
                                manuscript['pdf_url'] = href
                                
                                self.logger.info(f"Found manuscript PDF for {manuscript['id']}: {href}")
                                manuscript_pdf_found = True
                                
                        except Exception as e:
                            self.logger.warning(f"Error processing PDF link: {e}")
                            continue
                
                # Set found flags
                manuscript['pdf_found'] = manuscript_pdf_found
                manuscript['cover_letter_found'] = cover_letter_found
                
            # If no Manuscript Items section found, try to find PDFs elsewhere
            if not manuscript_pdf_found and not cover_letter_found:
                # Look for any PDF links in the page
                pdf_links = self.driver.find_elements(
                    By.XPATH, "//a[contains(@href, '.pdf')]"
                )
                
                for pdf_link in pdf_links:
                    try:
                        href = pdf_link.get_attribute('href')
                        link_text = pdf_link.text.strip()
                        
                        # Check if this is a cover letter based on URL pattern
                        if 'cover_letter' in href.lower() or 'auth_cover_letter' in href.lower():
                            cover_letter_filename = f"{manuscript['id']}_cover_letter.pdf"
                            cover_letter_path = self.output_dir / 'cover_letters' / cover_letter_filename
                            cover_letter_path.parent.mkdir(exist_ok=True)
                            
                            manuscript['documents']['cover_letter'] = str(cover_letter_path)
                            manuscript['cover_letter_url'] = href
                            
                            self.logger.info(f"Found cover letter for {manuscript['id']}: {href}")
                            cover_letter_found = True
                            
                        # Check if this is the main manuscript file
                        elif ('art_file' in href.lower() or 'manuscript' in link_text.lower()) and not manuscript_pdf_found:
                            pdf_filename = f"{manuscript['id']}_manuscript.pdf"
                            pdf_path = self.output_dir / 'pdfs' / pdf_filename
                            pdf_path.parent.mkdir(exist_ok=True)
                            
                            manuscript['documents']['pdf'] = str(pdf_path)
                            manuscript['pdf_url'] = href
                            
                            self.logger.info(f"Found manuscript PDF for {manuscript['id']}: {href}")
                            manuscript_pdf_found = True
                            
                    except Exception as e:
                        self.logger.warning(f"Error processing PDF link: {e}")
                        continue
                
                # Set found flags
                manuscript['pdf_found'] = manuscript_pdf_found
                manuscript['cover_letter_found'] = cover_letter_found
            
        except Exception as e:
            self.logger.error(f"Error downloading SICON documents for {manuscript['id']}: {e}")
    
    def _extract_referee_reports_sicon(self, manuscript: dict) -> int:
        """Extract referee reports from SICON Associate Editor Recommendation workflow"""
        reports_found = 0
        main_window = self.driver.current_window_handle
        
        try:
            # Look for Associate Editor Recommendation link
            workflow_links = self.driver.find_elements(
                By.XPATH, "//a[contains(text(), 'Associate Editor Recommendation')]"
            )
            
            if workflow_links:
                self.logger.info(f"Found Associate Editor Recommendation link for {manuscript['id']}")
                
                # Click the Associate Editor Recommendation link
                workflow_link = workflow_links[0]
                self.driver.execute_script("arguments[0].click();", workflow_link)
                
                # Wait for new window to open with timeout
                wait_time = 0
                while len(self.driver.window_handles) == 1 and wait_time < 10:
                    time.sleep(0.5)
                    wait_time += 0.5
                
                # Handle new window/tab
                if len(self.driver.window_handles) > 1:
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    time.sleep(2)
                    
                    # Look for PDF links in the reports window with timeout
                    try:
                        from selenium.webdriver.support.ui import WebDriverWait
                        from selenium.webdriver.support import expected_conditions as EC
                        
                        # Wait for page to load
                        wait = WebDriverWait(self.driver, 10)
                        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                        
                        # Look for PDF links in the reports window
                        pdf_links = self.driver.find_elements(
                            By.XPATH, "//a[contains(@href, '.pdf')]"
                        )
                        
                        for i, pdf_link in enumerate(pdf_links):
                            try:
                                href = pdf_link.get_attribute('href')
                                link_text = pdf_link.text.strip()
                                
                                # Make URL absolute (SICON uses sicon instead of sifin)
                                if href.startswith('/'):
                                    href = f"https://sicon.siam.org{href}"
                                elif not href.startswith('http'):
                                    href = f"https://sicon.siam.org/{href}"
                                
                                # Store referee report info
                                report_info = {
                                    'url': href,
                                    'title': link_text,
                                    'source': 'Associate Editor Recommendation'
                                }
                                
                                manuscript['documents']['referee_reports'].append(report_info)
                                
                                self.logger.info(f"Found referee report for {manuscript['id']}: {link_text}")
                                reports_found += 1
                                
                            except Exception as e:
                                self.logger.warning(f"Error processing referee report link: {e}")
                                continue
                        
                        # Close the reports window
                        self.driver.close()
                        self.driver.switch_to.window(main_window)
                        
                    except Exception as e:
                        self.logger.warning(f"Error extracting referee reports: {e}")
                        # Make sure we're back on main window
                        try:
                            if len(self.driver.window_handles) > 1:
                                self.driver.close()
                                self.driver.switch_to.window(main_window)
                        except:
                            pass
                else:
                    self.logger.warning(f"No new window opened for referee reports")
            else:
                self.logger.info(f"No Associate Editor Recommendation link found for {manuscript['id']}")
                
        except Exception as e:
            self.logger.error(f"Error extracting SICON referee reports: {e}")
            # Make sure we're back on main window
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(main_window)
            except:
                pass
        
        return reports_found