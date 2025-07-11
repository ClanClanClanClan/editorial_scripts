#!/usr/bin/env python3
"""
Debug SICON post-authentication page structure
"""

from journals.sicon import SICON
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def debug_sicon_post_auth():
    """Debug what the SICON page looks like after authentication"""
    print("=" * 60)
    print("DEBUGGING SICON POST-AUTHENTICATION PAGE")
    print("=" * 60)
    
    try:
        # Create and setup SICON
        sicon = SICON()
        sicon.setup_driver(headless=False)  # Use visible mode
        
        print("\n1. Authenticating...")
        if not sicon.authenticate():
            print("❌ Authentication failed")
            return False
        
        print("✅ Authentication successful!")
        
        print(f"\n2. Post-authentication page analysis:")
        print(f"   Current URL: {sicon.driver.current_url}")
        print(f"   Page title: {sicon.driver.title}")
        
        # Save page source for analysis
        page_source = sicon.driver.page_source
        with open('sicon_post_auth_page.html', 'w') as f:
            f.write(page_source)
        print("   Saved page source to sicon_post_auth_page.html")
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(page_source, 'html.parser')
        
        print("\n3. Looking for manuscript/folder navigation...")
        
        # Check for folder links
        folder_links = soup.find_all('a', href=lambda x: x and 'folder_link' in x)
        print(f"   Found {len(folder_links)} folder links:")
        for i, link in enumerate(folder_links):
            href = link.get('href')
            text = link.text.strip()
            print(f"     {i+1}. {text} -> {href}")
        
        # Check for any manuscript-related links
        manuscript_keywords = ['manuscript', 'ms_id', 'paper', 'submission', 'review']
        manuscript_links = []
        all_links = soup.find_all('a')
        
        for link in all_links:
            href = link.get('href', '')
            text = link.text.strip()
            if any(keyword in href.lower() or keyword in text.lower() for keyword in manuscript_keywords):
                manuscript_links.append((text, href))
        
        print(f"\n   Found {len(manuscript_links)} manuscript-related links:")
        for i, (text, href) in enumerate(manuscript_links):
            print(f"     {i+1}. {text} -> {href}")
        
        # Look for tables
        tables = soup.find_all('table')
        print(f"\n   Found {len(tables)} tables")
        for i, table in enumerate(tables):
            rows = table.find_all('tr')
            print(f"     Table {i+1}: {len(rows)} rows")
            if rows:
                # Show first few rows
                for j, row in enumerate(rows[:3]):
                    cells = row.find_all(['th', 'td'])
                    cell_texts = [cell.text.strip() for cell in cells if cell.text.strip()]
                    if cell_texts:
                        print(f"       Row {j+1}: {cell_texts}")
        
        # Check for any navigation or menu items
        print("\n4. Navigation elements:")
        
        # Look for common navigation patterns
        nav_elements = soup.find_all(['nav', 'ul', 'ol'])
        for i, nav in enumerate(nav_elements):
            if nav.find('a'):  # Only show navs with links
                links = nav.find_all('a')
                print(f"   Navigation {i+1}: {len(links)} links")
                for link in links[:5]:  # Show first 5 links
                    text = link.text.strip()
                    href = link.get('href', '')
                    if text:
                        print(f"     - {text} -> {href}")
        
        # Check for forms
        forms = soup.find_all('form')
        print(f"\n   Found {len(forms)} forms")
        for i, form in enumerate(forms):
            action = form.get('action', 'No action')
            method = form.get('method', 'GET')
            print(f"     Form {i+1}: {method} {action}")
        
        # Check for any error messages
        error_keywords = ['error', 'warning', 'alert', 'message']
        page_text = soup.get_text().lower()
        for keyword in error_keywords:
            if keyword in page_text:
                print(f"\n   ⚠️  Found '{keyword}' in page text")
        
        input("Press Enter to continue...")
        
        return True
            
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
    success = debug_sicon_post_auth()
    print(f"\nSICON Post-Auth Debug Result: {'SUCCESS' if success else 'FAILED'}")