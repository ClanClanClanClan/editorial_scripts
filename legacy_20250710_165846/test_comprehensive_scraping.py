#!/usr/bin/env python3

"""
Comprehensive test to find ALL manuscripts and referees across all journals.
Based on user feedback, we should be finding:
- MOR: 6 referees
- SICON: 4 referees  
- MF: 4 referees
- SIFIN: 6 referees
- FS: 5 referees
- NACO: 0 referees
- MAFE: 0 referees
- JOTA: 0 referees
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
from bs4 import BeautifulSoup

def comprehensive_manuscript_search(driver, journal_name, manuscript_pattern):
    """
    Perform comprehensive search for manuscripts across all possible locations.
    """
    print(f"\n=== COMPREHENSIVE SEARCH FOR {journal_name} ===")
    
    manuscripts_found = []
    total_referees = 0
    
    # Save current page for analysis
    with open(f'{journal_name}_dashboard.html', 'w') as f:
        f.write(driver.page_source)
    
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    # 1. Search all tables for manuscript IDs
    print("1. Searching all tables for manuscript IDs...")
    all_tables = soup.find_all("table")
    for idx, table in enumerate(all_tables):
        text = table.get_text()
        if re.search(manuscript_pattern, text):
            print(f"   Found manuscripts in table #{idx}")
            # Extract all manuscript IDs from this table
            ms_ids = re.findall(manuscript_pattern, text)
            print(f"   Manuscript IDs found: {ms_ids}")
            manuscripts_found.extend(ms_ids)
    
    # 2. Search all links
    print("2. Searching all links...")
    all_links = driver.find_elements(By.TAG_NAME, "a")
    print(f"   Total links on page: {len(all_links)}")
    
    manuscript_links = []
    for link in all_links:
        try:
            href = link.get_attribute("href") or ""
            text = link.text or ""
            onclick = link.get_attribute("onclick") or ""
            
            # Check if link contains manuscript pattern
            if (re.search(manuscript_pattern, href) or 
                re.search(manuscript_pattern, text) or
                re.search(manuscript_pattern, onclick)):
                manuscript_links.append({
                    'href': href,
                    'text': text,
                    'onclick': onclick
                })
        except:
            continue
    
    print(f"   Manuscript-related links found: {len(manuscript_links)}")
    
    # 3. Check all status queues
    print("3. Checking all status queues...")
    
    # Find all td elements that might contain status counts
    all_tds = soup.find_all("td")
    status_queues = []
    
    for i in range(len(all_tds) - 1):
        td = all_tds[i]
        next_td = all_tds[i + 1]
        
        # Check if this td contains a number
        text = td.get_text(strip=True)
        if text.isdigit() and int(text) > 0:
            # Check if next td contains status text
            status_text = next_td.get_text(strip=True)
            if len(status_text) > 5 and len(status_text) < 100:  # Reasonable status text length
                status_queues.append({
                    'count': int(text),
                    'status': status_text
                })
    
    print(f"   Status queues with manuscripts: {len(status_queues)}")
    for sq in status_queues:
        print(f"     - {sq['status']}: {sq['count']} manuscripts")
    
    # 4. Look for referee information
    print("4. Looking for referee information...")
    
    # Common patterns for referee names and status
    referee_patterns = [
        r"([A-Z][a-z]+)\s+([A-Z][a-z]+).*?(Accepted|Contacted|Agreed|Declined|Overdue)",
        r"Referee.*?:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)",
        r"Reviewer.*?:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)"
    ]
    
    for pattern in referee_patterns:
        matches = re.findall(pattern, driver.page_source)
        if matches:
            print(f"   Found {len(matches)} potential referees with pattern: {pattern[:30]}...")
            total_referees += len(matches)
    
    # 5. Check for hidden or collapsed sections
    print("5. Checking for expandable/hidden sections...")
    
    # Look for expand/collapse buttons
    expand_buttons = driver.find_elements(By.XPATH, "//button[contains(@class, 'expand') or contains(@class, 'collapse') or contains(@onclick, 'expand') or contains(@onclick, 'toggle')]")
    print(f"   Found {len(expand_buttons)} expandable sections")
    
    # Look for "View All" or "Show More" links
    view_all_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'View All') or contains(text(), 'Show More') or contains(text(), 'See All')]")
    print(f"   Found {len(view_all_links)} 'View All' type links")
    
    return {
        'manuscripts_found': len(set(manuscripts_found)),
        'total_referees': total_referees,
        'status_queues': status_queues,
        'manuscript_links': len(manuscript_links)
    }

def test_mor_comprehensive():
    """Test MOR journal to find all 6 referees."""
    print("\n" + "="*60)
    print("TESTING MOR JOURNAL - EXPECTING 6 REFEREES")
    print("="*60)
    
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    driver = webdriver.Chrome(options=options)
    
    try:
        from journals.mor import MORJournal
        mor = MORJournal(driver, debug=True)
        
        # Login
        print("Logging in to MOR...")
        mor.login()
        time.sleep(3)
        
        # Try to navigate to different sections
        print("\nTrying different navigation paths...")
        
        # Save the dashboard
        with open('mor_after_login.html', 'w') as f:
            f.write(driver.page_source)
        
        # Look for all possible navigation links
        nav_patterns = [
            "Associate Editor",
            "Editor Center",
            "Manuscripts",
            "Submissions",
            "Review",
            "My Manuscripts",
            "Assigned Manuscripts",
            "Dashboard"
        ]
        
        for pattern in nav_patterns:
            links = driver.find_elements(By.XPATH, f"//a[contains(text(), '{pattern}')]")
            if links:
                print(f"Found {len(links)} links containing '{pattern}'")
                # Click the first one
                try:
                    links[0].click()
                    time.sleep(2)
                    
                    # Perform comprehensive search
                    results = comprehensive_manuscript_search(driver, "MOR", r"MOR-\d{4}-\d+")
                    
                    if results['total_referees'] >= 6:
                        print(f"\n✅ SUCCESS! Found {results['total_referees']} referees")
                        break
                except Exception as e:
                    print(f"   Error clicking {pattern}: {e}")
                    continue
        
        # Final attempt - check current page
        results = comprehensive_manuscript_search(driver, "MOR", r"MOR-\d{4}-\d+")
        
        print(f"\n=== MOR FINAL RESULTS ===")
        print(f"Manuscripts found: {results['manuscripts_found']}")
        print(f"Total referees found: {results['total_referees']}")
        print(f"Expected referees: 6")
        
        if results['total_referees'] < 6:
            print(f"⚠️  MISSING {6 - results['total_referees']} REFEREES")
            print("\nPossible reasons:")
            print("- Not all status queues are being checked")
            print("- Some manuscripts are in different sections")
            print("- Referees might be in collapsed/hidden sections")
            print("- Need to navigate to specific manuscript detail pages")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        driver.quit()

def test_all_journals():
    """Test all journals to verify referee counts."""
    expected_counts = {
        'MOR': 6,
        'SICON': 4,
        'MF': 4,
        'SIFIN': 6,
        'FS': 5,
        'NACO': 0,
        'MAFE': 0,
        'JOTA': 0
    }
    
    print("\n" + "="*60)
    print("COMPREHENSIVE JOURNAL TESTING")
    print("="*60)
    
    for journal, expected_refs in expected_counts.items():
        print(f"\n{journal}: Expecting {expected_refs} referees")
        # TODO: Implement tests for each journal

if __name__ == "__main__":
    # Start with MOR since we know it should have 6 referees
    test_mor_comprehensive()
    
    # Then test others
    # test_all_journals()