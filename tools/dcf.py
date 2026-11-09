#!/usr/bin/env python3
"""Discounted-cash-flow valuation: bear/base/bull cases, per-segment or single-line,
plus a reverse DCF (what the current price already assumes). Stdlib only.

dcf.py ASSUMPTIONS.json [PRICE]        (without PRICE, the last Yahoo close is used)

Two input shapes. Both need: ticker, net_debt, shares, discount, terminal_growth, cases.

1) Single line (one business):
   "revenue": 775e9, "fcf_margin_now": -0.01,
   "cases": {"base": {"growth": 0.11, "margin": 0.08}, ...}
   Revenue growth fades in a straight line to terminal_growth by year 10; the
   free-cash-flow margin moves in a straight line to `margin` by year 5, then holds.

2) Segments (businesses with different growth and margins, e.g. AWS vs retail):
   "tax_rate": 0.18, "conversion_now": -0.10,
   "segments": {"AWS": {"revenue": 169e9, "margin_now": 0.39}, ...},
   "cases": {"base": {"conversion": 0.7,
                      "AWS": {"growth": 0.30, "margin": 0.35}, ...}, ...}
   Optional per-case "roic" (return on invested capital, e.g. 0.18): from year 11 on,
   reinvestment falls to terminal_growth / roic of after-tax profit, the steady-state
   rule, instead of holding `conversion` forever.
   Each segment grows and changes margin as above -> operating income. After tax,
   `conversion` is the share of that profit left as free cash after reinvestment
   (capex beyond depreciation, working capital). It moves from conversion_now to the
   case value by year 5. Heavy building = low conversion; mature = high.

Each year's free cash flow is discounted at `discount`; a terminal value (Gordon
growth) covers year 11 onward. Equity = enterprise value - net debt, per share.
"""
import copy, json, sys, urllib.request

YEARS = 10


def ramp(now, target, y):
    return now + (target - now) * min(y, 5) / 5


def fade(g0, g_t, y):
    return g0 + (g_t - g0) * (y - 1) / (YEARS - 1)


def cash_flows(a, case):
    """Yearly (revenue, free cash flow) for one case."""
    g_t, out = a["terminal_growth"], []
    if "segments" in a:
        rev = {k: s["revenue"] for k, s in a["segments"].items()}
        for y in range(1, YEARS + 1):
            oi = 0.0
            for k, s in a["segments"].items():
                rev[k] *= 1 + fade(case[k]["growth"], g_t, y)
                oi += rev[k] * ramp(s["margin_now"], case[k]["margin"], y)
            conv = ramp(a["conversion_now"], case["conversion"], y)
            out.append((sum(rev.values()), oi * (1 - a["tax_rate"]) * conv, oi))
    else:
        rev = a["revenue"]
        for y in range(1, YEARS + 1):
            rev *= 1 + fade(case["growth"], g_t, y)
            out.append((rev, rev * ramp(a["fcf_margin_now"], case["margin"], y), None))
    return out


def value(a, case, discount=None):
    r, g_t = discount or a["discount"], a["terminal_growth"]
    flows = cash_flows(a, case)
    pv = sum(f / (1 + r) ** y for y, (_, f, _) in enumerate(flows, 1))
    last = flows[-1][1]
    if "roic" in case and flows[-1][2] is not None:
        # Mature years: reinvest only growth / return-on-capital of after-tax profit.
        last = flows[-1][2] * (1 - a["tax_rate"]) * (1 - g_t / case["roic"])
    pv_tv = last * (1 + g_t) / (r - g_t) / (1 + r) ** YEARS
    return (pv + pv_tv - a["net_debt"]) / a["shares"], flows, pv_tv / (pv + pv_tv)


def solve(f, lo, hi, target):
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) < target else (lo, mid)
    return mid


def with_growth_shift(case, a, d):
    c = copy.deepcopy(case)
    if "segments" in a:
        for k in a["segments"]:
            c[k]["growth"] += d
    else:
        c["growth"] += d
    return c


def last_close(t):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=5d&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    q = json.load(urllib.request.urlopen(req, timeout=30))["chart"]["result"][0]["indicators"]["quote"][0]
    return [c for c in q["close"] if c][-1]


def main(path, price=None):
    a = json.load(open(path))
    price = price or last_close(a["ticker"])
    seg = "segments" in a
    print(f"{a['ticker']} DCF  price ${price:,.2f}  discount {a['discount']:.0%}  "
          f"terminal growth {a['terminal_growth']:.0%}  net debt ${a['net_debt']/1e9:,.1f}B  "
          f"{a['shares']/1e9:.2f}B shares")
    if seg:
        print("Segments now: " + ", ".join(f"{k} ${s['revenue']/1e9:,.0f}B @ {s['margin_now']:.0%}"
                                          for k, s in a["segments"].items()))
    print(f"\n{'case':<6}{'yr10 revenue':>13}{'yr10 op margin' if seg else '':>15}{'value/sh':>10}"
          f"{'vs price':>10}{'% from TV':>10}")
    for name, c in a["cases"].items():
        v, flows, tv = value(a, c)
        rev10, _, oi10 = flows[-1]
        om = f"{oi10/rev10:>15.1%}" if seg else f"{'':>15}"
        print(f"{name:<6}{rev10/1e9:>12,.0f}B{om}{v:>10,.0f}{v/price-1:>+10.0%}{tv:>10.0%}")
    base = a["cases"]["base"]
    print("\nBase case at other discount rates:",
          "  ".join(f"{r:.0%}: ${value(a, base, r)[0]:,.0f}" for r in (0.08, 0.09, 0.10)))
    print(f"\nReverse DCF (what ${price:,.2f} already assumes, holding the rest of the base case):")
    d = solve(lambda x: value(a, with_growth_shift(base, a, x))[0], -0.3, 0.6, price)
    print(f"  growth: every {'segment' if seg else 'line'} grows {d:+.1%} a year faster than base, at the start")
    if seg:
        k = "conversion"
        cv = solve(lambda x: value(a, dict(base, conversion=x))[0], -1, 3, price)
        print(f"  cash conversion: {cv:.0%} of after-tax operating profit kept as free cash (base {base[k]:.0%})")
        for s in a["segments"]:
            m = solve(lambda x: value(a, dict(base, **{s: dict(base[s], margin=x)}))[0], -1, 2, price)
            print(f"  {s} margin alone: {m:.0%} by year 5 (base {base[s]['margin']:.0%})")
    else:
        m = solve(lambda x: value(a, dict(base, margin=x))[0], -0.5, 1, price)
        print(f"  FCF margin: {m:.1%} by year 5 (base {base['margin']:.0%})")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else None)
