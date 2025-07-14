#!/usr/bin/env python3
"""Test SICON scraper with fixes"""

import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_sicon_fix():
    print("🧪 TESTING SICON FIX")
    print("=" * 50)
    
    os.environ['ORCID_EMAIL'] = "dylan.possamai@polytechnique.org"
    os.environ['ORCID_PASSWORD'] = "Hioupy0042%"
    
    # Import after path setup
    from src.infrastructure.scrapers.siam_scraper import SIAMScraper
    
    try:
        # Create SICON scraper
        print("📊 Creating SICON scraper...")
        scraper = SIAMScraper('SICON')
        print("✅ Scraper created successfully")
        
        # Check stealth manager
        print(f"🔍 Stealth manager type: {type(scraper.stealth_manager)}")
        print(f"🔍 Stealth manager methods: {[m for m in dir(scraper.stealth_manager) if not m.startswith('_')]}")
        
        # Run extraction
        print("\n🔄 Running extraction...")
        result = await scraper.run_extraction()
        
        if result.success:
            print(f"✅ SUCCESS! Found {result.total_count} manuscripts")
            for ms in result.manuscripts:
                print(f"  - {ms.id}: {ms.title[:50]}...")
                docs = ms.metadata.get('documents', {})
                if docs.get('manuscript_pdf'):
                    print(f"    📎 PDF: {docs['manuscript_pdf']}")
        else:
            print(f"❌ FAILED: {result.error_message}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_sicon_fix())