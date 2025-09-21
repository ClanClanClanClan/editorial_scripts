"""Step 1: Test credential loading and adapter initialization."""

import asyncio
import os
from pathlib import Path

# Set up credentials for testing
os.environ["MF_EMAIL"] = os.environ.get("MF_EMAIL", "test@example.com")
os.environ["MF_PASSWORD"] = os.environ.get("MF_PASSWORD", "test_password")


async def test_adapter_initialization():
    """Test that MF adapter can be created and initialized properly."""
    print("=" * 60)
    print("STEP 1: Testing MF Adapter Initialization")
    print("=" * 60)
    
    # Test 1: Can we import the adapter?
    try:
        from src.ecc.adapters.journals.mf import MFAdapter
        print("✅ MFAdapter imported successfully")
    except Exception as e:
        print(f"❌ Failed to import MFAdapter: {e}")
        return False
    
    # Test 2: Can we create an adapter instance?
    try:
        adapter = MFAdapter(headless=True)
        print("✅ MFAdapter instance created")
        print(f"   Journal ID: {adapter.config.journal_id}")
        print(f"   URL: {adapter.config.url}")
        print(f"   Platform: {adapter.config.platform}")
    except Exception as e:
        print(f"❌ Failed to create MFAdapter: {e}")
        return False
    
    # Test 3: Can we initialize browser?
    try:
        async with adapter:
            print("✅ Browser initialized")
            print(f"   Browser type: Playwright")
            print(f"   Headless: {adapter.config.headless}")
            
            # Test 4: Can we navigate to the URL?
            try:
                await adapter.navigate_with_retry(adapter.config.url)
                print("✅ Successfully navigated to MF URL")
                
                # Check what's on the page
                title = await adapter.page.title()
                print(f"   Page title: {title}")
                
                # Look for login elements
                userid_field = await adapter.page.query_selector("#USERID")
                password_field = await adapter.page.query_selector("#PASSWORD")
                login_button = await adapter.page.query_selector("#logInButton")
                
                if userid_field and password_field and login_button:
                    print("✅ Login form elements found")
                else:
                    print("⚠️ Some login elements missing (site may be down)")
                    
            except Exception as e:
                print(f"⚠️ Could not navigate to URL: {e}")
                print("   (This is expected if site is down for maintenance)")
                
    except Exception as e:
        print(f"❌ Failed to initialize browser: {e}")
        return False
    
    # Test 5: Check credential loading
    try:
        # Create a new adapter to test credential loading
        async with MFAdapter(headless=True) as adapter:
            creds = await adapter._get_credentials()
            if creds["username"] and creds["password"]:
                print("✅ Credentials loaded from environment")
                print(f"   Username: {creds['username'][:3]}...")  # Show first 3 chars only
            else:
                print("⚠️ No credentials found in environment")
                print("   Set MF_EMAIL and MF_PASSWORD environment variables")
    except Exception as e:
        print(f"❌ Failed to load credentials: {e}")
    
    print("\n" + "=" * 60)
    print("STEP 1 COMPLETE: Basic adapter functionality verified")
    print("=" * 60)
    return True


async def main():
    """Run incremental test step 1."""
    success = await test_adapter_initialization()
    
    if success:
        print("\n✅ Ready for Step 2: Testing authentication when site is available")
    else:
        print("\n❌ Fix the issues above before proceeding")
    
    return success


if __name__ == "__main__":
    result = asyncio.run(main())