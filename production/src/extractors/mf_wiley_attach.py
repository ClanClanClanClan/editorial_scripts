#!/usr/bin/env python3
"""Wiley ScienceConnect — ATTACH MODE extractor.

Extracts from an already-open Chrome tab on review.wiley.com by driving
AppleScript JavaScript execution. Avoids all Cloudflare Turnstile,
ORCID login, and Chrome 146 headful crash issues.

Requirements:
- Chrome View > Developer > Allow JavaScript from Apple Events = ON
- A review.wiley.com/ tab must be open and logged in

Usage:
    python3 production/src/extractors/mf_wiley_attach.py
"""

import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.output_schema import normalize_wrapper

JOURNAL_CODE = "MF_WILEY"
JOURNAL_NAME = "Mathematical Finance"

BASE_DIR = Path(__file__).parent.parent.parent
OUTPUT_DIR = BASE_DIR / "outputs" / JOURNAL_CODE.lower()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _osa(script: str) -> str:
    r = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    return r.stdout.strip()


def js(code: str) -> str:
    """Execute JS in the active tab of Chrome's front window."""
    escaped = code.replace("\\", "\\\\").replace('"', '\\"')
    script = f"""tell application "Google Chrome"
    tell active tab of front window
        return execute javascript "{escaped}"
    end tell
end tell"""
    return _osa(script)


def switch_to_wiley_tab() -> bool:
    """Find and focus the review.wiley.com tab."""
    script = """tell application "Google Chrome"
    repeat with w in every window
        set idx to 0
        repeat with t in every tab of w
            set idx to idx + 1
            if URL of t contains "review.wiley.com" then
                set active tab index of w to idx
                set index of w to 1
                return "OK"
            end if
        end repeat
    end repeat
    return "NOT_FOUND"
end tell"""
    return _osa(script) == "OK"


def navigate(url: str):
    """Navigate the active tab to a URL."""
    _osa(
        f"""tell application "Google Chrome"
    set URL of active tab of front window to "{url}"
end tell"""
    )


def wait_for(test_js: str, timeout: int = 30) -> bool:
    """Poll a JS condition until true or timeout."""
    for _ in range(timeout):
        result = js(test_js)
        if result == "true" or result == "1":
            return True
        time.sleep(1)
    return False


