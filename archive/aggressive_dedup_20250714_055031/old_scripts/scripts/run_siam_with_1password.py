#!/usr/bin/env python3
"""
Run SIAM scraper with 1Password integration
Handles authentication and credential retrieval automatically
"""

import asyncio
import sys
import os
import subprocess
import logging
from pathlib import Path
from datetime import datetime

# Add src and core to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def setup_1password_session():
    """Set up 1Password session"""
    print("🔐 Setting up 1Password session...")
    
    try:
        # First check if already signed in
        whoami = subprocess.run(['op', 'whoami'], capture_output=True, text=True)
        if whoami.returncode == 0:
            print(f"✅ Already signed in as: {whoami.stdout.strip()}")
            
            # Get session token
            signin = subprocess.run(['op', 'signin', '--raw'], capture_output=True, text=True)
            if signin.returncode == 0:
                session_token = signin.stdout.strip()
                os.environ['OP_SESSION_my'] = session_token
                print("✅ Session token retrieved")
                return True
        
        # Try to sign in
        print("🔑 Attempting to sign in to 1Password...")
        print("💡 You may be prompted for your 1Password master password or biometrics")
        
        # Use eval to set environment variable
        signin_cmd = subprocess.run(['op', 'signin', '--raw'], capture_output=True, text=True)
        if signin_cmd.returncode == 0:
            session_token = signin_cmd.stdout.strip()
            os.environ['OP_SESSION_my'] = session_token
            
            # Save session for credential manager
            session_file = Path.home() / ".config" / "op" / "session"
            session_file.parent.mkdir(parents=True, exist_ok=True)
            with open(session_file, 'w') as f:
                f.write(session_token)
            os.chmod(session_file, 0o600)
            
            print("✅ Successfully signed in to 1Password")
            return True
        else:
            print("❌ Failed to sign in to 1Password")
            return False
            
    except Exception as e:
        print(f"❌ Error setting up 1Password session: {e}")
        return False

async def test_credentials():
    """Test credential retrieval"""
    print("\n🔍 Testing credential retrieval...")
    
    try:
        from core.credential_manager import get_credential_manager
        
        cred_manager = get_credential_manager()
        orcid_creds = cred_manager.get_journal_credentials('ORCID')
        
        if orcid_creds.get('email') and orcid_creds.get('password'):
            print("✅ ORCID credentials retrieved successfully")
            print(f"   Email: {orcid_creds['email'][:3]}****")
            return True
        else:
            print("❌ ORCID credentials not found")
            print("\n💡 Checking 1Password for ORCID item...")
            
            # Try to list items
            list_cmd = subprocess.run(['op', 'item', 'list', '--categories', 'Login'], 
                                    capture_output=True, text=True)
            if list_cmd.returncode == 0:
                if 'ORCID' in list_cmd.stdout:
                    print("✅ ORCID item exists in 1Password")
                    print("⚠️ But credentials couldn't be retrieved")
                else:
                    print("❌ No ORCID item found in 1Password")
                    print("\n📋 Please create an ORCID item in 1Password with:")
                    print("   - Title: ORCID")
                    print("   - email field: your ORCID email")
                    print("   - password field: your ORCID password")
            
            return False
            
    except Exception as e:
        print(f"❌ Error testing credentials: {e}")
        import traceback
        traceback.print_exc()
        return False

async def run_siam_extraction(journal_code: str):
    """Run SIAM extraction with credentials from 1Password"""
    print(f"\n🚀 Starting {journal_code} extraction...")
    
    try:
        from src.infrastructure.scrapers.siam_scraper import SIAMScraper
        
        # Create scraper
        scraper = SIAMScraper(journal_code)
        print(f"✅ Created {journal_code} scraper")
        
        # Run extraction
        print(f"🔄 Running extraction (this may take a few minutes)...")
        result = await scraper.run_extraction()
        
        # Display results
        print(f"\n📊 EXTRACTION RESULTS:")
        print(f"   Success: {'✅' if result.success else '❌'}")
        print(f"   Manuscripts: {result.total_count}")
        print(f"   Extraction Time: {result.extraction_time}")
        
        if result.error_message:
            print(f"   Error: {result.error_message}")
        
        if result.manuscripts:
            print(f"\n📄 Sample manuscripts:")
            for i, manuscript in enumerate(result.manuscripts[:3]):
                print(f"   {i+1}. {manuscript.id}: {manuscript.title[:50]}...")
                print(f"      Referees: {len(manuscript.referees)}")
        
        return result
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    """Main execution"""
    print("🎭 SIAM SCRAPER WITH 1PASSWORD INTEGRATION")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Set up 1Password session
    if not setup_1password_session():
        print("\n❌ Failed to set up 1Password session")
        print("💡 Make sure you have 1Password CLI installed and configured")
        return False
    
    # Step 2: Test credentials
    if not await test_credentials():
        print("\n❌ Failed to retrieve credentials from 1Password")
        return False
    
    # Step 3: Choose journal
    print("\n📋 Available SIAM journals:")
    print("   1. SICON - SIAM Journal on Control and Optimization")
    print("   2. SIFIN - SIAM Journal on Financial Mathematics")
    print("   3. BOTH - Extract from both journals")
    
    choice = input("\nSelect journal (1/2/3) [default: 3]: ").strip() or "3"
    
    journals = []
    if choice == "1":
        journals = ["SICON"]
    elif choice == "2":
        journals = ["SIFIN"]
    else:
        journals = ["SICON", "SIFIN"]
    
    # Step 4: Run extraction
    print(f"\n🎯 Extracting from: {', '.join(journals)}")
    
    results = {}
    for journal_code in journals:
        result = await run_siam_extraction(journal_code)
        results[journal_code] = result
    
    # Step 5: Summary
    print(f"\n{'=' * 80}")
    print("🎯 EXTRACTION SUMMARY")
    print("=" * 80)
    
    total_manuscripts = 0
    successful_journals = 0
    
    for journal_code, result in results.items():
        if result and result.success:
            successful_journals += 1
            total_manuscripts += result.total_count
            print(f"✅ {journal_code}: {result.total_count} manuscripts")
        else:
            print(f"❌ {journal_code}: Failed")
    
    print(f"\nTotal: {total_manuscripts} manuscripts from {successful_journals}/{len(journals)} journals")
    
    if successful_journals == len(journals):
        print("\n🎉 All extractions completed successfully!")
    else:
        print("\n⚠️ Some extractions failed. Check the logs for details.")
    
    return successful_journals > 0

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Extraction interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Extraction failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)