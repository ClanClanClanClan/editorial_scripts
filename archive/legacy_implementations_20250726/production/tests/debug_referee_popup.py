#!/usr/bin/env python3
"""
Debug script to test referee popup extraction
"""

import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# Add parent directory to path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.secure_credentials import SecureCredentialManager

def test_referee_popup():
    """Test referee popup extraction with detailed debugging"""
    
    # Setup Chrome with visible window for debugging
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    # Not headless so we can see what's happening
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    
    try:
        # Load credentials
        creds = SecureCredentialManager()
        email, password = creds.load_credentials()
        
        # Login
        print("🔐 Logging in...")
        driver.get("https://mc.manuscriptcentral.com/mafi")
        time.sleep(3)
        
        # Login
        driver.find_element(By.ID, "USERID").send_keys(email)
        driver.find_element(By.ID, "PASSWORD").send_keys(password)
        driver.execute_script("document.getElementById('logInButton').click();")
        time.sleep(5)
        
        # Navigate to AE center
        print("🏠 Navigating to AE Center...")
        ae_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Associate Editor Center')]")
        ae_link.click()
        time.sleep(3)
        
        # Find a manuscript with referees
        print("📄 Finding manuscripts...")
        manuscript_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'CURRENT_STAGE_ID=')]")
        
        if not manuscript_links:
            print("❌ No manuscripts found!")
            return
            
        # Click first manuscript
        print(f"📄 Opening first manuscript...")
        manuscript_links[0].click()
        time.sleep(3)
        
        # Look for referee table
        print("🔍 Looking for referee table...")
        referee_rows = driver.find_elements(By.XPATH, "//td[@class='tablelines']//tr[td[@class='tablelightcolor'] and .//a[contains(@href,'mailpopup')]]")
        
        print(f"Found {len(referee_rows)} referee rows")
        
        if not referee_rows:
            print("❌ No referee rows found!")
            # Save page source for debugging
            with open("debug_no_referees_page.html", "w") as f:
                f.write(driver.page_source)
            return
            
        # Test first referee
        print("\n🧪 Testing first referee popup...")
        row = referee_rows[0]
        
        # Find the link
        name_link = row.find_element(By.XPATH, ".//a[contains(@href,'mailpopup')]")
        referee_name = name_link.text.strip()
        print(f"   Referee name: {referee_name}")
        
        # Check link attributes
        href = name_link.get_attribute('href')
        onclick = name_link.get_attribute('onclick')
        print(f"   href: {href[:100]}...")
        print(f"   onclick: {onclick[:100] if onclick else 'None'}...")
        
        # Store current window
        main_window = driver.current_window_handle
        initial_windows = driver.window_handles
        print(f"   Initial windows: {len(initial_windows)}")
        
        # Try to open popup
        print("   Clicking referee link...")
        if href and href.startswith('javascript:'):
            # Execute the JavaScript
            js_code = href.replace('javascript:', '').strip()
            print(f"   Executing: {js_code[:100]}...")
            driver.execute_script(js_code)
        else:
            name_link.click()
            
        # Wait for popup
        time.sleep(3)
        
        # Check for new window
        current_windows = driver.window_handles
        print(f"   Current windows: {len(current_windows)}")
        
        if len(current_windows) > len(initial_windows):
            print("   ✅ Popup opened!")
            
            # Switch to popup
            driver.switch_to.window(current_windows[-1])
            
            # Debug popup content
            print("\n   📧 Analyzing popup content...")
            
            # Check for frames
            frames = driver.find_elements(By.TAG_NAME, "frame")
            print(f"   Frames found: {len(frames)}")
            
            if frames:
                # Try each frame
                for i, frame in enumerate(frames):
                    try:
                        driver.switch_to.frame(frame)
                        print(f"\n   Frame {i}:")
                        
                        # Look for email fields
                        email_fields = driver.find_elements(By.XPATH, "//input[@name='EMAIL_TEMPLATE_TO']")
                        if email_fields:
                            email_value = email_fields[0].get_attribute('value')
                            print(f"      ✅ EMAIL_TEMPLATE_TO found: {email_value}")
                        
                        # Look for any email in the frame
                        body_text = driver.find_element(By.TAG_NAME, "body").text
                        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', body_text)
                        if emails:
                            print(f"      Emails found in frame: {emails}")
                        
                        # Switch back to popup window
                        driver.switch_to.default_content()
                        
                    except Exception as e:
                        print(f"      Error in frame {i}: {e}")
                        driver.switch_to.default_content()
            else:
                # No frames, check main popup
                print("   No frames, checking main window...")
                
                # Save popup HTML
                with open("debug_popup_content.html", "w") as f:
                    f.write(driver.page_source)
                
                # Look for emails
                body_text = driver.find_element(By.TAG_NAME, "body").text
                emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', body_text)
                print(f"   Emails found: {emails}")
            
            # Close popup
            driver.close()
            driver.switch_to.window(main_window)
            
        else:
            print("   ❌ No popup opened!")
            print("   Checking if email is in onclick...")
            
            # Try to extract email from onclick/href
            if onclick:
                email_match = re.search(r"mailpopup\('([^']+)'", onclick)
                if email_match:
                    print(f"   ✅ Email found in onclick: {email_match.group(1)}")
        
        print("\n✅ Debug complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        input("\n⏸️  Press Enter to close browser...")
        driver.quit()

if __name__ == "__main__":
    test_referee_popup()