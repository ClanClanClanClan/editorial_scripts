#!/usr/bin/env python3
"""
Debug SICON navigation to see what's on the page after login
"""

import asyncio
import logging
import re
from unified_system.extractors.siam.sicon_real_fix import SICONRealExtractor

# Set up logging
logging.basicConfig(level=logging.INFO)

async def debug_navigation():
    """Debug what's on the page after SICON login"""
    
    print("🔍 DEBUGGING SICON NAVIGATION")
    print("=" * 50)
    
    try:
        extractor = SICONRealExtractor()
        
        # Initialize browser and login
        await extractor._init_browser(headless=False)  # Use non-headless for debugging
        await extractor._authenticate()
        
        print("\n📄 Checking page content after login...")
        
        # Get page content
        content = await extractor.page.content()
        
        # Look for AE task patterns
        patterns = [
            r'Under Review\s+(\d+)\s+AE',
            r'All Pending Manuscripts\s+(\d+)\s+AE',
            r'Waiting for Revision\s+(\d+)\s+AE',
            r'Awaiting Referee Assignment\s+(\d+)\s+AE'
        ]
        
        print("\n🔍 Looking for AE task patterns:")
        found_any = False
        for pattern in patterns:
            matches = re.findall(pattern, content)
            if matches:
                print(f"✅ Found: {pattern} -> {matches}")
                found_any = True
            else:
                print(f"❌ Not found: {pattern}")
        
        if not found_any:
            print("\n📋 Page content preview (first 2000 chars):")
            print(content[:2000])
            print("\n...")
            
            # Look for any links with numbers
            print("\n🔗 Links with numbers:")
            link_pattern = r'<a[^>]*href="[^"]*"[^>]*>([^<]*\d+[^<]*)</a>'
            links = re.findall(link_pattern, content)
            for link in links[:10]:  # First 10
                print(f"  - {link}")
        
        await extractor._cleanup()
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_navigation())