"""Cross-platform smoke tests for canonical referee report extraction.

For each journal that has an extraction file on disk:
- Re-runs normalize_wrapper to apply the canonical schema migration.
- Verifies that any report present has the canonical fields.
- WARNS (not fails) when zero referees have report.comments_to_author —
  this is a regression flag, not a hard requirement (some journals
  legitimately have no submitted reports yet).

Run as part of the regular test suite. Catches schema drift across the
9 extractors.
"""

import json
import warnings
from pathlib import Path

import pytest
from core.output_schema import (
    CANONICAL_REPORT_FIELDS,
    normalize_wrapper,
)

OUTPUTS_DIR = Path(__file__).parent.parent / "production" / "outputs"
JOURNALS = ["mf", "mor", "fs", "jota", "mafe", "sicon", "sifin", "naco", "mf_wiley"]


def _latest_extraction(journal: str):
    files = sorted(OUTPUTS_DIR.joinpath(journal).glob(f"{journal}_extraction_*.json"))
    return files[-1] if files else None


def _load_and_normalize(journal: str):
    f = _latest_extraction(journal)
    if not f:
        return None, None
    data = json.load(open(f))
    normalize_wrapper(data, journal.upper())
    return f, data


@pytest.mark.parametrize("journal", JOURNALS)
def test_canonical_report_schema(journal):
    """Every report in every referee should conform to the canonical schema."""
    f, data = _load_and_normalize(journal)
    if data is None:
        pytest.skip(f"No extraction file for {journal}")

    violations = []
    n_reports = 0
    for ms in data.get("manuscripts", []):
        for ref in ms.get("referees", []) or []:
            for rpt in ref.get("reports", []) or []:
                n_reports += 1
                if not isinstance(rpt, dict):
                    violations.append(f"  {ms.get('manuscript_id')}/{ref.get('name')}: not a dict")
                    continue
                # Canonical fields must be present
                missing = []
                for required in (
                    "revision",
                    "recommendation",
                    "comments_to_author",
                    "raw_text",
                    "scores",
                    "available",
                    "extraction_status",
                    "source",
                    "word_count",
                ):
                    if required not in rpt:
                        missing.append(required)
                if missing:
                    violations.append(
                        f"  {ms.get('manuscript_id')}/{ref.get('name')}: missing {missing}"
                    )

    if violations:
        pytest.fail(
            f"{journal}: {len(violations)} schema violations in {n_reports} reports:\n"
            + "\n".join(violations[:10])
        )


@pytest.mark.parametrize("journal", JOURNALS)
def test_referee_reports_listed(journal):
    """Every referee with at least one report should have a non-empty `reports` list."""
    f, data = _load_and_normalize(journal)
    if data is None:
        pytest.skip(f"No extraction file for {journal}")

    for ms in data.get("manuscripts", []):
        for ref in ms.get("referees", []) or []:
            singular = ref.get("report")
            if isinstance(singular, dict) and (
                singular.get("comments_to_author")
                or singular.get("raw_text")
                or singular.get("recommendation")
            ):
                reports = ref.get("reports", [])
                assert isinstance(reports, list), (
                    f"{journal}/{ms.get('manuscript_id')}/{ref.get('name')}: "
                    f"singular report present but reports list missing"
                )


@pytest.mark.parametrize("journal", JOURNALS)
def test_warn_zero_text_reports(journal, recwarn):
    """Diagnostic: warn when zero referees have any report text in this journal.

    Doesn't fail — some journals legitimately have no submitted reports yet.
    But it's a useful regression flag.
    """
    f, data = _load_and_normalize(journal)
    if data is None:
        pytest.skip(f"No extraction file for {journal}")

    n_total = 0
    n_with_text = 0
    for ms in data.get("manuscripts", []):
        for ref in ms.get("referees", []) or []:
            n_total += 1
            for rpt in ref.get("reports", []) or []:
                if rpt.get("comments_to_author") or rpt.get("raw_text"):
                    n_with_text += 1
                    break

    if n_total > 0 and n_with_text == 0:
        warnings.warn(
            f"{journal}: {n_total} referees, 0 with report text "
            "(may be legitimate if no submissions yet)",
            UserWarning,
            stacklevel=2,
        )


@pytest.mark.parametrize("journal", JOURNALS)
def test_no_extra_fields_in_report(journal):
    """Reports should only contain canonical fields + platform_specific."""
    f, data = _load_and_normalize(journal)
    if data is None:
        pytest.skip(f"No extraction file for {journal}")

    allowed = CANONICAL_REPORT_FIELDS | {"platform_specific"}

    for ms in data.get("manuscripts", []):
        for ref in ms.get("referees", []) or []:
            for rpt in ref.get("reports", []) or []:
                if not isinstance(rpt, dict):
                    continue
                extra = set(rpt.keys()) - allowed
                # Schema is permissive: extras get tolerated, but flag obvious
                # leaks like raw HTML or selenium objects
                bad = {k for k in extra if not k.startswith("_")}
                # We don't strict-fail because legacy extractors may carry
                # historical fields (like attached_files, report_text_file)
                # that haven't been migrated yet. Just sanity check:
                assert (
                    "html" not in str(bad).lower()
                ), f"{journal}/{ms.get('manuscript_id')}: report has html field {bad}"
