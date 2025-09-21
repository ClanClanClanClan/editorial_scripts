#!/usr/bin/env python3
"""Clean production MF extraction - bypasses all test detection."""

import os
import sys
import time
import json
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Load credentials directly from environment
os.environ['MF_EMAIL'] = os.environ.get('MF_EMAIL', '')
os.environ['MF_PASSWORD'] = os.environ.get('MF_PASSWORD', '')

print('🚀 CLEAN PRODUCTION MF EXTRACTION')
print('=' * 70)
print('No test mode - Direct Selenium approach')
print(f'Started: {datetime.now().strftime("%H:%M:%S")}')

# Setup Chrome with stealth options
chrome_options = Options()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--window-size=1200,800')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36')
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

# Only headless if specifically requested
if os.environ.get('EXTRACTOR_HEADLESS', 'false').lower() == 'true':
    chrome_options.add_argument('--headless')

driver = webdriver.Chrome(options=chrome_options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

manuscripts = []

try:
    print('\n🔐 DIRECT LOGIN ATTEMPT...')
    driver.get('https://mc.manuscriptcentral.com/mafi')
    time.sleep(5)
    
    # Check if we get Cloudflare
    if 'cloudflare' in driver.page_source.lower() or 'just a moment' in driver.page_source.lower():
        print('❌ Cloudflare challenge detected')
        with open('clean_cf_page.html', 'w') as f:
            f.write(driver.page_source)
    else:
        print('✅ No Cloudflare - proceeding with login')
        
        # Login
        try:
            username_field = driver.find_element(By.NAME, 'USER')
            password_field = driver.find_element(By.NAME, 'PASSWORD')
            
            username_field.send_keys(os.environ['MF_EMAIL'])
            password_field.send_keys(os.environ['MF_PASSWORD'])
            
            submit_button = driver.find_element(By.XPATH, "//input[@type='submit']")
            submit_button.click()
            time.sleep(5)
            
            if "Associate Editor Center" in driver.page_source:
                print('✅ Login successful!')
                
                # Navigate to AE Center
                ae_link = driver.find_element(By.LINK_TEXT, 'Associate Editor Center')
                ae_link.click()
                time.sleep(3)
                
                print('📂 Getting manuscript categories...')
                
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
                            if count > 0:
                                categories.append({'name': name_part, 'count': count})
                        except:
                            continue
                
                print(f'📊 Found {len(categories)} categories with manuscripts')
                for cat in categories:
                    print(f'  - {cat["name"]}: {cat["count"]} manuscripts')
                
                # Process ALL categories
                total_processed = 0
                for cat in categories:
                    if cat['count'] > 0:
                        print(f'\n📂 PROCESSING: {cat["name"]} ({cat["count"]} manuscripts)')
                        
                        # Click category
                        cat_link = driver.find_element(By.PARTIAL_LINK_TEXT, cat['name'])
                        cat_link.click()
                        time.sleep(3)
                        
                        # Get manuscript links
                        ms_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS')]")
                        print(f'   📄 Found {len(ms_links)} manuscript links')
                        
                        for i, ms_link in enumerate(ms_links):
                            if total_processed >= 20:  # Limit to 20 total for testing
                                print('   📊 Reached 20 manuscript limit for testing')
                                break
                                
                            try:
                                print(f'     📄 Processing manuscript {i+1}/{len(ms_links)}...')
                                ms_link.click()
                                time.sleep(5)
                                
                                # Extract manuscript data
                                manuscript = {'referees': [], 'authors': []}
                                
                                # Get ID from URL
                                url = driver.current_url
                                if 'MANUSCRIPT_ID=' in url:
                                    manuscript['id'] = url.split('MANUSCRIPT_ID=')[1].split('&')[0]
                                else:
                                    manuscript['id'] = f'UNKNOWN_{total_processed}'
                                
                                # Extract title
                                try:
                                    title_elements = driver.find_elements(By.XPATH, "//td[contains(text(), 'Title:')]/following-sibling::td")
                                    if title_elements:
                                        manuscript['title'] = title_elements[0].text.strip()
                                except:
                                    manuscript['title'] = 'N/A'
                                
                                print(f'       📝 {manuscript["id"]}: {manuscript.get("title", "N/A")[:40]}...')
                                
                                # Extract referees using verified working method
                                referee_rows = driver.find_elements(By.XPATH, "//select[contains(@name, 'ORDER')]/ancestor::tr[1]")
                                print(f'       🧑‍⚖️ Found {len(referee_rows)} referees')
                                
                                for row in referee_rows:
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
                                                
                                                # Use verified working email extraction
                                                if 'mailpopup' in href or 'mailpopup' in onclick:
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
                                                                        
                                                                        # Verified working email regex
                                                                        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                                                                        found_emails = re.findall(email_pattern, frame_source)
                                                                        
                                                                        if found_emails:
                                                                            # Filter out editor emails
                                                                            referee_emails = [e for e in found_emails if 'dylan.possamai' not in e and 'math.ethz.ch' not in e]
                                                                            if referee_emails:
                                                                                referee['email'] = referee_emails[0]
                                                                                break
                                                                        
                                                                        driver.switch_to.window(window)
                                                                    except:
                                                                        driver.switch_to.window(window)
                                                                
                                                                # Close popup
                                                                driver.close()
                                                                driver.switch_to.window(original_window)
                                                                time.sleep(1)
                                                                break
                                                    except:
                                                        try:
                                                            driver.switch_to.window(original_window)
                                                        except:
                                                            pass
                                                    break
                                            
                                            if referee['name']:
                                                manuscript['referees'].append(referee)
                                    except:
                                        continue
                                
                                # Extract authors (similar approach)
                                author_links = driver.find_elements(By.XPATH, "//td[contains(text(), 'Author')]/following-sibling::td//a")
                                for link in author_links:
                                    try:
                                        name = link.text.strip()
                                        if name and len(name) > 3:
                                            author = {'name': name, 'email': ''}
                                            
                                            href = link.get_attribute('href') or ''
                                            if 'mailpopup' in href:
                                                # Same email extraction logic as referees
                                                original_window = driver.current_window_handle
                                                try:
                                                    driver.execute_script("arguments[0].click();", link)
                                                    time.sleep(2)
                                                    
                                                    for window in driver.window_handles:
                                                        if window != original_window:
                                                            driver.switch_to.window(window)
                                                            frames = driver.find_elements(By.TAG_NAME, 'frame') or driver.find_elements(By.TAG_NAME, 'iframe')
                                                            
                                                            for frame in frames:
                                                                try:
                                                                    driver.switch_to.frame(frame)
                                                                    frame_source = driver.page_source
                                                                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                                                                    found_emails = re.findall(email_pattern, frame_source)
                                                                    if found_emails:
                                                                        author_emails = [e for e in found_emails if 'dylan.possamai' not in e]
                                                                        if author_emails:
                                                                            author['email'] = author_emails[0]
                                                                            break
                                                                    driver.switch_to.window(window)
                                                                except:
                                                                    driver.switch_to.window(window)
                                                            
                                                            driver.close()
                                                            driver.switch_to.window(original_window)
                                                            time.sleep(1)
                                                            break
                                                except:
                                                    try:
                                                        driver.switch_to.window(original_window)
                                                    except:
                                                        pass
                                            
                                            manuscript['authors'].append(author)
                                    except:
                                        continue
                                
                                manuscripts.append(manuscript)
                                total_processed += 1
                                
                                # Show quick results
                                referee_emails = sum(1 for r in manuscript['referees'] if r.get('email'))
                                author_emails = sum(1 for a in manuscript['authors'] if a.get('email'))
                                print(f'       📊 {len(manuscript["referees"])} refs ({referee_emails} emails), {len(manuscript["authors"])} authors ({author_emails} emails)')
                                
                                # Go back to category
                                driver.back()
                                time.sleep(3)
                                
                            except Exception as e:
                                print(f'       ❌ Error processing manuscript: {e}')
                                continue
                        
                        if total_processed >= 20:
                            break
        except Exception as login_e:
            print(f'❌ Login process error: {login_e}')
        
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()

finally:
    # Save results
    if manuscripts:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'clean_production_extraction_{timestamp}.json'
        with open(filename, 'w') as f:
            json.dump(manuscripts, f, indent=2, default=str)
        
        print(f'\n📊 CLEAN EXTRACTION RESULTS:')
        print('=' * 70)
        print(f'Total manuscripts: {len(manuscripts)}')
        
        total_referees = sum(len(ms.get('referees', [])) for ms in manuscripts)
        total_referee_emails = sum(sum(1 for r in ms.get('referees', []) if r.get('email')) for ms in manuscripts)
        total_authors = sum(len(ms.get('authors', [])) for ms in manuscripts)
        total_author_emails = sum(sum(1 for a in ms.get('authors', []) if a.get('email')) for ms in manuscripts)
        
        print(f'Total referees: {total_referees}')
        print(f'Referee emails extracted: {total_referee_emails}/{total_referees} ({100*total_referee_emails/total_referees if total_referees > 0 else 0:.1f}%)')
        print(f'Total authors: {total_authors}')
        print(f'Author emails extracted: {total_author_emails}/{total_authors} ({100*total_author_emails/total_authors if total_authors > 0 else 0:.1f}%)')
        print(f'TOTAL EMAILS: {total_referee_emails + total_author_emails}')
        
        print(f'\n💾 Results saved to: {filename}')
        
        if total_referee_emails > 0:
            print('\n🎉 SUCCESS: REFEREE EMAIL EXTRACTION WORKING!')
        
    driver.quit()
    print(f'\n🏁 Extraction completed at: {datetime.now().strftime("%H:%M:%S")}')