#!/usr/bin/env python3
"""
Extract manuscripts from SICON "Under Review" folder
"""

import os
import time
import json
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup


def extract_sicon_under_review():
    """Login to SICON and extract manuscripts from Under Review folder."""
    
    # Setup browser
    chrome_options = Options()
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 30)
    
    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f'./sicon_under_review_{timestamp}')
    output_dir.mkdir(exist_ok=True)
    
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
            
            // Also click continue button if present
            var continueBtn = document.getElementById('continue-btn');
            if (continueBtn) continueBtn.click();
        """)
        
        # Click ORCID link
        orcid_link = driver.find_element(By.XPATH, "//a[contains(@href, 'orcid')]")
        driver.execute_script("arguments[0].click();", orcid_link)
        
        # Wait for ORCID page
        wait.until(lambda driver: 'orcid.org' in driver.current_url)
        time.sleep(2)
        
        # Fill credentials
        orcid_user = os.getenv("ORCID_USER", "0000-0002-9364-0124")
        orcid_pass = os.getenv("ORCID_PASS", "Hioupy0042%")
        
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
        
        # Remove any cookie banners again
        driver.execute_script("""
            var elements = ['#cookie-policy-layer-bg', '#cookie-policy-layer'];
            elements.forEach(function(sel) {
                var els = document.querySelectorAll(sel);
                els.forEach(function(el) { el.remove(); });
            });
        """)
        
        # Find and click the "Under Review" folder
        print("\n📋 Looking for Under Review folder...")
        
        # Find the Under Review folder link - it has "4 AE" in it
        under_review_link = driver.find_element(By.XPATH, "//a[contains(@href, 'is_open_1400=1') and contains(text(), '4 AE')]")
        under_review_url = under_review_link.get_attribute('href')
        print(f"Found Under Review folder: {under_review_url}")
        
        # Navigate to the Under Review folder
        driver.get(under_review_url)
        time.sleep(3)
        
        print("📄 Extracting manuscripts from Under Review folder...")
        
        # Parse the page
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Save the HTML for analysis
        with open(output_dir / "under_review_page.html", 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        
        # Look for manuscript links
        manuscripts = []
        
        # Find all links that look like manuscript IDs (e.g., M174160)
        for link in soup.find_all('a'):
            text = link.get_text(strip=True)
            href = link.get('href', '')
            
            # Check if this looks like a manuscript link
            if text.startswith('M') and len(text) > 3 and text[1:].isdigit():
                print(f"\nFound manuscript: {text}")
                
                # Get the full URL
                full_url = href if href.startswith('http') else f"http://sicon.siam.org/{href}"
                
                # Navigate to manuscript details
                driver.get(full_url)
                time.sleep(2)
                
                # Extract manuscript details
                ms_soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                ms_data = {
                    "manuscript_id": text,
                    "url": full_url,
                    "title": "",
                    "authors": "",
                    "submission_date": "",
                    "status": "",
                    "referees": []
                }
                
                # Look for the details table
                for table in ms_soup.find_all('table'):
                    for row in table.find_all('tr'):
                        cells = row.find_all(['th', 'td'])
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True).lower()
                            value = cells[1].get_text(strip=True)
                            
                            if 'title' in label:
                                ms_data["title"] = value
                                print(f"  Title: {value[:50]}...")
                            elif 'author' in label:
                                ms_data["authors"] = value
                            elif 'submission' in label:
                                ms_data["submission_date"] = value
                            elif 'status' in label or 'stage' in label:
                                ms_data["status"] = value
                            elif 'referee' in label:
                                # Extract referee information
                                referee_cell = cells[1]
                                for ref_link in referee_cell.find_all('a'):
                                    ref_name = ref_link.get_text(strip=True)
                                    ms_data["referees"].append({
                                        "name": ref_name,
                                        "status": "Unknown"
                                    })
                
                print(f"  Referees: {len(ms_data['referees'])}")
                manuscripts.append(ms_data)
                
                # Go back to Under Review folder
                driver.get(under_review_url)
                time.sleep(1)
        
        print(f"\n📊 Total manuscripts found: {len(manuscripts)}")
        
        # Save results
        results = {
            "journal": "SICON",
            "extraction_time": datetime.now().isoformat(),
            "total_manuscripts": len(manuscripts),
            "manuscripts": manuscripts
        }
        
        with open(output_dir / "sicon_manuscripts.json", 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_dir}")
        
        # Count referees
        total_referees = sum(len(ms["referees"]) for ms in manuscripts)
        print(f"👥 Total referees: {total_referees}")
        
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
    manuscripts = extract_sicon_under_review()
    
    if len(manuscripts) == 4:
        print("\n✅ SUCCESS! Found 4 SICON manuscripts as expected!")
    else:
        print(f"\n⚠️  Found {len(manuscripts)} manuscripts (expected 4)")