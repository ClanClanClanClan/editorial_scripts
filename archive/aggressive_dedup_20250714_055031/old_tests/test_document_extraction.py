#!/usr/bin/env python3
"""Test document extraction - PDFs, cover letters, referee reports"""

import asyncio
import os
import sys
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.infrastructure.scrapers.siam_scraper import SIAMScraper

async def test_document_extraction():
    print("🧪 TESTING DOCUMENT EXTRACTION (PDFs, Cover Letters, Reports)")
    print("=" * 70)
    
    os.environ['ORCID_EMAIL'] = "dylan.possamai@polytechnique.org"
    os.environ['ORCID_PASSWORD'] = "Hioupy0042%"
    
    # Focus on SIFIN since it's working
    print("\n📊 Testing SIFIN Document Extraction...")
    
    try:
        scraper = SIAMScraper('SIFIN')
        result = await scraper.run_extraction()
        
        if result.success:
            print(f"✅ SIFIN extraction successful - {result.total_count} manuscripts")
            
            # Detailed document analysis
            for i, ms in enumerate(result.manuscripts, 1):
                print(f"\n📄 Manuscript {i}: {ms.id}")
                print(f"   Title: {ms.title[:60]}...")
                print(f"   Status: {ms.status}")
                print(f"   Referees: {len(ms.referees)}")
                
                # Check metadata for documents
                documents = ms.metadata.get('documents', {})
                print(f"\n   📎 Documents found:")
                
                if documents:
                    # Manuscript PDF
                    if 'manuscript_pdf' in documents:
                        print(f"      ✅ Manuscript PDF: {documents['manuscript_pdf']}")
                    else:
                        print(f"      ❌ No manuscript PDF URL")
                    
                    # Cover letter
                    if 'cover_letter' in documents:
                        print(f"      ✅ Cover Letter: {documents['cover_letter']}")
                    else:
                        print(f"      ℹ️  No cover letter")
                    
                    # Referee reports
                    if 'referee_reports' in documents:
                        reports = documents['referee_reports']
                        print(f"      ✅ Referee Reports: {len(reports)} found")
                        for j, report in enumerate(reports[:3], 1):
                            print(f"         {j}. {report}")
                    else:
                        print(f"      ℹ️  No referee reports")
                    
                    # Other documents
                    other_docs = [k for k in documents.keys() 
                                 if k not in ['manuscript_pdf', 'cover_letter', 'referee_reports']]
                    if other_docs:
                        print(f"      📄 Other documents: {', '.join(other_docs)}")
                else:
                    print(f"      ❌ No documents found in metadata")
                
                # Also check referees for any attached reports
                print(f"\n   👥 Referee details:")
                for ref in ms.referees[:3]:
                    print(f"      - {ref.name}: {ref.status}")
                    if hasattr(ref, 'report_url') and ref.report_url:
                        print(f"        📎 Report: {ref.report_url}")
                
                print("-" * 70)
                
                # Only show first 2 manuscripts in detail
                if i >= 2:
                    if result.total_count > 2:
                        print(f"\n... and {result.total_count - 2} more manuscripts")
                    break
            
            # Summary
            print("\n📊 DOCUMENT EXTRACTION SUMMARY:")
            total_ms = len(result.manuscripts)
            ms_with_pdf = sum(1 for ms in result.manuscripts 
                            if ms.metadata.get('documents', {}).get('manuscript_pdf'))
            ms_with_cover = sum(1 for ms in result.manuscripts 
                              if ms.metadata.get('documents', {}).get('cover_letter'))
            ms_with_reports = sum(1 for ms in result.manuscripts 
                                if ms.metadata.get('documents', {}).get('referee_reports'))
            
            print(f"   Total manuscripts: {total_ms}")
            print(f"   With PDF URLs: {ms_with_pdf}/{total_ms}")
            print(f"   With cover letters: {ms_with_cover}/{total_ms}")
            print(f"   With referee reports: {ms_with_reports}/{total_ms}")
            
            # Save detailed results
            with open('sifin_extraction_details.json', 'w') as f:
                extraction_data = {
                    'total_manuscripts': total_ms,
                    'manuscripts': [
                        {
                            'id': ms.id,
                            'title': ms.title,
                            'documents': ms.metadata.get('documents', {}),
                            'referees': [
                                {
                                    'name': ref.name,
                                    'status': str(ref.status),
                                    'invited_date': ref.invited_date.isoformat() if ref.invited_date else None,
                                    'due_date': ref.due_date.isoformat() if ref.due_date else None
                                }
                                for ref in ms.referees
                            ]
                        }
                        for ms in result.manuscripts
                    ]
                }
                json.dump(extraction_data, f, indent=2)
            print("\n💾 Full extraction details saved to: sifin_extraction_details.json")
            
        else:
            print(f"❌ SIFIN extraction failed: {result.error_message}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_document_extraction())