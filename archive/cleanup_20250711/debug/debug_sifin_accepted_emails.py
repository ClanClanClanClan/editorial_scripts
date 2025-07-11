#!/usr/bin/env python3
"""
Debug SIFIN Accepted referee email extraction specifically
"""

from journals.sifin import SIFIN
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import re

def debug_accepted_referee_emails():
    """Debug why Accepted referee emails are not being extracted"""
    print("DEBUGGING SIFIN ACCEPTED REFEREE EMAIL EXTRACTION")
    print("=" * 60)
    
    sifin = SIFIN()
    sifin.setup_driver(headless=False)
    
    if not sifin.authenticate():
        print("Authentication failed")
        return
    
    try:
        # Navigate to first manuscript
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
                
                # Extract referee information first
                soup = BeautifulSoup(sifin.driver.page_source, 'html.parser')
                details_table = soup.find('table', {'id': 'ms_details_expanded'})
                
                accepted_referees = []
                other_referees = []
                
                if details_table:
                    for row in details_table.find_all('tr'):
                        th = row.find('th')
                        td = row.find('td')
                        if not th or not td:
                            continue
                        
                        label = th.get_text(strip=True)
                        
                        if label == "Referees":
                            # These are accepted referees
                            for ref_link in td.find_all('a'):
                                name = ref_link.get_text(strip=True)
                                accepted_referees.append((name, ref_link, 'Accepted'))
                        
                        elif "Potential Referees" in label:
                            # These are contacted/declined referees
                            for ref_link in td.find_all('a'):
                                name = ref_link.get_text(strip=True)
                                # Check status in surrounding text
                                next_text = ''
                                node = ref_link.next_sibling
                                while node and len(next_text) < 200:
                                    if hasattr(node, 'name') and node.name == 'a':
                                        break
                                    next_text += str(node)
                                    node = node.next_sibling if hasattr(node, 'next_sibling') else None
                                
                                if 'declined' in next_text.lower():
                                    status = 'Declined'
                                else:
                                    status = 'Contacted'
                                
                                other_referees.append((name, ref_link, status))
                
                print(f"\\nFound referees:")
                print(f"  Accepted: {len(accepted_referees)}")
                print(f"  Other: {len(other_referees)}")
                
                # Test each accepted referee
                main_window = sifin.driver.current_window_handle
                
                for i, (name, link, status) in enumerate(accepted_referees):
                    print(f"\\n--- Testing Accepted Referee {i+1}: {name} ---")
                    
                    try:
                        # Click the referee link
                        sifin.driver.execute_script("arguments[0].click();", link)
                        time.sleep(3)
                        
                        # Check if new window opened
                        if len(sifin.driver.window_handles) > 1:
                            print("New window opened")
                            sifin.driver.switch_to.window(sifin.driver.window_handles[-1])
                        else:
                            print("No new window - possibly popup or same page")
                        
                        print(f"Current URL: {sifin.driver.current_url}")
                        print(f"Page title: {sifin.driver.title}")
                        
                        # Save page source for analysis
                        page_source = sifin.driver.page_source
                        filename = f"accepted_referee_{i+1}_{name.replace(' ', '_')}.html"
                        with open(filename, 'w') as f:
                            f.write(page_source)
                        print(f"Saved page source to {filename}")
                        
                        # Look for emails in page source
                        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}'
                        emails_found = re.findall(email_pattern, page_source)
                        print(f"Emails found in page source: {emails_found}")
                        
                        # Try all email selectors
                        email_selectors = [
                            "//td[contains(text(), 'E-mail')]/following-sibling::td",
                            "//td[contains(text(), 'Email')]/following-sibling::td",
                            "//td[text()='E-mail']/following-sibling::td",
                            "//td[text()='Email']/following-sibling::td",
                            "//th[text()='E-mail']/following-sibling::td",
                            "//th[text()='Email']/following-sibling::td",
                            "//tr[contains(.,'E-mail')]//td[2]",
                            "//tr[contains(.,'Email')]//td[2]",
                            "//tr[contains(.,'e-mail')]//td[2]",
                            "//tr[contains(.,'email')]//td[2]",
                            "//td[contains(text(), '@')]",
                            "//span[contains(text(), '@')]"
                        ]
                        
                        print("\\nTesting email selectors:")
                        found_email = False
                        for selector in email_selectors:
                            try:
                                element = sifin.driver.find_element(By.XPATH, selector)
                                email_text = element.text.strip()
                                if '@' in email_text:
                                    print(f"✅ FOUND: '{selector}' -> '{email_text}'")
                                    found_email = True
                                    break
                                else:
                                    print(f"⚠️  FOUND NON-EMAIL: '{selector}' -> '{email_text}'")
                            except:
                                print(f"❌ FAILED: '{selector}'")
                        
                        if not found_email:
                            print("🔍 No email found with XPath selectors")
                        
                        # Check page structure
                        print("\\nPage structure:")
                        try:
                            tables = sifin.driver.find_elements(By.TAG_NAME, "table")
                            print(f"Found {len(tables)} tables")
                            
                            for j, table in enumerate(tables[:3]):  # Check first 3 tables
                                print(f"\\nTable {j+1}:")
                                rows = table.find_elements(By.TAG_NAME, "tr")
                                for k, row in enumerate(rows[:5]):  # First 5 rows
                                    cells = row.find_elements(By.TAG_NAME, "td")
                                    cell_texts = [cell.text.strip() for cell in cells]
                                    if cell_texts and any(cell_texts):
                                        print(f"  Row {k+1}: {cell_texts}")
                                        # Check for email in this row
                                        for cell_text in cell_texts:
                                            if '@' in cell_text:
                                                print(f"    🎯 EMAIL FOUND: {cell_text}")
                        except Exception as e:
                            print(f"Error analyzing page structure: {e}")
                        
                        # Close window and return to main
                        if len(sifin.driver.window_handles) > 1:
                            sifin.driver.close()
                            sifin.driver.switch_to.window(main_window)
                        else:
                            # Try to go back
                            sifin.driver.execute_script("window.history.back();")
                            time.sleep(1)
                        
                        print(f"Finished testing {name}")
                        
                    except Exception as e:
                        print(f"Error testing {name}: {e}")
                        import traceback
                        traceback.print_exc()
                        
                        # Make sure we're back on main window
                        try:
                            if len(sifin.driver.window_handles) > 1:
                                sifin.driver.switch_to.window(main_window)
                        except:
                            pass
                
                print("\\n" + "=" * 60)
                print("DEBUGGING COMPLETE")
                print("Check the saved HTML files for detailed analysis")
                input("Press Enter to exit...")
    
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
    debug_accepted_referee_emails()