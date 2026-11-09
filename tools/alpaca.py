#!/usr/bin/env python3
"""Alpaca trading API client for cloud runs (stdlib only).

Keys come from the environment: ALPACA_API_KEY, ALPACA_SECRET_KEY.
ALPACA_PAPER_TRADE must be exactly "false" to reach the LIVE account;
anything else, including unset, uses the paper account.

  alpaca.py mode                        which account (live/paper) this run is using
  alpaca.py account                     equity, cash, buying power, status
  alpaca.py config                      margin/shorting/options settings
  alpaca.py positions                   open positions
  alpaca.py orders [open|closed|all] [N]
  alpaca.py activities [YYYY-MM-DD]     fills on/after a date
  alpaca.py clock                       is the market open, next open/close
  alpaca.py asset SYMBOL                tradable/fractionable
  alpaca.py quote SYMBOL[,SYMBOL...]    latest trade, quote and daily bars
  alpaca.py buy SYMBOL DOLLARS [CLIENT_ORDER_ID]      market, day, fractional by notional
  alpaca.py sell SYMBOL QTY|all [CLIENT_ORDER_ID]     market, day
  alpaca.py order ORDER_ID              one order's status and fill

Never prints the keys.
"""
import json, os, sys, urllib.error, urllib.request

LIVE = os.environ.get("ALPACA_PAPER_TRADE", "true").strip().lower() == "false"
BASE = "https://api.alpaca.markets/v2" if LIVE else "https://paper-api.alpaca.markets/v2"
DATA = "https://data.alpaca.markets/v2"

def call(method, url, body=None):
    key, secret = os.environ.get("ALPACA_API_KEY"), os.environ.get("ALPACA_SECRET_KEY")
    if not key or not secret:
        sys.exit("ALPACA_API_KEY / ALPACA_SECRET_KEY are not set in this environment.")
    req = urllib.request.Request(url, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret,
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"Alpaca {e.code}: {e.read().decode(errors='ignore')[:500]}")

def show(obj, keys=None):
    if isinstance(obj, list):
        for o in obj:
            show(o, keys); print("-")
        if not obj:
            print("(none)")
        return
    for k in keys or obj.keys():
        print(f"{k:28} {obj.get(k)}")

ORDER_KEYS = ["id", "client_order_id", "symbol", "side", "type", "notional", "qty", "status",
              "filled_qty", "filled_avg_price", "submitted_at", "filled_at"]

def main(cmd, *a):
    if cmd == "mode":
        print("LIVE (real money)" if LIVE else "PAPER"); print(BASE)
    elif cmd == "account":
        show(call("GET", f"{BASE}/account"), ["status", "equity", "last_equity", "cash", "buying_power",
             "multiplier", "shorting_enabled", "options_trading_level", "trading_blocked", "pattern_day_trader"])
    elif cmd == "config":
        show(call("GET", f"{BASE}/account/configurations"))
    elif cmd == "positions":
        show(call("GET", f"{BASE}/positions"), ["symbol", "qty", "avg_entry_price", "current_price",
             "market_value", "cost_basis", "unrealized_pl", "unrealized_plpc", "change_today"])
    elif cmd == "orders":
        status, n = (a + ("all",))[0], int((a + (None, "20"))[1] or 20)
        show(call("GET", f"{BASE}/orders?status={status}&limit={n}&direction=desc"), ORDER_KEYS)
    elif cmd == "activities":
        q = f"?activity_types=FILL&after={a[0]}T00:00:00Z" if a else "?activity_types=FILL"
        show(call("GET", f"{BASE}/account/activities{q}"))
    elif cmd == "clock":
        show(call("GET", f"{BASE}/clock"))
    elif cmd == "asset":
        show(call("GET", f"{BASE}/assets/{a[0].upper()}"), ["symbol", "name", "exchange", "status",
             "tradable", "fractionable"])
    elif cmd == "quote":
        snap = call("GET", f"{DATA}/stocks/snapshots?symbols={a[0].upper()}")
        for sym, s in snap.items():
            lt, lq, d, p = s.get("latestTrade", {}), s.get("latestQuote", {}), s.get("dailyBar", {}), s.get("prevDailyBar", {})
            print(f"{sym}: last {lt.get('p')} at {lt.get('t')}  bid {lq.get('bp')} ask {lq.get('ap')}  "
                  f"today o{d.get('o')} h{d.get('h')} l{d.get('l')} c{d.get('c')} v{d.get('v')}  prev close {p.get('c')}")
    elif cmd == "buy":
        body = {"symbol": a[0].upper(), "side": "buy", "type": "market", "time_in_force": "day",
                "notional": f"{float(a[1]):.2f}"}
        if len(a) > 2:
            body["client_order_id"] = a[2]
        show(call("POST", f"{BASE}/orders", body), ORDER_KEYS)
    elif cmd == "sell":
        if a[1] == "all":
            show(call("DELETE", f"{BASE}/positions/{a[0].upper()}"), ORDER_KEYS)
        else:
            body = {"symbol": a[0].upper(), "side": "sell", "type": "market", "time_in_force": "day", "qty": a[1]}
            if len(a) > 2:
                body["client_order_id"] = a[2]
            show(call("POST", f"{BASE}/orders", body), ORDER_KEYS)
    elif cmd == "order":
        show(call("GET", f"{BASE}/orders/{a[0]}"), ORDER_KEYS)
    else:
        sys.exit(__doc__)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(*sys.argv[1:])
