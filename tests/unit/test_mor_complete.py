#!/usr/bin/env python3
"""
Complete test of MOR functionality
"""

from journals.mor import MORJournal
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json

def test_mor_complete():
    """Test MOR with full functionality"""
    print("🔍 Testing MOR Complete Functionality")
    
    # Setup Chrome
    chrome_options = Options()
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print("1. Setting up MOR journal...")
        mor = MORJournal(driver)
        
        print("2. Logging in...")
        mor.login()
        
        print("3. Scraping manuscripts and emails...")
        manuscripts = mor.scrape_manuscripts_and_emails()
        
        print(f"\n✅ MOR Results:")
        print(f"   Total manuscripts: {len(manuscripts)}")
        
        # Detailed results
        total_referees = 0
        total_emails = 0
        total_cover_letters = 0
        total_reports = 0
        
        for ms in manuscripts:
            referees = ms.get('referees', [])
            total_referees += len(referees)
            
            emails_in_ms = 0
            for ref in referees:
                if ref.get('email'):
                    emails_in_ms += 1
                    total_emails += 1
            
            if ms.get('cover_letter_path'):
                total_cover_letters += 1
                
            if ms.get('referee_reports'):
                total_reports += len(ms.get('referee_reports', []))
            
            print(f"\n   Manuscript {ms['id']}:")
            print(f"     - Title: {ms['title'][:50]}...")
            print(f"     - Status: {ms.get('status', 'Unknown')}")
            print(f"     - Referees: {len(referees)}")
            print(f"     - Emails found: {emails_in_ms}")
            print(f"     - Cover letter: {'Yes' if ms.get('cover_letter_path') else 'No'}")
            print(f"     - Reports: {len(ms.get('referee_reports', []))}")
            
            # Show referee details
            for i, ref in enumerate(referees):
                print(f"       Referee {i+1}: {ref.get('name', 'Unknown')} - {ref.get('email', 'No email')} ({ref.get('status', 'Unknown')})")
        
        print(f"\n📊 Summary:")
        print(f"   - Total manuscripts: {len(manuscripts)}")
        print(f"   - Total referees: {total_referees}")
        print(f"   - Total emails extracted: {total_emails}")
        print(f"   - Total cover letters: {total_cover_letters}")
        print(f"   - Total referee reports: {total_reports}")
        
        # Save detailed results
        with open("mor_complete_test_results.json", "w") as f:
            json.dump({
                'success': True,
                'total_manuscripts': len(manuscripts),
                'total_referees': total_referees,
                'total_emails': total_emails,
                'total_cover_letters': total_cover_letters,
                'total_reports': total_reports,
                'manuscripts': manuscripts
            }, f, indent=2)
            
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        
        # Save error info
        with open("mor_complete_test_results.json", "w") as f:
            json.dump({
                'success': False,
                'error': str(e)
            }, f, indent=2)
    
    finally:
        driver.quit()

if __name__ == "__main__":
    test_mor_complete()