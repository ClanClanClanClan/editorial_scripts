#!/usr/bin/env python3
"""
Analyze SICON page structure to understand the login process
"""

from journals.sicon import SICON
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def analyze_sicon_page():
    """Analyze the SICON page structure"""
    print("=" * 60)
    print("ANALYZING SICON PAGE STRUCTURE")
    print("=" * 60)
    
    try:
        # Create and setup SICON
        sicon = SICON()
        sicon.setup_driver(headless=False)  # Use visible mode
        
        print("\n1. Navigating to SICON main page...")
        login_url = f"{sicon.config['base_url']}/cgi-bin/main.plex"
        print(f"URL: {login_url}")
        
        sicon.driver.get(login_url)
        time.sleep(3)
        
        print(f"Current URL: {sicon.driver.current_url}")
        print(f"Page title: {sicon.driver.title}")
        
        # Save page source for analysis
        page_source = sicon.driver.page_source
        with open('sicon_main_page.html', 'w') as f:
            f.write(page_source)
        print("Saved page source to sicon_main_page.html")
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(page_source, 'html.parser')
        
        print("\n2. Analyzing page structure...")
        
        # Look for login/authentication elements
        print("\n--- Authentication Elements ---")
        
        # Check for login forms
        forms = soup.find_all('form')
        print(f"Found {len(forms)} forms")
        for i, form in enumerate(forms):
            action = form.get('action', 'No action')
            method = form.get('method', 'No method')
            print(f"  Form {i+1}: action={action}, method={method}")
            
            # Check for inputs in this form
            inputs = form.find_all('input')
            for inp in inputs:
                name = inp.get('name', 'No name')
                type_attr = inp.get('type', 'No type')
                value = inp.get('value', 'No value')
                print(f"    Input: name={name}, type={type_attr}, value={value}")
        
        # Look for ORCID-related elements
        print("\n--- ORCID Elements ---")
        orcid_elements = soup.find_all(lambda tag: tag.name and ('orcid' in str(tag).lower()))
        print(f"Found {len(orcid_elements)} ORCID-related elements")
        for i, elem in enumerate(orcid_elements):
            print(f"  ORCID {i+1}: {elem.name} - {elem.get('href', elem.get('value', elem.text.strip()))}")
        
        # Look for login/signin/auth related text
        print("\n--- Login-related Text ---")
        login_keywords = ['login', 'sign in', 'signin', 'authenticate', 'auth', 'log in']
        all_text = soup.get_text().lower()
        for keyword in login_keywords:
            if keyword in all_text:
                print(f"  Found keyword: '{keyword}'")
        
        # Look for all links
        print("\n--- All Links ---")
        links = soup.find_all('a')
        print(f"Found {len(links)} links")
        for i, link in enumerate(links):
            href = link.get('href', 'No href')
            text = link.text.strip()
            if text:
                print(f"  Link {i+1}: {text} -> {href}")
        
        # Check if we're already authenticated
        print("\n--- Authentication Status ---")
        if 'logout' in all_text.lower():
            print("✅ 'Logout' found - might already be authenticated")
        else:
            print("❌ No 'Logout' found - likely not authenticated")
        
        # Look for manuscript/editorial elements
        print("\n--- Editorial Elements ---")
        editorial_keywords = ['manuscript', 'paper', 'submission', 'review', 'referee', 'editor']
        for keyword in editorial_keywords:
            if keyword in all_text.lower():
                print(f"  Found keyword: '{keyword}'")
        
        # Look for table elements (manuscripts might be in tables)
        tables = soup.find_all('table')
        print(f"\nFound {len(tables)} tables")
        for i, table in enumerate(tables):
            rows = table.find_all('tr')
            print(f"  Table {i+1}: {len(rows)} rows")
            if rows:
                # Show first row as header
                first_row = rows[0]
                cells = first_row.find_all(['th', 'td'])
                if cells:
                    headers = [cell.text.strip() for cell in cells]
                    print(f"    Headers: {headers}")
        
        input("Press Enter to continue...")
            
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
    analyze_sicon_page()