#!/bin/bash
# Script to run SICON extraction with proper environment

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Editorial Scripts - SICON Extraction${NC}"
echo "======================================"

# Check if we're in the right directory
if [ ! -d "editorial_scripts_ultimate" ]; then
    echo -e "${RED}Error: Must run from editorial_scripts directory${NC}"
    exit 1
fi

# Load credentials from .env.production if it exists
if [ -f ".env.production" ]; then
    echo -e "${GREEN}Loading credentials from .env.production${NC}"
    export $(grep -v '^#' .env.production | xargs)
fi

# Check credentials
if [ -z "$ORCID_EMAIL" ] || [ -z "$ORCID_PASSWORD" ]; then
    echo -e "${RED}Error: Missing credentials${NC}"
    echo ""
    echo "Please set credentials first:"
    echo '  export ORCID_EMAIL="your.email@example.com"'
    echo '  export ORCID_PASSWORD="your_password"'
    echo ""
    echo "Or use the credential manager:"
    echo "  python3 scripts/setup/secure_credential_manager.py --setup"
    exit 1
fi

echo -e "${GREEN}✓ Credentials found${NC}"
echo "  ORCID_EMAIL: $ORCID_EMAIL"
echo ""

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
else
    echo -e "${RED}Error: Virtual environment not found${NC}"
    exit 1
fi

# Run SICON extraction
echo -e "${YELLOW}Starting SICON extraction...${NC}"
echo ""

cd editorial_scripts_ultimate
python main.py sicon --test

# Capture exit code
EXIT_CODE=$?

# Deactivate virtual environment
deactivate

# Show results location
echo ""
echo -e "${YELLOW}Results saved to:${NC}"
echo "  editorial_scripts_ultimate/ultimate_results/"
echo ""

# Exit with same code as the extraction
exit $EXIT_CODE