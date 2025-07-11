#!/usr/bin/env python3
"""
Robust MF/MOR Extractor - Simplified and reliable
"""

import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from bs4 import BeautifulSoup
import json
import re
import traceback

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('robust_extraction.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ROBUST_EXTRACTOR")

class RobustMFMORExtractor:
    """Simplified, robust extractor for MF/MOR"""
    
    def __init__(self):
        self.driver = None
        self.debug_dir = Path("robust_debug")
        self.debug_dir.mkdir(exist_ok=True)
        
    def capture_state(self, step_name: str):
        """Capture current state for debugging"""
        try:
            timestamp = datetime.now().strftime("%H%M%S")
            if self.driver:
                # Screenshot
                screenshot_path = self.debug_dir / f"{timestamp}_{step_name}.png"
                self.driver.save_screenshot(str(screenshot_path))
                
                # Current URL and title
                logger.info(f"📍 {step_name} - URL: {self.driver.current_url}")
                logger.info(f"📑 {step_name} - Title: {self.driver.title}")
                
        except Exception as e:
            logger.warning(f"Could not capture state for {step_name}: {e}")
    
    def create_simple_driver(self, headless=False):
        """Create a simple, reliable Chrome driver"""
        logger.info("🚀 Creating simple Chrome driver...")
        
        try:
            options = Options()
            
            # Essential options only
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            
            if headless:
                options.add_argument('--headless')
                
            # Disable logging to reduce noise
            options.add_argument('--log-level=3')
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Try to create driver
            self.driver = webdriver.Chrome(options=options)
            
            # Set timeouts
            self.driver.implicitly_wait(10)
            self.driver.set_page_load_timeout(30)
            
            logger.info("✅ Simple Chrome driver created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create simple driver: {e}")
            return False
    
    def robust_navigate(self, url: str, max_retries=3):
        """Navigate with retries"""
        for attempt in range(max_retries):
            try:
                logger.info(f"🌐 Navigating to: {url} (attempt {attempt + 1})")
                self.driver.get(url)
                
                # Wait for page to load
                WebDriverWait(self.driver, 15).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                
                self.capture_state(f"navigate_success_{attempt + 1}")
                return True
                
            except Exception as e:
                logger.warning(f"Navigation attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                    
        return False
    
    def find_and_click(self, selectors, element_name, timeout=15):
        """Find element using multiple selectors and click it"""
        logger.info(f"🔍 Looking for: {element_name}")
        
        # Ensure selectors is a list
        if isinstance(selectors, str):
            selectors = [selectors]
            
        for i, selector in enumerate(selectors):
            try:
                logger.debug(f"   Trying selector {i+1}: {selector}")
                
                if selector.startswith("//"):
                    # XPath
                    element = WebDriverWait(self.driver, timeout).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                elif selector.startswith("#") or selector.startswith("."):
                    # CSS selector
                    element = WebDriverWait(self.driver, timeout).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                else:
                    # Link text
                    element = WebDriverWait(self.driver, timeout).until(
                        EC.element_to_be_clickable((By.LINK_TEXT, selector))
                    )
                
                # Scroll into view
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(0.5)
                
                # Click
                element.click()
                logger.info(f"✅ Successfully clicked: {element_name}")
                time.sleep(2)
                return True
                
            except TimeoutException:
                logger.debug(f"   Selector {i+1} timed out")
                continue
            except Exception as e:
                logger.debug(f"   Selector {i+1} failed: {e}")
                continue
                
        logger.error(f"❌ Could not find/click: {element_name}")
        return False
    
    def handle_login_and_verification(self, journal_code="MF"):
        """Handle complete login process including credentials and verification"""
        logger.info("🔐 Starting login process...")
        
        try:
            # Check if we need to login first
            page_source = self.driver.page_source.lower()
            
            # Look for login form (exact same as working system)
            try:
                username_input = WebDriverWait(self.driver, 5).until(
                    EC.visibility_of_element_located((By.ID, "USERID"))
                )
                logger.info("📝 Found username input field")
            except TimeoutException:
                logger.info("ℹ️  No login form found, may already be logged in")
                username_input = None
            
            if username_input:
                logger.info("🔑 Login form detected, entering credentials...")
                
                # Find password field (exact same as working system)
                try:
                    password_input = self.driver.find_element(By.ID, "PASSWORD")
                    logger.info("🔒 Found password input field")
                except:
                    logger.error("❌ Could not find password field")
                    return False
                
                # Get credentials (same as working system)
                username = os.getenv('MF_USER')
                password = os.getenv('MF_PASS')
                
                if not username or not password:
                    logger.error("❌ Please set MF_USER and MF_PASS environment variables")
                    return False
                
                # Enter credentials
                username_input.clear()
                username_input.send_keys(username)
                
                password_input.clear()
                password_input.send_keys(password)
                
                # Submit login (exact same as working system)
                try:
                    login_button = self.driver.find_element(By.ID, "logInButton")
                    login_button.click()
                    logger.info("📤 Submitted login form")
                    time.sleep(4)  # Same timing as working system
                except:
                    logger.error("❌ Could not find login button")
                    return False
                
                self.capture_state("after_login_submit")
            
            # Now check for verification code (exact same as working system)
            logger.info("🔐 Checking for verification code...")
            
            wait = WebDriverWait(self.driver, 15)
            verification_input = None
            
            try:
                # Check for reCAPTCHA first (like working system)
                try:
                    recaptcha_iframe = self.driver.find_element(By.XPATH, "//iframe[contains(@title, 'reCAPTCHA')]")
                    if recaptcha_iframe.is_displayed():
                        logger.info("🤖 reCAPTCHA detected, handling...")
                        self.driver.switch_to.frame(recaptcha_iframe)
                        checkbox = self.driver.find_element(By.ID, "recaptcha-anchor")
                        checkbox.click()
                        self.driver.switch_to.default_content()
                        logger.info("✅ Clicked reCAPTCHA checkbox")
                        time.sleep(2)
                except:
                    logger.debug("No reCAPTCHA present")
                
                # Look for verification code input (same as working system)
                try:
                    verification_input = wait.until(
                        lambda d: d.find_element(By.ID, "TOKEN_VALUE") if d.find_element(By.ID, "TOKEN_VALUE").is_displayed() else None
                    )
                    logger.info("📧 Found TOKEN_VALUE verification input")
                except TimeoutException:
                    try:
                        verification_input = wait.until(
                            lambda d: d.find_element(By.ID, "validationCode") if d.find_element(By.ID, "validationCode").is_displayed() else None
                        )
                        logger.info("📧 Found validationCode verification input")
                    except TimeoutException:
                        logger.debug("No visible verification input appeared within 15s")
                        verification_input = None
            except Exception as e:
                logger.debug(f"Verification check error: {e}")
                verification_input = None
            
            if not verification_input:
                logger.info("ℹ️  No verification code required")
                return True
            
            # Fetch verification code
            sys.path.insert(0, str(Path(__file__).parent))
            from core.email_utils import fetch_latest_verification_code
            
            logger.info("⏳ Waiting for verification email...")
            time.sleep(5)
            
            # Try to get code multiple times
            verification_code = None
            for attempt in range(3):
                verification_code = fetch_latest_verification_code(journal=journal_code)
                if verification_code:
                    break
                logger.info(f"   No code yet, attempt {attempt + 1}/3...")
                time.sleep(3)
            
            if not verification_code:
                logger.error("❌ Could not get verification code")
                return False
                
            logger.info(f"✅ Got verification code: {verification_code}")
            
            # Enter code
            verification_input.clear()
            verification_input.send_keys(verification_code)
            verification_input.send_keys(Keys.RETURN)
            
            logger.info("📤 Submitted verification code")
            time.sleep(3)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Login/verification failed: {e}")
            return False
    
    def test_mf_login_and_navigation(self, headless=False):
        """Test MF login and basic navigation"""
        logger.info("🧪 Testing MF login and navigation")
        
        try:
            # Create driver
            if not self.create_simple_driver(headless=headless):
                raise Exception("Driver creation failed")
            
            # Navigate to MF
            mf_url = "https://mc.manuscriptcentral.com/mafi"
            if not self.robust_navigate(mf_url):
                raise Exception("Navigation to MF failed")
                
            self.capture_state("initial_page")
            
            # Handle cookies
            logger.info("🍪 Handling cookies...")
            cookie_selectors = [
                "//button[contains(text(), 'Accept All')]",
                "//button[contains(text(), 'Accept')]",
                "//button[@id='onetrust-accept-btn-handler']"
            ]
            
            for selector in cookie_selectors:
                try:
                    self.find_and_click([selector], "cookie accept button", timeout=5)
                    break
                except:
                    continue
            
            self.capture_state("after_cookies")
            
            # Handle login and verification
            if not self.handle_login_and_verification("MF"):
                raise Exception("Login/verification failed")
                
            self.capture_state("after_verification")
            
            # Wait for main page to load
            logger.info("⏳ Waiting for main page...")
            time.sleep(5)
            
            # Look for navigation elements
            logger.info("🔍 Checking page content...")
            page_text = self.driver.page_source.lower()
            
            if "associate editor" in page_text:
                logger.info("✅ Found 'Associate Editor' in page content")
            if "center" in page_text:
                logger.info("✅ Found 'Center' in page content")
            if "manuscript" in page_text:
                logger.info("✅ Found 'Manuscript' in page content")
                
            # Try to find Associate Editor Center
            ae_selectors = [
                "Associate Editor Center",
                "//a[contains(text(), 'Associate Editor Center')]",
                "//a[contains(text(), 'Associate Editor')]",
                "//a[contains(text(), 'Editor Center')]"
            ]
            
            if self.find_and_click(ae_selectors, "Associate Editor Center", timeout=10):
                logger.info("🎉 Successfully clicked Associate Editor Center!")
                self.capture_state("ae_center_success")
                
                # Look for categories
                time.sleep(3)
                logger.info("🔍 Looking for manuscript categories...")
                
                categories = ["Awaiting Reviewer Scores", "Awaiting Reviewer Reports"]
                for category in categories:
                    try:
                        cat_element = self.driver.find_element(By.LINK_TEXT, category)
                        logger.info(f"✅ Found category: {category}")
                    except:
                        logger.debug(f"   Category not found: {category}")
                
                self.capture_state("final_success")
                return True
            else:
                logger.error("❌ Could not find Associate Editor Center")
                
                # Debug: show all links
                logger.info("🔍 Debug - All links on page:")
                try:
                    links = self.driver.find_elements(By.TAG_NAME, "a")
                    for i, link in enumerate(links[:15]):
                        text = link.text.strip()
                        href = link.get_attribute('href')
                        if text:
                            logger.info(f"   {i+1}. '{text}' -> {href}")
                except Exception as e:
                    logger.error(f"Error listing links: {e}")
                
                self.capture_state("ae_center_not_found")
                return False
                
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.capture_state("test_failure")
            return False
            
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    logger.info("🔄 Driver closed")
                except:
                    pass

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    args = parser.parse_args()
    
    extractor = RobustMFMORExtractor()
    success = extractor.test_mf_login_and_navigation(headless=args.headless)
    
    if success:
        print("✅ Test passed! MF navigation works.")
        sys.exit(0)
    else:
        print("❌ Test failed!")
        sys.exit(1)