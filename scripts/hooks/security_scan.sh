#!/usr/bin/env bash
set -eo pipefail

STAGE="$1"  # commit|push
CONFIG_FILE=".precommit-security.yaml"

MODE="push"
if [ -f "$CONFIG_FILE" ]; then
  # crude YAML parsing: look for line like `mode: commit|push|both`
  MODE_LINE=$(grep -E '^\s*mode\s*:' "$CONFIG_FILE" || true)
  if [ -n "$MODE_LINE" ]; then
    MODE=$(echo "$MODE_LINE" | awk -F: '{gsub(/ /, "", $2); print $2}')
  fi
fi

should_run() {
  case "$MODE" in
    both) return 0 ;;
    commit) [ "$STAGE" = "commit" ] && return 0 || return 1 ;;
    push) [ "$STAGE" = "push" ] && return 0 || return 1 ;;
    *) [ "$STAGE" = "push" ] && return 0 || return 1 ;;
  esac
}

if ! should_run; then
  echo "[security-scan] Skipping for stage=$STAGE (mode=$MODE)"
  exit 0
fi

echo "[security-scan] Running bandit and pip-audit (stage=$STAGE, mode=$MODE)"

# Read allowlists if present
ALLOW_BANDIT=$(grep -v '^#' .security/bandit-allowlist.txt 2>/dev/null | grep -v '^$' | tr '\n' ',' | sed 's/,$//' || true)
ALLOW_PIP=$(grep -v '^#' .security/pip-audit-allowlist.txt 2>/dev/null | grep -v '^$' | xargs -I{} printf -- '--ignore-vuln %s ' '{}' || true)

# Severity: default HIGH (fail on high); override with BANDIT_LEVEL env (e.g., MEDIUM|LOW)
BANDIT_LEVEL=${BANDIT_LEVEL:-HIGH}
BANDIT_FLAGS=("-r" "production/src" "-x" "tests,dev,archive")
case "$BANDIT_LEVEL" in
  HIGH) BANDIT_FLAGS=("-ll" "${BANDIT_FLAGS[@]}");;
  MEDIUM) BANDIT_FLAGS=("-l" "${BANDIT_FLAGS[@]}");;
  *) : ;; # default
esac

# bandit
if command -v bandit >/dev/null 2>&1; then
  if [ -n "$ALLOW_BANDIT" ]; then
    bandit -q "${BANDIT_FLAGS[@]}" -s "$ALLOW_BANDIT"
  else
    bandit -q "${BANDIT_FLAGS[@]}"
  fi
else
  echo "[security-scan] bandit not found; install or run via CI"
fi

# pip-audit
if command -v pip-audit >/dev/null 2>&1; then
  pip-audit -s $ALLOW_PIP
else
  echo "[security-scan] pip-audit not found; install or run via CI"
fi
