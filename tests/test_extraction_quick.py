#!/usr/bin/env python3
"""
Quick test of extraction system without full browser automation
"""

import asyncio
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

async def test_extraction_quick():
    """Quick test of extraction system"""
    
    print("🚀 QUICK EXTRACTION TEST")
    print("=" * 30)
    
    try:
        # Import credential manager
        from src.core.credential_manager import get_credential_manager
        
        # Get credentials
        cred_manager = get_credential_manager()
        creds = cred_manager.get_credentials('SICON')
        
        if not creds:
            print("❌ No SICON credentials found")
            return
        
        print(f"✅ Credentials found: {creds['username'][:10]}...")
        
        # Import extractor
        from unified_system.extractors.siam.sicon import SICONExtractor
        
        # Create extractor
        extractor = SICONExtractor()
        print("✅ SICON extractor created")
        
        # Test credential setup
        extractor.username = creds['username'] 
        extractor.password = creds['password']
        print("✅ Credentials set on extractor")
        
        # Test browser initialization (but don't go to websites)
        print("🌐 Testing browser initialization...")
        await extractor._init_browser(headless=True)
        print("✅ Browser initialized successfully")
        
        # Test credential manager integration
        print("🔐 Testing credential manager integration...")
        extractor._setup_credential_manager()
        print("✅ Credential manager integration working")
        
        # Cleanup
        await extractor._cleanup()
        print("✅ Cleanup successful")
        
        print("\n🎉 ALL CORE SYSTEMS WORKING!")
        print("\n📋 Ready for full extraction:")
        print("  python3 run_unified_with_1password.py --journal SICON")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_extraction_quick())
    
    if success:
        print("\n✅ System ready for full extraction!")
    else:
        print("\n❌ System needs more work")