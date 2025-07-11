#!/usr/bin/env python3
"""
Debug why MOR/MF can't find Associate Editor Center in bulk tests
"""

from journals.mor import MORJournal
from journals.mf import MFJournal
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

def debug_ae_center_issue(journal_name, journal_class):
    """Debug Associate Editor Center navigation"""
    print(f"\n🔍 Debugging {journal_name} AE Center Issue")
    
    # Setup Chrome
    chrome_options = Options()
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print(f"1. Setting up {journal_name} journal...")
        journal = journal_class(driver)
        
        print(f"2. Logging in to {journal_name}...")
        journal.login()
        
        print("3. Waiting for page to stabilize...")
        time.sleep(5)
        
        # Save current page
        with open(f"{journal_name.lower()}_after_login_debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        driver.save_screenshot(f"{journal_name.lower()}_after_login_debug.png")
        
        print("4. Searching for Associate Editor Center links...")
        # Search for all links
        all_links = driver.find_elements(By.XPATH, "//a")
        ae_links = []
        
        for link in all_links:
            try:
                text = link.text.strip().lower()
                href = link.get_attribute("href") or ""
                if any(phrase in text for phrase in ["associate", "editor", "ae", "center", "centre"]):
                    ae_links.append({
                        "text": link.text.strip(),
                        "href": href,
                        "displayed": link.is_displayed()
                    })
            except:
                pass
        
        print(f"   Found {len(ae_links)} potential AE links:")
        for i, link in enumerate(ae_links):
            print(f"   {i+1}. Text: '{link['text']}' | Displayed: {link['displayed']} | Href: {link['href'][:50]}...")
        
        # Check if we're on a specific page
        current_url = driver.current_url
        page_title = driver.title
        print(f"\n5. Current page info:")
        print(f"   URL: {current_url}")
        print(f"   Title: {page_title}")
        
        # Check for any error messages or special states
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if "unrecognized" in page_text.lower():
            print("   ⚠️  Page contains 'unrecognized' - might be on device verification page")
        if "error" in page_text.lower():
            print("   ⚠️  Page contains 'error' text")
        
        # Try to find the AE center using the actual scraping logic
        print("\n6. Attempting to navigate using journal's scrape method...")
        try:
            journal.scrape_manuscripts_and_emails()
            print("   ✅ Successfully navigated to manuscripts!")
        except Exception as e:
            print(f"   ❌ Failed to navigate: {e}")
            
    except Exception as e:
        print(f"❌ Error during debug: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        driver.quit()

if __name__ == "__main__":
    # Test both journals
    debug_ae_center_issue("MOR", MORJournal)
    debug_ae_center_issue("MF", MFJournal)