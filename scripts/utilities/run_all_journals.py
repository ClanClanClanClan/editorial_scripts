#!/usr/bin/env python3
"""
Complete Journal Extraction System - All Journals Supported
Supports: SICON, SIFIN, MF, MOR, FS, JOTA
"""

import asyncio
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

def setup_logging():
    """Set up logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'extraction_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )

async def run_extraction(journal: str, output_dir: str = None):
    """Run extraction for specified journal"""
    
    logger = logging.getLogger(__name__)
    
    print(f"🚀 COMPLETE JOURNAL EXTRACTION SYSTEM")
    print(f"📖 Journal: {journal.upper()}")
    print(f"🔐 Using: Secure Credential Manager")
    print("=" * 50)
    
    # Import credential manager
    try:
        from src.core.credential_manager import get_credential_manager
        cred_manager = get_credential_manager()
        
        # Test credentials
        creds = cred_manager.get_credentials(journal)
        if not creds:
            print(f"❌ No credentials found for {journal}")
            print("💡 Run: python3 secure_credential_manager.py setup")
            return False
        
        print(f"✅ Credentials loaded: {creds['username'][:10]}...")
        
    except Exception as e:
        print(f"❌ Credential manager error: {e}")
        return False
    
    # Import appropriate scraper
    try:
        journal_lower = journal.lower()
        
        if journal_lower in ['sicon', 'sifin']:
            # SIAM journals
            if journal_lower == 'sicon':
                from src.infrastructure.scrapers.siam.sicon_scraper import SICONRealExtractor
                extractor = SICONRealExtractor()
            else:
                from src.infrastructure.scrapers.siam.sifin_scraper import SIFINExtractor  
                extractor = SIFINExtractor()
            
        elif journal_lower in ['mf', 'mor']:
            # ScholarOne journals
            if journal_lower == 'mf':
                from src.infrastructure.scrapers.scholarone.mf_scraper import MFScraperFixed
                extractor = MFScraperFixed()
            else:
                from src.infrastructure.scrapers.scholarone.mor_scraper import MORScraperFixed
                extractor = MORScraperFixed()
                
        elif journal_lower in ['fs', 'jota']:
            # Email-based journals
            if journal_lower == 'fs':
                from src.infrastructure.scrapers.email_based.fs_scraper import FSScraperFixed
                extractor = FSScraperFixed()
            else:
                from src.infrastructure.scrapers.email_based.jota_scraper import JOTAScraperFixed
                extractor = JOTAScraperFixed()
                
        else:
            print(f"❌ Unknown journal: {journal}")
            print("💡 Available journals: SICON, SIFIN, MF, MOR, FS, JOTA")
            return False
        
        # Set output directory
        if output_dir:
            extractor.output_dir = Path(output_dir)
        
        # Set credentials
        extractor.username = creds['username']
        extractor.password = creds['password']
        
        print(f"✅ {journal.upper()} scraper initialized")
        
        # Run extraction
        print(f"🔄 Starting {journal.upper()} extraction...")
        results = await extractor.extract(
            username=creds['username'],
            password=creds['password'],
            headless=True
        )
        
        if results and results.get('manuscripts'):
            manuscripts = results['manuscripts']
            print(f"✅ Extraction completed!")
            print(f"📊 Found {len(manuscripts)} manuscripts")
            print(f"📁 Output: {extractor.output_dir}")
            
            # Show statistics
            if 'statistics' in results:
                stats = results['statistics']
                print(f"👥 Total referees: {stats.get('total_referees', 0)}")
                print(f"📄 PDFs found: {stats.get('pdfs_found', 0)}")
            
            return True
        else:
            print(f"❌ No manuscripts found")
            return False
            
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        logger.exception("Extraction error")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Complete Journal Extraction System')
    parser.add_argument('--journal', '-j', required=True, 
                       choices=['SICON', 'SIFIN', 'MF', 'MOR', 'FS', 'JOTA'],
                       help='Journal to extract from')
    parser.add_argument('--output', '-o', 
                       help='Output directory (optional)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose logging')
    
    args = parser.parse_args()
    
    # Set up logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    setup_logging()
    
    # Check master password
    import os
    if not os.environ.get('EDITORIAL_MASTER_PASSWORD'):
        print("❌ EDITORIAL_MASTER_PASSWORD environment variable not set")
        print("💡 Set it with: export EDITORIAL_MASTER_PASSWORD='your_password'")
        return 1
    
    # Run extraction
    try:
        success = asyncio.run(run_extraction(args.journal, args.output))
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⚠️ Extraction cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())