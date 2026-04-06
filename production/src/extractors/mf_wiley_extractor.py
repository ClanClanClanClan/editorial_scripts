#!/usr/bin/env python3
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.wiley_base import WileyBaseExtractor


class MFWileyExtractor(WileyBaseExtractor):
    JOURNAL_CODE = "MF_WILEY"
    JOURNAL_NAME = "Mathematical Finance"
    MANUSCRIPT_PATTERN = r"\d{7}"


if __name__ == "__main__":
    headless = os.environ.get("EXTRACTOR_HEADLESS", "false").lower() == "true"
    extractor = MFWileyExtractor(headless=headless)
    try:
        results = extractor.run()
        if results:
            print(f"\n\u2705 MF Wiley extraction complete: {len(results)} manuscripts")
        else:
            print("\n\u274c No manuscripts extracted")
    except KeyboardInterrupt:
        print("\n\u26a0\ufe0f Interrupted")
    except Exception as e:
        print(f"\n\u274c Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        extractor.cleanup_driver()
