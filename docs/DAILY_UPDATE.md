# 🔄 Daily Question Bank Auto-Update

PyStart Academy includes an automated pipeline that fetches the latest Python practice trends from the web and updates the question bank daily.

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    Signal Sources                           │
├─────────────────────────────────────────────────────────────┤
│  GitHub Search API  │  RSS Feeds  │  Popular Exercise Sites │
│  (recent repos)     │  (articles) │  (W3Schools, etc.)      │
└─────────────────────┴──────┬──────┴─────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              daily_question_update.py                        │
│  • Collects 100+ signals from multiple sources              │
│  • Classifies into 30 chapter topics                        │
│  • Generates original exercises (not copied)                │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│            import_to_curated_bank.py                         │
│  • Deduplicates by title                                    │
│  • Replaces exercises of matching level                     │
│  • Maintains 8 exercises per chapter                        │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│         question_banks/curated-v2/question_bank.json        │
│                    (Production Bank)                         │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Manual Run
```bash
# Run the full update pipeline
python scripts/daily_question_update.py
python scripts/import_to_curated_bank.py

# Or use the convenience script
./scripts/daily-update.sh

# Preview changes without importing
./scripts/daily-update.sh --dry-run
```

### Automated Daily Updates

#### Option 1: System Cron (Recommended for local/server)
```bash
# Interactive setup
./scripts/setup-cron.sh

# Or manually add to crontab:
# 0 2 * * * /path/to/pystart-academy/scripts/daily-update.sh >> /var/log/pystart-update.log 2>&1
```

#### Option 2: GitHub Actions (Recommended for repos)
1. Copy the workflow reference:
   ```bash
   cp scripts/workflow-reference/daily-question-update.yml .github/workflows/
   ```
2. Commit and push:
   ```bash
   git add .github/workflows/daily-question-update.yml
   git commit -m "ci: enable daily question update"
   git push
   ```

**Note**: GitHub token needs `workflow` scope to push workflow files.

## Signal Sources

| Source | What It Fetches | Frequency |
|--------|-----------------|-----------|
| GitHub Search | Recent Python practice repos (last 30 days) | Daily |
| Real Python | Tutorial articles and exercises | Daily |
| Planet Python | Community blog posts | Daily |
| Python Insider | Official Python blog | Daily |
| W3Schools | Python exercise topics | Daily |
| PracticePython | Practice exercise listings | Daily |
| CodingBat | Python coding challenges | Daily |

## Topic Classification

Signals are automatically classified into 30 chapters based on keywords:

| Keyword | Chapter | Topic |
|---------|---------|-------|
| `quiz`, `dict` | c12 | 字典和集合 |
| `leetcode`, `algorithm` | c23 | 列表进阶 |
| `oop`, `class` | c19 | 类和对象 |
| `function`, `recursion` | c13 | 函数定义 |
| `loop` | c08 | 循环 |
| `string` | c10 | 字符串操作 |
| `file` | c26 | 文件脚本 |
| `exception`, `error` | c27 | 异常处理 |
| ... | ... | ... |

## Import Rules

- **Deduplication**: Skips exercises with existing titles
- **Level Matching**: Replaces exercises of the same difficulty level
- **Chapter Size**: Maintains 8 exercises per chapter (curated-v2 standard)
- **Backup**: Creates backup before import (`question_bank.backup.json`)
- **Non-Fatal Errors**: Import failures don't stop the pipeline

## File Structure

```
pystart-academy/
├── scripts/
│   ├── daily_question_update.py      # Main update pipeline
│   ├── import_to_curated_bank.py     # Import into question bank
│   ├── daily-update.sh               # Convenience shell script
│   ├── setup-cron.sh                 # Cron job installer
│   └── workflow-reference/
│       └── daily-question-update.yml # GitHub Actions reference
├── data/
│   └── latest_python_questions.json  # Latest generated drafts
└── question_banks/
    └── curated-v2/
        ├── question_bank.json        # Production question bank
        └── question_bank.backup.json # Backup (auto-created)
```

## Monitoring

### Check Update Status
```bash
# View latest generated exercises
cat data/latest_python_questions.json | python -m json.tool

# Check question bank metadata
python -c "import json; d=json.load(open('question_banks/curated-v2/question_bank.json')); print(f'Updated: {d.get(\"updatedAt\")}')"

# View cron job logs
tail -f /var/log/pystart-update.log
```

### Manual Verification
```bash
# Run dry-run to see what would change
python scripts/import_to_curated_bank.py --dry-run

# Validate question bank structure
python scripts/validate_curated_question_bank.py
```

## Troubleshooting

### No exercises generated
- Check internet connectivity
- Verify GitHub API rate limits (10 req/min without token)
- Check RSS feed availability

### Import fails
- Ensure `question_banks/curated-v2/question_bank.json` exists
- Verify JSON structure is valid
- Check file permissions

### Cron job not running
- Verify cron service is running: `systemctl status cron`
- Check cron logs: `grep CRON /var/log/syslog`
- Test script manually: `./scripts/daily-update.sh --dry-run`

## Contributing

To add new signal sources or topic rules, edit `scripts/daily_question_update.py`:

1. **Add RSS Feed**: Append to `RSS_FEEDS` list
2. **Add Topic Rule**: Append to `TOPIC_RULES` list
3. **Add Exercise Template**: Add to `TEMPLATES` dict

## License

This automated update system follows the same license as PyStart Academy.
