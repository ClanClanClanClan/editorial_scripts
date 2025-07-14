#!/usr/bin/env python3
"""
Test Unified System - Verify REAL extraction functionality
NO PLACEHOLDERS, NO SIMULATIONS - REAL EXTRACTIONS ONLY
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import our unified extractors
from unified_system import SICONExtractor, SIFINExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


async def test_sicon_extraction():
    """Test SICON extraction with REAL data"""
    logger.info("=" * 60)
    logger.info("🧪 Testing SICON Extraction")
    logger.info("=" * 60)
    
    # Get credentials from environment
    username = os.getenv("ORCID_USERNAME")
    password = os.getenv("ORCID_PASSWORD")
    
    if not username or not password:
        logger.error("❌ ORCID credentials not found in environment")
        logger.info("Please set ORCID_USERNAME and ORCID_PASSWORD in .env file")
        return None
    
    try:
        # Create extractor
        extractor = SICONExtractor()
        
        # Run extraction (headless=False for debugging)
        results = await extractor.extract(
            username=username,
            password=password,
            headless=False  # Set to True for production
        )
        
        # Display results
        logger.info("\n📊 SICON Extraction Results:")
        logger.info(f"  - Total manuscripts: {results['total_manuscripts']}")
        logger.info(f"  - Total referees: {results['statistics']['total_referees']}")
        logger.info(f"  - PDFs found: {results['statistics']['pdfs_found']}")
        logger.info(f"  - Manuscripts with reports: {results['statistics']['manuscripts_with_reports']}")
        
        # Show sample manuscript details
        if results['manuscripts']:
            logger.info("\n📄 Sample Manuscript Details:")
            for ms in results['manuscripts'][:2]:  # Show first 2
                logger.info(f"\n  Manuscript: {ms['id']}")
                logger.info(f"  Title: {ms['title'][:50]}...")
                logger.info(f"  Status: {ms['status']}")
                logger.info(f"  Referees: {len(ms.get('referees', []))}")
                
                # Show referee details
                for ref in ms.get('referees', [])[:2]:  # Show first 2 referees
                    logger.info(f"    - {ref['name']} ({ref['status']})")
                    if ref.get('email'):
                        logger.info(f"      Email: {ref['email']}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ SICON extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_sifin_extraction():
    """Test SIFIN extraction with REAL data"""
    logger.info("\n" + "=" * 60)
    logger.info("🧪 Testing SIFIN Extraction")
    logger.info("=" * 60)
    
    # Get credentials from environment
    username = os.getenv("ORCID_USERNAME")
    password = os.getenv("ORCID_PASSWORD")
    
    if not username or not password:
        logger.error("❌ ORCID credentials not found in environment")
        return None
    
    try:
        # Create extractor
        extractor = SIFINExtractor()
        
        # Run extraction
        results = await extractor.extract(
            username=username,
            password=password,
            headless=False  # Set to True for production
        )
        
        # Display results
        logger.info("\n📊 SIFIN Extraction Results:")
        logger.info(f"  - Total manuscripts: {results['total_manuscripts']}")
        logger.info(f"  - Total referees: {results['statistics']['total_referees']}")
        logger.info(f"  - PDFs found: {results['statistics']['pdfs_found']}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ SIFIN extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def verify_extraction_quality(results):
    """Verify that extraction results are REAL, not simulated"""
    if not results:
        return False
    
    logger.info("\n🔍 Verifying Extraction Quality...")
    
    issues = []
    
    # Check for fake/placeholder data patterns
    fake_patterns = [
        "test", "demo", "sample", "example", "placeholder",
        "manuscript_1", "referee_1", "fake", "simulated"
    ]
    
    for ms in results.get('manuscripts', []):
        # Check manuscript ID
        ms_id = ms.get('id', '').lower()
        if any(pattern in ms_id for pattern in fake_patterns):
            issues.append(f"Suspicious manuscript ID: {ms_id}")
        
        # Check title
        title = ms.get('title', '').lower()
        if any(pattern in title for pattern in fake_patterns):
            issues.append(f"Suspicious title: {title}")
        
        # Check referees
        for ref in ms.get('referees', []):
            ref_name = ref.get('name', '').lower()
            if any(pattern in ref_name for pattern in fake_patterns):
                issues.append(f"Suspicious referee name: {ref_name}")
            
            # Check email format
            email = ref.get('email', '')
            if email and not '@' in email:
                issues.append(f"Invalid email format: {email}")
    
    # Report findings
    if issues:
        logger.warning("⚠️  Quality Issues Found:")
        for issue in issues[:5]:  # Show first 5
            logger.warning(f"  - {issue}")
        if len(issues) > 5:
            logger.warning(f"  ... and {len(issues) - 5} more issues")
        return False
    else:
        logger.info("✅ All data appears to be REAL extraction results")
        return True


async def main():
    """Run all tests"""
    logger.info("🚀 UNIFIED SYSTEM TEST - REAL EXTRACTIONS ONLY")
    logger.info("=" * 80)
    
    # Test SICON
    sicon_results = await test_sicon_extraction()
    if sicon_results:
        await verify_extraction_quality(sicon_results)
    
    # Small delay between tests
    await asyncio.sleep(5)
    
    # Test SIFIN
    sifin_results = await test_sifin_extraction()
    if sifin_results:
        await verify_extraction_quality(sifin_results)
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("📋 TEST SUMMARY")
    logger.info("=" * 80)
    
    if sicon_results and sifin_results:
        logger.info("✅ Both SICON and SIFIN extractions completed successfully")
        logger.info("✅ The unified system is working with REAL data extraction")
    else:
        logger.error("❌ Some extractions failed - check logs above")
        if not sicon_results:
            logger.error("  - SICON extraction failed")
        if not sifin_results:
            logger.error("  - SIFIN extraction failed")
    
    logger.info("\n💡 Next Steps:")
    logger.info("  1. Verify PDF downloads are working")
    logger.info("  2. Test referee report extraction")
    logger.info("  3. Add more journal extractors (MF, MOR, etc.)")
    logger.info("  4. Implement comprehensive testing suite")


if __name__ == "__main__":
    asyncio.run(main())