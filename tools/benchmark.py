#!/usr/bin/env python3
"""Account vs index benchmark since the live start (Yahoo daily closes, free, no key). Read-only.

  benchmark.py EQUITY [DEPOSITED]     EQUITY = live account equity; DEPOSITED = total money put in
                                      (default 100)

Compares the account's return with what the same money would have done sitting in QQQ or VOO
since the close on 2026-09-24. If the picks trail QQQ over months, the system is not adding value.
A later deposit is treated as if it had been there from the start, so the comparison is approximate
after one.
"""
import datetime, sys
from technicals import bars

START = datetime.date(2026, 9, 24)

def since_start(t):
    rows = bars(t)
    base = [r for r in rows if r[0] <= START][-1]
    last = rows[-1]
    return base[4], last[4], last[0]

def main(equity, deposited):
    acct = equity / deposited - 1
    print(f"Since {START} close (index prices are Yahoo daily closes, delayed):")
    print(f"  Account  ${equity:,.2f} on ${deposited:,.2f} deposited  {acct * 100:+.2f}%")
    for t in ("QQQ", "VOO"):
        b, px, d = since_start(t)
        r = px / b - 1
        print(f"  {t:7}  ${deposited * (1 + r):,.2f} if all in {t} ({b:.2f} -> {px:.2f} on {d})  {r * 100:+.2f}%"
              f"   account {'ahead by' if acct >= r else 'behind by'} {abs(acct - r) * 100:.2f} pts")

if __name__ == "__main__":
    a = sys.argv[1:]
    if not 1 <= len(a) <= 2:
        sys.exit(__doc__)
    main(float(a[0]), float(a[1]) if len(a) == 2 else 100.0)
