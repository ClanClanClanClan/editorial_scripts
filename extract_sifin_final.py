#!/usr/bin/env python3
"""
Extract SIFIN manuscripts - Final version
Expected: 4 papers, 6 referees (2 reports received)
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


def extract_sifin_manuscripts():
    """Extract SIFIN manuscripts with complete information."""
    
    # Setup browser
    chrome_options = Options()
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 30)
    
    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f'./sifin_complete_{timestamp}')
    output_dir.mkdir(exist_ok=True)
    
    try:
        print("🔐 Logging into SIFIN...")
        
        # Navigate to SIFIN
        driver.get("http://sifin.siam.org")
        time.sleep(3)
        
        # Remove cookie banners
        driver.execute_script("""
            var elements = ['#cookie-policy-layer-bg', '#cookie-policy-layer', '.cc_banner-wrapper'];
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
        
        # Wait for redirect back to SIFIN
        wait.until(lambda driver: 'sifin.siam.org' in driver.current_url)
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
        
        # Save dashboard HTML
        with open(output_dir / "sifin_dashboard.html", 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        
        # Based on user's description, manuscripts are in Associate Editor Tasks section
        # They appear as: "# M174160 - Under Review / Chase Referees - Complex Discontinuities..."
        
        print("\n📋 Looking for manuscripts in Associate Editor Tasks...")
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Find all links that match the manuscript pattern
        manuscript_links = []
        
        # Look for links with text starting with # and containing manuscript ID
        for link in soup.find_all('a'):
            text = link.get_text(strip=True)
            # Match pattern like "# M174160 - Under Review / Chase Referees..."
            if text.startswith('#') and re.search(r'M\d+', text):
                href = link.get('href', '')
                manuscript_links.append({
                    'text': text,
                    'href': href,
                    'url': href if href.startswith('http') else f"http://sifin.siam.org/{href}"
                })
        
        # If not found, try looking in Under Review folder
        if not manuscript_links:
            print("   Looking for Under Review folder...")
            # Find Under Review folder link
            under_review_links = soup.find_all('a', string=re.compile(r'Under Review.*\d+\s*AE'))
            
            if under_review_links:
                under_review_url = under_review_links[0].get('href', '')
                if not under_review_url.startswith('http'):
                    under_review_url = f"http://sifin.siam.org/{under_review_url}"
                
                driver.get(under_review_url)
                time.sleep(3)
                
                # Parse again
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Save this page too
                with open(output_dir / "sifin_under_review.html", 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                
                # Look for manuscript links again
                for link in soup.find_all('a'):
                    text = link.get_text(strip=True)
                    if re.search(r'M\d+', text):
                        href = link.get('href', '')
                        manuscript_links.append({
                            'text': text,
                            'href': href,
                            'url': href if href.startswith('http') else f"http://sifin.siam.org/{href}"
                        })
        
        print(f"\n📋 Found {len(manuscript_links)} manuscripts")
        
        manuscripts = []
        
        for i, ms_link in enumerate(manuscript_links, 1):
            try:
                # Extract manuscript ID from text
                ms_id_match = re.search(r'M\d+', ms_link['text'])
                if not ms_id_match:
                    continue
                
                ms_id = ms_id_match.group()
                print(f"\n📄 Manuscript {i}: {ms_id}")
                
                # Parse status from text (e.g., "Under Review / Chase Referees")
                status_match = re.search(r'-\s*([^-]+?)\s*-', ms_link['text'])
                status = status_match.group(1).strip() if status_match else "Unknown"
                
                # Navigate to manuscript details
                driver.get(ms_link['url'])
                time.sleep(2)
                
                # Extract detailed information
                ms_soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                ms_data = {
                    "manuscript_id": ms_id,
                    "url": ms_link['url'],
                    "status_from_list": status,
                    "title": "",
                    "corresponding_author": "",
                    "authors": "",
                    "submission_date": "",
                    "current_stage": "",
                    "abstract": "",
                    "keywords": "",
                    "referees": [],
                    "associate_editor": ""
                }
                
                # Look for the manuscript details table
                for table in ms_soup.find_all('table'):
                    for row in table.find_all('tr'):
                        cells = row.find_all(['th', 'td'])
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True).lower()
                            value = cells[1].get_text(strip=True)
                            
                            if 'manuscript #' in label:
                                ms_data["manuscript_id"] = value
                            elif 'title' in label and 'subtitle' not in label:
                                ms_data["title"] = value
                                print(f"   Title: {value[:50]}...")
                            elif 'corresponding author' in label:
                                ms_data["corresponding_author"] = value
                            elif 'contributing author' in label:
                                ms_data["authors"] = value
                            elif 'submission date' in label:
                                ms_data["submission_date"] = value
                            elif 'current stage' in label:
                                ms_data["current_stage"] = value
                            elif 'abstract' in label:
                                ms_data["abstract"] = value[:200] + "..." if len(value) > 200 else value
                            elif 'keywords' in label or 'ams' in label:
                                ms_data["keywords"] = value
                            elif 'associate editor' in label:
                                ms_data["associate_editor"] = value
                            elif 'referee' in label and 'potential' not in label:
                                # Extract referee information
                                referee_cell = cells[1]
                                
                                # Parse referees - they might be separated by commas or newlines
                                cell_text = referee_cell.get_text(separator="\n")
                                referee_entries = re.split(r'[,\n]', cell_text)
                                
                                for entry in referee_entries:
                                    entry = entry.strip()
                                    if not entry or entry.lower() == 'referees':
                                        continue
                                    
                                    ref_data = {
                                        "name": "",
                                        "number": "",
                                        "due_date": "",
                                        "received_date": "",
                                        "status": "Awaiting Report"
                                    }
                                    
                                    # Parse referee name and number
                                    name_match = re.match(r'^([^#(]+)(?:#(\d+))?', entry)
                                    if name_match:
                                        ref_data["name"] = name_match.group(1).strip()
                                        if name_match.group(2):
                                            ref_data["number"] = name_match.group(2)
                                    
                                    # Check for dates
                                    due_match = re.search(r'Due:\s*([\d-]+)', entry)
                                    if due_match:
                                        ref_data["due_date"] = due_match.group(1)
                                    
                                    rcvd_match = re.search(r'Rcvd:\s*([\d-]+)', entry)
                                    if rcvd_match:
                                        ref_data["received_date"] = rcvd_match.group(1)
                                        ref_data["status"] = "Report Received"
                                    
                                    if ref_data["name"]:
                                        ms_data["referees"].append(ref_data)
                
                # Remove duplicates
                unique_referees = []
                seen = set()
                for ref in ms_data["referees"]:
                    key = (ref["name"], ref["number"])
                    if key not in seen:
                        seen.add(key)
                        unique_referees.append(ref)
                ms_data["referees"] = unique_referees
                
                print(f"   Corresponding Author: {ms_data['corresponding_author']}")
                print(f"   Stage: {ms_data['current_stage']}")
                print(f"   Total referees: {len(ms_data['referees'])}")
                
                # Print referee details
                for ref in ms_data["referees"]:
                    status_symbol = "✅" if ref["status"] == "Report Received" else "⏳"
                    print(f"     {status_symbol} {ref['name']} #{ref['number']} - {ref['status']}")
                    if ref["received_date"]:
                        print(f"        Received: {ref['received_date']}")
                    elif ref["due_date"]:
                        print(f"        Due: {ref['due_date']}")
                
                manuscripts.append(ms_data)
                
                # Go back to main page
                driver.get("http://sifin.siam.org")
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
            "journal": "SIFIN",
            "extraction_time": datetime.now().isoformat(),
            "total_manuscripts": len(manuscripts),
            "total_referees": total_referees,
            "referees_with_reports": referees_with_reports,
            "manuscripts": manuscripts
        }
        
        with open(output_dir / "sifin_manuscripts.json", 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {output_dir}")
        
        # Print summary
        print("\n" + "="*60)
        print("📊 SIFIN EXTRACTION SUMMARY")
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
    manuscripts = extract_sifin_manuscripts()
    
    # Verify expectations
    print("\n" + "="*60)
    print("🎯 VERIFICATION")
    print("="*60)
    
    print(f"\nExpected: 4 papers with 6 referees (2 reports)")
    print(f"Actual: {len(manuscripts)} papers")
    
    if len(manuscripts) == 4:
        total_refs = sum(len(ms["referees"]) for ms in manuscripts)
        refs_with_reports = sum(1 for ms in manuscripts for ref in ms["referees"] if ref["status"] == "Report Received")
        
        print(f"        {total_refs} referees ({refs_with_reports} reports)")
        
        if total_refs == 6 and refs_with_reports == 2:
            print("\n✅ SUCCESS! Results match expectations!")
        else:
            print("\n⚠️  Referee counts don't match expectations")
    else:
        print(f"\n⚠️  Found {len(manuscripts)} manuscripts (expected 4)")