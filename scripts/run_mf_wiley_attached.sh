#!/usr/bin/env bash
# Wrapper for the MF_WILEY attach-mode extractor.
#
# This is a manual or scheduled-via-launchd task. It cannot run from cron
# because Wiley's Cloudflare Turnstile requires a logged-in Chrome tab
# with a human checkbox click. The wrapper:
#
#   1. Activates Chrome and opens review.wiley.com in a new tab if no
#      review.wiley.com tab is already open.
#   2. Waits a configurable warm-up window for any Cloudflare challenge
#      to resolve (operator may need to click "Verify you are human").
#   3. Runs the pre-flight check (scripts/check_wiley_prereqs.py).
#   4. Invokes the attach-mode extractor.
#
# Usage:
#   bash scripts/run_mf_wiley_attached.sh                 # interactive
#   bash scripts/run_mf_wiley_attached.sh --warm 60       # wait 60s before extracting

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="${PYTHON:-/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12}"

WARM_SECONDS=15
while [[ $# -gt 0 ]]; do
    case "$1" in
        --warm)
            WARM_SECONDS="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

echo "▶ MF_WILEY attach-mode wrapper"
echo "  Project: $PROJECT_DIR"
echo "  Python:  $PYTHON"
echo "  Warm-up: ${WARM_SECONDS}s"
echo

# Step 1: ensure Chrome is open with a review.wiley.com tab
osascript <<'APPLESCRIPT'
tell application "Google Chrome"
    activate
    set foundTab to false
    repeat with w in every window
        repeat with t in every tab of w
            if URL of t contains "review.wiley.com" then
                set foundTab to true
                exit repeat
            end if
        end repeat
        if foundTab then exit repeat
    end repeat
    if not foundTab then
        if (count of windows) is 0 then
            make new window
        end if
        set newTab to make new tab at end of tabs of front window
        set URL of newTab to "https://review.wiley.com/"
    end if
end tell
APPLESCRIPT

# Step 2: warm-up window (give Cloudflare time to resolve / let operator click)
echo "  Waiting ${WARM_SECONDS}s for Wiley dashboard to load..."
sleep "$WARM_SECONDS"

# Step 3: pre-flight
echo
if ! "$PYTHON" "$PROJECT_DIR/scripts/check_wiley_prereqs.py"; then
    echo
    echo "❌ Pre-flight failed. Aborting."
    exit 1
fi

# Step 4: run the extractor
echo
echo "▶ Running attach-mode extractor"
cd "$PROJECT_DIR"
exec env PYTHONPATH="$PROJECT_DIR/production/src" "$PYTHON" \
    "$PROJECT_DIR/production/src/extractors/mf_wiley_attach.py"
