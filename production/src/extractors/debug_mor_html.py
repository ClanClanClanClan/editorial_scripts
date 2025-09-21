#!/usr/bin/env python3
"""
Debug MOR HTML structure to see what's actually on the page
"""
import os
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

def debug_mor_html():
    print("🔍 DEBUGGING MOR HTML STRUCTURE")

    # Load credentials
    result = subprocess.run(['bash', '-c', 'source ~/.editorial_scripts/load_all_credentials.sh && echo "OK"'],
                          capture_output=True, text=True)

    # Setup browser
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    try:
        # Login
        driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(3)

        username = os.getenv('MOR_EMAIL')
        password = os.getenv('MOR_PASSWORD')

        # Login
        driver.find_element(By.ID, "USERID").send_keys(username)
        driver.find_element(By.ID, "PASSWORD").send_keys(password)
        driver.find_element(By.ID, "PASSWORD").send_keys(Keys.RETURN)
        time.sleep(10)  # Wait for 2FA

        # Navigate to AE Center
        ae_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Associate Editor')]")
        if ae_links:
            ae_links[0].click()
            time.sleep(3)

        # Find manuscripts
        manuscript_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Awaiting Reviewer Reports')]")
        if manuscript_links:
            manuscript_links[0].click()
            time.sleep(3)

        # Find and click on a manuscript
        manuscript_rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
        if manuscript_rows:
            manuscript_link = manuscript_rows[0].find_element(By.XPATH, ".//a")
            manuscript_link.click()
            time.sleep(5)

        print("\n📄 CURRENT PAGE HTML ANALYSIS:")
        print(f"URL: {driver.current_url}")
        print(f"Title: {driver.title}")

        # Check for referee-related elements
        print("\n🔍 REFEREE ELEMENT ANALYSIS:")

        # Check XIK_RP_ID inputs
        xik_inputs = driver.find_elements(By.XPATH, "//input[contains(@name, 'XIK_RP_ID')]")
        print(f"XIK_RP_ID inputs: {len(xik_inputs)}")
        for i, inp in enumerate(xik_inputs[:3]):
            print(f"  {i+1}. name={inp.get_attribute('name')}, value={inp.get_attribute('value')}")

        # Check for ORDER selects
        order_selects = driver.find_elements(By.XPATH, "//select[contains(@name, 'ORDER')]")
        print(f"ORDER selects: {len(order_selects)}")

        # Check mailpopup links
        mailpopup_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'mailpopup')]")
        print(f"Mailpopup links: {len(mailpopup_links)}")
        for i, link in enumerate(mailpopup_links[:3]):
            print(f"  {i+1}. text='{link.text}', href='{link.get_attribute('href')[:100]}...'")

        # Check for any tables or forms
        tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"Tables found: {len(tables)}")

        forms = driver.find_elements(By.TAG_NAME, "form")
        print(f"Forms found: {len(forms)}")

        # Check for any elements containing "referee" or "reviewer"
        referee_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'referee') or contains(text(), 'Referee') or contains(text(), 'reviewer') or contains(text(), 'Reviewer')]")
        print(f"Elements mentioning referee/reviewer: {len(referee_elements)}")
        for i, elem in enumerate(referee_elements[:5]):
            print(f"  {i+1}. {elem.tag_name}: '{elem.text[:50]}...'")

        # Save page source for analysis
        with open("mor_page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"\n💾 Page source saved to: mor_page_source.html")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        input("Press Enter to close browser...")
        driver.quit()

if __name__ == "__main__":
    debug_mor_html()