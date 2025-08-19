#!/usr/bin/env python3
"""Simple test of MOR extractor - just login and categories."""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))
from production.src.extractors.mor_extractor import ComprehensiveMORExtractor

def test_simple_mor():
    """Simple test - just login and get categories."""
    print("🧪 SIMPLE MOR TEST - Login and Categories Only")
    print("=" * 60)
    
    extractor = ComprehensiveMORExtractor()
    
    try:
        # Test login
        print("🔐 Testing login...")
        extractor.login()
        print("   ✅ Login successful")
        
        # Navigate to AE Center
        print("📋 Testing navigation to AE Center...")
        extractor.navigate_to_ae_center()
        print("   ✅ Navigation successful")
        
        # Get categories
        print("📂 Getting manuscript categories...")
        categories = extractor.get_manuscript_categories()
        print(f"   ✅ Found {len(categories)} categories")
        
        for cat in categories:
            print(f"      - {cat['name']}: {cat['count']} manuscripts")
        
        print("\n✅ SIMPLE TEST PASSED - Ready for full extraction")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        extractor.cleanup()

if __name__ == "__main__":
    test_simple_mor()