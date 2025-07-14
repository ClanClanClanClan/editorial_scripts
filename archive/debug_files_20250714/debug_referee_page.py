#!/usr/bin/env python3
"""
Debug what's on a referee detail page to understand name extraction
"""

import asyncio
import logging
import re
from unified_system.extractors.siam.sicon_real_fix import SICONRealExtractor

# Set up logging
logging.basicConfig(level=logging.INFO)

async def debug_referee_page():
    """Debug what's on a referee detail page"""
    
    print("🔍 DEBUGGING REFEREE DETAIL PAGE")
    print("=" * 50)
    
    try:
        extractor = SICONRealExtractor()
        
        # Initialize browser and login
        await extractor._init_browser(headless=False)
        await extractor._authenticate()
        
        # Navigate to a manuscript and get a referee biblio URL
        await extractor._navigate_to_manuscripts()
        manuscripts = await extractor._extract_manuscripts()
        
        if manuscripts and manuscripts[0].referees:
            referee = manuscripts[0].referees[0]
            if hasattr(referee, 'biblio_url'):
                print(f"\n📄 Examining referee: {referee.name}")
                print(f"   Biblio URL: {referee.biblio_url}")
                
                # Navigate to the referee detail page
                await extractor.page.goto(referee.biblio_url, wait_until="networkidle")
                await asyncio.sleep(2)
                
                content = await extractor.page.content()
                
                print(f"\n📋 Page content (first 2000 chars):")
                print(content[:2000])
                print("...")
                
                # Test the name patterns
                name_patterns = [
                    r'<b>Name:</b>\s*([^<]+)',
                    r'<b>Referee:</b>\s*([^<]+)',
                    r'<td[^>]*>\s*([A-Z][a-z]+\s+[A-Z][a-z]+)\s*</td>',
                    r'([A-Z][a-z]+,\s*[A-Z][a-z]+)',  # Last, First format
                ]
                
                print(f"\n🔍 Testing name extraction patterns:")
                for i, pattern in enumerate(name_patterns, 1):
                    matches = re.findall(pattern, content)
                    print(f"   Pattern {i}: {pattern}")
                    print(f"   Matches: {matches[:5]}")  # First 5 matches
                
                # Look for table structure
                print(f"\n📊 Looking for table data:")
                table_cells = re.findall(r'<td[^>]*>([^<]+)</td>', content)
                print(f"   All table cells: {table_cells[:10]}")  # First 10
        
        await extractor._cleanup()
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_referee_page())