#!/usr/bin/env python3
"""
Deep debugging test for browser-based journals to verify actual login and data scraping
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def create_browser(headless=False):
    """Create a Chrome browser instance"""
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1200,800")
    
    # Add user agent to avoid detection
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    return webdriver.Chrome(options=options)

def test_mf_journal_deep():
    """Deep test of MF journal with actual login attempt"""
    print("🔍 DEEP TESTING MF JOURNAL")
    print("=" * 40)
    
    driver = None
    try:
        driver = create_browser(headless=False)  # Use visible browser for debugging
        
        from journals.mf import MFJournal
        mf = MFJournal(driver)
        
        print("✅ MF Journal instantiated successfully")
        print(f"✅ Driver created: {driver}")
        
        # Test the login process step by step
        print("\n🔐 Testing MF Login Process:")
        
        # Step 1: Check if we can reach the login page
        print("  1. Attempting to navigate to MF login page...")
        try:
            mf.login()
            print("  ✅ Login method completed without error")
        except Exception as e:
            print(f"  ❌ Login failed: {e}")
            
        # Step 2: Check current page
        print(f"  2. Current URL: {driver.current_url}")
        print(f"  3. Page title: {driver.title}")
        
        # Step 3: Try to scrape manuscripts
        print("\n📋 Testing MF Manuscript Scraping:")
        try:
            manuscripts = mf.scrape_manuscripts_and_emails()
            print(f"  ✅ Scraping completed: {len(manuscripts)} manuscripts found")
            
            if len(manuscripts) > 0:
                print("  📄 Sample manuscript data:")
                for i, ms in enumerate(manuscripts[:2]):
                    print(f"    {i+1}. {ms.get('Manuscript #', 'Unknown')}: {ms.get('Title', 'No title')}")
                    print(f"       Stage: {ms.get('Current Stage', 'Unknown')}")
                    print(f"       Referees: {len(ms.get('Referees', []))}")
                return True
            else:
                print("  ⚠️ No manuscripts found - may need authentication")
                return False
                
        except Exception as e:
            print(f"  ❌ Scraping failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ MF Journal setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver:
            driver.quit()

def test_mor_journal_deep():
    """Deep test of MOR journal with actual login attempt"""
    print("\n🔍 DEEP TESTING MOR JOURNAL")
    print("=" * 40)
    
    driver = None
    try:
        driver = create_browser(headless=False)
        
        from journals.mor import MORJournal
        mor = MORJournal(driver)
        
        print("✅ MOR Journal instantiated successfully")
        
        # Test the login process
        print("\n🔐 Testing MOR Login Process:")
        
        print("  1. Attempting to navigate to MOR login page...")
        try:
            mor.login()
            print("  ✅ Login method completed without error")
        except Exception as e:
            print(f"  ❌ Login failed: {e}")
            
        print(f"  2. Current URL: {driver.current_url}")
        print(f"  3. Page title: {driver.title}")
        
        # Try to scrape manuscripts
        print("\n📋 Testing MOR Manuscript Scraping:")
        try:
            manuscripts = mor.scrape_manuscripts_and_emails()
            print(f"  ✅ Scraping completed: {len(manuscripts)} manuscripts found")
            
            if len(manuscripts) > 0:
                print("  📄 Sample manuscript data:")
                for i, ms in enumerate(manuscripts[:2]):
                    print(f"    {i+1}. {ms.get('Manuscript #', 'Unknown')}: {ms.get('Title', 'No title')}")
                    print(f"       Stage: {ms.get('Current Stage', 'Unknown')}")
                    print(f"       Referees: {len(ms.get('Referees', []))}")
                return True
            else:
                print("  ⚠️ No manuscripts found - may need authentication")
                return False
                
        except Exception as e:
            print(f"  ❌ Scraping failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ MOR Journal setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver:
            driver.quit()

def test_naco_journal_deep():
    """Deep test of NACO journal with actual login attempt"""
    print("\n🔍 DEEP TESTING NACO JOURNAL")
    print("=" * 40)
    
    driver = None
    try:
        driver = create_browser(headless=False)
        
        from journals.naco import NACOJournal
        naco = NACOJournal(driver)
        
        print("✅ NACO Journal instantiated successfully")
        
        # Test the login process
        print("\n🔐 Testing NACO Login Process:")
        
        print("  1. Attempting to navigate to NACO login page...")
        try:
            naco.login()
            print("  ✅ Login method completed without error")
        except Exception as e:
            print(f"  ❌ Login failed: {e}")
            
        print(f"  2. Current URL: {driver.current_url}")
        print(f"  3. Page title: {driver.title}")
        
        # Try to scrape manuscripts
        print("\n📋 Testing NACO Manuscript Scraping:")
        try:
            manuscripts = naco.scrape_manuscripts_and_emails()
            print(f"  ✅ Scraping completed: {len(manuscripts)} manuscripts found")
            
            if len(manuscripts) > 0:
                print("  📄 Sample manuscript data:")
                for i, ms in enumerate(manuscripts[:2]):
                    print(f"    {i+1}. {ms.get('Manuscript #', 'Unknown')}: {ms.get('Title', 'No title')}")
                    print(f"       Stage: {ms.get('Current Stage', 'Unknown')}")
                    print(f"       Referees: {len(ms.get('Referees', []))}")
                return True
            else:
                print("  ⚠️ No manuscripts found")
                return False
                
        except Exception as e:
            print(f"  ❌ Scraping failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ NACO Journal setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver:
            driver.quit()

def test_sicon_journal_deep():
    """Deep test of SICON journal with actual login attempt"""
    print("\n🔍 DEEP TESTING SICON JOURNAL")
    print("=" * 40)
    
    driver = None
    try:
        driver = create_browser(headless=False)
        
        from journals.sicon import SICONJournal
        sicon = SICONJournal(driver)
        
        print("✅ SICON Journal instantiated successfully")
        
        # Test the login process
        print("\n🔐 Testing SICON Login Process:")
        
        print("  1. Attempting to navigate to SICON login page...")
        try:
            sicon.login()
            print("  ✅ Login method completed without error")
        except Exception as e:
            print(f"  ❌ Login failed: {e}")
            
        print(f"  2. Current URL: {driver.current_url}")
        print(f"  3. Page title: {driver.title}")
        
        # Try to scrape manuscripts
        print("\n📋 Testing SICON Manuscript Scraping:")
        try:
            manuscripts = sicon.scrape_manuscripts_and_emails()
            print(f"  ✅ Scraping completed: {len(manuscripts)} manuscripts found")
            
            if len(manuscripts) > 0:
                print("  📄 Sample manuscript data:")
                for i, ms in enumerate(manuscripts[:2]):
                    print(f"    {i+1}. {ms.get('Manuscript #', 'Unknown')}: {ms.get('Title', 'No title')}")
                    print(f"       Stage: {ms.get('Current Stage', 'Unknown')}")
                    print(f"       Referees: {len(ms.get('Referees', []))}")
                return True
            else:
                print("  ⚠️ No manuscripts found")
                return False
                
        except Exception as e:
            print(f"  ❌ Scraping failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ SICON Journal setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver:
            driver.quit()

def test_sifin_journal_deep():
    """Deep test of SIFIN journal with actual login attempt"""
    print("\n🔍 DEEP TESTING SIFIN JOURNAL")
    print("=" * 40)
    
    driver = None
    try:
        driver = create_browser(headless=False)
        
        from journals.sifin import SIFINJournal
        sifin = SIFINJournal(driver)
        
        print("✅ SIFIN Journal instantiated successfully")
        
        # Test the login process
        print("\n🔐 Testing SIFIN Login Process:")
        
        print("  1. Attempting to navigate to SIFIN login page...")
        try:
            sifin.login()
            print("  ✅ Login method completed without error")
        except Exception as e:
            print(f"  ❌ Login failed: {e}")
            
        print(f"  2. Current URL: {driver.current_url}")
        print(f"  3. Page title: {driver.title}")
        
        # Try to scrape manuscripts
        print("\n📋 Testing SIFIN Manuscript Scraping:")
        try:
            manuscripts = sifin.scrape_manuscripts_and_emails()
            print(f"  ✅ Scraping completed: {len(manuscripts)} manuscripts found")
            
            if len(manuscripts) > 0:
                print("  📄 Sample manuscript data:")
                for i, ms in enumerate(manuscripts[:2]):
                    print(f"    {i+1}. {ms.get('Manuscript #', 'Unknown')}: {ms.get('Title', 'No title')}")
                    print(f"       Stage: {ms.get('Current Stage', 'Unknown')}")
                    print(f"       Referees: {len(ms.get('Referees', []))}")
                return True
            else:
                print("  ⚠️ No manuscripts found")
                return False
                
        except Exception as e:
            print(f"  ❌ Scraping failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ SIFIN Journal setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver:
            driver.quit()

def test_mafe_journal_deep():
    """Deep test of MAFE journal with actual login attempt"""
    print("\n🔍 DEEP TESTING MAFE JOURNAL")
    print("=" * 40)
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            
            from journals.mafe import MAFEJournal
            mafe = MAFEJournal(page)
            
            print("✅ MAFE Journal instantiated successfully")
            
            # Test the login process
            print("\n🔐 Testing MAFE Login Process:")
            
            print("  1. Attempting to navigate to MAFE login page...")
            try:
                mafe.login()
                print("  ✅ Login method completed without error")
            except Exception as e:
                print(f"  ❌ Login failed: {e}")
                
            print(f"  2. Current URL: {page.url}")
            print(f"  3. Page title: {page.title()}")
            
            # Try to scrape manuscripts
            print("\n📋 Testing MAFE Manuscript Scraping:")
            try:
                manuscripts = mafe.scrape_manuscripts_and_emails()
                print(f"  ✅ Scraping completed: {len(manuscripts)} manuscripts found")
                
                if len(manuscripts) > 0:
                    print("  📄 Sample manuscript data:")
                    for i, ms in enumerate(manuscripts[:2]):
                        print(f"    {i+1}. {ms.get('Manuscript #', 'Unknown')}: {ms.get('Title', 'No title')}")
                        print(f"       Stage: {ms.get('Current Stage', 'Unknown')}")
                        print(f"       Referees: {len(ms.get('Referees', []))}")
                    browser.close()
                    return True
                else:
                    print("  ⚠️ No manuscripts found")
                    browser.close()
                    return False
                    
            except Exception as e:
                print(f"  ❌ Scraping failed: {e}")
                import traceback
                traceback.print_exc()
                browser.close()
                return False
                
    except Exception as e:
        print(f"❌ MAFE Journal setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run deep tests for all browser-based journals"""
    print("🚀 DEEP BROWSER JOURNAL TESTING")
    print("This will test actual login and data scraping for all browser-based journals")
    print("=" * 80)
    
    results = {}
    
    # Test each journal
    results['MF'] = test_mf_journal_deep()
    results['MOR'] = test_mor_journal_deep()
    results['NACO'] = test_naco_journal_deep()
    results['SICON'] = test_sicon_journal_deep()
    results['SIFIN'] = test_sifin_journal_deep()
    results['MAFE'] = test_mafe_journal_deep()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 DEEP TESTING RESULTS SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for journal, result in results.items():
        status = "✅ SUCCESS - LOGIN AND DATA SCRAPING WORKING" if result else "❌ FAILED - LOGIN OR SCRAPING ISSUES"
        print(f"{journal:8s}: {status}")
    
    print(f"\nOverall: {passed}/{total} browser-based journals fully working")
    
    if passed == total:
        print("🎉 ALL BROWSER-BASED JOURNALS FULLY FUNCTIONAL!")
    else:
        print("⚠️ Some journals need debugging for login/scraping")

if __name__ == "__main__":
    main()