def parse_wiley_date(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def map_status(wiley_status: str) -> str:
    s = (wiley_status or "").lower()
    if "accepted" in s:
        return "Agreed"
    if "pending" in s:
        return "Invited"
    if "declined" in s:
        return "Declined"
    if "expired" in s:
        return "No Response"
    if "revoked" in s:
        return "Terminated"
    if "submitted" in s or "complete" in s:
        return "Report Submitted"
    return wiley_status


_CARD_DATE_RE = re.compile(
    r"(Invited|Accepted|Declined|Expired|Submitted|Due)\s*:\s*"
    r"([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})",
    re.IGNORECASE,
)


def _parse_card_dates(card_text: str) -> dict:
    """Extract all Invited/Accepted/Declined/Expired/Submitted/Due dates from card text.

    Returns the FIRST match per label (robust to duplicate divs)."""
    dates: dict[str, str] = {}
    if not card_text:
        return dates
    for m in _CARD_DATE_RE.finditer(card_text):
        label = m.group(1).lower()
        date_val = parse_wiley_date(m.group(2))
        if date_val and label not in dates:
            dates[label] = date_val
    return dates


def extract_source_from_tid(tid: str) -> str:
    for prefix in ("reviewerInvitedManually-", "reviewerSuggestions-", "reviewerSearch-"):
        if prefix in tid:
            return prefix.rstrip("-").replace("reviewer", "").lower()
    return "unknown"


def collect_manuscript_ids() -> list[dict]:
    # Click "All" filter
    js("document.querySelector('[data-test-id=\\\"bin-radio-all\\\"]').click()")
    time.sleep(3)
    # Get card IDs (skip show-less-toggle)
    raw = js(
        """
        var cards = document.querySelectorAll('[data-test-id^=\\"manuscript-card\\"]');
        var ids = [];
        cards.forEach(function(c){
            var tid = c.getAttribute('data-test-id');
            if (!tid) return;
            var suffix = tid.replace('manuscript-card','');
            if (!suffix) return;
            if (suffix.indexOf('-') >= 0) return;
            ids.push(suffix);
        });
        ids.join(',');
    """
    )
    if not raw:
        return []
    ms_ids = [mid.strip() for mid in raw.split(",") if mid.strip()]
    manuscripts = []
    for ms_id in ms_ids:
        info = js(
            f"""
            var card = document.querySelector('[data-test-id=\\"manuscript-card{ms_id}\\"]');
            if (!card) {{ 'MISSING'; }}
            else {{
                var title = (card.querySelector('[data-test-id=\\"manuscript-title\\"]') || {{}}).textContent || '';
                var status = (card.querySelector('[data-test-id=\\"manuscript-status\\"]') || {{}}).textContent || '';
                var link = card.querySelector('[data-test-id=\\"manuscript-title\\"]').closest('a');
                title + '|||' + status + '|||' + (link ? link.href : '');
            }}
        """
        )
        parts = info.split("|||")
        if len(parts) == 3:
            manuscripts.append(
                {
                    "manuscript_id": ms_id,
                    "title": parts[0].strip(),
                    "status": parts[1].strip(),
                    "href": parts[2].strip(),
                }
            )
    return manuscripts


def extract_metadata() -> dict:
    raw = js(
        """
        function t(s){var e=document.querySelector(s);return e?e.textContent.trim():'';}
        JSON.stringify({
            msId: t('[data-test-id=\\"manuscript-id\\"]').replace(/^ID\\\\s*/,'').trim(),
            title: t('[data-test-id=\\"manuscript-title\\"]'),
            status: t('[data-test-id=\\"manuscript-status\\"]'),
            version: t('[data-test-id=\\"manuscript-current-version\\"]'),
            articleType: t('[data-test-id=\\"article-type\\"]'),
            journal: t('[data-test-id=\\"journal-title\\"]'),
            keywords: t('[data-test-id=\\"manuscript-keywords\\"]')
        });
    """
    )
    try:
        d = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    kw = d.get("keywords", "")
    return {
        "manuscript_id": d.get("msId", ""),
        "title": d.get("title", ""),
        "status": d.get("status", ""),
        "article_type": d.get("articleType", ""),
        "keywords": [k.strip() for k in kw.split(";") if k.strip()] if kw else [],
        "metadata": {
            "journal": d.get("journal", ""),
            "version": d.get("version", ""),
        },
    }


def extract_authors() -> list[dict]:
    raw = js(
        """
        var els = document.querySelectorAll('[data-test-id^=\\"author-name-\\"]');
        var out = [];
        els.forEach(function(el){
            var tid = el.getAttribute('data-test-id') || '';
            var email = tid.replace('author-name-','');
            var name = el.textContent.trim();
            if (name && email) out.push(email + '|' + name);
        });
        out.join(';;;');
    """
    )
    if not raw:
        return []
    authors = []
    for entry in raw.split(";;;"):
        if "|" in entry:
            email, name = entry.split("|", 1)
            authors.append({"name": name.strip(), "email": email.strip()})
    return authors


def extract_editors() -> list[dict]:
    raw = js(
        """
        var els = document.querySelectorAll('[data-test-id^=\\"editor-label-\\"]');
        var out = [];
        els.forEach(function(el){
            var tid = el.getAttribute('data-test-id') || '';
            var email = tid.replace('editor-label-','');
            var text = el.textContent.trim();
            out.push(email + '|' + text);
        });
        out.join(';;;');
    """
    )
    if not raw:
        return []
    editors = []
    for entry in raw.split(";;;"):
        if "|" not in entry:
            continue
        email, text = entry.split("|", 1)
        role = ""
        name = text
        if ":" in text:
            role, name = text.split(":", 1)
            role, name = role.strip(), name.strip()
        editors.append({"name": name, "email": email, "role": role})
    return editors


def extract_submitted_report_for_referee(card_index: int, referee_name: str) -> dict | None:
    """Defensive extraction of a submitted-report panel under a reviewer card.

    No reviewer on the live MF_WILEY platform has submitted a report yet, so
    this is forward-looking scaffolding. When the first real report arrives,
    the operator should:

      1. Navigate to the manuscript detail page in Chrome (logged in).
      2. Inspect the DOM under the reviewer card that has a submitted report.
      3. Confirm the panel data-test-id (likely "Submitted-reports" at the
         manuscript level OR per-reviewer "submitted-report-{uuid}").
      4. Confirm the recommendation lives inside as data-test-id=
         "reviewer-recommendation" or similar; comments-to-author as a
         readonly textarea or div under a "Comments to Author:" heading.
      5. Confirm any attached PDF is downloadable via data-test-id=
         "report-attachment-link" -> href.
      6. Update the JS selector pass below to match the discovered structure.

    Until then this function returns None whenever the card does not contain
    any descendant matching `[data-test-id*="report"]` or
    `[data-test-id*="Submitted"]` with non-trivial text content.

    Returns: a canonical report dict (per output_schema.CANONICAL_REPORT_FIELDS)
    when content is found, else None.
    """
    raw = js(
        f"""
        (function(){{
            var c = window._revCards[{card_index}];
            if (!c) return 'NO_CARD';
            // Search for any report-related panel inside the card
            var panels = c.querySelectorAll('[data-test-id*="report"], [data-test-id*="Submitted"], [data-test-id*="submitted"]');
            if (!panels || panels.length === 0) return 'NO_PANEL';
            var combinedText = '';
            for (var i = 0; i < panels.length; i++) {{
                var t = (panels[i].textContent || '').trim();
                // Skip stub/empty panels (just a button or label)
                if (t.length < 30) continue;
                combinedText += t + '\\n';
            }}
            if (!combinedText.trim()) return 'NO_TEXT';
            return combinedText.substring(0, 20000);
        }})()
    """
    )
    if not raw or raw in ("NO_CARD", "NO_PANEL", "NO_TEXT"):
        return None

    text = raw.strip()
    if len(text) < 30:
        return None

    # Best-effort heuristic parsing — labels match what the operator will
    # discover in the real DOM. Loose: case-insensitive, multiline.
    rec_match = re.search(r"recommendation\s*[:.]?\s*([A-Z][^\n]{2,80})", text, re.IGNORECASE)
    cta_match = re.search(
        r"comments?\s*to\s*(?:the\s*)?authors?\s*[:.]?\s*\n?(.+?)"
        r"(?=\n(?:confidential|comments?\s*to\s*editor|recommendation|score|attachments|$))",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    cc_match = re.search(
        r"(?:confidential\s*comments?|comments?\s*to\s*editor)\s*[:.]?\s*\n?(.+?)"
        r"(?=\n(?:comments?\s*to\s*author|recommendation|score|attachments|$))",
        text,
        re.DOTALL | re.IGNORECASE,
    )

    recommendation = (rec_match.group(1).strip() if rec_match else "") or ""
    cta = (cta_match.group(1).strip() if cta_match else "") or ""
    cc = (cc_match.group(1).strip() if cc_match else "") or ""

    if not (recommendation or cta or cc):
        return None

    word_text = cta or text
    return {
        "revision": 0,
        "recommendation": recommendation,
        "recommendation_raw": recommendation,
        "comments_to_author": cta[:20000],
        "confidential_comments": cc[:20000],
        "raw_text": text[:20000],
        "scores": {},
        "report_date": None,
        "word_count": len(word_text.split()),
        "attachments": [],
        "source": "wiley_panel",
        "extraction_status": "ok" if (cta or cc) else "shell_only",
        "available": True,
        "platform_specific": {
            "referee_name": referee_name,
            "card_index": card_index,
        },
    }


def extract_referees() -> list[dict]:
    # Expand all "More Details" — multiple passes because cards start in mixed states
    # and clicking toggles. We want them ALL expanded; the button text changes to
    # "Less Details" when expanded, so click only buttons that say "More".
    for _ in range(3):
        clicked = js(
            """
            var btns = document.querySelectorAll('[data-test-id="more-details-button"]');
            var n = 0;
            for (var i = 0; i < btns.length; i++) {
                var txt = (btns[i].textContent || '').toLowerCase();
                if (txt.indexOf('more') >= 0) {
                    btns[i].click();
                    n++;
                }
            }
            n + '';
        """
        )
        time.sleep(1.5)
        try:
            if int(clicked.strip()) == 0:
                break
        except ValueError:
            break

    # Get count
    count_s = js(
        'document.querySelectorAll(\'[data-test-id=\\"reviewer-invitation-log-card\\"]\').length + ""'
    )
    try:
        count = int(count_s)
    except ValueError:
        count = 0

    # Make stable references
    js(
        "window._revCards = document.querySelectorAll('[data-test-id=\\\"reviewer-invitation-log-card\\\"]');"
    )

    referees = []
    for i in range(count):
        # Basic fields
        basic = js(
            f"""
            var c = window._revCards[{i}];
            var nameEl = c.querySelector('[data-test-id*=\\"reviewer-name-\\"]');
            var name = nameEl ? nameEl.textContent.trim() : '';
            var nameTid = nameEl ? nameEl.getAttribute('data-test-id') : '';
            var email = (c.querySelector('[data-test-id=\\"reviewer-email\\"]') || {{}}).textContent || '';
            var aff = (c.querySelector('[data-test-id^=\\"aff-\\"]') || {{}}).textContent || '';
            var status = (c.querySelector('[data-test-id=\\"reviewer-card-status\\"]') || {{}}).textContent || '';
            var kw = (c.querySelector('[data-test-id=\\"footer-keywords-list\\"]') || {{}}).textContent || '';
            name + ';|;' + nameTid + ';|;' + email + ';|;' + aff + ';|;' + status + ';|;' + kw;
        """
        )
        parts = basic.split(";|;")
        if len(parts) != 6:
            continue
        name, name_tid, email, aff, status, kw = parts
        name = name.strip()
        email = email.strip()
        aff = aff.strip()
        status = status.strip()
        kw = kw.strip()

        # Get card innerText and parse dates from it (robust to DOM structure)
        card_text = js(f"window._revCards[{i}].innerText || ''")
        dates = _parse_card_dates(card_text)

        source = extract_source_from_tid(name_tid)
        ref = {
            "name": name,
            "email": email,
            "institution": aff,
            "status": map_status(status),
            "dates": {
                "invited": dates.get("invited", ""),
                "agreed": dates.get("accepted", ""),
                "due": dates.get("due", ""),
                "returned": dates.get("submitted", ""),
            },
            "platform_specific": {
                "wiley_status": status,
                "source": source,
                "invited_date": dates.get("invited", ""),
                "accepted_date": dates.get("accepted", ""),
                "expired_date": dates.get("expired", ""),
                "declined_date": dates.get("declined", ""),
                "due_date": dates.get("due", ""),
                "submitted_date": dates.get("submitted", ""),
            },
        }
        if kw and "no keywords" not in kw.lower():
            ref["web_profile"] = {
                "research_topics": [k.strip() for k in kw.split(";") if k.strip()]
            }

        # Defensive: extract submitted-report panel content if any reviewer
        # has actually submitted (today: none have).
        try:
            submitted = extract_submitted_report_for_referee(i, name)
        except Exception as e:
            print(f"   ⚠️ Submitted-report extraction failed for {name}: {str(e)[:60]}")
            submitted = None
        if submitted:
            ref.setdefault("reports", []).append(submitted)
            ref["report"] = dict(submitted)
            if submitted.get("recommendation") and not ref.get("recommendation"):
                ref["recommendation"] = submitted["recommendation"]

        referees.append(ref)
    return referees


def extract_files() -> dict:
    # Click files collapsible header
    js(
        """
        var c = document.querySelector('[data-test-id=\\"files-collapsible\\"]');
        if (c) { var h = c.querySelector('.ant-collapse-header'); if (h) h.click(); }
    """
    )
    time.sleep(1)

    raw = js(
        """
        var c = document.querySelector('[data-test-id=\\"files-collapsible\\"]');
        if (!c) { 'NONE'; }
        else {
            var spans = c.querySelectorAll('span');
            var out = [];
            for (var i = 0; i < spans.length; i++) {
                var t = spans[i].textContent.trim();
                if (!t || t === 'Files') continue;
                out.push(t);
            }
            out.join(';;;');
        }
    """
    )
    if not raw or raw == "NONE":
        return {"files": []}

    tokens = raw.split(";;;")
    files = []
    current = ""
    for tok in tokens:
        t = tok.strip()
        if not t:
            continue
        if re.search(r"\b(KB|MB|GB)\b", t):
            if current:
                files.append({"filename": current, "size": t})
                current = ""
        else:
            if current and not files:
                pass
            current = t
    return {"files": files}


def expand_all_panels():
    """Click every ant-collapse-header until all top-level panels are open."""
    # Click all headers (idempotent for already-active items)
    for _ in range(3):
        clicked = js(
            """
            var headers = document.querySelectorAll('.ant-collapse-header');
            var n = 0;
            for (var i = 0; i < headers.length; i++) {
                var item = headers[i].closest('.ant-collapse-item');
                if (item && !item.classList.contains('ant-collapse-item-active')) {
                    headers[i].click();
                    n++;
                }
            }
            n;
        """
        )
        time.sleep(2)
        try:
            if int(clicked or "0") == 0:
                break
        except ValueError:
            break


def _find_panel_by_label(label_prefix: str) -> int:
    """Return the index of the first .ant-collapse-item whose header starts with label."""
    raw = js(
        f"""
        var items = document.querySelectorAll('.ant-collapse-item');
        var found = -1;
        for (var i = 0; i < items.length; i++) {{
            var h = items[i].querySelector('.ant-collapse-header');
            if (!h) continue;
            var t = h.textContent.trim().toLowerCase();
            if (t.indexOf('{label_prefix.lower()}') === 0) {{
                found = i;
                break;
            }}
        }}
        found + '';
    """
    )
    try:
        return int(raw.strip())
    except ValueError:
        return -1


def extract_abstract() -> str:
    """Read the Abstract panel, expanding it if necessary."""
    idx = _find_panel_by_label("abstract")
    if idx < 0:
        return ""

    for _ in range(4):
        raw = js(
            f"""
            (function(){{
                var it = document.querySelectorAll('.ant-collapse-item')[{idx}];
                if (!it) return '';
                var box = it.querySelector('.ant-collapse-content-box');
                if (box && box.textContent && box.textContent.trim()) return box.textContent.trim();
                var content = it.querySelector('.ant-collapse-content');
                if (content && content.textContent && content.textContent.trim()) return content.textContent.trim();
                return (it.textContent || '').trim();
            }})()
        """
        )
        text = (raw or "").strip()
        if len(text) > 30:
            break
        # Click the Abstract header to expand the panel
        js(
            f"""
            (function(){{
                var it = document.querySelectorAll('.ant-collapse-item')[{idx}];
                if (!it) return;
                var h = it.querySelector('.ant-collapse-header');
                if (h) h.click();
            }})()
        """
        )
        time.sleep(2)
    else:
        return ""

    # Strip the leading "Abstract" header
    lines = text.split("\n", 1)
    if len(lines) == 2 and lines[0].strip().lower() == "abstract":
        return lines[1].strip()
    if text.lower().startswith("abstract"):
        return text[len("abstract") :].strip()
    return text


def extract_version_info() -> dict:
    """Extract version number and is_revision flag."""
    raw = js(
        "(document.querySelector('[data-test-id=\\\"manuscript-current-version\\\"]') || {}).textContent || ''"
    )
    ver_raw = (raw or "").strip()
    # e.g. "v1", "v2", "V1", "Version 1"
    m = re.search(r"(\d+)", ver_raw)
    version = int(m.group(1)) if m else 1
    # version isn't a canonical top-level field, so also stash in platform_specific
    return {
        "is_revision": version > 1,
        "revision_number": max(version - 1, 0),
        "_wiley_version_raw": ver_raw or f"v{version}",
        "_wiley_version_num": version,
    }


_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def _parse_activity_datetime(s: str) -> tuple[str, str]:
    """Parse 'March 29, 2026 at 23:21' → ('2026-03-29', '2026-03-29T23:21:00')"""
    if not s:
        return "", ""
    s = s.strip()
    m = re.match(
        r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})(?:\s+at\s+(\d{1,2}):(\d{2}))?",
        s,
    )
    if not m:
        return "", ""
    month_name, day, year, hh, mm = m.groups()
    month = _MONTHS.get(month_name.lower())
    if not month:
        return "", ""
    try:
        date_obj = datetime(int(year), month, int(day))
    except ValueError:
        return "", ""
    date_str = date_obj.strftime("%Y-%m-%d")
    if hh is not None and mm is not None:
        dt_obj = date_obj.replace(hour=int(hh), minute=int(mm))
        return date_str, dt_obj.isoformat()
    return date_str, date_obj.isoformat()


