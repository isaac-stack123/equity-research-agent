# Trading Strategy

**Status:** approved rulebook for a dedicated live account (see section 10).
**Mode:** LIVE, dedicated account.

Every scheduled run reads this file first and follows it. If a proposed trade
is not permitted here, it does not happen. When in doubt, do nothing and note
it in the log.


---

## 0. BASE — the account's actual equity

- The **book** is the live account's equity as Alpaca reports it (funded
  2026-09-24).
- Position sizes in section 3 are percentages of the book.
- The circuit breakers in section 6 are measured from starting equity.
- Every run reads live equity before acting and states it in the daily report.

---

## 1. Account

- **Starting equity:** the amount funded on 2026-09-24. An earlier paper-trading
  stage preceded it.
- **Account type:** cash (no margin — no borrowing from the broker)
- **Objective:** high-volatility returns, accepting large gains and losses

This is a high-volatility mandate. The stop rules below cap how fast it can go
wrong, not whether it can.

## 2. What may be traded

**Long positions only.** Every position is a purchase of shares. Nothing is sold
short, nothing is borrowed.

**Permitted:**
- Leveraged index and sector ETFs — TQQQ, SQQQ, SOXL, SOXS, LABU, LABD, UVXY
  (these move 2–3x the daily move of what they track, up and down). An inverse
  ETF like SQQQ is permitted because it is *bought* — a long position in a fund
  that rises when its index falls, not a short sale.
- High-volatility single stocks, US-listed, price > $5, average daily volume
  > 5 million shares
- **Small-company slot (added 2026-09-24): at most ONE open position** may be a
  smaller, less-followed company that fails the volume test above, if it meets all of:
  - common stock listed on NYSE or Nasdaq (no OTC or "pink sheet" stocks)
  - price > $3, market value $100 million to $5 billion
  - average daily *dollar* volume > $2 million over the last 20 days
  - thesis rests on a primary source: an SEC filing (8-K, 10-Q, 10-K, Form 4,
    spin-off Form 10) or a dated corporate event, cited in TRADES.md
  - **limit orders only**, never market orders (small stocks have wide spreads;
    a market order can fill far from the last price)
  - **maximum 25% of the book** for this slot
  The point of this slot is to test whether reading filings nobody else reads is an
  edge. Every report marks this position so its results can be compared.

- QQQ, only as the idle-cash holding in section 3

**Not permitted:**
- Crypto — removed 2026-09-22 (the system is long-only stocks and ETFs)
- Options — outside the mandate
- Margin or short selling — cash account, no borrowing, no shorting
- Stocks under $5 or under 5M average daily volume — except one position that
  meets the small-company slot rules above. Below those limits, prices are too easily
  manipulated and spreads are costly
- Anything not listed as permitted above

## 3. Position sizing

- **Maximum 4 open positions at a time.** Four is the ceiling, not a target —
  see below.
- **Maximum 60% of the book per position.** Raised from 45% on 2026-09-24.
- **No minimum cash balance.** The book may be fully invested (removed 2026-09-24).
- **Idle cash goes into QQQ** (Nasdaq-100 index fund; added 2026-09-25). Settled cash
  above ~5% of the book that no thesis trade needs is held in QQQ. QQQ is the default
  holding, not a bet: it needs no thesis or invalidation point, does not count toward the
  4-position limit, and is exempt from the -30% hard stop and from resting stop orders
  (the section 6 breakers still cover it). It is sold first to fund any thesis trade. The sale settles next business
  day, so that entry waits a day unless enough settled cash already exists.
- **Weight by conviction, not by slot count.** Positions are not equal-weighted.
  The highest-conviction idea may take the full 60%; a medium-conviction idea
  takes ~25-35%. A slot is filled only when a thesis clears section 4 — an empty
  slot is a position in cash, and cash is preferable to a manufactured thesis.
  Deploying the book is not itself a goal.
- Fractional shares are used to hit these sizes precisely.

## 4. Entry rules

Horizon: **weeks to months.** The priority is return, not speed.

A position requires a written **thesis** plus a written **invalidation point**,
both recorded in `TRADES.md` before entry. The thesis comes from one of:

