#!/usr/bin/env python3
"""Minimal MOR test - no referee extraction"""
print("🔧 Test script starting...")

import sys
import os
from pathlib import Path

print("🔧 Imports done, setting up path...")

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "production" / "src"))

print("🔧 Importing extractor...")
from extractors.mor_extractor_enhanced import MORExtractor

print("🔧 Creating extractor instance...")
extractor = MORExtractor(use_cache=False, max_manuscripts_per_category=1)

print("✅ Starting test (1 manuscript per category)")

# Run extraction
result = extractor.run()

print(f"\n✅ Completed! Got {len(result.get('manuscripts', []))} manuscripts")

# Show details
for ms in result.get("manuscripts", []):
    print(f"\n📋 {ms['id']}")
    print(f"   Referees: {len(ms.get('referees', []))}")
    for ref in ms.get("referees", []):
        email_status = "✅" if ref.get("email") else "❌"
        print(f"      {email_status} {ref.get('name')} - {ref.get('email') or 'NO EMAIL'}")
