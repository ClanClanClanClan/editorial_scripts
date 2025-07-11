#!/usr/bin/env python3
"""
Test script to run just MOR extraction to verify status detection
"""

import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from final_working_referee_extractor import FinalWorkingRefereeExtractor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TEST_MOR_ONLY")

def test_mor_extraction():
    """Test MOR extraction specifically"""
    logger.info("🔍 TESTING MOR EXTRACTION WITH IMPROVED STATUS DETECTION")
    
    # Extract MOR only
    mor_extractor = FinalWorkingRefereeExtractor("MOR")
    mor_extractor.extract_referee_data(headless=True)
    
    logger.info("✅ MOR extraction completed")

if __name__ == "__main__":
    test_mor_extraction()