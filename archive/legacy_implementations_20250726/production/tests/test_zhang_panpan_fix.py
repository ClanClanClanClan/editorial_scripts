#!/usr/bin/env python3

"""
Quick test to verify Zhang, Panpan is now detected as an author.
Focus: Check that zhangpanpan@mail.sdu.edu.cn is extracted from audit trail and used for author extraction.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from extractors.mf_extractor import ComprehensiveMFExtractor
import json

def test_zhang_panpan_fix():
    """Test that Zhang, Panpan is now extracted as an author."""
    print("🔧 TESTING ZHANG PANPAN AUTHOR EXTRACTION FIX")
    print("="*60)
    print("🎯 Goal: Verify zhangpanpan@mail.sdu.edu.cn is found and Zhang, Panpan extracted")
    print("="*60)
    
    extractor = ComprehensiveMFExtractor()
    
    try:
        # Login and get data
        if not extractor.login():
            print("❌ Login failed")
            return False
        
        print("✅ Login successful!")
        
        # Run comprehensive extraction
        results = extractor.extract_all()
        
        # Focus on MAFI-2024-0167
        target_manuscript = None
        for ms in results:
            if ms.get('id') == 'MAFI-2024-0167':
                target_manuscript = ms
                break
        
        if not target_manuscript:
            print("❌ Could not find MAFI-2024-0167")
            return False
        
        print(f"\n📊 MAFI-2024-0167 AUTHOR ANALYSIS:")
        print("="*50)
        
        authors = target_manuscript.get('authors', [])
        print(f"Total authors found: {len(authors)}")
        
        zhang_found = False
        for i, author in enumerate(authors, 1):
            name = author.get('name', 'NO NAME')
            email = author.get('email', 'NO EMAIL')
            
            print(f"\n👤 Author {i}:")
            print(f"   Name: {name}")
            print(f"   Email: {email}")
            
            # Check for Zhang, Panpan specifically
            if ('zhang' in name.lower() and 'panpan' in name.lower()) or 'zhangpanpan@mail.sdu.edu.cn' in email:
                zhang_found = True
                print("   🎯 THIS IS ZHANG, PANPAN! ✅")
                break
        
        print("\n" + "="*50)
        if zhang_found:
            print("✅ SUCCESS: Zhang, Panpan detected as author!")
            return True
        else:
            print("❌ FAILURE: Zhang, Panpan still not found as author")
            
            # Debug: Show audit trail emails collected
            print(f"\n🔍 DEBUG - Audit trail emails collected:")
            if hasattr(extractor, 'audit_trail_emails'):
                for manuscript_id, emails in extractor.audit_trail_emails.items():
                    print(f"   {manuscript_id}: {emails}")
            else:
                print("   No audit trail emails collected")
            
            return False
        
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
    success = test_zhang_panpan_fix()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILURE'}")
    sys.exit(0 if success else 1)