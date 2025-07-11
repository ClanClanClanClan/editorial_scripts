#!/usr/bin/env python3
"""
Save SICON and SIFIN dashboard HTML after login for analysis
"""

import os
import time
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys


def save_dashboard_html():
    """Login and save dashboard HTML."""
    
    output_dir = Path(f'./dashboard_html_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
    output_dir.mkdir(exist_ok=True)
    
    chrome_options = Options()
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 30)
    
    try:
        # SICON
        print("🔐 Logging into SICON...")
        driver.get("http://sicon.siam.org")
        time.sleep(3)
        
        # Remove cookie banners
        driver.execute_script("""
            var elements = ['#cookie-policy-layer-bg', '#cookie-policy-layer'];
            elements.forEach(function(sel) {
                var els = document.querySelectorAll(sel);
                els.forEach(function(el) { el.remove(); });
            });
        """)
        
        # Click ORCID
        orcid_link = driver.find_element(By.XPATH, "//a[contains(@href, 'orcid')]")
        driver.execute_script("arguments[0].click();", orcid_link)
        
        # Wait for ORCID
        wait.until(lambda driver: 'orcid.org' in driver.current_url)
        time.sleep(2)
        
        # Fill credentials
        orcid_user = os.getenv("ORCID_USER")
        orcid_pass = os.getenv("ORCID_PASS")
        
        username_field = driver.find_element(By.ID, "username-input")
        username_field.clear()
        username_field.send_keys(orcid_user)
        
        password_field = driver.find_element(By.ID, "password")
        password_field.clear()
        password_field.send_keys(orcid_pass)
        password_field.send_keys(Keys.RETURN)
        
        print("⏳ Waiting for authentication...")
        wait.until(lambda driver: 'sicon.siam.org' in driver.current_url)
        time.sleep(5)
        
        print("✅ Authenticated with SICON")
        
        # Save SICON dashboard
        with open(output_dir / "sicon_dashboard.html", 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        
        # Take screenshot
        driver.save_screenshot(str(output_dir / "sicon_dashboard.png"))
        
        print(f"💾 Saved SICON dashboard to {output_dir}")
        
        # Check what we see
        page_text = driver.page_source.lower()
        print("\n📋 SICON Page Analysis:")
        print(f"  - Contains 'associate editor': {'associate editor' in page_text}")
        print(f"  - Contains 'manuscript': {'manuscript' in page_text}")
        print(f"  - Contains 'M174': {'m174' in page_text}")
        print(f"  - Contains 'referee': {'referee' in page_text}")
        
        # SIFIN
        print("\n🔐 Logging into SIFIN...")
        driver.get("http://sifin.siam.org")
        time.sleep(3)
        
        # Remove banners
        driver.execute_script("""
            var elements = ['#cookie-policy-layer-bg', '#cookie-policy-layer'];
            elements.forEach(function(sel) {
                var els = document.querySelectorAll(sel);
                els.forEach(function(el) { el.remove(); });
            });
        """)
        
        # Click ORCID
        orcid_link = driver.find_element(By.XPATH, "//a[contains(@href, 'orcid')]")
        driver.execute_script("arguments[0].click();", orcid_link)
        
        # Wait for ORCID
        wait.until(lambda driver: 'orcid.org' in driver.current_url)
        time.sleep(2)
        
        # Fill credentials
        username_field = driver.find_element(By.ID, "username-input")
        username_field.clear()
        username_field.send_keys(orcid_user)
        
        password_field = driver.find_element(By.ID, "password")
        password_field.clear()
        password_field.send_keys(orcid_pass)
        password_field.send_keys(Keys.RETURN)
        
        print("⏳ Waiting for authentication...")
        wait.until(lambda driver: 'sifin.siam.org' in driver.current_url)
        time.sleep(5)
        
        print("✅ Authenticated with SIFIN")
        
        # Save SIFIN dashboard
        with open(output_dir / "sifin_dashboard.html", 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        
        # Take screenshot
        driver.save_screenshot(str(output_dir / "sifin_dashboard.png"))
        
        print(f"💾 Saved SIFIN dashboard to {output_dir}")
        
        # Check what we see
        page_text = driver.page_source.lower()
        print("\n📋 SIFIN Page Analysis:")
        print(f"  - Contains 'associate editor': {'associate editor' in page_text}")
        print(f"  - Contains 'manuscript': {'manuscript' in page_text}")
        print(f"  - Contains 'M174': {'m174' in page_text}")
        print(f"  - Contains 'referee': {'referee' in page_text}")
        
        print(f"\n📁 All files saved to: {output_dir}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        driver.quit()


if __name__ == "__main__":
    save_dashboard_html()