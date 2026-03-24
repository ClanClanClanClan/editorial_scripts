"""Validate extractor outputs against the action_items data contract.

Reads the LATEST extraction output for each journal from production/outputs/
and validates structural conformance. Does not require running extractors.

Failures = required contract fields missing.
Warnings = optional fields missing (logged but not failing).
"""

import datetime
import warnings

import pytest
from reporting.action_items import (
    _effective_dates,
    _normalize_referee_status,
    _parse_date,
)
from reporting.cross_journal_report import JOURNALS, load_journal_data

AVAILABLE_JOURNALS: list[str] = []
JOURNAL_DATA: dict[str, dict] = {}


def _load_all():
    if JOURNAL_DATA:
        return
    for journal in JOURNALS:
        data = load_journal_data(journal)
        if data and data.get("manuscripts"):
            AVAILABLE_JOURNALS.append(journal)
            JOURNAL_DATA[journal] = data


_load_all()


def _journal_ids():
    return AVAILABLE_JOURNALS


def _all_manuscripts(journal):
    return JOURNAL_DATA[journal].get("manuscripts", [])


def _all_referees(journal):
    for ms in _all_manuscripts(journal):
        for ref in ms.get("referees", []):
            yield ms, ref


class TestOutputWrapper:
    @pytest.mark.parametrize("journal", _journal_ids())
    def test_has_extraction_timestamp(self, journal):
        assert JOURNAL_DATA[journal].get(
            "extraction_timestamp"
        ), f"{journal}: missing extraction_timestamp"

    @pytest.mark.parametrize("journal", _journal_ids())
    def test_has_journal_code(self, journal):
        assert JOURNAL_DATA[journal].get("journal"), f"{journal}: missing journal field"

    @pytest.mark.parametrize("journal", _journal_ids())
    def test_manuscripts_is_list(self, journal):
        mss = JOURNAL_DATA[journal].get("manuscripts")
        assert isinstance(mss, list), f"{journal}: manuscripts is not a list"


class TestManuscriptRequired:
    @pytest.mark.parametrize("journal", _journal_ids())
    def test_every_manuscript_has_id(self, journal):
        for ms in _all_manuscripts(journal):
            assert ms.get("manuscript_id"), f"{journal}: manuscript missing manuscript_id"

    @pytest.mark.parametrize("journal", _journal_ids())
    def test_every_manuscript_has_title(self, journal):
        for ms in _all_manuscripts(journal):
            assert ms.get("title"), f"{journal}/{ms.get('manuscript_id', '?')}: missing title"

    @pytest.mark.parametrize("journal", _journal_ids())
    def test_every_manuscript_has_status_or_category(self, journal):
        for ms in _all_manuscripts(journal):
            assert ms.get("status") or ms.get("category"), (
                f"{journal}/{ms.get('manuscript_id', '?')}: " "missing both status and category"
            )

    @pytest.mark.parametrize("journal", _journal_ids())
    def test_referees_is_list(self, journal):
        for ms in _all_manuscripts(journal):
            refs = ms.get("referees")
            assert isinstance(
                refs, list
            ), f"{journal}/{ms.get('manuscript_id', '?')}: referees is not a list"


class TestRefereeRequired:
    @pytest.mark.parametrize("journal", _journal_ids())
    def test_every_referee_has_name(self, journal):
        for ms, ref in _all_referees(journal):
            name = ref.get("name")
            assert (
                name and name.strip()
            ), f"{journal}/{ms.get('manuscript_id', '?')}: referee missing name"

    @pytest.mark.parametrize("journal", _journal_ids())
    def test_every_referee_has_status_source(self, journal):
        for ms, ref in _all_referees(journal):
            ps = ref.get("platform_specific") or {}
            sd = ref.get("status_details") or {}
            dates = ref.get("dates") or {}
            has_any = (
                ref.get("status")
                or ps.get("status")
                or sd.get("agreed_to_review")
                or sd.get("review_received")
                or sd.get("declined")
                or sd.get("no_response")
                or dates.get("returned")
                or dates.get("agreed")
                or dates.get("invited")
                or ref.get("recommendation")
                or ps.get("reports")
            )
            assert has_any, (
                f"{journal}/{ms.get('manuscript_id', '?')}/{ref.get('name')}: " "no status source"
            )

    @pytest.mark.parametrize("journal", _journal_ids())
    def test_normalize_status_does_not_crash(self, journal):
        for ms, ref in _all_referees(journal):
            norm = _normalize_referee_status(ref, journal)
            assert norm in (
                "agreed",
                "completed",
                "pending",
                "declined",
                "terminated",
                "unknown",
            ), (
                f"{journal}/{ms.get('manuscript_id', '?')}/{ref.get('name')}: "
                f"unexpected status: {norm!r}"
            )

    @pytest.mark.parametrize("journal", _journal_ids())
    def test_dates_dict_type(self, journal):
        for ms, ref in _all_referees(journal):
            dates = ref.get("dates")
            assert dates is None or isinstance(dates, dict), (
                f"{journal}/{ms.get('manuscript_id', '?')}/{ref.get('name')}: "
                f"dates is {type(dates)}, expected dict or None"
            )


