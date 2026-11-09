#!/usr/bin/env python3
"""Cheap first-pass screen of many stocks from Yahoo daily bars (free, no key). Read-only.

  screen.py                   screen every ticker in tools/universe.txt (~50)
  screen.py TICKER ...        screen just these tickers

One line per stock, grouped by sector: price, returns, distance from the 52-week
high, RSI, trend vs the 50/200-day averages, daily volatility, 20-day volume, and
whether it passes STRATEGY.md section 2 (price > $5, 20-day avg volume > 5M).
Flags point at something worth a look; they are not theses and not buy signals.
"""
import os, sys
from concurrent.futures import ThreadPoolExecutor
from technicals import bars, sma, rsi

UNIVERSE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "universe.txt")

def load_universe():
    groups = []
    for line in open(UNIVERSE):
        line = line.strip()
        if line and not line.startswith("#") and ":" in line:
            sector, tickers = line.split(":", 1)
            groups.append((sector.strip(), tickers.split()))
    return groups

def metrics(t):
    rows = bars(t)
    h, l, c, v = [r[2] for r in rows], [r[3] for r in rows], [r[4] for r in rows], [r[5] or 0 for r in rows]
    px = c[-1]
    s50, s200 = sma(c, 50), sma(c, 200)
    tr = [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, len(c))]
    vol20 = sma(v, 20)
    ret = lambda n: (px / c[-1 - n] - 1) * 100 if len(c) > n else float("nan")
    m = dict(t=t, date=rows[-1][0], px=px, r5=ret(5), r21=ret(21), r63=ret(63),
             off_hi=(px / max(h) - 1) * 100, rsi=rsi(c), atr=sum(tr[-14:]) / 14 / px * 100,
             vol20=vol20, vol_x=v[-1] / vol20 if vol20 else 0,
             trend=("above" if s50 and px > s50 else "below") + "/" + ("above" if s200 and px > s200 else "below"))
    m["eligible"] = px > 5 and vol20 > 5_000_000
    flags = []
    if m["rsi"] >= 70: flags.append("overbought")
    if m["rsi"] <= 30: flags.append("oversold")
    if m["off_hi"] >= -2: flags.append("at 52w high")
    if m["off_hi"] <= -30: flags.append(f"{m['off_hi']:.0f}% off high")
    if abs(m["r5"]) >= 8: flags.append(f"5d {m['r5']:+.0f}%")
    if m["vol_x"] >= 2: flags.append(f"volume {m['vol_x']:.1f}x")
    if trend_cross(c): flags.append(trend_cross(c))
    m["flags"] = flags
    return m

def trend_cross(c):
    """Price crossed its 50-day average within the last 5 sessions."""
    if len(c) < 56:
        return None
    was = c[-6] > sma(c[:-5], 50)
    now = c[-1] > sma(c, 50)
    return None if was == now else ("crossed above 50d" if now else "crossed below 50d")

def safe(t):
    try:
        return metrics(t)
    except Exception as e:
        return dict(t=t, error=f"{type(e).__name__}: {e}")

def main(args):
    groups = [("Requested", [a.upper() for a in args])] if args else load_universe()
    tickers = [t for _, ts in groups for t in ts]
    with ThreadPoolExecutor(8) as pool:
        results = dict(zip(tickers, pool.map(safe, tickers)))
    ok = [m for m in results.values() if "error" not in m]
    asof = max((m["date"] for m in ok), default="n/a")
    print(f"Screen of {len(tickers)} stocks, Yahoo daily bars as of {asof} (delayed; verify before trading)")
    print("trend = price vs 50-day / 200-day average; ATR = average daily range as % of price;"
          " elig = passes STRATEGY.md section 2 (price > $5, 20d avg volume > 5M)\n")
    hdr = f"{'tkr':6}{'price':>9}{'5d%':>7}{'1m%':>7}{'3m%':>7}{'offHi%':>8}{'RSI':>6}{'ATR%':>6}{'vol20M':>8}  {'trend':12}{'elig':5} flags"
    for sector, ts in groups:
        print(f"== {sector}")
        print(hdr)
        for t in ts:
            m = results[t]
            if "error" in m:
                print(f"{t:6} data failed: {m['error']}")
                continue
            print(f"{t:6}{m['px']:9.2f}{m['r5']:+7.1f}{m['r21']:+7.1f}{m['r63']:+7.1f}{m['off_hi']:+8.1f}"
                  f"{m['rsi']:6.0f}{m['atr']:6.1f}{m['vol20']/1e6:8.1f}  {m['trend']:12}{'yes' if m['eligible'] else 'NO':5} "
                  + ", ".join(m["flags"]))
        print()
    failed = [t for t, m in results.items() if "error" in m]
    if failed:
        print(f"Data failed for {len(failed)}: {' '.join(failed)}")

if __name__ == "__main__":
    main(sys.argv[1:])
