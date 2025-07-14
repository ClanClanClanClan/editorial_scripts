#!/usr/bin/env python3
"""
Main entry point for production editorial scripts
Simple, clean interface for running extractions
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.credentials import CredentialManager
from extractors.sicon import SICONExtractor

# Configure logging
def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f"extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        ]
    )

async def run_sicon_extraction(headless: bool = True) -> Optional[dict]:
    """Run SICON extraction"""
    try:
        logger = logging.getLogger(__name__)
        logger.info("🚀 Starting SICON extraction")
        
        # Create extractor
        extractor = SICONExtractor()
        
        # Run extraction
        result = await extractor.extract(headless=headless)
        
        # Summary
        logger.info(f"✅ Extraction complete!")
        logger.info(f"   📊 Manuscripts: {result.total_manuscripts}")
        logger.info(f"   👥 Referees: {result.total_referees}")
        logger.info(f"   📧 With emails: {result.referees_with_emails}")
        logger.info(f"   📄 PDFs downloaded: {result.pdfs_downloaded}")
        
        # Status breakdown
        if result.referee_status_breakdown:
            logger.info("   📈 Referee status breakdown:")
            for status, count in result.referee_status_breakdown.items():
                logger.info(f"      - {status}: {count}")
        
        return result.to_dict()
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Editorial Scripts - Production System")
    parser.add_argument(
        "journal",
        choices=["sicon", "sifin", "mf", "mor", "all"],
        help="Journal to extract"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run in headless mode (default: True)"
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run in headed mode (show browser)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    parser.add_argument(
        "--check-credentials",
        action="store_true",
        help="Check credentials and exit"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Check credentials if requested
    if args.check_credentials:
        cred_manager = CredentialManager()
        logger.info("🔐 Checking credentials...")
        
        available = cred_manager.list_available_journals()
        if available:
            logger.info(f"✅ Credentials available for: {', '.join(available)}")
        else:
            logger.error("❌ No credentials found")
            logger.error("Please set environment variables:")
            logger.error("  - ORCID_EMAIL and ORCID_PASSWORD for SICON/SIFIN")
            logger.error("  - SCHOLARONE_EMAIL and SCHOLARONE_PASSWORD for MF/MOR")
        
        return
    
    # Determine headless mode
    headless = not args.headed
    
    # Run extraction based on journal
    if args.journal == "sicon":
        await run_sicon_extraction(headless=headless)
    elif args.journal == "sifin":
        logger.warning("SIFIN extraction not yet implemented")
    elif args.journal == "mf":
        logger.warning("MF extraction not yet implemented")
    elif args.journal == "mor":
        logger.warning("MOR extraction not yet implemented")
    elif args.journal == "all":
        logger.info("Running all available extractions...")
        cred_manager = CredentialManager()
        available = cred_manager.list_available_journals()
        
        for journal in available:
            logger.info(f"\n{'='*60}")
            logger.info(f"Running {journal.upper()} extraction...")
            logger.info(f"{'='*60}\n")
            
            if journal == "sicon":
                await run_sicon_extraction(headless=headless)
            else:
                logger.warning(f"{journal.upper()} extraction not yet implemented")

if __name__ == "__main__":
    asyncio.run(main())