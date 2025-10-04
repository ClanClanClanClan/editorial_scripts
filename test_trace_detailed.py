#!/usr/bin/env python3
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "production" / "src"))

from extractors.mor_extractor_enhanced import MORExtractor

print("Creating extractor with verbose logging...")

# Monkey-patch to add logging
original_process = MORExtractor.process_manuscripts_by_category


def logged_process(self, category_url, category_name):
    print(f"\n📍 TRACE: Entering process_manuscripts_by_category for {category_name}")
    result = original_process(self, category_url, category_name)
    print(f"📍 TRACE: Exiting process_manuscripts_by_category for {category_name}")
    return result


MORExtractor.process_manuscripts_by_category = logged_process

extractor = MORExtractor(use_cache=False, max_manuscripts_per_category=1)

import signal


def timeout_handler(signum, frame):
    print(f"\n⏱️ TIMEOUT after 120s!")
    import traceback

    traceback.print_stack(frame)
    sys.exit(1)


signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(120)

try:
    result = extractor.run()
    signal.alarm(0)
    print(f"\n✅ Completed: {len(result.get('manuscripts', []))} manuscripts")
except Exception as e:
    signal.alarm(0)
    print(f"\n❌ Error: {e}")
    import traceback

    traceback.print_exc()
