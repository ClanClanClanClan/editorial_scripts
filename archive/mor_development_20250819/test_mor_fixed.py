#!/usr/bin/env python3
"""Test the FIXED MOR extractor."""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))
from production.src.extractors.mor_extractor import ComprehensiveMORExtractor

def test_mor_fixed():
    """Test the fixed MOR extractor."""
    print("🚀 TESTING FIXED MOR EXTRACTOR")
    print("=" * 60)
    
    extractor = ComprehensiveMORExtractor()
    
    try:
        # Run full extraction
        print("📊 Running full extraction...")
        extractor.run()
        
        # Check results
        print("\n📋 RESULTS:")
        if extractor.results:
            for manuscript in extractor.results:
                print(f"\n📄 {manuscript.get('id', 'Unknown')}")
                
                # Check referees
                referees = manuscript.get('referees', [])
                print(f"   Referees: {len(referees)}")
                
                for i, referee in enumerate(referees[:3]):
                    name = referee.get('name', 'Unknown')
                    email = referee.get('email', '')
                    
                    if email and '@' in email:
                        print(f"   ✅ {name} → {email}")
                    else:
                        print(f"   ❌ {name} → NO EMAIL")
                
                # Validate referees are actual reviewers, not authors/editors
                suspicious = ['cerny', 'possamai', 'srikant', 'scheinberg']
                for referee in referees:
                    if any(s in referee.get('name', '').lower() for s in suspicious):
                        print(f"   ⚠️ WARNING: {referee['name']} might not be a referee!")
        else:
            print("❌ No results extracted")
            
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        extractor.cleanup()

if __name__ == "__main__":
    test_mor_fixed()