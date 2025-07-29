#!/usr/bin/env python3
"""
Secure Credential Storage System
Stores credentials securely in macOS Keychain and loads them automatically.
"""

import subprocess
import os
import sys
import getpass
from pathlib import Path

class SecureCredentialManager:
    def __init__(self):
        self.service_name = "editorial-scripts-mf"
        
    def store_credentials(self, email=None, password=None):
        """Store credentials securely in macOS Keychain."""
        print("🔐 SECURE CREDENTIAL SETUP")
        print("=" * 50)
        
        # Get email
        if not email:
            email = input("📧 Enter your MF email: ").strip()
        
        # Get password
        if not password:
            password = getpass.getpass("🔑 Enter your MF password: ")
        
        try:
            # Store email in keychain
            cmd_email = [
                'security', 'add-generic-password',
                '-a', email,
                '-s', f"{self.service_name}-email",
                '-w', email,
                '-U'  # Update if exists
            ]
            subprocess.run(cmd_email, check=True, capture_output=True)
            
            # Store password in keychain
            cmd_password = [
                'security', 'add-generic-password', 
                '-a', email,
                '-s', f"{self.service_name}-password",
                '-w', password,
                '-U'  # Update if exists
            ]
            subprocess.run(cmd_password, check=True, capture_output=True)
            
            print("✅ Credentials stored securely in macOS Keychain")
            print("🎉 You'll never need to enter them again!")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to store credentials: {e}")
            return False
    
    def load_credentials(self):
        """Load credentials from macOS Keychain."""
        try:
            # Get email
            cmd_email = [
                'security', 'find-generic-password',
                '-s', f"{self.service_name}-email",
                '-w'
            ]
            result_email = subprocess.run(cmd_email, capture_output=True, text=True, check=True)
            email = result_email.stdout.strip()
            
            # Get password  
            cmd_password = [
                'security', 'find-generic-password',
                '-s', f"{self.service_name}-password", 
                '-w'
            ]
            result_password = subprocess.run(cmd_password, capture_output=True, text=True, check=True)
            password = result_password.stdout.strip()
            
            return email, password
            
        except subprocess.CalledProcessError:
            return None, None
    
    def setup_environment(self):
        """Set up environment variables with stored credentials."""
        email, password = self.load_credentials()
        
        if email and password:
            os.environ['MF_EMAIL'] = email
            os.environ['MF_PASSWORD'] = password
            print(f"✅ Loaded credentials for: {email}")
            return True
        else:
            print("❌ No stored credentials found")
            return False
    
    def delete_credentials(self):
        """Delete stored credentials."""
        try:
            # Delete email
            subprocess.run([
                'security', 'delete-generic-password',
                '-s', f"{self.service_name}-email"
            ], capture_output=True)
            
            # Delete password
            subprocess.run([
                'security', 'delete-generic-password', 
                '-s', f"{self.service_name}-password"
            ], capture_output=True)
            
            print("✅ Credentials deleted from keychain")
            return True
            
        except Exception as e:
            print(f"⚠️ Error deleting credentials: {e}")
            return False

def main():
    """Interactive credential management."""
    manager = SecureCredentialManager()
    
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        
        if action == 'store':
            manager.store_credentials()
        elif action == 'load':
            email, password = manager.load_credentials()
            if email:
                print(f"Email: {email}")
                print(f"Password: {'*' * len(password)}")
            else:
                print("No credentials found")
        elif action == 'delete':
            manager.delete_credentials()
        elif action == 'setup':
            manager.setup_environment()
        else:
            print(f"Unknown action: {action}")
    else:
        print("🔐 CREDENTIAL MANAGER")
        print("=" * 30)
        print("1. Store credentials")
        print("2. Load credentials") 
        print("3. Delete credentials")
        print("4. Setup environment")
        
        choice = input("Choose option (1-4): ").strip()
        
        if choice == '1':
            manager.store_credentials()
        elif choice == '2':
            email, password = manager.load_credentials()
            if email:
                print(f"✅ Email: {email}")
                print(f"✅ Password: {'*' * len(password)}")
            else:
                print("❌ No credentials found")
        elif choice == '3':
            manager.delete_credentials()
        elif choice == '4':
            if manager.setup_environment():
                print("✅ Environment ready!")
            else:
                print("❌ Need to store credentials first")

if __name__ == "__main__":
    main()