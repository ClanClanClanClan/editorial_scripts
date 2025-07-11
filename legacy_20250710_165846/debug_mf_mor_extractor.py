#!/usr/bin/env python3
"""
Ultra-Debug MF/MOR Extractor - Comprehensive crash diagnosis and recovery
"""

import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from bs4 import BeautifulSoup
import json
import re
import traceback
from selenium.webdriver.chrome.options import Options

# Setup comprehensive logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug_extraction.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("DEBUG_EXTRACTOR")

class DebugMFMORExtractor:
    """Ultra-robust extractor with comprehensive debugging"""
    
    def __init__(self):
        self.driver = None
        self.debug_dir = Path("debug_screenshots")
        self.debug_dir.mkdir(exist_ok=True)
        self.step_counter = 0
        
    def capture_debug_info(self, step_name: str, save_screenshot=True, save_html=True):
        """Capture comprehensive debug information"""
        self.step_counter += 1
        timestamp = datetime.now().strftime("%H%M%S")
        prefix = f"{self.step_counter:02d}_{timestamp}_{step_name}"
        
        try:
            if save_screenshot and self.driver:
                screenshot_path = self.debug_dir / f"{prefix}_screenshot.png"
                self.driver.save_screenshot(str(screenshot_path))
                logger.debug(f"📸 Screenshot saved: {screenshot_path}")
                
            if save_html and self.driver:
                html_path = self.debug_dir / f"{prefix}_page.html"
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                logger.debug(f"📄 HTML saved: {html_path}")
                
            # Log current URL and page title
            if self.driver:
                logger.debug(f"🌐 Current URL: {self.driver.current_url}")
                logger.debug(f"📑 Page title: {self.driver.title}")
                
                # Check for common error indicators
                page_source = self.driver.page_source.lower()
                if 'error' in page_source:
                    logger.warning("⚠️  'Error' found in page source")
                if 'timeout' in page_source:
                    logger.warning("⚠️  'Timeout' found in page source")
                if 'access denied' in page_source:
                    logger.warning("⚠️  'Access denied' found in page source")
                    
        except Exception as e:
            logger.error(f"Error capturing debug info for {step_name}: {e}")
    
    def create_robust_driver(self, headless=False, attempt=1):
        """Create Chrome driver with multiple fallback options"""
        logger.info(f"🚀 Creating Chrome driver (attempt {attempt})")
        
        options = uc.ChromeOptions()
        
        # Base options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=VizDisplayCompositor')
        
        # Memory and stability options
        options.add_argument('--max_old_space_size=4096')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        
        # Anti-detection options
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        if headless:
            options.add_argument('--headless=new')
            
        try:
            # Try different driver creation methods
            if attempt == 1:
                # Standard undetected chrome
                self.driver = uc.Chrome(options=options, version_main=None)
            elif attempt == 2:
                # With explicit version
                self.driver = uc.Chrome(options=options, version_main=126)
            elif attempt == 3:
                # Patcher auto-download
                self.driver = uc.Chrome(options=options, patcher_force_close=True)
            else:
                raise Exception("All driver creation attempts failed")
                
            logger.info("✅ Chrome driver created successfully")
            
            # Set additional properties
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
            })
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Driver creation attempt {attempt} failed: {e}")
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            
            if attempt < 3:
                logger.info(f"🔄 Retrying driver creation...")
                time.sleep(2)
                return self.create_robust_driver(headless, attempt + 1)
            else:
                raise Exception(f"Failed to create driver after {attempt} attempts")
    
    def safe_navigate(self, url: str, timeout: int = 30, retries: int = 3):
        """Navigate with comprehensive error handling"""
        for attempt in range(retries):
            try:
                logger.info(f"🌐 Navigating to: {url} (attempt {attempt + 1})")
                self.driver.set_page_load_timeout(timeout)
                self.driver.get(url)
                
                # Wait for basic page load
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                
                self.capture_debug_info(f"navigate_{attempt + 1}")
                logger.info("✅ Navigation successful")
                return True
                
            except TimeoutException:
                logger.warning(f"⏰ Navigation timeout on attempt {attempt + 1}")
                if attempt < retries - 1:
                    time.sleep(3)
                    continue
            except WebDriverException as e:
                logger.error(f"❌ WebDriver error on attempt {attempt + 1}: {e}")
                if attempt < retries - 1:
                    time.sleep(3)
                    continue
            except Exception as e:
                logger.error(f"❌ Unexpected error on attempt {attempt + 1}: {e}")
                self.capture_debug_info(f"navigate_error_{attempt + 1}")
                if attempt < retries - 1:
                    time.sleep(3)
                    continue
                    
        return False
    
    def safe_click(self, element_locator, element_name: str, timeout: int = 10, retries: int = 3):
        """Click element with comprehensive error handling"""
        for attempt in range(retries):
            try:
                logger.info(f"🖱️  Clicking {element_name} (attempt {attempt + 1})")
                
                # Try multiple locator strategies
                element = None
                if isinstance(element_locator, tuple):
                    by, value = element_locator
                    element = WebDriverWait(self.driver, timeout).until(
                        EC.element_to_be_clickable((by, value))
                    )
                elif isinstance(element_locator, str):
                    # Try multiple strategies for string locators
                    strategies = [
                        (By.LINK_TEXT, element_locator),
                        (By.PARTIAL_LINK_TEXT, element_locator),
                        (By.XPATH, f"//*[contains(text(), '{element_locator}')]"),
                        (By.CSS_SELECTOR, element_locator)
                    ]
                    
                    for by, value in strategies:
                        try:
                            element = WebDriverWait(self.driver, 5).until(
                                EC.element_to_be_clickable((by, value))
                            )
                            logger.debug(f"✅ Found element using {by}: {value}")
                            break
                        except TimeoutException:
                            continue
                
                if not element:
                    raise Exception(f"Could not find clickable element: {element_locator}")
                
                # Scroll into view
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(0.5)
                
                # Capture before click
                self.capture_debug_info(f"before_click_{element_name}_{attempt + 1}")
                
                # Try different click methods
                try:
                    element.click()
                except Exception:
                    # Fallback to JavaScript click
                    logger.debug("🔄 Fallback to JavaScript click")
                    self.driver.execute_script("arguments[0].click();", element)
                
                time.sleep(2)
                self.capture_debug_info(f"after_click_{element_name}_{attempt + 1}")
                
                logger.info(f"✅ Successfully clicked {element_name}")
                return True
                
            except TimeoutException:
                logger.warning(f"⏰ Timeout waiting for {element_name} on attempt {attempt + 1}")
                self.capture_debug_info(f"click_timeout_{element_name}_{attempt + 1}")
            except Exception as e:
                logger.error(f"❌ Error clicking {element_name} on attempt {attempt + 1}: {e}")
                self.capture_debug_info(f"click_error_{element_name}_{attempt + 1}")
                
            if attempt < retries - 1:
                time.sleep(2)
                
        return False
    
    def handle_verification_code(self):
        """Handle 2FA verification with robust error handling"""
        try:
            logger.info("🔐 Checking for verification code prompt...")
            
            # Check if verification is needed
            verification_input = None
            selectors = [
                (By.NAME, "TOKEN_VALUE"),
                (By.ID, "TOKEN_VALUE"),
                (By.XPATH, "//input[contains(@name, 'TOKEN')]"),
                (By.XPATH, "//input[contains(@id, 'token')]")
            ]
            
            for by, value in selectors:
                try:
                    verification_input = WebDriverWait(self.driver, 5).until(
                        EC.visibility_of_element_located((by, value))
                    )
                    logger.debug(f"✅ Found verification input using {by}: {value}")
                    break
                except TimeoutException:
                    continue
            
            if not verification_input:
                logger.info("ℹ️  No verification code required")
                return True
                
            logger.info("📧 Verification code required. Fetching from email...")
            self.capture_debug_info("verification_prompt")
            
            # Import and fetch verification code
            sys.path.insert(0, str(Path(__file__).parent))
            from core.email_utils import fetch_verification_code_by_journal
            
            # Wait for email
            logger.info("⏳ Waiting 5 seconds for verification email...")
            time.sleep(5)
            
            # Try fetching code multiple times
            verification_code = None
            for attempt in range(3):
                try:
                    verification_code = fetch_verification_code_by_journal("MF")
                    if verification_code:
                        break
                    logger.warning(f"No code found on attempt {attempt + 1}, waiting...")
                    time.sleep(3)
                except Exception as e:
                    logger.error(f"Error fetching verification code: {e}")
                    time.sleep(3)
            
            if not verification_code:
                raise Exception("Failed to fetch verification code after multiple attempts")
                
            logger.info(f"✅ Got verification code: {verification_code}")
            
            # Clear and enter code
            verification_input.clear()
            verification_input.send_keys(verification_code)
            self.capture_debug_info("verification_entered")
            
            # Find and click submit button
            submit_selectors = [
                (By.XPATH, "//button[@type='submit']"),
                (By.XPATH, "//input[@type='submit']"),
                (By.XPATH, "//button[contains(text(), 'Submit')]"),
                (By.XPATH, "//button[contains(text(), 'Verify')]")
            ]
            
            for by, value in submit_selectors:
                try:
                    submit_button = self.driver.find_element(by, value)
                    if submit_button.is_displayed():
                        submit_button.click()
                        logger.info("✅ Clicked submit button")
                        break
                except:
                    continue
            else:
                # Fallback: press Enter
                verification_input.send_keys(Keys.RETURN)
                logger.info("🔄 Pressed Enter to submit")
            
            time.sleep(3)
            self.capture_debug_info("verification_submitted")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Verification handling failed: {e}")
            self.capture_debug_info("verification_error")
            return False
    
    def test_mf_extraction(self, headless=False):
        """Test MF extraction with comprehensive debugging"""
        logger.info("🧪 Starting comprehensive MF extraction test")
        
        try:
            # Create driver
            if not self.create_robust_driver(headless=headless):
                raise Exception("Failed to create driver")
                
            # Navigate to MF
            mf_url = "https://mc.manuscriptcentral.com/mafi"
            if not self.safe_navigate(mf_url):
                raise Exception("Failed to navigate to MF")
                
            time.sleep(3)
            self.capture_debug_info("initial_page")
            
            # Handle cookies
            logger.info("🍪 Handling cookies...")
            cookie_selectors = [
                "//button[contains(text(), 'Accept')]",
                "//button[contains(text(), 'Accept All')]",
                "//button[@id='onetrust-accept-btn-handler']"
            ]
            
            for selector in cookie_selectors:
                try:
                    cookie_btn = self.driver.find_element(By.XPATH, selector)
                    if cookie_btn.is_displayed():
                        cookie_btn.click()
                        logger.info("✅ Accepted cookies")
                        time.sleep(2)
                        break
                except:
                    continue
            
            self.capture_debug_info("after_cookies")
            
            # Handle verification if needed
            if not self.handle_verification_code():
                raise Exception("Verification code handling failed")
                
            self.capture_debug_info("after_verification")
            
            # Wait for dashboard to load
            logger.info("⏳ Waiting for dashboard...")
            try:
                WebDriverWait(self.driver, 15).until(
                    lambda driver: "dashboard" in driver.current_url.lower() or 
                                 "center" in driver.page_source.lower()
                )
                logger.info("✅ Dashboard loaded")
            except TimeoutException:
                logger.warning("⏰ Dashboard load timeout, proceeding anyway")
                
            self.capture_debug_info("dashboard_loaded")
            
            # Try to find Associate Editor Center link
            logger.info("🔍 Looking for Associate Editor Center...")
            ae_center_found = False
            
            # Try multiple strategies to find AE Center
            ae_strategies = [
                (By.LINK_TEXT, "Associate Editor Center"),
                (By.PARTIAL_LINK_TEXT, "Associate Editor"),
                (By.PARTIAL_LINK_TEXT, "Editor Center"),
                (By.XPATH, "//a[contains(text(), 'Associate Editor')]"),
                (By.XPATH, "//a[contains(text(), 'Editor Center')]"),
                (By.XPATH, "//*[contains(@class, 'nav')]//a[contains(text(), 'Associate')]")
            ]
            
            for by, value in ae_strategies:
                try:
                    ae_link = self.driver.find_element(by, value)
                    if ae_link.is_displayed():
                        logger.info(f"✅ Found AE Center using {by}: {value}")
                        logger.debug(f"   Link text: '{ae_link.text}'")
                        logger.debug(f"   Link href: '{ae_link.get_attribute('href')}'")
                        ae_center_found = True
                        break
                except:
                    continue
            
            if not ae_center_found:
                logger.error("❌ Could not find Associate Editor Center link")
                self.capture_debug_info("ae_center_not_found")
                
                # List all links for debugging
                logger.debug("🔍 All links on page:")
                try:
                    links = self.driver.find_elements(By.TAG_NAME, "a")
                    for i, link in enumerate(links[:20]):  # Show first 20 links
                        try:
                            text = link.text.strip()
                            href = link.get_attribute('href')
                            if text or href:
                                logger.debug(f"   {i+1}. '{text}' -> {href}")
                        except:
                            continue
                except Exception as e:
                    logger.error(f"Error listing links: {e}")
                    
                return False
            
            # Try to click Associate Editor Center
            logger.info("🖱️  Attempting to click Associate Editor Center...")
            if not self.safe_click("Associate Editor Center", "Associate Editor Center"):
                raise Exception("Failed to click Associate Editor Center")
                
            self.capture_debug_info("after_ae_center_click")
            
            # Check if we're in the right place
            logger.info("✅ Successfully navigated to Associate Editor Center!")
            
            # Look for manuscript categories
            logger.info("🔍 Looking for manuscript categories...")
            try:
                categories = ["Awaiting Reviewer Scores", "Awaiting Reviewer Reports"]
                for category in categories:
                    try:
                        cat_link = self.driver.find_element(By.LINK_TEXT, category)
                        logger.info(f"✅ Found category: {category}")
                    except:
                        logger.debug(f"   Category not found: {category}")
                        
            except Exception as e:
                logger.error(f"Error checking categories: {e}")
                
            self.capture_debug_info("final_state")
            logger.info("🎉 Test completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.capture_debug_info("test_failure")
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
    
    extractor = DebugMFMORExtractor()
    success = extractor.test_mf_extraction(headless=args.headless)
    
    if success:
        print("✅ Test passed!")
        sys.exit(0)
    else:
        print("❌ Test failed!")
        sys.exit(1)