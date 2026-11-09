#!/bin/bash
# Post-close run: log fills, update trade log, write the daily report.
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
cd "$HOME/trading" || exit 1
STAMP=$(date +%Y-%m-%d)
LOG="$HOME/trading/logs/postclose-$STAMP.log"
git pull --rebase --autostash -q >> "$LOG" 2>&1 || echo "git pull failed" >> "$LOG"
caffeinate -i claude -p "$(cat "$HOME/trading/prompts/postclose.txt")" \
  --model claude-sonnet-5 \
  --add-dir "$HOME/trading" \
  --allowedTools "mcp__alpaca-live__*" "Read" "Write" "Edit" "WebSearch" "WebFetch" \
  "Bash(~/trading/tools/benchmark.py:*)" "Bash(python3 ~/trading/tools/benchmark.py:*)" "Bash(tools/benchmark.py:*)" "Bash(python3 tools/benchmark.py:*)" "Bash(./tools/benchmark.py:*)" \
  >> "$LOG" 2>&1
RC=$?
# Publish the trade log and report so the next cloud research run sees them.
git add TRADES.md reports/ >> "$LOG" 2>&1
git diff --cached --quiet || git commit -q -m "Post-close $STAMP" >> "$LOG" 2>&1
git push -q >> "$LOG" 2>&1 || echo "git push failed" >> "$LOG"
# Email the owner only if something went wrong (login expired, missing report, breaker, etc.).
"$HOME/trading/tools/alert.py" check postclose "$LOG" "$RC" >> "$LOG" 2>&1