class TestDateParsing:
    @pytest.mark.parametrize("journal", _journal_ids())
    def test_all_date_strings_parseable(self, journal):
        unparseable = []
        for ms, ref in _all_referees(journal):
            eff = _effective_dates(ref)
            for key in ("invited", "agreed", "due", "returned"):
                val = eff.get(key)
                if val and _parse_date(val) is None:
                    unparseable.append(
                        f"{ms.get('manuscript_id', '?')}/{ref.get('name', '?')}" f".{key}={val!r}"
                    )
        assert not unparseable, f"{journal}: unparseable dates:\n" + "\n".join(unparseable)

    @pytest.mark.parametrize("journal", _journal_ids())
    def test_dates_not_in_far_future(self, journal):
        cutoff = datetime.date.today() + datetime.timedelta(days=730)
        bad = []
        for ms, ref in _all_referees(journal):
            eff = _effective_dates(ref)
            for key in ("invited", "agreed", "due", "returned"):
                val = eff.get(key)
                if val:
                    d = _parse_date(val)
                    if d and d > cutoff:
                        bad.append(
                            f"{ms.get('manuscript_id', '?')}/{ref.get('name', '?')}" f".{key}={val}"
                        )
        assert not bad, f"{journal}: dates far in future:\n" + "\n".join(bad)


class TestActiveDateCoverage:
    @pytest.mark.parametrize("journal", _journal_ids())
    def test_agreed_referees_have_date_source(self, journal):
        missing = []
        for ms, ref in _all_referees(journal):
            norm = _normalize_referee_status(ref, journal)
            if norm != "agreed":
                continue
            eff = _effective_dates(ref)
            has_any_date = any(eff.get(k) for k in ("invited", "agreed", "due"))
            if not has_any_date:
                missing.append(f"{ms.get('manuscript_id', '?')}/{ref.get('name', '?')}")
        assert not missing, f"{journal}: agreed referees with no date source:\n" + "\n".join(
            missing
        )


class TestStatistics:
    @pytest.mark.parametrize("journal", _journal_ids())
    def test_reminders_nonnegative(self, journal):
        bad = []
        for ms, ref in _all_referees(journal):
            stats = ref.get("statistics") or {}
            r = stats.get("reminders_received")
            if r is not None and (not isinstance(r, int) or r < 0):
                bad.append(
                    f"{ms.get('manuscript_id', '?')}/{ref.get('name', '?')}: "
                    f"reminders_received={r!r}"
                )
        assert not bad, f"{journal}: invalid reminder counts:\n" + "\n".join(bad)


class TestNoDuplicates:
    @pytest.mark.parametrize("journal", _journal_ids())
    def test_no_duplicate_referee_names(self, journal):
        dupes = []
        for ms in _all_manuscripts(journal):
            names = [(r.get("name") or "").strip().lower() for r in ms.get("referees", [])]
            seen = set()
            for n in names:
                if n and n in seen:
                    dupes.append(f"{ms.get('manuscript_id', '?')}: duplicate '{n}'")
                seen.add(n)
        assert not dupes, f"{journal}: duplicate referees:\n" + "\n".join(dupes)


