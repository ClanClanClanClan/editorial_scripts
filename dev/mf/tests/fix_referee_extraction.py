#!/usr/bin/env python3
"""
Fix and test referee extraction for MOR
"""

import sys
import time
import re
from pathlib import Path

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from extractors.mor_extractor import MORExtractor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

print("="*60)
print("🔧 FIXING REFEREE EXTRACTION")
print("="*60)

def extract_referees_fixed(driver, safe_get_text):
    """Fixed referee extraction that actually works"""
    referees = []

    try:
        # First, find the referee table by looking for ORDER select elements
        order_selects = driver.find_elements(By.XPATH, "//select[contains(@name,'ORDER')]")
        print(f"   Found {len(order_selects)} ORDER selects")

        if order_selects:
            # Get all rows containing ORDER selects
            for select in order_selects:
                try:
                    # Get the parent row
                    row = select.find_element(By.XPATH, "./ancestor::tr[1]")
                    row_text = safe_get_text(row)

                    if not row_text:
                        continue

                    # Parse the row
                    referee_data = {}

                    # Extract name (usually in a link)
                    name_links = row.find_elements(By.XPATH, ".//a[not(contains(@href,'orcid'))]")
                    if name_links:
                        for link in name_links:
                            link_text = safe_get_text(link).strip()
                            # Check if this looks like a name (not a status or action)
                            if link_text and ',' in link_text and not any(x in link_text.lower() for x in ['invite', 'suggest', 'view', 'edit']):
                                referee_data['name'] = link_text
                                break

                    # If no name in links, try to extract from text
                    if 'name' not in referee_data:
                        # Look for name pattern (Last, First)
                        name_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z][a-z]+(?:\s+[A-Z]\.?)?)', row_text)
                        if name_match:
                            referee_data['name'] = name_match.group(0)

                    # Extract status
                    status_keywords = ['Declined', 'Agreed', 'Invited', 'Pending', 'Overdue', 'Complete', 'In Review']
                    for keyword in status_keywords:
                        if keyword in row_text:
                            referee_data['status'] = keyword
                            break

                    # Extract institution (often in its own line/cell)
                    inst_pattern = r'([A-Z][^,\n]+(?:University|Institute|College|School|Department|Universit[yé]|ETH|MIT|UCLA|UCSD|NYU)[^,\n]*)'
                    inst_match = re.search(inst_pattern, row_text)
                    if inst_match:
                        referee_data['institution'] = inst_match.group(1).strip()

                    # Extract dates
                    date_pattern = r'\d{2}-[A-Z][a-z]{2}-\d{4}'
                    dates = re.findall(date_pattern, row_text)
                    if dates:
                        referee_data['invitation_date'] = dates[0]
                        if len(dates) > 1:
                            referee_data['response_date'] = dates[1]

                    # Extract email if visible
                    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                    email_match = re.search(email_pattern, row_text)
                    if email_match:
                        referee_data['email'] = email_match.group(0)

                    # Only add if we have at least a name
                    if 'name' in referee_data:
                        referees.append(referee_data)
                        print(f"      ✅ Extracted: {referee_data['name']} - {referee_data.get('status', 'Unknown')}")

                except Exception as e:
                    print(f"      ⚠️ Error parsing row: {str(e)[:50]}")
                    continue

        # Alternative: Look for table rows with referee indicators
        if not referees:
            print("   Trying alternative extraction method...")
            status_indicators = ['Declined', 'Agreed', 'Invited', 'Pending', 'Overdue', 'Complete']

            for status in status_indicators:
                rows = driver.find_elements(By.XPATH, f"//tr[contains(., '{status}')]")
                for row in rows:
                    row_text = safe_get_text(row)
                    if not row_text or len(row_text) < 20:
                        continue

                    # Parse as above
                    referee_data = {}

                    # Extract name
                    name_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z][a-z]+(?:\s+[A-Z]\.?)?)', row_text)
                    if name_match:
                        referee_data['name'] = name_match.group(0)
                        referee_data['status'] = status

                        # Extract institution
                        inst_pattern = r'([A-Z][^,\n]+(?:University|Institute|College|School|Department|Universit[yé])[^,\n]*)'
                        inst_match = re.search(inst_pattern, row_text)
                        if inst_match:
                            referee_data['institution'] = inst_match.group(1).strip()

                        if referee_data not in referees:
                            referees.append(referee_data)
                            print(f"      ✅ Found: {referee_data['name']} - {status}")

    except Exception as e:
        print(f"   ❌ Error in extraction: {e}")

    return referees

mor = None
try:
    # Setup
    print("\n1️⃣ Setting up MOR...")
    mor = MORExtractor(use_cache=False)
    mor.driver = webdriver.Chrome(options=mor.chrome_options)
    mor.driver.set_page_load_timeout(30)
    mor.driver.implicitly_wait(10)
    mor.wait = WebDriverWait(mor.driver, 10)
    mor.original_window = mor.driver.current_window_handle
    print("   ✅ Setup complete")

    # Login
    print("\n2️⃣ Logging in...")
    if not mor.login():
        raise Exception("Login failed")
    print("   ✅ Login successful")

    # Navigate
    print("\n3️⃣ Navigating to AE Center...")
    if not mor.navigate_to_ae_center():
        raise Exception("Navigation failed")
    print("   ✅ In AE Center")

    # Find manuscripts
    print("\n4️⃣ Finding manuscripts...")
    category = "Awaiting Reviewer Reports"

    try:
        category_link = mor.driver.find_element(By.LINK_TEXT, category)
        mor.safe_click(category_link)
        mor.smart_wait(3)
        print(f"   ✅ Clicked on '{category}'")
    except:
        # Try any category
        links = mor.driver.find_elements(By.XPATH, "//a[contains(text(), 'Awaiting') or contains(text(), 'Overdue')]")
        if links:
            mor.safe_click(links[0])
            mor.smart_wait(3)

    # Click on first manuscript
    manuscript_rows = mor.driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
    if manuscript_rows:
        row = manuscript_rows[0]
        try:
            check_icon = row.find_element(By.XPATH, ".//img[contains(@src, 'check')]")
            parent_link = check_icon.find_element(By.XPATH, "./parent::*")
            mor.safe_click(parent_link)
        except:
            ms_link = row.find_element(By.XPATH, ".//a[contains(text(), 'MOR-')]")
            mor.safe_click(ms_link)
        mor.smart_wait(3)
        print("   ✅ Opened manuscript")

        # Navigate to referee tab if needed
        referee_tabs = mor.driver.find_elements(By.XPATH,
            "//a[contains(text(), 'Referee') or contains(text(), 'Reviewer') or contains(text(), 'Review')]")
        if referee_tabs:
            mor.safe_click(referee_tabs[0])
            mor.smart_wait(3)
            print("   ✅ Clicked referee tab")

        # Extract referees with fixed method
        print("\n5️⃣ Extracting referees with fixed method...")
        referees = extract_referees_fixed(mor.driver, mor.safe_get_text)

        print(f"\n📊 RESULTS: Extracted {len(referees)} referees")
        for i, ref in enumerate(referees, 1):
            print(f"\n   Referee {i}:")
            for key, value in ref.items():
                print(f"      {key}: {value}")

        # Now test if the MOR method works
        print("\n6️⃣ Testing MOR's built-in method...")
        try:
            mor_referees = mor.extract_referees_enhanced()
            print(f"   MOR method found {len(mor_referees)} referees")
        except Exception as e:
            print(f"   MOR method error: {e}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if mor and hasattr(mor, 'driver'):
        try:
            mor.driver.quit()
            print("\n🧹 Driver closed")
        except:
            pass
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)