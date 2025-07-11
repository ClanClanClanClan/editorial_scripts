#!/usr/bin/env python3
"""
Test SIAM login flow without actual credentials.
This simulates the login process to validate the automation workflow.
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
from selenium.common.exceptions import TimeoutException

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from editorial_assistant.utils.session_manager import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SIAMLoginFlowTester:
    """Test SIAM login flow simulation."""
    
    def __init__(self):
        self.session_manager = SessionManager(Path('.'))
        self.results = {
            "sicon": {
                "page_load": False,
                "orcid_button_found": False,
                "orcid_redirect": False,
                "login_form_found": False
            },
            "sifin": {
                "page_load": False,
                "orcid_button_found": False,
                "orcid_redirect": False,
                "login_form_found": False
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
    
    def test_journal_login_flow(self, driver, journal_code, url):
        """Test login flow for a specific journal."""
        journal_results = self.results[journal_code.lower()]
        
        try:
            logger.info(f"🔍 Testing {journal_code} login flow...")
            
            # Step 1: Load the page
            driver.get(url)
            time.sleep(3)
            
            if journal_code.upper() in driver.title or journal_code.lower() in driver.current_url:
                journal_results["page_load"] = True
                logger.info(f"✅ {journal_code} page loaded successfully")
            else:
                logger.warning(f"⚠️  {journal_code} page may not have loaded correctly")
                
            # Step 2: Look for ORCID login elements more thoroughly
            orcid_selectors = [
                "//a[contains(@href, 'orcid')]",
                "//a[contains(text(), 'ORCID')]", 
                "//button[contains(text(), 'ORCID')]",
                "//input[contains(@value, 'ORCID')]",
                "//a[contains(@title, 'ORCID')]",
                "//a[contains(@class, 'orcid')]",
                "//div[contains(@class, 'orcid')]//a",
                "//span[contains(text(), 'ORCID')]/ancestor::a"
            ]
            
            orcid_element = None
            for selector in orcid_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements:
                        orcid_element = elements[0]
                        journal_results["orcid_button_found"] = True
                        logger.info(f"✅ {journal_code} ORCID login element found with selector: {selector}")
                        break
                except Exception:
                    continue
            
            if not orcid_element:
                logger.warning(f"⚠️  {journal_code} ORCID login element not found")
                
                # Save page source for debugging
                debug_file = Path(f"debug_output/{journal_code.lower()}_page_source.html")
                debug_file.parent.mkdir(exist_ok=True)
                with open(debug_file, 'w') as f:
                    f.write(driver.page_source)
                logger.info(f"📄 {journal_code} page source saved to {debug_file}")
                return
            
            # Step 3: Try to click ORCID button (without completing login)
            try:
                current_url = driver.current_url
                orcid_element.click()
                time.sleep(3)
                
                # Check if we were redirected (indicates button works)
                if driver.current_url != current_url:
                    journal_results["orcid_redirect"] = True
                    logger.info(f"✅ {journal_code} ORCID button redirected successfully")
                    
                    # Check if we're on ORCID login page
                    if "orcid.org" in driver.current_url:
                        # Look for ORCID login form
                        try:
                            login_form = driver.find_element(By.ID, "signin-form")
                            if login_form:
                                journal_results["login_form_found"] = True
                                logger.info(f"✅ {journal_code} ORCID login form found")
                        except:
                            try:
                                # Alternative selectors for ORCID login
                                username_field = driver.find_element(By.ID, "username")
                                password_field = driver.find_element(By.ID, "password")
                                if username_field and password_field:
                                    journal_results["login_form_found"] = True
                                    logger.info(f"✅ {journal_code} ORCID login fields found")
                            except:
                                logger.warning(f"⚠️  {journal_code} ORCID login form not found on redirect page")
                    
                else:
                    logger.warning(f"⚠️  {journal_code} ORCID button did not redirect")
                    
            except Exception as e:
                logger.warning(f"⚠️  {journal_code} Could not click ORCID button: {e}")
                
        except Exception as e:
            error_msg = f"{journal_code} login flow test failed: {str(e)}"
            self.results["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}")
    
    def run_test(self, headless=True):
        """Run comprehensive login flow test."""
        logger.info("🚀 Starting SIAM login flow test...")
        
        driver = None
        try:
            # Create driver
            driver = self.create_driver(headless)
            if not driver:
                return self.results
                
            # Test SICON login flow
            self.test_journal_login_flow(driver, "SICON", "https://mc.manuscriptcentral.com/sicon")
            
            # Test SIFIN login flow
            self.test_journal_login_flow(driver, "SIFIN", "https://mc.manuscriptcentral.com/sifin")
            
            # Save progress
            self.session_manager.auto_save_progress(
                "SIAM login flow test completed",
                learning=f"Login flow validation completed for SICON and SIFIN"
            )
            
        except Exception as e:
            error_msg = f"Login flow test failed: {str(e)}"
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
        print("🔐 SIAM LOGIN FLOW TEST SUMMARY")
        print("="*80)
        
        for journal in ["sicon", "sifin"]:
            results = self.results[journal]
            print(f"\n📊 {journal.upper()} Results:")
            print(f"   Page Load: {'✅ SUCCESS' if results['page_load'] else '❌ FAILED'}")
            print(f"   ORCID Button: {'✅ FOUND' if results['orcid_button_found'] else '❌ NOT FOUND'}")
            print(f"   ORCID Redirect: {'✅ SUCCESS' if results['orcid_redirect'] else '❌ FAILED'}")
            print(f"   Login Form: {'✅ FOUND' if results['login_form_found'] else '❌ NOT FOUND'}")
        
        if self.results["errors"]:
            print(f"\n❌ ERRORS ({len(self.results['errors'])}):")
            for i, error in enumerate(self.results["errors"], 1):
                print(f"   {i}. {error}")
        
        # Calculate overall success
        total_checks = 0
        passed_checks = 0
        
        for journal in ["sicon", "sifin"]:
            results = self.results[journal]
            for check in results.values():
                total_checks += 1
                if check:
                    passed_checks += 1
        
        success_rate = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
        
        print(f"\n📈 OVERALL SUCCESS RATE: {success_rate:.1f}% ({passed_checks}/{total_checks})")
        
        if success_rate >= 75:
            print("✅ LOGIN FLOW: Ready for credential testing!")
        elif success_rate >= 50:
            print("⚠️  LOGIN FLOW: Partially working, some issues to resolve")
        else:
            print("❌ LOGIN FLOW: Significant issues found")

def main():
    """Main test entry point."""
    tester = SIAMLoginFlowTester()
    
    print("🔐 Testing SIAM journal login flow (no actual credentials)")
    print("This will test ORCID button detection and redirect functionality...")
    
    # Run test
    results = tester.run_test(headless=True)
    
    # Print summary
    tester.print_summary()
    
    # Return exit code based on results
    total_journals = len(["sicon", "sifin"])
    successful_journals = sum(1 for journal in ["sicon", "sifin"] 
                            if results[journal]["orcid_button_found"])
    
    return 0 if successful_journals >= 1 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)