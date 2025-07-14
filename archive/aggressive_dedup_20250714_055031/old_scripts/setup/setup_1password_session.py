#!/usr/bin/env python3
"""
Setup proper 1Password session for automated access
Fixes the Terminal authentication requirement
"""

import subprocess
import sys
import os
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def enable_1password_integration():
    """Enable 1Password CLI integration in Terminal"""
    logger.info("🔐 Setting up 1Password CLI integration for Terminal...")
    
    try:
        # Check if 1Password CLI is installed
        result = subprocess.run(['op', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("❌ 1Password CLI not installed")
            logger.info("Install with: brew install --cask 1password-cli")
            return False
        
        logger.info(f"✅ 1Password CLI version: {result.stdout.strip()}")
        
        # Enable CLI integration in 1Password app
        logger.info("\n📱 ENABLING 1PASSWORD CLI INTEGRATION:")
        logger.info("1. Open 1Password app")
        logger.info("2. Go to Settings > Developer")
        logger.info("3. Enable 'Integrate with 1Password CLI'")
        logger.info("4. Enable 'Connect with 1Password CLI'")
        logger.info("5. Allow Terminal.app when prompted")
        
        input("\nPress Enter when you've enabled CLI integration...")
        
        # Test CLI access
        logger.info("🧪 Testing CLI access...")
        result = subprocess.run(['op', 'whoami'], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"✅ CLI access working: {result.stdout.strip()}")
            return True
        else:
            logger.error("❌ CLI access still not working")
            logger.info("Error: " + result.stderr)
            return False
            
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        return False

def create_session_manager():
    """Create a session manager that handles authentication automatically"""
    session_script = """#!/bin/bash
# 1Password Session Manager
# Automatically handles session authentication

# Check if already signed in
if op whoami >/dev/null 2>&1; then
    echo "✅ Already signed in to 1Password"
    exit 0
fi

# Sign in using biometric unlock
echo "🔐 Signing in to 1Password..."
if op signin --account my.1password.eu >/dev/null 2>&1; then
    echo "✅ Successfully signed in"
    exit 0
else
    echo "❌ Sign-in failed - manual intervention required"
    exit 1
fi
"""
    
    script_path = Path.home() / ".local" / "bin" / "op-session"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(script_path, 'w') as f:
        f.write(session_script)
    
    os.chmod(script_path, 0o755)
    logger.info(f"✅ Session manager created: {script_path}")
    
    return script_path

def setup_environment():
    """Setup environment for seamless 1Password access"""
    logger.info("🔧 Setting up environment...")
    
    # Add to shell profile
    shell_config = """
# 1Password CLI integration
export OP_BIOMETRIC_UNLOCK_ENABLED=true
export OP_SESSION_my=""

# Auto-authenticate function
op_auth() {
    if ! op whoami >/dev/null 2>&1; then
        eval $(op signin --account my.1password.eu)
    fi
}

# Auto-run on terminal start (optional)
# op_auth
"""
    
    profiles = [
        Path.home() / ".zshrc",
        Path.home() / ".bashrc", 
        Path.home() / ".bash_profile"
    ]
    
    for profile in profiles:
        if profile.exists():
            with open(profile, 'a') as f:
                f.write(f"\n# 1Password CLI integration\n{shell_config}\n")
            logger.info(f"✅ Updated {profile}")
            break
    
    return True

def test_orcid_access():
    """Test ORCID credential access"""
    logger.info("🧪 Testing ORCID credential access...")
    
    try:
        # Test username field
        result = subprocess.run(['op', 'item', 'get', 'ORCID', '--fields', 'username'], 
                               capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            username = result.stdout.strip()
            logger.info(f"✅ ORCID username: {username[:3]}****")
        else:
            logger.error("❌ Cannot access ORCID username field")
            logger.info("Make sure ORCID item has 'username' field, not 'email'")
            return False
        
        # Test password field
        result = subprocess.run(['op', 'item', 'get', 'ORCID', '--fields', 'password'], 
                               capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("✅ ORCID password accessible")
        else:
            logger.error("❌ Cannot access ORCID password field")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ ORCID test failed: {e}")
        return False

def main():
    """Complete 1Password setup for automation"""
    logger.info("🚀 1PASSWORD AUTOMATION SETUP")
    logger.info("=" * 60)
    
    steps = [
        ("Enable 1Password Integration", enable_1password_integration),
        ("Create Session Manager", create_session_manager),
        ("Setup Environment", setup_environment),
        ("Test ORCID Access", test_orcid_access)
    ]
    
    for step_name, step_func in steps:
        logger.info(f"\n📋 {step_name}...")
        if step_func():
            logger.info(f"✅ {step_name} completed")
        else:
            logger.error(f"❌ {step_name} failed")
            return False
    
    logger.info(f"\n{'=' * 60}")
    logger.info("🎉 SETUP COMPLETE!")
    logger.info("✅ 1Password CLI integration enabled")
    logger.info("✅ Terminal authentication configured")
    logger.info("✅ ORCID credentials accessible")
    logger.info("\n🚀 Ready for fully automated extraction!")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Setup interrupted")
        sys.exit(1)