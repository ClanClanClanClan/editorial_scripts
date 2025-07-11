#!/usr/bin/env python3
"""
Test SIFIN email extraction improvements
"""

from journals.sifin import SIFIN
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_sifin_quick():
    """Quick test of SIFIN email extraction"""
    print("=" * 60)
    print("TESTING SIFIN EMAIL EXTRACTION IMPROVEMENTS")
    print("=" * 60)
    
    try:
        # Create and setup
        sifin = SIFIN()
        sifin.setup_driver(headless=False)
        
        # Authenticate
        if not sifin.authenticate():
            print("❌ Authentication failed")
            return False
        
        # Extract just first manuscript to test
        print("\n1. Testing first manuscript only...")
        manuscripts = sifin.extract_manuscripts()
        
        if not manuscripts:
            print("❌ No manuscripts found")
            return False
        
        # Test just first manuscript
        manuscript = manuscripts[0]
        print(f"\n2. Testing manuscript: {manuscript['id']}")
        print(f"   Title: {manuscript['title'][:50]}...")
        print(f"   Referees: {len(manuscript['referees'])}")
        
        # Check email extraction
        emails_found = 0
        for referee in manuscript['referees']:
            if referee.get('email'):
                emails_found += 1
                print(f"   ✅ {referee['name']}: {referee['email']}")
            else:
                print(f"   ❌ {referee['name']}: No email")
        
        print(f"\n3. Results:")
        print(f"   Emails found: {emails_found}/{len(manuscript['referees'])}")
        
        if emails_found == len(manuscript['referees']):
            print("   🎉 PERFECT! All emails extracted!")
            return True
        elif emails_found > 0:
            print("   ⚠️  PARTIAL: Some emails extracted")
            return False
        else:
            print("   ❌ FAILED: No emails extracted")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        try:
            sifin.driver.quit()
        except:
            pass

if __name__ == "__main__":
    success = test_sifin_quick()
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")