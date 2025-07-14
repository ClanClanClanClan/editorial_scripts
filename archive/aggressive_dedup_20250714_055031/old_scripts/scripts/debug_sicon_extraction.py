#!/usr/bin/env python3
"""
Debug SICON extraction to see why it's not finding manuscripts
"""

import os
import sys
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

def debug_sicon_extraction():
    """Debug SICON manuscript extraction"""
    print("🔍 Debugging SICON manuscript extraction...")
    
    # Set credentials
    os.environ['ORCID_EMAIL'] = 'dylan.possamai@polytechnique.org'
    os.environ['ORCID_PASSWORD'] = 'Hioupy0042%'
    
    # Setup driver
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 30)
    
    try:
        print("🌐 Navigating to SICON...")
        driver.get("http://sicon.siam.org/cgi-bin/main.plex")
        
        # Handle Cloudflare
        page_source = driver.page_source.lower()
        if 'cloudflare' in page_source or 'verifying you are human' in page_source:
            print("🛡️ Cloudflare detected - waiting 60 seconds...")
            time.sleep(60)
        
        # Authenticate
        print("🔐 Authenticating...")
        orcid_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href*="orcid"]')))
        driver.execute_script("arguments[0].click();", orcid_element)
        time.sleep(5)
        
        # Enter credentials with multiple selectors (same as working SIFIN approach)
        username_selectors = [
            'input[name="userId"]',
            'input[id="username"]',
            'input[placeholder*="email"]',
            'input[placeholder*="Email"]'
        ]
        
        for selector in username_selectors:
            try:
                username_field = driver.find_element(By.CSS_SELECTOR, selector)
                if username_field:
                    username_field.clear()
                    username_field.send_keys(os.environ['ORCID_EMAIL'])
                    print("✅ Username entered")
                    break
            except:
                continue
        
        password_selectors = [
            'input[name="password"]',
            'input[type="password"]',
            'input[placeholder*="password"]'
        ]
        
        for selector in password_selectors:
            try:
                password_field = driver.find_element(By.CSS_SELECTOR, selector)
                if password_field:
                    password_field.clear()
                    password_field.send_keys(os.environ['ORCID_PASSWORD'])
                    print("✅ Password entered")
                    break
            except:
                continue
        
        submit_selectors = [
            'input[type="submit"]',
            'button[type="submit"]',
            'button:contains("Sign in")',
            '#signin-button'
        ]
        
        for selector in submit_selectors:
            try:
                submit_btn = driver.find_element(By.CSS_SELECTOR, selector)
                if submit_btn:
                    submit_btn.click()
                    print("✅ Login form submitted")
                    break
            except:
                continue
        
        time.sleep(10)
        print("✅ Authentication complete")
        
        # Debug: Save current page
        with open('sicon_debug_page.html', 'w') as f:
            f.write(driver.page_source)
        print("💾 Saved current page as sicon_debug_page.html")
        
        # Look for manuscripts with different strategies
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        print("\n🔍 Strategy 1: Looking for M### patterns...")
        manuscript_patterns = soup.find_all(string=re.compile(r'M\d+'))
        print(f"Found {len(manuscript_patterns)} M### patterns:")
        for i, pattern in enumerate(manuscript_patterns[:10]):
            print(f"  {i+1}. {pattern.strip()[:100]}")
        
        print("\n🔍 Strategy 2: Looking for manuscript-related elements...")
        manuscript_elements = soup.find_all(['a', 'tr', 'td'], string=re.compile(r'M\d+'))
        print(f"Found {len(manuscript_elements)} manuscript elements:")
        for i, elem in enumerate(manuscript_elements[:10]):
            print(f"  {i+1}. {elem.name}: {elem.get_text().strip()[:100]}")
        
        print("\n🔍 Strategy 3: Looking for links containing manuscript IDs...")
        links = soup.find_all('a', href=True)
        manuscript_links = [link for link in links if re.search(r'M\d+', str(link.get('href', '')))]
        print(f"Found {len(manuscript_links)} manuscript links:")
        for i, link in enumerate(manuscript_links[:10]):
            print(f"  {i+1}. {link.get('href')} - {link.get_text().strip()[:50]}")
        
        print("\n🔍 Strategy 4: Looking for table rows with manuscript data...")
        tables = soup.find_all('table')
        print(f"Found {len(tables)} tables on page")
        
        manuscript_rows = []
        for table_idx, table in enumerate(tables):
            rows = table.find_all('tr')
            for row_idx, row in enumerate(rows):
                if re.search(r'M\d+', row.get_text()):
                    manuscript_rows.append((table_idx, row_idx, row.get_text().strip()[:100]))
        
        print(f"Found {len(manuscript_rows)} table rows with manuscripts:")
        for i, (table_idx, row_idx, text) in enumerate(manuscript_rows[:10]):
            print(f"  {i+1}. Table {table_idx}, Row {row_idx}: {text}")
        
        print("\n🔍 Strategy 5: Looking for any text containing 'manuscript'...")
        manuscript_text = soup.find_all(string=re.compile(r'manuscript', re.IGNORECASE))
        print(f"Found {len(manuscript_text)} references to 'manuscript':")
        for i, text in enumerate(manuscript_text[:5]):
            print(f"  {i+1}. {text.strip()[:100]}")
        
        # Check if we need to navigate somewhere
        print("\n🔍 Strategy 6: Looking for navigation elements...")
        nav_elements = soup.find_all('a', string=re.compile(r'manuscripts?|folder|submissions?', re.IGNORECASE))
        print(f"Found {len(nav_elements)} potential navigation elements:")
        for i, elem in enumerate(nav_elements[:10]):
            print(f"  {i+1}. {elem.get_text().strip()} -> {elem.get('href', 'No href')}")
        
        # Try clicking on manuscript-related navigation
        if nav_elements:
            print(f"\n🖱️ Trying to click on navigation element...")
            try:
                nav_elem = nav_elements[0]
                href = nav_elem.get('href')
                if href:
                    if href.startswith('http'):
                        driver.get(href)
                    else:
                        driver.get(f"http://sicon.siam.org{href}")
                    
                    time.sleep(5)
                    
                    # Re-analyze after navigation
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    manuscript_elements = soup.find_all(['a', 'tr', 'td'], string=re.compile(r'M\d+'))
                    print(f"After navigation: Found {len(manuscript_elements)} manuscript elements")
                    
                    for i, elem in enumerate(manuscript_elements[:10]):
                        print(f"  {i+1}. {elem.get_text().strip()[:100]}")
            except Exception as e:
                print(f"❌ Navigation failed: {e}")
        
        # Save final page
        with open('sicon_debug_final.html', 'w') as f:
            f.write(driver.page_source)
        print("💾 Saved final page as sicon_debug_final.html")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    debug_sicon_extraction()