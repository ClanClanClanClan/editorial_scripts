#!/bin/bash
# Setup script for weekly referee extraction cron job

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_PATH=$(which python3)

echo "Setting up weekly referee extraction cron job..."
echo "Script directory: $SCRIPT_DIR"
echo "Python path: $PYTHON_PATH"

# Create log directory
mkdir -p "$SCRIPT_DIR/logs"

# Create wrapper script that handles environment
cat > "$SCRIPT_DIR/run_weekly_cron.sh" << EOF
#!/bin/bash
# Wrapper script for cron execution

# Set up environment
export PATH="/usr/local/bin:/usr/bin:/bin"
cd "$SCRIPT_DIR"

# Run extraction and log output
LOG_FILE="$SCRIPT_DIR/logs/weekly_extraction_\$(date +%Y%m%d_%H%M%S).log"
echo "Starting weekly extraction at \$(date)" >> "\$LOG_FILE"

$PYTHON_PATH "$SCRIPT_DIR/run_weekly_extraction.py" >> "\$LOG_FILE" 2>&1

# Check if successful and send notification
if [ \$? -eq 0 ]; then
    echo "Extraction completed successfully at \$(date)" >> "\$LOG_FILE"
    
    # Optional: Send email notification with digest
    # mail -s "Weekly Referee Extraction Complete" your@email.com < "$SCRIPT_DIR/weekly_extractions/\$(date +%Y_week_%V)/email_digest.txt"
else
    echo "Extraction failed at \$(date)" >> "\$LOG_FILE"
    # Optional: Send failure notification
    # echo "Weekly extraction failed. Check logs at $SCRIPT_DIR/logs/" | mail -s "Referee Extraction Failed" your@email.com
fi
EOF

# Make wrapper executable
chmod +x "$SCRIPT_DIR/run_weekly_cron.sh"

# Display cron entry to add
echo ""
echo "Add this line to your crontab (run 'crontab -e' to edit):"
echo ""
echo "# Run referee extraction every Monday at 9 AM"
echo "0 9 * * 1 $SCRIPT_DIR/run_weekly_cron.sh"
echo ""
echo "Or for testing (every hour):"
echo "0 * * * * $SCRIPT_DIR/run_weekly_cron.sh"
echo ""
echo "To check current cron jobs: crontab -l"
echo "To edit cron jobs: crontab -e"
echo ""
echo "Logs will be saved to: $SCRIPT_DIR/logs/"