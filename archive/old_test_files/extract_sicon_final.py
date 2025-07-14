#!/usr/bin/env python3
"""
Extract SICON manuscripts - Final version based on actual page structure
"""

import os
import re
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


def extract_referee_info(text):
    """Extract referee information from text like 'Submit Review # M172838 (Yu) 141 days (for LI due on 2025-04-17)'"""
    # Extract manuscript ID
    ms_id_match = re.search(r'M\d+', text)
    ms_id = ms_id_match.group() if ms_id_match else ""
    
    # Extract author name (in parentheses after manuscript ID)
    author_match = re.search(r'M\d+\s*\(([^)]+)\)', text)
    author = author_match.group(1) if author_match else ""
    
    # Extract days remaining
    days_match = re.search(r'(\d+)\s*days', text)
    days_remaining = days_match.group(1) if days_match else ""
    
    # Extract referee info (for X due on Y)
    referee_match = re.search(r'for\s+(\w+)\s+due\s+on\s+([\d-]+)', text)
    referee_name = referee_match.group(1) if referee_match else ""
    due_date = referee_match.group(2) if referee_match else ""
    
    return {
        "manuscript_id": ms_id,
        "author": author,
        "days_remaining": days_remaining,
        "referee_awaiting": referee_name,
        "due_date": due_date
    }


