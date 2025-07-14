#!/usr/bin/env python3
"""
Secure Credential Manager - Alternative to 1Password CLI
Uses encrypted local storage with master password
"""

import os
import json
import base64
import hashlib
import getpass
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import sys

class SecureCredentialManager:
    """Secure local credential storage"""
    
    def __init__(self):
        self.creds_file = Path.home() / ".editorial_credentials"
        self.salt_file = Path.home() / ".editorial_salt"
        
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def _load_from_environment(self, credentials: dict) -> bool:
        """Load credentials from environment variables"""
        loaded_any = False
        
        # ORCID credentials
        orcid_email = os.environ.get('ORCID_EMAIL')
        orcid_password = os.environ.get('ORCID_PASSWORD')
        if orcid_email and orcid_password:
            credentials['orcid'] = {
                'email': orcid_email,
                'password': orcid_password,
                'username': orcid_email
            }
            loaded_any = True
            print("  ✅ ORCID credentials loaded from environment")
        
        # ScholarOne credentials
        scholar_email = os.environ.get('SCHOLARONE_EMAIL')
        scholar_password = os.environ.get('SCHOLARONE_PASSWORD')
        if scholar_email and scholar_password:
            credentials['scholarone'] = {
                'email': scholar_email,
                'password': scholar_password,
                'username': scholar_email
            }
            loaded_any = True
            print("  ✅ ScholarOne credentials loaded from environment")
        
        return loaded_any
    
    def setup_credentials(self):
        """Set up encrypted credentials for the first time"""
        print("🔐 SECURE CREDENTIAL SETUP")
        print("=" * 40)
        print("This will create an encrypted credential store on your machine.")
        print("You'll only need to do this once.\n")
        
        # Check if master password is in environment
        master_password = os.environ.get('EDITORIAL_MASTER_PASSWORD')
        
        if not master_password:
            # Interactive mode
            try:
                while True:
                    master_password = getpass.getpass("Create a master password for credential storage: ")
                    confirm_password = getpass.getpass("Confirm master password: ")
                    
                    if master_password == confirm_password:
                        break
                    print("❌ Passwords don't match. Try again.")
            except (EOFError, KeyboardInterrupt):
                print("\n❌ Interactive password input not available.")
                print("💡 Set EDITORIAL_MASTER_PASSWORD environment variable:")
                print("   export EDITORIAL_MASTER_PASSWORD='your_secure_password'")
                print("   python3 secure_credential_manager.py setup")
                return False
        else:
            print("✅ Using master password from environment variable")
        
        # Generate salt
        salt = os.urandom(16)
        
        # Save salt
        with open(self.salt_file, 'wb') as f:
            f.write(salt)
        os.chmod(self.salt_file, 0o600)
        
        # Set up encryption
        key = self._derive_key(master_password, salt)
        fernet = Fernet(key)
        
        # Collect credentials
        credentials = {}
        
        # Check if credentials are in environment
        if self._load_from_environment(credentials):
            print("✅ Loaded credentials from environment variables")
        else:
            print("\n📋 Enter your journal credentials:")
            print("(Leave blank to skip any journal)\n")
            
            try:
                # ORCID (for SICON/SIFIN)
                print("🔬 ORCID (for SICON/SIFIN):")
                orcid_email = input("  ORCID Email: ").strip()
                if orcid_email:
                    orcid_password = getpass.getpass("  ORCID Password: ")
                    credentials['orcid'] = {
                        'email': orcid_email,
                        'password': orcid_password,
                        'username': orcid_email
                    }
                    print("  ✅ ORCID credentials saved")
                
                # ScholarOne (for MF/MOR)
                print("\n📚 ScholarOne (for MF/MOR):")
                scholar_email = input("  ScholarOne Email: ").strip()
                if scholar_email:
                    scholar_password = getpass.getpass("  ScholarOne Password: ")
                    credentials['scholarone'] = {
                        'email': scholar_email,
                        'password': scholar_password,
                        'username': scholar_email
                    }
                    print("  ✅ ScholarOne credentials saved")
                
                # Other journals
                other_journals = ['mafe', 'naco', 'jota', 'fs']
                for journal in other_journals:
                    print(f"\n📖 {journal.upper()}:")
                    email = input(f"  {journal.upper()} Email/Username: ").strip()
                    if email:
                        password = getpass.getpass(f"  {journal.upper()} Password: ")
                        credentials[journal] = {
                            'email': email,
                            'password': password,
                            'username': email
                        }
                        print(f"  ✅ {journal.upper()} credentials saved")
            except (EOFError, KeyboardInterrupt):
                print("\n❌ Interactive credential input not available.")
                print("💡 Set environment variables:")
                print("   export ORCID_EMAIL='your@email.com'")
                print("   export ORCID_PASSWORD='your_password'")
                print("   export SCHOLARONE_EMAIL='your@email.com'")  
                print("   export SCHOLARONE_PASSWORD='your_password'")
                print("   python3 secure_credential_manager.py setup")
                return False
        
        # Encrypt and save
        encrypted_data = fernet.encrypt(json.dumps(credentials).encode())
        
        with open(self.creds_file, 'wb') as f:
            f.write(encrypted_data)
        os.chmod(self.creds_file, 0o600)
        
        print(f"\n✅ Credentials encrypted and saved!")
        print(f"📁 Location: {self.creds_file}")
        print(f"🔐 Salt file: {self.salt_file}")
        print("\n⚠️  IMPORTANT:")
        print("- Remember your master password - it cannot be recovered!")
        print("- Keep these files secure")
        print("- You can run this setup again to update credentials")
        
        return True
    
    def get_credentials(self, journal: str) -> dict:
        """Get credentials for a journal"""
        if not self.creds_file.exists() or not self.salt_file.exists():
            print("❌ No encrypted credentials found. Run setup first.")
            return None
        
        try:
            # Read salt
            with open(self.salt_file, 'rb') as f:
                salt = f.read()
            
            # Get master password from environment or prompt
            master_password = os.environ.get('EDITORIAL_MASTER_PASSWORD')
            if not master_password:
                master_password = getpass.getpass("Enter master password: ")
            
            # Derive key
            key = self._derive_key(master_password, salt)
            fernet = Fernet(key)
            
            # Read and decrypt credentials
            with open(self.creds_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = fernet.decrypt(encrypted_data)
            credentials = json.loads(decrypted_data.decode())
            
            # Map journal names
            journal_mapping = {
                'sicon': 'orcid',
                'sifin': 'orcid', 
                'mf': 'scholarone',
                'mor': 'scholarone',
                'mafe': 'mafe',
                'naco': 'naco',
                'jota': 'jota',
                'fs': 'fs'
            }
            
            cred_key = journal_mapping.get(journal.lower(), journal.lower())
            return credentials.get(cred_key)
            
        except Exception as e:
            print(f"❌ Error accessing credentials: {e}")
            return None
    
    def test_credentials(self):
        """Test credential access"""
        print("🧪 TESTING CREDENTIAL ACCESS")
        print("=" * 40)
        
        journals = ['sicon', 'sifin', 'mf', 'mor', 'mafe', 'naco', 'jota', 'fs']
        
        for journal in journals:
            creds = self.get_credentials(journal)
            if creds:
                email = creds.get('email', creds.get('username', 'N/A'))
                print(f"✅ {journal.upper()}: {email[:10]}...@...")
            else:
                print(f"❌ {journal.upper()}: No credentials")
        
        return True
    
    def update_password_env(self):
        """Helper to set master password in environment"""
        master_password = getpass.getpass("Enter master password to save to environment: ")
        
        # Add to .zshrc
        zshrc_path = Path.home() / ".zshrc"
        env_line = f'export EDITORIAL_MASTER_PASSWORD="{master_password}"'
        
        # Check if already exists
        if zshrc_path.exists():
            with open(zshrc_path, 'r') as f:
                content = f.read()
            
            if 'EDITORIAL_MASTER_PASSWORD' in content:
                # Replace existing
                lines = content.split('\n')
                new_lines = []
                for line in lines:
                    if 'EDITORIAL_MASTER_PASSWORD' not in line:
                        new_lines.append(line)
                new_lines.append(env_line)
                content = '\n'.join(new_lines)
            else:
                # Add new
                content += f'\n{env_line}\n'
            
            with open(zshrc_path, 'w') as f:
                f.write(content)
        
        print("✅ Master password added to ~/.zshrc")
        print("⚠️  Run 'source ~/.zshrc' or restart terminal to activate")
        print("🔒 Now extractions will run without password prompts")


def main():
    """Main setup function"""
    manager = SecureCredentialManager()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'setup':
            manager.setup_credentials()
        elif command == 'test':
            manager.test_credentials()
        elif command == 'env':
            manager.update_password_env()
        else:
            print("Usage: python3 secure_credential_manager.py [setup|test|env]")
    else:
        print("🔐 SECURE CREDENTIAL MANAGER")
        print("=" * 40)
        print("Commands:")
        print("  setup - Set up encrypted credentials")
        print("  test  - Test credential access") 
        print("  env   - Add master password to environment")
        print("\nExample: python3 secure_credential_manager.py setup")


if __name__ == "__main__":
    main()