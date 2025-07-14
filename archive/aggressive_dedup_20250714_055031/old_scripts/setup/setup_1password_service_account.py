#!/usr/bin/env python3
"""
Setup 1Password Service Account for CLI automation
Eliminates authentication prompts completely
"""

import subprocess
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_service_account():
    """Setup 1Password Service Account for automation"""
    logger.info("🔐 Setting up 1Password Service Account...")
    
    logger.info("\n📋 INSTRUCTIONS:")
    logger.info("1. Go to https://start.1password.com/settings/tokens")
    logger.info("2. Create a new Service Account token")
    logger.info("3. Give it access to your vault with ORCID credentials")
    logger.info("4. Copy the token when generated")
    
    token = input("\nPaste your service account token: ").strip()
    
    if not token:
        logger.error("❌ No token provided")
        return False
    
    # Set environment variable
    os.environ['OP_SERVICE_ACCOUNT_TOKEN'] = token
    
    # Add to shell profile for persistence
    shell_files = [
        os.path.expanduser("~/.zshrc"),
        os.path.expanduser("~/.bashrc"),
        os.path.expanduser("~/.bash_profile")
    ]
    
    env_line = f'export OP_SERVICE_ACCOUNT_TOKEN="{token}"\n'
    
    for shell_file in shell_files:
        if os.path.exists(shell_file):
            with open(shell_file, 'a') as f:
                f.write(f"\n# 1Password Service Account\n{env_line}")
            logger.info(f"✅ Added to {shell_file}")
            break
    
    # Test the token
    try:
        result = subprocess.run(['op', 'whoami'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info(f"✅ Service account working: {result.stdout.strip()}")
            return True
        else:
            logger.error(f"❌ Service account test failed: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

def test_credentials():
    """Test ORCID credential access with service account"""
    logger.info("🧪 Testing ORCID credentials...")
    
    try:
        # Test username with vault specified
        result = subprocess.run(['op', 'item', 'get', 'ORCID', '--fields', 'username', '--vault', 'Private'], 
                               capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            username = result.stdout.strip()
            logger.info(f"✅ Username: {username[:3]}****")
        else:
            logger.error(f"❌ Username failed: {result.stderr}")
            return False
        
        # Test password with vault specified
        result = subprocess.run(['op', 'item', 'get', 'ORCID', '--fields', 'password', '--vault', 'Private'], 
                               capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("✅ Password accessible")
        else:
            logger.error(f"❌ Password failed: {result.stderr}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Credential test failed: {e}")
        return False

def main():
    """Setup complete service account automation"""
    logger.info("🚀 1PASSWORD SERVICE ACCOUNT SETUP")
    logger.info("=" * 60)
    
    if setup_service_account():
        if test_credentials():
            logger.info("\n🎉 SETUP COMPLETE!")
            logger.info("✅ No more authentication prompts")
            logger.info("✅ Fully automated 1Password access")
            logger.info("\n🔄 Restart your terminal to apply changes")
            return True
    
    logger.error("\n❌ Setup failed")
    return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Setup interrupted")
        sys.exit(1)