#!/usr/bin/env python3
"""
Run the actual MF extractor
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from src.extractors.mf_extractor import ComprehensiveMFExtractor

if __name__ == "__main__":
    extractor = ComprehensiveMFExtractor()
    extractor.extract_all()
