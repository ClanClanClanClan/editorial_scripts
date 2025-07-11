#!/usr/bin/env python3
"""
Debug SIFIN Accepted referee email extraction in headless mode
"""

from journals.sifin import SIFIN
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import re

def debug_accepted_referee_emails():
    """Debug why Accepted referee emails are not being extracted"""
    print("DEBUGGING SIFIN ACCEPTED REFEREE EMAIL EXTRACTION (HEADLESS)")
    print("=" * 60)
    
    sifin = SIFIN()
    sifin.setup_driver(headless=True)  # HEADLESS
    
    if not sifin.authenticate():
        print("Authentication failed")
        return
    
    try:
        # Extract manuscripts first to get to the right page
        manuscripts = sifin.extract_manuscripts()
        
        if not manuscripts:
            print("No manuscripts found")
            return
        
        # Use first manuscript
        manuscript = manuscripts[0]
        print(f"\\nTesting manuscript: {manuscript['id']}")
        print(f"Title: {manuscript['title'][:50]}...")
        print(f"Total referees: {len(manuscript['referees'])}")
        
        # Analyze referee statuses
        accepted_count = 0
        other_count = 0
        
        for referee in manuscript['referees']:
            if referee['status'] == 'Accepted':
                accepted_count += 1
                print(f"  Accepted: {referee['name']} - Email: {referee['email'] if referee['email'] else 'MISSING'}")
            else:
                other_count += 1
                print(f"  {referee['status']}: {referee['name']} - Email: {referee['email'] if referee['email'] else 'MISSING'}")
        
        print(f"\\nSummary:")
        print(f"  Accepted referees: {accepted_count}")
        print(f"  Other referees: {other_count}")
        
        # Check which emails are missing
        missing_emails = []
        found_emails = []
        
        for referee in manuscript['referees']:
            if referee['email']:
                found_emails.append((referee['name'], referee['status'], referee['email']))
            else:
                missing_emails.append((referee['name'], referee['status']))
        
        print(f"\\nEmail extraction results:")
        print(f"  Found emails: {len(found_emails)}")
        print(f"  Missing emails: {len(missing_emails)}")
        
        if missing_emails:
            print("\\nMissing emails:")
            for name, status in missing_emails:
                print(f"  - {name} ({status})")
        
        if found_emails:
            print("\\nFound emails:")
            for name, status, email in found_emails:
                print(f"  - {name} ({status}): {email}")
        
        # Now let's test the specific issue: navigate back to the manuscript page
        # and test email extraction for accepted referees
        print("\\n" + "=" * 60)
        print("TESTING ACCEPTED REFEREE EMAIL EXTRACTION")
        print("=" * 60)
        
        # Navigate to manuscript detail page
        if manuscript.get('url'):
            full_url = f"https://sifin.siam.org/{manuscript['url']}"
            print(f"Navigating to: {full_url}")
            sifin.driver.get(full_url)
            time.sleep(3)
            
            # Test email extraction specifically for accepted referees
            main_window = sifin.driver.current_window_handle
            
            # Find accepted referee links
            accepted_referee_links = []
            soup = BeautifulSoup(sifin.driver.page_source, 'html.parser')
            details_table = soup.find('table', {'id': 'ms_details_expanded'})
            
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
                            accepted_referee_links.append((name, ref_link))
            
            print(f"Found {len(accepted_referee_links)} accepted referee links")
            
            for i, (name, link) in enumerate(accepted_referee_links):
                print(f"\\nTesting accepted referee {i+1}: {name}")
                
                try:
                    # Click the referee link
                    sifin.driver.execute_script("arguments[0].click();", link)
                    time.sleep(3)
                    
                    # Check if new window opened
                    if len(sifin.driver.window_handles) > 1:
                        sifin.driver.switch_to.window(sifin.driver.window_handles[-1])
                        print("  New window opened")
                    else:
                        print("  No new window (popup or same page)")
                    
                    # Look for emails in page source with regex
                    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}'
                    emails_found = re.findall(email_pattern, sifin.driver.page_source)
                    
                    if emails_found:
                        # Filter out system emails
                        filtered_emails = [e for e in emails_found if not any(skip in e.lower() for skip in ['noreply', 'no-reply', 'admin', 'system', 'test'])]
                        print(f"  Emails found in page source: {filtered_emails}")
                        
                        if filtered_emails:
                            print(f"  ✅ EMAIL FOUND: {filtered_emails[0]}")
                        else:
                            print(f"  ⚠️  Only system emails found: {emails_found}")
                    else:
                        print("  ❌ No emails found in page source")
                    
                    # Try XPath selectors
                    email_selectors = [
                        "//td[contains(text(), 'E-mail')]/following-sibling::td",
                        "//td[contains(text(), 'Email')]/following-sibling::td",
                        "//td[text()='E-mail']/following-sibling::td",
                        "//td[text()='Email']/following-sibling::td",
                        "//th[text()='E-mail']/following-sibling::td",
                        "//th[text()='Email']/following-sibling::td",
                        "//tr[contains(.,'E-mail')]//td[2]",
                        "//tr[contains(.,'Email')]//td[2]",
                        "//td[contains(text(), '@')]"
                    ]
                    
                    found_with_xpath = False
                    for selector in email_selectors:
                        try:
                            element = sifin.driver.find_element(By.XPATH, selector)
                            email_text = element.text.strip()
                            if '@' in email_text:
                                print(f"  ✅ XPath found: {selector} -> {email_text}")
                                found_with_xpath = True
                                break
                        except:
                            continue
                    
                    if not found_with_xpath:
                        print("  ❌ No email found with XPath selectors")
                    
                    # Close window and return to main
                    if len(sifin.driver.window_handles) > 1:
                        sifin.driver.close()
                        sifin.driver.switch_to.window(main_window)
                    else:
                        sifin.driver.execute_script("window.history.back();")
                        time.sleep(1)
                    
                except Exception as e:
                    print(f"  Error testing {name}: {e}")
                    # Make sure we're back on main window
                    try:
                        if len(sifin.driver.window_handles) > 1:
                            sifin.driver.switch_to.window(main_window)
                    except:
                        pass
    
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