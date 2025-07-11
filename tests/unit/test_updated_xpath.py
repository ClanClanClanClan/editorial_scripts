#!/usr/bin/env python3
"""
Test the updated XPath pattern
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

def test_updated_xpath():
    """Test the updated XPath pattern"""
    
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
        
        # Test updated XPath patterns
        xpath_patterns = [
            "//table[@id='ms_details_expanded']//th[contains(.,'Referees')]/../td//a[contains(@href, 'biblio_dump')]",
            "//table[@id='ms_details_expanded']//th[contains(text(), 'Potential Referees')]/../td//a[contains(@href, 'biblio_dump')]"
        ]
        
        all_referee_links = []
        for i, pattern in enumerate(xpath_patterns):
            print(f"\nTesting updated XPath pattern {i+1}: {pattern}")
            try:
                elements = driver.find_elements(By.XPATH, pattern)
                print(f"  Found {len(elements)} elements")
                all_referee_links.extend(elements)
                
                for j, elem in enumerate(elements):
                    text = elem.text.strip()
                    href = elem.get_attribute('href')
                    print(f"    Element {j+1}: {text} -> {href}")
                    
            except Exception as e:
                print(f"  Error: {e}")
        
        # Filter to only include actual referee names (not other bio links)
        referee_links = []
        for link in all_referee_links:
            link_text = link.text.strip()
            # Skip non-referee links and duplicates
            if (link_text and 
                '#' in link_text and  # Referee names have #1, #2, etc.
                not any(skip in link_text.lower() for skip in ['current', 'stage', 'due', 'invited']) and
                link not in referee_links):
                referee_links.append(link)
        
        print(f"\n=== FINAL FILTERED REFEREE LINKS ===")
        print(f"Found {len(referee_links)} referee profile links")
        
        for i, link in enumerate(referee_links):
            text = link.text.strip()
            href = link.get_attribute('href')
            print(f"  Referee {i+1}: {text} -> {href}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    test_updated_xpath()