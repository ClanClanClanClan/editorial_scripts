"""Step 2: Test authentication when site is available."""

import asyncio
import os
import sys
from datetime import datetime

# Ensure credentials are loaded
sys.path.append('production/src')
try:
    from core.secure_credentials import load_credentials_from_keychain
    creds = load_credentials_from_keychain("MF")
    if creds:
        os.environ["MF_EMAIL"] = creds["email"]
        os.environ["MF_PASSWORD"] = creds["password"]
        print("✅ Loaded credentials from keychain")
except:
    print("⚠️ Using environment variables for credentials")


async def test_authentication():
    """Test that MF adapter can authenticate properly."""
    print("=" * 60)
    print("STEP 2: Testing MF Authentication")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    from src.ecc.adapters.journals.mf import MFAdapter
    
    async with MFAdapter(headless=False) as adapter:  # Use headless=False to watch
        print("🌐 Checking site availability...")
        
        # First, just try to reach the site
        try:
            await adapter.navigate_with_retry(adapter.config.url)
            title = await adapter.page.title()
            print(f"✅ Site is reachable. Title: {title}")
        except Exception as e:
            print(f"❌ Site unreachable: {e}")
            print("   Site may still be down for maintenance")
            return False
        
        # Check for maintenance message
        maintenance_text = await adapter.page.query_selector("text=maintenance")
        if maintenance_text:
            print("⚠️ Site shows maintenance message")
            maintenance_msg = await maintenance_text.inner_text()
            print(f"   Message: {maintenance_msg}")
            return False
        
        # Look for login form
        userid_field = await adapter.page.query_selector("#USERID")
        password_field = await adapter.page.query_selector("#PASSWORD")
        login_button = await adapter.page.query_selector("#logInButton")
        
        if not (userid_field and password_field and login_button):
            print("❌ Login form not found")
            print("   The site structure may have changed")
            
            # Try to find what IS on the page
            all_inputs = await adapter.page.query_selector_all("input")
            print(f"   Found {len(all_inputs)} input fields")
            
            all_buttons = await adapter.page.query_selector_all("button")
            print(f"   Found {len(all_buttons)} buttons")
            
            return False
        
        print("✅ Login form found")
        
        # Try to authenticate
        print("🔐 Attempting authentication...")
        
        try:
            # Handle cookie banner if present
            try:
                cookie_reject = await adapter.page.query_selector("#onetrust-reject-all-handler")
                if cookie_reject:
                    await cookie_reject.click()
                    print("   Dismissed cookie banner")
                    await asyncio.sleep(1)
            except:
                pass
            
            # Get credentials
            creds = await adapter._get_credentials()
            if not creds["username"] or not creds["password"]:
                print("❌ No credentials available")
                print("   Set MF_EMAIL and MF_PASSWORD environment variables")
                return False
            
            # Clear and fill username
            await userid_field.click()
            await userid_field.fill("")  # Clear first
            await userid_field.fill(creds["username"])
            print(f"   Entered username: {creds['username'][:3]}...")
            
            # Clear and fill password
            await password_field.click()
            await password_field.fill("")  # Clear first
            await password_field.fill(creds["password"])
            print("   Entered password: ***")
            
            # Click login button
            await login_button.click()
            print("   Clicked login button")
            
            # Wait for navigation
            await adapter.page.wait_for_load_state("networkidle", timeout=10000)
            
            # Check for 2FA
            token_field = await adapter.page.query_selector("#TOKEN_VALUE")
            if token_field:
                print("🔐 2FA required")
                print("   Waiting 30 seconds for manual 2FA entry...")
                print("   (In production, this would fetch from Gmail)")
                await asyncio.sleep(30)
                
                # Check if we got past 2FA
                await adapter.page.wait_for_load_state("networkidle", timeout=5000)
            
            # Check if login succeeded
            # Look for signs we're logged in
            dashboard = await adapter.page.query_selector("text=Dashboard")
            ae_center = await adapter.page.query_selector("text=Associate Editor Center")
            logout = await adapter.page.query_selector("text=Log Out")
            
            if dashboard or ae_center or logout:
                print("✅ Authentication successful!")
                
                # Try to get username from page
                user_elem = await adapter.page.query_selector(".user-name")
                if user_elem:
                    username = await user_elem.inner_text()
                    print(f"   Logged in as: {username}")
                
                return True
            else:
                print("❌ Authentication failed")
                
                # Check for error messages
                error = await adapter.page.query_selector(".error-message")
                if error:
                    error_text = await error.inner_text()
                    print(f"   Error: {error_text}")
                
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    print("\n" + "=" * 60)
    print("STEP 2 COMPLETE")
    print("=" * 60)


async def main():
    """Run incremental test step 2."""
    success = await test_authentication()
    
    if success:
        print("\n✅ Ready for Step 3: Fetching manuscript categories")
    else:
        print("\n⚠️ Authentication not working yet")
        print("   - Check if site is up")
        print("   - Verify credentials are correct")
        print("   - Try again later if site is down")
    
    return success


if __name__ == "__main__":
    result = asyncio.run(main())