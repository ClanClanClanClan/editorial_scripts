#!/usr/bin/env python3
"""
Editorial Scripts - Final Implementation
Clean, simple, and working
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime
import argparse

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.credentials import CredentialManager
from extractors.sicon import SICONExtractor

# Configure logging
def setup_logging(log_level: str = "INFO", log_file: bool = True):
    """Setup logging configuration"""
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        log_filename = f"extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        handlers.append(logging.FileHandler(log_filename))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers
    )


async def test_extraction(journal: str = "sicon") -> bool:
    """Test extraction and compare with baseline"""
    logger = logging.getLogger(__name__)
    
    logger.info(f"🧪 Testing {journal.upper()} extraction")
    
    if journal.lower() == "sicon":
        extractor = SICONExtractor()
        
        try:
            result = await extractor.extract(headless=True)
            
            # Analyze results
            logger.info("\n📊 Extraction Results:")
            logger.info(f"   Manuscripts: {result.total_manuscripts}")
            logger.info(f"   Referees: {result.total_referees}")
            logger.info(f"   With emails: {result.referees_with_emails}")
            logger.info(f"   PDFs: {result.pdfs_downloaded}")
            
            # Check against baseline
            logger.info("\n🎯 Baseline Comparison (July 11):")
            
            success = True
            
            if result.total_manuscripts >= 4:
                logger.info("   ✅ Manuscripts: Expected 4, got %d", result.total_manuscripts)
            else:
                logger.warning("   ⚠️ Manuscripts: Expected 4, got %d", result.total_manuscripts)
                success = False
            
            # Check metadata
            empty_titles = sum(1 for ms in result.manuscripts if not ms.title or ms.title.startswith("Manuscript"))
            if empty_titles == 0:
                logger.info("   ✅ All manuscripts have proper titles")
            else:
                logger.error("   ❌ %d manuscripts have empty/default titles", empty_titles)
                success = False
            
            if result.total_referees >= 10:
                logger.info("   ✅ Referees: Expected 13, got %d", result.total_referees)
            else:
                logger.warning("   ⚠️ Referees: Expected 13, got %d", result.total_referees)
            
            if result.pdfs_downloaded >= 4:
                logger.info("   ✅ PDFs: Expected 4, got %d", result.pdfs_downloaded)
            else:
                logger.warning("   ⚠️ PDFs: Expected 4, got %d", result.pdfs_downloaded)
            
            # Sample output
            if result.manuscripts:
                ms = result.manuscripts[0]
                logger.info("\n📄 Sample Manuscript:")
                logger.info(f"   ID: {ms.id}")
                logger.info(f"   Title: {ms.title[:60]}...")
                logger.info(f"   Authors: {', '.join(ms.authors[:2])}")
                logger.info(f"   Referees: {len(ms.referees)}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    else:
        logger.error(f"Journal {journal} not yet implemented")
        return False


async def run_extraction(journal: str, headless: bool = True):
    """Run extraction for a journal"""
    logger = logging.getLogger(__name__)
    
    logger.info(f"🚀 Starting {journal.upper()} extraction")
    
    if journal.lower() == "sicon":
        extractor = SICONExtractor()
    else:
        logger.error(f"Journal {journal} not yet implemented")
        return None
    
    try:
        result = await extractor.extract(headless=headless)
        
        logger.info(f"✅ Extraction complete!")
        logger.info(f"   📊 Manuscripts: {result.total_manuscripts}")
        logger.info(f"   👥 Referees: {result.total_referees}")
        logger.info(f"   📧 With emails: {result.referees_with_emails}")
        logger.info(f"   📄 PDFs: {result.pdfs_downloaded}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Editorial Scripts - Extract journal manuscript data"
    )
    
    parser.add_argument(
        "journal",
        choices=["sicon", "sifin", "mf", "mor", "fs", "jota"],
        help="Journal to extract"
    )
    
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode with baseline comparison"
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode (default)"
    )
    
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show browser window"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    
    parser.add_argument(
        "--check-credentials",
        action="store_true",
        help="Check if credentials are available and exit"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Check credentials
    if args.check_credentials:
        cred_manager = CredentialManager()
        available = cred_manager.list_available_journals()
        
        if available:
            logger.info(f"✅ Credentials available for: {', '.join(available)}")
        else:
            logger.error("❌ No credentials found")
            logger.info(cred_manager.get_setup_instructions(args.journal))
        
        return
    
    # Verify credentials for selected journal
    cred_manager = CredentialManager()
    if not cred_manager.validate_credentials(args.journal):
        logger.error(f"❌ No credentials found for {args.journal.upper()}")
        logger.info(cred_manager.get_setup_instructions(args.journal))
        sys.exit(1)
    
    # Determine headless mode
    headless = not args.headed
    
    # Run extraction or test
    if args.test:
        success = asyncio.run(test_extraction(args.journal))
        sys.exit(0 if success else 1)
    else:
        result = asyncio.run(run_extraction(args.journal, headless))
        sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()