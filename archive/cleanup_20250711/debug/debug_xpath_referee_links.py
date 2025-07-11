#!/usr/bin/env python3
"""
Debug XPath patterns to find ALL referee links in the saved HTML
"""

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

def debug_xpath_patterns():
    """Test different XPath patterns to find all referee links"""
    
    # Read the saved HTML file
    with open('sifin_manuscript_detail.html', 'r') as f:
        html_content = f.read()
    
    # Parse with BeautifulSoup for analysis
    soup = BeautifulSoup(html_content, 'html.parser')
    
    print("=== BeautifulSoup Analysis ===")
    
    # Find all biblio_dump links
    all_biblio_links = soup.find_all('a', href=lambda x: x and 'biblio_dump' in x)
    print(f"Total biblio_dump links found: {len(all_biblio_links)}")
    
    for i, link in enumerate(all_biblio_links):
        text = link.get_text(strip=True)
        href = link.get('href')
        print(f"  Link {i+1}: {text} -> {href}")
    
    # Find the ms_details_expanded table
    details_table = soup.find('table', {'id': 'ms_details_expanded'})
    if details_table:
        print("\n=== ms_details_expanded Table Structure ===")
        
        # Find referee sections
        for row in details_table.find_all('tr'):
            th = row.find('th')
            td = row.find('td')
            if th and td:
                label = th.get_text(strip=True)
                if 'referee' in label.lower():
                    print(f"\nFound referee section: {label}")
                    
                    # Find all links in this section
                    section_links = td.find_all('a')
                    print(f"  Links in section: {len(section_links)}")
                    
                    for link in section_links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        if 'biblio_dump' in href:
                            print(f"    Referee link: {text} -> {href}")
    
    # Now test with Selenium
    print("\n=== Selenium XPath Testing ===")
    
    # Setup Chrome driver
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Load the HTML file
        driver.get('file://' + '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/sifin_manuscript_detail.html')
        time.sleep(2)
        
        # Test current XPath patterns
        xpath_patterns = [
            "//table[@id='ms_details_expanded']//th[text()='Referees']/../td//a[contains(@href, 'biblio_dump')]",
            "//table[@id='ms_details_expanded']//th[contains(text(), 'Potential Referees')]/../td//a[contains(@href, 'biblio_dump')]",
            "//table[@id='ms_details_expanded']//a[contains(@href, 'biblio_dump')]",  # Broader pattern
            "//a[contains(@href, 'biblio_dump')]",  # Even broader
        ]
        
        for i, pattern in enumerate(xpath_patterns):
            print(f"\nTesting XPath pattern {i+1}: {pattern}")
            try:
                elements = driver.find_elements(By.XPATH, pattern)
                print(f"  Found {len(elements)} elements")
                
                for j, elem in enumerate(elements):
                    text = elem.text.strip()
                    href = elem.get_attribute('href')
                    print(f"    Element {j+1}: {text} -> {href}")
                    
            except Exception as e:
                print(f"  Error: {e}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    debug_xpath_patterns()