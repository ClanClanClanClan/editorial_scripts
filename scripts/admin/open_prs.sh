#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   REPO_SLUG=ClanClanClanClan/editorial_scripts \
#   BASE_BRANCH=master \
#   REMOTE_NAME=origin \
#   scripts/admin/open_prs.sh
#
# Requires: gh (GitHub CLI) authenticated with access to the repo

REPO_SLUG=${REPO_SLUG:-""}
BASE_BRANCH=${BASE_BRANCH:-"master"}
REMOTE_NAME=${REMOTE_NAME:-"origin"}

if [ -z "$REPO_SLUG" ]; then
  echo "Set REPO_SLUG, e.g. REPO_SLUG=ClanClanClanClan/editorial_scripts" >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) is required. Install and run: gh auth login" >&2
  exit 1
fi

# Ensure remote exists and points to provided slug
if git remote get-url "$REMOTE_NAME" >/dev/null 2>&1; then
  echo "[info] Using existing remote $REMOTE_NAME"
else
  echo "[info] Adding remote $REMOTE_NAME for $REPO_SLUG"
  git remote add "$REMOTE_NAME" "https://github.com/$REPO_SLUG.git"
fi

push_branch_pr() {
  local branch=$1 title=$2 body=$3
  echo "[push] $branch"
  git push -u "$REMOTE_NAME" "$branch"
  echo "[pr]   $branch -> $BASE_BRANCH"
  gh pr create --repo "$REPO_SLUG" \
    --base "$BASE_BRANCH" \
    --head "$branch" \
    --title "$title" \
    --body "$body"
}

# style-sweep
if git rev-parse --verify style-sweep >/dev/null 2>&1; then
  push_branch_pr style-sweep \
    "chore(style): normalize whitespace/EOF across non-active trees" \
    "Non-functional style cleanup across archive/dev/production/docs; no code behavior changes."
fi

# ci-trivy
if git rev-parse --verify ci-trivy >/dev/null 2>&1; then
  push_branch_pr ci-trivy \
    "docs: add Makefile and CONTRIBUTING; reinforce CI/dev workflow" \
    "Add Makefile targets (install, hooks, lint, fix, type, test, security), and CONTRIBUTING with tiered mypy and configurable security hooks."
fi

# mypy-monitoring
if git rev-parse --verify mypy-monitoring >/dev/null 2>&1; then
  push_branch_pr mypy-monitoring \
    "chore(mypy): enforce monitoring (middleware/telemetry); typing/logging fixes" \
    "Adds enforced mypy for monitoring. Minimal typing/logging adjustments for clean checks."
fi

# mypy-tasks
if git rev-parse --verify mypy-tasks >/dev/null 2>&1; then
  push_branch_pr mypy-tasks \
    "chore(mypy): add enforced tier for monitoring and tasks" \
    "Extends enforced mypy tier to src/ecc/infrastructure/tasks."
fi

# mypy-storage
if git rev-parse --verify mypy-storage >/dev/null 2>&1; then
  push_branch_pr mypy-storage \
    "chore(mypy): add storage (infra/adapters) to enforced tier" \
    "Extends enforced mypy tier to src/ecc/infrastructure/storage and src/ecc/adapters/storage."
fi

# mypy-adapters-journals
if git rev-parse --verify mypy-adapters-journals >/dev/null 2>&1; then
  push_branch_pr mypy-adapters-journals \
    "chore(mypy): add enforced tier for adapters/journals; annotate factory return" \
    "Adds enforced mypy for adapters/journals and annotates get_adapter() return."
fi

echo "[done] Pushed branches and opened PRs where applicable."
