#!/bin/bash
# PyStart Academy - Daily Question Bank Update
# This script fetches new Python practice signals and updates the question bank
#
# Usage: ./scripts/daily-update.sh [--dry-run]
#
# To install as cron job:
#   crontab -e
#   0 2 * * * /path/to/pystart-academy/scripts/daily-update.sh >> /var/log/pystart-update.log 2>&1

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/logs/daily-update-$(date +%Y%m%d).log"

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting daily question bank update..."

cd "$PROJECT_DIR"

# Pull latest changes
log "Pulling latest changes..."
git pull --quiet origin main || log "Warning: git pull failed"

# Run the update pipeline
log "Running signal collection and exercise generation..."
python3 scripts/daily_question_update.py 2>&1 | tee -a "$LOG_FILE"

# Import into question bank
if [ "$1" != "--dry-run" ]; then
    log "Importing exercises into curated-v2 question bank..."
    python3 scripts/import_to_curated_bank.py 2>&1 | tee -a "$LOG_FILE"
else
    log "Dry run - skipping import"
    python3 scripts/import_to_curated_bank.py --dry-run 2>&1 | tee -a "$LOG_FILE"
fi

# Commit and push changes
if [ "$1" != "--dry-run" ]; then
    log "Committing changes..."
    git add data/latest_python_questions.json question_banks/curated-v2/question_bank.json
    
    if git diff --cached --quiet; then
        log "No changes to commit."
    else
        DATE=$(date +%Y-%m-%d)
        git commit -m "chore: daily question bank update ${DATE}

Automated update from web trend signals."
        git push --quiet origin main || log "Warning: git push failed"
        log "Changes committed and pushed."
    fi
fi

log "Daily update completed successfully!"

# Clean up old logs (keep last 30 days)
find "$PROJECT_DIR/logs" -name "daily-update-*.log" -mtime +30 -delete 2>/dev/null || true
