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


def extract_referees() -> list[dict]:
    # Expand all "More Details"
    js(
        "document.querySelectorAll('[data-test-id=\\\"more-details-button\\\"]').forEach(function(b){b.click();});"
    )
    time.sleep(2)

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

        # Dates (ASCII-safe, no regex to avoid escape-layer issues)
        dates_raw = js(
            f"""
            var c = window._revCards[{i}];
            var divs = c.querySelectorAll('div');
            var out = [];
            var labels = ['Invited','Accepted','Declined','Expired','Submitted','Due'];
            for (var j = 0; j < divs.length; j++) {{
                var t = divs[j].textContent.trim();
                if (t.length > 80 || t.length < 8) continue;
                for (var k = 0; k < labels.length; k++) {{
                    var L = labels[k];
                    var idx = t.indexOf(L + ':');
                    if (idx === 0) {{
                        var v = t.substring(L.length + 1).trim();
                        out.push(L + '=' + v);
                        break;
                    }}
                }}
            }}
            out.join(';');
        """
        )
        dates = {}
        if dates_raw:
            for entry in dates_raw.split(";"):
                if "=" in entry:
                    k, v = entry.split("=", 1)
                    k = k.lower().strip()
                    v = v.strip()
                    if k not in dates:
                        dates[k] = parse_wiley_date(v)

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
    # Always use the canonical numeric ID from the card, not the heading text
    meta.pop("manuscript_id", None)
    data.update(meta)
    data["manuscript_id"] = ms["manuscript_id"]

    data["authors"] = extract_authors()
    data["editors"] = extract_editors()
    data["referees"] = extract_referees()
    data["documents"] = extract_files()

    print(
        f"   ✅ authors={len(data['authors'])} "
        f"editors={len(data['editors'])} "
        f"referees={len(data['referees'])} "
        f"files={len(data['documents']['files'])}"
    )
    return data


def main():
    print("=" * 60)
    print(f"  {JOURNAL_NAME} — Wiley ScienceConnect Attach Extractor")
    print("=" * 60)

    if not switch_to_wiley_tab():
        print("❌ No review.wiley.com tab open. Please navigate there first.")
        sys.exit(1)

    # Ensure AppleScript JS is on
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
