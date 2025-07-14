#!/usr/bin/env python3
"""
Test 1Password Integration with Unified System
Quick verification that automation is working
"""

import sys
import subprocess
import logging
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'core'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_1password_cli():
    """Test 1Password CLI basics"""
    logger.info("🔍 Testing 1Password CLI...")
    
    try:
        # Check version
        version = subprocess.run(['op', '--version'], capture_output=True, text=True, timeout=5)
        if version.returncode == 0:
            logger.info(f"✅ CLI version: {version.stdout.strip()}")
        else:
            logger.error("❌ CLI not working")
            return False
        
        # Check session
        whoami = subprocess.run(['op', 'whoami'], capture_output=True, text=True, timeout=5)
        if whoami.returncode == 0:
            logger.info(f"✅ Signed in as: {whoami.stdout.strip()}")
        else:
            logger.error("❌ Not signed in")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ CLI test failed: {e}")
        return False

def test_credential_manager():
    """Test credential manager"""
    logger.info("🔍 Testing credential manager...")
    
    try:
        from core.credential_manager import get_credential_manager
        
        cred_manager = get_credential_manager()
        orcid_creds = cred_manager.get_journal_credentials('ORCID')
        
        if orcid_creds.get('email') and orcid_creds.get('password'):
            logger.info(f"✅ ORCID credentials: {orcid_creds['email'][:3]}****@****")
            return True
        else:
            logger.error("❌ No ORCID credentials found")
            return False
            
    except Exception as e:
        logger.error(f"❌ Credential manager failed: {e}")
        return False

def test_unified_imports():
    """Test unified system imports"""
    logger.info("🔍 Testing unified system imports...")
    
    try:
        from unified_system import SICONExtractor, SIFINExtractor
        
        sicon = SICONExtractor()
        sifin = SIFINExtractor()
        
        logger.info(f"✅ SICON: {sicon.journal_name} at {sicon.base_url}")
        logger.info(f"✅ SIFIN: {sifin.journal_name} at {sifin.base_url}")
        
        # Test 1Password integration flag
        if hasattr(sicon, '_has_1password_creds'):
            logger.info(f"✅ 1Password integration: {sicon._has_1password_creds}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    logger.info("🧪 1PASSWORD UNIFIED SYSTEM TEST")
    logger.info("=" * 60)
    
    tests = [
        ("1Password CLI", test_1password_cli),
        ("Credential Manager", test_credential_manager), 
        ("Unified System", test_unified_imports)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
        else:
            logger.error(f"❌ {test_name} failed")
    
    # Summary
    logger.info(f"\n{'=' * 60}")
    logger.info(f"🎯 TEST RESULTS: {passed}/{total} passed")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED!")
        logger.info("✅ Fully automated extraction is ready")
        logger.info("\n🚀 Run: python3 run_unified_with_1password.py")
    else:
        logger.error("❌ Some tests failed")
        logger.info("\n🔧 Run: python3 setup_1password_automation.py")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        sys.exit(1)