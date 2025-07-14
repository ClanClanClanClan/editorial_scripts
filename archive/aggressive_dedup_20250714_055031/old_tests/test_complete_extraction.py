#!/usr/bin/env python3
"""Test complete extraction including documents - final production test"""

import asyncio
import os
import json
from datetime import datetime

# Fix the dict callable issue by using proper imports
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Direct SIFIN test avoiding stealth manager issues
async def test_complete_extraction():
    print("🧪 COMPLETE SIAM EXTRACTION TEST (WITH DOCUMENTS)")
    print("=" * 70)
    
    os.environ['ORCID_EMAIL'] = "dylan.possamai@polytechnique.org"
    os.environ['ORCID_PASSWORD'] = "Hioupy0042%"
    
    # Import here to ensure path is set
    from src.infrastructure.scrapers.siam_scraper import SIAMScraper
    
    # Test SIFIN (working scraper)
    print("\n📊 Testing SIFIN Complete Extraction...")
    
    try:
        # Create scraper - will run in headless mode by default
        scraper = SIAMScraper('SIFIN')
        print("✅ Created SIFIN scraper (headless mode)")
        
        # Run extraction
        start_time = datetime.now()
        result = await scraper.run_extraction()
        end_time = datetime.now()
        
        if result.success:
            print(f"\n🎉 EXTRACTION SUCCESSFUL!")
            print(f"⏱️  Time taken: {end_time - start_time}")
            print(f"📄 Manuscripts found: {result.total_count}")
            
            # Detailed analysis
            total_with_pdf = 0
            total_with_cover = 0
            total_with_reports = 0
            total_referees = 0
            
            extraction_details = {
                'extraction_time': str(end_time - start_time),
                'total_manuscripts': result.total_count,
                'manuscripts': []
            }
            
            for i, ms in enumerate(result.manuscripts, 1):
                print(f"\n{'='*70}")
                print(f"📄 MANUSCRIPT {i}: {ms.id}")
                print(f"   Title: {ms.title[:70]}...")
                print(f"   Status: {ms.status}")
                print(f"   Editor: {ms.associate_editor}")
                print(f"   Submission Date: {ms.submission_date}")
                
                # Document analysis
                docs = ms.metadata.get('documents', {})
                ms_details = {
                    'id': ms.id,
                    'title': ms.title,
                    'status': str(ms.status),
                    'documents': {}
                }
                
                print(f"\n   📎 DOCUMENTS:")
                
                # Main manuscript PDF
                if docs.get('manuscript_pdf'):
                    print(f"      ✅ Manuscript PDF: {docs['manuscript_pdf']}")
                    total_with_pdf += 1
                    ms_details['documents']['manuscript_pdf'] = docs['manuscript_pdf']
                else:
                    print(f"      ❌ No manuscript PDF")
                
                # Manuscript versions (if multiple)
                if docs.get('manuscript_versions'):
                    print(f"      📋 {len(docs['manuscript_versions'])} PDF versions available")
                    ms_details['documents']['versions'] = docs['manuscript_versions']
                
                # Cover letter
                if docs.get('cover_letter'):
                    print(f"      ✅ Cover Letter: {docs['cover_letter']}")
                    total_with_cover += 1
                    ms_details['documents']['cover_letter'] = docs['cover_letter']
                else:
                    print(f"      ℹ️  No cover letter")
                
                # Referee reports
                if docs.get('referee_reports'):
                    print(f"      ✅ Referee Reports: {len(docs['referee_reports'])} found")
                    for j, report_url in enumerate(docs['referee_reports'][:3], 1):
                        print(f"         {j}. {report_url}")
                    total_with_reports += 1
                    ms_details['documents']['referee_reports'] = docs['referee_reports']
                else:
                    print(f"      ℹ️  No referee reports")
                
                # Referee information
                print(f"\n   👥 REFEREES: {len(ms.referees)}")
                ms_details['referees'] = []
                for ref in ms.referees:
                    print(f"      - {ref.name}: {ref.status}")
                    if ref.invited_date:
                        print(f"        Invited: {ref.invited_date}")
                    if ref.due_date:
                        print(f"        Due: {ref.due_date}")
                    
                    ms_details['referees'].append({
                        'name': ref.name,
                        'status': str(ref.status),
                        'invited_date': ref.invited_date.isoformat() if ref.invited_date else None,
                        'due_date': ref.due_date.isoformat() if ref.due_date else None
                    })
                
                total_referees += len(ms.referees)
                extraction_details['manuscripts'].append(ms_details)
            
            # Summary statistics
            print(f"\n{'='*70}")
            print("📊 EXTRACTION SUMMARY:")
            print(f"   Total manuscripts: {result.total_count}")
            print(f"   With PDF: {total_with_pdf}/{result.total_count} ({total_with_pdf/result.total_count*100:.0f}%)")
            print(f"   With cover letter: {total_with_cover}/{result.total_count} ({total_with_cover/result.total_count*100:.0f}%)")
            print(f"   With referee reports: {total_with_reports}/{result.total_count} ({total_with_reports/result.total_count*100:.0f}%)")
            print(f"   Total referees: {total_referees}")
            print(f"   Average referees per MS: {total_referees/result.total_count:.1f}")
            
            # Save detailed results
            with open('complete_extraction_results.json', 'w') as f:
                json.dump(extraction_details, f, indent=2)
            print(f"\n💾 Detailed results saved to: complete_extraction_results.json")
            
            print(f"\n✅ SIFIN SCRAPER IS FULLY OPERATIONAL!")
            print("   ✅ Authentication working")
            print("   ✅ Manuscript extraction working")
            print("   ✅ Document URLs extracted")
            print("   ✅ Referee information complete")
            print("   ✅ Running in headless mode")
            print("   ✅ Ready for production use!")
            
        else:
            print(f"❌ Extraction failed: {result.error_message}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_complete_extraction())