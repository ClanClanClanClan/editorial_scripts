#!/usr/bin/env python3
"""
Test SICON authentication to identify the issue
"""

from journals.sicon import SICON
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_sicon_auth():
    """Test SICON authentication only"""
    print("=" * 60)
    print("TESTING SICON AUTHENTICATION")
    print("=" * 60)
    
    try:
        # Create and setup SICON
        sicon = SICON()
        sicon.setup_driver(headless=True)
        
        print("\n1. Testing authentication...")
        if sicon.authenticate():
            print("✅ Authentication successful!")
            
            # Quick test to see if we can access the dashboard
            print("\n2. Testing dashboard access...")
            try:
                # Try to find some basic elements
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                # Look for manuscript elements
                elements = sicon.driver.find_elements(By.TAG_NAME, "a")
                print(f"Found {len(elements)} links on page")
                
                # Check page title
                print(f"Page title: {sicon.driver.title}")
                print(f"Current URL: {sicon.driver.current_url}")
                
                return True
            except Exception as e:
                print(f"❌ Dashboard access failed: {e}")
                return False
        else:
            print("❌ Authentication failed")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        try:
            sicon.driver.quit()
        except:
            pass

if __name__ == "__main__":
    success = test_sicon_auth()
    print(f"\nSICON Authentication Result: {'SUCCESS' if success else 'FAILED'}")