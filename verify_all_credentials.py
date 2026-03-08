#!/usr/bin/env python3
"""
Verify all journal credentials are properly configured.

This script checks that all required credentials are available for the
8 supported journals across 4 different platforms.
"""

import os
import sys
from pathlib import Path


class CredentialVerifier:
    """Verifies that all journal credentials are properly configured."""

    def __init__(self):
        """Initialize the credential verifier."""
        self.journals = {
            # ScholarOne (Manuscript Central)
            "MF": {
                "name": "Mathematical Finance",
                "platform": "ScholarOne",
                "email_env": "MF_EMAIL",
                "password_env": "MF_PASSWORD",
            },
            "MOR": {
                "name": "Mathematics of Operations Research",
                "platform": "ScholarOne",
                "email_env": "MOR_EMAIL",
                "password_env": "MOR_PASSWORD",
            },
            # SIAM (ORCID Authentication)
            "SICON": {
                "name": "SIAM Control and Optimization",
                "platform": "SIAM",
                "email_env": "SICON_EMAIL",
                "password_env": "SICON_PASSWORD",
            },
            "SIFIN": {
                "name": "SIAM Financial Mathematics",
                "platform": "SIAM",
                "email_env": "SIFIN_EMAIL",
                "password_env": "SIFIN_PASSWORD",
            },
            # EditFlow (MSP)
            "NACO": {
                "name": "Numerical Algebra, Control and Optimization",
                "platform": "EditFlow (MSP)",
                "email_env": "NACO_USERNAME",
                "password_env": "NACO_PASSWORD",
            },
            # Editorial Manager
            "JOTA": {
                "name": "Journal of Optimization Theory and Applications",
                "platform": "Editorial Manager",
                "email_env": "JOTA_USERNAME",
                "password_env": "JOTA_PASSWORD",
            },
            "MAFE": {
                "name": "Mathematics and Financial Economics",
                "platform": "Editorial Manager",
                "email_env": "MAFE_USERNAME",
                "password_env": "MAFE_PASSWORD",
            },
            "FS": {
                "name": "Finance and Stochastics",
                "platform": "Email (Gmail)",
                "email_env": None,
                "password_env": None,
            },
        }

    def check_environment_variables(self):
        """Check if all required environment variables are set."""
        print("🔍 Checking environment variables...")

        all_present = True
        missing_vars = []

        for journal_code, journal_info in self.journals.items():
            email_var = journal_info["email_env"]
            password_var = journal_info["password_env"]

            if email_var is None and password_var is None:
                print(
                    f"  {journal_code:6} ({journal_info['platform']:16}): ✅ OAuth (no env vars needed)"
                )
                continue

            email_present = bool(os.getenv(email_var)) if email_var else True
            password_present = bool(os.getenv(password_var)) if password_var else True

            status_email = "✅" if email_present else "❌"
            status_password = "✅" if password_present else "❌"

            print(
                f"  {journal_code:6} ({journal_info['platform']:16}): {status_email} {email_var:12} {status_password} {password_var}"
            )

            if not email_present:
                missing_vars.append(email_var)
                all_present = False
            if not password_present:
                missing_vars.append(password_var)
                all_present = False

        if not all_present:
            print(f"\n❌ Missing environment variables: {', '.join(missing_vars)}")
            print("\n💡 To load credentials, run:")
            print("   source ~/.editorial_scripts/load_all_credentials.sh")
        else:
            print("\n✅ All environment variables are set!")

        return all_present

    def check_keychain_status(self):
        """Check if credentials are stored in macOS Keychain."""
        print("\n🔐 Checking macOS Keychain storage...")

        try:
            import subprocess

            keychain_services = []

            for journal_code in self.journals.keys():
                service_name = f"editorial-scripts-{journal_code.lower()}"
                try:
                    # Check if keychain entry exists
                    result = subprocess.run(
                        ["security", "find-generic-password", "-s", service_name, "-w"],
                        capture_output=True,
                        text=True,
                    )

                    if result.returncode == 0:
                        print(f"  ✅ {journal_code}: Stored in keychain")
                        keychain_services.append(service_name)
                    else:
                        print(f"  ❌ {journal_code}: Not in keychain")

                except Exception as e:
                    print(f"  ⚠️ {journal_code}: Could not check keychain - {e}")

            if keychain_services:
                print(f"\n✅ Found {len(keychain_services)} services in keychain")
            else:
                print("\n❌ No credentials found in keychain")
                print("\n💡 To store in keychain, use:")
                print(
                    "   security add-generic-password -s 'editorial-scripts-mf' -a 'email' -w 'password'"
                )

        except ImportError:
            print("  ⚠️ Could not check keychain (not on macOS or missing tools)")

    def check_gmail_api_setup(self):
        """Check if Gmail API is properly configured for 2FA."""
        print("\n📧 Checking Gmail API setup...")

        gmail_files = [
            "config/gmail_credentials.json",
            "config/gmail_token.json",
            "config/gmail_token.pickle",
        ]

        found_files = []
        for file_path in gmail_files:
            if Path(file_path).exists():
                found_files.append(file_path)
                print(f"  ✅ {file_path}: Found")
            else:
                print(f"  ❌ {file_path}: Missing")

        if found_files:
            print(f"\n✅ Gmail API files found: {len(found_files)}")
        else:
            print("\n❌ No Gmail API files found")
            print("\n💡 Gmail API is needed for 2FA code retrieval")

    def test_production_extractors(self):
        """Test if production extractors can be imported."""
        print("\n🧪 Testing production extractors...")

        extractors = {
            "MF": "production/src/extractors/mf_extractor.py",
            "MOR": "production/src/extractors/mor_extractor.py",
        }

        for journal, extractor_path in extractors.items():
            if Path(extractor_path).exists():
                try:
                    # Test import from correct directory
                    original_cwd = os.getcwd()
                    original_path = sys.path[:]

                    extractor_dir = Path(extractor_path).parent.absolute()
                    os.chdir(extractor_dir)
                    sys.path.insert(0, str(extractor_dir))

                    if journal == "MF":
                        import mf_extractor

                        extractor = mf_extractor.ComprehensiveMFExtractor()
                        print(f"  ✅ {journal}: Extractor imports and instantiates")
                    elif journal == "MOR":
                        import mor_extractor

                        extractor = mor_extractor.MORExtractor()
                        print(f"  ✅ {journal}: Extractor imports and instantiates")

                    # Cleanup
                    os.chdir(original_cwd)
                    sys.path[:] = original_path

                except Exception as e:
                    # Cleanup on error
                    os.chdir(original_cwd)
                    sys.path[:] = original_path
                    print(f"  ❌ {journal}: Import failed - {e}")
            else:
                print(f"  ❌ {journal}: Extractor file not found")

    def run_verification(self):
        """Run complete credential verification."""
        print("🔐 EDITORIAL SCRIPTS CREDENTIAL VERIFICATION")
        print("=" * 50)

        # Check environment variables
        env_ok = self.check_environment_variables()

        # Check keychain
        self.check_keychain_status()

        # Check Gmail API
        self.check_gmail_api_setup()

        # Test extractors
        self.test_production_extractors()

        # Final summary
        print("\n" + "=" * 50)
        if env_ok:
            print("🎉 VERIFICATION COMPLETE: All credentials are configured!")
            print("\n✅ You can now run the extractors:")
            print("   cd production/src/extractors")
            print("   python3 mf_extractor.py")
            print("   python3 mor_extractor.py")
        else:
            print("❌ VERIFICATION FAILED: Missing credentials")
            print("\n💡 Next steps:")
            print("1. Load environment variables:")
            print("   source ~/.editorial_scripts/load_all_credentials.sh")
            print("2. Or store in keychain using security command")
            print("3. Re-run this script to verify")

        return env_ok


def main():
    """Main entry point."""
    verifier = CredentialVerifier()
    success = verifier.run_verification()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
