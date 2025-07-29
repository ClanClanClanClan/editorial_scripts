#!/bin/bash

echo "🚀 MF EXTRACTOR RUNNER"
echo "====================="

# Try to load secure credentials first
echo "🔐 Setting up secure credentials..."
python3 -c "from secure_credentials import SecureCredentialManager; manager = SecureCredentialManager(); manager.setup_environment()"

# Check if credentials are now available (from secure storage or environment)
if [ -z "$MF_EMAIL" ] || [ -z "$MF_PASSWORD" ]; then
    echo ""
    echo "❌ No credentials found. You need to store them securely first:"
    echo ""
    echo "   python3 secure_credentials.py store"
    echo ""
    echo "Or set environment variables manually:"
    echo "   export MF_EMAIL='your-email@domain.com'"
    echo "   export MF_PASSWORD='your-password'"
    echo ""
    echo "Then run this script again."
    exit 1
fi

echo "✅ Credentials loaded successfully"
echo "📧 Email: $MF_EMAIL"
echo "🔐 Password: [HIDDEN]"
echo ""

echo "🏃 Running MF extractor..."
python3 mf_extractor.py

echo ""
echo "🎯 Extraction complete!"
echo "Check the output above for results."