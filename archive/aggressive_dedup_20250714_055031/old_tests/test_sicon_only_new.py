#!/usr/bin/env python3
"""
Test only SICON extraction with updated AE navigation
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add paths for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / 'unified_system'))

from unified_system.extractors.siam.sicon import SICONExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_sicon_only():
    """Test only SICON extraction"""
    try:
        logger.info("🎯 Testing SICON extraction only")
        
        # Create output directory
        output_dir = Path("output/sicon")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create extractor
        extractor = SICONExtractor(output_dir=output_dir)
        
        # Run extraction with parameters (credentials ignored due to hardcoded ones)
        result = await extractor.extract(
            username="dummy",  # Ignored due to hardcoded credentials
            password="dummy",  # Ignored due to hardcoded credentials
            headless=False
        )
        
        logger.info(f"✅ SICON extraction completed: {result['total_manuscripts']} manuscripts")
        
        # Print results
        if result['manuscripts']:
            logger.info("📄 Found manuscripts:")
            for ms in result['manuscripts']:
                logger.info(f"  - {ms['id']}: {ms['title'][:60]}...")
        else:
            logger.warning("❌ No manuscripts found")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(test_sicon_only())