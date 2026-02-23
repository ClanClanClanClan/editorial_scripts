#!/usr/bin/env python3
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.siam_base import SIAMExtractor


class SICONExtractor(SIAMExtractor):
    JOURNAL_CODE = "SICON"
    JOURNAL_NAME = "SIAM Journal on Control and Optimization"
    BASE_URL = "https://sicon.siam.org"
    MAIN_URL = "https://sicon.siam.org"
    MANUSCRIPT_PATTERN = r"M\d{6}"
    CLOUDFLARE_WAIT = 180


if __name__ == "__main__":
    headless = os.environ.get("EXTRACTOR_HEADLESS", "true").lower() == "true"
    extractor = SICONExtractor(headless=headless)
    try:
        results = extractor.run()
        if results:
            print(f"\n\u2705 SICON extraction complete: {len(results)} manuscripts")
        else:
            print("\n\u274c No manuscripts extracted")
    except KeyboardInterrupt:
        print("\n\u26a0\ufe0f Interrupted")
    except Exception as e:
        print(f"\n\u274c Error: {e}")
    finally:
        extractor.cleanup_driver()
