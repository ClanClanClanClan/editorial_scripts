#!/usr/bin/env python3
"""
Test SIAM actual login page after JavaScript redirect.
This follows the redirect to find the actual login form.
"""

import sys
import time
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from editorial_assistant.utils.session_manager import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SIAMActualLoginTester:
    """Test SIAM actual login page after redirects."""
    
    def __init__(self):
        self.session_manager = SessionManager(Path('.'))
        self.results = {
            "sicon": {
                "initial_load": False,
                "redirect_occurred": False,
                "login_page_found": False,
                "orcid_button_found": False,
                "final_url": ""
            },
            "sifin": {
                "initial_load": False,
                "redirect_occurred": False,
                "login_page_found": False,
                "orcid_button_found": False,
                "final_url": ""
            },
            "errors": []
        }
        
    def create_driver(self, headless=True):
        """Create a Chrome WebDriver instance."""
        try:
            chrome_options = Options()
            if headless:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            
            logger.info("✅ Chrome WebDriver created successfully")
            return driver
            
        except Exception as e:
            error_msg = f"Failed to create Chrome driver: {str(e)}"
            self.results["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}")
            return None
    
    def test_actual_login_page(self, driver, journal_code, url):
        """Test actual login page after JavaScript redirects."""
        journal_results = self.results[journal_code.lower()]
        
        try:
            logger.info(f"🔍 Testing {journal_code} actual login page...")
            
            # Step 1: Load the initial page
            initial_url = url
            driver.get(initial_url)
            time.sleep(2)
            
            journal_results["initial_load"] = True
            logger.info(f"✅ {journal_code} initial page loaded")
            
            # Step 2: Wait for JavaScript redirect (up to 10 seconds)
            wait_time = 0
            max_wait = 10
            current_url = driver.current_url
            
            while wait_time < max_wait and driver.current_url == current_url:
                time.sleep(1)
                wait_time += 1
            
            if driver.current_url != current_url:
                journal_results["redirect_occurred"] = True
                journal_results["final_url"] = driver.current_url
                logger.info(f"✅ {journal_code} redirect occurred to: {driver.current_url}")
            else:
                logger.warning(f"⚠️  {journal_code} no redirect occurred")
                journal_results["final_url"] = driver.current_url
            
            # Step 3: Check if we're on a login page
            page_title = driver.title.lower()
            page_source = driver.page_source.lower()
            
            login_indicators = ["login", "sign in", "authentication", "userid", "username", "password"]
            
            for indicator in login_indicators:
                if indicator in page_title or indicator in page_source:
                    journal_results["login_page_found"] = True
                    logger.info(f"✅ {journal_code} login page detected (found '{indicator}')")
                    break
            
            if not journal_results["login_page_found"]:
                logger.warning(f"⚠️  {journal_code} login page not clearly identified")
            
            # Step 4: Look for ORCID elements more thoroughly
            orcid_selectors = [
                "//a[contains(@href, 'orcid')]",
                "//a[contains(text(), 'ORCID')]", 
                "//button[contains(text(), 'ORCID')]",
                "//input[contains(@value, 'ORCID')]",
                "//a[contains(@title, 'ORCID')]",
                "//a[contains(@class, 'orcid')]",
                "//div[contains(@class, 'orcid')]//a",
                "//span[contains(text(), 'ORCID')]/ancestor::a",
                "//*[contains(text(), 'ORCID iD')]",
                "//*[contains(text(), 'Connect with ORCID')]",
                "//img[contains(@src, 'orcid')]//ancestor::a",
                "//img[contains(@alt, 'orcid')]//ancestor::a"
            ]
            
            for selector in orcid_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements:
                        journal_results["orcid_button_found"] = True
                        logger.info(f"✅ {journal_code} ORCID element found with selector: {selector}")
                        logger.info(f"   Element text: '{elements[0].text}'")
                        if elements[0].get_attribute("href"):
                            logger.info(f"   Element href: '{elements[0].get_attribute('href')}'")
                        break
                except Exception:
                    continue
            
            if not journal_results["orcid_button_found"]:
                logger.warning(f"⚠️  {journal_code} ORCID element still not found")
                
                # Save final page source for debugging
                debug_file = Path(f"debug_output/{journal_code.lower()}_login_page_source.html")
                debug_file.parent.mkdir(exist_ok=True)
                with open(debug_file, 'w') as f:
                    f.write(driver.page_source)
                logger.info(f"📄 {journal_code} login page source saved to {debug_file}")
                
                # Also save a screenshot
                try:
                    screenshot_file = Path(f"debug_output/{journal_code.lower()}_login_screenshot.png")
                    driver.save_screenshot(str(screenshot_file))
                    logger.info(f"📸 {journal_code} login screenshot saved to {screenshot_file}")
                except Exception as e:
                    logger.warning(f"⚠️  Could not save screenshot: {e}")
                
        except Exception as e:
            error_msg = f"{journal_code} actual login test failed: {str(e)}"
            self.results["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}")
    
    def run_test(self, headless=True):
        """Run comprehensive actual login test."""
        logger.info("🚀 Starting SIAM actual login page test...")
        
        driver = None
        try:
            # Create driver
            driver = self.create_driver(headless)
            if not driver:
                return self.results
                
            # Test SICON actual login
            self.test_actual_login_page(driver, "SICON", "https://mc.manuscriptcentral.com/sicon")
            
            time.sleep(2)  # Brief pause between tests
            
            # Test SIFIN actual login
            self.test_actual_login_page(driver, "SIFIN", "https://mc.manuscriptcentral.com/sifin")
            
            # Save progress
            self.session_manager.auto_save_progress(
                "SIAM actual login page test completed",
                learning=f"Login page analysis completed for SICON and SIFIN"
            )
            
        except Exception as e:
            error_msg = f"Actual login test failed: {str(e)}"
            self.results["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}")
            
        finally:
            if driver:
                driver.quit()
                logger.info("🔄 WebDriver closed")
        
        return self.results
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*80)
        print("🔐 SIAM ACTUAL LOGIN PAGE TEST SUMMARY")
        print("="*80)
        
        for journal in ["sicon", "sifin"]:
            results = self.results[journal]
            print(f"\n📊 {journal.upper()} Results:")
            print(f"   Initial Load: {'✅ SUCCESS' if results['initial_load'] else '❌ FAILED'}")
            print(f"   Redirect: {'✅ OCCURRED' if results['redirect_occurred'] else '❌ NO REDIRECT'}")
            print(f"   Login Page: {'✅ FOUND' if results['login_page_found'] else '❌ NOT FOUND'}")
            print(f"   ORCID Button: {'✅ FOUND' if results['orcid_button_found'] else '❌ NOT FOUND'}")
            print(f"   Final URL: {results['final_url']}")
        
        if self.results["errors"]:
            print(f"\n❌ ERRORS ({len(self.results['errors'])}):")
            for i, error in enumerate(self.results["errors"], 1):
                print(f"   {i}. {error}")
        
        # Calculate success metrics
        orcid_found_count = sum(1 for journal in ["sicon", "sifin"] 
                               if self.results[journal]["orcid_button_found"])
        
        print(f"\n📈 ORCID DETECTION: {orcid_found_count}/2 journals")
        
        if orcid_found_count == 2:
            print("✅ READY FOR CREDENTIAL TESTING: All ORCID buttons found!")
        elif orcid_found_count == 1:
            print("⚠️  PARTIAL SUCCESS: One ORCID button found")
        else:
            print("❌ ORCID DETECTION FAILED: May need different approach")
            print("💡 Consider checking if login requires institutional access")

def main():
    """Main test entry point."""
    tester = SIAMActualLoginTester()
    
    print("🔐 Testing SIAM actual login pages (after redirects)")
    print("This will find the real login forms and ORCID buttons...")
    
    # Run test
    results = tester.run_test(headless=True)
    
    # Print summary
    tester.print_summary()
    
    # Return exit code
    orcid_found = sum(1 for journal in ["sicon", "sifin"] 
                     if results[journal]["orcid_button_found"])
    
    return 0 if orcid_found >= 1 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)