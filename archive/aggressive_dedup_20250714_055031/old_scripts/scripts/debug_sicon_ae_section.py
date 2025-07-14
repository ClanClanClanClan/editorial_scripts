#!/usr/bin/env python3
"""
Debug SICON Associate Editor section to find the correct structure
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

def debug_sicon_ae_section():
    """Debug SICON Associate Editor section"""
    print("🔍 Debugging SICON Associate Editor section...")
    
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
        
        # Enter credentials
        username_field = driver.find_element(By.CSS_SELECTOR, 'input[placeholder*="Email"]')
        username_field.clear()
        username_field.send_keys(os.environ['ORCID_EMAIL'])
        
        password_field = driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')
        password_field.clear()
        password_field.send_keys(os.environ['ORCID_PASSWORD'])
        
        submit_btn = driver.find_element(By.CSS_SELECTOR, 'input[type="submit"]')
        submit_btn.click()
        
        time.sleep(10)
        print("✅ Authentication complete")
        
        # Save the authenticated page for analysis
        with open('sicon_ae_debug.html', 'w') as f:
            f.write(driver.page_source)
        print("💾 Saved page as sicon_ae_debug.html")
        
        # Analyze the page structure
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        print("\n🔍 Looking for Associate Editor section...")
        
        # Strategy 1: Find by text content
        ae_texts = soup.find_all(string=re.compile(r'Associate Editor', re.IGNORECASE))
        print(f"Found {len(ae_texts)} 'Associate Editor' text references")
        
        # Strategy 2: Find by role attribute  
        ae_roles = soup.find_all(attrs={'role': re.compile(r'assoc.*ed', re.IGNORECASE)})
        print(f"Found {len(ae_roles)} elements with assoc_ed role")
        
        # Strategy 3: Look for the specific categories mentioned by user
        target_categories = [
            'Awaiting Referee Assignment',
            'Under Review', 
            'Awaiting Associate Editor Recommendation',
            'All Pending Manuscripts',
            'Waiting for Revision'
        ]
        
        print(f"\n🎯 Looking for specific categories...")
        for category in target_categories:
            # Look for exact matches
            exact_matches = soup.find_all(string=re.compile(category, re.IGNORECASE))
            print(f"  {category}: {len(exact_matches)} exact matches")
            
            # Look for links containing category
            link_matches = soup.find_all('a', string=re.compile(category, re.IGNORECASE))
            print(f"  {category}: {len(link_matches)} link matches")
            
            if link_matches:
                for link in link_matches[:3]:  # First 3
                    text = link.get_text().strip()
                    href = link.get('href', 'No href')
                    print(f"    - '{text}' -> {href}")
        
        print(f"\n🔍 Looking for '4 AE' pattern (Under Review 4 AE)...")
        ae_count_matches = soup.find_all(string=re.compile(r'\d+\s*AE'))
        print(f"Found {len(ae_count_matches)} elements with 'X AE' pattern:")
        for match in ae_count_matches:
            print(f"  - '{match.strip()}'")
        
        print(f"\n🔍 Searching for tbody with role='assoc_ed'...")
        assoc_ed_tbody = soup.find_all('tbody', {'class': re.compile(r'desktop-section'), 'role': 'assoc_ed'})
        print(f"Found {len(assoc_ed_tbody)} assoc_ed tbody sections")
        
        if assoc_ed_tbody:
            print("📋 Analyzing Associate Editor tbody section...")
            ae_section = assoc_ed_tbody[0]
            
            # Find all links in this section
            ae_links = ae_section.find_all('a')
            print(f"Found {len(ae_links)} links in AE section:")
            
            for i, link in enumerate(ae_links):
                text = link.get_text().strip()
                href = link.get('href', '')
                print(f"  {i+1}. '{text}' -> {href}")
                
                # Check if this matches our target categories
                for category in target_categories:
                    if category.lower() in text.lower():
                        print(f"     ⭐ MATCHES: {category}")
        
        print(f"\n🔍 Looking for 'Under Review' specifically...")
        under_review_elements = soup.find_all(string=re.compile(r'Under Review.*\d+.*AE', re.IGNORECASE))
        print(f"Found {len(under_review_elements)} 'Under Review X AE' elements:")
        for elem in under_review_elements:
            print(f"  - '{elem.strip()}'")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    debug_sicon_ae_section()