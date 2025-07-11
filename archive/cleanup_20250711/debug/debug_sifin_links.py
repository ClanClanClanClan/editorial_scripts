#!/usr/bin/env python3
"""
Debug SIFIN referee profile links
"""

from journals.sifin import SIFIN

def debug_sifin_links():
    """Debug SIFIN referee profile links"""
    print("=" * 60)
    print("DEBUGGING SIFIN REFEREE PROFILE LINKS")
    print("=" * 60)
    
    sifin = SIFIN()
    sifin.setup_driver(headless=False)
    
    if not sifin.authenticate():
        print("Authentication failed")
        return
    
    # Navigate to first manuscript
    try:
        # Get first manuscript URL
        soup = sifin.driver.page_source
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(soup, 'html.parser')
        
        assoc_ed_section = soup.find('tbody', {'role': 'assoc_ed'})
        if assoc_ed_section:
            first_link = assoc_ed_section.find('a', {'class': 'ndt_task_link'})
            if first_link:
                href = first_link.get('href')
                full_url = f"https://sifin.siam.org/{href}"
                print(f"Navigating to: {full_url}")
                
                sifin.driver.get(full_url)
                import time
                time.sleep(3)
                
                # Check page source
                print("\nPage title:", sifin.driver.title)
                print("\nLooking for referee profile links...")
                
                # Try different selectors
                selectors = [
                    "//a[contains(@href, 'au_show_info')]",
                    "//table[@id='ms_details_expanded']//a[contains(@href, 'au_show_info')]",
                    "//table//a[contains(@href, 'au_show_info')]",
                    "//a[contains(@href, 'show_info')]",
                    "//a[contains(@href, 'author')]",
                    "//a[contains(@href, 'referee')]"
                ]
                
                from selenium.webdriver.common.by import By
                for selector in selectors:
                    try:
                        links = sifin.driver.find_elements(By.XPATH, selector)
                        print(f"Selector '{selector}': Found {len(links)} links")
                        if links:
                            for i, link in enumerate(links[:3]):  # Show first 3
                                print(f"  Link {i+1}: {link.get_attribute('href')}")
                                print(f"           Text: {link.text}")
                    except Exception as e:
                        print(f"Selector '{selector}': Error - {e}")
                
                # Check if table exists
                try:
                    table = sifin.driver.find_element(By.ID, 'ms_details_expanded')
                    print(f"\nTable 'ms_details_expanded' found: {table is not None}")
                    
                    # Get table HTML
                    table_html = table.get_attribute('outerHTML')
                    print(f"Table HTML preview: {table_html[:200]}...")
                    
                    # Look for any links in the table
                    links_in_table = table.find_elements(By.TAG_NAME, 'a')
                    print(f"Total links in table: {len(links_in_table)}")
                    
                    for i, link in enumerate(links_in_table):
                        href = link.get_attribute('href')
                        text = link.text
                        print(f"  Table link {i+1}: {href} - '{text}'")
                        
                except Exception as e:
                    print(f"Error checking table: {e}")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            sifin.driver.quit()
        except:
            pass

if __name__ == "__main__":
    debug_sifin_links()