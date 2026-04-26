#!/usr/bin/env python3
"""Pre-flight check for the MF_WILEY attach-mode extractor.

The attach-mode extractor (production/src/extractors/mf_wiley_attach.py)
requires three things before it can run:

  1. A review.wiley.com tab open in Chrome.
  2. AppleScript JavaScript execution enabled in Chrome
     (View > Developer > Allow JavaScript from Apple Events).
  3. The tab is logged in (page title is "Dashboard | Wiley", not
     "Connexion - CONNECT" or a Cloudflare challenge).

This script verifies all three. Exits 0 with a success summary when all
pass, or exits 1 with an actionable remediation message.

Usage:
    python3 scripts/check_wiley_prereqs.py
    python3 scripts/check_wiley_prereqs.py --quiet   # only print errors
"""

import argparse
import subprocess
import sys


def _osa(script: str, timeout: float = 10) -> tuple[int, str, str]:
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", "osascript timeout"
    except FileNotFoundError:
        return 1, "", "osascript not found (not on macOS?)"


def _chrome_running() -> bool:
    rc, out, _ = _osa(
        'tell application "System Events" to (name of processes) contains "Google Chrome"'
    )
    return rc == 0 and out.lower().startswith("true")


def _find_wiley_tab() -> tuple[bool, str, str]:
    """Returns (found, url, title)."""
    script = """
tell application "Google Chrome"
    repeat with w in every window
        repeat with t in every tab of w
            if URL of t contains "review.wiley.com" then
                return (URL of t) & "|||" & (title of t)
            end if
        end repeat
    end repeat
    return "NOT_FOUND"
end tell
""".strip()
    rc, out, _ = _osa(script)
    if rc != 0 or out == "NOT_FOUND" or not out:
        return False, "", ""
    parts = out.split("|||", 1)
    url = parts[0] if parts else ""
    title = parts[1] if len(parts) > 1 else ""
    return True, url, title


def _js_apple_events_enabled() -> bool:
    """Try to evaluate a trivial JS expression against the Wiley tab if one
    is open, otherwise the front-window active tab. Handles zero-windows
    Chrome (no front window) and missing-tab cases.

    If AppleScript JS is disabled, Chrome returns an error message
    containing 'turned off' or 'JavaScript through AppleScript'.
    """
    script = """
tell application "Google Chrome"
    if (count of windows) is 0 then return "NO_WINDOWS"
    set targetTab to missing value
    repeat with w in every window
        repeat with t in every tab of w
            if URL of t contains "review.wiley.com" then
                set targetTab to t
                exit repeat
            end if
        end repeat
        if targetTab is not missing value then exit repeat
    end repeat
    if targetTab is missing value then
        try
            set targetTab to active tab of front window
        on error
            return "NO_TAB"
        end try
    end if
    try
        return (execute targetTab javascript "1+1") as text
    on error errMsg
        return "ERR:" & errMsg
    end try
end tell
""".strip()
    rc, out, err = _osa(script)
    if rc == 0 and out == "2":
        return True
    combined = (out + " " + err).lower()
    if "turned off" in combined or "javascript through applescript" in combined:
        return False
    # Other failures (no windows, no tab, syntax error) — treat as disabled so
    # the surrounding remediation message points the operator at Chrome
    return False


def _classify_title(title: str) -> str:
    t = (title or "").strip().lower()
    if not t:
        return "empty"
    # Cloudflare challenge — check first because "moment" appears in localized
    # variants across languages
    if "moment" in t or "instant" in t or "verifying" in t:
        return "cloudflare"
    # Logged-in pages — dashboard, manuscript details, profile, settings, list
    if "wiley" in t and (
        "dashboard" in t
        or "manuscript details" in t
        or "manuscripts" in t
        or "profile" in t
        or "settings" in t
        or "research exchange" in t
    ):
        return "logged_in"
    # Login pages: English ("Connect", "Sign in"), French ("Connexion"),
    # German ("Anmelden"), Spanish ("Iniciar sesión", "Conectar"), Italian
    # ("Accedi"), Portuguese ("Entrar")
    login_markers = (
        "connexion",
        "connect",
        "sign in",
        "log in",
        "login",
        "anmelden",
        "iniciar sesión",
        "iniciar sesion",
        "conectar",
        "accedi",
        "entrar",
    )
    if any(m in t for m in login_markers):
        return "logged_out"
    return "unknown"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true", help="only print on failure")
    args = parser.parse_args()

    failures: list[str] = []

    if not _chrome_running():
        print("❌ Google Chrome is not running.")
        print("   Open Chrome and navigate to https://review.wiley.com")
        sys.exit(1)

    found, url, title = _find_wiley_tab()
    if not found:
        failures.append(
            "❌ No review.wiley.com tab open in Chrome.\n"
            "   Open https://review.wiley.com in a Chrome tab and pass the\n"
            "   Cloudflare challenge if prompted."
        )
        # Skip the JS / title checks — they would target the wrong tab and
        # produce misleading remediation steps. Operator must open the tab
        # first; subsequent re-runs will surface JS / login issues.
        for f in failures:
            print(f)
        sys.exit(1)

    if not _js_apple_events_enabled():
        failures.append(
            "❌ AppleScript JavaScript execution is disabled in Chrome.\n"
            "   Open Chrome, go to View > Developer > "
            "Allow JavaScript from Apple Events, and check the box."
        )

    state = _classify_title(title)
    if state == "logged_out":
        failures.append(
            "❌ Wiley tab is on the login page.\n"
            "   Sign in via ORCID and pass any Cloudflare challenge first."
        )
    elif state == "cloudflare":
        failures.append(
            "❌ Wiley tab is on the Cloudflare challenge page.\n"
            "   Click the 'Verify you are human' checkbox and wait for the\n"
            "   dashboard to load."
        )
    elif state == "empty" and found:
        failures.append(
            "❌ Wiley tab title is empty (page may still be loading).\n"
            "   Wait for the dashboard to finish loading and re-run."
        )
    elif state == "unknown" and found:
        failures.append(
            f"⚠️ Wiley tab is on an unrecognized page ({title!r}).\n"
            "   Make sure the tab shows 'Dashboard | Wiley'."
        )

    if failures:
        for f in failures:
            print(f)
        sys.exit(1)

    if not args.quiet:
        print("✅ MF_WILEY pre-flight checks passed.")
        print(f"   Tab: {url}")
        print(f"   Title: {title}")
    sys.exit(0)


if __name__ == "__main__":
    main()
