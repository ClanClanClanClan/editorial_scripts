#!/usr/bin/env python3
"""
Test script to run just MF extraction to verify status detection
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
logger = logging.getLogger("TEST_MF_ONLY")

def test_mf_extraction():
    """Test MF extraction specifically"""
    logger.info("🔍 TESTING MF EXTRACTION WITH ROBUST STATUS DETECTION")
    
    # Extract MF only
    mf_extractor = FinalWorkingRefereeExtractor("MF")
    mf_extractor.extract_referee_data(headless=True)
    
    logger.info("✅ MF extraction completed")

if __name__ == "__main__":
    test_mf_extraction()