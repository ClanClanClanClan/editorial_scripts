#!/usr/bin/env python3
"""
Extract manuscripts that are visible after SICON login
"""

import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup


def extract_sicon_manuscripts():
    """Login to SICON and extract visible manuscripts."""
    
    # Setup browser
    chrome_options = Options()
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 30)
    
    try:
        print("🔐 Logging into SICON...")
        
        # Navigate to SICON
        driver.get("http://sicon.siam.org")
        time.sleep(3)
        
        # Remove cookie banners
        driver.execute_script("""
            var elements = ['#cookie-policy-layer-bg', '#cookie-policy-layer'];
            elements.forEach(function(sel) {
                var els = document.querySelectorAll(sel);
                els.forEach(function(el) { el.remove(); });
            });
        """)
        
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
        username_field.clear()
        username_field.send_keys(orcid_user)
        
        password_field = driver.find_element(By.ID, "password")
        password_field.clear()
        password_field.send_keys(orcid_pass)
        password_field.send_keys(Keys.RETURN)
        
        print("⏳ Waiting for authentication...")
        
        # Wait for redirect back to SICON
        wait.until(lambda driver: 'sicon.siam.org' in driver.current_url)
        time.sleep(3)
        
        print("✅ Successfully authenticated!")
        
        # Now extract manuscripts
        print("\n📋 Extracting manuscripts...")
        
        # Parse the page
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Look for task rows
        task_rows = soup.find_all('tr', class_='ndt_task')
        print(f"Found {len(task_rows)} task rows")
        
        manuscripts = []
        
        # Extract each task row
        for i, row in enumerate(task_rows, 1):
            try:
                # Find the manuscript link
                link = row.find('a', class_='ndt_task_link')
                if not link:
                    continue
                
                ms_id = link.get_text(strip=True)
                ms_url = link.get('href', '')
                
                # Get other info from the row
                cells = row.find_all('td')
                
                print(f"\n📄 Manuscript {i}: {ms_id}")
                
                # Navigate to manuscript details
                if ms_url:
                    full_url = ms_url if ms_url.startswith('http') else f"https://sicon.siam.org{ms_url}"
                    driver.get(full_url)
                    time.sleep(2)
                    
                    # Extract details
                    detail_soup = BeautifulSoup(driver.page_source, 'html.parser')
                    
                    ms_data = {
                        "manuscript_id": ms_id,
                        "url": full_url,
                        "title": "",
                        "referees": []
                    }
                    
                    # Look for title
                    title_row = detail_soup.find('th', string=lambda x: x and 'Title' in x)
                    if title_row:
                        title_cell = title_row.find_next_sibling('td')
                        if title_cell:
                            ms_data["title"] = title_cell.get_text(strip=True)
                            print(f"   Title: {ms_data['title'][:50]}...")
                    
                    # Look for referees
                    referee_row = detail_soup.find('th', string=lambda x: x and 'Referee' in x)
                    if referee_row:
                        referee_cell = referee_row.find_next_sibling('td')
                        if referee_cell:
                            # Find all referee links
                            ref_links = referee_cell.find_all('a')
                            print(f"   Referees: {len(ref_links)}")
                            
                            for ref_link in ref_links:
                                ref_name = ref_link.get_text(strip=True)
                                
                                # Check for status
                                parent_text = referee_cell.get_text()
                                status = "Unknown"
                                if "Accepted" in parent_text:
                                    status = "Accepted"
                                    # Check if report is submitted
                                    if "Report" in parent_text or "Submitted" in parent_text:
                                        status = "Accepted - Report Submitted"
                                
                                ms_data["referees"].append({
                                    "name": ref_name,
                                    "status": status
                                })
                                print(f"      • {ref_name} - {status}")
                    
                    manuscripts.append(ms_data)
                    
                    # Go back to main page
                    driver.get("http://sicon.siam.org")
                    time.sleep(1)
                    
            except Exception as e:
                print(f"   Error processing row {i}: {e}")
                continue
        
        print(f"\n📊 Total manuscripts found: {len(manuscripts)}")
        
        # Count referees with reports
        total_referees = sum(len(ms["referees"]) for ms in manuscripts)
        referees_with_reports = sum(1 for ms in manuscripts for ref in ms["referees"] if "Report" in ref["status"])
        
        print(f"👥 Total referees: {total_referees}")
        print(f"📝 Referees with reports: {referees_with_reports}")
        
        return manuscripts
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    finally:
        input("\n⏸️  Press Enter to close browser...")
        driver.quit()


if __name__ == "__main__":
    manuscripts = extract_sicon_manuscripts()
    
    if len(manuscripts) == 4:
        print("\n✅ SUCCESS! Found 4 SICON manuscripts as expected!")
    else:
        print(f"\n⚠️  Found {len(manuscripts)} manuscripts (expected 4)")