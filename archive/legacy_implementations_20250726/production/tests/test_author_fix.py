#!/usr/bin/env python3

"""
Test script to verify the author extraction fix.
Focus: Ensure Zhang, Panpan is extracted as an author with complete details.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from extractors.mf_extractor import ComprehensiveMFExtractor
import json

def test_author_extraction():
    """Test that all authors are extracted correctly including Zhang, Panpan."""
    print("🔧 TESTING AUTHOR EXTRACTION FIX")
    print("="*70)
    print("⏰ Primary Goal: Verify Zhang, Panpan is extracted as author")
    print("📋 Secondary Goals:")
    print("   • Complete author names and affiliations")
    print("   • No duplicate emails")
    print("   • All metadata extraction working")
    print("="*70)
    
    extractor = ComprehensiveMFExtractor()
    
    try:
        # Login
        if not extractor.login():
            print("❌ Login failed")
            return False
        
        print("✅ Login successful!")
        
        # Run the extraction
        extractor.__init__()  # Reset
        results = extractor.extract_all()
        
        # Focus on manuscript MAFI-2024-0167 where Zhang, Panpan should be an author
        target_manuscript = None
        for ms in results:
            if ms.get('id') == 'MAFI-2024-0167':
                target_manuscript = ms
                break
        
        if not target_manuscript:
            print("❌ Could not find MAFI-2024-0167")
            return False
        
        print("\n" + "="*70)
        print("🔍 DETAILED AUTHOR ANALYSIS FOR MAFI-2024-0167")
        print("="*70)
        
        authors = target_manuscript.get('authors', [])
        print(f"📊 Total authors found: {len(authors)}")
        
        zhang_found = False
        for i, author in enumerate(authors, 1):
            print(f"\n👤 Author {i}:")
            print(f"   Name: {author.get('name', 'NO NAME')}")
            print(f"   Email: {author.get('email', 'NO EMAIL')}")
            print(f"   Institution: {author.get('institution', 'NO INSTITUTION')}")
            print(f"   Country: {author.get('country', 'NO COUNTRY')}")
            print(f"   ORCID: {author.get('orcid', 'None')}")
            print(f"   Corresponding: {author.get('is_corresponding', False)}")
            
            # Check if this is Zhang, Panpan
            if 'zhang' in author.get('name', '').lower() and 'panpan' in author.get('name', '').lower():
                zhang_found = True
                print("   🎯 THIS IS ZHANG, PANPAN! ✅")
        
        print("\n" + "="*50)
        if zhang_found:
            print("✅ SUCCESS: Zhang, Panpan found as author!")
        else:
            print("❌ FAILURE: Zhang, Panpan NOT found as author!")
            
        # Check for other data
        print(f"\n📊 Other manuscript data:")
        print(f"   Keywords: {len(target_manuscript.get('keywords', []))} found")
        print(f"   Funding: {'✅' if target_manuscript.get('funding_information') else '❌'}")
        print(f"   Word count: {target_manuscript.get('word_count', 'Not found')}")
        print(f"   Audit trail: {len(target_manuscript.get('communications', []))} events")
        
        return zhang_found
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        try:
            extractor.driver.quit()
        except:
            pass

if __name__ == "__main__":
    success = test_author_extraction()
    sys.exit(0 if success else 1)