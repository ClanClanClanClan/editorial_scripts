#!/usr/bin/env python3
"""Direct MF extraction bypassing all cache systems."""

import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import json

# Load credentials
os.environ['MF_EMAIL'] = os.environ.get('MF_EMAIL', '')
os.environ['MF_PASSWORD'] = os.environ.get('MF_PASSWORD', '')

print(f"🚀 DIRECT MF EXTRACTION - {datetime.now().strftime('%H:%M:%S')}")
print("=" * 60)

# Setup Chrome
chrome_options = Options()
if os.environ.get('EXTRACTOR_HEADLESS', 'true').lower() == 'true':
    chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--window-size=1200,800')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

driver = webdriver.Chrome(options=chrome_options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

manuscripts = []

try:
    # Navigate to MF
    print("🔐 Logging in...")
    driver.get('https://mc.manuscriptcentral.com/mafi')
    time.sleep(5)
    
    # Check page source
    if 'cloudflare' in driver.page_source.lower():
        print("⚠️ Cloudflare challenge detected")
        with open('cloudflare_page.html', 'w') as f:
            f.write(driver.page_source)
    
    # Try login
    try:
        username_field = driver.find_element(By.NAME, 'USER')
        password_field = driver.find_element(By.NAME, 'PASSWORD')
        
        username_field.send_keys(os.environ['MF_EMAIL'])
        password_field.send_keys(os.environ['MF_PASSWORD'])
        
        submit_button = driver.find_element(By.XPATH, "//input[@type='submit']")
        submit_button.click()
        
        time.sleep(5)
        
        if "Associate Editor Center" in driver.page_source:
            print("✅ Login successful!")
            
            # Navigate to AE Center
            ae_link = driver.find_element(By.LINK_TEXT, 'Associate Editor Center')
            ae_link.click()
            time.sleep(3)
            
            # Get categories
            category_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'AUTHOR_SUBMIT_CHECK')]")
            categories = []
            
            for link in category_links:
                text = link.text.strip()
                if '(' in text and ')' in text:
                    name_part = text[:text.rfind('(')].strip()
                    count_part = text[text.rfind('(')+1:text.rfind(')')].strip()
                    try:
                        count = int(count_part)
                        categories.append({'name': name_part, 'count': count})
                    except:
                        continue
            
            print(f"📂 Found {len(categories)} categories:")
            for cat in categories:
                print(f"  - {cat['name']} ({cat['count']} manuscripts)")
            
            # Process first category with manuscripts
            for cat in categories:
                if cat['count'] > 0:
                    print(f"\n📄 Processing {cat['name']}...")
                    
                    # Click category
                    cat_link = driver.find_element(By.PARTIAL_LINK_TEXT, cat['name'])
                    cat_link.click()
                    time.sleep(3)
                    
                    # Get first manuscript
                    ms_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS')]")
                    if ms_links:
                        print(f"  Found {len(ms_links)} manuscripts")
                        
                        # Click first manuscript
                        ms_links[0].click()
                        time.sleep(5)
                        
                        # Extract manuscript ID
                        url = driver.current_url
                        ms_id = url.split('MANUSCRIPT_ID=')[1].split('&')[0] if 'MANUSCRIPT_ID=' in url else 'UNKNOWN'
                        
                        print(f"  Extracting manuscript {ms_id}...")
                        
                        manuscript = {'id': ms_id, 'referees': [], 'authors': []}
                        
                        # Extract title
                        try:
                            title_elements = driver.find_elements(By.XPATH, "//td[contains(text(), 'Title:')]/following-sibling::td")
                            if title_elements:
                                manuscript['title'] = title_elements[0].text.strip()
                                print(f"  Title: {manuscript['title'][:50]}...")
                        except:
                            pass
                        
                        # Extract referees
                        referee_rows = driver.find_elements(By.XPATH, "//select[contains(@name, 'ORDER')]/ancestor::tr[1]")
                        print(f"  Found {len(referee_rows)} referees")
                        
                        for i, row in enumerate(referee_rows[:3]):  # First 3 referees
                            try:
                                cells = row.find_elements(By.XPATH, ".//td[@class='tablelightcolor']")
                                if len(cells) > 1:
                                    name_cell = cells[1]
                                    name_links = name_cell.find_elements(By.XPATH, './/a')
                                    
                                    referee = {'name': '', 'email': ''}
                                    
                                    for link in name_links:
                                        link_text = link.text.strip()
                                        if link_text and ',' in link_text:
                                            referee['name'] = link_text
                                            
                                        href = link.get_attribute('href') or ''
                                        onclick = link.get_attribute('onclick') or ''
                                        
                                        if 'mailpopup' in href or 'mailpopup' in onclick:
                                            print(f"    Testing referee {i+1} email extraction...")
                                            
                                            # Try to extract email from popup
                                            original_window = driver.current_window_handle
                                            try:
                                                driver.execute_script("arguments[0].click();", link)
                                                time.sleep(2)
                                                
                                                # Switch to popup
                                                for window in driver.window_handles:
                                                    if window != original_window:
                                                        driver.switch_to.window(window)
                                                        time.sleep(1)
                                                        
                                                        # Check frames
                                                        frames = driver.find_elements(By.TAG_NAME, 'frame')
                                                        if not frames:
                                                            frames = driver.find_elements(By.TAG_NAME, 'iframe')
                                                        
                                                        for frame in frames:
                                                            try:
                                                                driver.switch_to.frame(frame)
                                                                frame_source = driver.page_source
                                                                
                                                                # Look for email
                                                                import re
                                                                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                                                                found_emails = re.findall(email_pattern, frame_source)
                                                                
                                                                if found_emails:
                                                                    # Filter out editor emails
                                                                    referee_emails = [e for e in found_emails if 'dylan.possamai' not in e and 'math.ethz.ch' not in e]
                                                                    if referee_emails:
                                                                        referee['email'] = referee_emails[0]
                                                                        print(f"      ✅ Email extracted: {referee['email']}")
                                                                        break
                                                                
                                                                driver.switch_to.window(window)
                                                            except:
                                                                driver.switch_to.window(window)
                                                        
                                                        # Close popup
                                                        driver.close()
                                                        driver.switch_to.window(original_window)
                                                        time.sleep(1)
                                                        break
                                            except Exception as e:
                                                print(f"      ❌ Popup error: {e}")
                                                try:
                                                    driver.switch_to.window(original_window)
                                                except:
                                                    pass
                                            
                                            break
                                    
                                    if referee['name']:
                                        manuscript['referees'].append(referee)
                                        print(f"    Referee: {referee['name']} - Email: {referee['email'] or 'NOT EXTRACTED'}")
                            except Exception as e:
                                print(f"    Error processing referee {i+1}: {e}")
                        
                        manuscripts.append(manuscript)
                        
                        print(f"\n📊 EXTRACTION RESULTS FOR {ms_id}:")
                        print(f"  Title: {manuscript.get('title', 'N/A')[:50]}...")
                        print(f"  Referees: {len(manuscript['referees'])}")
                        referee_emails = sum(1 for r in manuscript['referees'] if r.get('email'))
                        print(f"  Referee emails extracted: {referee_emails}/{len(manuscript['referees'])}")
                        
                        for r in manuscript['referees']:
                            status = "✅" if r.get('email') else "❌"
                            print(f"    {status} {r['name']}: {r.get('email', 'NO EMAIL')}")
                    
                    break  # Just process first category for testing
        else:
            print("❌ Login failed - not on AE page")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Save page for debugging
        with open('error_page.html', 'w') as f:
            f.write(driver.page_source)

finally:
    # Save results
    if manuscripts:
        filename = f'direct_extraction_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(filename, 'w') as f:
            json.dump(manuscripts, f, indent=2)
        print(f"\n💾 Results saved to {filename}")
    
    driver.quit()
    print(f"\n🏁 Extraction completed at {datetime.now().strftime('%H:%M:%S')}")