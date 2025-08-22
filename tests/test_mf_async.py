"""Test script for async MF adapter."""

import asyncio
import logging
import os
from datetime import datetime

from src.ecc.adapters.journals.mf import MFAdapter


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_mf_adapter():
    """Test the async MF adapter."""
    print("🧪 Testing Async MF Adapter")
    print("=" * 60)
    
    # Check credentials
    mf_email = os.getenv("MF_EMAIL")
    mf_password = os.getenv("MF_PASSWORD")
    
    if not mf_email or not mf_password:
        print("❌ MF credentials not found in environment variables")
        print("   Set MF_EMAIL and MF_PASSWORD environment variables")
        return False
        
    print(f"✅ Using credentials for: {mf_email}")
    
    start_time = datetime.now()
    
    try:
        # Test with visible browser for debugging
        async with MFAdapter(headless=False) as adapter:
            print(f"\n🔐 Testing authentication...")
            
            # Test authentication
            auth_success = await adapter.authenticate()
            
            if not auth_success:
                print("❌ Authentication failed")
                return False
                
            print("✅ Authentication successful")
            
            # Test fetching manuscript categories
            print(f"\n📋 Testing manuscript category fetching...")
            categories = await adapter.get_default_categories()
            print(f"✅ Found {len(categories)} default categories:")
            for cat in categories:
                print(f"   - {cat}")
                
            # Test fetching manuscripts from one category
            print(f"\n📄 Testing manuscript fetching...")
            test_categories = [categories[0]] if categories else []
            
            if test_categories:
                manuscripts = await adapter.fetch_manuscripts(test_categories)
                print(f"✅ Found {len(manuscripts)} manuscripts in '{test_categories[0]}'")
                
                # Show details of first manuscript
                if manuscripts:
                    ms = manuscripts[0]
                    print(f"\n📊 First manuscript details:")
                    print(f"   ID: {ms.external_id}")
                    print(f"   Title: {ms.title[:60]}..." if len(ms.title) > 60 else f"   Title: {ms.title}")
                    print(f"   Status: {ms.current_status}")
                    print(f"   Authors: {len(ms.authors)}")
                    print(f"   Referees: {len(ms.referees)}")
                    
                    # Test detailed extraction for first manuscript
                    if ms.external_id:
                        print(f"\n🔍 Testing detailed extraction for {ms.external_id}...")
                        detailed_ms = await adapter.extract_manuscript_details(ms.external_id)
                        
                        print(f"   Authors: {len(detailed_ms.authors)}")
                        print(f"   Referees: {len(detailed_ms.referees)}")
                        print(f"   Abstract length: {len(detailed_ms.abstract)}")
                        print(f"   Keywords: {len(detailed_ms.keywords)}")
                        
                        # Show referee details
                        if detailed_ms.referees:
                            print(f"\n👥 Referee details:")
                            for i, ref in enumerate(detailed_ms.referees[:3]):  # First 3
                                print(f"   {i+1}. {ref.name}")
                                print(f"      Email: {ref.email if ref.email else 'Not found'}")
                                print(f"      Status: {ref.status}")
                                print(f"      Institution: {ref.institution if ref.institution else 'Not found'}")
                                
            else:
                print("ℹ️ No categories available for testing")
                
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        elapsed = datetime.now() - start_time
        print(f"\n⏱️ Test completed in {elapsed.total_seconds():.2f} seconds")
        
    print("\n✅ Async MF adapter test completed successfully!")
    return True


async def test_adapter_without_auth():
    """Test adapter initialization without authentication."""
    print("\n🧪 Testing adapter initialization (no auth)")
    
    try:
        async with MFAdapter(headless=True) as adapter:
            print("✅ Adapter initialized successfully")
            print(f"   Journal ID: {adapter.config.journal_id}")
            print(f"   Platform: {adapter.config.platform}")
            print(f"   URL: {adapter.config.url}")
            
            # Test default categories
            categories = await adapter.get_default_categories()
            print(f"✅ Default categories: {len(categories)}")
            
    except Exception as e:
        print(f"❌ Initialization test failed: {e}")
        return False
        
    return True


async def main():
    """Main test function."""
    print("🚀 MF Async Adapter Test Suite")
    print("=" * 70)
    
    # Test 1: Initialization
    init_success = await test_adapter_without_auth()
    
    # Test 2: Full workflow (requires credentials)
    if init_success:
        full_success = await test_mf_adapter()
        
        if full_success:
            print("\n🎉 ALL TESTS PASSED!")
            print("   The async MF adapter is working correctly")
        else:
            print("\n⚠️ Some tests failed")
    else:
        print("\n❌ Initialization failed, skipping full test")


if __name__ == "__main__":
    asyncio.run(main())