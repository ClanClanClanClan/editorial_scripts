#!/usr/bin/env python3
"""
Test basic web access to SIAM journals without credentials.
This validates browser setup and basic navigation capabilities.
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

class SIAMWebAccessTester:
    """Test basic web access to SIAM journals."""
    
    def __init__(self):
        self.session_manager = SessionManager(Path('.'))
        self.results = {
            "browser_setup": False,
            "sicon_access": False, 
            "sifin_access": False,
            "orcid_button_found": {"sicon": False, "sifin": False},
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
            
            self.results["browser_setup"] = True
            logger.info("✅ Chrome WebDriver created successfully")
            return driver
            
        except Exception as e:
            error_msg = f"Failed to create Chrome driver: {str(e)}"
            self.results["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}")
            return None
    
    def test_sicon_access(self, driver):
        """Test basic access to SICON website."""
        try:
            logger.info("🔍 Testing SICON access...")
            
            url = "https://mc.manuscriptcentral.com/sicon"
            driver.get(url)
            time.sleep(3)
            
            # Check if page loaded
            if "SICON" in driver.title or "sicon" in driver.current_url:
                self.results["sicon_access"] = True
                logger.info("✅ SICON website accessible")
                
                # Look for ORCID login button
                try:
                    orcid_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'orcid') or contains(text(), 'ORCID')]")
                    if orcid_elements:
                        self.results["orcid_button_found"]["sicon"] = True
                        logger.info("✅ ORCID login button found on SICON")
                    else:
                        logger.info("⚠️  ORCID login button not immediately visible on SICON")
                        
                except Exception as e:
                    logger.warning(f"⚠️  Could not check for ORCID button on SICON: {e}")
                    
            else:
                error_msg = f"SICON page did not load correctly. Title: {driver.title}, URL: {driver.current_url}"
                self.results["errors"].append(error_msg)
                logger.error(f"❌ {error_msg}")
                
        except Exception as e:
            error_msg = f"Failed to access SICON: {str(e)}"
            self.results["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}")
    
    def test_sifin_access(self, driver):
        """Test basic access to SIFIN website."""
        try:
            logger.info("🔍 Testing SIFIN access...")
            
            url = "https://mc.manuscriptcentral.com/sifin"
            driver.get(url)
            time.sleep(3)
            
            # Check if page loaded
            if "SIFIN" in driver.title or "sifin" in driver.current_url:
                self.results["sifin_access"] = True
                logger.info("✅ SIFIN website accessible")
                
                # Look for ORCID login button
                try:
                    orcid_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'orcid') or contains(text(), 'ORCID')]")
                    if orcid_elements:
                        self.results["orcid_button_found"]["sifin"] = True
                        logger.info("✅ ORCID login button found on SIFIN")
                    else:
                        logger.info("⚠️  ORCID login button not immediately visible on SIFIN")
                        
                except Exception as e:
                    logger.warning(f"⚠️  Could not check for ORCID button on SIFIN: {e}")
                    
            else:
                error_msg = f"SIFIN page did not load correctly. Title: {driver.title}, URL: {driver.current_url}"
                self.results["errors"].append(error_msg)
                logger.error(f"❌ {error_msg}")
                
        except Exception as e:
            error_msg = f"Failed to access SIFIN: {str(e)}"
            self.results["errors"].append(error_msg)
            logger.error(f"❌ {error_msg}")
    
    def run_test(self, headless=True):
        """Run comprehensive web access test."""
        logger.info("🚀 Starting SIAM web access test...")
        
        driver = None
        try:
            # Create driver
            driver = self.create_driver(headless)
            if not driver:
                return self.results
                
            # Test SICON access
            self.test_sicon_access(driver)
            
            # Test SIFIN access  
            self.test_sifin_access(driver)
            
            # Save progress
            self.session_manager.auto_save_progress(
                "SIAM web access test completed",
                learning=f"Browser setup: {self.results['browser_setup']}, SICON: {self.results['sicon_access']}, SIFIN: {self.results['sifin_access']}"
            )
            
        except Exception as e:
            error_msg = f"Web access test failed: {str(e)}"
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
        print("🌐 SIAM WEB ACCESS TEST SUMMARY")
        print("="*80)
        
        print(f"🖥️  Browser Setup: {'✅ SUCCESS' if self.results['browser_setup'] else '❌ FAILED'}")
        print(f"📊 SICON Access: {'✅ SUCCESS' if self.results['sicon_access'] else '❌ FAILED'}")
        print(f"💰 SIFIN Access: {'✅ SUCCESS' if self.results['sifin_access'] else '❌ FAILED'}")
        
        print(f"\n🔐 ORCID Button Detection:")
        print(f"   SICON: {'✅ FOUND' if self.results['orcid_button_found']['sicon'] else '❌ NOT FOUND'}")
        print(f"   SIFIN: {'✅ FOUND' if self.results['orcid_button_found']['sifin'] else '❌ NOT FOUND'}")
        
        if self.results["errors"]:
            print(f"\n❌ ERRORS ({len(self.results['errors'])}):")
            for i, error in enumerate(self.results["errors"], 1):
                print(f"   {i}. {error}")
        
        # Overall status
        success_count = sum([
            self.results["browser_setup"],
            self.results["sicon_access"],
            self.results["sifin_access"]
        ])
        
        if success_count == 3:
            print(f"\n✅ OVERALL STATUS: SUCCESS - Ready for credential testing!")
            print("📋 Next step: Set ORCID credentials and run full debug script")
        elif success_count >= 2:
            print(f"\n⚠️  OVERALL STATUS: PARTIAL SUCCESS ({success_count}/3)")
            print("🔧 Some issues found but basic functionality working")
        else:
            print(f"\n❌ OVERALL STATUS: FAILED ({success_count}/3)")
            print("🚨 Critical issues need to be resolved")

def main():
    """Main test entry point."""
    tester = SIAMWebAccessTester()
    
    print("🧪 Testing SIAM journal web access (no credentials required)")
    print("This will validate browser setup and basic site connectivity...")
    
    # Run test
    results = tester.run_test(headless=True)
    
    # Print summary
    tester.print_summary()
    
    # Return exit code
    success_count = sum([
        results["browser_setup"],
        results["sicon_access"], 
        results["sifin_access"]
    ])
    
    return 0 if success_count >= 2 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)