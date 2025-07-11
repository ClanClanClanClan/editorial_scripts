#!/bin/bash
# 1Password session management script

# Check if signed in
if ! op whoami > /dev/null 2>&1; then
    echo "Signing in to 1Password..."
    if eval $(op signin --raw); then
        echo "✅ 1Password signed in successfully"
    else
        echo "❌ Failed to sign in to 1Password"
        exit 1
    fi
else
    echo "✅ Already signed in to 1Password"
fi

# Export session for current shell
export OP_SESSION_my=$(op signin --raw)
echo "Session exported: $OP_SESSION_my"