class TestFSSpecific:
    def _fs_manuscripts(self):
        if "fs" not in JOURNAL_DATA:
            pytest.skip("No FS output available")
        return _all_manuscripts("fs")

    def test_fs_has_revision_round(self):
        for ms in self._fs_manuscripts():
            ps = ms.get("platform_specific") or {}
            assert "revision_round" in ps, (
                f"FS/{ms.get('manuscript_id', '?')}: " "missing platform_specific.revision_round"
            )

    def test_fs_has_revision_history(self):
        for ms in self._fs_manuscripts():
            ps = ms.get("platform_specific") or {}
            assert "revision_history" in ps, (
                f"FS/{ms.get('manuscript_id', '?')}: " "missing platform_specific.revision_history"
            )
            assert isinstance(ps["revision_history"], list)

    def test_fs_has_timeline_metrics(self):
        for ms in self._fs_manuscripts():
            ps = ms.get("platform_specific") or {}
            assert "timeline_metrics" in ps, (
                f"FS/{ms.get('manuscript_id', '?')}: " "missing platform_specific.timeline_metrics"
            )

    def test_fs_has_referee_reports(self):
        for ms in self._fs_manuscripts():
            ps = ms.get("platform_specific") or {}
            assert "referee_reports" in ps, (
                f"FS/{ms.get('manuscript_id', '?')}: " "missing platform_specific.referee_reports"
            )
            assert isinstance(ps["referee_reports"], list)

    def test_fs_referees_have_status_details(self):
        if "fs" not in JOURNAL_DATA:
            pytest.skip("No FS output available")
        for ms, ref in _all_referees("fs"):
            assert ref.get("status_details") is not None, (
                f"FS/{ms.get('manuscript_id', '?')}/{ref.get('name', '?')}: "
                "missing status_details"
            )


class TestOptionalFieldWarnings:
    @pytest.mark.parametrize("journal", _journal_ids())
    def test_warn_null_web_profiles(self, journal):
        null_count = 0
        total = 0
        for _, ref in _all_referees(journal):
            total += 1
            if ref.get("web_profile") is None:
                null_count += 1
        if null_count > 0:
            warnings.warn(
                f"{journal}: {null_count}/{total} referees have "
                f"web_profile=None (enrichment gap)",
                UserWarning,
                stacklevel=1,
            )

    @pytest.mark.parametrize("journal", _journal_ids())
    def test_warn_missing_emails(self, journal):
        missing = 0
        total = 0
        for _, ref in _all_referees(journal):
            total += 1
            if not ref.get("email"):
                missing += 1
        if missing > 0:
            warnings.warn(
                f"{journal}: {missing}/{total} referees have no email",
                UserWarning,
                stacklevel=1,
            )

    @pytest.mark.parametrize("journal", _journal_ids())
    def test_warn_missing_returned_for_completed(self, journal):
        missing = []
        for ms, ref in _all_referees(journal):
            norm = _normalize_referee_status(ref, journal)
            if norm == "completed":
                eff = _effective_dates(ref)
                if not eff.get("returned"):
                    missing.append(f"{ms.get('manuscript_id', '?')}/{ref.get('name', '?')}")
        if missing:
            warnings.warn(
                f"{journal}: {len(missing)} completed referees have no "
                f"returned date: " + ", ".join(missing[:5]),
                UserWarning,
                stacklevel=1,
            )


# ── Untestable without live extraction ───────────────────────────────
#
# The following aspects CANNOT be validated from output JSON alone and
# require live extractor runs. Documented here for manual verification
# or future integration tests.
#
# @live_only: Email parsing accuracy (FS)
#   FS extractor parses Gmail threads to identify referee names,
#   institutions, and timeline events. Accuracy depends on email
#   formatting which varies by sender.
#
# @live_only: Selenium navigation reliability
#   All browser-based extractors (MF, MOR, JOTA, MAFE, SICON, SIFIN,
#   NACO) depend on DOM structure of their respective platforms.
#   Breaking changes are only detectable by running extractors.
#
# @live_only: Web enrichment API availability
#   OpenAlex, Semantic Scholar, CrossRef, ORCID APIs may be down or
#   rate-limited. web_profile=None is expected when APIs fail.
#
# @live_only: Cloudflare challenge resolution
#   ScholarOne (MF, MOR) and SIAM (SICON, SIFIN) sites use Cloudflare.
#   Off-screen headful mode resolves challenges, but Cloudflare may
#   update its detection at any time.
#
# @live_only: Document download completeness
#   JOTA, MAFE, MF, MOR, SICON, SIFIN download manuscript PDFs and
#   supplementary files. Download success depends on session state,
#   file availability, and redirect handling.
#
# @live_only: NACO credential/site accessibility
#   NACO (EditFlow/MSP) returns 0 manuscripts when there are no active
#   papers or credentials are invalid. Requires live login to verify.
