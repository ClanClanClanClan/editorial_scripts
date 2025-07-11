#!/usr/bin/env python3
"""
Debug SIFIN email page structure to find correct XPath
"""

from journals.sifin import SIFIN
from selenium.webdriver.common.by import By
import time
import re

def debug_sifin_email_page():
    """Debug SIFIN email page to find correct selectors"""
    print("DEBUGGING SIFIN EMAIL PAGE STRUCTURE")
    print("="*50)
    
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
                
                # Find and click first referee link
                referee_links = []
                referee_sections = sifin.driver.find_elements(
                    By.XPATH, "//table[@id='ms_details_expanded']//th[contains(text(), 'Referees')]/../td//a"
                )
                
                for link in referee_sections:
                    link_text = link.text.strip()
                    if link_text and not any(skip in link_text.lower() for skip in ['current', 'stage', 'due', 'invited']):
                        referee_links.append(link)
                
                if referee_links:
                    first_referee = referee_links[0]
                    referee_name = first_referee.text.strip()
                    print(f"Clicking referee: {referee_name}")
                    
                    # Click referee link
                    sifin.driver.execute_script("arguments[0].click();", first_referee)
                    time.sleep(3)
                    
                    # Handle new window
                    main_window = sifin.driver.current_window_handle
                    if len(sifin.driver.window_handles) > 1:
                        print("New window opened")
                        sifin.driver.switch_to.window(sifin.driver.window_handles[-1])
                        time.sleep(2)
                    
                    print(f"Current URL: {sifin.driver.current_url}")
                    print(f"Page title: {sifin.driver.title}")
                    
                    # Save page source
                    page_source = sifin.driver.page_source
                    with open('referee_profile_page.html', 'w') as f:
                        f.write(page_source)
                    print("Saved page source to referee_profile_page.html")
                    
                    # Look for email patterns in page source
                    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                    emails_found = re.findall(email_pattern, page_source)
                    print(f"Email addresses found in page: {emails_found}")
                    
                    # Try multiple XPath selectors
                    email_selectors = [
                        "//td[contains(text(), 'E-mail')]/following-sibling::td",
                        "//td[contains(text(), 'Email')]/following-sibling::td",
                        "//td[contains(text(), 'e-mail')]/following-sibling::td",
                        "//td[contains(text(), 'EMAIL')]/following-sibling::td",
                        "//td[contains(text(), 'mail')]/following-sibling::td",
                        "//td[text()='E-mail']/following-sibling::td",
                        "//td[text()='Email']/following-sibling::td",
                        "//th[contains(text(), 'E-mail')]/following-sibling::td",
                        "//th[contains(text(), 'Email')]/following-sibling::td",
                        "//th[text()='E-mail']/following-sibling::td",
                        "//th[text()='Email']/following-sibling::td",
                        "//tr[contains(.,'E-mail')]//td[2]",
                        "//tr[contains(.,'Email')]//td[2]",
                        "//tr[contains(.,'e-mail')]//td[2]",
                        "//tr[contains(.,'email')]//td[2]",
                        "//td[contains(@class, 'email')]",
                        "//span[contains(@class, 'email')]",
                        "//div[contains(@class, 'email')]",
                        f"//td[contains(text(), '{emails_found[0]}')]" if emails_found else "//td[contains(text(), '@')]"
                    ]
                    
                    print("\nTrying email selectors:")
                    for selector in email_selectors:
                        try:
                            element = sifin.driver.find_element(By.XPATH, selector)
                            email_text = element.text.strip()
                            print(f"✅ FOUND: '{selector}' -> '{email_text}'")
                            if '@' in email_text:
                                print(f"🎯 THIS IS THE CORRECT SELECTOR!")
                                break
                        except Exception as e:
                            print(f"❌ FAILED: '{selector}'")
                    
                    # Check all table structure
                    print("\nTable structure analysis:")
                    tables = sifin.driver.find_elements(By.TAG_NAME, "table")
                    for i, table in enumerate(tables):
                        print(f"\nTable {i+1}:")
                        try:
                            rows = table.find_elements(By.TAG_NAME, "tr")
                            for j, row in enumerate(rows[:10]):  # First 10 rows
                                cells = row.find_elements(By.TAG_NAME, "td")
                                cell_texts = [cell.text.strip() for cell in cells]
                                if cell_texts and any(cell_texts):
                                    print(f"  Row {j+1}: {cell_texts}")
                                    # Check for email in this row
                                    for cell_text in cell_texts:
                                        if '@' in cell_text:
                                            print(f"    🎯 EMAIL FOUND: {cell_text}")
                        except Exception as e:
                            print(f"  Error reading table {i+1}: {e}")
                    
                    input("Press Enter to continue...")
    
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
    debug_sifin_email_page()