_EVENT_TYPE_MAP = [
    ("manuscript submitted", "manuscript_submission"),
    ("approved manuscript after technical checks", "technical_check_passed"),
    ("editor assigned to the manuscript for pre-peer review", "editor_assigned_prepr"),
    ("editor assigned to the manuscript for peer review", "ae_assigned"),
    ("invitation to review", "reviewer_invitation"),
    ("reviewer accepted to review", "reviewer_accepted"),
    ("accepted invitation to review", "reviewer_accepted"),
    ("thank you for agreeing to review", "reviewer_thanks"),
    ("third reminder to respond to review invite", "reminder_respond_3"),
    ("second reminder to respond to review invite", "reminder_respond_2"),
    ("first reminder to respond to review invite", "reminder_respond_1"),
    ("third reminder to invite reviewers", "reminder_invite_3"),
    ("second reminder to invite reviewers", "reminder_invite_2"),
    ("first reminder to invite reviewers", "reminder_invite_1"),
    ("reviewers needed", "reviewers_needed_reminder"),
    ("review invitation expired", "reviewer_expired"),
    ("review invitation revoked", "reviewer_revoked"),
    ("review invitation declined", "reviewer_declined"),
    ("declined invitation to review", "reviewer_declined"),
    ("review declined", "reviewer_declined"),
    ("review report submitted", "reviewer_report_submitted"),
    ("review submitted", "reviewer_report_submitted"),
    ("review overdue", "reviewer_overdue"),
]


