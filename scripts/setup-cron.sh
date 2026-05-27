#!/bin/bash
# Setup script for PyStart Academy daily update cron job
# Run this script to install the cron job

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
UPDATE_SCRIPT="$PROJECT_DIR/scripts/daily-update.sh"

echo "PyStart Academy - Daily Update Setup"
echo "====================================="
echo ""
echo "Project directory: $PROJECT_DIR"
echo "Update script: $UPDATE_SCRIPT"
echo ""

# Check if script exists
if [ ! -f "$UPDATE_SCRIPT" ]; then
    echo "Error: Update script not found at $UPDATE_SCRIPT"
    exit 1
fi

# Make sure script is executable
chmod +x "$UPDATE_SCRIPT"

# Create cron job entry (run daily at 02:00 UTC / 10:00 Beijing time)
CRON_ENTRY="0 2 * * * $UPDATE_SCRIPT >> /var/log/pystart-update.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "pystart-academy"; then
    echo "Cron job already exists:"
    crontab -l | grep "pystart"
    echo ""
    read -p "Replace existing cron job? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 0
    fi
    # Remove existing entry
    crontab -l | grep -v "pystart-academy" | crontab -
fi

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo "Cron job installed successfully!"
echo ""
echo "Schedule: Daily at 02:00 UTC (10:00 Beijing time)"
echo "Log file: /var/log/pystart-update.log"
echo ""
echo "To verify: crontab -l"
echo "To remove: crontab -e (delete the pystart-academy line)"
echo ""
echo "To run manually: $UPDATE_SCRIPT"
echo "To dry-run: $UPDATE_SCRIPT --dry-run"
