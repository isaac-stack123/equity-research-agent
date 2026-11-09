#!/bin/bash
# Registers the LIVE Alpaca account with Claude Code as a separate MCP server
# named "alpaca-live". The paper server ("alpaca") is left untouched.
# Reads keys from ~/.alpaca-live.env and never prints them.
set -a; . "$HOME/.alpaca-live.env"; set +a
if [ -z "$ALPACA_API_KEY" ] || [ -z "$ALPACA_SECRET_KEY" ]; then
  echo "Keys missing: fill in ~/.alpaca-live.env first."; exit 1
fi
claude mcp remove alpaca-live -s user >/dev/null 2>&1
if claude mcp add alpaca-live -s user \
     -e ALPACA_API_KEY="$ALPACA_API_KEY" \
     -e ALPACA_SECRET_KEY="$ALPACA_SECRET_KEY" \
     -e ALPACA_PAPER_TRADE=false \
     -- uvx alpaca-mcp-server >/dev/null 2>&1; then
  echo "Connected: alpaca-live registered (paper server unchanged)."
else
  echo "Failed to register alpaca-live."; exit 1
fi