def _classify_event(title: str) -> str:
    tl = (title or "").lower()
    for needle, etype in _EVENT_TYPE_MAP:
        if needle in tl:
            return etype
    return "other"


def extract_audit_trail() -> list[dict]:
    """Parse the Activity Logs panel into structured events."""
    # Ensure the Activity Log panel is expanded. It must be open for child events to render.
    for _ in range(4):
        count_raw = js(
            "var s = document.querySelector('[data-test-id=\"activity-log-section\"]'); "
            "s ? s.querySelectorAll('.ant-collapse-item').length + '' : '0'"
        )
        try:
            count = int(count_raw.strip())
        except ValueError:
            count = 0
        if count > 1:  # > 1 means the section header exists + has child events
            break
        # Click the Activity Log header to expand it
        js(
            "var s = document.querySelector('[data-test-id=\"activity-log-section\"]'); "
            "if (s) { var h = s.querySelector('.ant-collapse-header'); if (h) h.click(); }"
        )
        time.sleep(2)
    if count == 0:
        return []

    # Read each header directly (no window._alItems cache — stale refs break across navigations)
    items = []
    for i in range(count):
        header_text = js(
            f"""
            (function(){{
                var section = document.querySelector('[data-test-id=\"activity-log-section\"]');
                if (!section) return '';
                var its = section.querySelectorAll('.ant-collapse-item');
                if (!its[{i}]) return '';
                var h = its[{i}].querySelector('.ant-collapse-header');
                return h ? h.innerText : '';
            }})()
        """
        )
        if not header_text or header_text == "missing value":
            continue
        items.append(header_text)

    events = []
    date_re = re.compile(r"([A-Za-z]+\s+\d{1,2},?\s+\d{4}\s+at\s+\d{1,2}:\d{2})")
    for seq, block in enumerate(items, 1):
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        title = lines[0]
        # Skip the Activity Logs section header itself
        if title.lower().startswith("activity logs") or title.lower() in (
            "filter",
            "from",
            "to",
        ):
            continue
        # Find the date line
        date_line = ""
        for ln in lines:
            if date_re.search(ln):
                date_line = ln
                break
        date_str, datetime_str = _parse_activity_datetime(date_line)

        # Collect From / To info
        sender = ""
        sender_role = ""
        recipient = ""
        recipient_role = ""
        i = 0
        while i < len(lines):
            ln = lines[i]
            if ln == "From:" and i + 1 < len(lines):
                sender = lines[i + 1]
                if i + 2 < len(lines) and lines[i + 2] not in ("To:",):
                    # Role line often follows, e.g. "– Associate Editor" or "REVIEWER"
                    peek = lines[i + 2]
                    if peek not in ("To:",) and len(peek) < 60 and not date_re.search(peek):
                        sender_role = peek
            if ln == "To:" and i + 1 < len(lines):
                recipient = lines[i + 1]
                if i + 2 < len(lines):
                    peek = lines[i + 2]
                    if peek != "From:" and len(peek) < 60 and not date_re.search(peek):
                        recipient_role = peek
            i += 1

        etype = _classify_event(title)
        ev = {
            "date": date_str,
            "datetime": datetime_str,
            "type": etype,
            "event_type": "email"
            if etype.startswith("reminder_") or "invitation" in etype or "reviewer_" in etype
            else "status_change",
            "description": title,
            "source": "wiley_scienceconnect",
            "external": False,
            "from": sender,
            "from_role": sender_role.lstrip("– ").strip(),
            "to": recipient,
            "to_role": recipient_role.lstrip("– ").strip(),
            "sequence": seq,
        }
        events.append(ev)

    # Sort chronologically (earliest first)
    events.sort(key=lambda e: e.get("datetime", ""))
    for i, ev in enumerate(events, 1):
        ev["sequence"] = i
    return events


