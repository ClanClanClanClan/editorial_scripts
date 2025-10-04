#!/usr/bin/env python3
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "production" / "src"))

from extractors.mor_extractor_enhanced import MORExtractor

print("Creating extractor...")
extractor = MORExtractor(use_cache=False, max_manuscripts_per_category=1)

print("Calling run()...")
import signal


def timeout_handler(signum, frame):
    print(f"\n⏱️ TIMEOUT! Stuck in run() method")
    import traceback

    traceback.print_stack(frame)
    sys.exit(1)


signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(45)  # 45 second timeout

try:
    result = extractor.run()
    signal.alarm(0)  # Cancel alarm
    print(f"✅ run() completed: {len(result.get('manuscripts', []))} manuscripts")
except Exception as e:
    signal.alarm(0)
    print(f"❌ run() failed: {e}")
    import traceback

    traceback.print_exc()