1. **A dated catalyst** — a specific, verifiable event: an earnings report, an
   SEC filing (8-K, 10-Q, 10-K), an FOMC decision, a CPI release, a named
   company announcement.
2. **A trend or macro thesis** — a documented, checkable argument about a sector
   or the market over the coming weeks or months, citing specific evidence
   (rate path, capex cycle, sector earnings trend, commodity move). "Momentum"
   and "it looks strong" are still not theses.

**The invalidation point is mandatory and specific:** the observable fact that
would prove the thesis wrong — a level, a data release, a guidance change. If a
run cannot state one in a sentence, the thesis is too vague and there is no trade.

Every run checks each open position's invalidation point against reality.

## 5. Exit rules

- **Hard stop: -30% from entry.** Exit, no exceptions, no averaging down.
  Wider than a normal stop because a 3x ETF swings 20% in ordinary chop — the
  stop is there to end a broken thesis, not to react to noise.
- **Stops are real orders.** Each open position carries a resting sell-stop order at
  Alpaca at its current stop level, so a stop fires during market hours rather than
  waiting for a scheduled run. Alpaca allows fractional-share stops only as day orders,
  so the pre-market run places them again every trading day. The small-company slot
  uses a stop-limit, with the limit 5% below the stop (section 2 bars market orders);
  if the price gaps past that limit, the next run exits under this rule.
- **No fixed profit target.** Once a position is up 40%, trail a 20% stop from
  the high and let it run. Winners paying for losers is the whole model here.
- **Time stop: 60 trading days (~3 months).** If the thesis has not played out
  by then, exit and note why in the log. One exception: if the company has officially
  announced its next earnings date, and that date falls within 5 trading days after the
  time stop, the time stop moves to the first session after the report. An estimated
  date does not qualify. The other exit rules still apply during the extension.
- **Invalidation hit:** if the position's written invalidation point occurs, exit
  at the next session regardless of P&L. This overrides everything above — it is
  the one rule that is never overridden by a hopeful re-read of the thesis.

## 6. Account-level circuit breaker

- **If equity falls 40% below starting equity, all trading stops.** Close positions,
  write a full post-mortem, and do not trade again until the owner reviews and
  restarts it.
- **If equity falls 20% below starting equity, position sizing halves** (max 30% per
  position) until equity recovers to within 5% of starting equity.

## 7. Cadence

- **Pre-market, 8:00am ET weekdays:** read overnight news and new filings on open
  positions and the watchlist; check stops; place orders.
- **Post-close, 4:30pm ET weekdays:** log fills, update the trade log, write the
  daily report to the owner.
- Positions are held overnight by design (swing trading).

## 8. Logging

Every trade is written to `TRADES.md` at entry and at exit:
date, ticker, direction, size, entry price, the catalyst, the one-sentence
thesis, then exit price, P&L, and what the outcome taught.

Each run reads `TRADES.md` before acting. This file plus that log is the only
memory the system has between runs.

## 9. Going live

Paper trading runs for **one month from the first trade**. At the end, the owner
reviews the log and decides. Live trading requires, at minimum:

- The owner's written approval recorded in this file, with a date
- A dedicated account funded with a fixed amount and nothing more
- Margin and options disabled at the broker
- `ALPACA_PAPER_TRADE` changed to `false` — a deliberate, separate step

## 10. Rule history

Live trading was approved by the account owner on 2026-09-24, after a paper-trading
stage. The agent places orders without per-trade confirmation, inside these rules.

How the rules evolved:

- Entries widened from dated catalysts only to catalysts or documented trend/macro
  theses, with a written invalidation point now required for every position.
- Time stop extended from 15 to 60 trading days; hard stop widened from -20% to -30%;
  fixed profit target replaced by a 20% trailing stop once a position is up 40%.
- Maximum positions raised from 2 to 4, weighted by conviction.
- Crypto removed; the system is long-only stocks and ETFs.
- One small-company slot added to test whether filing-based research is an edge.
- Idle cash moved from a minimum cash balance into QQQ.
- Stops changed from being checked at scheduled runs to resting broker orders.