def compute_timeline_analytics(audit_trail: list[dict], referees: list[dict]) -> dict:
    """Compute basic analytics over the audit trail."""
    if not audit_trail:
        return {}

    from collections import Counter

    dates = [e.get("datetime") for e in audit_trail if e.get("datetime")]
    if not dates:
        return {"total_events": len(audit_trail)}

    try:
        parsed = [datetime.fromisoformat(d) for d in dates]
    except ValueError:
        return {"total_events": len(audit_trail)}

    parsed.sort()
    span_days = (parsed[-1] - parsed[0]).days

    weekday_counts = Counter(d.strftime("%A") for d in parsed)
    hour_counts = Counter(str(d.hour) for d in parsed)
    participants = set()
    for e in audit_trail:
        if e.get("from"):
            participants.add(e["from"])
        if e.get("to"):
            participants.add(e["to"])

    # Per-referee metrics
    ref_metrics = {}
    for r in referees:
        email = (r.get("email") or "").lower()
        if not email:
            continue
        invited = r.get("dates", {}).get("invited")
        agreed = r.get("dates", {}).get("agreed")
        reminders = sum(
            1
            for e in audit_trail
            if e.get("to", "").strip().lower().replace(" ", "")
            in r.get("name", "").lower().replace(" ", "")
            and "reminder" in e.get("type", "")
        )
        response_days = 0
        if invited and agreed:
            try:
                response_days = (
                    datetime.strptime(agreed, "%Y-%m-%d") - datetime.strptime(invited, "%Y-%m-%d")
                ).days
            except ValueError:
                response_days = 0
        reliability = (
            100
            if r.get("status") == "Agreed"
            else (0 if r.get("status") in ("Declined", "No Response", "Terminated") else 50)
        )
        ref_metrics[email] = {
            "response_time_days": response_days,
            "reliability_score": reliability,
            "reminders_received": reminders,
            "responses_sent": 1 if r.get("status") != "Invited" else 0,
        }

    peak_weekday = weekday_counts.most_common(1)[0][0] if weekday_counts else ""
    peak_hour = hour_counts.most_common(1)[0][0] if hour_counts else ""

    return {
        "total_events": len(audit_trail),
        "communication_span_days": span_days,
        "unique_participants": len(participants),
        "referee_metrics": ref_metrics,
        "communication_patterns": {
            "peak_weekday": peak_weekday,
            "peak_hour": f"{peak_hour}:00" if peak_hour else "",
            "weekday_distribution": dict(weekday_counts),
            "hour_distribution": dict(hour_counts),
            "most_active_period": (
                f"{peak_weekday} {peak_hour}:00" if peak_weekday and peak_hour else ""
            ),
        },
        "response_time_analysis": {},
        "reminder_effectiveness": {},
    }


