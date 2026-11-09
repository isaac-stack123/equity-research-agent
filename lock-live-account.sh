#!/bin/bash
# Locks the LIVE Alpaca account to section 2 of STRATEGY.md: no margin, no shorting.
# Changes account settings only. Places no orders. Never prints the keys.
set -a; . "$HOME/.alpaca-live.env"; set +a
if [ -z "$ALPACA_API_KEY" ] || [ -z "$ALPACA_SECRET_KEY" ]; then
  echo "Keys missing: fill in ~/.alpaca-live.env first."; exit 1
fi
curl -s -X PATCH "https://api.alpaca.markets/v2/account/configurations" \
  -H "APCA-API-KEY-ID: $ALPACA_API_KEY" -H "APCA-API-SECRET-KEY: $ALPACA_SECRET_KEY" \
  -H "Content-Type: application/json" \
  -d '{"no_shorting": true, "max_margin_multiplier": "1"}' | python3 -c '
import json,sys
c=json.load(sys.stdin)
if "no_shorting" not in c: print("Alpaca error:", c.get("message", c)); sys.exit(1)
print("Updated. Now:")
for k in ["no_shorting","max_margin_multiplier","max_options_trading_level"]:
    print(f"  {k:24} {c.get(k)}")'
