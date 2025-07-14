#!/usr/bin/env python3
"""Test SICON specifically to debug bot detection"""

import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.infrastructure.scrapers.siam_scraper import SIAMScraper

async def test_sicon():
    print("🧪 TESTING SICON SCRAPER SPECIFICALLY")
    print("=" * 50)
    
    os.environ['ORCID_EMAIL'] = "dylan.possamai@polytechnique.org"
    os.environ['ORCID_PASSWORD'] = "Hioupy0042%"
    
    try:
        # Create SICON scraper with debug logging
        import logging
        logging.basicConfig(level=logging.DEBUG)
        
        scraper = SIAMScraper('SICON')
        print("✅ Created SICON scraper")
        
        # Run extraction
        print("🔄 Running SICON extraction...")
        result = await scraper.run_extraction()
        
        if result.success:
            print(f"🎉 SUCCESS! Found {result.total_count} manuscripts")
            for ms in result.manuscripts[:3]:
                print(f"  - {ms.id}: {ms.title[:50]}...")
        else:
            print(f"❌ FAILED: {result.error_message}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_sicon())