def extract_manuscript_detail(ms: dict) -> dict:
    print(f"\n🔍 Extracting {ms['manuscript_id']}: {ms['title'][:60]}")
    navigate(ms["href"])
    # Wait for detail page
    for _ in range(20):
        time.sleep(1)
        got = js(
            "document.querySelector('[data-test-id=\\\"manuscript-id\\\"]') ? 'true' : 'false'"
        )
        if got == "true":
            break
    time.sleep(2)

    data = {
        "manuscript_id": ms["manuscript_id"],
        "extraction_timestamp": datetime.now().isoformat(),
    }
    meta = extract_metadata()
    meta.pop("manuscript_id", None)
    data.update(meta)
    data["manuscript_id"] = ms["manuscript_id"]

    # NOTE: do NOT call expand_all_panels here — individual extractors handle
    # their own expansion (abstract, files, activity-log, reviewers).

    # Version / is_revision
    ver_info = extract_version_info()
    # Canonical fields
    data["is_revision"] = ver_info["is_revision"]
    data["revision_number"] = ver_info["revision_number"]
    # Non-canonical fields stashed in platform_specific
    data.setdefault("platform_specific", {})
    data["platform_specific"]["wiley_version_raw"] = ver_info["_wiley_version_raw"]
    data["platform_specific"]["wiley_version_num"] = ver_info["_wiley_version_num"]
    # Keep internal field for the debug print below
    data["_wiley_version_num"] = ver_info["_wiley_version_num"]

    # Abstract
    data["abstract"] = extract_abstract()

    data["authors"] = extract_authors()
    data["editors"] = extract_editors()
    data["referees"] = extract_referees()
    data["documents"] = extract_files()

    # Audit trail + timeline analytics
    data["audit_trail"] = extract_audit_trail()
    data["communication_timeline"] = [
        e for e in data["audit_trail"] if e.get("event_type") == "email"
    ]
    data["timeline_analytics"] = compute_timeline_analytics(data["audit_trail"], data["referees"])

    # Derive submission_date from audit trail (earliest manuscript_submission event)
    sub_events = [e for e in data["audit_trail"] if e.get("type") == "manuscript_submission"]
    if sub_events:
        # Use the earliest
        sub_events.sort(key=lambda e: e.get("datetime", ""))
        data["submission_date"] = sub_events[0].get("date", "")
    else:
        data["submission_date"] = ""

    # Backfill referee dates from audit trail where missing
    _backfill_referee_dates(data["referees"], data["audit_trail"])

    print(
        f"   ✅ abs={len(data['abstract'])}c "
        f"authors={len(data['authors'])} "
        f"editors={len(data['editors'])} "
        f"referees={len(data['referees'])} "
        f"files={len(data['documents']['files'])} "
        f"audit_trail={len(data['audit_trail'])} "
        f"sub={data['submission_date']} "
        f"v{data.get('_wiley_version_num', 1)}"
    )
    return data


