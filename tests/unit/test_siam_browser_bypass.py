#!/usr/bin/env python3
"""
Test bypassing ScholarOne browser requirements page to reach actual login.
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

class SIAMBrowserBypassTester:
    """Test bypassing browser requirements to reach login."""
    
    def __init__(self):
        self.session_manager = SessionManager(Path('.'))
        self.results = {
            "sicon": {
                "initial_load": False,
                "browser_warning_found": False,
                "bypass_link_found": False,
                "bypass_successful": False,
                "login_page_reached": False,
                "orcid_button_found": False,
                "final_url": ""
            },
            "sifin": {
                "initial_load": False,
                "browser_warning_found": False,
                "bypass_link_found": False,
                "bypass_successful": False,
                "login_page_reached": False,
                "orcid_button_found": False,
                "final_url": ""
            },
            "errors": []
        }
        
    def create_better_driver(self, headless=True):
        """Create Chrome driver with better compatibility settings."""
        try:
            chrome_options = Options()
            if headless:
                chrome_options.add_argument("--headless")
            
            # Better user agent for ScholarOne compatibility
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Additional compatibility flags
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            
            # Remove webdriver property to avoid detection
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("✅ Enhanced Chrome WebDriver created")
            return driver
            
        except Exception as e:
            error_msg = f"Failed to create enhanced Chrome driver: {str(e)}"
            self.results["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}")
            return None
    
    def test_browser_bypass(self, driver, journal_code, url):
        """Test bypassing browser requirements page."""
        journal_results = self.results[journal_code.lower()]
        
        try:
            logger.info(f"🔍 Testing {journal_code} browser bypass...")
            
            # Step 1: Load the initial page
            driver.get(url)
            time.sleep(3)
            
            journal_results["initial_load"] = True
            logger.info(f"✅ {journal_code} initial page loaded")
            
            # Step 2: Check if we got the browser requirements page
            page_source = driver.page_source.lower()
            page_title = driver.title.lower()
            
            if "browser" in page_source and "requirements" in page_source:
                journal_results["browser_warning_found"] = True
                logger.info(f"🔍 {journal_code} browser requirements page detected")
                
                # Step 3: Look for bypass link ("here" link)
                bypass_selectors = [
                    "//a[contains(text(), 'here')]",
                    "//a[contains(@href, 'supported')]",
                    "//a[contains(@href, 'browser')]",
                    "//a[contains(text(), 'Click')]",
                    "//a[contains(text(), 'continue')]"
                ]
                
                bypass_link = None
                for selector in bypass_selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        if elements:
                            bypass_link = elements[0]
                            journal_results["bypass_link_found"] = True
                            logger.info(f"✅ {journal_code} bypass link found: '{bypass_link.text}'")
                            break
                    except Exception:
                        continue
                
                if bypass_link:
                    # Step 4: Click the bypass link
                    try:
                        original_url = driver.current_url
                        bypass_link.click()
                        time.sleep(3)
                        
                        if driver.current_url != original_url:
                            journal_results["bypass_successful"] = True
                            logger.info(f"✅ {journal_code} bypass successful, new URL: {driver.current_url}")
                        else:
                            logger.warning(f"⚠️  {journal_code} bypass link clicked but no redirect")
                    except Exception as e:
                        logger.warning(f"⚠️  {journal_code} could not click bypass link: {e}")
                else:
                    logger.warning(f"⚠️  {journal_code} no bypass link found")
            else:
                logger.info(f"✅ {journal_code} no browser requirements page (direct access)")
                journal_results["bypass_successful"] = True
            
            # Step 5: Check if we're now on a login page
            current_page = driver.page_source.lower()
            current_title = driver.title.lower()
            
            login_indicators = ["login", "sign in", "authentication", "user id", "password", "submit"]
            
            for indicator in login_indicators:
                if indicator in current_page or indicator in current_title:
                    journal_results["login_page_reached"] = True
                    logger.info(f"✅ {journal_code} login page reached (found '{indicator}')")
                    break
            
            # Step 6: Look for ORCID elements
            orcid_selectors = [
                "//a[contains(@href, 'orcid')]",
                "//a[contains(text(), 'ORCID')]", 
                "//button[contains(text(), 'ORCID')]",
                "//input[contains(@value, 'ORCID')]",
                "//a[contains(@title, 'ORCID')]",
                "//img[contains(@src, 'orcid')]//ancestor::a",
                "//*[contains(text(), 'ORCID iD')]",
                "//*[contains(text(), 'Connect')]",
                "//a[contains(@class, 'orcid')]"
            ]
            
            for selector in orcid_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements:
                        journal_results["orcid_button_found"] = True
                        logger.info(f"✅ {journal_code} ORCID element found: '{elements[0].text}'")
                        if elements[0].get_attribute("href"):
                            logger.info(f"   ORCID URL: {elements[0].get_attribute('href')}")
                        break
                except Exception:
                    continue
            
            journal_results["final_url"] = driver.current_url
            
            # Save final state for debugging
            if not journal_results["orcid_button_found"]:
                debug_file = Path(f"debug_output/{journal_code.lower()}_final_page_source.html")
                debug_file.parent.mkdir(exist_ok=True)
                with open(debug_file, 'w') as f:
                    f.write(driver.page_source)
                logger.info(f"📄 {journal_code} final page source saved to {debug_file}")
                
                try:
                    screenshot_file = Path(f"debug_output/{journal_code.lower()}_final_screenshot.png")
                    driver.save_screenshot(str(screenshot_file))
                    logger.info(f"📸 {journal_code} final screenshot saved to {screenshot_file}")
                except Exception as e:
                    logger.warning(f"⚠️  Could not save screenshot: {e}")
                
        except Exception as e:
            error_msg = f"{journal_code} browser bypass test failed: {str(e)}"
            self.results["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}")
    
    def run_test(self, headless=True):
        """Run comprehensive browser bypass test."""
        logger.info("🚀 Starting SIAM browser bypass test...")
        
        driver = None
        try:
            # Create enhanced driver
            driver = self.create_better_driver(headless)
            if not driver:
                return self.results
                
            # Test SICON bypass
            self.test_browser_bypass(driver, "SICON", "https://mc.manuscriptcentral.com/sicon")
            
            time.sleep(2)  # Brief pause between tests
            
            # Test SIFIN bypass
            self.test_browser_bypass(driver, "SIFIN", "https://mc.manuscriptcentral.com/sifin")
            
            # Save progress
            self.session_manager.auto_save_progress(
                "SIAM browser bypass test completed",
                learning=f"Browser compatibility testing completed for SICON and SIFIN"
            )
            
        except Exception as e:
            error_msg = f"Browser bypass test failed: {str(e)}"
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
        print("🌐 SIAM BROWSER BYPASS TEST SUMMARY")
        print("="*80)
        
        for journal in ["sicon", "sifin"]:
            results = self.results[journal]
            print(f"\n📊 {journal.upper()} Results:")
            print(f"   Initial Load: {'✅ SUCCESS' if results['initial_load'] else '❌ FAILED'}")
            print(f"   Browser Warning: {'⚠️  DETECTED' if results['browser_warning_found'] else '✅ NOT FOUND'}")
            print(f"   Bypass Link: {'✅ FOUND' if results['bypass_link_found'] else '❌ NOT FOUND'}")
            print(f"   Bypass Success: {'✅ SUCCESS' if results['bypass_successful'] else '❌ FAILED'}")
            print(f"   Login Page: {'✅ REACHED' if results['login_page_reached'] else '❌ NOT REACHED'}")
            print(f"   ORCID Button: {'✅ FOUND' if results['orcid_button_found'] else '❌ NOT FOUND'}")
            print(f"   Final URL: {results['final_url']}")
        
        if self.results["errors"]:
            print(f"\n❌ ERRORS ({len(self.results['errors'])}):")
            for i, error in enumerate(self.results["errors"], 1):
                print(f"   {i}. {error}")
        
        # Calculate success metrics
        orcid_found_count = sum(1 for journal in ["sicon", "sifin"] 
                               if self.results[journal]["orcid_button_found"])
        login_reached_count = sum(1 for journal in ["sicon", "sifin"] 
                                 if self.results[journal]["login_page_reached"])
        
        print(f"\n📈 SUCCESS METRICS:")
        print(f"   Login Pages Reached: {login_reached_count}/2")
        print(f"   ORCID Buttons Found: {orcid_found_count}/2")
        
        if orcid_found_count == 2:
            print("\n✅ READY FOR CREDENTIAL TESTING!")
            print("🔑 Next step: Set ORCID credentials and run full authentication test")
        elif login_reached_count == 2:
            print("\n⚠️  LOGIN PAGES REACHED BUT ORCID NOT FOUND")
            print("💡 May need different ORCID detection approach or institutional access")
        else:
            print("\n❌ BROWSER COMPATIBILITY ISSUES PERSIST")
            print("🔧 May need alternative browser configuration or direct URL access")

def main():
    """Main test entry point."""
    tester = SIAMBrowserBypassTester()
    
    print("🌐 Testing SIAM browser bypass with enhanced compatibility")
    print("This will attempt to bypass browser requirements and reach login pages...")
    
    # Run test
    results = tester.run_test(headless=True)
    
    # Print summary
    tester.print_summary()
    
    # Return exit code
    login_reached = sum(1 for journal in ["sicon", "sifin"] 
                       if results[journal]["login_page_reached"])
    
    return 0 if login_reached >= 1 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)