def extract_sicon_manuscripts():
    """Extract SICON manuscripts with complete information."""
    
    # Setup browser
    chrome_options = Options()
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 30)
    
    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f'./sicon_complete_{timestamp}')
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
        
        # Find and click the "Under Review" folder
        print("\n📋 Looking for Under Review folder...")
        
        # Find the Under Review folder link
        under_review_link = driver.find_element(By.XPATH, "//a[contains(@href, 'is_open_1400=1') and contains(text(), '4 AE')]")
        under_review_url = under_review_link.get_attribute('href')
        print(f"Found Under Review folder")
        
        # Navigate to the Under Review folder
        driver.get(under_review_url)
        time.sleep(3)
        
        print("📄 Extracting manuscripts from Under Review folder...")
        
        # Parse the page
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Save the HTML for reference
        with open(output_dir / "under_review_page.html", 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        
        # Find all manuscript links (they have "Submit Review" text)
        manuscript_links = soup.find_all('a', string=re.compile(r'Submit Review.*M\d+'))
        
        manuscripts = []
        
        print(f"\n📋 Found {len(manuscript_links)} manuscripts")
        
        for i, link in enumerate(manuscript_links, 1):
            try:
                # Extract basic info from link text
                link_text = link.get_text(strip=True)
                basic_info = extract_referee_info(link_text)
                
                ms_id = basic_info['manuscript_id']
                print(f"\n📄 Manuscript {i}: {ms_id}")
                print(f"   Author: {basic_info['author']}")
                print(f"   Referee waiting: {basic_info['referee_awaiting']} (due {basic_info['due_date']})")
                
                # Get the manuscript URL
                ms_url = link.get('href', '')
                full_url = ms_url if ms_url.startswith('http') else f"http://sicon.siam.org/{ms_url}"
                
                # Navigate to manuscript details
                driver.get(full_url)
                time.sleep(2)
                
                # Extract detailed information
                ms_soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                ms_data = {
                    "manuscript_id": ms_id,
                    "url": full_url,
                    "corresponding_author": basic_info['author'],
                    "referee_awaiting": basic_info['referee_awaiting'],
                    "due_date": basic_info['due_date'],
                    "days_remaining": basic_info['days_remaining'],
                    "title": "",
                    "authors": "",
                    "submission_date": "",
                    "current_stage": "Under Review",
                    "abstract": "",
                    "keywords": "",
                    "referees": []
                }
                
                # Look for the manuscript details table
                for table in ms_soup.find_all('table'):
                    for row in table.find_all('tr'):
                        cells = row.find_all(['th', 'td'])
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True).lower()
                            value = cells[1].get_text(strip=True)
                            
                            if 'title' in label and not 'subtitle' in label:
                                ms_data["title"] = value
                                print(f"   Title: {value[:50]}...")
                            elif 'contributing author' in label:
                                ms_data["authors"] = value
                            elif 'submission date' in label:
                                ms_data["submission_date"] = value
                            elif 'abstract' in label:
                                ms_data["abstract"] = value[:200] + "..." if len(value) > 200 else value
                            elif 'keywords' in label or 'ams' in label:
                                ms_data["keywords"] = value
                            elif 'referee' in label and 'potential' not in label:
                                # Extract all referee information
                                referee_cell = cells[1]
                                
                                # Get text content and parse referees
                                cell_text = referee_cell.get_text(separator="\n")
                                referee_lines = [line.strip() for line in cell_text.split('\n') if line.strip()]
                                
                                for ref_line in referee_lines:
                                    if ref_line and not ref_line.startswith('Referee'):
                                        # Parse referee info
                                        ref_data = {
                                            "name": "",
                                            "number": "",
                                            "due_date": "",
                                            "received_date": "",
                                            "status": "Awaiting Report"
                                        }
                                        
                                        # Extract name and number
                                        name_match = re.match(r'^([^#]+)#(\d+)', ref_line)
                                        if name_match:
                                            ref_data["name"] = name_match.group(1).strip()
                                            ref_data["number"] = name_match.group(2)
                                        
                                        # Extract dates
                                        due_match = re.search(r'Due:\s*([\d-]+)', ref_line)
                                        if due_match:
                                            ref_data["due_date"] = due_match.group(1)
                                        
                                        rcvd_match = re.search(r'Rcvd:\s*([\d-]+)', ref_line)
                                        if rcvd_match:
                                            ref_data["received_date"] = rcvd_match.group(1)
                                            ref_data["status"] = "Report Received"
                                        
                                        if ref_data["name"]:
                                            ms_data["referees"].append(ref_data)
                
                print(f"   Total referees: {len(ms_data['referees'])}")
                
                # Print referee details
                for ref in ms_data["referees"]:
                    status_symbol = "✅" if ref["status"] == "Report Received" else "⏳"
                    print(f"     {status_symbol} {ref['name']} #{ref['number']} - {ref['status']}")
                    if ref["received_date"]:
                        print(f"        Received: {ref['received_date']}")
                    else:
                        print(f"        Due: {ref['due_date']}")
                
                manuscripts.append(ms_data)
                
                # Go back to Under Review folder
                driver.get(under_review_url)
                time.sleep(1)
                
            except Exception as e:
                print(f"   ❌ Error processing manuscript: {e}")
                continue
        
        print(f"\n📊 Total manuscripts extracted: {len(manuscripts)}")
        
        # Count referees
        total_referees = sum(len(ms["referees"]) for ms in manuscripts)
        referees_with_reports = sum(1 for ms in manuscripts for ref in ms["referees"] if ref["status"] == "Report Received")
        
        print(f"👥 Total referees: {total_referees}")
        print(f"📝 Referees with reports: {referees_with_reports}")
        
        # Save results
        results = {
            "journal": "SICON",
            "extraction_time": datetime.now().isoformat(),
            "total_manuscripts": len(manuscripts),
            "total_referees": total_referees,
            "referees_with_reports": referees_with_reports,
            "manuscripts": manuscripts
        }
        
        with open(output_dir / "sicon_manuscripts.json", 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {output_dir}")
        
        # Print summary
        print("\n" + "="*60)
        print("📊 SICON EXTRACTION SUMMARY")
        print("="*60)
        print(f"✅ Manuscripts: {len(manuscripts)}")
        print(f"✅ Total referees: {total_referees}")
        print(f"✅ Reports received: {referees_with_reports}")
        
        return manuscripts
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    finally:
        print("\n🔄 Closing browser...")
        driver.quit()


if __name__ == "__main__":
    manuscripts = extract_sicon_manuscripts()
    
    # Verify expectations
    if len(manuscripts) == 4:
        print("\n✅ SUCCESS! Found 4 SICON manuscripts as expected!")
        
        # Check referee counts
        total_refs = sum(len(ms["referees"]) for ms in manuscripts)
        refs_with_reports = sum(1 for ms in manuscripts for ref in ms["referees"] if ref["status"] == "Report Received")
        
        print(f"\n📋 Expected: 4 papers with 4 referees (1 report each)")
        print(f"📋 Actual: {len(manuscripts)} papers with {total_refs} referees ({refs_with_reports} reports)")
    else:
        print(f"\n⚠️  Found {len(manuscripts)} manuscripts (expected 4)")