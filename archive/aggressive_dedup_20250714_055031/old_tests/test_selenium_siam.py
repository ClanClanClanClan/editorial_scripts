#!/usr/bin/env python3
"""
Test the existing Selenium-based SIAM extractor
"""

import os
import sys
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_selenium_siam():
    """Test the working Selenium SIAM extractor"""
    print("Testing Selenium-based SIAM extractor...")
    
    # Set credentials
    os.environ['ORCID_EMAIL'] = 'dylan.possamai@polytechnique.org'
    os.environ['ORCID_PASSWORD'] = 'Hioupy0042%'
    
    try:
        from journals.siam_base import SIAMJournalExtractor
        
        print("Creating SIFIN extractor...")
        extractor = SIAMJournalExtractor('SIFIN')
        
        print("Initializing browser...")
        extractor.initialize()
        
        print("Starting authentication...")
        auth_result = extractor.authenticate()
        print(f"Authentication result: {auth_result}")
        
        if auth_result:
            print("✅ Authentication successful!")
            print("Extracting manuscripts...")
            
            # Get manuscript data
            manuscripts = extractor.extract_all_manuscripts()
            print(f"Found {len(manuscripts)} manuscripts")
            
            for i, ms in enumerate(manuscripts[:2]):  # First 2 for testing
                print(f"\nManuscript {i+1}:")
                print(f"  ID: {ms.get('id', 'Unknown')}")
                print(f"  Title: {ms.get('title', 'Unknown')}")
                print(f"  Status: {ms.get('status', 'Unknown')}")
        else:
            print("❌ Authentication failed")
        
        print("Closing browser...")
        extractor.cleanup()
        
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_selenium_siam()