def _backfill_referee_dates(referees: list[dict], audit_trail: list[dict]):
    """Fill in missing referee dates from the audit trail event log."""
    by_name = {r.get("name", "").lower(): r for r in referees if r.get("name")}

    # Collect bulk invitation dates (sent to "reviewers (N)")
    bulk_invite_dates = [
        ev.get("date")
        for ev in audit_trail
        if ev.get("type") == "reviewer_invitation"
        and "reviewers" in (ev.get("to") or "").lower()
        and "(" in (ev.get("to") or "")
        and ev.get("date")
    ]

    for ev in audit_trail:
        etype = ev.get("type", "")
        date_str = ev.get("date", "")
        if not date_str:
            continue
        ref_name = (ev.get("to") or "").lower()
        if etype == "reviewer_invitation" and ref_name in by_name:
            r = by_name[ref_name]
            if not r.get("dates", {}).get("invited"):
                r.setdefault("dates", {})["invited"] = date_str
                r.setdefault("platform_specific", {})["invited_date"] = date_str
        elif etype == "reviewer_accepted" and (ev.get("from") or "").lower() in by_name:
            r = by_name[(ev.get("from") or "").lower()]
            if not r.get("dates", {}).get("agreed"):
                r.setdefault("dates", {})["agreed"] = date_str
                r.setdefault("platform_specific", {})["accepted_date"] = date_str
        elif etype == "reviewer_declined" and (ev.get("from") or "").lower() in by_name:
            r = by_name[(ev.get("from") or "").lower()]
            r.setdefault("platform_specific", {})["declined_date"] = date_str

    # For referees still missing invited date, use earliest bulk invitation
    # (likely covers them since they weren't individually addressed)
    if bulk_invite_dates:
        earliest_bulk = min(bulk_invite_dates)
        for r in referees:
            if not r.get("dates", {}).get("invited"):
                r.setdefault("dates", {})["invited"] = earliest_bulk
                ps = r.setdefault("platform_specific", {})
                ps["invited_date"] = earliest_bulk
                ps["invite_source"] = "bulk_invitation"


