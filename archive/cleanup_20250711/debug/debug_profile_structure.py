#!/usr/bin/env python3
"""
Debug SIFIN profile page structure to understand email extraction
"""

from journals.sifin import SIFIN
from selenium.webdriver.common.by import By
import time

def debug_profile_structure():
    """Debug the structure of SIFIN profile pages"""
    print("=" * 60)
    print("DEBUGGING SIFIN PROFILE PAGE STRUCTURE")
    print("=" * 60)
    
    sifin = SIFIN()
    sifin.setup_driver(headless=False)
    
    if not sifin.authenticate():
        print("Authentication failed")
        return
    
    try:
        # Navigate to first manuscript
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(sifin.driver.page_source, 'html.parser')
        
        assoc_ed_section = soup.find('tbody', {'role': 'assoc_ed'})
        if assoc_ed_section:
            first_link = assoc_ed_section.find('a', {'class': 'ndt_task_link'})
            if first_link:
                href = first_link.get('href')
                full_url = f"https://sifin.siam.org/{href}"
                print(f"Navigating to: {full_url}")
                
                sifin.driver.get(full_url)
                time.sleep(3)
                
                # Find referee links
                referee_links = sifin.driver.find_elements(
                    By.XPATH, "//table[@id='ms_details_expanded']//th[contains(text(), 'Referees')]/../td//a"
                )
                
                # Filter to only include actual referee names
                filtered_links = []
                for link in referee_links:
                    link_text = link.text.strip()
                    if link_text and not any(skip in link_text.lower() for skip in ['current', 'stage', 'due', 'invited']):
                        filtered_links.append(link)
                
                print(f"Found {len(filtered_links)} referee links")
                
                if filtered_links:
                    first_referee = filtered_links[0]
                    referee_name = first_referee.text.strip()
                    print(f"Clicking on first referee: {referee_name}")
                    
                    # Click the referee link
                    sifin.driver.execute_script("arguments[0].click();", first_referee)
                    time.sleep(3)
                    
                    # Check if new window opened
                    if len(sifin.driver.window_handles) > 1:
                        print("New window opened - switching to it")
                        sifin.driver.switch_to.window(sifin.driver.window_handles[-1])
                        time.sleep(2)
                    
                    print(f"Current URL: {sifin.driver.current_url}")
                    print(f"Page title: {sifin.driver.title}")
                    
                    # Look for email in various ways
                    email_selectors = [
                        "//td[contains(text(), 'E-mail')]/following-sibling::td",
                        "//td[contains(text(), 'Email')]/following-sibling::td", 
                        "//td[contains(text(), 'e-mail')]/following-sibling::td",
                        "//td[contains(text(), 'EMAIL')]/following-sibling::td",
                        "//td[contains(text(), 'mail')]/following-sibling::td",
                        "//td[text()='E-mail']/following-sibling::td",
                        "//td[text()='Email']/following-sibling::td",
                        "//th[contains(text(), 'E-mail')]/following-sibling::td",
                        "//th[contains(text(), 'Email')]/following-sibling::td"
                    ]
                    
                    for selector in email_selectors:
                        try:
                            email_element = sifin.driver.find_element(By.XPATH, selector)
                            email = email_element.text.strip()
                            print(f"✅ Found email with selector '{selector}': {email}")
                            break
                        except:
                            print(f"❌ Selector '{selector}' failed")
                    
                    # Check all table elements
                    print("\nAll table elements on page:")
                    tables = sifin.driver.find_elements(By.TAG_NAME, "table")
                    for i, table in enumerate(tables):
                        print(f"Table {i+1}:")
                        rows = table.find_elements(By.TAG_NAME, "tr")
                        for j, row in enumerate(rows[:5]):  # Show first 5 rows
                            cells = row.find_elements(By.TAG_NAME, "td")
                            if cells:
                                cell_texts = [cell.text.strip() for cell in cells]
                                print(f"  Row {j+1}: {cell_texts}")
                    
                    # Save page source for inspection
                    page_source = sifin.driver.page_source
                    with open('profile_page_debug.html', 'w') as f:
                        f.write(page_source)
                    print(f"\nSaved page source to profile_page_debug.html")
                    
                    # Look for email pattern in page source
                    import re
                    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                    emails_found = re.findall(email_pattern, page_source)
                    if emails_found:
                        print(f"Found emails in page source: {emails_found}")
                    else:
                        print("No emails found in page source")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        input("Press Enter to close browser...")
        try:
            sifin.driver.quit()
        except:
            pass

if __name__ == "__main__":
    debug_profile_structure()