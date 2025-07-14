#!/usr/bin/env python3
"""
Test PDF Download Functionality - Verify REAL PDF downloads work
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
from unified_system import SICONExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


async def test_pdf_downloads():
    """Test PDF download functionality with SICON"""
    logger.info("=" * 60)
    logger.info("🧪 Testing PDF Download Functionality")
    logger.info("=" * 60)
    
    # Get credentials from environment
    username = os.getenv("ORCID_USERNAME")
    password = os.getenv("ORCID_PASSWORD")
    
    if not username or not password:
        logger.error("❌ ORCID credentials not found in environment")
        return None
    
    try:
        # Create extractor with custom output directory
        output_dir = Path("test_pdf_output")
        extractor = SICONExtractor(output_dir=output_dir)
        
        logger.info(f"📁 PDFs will be saved to: {output_dir.absolute()}")
        
        # Run extraction
        results = await extractor.extract(
            username=username,
            password=password,
            headless=False  # Watch it work
        )
        
        # Check results
        if not results:
            logger.error("❌ Extraction failed")
            return None
        
        logger.info(f"\n📊 Extraction Results:")
        logger.info(f"  - Total manuscripts: {results['total_manuscripts']}")
        logger.info(f"  - PDFs found: {results['statistics']['pdfs_found']}")
        logger.info(f"  - PDFs downloaded: {results['statistics']['pdfs_downloaded']}")
        
        # Verify downloaded PDFs
        logger.info("\n🔍 Verifying Downloaded PDFs:")
        
        pdf_dir = output_dir / "pdfs"
        if pdf_dir.exists():
            pdf_files = list(pdf_dir.glob("*.pdf"))
            logger.info(f"  - Found {len(pdf_files)} PDF files in {pdf_dir}")
            
            for pdf_file in pdf_files[:5]:  # Show first 5
                size_kb = pdf_file.stat().st_size / 1024
                logger.info(f"    ✅ {pdf_file.name} ({size_kb:.1f} KB)")
                
                # Verify it's a real PDF
                with open(pdf_file, 'rb') as f:
                    header = f.read(4)
                    if header == b'%PDF':
                        logger.info(f"       Valid PDF header confirmed")
                    else:
                        logger.error(f"       ❌ Invalid PDF header: {header}")
        else:
            logger.warning(f"  ⚠️ PDF directory not found: {pdf_dir}")
        
        # Show manuscript details with PDF info
        logger.info("\n📄 Manuscript PDF Details:")
        for ms in results['manuscripts'][:3]:  # Show first 3
            logger.info(f"\n  Manuscript: {ms['id']}")
            logger.info(f"  Title: {ms['title'][:50]}...")
            
            if ms.get('pdf_urls'):
                logger.info(f"  PDF URLs found:")
                for pdf_type, url in ms['pdf_urls'].items():
                    logger.info(f"    - {pdf_type}: {url[:80]}...")
            
            if ms.get('pdf_paths'):
                logger.info(f"  PDFs downloaded:")
                for pdf_type, path in ms['pdf_paths'].items():
                    logger.info(f"    - {pdf_type}: {Path(path).name}")
            else:
                logger.warning(f"  ⚠️ No PDFs downloaded for this manuscript")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def cleanup_test_files():
    """Clean up test output directory"""
    output_dir = Path("test_pdf_output")
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
        logger.info(f"🧹 Cleaned up {output_dir}")


async def main():
    """Run PDF download test"""
    logger.info("🚀 PDF DOWNLOAD TEST - REAL DOWNLOADS ONLY")
    logger.info("=" * 80)
    
    # Run test
    results = await test_pdf_downloads()
    
    if results and results['statistics']['pdfs_downloaded'] > 0:
        logger.info("\n✅ PDF DOWNLOAD TEST PASSED")
        logger.info(f"✅ Successfully downloaded {results['statistics']['pdfs_downloaded']} PDFs")
    else:
        logger.error("\n❌ PDF DOWNLOAD TEST FAILED")
        logger.error("❌ No PDFs were downloaded")
    
    # Ask if we should clean up
    if results:
        response = input("\n🗑️ Clean up downloaded PDFs? (y/n): ")
        if response.lower() == 'y':
            await cleanup_test_files()


if __name__ == "__main__":
    asyncio.run(main())