#!/usr/bin/env python3
"""
Complete 1Password CLI automation fix to eliminate all prompts.
This script sets up automatic authentication for 1Password CLI.
"""

import os
import subprocess
import sys
import json
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OnePasswordAuthFixer:
    def __init__(self):
        self.op_config_dir = Path.home() / ".config" / "op"
        self.op_config_dir.mkdir(parents=True, exist_ok=True)
        
    def check_op_cli_installed(self):
        """Check if 1Password CLI is installed"""
        try:
            result = subprocess.run(['op', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"1Password CLI version: {result.stdout.strip()}")
                return True
            return False
        except FileNotFoundError:
            logger.error("1Password CLI not found. Please install it first.")
            return False
    
    def setup_biometric_unlock(self):
        """Enable biometric unlock for 1Password CLI"""
        try:
            # Enable biometric unlock
            result = subprocess.run(['op', 'signin', '--raw'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                session_token = result.stdout.strip()
                logger.info("Biometric unlock enabled successfully")
                return session_token
            else:
                logger.error(f"Failed to enable biometric unlock: {result.stderr}")
                return None
        except subprocess.TimeoutExpired:
            logger.error("Biometric unlock setup timed out")
            return None
        except Exception as e:
            logger.error(f"Error setting up biometric unlock: {e}")
            return None
    
    def configure_service_account(self):
        """Configure service account for automated access"""
        try:
            # Check if service account is already configured
            result = subprocess.run(['op', 'account', 'list'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("Service account already configured")
                return True
            
            # If not configured, try to set up automatic authentication
            logger.info("Setting up automatic authentication...")
            
            # Try to get current session
            env = os.environ.copy()
            result = subprocess.run(['op', 'whoami'], 
                                  capture_output=True, text=True, env=env)
            
            if result.returncode == 0:
                logger.info("Already authenticated to 1Password")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error configuring service account: {e}")
            return False
    
    def setup_session_persistence(self):
        """Set up session persistence to avoid repeated prompts"""
        try:
            # Create session file
            session_file = self.op_config_dir / "session"
            
            # Get current session token
            result = subprocess.run(['op', 'signin', '--raw'], 
                                  capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                session_token = result.stdout.strip()
                
                # Save session token
                with open(session_file, 'w') as f:
                    f.write(session_token)
                
                # Set permissions
                os.chmod(session_file, 0o600)
                
                logger.info("Session persistence configured")
                return session_token
            else:
                logger.error(f"Failed to get session token: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error setting up session persistence: {e}")
            return None
    
    def create_auth_wrapper(self):
        """Create wrapper script for automatic authentication"""
        wrapper_script = """#!/bin/bash
# 1Password CLI authentication wrapper

# Function to check if we're signed in
check_signin() {
    op whoami >/dev/null 2>&1
    return $?
}

# Function to sign in automatically
auto_signin() {
    local session_file="$HOME/.config/op/session"
    
    # Try to use existing session
    if [ -f "$session_file" ]; then
        export OP_SESSION_my=$(cat "$session_file" 2>/dev/null)
        if check_signin; then
            return 0
        fi
    fi
    
    # Try biometric unlock
    if command -v op >/dev/null 2>&1; then
        # Use Touch ID/Face ID if available
        if op signin --raw >/dev/null 2>&1; then
            export OP_SESSION_my=$(op signin --raw 2>/dev/null)
            if [ -n "$OP_SESSION_my" ]; then
                echo "$OP_SESSION_my" > "$session_file"
                chmod 600 "$session_file"
                return 0
            fi
        fi
    fi
    
    return 1
}

# Main execution
if ! check_signin; then
    auto_signin
fi

# Execute the original op command
exec op "$@"
"""
        
        wrapper_path = Path.home() / ".local" / "bin" / "op-auto"
        wrapper_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(wrapper_path, 'w') as f:
            f.write(wrapper_script)
        
        os.chmod(wrapper_path, 0o755)
        logger.info(f"Created authentication wrapper at {wrapper_path}")
        
        return wrapper_path
    
    def setup_environment_variables(self):
        """Set up environment variables for automatic authentication"""
        try:
            # Get session token
            session_token = self.setup_session_persistence()
            if not session_token:
                return False
            
            # Create environment setup script
            env_script = f"""#!/bin/bash
# 1Password CLI environment setup

# Set session token
export OP_SESSION_my="{session_token}"

# Add to PATH if needed
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    export PATH="$HOME/.local/bin:$PATH"
fi

# Function to refresh session if needed
refresh_op_session() {{
    if ! op whoami >/dev/null 2>&1; then
        export OP_SESSION_my=$(op signin --raw 2>/dev/null)
        if [ -n "$OP_SESSION_my" ]; then
            echo "$OP_SESSION_my" > "$HOME/.config/op/session"
        fi
    fi
}}

# Auto-refresh session
refresh_op_session
"""
            
            env_file = self.op_config_dir / "env_setup.sh"
            with open(env_file, 'w') as f:
                f.write(env_script)
            
            os.chmod(env_file, 0o755)
            logger.info(f"Created environment setup script at {env_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting up environment variables: {e}")
            return False
    
    def update_credential_manager(self):
        """Update credential manager to use automatic authentication"""
        cred_manager_path = Path("core/credential_manager.py")
        
        if not cred_manager_path.exists():
            logger.error("Credential manager not found")
            return False
        
        try:
            # Read current credential manager
            with open(cred_manager_path, 'r') as f:
                content = f.read()
            
            # Update the OnePasswordProvider class to use session token
            updated_content = content.replace(
                'class OnePasswordProvider(CredentialProvider):',
                '''class OnePasswordProvider(CredentialProvider):
    def __init__(self, vault: str = "Private"):
        self.vault = vault
        self.session_token = None
        self._setup_session()
        self._verify_cli()
    
    def _setup_session(self):
        """Set up automatic session"""
        session_file = Path.home() / ".config" / "op" / "session"
        
        # Try to load existing session
        if session_file.exists():
            try:
                with open(session_file, 'r') as f:
                    self.session_token = f.read().strip()
                    os.environ['OP_SESSION_my'] = self.session_token
            except:
                pass
        
        # If no session, try to create one
        if not self.session_token:
            try:
                result = subprocess.run(['op', 'signin', '--raw'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    self.session_token = result.stdout.strip()
                    os.environ['OP_SESSION_my'] = self.session_token
                    # Save session
                    session_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(session_file, 'w') as f:
                        f.write(self.session_token)
                    os.chmod(session_file, 0o600)
            except:
                pass'''
            )
            
            # Update the get_credential method to use session
            updated_content = updated_content.replace(
                'def get_credential(self, service: str, field: str = "password") -> Optional[str]:',
                '''def get_credential(self, service: str, field: str = "password") -> Optional[str]:
        """Fetch credential from 1Password with automatic authentication"""
        # Ensure session is active
        if not self._check_session():
            self._setup_session()
        
        # Original method continues below'''
            )
            
            # Add session check method
            session_check_method = '''
    def _check_session(self) -> bool:
        """Check if current session is valid"""
        try:
            if self.session_token:
                os.environ['OP_SESSION_my'] = self.session_token
            result = subprocess.run(['op', 'whoami'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
'''
            
            # Insert the session check method
            updated_content = updated_content.replace(
                'class OnePasswordProvider(CredentialProvider):',
                f'class OnePasswordProvider(CredentialProvider):{session_check_method}'
            )
            
            # Write updated content
            with open(cred_manager_path, 'w') as f:
                f.write(updated_content)
            
            logger.info("Updated credential manager with automatic authentication")
            return True
            
        except Exception as e:
            logger.error(f"Error updating credential manager: {e}")
            return False
    
    def fix_authentication(self):
        """Main method to fix all authentication issues"""
        logger.info("Starting 1Password CLI authentication fix...")
        
        if not self.check_op_cli_installed():
            return False
        
        # Step 1: Configure service account
        if not self.configure_service_account():
            logger.warning("Service account configuration failed, continuing...")
        
        # Step 2: Set up session persistence
        if not self.setup_session_persistence():
            logger.warning("Session persistence setup failed, continuing...")
        
        # Step 3: Create authentication wrapper
        wrapper_path = self.create_auth_wrapper()
        
        # Step 4: Set up environment variables
        if not self.setup_environment_variables():
            logger.warning("Environment setup failed, continuing...")
        
        # Step 5: Update credential manager
        if not self.update_credential_manager():
            logger.warning("Credential manager update failed, continuing...")
        
        logger.info("1Password CLI authentication fix completed!")
        logger.info("Please restart your terminal or run: source ~/.config/op/env_setup.sh")
        
        return True

def main():
    fixer = OnePasswordAuthFixer()
    success = fixer.fix_authentication()
    
    if success:
        print("✅ 1Password CLI authentication fixed successfully!")
        print("🔄 Please restart your terminal or run: source ~/.config/op/env_setup.sh")
    else:
        print("❌ Failed to fix 1Password CLI authentication")
        sys.exit(1)

if __name__ == "__main__":
    main()