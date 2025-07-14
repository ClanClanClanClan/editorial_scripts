#!/usr/bin/env python3
"""
Test Authentication Only - Verify ORCID flow works
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import our unified extractors
from unified_system import SICONExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


async def test_authentication_only():
    """Test just the authentication flow"""
    logger.info("🧪 TESTING AUTHENTICATION ONLY")
    logger.info("=" * 60)
    
    # Check environment
    orcid_email = os.getenv("ORCID_EMAIL")
    orcid_password = os.getenv("ORCID_PASSWORD")
    
    logger.info(f"ORCID Email: {orcid_email}")
    logger.info(f"ORCID Password: {'*' * len(orcid_password) if orcid_password else 'None'}")
    
    if not orcid_email or not orcid_password:
        logger.error("❌ No ORCID credentials in environment")
        return False
    
    if orcid_email == "test@example.com":
        logger.error("❌ Still using fake test credentials!")
        logger.error("   Please update .env with real ORCID credentials")
        return False
    
    try:
        # Create extractor
        extractor = SICONExtractor()
        
        logger.info(f"🎯 Testing {extractor.journal_name} at {extractor.base_url}")
        
        # Initialize browser
        await extractor._init_browser(headless=False)  # Keep visible for debugging
        
        # Test authentication only
        auth_success = await extractor._authenticate()
        
        if auth_success:
            logger.info("✅ AUTHENTICATION SUCCESSFUL!")
            
            # Check current URL
            current_url = extractor.page.url
            logger.info(f"Current URL: {current_url}")
            
            # Take a screenshot for verification
            screenshot_path = f"auth_success_{extractor.journal_name}.png"
            await extractor.page.screenshot(path=screenshot_path)
            logger.info(f"📸 Screenshot saved: {screenshot_path}")
            
            # Wait a bit to see the page
            logger.info("⏳ Waiting 10 seconds to observe the page...")
            await asyncio.sleep(10)
            
        else:
            logger.error("❌ AUTHENTICATION FAILED!")
            
            # Take error screenshot
            screenshot_path = f"auth_failed_{extractor.journal_name}.png"
            await extractor.page.screenshot(path=screenshot_path)
            logger.info(f"📸 Error screenshot saved: {screenshot_path}")
        
        # Cleanup
        await extractor._cleanup()
        
        return auth_success
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run authentication test"""
    logger.info("🚀 AUTHENTICATION TEST - REAL CREDENTIALS ONLY")
    logger.info("=" * 80)
    
    success = await test_authentication_only()
    
    logger.info("\n" + "=" * 80)
    if success:
        logger.info("✅ AUTHENTICATION TEST PASSED")
        logger.info("✅ Ready to proceed with full extraction testing")
    else:
        logger.error("❌ AUTHENTICATION TEST FAILED")
        logger.error("❌ Check credentials and website accessibility")
    
    logger.info("\n💡 Next Steps:")
    if success:
        logger.info("  1. Run full extraction test: python3 test_unified_system.py")
        logger.info("  2. Test PDF downloads: python3 test_pdf_downloads.py")
    else:
        logger.info("  1. Verify ORCID credentials are correct")
        logger.info("  2. Check if SIAM websites are accessible")
        logger.info("  3. Check for CloudFlare issues")


if __name__ == "__main__":
    asyncio.run(main())