#!/usr/bin/env python3
"""
Explore SIAM sites after successful login to find manuscripts
"""

import os
import time
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup


def explore_siam_after_login():
    """Login and explore the page structure to find manuscripts."""
    
    # Setup browser
    chrome_options = Options()
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 30)
    
    # Create output directory
    output_dir = Path('./siam_exploration_' + datetime.now().strftime("%Y%m%d_%H%M%S"))
    output_dir.mkdir(exist_ok=True)
    
    try:
        print("🔐 Logging into SICON...")
        
        # Navigate to SICON
        driver.get("http://sicon.siam.org")
        time.sleep(3)
        
        # Remove cookie banners
        driver.execute_script("""
            var cookieElements = document.querySelectorAll('#cookie-policy-layer-bg, #cookie-policy-layer');
            cookieElements.forEach(function(el) { el.remove(); });
        """)
        time.sleep(1)
        
        # Click ORCID link
        orcid_link = driver.find_element(By.XPATH, "//a[contains(@href, 'orcid')]")
        driver.execute_script("arguments[0].click();", orcid_link)
        
        # Wait for ORCID page
        wait.until(lambda driver: 'orcid.org' in driver.current_url)
        time.sleep(2)
        
        # Fill credentials
        orcid_user = os.getenv("ORCID_USER")
        orcid_pass = os.getenv("ORCID_PASS")
        
        username_field = driver.find_element(By.ID, "username-input")
        driver.execute_script("arguments[0].value = arguments[1];", username_field, orcid_user)
        
        password_field = driver.find_element(By.ID, "password")
        driver.execute_script("arguments[0].value = arguments[1];", password_field, orcid_pass)
        
        # Submit
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        driver.execute_script("arguments[0].click();", submit_button)
        
        # Wait for redirect
        print("⏳ Waiting for authentication...")
        time.sleep(10)
        
        # Check if we're back on SICON
        current_url = driver.current_url
        print(f"📍 Current URL: {current_url}")
        
        if 'sicon.siam.org' in current_url:
            print("✅ Successfully authenticated!")
            
            # Take screenshot
            driver.save_screenshot(str(output_dir / "after_login.png"))
            
            # Analyze the page
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Save page source
            with open(output_dir / "page_source.html", 'w') as f:
                f.write(driver.page_source)
            
            print("\n📋 Page Analysis:")
            
            # Look for user info
            page_text = soup.get_text().lower()
            if 'dylan' in page_text or 'possamai' in page_text:
                print("✅ Found your name in the page")
            
            # Look for role indicators
            if 'associate editor' in page_text:
                print("✅ Found 'associate editor' text")
            if 'editor' in page_text:
                print("✅ Found 'editor' text")
            
            # Find all links
            print("\n🔗 Looking for manuscript-related links:")
            all_links = soup.find_all('a', href=True)
            manuscript_links = []
            
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Look for potential manuscript links
                if any(keyword in href.lower() for keyword in ['manuscript', 'ms', 'view', 'task', 'review']):
                    print(f"   📎 {text} -> {href}")
                    manuscript_links.append((text, href))
                
                # Look for links with manuscript IDs (starting with #)
                if text.startswith('#'):
                    print(f"   📄 {text} -> {href}")
                    manuscript_links.append((text, href))
            
            # Look for tables
            print("\n📊 Looking for tables:")
            tables = soup.find_all('table')
            print(f"   Found {len(tables)} tables")
            
            for i, table in enumerate(tables):
                # Check if table has manuscript-related content
                table_text = table.get_text().lower()
                if any(keyword in table_text for keyword in ['manuscript', 'title', 'author', 'referee']):
                    print(f"   Table {i+1} appears to contain manuscript data")
                    
                    # Save table HTML
                    with open(output_dir / f"table_{i+1}.html", 'w') as f:
                        f.write(str(table))
            
            # Look for specific sections
            print("\n📂 Looking for sections:")
            
            # Look for associate editor sections
            ae_sections = soup.find_all(['tbody', 'div'], attrs={'role': 'assoc_ed'})
            print(f"   Found {len(ae_sections)} associate editor sections")
            
            # Look for task sections
            task_elements = soup.find_all(class_='ndt_task')
            print(f"   Found {len(task_elements)} task elements")
            
            # Look for manuscript counts
            print("\n📊 Looking for manuscript counts:")
            text_content = soup.get_text()
            
            # Common patterns for manuscript counts
            import re
            patterns = [
                r'(\d+)\s*manuscript',
                r'(\d+)\s*paper',
                r'(\d+)\s*submission',
                r'total:\s*(\d+)',
                r'assigned:\s*(\d+)'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                if matches:
                    print(f"   Pattern '{pattern}' found: {matches}")
            
            # Try to find navigation links
            print("\n🧭 Looking for navigation links:")
            nav_keywords = ['dashboard', 'home', 'tasks', 'manuscripts', 'reviews', 'assignments']
            
            for link in all_links:
                text = link.get_text(strip=True).lower()
                if any(keyword in text for keyword in nav_keywords):
                    print(f"   🔗 {link.get_text(strip=True)} -> {link.get('href')}")
            
            print(f"\n📁 Analysis saved to: {output_dir}")
            
        else:
            print("❌ Not on SICON after authentication")
        
        input("\n⏸️  Browser is open. Explore manually and press Enter to close...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        driver.quit()


if __name__ == "__main__":
    explore_siam_after_login()