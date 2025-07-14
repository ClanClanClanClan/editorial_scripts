
import sys
sys.path.append('.')
from journals.mf import MFJournal
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import traceback

def verify_mf():
    chrome_options = Options()
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-background-timer-throttling')
    chrome_options.add_argument('--disable-backgrounding-occluded-windows')
    chrome_options.add_argument('--disable-renderer-backgrounding')
    chrome_options.add_argument('--disable-features=TranslateUI')
    chrome_options.add_argument('--disable-ipc-flooding-protection')
    chrome_options.add_argument('--max_old_space_size=4096')
    chrome_options.add_argument('--memory-pressure-off')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        journal = MFJournal(driver)
        journal.login()
        manuscripts = journal.scrape_manuscripts_and_emails()
        
        print(f"✅ MF SUCCESS:")
        print(f"   - Manuscripts found: {len(manuscripts)}")
        
        referee_count = 0
        email_count = 0
        cover_letter_count = 0
        
        for ms in manuscripts:
            referee_count += len(ms.get('referees', []))
            for ref in ms.get('referees', []):
                if ref.get('email'):
                    email_count += 1
            if ms.get('cover_letter_path'):
                cover_letter_count += 1
        
        print(f"   - Total referees: {referee_count}")
        print(f"   - Emails extracted: {email_count}")
        print(f"   - Cover letters: {cover_letter_count}")
        
        # Save results
        with open(f"mf_individual_result.txt", "w") as f:
            f.write(f"SUCCESS\n")
            f.write(f"Manuscripts: {len(manuscripts)}\n")
            f.write(f"Referees: {referee_count}\n")
            f.write(f"Emails: {email_count}\n")
            f.write(f"Cover Letters: {cover_letter_count}\n")
            
    except Exception as e:
        print(f"❌ MF FAILED: {e}")
        traceback.print_exc()
        
        with open(f"mf_individual_result.txt", "w") as f:
            f.write(f"FAILED\n")
            f.write(f"Error: {str(e)}\n")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    verify_mf()
