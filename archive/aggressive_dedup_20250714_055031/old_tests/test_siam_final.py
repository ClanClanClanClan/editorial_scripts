#!/usr/bin/env python3
"""Final SIAM scraping test with minimal logging"""

import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.infrastructure.scrapers.siam_scraper import SIAMScraper

async def test_siam_final():
    print("🧪 FINAL SIAM SCRAPING TEST")
    print("=" * 60)
    
    os.environ['ORCID_EMAIL'] = "dylan.possamai@polytechnique.org"
    os.environ['ORCID_PASSWORD'] = "Hioupy0042%"
    
    results = {}
    
    for journal in ['SICON', 'SIFIN']:
        print(f"\n📊 Testing {journal}...")
        try:
            scraper = SIAMScraper(journal)
            result = await scraper.run_extraction()
            
            if result.success:
                print(f"✅ {journal}: SUCCESS - {result.total_count} manuscripts")
                if result.manuscripts:
                    for ms in result.manuscripts[:2]:
                        print(f"   - {ms.id}: {ms.title[:40]}...")
                results[journal] = True
            else:
                print(f"❌ {journal}: FAILED - {result.error_message}")
                results[journal] = False
                
        except Exception as e:
            print(f"❌ {journal}: ERROR - {e}")
            results[journal] = False
    
    print("\n" + "=" * 60)
    print("📊 FINAL RESULTS:")
    success_count = sum(1 for v in results.values() if v)
    print(f"✅ Successful: {success_count}/2")
    
    if success_count == 2:
        print("\n🎉 ALL SIAM SCRAPERS WORKING!")
    elif success_count == 1:
        print("\n⚠️ PARTIAL SUCCESS - One scraper working")
    else:
        print("\n❌ BOTH SCRAPERS NEED ATTENTION")

if __name__ == "__main__":
    asyncio.run(test_siam_final())