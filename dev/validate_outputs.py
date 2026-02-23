#!/usr/bin/env python3
"""
Validate output JSON files against canonical schema v1.0.0.
Usage: python3 dev/validate_outputs.py [--normalize]

--normalize: Apply normalize_wrapper to each file in-place before validating.
             Without this flag, only validates existing files.
"""

import json
import re
import sys
from pathlib import Path

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

REQUIRED_WRAPPER_FIELDS = [
    "schema_version",
    "extraction_timestamp",
    "journal",
    "journal_name",
    "platform",
    "manuscripts",
    "summary",
    "errors",
]

LEGACY_REFEREE_DATE_FIELDS = [
    "contact_date",
    "acceptance_date",
    "invitation_date",
    "agreed_date",
    "invited_date",
    "received_date",
    "response_date",
    "report_date",
    "contacted_date",
    "review_returned_date",
    "due_date",
]


def validate_file(path: Path) -> list:
    errors = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"PARSE ERROR: {e}"]

    for field in REQUIRED_WRAPPER_FIELDS:
        if field not in data:
            errors.append(f"WRAPPER: missing '{field}'")

    sv = data.get("schema_version")
    if sv and sv != "1.0.0":
        errors.append(f"WRAPPER: unexpected schema_version '{sv}'")

    manuscripts = data.get("manuscripts", [])
    for i, ms in enumerate(manuscripts):
        pfx = f"manuscripts[{i}]"

        if "manuscript_id" not in ms:
            errors.append(f"{pfx}: missing 'manuscript_id'")

        if "title" not in ms:
            errors.append(f"{pfx}: missing top-level 'title'")

        sd = ms.get("submission_date")
        if sd is not None and not ISO_DATE_RE.match(str(sd)):
            errors.append(f"{pfx}: submission_date not ISO 8601: '{sd}'")

        kw = ms.get("keywords")
        if kw is not None and not isinstance(kw, list):
            errors.append(f"{pfx}: keywords is {type(kw).__name__}, not list")

        for j, author in enumerate(ms.get("authors", [])):
            apfx = f"{pfx}.authors[{j}]"
            ic = author.get("is_corresponding")
            if ic is not None and not isinstance(ic, bool):
                errors.append(f"{apfx}: is_corresponding is {type(ic).__name__}, not bool")

        for j, ref in enumerate(ms.get("referees", [])):
            rpfx = f"{pfx}.referees[{j}]"
            dates = ref.get("dates")
            if dates is None:
                errors.append(f"{rpfx}: missing 'dates' sub-dict")
            elif isinstance(dates, dict):
                for key in ("invited", "agreed", "due", "returned"):
                    if key not in dates:
                        errors.append(f"{rpfx}.dates: missing '{key}'")
                    elif dates[key] is not None and not ISO_DATE_RE.match(str(dates[key])):
                        errors.append(f"{rpfx}.dates.{key} not ISO 8601: '{dates[key]}'")

            for legacy in LEGACY_REFEREE_DATE_FIELDS:
                if legacy in ref and "platform_specific" not in ref:
                    errors.append(f"{rpfx}: legacy field '{legacy}' at top level")

    return errors


def normalize_file(path: Path, journal_code: str) -> None:
    sys.path.insert(0, str(Path(__file__).parent.parent / "production" / "src"))
    from core.output_schema import normalize_wrapper

    data = json.loads(path.read_text(encoding="utf-8"))
    normalize_wrapper(data, journal_code)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f"  📝 Normalized: {path.name}")


def main():
    do_normalize = "--normalize" in sys.argv

    project_root = Path(__file__).parent.parent
    output_root = project_root / "production" / "outputs"

    journal_dirs = {
        "mf": "MF",
        "mor": "MOR",
        "fs": "FS",
        "jota": "JOTA",
        "mafe": "MAFE",
        "sicon": "SICON",
        "sifin": "SIFIN",
        "naco": "NACO",
    }

    all_errors = {}
    total_files = 0
    total_valid = 0

    for dir_name, journal_code in sorted(journal_dirs.items()):
        journal_dir = output_root / dir_name
        if not journal_dir.exists():
            continue

        json_files = sorted(journal_dir.glob("*.json"))
        json_files = [
            f for f in json_files if "debug" not in f.name.lower() and "BASELINE" not in f.name
        ]

        if not json_files:
            continue

        print(f"\n📂 {journal_code} ({len(json_files)} files)")

        for json_file in json_files:
            total_files += 1

            if do_normalize:
                try:
                    normalize_file(json_file, journal_code)
                except Exception as e:
                    print(f"  ❌ Normalize failed: {json_file.name}: {e}")

            errors = validate_file(json_file)
            if errors:
                all_errors[str(json_file)] = errors
                print(f"  ❌ {json_file.name}: {len(errors)} error(s)")
                for e in errors[:3]:
                    print(f"     • {e}")
                if len(errors) > 3:
                    print(f"     ... and {len(errors) - 3} more")
            else:
                total_valid += 1
                print(f"  ✅ {json_file.name}")

    print(f"\n{'=' * 60}")
    if all_errors:
        print(
            f"❌ VALIDATION: {total_valid}/{total_files} files valid, "
            f"{len(all_errors)} with errors"
        )
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED: {total_files}/{total_files} files valid")
        sys.exit(0)


if __name__ == "__main__":
    main()
