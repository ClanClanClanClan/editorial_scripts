#!/usr/bin/env python3
"""
Test the corrected SIAM URLs directly.
"""

import sys
import time
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from editorial_assistant.utils.session_manager import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CorrectedSIAMURLTester:
    """Test corrected SIAM URLs."""
    
    def __init__(self):
        self.session_manager = SessionManager(Path('.'))
        self.results = {
            "sicon": {
                "url_accessible": False,
                "login_form_found": False,
                "orcid_button_found": False,
                "final_url": "",
                "page_title": ""
            },
            "sifin": {
                "url_accessible": False,
                "login_form_found": False,
                "orcid_button_found": False,
                "final_url": "",
                "page_title": ""
            },
            "errors": []
        }
        
    def create_driver(self, headless=True):
        """Create Chrome driver."""
        try:
            chrome_options = Options()
            if headless:
                chrome_options.add_argument("--headless")
            
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            
            logger.info("✅ Chrome WebDriver created")
            return driver
            
        except Exception as e:
            error_msg = f"Failed to create Chrome driver: {str(e)}"
            self.results["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}")
            return None
    
    def test_siam_url(self, driver, journal_code, url):
        """Test a specific SIAM URL."""
        journal_results = self.results[journal_code.lower()]
        
        try:
            logger.info(f"🔍 Testing {journal_code} URL: {url}")
            
            # Navigate to URL
            driver.get(url)
            time.sleep(3)
            
            # Check if page loaded successfully
            current_url = driver.current_url
            page_title = driver.title
            page_source = driver.page_source.lower()
            
            journal_results["final_url"] = current_url
            journal_results["page_title"] = page_title
            
            # Check for error pages
            if "not found" in page_title.lower() or "error" in page_title.lower():
                logger.warning(f"⚠️  {journal_code} URL returned error page: {page_title}")
                journal_results["url_accessible"] = False
            else:
                journal_results["url_accessible"] = True
                logger.info(f"✅ {journal_code} URL accessible: {page_title}")
            
            # Look for login indicators
            login_indicators = ["login", "sign in", "user", "password", "submit"]
            for indicator in login_indicators:
                if indicator in page_source:
                    journal_results["login_form_found"] = True
                    logger.info(f"✅ {journal_code} login elements detected")
                    break
            
            # Look for ORCID elements
            orcid_selectors = [
                "//a[contains(@href, 'orcid')]",
                "//a[contains(text(), 'ORCID')]", 
                "//button[contains(text(), 'ORCID')]",
                "//input[contains(@value, 'ORCID')]",
                "//img[contains(@src, 'orcid')]",
                "//*[contains(text(), 'ORCID')]"
            ]
            
            for selector in orcid_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements:
                        journal_results["orcid_button_found"] = True
                        logger.info(f"✅ {journal_code} ORCID element found: '{elements[0].text}'")
                        break
                except Exception:
                    continue
            
            # Save debug info
            debug_file = Path(f"debug_output/{journal_code.lower()}_corrected_url_source.html")
            debug_file.parent.mkdir(exist_ok=True)
            with open(debug_file, 'w') as f:
                f.write(driver.page_source)
            logger.info(f"📄 {journal_code} page source saved to {debug_file}")
            
            try:
                screenshot_file = Path(f"debug_output/{journal_code.lower()}_corrected_url_screenshot.png")
                driver.save_screenshot(str(screenshot_file))
                logger.info(f"📸 {journal_code} screenshot saved to {screenshot_file}")
            except Exception as e:
                logger.warning(f"⚠️  Could not save screenshot: {e}")
                
        except Exception as e:
            error_msg = f"{journal_code} URL test failed: {str(e)}"
            self.results["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}")
    
    def run_test(self, headless=True):
        """Run URL test."""
        logger.info("🚀 Starting corrected SIAM URL test...")
        
        driver = None
        try:
            driver = self.create_driver(headless)
            if not driver:
                return self.results
                
            # Test corrected URLs
            self.test_siam_url(driver, "SICON", "http://sicon.siam.org")
            time.sleep(2)
            self.test_siam_url(driver, "SIFIN", "http://sifin.siam.org")
            
            # Save progress
            self.session_manager.auto_save_progress(
                "Corrected SIAM URL test completed",
                learning=f"Tested correct SIAM URLs: sicon.siam.org and sifin.siam.org"
            )
            
        except Exception as e:
            error_msg = f"URL test failed: {str(e)}"
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
        print("🌐 CORRECTED SIAM URL TEST SUMMARY")
        print("="*80)
        
        for journal in ["sicon", "sifin"]:
            results = self.results[journal]
            print(f"\n📊 {journal.upper()} Results:")
            print(f"   URL Accessible: {'✅ SUCCESS' if results['url_accessible'] else '❌ FAILED'}")
            print(f"   Login Form: {'✅ FOUND' if results['login_form_found'] else '❌ NOT FOUND'}")
            print(f"   ORCID Button: {'✅ FOUND' if results['orcid_button_found'] else '❌ NOT FOUND'}")
            print(f"   Page Title: {results['page_title']}")
            print(f"   Final URL: {results['final_url']}")
        
        if self.results["errors"]:
            print(f"\n❌ ERRORS ({len(self.results['errors'])}):")
            for i, error in enumerate(self.results["errors"], 1):
                print(f"   {i}. {error}")
        
        # Calculate success metrics
        accessible_count = sum(1 for journal in ["sicon", "sifin"] 
                              if self.results[journal]["url_accessible"])
        orcid_found_count = sum(1 for journal in ["sicon", "sifin"] 
                               if self.results[journal]["orcid_button_found"])
        
        print(f"\n📈 SUCCESS METRICS:")
        print(f"   URLs Accessible: {accessible_count}/2")
        print(f"   ORCID Buttons Found: {orcid_found_count}/2")
        
        if accessible_count == 2 and orcid_found_count >= 1:
            print("\n✅ SUCCESS! READY FOR CREDENTIAL TESTING")
        elif accessible_count == 2:
            print("\n⚠️  URLs WORK BUT ORCID DETECTION NEEDS WORK")
        else:
            print("\n❌ URL ISSUES PERSIST")

def main():
    """Main test entry point."""
    tester = CorrectedSIAMURLTester()
    
    print("🌐 Testing corrected SIAM URLs")
    print("SICON: http://sicon.siam.org")
    print("SIFIN: http://sifin.siam.org")
    
    # Run test
    results = tester.run_test(headless=True)
    
    # Print summary
    tester.print_summary()
    
    # Return exit code
    accessible_count = sum(1 for journal in ["sicon", "sifin"] 
                          if results[journal]["url_accessible"])
    
    return 0 if accessible_count >= 1 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)