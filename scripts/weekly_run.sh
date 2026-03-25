#!/usr/bin/env bash
# Weekly editorial extraction pipeline.
# Runs all extractors, trains models, generates recommendations and dashboard.
#
# Usage:
#   bash scripts/weekly_run.sh
#
# Scheduled via launchd (Monday 7 AM):
#   ~/Library/LaunchAgents/com.editorial-scripts.weekly.plist

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="$PROJECT_DIR/results/logs"
LOG_FILE="$LOG_DIR/weekly_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"

# Tee output to log file
exec > >(tee -a "$LOG_FILE") 2>&1

echo "========================================"
echo "  Editorial Scripts — Weekly Run"
echo "  $(date)"
echo "========================================"
echo ""

cd "$PROJECT_DIR"

# Load credentials
if [ -f "$HOME/.editorial_scripts/load_all_credentials.sh" ]; then
    source "$HOME/.editorial_scripts/load_all_credentials.sh"
    echo "Credentials loaded."
else
    echo "WARNING: Credential loader not found."
fi

# Ensure PATH includes Python 3.12 + homebrew
export PATH="/Library/Frameworks/Python.framework/Versions/3.12/bin:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
export PYTHONPATH="$PROJECT_DIR/production/src"
PYTHON="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12"

FAILED=0
STEP=0

run_step() {
    STEP=$((STEP + 1))
    local desc="$1"
    shift
    echo ""
    echo "--- Step $STEP: $desc ---"
    if "$@"; then
        echo "  OK"
    else
        echo "  FAILED (exit $?)"
        FAILED=$((FAILED + 1))
    fi
}

# Step 1: Extract all journals
# SIAM needs headful mode for Cloudflare
export EXTRACTOR_HEADLESS=false
run_step "Extract all journals" $PYTHON run_extractors.py --all

# Step 2: Cross-journal report
run_step "Cross-journal report" $PYTHON run_extractors.py --report --json

# Step 3: Train ML models
run_step "Train ML models" $PYTHON run_pipeline.py --train

# Step 4: Run referee pipeline for all journals
PIPELINE_JOURNALS="mf mor sicon sifin jota mafe naco"
for j in $PIPELINE_JOURNALS; do
    run_step "Pipeline: $j" $PYTHON run_pipeline.py -j "$j" --pending || true
done

# Step 5: Process events (detect state changes, auto-generate AE reports)
run_step "Process events" $PYTHON -c "
from core.event_processor import process_all
process_all(provider='clipboard')
"

# Step 6: Update referee performance database
run_step "Update referee DB" $PYTHON -c "
from pipeline.referee_db_backfill import backfill
backfill(incremental=True)
"

# Step 7: Auto-generate AE reports for ready manuscripts
run_step "Auto AE reports" $PYTHON run_pipeline.py --ae-auto --provider clipboard

# Step 8: Generate dashboard
run_step "Generate dashboard" $PYTHON scripts/generate_dashboard.py

# Step 9: Send email digest (skip if Gmail scope not upgraded)
if $PYTHON -c "from pathlib import Path; import json; t=json.load(open(Path.home()/'.editorial_scripts'/'gmail_token.json' if (Path.home()/'.editorial_scripts'/'gmail_token.json').exists() else Path('config/gmail_token.json'))); exit(0 if 'gmail.send' in t.get('scopes',[]) else 1)" 2>/dev/null; then
    run_step "Send email digest" $PYTHON scripts/send_digest.py
else
    echo ""
    echo "--- Step $((STEP + 1)): Send email digest ---"
    echo "  SKIPPED (Gmail send scope not available)"
    STEP=$((STEP + 1))
fi

# Step 10: Rotate old logs (keep 90 days)
echo ""
echo "--- Log rotation ---"
find "$LOG_DIR" -name "weekly_*.log" -mtime +90 -delete 2>/dev/null || true
find "$LOG_DIR" -name "launchd_*.log" -mtime +90 -delete 2>/dev/null || true
echo "  Old logs cleaned."

# Summary
echo ""
echo "========================================"
if [ "$FAILED" -eq 0 ]; then
    echo "  All steps completed successfully."
    SOUND="Glass"
    TITLE="Editorial Scripts: Weekly Run Complete"
    MSG="All $STEP steps succeeded. Dashboard ready."
else
    echo "  Completed with $FAILED failure(s)."
    SOUND="Basso"
    TITLE="Editorial Scripts: Issues Detected"
    MSG="$FAILED of $STEP steps failed. Check log: $LOG_FILE"
fi
echo "  Log: $LOG_FILE"
echo "  $(date)"
echo "========================================"

# macOS notification
osascript -e "display notification \"$MSG\" with title \"$TITLE\" sound name \"$SOUND\"" 2>/dev/null || true
