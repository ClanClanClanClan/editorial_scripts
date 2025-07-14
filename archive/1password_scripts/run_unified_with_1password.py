#!/usr/bin/env python3
"""
Run Unified System with 1Password Integration
FULLY AUTOMATED - No manual credential entry required
"""

import asyncio
import logging
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OnePasswordManager:
    """Handles 1Password CLI setup and session management"""
    
    def __init__(self):
        self.session_token = None
        
    def check_cli_installed(self) -> bool:
        """Check if 1Password CLI is installed"""
        try:
            result = subprocess.run(['op', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                logger.info(f"✅ 1Password CLI version: {result.stdout.strip()}")
                return True
            return False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def setup_session(self) -> bool:
        """Set up 1Password session automatically"""
        logger.info("🔐 Setting up 1Password session...")
        
        try:
            # Check if already signed in
            whoami = subprocess.run(['op', 'whoami'], 
                                  capture_output=True, text=True, timeout=10)
            if whoami.returncode == 0:
                logger.info(f"✅ Already signed in as: {whoami.stdout.strip()}")
                return self._get_session_token()
            
            # Try to sign in automatically
            logger.info("🔑 Attempting automatic sign-in...")
            logger.info("💡 You may be prompted for your master password or biometrics")
            
            # Try signin with raw output to get session token
            signin = subprocess.run(['op', 'signin', '--raw'], 
                                  capture_output=True, text=True, timeout=60)
            
            if signin.returncode == 0:
                self.session_token = signin.stdout.strip()
                os.environ['OP_SESSION_my'] = self.session_token
                
                # Save session for future use
                self._save_session_token()
                
                logger.info("✅ Successfully signed in to 1Password")
                return True
            else:
                logger.error(f"❌ Sign-in failed: {signin.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Sign-in timed out - please try again")
            return False
        except Exception as e:
            logger.error(f"❌ Error setting up 1Password session: {e}")
            return False
    
    def _get_session_token(self) -> bool:
        """Get session token for current session"""
        try:
            signin = subprocess.run(['op', 'signin', '--raw'], 
                                  capture_output=True, text=True, timeout=15)
            if signin.returncode == 0:
                self.session_token = signin.stdout.strip()
                os.environ['OP_SESSION_my'] = self.session_token
                self._save_session_token()
                return True
            return False
        except Exception:
            return False
    
    def _save_session_token(self):
        """Save session token for credential manager"""
        try:
            session_file = Path.home() / ".config" / "op" / "session"
            session_file.parent.mkdir(parents=True, exist_ok=True)
            with open(session_file, 'w') as f:
                f.write(self.session_token)
            os.chmod(session_file, 0o600)
        except Exception as e:
            logger.debug(f"Could not save session token: {e}")
    
    def test_credentials(self) -> bool:
        """Test ORCID credential retrieval"""
        logger.info("🔍 Testing ORCID credential retrieval...")
        
        try:
            from src.core.credential_manager import get_credential_manager
            
            cred_manager = get_credential_manager()
            orcid_creds = cred_manager.get_credentials('SICON')
            
            if orcid_creds.get('email') and orcid_creds.get('password'):
                logger.info(f"✅ ORCID credentials found: {orcid_creds['email'][:3]}****@****")
                return True
            else:
                logger.error("❌ ORCID credentials not found in 1Password")
                self._show_setup_instructions()
                return False
                
        except Exception as e:
            logger.error(f"❌ Error testing credentials: {e}")
            return False
    
    def _show_setup_instructions(self):
        """Show instructions for setting up ORCID item in 1Password"""
        logger.info("\n📋 ORCID SETUP INSTRUCTIONS:")
        logger.info("1. Open 1Password app")
        logger.info("2. Create a new Login item")
        logger.info("3. Set Title: ORCID")
        logger.info("4. Add fields:")
        logger.info("   - email: your ORCID email address")
        logger.info("   - password: your ORCID password")
        logger.info("5. Save the item")
        logger.info("6. Run this script again")


async def run_unified_extraction():
    """Run unified system extraction with 1Password credentials"""
    logger.info("🚀 Starting unified system extraction...")
    
    try:
        # Import unified extractors
        from unified_system import SICONExtractor, SIFINExtractor
        
        # Choose journals to extract
        extractors = {
            'SICON': SICONExtractor(),
            'SIFIN': SIFINExtractor()
        }
        
        logger.info(f"📋 Extracting from: {', '.join(extractors.keys())}")
        
        results = {}
        total_manuscripts = 0
        
        for journal_name, extractor in extractors.items():
            logger.info(f"\n{'='*60}")
            logger.info(f"🎯 Extracting from {journal_name}")
            logger.info(f"{'='*60}")
            
            try:
                # Run extraction - credentials will be pulled from 1Password automatically
                result = await extractor.extract(
                    username="",  # Will be overridden by 1Password
                    password="",  # Will be overridden by 1Password
                    headless=True  # Silent operation
                )
                
                if result:
                    results[journal_name] = result
                    total_manuscripts += result['total_manuscripts']
                    
                    logger.info(f"✅ {journal_name} extraction completed:")
                    logger.info(f"   - Manuscripts: {result['total_manuscripts']}")
                    logger.info(f"   - Referees: {result['statistics']['total_referees']}")
                    logger.info(f"   - PDFs downloaded: {result['statistics']['pdfs_downloaded']}")
                else:
                    logger.error(f"❌ {journal_name} extraction failed")
                    results[journal_name] = None
                    
            except Exception as e:
                logger.error(f"❌ {journal_name} extraction failed: {e}")
                results[journal_name] = None
        
        # Summary
        logger.info(f"\n{'='*80}")
        logger.info("🎯 EXTRACTION SUMMARY")
        logger.info(f"{'='*80}")
        
        successful = sum(1 for r in results.values() if r is not None)
        total_journals = len(results)
        
        logger.info(f"Successful extractions: {successful}/{total_journals}")
        logger.info(f"Total manuscripts: {total_manuscripts}")
        
        if successful == total_journals:
            logger.info("\n🎉 ALL EXTRACTIONS COMPLETED SUCCESSFULLY!")
        else:
            logger.warning("\n⚠️ Some extractions failed - check logs above")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Main execution with full 1Password automation"""
    logger.info("🎭 UNIFIED SYSTEM WITH 1PASSWORD INTEGRATION")
    logger.info("🤖 FULLY AUTOMATED - NO MANUAL CREDENTIALS REQUIRED")
    logger.info("="*80)
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Check 1Password CLI
    op_manager = OnePasswordManager()
    
    if not op_manager.check_cli_installed():
        logger.error("❌ 1Password CLI not installed")
        logger.info("💡 Install from: https://1password.com/downloads/command-line/")
        logger.info("💡 Or run: brew install --cask 1password-cli")
        return False
    
    # Step 2: Set up 1Password session
    if not op_manager.setup_session():
        logger.error("❌ Failed to set up 1Password session")
        logger.info("💡 Make sure you're signed in to 1Password desktop app")
        return False
    
    # Step 3: Test credentials
    if not op_manager.test_credentials():
        logger.error("❌ ORCID credentials not found in 1Password")
        return False
    
    # Step 4: Run extraction
    logger.info("\n🚀 All checks passed - starting extraction...")
    results = await run_unified_extraction()
    
    if results:
        logger.info("\n✅ EXTRACTION COMPLETE - FULLY AUTOMATED SUCCESS!")
        return True
    else:
        logger.error("\n❌ EXTRACTION FAILED")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        
        if success:
            logger.info("\n🎉 ALL DONE - AUTOMATION SUCCESSFUL!")
            logger.info("💡 Check the output directories for extracted data")
        else:
            logger.error("\n❌ AUTOMATION FAILED")
            logger.error("💡 Check the logs above for troubleshooting")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)