#!/usr/bin/env python3
"""Minimal MOR test with aggressive timeouts."""
import sys
import signal
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "production" / "src"))

from extractors.mor_extractor_enhanced import MORExtractor


# Global timeout for entire test
def global_timeout(signum, frame):
    print("\n⏱️ GLOBAL TIMEOUT (90s)!")
    import traceback

    traceback.print_stack(frame)
    sys.exit(1)


signal.signal(signal.SIGALRM, global_timeout)
signal.alarm(90)

try:
    print("Creating extractor...")
    extractor = MORExtractor(use_cache=False, max_manuscripts_per_category=1)

    print("Running extraction...")
    result = extractor.run()

    signal.alarm(0)
    print(f"\n✅ Success: {len(result.get('manuscripts', []))} manuscripts")
    print(
        f"   Emails: {result['summary']['referee_emails_extracted']}/{result['summary']['total_referees']}"
    )
except Exception as e:
    signal.alarm(0)
    print(f"\n❌ Error: {e}")
    import traceback

    traceback.print_exc()
