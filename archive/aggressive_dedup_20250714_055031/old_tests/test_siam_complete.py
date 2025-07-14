#!/usr/bin/env python3
"""
Complete test of SIAM scrapers (SICON/SIFIN) in headless mode
Tests authentication, extraction, document download, and metadata storage
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_siam_scraper(journal_code: str):
    """Test a SIAM scraper with full functionality"""
    print(f"\n{'='*60}")
    print(f"🧪 TESTING {journal_code} SCRAPER")
    print(f"{'='*60}\n")
    
    # Set credentials
    os.environ['ORCID_EMAIL'] = 'dylan.possamai@polytechnique.org'
    os.environ['ORCID_PASSWORD'] = 'Hioupy0042%'
    
    try:
        # Import after setting path
        from src.infrastructure.scrapers.siam_scraper import SIAMScraper
        
        # Create scraper
        print(f"📊 Creating {journal_code} scraper...")
        scraper = SIAMScraper(journal_code)
        print(f"✅ Scraper created successfully")
        print(f"   Base URL: {scraper.config.base_url}")
        print(f"   Folder ID: {scraper.config.folder_id}")
        print(f"   Max manuscripts: {scraper.config.max_manuscripts}")
        
        # Run extraction
        print(f"\n🔄 Running extraction (this may take a few minutes)...")
        start_time = datetime.now()
        result = await scraper.run_extraction()
        duration = datetime.now() - start_time
        
        if result.success:
            print(f"\n✅ EXTRACTION SUCCESSFUL!")
            print(f"   Total manuscripts: {result.total_count}")
            print(f"   Extraction time: {duration}")
            
            # Show document download statistics
            if result.metadata.get('documents_downloaded'):
                docs = result.metadata['documents_downloaded']
                print(f"\n📎 Document Downloads:")
                print(f"   Manuscripts: {docs.get('manuscripts', 0)}")
                print(f"   Cover letters: {docs.get('cover_letters', 0)}")
                print(f"   Referee reports: {docs.get('referee_reports', 0)}")
            
            # Show manuscript details
            print(f"\n📄 Manuscript Details:")
            for i, ms in enumerate(result.manuscripts[:5], 1):  # Show first 5
                print(f"\n   {i}. {ms.id}")
                print(f"      Title: {ms.title[:60]}...")
                print(f"      Status: {ms.status}")
                print(f"      Editors: {ms.corresponding_editor} / {ms.associate_editor}")
                
                # Show document info
                docs = ms.metadata.get('documents', {})
                if docs:
                    print(f"      Documents:")
                    if docs.get('manuscript_pdf_local'):
                        print(f"        - PDF: ✓ (downloaded)")
                    if docs.get('cover_letter_local'):
                        print(f"        - Cover Letter: ✓ (downloaded)")
                    if docs.get('referee_reports_local'):
                        print(f"        - Referee Reports: {len(docs['referee_reports_local'])}")
                
                # Show referee info
                if ms.referees:
                    print(f"      Referees: {len(ms.referees)}")
                    for ref in ms.referees[:2]:  # Show first 2
                        print(f"        - {ref.name}: {ref.status}")
            
            if result.total_count > 5:
                print(f"\n   ... and {result.total_count - 5} more manuscripts")
            
            # Check metadata storage
            data_dir = Path.home() / '.editorial_scripts' / 'documents'
            metadata_dir = data_dir / 'metadata' / journal_code
            if metadata_dir.exists():
                metadata_files = list(metadata_dir.glob('*.json'))
                print(f"\n💾 Metadata Storage:")
                print(f"   Location: {metadata_dir}")
                print(f"   Files created: {len(metadata_files)}")
                
                # Show summary file
                summary_files = list(metadata_dir.glob('extraction_summary_*.json'))
                if summary_files:
                    print(f"   Summary file: {summary_files[-1].name}")
            
            # Check document storage
            manuscripts_dir = data_dir / 'manuscripts' / journal_code
            if manuscripts_dir.exists():
                total_pdfs = 0
                total_size = 0
                for ms_dir in manuscripts_dir.iterdir():
                    if ms_dir.is_dir():
                        pdfs = list(ms_dir.glob('*.pdf'))
                        total_pdfs += len(pdfs)
                        for pdf in pdfs:
                            total_size += pdf.stat().st_size
                
                print(f"\n📁 Document Storage:")
                print(f"   Location: {manuscripts_dir}")
                print(f"   Total PDFs: {total_pdfs}")
                print(f"   Total size: {total_size / 1024 / 1024:.1f} MB")
            
            return True
            
        else:
            print(f"\n❌ EXTRACTION FAILED!")
            print(f"   Error: {result.error_message}")
            print(f"   Duration: {duration}")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_both_scrapers():
    """Test both SICON and SIFIN scrapers"""
    print("🚀 SIAM SCRAPERS COMPREHENSIVE TEST")
    print("=" * 60)
    print("Testing in HEADLESS mode with full functionality:")
    print("- Authentication via ORCID SSO")
    print("- Manuscript extraction")
    print("- Document downloads (PDFs, cover letters, referee reports)")
    print("- Metadata storage")
    print("=" * 60)
    
    # Test SIFIN first (known to work)
    sifin_success = await test_siam_scraper('SIFIN')
    
    # Test SICON
    sicon_success = await test_siam_scraper('SICON')
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    print(f"SIFIN: {'✅ PASSED' if sifin_success else '❌ FAILED'}")
    print(f"SICON: {'✅ PASSED' if sicon_success else '❌ FAILED'}")
    
    if sifin_success and sicon_success:
        print("\n🎉 ALL TESTS PASSED! Both scrapers working perfectly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    # Show storage location
    data_dir = Path.home() / '.editorial_scripts' / 'documents'
    print(f"\n📁 All data stored in: {data_dir}")
    print("   - manuscripts/: Downloaded PDFs")
    print("   - metadata/: JSON metadata files")


if __name__ == "__main__":
    asyncio.run(test_both_scrapers())