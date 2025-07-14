#!/usr/bin/env python3
"""
Debug what's on SICON category pages
"""

import asyncio
import logging
import re
from unified_system.extractors.siam.sicon_real_fix import SICONRealExtractor

# Set up logging
logging.basicConfig(level=logging.INFO)

async def debug_category_pages():
    """Debug what's on the category pages"""
    
    print("🔍 DEBUGGING SICON CATEGORY PAGES")
    print("=" * 50)
    
    try:
        extractor = SICONRealExtractor()
        
        # Initialize browser and login
        await extractor._init_browser(headless=False)
        await extractor._authenticate()
        
        print("\n📄 Getting AE links...")
        
        # Get main page content
        content = await extractor.page.content()
        ae_links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*?(\d+)\s+AE[^<]*)</a>', content)
        
        for i, (href, link_text, count) in enumerate(ae_links):
            if int(count) > 0:
                print(f"\n📂 Investigating link {i+1}: '{link_text.strip()}' ({count} manuscripts)")
                print(f"   URL: {href}")
                
                try:
                    # Click the link
                    full_url = href if href.startswith('http') else f"{extractor.base_url}/{href}"
                    await extractor.page.goto(full_url, wait_until="networkidle")
                    await asyncio.sleep(3)
                    
                    # Get page content
                    category_content = await extractor.page.content()
                    
                    # Look for manuscript patterns
                    print("\n   🔍 Looking for manuscript patterns:")
                    
                    # Pattern 1: /m/M123456
                    ms_ids_1 = re.findall(r'/m/(M\d+)', category_content)
                    print(f"   - Pattern '/m/(M\\d+)': {len(ms_ids_1)} found: {ms_ids_1[:5]}")
                    
                    # Pattern 2: M123456 standalone
                    ms_ids_2 = re.findall(r'\b(M\d{6})\b', category_content)
                    print(f"   - Pattern 'M\\d{{6}}': {len(ms_ids_2)} found: {ms_ids_2[:5]}")
                    
                    # Pattern 3: Any links with manuscript-like text
                    ms_links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*(?:M\d+|manuscript|Manuscript)[^<]*)</a>', category_content, re.I)
                    print(f"   - Links with 'M' or 'manuscript': {len(ms_links)} found")
                    for j, (link_href, link_text) in enumerate(ms_links[:3]):
                        print(f"     {j+1}. {link_text.strip()} -> {link_href}")
                    
                    # Show first part of page content
                    print(f"\n   📋 Page content preview (first 1000 chars):")
                    print(category_content[:1000])
                    print("   ...")
                    
                    break  # Just examine first category for now
                    
                except Exception as e:
                    print(f"   ❌ Error: {e}")
        
        await extractor._cleanup()
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_category_pages())