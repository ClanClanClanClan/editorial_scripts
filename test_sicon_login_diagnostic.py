#!/usr/bin/env python3
"""
SICON Login Diagnostic Test

Diagnoses the current SICON login page to understand available authentication methods
and what's preventing the extraction from working.
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv(project_root / ".env.production")

def diagnose_sicon_login():
    """Diagnose the SICON login page to understand authentication options."""
    
    print("🔍 SICON Login Diagnostic Test")
    print("=" * 50)
    
    try:
        import undetected_chromedriver as uc
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from bs4 import BeautifulSoup
        
        # Create browser
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        print("🌐 Creating browser...")
        driver = uc.Chrome(options=options)
        
        try:
            # Navigate to SICON
            sicon_url = "https://sicon.siam.org/cgi-bin/main.plex"
            print(f"📍 Navigating to: {sicon_url}")
            driver.get(sicon_url)
            time.sleep(5)
            
            print(f"✅ Page loaded: {driver.title}")
            print(f"🌐 Current URL: {driver.current_url}")
            
            # Save page source for analysis
            output_dir = project_root / "output" / "sicon_diagnostic"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            page_source_file = output_dir / "sicon_page_source.html"
            with open(page_source_file, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            
            print(f"💾 Page source saved to: {page_source_file}")
            
            # Analyze page content
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            print("\n🔍 AUTHENTICATION OPTIONS ANALYSIS:")
            print("-" * 40)
            
            # Look for ORCID mentions
            orcid_mentions = soup.find_all(text=lambda text: text and 'orcid' in text.lower())
            if orcid_mentions:
                print(f"✅ Found {len(orcid_mentions)} ORCID mentions:")
                for mention in orcid_mentions[:3]:
                    print(f"   '{mention.strip()}'")
            else:
                print("❌ No ORCID mentions found")
            
            # Look for login buttons
            login_buttons = []
            for tag in ['button', 'input', 'a']:
                elements = soup.find_all(tag)
                for elem in elements:
                    text = elem.get_text().lower() if elem.get_text() else ''
                    attrs = ' '.join([f"{k}={v}" for k, v in elem.attrs.items() if isinstance(v, str)])
                    
                    if any(keyword in text or keyword in attrs.lower() for keyword in ['login', 'sign in', 'orcid', 'authenticate']):
                        login_buttons.append({
                            'tag': tag,
                            'text': elem.get_text().strip(),
                            'attrs': dict(elem.attrs) if hasattr(elem, 'attrs') else {}
                        })
            
            if login_buttons:
                print(f"\n✅ Found {len(login_buttons)} potential login elements:")
                for i, button in enumerate(login_buttons[:5]):
                    print(f"   {i+1}. <{button['tag']}> '{button['text']}'")
                    if button['attrs']:
                        print(f"      Attributes: {button['attrs']}")
            else:
                print("\n❌ No login buttons found")
            
            # Look for forms
            forms = soup.find_all('form')
            if forms:
                print(f"\n📝 Found {len(forms)} forms:")
                for i, form in enumerate(forms):
                    action = form.get('action', 'No action')
                    method = form.get('method', 'No method')
                    inputs = form.find_all('input')
                    print(f"   Form {i+1}: action='{action}' method='{method}' inputs={len(inputs)}")
            else:
                print("\n❌ No forms found")
            
            # Look for redirect or JavaScript
            scripts = soup.find_all('script')
            if scripts:
                print(f"\n🔧 Found {len(scripts)} scripts (may contain redirects)")
                
                # Check for common redirect patterns
                for script in scripts:
                    if script.string:
                        script_content = script.string.lower()
                        if any(keyword in script_content for keyword in ['redirect', 'location.href', 'window.location']):
                            print("   ⚠️  Potential redirect script found")
            
            # Check for meta redirects
            meta_redirects = soup.find_all('meta', attrs={'http-equiv': 'refresh'})
            if meta_redirects:
                print(f"\n🔄 Found {len(meta_redirects)} meta redirects")
                for meta in meta_redirects:
                    print(f"   Content: {meta.get('content', 'No content')}")
            
            # Look for error messages
            page_text = soup.get_text().lower()
            error_keywords = ['error', 'not found', 'unavailable', 'maintenance', 'temporarily down']
            found_errors = [keyword for keyword in error_keywords if keyword in page_text]
            if found_errors:
                print(f"\n⚠️  Potential issues found: {found_errors}")
            
            # Check for journal-specific elements
            journal_indicators = ['sicon', 'siamjco', 'siam', 'control', 'optimization']
            found_indicators = [indicator for indicator in journal_indicators if indicator in page_text]
            if found_indicators:
                print(f"\n✅ Journal indicators found: {found_indicators}")
            else:
                print("\n❌ No SICON/SIAM indicators found - may be wrong page")
            
            # Save diagnostic summary
            diagnostic_summary = {
                'timestamp': datetime.now().isoformat(),
                'url': driver.current_url,
                'title': driver.title,
                'orcid_mentions': len(orcid_mentions),
                'login_buttons': len(login_buttons),
                'forms': len(forms),
                'scripts': len(scripts),
                'meta_redirects': len(meta_redirects),
                'potential_errors': found_errors,
                'journal_indicators': found_indicators,
                'page_size': len(driver.page_source)
            }
            
            import json
            summary_file = output_dir / "diagnostic_summary.json"
            with open(summary_file, 'w') as f:
                json.dump(diagnostic_summary, f, indent=2)
            
            print(f"\n💾 Diagnostic summary saved to: {summary_file}")
            
            # Final assessment
            print("\n🎯 DIAGNOSTIC ASSESSMENT:")
            print("-" * 30)
            
            if orcid_mentions and login_buttons:
                print("✅ ORCID authentication appears available")
                print("🔧 Recommendation: Debug ORCID button detection logic")
            elif login_buttons:
                print("⚠️  Login options found but no ORCID")
                print("🔧 Recommendation: Check for alternative authentication")
            elif found_errors:
                print("❌ Site appears to have issues")
                print("🔧 Recommendation: Try again later or check site status")
            else:
                print("❌ No clear authentication path found")
                print("🔧 Recommendation: Manual inspection needed")
            
            return True
            
        finally:
            driver.quit()
            print("🖥️  Browser closed")
            
    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run SICON login diagnostic."""
    
    # Check credentials
    orcid_email = os.getenv('ORCID_EMAIL')
    orcid_password = os.getenv('ORCID_PASSWORD')
    
    if not orcid_email or not orcid_password:
        print("❌ Missing ORCID credentials in environment")
        return False
    
    print(f"🔐 Credentials found for: {orcid_email}")
    
    success = diagnose_sicon_login()
    
    if success:
        print("\n✅ Diagnostic completed successfully")
        print("\nNext steps:")
        print("1. Review the saved page source and diagnostic summary")
        print("2. Update authentication logic based on findings")
        print("3. Test specific login elements manually if needed")
    else:
        print("\n❌ Diagnostic failed")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)