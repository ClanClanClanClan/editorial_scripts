#!/usr/bin/env python3
"""
Debug MOR referee email extraction issue
"""

from journals.mor import MORJournal
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

def debug_mor_referee_extraction():
    """Debug why MOR can't extract referee emails"""
    print("🔍 Debugging MOR Referee Email Extraction")
    
    # Setup Chrome
    chrome_options = Options()
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print("1. Setting up MOR journal...")
        mor = MORJournal(driver)
        
        print("2. Logging in...")
        mor.login()
        
        print("3. Navigating to manuscripts...")
        # Wait for page to fully load after login
        time.sleep(5)
        
        # Save current page to debug
        with open("mor_after_device_verification.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        
        # Navigate to Associate Editor Center with wait
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        try:
            ae_link = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            time.sleep(3)
        except:
            print("   Failed to find 'Associate Editor Center' link")
            print("   Current URL:", driver.current_url)
            print("   Looking for alternative selectors...")
            # Try alternative selectors
            ae_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Associate Editor')]"))
            )
            ae_link.click()
            time.sleep(3)
        
        # Click on "Awaiting Reviewer Reports"
        status_link = driver.find_element(By.XPATH, "//a[contains(@href, 'Awaiting+Reviewer+Reports')]")
        status_link.click()
        time.sleep(3)
        
        print("4. Analyzing manuscript page structure...")
        
        # Save the page
        with open("mor_manuscript_page_debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        driver.save_screenshot("mor_manuscript_page_debug.png")
        
        # Look for all links that might contain referee information
        print("5. Searching for referee-related links...")
        
        # Check for referee links with various patterns
        patterns = [
            "//a[contains(@href, 'reviewer')]",
            "//a[contains(@href, 'REVIEWER')]",
            "//a[contains(@href, 'referee')]",
            "//a[contains(@href, 'REFEREE')]",
            "//a[contains(@onclick, 'reviewer')]",
            "//a[contains(@onclick, 'referee')]",
            "//a[contains(text(), 'View')]",
            "//a[contains(text(), 'Details')]",
            "//a[contains(text(), 'Profile')]",
            "//td[contains(@class, 'referee')]//a",
            "//td[contains(@class, 'reviewer')]//a"
        ]
        
        all_referee_links = []
        for pattern in patterns:
            try:
                links = driver.find_elements(By.XPATH, pattern)
                if links:
                    print(f"   Found {len(links)} links with pattern: {pattern}")
                    for link in links[:3]:  # Show first 3
                        text = link.text or "No text"
                        href = link.get_attribute("href") or "No href"
                        onclick = link.get_attribute("onclick") or "No onclick"
                        print(f"      - Text: '{text}', Href: {href[:50]}..., Onclick: {onclick[:50] if onclick != 'No onclick' else 'No onclick'}")
                    all_referee_links.extend(links)
            except:
                pass
        
        print(f"\n6. Total potential referee links found: {len(all_referee_links)}")
        
        # Look for email addresses directly in the page
        print("\n7. Searching for email addresses in page content...")
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        page_text = driver.find_element(By.TAG_NAME, "body").text
        emails = re.findall(email_pattern, page_text)
        print(f"   Found {len(emails)} email addresses in page: {emails}")
        
        # Check table structure
        print("\n8. Analyzing table structure...")
        tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"   Found {len(tables)} tables")
        
        for i, table in enumerate(tables[:3]):
            print(f"\n   Table {i+1}:")
            try:
                # Get headers
                headers = table.find_elements(By.XPATH, ".//th")
                if headers:
                    print(f"   Headers: {[h.text for h in headers[:5]]}")
                
                # Get first row
                rows = table.find_elements(By.XPATH, ".//tr")
                if len(rows) > 1:
                    cells = rows[1].find_elements(By.XPATH, ".//td")
                    print(f"   First row cells: {[c.text[:30] for c in cells[:5]]}")
            except:
                pass
        
    except Exception as e:
        print(f"❌ Error during debug: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        driver.quit()

if __name__ == "__main__":
    debug_mor_referee_extraction()