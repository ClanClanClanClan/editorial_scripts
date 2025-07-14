#!/usr/bin/env python3
"""
Base Journal Class - Generic implementation for all ScholarOne journals
"""

import time
import logging
from typing import Dict, Optional, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
from pathlib import Path

# Load journal configuration
config_path = Path(__file__).parent.parent / "config" / "journals_config.json"
with open(config_path) as f:
    JOURNALS_CONFIG = json.load(f)

logger = logging.getLogger(__name__)


class BaseJournal:
    """Base class for all journal implementations"""
    
    def __init__(self, journal_code: str, driver, debug: bool = False):
        self.journal_code = journal_code
        self.driver = driver
        self.debug = debug
        
        # Load journal-specific configuration
        if journal_code not in JOURNALS_CONFIG['journals']:
            raise ValueError(f"Unknown journal code: {journal_code}")
            
        self.config = JOURNALS_CONFIG['journals'][journal_code]
        self.name = self.config['name']
        self.url = self.config['url']
        self.login_url = self.config['login_url']
        self.ae_category = self.config['ae_category']
        self.final_category = self.config['final_category']
        self.email_prefix = self.config['email_prefix']
        
        # Common settings
        self.settings = JOURNALS_CONFIG['extraction_settings']
        
    def login(self) -> bool:
        """Generic login process for ScholarOne"""
        try:
            logger.info(f"Navigating to {self.journal_code} dashboard...")
            self.driver.get(self.login_url)
            time.sleep(3)
            
            # Handle cookie consent if present
            self._handle_cookie_consent()
            
            # Check for reCAPTCHA
            self._check_recaptcha()
            
            # Handle verification code
            if self._needs_verification():
                self._handle_verification()
                
            # Final reCAPTCHA check
            self._check_recaptcha()
            
            logger.info("Ready to continue navigation after login.")
            return True
            
        except Exception as e:
            logger.error(f"Login failed for {self.journal_code}: {e}")
            return False
            
    def _handle_cookie_consent(self):
        """Handle cookie consent banner if present"""
        try:
            # Try multiple common cookie consent patterns
            cookie_selectors = [
                "//button[contains(text(), 'Accept') and contains(@class, 'cookie')]",
                "//button[contains(text(), 'Accept All')]",
                "//button[@id='onetrust-accept-btn-handler']",
                "//button[contains(@class, 'accept-cookies')]"
            ]
            
            for selector in cookie_selectors:
                try:
                    cookie_button = self.driver.find_element(By.XPATH, selector)
                    if cookie_button.is_displayed():
                        cookie_button.click()
                        logger.info("Accepted cookies.")
                        time.sleep(2)
                        return
                except NoSuchElementException:
                    continue
                    
            if self.debug:
                logger.debug("No cookie accept button found.")
                
        except Exception as e:
            if self.debug:
                logger.debug(f"Cookie handling error: {e}")
                
    def _check_recaptcha(self):
        """Check for reCAPTCHA presence"""
        try:
            recaptcha = self.driver.find_element(By.CLASS_NAME, "g-recaptcha")
            if recaptcha.is_displayed():
                logger.warning("reCAPTCHA detected. Manual intervention may be required.")
                # In production, this could trigger a notification or use a solving service
                time.sleep(5)
        except NoSuchElementException:
            if self.debug:
                logger.debug("No reCAPTCHA found.")
                
    def _needs_verification(self) -> bool:
        """Check if verification code is needed"""
        try:
            # Check for common verification code input fields
            verification_selectors = [
                "TOKEN_VALUE",
                "verification_code", 
                "auth_code",
                "two_factor_code"
            ]
            
            for selector in verification_selectors:
                try:
                    element = self.driver.find_element(By.NAME, selector)
                    if element.is_displayed():
                        if self.debug:
                            logger.debug(f"Found and visible: {selector}")
                        return True
                except NoSuchElementException:
                    continue
                    
            # Also check by waiting
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.visibility_of_element_located((By.NAME, "TOKEN_VALUE"))
                )
                return True
            except TimeoutException:
                if self.debug:
                    logger.debug("No visible verification input appeared within 15s.")
                    
            return False
            
        except Exception as e:
            logger.error(f"Error checking for verification: {e}")
            return False
            
    def _handle_verification(self):
        """Handle verification code entry"""
        try:
            logger.info("Verification prompt visible. Fetching code from email...")
            
            # Import email fetching function
            from core.email_utils import fetch_verification_code_by_journal
            
            # Wait for email to arrive
            logger.info("Waiting 5 seconds for verification email to arrive...")
            time.sleep(5)
            
            # Fetch verification code
            verification_code = fetch_verification_code_by_journal(self.journal_code)
            
            if verification_code:
                if self.debug:
                    logger.debug(f"Verification code fetched: '{verification_code}'")
                    
                # Find and fill verification input
                try:
                    token_input = self.driver.find_element(By.NAME, "TOKEN_VALUE")
                    token_input.clear()
                    token_input.send_keys(verification_code)
                    
                    # Submit the form
                    submit_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
                    submit_button.click()
                    logger.info("Submitted verification code.")
                    time.sleep(3)
                    
                except Exception as e:
                    logger.error(f"Error submitting verification code: {e}")
                    
            else:
                logger.error("Failed to fetch verification code from email.")
                
        except Exception as e:
            logger.error(f"Verification handling error: {e}")
            
    def navigate_to_ae_center(self) -> bool:
        """Navigate to Associate Editor Center"""
        try:
            ae_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to AE Center: {e}")
            return False
            
    def navigate_to_category(self, category: Optional[str] = None) -> bool:
        """Navigate to specific manuscript category"""
        if category is None:
            category = self.ae_category
            
        try:
            category_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, category))
            )
            category_link.click()
            time.sleep(3)
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to category '{category}': {e}")
            return False
            
    def get_manuscript_table(self):
        """Get the main manuscript table"""
        try:
            return self.driver.find_element(By.TAG_NAME, "table")
        except NoSuchElementException:
            logger.error("No manuscript table found")
            return None
            
    def find_manuscript_checkbox(self, manuscript_id: str):
        """Find checkbox for a specific manuscript"""
        table = self.get_manuscript_table()
        if not table:
            return None
            
        rows = table.find_elements(By.TAG_NAME, "tr")
        
        for row in rows:
            row_text = row.text.strip()
            if row_text.startswith(manuscript_id):
                checkboxes = row.find_elements(
                    By.XPATH, f".//img[contains(@src, '{self.settings['checkbox_image']}')]"
                )
                if len(checkboxes) == 1:
                    logger.info(f"Found checkbox for {manuscript_id}")
                    return checkboxes[0]
                    
        return None
        
    def click_manuscript_checkbox(self, manuscript_id: str) -> bool:
        """Click checkbox for a manuscript"""
        checkbox = self.find_manuscript_checkbox(manuscript_id)
        if checkbox:
            try:
                self.driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                time.sleep(0.5)
                checkbox.click()
                time.sleep(3)
                return True
            except Exception as e:
                logger.error(f"Failed to click checkbox: {e}")
                
        return False
        
    def navigate_back_to_ae_center(self) -> bool:
        """Navigate back to AE Center from referee details page"""
        try:
            ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
            ae_link.click()
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Failed to navigate back: {e}")
            return False