#!/bin/bash
# Read-only check of the LIVE Alpaca account. Prints balances and settings only,
# never the keys. Places no orders and changes nothing.
set -a; . "$HOME/.alpaca-live.env"; set +a
if [ -z "$ALPACA_API_KEY" ] || [ -z "$ALPACA_SECRET_KEY" ]; then
  echo "Keys missing: fill in ~/.alpaca-live.env first."; exit 1
fi
H=(-s -H "APCA-API-KEY-ID: $ALPACA_API_KEY" -H "APCA-API-SECRET-KEY: $ALPACA_SECRET_KEY")
BASE="https://api.alpaca.markets/v2"
curl "${H[@]}" "$BASE/account" | python3 -c '
import json,sys
a=json.load(sys.stdin)
if "status" not in a: print("Alpaca error:", a.get("message", a)); sys.exit(1)
for k in ["status","cash","equity","buying_power","multiplier","shorting_enabled","options_trading_level","options_approved_level","pattern_day_trader","trading_blocked","transfers_blocked"]:
    print(f"{k:24} {a.get(k)}")'
echo "--- configurations"
curl "${H[@]}" "$BASE/account/configurations" | python3 -c '
import json,sys
c=json.load(sys.stdin)
for k in ["no_shorting","max_margin_multiplier","max_options_trading_level","suspend_trade","trade_confirm_email"]:
    print(f"{k:24} {c.get(k)}")'
