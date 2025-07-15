#!/bin/bash
# Setup script for full automation - adds credentials to environment
# Run once to enable fully automated extractions

echo "🔧 EDITORIAL SCRIPTS AUTOMATION SETUP"
echo "======================================"
echo ""
echo "This script will help you set up environment variables for full automation."
echo "Your credentials will be stored in your shell profile for persistent access."
echo ""

# Check which shell is being used
if [[ $SHELL == *"zsh"* ]]; then
    PROFILE_FILE="$HOME/.zshrc"
    SHELL_NAME="zsh"
elif [[ $SHELL == *"bash"* ]]; then
    PROFILE_FILE="$HOME/.bashrc"
    SHELL_NAME="bash"
else
    PROFILE_FILE="$HOME/.profile"
    SHELL_NAME="default"
fi

echo "📝 Using profile file: $PROFILE_FILE"
echo ""

# Function to add or update environment variable
update_env_var() {
    local var_name=$1
    local var_value=$2
    local profile_file=$3
    
    # Remove existing line if it exists
    if [[ -f "$profile_file" ]]; then
        grep -v "export $var_name=" "$profile_file" > "${profile_file}.tmp" && mv "${profile_file}.tmp" "$profile_file"
    fi
    
    # Add new line
    echo "export $var_name=\"$var_value\"" >> "$profile_file"
}

# Get ORCID credentials
echo "🔬 ORCID Credentials (for SICON/SIFIN):"
read -p "ORCID Email: " orcid_email
read -s -p "ORCID Password: " orcid_password
echo ""

if [[ -n "$orcid_email" && -n "$orcid_password" ]]; then
    update_env_var "ORCID_EMAIL" "$orcid_email" "$PROFILE_FILE"
    update_env_var "ORCID_PASSWORD" "$orcid_password" "$PROFILE_FILE"
    echo "✅ ORCID credentials added"
fi

echo ""

# Get ScholarOne credentials
echo "📚 ScholarOne Credentials (for MF/MOR):"
read -p "ScholarOne Email: " scholar_email
read -s -p "ScholarOne Password: " scholar_password
echo ""

if [[ -n "$scholar_email" && -n "$scholar_password" ]]; then
    update_env_var "SCHOLARONE_EMAIL" "$scholar_email" "$PROFILE_FILE"
    update_env_var "SCHOLARONE_PASSWORD" "$scholar_password" "$PROFILE_FILE"
    echo "✅ ScholarOne credentials added"
fi

echo ""

# Optional: OpenAI API Key
echo "🤖 OpenAI API Key (optional, for AI analysis):"
read -p "OpenAI API Key (press Enter to skip): " openai_key

if [[ -n "$openai_key" ]]; then
    update_env_var "OPENAI_API_KEY" "$openai_key" "$PROFILE_FILE"
    echo "✅ OpenAI API key added"
fi

echo ""
echo "✅ AUTOMATION SETUP COMPLETE!"
echo ""
echo "📋 Next steps:"
echo "1. Reload your shell profile:"
echo "   source $PROFILE_FILE"
echo ""
echo "2. Or restart your terminal"
echo ""
echo "3. Test automation:"
echo "   python3 test_credential_fix.py"
echo ""
echo "🚀 Now you can run extractions without any prompts!"
echo "   The system will automatically use environment variables."
echo ""
echo "🔒 Security note:"
echo "   Your credentials are stored in your shell profile."
echo "   Make sure your home directory has proper permissions."

# Set proper permissions
chmod 600 "$PROFILE_FILE" 2>/dev/null || true

echo ""
echo "✅ Profile file permissions secured: $PROFILE_FILE"