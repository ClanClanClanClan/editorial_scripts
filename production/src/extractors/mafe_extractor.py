#!/usr/bin/env python3
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.em_base import EMExtractor


class MAFEExtractor(EMExtractor):
    JOURNAL_CODE = "MAFE"
    JOURNAL_NAME = "Mathematics and Financial Economics"
    BASE_URL = "https://www.editorialmanager.com/mafe"
    ALT_URL = "https://www2.cloud.editorialmanager.com/mafe/default2.aspx"
    MANUSCRIPT_PATTERN = r"MAFE-D-\d{2}-\d{5}"
    CATEGORIES = ["With Referees", "Under Review"]
    MAX_MANUSCRIPTS = 25
    CREDENTIAL_PREFIX = "MAFE"
    EDITOR_ROLE = "editor"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--include-archived",
        action="store_true",
        help="Include archived manuscripts (Final Disposition). One-time historical extraction, not for regular runs.",
    )
    parser.add_argument("--all-folders", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    headless = os.environ.get("EXTRACTOR_HEADLESS", "true").lower() == "true"
    extractor = MAFEExtractor(headless=headless)
    if args.include_archived or args.all_folders:
        extractor.CATEGORIES = []
    try:
        results = extractor.run()
        if results:
            print(f"\n✅ MAFE extraction complete: {len(results)} manuscripts")
        else:
            print("\n⚠️ No manuscripts extracted")
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        extractor.cleanup_driver()
