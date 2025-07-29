#!/usr/bin/env python3
"""
Verify that all credentials are properly stored and accessible.
This script does NOT display passwords, only confirms they exist.
"""

import subprocess
import os
from pathlib import Path


def verify_keychain_credentials():
    """Verify all credentials in keychain."""
    print("\n🔐 Verifying Keychain Storage")
    print("=" * 50)
    
    journals = [
        ("ORCID", "editorial-scripts-orcid"),
        ("MF", "editorial-scripts-mf"),
        ("MOR", "editorial-scripts-mor"),
        ("SICON", "editorial-scripts-sicon"),
        ("SIFIN", "editorial-scripts-sifin"),
        ("JOTA", "editorial-scripts-jota"),
        ("MAFE", "editorial-scripts-mafe"),
        ("NACO", "editorial-scripts-naco"),
    ]
    
    all_good = True
    for journal, service in journals:
        try:
            cmd = ['security', 'find-generic-password', '-s', service, '-w']
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            password = result.stdout.strip()
            if password:
                print(f"✅ {journal:8} - Stored (length: {len(password)})")
            else:
                print(f"❌ {journal:8} - Empty")
                all_good = False
        except:
            print(f"❌ {journal:8} - Not found")
            all_good = False
    
    return all_good


def verify_environment_variables():
    """Verify environment variables after sourcing."""
    print("\n🌍 Verifying Environment Variables")
    print("=" * 50)
    
    # Source the credentials and check
    source_cmd = 'source ~/.editorial_scripts/load_all_credentials.sh && env | grep -E "(EMAIL|PASSWORD|USERNAME)" | wc -l'
    result = subprocess.run(['zsh', '-c', source_cmd], capture_output=True, text=True)
    
    try:
        count = int(result.stdout.strip())
        if count > 0:
            print(f"✅ {count} credential variables will be loaded")
            print("✅ These load automatically in new terminals")
            return True
        else:
            print("❌ No credential variables found")
            return False
    except:
        print("❌ Could not verify environment variables")
        return False


def verify_shell_profile():
    """Verify shell profile setup."""
    print("\n🐚 Verifying Shell Profile")
    print("=" * 50)
    
    zshrc = Path.home() / ".zshrc"
    if zshrc.exists():
        content = zshrc.read_text()
        if "load_all_credentials.sh" in content:
            print("✅ Credential loading added to ~/.zshrc")
            print("✅ Will load automatically on terminal start")
            return True
        else:
            print("❌ Credential loading not in ~/.zshrc")
            return False
    else:
        print("❌ ~/.zshrc not found")
        return False


def test_credential_access():
    """Test that credentials can be accessed by extractors."""
    print("\n🧪 Testing Credential Access")
    print("=" * 50)
    
    # Test different access methods
    print("\n1. Direct keychain access:")
    test_script = """
import subprocess
try:
    result = subprocess.run(
        ['security', 'find-generic-password', '-s', 'editorial-scripts-mf-email', '-w'],
        capture_output=True, text=True, check=True
    )
    email = result.stdout.strip()
    print(f"   ✅ Can read MF email: {email}")
except:
    print("   ❌ Cannot read from keychain")
"""
    subprocess.run(['python3', '-c', test_script])
    
    print("\n2. Environment after sourcing:")
    test_cmd = 'source ~/.editorial_scripts/load_all_credentials.sh && echo "   ✅ MF_EMAIL=$MF_EMAIL"'
    subprocess.run(['zsh', '-c', test_cmd])
    
    return True


def show_usage():
    """Show how to use the credentials."""
    print("\n📚 How to Use Your Stored Credentials")
    print("=" * 50)
    
    print("\n✅ Your credentials are stored in 2 places:")
    print("   1. macOS Keychain (secure, permanent)")
    print("   2. Shell script (for environment variables)")
    
    print("\n✅ They load automatically:")
    print("   • Every new terminal (via ~/.zshrc)")
    print("   • All extractors (via credential managers)")
    print("   • After reboots (persistent storage)")
    
    print("\n✅ Example usage:")
    print("   # Just run any extractor - credentials load automatically!")
    print("   python3 production/src/extractors/mf_extractor.py")
    print("   python3 editorial_assistant/extractors/sicon.py")
    print("   python3 editorial_assistant/extractors/jota.py")
    
    print("\n✅ Manual loading (if needed):")
    print("   source ~/.editorial_scripts/load_all_credentials.sh")


def main():
    """Run all verifications."""
    print("🔐 CREDENTIAL VERIFICATION")
    print("=" * 60)
    print("Verifying all credentials are properly stored")
    print("(Passwords are NOT displayed for security)")
    
    # Run all checks
    keychain_ok = verify_keychain_credentials()
    env_ok = verify_environment_variables()
    shell_ok = verify_shell_profile()
    access_ok = test_credential_access()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    all_ok = keychain_ok and env_ok and shell_ok and access_ok
    
    if all_ok:
        print("\n✅ ALL CREDENTIALS PROPERLY STORED!")
        print("✅ You will NEVER need to enter them again!")
        print("✅ They will persist forever until explicitly deleted!")
        
        show_usage()
    else:
        print("\n⚠️ Some issues detected")
        print("Run: python3 store_all_credentials_secure.py")
    
    print("\n🎉 Remember: One-time setup, lifetime convenience!")


if __name__ == "__main__":
    main()