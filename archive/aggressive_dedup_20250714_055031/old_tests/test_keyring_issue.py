#!/usr/bin/env python3
"""
Test to identify the keyring issue
"""

import keyring
import sys

# Test basic keyring functionality
print("Testing keyring functionality...")

try:
    # Try to set a simple key
    keyring.set_password("test_service", "test_user", "test_password")
    print("✅ Basic keyring set works")
    
    # Try to get it back
    result = keyring.get_password("test_service", "test_user")
    print(f"✅ Basic keyring get works: {result}")
    
    # Try with a URL-like key (this might fail)
    try:
        keyring.set_password("https://example.com_uid", "test_user", "test_value")
        print("✅ URL-like key works")
    except Exception as e:
        print(f"❌ URL-like key fails: {e}")
        
    # Try with just the problematic key
    try:
        keyring.set_password("https://sifin.siam.org_uid", "test", "value")
        print("✅ Problematic key works")
    except Exception as e:
        print(f"❌ Problematic key fails: {e}")
        
except Exception as e:
    print(f"❌ Keyring error: {e}")
    
# Show keyring backend
print(f"\nKeyring backend: {keyring.get_keyring()}")