def _run_preflight() -> bool:
    """Run scripts/check_wiley_prereqs.py and return True iff all checks pass.
    On failure, prints the same actionable remediation message that the
    standalone script would emit, then returns False.
    """
    project_dir = Path(__file__).parent.parent.parent.parent
    preflight = project_dir / "scripts" / "check_wiley_prereqs.py"
    if not preflight.exists():
        # Pre-flight script is optional; fall through to legacy in-process check
        return True
    r = subprocess.run(
        [sys.executable, str(preflight)],
        capture_output=True,
        text=True,
        timeout=20,
    )
    if r.stdout:
        print(r.stdout, end="" if r.stdout.endswith("\n") else "\n")
    if r.stderr:
        print(r.stderr, end="" if r.stderr.endswith("\n") else "\n")
    return r.returncode == 0


def main():
    print("=" * 60)
    print(f"  {JOURNAL_NAME} — Wiley ScienceConnect Attach Extractor")
    print("=" * 60)

    # Pre-flight: tab open, AppleScript JS enabled, logged in
    if not _run_preflight():
        print("\nResolve the issues above and re-run.")
        sys.exit(1)

    if not switch_to_wiley_tab():
        print("❌ No review.wiley.com tab open. Please navigate there first.")
        sys.exit(1)

    # Ensure AppleScript JS is on (defensive — pre-flight covers this)
    title = js("document.title")
    if not title:
        print("❌ AppleScript JS returned empty. Enable:")
        print("   Chrome > View > Developer > Allow JavaScript from Apple Events")
        sys.exit(1)

    print(f"✅ Connected to Wiley dashboard (title: {title})")

    # Navigate to dashboard if not already there
    url = _osa('tell application "Google Chrome" to return URL of active tab of front window')
    if url and url.rstrip("/") != "https://review.wiley.com":
        navigate("https://review.wiley.com/")
        time.sleep(4)

    print("\n📋 Collecting manuscripts from dashboard...")
    manuscripts = collect_manuscript_ids()
    print(f"   Found {len(manuscripts)} manuscript(s)")
    for m in manuscripts:
        print(f"   • {m['manuscript_id']}: {m['title'][:60]}")

    if not manuscripts:
        print("❌ No manuscripts found")
        sys.exit(1)

    extracted = []
    for ms in manuscripts:
        try:
            data = extract_manuscript_detail(ms)
            if data:
                extracted.append(data)
        except Exception as e:
            print(f"   ❌ Failed for {ms['manuscript_id']}: {e}")

    # Return to dashboard for next run
    navigate("https://review.wiley.com/")

    # Build final output
    result = {
        "extraction_timestamp": datetime.now().isoformat(),
        "journal": JOURNAL_CODE,
        "journal_name": JOURNAL_NAME,
        "extractor_version": "1.0.0-attach",
        "manuscripts": extracted,
        "summary": {
            "total": len(extracted),
            "statuses": {},
        },
    }
    for m in extracted:
        st = m.get("status", "Unknown")
        result["summary"]["statuses"][st] = result["summary"]["statuses"].get(st, 0) + 1
        # Strip internal-only fields before normalize + save
        m.pop("_wiley_version_num", None)

    normalize_wrapper(result, JOURNAL_CODE)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = OUTPUT_DIR / f"mf_wiley_extraction_{ts}.json"
    with open(out_file, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n💾 Saved: {out_file}")
    print(f"   {len(extracted)} manuscript(s), schema v{result.get('schema_version', '?')}")
    return out_file


if __name__ == "__main__":
    main()
