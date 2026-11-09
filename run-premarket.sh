#!/bin/bash
# Pre-market run: news, filings, stop checks, orders. LIVE account (alpaca-live).
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
# Let background analyst agents (e.g. risk-reviewer) finish: 30 min, not the 10 min default.
export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=1800000
caffeinate -i -w $$ &
cd "$HOME/trading" || exit 1
STAMP=$(date +%Y-%m-%d)
LOG="$HOME/trading/logs/premarket-$STAMP.log"
# Pull the cloud research brief and the latest log before trading.
git pull --rebase --autostash -q >> "$LOG" 2>&1 || echo "git pull failed" >> "$LOG"
# Data-tool rules below cover every form agents call them in (bare, python3, full, relative paths).
caffeinate -i claude -p "$(cat "$HOME/trading/prompts/premarket.txt")" \
  --model claude-sonnet-5 \
  --add-dir "$HOME/trading" \
  --allowedTools "mcp__alpaca-live__*" "Read" "Write" "Edit" "WebSearch" "WebFetch" "Agent" \
  "Bash(~/trading/tools/edgar.py:*)" "Bash(python3 ~/trading/tools/edgar.py:*)" \
  "Bash(tools/edgar.py:*)" "Bash(python3 tools/edgar.py:*)" "Bash(./tools/edgar.py:*)" "Bash(python3 ./tools/edgar.py:*)" \
  "Bash(~/trading/tools/technicals.py:*)" "Bash(python3 ~/trading/tools/technicals.py:*)" \
  "Bash(tools/technicals.py:*)" "Bash(python3 tools/technicals.py:*)" "Bash(./tools/technicals.py:*)" "Bash(python3 ./tools/technicals.py:*)" \
  "Bash(~/trading/tools/stocktwits.py:*)" "Bash(python3 ~/trading/tools/stocktwits.py:*)" \
  "Bash(tools/stocktwits.py:*)" "Bash(python3 tools/stocktwits.py:*)" "Bash(./tools/stocktwits.py:*)" "Bash(python3 ./tools/stocktwits.py:*)" \
  "Bash(~/trading/tools/screen.py:*)" "Bash(python3 ~/trading/tools/screen.py:*)" \
  "Bash(tools/screen.py:*)" "Bash(python3 tools/screen.py:*)" "Bash(./tools/screen.py:*)" "Bash(python3 ./tools/screen.py:*)" \
  "Bash(~/trading/tools/dcf.py:*)" "Bash(python3 ~/trading/tools/dcf.py:*)" \
  "Bash(tools/dcf.py:*)" "Bash(python3 tools/dcf.py:*)" "Bash(./tools/dcf.py:*)" "Bash(python3 ./tools/dcf.py:*)" \
  "Bash(curl -s https://gamma-api.polymarket.com:*)" "Bash(curl -s \"https://gamma-api.polymarket.com:*)" \
  >> "$LOG" 2>&1
RC=$?
# Publish the trade log and report so the next cloud research run sees them.
git add TRADES.md reports/ >> "$LOG" 2>&1
git diff --cached --quiet || git commit -q -m "Pre-market $STAMP" >> "$LOG" 2>&1
git push -q >> "$LOG" 2>&1 || echo "git push failed" >> "$LOG"
# Email the owner only if something went wrong (login expired, missing report, breaker, etc.).
"$HOME/trading/tools/alert.py" check premarket "$LOG" "$RC" >> "$LOG" 2>&1
