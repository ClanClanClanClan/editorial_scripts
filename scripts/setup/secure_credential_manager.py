#!/usr/bin/env python3
"""
Secure Credential Manager for Editorial Scripts
Provides multiple secure methods to store and retrieve credentials
"""

import os
import sys
import json
import base64
import keyring
import getpass
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Dict, Optional


class SecureCredentialManager:
    """Manage credentials securely with multiple storage options"""
    
    def __init__(self):
        self.app_name = "editorial_scripts"
        self.credential_dir = Path.home() / ".editorial_scripts"
        self.credential_dir.mkdir(exist_ok=True, mode=0o700)
        
    def setup_credentials(self):
        """Interactive setup for credentials"""
        print("🔐 Editorial Scripts Credential Setup")
        print("=" * 50)
        print("\nChoose credential storage method:")
        print("1. System Keychain (Most Secure - Recommended)")
        print("2. Encrypted File with Master Password")
        print("3. Environment File (.env)")
        print("4. Shell Profile (bash/zsh)")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        # Get credentials
        print("\n📝 Enter your credentials:")
        orcid_email = input("ORCID Email: ").strip()
        orcid_password = getpass.getpass("ORCID Password: ")
        
        # Optional additional credentials
        print("\n📝 Optional credentials (press Enter to skip):")
        scholarone_email = input("ScholarOne Email: ").strip() or None
        scholarone_password = getpass.getpass("ScholarOne Password: ") if scholarone_email else None
        
        credentials = {
            "ORCID_EMAIL": orcid_email,
            "ORCID_PASSWORD": orcid_password,
        }
        
        if scholarone_email:
            credentials.update({
                "SCHOLARONE_EMAIL": scholarone_email,
                "SCHOLARONE_PASSWORD": scholarone_password,
            })
        
        # Store based on choice
        if choice == "1":
            self._store_in_keychain(credentials)
        elif choice == "2":
            self._store_encrypted_file(credentials)
        elif choice == "3":
            self._store_env_file(credentials)
        elif choice == "4":
            self._store_shell_profile(credentials)
        else:
            print("❌ Invalid choice")
            return
        
        print("\n✅ Credentials stored successfully!")
        print("\n🧪 Testing credential retrieval...")
        self.test_credentials()
    
    def _store_in_keychain(self, credentials: Dict[str, str]):
        """Store credentials in system keychain (macOS Keychain, Windows Credential Manager, Linux Secret Service)"""
        try:
            for key, value in credentials.items():
                keyring.set_password(self.app_name, key, value)
            
            # Create loader script
            loader_script = f"""#!/bin/bash
# Load credentials from system keychain
export ORCID_EMAIL=$(python3 -c "import keyring; print(keyring.get_password('{self.app_name}', 'ORCID_EMAIL'))")
export ORCID_PASSWORD=$(python3 -c "import keyring; print(keyring.get_password('{self.app_name}', 'ORCID_PASSWORD'))")
"""
            
            if "SCHOLARONE_EMAIL" in credentials:
                loader_script += f"""export SCHOLARONE_EMAIL=$(python3 -c "import keyring; print(keyring.get_password('{self.app_name}', 'SCHOLARONE_EMAIL'))")
export SCHOLARONE_PASSWORD=$(python3 -c "import keyring; print(keyring.get_password('{self.app_name}', 'SCHOLARONE_PASSWORD'))")
"""
            
            script_path = self.credential_dir / "load_credentials.sh"
            script_path.write_text(loader_script)
            script_path.chmod(0o700)
            
            print(f"\n📌 Credentials stored in system keychain")
            print(f"📌 To load credentials in any session:")
            print(f"   source {script_path}")
            
        except Exception as e:
            print(f"❌ Failed to store in keychain: {e}")
            print("   Falling back to encrypted file method...")
            self._store_encrypted_file(credentials)
    
    def _store_encrypted_file(self, credentials: Dict[str, str]):
        """Store credentials in encrypted file with master password"""
        master_password = getpass.getpass("\nEnter master password for encryption: ")
        confirm_password = getpass.getpass("Confirm master password: ")
        
        if master_password != confirm_password:
            print("❌ Passwords don't match!")
            return
        
        # Generate encryption key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'editorial_scripts_salt',  # In production, use random salt
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
        fernet = Fernet(key)
        
        # Encrypt credentials
        encrypted_data = fernet.encrypt(json.dumps(credentials).encode())
        
        # Save encrypted file
        encrypted_file = self.credential_dir / "credentials.enc"
        encrypted_file.write_bytes(encrypted_data)
        encrypted_file.chmod(0o600)
        
        # Create loader script
        loader_script = f"""#!/usr/bin/env python3
import os
import sys
import json
import base64
import getpass
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def load_encrypted_credentials():
    encrypted_file = Path("{encrypted_file}")
    if not encrypted_file.exists():
        print("❌ Encrypted credentials file not found")
        sys.exit(1)
    
    master_password = getpass.getpass("Enter master password: ")
    
    # Recreate key
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'editorial_scripts_salt',
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
    fernet = Fernet(key)
    
    try:
        encrypted_data = encrypted_file.read_bytes()
        decrypted_data = fernet.decrypt(encrypted_data)
        credentials = json.loads(decrypted_data)
        
        # Export to environment
        for key, value in credentials.items():
            print(f'export {{key}}="{{value}}"')
    
    except Exception as e:
        print(f"❌ Failed to decrypt: {{e}}")
        sys.exit(1)

if __name__ == "__main__":
    load_encrypted_credentials()
"""
        
        loader_path = self.credential_dir / "load_encrypted.py"
        loader_path.write_text(loader_script)
        loader_path.chmod(0o700)
        
        # Create bash wrapper
        bash_wrapper = f"""#!/bin/bash
# Load encrypted credentials
eval "$(python3 {loader_path})"
"""
        
        wrapper_path = self.credential_dir / "load_credentials.sh"
        wrapper_path.write_text(bash_wrapper)
        wrapper_path.chmod(0o700)
        
        print(f"\n📌 Credentials encrypted and stored in {encrypted_file}")
        print(f"📌 To load credentials in any session:")
        print(f"   source {wrapper_path}")
    
    def _store_env_file(self, credentials: Dict[str, str]):
        """Store credentials in .env file"""
        env_file = self.credential_dir / ".env"
        
        env_content = "# Editorial Scripts Credentials\n"
        env_content += "# SECURITY WARNING: This file contains sensitive credentials\n\n"
        
        for key, value in credentials.items():
            env_content += f'{key}="{value}"\n'
        
        env_file.write_text(env_content)
        env_file.chmod(0o600)
        
        # Create loader script
        loader_script = f"""#!/bin/bash
# Load credentials from .env file
set -a
source {env_file}
set +a
"""
        
        loader_path = self.credential_dir / "load_credentials.sh"
        loader_path.write_text(loader_script)
        loader_path.chmod(0o700)
        
        print(f"\n📌 Credentials stored in {env_file}")
        print(f"📌 To load credentials in any session:")
        print(f"   source {loader_path}")
        
        # Also create .envrc for direnv users
        envrc_content = f"source {loader_path}"
        envrc_path = Path.cwd() / ".envrc"
        envrc_path.write_text(envrc_content)
        print(f"\n📌 Also created .envrc for direnv users")
    
    def _store_shell_profile(self, credentials: Dict[str, str]):
        """Add credentials to shell profile"""
        shell = os.environ.get("SHELL", "/bin/bash")
        
        if "zsh" in shell:
            profile_file = Path.home() / ".zshrc"
        elif "bash" in shell:
            profile_file = Path.home() / ".bashrc"
        else:
            profile_file = Path.home() / ".profile"
        
        print(f"\n📌 Adding credentials to {profile_file}")
        
        # Create backup
        if profile_file.exists():
            backup_file = profile_file.with_suffix(profile_file.suffix + ".backup")
            backup_file.write_text(profile_file.read_text())
            print(f"📌 Backup created: {backup_file}")
        
        # Add credentials section
        profile_content = "\n\n# Editorial Scripts Credentials (added by secure_credential_manager.py)\n"
        profile_content += "# To remove, delete this section\n"
        
        for key, value in credentials.items():
            # Escape special characters
            escaped_value = value.replace('"', '\\"').replace('$', '\\$')
            profile_content += f'export {key}="{escaped_value}"\n'
        
        profile_content += "# End Editorial Scripts Credentials\n"
        
        # Append to profile
        with profile_file.open('a') as f:
            f.write(profile_content)
        
        print(f"\n✅ Credentials added to {profile_file}")
        print(f"📌 To load credentials:")
        print(f"   source {profile_file}")
        print(f"   OR start a new terminal session")
    
    def test_credentials(self):
        """Test if credentials are accessible"""
        print("\n🧪 Testing credential access...")
        
        # Try environment variables first
        orcid_email = os.getenv("ORCID_EMAIL")
        orcid_password = os.getenv("ORCID_PASSWORD")
        
        if orcid_email and orcid_password:
            print(f"✅ ORCID_EMAIL: {orcid_email}")
            print(f"✅ ORCID_PASSWORD: {'*' * len(orcid_password)}")
            return True
        
        # Try keychain
        try:
            orcid_email = keyring.get_password(self.app_name, "ORCID_EMAIL")
            orcid_password = keyring.get_password(self.app_name, "ORCID_PASSWORD")
            
            if orcid_email and orcid_password:
                print(f"✅ Found credentials in keychain")
                print(f"✅ ORCID_EMAIL: {orcid_email}")
                print(f"✅ ORCID_PASSWORD: {'*' * len(orcid_password)}")
                return True
        except:
            pass
        
        print("❌ No credentials found in environment or keychain")
        return False
    
    def show_usage(self):
        """Show how to use stored credentials"""
        print("\n📚 How to Use Stored Credentials")
        print("=" * 50)
        
        loader_script = self.credential_dir / "load_credentials.sh"
        if loader_script.exists():
            print(f"\n1. Load credentials in current session:")
            print(f"   source {loader_script}")
            print(f"\n2. Use with editorial scripts:")
            print(f"   source {loader_script}")
            print(f"   cd editorial_scripts_ultimate")
            print(f"   python main.py sicon --test")
        
        print(f"\n3. Add to your shell profile for automatic loading:")
        print(f"   echo 'source {loader_script}' >> ~/.zshrc  # or ~/.bashrc")
        
        print(f"\n4. Use with direnv (if .envrc exists):")
        print(f"   direnv allow")
        
        print(f"\n5. Test credentials anytime:")
        print(f"   python {__file__} --test")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Secure Credential Manager for Editorial Scripts")
    parser.add_argument("--setup", action="store_true", help="Setup credentials")
    parser.add_argument("--test", action="store_true", help="Test credential access")
    parser.add_argument("--usage", action="store_true", help="Show usage instructions")
    
    args = parser.parse_args()
    
    manager = SecureCredentialManager()
    
    if args.setup:
        manager.setup_credentials()
    elif args.test:
        manager.test_credentials()
    elif args.usage:
        manager.show_usage()
    else:
        print("🔐 Secure Credential Manager for Editorial Scripts")
        print("\nOptions:")
        print("  --setup   Setup credentials")
        print("  --test    Test credential access")
        print("  --usage   Show usage instructions")
        print("\nExample: python secure_credential_manager.py --setup")


if __name__ == "__main__":
    main()