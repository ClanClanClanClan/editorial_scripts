#!/bin/bash
# Load credentials for editorial scripts

echo "🔐 Loading Editorial Scripts Credentials"
echo "======================================"

# Source the shell profile to get credentials
if [ -f ~/.zshrc ]; then
    # Extract the latest (last) occurrence of each credential
    export ORCID_EMAIL=$(grep "export ORCID_EMAIL=" ~/.zshrc | tail -1 | cut -d'"' -f2)
    export ORCID_PASSWORD=$(grep "export ORCID_PASSWORD=" ~/.zshrc | tail -1 | cut -d'"' -f2)
    export SCHOLARONE_EMAIL=$(grep "export SCHOLARONE_EMAIL=" ~/.zshrc | tail -1 | cut -d'"' -f2)
    export SCHOLARONE_PASSWORD=$(grep "export SCHOLARONE_PASSWORD=" ~/.zshrc | tail -1 | cut -d'"' -f2)
fi

# Display loaded credentials (masked)
if [ -n "$ORCID_EMAIL" ]; then
    echo "✅ ORCID_EMAIL: $ORCID_EMAIL"
    echo "✅ ORCID_PASSWORD: $(echo $ORCID_PASSWORD | sed 's/./*/g')"
else
    echo "❌ ORCID credentials not found"
fi

if [ -n "$SCHOLARONE_EMAIL" ]; then
    echo "✅ SCHOLARONE_EMAIL: $SCHOLARONE_EMAIL"
    echo "✅ SCHOLARONE_PASSWORD: $(echo $SCHOLARONE_PASSWORD | sed 's/./*/g')"
else
    echo "⚠️  ScholarOne credentials not found (optional)"
fi

echo ""
echo "Credentials loaded into current session."
echo "You can now run: ./run_sicon.sh"