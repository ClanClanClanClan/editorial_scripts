#!/usr/bin/env python3
"""
Test script for production SICON extraction
Validates that all fixes are working correctly
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test credentials if not already set
if not os.getenv('ORCID_EMAIL'):
    # Copy credentials from parent .env if available
    parent_env = Path(__file__).parent.parent / '.env'
    if parent_env.exists():
        from dotenv import load_dotenv
        load_dotenv(parent_env)

async def test_sicon_extraction():
    """Test SICON extraction with validation"""
    from production.extractors.sicon import SICONExtractor
    from production.core.credentials import CredentialManager
    
    print("🧪 Testing SICON Extraction")
    print("=" * 60)
    
    # Check credentials
    cred_manager = CredentialManager()
    if not cred_manager.validate_credentials('sicon'):
        print("❌ No SICON credentials found")
        print("Please set ORCID_EMAIL and ORCID_PASSWORD")
        return False
    
    print("✅ Credentials found")
    
    # Create extractor
    extractor = SICONExtractor()
    
    try:
        # Run extraction
        print("\n🚀 Running extraction...")
        result = await extractor.extract(headless=True)
        
        print("\n📊 Results:")
        print(f"   Manuscripts: {result.total_manuscripts}")
        print(f"   Referees: {result.total_referees}")
        print(f"   PDFs downloaded: {result.pdfs_downloaded}")
        
        # Validate results
        print("\n🔍 Validation:")
        
        # Check manuscript count
        if result.total_manuscripts >= 4:
            print("   ✅ Manuscript count matches July 11 baseline (4)")
        else:
            print(f"   ⚠️ Manuscript count ({result.total_manuscripts}) below July 11 baseline (4)")
        
        # Check metadata
        empty_titles = sum(1 for ms in result.manuscripts if not ms.title or ms.title.startswith("Manuscript"))
        if empty_titles == 0:
            print("   ✅ All manuscripts have titles")
        else:
            print(f"   ❌ {empty_titles} manuscripts have empty/default titles")
        
        # Check authors
        empty_authors = sum(1 for ms in result.manuscripts if not ms.authors or ms.authors == ["Author information not available"])
        if empty_authors == 0:
            print("   ✅ All manuscripts have authors")
        else:
            print(f"   ❌ {empty_authors} manuscripts have empty/default authors")
        
        # Check PDFs
        if result.pdfs_downloaded > 0:
            print(f"   ✅ PDFs downloaded successfully ({result.pdfs_downloaded})")
        else:
            print("   ❌ No PDFs downloaded")
        
        # Check referees
        if result.total_referees >= 10:
            print(f"   ✅ Referee count ({result.total_referees}) meets expectations")
        else:
            print(f"   ⚠️ Referee count ({result.total_referees}) below expectations")
        
        # Check emails
        if result.referees_with_emails > 0:
            print(f"   ✅ Referee emails extracted ({result.referees_with_emails})")
        else:
            print("   ❌ No referee emails extracted")
        
        # Sample manuscript details
        if result.manuscripts:
            print("\n📄 Sample manuscript:")
            ms = result.manuscripts[0]
            print(f"   ID: {ms.id}")
            print(f"   Title: {ms.title[:60]}..." if len(ms.title) > 60 else f"   Title: {ms.title}")
            print(f"   Authors: {', '.join(ms.authors[:2])}{'...' if len(ms.authors) > 2 else ''}")
            print(f"   AE: {ms.associate_editor}")
            print(f"   Referees: {len(ms.referees)}")
            
            if ms.referees:
                print("\n   Sample referee:")
                ref = ms.referees[0]
                print(f"      Name: {ref.name}")
                print(f"      Email: {ref.email}")
                print(f"      Status: {ref.status}")
        
        # Overall assessment
        print("\n📈 Overall Assessment:")
        if (result.total_manuscripts >= 4 and 
            empty_titles == 0 and 
            empty_authors == 0 and 
            result.pdfs_downloaded > 0):
            print("   ✅ EXTRACTION SUCCESSFUL - All fixes working!")
            return True
        else:
            print("   ⚠️ EXTRACTION PARTIALLY SUCCESSFUL - Some issues remain")
            return False
            
    except Exception as e:
        print(f"\n❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_sicon_extraction())
    sys.exit(0 if success else 1)