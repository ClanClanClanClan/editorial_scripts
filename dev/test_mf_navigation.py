#!/usr/bin/env python3
"""Quick test of MF navigation to Associate Editor Center."""

import sys
import os
from pathlib import Path

# Add production extractor to path
sys.path.append(str(Path(__file__).parent.parent / 'production' / 'src' / 'extractors'))
sys.path.append(str(Path(__file__).parent.parent / 'production' / 'src' / 'core'))

def test_navigation():
    """Test navigation to AE center."""
    print("🧪 Testing MF navigation to Associate Editor Center...")
    
    try:
        from mf_extractor import ComprehensiveMFExtractor
        
        extractor = ComprehensiveMFExtractor()
        
        # Test login only
        print("📝 Testing login...")
        login_success = extractor.login()
        
        if login_success:
            print("✅ Login successful")
            print(f"📍 Current URL: {extractor.driver.current_url}")
            
            # Try to navigate to AE center
            print("\n📋 Testing AE center navigation...")
            
            # Try direct URL first
            basic_url = "https://mc.manuscriptcentral.com/mf/associate_editor"
            print(f"🔗 Trying basic URL: {basic_url}")
            extractor.driver.get(basic_url)
            
            current_url = extractor.driver.current_url
            page_content = extractor.driver.page_source
            
            print(f"📍 Result URL: {current_url}")
            if "SITE_NOT_FOUND" in page_content:
                print("❌ Basic URL failed - SITE_NOT_FOUND")
                
                # Save the page for debugging
                with open("test_basic_url_fail.html", 'w') as f:
                    f.write(page_content)
                print("💾 Saved debug page to test_basic_url_fail.html")
                
                # Go back to the main page and look for the proper link
                print("\n🔄 Going back to main page to find proper AE link...")
                extractor.driver.get("https://mc.manuscriptcentral.com/mf/")
                
                page_source = extractor.driver.page_source
                
                # Save main page for analysis
                with open("test_main_page.html", 'w') as f:
                    f.write(page_source)
                print("💾 Saved main page to test_main_page.html")
                
                # Look for JavaScript patterns
                import re
                js_patterns = [
                    r"popWindow\('([^']*associate_editor[^']*)',",
                    r"href='([^']*associate_editor[^']*)'",
                    r'"([^"]*associate_editor[^"]*)"'
                ]
                
                found_urls = []
                for pattern in js_patterns:
                    matches = re.findall(pattern, page_source)
                    if matches:
                        found_urls.extend(matches)
                        print(f"✅ Found URLs with pattern: {pattern}")
                        for match in matches[:3]:  # Show first 3
                            print(f"   📎 {match}")
                
                if found_urls:
                    # Try the first found URL
                    test_url = found_urls[0]
                    if not test_url.startswith('http'):
                        test_url = f"https://mc.manuscriptcentral.com/{test_url.lstrip('/')}"
                    
                    print(f"\n🧪 Testing extracted URL: {test_url}")
                    extractor.driver.get(test_url)
                    
                    result_url = extractor.driver.current_url
                    result_content = extractor.driver.page_source
                    
                    print(f"📍 Result URL: {result_url}")
                    if "SITE_NOT_FOUND" not in result_content:
                        print("✅ Extracted URL worked!")
                        
                        # Look for categories
                        if "manuscript" in result_content.lower():
                            print("✅ Found manuscript-related content")
                        else:
                            print("⚠️ No manuscript content found")
                    else:
                        print("❌ Extracted URL also failed")
                else:
                    print("❌ No associate editor URLs found in JavaScript")
            else:
                print("✅ Basic URL worked!")
                
        else:
            print("❌ Login failed")
            
        # Clean up
        extractor.driver.quit()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_navigation()