#!/usr/bin/env python3
"""
Quick test to verify 3-pass navigation works correctly
"""

import sys
from pathlib import Path

# Add path to import the MF extractor  
sys.path.append(str(Path(__file__).parent.parent))

# Import credentials
try:
    from ensure_credentials import load_credentials
    load_credentials()
except ImportError:
    from dotenv import load_dotenv
    load_dotenv('.env.production')

from mf_extractor import ComprehensiveMFExtractor

def test_navigation():
    """Test just the navigation logic without full extraction"""
    print("🚀 Testing 3-pass navigation...")
    
    extractor = ComprehensiveMFExtractor()
    
    try:
        # Login
        print("📝 Logging in...")
        if not extractor.login():
            print("❌ Login failed")
            return
            
        # Navigate to AE Center
        print("🏠 Navigating to AE Center...")
        if not extractor.navigate_to_ae_center():
            print("❌ Navigation to AE Center failed")
            return
            
        # Find categories
        print("📋 Finding categories...")
        categories = extractor.get_categories()
        
        if not categories:
            print("❌ No categories found")
            return
            
        # Process just the first category with 2+ manuscripts
        target_category = None
        for category in categories:
            if category['count'] >= 2:
                target_category = category
                break
                
        if not target_category:
            print("❌ No category with 2+ manuscripts found")
            return
            
        print(f"🎯 Testing category: {target_category['name']} ({target_category['count']} manuscripts)")
        
        # Click category
        target_category['link'].click()
        
        # Get manuscript info
        manuscript_count, manuscript_data, manuscript_order = extractor.extract_basic_manuscript_info()
        
        if manuscript_count < 2:
            print("❌ Need at least 2 manuscripts for navigation test")
            return
            
        print(f"📄 Found {manuscript_count} manuscripts: {manuscript_order}")
        
        # Test navigation - Pass 1 simulation
        print("\n🔄 TESTING Pass 1 Navigation (Forward 1→2)")
        
        # Should be on manuscript 1
        current_id = extractor.get_current_manuscript_id()
        expected_id = manuscript_order[0]
        print(f"   Start: Expected {expected_id}, Got {current_id}")
        
        if current_id == expected_id:
            print("   ✅ Starting on correct manuscript")
        else:
            print("   ❌ Starting on wrong manuscript!")
            
        # Navigate to manuscript 2
        print("   Navigating to manuscript 2...")
        extractor.click_next_document()
        
        current_id = extractor.get_current_manuscript_id()
        expected_id = manuscript_order[1]
        print(f"   After Next: Expected {expected_id}, Got {current_id}")
        
        if current_id == expected_id:
            print("   ✅ Successfully navigated to manuscript 2")
        else:
            print("   ❌ Navigation to manuscript 2 failed!")
            
        # Test navigation - Pass 2 simulation  
        print("\n🔄 TESTING Pass 2 Navigation (Backward 2→1)")
        
        # Navigate back to manuscript 1
        print("   Navigating back to manuscript 1...")
        extractor.click_previous_document()
        
        current_id = extractor.get_current_manuscript_id() 
        expected_id = manuscript_order[0]
        print(f"   After Previous: Expected {expected_id}, Got {current_id}")
        
        if current_id == expected_id:
            print("   ✅ Successfully navigated back to manuscript 1")
        else:
            print("   ❌ Navigation back to manuscript 1 failed!")
            
        print("\n🎉 Navigation test complete!")
        
    except Exception as e:
        print(f"❌ Error during navigation test: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if hasattr(extractor, 'driver') and extractor.driver:
            extractor.driver.quit()

if __name__ == "__main__":
    test_navigation()