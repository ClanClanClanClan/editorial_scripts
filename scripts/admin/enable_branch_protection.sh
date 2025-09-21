#!/usr/bin/env bash
set -euo pipefail

# This script demonstrates how to enable required PR reviews (branch protection)
# using either GitHub CLI or direct REST API. Requires admin permissions.

REPO=${REPO:-"owner/repo"}      # e.g., my-org/my-repo
BRANCH=${BRANCH:-"main"}

echo "[info] Ensure gh CLI is authenticated: gh auth login"

if command -v gh >/dev/null 2>&1; then
  echo "[gh] Enabling required reviews on $REPO@$BRANCH"
  gh api \
    -X PUT \
    -H "Accept: application/vnd.github+json" \
    "/repos/$REPO/branches/$BRANCH/protection" \
    -f required_status_checks='{"strict":true,"contexts":[]}' \
    -f enforce_admins=true \
    -f required_pull_request_reviews='{"dismiss_stale_reviews":true,"require_code_owner_reviews":false,"required_approving_review_count":1}' \
    -f restrictions='null'
else
  echo "[curl] gh not found. Using REST API via curl. Set GITHUB_TOKEN and REPO."
  : "${GITHUB_TOKEN:?Set GITHUB_TOKEN env var}"
  curl -sS -X PUT \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github+json" \
    -d '{
      "required_status_checks": {"strict": true, "contexts": []},
      "enforce_admins": true,
      "required_pull_request_reviews": {
        "dismiss_stale_reviews": true,
        "require_code_owner_reviews": false,
        "required_approving_review_count": 1
      },
      "restrictions": null
    }' \
    "https://api.github.com/repos/$REPO/branches/$BRANCH/protection"
fi

echo "[done] Branch protection policy updated for $REPO@$BRANCH"

