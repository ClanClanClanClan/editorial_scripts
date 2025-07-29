#!/usr/bin/env python3
"""Test the cleaned up MF extractor."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src.extractors.mf_extractor_clean import MFExtractor

if __name__ == "__main__":
    print("🧪 Testing clean MF extractor...")
    print("=" * 60)
    
    extractor = MFExtractor()
    extractor.run()