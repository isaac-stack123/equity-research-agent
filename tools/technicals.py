#!/usr/bin/env python3
"""Price-trend indicators from Yahoo daily bars (free, no key). Read-only.

  technicals.py TICKER        one year of daily bars -> trend, momentum, volatility summary
"""
import json, sys, datetime, urllib.request

def bars(t):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=1y&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    r = json.load(urllib.request.urlopen(req, timeout=30))["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    rows = [(datetime.date.fromtimestamp(ts), o, h, l, c, v) for ts, o, h, l, c, v in
            zip(r["timestamp"], q["open"], q["high"], q["low"], q["close"], q["volume"]) if c is not None]
    return rows

def sma(x, n): return sum(x[-n:]) / n if len(x) >= n else None
def ema_series(x, n):
    k, out = 2 / (n + 1), [x[0]]
    for v in x[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out

def rsi(c, n=14):
    g = [max(c[i] - c[i - 1], 0) for i in range(1, len(c))]
    l = [max(c[i - 1] - c[i], 0) for i in range(1, len(c))]
    ag, al = sum(g[:n]) / n, sum(l[:n]) / n
    for i in range(n, len(g)):
        ag, al = (ag * (n - 1) + g[i]) / n, (al * (n - 1) + l[i]) / n
    return 100 if al == 0 else 100 - 100 / (1 + ag / al)

def main(t):
    rows = bars(t)
    d, h, l, c, v = [r[0] for r in rows], [r[2] for r in rows], [r[3] for r in rows], [r[4] for r in rows], [r[5] or 0 for r in rows]
    px = c[-1]
    s50, s200, e10 = sma(c, 50), sma(c, 200), ema_series(c, 10)[-1]
    macd = [a - b for a, b in zip(ema_series(c, 12), ema_series(c, 26))]
    sig = ema_series(macd, 9)
    mid = sma(c, 20)
    sd = (sum((x - mid) ** 2 for x in c[-20:]) / 20) ** 0.5
    tr = [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, len(c))]
    atr = sum(tr[-14:]) / 14
    vol20, vol_today = sma(v, 20), v[-1]
    hi52, lo52 = max(h), min(l)
    ret = lambda n: (px / c[-1 - n] - 1) * 100 if len(c) > n else float("nan")
    f = lambda x: "n/a" if x is None else f"{x:,.2f}"
    print(f"{t} as of {d[-1]} close ${px:,.2f}  ({len(c)} daily bars, Yahoo; verify prices before trading)")
    print(f"Returns: 5d {ret(5):+.1f}%  1m {ret(21):+.1f}%  3m {ret(63):+.1f}%  6m {ret(126):+.1f}%")
    print(f"52-week range ${lo52:,.2f} - ${hi52:,.2f}; price is {(px/hi52-1)*100:+.1f}% from the high")
    print(f"Trend: 10-day EMA {f(e10)}  50-day SMA {f(s50)}  200-day SMA {f(s200)}"
          + (f"  -> price {'above' if px > s50 else 'below'} 50d, {'above' if s200 and px > s200 else 'below'} 200d" if s50 else ""))
    print(f"Momentum: RSI(14) {rsi(c):.1f}  MACD {macd[-1]:.2f} vs signal {sig[-1]:.2f} (histogram {macd[-1]-sig[-1]:+.2f})")
    print(f"Bollinger(20,2): {f(mid-2*sd)} / {f(mid)} / {f(mid+2*sd)}")
    print(f"Volatility: ATR(14) ${atr:,.2f} = {atr/px*100:.1f}% of price per day")
    print(f"Volume: last {vol_today:,.0f} vs 20-day avg {vol20:,.0f} ({vol_today/vol20:.1f}x)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1].upper())
