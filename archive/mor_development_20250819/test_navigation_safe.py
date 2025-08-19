#!/usr/bin/env python3
"""Test safe navigation - process ONE category with NO dangerous clicks."""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))
from production.src.extractors.mor_extractor import ComprehensiveMORExtractor

def test_navigation_safe():
    """Test navigation through one category safely."""
    print("🛡️ SAFE NAVIGATION TEST - One Category Only")
    print("=" * 60)
    
    extractor = ComprehensiveMORExtractor()
    
    try:
        # Login and navigate
        print("🔐 Logging in...")
        extractor.login()
        
        print("📋 Navigating to AE Center...")
        extractor.navigate_to_ae_center()
        
        # Get categories
        categories = extractor.get_manuscript_categories()
        print(f"📂 Found {len(categories)} categories")
        
        # Process ONE category safely
        if categories:
            category = categories[0]  # Just first one
            print(f"\n🎯 Processing ONLY: {category['name']} ({category['count']} manuscripts)")
            
            # This should be safe navigation
            extractor.process_category(category)
            
            print(f"\n📊 Results:")
            if extractor.manuscripts:
                for manuscript in extractor.manuscripts:
                    manuscript_id = manuscript.get('id', 'Unknown')
                    referees = manuscript.get('referees', [])
                    print(f"   📄 {manuscript_id}: {len(referees)} referees")
                    
                    for i, referee in enumerate(referees[:2]):  # Show first 2
                        name = referee.get('name', 'Unknown')
                        email = referee.get('email', '')
                        if email and '@' in email:
                            print(f"      ✅ {name} → {email}")
                        else:
                            print(f"      ❌ {name} → NO EMAIL")
            else:
                print("   📭 No manuscripts extracted")
        
        print("\n✅ NAVIGATION TEST COMPLETE")
        
    except Exception as e:
        print(f"❌ Navigation test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        extractor.cleanup()

if __name__ == "__main__":
    test_navigation_safe()