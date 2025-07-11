#!/usr/bin/env python3
"""
Verify each journal individually to avoid timeout issues
"""

import subprocess
import sys
import time
from datetime import datetime

def run_journal_verification(journal_name):
    """Run verification for a single journal"""
    print(f"\n{'='*60}")
    print(f"🔍 Verifying {journal_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    try:
        # Create a separate script for each journal
        script_content = f"""
import sys
sys.path.append('.')
from journals.{journal_name.lower()} import {journal_name.upper()}Journal
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import traceback

def verify_{journal_name.lower()}():
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
        journal = {journal_name.upper()}Journal(driver)
        journal.login()
        manuscripts = journal.scrape_manuscripts_and_emails()
        
        print(f"✅ {journal_name.upper()} SUCCESS:")
        print(f"   - Manuscripts found: {{len(manuscripts)}}")
        
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
        
        print(f"   - Total referees: {{referee_count}}")
        print(f"   - Emails extracted: {{email_count}}")
        print(f"   - Cover letters: {{cover_letter_count}}")
        
        # Save results
        with open(f"{journal_name.lower()}_individual_result.txt", "w") as f:
            f.write(f"SUCCESS\\n")
            f.write(f"Manuscripts: {{len(manuscripts)}}\\n")
            f.write(f"Referees: {{referee_count}}\\n")
            f.write(f"Emails: {{email_count}}\\n")
            f.write(f"Cover Letters: {{cover_letter_count}}\\n")
            
    except Exception as e:
        print(f"❌ {journal_name.upper()} FAILED: {{e}}")
        traceback.print_exc()
        
        with open(f"{journal_name.lower()}_individual_result.txt", "w") as f:
            f.write(f"FAILED\\n")
            f.write(f"Error: {{str(e)}}\\n")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    verify_{journal_name.lower()}()
"""
        
        # Write temporary script
        script_file = f"temp_verify_{journal_name.lower()}.py"
        with open(script_file, "w") as f:
            f.write(script_content)
        
        # Run with timeout
        result = subprocess.run(
            [sys.executable, script_file],
            timeout=180,  # 3 minutes per journal
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
            
    except subprocess.TimeoutExpired:
        print(f"❌ {journal_name} timed out after 3 minutes")
        with open(f"{journal_name.lower()}_individual_result.txt", "w") as f:
            f.write("TIMEOUT\n")
    except Exception as e:
        print(f"❌ Error running {journal_name}: {e}")
        with open(f"{journal_name.lower()}_individual_result.txt", "w") as f:
            f.write(f"ERROR\n{str(e)}\n")
    finally:
        # Cleanup temp script
        try:
            import os
            os.remove(f"temp_verify_{journal_name.lower()}.py")
        except:
            pass

def main():
    """Run verification for all journals individually"""
    journals = ["SIFIN", "SICON", "MOR", "MF"]
    
    print("🚀 Starting Individual Journal Verification")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    for journal in journals:
        run_journal_verification(journal)
        time.sleep(2)  # Brief pause between journals
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 SUMMARY OF INDIVIDUAL RESULTS:")
    print(f"{'='*60}")
    
    for journal in journals:
        try:
            with open(f"{journal.lower()}_individual_result.txt", "r") as f:
                lines = f.readlines()
                status = lines[0].strip()
                print(f"\n{journal}: {status}")
                for line in lines[1:]:
                    print(f"  {line.strip()}")
        except:
            print(f"\n{journal}: NO RESULT FILE")

if __name__ == "__main__":
    main()